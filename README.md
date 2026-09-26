# TaskFlow Pro

> **A DAG-Enforced, Dependency-Aware Kanban Board**  
> *Correctness first: the board never shows a state that contradicts the dependency graph. Trust always: every automatic schedule change is fully explained.*

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-black?style=flat&logo=vercel)](https://glassboard-ten.vercel.app)
[![API Docs](https://img.shields.io/badge/API%20Docs-FastAPI%20%2F%20Render-blue?style=flat&logo=fastapi)](https://glassboard-backend.onrender.com/docs)
[![Test Suite](https://img.shields.io/badge/Test%20Suite-47%20Passed-success?style=flat&logo=pytest)](docs/PROGRESS.md)
[![AI Guardrails](https://img.shields.io/badge/AI%20Precision-100%25-green?style=flat)](docs/ARCHITECTURE.md#53-heuristic-performance-measured-by-scriptsmeasure_aipy)

**Live Production App:** [https://glassboard-ten.vercel.app](https://glassboard-ten.vercel.app)  
**Live API Documentation:** [https://glassboard-backend.onrender.com/docs](https://glassboard-backend.onrender.com/docs)  
**Submission Branch:** `my_sub`  

---

## 📑 Repository & Documentation Navigation

For hackathon judges and evaluators, all primary documentation is organized and cross-referenced below:

| Document | Purpose | Evaluation Mapping |
| :--- | :--- | :--- |
| **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** | Mandatory design doc detailing real architecture, mathematical proofs, Invariant Gate, and known limitations. | **Code Quality & Architecture (20%)** |
| **[AI_TOOL_DECLARATION.md](AI_TOOL_DECLARATION.md)** | Transparent, running log of AI coding assistant contributions and validation. | **AI/LLM Usage Disclosure (15%)** |
| **[docs/PROGRESS.md](docs/PROGRESS.md)** | Complete 9-phase progress log, milestone deliverables, and automated test matrix. | **Functional Correctness (20%)** |
| **[docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)** | 5-minute step-by-step evaluator script demonstrating core capabilities. | **Documentation & Explainability (13%)** |
| **[docs/TESTING_SCENARIOS.md](docs/TESTING_SCENARIOS.md)** | 9 interactive UI/UX and API edge-case verification scenarios. | **Testing & Reliability (10%)** |
| **[docs/synopsis/](docs/synopsis/)** | Frozen verbatim text of original hackathon synopsis sections (01 to 06). | **Baseline Problem & Scope Specification** |

---

## 1. Executive Summary

Traditional Kanban boards treat tasks as independent cards. In real-world projects, tasks form complex dependency networks:
- Moving a task before its prerequisites are complete introduces hidden risk and project failure.
- Delays along parallel tracks compound errantly in naive tools, artificially inflating delivery dates.
- Automated scheduling tools act as "black boxes," leaving teams confused about why dates moved.
- AI copilots in modern software frequently hallucinate and write unverified changes directly into graphs, causing undetected cycles.

**TaskFlow Pro** solves these challenges with five core pillars:
1. **Deterministic Graph Engine:** Pure Python DAG engine with **zero database and zero web-framework imports**. Enforces strict acyclicity, validates all state transitions through an Invariant Gate, and maintains mathematical correctness.
2. **Non-Compounding Incremental Scheduler:** Delays calculate non-compounding updates via the **max-not-sum** rule across diamond dependencies — avoiding false compounding when parallel tracks finish with slack.
3. **The Why Panel (Explainable Scheduling):** Click any task to inspect why its dates are what they are: identifies the exact driving prerequisite and per-prerequisite slack days in natural language.
4. **Guardrailed AI Copilot (Propose → Challenge → Verify → Human Approval):** An AI dependency copilot that can propose candidates, but **never** writes directly to the graph. Proposals must survive strict prerequisite substring checks, cycle detection, and require explicit human acceptance.
5. **Dual-Layer Authorization with Instant Guest Bypass:** The canonical shared workspace (`board_id=1`) has a prominent **"Continue as Guest / View Demo Board"** bypass so evaluators are never blocked behind credentials, while private tenant boards strictly enforce JWT ownership across all data endpoints.

---

## 2. Architecture & Layer Separation

```
Browser (React 19 + TypeScript + Vite + dnd-kit)
    │
    │  HTTP / JSON (REST API with Bearer JWT)
    ▼
FastAPI Backend (port 8000)
    │
    ├── backend/routes/ (boards, tasks, dependencies, auth)
    ├── backend/auth.py (JWT utilities, require_board_access authorization helper)
    ├── backend/ai/pipeline.py (Groq allam-2-7b + heuristic fallback copilot)
    │
    ├── SQLite / PostgreSQL Database (Neon Serverless, SQLAlchemy 2.0)
    │
    └── engine/ (PURE PYTHON — ZERO DB / ZERO WEB IMPORTS)
            ├── graph.py       (Cycle detection via forward BFS, path reconstruction)
            ├── scheduler.py   (Incremental recompute with max-not-sum propagation)
            ├── derive.py      (Dynamic derivation of blocked/ready state and slack)
            ├── invariants.py  (Invariant Gate validation)
            └── oracle.py      (Brute-force reference implementation for property testing)
```

- **Pure Engine Isolation:** The `engine/` package has zero imports from FastAPI, SQLAlchemy, or SQLite. It is 100% testable in isolation.
- **Derived State:** `blocked`, `ready`, `driving_prerequisite_id`, and `slack` are never stored in the database; they are dynamically computed on every read to guarantee zero state drift.
- **Optimistic Concurrency:** Every task update carries an incremental `version` tag. Concurrent edits trigger `409 VERSION_CONFLICT` instead of silent overwrites.

---

## 3. Quick Start & Setup

### Prerequisites
- **Python 3.11+** (tested on Python 3.13)
- **Node.js 18+** and **npm**

### Step 1: Clone & Backend Setup

```bash
# Clone the repository and switch to submission branch
git clone https://github.com/harsh-space/glassboard.git
cd glassboard
git checkout my_sub

# Set up Python virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env and ensure JWT_SECRET_KEY is populated

# Seed the database (creates TaskFlow Pro canonical 10-task board with diamond & chains)
python scripts/seed.py

# Start the FastAPI backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
*API documentation is live at `http://localhost:8000/docs`.*

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

## 4. Running the Test Suite (47 Passing Tests)

TaskFlow Pro includes 47 comprehensive automated tests across the engine, API, invariant checks, authorization, and AI guardrails:

```bash
# Run all tests with verbose output
python -m pytest -v
```

### Test Breakdown:
- **15 Engine Tests (`tests/engine/`):** Pure DAG cycle detection (BFS), diamond math (max-not-sum), regression rollback, Invariant Gate assertions, and a **1,000 random-graph oracle property test**.
- **20 API & Integration Tests (`tests/api/`):** Board retrieval, optimistic concurrency version conflict (`409`), drag-and-drop blocked rejection, Why Panel explanations, impact preview dry-run, CORS headers, and rate limiting.
- **8 Authorization Tests (`tests/api/test_authorization.py`):** Public guest bypass (`board_id=1`), 401 unauthenticated access rejection on private boards, 403 cross-tenant isolation, and owner access.
- **4 AI Pipeline Tests (`tests/ai/test_evidence_check.py`):** Hallucinated evidence rejection, strict prerequisite substring matching, and audit trail recording (`action='ai_suggestion_evidence_rejected'`).

### Measuring AI Copilot Performance
TaskFlow Pro includes an offline evaluation script measuring the AI dependency copilot against hand-labelled ground truth:

```bash
python scripts/measure_ai.py
```

*Results on blank-slate canonical board:*
- **Precision:** **100.0%** (Exceeds ≥85% target)
- **Recall:** **84.6%** (Exceeds ≥70% target)
- **F1 Score:** **91.7%**
- **Acceptance Rate:** **100.0%**

---

## 5. Walkthrough Demo Scenarios

> **Evaluator Quick Access:** When opening the application, click **"Continue as Guest / View Demo Board"** to immediately access the canonical seeded board (Board #1) with zero authentication friction. Evaluators may also register an account to test multi-tenant board creation.

### Scenario 1: Blocked Task Enforcement
1. Locate Task 2 (`Database Schema Design`). Notice the amber **Blocked** chip and subtitle: `Needs: Requirements Gathering`.
2. Attempt to drag Task 2 into `In Progress` or `Done`.
3. The board rejects the move, snaps the card back, and displays an explanation banner.
4. Drag Task 1 (`Requirements Gathering`) to `Done`. Task 2 instantly transitions to **Ready**.

### Scenario 2: Diamond Math & The Why Panel (+3 Days, Not +6)
1. Click on Task 7 (`Integration Testing`) to open its detail modal.
2. View the **Why Panel**:
   - Planned Start: `2026-10-05`
   - Driving Prerequisite: **Task 4 (Backend API Development)**
   - Slack: **Task 5 (Test Data Setup)** has **3 days of slack**.
3. Edit Task 2 (`Database Schema Design`) and increase its duration from 3 days to 6 days (+3 days).
4. Notice the **Ripple Toast** alerting that downstream tasks rescheduled.
5. Re-open Task 7: Planned start moved by *exactly* 3 days (to `2026-10-08`), proving that parallel paths (T4 and T5) did not compound errantly.

### Scenario 3: Real-Time Cycle Detection & Prevention
1. Open Task 2 detail view. Under **Add Prerequisite**, select **Task 10 (Release)** and click Add.
2. The system rejects the addition with `400 Bad Request` and exact path: `Cycle detected: [10 -> 2 -> 4 -> 6 -> 9 -> 10]`.
3. Zero database mutation occurs.

### Scenario 4: Guardrailed AI Dependency Copilot
1. Click the **AI Copilot** button in the header to open the suggestions drawer.
2. View candidate suggestions with rationale, confidence scores, and challenge badges.
3. Rejecting an edge discards it and records the rejection in `audit_log`. Accepting an edge runs through cycle detection and the Invariant Gate before committing.

### Scenario 5: Backward Regression Handling
1. Drag Task 1 (`Requirements Gathering`) backwards from `Done` to `In Progress`.
2. Downstream dependent tasks (Task 2, Task 3) immediately update back to **Blocked**.
3. An audit log event records `needs_reverification` without destructively corrupting task data.

For a comprehensive testing guide, see **[docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)** and **[docs/TESTING_SCENARIOS.md](docs/TESTING_SCENARIOS.md)**.

---

## 6. Key Assumptions and Design Constraints

Per `docs/synopsis/06-risks.md` and `docs/ARCHITECTURE.md`:
- **Finish-to-Start Only:** All dependencies follow finish-to-start semantics.
- **Calendar Day Granularity:** Durations and schedules operate on whole calendar days.
- **Done Completion:** A prerequisite is satisfied if and only if it resides in the `Done` column.
- **Single DAG per Board:** Each board models a single directed acyclic graph.
- **Deterministic `actual_end`:** When a task moves to `Done`, `actual_end` is set equal to `planned_end` to guarantee test reproducibility.
- **Multi-User Authentication with Guest Bypass:** Multi-tenant accounts isolate custom user boards, while the canonical shared demo board (`owner_id = NULL`) remains open for zero-friction evaluation.

---

## 7. AI Disclosure

Per hackathon requirements, comprehensive records of AI tool usage during development are maintained in **[AI_TOOL_DECLARATION.md](AI_TOOL_DECLARATION.md)**. Every file assisted by AI was reviewed, verified, and backed by automated tests.
