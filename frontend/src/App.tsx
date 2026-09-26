import React, { useState, useEffect, useCallback } from "react";
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import type {
  DragStartEvent,
  DragEndEvent,
} from "@dnd-kit/core";
import { sortableKeyboardCoordinates } from "@dnd-kit/sortable";

import type { Board, Task, ColumnType, AISuggestion, DownstreamChange } from "./types";
import { api, type AuthUser } from "./api";
import { KanbanColumn } from "./components/KanbanColumn";
import { TaskCard } from "./components/TaskCard";
import { TaskDetailModal } from "./components/TaskDetailModal";
import { NewTaskModal } from "./components/NewTaskModal";
import { AISuggestionsDrawer } from "./components/AISuggestionsDrawer";
import { RippleToast } from "./components/RippleToast";
import { LoginScreen } from "./components/LoginScreen";
import { BoardDashboard } from "./components/BoardDashboard";
import { Sparkles, Plus, AlertCircle, GitBranch, LayoutGrid, ChevronLeft } from "lucide-react";

type AppScreen = "login" | "dashboard" | "board";

function getSavedUser(): AuthUser | null {
  try {
    const token = localStorage.getItem("auth_token");
    const raw = localStorage.getItem("auth_user");
    if (!token || !raw) return null;
    const info = JSON.parse(raw);
    return { access_token: token, token_type: "bearer", ...info };
  } catch {
    return null;
  }
}

