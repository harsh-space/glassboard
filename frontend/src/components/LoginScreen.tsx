import React, { useState } from "react";
import { authApi, type AuthUser } from "../api";
import { ArrowRight, AlertCircle } from "lucide-react";

interface Props {
  onAuth: (user: AuthUser) => void;
}

type Mode = "login" | "register";

export const LoginScreen: React.FC<Props> = ({ onAuth }) => {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
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
        user = await authApi.register(email, password);
      }
      localStorage.setItem("auth_token", user.access_token);
      localStorage.setItem(
        "auth_user",
        JSON.stringify({
          user_id: user.user_id,
          username: user.username,
          email: user.email,
        })
      );
      onAuth(user);
    } catch (err: any) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        {/* Brand header */}
        <div style={styles.logoRow}>
          <div style={styles.logoIcon}>
            <svg width="24" height="24" viewBox="0 0 28 28" fill="none">
              <rect width="28" height="28" rx="8" fill="var(--color-primary)" />
              <path
                d="M7 14L11 18L21 8"
                stroke="white"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
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
        <div style={styles.tabContainer}>
          <button
            id="tab-login"
            type="button"
            style={{
              ...styles.tab,
              ...(mode === "login" ? styles.tabActive : styles.tabInactive),
            }}
            onClick={() => {
              setMode("login");
              setError(null);
            }}
          >
            Sign In
          </button>
          <button
            id="tab-register"
            type="button"
            style={{
              ...styles.tab,
              ...(mode === "register" ? styles.tabActive : styles.tabInactive),
            }}
            onClick={() => {
              setMode("register");
              setError(null);
            }}
          >
            Create Account
          </button>
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.field}>
            <label style={styles.label} htmlFor="auth-email">
              Email Address
            </label>
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

          <div style={styles.field}>
            <div style={styles.labelRow}>
              <label style={styles.label} htmlFor="auth-password">
                Password
              </label>
            </div>
            <input
              id="auth-password"
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={mode === "register" ? "At least 6 characters" : "••••••••"}
              style={styles.input}
            />
          </div>

          {error && (
            <div style={styles.errorBanner}>
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          <button
            id="auth-submit"
            type="submit"
            disabled={loading}
            style={{
              ...styles.submitBtn,
              ...(loading ? styles.submitBtnLoading : {}),
            }}
          >
            {loading ? (
              <span style={styles.spinner} />
            ) : (
              <>
                <span>{mode === "login" ? "Sign In" : "Create Account"}</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>

        <p style={styles.footerNote}>
          {mode === "login"
            ? "Don't have an account? "
            : "Already have an account? "}
          <button
            type="button"
            style={styles.switchBtn}
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError(null);
            }}
          >
            {mode === "login" ? "Create one" : "Sign in"}
          </button>
        </p>
      </div>

      <style>{`
        #auth-email:focus,
        #auth-password:focus {
          border-color: var(--color-primary) !important;
          box-shadow: 0 0 0 2px var(--color-primary-light);
        }
        #auth-submit:hover:not(:disabled) {
          background-color: var(--color-primary-active) !important;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "var(--color-canvas)",
    padding: "24px",
    fontFamily: "var(--font-sans)",
  },
  card: {
    width: "100%",
    maxWidth: "420px",
    backgroundColor: "var(--color-surface-card)",
    border: "1px solid var(--color-hairline)",
    borderRadius: "var(--radius-lg)",
    boxShadow: "var(--shadow-md)",
    padding: "36px 32px",
    animation: "fadeIn 0.25s ease-out",
  },
  logoRow: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    marginBottom: "20px",
  },
  logoIcon: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  logoText: {
    fontFamily: "var(--font-serif)",
    fontSize: "18px",
    fontWeight: 600,
    color: "var(--color-ink)",
    letterSpacing: "-0.2px",
  },
  title: {
    fontFamily: "var(--font-serif)",
    fontSize: "24px",
    fontWeight: 600,
    color: "var(--color-ink)",
    marginBottom: "6px",
    lineHeight: 1.25,
  },
  subtitle: {
    fontSize: "13px",
    color: "var(--color-muted)",
    marginBottom: "22px",
    lineHeight: 1.45,
  },
  tabContainer: {
    display: "flex",
    gap: "4px",
    background: "var(--color-surface-soft)",
    border: "1px solid var(--color-hairline)",
    borderRadius: "var(--radius-md)",
    padding: "3px",
    marginBottom: "20px",
  },
  tab: {
    flex: 1,
    padding: "7px 0",
    borderRadius: "calc(var(--radius-md) - 2px)",
    fontSize: "13px",
    cursor: "pointer",
    transition: "all 0.15s ease",
  },
  tabActive: {
    background: "var(--color-surface-card-elevated)",
    color: "var(--color-ink)",
    fontWeight: 600,
    boxShadow: "var(--shadow-sm)",
  },
  tabInactive: {
    background: "transparent",
    color: "var(--color-muted)",
    fontWeight: 500,
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  field: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  labelRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  label: {
    fontSize: "11px",
    fontWeight: 600,
    color: "var(--color-muted)",
    letterSpacing: "0.04em",
    textTransform: "uppercase",
  },
  input: {
    width: "100%",
    padding: "9px 12px",
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--color-hairline)",
    backgroundColor: "var(--color-canvas)",
    color: "var(--color-ink)",
    fontSize: "14px",
    outline: "none",
    transition: "border-color 0.15s ease, box-shadow 0.15s ease",
    boxSizing: "border-box",
  },
  errorBanner: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "9px 12px",
    borderRadius: "var(--radius-sm)",
    background: "var(--color-error-bg)",
    border: "1px solid var(--color-error-border)",
    color: "var(--color-error)",
    fontSize: "13px",
    lineHeight: 1.4,
  },
  submitBtn: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "8px",
    marginTop: "6px",
    padding: "10px 16px",
    borderRadius: "var(--radius-sm)",
    background: "var(--color-primary)",
    color: "var(--color-on-primary)",
    fontSize: "14px",
    fontWeight: 600,
    cursor: "pointer",
    transition: "background-color 0.15s ease",
    border: "none",
  },
  submitBtnLoading: {
    opacity: 0.7,
    cursor: "not-allowed",
  },
  spinner: {
    width: "16px",
    height: "16px",
    border: "2px solid rgba(255,255,255,0.3)",
    borderTopColor: "white",
    borderRadius: "50%",
    display: "inline-block",
    animation: "spin 0.6s linear infinite",
  },
  footerNote: {
    marginTop: "20px",
    textAlign: "center",
    fontSize: "13px",
    color: "var(--color-muted)",
  },
  switchBtn: {
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
