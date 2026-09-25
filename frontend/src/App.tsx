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
import { api, ApiRequestError } from "./api";
import { KanbanColumn } from "./components/KanbanColumn";
import { TaskCard } from "./components/TaskCard";
import { TaskDetailModal } from "./components/TaskDetailModal";
import { NewTaskModal } from "./components/NewTaskModal";
import { AISuggestionsDrawer } from "./components/AISuggestionsDrawer";
import { RippleToast } from "./components/RippleToast";
import { Sparkles, Plus, AlertCircle, GitBranch } from "lucide-react";


export const App: React.FC = () => {
  const [board, setBoard] = useState<Board | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  const [isNewTaskOpen, setIsNewTaskOpen] = useState(false);
  const [isAiDrawerOpen, setIsAiDrawerOpen] = useState(false);
  const [suggestions, setSuggestions] = useState<AISuggestion[]>([]);

  const [criticalPathIds, setCriticalPathIds] = useState<number[]>([]);
  const [showCriticalPath, setShowCriticalPath] = useState(false);

  const [downstreamChanges, setDownstreamChanges] = useState<DownstreamChange[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Setup dnd-kit sensors with activation constraint
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const loadBoard = useCallback(async () => {
    try {
      const data = await api.getBoard(1);
      setBoard(data);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load board");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSuggestions = useCallback(async () => {
    try {
      const data = await api.getPendingSuggestions(1);
      setSuggestions(data);
    } catch {
      // Ignored if API is loading or empty
    }
  }, []);

  useEffect(() => {
    loadBoard();
    loadSuggestions();
  }, [loadBoard, loadSuggestions]);

  // Toggle Critical Path
  const toggleCriticalPath = async () => {
    if (!showCriticalPath) {
      try {
        const cp = await api.getCriticalPath(1);
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
    if (task) {
      setActiveTask(task);
    }
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

    // Check if dropped directly onto a column container
    if (["backlog", "in_progress", "review", "done"].includes(String(over.id))) {
      targetColumn = over.id as ColumnType;
    } else {
      // Dropped onto another task card
      const overIdStr = String(over.id).replace("task-", "");
      const overTask = board.tasks.find((t) => t.id === Number(overIdStr));
      if (overTask) {
        targetColumn = overTask.column;
      }
    }

    if (targetColumn === task.column) return;

    // Snapshot previous board state for rollback on error (optimistic update)
    const previousBoard = { ...board, tasks: [...board.tasks] };

    // Apply optimistic update
    const optimisticTasks = board.tasks.map((t) =>
      t.id === taskId ? { ...t, column: targetColumn } : t
    );
    setBoard({ ...board, tasks: optimisticTasks });
    setErrorMessage(null);

    try {
      const res = await api.moveTask(task.id, {
        column: targetColumn,
        version: task.version,
      });

      // Reconcile with server response
      await loadBoard();

      if (res.downstream_changes && res.downstream_changes.length > 0) {
        setDownstreamChanges(res.downstream_changes);
      }
    } catch (err: any) {
      // Rollback optimistic state immediately
      setBoard(previousBoard);

      if (err instanceof ApiRequestError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage(err.message || "Failed to move task");
      }
    }
  };

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
        <p style={{ fontFamily: "var(--font-serif)", fontSize: "20px", color: "var(--color-muted)" }}>
          Loading TaskFlow Pro...
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
          padding: "16px 32px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h1
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: "26px",
                fontWeight: 600,
                color: "var(--color-ink)",
                letterSpacing: "-0.5px",
              }}
            >
              TaskFlow Pro
            </h1>
            <span
              style={{
                fontSize: "12px",
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
          <div style={{ fontSize: "13px", color: "var(--color-muted)", marginTop: "2px" }}>
            {board?.name} • Anchor Date: {board?.start_date}
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
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
            }}
          >
            <Plus size={16} />
            <span>New Task</span>
          </button>
        </div>
      </header>

      {/* Visible Error Banner for Invalid Drags (BUILD_SPEC.md §6 / §7) */}
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
            style={{ color: "var(--color-error)", fontWeight: 600, fontSize: "13px", padding: "4px 8px" }}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Kanban Board Canvas */}
      <main
        style={{
          flex: 1,
          padding: "24px 32px",
          overflowX: "auto",
        }}
      >
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
      </main>

      {/* Task Detail Modal */}
      <TaskDetailModal
        task={selectedTask}
        allTasks={board?.tasks || []}
        dependencies={board?.dependencies || []}
        onClose={() => setSelectedTask(null)}
        onTaskUpdated={(updatedTask, changes) => {
          setSelectedTask(updatedTask);
          loadBoard();
          if (changes && changes.length > 0) {
            setDownstreamChanges(changes);
          }
        }}
        onTaskDeleted={() => {
          loadBoard();
        }}
        onDependencyChanged={() => {
          loadBoard();
        }}
      />

      {/* New Task Modal */}
      <NewTaskModal
        boardId={board?.id || 1}
        isOpen={isNewTaskOpen}
        onClose={() => setIsNewTaskOpen(false)}
        onTaskCreated={() => {
          loadBoard();
        }}
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
          if (changes && changes.length > 0) {
            setDownstreamChanges(changes);
          }
        }}
      />

      {/* Ripple Effect Toast */}
      <RippleToast
        changes={downstreamChanges}
        allTasks={board?.tasks || []}
        onDismiss={() => setDownstreamChanges([])}
      />
    </div>
  );
};

export default App;
