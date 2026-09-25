import React, { useState } from "react";
import { api, ApiRequestError } from "../api";
import type { Task, ColumnType } from "../types";

import { X, Plus, AlertTriangle } from "lucide-react";

interface NewTaskModalProps {
  boardId: number;
  isOpen: boolean;
  onClose: () => void;
  onTaskCreated: (task: Task) => void;
}

export const NewTaskModal: React.FC<NewTaskModalProps> = ({
  boardId,
  isOpen,
  onClose,
  onTaskCreated,
}) => {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [durationDays, setDurationDays] = useState(2);
  const [column, setColumn] = useState<ColumnType>("backlog");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError("Task title is required.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const created = await api.createTask({
        board_id: boardId,
        title: title.trim(),
        description: description.trim(),
        duration_days: durationDays,
        column,
      });
      onTaskCreated(created);
      onClose();
    } catch (err: any) {
      if (err instanceof ApiRequestError) {
        setError(`${err.code}: ${err.message}`);
      } else {
        setError(err.message || "Failed to create task");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(20, 20, 19, 0.4)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: "20px",
      }}
      onClick={onClose}
    >
      <div
        className="modal-scroll"
        style={{
          background: "var(--color-surface-soft)",
          border: "1px solid var(--color-hairline)",
          borderRadius: "var(--radius-lg)",
          width: "100%",
          maxWidth: "520px",
          maxHeight: "90vh",
          overflowY: "auto",
          overflowX: "hidden",
          boxSizing: "border-box",
          padding: "24px",
          boxShadow: "var(--shadow-lg)",
          animation: "slideDown 0.2s ease-out",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <h2 style={{ fontFamily: "var(--font-serif)", fontSize: "22px", fontWeight: 600 }}>Create New Task</h2>
          <button onClick={onClose} style={{ color: "var(--color-muted)", padding: "4px" }}>
            <X size={20} />
          </button>
        </div>

        {error && (
          <div
            style={{
              background: "var(--color-error-bg)",
              color: "var(--color-error)",
              padding: "8px 12px",
              borderRadius: "var(--radius-sm)",
              marginBottom: "14px",
              fontSize: "13px",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <AlertTriangle size={15} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--color-muted)", marginBottom: "4px" }}>
              TITLE *
            </label>
            <input
              type="text"
              required
              placeholder="e.g. End-to-end load testing"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              style={{
                width: "100%",
                padding: "8px 12px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-hairline)",
                background: "var(--color-canvas)",
                color: "var(--color-ink)",
              }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--color-muted)", marginBottom: "4px" }}>
              DESCRIPTION
            </label>
            <textarea
              rows={3}
              placeholder="Provide context or technical details..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              style={{
                width: "100%",
                maxWidth: "100%",
                minHeight: "80px",
                padding: "8px 12px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-hairline)",
                background: "var(--color-canvas)",
                color: "var(--color-ink)",
                resize: "vertical",
              }}
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--color-muted)", marginBottom: "4px" }}>
                DURATION (DAYS)
              </label>
              <input
                type="number"
                min={1}
                value={durationDays}
                onChange={(e) => setDurationDays(Math.max(1, parseInt(e.target.value) || 1))}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-hairline)",
                  background: "var(--color-canvas)",
                  color: "var(--color-ink)",
                }}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--color-muted)", marginBottom: "4px" }}>
                INITIAL COLUMN
              </label>
              <select
                value={column}
                onChange={(e) => setColumn(e.target.value as ColumnType)}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-hairline)",
                  background: "var(--color-canvas)",
                  color: "var(--color-ink)",
                }}
              >
                <option value="backlog">Backlog</option>
                <option value="in_progress">In Progress</option>
                <option value="review">Review</option>
                <option value="done">Done</option>
              </select>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
            <button
              type="button"
              onClick={onClose}
              style={{ padding: "8px 16px", background: "var(--color-hairline)", borderRadius: "var(--radius-sm)", fontSize: "13px" }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
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
                opacity: loading ? 0.6 : 1,
              }}
            >
              <Plus size={16} /> Create Task
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
