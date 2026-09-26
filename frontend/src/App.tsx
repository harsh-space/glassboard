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
import { SetUsernameModal } from "./components/SetUsernameModal";
import { Sparkles, Plus, GitBranch, ChevronLeft, Lock, X } from "lucide-react";

type AppScreen = "login" | "dashboard" | "board";

interface MovementBannerData {
  taskId?: number;
  taskTitle?: string;
  sourceColumn?: string;
  targetColumn?: string;
  type: "TASK_BLOCKED" | "INVARIANT_VIOLATION" | "GENERAL_ERROR";
  title: string;
  reason: string;
  blockingTasks?: Array<{ id: number; title: string }>;
  affectedTasks?: Array<{ id: number; title: string }>;
}

function formatColumnName(col?: string): string {
  if (!col) return "";
  switch (col) {
    case "backlog": return "Backlog";
    case "in_progress": return "In Progress";
    case "review": return "Review";
    case "done": return "Done";
    default: return col.charAt(0).toUpperCase() + col.slice(1).replace("_", " ");
  }
}

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
  const [movementBanner, setMovementBanner] = useState<MovementBannerData | null>(null);

  // Auto-dismiss movement banner after 8 seconds
  useEffect(() => {
    if (!movementBanner) return;
    const timer = setTimeout(() => {
      setMovementBanner(null);
    }, 8000);
    return () => clearTimeout(timer);
  }, [movementBanner]);

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
    setMovementBanner(null);
  };

  const isTempUsername = authUser?.username ? authUser.username.startsWith("temp_") : false;

  const handleUsernameUpdated = (newUsername: string) => {
    if (authUser) {
      const updated: AuthUser = { ...authUser, username: newUsername };
      setAuthUser(updated);
      localStorage.setItem(
        "auth_user",
        JSON.stringify({
          user_id: updated.user_id,
          username: updated.username,
          email: updated.email,
        })
      );
    }
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
      setMovementBanner({
        type: "GENERAL_ERROR",
        title: "Board Error",
        reason: err.message || "Failed to load board",
      });
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
    setMovementBanner(null);
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveTask(null);

    if (!over || !board) return;

    const activeIdStr = String(active.id).replace("task-", "");
    const taskId = Number(activeIdStr);
    const task = board.tasks.find((t) => t.id === taskId);
    if (!task) return;

    const COLUMNS: ColumnType[] = ["backlog", "in_progress", "review", "done"];
    let targetColumn: ColumnType = task.column;

    // Priority 1: over is a column droppable (id is column name)
    if (COLUMNS.includes(String(over.id) as ColumnType)) {
      targetColumn = over.id as ColumnType;
    // Priority 2: over.data.current carries a column identifier (set by useDroppable)
    } else if (over.data.current?.column && COLUMNS.includes(over.data.current.column)) {
      targetColumn = over.data.current.column as ColumnType;
    // Priority 3: over is a task — use that task's column
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
    setMovementBanner(null);

    const targetColumnTitle = formatColumnName(targetColumn);

    try {
      const res = await api.moveTask(task.id, { column: targetColumn, version: task.version });
      await loadBoard();
      if (res.downstream_changes && res.downstream_changes.length > 0) {
        setDownstreamChanges(res.downstream_changes);
      }
    } catch (err: any) {
      setBoard(previousBoard);
      if (err?.code === "TASK_BLOCKED") {
        let blocking: Array<{ id: number; title: string }> = err.details?.blocking_prerequisites || [];
        if (!blocking.length && task.blocking_prerequisite_ids?.length) {
          blocking = board.tasks
            .filter((t) => task.blocking_prerequisite_ids.includes(t.id))
            .map((t) => ({ id: t.id, title: t.title }));
        }
        setMovementBanner({
          taskId: task.id,
          taskTitle: task.title,
          sourceColumn: task.column,
          targetColumn: targetColumnTitle,
          type: "TASK_BLOCKED",
          title: "Movement Blocked",
          reason: `Cannot advance to ${targetColumnTitle}: prerequisite tasks must be completed first.`,
          blockingTasks: blocking,
        });
      } else if (err?.code === "INVARIANT_VIOLATION") {
        const violations: string[] = err.details?.violations || [];
        const reason = parseInvariantReason(violations, taskId);
        const affectedIds = violations
          .filter((v) => v.startsWith("BLOCKED_TASK_ADVANCED:"))
          .map((v) => parseInt(v.split(":")[1], 10))
          .filter((id) => !isNaN(id));
        const affected = board.tasks
          .filter((t) => affectedIds.includes(t.id))
          .map((t) => ({ id: t.id, title: t.title }));

        setMovementBanner({
          taskId: task.id,
          taskTitle: task.title,
          sourceColumn: task.column,
          targetColumn: targetColumnTitle,
          type: "INVARIANT_VIOLATION",
          title: "Dependency Invariant",
          reason,
          affectedTasks: affected,
        });
      } else {
        setMovementBanner({
          taskId: task.id,
          taskTitle: task.title,
          sourceColumn: task.column,
          targetColumn: targetColumnTitle,
          type: "GENERAL_ERROR",
          title: "Action Failed",
          reason: err?.message || "Failed to move task. Please try again.",
        });
      }
    }
  };

  function parseInvariantReason(violations: string[], taskId: number): string {
    for (const v of violations) {
      if (v === "GRAPH_HAS_CYCLE") return "Cannot move task: would create a circular dependency cycle in the project graph.";
      if (v === `SCHEDULE_VIOLATION:${taskId}`) return "Cannot move task: planned start occurs before prerequisite finish dates.";
      if (v === `BLOCKED_TASK_ADVANCED:${taskId}`) return "Cannot move task: prerequisite tasks are not finished yet.";
      if (v.startsWith("SCHEDULE_VIOLATION:")) return "Cannot move task: causes a schedule conflict with connected tasks.";
      if (v.startsWith("BLOCKED_TASK_ADVANCED:")) return "Cannot move backwards: downstream active tasks depend on this task.";
    }
    return "Cannot move task: violates project dependency graph constraints.";
  }

  // ── Screens ─────────────────────────────────────────────────────────────────

  if (screen === "login") {
    return <LoginScreen onAuth={handleAuth} />;
  }

  if (screen === "dashboard") {
    return (
      <>
        <BoardDashboard
          user={authUser!}
          onSelectBoard={handleSelectBoard}
          onLogout={handleLogout}
        />
        <SetUsernameModal
          isOpen={isTempUsername}
          onUsernameUpdated={handleUsernameUpdated}
        />
      </>
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

      {/* Kanban Board Canvas */}
      <main style={{ flex: 1, padding: "20px 32px 24px", overflowX: "auto", display: "flex", flexDirection: "column" }}>
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

        {/* Space below the columns: Dedicated Movement / Invariant Violation Banner */}
        {movementBanner && (
          <div
            style={{
              marginTop: "20px",
              background: "#fffbfb",
              border: "1.5px solid #fca5a5",
              borderRadius: "var(--radius-md)",
              padding: "14px 20px",
              boxShadow: "0 4px 16px rgba(220, 38, 38, 0.08)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "16px",
              animation: "slideUp 0.2s ease",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "14px", flex: 1, minWidth: 0, flexWrap: "wrap" }}>
              <div
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "8px",
                  background: "rgba(220, 38, 38, 0.1)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                <Lock size={18} color="#b91c1c" />
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                  <span
                    style={{
                      fontSize: "11px",
                      fontFamily: "var(--font-mono)",
                      fontWeight: 700,
                      textTransform: "uppercase",
                      letterSpacing: "0.5px",
                      color: "#991b1b",
                      background: "rgba(220, 38, 38, 0.1)",
                      padding: "2px 7px",
                      borderRadius: "4px",
                    }}
                  >
                    {movementBanner.title}
                  </span>

                  {movementBanner.taskId && (
                    <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-ink)" }}>
                      T{movementBanner.taskId} {movementBanner.taskTitle}
                      {movementBanner.targetColumn && (
                        <span style={{ color: "var(--color-muted)", fontWeight: 400 }}>
                          {" "}→{" "}
                          <strong style={{ color: "var(--color-ink)", fontWeight: 600 }}>
                            {movementBanner.targetColumn}
                          </strong>
                        </span>
                      )}
                    </span>
                  )}
                </div>

                <div style={{ fontSize: "13px", color: "var(--color-body)", display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                  <span>{movementBanner.reason}</span>

                  {movementBanner.blockingTasks && movementBanner.blockingTasks.length > 0 && (
                    <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                      <span style={{ fontSize: "12px", color: "var(--color-muted)", fontWeight: 500 }}>Unfinished prerequisites:</span>
                      {movementBanner.blockingTasks.map((pt) => (
                        <button
                          key={pt.id}
                          onClick={() => {
                            const found = board?.tasks.find((t) => t.id === pt.id);
                            if (found) setSelectedTask(found);
                          }}
                          title="Click to view task details"
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "4px",
                            background: "rgba(220, 38, 38, 0.08)",
                            border: "1px solid rgba(220, 38, 38, 0.2)",
                            borderRadius: "4px",
                            padding: "2px 7px",
                            fontSize: "12px",
                            fontWeight: 600,
                            color: "#991b1b",
                            cursor: "pointer",
                            transition: "all 0.1s ease",
                          }}
                          onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(220, 38, 38, 0.16)")}
                          onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(220, 38, 38, 0.08)")}
                        >
                          <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", opacity: 0.8 }}>T{pt.id}</span>
                          <span>{pt.title}</span>
                        </button>
                      ))}
                    </div>
                  )}

                  {movementBanner.affectedTasks && movementBanner.affectedTasks.length > 0 && (
                    <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                      <span style={{ fontSize: "12px", color: "var(--color-muted)", fontWeight: 500 }}>Affects:</span>
                      {movementBanner.affectedTasks.map((at) => (
                        <button
                          key={at.id}
                          onClick={() => {
                            const found = board?.tasks.find((t) => t.id === at.id);
                            if (found) setSelectedTask(found);
                          }}
                          title="Click to view task details"
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "4px",
                            background: "rgba(220, 38, 38, 0.08)",
                            border: "1px solid rgba(220, 38, 38, 0.2)",
                            borderRadius: "4px",
                            padding: "2px 7px",
                            fontSize: "12px",
                            fontWeight: 600,
                            color: "#991b1b",
                            cursor: "pointer",
                            transition: "all 0.1s ease",
                          }}
                          onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(220, 38, 38, 0.16)")}
                          onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(220, 38, 38, 0.08)")}
                        >
                          <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", opacity: 0.8 }}>T{at.id}</span>
                          <span>{at.title}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            <button
              onClick={() => setMovementBanner(null)}
              title="Dismiss"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "4px",
                padding: "6px 12px",
                borderRadius: "6px",
                border: "1px solid rgba(0,0,0,0.08)",
                background: "white",
                color: "var(--color-muted)",
                fontSize: "12px",
                fontWeight: 600,
                cursor: "pointer",
                flexShrink: 0,
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = "var(--color-ink)";
                e.currentTarget.style.borderColor = "rgba(0,0,0,0.18)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = "var(--color-muted)";
                e.currentTarget.style.borderColor = "rgba(0,0,0,0.08)";
              }}
            >
              <X size={14} />
              <span>Dismiss</span>
            </button>
          </div>
        )}
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

      {/* Choose Username Modal (if user still has temporary handle) */}
      <SetUsernameModal
        isOpen={isTempUsername}
        onUsernameUpdated={handleUsernameUpdated}
      />
    </div>
  );
};

export default App;
