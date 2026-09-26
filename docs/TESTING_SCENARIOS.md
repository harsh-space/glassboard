# TaskFlow Pro — Interactive UI/UX & Functionality Testing Guide

Both local and production environments are live and ready for testing:
- **Live Production App:** [https://glassboard-ten.vercel.app](https://glassboard-ten.vercel.app)
- **Live Backend API Docs:** [https://glassboard-backend.onrender.com/docs](https://glassboard-backend.onrender.com/docs)
- **Local Dev Server:** [http://localhost:5173](http://localhost:5173) (API on `:8000`)
- **Database:** Seeded with the canonical 10-task, 13-dependency graph.

> **Access Note:** On first opening the app, you will land on the login screen. Click **"Continue as Guest / View Demo Board"** to immediately open the canonical shared workspace (Board #1) with zero login friction. (You may also register an account to create isolated personal boards).

---

## Scenario 1: Blocked vs. Ready Visual Enforcement & Drag-and-Drop Constraints

### Objective:
Verify that the Kanban board enforces mathematical dependency constraints visually and during drag-and-drop actions.

### Steps:
1. Open [http://localhost:5173](http://localhost:5173).
2. Look at **Task 1 ("Requirements Gathering")**:
   - **Expected UI:** Displays a green **Ready** badge. It has no prerequisites.
3. Look at **Task 2 ("Database Schema Design")**:
   - **Expected UI:** Displays an amber **Blocked** badge and a subtitle: `Needs: Requirements Gathering`.
4. Attempt to drag **Task 2** from `Backlog` into `In Progress` or `Done`:
   - **Expected Behavior:** The drag operation is rejected; the card snaps back to `Backlog`, and an error notification alerts: *"Cannot move blocked task: prerequisites incomplete"*.
5. Drag **Task 1** from `Backlog` into `Done`:
   - **Expected Behavior:** **Task 2** automatically switches its badge from **Blocked** to **Ready** in real-time. It can now be dragged to `In Progress`.

---

## Scenario 2: Diamond Math & The Why Panel (+3 Days, Not +6)

### Objective:
Verify that parallel paths leading to a milestone do not compound delays errantly (the *max-not-sum* rule) and that the Why Panel clearly explains dates and slack.

### Steps:
1. Click on **Task 7 ("Integration Testing")** to open its detail modal.
2. Inspect the **Why Panel** section:
   - **Planned Start:** `2026-10-05`
   - **Driving Prerequisite:** `Task 4 (Backend API Development)`
   - **Slack:** `Task 5 (Test Data Setup)` shows **3 days of slack**.
   - *Why?* Both Task 4 (duration 5) and Task 5 (duration 2) branch from Task 2. Task 4 finishes on Oct 05, while Task 5 finishes on Oct 02. Task 4 is the driver; Task 5 has 3 days of buffer.
3. Close the modal. Click on **Task 2 ("Database Schema Design")**.
4. Increase its **Duration** from `3` to `6` days (+3 days delay) and click **Save Changes**.
5. Observe the UI:
   - A **Ripple Toast** appears notifying that downstream tasks were rescheduled.
6. Re-open **Task 7 ("Integration Testing")**:
   - **Expected Date:** Planned Start moved from `2026-10-05` to `2026-10-08` (+3 days).
   - **Mathematical Check:** The delay moved Task 7 by *exactly* 3 days, not 3 + 3 = 6 days.
   - The Why Panel continues to show Task 4 as the driver and Task 5 with 3 days of slack.

---

## Scenario 3: Real-Time Cycle Detection & Prevention

### Objective:
Verify that cyclic dependencies are caught and rejected by forward BFS before any write occurs.

### Steps:
1. Click on **Task 2 ("Database Schema Design")** to open its modal.
2. In the **Dependencies** section, locate the **Add Prerequisite** dropdown.
3. Select **Task 10 ("Release")** as a prerequisite for Task 2 and click **Add**.
4. **Expected Behavior:**
   - The dependency is immediately blocked.
   - An error alert appears: `Cycle detected: [10 -> 2 -> 4 -> 6 -> 9 -> 10]`.
   - The dependency is **not** added to the table or graph.

---

## Scenario 4: Live AI Dependency Copilot (Groq `allam-2-7b`)

### Objective:
Verify the Propose → Challenge → Verify → Human Approval pipeline powered by your live Groq API key.

### Steps:
1. In the top navigation bar, click the **AI Copilot** button.
2. The **AI Suggestions Drawer** will open on the right side.
3. Observe the candidate suggestions returned:
   - Notice the badge: `groq/allam-2-7b`.
   - Each card displays the proposed link, confidence score, rationale, and extracted evidence phrase.
   - Notice the **Survived** badge indicating it passed the skeptic challenge pass.
4. Click **Accept** on any suggestion:
   - The suggestion is removed from pending, and the new dependency is created on the board.
5. Click **Reject** on another suggestion:
   - The suggestion is dismissed and permanently excluded from future prompts on this board.

---

## Scenario 5: Critical Path Highlighting

### Objective:
Verify that the longest path by duration can be toggled and visualized on the board.

### Steps:
1. In the header bar, click the **Critical Path** toggle switch.
2. **Expected Behavior:**
   - Tasks on the critical path (e.g., Task 1 → Task 2 → Task 4 → Task 6 → Task 9 → Task 10) are highlighted with a distinct primary accent border or badge.
   - Off-critical tasks (such as Task 3 and Task 5) remain muted.
3. Click the toggle again to turn off critical path mode.

---

## Scenario 6: Impact Preview (Dry-Run What-If Analysis)

### Objective:
Test schedule impact forecasting without committing changes.

### Steps:
1. Click on **Task 4 ("Backend API Development")**.
2. In the modal, locate the **Impact Preview** section.
3. Enter a hypothetical duration of `10` days (original is 5).
4. Click **Preview Impact**:
   - **Expected Behavior:** A list appears showing exactly which downstream tasks would move and their projected new start dates (Tasks 6, 7, 8, 9, 10), *without* modifying the actual board.
5. Close the modal without saving; verify no task dates were altered.

---

## Scenario 7: Backward Regression Handling

### Objective:
Verify that regressing a completed task back to in-progress safely invalidates downstream readiness.

### Steps:
1. Drag **Task 1 ("Requirements Gathering")** to **Done**. (Task 2 becomes Ready).
2. Move **Task 2 ("Database Schema Design")** to **In Progress**.
3. Now drag **Task 1** backwards from **Done** to **In Progress**.
4. **Expected Behavior:**
   - **Task 2** immediately updates back to **Blocked**.
   - Downstream progress is guarded, and an audit log event records `needs_reverification` without deleting or corrupting task data.

---

## Scenario 8: Concurrency Conflict (409) & Refresh Persistence

### Objective:
Verify state persistence across page refreshes and optimistic concurrency conflict handling.

### Steps:
1. Make any modification on the board (e.g. edit a task title or drag a card).
2. Press **F5** (hard refresh) in your browser:
   - **Expected Behavior:** The board reloads with the exact updated positions, dates, and column states.
3. To test `409 VERSION_CONFLICT`:
   - Open the application in two browser tabs side-by-side.
   - On Tab 1, open Task 1, edit the title to "Task 1 Updated", and save.
   - On Tab 2 (which still holds version 1), try saving a different change to Task 1.
   - **Expected Behavior:** Tab 2 displays a `409 Version Conflict` notification, preventing silent overwrite.

---

## Scenario 9: Board-Level Authorization & Multi-Tenant Isolation

### Objective:
Verify that the canonical guest board is open to all callers, while user-created boards strictly enforce JWT ownership across all data routes.

### Steps:
1. Open the app as Guest (`Continue as Guest / View Demo Board`):
   - You land directly on Board #1 (`owner_id = NULL`).
   - All DAG recomputes, drag-and-drop operations, and AI suggestions function with zero authentication token required.
2. In API docs (`/docs`), execute `GET /api/boards/1`:
   - Returns `200 OK` with the full board payload without providing any `Authorization` header.
3. Create a private board via `POST /api/auth/boards` with a valid user token.
4. Attempt `GET /api/boards/{private_board_id}` with **no token**:
   - Returns `401 UNAUTHORIZED`.
5. Attempt `GET /api/boards/{private_board_id}` with a **different user's token**:
   - Returns `403 FORBIDDEN`.
6. Attempt `GET /api/boards/{private_board_id}` with the **board owner's token**:
   - Returns `200 OK`.

---

## Automated Test Suite (47 Passing Tests)

For programmatic verification, run the full automated test suite:
```bash
python -m pytest -v
```
- **15 Engine Tests:** Pure DAG acyclicity, max-not-sum propagation, regression rollback, and 1,000 random-graph oracle property tests.
- **20 API Tests:** Board CRUD, blocked drag rejections, Why Panel derivation, impact preview, rate limiting, and CORS headers.
- **8 Authorization Tests:** Public guest bypass, 401 unauthenticated, 403 cross-tenant, and owner access verification.
- **4 AI Pipeline Tests:** Strict prerequisite substring matching, hallucinated evidence drops, and audit log recording.

