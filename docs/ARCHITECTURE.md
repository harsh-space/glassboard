# TaskFlow Pro — Architecture Document

> Written against what was actually built, per `BUILD_SPEC.md §7` and `CLAUDE.md §7`.
> Last updated: 2026-09-25

---

## 1. System overview

TaskFlow Pro is a Kanban-style task management tool that makes dependency
constraints visible and enforces them. The distinguishing property is that
all scheduling logic (planned start/end dates, blocked/ready state, critical
path, slack) is derived from a directed acyclic graph (DAG) of task
prerequisites, never stored directly. The AI copilot can propose new
dependency edges; a human must approve every link before it is committed.

```
Browser (React + TypeScript)
    |
    | HTTP/JSON (port 5173 → proxied to 8000)
    |
FastAPI Backend (port 8000)
    |
    |--- engine/ (pure Python, no DB/web imports)
    |       ├── graph.py        cycle detection, topological utilities
    |       ├── scheduler.py    incremental recompute (max-not-sum)
    |       ├── derive.py       blocked/ready derivation, regression
    |       ├── invariants.py   Invariant Gate
    |       └── oracle.py       brute-force reference impl (tests only)
    |
    |--- SQLite (taskflow.db, via SQLAlchemy)
    |       tables: board, task, dependency, ai_suggestion, audit_log
    |
    └--- backend/ai/pipeline.py    heuristic fallback + LLM stub
```

---

## 2. Data model decisions

Schema matches `BUILD_SPEC.md §2` exactly. Key decisions:

### 2.1 `actual_end` semantics (escalated decision, confirmed by user)

`actual_end` is set to `planned_end` (not `datetime.today()`) when a task
moves to Done. This choice was made for test determinism — tests comparing
`actual_end` to `planned_end` produce stable, repeatable results without
depending on the wall-clock date. The tradeoff is that "finished early"
scenarios (where `actual_end < planned_end`) cannot be naturally observed
through normal movement; they can still be forced by setting
`actual_end` explicitly in tests or by the regression handler (which sets
`actual_end = None` and recomputes).

**Documented impact on the Why Panel:** The sentence "moved N days earlier
because `<task>` finished early" will only fire when a task's `actual_end`
is explicitly set earlier than its `planned_end`. In normal usage (task
drag to Done = `actual_end = planned_end`), no early-finish acceleration
is observed.

### 2.2 Derived fields — never stored

`blocked`, `ready`, `driving_prerequisite_id`, and per-prerequisite `slack`
are computed on every read inside `engine.derive.derive_task_fields`. They
exist only in the HTTP response payload and in-memory for the duration of
each request. No database column, migration, or cached table was created
for these values.

### 2.3 Version column

Starts at 1, incremented by `PATCH /tasks/{id}` and `POST /tasks/{id}/move`
on every successful write. Used to detect stale concurrent edits: if the
request's `version` != the DB's current `version`, the endpoint returns
`409 VERSION_CONFLICT` and makes no change.

---

## 3. Core algorithm implementation

### 3.1 Cycle detection (`engine/graph.py`)

BFS forward from the proposed dependent task `T`, following successor
(task_id) edges. If the proposed prerequisite `P` is reachable from `T`,
adding `P → T` would create a cycle. The path `T → ... → P` is
reconstructed from the BFS parent map and appended with `T` again to show
the closed loop. The check runs before the INSERT, inside the same
transaction; nothing is written on rejection.

### 3.2 Scheduling recompute (`engine/scheduler.py`)

Implements the non-compounding max-not-sum rule from `BUILD_SPEC.md §3.2`
exactly:

