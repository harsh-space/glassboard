import React from "react";
import type { DownstreamChange, Task } from "../types";
import { ArrowRight, Activity, X } from "lucide-react";

interface RippleToastProps {
  changes: DownstreamChange[];
  allTasks: Task[];
  onDismiss: () => void;
}

export const RippleToast: React.FC<RippleToastProps> = ({
  changes,
  allTasks,
  onDismiss,
}) => {
  if (changes.length === 0) return null;

  return (
    <div
      onClick={(e) => e.stopPropagation()}
      style={{
        background: "var(--color-surface-soft)",
        color: "var(--color-ink)",
        borderRadius: "var(--radius-lg)",
        border: "1px solid var(--color-hairline)",
        boxShadow: "var(--shadow-lg)",
        animation: "slideDown 0.2s ease-out",
        width: "300px",
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        alignSelf: "stretch",
        maxHeight: "90vh",
        boxSizing: "border-box",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "18px 20px 14px",
          borderBottom: "1px solid var(--color-hairline)",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Activity size={16} color="var(--color-primary)" />
          <span style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: "16px", color: "var(--color-ink)" }}>
            Ripple Effect
          </span>
          <span
            style={{
              fontSize: "11px",
              fontWeight: 600,
              background: "var(--color-primary-light)",
              color: "var(--color-primary)",
              padding: "2px 8px",
              borderRadius: "var(--radius-pill)",
            }}
          >
            {changes.length} shifted
          </span>
        </div>
        <button
          onClick={onDismiss}
          style={{
            color: "var(--color-muted)",
            padding: "4px",
            borderRadius: "var(--radius-sm)",
            lineHeight: 1,
          }}
        >
          <X size={16} />
        </button>
      </div>

      {/* Scrollable list */}
      <div
        className="ripple-scroll"
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "12px 16px",
          display: "flex",
          flexDirection: "column",
          gap: "8px",
        }}
      >
        {changes.map((c) => {
          const t = allTasks.find((task) => task.id === c.task_id);
          const drivingPrereq = t?.driving_prerequisite_id
            ? allTasks.find((item) => item.id === t.driving_prerequisite_id)
            : null;

          return (
            <div
              key={c.task_id}
              style={{
                background: "var(--color-canvas)",
                border: "1px solid var(--color-hairline-soft)",
                borderRadius: "var(--radius-md)",
                padding: "10px 12px",
              }}
            >
              <div
                style={{
                  fontWeight: 600,
                  fontSize: "13px",
                  color: "var(--color-ink)",
                  marginBottom: "5px",
                }}
              >
                T{c.task_id}: {t?.title || "Task"}
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  fontSize: "12px",
                  color: "var(--color-muted)",
                }}
              >
                <span>{c.old_start}</span>
                <ArrowRight size={11} color="var(--color-muted)" />
                <span
                  style={{
                    color: "var(--color-primary)",
                    fontWeight: 700,
                    fontFamily: "var(--font-mono)",
                    fontSize: "11px",
                  }}
                >
                  {c.new_start}
                </span>
              </div>
              {drivingPrereq && (
                <div
                  style={{
                    fontSize: "11px",
                    color: "var(--color-muted-soft)",
                    marginTop: "5px",
                    paddingTop: "5px",
                    borderTop: "1px solid var(--color-hairline-soft)",
                  }}
                >
                  Caused by: T{drivingPrereq.id} ({drivingPrereq.title})
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
