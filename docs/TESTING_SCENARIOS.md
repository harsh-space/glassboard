# TaskFlow Pro — Demo Script & Testing Scenarios

Both a fast guided walkthrough and the full manual test matrix live in this
one document, so a judge can either watch the 5-minute version or work
through every scenario in depth without switching files.

**Environments:**
- **Live app:** [glassboard-umber.vercel.app](https://glassboard-umber.vercel.app)
- **Live API docs:** [glassboard-backend.onrender.com/docs](https://glassboard-backend.onrender.com/docs)
- **Local:** [http://localhost:5173](http://localhost:5173) (API on `:8000`), seeded with the canonical 10-task, 13-dependency graph.

> **Access:** the login screen has a **"Continue as Guest / View Demo Board"**
> button that lands directly on the canonical shared board (`id=1`,
> `owner_id=NULL`) with zero login friction. Registering an account instead
> creates an isolated private board.
>
> **Dates:** the board's start date is whatever day `scripts/seed.py` was
> run, so exact calendar dates below (e.g. `2026-10-05`) will differ from
> what you see. What's guaranteed is the *relative* shift — Task 7 moving
> by exactly 3 days, never 6 — not the specific date.

---

## Quick demo (5 minutes)

Local setup, if not already running:
```bash
# Terminal 1
python scripts/seed.py
uvicorn backend.main:app --host 0.0.0.0 --port 8000
# Terminal 2
cd frontend && npm run dev
```

1. **Blocked vs. Ready (60s).** *"TaskFlow Pro treats dependencies as mathematical constraints, not just visual state."* Task 1 shows a green **Ready** chip (no prerequisites). Task 2 shows amber **Blocked** with `Needs: Requirements Gathering`. Try dragging Task 2 into In Progress — it snaps back with `"Cannot move blocked task: prerequisites incomplete"`. Drag Task 1 to Done instead — Task 2 flips to **Ready** immediately.
2. **The Why Panel, +3 not +6 (90s).** *"Parallel paths converging on one task shouldn't compound a delay."* Open Task 7 — the Why Panel shows Task 4 as the driving prerequisite and Task 5 with 3 days of slack. Increase Task 2's duration from 3 to 6 days. A ripple toast lists every task that moved. Re-open Task 7: its start moved by exactly 3 days, not 6, and Task 4/Task 5 are still the driver/slack pair.
3. **Cycle prevention (60s).** *"Cycles are rejected in pure Python before anything touches the database."* On Task 2, try adding Task 10 as a prerequisite. It's rejected instantly with the exact loop path, e.g. `[10 -> 2 -> 4 -> 6 -> 9 -> 10]`, and nothing is written.
4. **The AI copilot (60s).** *"An LLM can propose a link; it can never write one."* Open the AI Suggestions drawer. Each candidate shows its reason, evidence phrase, and a challenge-pass badge. Accept one — it's created through the same endpoint a manual link would use. Reject another — it's excluded from future proposals on this board.
5. **Regression (30s).** *"Un-completing a task should never corrupt what depended on it."* Drag Task 1 back from Done to In Progress. Task 2 immediately re-blocks, and the audit log records `needs_reverification` for anything downstream that was already Done.

*"TaskFlow Pro delivers mathematical correctness through an isolated graph engine, non-compounding scheduling, complete explainability through the Why Panel, and responsible AI that respects human authority."*

---

## Full scenario matrix

The five scenarios above, plus four more that aren't part of the short demo: critical path highlighting, the impact-preview dry run, concurrency/refresh handling, and multi-tenant authorization.

### Scenario 5 — Critical Path Highlighting
Click the **Critical Path** toggle in the header. Tasks on the longest chain by duration (e.g. Task 1 → 2 → 4 → 6 → 9 → 10) get a distinct accent border; off-path tasks (Task 3, Task 5) stay muted. Toggle again to turn it off.

### Scenario 6 — Impact Preview (dry run)
Open Task 4, and in its **Impact Preview** section enter a hypothetical duration of 10 days (currently 5). Clicking **Preview Impact** lists exactly which downstream tasks (6, 7, 8, 9, 10) would move and to what dates — without touching the actual board. Closing the modal without saving leaves every date unchanged.

### Scenario 7 — Backward Regression (detailed)
Move Task 1 to Done (Task 2 becomes Ready), then move Task 2 to In Progress. Drag Task 1 back to In Progress. Task 2 re-blocks immediately, and the audit log gets a `needs_reverification` entry rather than any task data being deleted or silently altered.

### Scenario 8 — Concurrency (409) & Refresh Persistence
Edit a task or drag a card, then hard-refresh the browser (F5) — the board reloads with the exact same state. To see the concurrency guard: open the app in two tabs, edit and save Task 1's title in Tab 1, then try saving a different edit to the same task in Tab 2 (still holding the old version). Tab 2 gets a `409 VERSION_CONFLICT` instead of silently overwriting Tab 1's change.

### Scenario 9 — Board-Level Authorization & Multi-Tenant Isolation
As a guest, `GET /api/boards/1` returns `200` with no `Authorization` header at all — the canonical board is public by design. Create a private board via `POST /api/auth/boards` with a real user token, then try `GET /api/boards/{private_board_id}`: no token returns `401`, a different user's token returns `403`, and the owner's token returns `200`.

---

## Automated test suite (47 passing tests)

```bash
python -m pytest -v
```
- **15 engine tests** — cycle rejection, max-not-sum propagation (the diamond case), regression rollback, Invariant Gate assertions, and a 1,000-random-graph oracle property test.
- **20 API tests** — board retrieval, task/dependency CRUD, blocked-drag rejection, Why Panel derivation, impact preview, rate limiting, CORS headers, and uniform error formatting.
- **8 authorization tests** — public guest bypass, `401` unauthenticated, `403` cross-tenant, `200` owner access.
- **4 AI pipeline tests** — fabricated-evidence rejection, strict substring matching against the prerequisite's own text, audit-log recording of every drop.

---

**See also:** [`../README.md`](../README.md) for setup and the full documentation flow, and [`ARCHITECTURE.md`](ARCHITECTURE.md) for how each behavior above is implemented.