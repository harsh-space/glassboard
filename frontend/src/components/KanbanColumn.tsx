import React from "react";
import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import type { Task, ColumnType } from "../types";
import { TaskCard } from "./TaskCard";

interface KanbanColumnProps {
  id: ColumnType;
  title: string;
  tasks: Task[];
  allTasks: Task[];
  criticalPathIds: number[];
  onCardClick: (task: Task) => void;
}

export const KanbanColumn: React.FC<KanbanColumnProps> = ({
  id,
  title,
  tasks,
  allTasks,
  criticalPathIds,
  onCardClick,
}) => {
  const { setNodeRef, isOver } = useDroppable({
    id,
    data: { column: id },
  });

  return (
    <div
      ref={setNodeRef}
      style={{
        flex: 1,
        minWidth: "280px",
        maxWidth: "340px",
        background: isOver ? "var(--color-surface-cream-strong)" : "var(--color-surface-soft)",
        border: isOver ? "1.5px dashed var(--color-primary)" : "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-lg)",
        padding: "16px",
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 170px)",
        transition: "all 0.15s ease",
      }}
    >
      {/* Column Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "14px",
          paddingBottom: "10px",
          borderBottom: "1px solid var(--color-hairline)",
        }}
      >
        <h3
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: "18px",
            fontWeight: 500,
            color: "var(--color-ink)",
          }}
        >
          {title}
        </h3>
        <span
          style={{
            fontSize: "12px",
            fontWeight: 600,
            color: "var(--color-muted)",
            background: "rgba(0,0,0,0.06)",
            padding: "2px 8px",
            borderRadius: "var(--radius-pill)",
          }}
        >
          {tasks.length}
        </span>
      </div>

      {/* Task Cards List */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          paddingRight: "4px",
        }}
      >
        <SortableContext
          items={tasks.map((t) => `task-${t.id}`)}
          strategy={verticalListSortingStrategy}
        >
          {tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              allTasks={allTasks}
              isCriticalPath={criticalPathIds.includes(task.id)}
              onClick={onCardClick}
            />
          ))}
        </SortableContext>

        {tasks.length === 0 && (
          <div
            style={{
              padding: "24px 12px",
              textAlign: "center",
              color: "var(--color-muted)",
              fontSize: "13px",
              fontStyle: "italic",
            }}
          >
            No tasks in {title}
          </div>
        )}
      </div>
    </div>
  );
};
