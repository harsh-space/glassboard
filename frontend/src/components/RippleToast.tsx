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
      style={{
        position: "fixed",
        bottom: "24px",
        right: "24px",
        background: "var(--color-surface-dark)",
        color: "var(--color-on-dark)",
        borderRadius: "var(--radius-md)",
        padding: "16px 20px",
        boxShadow: "var(--shadow-lg)",
        zIndex: 1100,
        maxWidth: "420px",
        animation: "slideDown 0.2s ease-out",
        border: "1px solid var(--color-hairline)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 600, fontSize: "14px" }}>
          <Activity size={16} color="var(--color-accent-amber)" />
          <span>Ripple Effect ({changes.length} tasks shifted)</span>
        </div>
        <button
          onClick={onDismiss}
          style={{ color: "var(--color-muted-soft)", padding: "2px" }}
        >
          <X size={16} />
        </button>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxHeight: "200px", overflowY: "auto" }}>
        {changes.map((c) => {
          const t = allTasks.find((task) => task.id === c.task_id);
          const drivingPrereq = t?.driving_prerequisite_id
            ? allTasks.find((item) => item.id === t.driving_prerequisite_id)
            : null;

          return (
            <div
              key={c.task_id}
              style={{
                fontSize: "12px",
                background: "rgba(255,255,255,0.06)",
                padding: "8px 10px",
                borderRadius: "4px",
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: "2px" }}>
                T{c.task_id}: {t?.title || "Task"}
              </div>
              <div style={{ color: "var(--color-on-dark-soft)", display: "flex", alignItems: "center", gap: "6px" }}>
                <span>{c.old_start}</span>
                <ArrowRight size={11} />
                <span style={{ color: "var(--color-accent-amber)", fontWeight: 600 }}>{c.new_start}</span>
              </div>
              {drivingPrereq && (
                <div style={{ fontSize: "11px", color: "var(--color-muted-soft)", marginTop: "2px" }}>
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
