import React, { useState } from "react";
import { authApi } from "../api";
import { Sparkles, ArrowRight } from "lucide-react";

interface SetUsernameModalProps {
  isOpen: boolean;
  onUsernameUpdated: (newUsername: string) => void;
}

export const SetUsernameModal: React.FC<SetUsernameModalProps> = ({
  isOpen,
  onUsernameUpdated,
}) => {
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const clean = username.trim();
    if (!clean || clean.length < 3) {
      setError("Username must be at least 3 characters long.");
      return;
    }
    if (clean.toLowerCase().startsWith("temp_")) {
      setError("Username cannot start with 'temp_'.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const updated = await authApi.updateUsername(clean);
      onUsernameUpdated(updated.username);
    } catch (err: any) {
      setError(err.message || "Failed to update username. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(20, 20, 19, 0.5)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1200,
        padding: "20px",
        animation: "fadeIn 0.2s ease-out",
      }}
    >
      <div
        style={{
          background: "var(--color-surface-soft)",
          border: "1px solid var(--color-hairline)",
          borderRadius: "var(--radius-lg)",
          width: "100%",
          maxWidth: "420px",
          padding: "28px",
          boxShadow: "var(--shadow-lg)",
          animation: "slideDown 0.2s ease-out",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "var(--radius-md)",
              background: "var(--color-primary-light)",
              color: "var(--color-primary)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Sparkles size={20} />
          </div>
          <div>
            <h2
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: "20px",
                fontWeight: 600,
                color: "var(--color-ink)",
                lineHeight: 1.2,
              }}
            >
              Choose Your Username
            </h2>
            <span style={{ fontSize: "13px", color: "var(--color-muted)" }}>
              One last step to personalize your workspace
            </span>
          </div>
        </div>

        <p
          style={{
            fontSize: "13px",
            color: "var(--color-body)",
            marginBottom: "20px",
            lineHeight: 1.5,
          }}
        >
          You've signed up with a temporary handle. Please pick a permanent username for your project boards and activity.
        </p>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <label
              htmlFor="set-username-input"
              style={{
                display: "block",
                fontSize: "11px",
                fontWeight: 600,
                color: "var(--color-muted)",
                letterSpacing: "0.05em",
                textTransform: "uppercase",
                marginBottom: "6px",
              }}
            >
              Final Username *
            </label>
            <input
              id="set-username-input"
              type="text"
              autoFocus
              required
              minLength={3}
              maxLength={40}
              placeholder="e.g. alex_developer"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              style={{
                width: "100%",
                padding: "9px 12px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-hairline)",
                background: "var(--color-canvas)",
                color: "var(--color-ink)",
                fontSize: "14px",
                outline: "none",
                transition: "border-color 0.15s ease",
              }}
            />
          </div>

          {error && (
            <div
              style={{
                padding: "9px 12px",
                borderRadius: "var(--radius-sm)",
                background: "var(--color-error-bg)",
                border: "1px solid var(--color-error-border)",
                color: "var(--color-error)",
                fontSize: "13px",
                lineHeight: 1.4,
              }}
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !username.trim()}
            style={{
              padding: "10px 16px",
              borderRadius: "var(--radius-sm)",
              background: "var(--color-primary)",
              color: "var(--color-on-primary)",
              fontWeight: 600,
              fontSize: "14px",
              cursor: loading || !username.trim() ? "not-allowed" : "pointer",
              opacity: loading || !username.trim() ? 0.65 : 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              marginTop: "4px",
              transition: "background 0.15s ease",
            }}
          >
            {loading ? "Saving..." : "Set Username"}
            {!loading && <ArrowRight size={16} />}
          </button>
        </form>
      </div>
    </div>
  );
};
