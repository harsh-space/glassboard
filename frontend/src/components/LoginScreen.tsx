import React, { useState } from "react";
import { authApi, type AuthUser } from "../api";

interface Props {
  onAuth: (user: AuthUser) => void;
}

type Mode = "login" | "register";

export const LoginScreen: React.FC<Props> = ({ onAuth }) => {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      let user: AuthUser;
      if (mode === "login") {
        user = await authApi.login(email, password);
      } else {
        user = await authApi.register(email, username, password);
      }
      localStorage.setItem("auth_token", user.access_token);
      localStorage.setItem("auth_user", JSON.stringify({
        user_id: user.user_id,
        username: user.username,
        email: user.email,
      }));
      onAuth(user);
    } catch (err: any) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.overlay}>
      {/* Animated background */}
      <div style={styles.bgGradient} />
      <div style={styles.bgOrb1} />
      <div style={styles.bgOrb2} />

      <div style={styles.card}>
        {/* Logo */}
        <div style={styles.logoRow}>
          <div style={styles.logoIcon}>
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <rect width="28" height="28" rx="8" fill="var(--color-primary)" />
              <path d="M7 14L11 18L21 8" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <span style={styles.logoText}>TaskFlow Pro</span>
        </div>

        <h1 style={styles.title}>
          {mode === "login" ? "Welcome back" : "Create your account"}
        </h1>
        <p style={styles.subtitle}>
          {mode === "login"
            ? "Sign in to access your project boards"
            : "Get started with AI-powered project management"}
        </p>

        {/* Tab switcher */}
        <div style={styles.tabRow}>
          <button
            id="tab-login"
            style={{ ...styles.tab, ...(mode === "login" ? styles.tabActive : {}) }}
            onClick={() => { setMode("login"); setError(null); }}
          >
            Sign In
          </button>
          <button
            id="tab-register"
            style={{ ...styles.tab, ...(mode === "register" ? styles.tabActive : {}) }}
            onClick={() => { setMode("register"); setError(null); }}
          >
            Create Account
          </button>
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.fieldGroup}>
            <label style={styles.label} htmlFor="auth-email">Email</label>
            <input
              id="auth-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              style={styles.input}
            />
          </div>

          {mode === "register" && (
            <div style={styles.fieldGroup}>
              <label style={styles.label} htmlFor="auth-username">Username</label>
              <input
                id="auth-username"
                type="text"
                autoComplete="username"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="johndoe"
                style={styles.input}
              />
            </div>
          )}

          <div style={styles.fieldGroup}>
            <label style={styles.label} htmlFor="auth-password">Password</label>
            <input
              id="auth-password"
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={mode === "register" ? "Min. 6 characters" : "••••••••"}
              style={styles.input}
            />
          </div>

          {error && (
            <div style={styles.errorBox}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}>
                <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" />
                <path d="M8 5v3.5M8 11h.01" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
              {error}
            </div>
          )}

          <button
            id="auth-submit"
            type="submit"
            disabled={loading}
            style={{ ...styles.submitBtn, ...(loading ? styles.submitBtnLoading : {}) }}
          >
            {loading ? (
              <span style={styles.spinner} />
            ) : (
              mode === "login" ? "Sign In" : "Create Account"
            )}
          </button>
        </form>

        <p style={styles.switchText}>
          {mode === "login" ? "Don't have an account? " : "Already have an account? "}
          <button
            style={styles.switchLink}
            onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(null); }}
          >
            {mode === "login" ? "Sign up" : "Sign in"}
          </button>
        </p>
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(16px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes orbFloat {
          0%, 100% { transform: translateY(0px) scale(1); }
          50%       { transform: translateY(-30px) scale(1.04); }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        #auth-email:focus,
        #auth-username:focus,
        #auth-password:focus {
          outline: none;
          border-color: var(--color-primary) !important;
          box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.18);
        }
        #auth-submit:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 8px 24px rgba(99, 102, 241, 0.45);
        }
        #tab-login:hover, #tab-register:hover {
          background: rgba(99,102,241,0.08);
        }
      `}</style>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
    overflow: "hidden",
    background: "var(--color-bg)",
    padding: "24px",
  },
  bgGradient: {
    position: "absolute",
    inset: 0,
    background: "radial-gradient(ellipse 80% 60% at 50% -10%, rgba(99,102,241,0.18) 0%, transparent 70%)",
    pointerEvents: "none",
  },
  bgOrb1: {
    position: "absolute",
    width: "520px",
    height: "520px",
    borderRadius: "50%",
    background: "radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%)",
    top: "-120px",
    right: "-120px",
    animation: "orbFloat 8s ease-in-out infinite",
    pointerEvents: "none",
  },
  bgOrb2: {
    position: "absolute",
    width: "380px",
    height: "380px",
    borderRadius: "50%",
    background: "radial-gradient(circle, rgba(139,92,246,0.1) 0%, transparent 70%)",
    bottom: "-80px",
    left: "-80px",
    animation: "orbFloat 10s ease-in-out infinite reverse",
    pointerEvents: "none",
  },
  card: {
    position: "relative",
    zIndex: 1,
    background: "var(--color-surface-card)",
    border: "1px solid var(--color-hairline)",
    borderRadius: "20px",
    padding: "40px",
    width: "100%",
    maxWidth: "440px",
    boxShadow: "0 24px 80px rgba(0,0,0,0.18), 0 0 0 1px rgba(255,255,255,0.04)",
    animation: "fadeIn 0.35s ease",
  },
  logoRow: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    marginBottom: "28px",
  },
  logoIcon: {
    lineHeight: 0,
  },
  logoText: {
    fontFamily: "var(--font-serif)",
    fontSize: "18px",
    fontWeight: 700,
    color: "var(--color-ink)",
    letterSpacing: "-0.3px",
  },
  title: {
    fontFamily: "var(--font-serif)",
    fontSize: "26px",
    fontWeight: 700,
    color: "var(--color-ink)",
    marginBottom: "6px",
    letterSpacing: "-0.5px",
  },
  subtitle: {
    fontSize: "14px",
    color: "var(--color-muted)",
    marginBottom: "24px",
    lineHeight: 1.5,
  },
  tabRow: {
    display: "flex",
    gap: "4px",
    background: "var(--color-surface-soft)",
    borderRadius: "10px",
    padding: "4px",
    marginBottom: "24px",
  },
  tab: {
    flex: 1,
    padding: "8px 0",
    borderRadius: "8px",
    border: "none",
    background: "transparent",
    color: "var(--color-muted)",
    fontSize: "14px",
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.18s ease",
  },
  tabActive: {
    background: "var(--color-surface-card)",
    color: "var(--color-ink)",
    boxShadow: "0 1px 6px rgba(0,0,0,0.12)",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  fieldGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  label: {
    fontSize: "13px",
    fontWeight: 600,
    color: "var(--color-body)",
  },
  input: {
    padding: "11px 14px",
    borderRadius: "10px",
    border: "1px solid var(--color-hairline)",
    background: "var(--color-surface-soft)",
    color: "var(--color-ink)",
    fontSize: "14px",
    transition: "border-color 0.18s ease, box-shadow 0.18s ease",
  },
  errorBox: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "11px 14px",
    borderRadius: "10px",
    background: "var(--color-error-bg)",
    color: "var(--color-error)",
    fontSize: "13px",
    fontWeight: 500,
    border: "1px solid var(--color-error-border)",
  },
  submitBtn: {
    marginTop: "4px",
    padding: "13px",
    borderRadius: "10px",
    border: "none",
    background: "var(--color-primary)",
    color: "white",
    fontSize: "15px",
    fontWeight: 700,
    cursor: "pointer",
    transition: "transform 0.18s ease, box-shadow 0.18s ease",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "8px",
    letterSpacing: "-0.2px",
  },
  submitBtnLoading: {
    opacity: 0.7,
    cursor: "not-allowed",
  },
  spinner: {
    width: "18px",
    height: "18px",
    border: "2.5px solid rgba(255,255,255,0.3)",
    borderTopColor: "white",
    borderRadius: "50%",
    display: "inline-block",
    animation: "spin 0.7s linear infinite",
  },
  switchText: {
    marginTop: "20px",
    textAlign: "center",
    fontSize: "13px",
    color: "var(--color-muted)",
  },
  switchLink: {
    background: "none",
    border: "none",
    color: "var(--color-primary)",
    fontWeight: 600,
    cursor: "pointer",
    fontSize: "13px",
    textDecoration: "underline",
    textUnderlineOffset: "2px",
  },
};
