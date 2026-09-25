import React, { useState, useEffect } from "react";
import type { Task, Dependency, TaskExplanation } from "../types";
import { api, ApiRequestError } from "../api";
import { X, Save, Trash2, Plus, HelpCircle, AlertTriangle, Link2, Eye, ArrowRight } from "lucide-react";


interface TaskDetailModalProps {
  task: Task | null;
  allTasks: Task[];
  dependencies: Dependency[];
  onClose: () => void;
  onTaskUpdated: (updatedTask: Task, downstreamChanges: any[]) => void;
  onTaskDeleted: (taskId: number) => void;
  onDependencyChanged: () => void;
}

export const TaskDetailModal: React.FC<TaskDetailModalProps> = ({
  task,
  allTasks,
  dependencies,
  onClose,
  onTaskUpdated,
  onTaskDeleted,
  onDependencyChanged,
}) => {
  if (!task) return null;

  const [title, setTitle] = useState(task.title);
  const [description, setDescription] = useState(task.description);
  const [durationDays, setDurationDays] = useState(task.duration_days);
  const [pinnedStart, setPinnedStart] = useState<string>(task.pinned_start || "");

  const [explanation, setExplanation] = useState<TaskExplanation | null>(null);
  const [loadingExplanation, setLoadingExplanation] = useState(false);

  const [saving, setSaving] = useState(false);
  const [selectedPrereqId, setSelectedPrereqId] = useState<number | "">("");
  const [depError, setDepError] = useState<string | null>(null);
  const [cyclePath, setCyclePath] = useState<number[] | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);

  // Impact Preview (Dry-Run What-If Analysis)
  const [impactLoading, setImpactLoading] = useState(false);
  const [impactResults, setImpactResults] = useState<{ task_id: number; old_start: string; new_start: string }[] | null>(null);
  const [impactError, setImpactError] = useState<string | null>(null);

  const handleRunImpactPreview = async () => {
    setImpactLoading(true);
    setImpactError(null);
    try {
      const res = await api.getImpactPreview(task.id, {
        duration_days: durationDays,
        pinned_start: pinnedStart ? pinnedStart : null,
      });
      setImpactResults(res.would_change);
    } catch (err: any) {
      if (err instanceof ApiRequestError) {
        setImpactError(`${err.code}: ${err.message}`);
      } else {
        setImpactError(err.message || "Failed to calculate impact preview");
      }
    } finally {
      setImpactLoading(false);
    }
  };


  // Load explanation (Why Panel)
  useEffect(() => {
    let isMounted = true;
    setLoadingExplanation(true);
    api
      .getTaskExplanation(task.id)
      .then((data) => {
        if (isMounted) setExplanation(data);
      })
      .catch((err) => {
        console.error("Failed to load explanation", err);
      })
      .finally(() => {
        if (isMounted) setLoadingExplanation(false);
      });

    return () => {
      isMounted = false;
    };
  }, [task.id, task.planned_start, task.duration_days]);

  // Current prerequisites for this task
  const currentPrereqs = dependencies
    .filter((d) => d.task_id === task.id)
    .map((d) => ({
      dependencyId: d.id,
      prereqTask: allTasks.find((t) => t.id === d.prerequisite_id),
    }))
    .filter((p) => p.prereqTask !== undefined);

  // Available candidate prerequisites (not self, not already a prereq)
  const existingPrereqIds = new Set(dependencies.filter((d) => d.task_id === task.id).map((d) => d.prerequisite_id));
  const candidatePrereqs = allTasks.filter((t) => t.id !== task.id && !existingPrereqIds.has(t.id));

  const handleSave = async () => {
    setSaving(true);
    setGeneralError(null);
    try {
      const res = await api.updateTask(task.id, {
        title,
        description,
        duration_days: durationDays,
        pinned_start: pinnedStart ? pinnedStart : null,
        version: task.version,
      });
      onTaskUpdated(res.task, res.downstream_changes);
    } catch (err: any) {
      if (err instanceof ApiRequestError) {
        setGeneralError(`${err.code}: ${err.message}`);
      } else {
        setGeneralError(err.message || "Failed to save task");
      }
    } finally {
      setSaving(false);
    }
  };

  const handleAddDependency = async () => {
    if (!selectedPrereqId) return;
    setDepError(null);
    setCyclePath(null);

    try {
      await api.createDependency(task.id, Number(selectedPrereqId));
      setSelectedPrereqId("");
      onDependencyChanged();
    } catch (err: any) {
      if (err instanceof ApiRequestError) {
        if (err.code === "CYCLE_DETECTED" && err.details?.path) {
          setCyclePath(err.details.path);
          setDepError(err.message);
        } else {
          setDepError(`${err.code}: ${err.message}`);
        }
      } else {
        setDepError(err.message || "Failed to add dependency");
      }
    }
  };

  const handleRemoveDependency = async (depId: number) => {
    setDepError(null);
    try {
      await api.deleteDependency(depId);
      onDependencyChanged();
    } catch (err: any) {
      setDepError(err.message || "Failed to remove dependency");
    }
  };

  const handleDeleteTask = async () => {
    if (!window.confirm(`Are you sure you want to delete '${task.title}'?`)) return;
    try {
      await api.deleteTask(task.id);
      onTaskDeleted(task.id);
      onClose();
    } catch (err: any) {
      setGeneralError(err.message || "Failed to delete task");
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
        style={{
          background: "var(--color-surface-soft)",
          border: "1px solid var(--color-hairline)",
          borderRadius: "var(--radius-lg)",
          width: "100%",
          maxWidth: "680px",
          maxHeight: "90vh",
          overflowY: "auto",
          boxShadow: "var(--shadow-lg)",
          padding: "28px",
          position: "relative",
          animation: "slideDown 0.2s ease-out",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "20px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontWeight: 600,
                  fontSize: "13px",
                  color: "var(--color-muted)",
                  background: "var(--color-surface-cream-strong)",
                  padding: "2px 8px",
                  borderRadius: "4px",
                }}
              >
                T{task.id}
              </span>
              <span style={{ fontSize: "13px", color: "var(--color-muted)" }}>Version: {task.version}</span>
            </div>
            <h2
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: "24px",
                fontWeight: 600,
                color: "var(--color-ink)",
              }}
            >
              Task Details
            </h2>
          </div>
          <button
            onClick={onClose}
            style={{
              padding: "6px",
              borderRadius: "var(--radius-sm)",
              color: "var(--color-muted)",
            }}
          >
            <X size={20} />
          </button>
        </div>

        {generalError && (
          <div
            style={{
              padding: "10px 14px",
              background: "var(--color-error-bg)",
              color: "var(--color-error)",
              borderRadius: "var(--radius-sm)",
              marginBottom: "16px",
              fontSize: "13px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <AlertTriangle size={16} />
            <span>{generalError}</span>
          </div>
        )}

        {/* Task Edit Form */}
        <div style={{ display: "flex", flexDirection: "column", gap: "14px", marginBottom: "24px" }}>
          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--color-muted)", marginBottom: "4px" }}>
              TITLE
            </label>
            <input
              type="text"
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
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              style={{
                width: "100%",
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
                PINNED START DATE (OPTIONAL)
              </label>
              <input
                type="date"
                value={pinnedStart}
                onChange={(e) => setPinnedStart(e.target.value)}
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
          </div>

          {/* Current Schedule Summary */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              background: "var(--color-surface-cream-strong)",
              padding: "10px 14px",
              borderRadius: "var(--radius-sm)",
              fontSize: "13px",
            }}
          >
            <div>
              <span style={{ color: "var(--color-muted)" }}>Planned: </span>
              <strong>{task.planned_start}</strong> → <strong>{task.planned_end}</strong>
            </div>
            {task.actual_end && (
              <div>
                <span style={{ color: "var(--color-muted)" }}>Actual End: </span>
                <strong>{task.actual_end}</strong>
              </div>
            )}
          </div>

          <button
            onClick={handleSave}
            disabled={saving}
            style={{
              alignSelf: "flex-end",
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
            <Save size={15} />
            <span>{saving ? "Saving..." : "Save Task"}</span>
          </button>
        </div>

        {/* --- IMPACT PREVIEW / DRY RUN (BUILD_SPEC.md §4 & §7) --- */}
        <div
          style={{
            background: "var(--color-surface-soft)",
            border: "1px solid var(--color-hairline)",
            borderRadius: "var(--radius-md)",
            padding: "16px",
            marginBottom: "20px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <Eye size={17} color="var(--color-primary)" />
              <h3 style={{ fontFamily: "var(--font-serif)", fontSize: "16px", fontWeight: 600 }}>
                Impact Preview (Dry-Run What-If Analysis)
              </h3>
            </div>
            <span
              style={{
                fontSize: "11px",
                fontWeight: 600,
                textTransform: "uppercase",
                background: "var(--color-surface-cream-strong)",
                padding: "2px 8px",
                borderRadius: "var(--radius-sm)",
                color: "var(--color-primary)",
              }}
            >
              Dry Run
            </span>
          </div>

          <p style={{ fontSize: "13px", color: "var(--color-muted)", marginBottom: "12px", lineHeight: 1.4 }}>
            Simulate how modifying this task's duration ({durationDays}d) or pinned start ({pinnedStart || "unpinned"}) will shift downstream tasks across the board <em>without saving</em>.
          </p>

          <button
            type="button"
            onClick={handleRunImpactPreview}
            disabled={impactLoading}
            style={{
              background: "var(--color-surface-cream-strong)",
              color: "var(--color-primary)",
              border: "1px solid var(--color-primary)",
              padding: "7px 14px",
              borderRadius: "var(--radius-sm)",
              fontWeight: 600,
              fontSize: "13px",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              cursor: "pointer",
              marginBottom: "12px",
            }}
          >
            <Eye size={14} />
            <span>{impactLoading ? "Simulating Schedule..." : "Preview Schedule Impact"}</span>
          </button>

          {impactError && (
            <div
              style={{
                background: "var(--color-error-bg)",
                color: "var(--color-error)",
                padding: "8px 12px",
                borderRadius: "var(--radius-sm)",
                fontSize: "12px",
                marginBottom: "10px",
              }}
            >
              {impactError}
            </div>
          )}

          {impactResults !== null && (
            <div
              style={{
                background: "var(--color-canvas)",
                border: "1px solid var(--color-hairline)",
                borderRadius: "var(--radius-sm)",
                padding: "12px",
                fontSize: "13px",
              }}
            >
              {impactResults.length === 0 ? (
                <div style={{ color: "#166534", fontWeight: 500 }}>
                  ✓ No downstream tasks are affected. Existing schedule remains unchanged.
                </div>
              ) : (
                <div>
                  <div style={{ fontWeight: 600, marginBottom: "8px", color: "var(--color-ink)" }}>
                    {impactResults.length} downstream {impactResults.length === 1 ? "task" : "tasks"} will shift:
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    {impactResults.map((item) => {
                      const targetTask = allTasks.find((t) => t.id === item.task_id);
                      return (
                        <div
                          key={item.task_id}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            padding: "6px 10px",
                            background: "var(--color-surface-soft)",
                            borderRadius: "var(--radius-sm)",
                            fontSize: "12px",
                          }}
                        >
                          <span style={{ fontWeight: 600 }}>
                            Task {item.task_id}: {targetTask?.title || "Unknown"}
                          </span>
                          <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--color-primary)", fontWeight: 500 }}>
                            <span>{item.old_start}</span>
                            <ArrowRight size={12} />
                            <span style={{ fontWeight: 700 }}>{item.new_start}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>


        {/* --- WHY PANEL (BUILD_SPEC.md §6) --- */}
        <div
          style={{
            background: "var(--color-canvas)",
            border: "1px solid var(--color-hairline)",
            borderRadius: "var(--radius-md)",
            padding: "16px",
            marginBottom: "20px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
            <HelpCircle size={17} color="var(--color-primary)" />
            <h3 style={{ fontFamily: "var(--font-serif)", fontSize: "16px", fontWeight: 600 }}>Why Panel (Automation Explainer)</h3>
          </div>

          {loadingExplanation ? (
            <div style={{ fontSize: "13px", color: "var(--color-muted)" }}>Calculating explanation...</div>
          ) : explanation ? (
            <div>
              <p style={{ fontSize: "14px", color: "var(--color-ink)", marginBottom: "10px", lineHeight: 1.4 }}>
                {explanation.reason_text}
              </p>

              {explanation.slack.length > 0 && (
                <div style={{ marginTop: "10px" }}>
                  <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--color-muted)", marginBottom: "6px" }}>
                    SLACK ON OTHER PREREQUISITES:
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                    {explanation.slack.map((s) => {
                      const pTask = allTasks.find((t) => t.id === s.prerequisite_id);
                      return (
                        <div
                          key={s.prerequisite_id}
                          style={{
                            fontSize: "12px",
                            display: "flex",
                            justifyContent: "space-between",
                            background: "var(--color-surface-soft)",
                            padding: "4px 8px",
                            borderRadius: "4px",
                          }}
                        >
                          <span>{pTask ? `T${pTask.id} (${pTask.title})` : `Prerequisite #${s.prerequisite_id}`}</span>
                          <strong style={{ color: "var(--color-accent-teal)" }}>{s.days} days slack</strong>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* --- DEPENDENCY EDITOR --- */}
        <div
          style={{
            background: "var(--color-canvas)",
            border: "1px solid var(--color-hairline)",
            borderRadius: "var(--radius-md)",
            padding: "16px",
            marginBottom: "20px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "12px" }}>
            <Link2 size={17} color="var(--color-primary)" />
            <h3 style={{ fontFamily: "var(--font-serif)", fontSize: "16px", fontWeight: 600 }}>Prerequisites & Dependencies</h3>
          </div>

          {/* Cycle Rejection Path Display per BUILD_SPEC.md §6 */}
          {cyclePath && (
            <div
              style={{
                background: "var(--color-error-bg)",
                border: "1px solid var(--color-error-border)",
                borderRadius: "var(--radius-sm)",
                padding: "10px 14px",
                marginBottom: "12px",
                color: "var(--color-error)",
                fontSize: "13px",
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: "4px", display: "flex", alignItems: "center", gap: "6px" }}>
                <AlertTriangle size={15} /> Cycle Detected (409 CYCLE_DETECTED)
              </div>
              <div style={{ marginBottom: "6px" }}>
                Adding this dependency would create a cycle. The graph remains unchanged.
              </div>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontWeight: 600,
                  fontSize: "12px",
                  background: "rgba(0,0,0,0.05)",
                  padding: "4px 8px",
                  borderRadius: "4px",
                  wordBreak: "break-all",
                }}
              >
                {cyclePath.map((id) => `T${id}`).join(" → ")}
              </div>
            </div>
          )}

          {depError && !cyclePath && (
            <div
              style={{
                background: "var(--color-error-bg)",
                color: "var(--color-error)",
                padding: "8px 12px",
                borderRadius: "var(--radius-sm)",
                marginBottom: "12px",
                fontSize: "13px",
              }}
            >
              {depError}
            </div>
          )}

          {/* Current prerequisites list */}
          <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginBottom: "12px" }}>
            {currentPrereqs.length === 0 ? (
              <div style={{ fontSize: "13px", color: "var(--color-muted)", fontStyle: "italic" }}>
                No prerequisites configured.
              </div>
            ) : (
              currentPrereqs.map(({ dependencyId, prereqTask }) => (
                <div
                  key={dependencyId}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    background: "var(--color-surface-soft)",
                    padding: "6px 10px",
                    borderRadius: "4px",
                    fontSize: "13px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>T{prereqTask?.id}:</span>
                    <span>{prereqTask?.title}</span>
                    <span
                      style={{
                        fontSize: "11px",
                        color: prereqTask?.column === "done" ? "var(--color-success)" : "var(--color-muted)",
                        fontWeight: 600,
                      }}
                    >
                      ({prereqTask?.column})
                    </span>
                  </div>
                  <button
                    onClick={() => handleRemoveDependency(dependencyId)}
                    style={{ color: "var(--color-error)", padding: "2px 6px", fontSize: "12px" }}
                  >
                    Remove
                  </button>
                </div>
              ))
            )}
          </div>

          {/* Add prerequisite form */}
          <div style={{ display: "flex", gap: "8px" }}>
            <select
              value={selectedPrereqId}
              onChange={(e) => setSelectedPrereqId(e.target.value ? Number(e.target.value) : "")}
              style={{
                flex: 1,
                padding: "8px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-hairline)",
                background: "var(--color-surface-soft)",
                color: "var(--color-ink)",
              }}
            >
              <option value="">Select a prerequisite task...</option>
              {candidatePrereqs.map((t) => (
                <option key={t.id} value={t.id}>
                  T{t.id}: {t.title} ({t.duration_days}d)
                </option>
              ))}
            </select>
            <button
              onClick={handleAddDependency}
              disabled={!selectedPrereqId}
              style={{
                background: "var(--color-primary)",
                color: "var(--color-on-primary)",
                padding: "8px 14px",
                borderRadius: "var(--radius-sm)",
                fontWeight: 600,
                fontSize: "13px",
                display: "flex",
                alignItems: "center",
                gap: "4px",
                opacity: selectedPrereqId ? 1 : 0.5,
              }}
            >
              <Plus size={15} /> Add
            </button>
          </div>
        </div>

        {/* Footer actions */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "12px" }}>
          <button
            onClick={handleDeleteTask}
            style={{
              color: "var(--color-error)",
              fontSize: "13px",
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
          >
            <Trash2 size={15} /> Delete Task
          </button>

          <button
            onClick={onClose}
            style={{
              padding: "8px 16px",
              background: "var(--color-hairline)",
              borderRadius: "var(--radius-sm)",
              fontSize: "13px",
              fontWeight: 500,
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
