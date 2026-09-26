import React from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { Task } from "../types";
import { Clock, CheckCircle2, Lock, Sparkles, AlertTriangle } from "lucide-react";

interface TaskCardProps {
  task: Task;
  allTasks: Task[];
  isCriticalPath?: boolean;
  hasInvariantViolation?: boolean;
  invariantReason?: string;
  onClick: (task: Task) => void;
}

export const TaskCard: React.FC<TaskCardProps> = ({
  task,
  allTasks,
  isCriticalPath,
  hasInvariantViolation,
  invariantReason,
  onClick,
}) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: `task-${task.id}`,
    data: { task },
  });

  const cardStyle: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
    zIndex: isDragging ? 999 : 1,
    background: isCriticalPath && !hasInvariantViolation
      ? "#fffdf9"
      : "var(--color-surface-card)",
    border: isCriticalPath && !hasInvariantViolation
      ? "1.5px solid var(--color-primary)"
      : "1px solid var(--color-hairline)",
    borderRadius: "var(--radius-md)",
    padding: "14px 16px",
    marginBottom: "12px",
    cursor: "grab",
    boxShadow: isDragging ? "var(--shadow-drag)" : "var(--shadow-sm)",
    position: "relative",
  };

  // Find titles of blocking prerequisites
  const blockingTitles = task.blocking_prerequisite_ids
    .map((id) => allTasks.find((t) => t.id === id)?.title)
    .filter(Boolean);

  return (
    <div
      ref={setNodeRef}
      style={cardStyle}
      {...attributes}
      {...listeners}
      onClick={() => onClick(task)}
      className="task-card"
    >

      {/* Header: ID, badges, Duration */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
          <span
            style={{
              fontSize: "12px",
              fontFamily: "var(--font-mono)",
              fontWeight: 600,
              color: "var(--color-muted)",
              background: "rgba(0,0,0,0.04)",
              padding: "2px 6px",
              borderRadius: "4px",
            }}
          >
            T{task.id}
          </span>

          {/* Invariant violation chips — Invariant label + reason, styled like T# chip */}
          {hasInvariantViolation && (
            <>
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: 600,
                  color: "#b91c1c",
                  background: "rgba(220,38,38,0.08)",
                  border: "1px solid rgba(220,38,38,0.25)",
                  padding: "2px 6px",
                  borderRadius: "4px",
                  display: "flex",
                  alignItems: "center",
                  gap: "3px",
                  whiteSpace: "nowrap",
                }}
              >
                <AlertTriangle size={11} />
                Invariant
              </span>
              {invariantReason && (
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 500,
                    color: "#b91c1c",
                    background: "rgba(220,38,38,0.06)",
                    border: "1px solid rgba(220,38,38,0.18)",
                    padding: "2px 7px",
                    borderRadius: "4px",
                    whiteSpace: "nowrap",
                    maxWidth: "180px",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {invariantReason}
                </span>
              )}
            </>
          )}

          {isCriticalPath && !hasInvariantViolation && (
            <span
              style={{
                fontSize: "11px",
                fontWeight: 600,
                color: "var(--color-primary)",
                background: "var(--color-primary-light)",
                padding: "2px 6px",
                borderRadius: "var(--radius-pill)",
                display: "flex",
                alignItems: "center",
                gap: "3px",
              }}
            >
              <Sparkles size={11} /> Critical
            </span>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "4px", color: "var(--color-muted)", fontSize: "12px" }}>
          <Clock size={13} />
          <span>{task.duration_days}d</span>
        </div>
      </div>

      {/* Task Title */}
      <div
        style={{
          fontWeight: 600,
          fontSize: "14px",
          color: "var(--color-ink)",
          marginBottom: "10px",
          lineHeight: 1.35,
        }}
      >
        {task.title}
      </div>

      {/* Date Range */}
      <div
        style={{
          fontSize: "12px",
          color: "var(--color-muted)",
          marginBottom: "10px",
          display: "flex",
          alignItems: "center",
          gap: "4px",
        }}
      >
        <span>{task.planned_start}</span>
        <span>→</span>
        <span>{task.planned_end}</span>
      </div>

      {/* Chips: Blocked / Ready Status */}
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        {task.blocked ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "5px",
              background: "var(--color-error-bg)",
              color: "var(--color-error)",
              border: "1px solid var(--color-error-border)",
              borderRadius: "var(--radius-sm)",
              padding: "4px 8px",
              fontSize: "11px",
              fontWeight: 600,
            }}
          >
            <Lock size={12} />
            <span>Blocked</span>
          </div>
        ) : (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "5px",
              background: "var(--color-success-bg)",
              color: "var(--color-success)",
              border: "1px solid var(--color-success-border)",
              borderRadius: "var(--radius-sm)",
              padding: "4px 8px",
              fontSize: "11px",
              fontWeight: 600,
              width: "fit-content",
            }}
          >
            <CheckCircle2 size={12} />
            <span>Ready</span>
          </div>
        )}

        {/* Blocking Prerequisite details on card per BUILD_SPEC.md §6 */}
        {task.blocked && blockingTitles.length > 0 && (
          <div
            style={{
              fontSize: "11px",
              color: "var(--color-muted)",
              background: "rgba(0,0,0,0.03)",
              padding: "4px 8px",
              borderRadius: "4px",
              lineHeight: 1.3,
            }}
          >
            <span style={{ fontWeight: 600 }}>Needs: </span>
            {blockingTitles.join(", ")}
          </div>
        )}
      </div>
    </div>
  );
};