export const App: React.FC = () => {
  const [screen, setScreen] = useState<AppScreen>("login");
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [activeBoardId, setActiveBoardId] = useState<number>(1);

  const [board, setBoard] = useState<Board | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  const [isNewTaskOpen, setIsNewTaskOpen] = useState(false);
  const [isAiDrawerOpen, setIsAiDrawerOpen] = useState(false);
  const [suggestions, setSuggestions] = useState<AISuggestion[]>([]);

  const [criticalPathIds, setCriticalPathIds] = useState<number[]>([]);
  const [showCriticalPath, setShowCriticalPath] = useState(false);

  const [downstreamChanges, setDownstreamChanges] = useState<DownstreamChange[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [invariantTaskIds, setInvariantTaskIds] = useState<number[]>([]);

  // On mount: restore session
  useEffect(() => {
    const saved = getSavedUser();
    if (saved) {
      setAuthUser(saved);
      setScreen("dashboard");
    }
  }, []);

  const handleAuth = (user: AuthUser) => {
    setAuthUser(user);
    setScreen("dashboard");
  };

  const handleLogout = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    setAuthUser(null);
    setBoard(null);
    setScreen("login");
  };

  const handleSelectBoard = (boardId: number) => {
    setActiveBoardId(boardId);
    setBoard(null);
    setLoading(true);
    setScreen("board");
  };

  const handleBackToDashboard = () => {
    setScreen("dashboard");
    setBoard(null);
    setShowCriticalPath(false);
    setCriticalPathIds([]);
    setSuggestions([]);
    setDownstreamChanges([]);
    setErrorMessage(null);
  };

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const loadBoard = useCallback(async () => {
    try {
      const data = await api.getBoard(activeBoardId);
      setBoard(data);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load board");
    } finally {
      setLoading(false);
    }
  }, [activeBoardId]);

  const loadSuggestions = useCallback(async () => {
    try {
      const data = await api.getPendingSuggestions(activeBoardId);
      setSuggestions(data);
    } catch {
      // Ignored if API is loading or empty
    }
  }, [activeBoardId]);

  useEffect(() => {
    if (screen === "board") {
      loadBoard();
      loadSuggestions();
    }
  }, [screen, loadBoard, loadSuggestions]);

  const toggleCriticalPath = async () => {
    if (!showCriticalPath) {
      try {
        const cp = await api.getCriticalPath(activeBoardId);
        setCriticalPathIds(cp.task_ids);
        setShowCriticalPath(true);
      } catch (err) {
        console.error(err);
      }
    } else {
      setShowCriticalPath(false);
      setCriticalPathIds([]);
    }
  };

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    const task = board?.tasks.find((t) => `task-${t.id}` === active.id);
    if (task) setActiveTask(task);
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveTask(null);

    if (!over || !board) return;

    const activeIdStr = String(active.id).replace("task-", "");
    const taskId = Number(activeIdStr);
    const task = board.tasks.find((t) => t.id === taskId);
    if (!task) return;

    let targetColumn: ColumnType = task.column;

    if (["backlog", "in_progress", "review", "done"].includes(String(over.id))) {
      targetColumn = over.id as ColumnType;
    } else {
      const overIdStr = String(over.id).replace("task-", "");
      const overTask = board.tasks.find((t) => t.id === Number(overIdStr));
      if (overTask) targetColumn = overTask.column;
    }

    if (targetColumn === task.column) return;

    const previousBoard = { ...board, tasks: [...board.tasks] };
    const optimisticTasks = board.tasks.map((t) =>
      t.id === taskId ? { ...t, column: targetColumn } : t
    );
    setBoard({ ...board, tasks: optimisticTasks });
    setErrorMessage(null);

    try {
      const res = await api.moveTask(task.id, { column: targetColumn, version: task.version });
      await loadBoard();
      if (res.downstream_changes && res.downstream_changes.length > 0) {
        setDownstreamChanges(res.downstream_changes);
      }
    } catch (err: any) {
      setBoard(previousBoard);
      if (err?.code === "INVARIANT_VIOLATION") {
        setInvariantTaskIds((prev) => [...prev.filter((id) => id !== taskId), taskId]);
        setTimeout(() => {
          setInvariantTaskIds((prev) => prev.filter((id) => id !== taskId));
        }, 4000);
      } else {
        setErrorMessage(err.message || "Failed to move task");
      }
    }
  };

  // ── Screens ─────────────────────────────────────────────────────────────────

  if (screen === "login") {
    return <LoginScreen onAuth={handleAuth} />;
  }

  if (screen === "dashboard") {
    return (
      <BoardDashboard
        user={authUser!}
        onSelectBoard={handleSelectBoard}
        onLogout={handleLogout}
      />
    );
  }

  // Board screen
  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
        <p style={{ fontFamily: "var(--font-serif)", fontSize: "20px", color: "var(--color-muted)" }}>
          Loading board…
        </p>
      </div>
    );
  }

  const columns: { id: ColumnType; title: string }[] = [
    { id: "backlog", title: "Backlog" },
    { id: "in_progress", title: "In Progress" },
    { id: "review", title: "Review" },
    { id: "done", title: "Done" },
  ];

  const pendingSuggestionsCount = suggestions.filter((s) => s.status === "pending").length;

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Top Navigation Bar */}
      <header
        style={{
          background: "var(--color-surface-soft)",
          borderBottom: "1px solid var(--color-hairline)",
          padding: "12px 24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          {/* Back to boards */}
          <button
            id="back-to-boards"
            onClick={handleBackToDashboard}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "7px 12px",
              borderRadius: "8px",
              border: "1px solid var(--color-hairline)",
              background: "var(--color-surface-card)",
              color: "var(--color-muted)",
              fontSize: "13px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            <ChevronLeft size={15} />
            Boards
          </button>

          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <LayoutGrid size={18} color="var(--color-primary)" />
              <h1
                style={{
                  fontFamily: "var(--font-serif)",
                  fontSize: "22px",
                  fontWeight: 600,
                  color: "var(--color-ink)",
                  letterSpacing: "-0.4px",
                }}
              >
                {board?.name || "TaskFlow Pro"}
              </h1>
              <span
                style={{
                  fontSize: "11px",
                  color: "var(--color-primary)",
                  background: "var(--color-primary-light)",
                  padding: "2px 8px",
                  borderRadius: "var(--radius-pill)",
                  fontWeight: 600,
                }}
              >
                DAG Engine
              </span>
            </div>
            <div style={{ fontSize: "12px", color: "var(--color-muted)", marginTop: "1px" }}>
              Anchor Date: {board?.start_date}
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {/* Critical Path Toggle */}
          <button
            onClick={toggleCriticalPath}
            style={{
              padding: "8px 14px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-hairline)",
              background: showCriticalPath ? "var(--color-primary-light)" : "var(--color-surface-card)",
              color: showCriticalPath ? "var(--color-primary)" : "var(--color-body)",
              fontWeight: 600,
              fontSize: "13px",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              cursor: "pointer",
            }}
          >
            <GitBranch size={16} />
            <span>Critical Path {showCriticalPath ? "Active" : ""}</span>
          </button>

          {/* AI Copilot Drawer Button */}
          <button
            onClick={() => setIsAiDrawerOpen(true)}
            style={{
              padding: "8px 14px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-hairline)",
              background: "var(--color-surface-card)",
              color: "var(--color-body)",
              fontWeight: 600,
              fontSize: "13px",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              position: "relative",
              cursor: "pointer",
            }}
          >
            <Sparkles size={16} color="var(--color-primary)" />
            <span>AI Copilot</span>
            {pendingSuggestionsCount > 0 && (
              <span
                style={{
                  background: "var(--color-primary)",
                  color: "white",
                  fontSize: "10px",
                  fontWeight: 700,
                  padding: "1px 6px",
                  borderRadius: "var(--radius-pill)",
                }}
              >
                {pendingSuggestionsCount}
              </span>
            )}
          </button>

          {/* Add Task Button */}
          <button
            onClick={() => setIsNewTaskOpen(true)}
            style={{
              background: "var(--color-primary)",
              color: "var(--color-on-primary)",
              padding: "8px 16px",
              borderRadius: "var(--radius-sm)",
              fontWeight: 600,
              fontSize: "13px",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              border: "none",
              cursor: "pointer",
            }}
          >
            <Plus size={16} />
            <span>New Task</span>
          </button>
        </div>
      </header>

      {/* Error Banner */}
      {errorMessage && (
        <div
          style={{
            background: "var(--color-error-bg)",
            borderBottom: "1px solid var(--color-error-border)",
            color: "var(--color-error)",
            padding: "12px 32px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            fontSize: "14px",
            fontWeight: 500,
            animation: "slideDown 0.15s ease",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <AlertCircle size={18} />
            <span>{errorMessage}</span>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            style={{ color: "var(--color-error)", fontWeight: 600, fontSize: "13px", padding: "4px 8px", background: "none", border: "none", cursor: "pointer" }}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Kanban Board Canvas */}
      <main style={{ flex: 1, padding: "24px 32px", overflowX: "auto" }}>
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div style={{ display: "flex", gap: "20px", alignItems: "flex-start" }}>
            {columns.map((col) => {
              const colTasks = (board?.tasks || []).filter((t) => t.column === col.id);
              return (
                <KanbanColumn
                  key={col.id}
                  id={col.id}
                  title={col.title}
                  tasks={colTasks}
                  allTasks={board?.tasks || []}
                  criticalPathIds={criticalPathIds}
                  invariantTaskIds={invariantTaskIds}
                  onCardClick={(task) => setSelectedTask(task)}
                />
              );
            })}
          </div>

          <DragOverlay>
            {activeTask ? (
              <TaskCard
                task={activeTask}
                allTasks={board?.tasks || []}
                isCriticalPath={criticalPathIds.includes(activeTask.id)}
                onClick={() => {}}
              />
            ) : null}
          </DragOverlay>
        </DndContext>
      </main>

      {/* Task Detail Modal + Ripple Effect */}
      {(selectedTask || downstreamChanges.length > 0) && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: selectedTask ? "rgba(20, 20, 19, 0.4)" : "transparent",
            backdropFilter: selectedTask ? "blur(4px)" : "none",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
            pointerEvents: selectedTask ? "auto" : "none",
          }}
          onClick={selectedTask ? () => setSelectedTask(null) : undefined}
        >
          <div style={{ display: "flex", gap: "16px", alignItems: "stretch", maxHeight: "90vh", pointerEvents: "auto" }}>
            {selectedTask && (
              <TaskDetailModal
                task={selectedTask}
                allTasks={board?.tasks || []}
                dependencies={board?.dependencies || []}
                onClose={() => setSelectedTask(null)}
                onTaskUpdated={(updatedTask, changes) => {
                  setSelectedTask(updatedTask);
                  loadBoard();
                  if (changes && changes.length > 0) setDownstreamChanges(changes);
                }}
                onTaskDeleted={() => {
                  setSelectedTask(null);
                  loadBoard();
                }}
                onDependencyChanged={() => loadBoard()}
              />
            )}
            {downstreamChanges.length > 0 && (
              <RippleToast
                changes={downstreamChanges}
                allTasks={board?.tasks || []}
                onDismiss={() => setDownstreamChanges([])}
              />
            )}
          </div>
        </div>
      )}

      {/* New Task Modal */}
      <NewTaskModal
        boardId={board?.id || activeBoardId}
        isOpen={isNewTaskOpen}
        onClose={() => setIsNewTaskOpen(false)}
        onTaskCreated={() => loadBoard()}
      />

      {/* AI Suggestions Drawer */}
      <AISuggestionsDrawer
        isOpen={isAiDrawerOpen}
        suggestions={suggestions}
        allTasks={board?.tasks || []}
        onClose={() => setIsAiDrawerOpen(false)}
        onRefreshSuggestions={loadSuggestions}
        onSuggestionsLoaded={(list) => setSuggestions(list)}
        onSuggestionApplied={(changes) => {
          loadBoard();
          if (changes && changes.length > 0) setDownstreamChanges(changes);
        }}
      />
    </div>
  );
};

export default App;
