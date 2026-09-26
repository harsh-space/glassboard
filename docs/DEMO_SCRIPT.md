# TaskFlow Pro — Hackathon Demo Script

> **A 5-minute live demonstration script for hackathon judges and evaluators.**  
> Covers: 1. Blocked / Ready enforcement, 2. The Why Panel & diamond math (+3 not +6), 3. Cycle prevention, 4. AI Copilot (Propose → Verify → Human approval), 5. Regression & rollback.

---

## Preparation (30 seconds before demo)

1. Ensure the backend and frontend are running:
   ```bash
   # Terminal 1: Backend
   python scripts/seed.py
   uvicorn backend.main:app --host 0.0.0.0 --port 8000

   # Terminal 2: Frontend
   cd frontend && npm run dev
   ```
2. Open browser to `http://localhost:5173`.
3. On the login screen, click **"Continue as Guest / View Demo Board"** to land directly on the canonical 10-task board (no credentials required for evaluators).
4. Have the browser console or network tab visible if desired.

---

## Step 1: Blocked vs Ready Enforcement (60 seconds)

### Talking Point:
> *"Traditional Kanban boards let you drag cards anywhere, even if the work physically cannot start. TaskFlow Pro treats dependencies as mathematical constraints."*

### Actions:
1. Point to **Task 1 ("Requirements Gathering")**:
   - Notice the green **Ready** chip. It has no prerequisites and is ready to work on.
2. Point to **Task 2 ("Database Schema Design")**:
   - Notice the amber **Blocked** chip and the helper tag: `Needs: Requirements Gathering`.
3. Try dragging **Task 2** directly into **In Progress** or **Done**:
   - **Result:** The card snaps back, and an error banner alerts: `"Cannot move blocked task: prerequisites incomplete"`.
4. Now drag **Task 1 ("Requirements Gathering")** to **Done**:
   - **Result:** Immediately, Task 2 changes from **Blocked** to **Ready**!
   - Its dependency is satisfied, so it can now be moved into In Progress.

---

## Step 2: The Why Panel & Diamond Math (+3, not +6) (90 seconds)

### Talking Point:
> *"When a schedule slips, project managers want to know why. And when multiple parallel paths lead to one milestone, delays shouldn't compound errantly. TaskFlow Pro implements the non-compounding max-not-sum rule."*

### Actions:
1. Click on **Task 7 ("Integration Testing")** to open its detail modal.
2. Direct the judge's attention to the **Why Panel**:
   - **Planned Start:** `2026-10-05`
   - **Driving Prerequisite:** `Task 4 (Backend API Development)`
   - **Slack:** `Task 5 (Test Data Setup)` has **3 days of slack**.
   - Explain: *"Task 7 depends on both Task 4 (duration 5 days) and Task 5 (duration 2 days), which both branched from Task 2. Task 4 finishes on Oct 05, while Task 5 finishes on Oct 02. Task 4 is the driver; Task 5 has 3 days of buffer."*
3. Close the modal. Click on **Task 2 ("Database Schema Design")**.
4. Increase its duration from **3 days to 6 days** (+3 days delay) and save.
5. Notice the **Ripple Toast**:
   - Alerts that downstream tasks (Tasks 4, 5, 6, 7, 8, 9, 10) have been rescheduled.
6. Re-open **Task 7 ("Integration Testing")**:
   - Notice the new Planned Start: `2026-10-08`.
   - **The math:** Delay of 3 days at Task 2 moved Task 7 by *exactly* 3 days (not 3 + 3 = 6 days across both branches).
   - The Why Panel continues to show Task 4 as the driver and Task 5 with 3 days of slack.

---

## Step 3: Immediate Cycle Detection & Prevention (60 seconds)

### Talking Point:
> *"Cycles in dependency graphs freeze automated systems and break topological ordering. TaskFlow Pro detects cycles in pure Python using forward BFS before any write touches the database."*

### Actions:
1. Open **Task 2 ("Database Schema Design")** detail modal.
2. Scroll to the **Add Prerequisite** dropdown.
3. Select **Task 10 ("Release")** as a prerequisite for Task 2 and click **Add**.
4. **Result:** The system immediately blocks the addition with a clear error:
   ```
   Cycle detected: [10 -> 2 -> 4 -> 6 -> 9 -> 10]
   ```
5. Explain: *"Task 10 depends on Task 9, which depends on Task 6, which depends on Task 4, which depends on Task 2. Adding Task 10 as a prerequisite to Task 2 would create a circular dependency. The graph engine detected and rejected it with zero database mutation."*

---

## Step 4: Guardrailed AI Dependency Copilot (60 seconds)

### Talking Point:
> *"Unlike tools that let LLMs write directly to the project database, TaskFlow Pro uses a Propose → Challenge → Verify → Human Approval pipeline."*

### Actions:
1. In the top navigation bar, click the **AI Copilot** button.
2. The **AI Suggestions Drawer** slides open.
3. Show the suggested dependencies:
   - Each suggestion provides a candidate link (e.g. `Prerequisite -> Dependent`), a confidence score, and a clear architectural rationale.
   - Point out the **Heuristic / Skeptic Challenge Badge**.
4. Click **Accept** on a valid proposal:
   - The edge runs through the Invariant Gate and cycle detector, then safely attaches to the board.
5. Click **Reject** on another proposal:
   - The proposal is discarded and recorded as rejected in the audit log.

---

## Step 5: Regression & Safe Rollback (30 seconds)

### Talking Point:
> *"What happens if a completed task turns out to need rework? In naive systems, moving a Done task backwards corrupts completed history."*

### Actions:
1. Drag **Task 1 ("Requirements Gathering")** backwards from **Done** to **In Progress**.
2. Notice the result:
   - Downstream dependent tasks (Task 2, Task 3) immediately update to **Blocked**.
   - The system audit log records `needs_reverification` for downstream items without destructively wiping out user progress or crashing.

---

## Summary Wrap-Up (15 seconds)

> *"TaskFlow Pro delivers mathematical correctness through our isolated graph engine, non-compounding scheduling, complete explainability through the Why Panel, and responsible AI that respects human authority."*
