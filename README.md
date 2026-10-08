# TaskFlow Pro ![Hackathon Project](https://img.shields.io/badge/type-Hackathon%20Project-orange)
## A Dependency-Aware Execution Engine for Project Kanban Boards, with Non-Compounding Scheduling and a Guardrailed AI Copilot

**Live Demo Links:**
- **App:** [glassboard-umber.vercel.app](https://glassboard-umber.vercel.app) — click **"Continue as Guest / View Demo Board"** for zero-friction access to the canonical seeded board.
- **API Docs:** [glassboard-backend.onrender.com/docs](https://glassboard-backend.onrender.com/docs) — interactive Swagger UI for the live deployment.
- **Submission branch:** `main`
  
**Demo Video:** [Demo](https://github.com/user-attachments/assets/8f78c0bb-90a5-476c-9a0e-6fc19634090c)

---

> A Kanban board shows which column a card sits in. TaskFlow Pro decides which column a card is *allowed* to sit in, computes when it can start from first principles instead of a human typing a date, and explains every date it produces well enough that a project manager doesn't have to take it on faith.

---

## Executive Summary

Ordinary Kanban tools treat cards as independent objects: a person drags a card, a person types a due date, and nothing in the tool notices when those two facts contradict each other. Real engineering work isn't independent — it's a network of prerequisites, and when one task slips, every task downstream of it should slip too, by the correct amount, automatically.

**TaskFlow Pro** is a Kanban board where the board is only the interface. Underneath it is a deterministic, dependency-aware execution engine that decides what's ready, what's blocked, and what moves when something changes. The system is built around five pillars:

1. **A pure-Python DAG engine** as the single source of truth for scheduling — no database or web-framework code anywhere near it, so it can be tested in total isolation.
2. **Non-compounding incremental scheduling.** When two parallel chains converge on one task, a delay upstream is applied once, via whichever chain is actually driving the date — never summed across both chains.
3. **The Why Panel**, which turns every automatically-computed date into a plain-English explanation instead of a black box.
4. **A guardrailed AI dependency copilot** that can propose links between tasks but can never write one to the graph — every suggestion passes through a skeptic pass, deterministic verification, and a human decision before it becomes real.
5. **Board-level authorization** with a zero-friction guest path: the canonical shared board is open to any evaluator instantly, while a JWT-authenticated layer on top lets registered users own private boards.

The full reasoning behind these five pillars — including the original failure modes they were designed against — is written up in [`docs/synopsis/01-problem.md`](docs/synopsis/01-problem.md) and [`docs/synopsis/02-solution.md`](docs/synopsis/02-solution.md), the frozen text of the original problem statement and design.

---

## The Problem

A dependency graph fails silently in a handful of specific, recurring ways, and TaskFlow Pro is designed against each of them directly:

- **Converging paths.** If task A feeds both task B and task C, and both B and C feed task D, a 3-day delay in A must move D by 3 days — not 6. Naively propagating a delay down every path and summing the effect at the convergence point is a classic scheduling bug, and it gets worse the deeper the graph.
- **Derived state going stale.** "Blocked" and "Ready" are facts about the graph, not facts you can store in a column. The instant a prerequisite changes, a stored Blocked/Ready flag is wrong until something remembers to recompute it — so TaskFlow Pro never stores it at all.
- **Cycles.** A → B → C → A must be rejected before anything touches the database, with a message that names the loop, not a generic error.
- **Regression.** Moving a completed task backwards into "In Progress" has to re-block every downstream task that depended on it being done — at every level, not just the immediate neighbor.
- **Invalid state transitions.** Dragging a Blocked card into "In Progress" is a state transition that violates the dependency model, and rejecting it has to happen in the engine, not just as a UI nicety that a direct API call could bypass.
- **Trust in automation.** A date that moved for reasons nobody can see gets overridden by hand the first time it's wrong, which defeats the point of automating it. Every automatic move needs a visible cause.
- **AI trust.** A language model asked to suggest dependencies can invent connections or get the direction backwards. A suggestion has to stay a proposal — checked deterministically and approved by a human — until it's a real dependency.
- **Concurrent edits.** Two people editing the same task from two tabs must not silently overwrite each other; a stale write needs to fail loudly, not quietly lose data.

These are elaborated with worked examples in [`docs/synopsis/01-problem.md`](docs/synopsis/01-problem.md).

---

## Key Features & Contributions

- **Deterministic DAG engine** (`engine/`) — cycle detection, incremental scheduling, Blocked/Ready derivation, and regression handling, implemented with zero imports from the database or web layer.
- **Max-not-sum scheduling** — a task's start date is the *maximum* of its prerequisites' finish dates, computed once per task in topological order, so parallel convergences never compound a delay.
- **The Invariant Gate** — a set of cheap assertions (graph still acyclic, no task starting before a prerequisite finishes, no Blocked task advanced) that runs immediately before every commit and aborts the transaction if anything is inconsistent.
- **The Why Panel** — click any task to see its driving prerequisite and the slack (in days) held by every other prerequisite, in a plain sentence rather than a raw timestamp diff.
- **Ripple view** — after any change that moves other tasks, a toast lists exactly which tasks moved, their old and new dates, and what caused the move.
- **Guardrailed AI copilot** — a Propose → Challenge → Verify → Human pipeline (detailed below) that proposes dependency links from task text but never writes one without a person accepting it.
- **Critical path highlighting and impact-preview dry runs** — see the longest chain by duration, or preview what a hypothetical duration change would move before committing to it.
- **Optimistic concurrency control** — every task carries a version number; a stale write is rejected with `409 VERSION_CONFLICT` instead of silently overwriting a newer edit.
- **Guest-bypass authentication** — a canonical shared board is open to anyone with no login, while JWT-authenticated accounts can own private boards on the same instance.

---

## System Architecture

TaskFlow Pro is structured as a layered pipeline so that the part responsible for correctness (the engine) never depends on the parts responsible for delivery (the API, the database, the AI provider). The data model — five core tables plus the `user` table added for authentication — the security posture (input validation, parameterized queries, CORS scope, and how the LLM key is kept server-side), and the concurrency assumptions behind it are all locked in during design and recorded in [`docs/synopsis/03-data.md`](docs/synopsis/03-data.md).

<div align="center">

<table width="100%" style="text-align: center; border-collapse: collapse;">
  <thead>
    <tr style="border-bottom: 2px solid #ccc; background-color: rgba(255, 255, 255, 0.03);">
      <th style="padding: 12px;">Layer</th>
      <th style="padding: 12px;">Primary Components</th>
      <th style="padding: 12px;">Responsibilities</th>
    </tr>
  </thead>
  <tbody>
    <tr style="border-bottom: 1px solid #ddd;">
      <td style="padding: 12px;"><b>1. Engine</b></td>
      <td style="padding: 12px;"><code>engine/graph.py</code>, <code>scheduler.py</code>, <code>derive.py</code>, <code>invariants.py</code>, <code>oracle.py</code></td>
      <td style="padding: 12px;">Pure Python. Cycle detection, incremental max-not-sum scheduling, Blocked/Ready derivation, regression handling, and the pre-commit Invariant Gate. Zero database or web-framework imports — importable and testable with nothing running.</td>
    </tr>
    <tr style="border-bottom: 1px solid #ddd;">
      <td style="padding: 12px;"><b>2. API & Persistence</b></td>
      <td style="padding: 12px;"><code>backend/main.py</code>, <code>routes/</code>, <code>models.py</code>, <code>auth.py</code></td>
      <td style="padding: 12px;">FastAPI application, SQLAlchemy models, request validation, uniform error formatting, board-level authorization, and the transaction that wraps every mutation: validate → apply → recompute → check invariants → commit.</td>
    </tr>
    <tr style="border-bottom: 1px solid #ddd;">
      <td style="padding: 12px;"><b>3. AI Copilot</b></td>
      <td style="padding: 12px;"><code>backend/ai/pipeline.py</code></td>
      <td style="padding: 12px;">Propose/Challenge calls to an LLM provider, deterministic verification against the engine's own cycle check, and a keyword-heuristic fallback when no LLM key is configured.</td>
    </tr>
    <tr style="border-bottom: 1px solid #ddd;">
      <td style="padding: 12px;"><b>4. Frontend</b></td>
      <td style="padding: 12px;"><code>frontend/src/</code> (React, TypeScript, dnd-kit)</td>
      <td style="padding: 12px;">The Kanban board, drag-and-drop, the Why Panel, the AI suggestions drawer, and optimistic updates with rollback on error.</td>
    </tr>
  </tbody>
</table>

</div>

```
Browser (React + TypeScript + Vite + dnd-kit)
    │
    │  HTTP / JSON (REST, Bearer JWT on private boards)
    ▼
FastAPI Backend
    │
    ├── backend/routes/  (boards, tasks, dependencies, auth)
    ├── backend/auth.py  (JWT issuance, bcrypt hashing, board-level access control)
    ├── backend/ai/pipeline.py  (LLM copilot + heuristic fallback)
    │
    ├── SQLite (local dev) / Neon PostgreSQL (deployed), via SQLAlchemy
    │
    └── engine/  — PURE PYTHON, ZERO DB / WEB IMPORTS
            ├── graph.py       cycle detection via forward BFS, path reconstruction
            ├── scheduler.py   incremental recompute, max-not-sum propagation
            ├── derive.py      Blocked/Ready derivation, regression handling
            ├── invariants.py  the Invariant Gate
            └── oracle.py      brute-force reference scheduler (tests only)
```

The engine's isolation is deliberate and enforced, not just described: `engine/` has no import of `fastapi`, `sqlalchemy`, or anything from `backend/`, which means the highest-risk logic in the whole system — the scheduling math — can be property-tested against thousands of randomly generated graphs with no server or database involved at all (see [Testing & Verification](#testing--verification) below). The full architectural rationale, every data-model decision, and the reasoning behind each deviation from the original plan is written up in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), and the original implementation spec it was built against is [`BUILD_SPEC.md`](BUILD_SPEC.md).

---

## Engine Intelligence: Algorithms & Guarantees

### 1. Cycle Detection

A dependency row means "the prerequisite must finish before the dependent starts" — think of it as a directed edge `prerequisite → dependent`. To check whether a *proposed* edge `P → T` would create a cycle, the engine runs a breadth-first search forward from `T`, following existing edges, looking for a path back to `P`:

```
would_create_cycle(P, T):
    if P is reachable from T by following existing edges,
    then adding P → T would close a loop T → ... → P → T.
```

If a cycle would form, the API rejects the write with `HTTP 409 CYCLE_DETECTED` and returns the exact path that would close (e.g. `[10, 9, 6, 4, 2, 10]`), and nothing is written to the database — the check runs inside the same transaction as the insert, before it.

### 2. Max-Not-Sum Scheduling

For a task with prerequisites, the planned start date is:

$$\text{planned\_start}(t) = \max\Big(\{\text{finish}(p) : p \in \text{prerequisites}(t)\} \cup \{\text{pinned\_start}(t),\ \text{board.start\_date}\}\Big)$$

where `finish(p)` is `p`'s actual finish date if `p` is Done, or its currently planned end date otherwise. The task whose finish date produced the maximum is recorded as the **driving prerequisite**; every other prerequisite's **slack** is the difference between the driving finish date and its own:

$$\text{slack}(p) = \text{finish}(p_{\text{driving}}) - \text{finish}(p)$$

Because this is a `max()` taken once per task — not a sum, and not computed per-path — two parallel chains converging on the same task never compound a delay: whichever chain finishes later determines the date, and the other chain's difference becomes visible slack instead of invisible extra delay. Recomputation walks only the forward closure of a changed task, in topological order, so a single edit is `O(affected subgraph)`, not `O(entire board)`.

### 3. Blocked / Ready Derivation

```
is_ready(t)   = all(p.column == "done" for p in prerequisites(t))
is_blocked(t) = not is_ready(t)
```

These are never persisted — they're computed fresh from the live graph on every read, which is what guarantees they can never go stale. The "move task to column" endpoint enforces this at the transaction layer: an attempt to move a Blocked task into In Progress, Review, or Done is rejected with `409 TASK_BLOCKED` regardless of what the client sends, so the rule can't be bypassed by calling the API directly.

### 4. Regression Handling

When a task moves out of Done, its `actual_end` is cleared and the schedule is recomputed using its planned end date again. Every downstream task is re-derived automatically (since Blocked/Ready is always computed live), and any downstream task that was *already* Done gets flagged `needs_reverification` in the audit log — a human decides whether it actually needs rework, rather than the system silently un-completing it.

### 5. The Invariant Gate

Before any write commits, three cheap assertions run against the full graph: it's still acyclic, no task starts before any of its prerequisites finish, and no Blocked task is sitting in In Progress, Review, or Done. If any of these fire, the transaction aborts and the attempt is logged — this should never trigger in normal operation if the four algorithms above are implemented correctly; its only job is to catch a future regression before it reaches the database.

---

## Guardrailed AI Dependency Copilot

An LLM proposing project dependencies unsupervised is exactly the kind of thing that erodes trust the moment it's wrong once. TaskFlow Pro's copilot is built so that an LLM can never write to the graph directly — every suggestion goes through four stages before a person even sees it:

1. **Propose.** A single batched call gets the closed list of board tasks (ids, titles, descriptions only) and returns candidate `prerequisite → dependent` links with a rationale and an exact evidence quote from the dependent task's text. It must not infer a link from project lifecycle order or topical similarity alone. Temperature is set to zero, and returning nothing is a valid answer when no clear dependency exists.
2. **Challenge.** A second call judges each indexed pair as supplied and argues against it: is the direction reversed, is this only a topical connection rather than a true finish-to-start requirement, could the tasks run in parallel, and does the evidence support this exact pair? Only an explicit `survived` verdict is eligible.
3. **Verify (deterministic, no LLM).** Every survivor is checked in code: both task ids exist, the dependent matches the requested target when scoped, they're not the same task, the pair isn't already present or previously rejected, the evidence phrase is an exact substring of the dependent task's text, the confidence is finite and in range and clears the threshold, and — critically — the pair passes the same `would_create_cycle` check used everywhere else in the engine. The displayed reason is generated from the verified task IDs and titles rather than free-form model output. A suggestion that would create a cycle is dropped and logged; it's never shown to a person.
4. **Human.** What survives appears as a dashed "ghost" edge with its pair-grounded reason and evidence. The UI labels the source as "AI" or "Heuristic" and does not present the model's self-reported confidence as a calibrated percentage. Accepting a suggestion calls the exact same dependency-creation endpoint a manual link would use — there is no separate write path for AI-originated edges anywhere in the code.

If either LLM call times out, fails, or returns malformed or incomplete output, unverified LLM candidates are not passed through; the pipeline falls back to a deterministic keyword heuristic (ordered by delivery stage) so the feature keeps working without an API key. The provider used in the deployed instance is Groq, running `allam-2-7b`. `scripts/measure_ai.py` measures the heuristic fallback against the hand-labelled ground-truth set; mocked regression tests cover the LLM validation and failure paths. The exact heuristic precision/recall numbers are recorded in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#5-ai-pipeline). The original design for this pipeline — including why a human has to approve every link — is in [`docs/synopsis/04-ai.md`](docs/synopsis/04-ai.md).

---

## Authorization & Multi-Tenancy

TaskFlow Pro's canonical board is meant to be opened by anyone with zero friction — there's a **"Continue as Guest / View Demo Board"** option on the login screen that lands directly on the shared seeded board, no account required. Layered on top of that same instance is JWT-based authentication: a registered user can create private boards that only they can see. Authorization is enforced once, centrally, in a `require_board_access` check used by every route that touches board data (not just the auth-listing endpoints), with three outcomes: a board with no owner is public to anyone, a private board with no bearer token returns `401`, and a private board accessed by the wrong user returns `403`. Passwords are hashed with bcrypt; tokens are signed with a server-side secret that the application refuses to start without. The reasoning for adding this layer beyond the original single-workspace design — and how the guest board preserves that original design intact — is documented in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#8-known-limitations--known_failures).

---

## REST API Overview

All endpoints are mounted under `/api`. Every mutating endpoint runs inside one transaction: validate → apply → recompute → check invariants → commit, and every error response has the same shape: `{"error": {"code": ..., "message": ..., "details": {...}}}`.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/boards/{id}` | Full board: tasks with derived Blocked/Ready/slack fields, and dependencies |
| `GET` | `/boards/{id}/critical-path` | Longest chain through the graph by total duration |
| `POST` | `/tasks` | Create a task |
| `PATCH` | `/tasks/{id}` | Edit a task; must include its current `version` (optimistic concurrency) |
| `POST` | `/tasks/{id}/move` | Change a task's column and/or position; rejected if the task is Blocked |
| `DELETE` | `/tasks/{id}` | Delete a task; cascades its dependencies |
| `GET` | `/tasks/{id}/explanation` | Why Panel data: driving prerequisite, per-prerequisite slack, plain-language reason |
| `POST` | `/tasks/{id}/impact-preview` | Dry run: what would move if this task's duration or pinned start changed, without committing |
| `POST` | `/dependencies` | Create a dependency; rejected with the full cycle path if it would close a loop |
| `DELETE` | `/dependencies/{id}` | Remove a dependency |
| `GET` | `/dependencies/suggestions` | List pending AI-proposed dependencies for a board |
| `POST` | `/dependencies/suggestions` | Trigger the Propose → Challenge → Verify pipeline for one task or the whole board |
| `POST` | `/dependencies/suggestions/{id}/accept` | Accept a suggestion — goes through the same path as a manual `POST /dependencies` |
| `POST` | `/dependencies/suggestions/{id}/reject` | Reject a suggestion; excluded from future proposals on that board |
| `POST` | `/auth/register` | Create an account |
| `POST` | `/auth/login` | Exchange credentials for a JWT |
| `GET` | `/auth/me` | Current authenticated user |
| `PATCH` | `/auth/username` | Set a permanent username after registration |
| `GET` | `/auth/boards` | List boards owned by the current user |
| `POST` | `/auth/boards` | Create a new private board |
| `DELETE` | `/auth/boards/{id}` | Delete a board owned by the current user |

The interactive Swagger docs for the live deployment are at [glassboard-backend.onrender.com/docs](https://glassboard-backend.onrender.com/docs).

---

## Setup & Execution

### 1. Prerequisites
- **Python 3.11+** (tested on Python 3.13)
- **Node.js 18+** and **npm**

### 2. Clone & Backend Setup

```bash
# The repository is named glassboard from an earlier working name; the product is TaskFlow Pro
git clone https://github.com/harsh-space/glassboard.git
cd glassboard

python -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\Activate.ps1

pip install -r requirements.txt

cp .env.example .env
# Edit .env — JWT_SECRET_KEY is required, the app refuses to start without it.
# Optionally add GROQ_API_KEY to enable the live LLM copilot instead of the heuristic fallback.

python scripts/seed.py          # creates the canonical 10-task board with the diamond and chain

uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
API documentation is then live at `http://localhost:8000/docs`.

### 3. Frontend Setup

In a second terminal:

```bash
cd glassboard/frontend
npm install
npm run dev
```
Open `http://localhost:5173` and click **"Continue as Guest / View Demo Board"** to land directly on the seeded board with no login required.

### 4. Measuring the AI Copilot

```bash
python scripts/measure_ai.py
```
Runs the pipeline against the canonical board and reports true positives, false positives, false negatives, precision, recall, F1, and acceptance rate against a hand-labelled reference set (`tests/seed_dependency_labels.json`).

### 5. Measuring Scheduler Performance

```bash
python scripts/measure_performance.py
```
Benchmarks cycle detection, propagation, and the Invariant Gate against synthetic graphs of up to 1,000 tasks and 3,000 dependencies. Results and targets are recorded in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) (§3.5).

---

## Testing & Verification

```bash
python -m pytest -v
```

The suite covers four layers:

- **Engine tests** (`tests/engine/`) — pure DAG cycle rejection, the diamond-math case (a 3-day delay produces exactly a 3-day shift downstream, never 6), regression rollback, Invariant Gate assertions, and a property test comparing the incremental scheduler against a brute-force oracle across 1,000 randomly generated graphs.
- **API tests** (`tests/api/`) — board retrieval, full task/dependency CRUD, optimistic-concurrency version conflicts, blocked-drag rejection, Why Panel explanations, impact-preview dry runs, CORS headers, and uniform error formatting.
- **Authorization tests** (`tests/api/test_authorization.py`) — the public guest bypass, `401` on an unauthenticated private-board request, `403` on a cross-tenant request, and `200` for the actual owner.
- **AI pipeline tests** (`tests/ai/`) — evidence grounding against dependent-task text, task-pair/reason consistency, target-task enforcement, challenge-failure fallback, and audit-log recording of rejected evidence.

A full guided walkthrough of the running application — a 5-minute demo script followed by the complete manual test matrix, including authorization and concurrency scenarios — is in [`docs/TESTING_SCENARIOS.md`](docs/TESTING_SCENARIOS.md).

---

## Key Assumptions & Limitations

### Key Assumptions

The system design and execution engine operate under the following core assumptions:
- **Finish-to-start dependencies only:** All task dependencies are strictly finish-to-start (a dependent task cannot begin until all its direct prerequisites have reached the `done` column). Start-to-start, finish-to-finish, and lead/lag intervals are intentionally out of scope.
- **Whole-day durations & continuous calendar:** Task durations are whole positive integers (`duration_days > 0`). Calendar days are treated continuously without modeling weekends or regional holidays.
- **Single graph per board:** Each Kanban board represents a single dependency graph; unconstrained tasks anchor at the board's `start_date`.
- **Database architecture:** SQLite is assumed for local development, fast seed resets, and offline testing; managed PostgreSQL (Neon) is assumed for production deployments to avoid file-lock contention under concurrent load.
- **In-process AI rate limiting:** AI copilot proposal generation utilizes an in-memory lock per board for single-instance deployments, assuming external distributed locking (e.g. Redis) would be used for multi-process scaling.
- **Semantic text quality:** LLM proposals require a supporting quote from the dependent task's text and a positive challenge verdict. Sparse or vague task descriptions can therefore reduce suggestions; the model's review is still a probabilistic judgment, so every suggestion remains subject to human approval.

### Known Limitations

These are the practical boundaries of the system as shipped (see [`docs/synopsis/06-risks.md`](docs/synopsis/06-risks.md) and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#8-known-limitations--known_failures)):
- **SQLite under concurrent load:** Local development uses SQLite, which serializes writes; simultaneous editors can produce write-lock timeouts distinct from the intended `409 VERSION_CONFLICT` behavior. The deployed instance uses managed PostgreSQL (Neon) instead, which does not share this constraint.
- **AI rate limiting is in-process:** The one-suggestion-round-per-board limit is enforced with an in-memory lock, which is correct for a single server process but would need a distributed lock (e.g. Redis-backed) behind a multi-process deployment.
- **Finish-to-start dependencies only:** Whole-day durations, and calendar days with no weekends or holidays modeled — extending to other dependency types or a working-calendar model is a documented, deliberate scope boundary rather than an oversight.
- **Single graph per board:** Single graph per board is supported; AI suggestion quality depends on task titles and descriptions being descriptive enough to extract an evidence phrase from.
- **Large-graph tuning:** Boards beyond several thousand tasks have not been benchmarked; large-scale graphs with deep cyclic verification may require batch topological checks.

A full, itemized limitations list — including the reasoning behind each — is maintained in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#8-known-limitations--known_failures) as the project evolves. The exact schemas and algorithms this implementation follows are in [`BUILD_SPEC.md`](BUILD_SPEC.md), and a disclosed account of AI-assisted development is kept in [`AI_TOOL_DECLARATION.md`](AI_TOOL_DECLARATION.md).

---

## Conclusion

TaskFlow Pro treats "when can this start" as a question with a single correct, derivable answer rather than a field a person fills in — and treats "why did this move" as a question the system must always be able to answer. Isolating the scheduling math into a dependency-free engine made both of those guarantees independently testable, and building the AI copilot around a human-approval boundary rather than an autonomous write path let the project use an LLM for something genuinely useful (surfacing candidate dependencies from plain-text descriptions) without inheriting an LLM's failure modes in the one place — the dependency graph — where they'd be most damaging. The business case for automating this — how much manual re-editing a single upstream change saves, and the correctness and performance targets the engine is measured against — is laid out in [`docs/synopsis/05-impact.md`](docs/synopsis/05-impact.md), and every phase of the build described above, from the engine's first test through deployment, is checked off, with the current test and measurement results, in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#9-deployment-status).
