import React from "react";
import type { DownstreamChange, Task } from "../types";
import { Activity, X, ArrowRight } from "lucide-react";

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
      style={{
        marginTop: 0,
        background: "var(--color-surface-soft)",
        border: "1px solid var(--color-hairline)",
        borderLeft: "4px solid var(--color-primary)",
        borderRadius: "var(--radius-lg)",
        padding: "14px 20px",
        boxShadow: "var(--shadow-sm)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "20px",
        animation: "slideUp 0.2s ease-out",
      }}
    >
      {/* Left content */}
      <div style={{ display: "flex", alignItems: "center", gap: "14px", flex: 1, minWidth: 0, flexWrap: "wrap" }}>
        {/* Icon badge */}
        <div
          style={{
            width: "32px",
            height: "32px",
            borderRadius: "var(--radius-pill)",
            background: "var(--color-primary-light)",
            border: "1px solid var(--color-hairline)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <Activity size={15} color="var(--color-primary)" />
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
          {/* Title row */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
            <span
              style={{
                fontFamily: "var(--font-sans)",
                fontSize: "11px",
                fontWeight: 600,
                color: "var(--color-primary)",
                background: "var(--color-primary-light)",
                border: "1px solid var(--color-hairline)",
                padding: "2px 8px",
                borderRadius: "var(--radius-pill)",
                textTransform: "uppercase",
                letterSpacing: "0.5px",
              }}
            >
              Ripple Effect
            </span>

            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ fontWeight: 600, fontSize: "14px", color: "var(--color-ink)" }}>
                {changes.length} downstream {changes.length === 1 ? "task" : "tasks"} rescheduled
              </span>
            </div>
          </div>

          {/* Shifted tasks row */}
          <div style={{ fontSize: "13px", color: "var(--color-body)", display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
            <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
              <span style={{ fontSize: "12px", color: "var(--color-muted)", fontWeight: 500 }}>
                Shifted:
              </span>
              {changes.map((c) => {
                const t = allTasks.find((task) => task.id === c.task_id);
                return (
                  <div
                    key={c.task_id}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "5px",
                      background: "var(--color-surface-card)",
                      border: "1px solid var(--color-hairline)",
                      borderRadius: "var(--radius-sm)",
                      padding: "3px 8px",
                      fontSize: "12px",
                      fontWeight: 500,
                      color: "var(--color-ink)",
                    }}
                  >
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "10px",
                        fontWeight: 600,
                        color: "var(--color-muted)",
                      }}
                    >
                      T{c.task_id}
                    </span>
                    <span>{t?.title || `Task ${c.task_id}`}</span>
                    <ArrowRight size={10} color="var(--color-muted)" />
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "10px",
                        fontWeight: 700,
                        color: "var(--color-primary)",
                      }}
                    >
                      {c.new_start}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Dismiss button — exact copy from Movement Blocked */}
      <button
        onClick={onDismiss}
        title="Dismiss"
        style={{
          display: "flex",
          alignItems: "center",
          gap: "5px",
          padding: "6px 12px",
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--color-hairline)",
          background: "var(--color-surface-card)",
          color: "var(--color-muted)",
          fontSize: "12px",
          fontWeight: 600,
          cursor: "pointer",
          flexShrink: 0,
          transition: "all 0.15s ease",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.color = "var(--color-ink)";
          e.currentTarget.style.borderColor = "var(--color-body-strong)";
          e.currentTarget.style.background = "var(--color-surface-card-hover)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.color = "var(--color-muted)";
          e.currentTarget.style.borderColor = "var(--color-hairline)";
          e.currentTarget.style.background = "var(--color-surface-card)";
        }}
      >
        <X size={14} />
        <span>Dismiss</span>
      </button>
    </div>
  );
};
