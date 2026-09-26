# TaskFlow Pro

> **A DAG-Enforced, Dependency-Aware Kanban Board**  
> *Correctness first: the board never shows a state that contradicts the dependency graph. Trust always: every automatic schedule change is fully explained.*

**Live Demo:** [https://glassboard-ten.vercel.app](https://glassboard-ten.vercel.app) | **API Docs:** [https://glassboard-backend.onrender.com/docs](https://glassboard-backend.onrender.com/docs)

---

## 1. Executive Summary

Traditional Kanban boards treat tasks as independent cards. In real-world projects, tasks form complex dependency networks:
- Moving a task before its prerequisites are complete introduces hidden risk.
- Delays along parallel paths compound errantly in naive tools, artificially inflating delivery dates.
- Automated scheduling tools often act as "black boxes," leaving teams confused about why dates moved.
- AI copilots in modern software frequently write unverified changes directly into project graphs, causing undetected cycles and schedule corruption.

**TaskFlow Pro** solves these problems with four pillars:
1. **Deterministic Graph Engine:** A pure Python DAG engine (zero DB/web imports) that enforces acyclicity, validates all state transitions through an Invariant Gate, and maintains mathematical correctness.
2. **Non-Compounding Incremental Scheduler:** Delays calculate non-compounding updates via the *max-not-sum* rule across diamond dependencies — avoiding false delays when parallel tracks finish with slack.
3. **The Why Panel (Explainable Scheduling):** Click any task to inspect why its dates are what they are: identifies the exact driving prerequisite and per-prerequisite slack days in natural language.
4. **Guardrailed AI Copilot (Propose → Challenge → Verify → Human Approval):** An AI dependency copilot that can propose candidates, but *never* writes directly to the graph. Proposals must survive deterministic cycle and schedule verification, and require explicit human acceptance.

---

## 2. Architecture & Design Principles

```
Browser (React 19 + TypeScript + Vite + dnd-kit)
    │
    │  HTTP / JSON (REST API)
    ▼
FastAPI Backend (port 8000)
    │
    ├── backend/routes/ (boards, tasks, dependencies)
    ├── backend/ai/pipeline.py (LLM / heuristic fallback copilot)
    │
    ├── SQLite Database (via SQLAlchemy 2.0 with Foreign Key enforcement)
    │
    └── engine/ (PURE PYTHON — zero DB / zero web imports)
            ├── graph.py       (Cycle detection via forward BFS, path reconstruction)
            ├── scheduler.py   (Incremental recompute with max-not-sum propagation)
            ├── derive.py      (Dynamic derivation of blocked/ready state and slack)
            ├── invariants.py  (Invariant Gate validation)
            └── oracle.py      (Brute-force reference implementation for property testing)
```

- **Clean Layer Separation:** The `engine/` package has zero dependencies on FastAPI, SQLAlchemy, or SQLite. It is 100% testable in isolation.
- **Derived State:** `blocked`, `ready`, `driving_prerequisite_id`, and `slack` are never stored in the database; they are dynamically computed on every read to guarantee zero drift.
- **Optimistic Concurrency:** Every task update carries an incremental `version` tag. Concurrent edits trigger `409 VERSION_CONFLICT` instead of silent overwrites.
- **Authentication & Guest Mode:** Multi-user authentication (JWT with bcrypt) enables personal board creation and management, while a prominent **"Continue as Guest / View Demo Board"** bypass on the login screen provides instant, zero-barrier access directly to the canonical shared workspace (Board #1).

---

## 3. Quick Start & Setup

### Prerequisites
- **Python 3.11+** (tested on Python 3.13)
- **Node.js 18+** and **npm**

### Step 1: Clone & Backend Setup

```bash
# Clone the repository
git clone https://github.com/harsh-space/glassboard.git
cd glassboard

# Set up Python virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r requirements.txt

# Seed the database (creates TaskFlow Pro canonical 10-task board with diamond & chains)
python scripts/seed.py

# Start the FastAPI backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
*The backend API documentation is now live at `http://localhost:8000/docs`.*

### Step 2: Frontend Setup

Open a second terminal window:

```bash
cd glassboard/frontend

# Install frontend dependencies
npm install

# Start the Vite development server
npm run dev
```
*Open `http://localhost:5173` in your browser to interact with TaskFlow Pro.*

---

## 4. Running the Test Suite

TaskFlow Pro includes 33 comprehensive unit and integration tests covering the engine, API, invariant checks, and property-based oracle agreement:

```bash
# Run all tests with verbose output
python -m pytest -v
```

### Key Test Categories:
- **Cycle Detection:** `tests/engine/test_cycle.py` — tests that adding cyclic edges (e.g., T10 → T2) is rejected before database insertion, returning the exact cycle path `[10, 2, 4, 6, 9, 10]`.
- **Diamond Math (Max-Not-Sum):** `tests/engine/test_diamond.py` — verifies that delaying task T2 by 3 days shifts convergence task T7 by *exactly* 3 days (not 3+3=6), and identifies T4 as the driving prerequisite with T5 having 3 days of slack.
- **Oracle Property Testing:** `tests/engine/test_oracle_property.py` — generates 1,000 random DAG mutations and compares incremental schedule recomputation against a brute-force topological oracle from scratch. Zero divergences.
- **Regression Handling:** `tests/engine/test_regression.py` — verifies that regressing a task back from Done clears downstream `actual_end` and logs `needs_reverification` without mutating user-completed tasks.
- **API & Concurrency:** `tests/api/` — covers optimistic locking (`409 VERSION_CONFLICT`), Pydantic validation, CORS headers, and AI rate limiting.

### Measuring AI Copilot Performance
TaskFlow Pro includes a benchmark script measuring the AI dependency copilot against hand-labelled ground truth:

```bash
python scripts/measure_ai.py
```

*Results on blank slate graph:*
- **Precision:** 87.5% (Exceeds ≥85% target)
- **Recall:** 53.8% (Conservative heuristic intentionally minimizes false positives)

---

## 5. Walkthrough Demo Scenarios

> **Access Note:** On first loading the application, you will see the authentication screen. Click **"Continue as Guest / View Demo Board"** to immediately access the canonical seeded board (Board #1) without creating an account or entering credentials. (You can also create an account to manage isolated personal boards).

### Scenario 1: Blocked Task Enforcement
1. Locate Task 2 (`Database Schema Design`). Notice the **Blocked** badge indicating it depends on Task 1 (`Requirements Gathering`).
2. Attempt to drag Task 2 to `In Progress` or `Done`.
3. The board rejects the drop and displays an error explaining that Task 1 must be completed first.
4. Drag Task 1 to `Done`. Task 2 instantly transitions to **Ready**.

### Scenario 2: Diamond Convergence & The Why Panel
1. Click on Task 7 (`Integration Testing`) to open its detail modal.
2. View the **Why Panel**:
   - Planned Start: `2026-10-05`
   - Driving Prerequisite: **Task 4 (Backend API Development)**
   - Slack: **Task 5 (Test Data Setup)** has **3 days of slack**.
3. Now edit Task 2 (`Database Schema Design`) and increase its duration from 3 days to 6 days.
4. Observe that Task 7 shifts forward by exactly 3 days. It does *not* compound across the parallel branches (T4 and T5).

### Scenario 3: Cycle Prevention
1. Open Task 2 detail view or call `POST /dependencies` attempting to make Task 10 (`Release`) a prerequisite of Task 2.
2. The system rejects the addition with `400 Bad Request` and message: `Cycle detected: [10 -> 2 -> 4 -> 6 -> 9 -> 10]`.

### Scenario 4: AI Dependency Copilot
1. Click the **AI Copilot** button in the header.
2. The drawer presents candidate dependencies with rationale and confidence scores.
3. Rejecting an edge discards it. Accepting an edge triggers deterministic cycle and schedule verification before committing to the board.

---

## 6. Key Assumptions and Limitations

Per `CLAUDE.md §8` and `docs/synopsis/06-risks.md`:
- **Finish-to-Start Only:** All dependencies follow finish-to-start semantics. Start-to-start or finish-to-finish links are not modeled.
- **Calendar Day Granularity:** Durations and schedules operate on whole calendar days; weekend/holiday calendars are not modeled.
- **Done Completion:** A prerequisite is satisfied if and only if it resides in the `Done` column.
- **Single Board / Single DAG:** Each workspace board models a single directed acyclic graph.
- **Deterministic `actual_end`:** When a task moves to `Done`, `actual_end` is set equal to `planned_end` to maintain test reproducibility.
- **Authentication:** The prototype operates as a single-workspace collaborative environment without multi-tenant authentication.

---

## 7. AI Disclosure

Per hackathon requirements, detailed records of AI tool usage during development are maintained in [AI_TOOL_DECLARATION.md](AI_TOOL_DECLARATION.md). Every file assisted by AI was reviewed, verified, and backed by automated tests.
