import React, { useState, useEffect } from "react";
import { authApi, type BoardSummary, type AuthUser } from "../api";
import { Plus, LayoutGrid, LogOut, Clock, ChevronRight, Layers } from "lucide-react";

interface Props {
  user: AuthUser;
  onSelectBoard: (boardId: number) => void;
  onLogout: () => void;
}

export const BoardDashboard: React.FC<Props> = ({ user, onSelectBoard, onLogout }) => {
  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newBoardName, setNewBoardName] = useState("");
  const [newBoardDate, setNewBoardDate] = useState(new Date().toISOString().split("T")[0]);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    loadBoards();
  }, []);

  const loadBoards = async () => {
    setLoading(true);
    try {
      const data = await authApi.listBoards();
      setBoards(data);
    } catch {
      setBoards([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newBoardName.trim()) return;
    setCreating(true);
    setCreateError(null);
    try {
      const board = await authApi.createBoard(newBoardName.trim(), newBoardDate);
      setBoards((prev) => [board, ...prev]);
      setShowCreate(false);
      setNewBoardName("");
      // Auto-open the newly created board
      onSelectBoard(board.id);
    } catch (err: any) {
      setCreateError(err.message || "Failed to create board.");
    } finally {
      setCreating(false);
    }
  };

  const initials = user.username
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <div style={styles.page}>
      {/* Navbar */}
      <header style={styles.navbar}>
        <div style={styles.navLogo}>
          <div style={styles.logoIcon}>
            <svg width="26" height="26" viewBox="0 0 28 28" fill="none">
              <rect width="28" height="28" rx="8" fill="var(--color-primary)" />
              <path d="M7 14L11 18L21 8" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <span style={styles.logoText}>TaskFlow Pro</span>
        </div>

        <div style={styles.navRight}>
          <div style={styles.avatar}>{initials}</div>
          <div style={styles.userInfo}>
            <span style={styles.userName}>{user.username}</span>
            <span style={styles.userEmail}>{user.email}</span>
          </div>
          <button id="logout-btn" onClick={onLogout} style={styles.logoutBtn} title="Sign out">
            <LogOut size={16} />
          </button>
        </div>
      </header>

      {/* Main content */}
      <main style={styles.main}>
        {/* Hero row */}
        <div style={styles.heroRow}>
          <div>
            <h1 style={styles.heroTitle}>Your Boards</h1>
            <p style={styles.heroSub}>
              Select a board to open it, or create a new one to get started.
            </p>
          </div>
          <button
            id="create-board-btn"
            onClick={() => setShowCreate(true)}
            style={styles.createBtn}
          >
            <Plus size={18} />
            New Board
          </button>
        </div>

        {/* Board grid */}
        {loading ? (
          <div style={styles.loadingRow}>
            {[1, 2, 3].map((i) => (
              <div key={i} style={styles.skeletonCard} />
            ))}
          </div>
        ) : boards.length === 0 ? (
          <div style={styles.emptyState}>
            <div style={styles.emptyIcon}>
              <Layers size={40} color="var(--color-muted)" />
            </div>
            <h2 style={styles.emptyTitle}>No boards yet</h2>
            <p style={styles.emptySub}>Create your first board to start organizing your project tasks.</p>
            <button
              id="empty-create-btn"
              onClick={() => setShowCreate(true)}
              style={styles.createBtn}
            >
              <Plus size={16} />
              Create Board
            </button>
          </div>
        ) : (
          <div style={styles.grid}>
            {boards.map((board) => (
              <button
                key={board.id}
                id={`board-card-${board.id}`}
                onClick={() => onSelectBoard(board.id)}
                style={styles.boardCard}
              >
                {/* Board icon */}
                <div style={styles.boardIconWrap}>
                  <LayoutGrid size={22} color="var(--color-primary)" />
                </div>

                <div style={styles.boardCardBody}>
                  <div style={styles.boardName}>{board.name}</div>
                  <div style={styles.boardMeta}>
                    <span style={styles.metaChip}>
                      <Clock size={11} />
                      {new Date(board.start_date).toLocaleDateString("en-US", {
                        month: "short", day: "numeric", year: "numeric"
                      })}
                    </span>
                    <span style={styles.metaChip}>
                      {board.task_count} task{board.task_count !== 1 ? "s" : ""}
                    </span>
                  </div>
                </div>

                <ChevronRight size={18} color="var(--color-muted)" style={{ flexShrink: 0 }} />
              </button>
            ))}
          </div>
        )}
      </main>

      {/* Create Board Modal */}
      {showCreate && (
        <div style={styles.modalOverlay} onClick={() => setShowCreate(false)}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h2 style={styles.modalTitle}>Create New Board</h2>
            <p style={styles.modalSub}>Give your project board a name and an anchor start date.</p>

            <form onSubmit={handleCreate} style={styles.modalForm}>
              <div style={styles.fieldGroup}>
                <label style={styles.label} htmlFor="new-board-name">Board Name</label>
                <input
                  id="new-board-name"
                  type="text"
                  required
                  autoFocus
                  value={newBoardName}
                  onChange={(e) => setNewBoardName(e.target.value)}
                  placeholder="e.g. Q4 Product Launch"
                  style={styles.input}
                />
              </div>

              <div style={styles.fieldGroup}>
                <label style={styles.label} htmlFor="new-board-date">Anchor Start Date</label>
                <input
                  id="new-board-date"
                  type="date"
                  required
                  value={newBoardDate}
                  onChange={(e) => setNewBoardDate(e.target.value)}
                  style={styles.input}
                />
              </div>

              {createError && (
                <div style={styles.errorBox}>{createError}</div>
              )}

              <div style={styles.modalActions}>
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  style={styles.cancelBtn}
                >
                  Cancel
                </button>
                <button
                  id="confirm-create-board"
                  type="submit"
                  disabled={creating}
                  style={{ ...styles.createBtn, opacity: creating ? 0.7 : 1 }}
                >
                  {creating ? "Creating…" : "Create Board"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <style>{`
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(12px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        #create-board-btn:hover,
        #empty-create-btn:hover,
        #confirm-create-board:hover {
          background-color: var(--color-primary-active) !important;
        }
        #logout-btn:hover { background: var(--color-surface-soft) !important; }
        [id^="board-card-"]:hover {
          border-color: var(--color-primary) !important;
          box-shadow: var(--shadow-md) !important;
          transform: translateY(-1px);
        }
        #new-board-name:focus, #new-board-date:focus {
          outline: none;
          border-color: var(--color-primary) !important;
          box-shadow: 0 0 0 2px var(--color-primary-light);
        }
      `}</style>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: "100vh",
    background: "var(--color-canvas)",
    position: "relative",
  },
  navbar: {
    position: "relative",
    zIndex: 10,
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "16px 32px",
    background: "var(--color-surface-soft)",
    borderBottom: "1px solid var(--color-hairline)",
    backdropFilter: "blur(12px)",
  },
  navLogo: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
  },
  logoIcon: { lineHeight: 0 },
  logoText: {
    fontFamily: "var(--font-serif)",
    fontSize: "18px",
    fontWeight: 700,
    color: "var(--color-ink)",
    letterSpacing: "-0.3px",
  },
  navRight: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
  },
  avatar: {
    width: "36px",
    height: "36px",
    borderRadius: "50%",
    background: "linear-gradient(135deg, var(--color-primary), #8b5cf6)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "white",
    fontSize: "13px",
    fontWeight: 700,
    flexShrink: 0,
  },
  userInfo: {
    display: "flex",
    flexDirection: "column",
  },
  userName: {
    fontSize: "13px",
    fontWeight: 600,
    color: "var(--color-ink)",
    lineHeight: 1.2,
  },
  userEmail: {
    fontSize: "11px",
    color: "var(--color-muted)",
    lineHeight: 1.2,
  },
  logoutBtn: {
    padding: "8px",
    borderRadius: "8px",
    border: "1px solid var(--color-hairline)",
    background: "transparent",
    color: "var(--color-muted)",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    transition: "background 0.15s",
  },
  main: {
    position: "relative",
    zIndex: 1,
    maxWidth: "900px",
    margin: "0 auto",
    padding: "48px 24px",
    animation: "fadeUp 0.4s ease",
  },
  heroRow: {
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "space-between",
    marginBottom: "36px",
    flexWrap: "wrap",
    gap: "16px",
  },
  heroTitle: {
    fontFamily: "var(--font-serif)",
    fontSize: "32px",
    fontWeight: 700,
    color: "var(--color-ink)",
    letterSpacing: "-0.8px",
    marginBottom: "6px",
  },
  heroSub: {
    fontSize: "15px",
    color: "var(--color-muted)",
  },
  createBtn: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "11px 20px",
    borderRadius: "10px",
    border: "none",
    background: "var(--color-primary)",
    color: "white",
    fontSize: "14px",
    fontWeight: 700,
    cursor: "pointer",
    transition: "transform 0.18s ease, box-shadow 0.18s ease",
    flexShrink: 0,
  },
  loadingRow: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  skeletonCard: {
    height: "80px",
    borderRadius: "14px",
    background: "var(--color-surface-soft)",
    animation: "pulse 1.4s ease-in-out infinite",
  },
  grid: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  boardCard: {
    display: "flex",
    alignItems: "center",
    gap: "16px",
    padding: "20px 24px",
    borderRadius: "14px",
    border: "1px solid var(--color-hairline)",
    background: "var(--color-surface-card)",
    cursor: "pointer",
    textAlign: "left",
    transition: "all 0.2s ease",
    width: "100%",
    boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
  },
  boardIconWrap: {
    width: "48px",
    height: "48px",
    borderRadius: "12px",
    background: "var(--color-primary-light)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  },
  boardCardBody: {
    flex: 1,
    minWidth: 0,
  },
  boardName: {
    fontSize: "16px",
    fontWeight: 700,
    color: "var(--color-ink)",
    letterSpacing: "-0.2px",
    marginBottom: "6px",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  boardMeta: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    flexWrap: "wrap",
  },
  metaChip: {
    display: "inline-flex",
    alignItems: "center",
    gap: "4px",
    fontSize: "12px",
    color: "var(--color-muted)",
    background: "var(--color-surface-soft)",
    padding: "3px 10px",
    borderRadius: "20px",
    fontWeight: 500,
  },
  emptyState: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: "80px 24px",
    textAlign: "center",
    gap: "12px",
  },
  emptyIcon: {
    width: "80px",
    height: "80px",
    borderRadius: "20px",
    background: "var(--color-surface-soft)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: "8px",
  },
  emptyTitle: {
    fontFamily: "var(--font-serif)",
    fontSize: "22px",
    fontWeight: 700,
    color: "var(--color-ink)",
  },
  emptySub: {
    fontSize: "14px",
    color: "var(--color-muted)",
    maxWidth: "360px",
    marginBottom: "12px",
  },
  modalOverlay: {
    position: "fixed",
    inset: 0,
    background: "rgba(0,0,0,0.45)",
    backdropFilter: "blur(6px)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
    padding: "24px",
  },
  modal: {
    background: "var(--color-surface-card)",
    borderRadius: "20px",
    border: "1px solid var(--color-hairline)",
    padding: "36px",
    width: "100%",
    maxWidth: "420px",
    boxShadow: "0 24px 80px rgba(0,0,0,0.22)",
    animation: "fadeUp 0.25s ease",
  },
  modalTitle: {
    fontFamily: "var(--font-serif)",
    fontSize: "22px",
    fontWeight: 700,
    color: "var(--color-ink)",
    marginBottom: "6px",
  },
  modalSub: {
    fontSize: "13px",
    color: "var(--color-muted)",
    marginBottom: "24px",
  },
  modalForm: {
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
    transition: "border-color 0.18s, box-shadow 0.18s",
  },
  errorBox: {
    padding: "11px 14px",
    borderRadius: "10px",
    background: "var(--color-error-bg)",
    color: "var(--color-error)",
    fontSize: "13px",
    fontWeight: 500,
    border: "1px solid var(--color-error-border)",
  },
  modalActions: {
    display: "flex",
    justifyContent: "flex-end",
    gap: "10px",
    marginTop: "4px",
  },
  cancelBtn: {
    padding: "10px 18px",
    borderRadius: "10px",
    border: "1px solid var(--color-hairline)",
    background: "var(--color-surface-soft)",
    color: "var(--color-body)",
    fontSize: "14px",
    fontWeight: 600,
    cursor: "pointer",
  },
};
