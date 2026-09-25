import React, { useState } from "react";
import type { AISuggestion, Task } from "../types";
import { api, ApiRequestError } from "../api";
import { Sparkles, Check, X, AlertTriangle, ArrowRight } from "lucide-react";


interface AISuggestionsDrawerProps {
  isOpen: boolean;
  suggestions: AISuggestion[];
  allTasks: Task[];
  onClose: () => void;
  onRefreshSuggestions: () => void;
  onSuggestionsLoaded?: (suggestions: AISuggestion[]) => void;
  onSuggestionApplied: (downstreamChanges: any[]) => void;
}

export const AISuggestionsDrawer: React.FC<AISuggestionsDrawerProps> = ({
  isOpen,
  suggestions,
  allTasks,
  onClose,
  onRefreshSuggestions,
  onSuggestionsLoaded,
  onSuggestionApplied,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getAISuggestions(1);
      if (onSuggestionsLoaded) {
        onSuggestionsLoaded(res);
      }
      onRefreshSuggestions();
    } catch (err: any) {
      if (err instanceof ApiRequestError) {
        setError(`${err.code}: ${err.message}`);
      } else {
        setError(err.message || "Failed to trigger AI suggestions");
      }
    } finally {
      setLoading(false);
    }
  };


  const handleAccept = async (id: number) => {
    setError(null);
    try {
      const res = await api.acceptSuggestion(id);
      onSuggestionApplied(res.downstream_changes);
      onRefreshSuggestions();
    } catch (err: any) {
      if (err instanceof ApiRequestError) {
        setError(`${err.code}: ${err.message}`);
      } else {
        setError(err.message || "Failed to accept suggestion");
      }
    }
  };

  const handleReject = async (id: number) => {
    setError(null);
    try {
      await api.rejectSuggestion(id);
      onRefreshSuggestions();
    } catch (err: any) {
      setError(err.message || "Failed to reject suggestion");
    }
  };

  const pendingList = suggestions.filter((s) => s.status === "pending");

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        right: 0,
        bottom: 0,
        width: "440px",
        background: "var(--color-surface-soft)",
        borderLeft: "1px solid var(--color-hairline)",
        boxShadow: "var(--shadow-lg)",
        zIndex: 1200,
        display: "flex",
        flexDirection: "column",
        padding: "24px",
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Sparkles size={20} color="var(--color-primary)" />
          <h2 style={{ fontFamily: "var(--font-serif)", fontSize: "20px", fontWeight: 600 }}>
            AI Dependency Copilot
          </h2>
        </div>
        <button onClick={onClose} style={{ color: "var(--color-muted)", padding: "4px" }}>
          <X size={20} />
        </button>
      </div>

      <p style={{ fontSize: "13px", color: "var(--color-muted)", marginBottom: "16px", lineHeight: 1.4 }}>
        Guardrailed pipeline: The AI proposes candidate links, deterministic checks verify invariants, and you approve or reject each link.
      </p>

      {/* Trigger Button */}
      <button
        onClick={handleGenerate}
        disabled={loading}
        style={{
          background: "var(--color-primary)",
          color: "var(--color-on-primary)",
          padding: "10px 16px",
          borderRadius: "var(--radius-sm)",
          fontWeight: 600,
          fontSize: "14px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "8px",
          marginBottom: "16px",
          opacity: loading ? 0.6 : 1,
        }}
      >
        <Sparkles size={16} />
        <span>{loading ? "Analyzing Board Lifecycle..." : "Find Candidate Dependencies"}</span>
      </button>

      {error && (
        <div
          style={{
            background: "var(--color-error-bg)",
            color: "var(--color-error)",
            padding: "10px 12px",
            borderRadius: "var(--radius-sm)",
            fontSize: "13px",
            marginBottom: "16px",
            display: "flex",
            alignItems: "center",
            gap: "6px",
          }}
        >
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Suggestions List */}
      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "12px" }}>
        {pendingList.length === 0 ? (
          <div
            style={{
              padding: "40px 16px",
              textAlign: "center",
              color: "var(--color-muted)",
              fontSize: "14px",
              background: "var(--color-canvas)",
              borderRadius: "var(--radius-md)",
              border: "1px dashed var(--color-hairline)",
            }}
          >
            No pending suggestions. Click the button above to run the dependency copilot on this board.
          </div>
        ) : (
          pendingList.map((sug) => {
            const pTask = allTasks.find((t) => t.id === sug.prerequisite_id);
            const depTask = allTasks.find((t) => t.id === sug.task_id);

            return (
              <div
                key={sug.id}
                style={{
                  background: "var(--color-canvas)",
                  border: "1px solid var(--color-hairline)",
                  borderRadius: "var(--radius-md)",
                  padding: "14px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "8px",
                }}
              >
                {/* Proposed link pair */}
                <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 600, fontSize: "13px" }}>
                  <span style={{ color: "var(--color-primary)" }}>T{sug.prerequisite_id}</span>
                  <ArrowRight size={13} color="var(--color-muted)" />
                  <span style={{ color: "var(--color-ink)" }}>T{sug.task_id}</span>

                  <span
                    style={{
                      marginLeft: "auto",
                      fontSize: "11px",
                      padding: "2px 6px",
                      borderRadius: "var(--radius-pill)",
                      background: sug.model_name === "heuristic-fallback" ? "var(--color-warning-bg)" : "var(--color-primary-light)",
                      color: sug.model_name === "heuristic-fallback" ? "var(--color-warning)" : "var(--color-primary)",
                      fontWeight: 600,
                    }}
                  >
                    {sug.model_name === "heuristic-fallback" ? "Heuristic" : `${Math.round(sug.proposer_confidence * 100)}%`}
                  </span>
                </div>

                <div style={{ fontSize: "12px", color: "var(--color-muted)" }}>
                  <strong>Prereq:</strong> {pTask?.title || `Task #${sug.prerequisite_id}`}
                  <br />
                  <strong>Dependent:</strong> {depTask?.title || `Task #${sug.task_id}`}
                </div>

                <div style={{ fontSize: "13px", color: "var(--color-body)", fontStyle: "italic", lineHeight: 1.35 }}>
                  "{sug.reason}"
                </div>

                {sug.evidence_phrase && (
                  <div style={{ fontSize: "11px", color: "var(--color-muted)" }}>
                    <span style={{ fontWeight: 600 }}>Evidence quote: </span>
                    <code style={{ background: "rgba(0,0,0,0.05)", padding: "1px 4px", borderRadius: "3px" }}>
                      {sug.evidence_phrase}
                    </code>
                  </div>
                )}

                {/* Actions */}
                <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
                  <button
                    onClick={() => handleAccept(sug.id)}
                    style={{
                      flex: 1,
                      background: "var(--color-success)",
                      color: "white",
                      padding: "6px 12px",
                      borderRadius: "var(--radius-sm)",
                      fontSize: "12px",
                      fontWeight: 600,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: "4px",
                    }}
                  >
                    <Check size={14} /> Accept
                  </button>
                  <button
                    onClick={() => handleReject(sug.id)}
                    style={{
                      background: "rgba(0,0,0,0.05)",
                      color: "var(--color-muted)",
                      padding: "6px 12px",
                      borderRadius: "var(--radius-sm)",
                      fontSize: "12px",
                      fontWeight: 500,
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                    }}
                  >
                    <X size={14} /> Reject
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