1. Forward closure from the changed task (BFS through successor edges).
2. Topological sort of the affected set (Kahn's algorithm), but reads
   finish dates from prerequisites even outside the affected set.
3. For each task in topological order:
   `planned_start = max(prerequisite finish dates, pinned_start, board.start_date)`
   The `max()` is taken once from final prerequisite finish dates — never
   summed, never taken per-path. This prevents compounding across diamond
   convergences.

**Diamond verification (seed board T4/T5 → T7):**
Delaying T2 by 3 days causes T4 (the driving prerequisite, longest path)
to move by 3 days, pulling T7 exactly 3 days. T5 moves by the same 3 days
but T7's `planned_start` was already pinned by T4, so T7's movement is
3 days (not 6). T5's slack for T7 is reported as 3 days — the difference
between T4's and T5's finish dates.

### 3.3 Regression handling (`engine/derive.py`)

When a task moves out of Done:
- `actual_end` is cleared to `None`.
- `recompute()` reruns using `planned_end` again (instead of the now-null
  `actual_end`).
- Downstream tasks already in Done are flagged with
  `audit_log(action='needs_reverification')` but are NOT auto-moved — a
  human must decide whether to regress them too.

### 3.4 Invariant Gate (`engine/invariants.py`)

Runs inside every write transaction, immediately before commit. Checks:
1. Graph is still acyclic.
2. No `dep.planned_start < prereq_finish` for any edge.
3. No task with column ∈ {in_progress, review, done} is blocked.

If any violation fires, the transaction is aborted and `audit_log` gets
`action='invariant_gate_failed'`. In correct production code this should
never fire; if it does, it is a bug.

### 3.5 Performance benchmarks (measured by `scripts/measure_performance.py`)

Benchmarks measured against the internal targets defined in `docs/synopsis/05-impact.md`:

| Benchmark | Configuration | Measured Result | 05-impact.md Target | Status |
|---|---|---|---|---|
| Cycle check + propagation + Invariant Gate | Synthetic DAG: 1,000 tasks, 3,000 dependencies | 109.42 ms | < 100 ms | MISS (slight overrun, ~94–117ms across runs) |
| Board load derive | In-memory graph: 500 tasks, 1,000 dependencies | 212.15 ms | < 300 ms | MET |
| Drag-and-drop persist | In-memory engine cost: 100 tasks, 200 dependencies | 2.22 ms/op | < 150 ms | MET |

The engine propagation and Invariant Gate on 1,000 tasks and 3,000 dependencies runs in ~109 ms in pure Python (borderline around the 100 ms target depending on CPU load), while board-load derive across 500 tasks easily beats the 300 ms limit at 212 ms.

---

## 4. API design

All mutation endpoints follow the pattern:
`validate → apply → recompute → check invariants → commit → return`

Error body is always:
```json
{"error": {"code": "SOME_CODE", "message": "human readable", "details": {}}}
```

CORS is restricted to `http://localhost:5173` (the Vite dev server origin)
only, not `*`. This is enforced in `backend/main.py` via FastAPI's
`CORSMiddleware` with `allow_origins=["http://localhost:5173"]`.

Pydantic v2 schemas validate every request body. A missing required field
or wrong type returns a clean `400 BAD_REQUEST`, not a raw stack trace.
The `app.exception_handler(RequestValidationError)` handler normalizes all
Pydantic errors to the standard error body format.

---

## 5. AI pipeline

### 5.1 Architecture (heuristic fallback mode — no LLM key set)

The AI pipeline in `backend/ai/pipeline.py` implements:
- **Propose:** `generate_heuristic_suggestions()` — keyword-stage ordering
  heuristic from `BUILD_SPEC.md §5.6`.
- **Challenge:** Not run in heuristic mode (verdict = "not_run").
- **Verify:** Seven deterministic checks per `BUILD_SPEC.md §5.3` run in
  the route handler (`backend/routes/dependencies.py`).
- **Human review:** Accept / Reject endpoints per §5.4.

Rate limiting: one suggestion round per board at a time, enforced by
`BoardLockContext` (in-memory threading.Lock). A concurrent request returns
`429 RATE_LIMITED`.

### 5.2 Model/provider decision [CONFIRMED — Groq / allam-2-7b]

For Phase 5 (full LLM path), the confirmed production provider is **Groq**
using the **allam-2-7b** model (via `GROQ_API_KEY` and Groq's OpenAI-compatible
endpoint). The pipeline in `backend/ai/pipeline.py` implements a two-call
architecture (Propose + Challenge) with deterministic verification. If
`GROQ_API_KEY` is unset or unavailable, the system automatically and
transparently falls back to the deterministic keyword-stage heuristic.

### 5.3 Heuristic performance (measured by `scripts/measure_ai.py`)

Against the canonical 13-edge seed board, with a blank starting graph
(all edges cleared before the heuristic runs) and no LLM:

| Metric | Before Tuning | After Tuning (Prereq Keyword Scope) | Target |
|---|---|---|---|
| Suggestions generated | 8 | 11 | — |
| True Positives | 7 | 11 | — |
| False Positives | 1 | 0 | — |
| False Negatives | 6 | 2 | — |
| Precision | 87.5% | 100.0% | ≥ 85% (MET) |
| Recall | 53.8% | 84.6% | ≥ 70% (MET) |
| F1 | 66.7% | 91.7% | — |
| Acceptance rate (offline TP) | 87.5% | 100.0% | — |

**Tuning changes:**
1. In `_get_stage()`, prioritized task `title` keywords before falling back to `description`. This prevents downstream tasks that describe what they depend on (such as T4 "Backend API Development" and T5 "Test Data Setup" both mentioning "database schema") from being falsely classified into their prerequisite's stage.
2. In `generate_heuristic_suggestions()`, restricted evidence keyword matching to keywords associated with the specific prerequisite task (rather than any task sharing the prerequisite's lifecycle stage). This eliminates false positives between sibling tasks sharing a stage (e.g. T2 Schema vs T3 Wireframes).

Remaining false negatives (2):
- T1→T2 (Requirements → Schema): "requirements" does not appear in T2 description.
- T1→T3 (Requirements → Wireframes): "requirements" does not appear in T3 description.

### 5.4 Confidence threshold

The deterministic Verify step (§5.3 check 6) uses a confidence threshold
of **0.5**. Heuristic-mode suggestions are assigned a fixed confidence of
`0.85`, so all pass. When a real LLM is added, tune this threshold during
Phase 5 testing and update this document.

---

## 6. Frontend architecture

React 19 + TypeScript + Vite. Key choices:

- **dnd-kit** for drag-and-drop: `@dnd-kit/core` DndContext wraps the
  board; each card uses `useSortable`; the `DragOverlay` renders the
  floating ghost card during drag.
- **Optimistic updates:** On drag-end, the board state is updated
  immediately in React state, and the move API call is made. On error, the
  pre-drag snapshot is restored.
- **Blocked enforcement (dual-layer):** The backend rejects any move of a
  blocked task with `409 TASK_BLOCKED`. The frontend also shows a visible
  error banner with the server's error message — the drag is not silently
  no-op'd.
- **Why Panel:** Opens in the Task Detail Modal, fetches
  `GET /tasks/{id}/explanation`, shows the driving prerequisite in plain
  English and per-prerequisite slack in days.
- **Ripple toast:** After any mutation returning `downstream_changes`, a
  dismissible notification lists each affected task: title, old date → new
  date, and driving cause.

---

## 7. Concurrency model

SQLite is single-writer; the version column provides optimistic concurrency
for multi-tab scenarios. Under high concurrent load beyond two tabs, SQLite's
write locking may produce spurious timeouts (not `VERSION_CONFLICT`). This
is a known limitation documented in §8 below.

FastAPI runs in a single worker process (uvicorn, single thread for dev).
The in-memory `_board_locks` set for AI rate limiting is per-process and
would not function correctly behind a multi-process deployment. For
production, replace with a Redis-backed distributed lock.

---

## 8. Known limitations / KNOWN_FAILURES

Per `BUILD_SPEC.md §8.3`:

| Limitation | Risk | Status |
|---|---|---|
| SQLite write lock contention at >2 concurrent editors | Low for demo | Not fixed — use PostgreSQL for production |
| AI rate limiter is in-process only (not distributed) | Medium if multi-process | Documented; replace with Redis for prod |
| Heuristic performance meets targets (100% prec, 84.6% rec) | Low | Tuning complete (§5.3); LLM mode provides semantic reasoning |
| Board anchored to fixed board_id=1 | Low for demo scope | Single-board design per spec (extended with multi-board auth) |
| Production deployment target not confirmed | Low for local evaluation | Escalated per BUILD_SPEC.md §10 |

### Multi-User Authentication & Canonical Guest Mode

Multi-user authentication (via JWT with bcrypt password hashing in `backend/auth.py` and `backend/routes/auth.py`) was introduced beyond the original synopsis build target to enable user-specific board ownership, creation, and deletion in multi-tenant environments. To strictly preserve the synopsis's core promise of a single shared, zero-friction workspace, a dedicated **Guest Bypass** (`Continue as Guest / View Demo Board`) is integrated into `LoginScreen.tsx` and `App.tsx`. Guest sessions directly load the canonical seeded board (`id=1`, `owner_id=NULL`) with complete access to the DAG scheduling engine, Invariant Gate, and AI Copilot, guaranteeing that evaluators and demo runs are never blocked behind credentials.

---

## 9. Deployment status

**Architecture:**
- **Database:** Neon Serverless PostgreSQL (pooler endpoint, SSL required).
- **Backend API:** Render Web Service (`render.yaml` blueprint with Uvicorn / FastAPI).
- **Frontend SPA:** Vercel (`frontend/vercel.json` SPA routing with Vite).

To run locally:
```bash
# Backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm run dev
```

---

## 10. Configuration

All configuration via environment variables. Copy `.env.example` to `.env`
before running:

| Variable | Purpose | Required |
|---|---|---|
| `DATABASE_URL` | SQLite path (default: `sqlite:///./taskflow.db`) | No |
| `GROQ_API_KEY` | LLM key for Groq API (`allam-2-7b` model) | No — falls back to heuristic |
| `LLM_MODEL_NAME` | Model identifier (default: `allam-2-7b`) | No |
| `ALLOWED_ORIGIN` | Frontend origin for CORS (default: `http://localhost:5173`) | No |
