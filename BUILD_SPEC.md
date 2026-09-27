# TaskFlow Pro — Build Specification

The precise algorithms, schemas, and API contract this implementation
follows — cited by section number throughout `engine/`, `backend/`,
`tests/`, and `scripts/`. Where the finished build diverged from this plan
(most notably, adding multi-user authentication, which isn't mentioned
below), `docs/ARCHITECTURE.md` is the authoritative source for what was
actually shipped.

---

## 1. Canonical seed data

Use exactly this seed set. It is designed so the diamond, the slack branch,
the cycle-rejection demo, and the regression demo all exist in one small
graph — don't invent a different one.

Board start date: seed script sets it to the date the script runs.
Durations are in whole days.

| id | title | duration | prerequisites |
|----|-------|----------|----------------|
| T1 | Requirements Gathering | 2 | — |
| T2 | Database Schema Design | 3 | T1 |
| T3 | UI Wireframes | 2 | T1 |
| T4 | Backend API Development | 5 | T2 |
| T5 | Test Data Setup | 2 | T2 |
| T6 | Frontend Implementation | 4 | T3, T4 |
| T7 | Integration Testing | 2 | T4, T5 |
| T8 | API Documentation | 1 | T4 |
| T9 | Deployment Prep | 2 | T6, T7 |
| T10 | Release | 1 | T8, T9 |

**Why this shape:** T2 → T4 → T7 and T2 → T5 → T7 is the diamond. T4 takes
5 days, T5 takes 2 days, so T5 finishes 3 days before T4 — that's the slack
branch for the Why Panel demo. Delaying T2 by 3 days must move T7's start
by exactly 3 days (via T4, the driving prerequisite), not 6. T6 depends on
both T3 and T4, giving a second convergence to test. Attempting T10 → T2 as
a new prerequisite closes a loop (T2 already reaches T10 via T4→T6→T9→T10
or T4→T8→T10) — that is the demo input that must get HTTP 409, and it
must never actually be created.

This gives 10 tasks and **13 dependency edges** in total: T2→T1, T3→T1,
T4→T2, T5→T2, T6→T3, T6→T4, T7→T4, T7→T5, T8→T4, T9→T6, T9→T7, T10→T8,
T10→T9.

Descriptions (needed for the AI pipeline's evidence-phrase check — make
sure each description contains language a prerequisite reason could
plausibly quote):

- T1: "Gather and document functional and non-functional requirements from stakeholders."
- T2: "Design the relational schema, including tables for tasks, dependencies, and suggestions."
- T3: "Create wireframes for the Kanban board and task detail views."
- T4: "Build REST endpoints for tasks, dependencies, and scheduling, backed by the database schema."
- T5: "Prepare seeded and synthetic test data matching the database schema for integration testing."
- T6: "Implement the React frontend against the wireframes and the backend API."
- T7: "Run integration tests against the backend API using the prepared test data."
- T8: "Write API documentation describing the endpoints built for the backend."
- T9: "Prepare the deployment environment once the frontend and integration tests pass."
- T10: "Tag and release the version once documentation and deployment prep are complete."

---

## 2. Data model — exact schema

### `board`
| column | type | notes |
|---|---|---|
| id | integer, PK | |
| name | text | |
| start_date | date | all unconstrained tasks anchor here |

### `task`
| column | type | notes |
|---|---|---|
| id | integer, PK | |
| board_id | integer, FK → board.id | |
| title | text | |
| description | text | |
| column | enum: backlog, in_progress, review, done | |
| position | float | fractional ordering within a column |
| duration_days | integer | > 0 |
| pinned_start | date, nullable | overrides computed start if later than prerequisites allow |
| planned_start | date | computed, not user-editable |
| planned_end | date | computed = planned_start + duration_days |
| actual_end | date, nullable | set when column becomes `done`; cleared on regression |
| version | integer | starts at 1, incremented on every update; used for HTTP 409 |
| created_at, updated_at | timestamp | |

### `dependency`
| column | type | notes |
|---|---|---|
| id | integer, PK | |
| task_id | integer, FK → task.id | the dependent task |
| prerequisite_id | integer, FK → task.id | must finish first |
| created_at | timestamp | |

Constraints: unique (`task_id`, `prerequisite_id`); check `task_id !=
prerequisite_id`; `ON DELETE CASCADE` on both FKs.

### `ai_suggestion`
| column | type | notes |
|---|---|---|
| id | integer, PK | |
| task_id | integer | candidate dependent |
| prerequisite_id | integer | candidate prerequisite |
| reason | text | model's one-sentence reason |
| evidence_phrase | text | must appear verbatim in the source task's title or description |
| proposer_confidence | float, 0–1 | |
| challenge_verdict | enum: not_run, survived, contested, rejected | |
| status | enum: pending, accepted, rejected | |
| model_name | text | |
| prompt_version | text | |
| created_at | timestamp | |

### `audit_log`
| column | type | notes |
|---|---|---|
| id | integer, PK | |
| action | text | e.g. `dependency_created`, `task_moved`, `invariant_gate_failed` |
| payload | json | the request/change that was applied (or attempted) |
| source | enum: human, ai | |
| timestamp | timestamp | |

**Derived, never stored — computed on every read from the current graph
state:** `blocked` (bool), `ready` (bool), `driving_prerequisite_id`
(nullable int), `slack_days` per non-driving prerequisite. These are
returned by the API but must not exist as columns anywhere.

**Post-spec addition — the `user` table.** Authentication was added
beyond this original spec (see `docs/ARCHITECTURE.md` §8). A `user` table
(id, email, username, hashed_password, is_active, created_at) was
introduced, and `board` gained a nullable `owner_id` foreign key to it. A
board with `owner_id = NULL` is the original single-shared-workspace
design this spec describes; a board with `owner_id` set is a private,
JWT-authenticated tenant board layered on top. This did not change any of
the five tables above.

---

## 3. Core algorithms — implement exactly this logic

All of §3 lives in `engine/` and has zero imports from `backend/`.

### 3.1 Cycle detection (`engine/graph.py`)

Direction convention: a `dependency` row means `prerequisite_id` must
finish before `task_id` starts. Think of it as an edge
`prerequisite_id → task_id`.

To check whether adding a new edge `P → T` (i.e. a proposed dependency
with `prerequisite_id=P`, `task_id=T`) would create a cycle:

```
def would_create_cycle(P, T, existing_edges) -> bool | list[int]:
    # BFS/DFS forward from T, following existing edges prerequisite_id=T
    # i.e. find every task that currently depends (directly or
    # transitively) on T.
    visited = {T}
    queue = [T]
    parent = {T: None}
    while queue:
        current = queue.pop()
        for dependent in successors_of(current):  # WHERE prerequisite_id = current
            if dependent == P:
                # reconstruct path T -> ... -> P for the error message
                return reconstruct_path(parent, dependent)
            if dependent not in visited:
                visited.add(dependent)
                parent[dependent] = current
                queue.append(dependent)
    return False
```

If it returns a path, the API must reject with **HTTP 409**, body:
```json
{"error": {"code": "CYCLE_DETECTED",
           "message": "Adding this dependency would create a cycle.",
           "details": {"path": [T, "...", P, T]}}}
```
Nothing is written — the check runs before the INSERT, inside the same
transaction, not after.

Self-links (`P == T`) and duplicate edges are rejected by the database
constraints in §2, not by this function — but validate them in the API
layer too so the error message is clean instead of a raw DB error.

### 3.2 Scheduling recompute (`engine/scheduler.py`)

Triggered after: a dependency is added/removed, a task's duration or
pinned_start changes, or a task's column changes (in particular entering
or leaving `done`).

```
def recompute(changed_task_id, all_tasks, all_edges):
    affected = forward_closure(changed_task_id, all_edges)  # BFS through
                                                              # successors;
                                                              # includes
                                                              # changed_task_id
                                                              # itself
    ordered = topological_sort(affected, all_edges)          # Kahn's
                                                              # algorithm,
                                                              # restricted
                                                              # to `affected`
                                                              # but reading
                                                              # finish dates
                                                              # of ANY
                                                              # prerequisite,
                                                              # even ones
                                                              # outside
                                                              # `affected`
    for task in ordered:
        candidates = []
        for prereq in prerequisites_of(task):
            finish = prereq.actual_end if prereq.column == 'done' else prereq.planned_end
            candidates.append((finish, prereq.id))
        if task.pinned_start:
            candidates.append((task.pinned_start, None))
        if not candidates:
            candidates.append((task.board.start_date, None))

        driving_finish, driving_id = max(candidates, key=lambda c: c[0])
        task.planned_start = driving_finish
        task.planned_end = task.planned_start + task.duration_days
        task.driving_prerequisite_id = driving_id  # None means pinned_start
                                                      # or board start date won
        for finish, prereq_id in candidates:
            if prereq_id is not None and prereq_id != driving_id:
                task.slack[prereq_id] = driving_finish - finish
    return ordered  # the set of tasks whose dates changed — this is what
                     # the ripple view and the impact-preview endpoint show
```

**This is the rule that prevents compounding.** `max()` is taken once per
task from *final* prerequisite finish dates — never summed, never taken
per-path. Because `ordered` is a topological order, every prerequisite of
`task` has already been recomputed earlier in the same loop, so
`prereq.planned_end` is always current, not stale.

A task moved into `done`: set `actual_end = today` (or `planned_end` if
you want deterministic tests — pick one and be consistent; document the
choice in `docs/ARCHITECTURE.md`). If `actual_end < planned_end` (finished
early), the recompute above naturally pulls unpinned successors forward
using the earlier `actual_end` — this is a locked assumption from the original design. The Why Panel (§6) must render this case as: *"moved N
days earlier because \<task> finished early."*

### 3.3 Blocked / Ready derivation (`engine/derive.py`)

Computed on every read, never stored:

```
def is_ready(task, all_tasks):
    return all(p.column == 'done' for p in prerequisites_of(task))

def is_blocked(task, all_tasks):
    return not is_ready(task, all_tasks)
```

Enforcement: the "move task to column" endpoint must reject (HTTP 409,
code `TASK_BLOCKED`) any attempt to set `column = in_progress` (or
`review`, or `done`) on a task where `is_blocked(task)` is true. This
check happens in the API/transaction layer, not just the frontend — the
frontend disabling the drag is a UX nicety, not the enforcement.

### 3.4 Regression handling (`engine/derive.py` + `scheduler.py`)

When a task's column moves from `done` to anything else:

```
def handle_regression(task, all_tasks, all_edges):
    task.actual_end = None
    recompute(task.id, all_tasks, all_edges)   # uses planned_end again
    downstream = forward_closure(task.id, all_edges) - {task.id}
    for dep in downstream:
        if dep.column == 'done':
            audit_log.write(action='needs_reverification', task_id=dep.id, source='human')
            # do NOT auto-move it out of done — flag only, per synopsis
        # dep.blocked/ready is already correct because it's derived live
```

Downstream tasks that are not `done` need no special handling — their
`blocked`/`ready` status is derived live and will already reflect the
regressed prerequisite on the next read. `done` dependents are the only
ones that need an explicit flag, because a `done` task normally implies
its prerequisites stayed satisfied — that assumption just broke, and a
human should look at it.

### 3.5 Invariant Gate (`engine/invariants.py`)

Runs inside the same transaction, immediately before commit, on every
write that touches the graph or schedule:

```
def check_invariants(all_tasks, all_edges) -> list[str]:
    violations = []
    if not is_acyclic(all_edges):
        violations.append("GRAPH_HAS_CYCLE")
    for edge in all_edges:
        prereq = get(edge.prerequisite_id)
        dep = get(edge.task_id)
        prereq_finish = prereq.actual_end if prereq.column == 'done' else prereq.planned_end
        if dep.planned_start < prereq_finish:
            violations.append(f"SCHEDULE_VIOLATION:{edge.task_id}")
    for task in all_tasks:
        if task.column in ('in_progress', 'review', 'done') and is_blocked(task, all_tasks):
            violations.append(f"BLOCKED_TASK_ADVANCED:{task.id}")
    return violations
```

If `violations` is non-empty: **abort the transaction**, write an
`audit_log` row with `action='invariant_gate_failed'` and the violations
list, return HTTP 500 with code `INVARIANT_VIOLATION`. This should never
actually fire in production use if §3.1–3.4 are implemented correctly —
its only job is to catch a future code change that breaks one of them. It
firing in a demo is a bug, not a feature; don't ship code that relies on
it to "fix" bad state after the fact.

The brute-force oracle (`engine/oracle.py`, **tests only, never imported
by `backend/`**): given a full task/edge set, recompute every task's
start/end from scratch with no incremental logic (full topological sort,
same max-not-sum rule, no shortcuts). Used in property tests (§8) to
compare against the incremental `recompute()` on randomly generated DAGs —
they must always agree.

---

## 4. API contract

Base path `/api`. All mutating endpoints run inside one DB transaction:
validate → apply → recompute → check invariants → commit → return.
Error body shape, always:
```json
{"error": {"code": "SOME_CODE", "message": "human readable", "details": {}}}
```

CORS must never be `*`; it must resolve to the frontend's actual
origin(s). (The shipped implementation makes this configurable via an
`ALLOWED_ORIGIN` env var rather than a single hardcoded value, to support
both local dev and a deployed frontend — see `docs/ARCHITECTURE.md` §4
for the exact mechanism.)

| Method & path | Purpose | Success body | Key error codes |
|---|---|---|---|
| `GET /boards/{id}` | Full board: tasks (with derived fields), dependencies | `{tasks: [...], dependencies: [...]}` | 404 |
| `POST /tasks` | Create task | created task | 400 |
| `PATCH /tasks/{id}` | Edit title/description/duration/pinned_start; **must include `version`** | updated task + list of other tasks whose dates changed | `409 VERSION_CONFLICT`, `409 INVARIANT_VIOLATION` |
| `POST /tasks/{id}/move` | Change column and/or position | updated task + downstream changes | `409 TASK_BLOCKED`, `409 VERSION_CONFLICT` |
| `POST /dependencies` | Create `{task_id, prerequisite_id}` | created dependency + recompute results | `409 CYCLE_DETECTED`, `400 SELF_DEPENDENCY`, `400 DUPLICATE_DEPENDENCY` |
| `DELETE /dependencies/{id}` | Remove a dependency | recompute results | 404 |
| `DELETE /tasks/{id}` | Delete task (cascades dependencies) | 204 | 404 |
| `GET /tasks/{id}/explanation` | Why Panel data: driving prerequisite, slack per other prerequisite, in plain-language sentence form | `{driving_prerequisite_id, reason_text, slack: [{prerequisite_id, days}]}` | 404 |
| `POST /tasks/{id}/impact-preview` | Dry run: given a hypothetical change (new duration, new pinned_start), return what *would* move, without committing | `{would_change: [{task_id, old_start, new_start}]}` | 400 |
| `POST /dependencies/suggestions` | Trigger the AI pipeline for one task or the whole board | list of surviving `ai_suggestion` rows | `503 AI_UNAVAILABLE` (still 200 with heuristic fallback results — see §5.6) |
| `POST /dependencies/suggestions/{id}/accept` | Accept — calls the same path as `POST /dependencies` internally | created dependency | same as `POST /dependencies` |
| `POST /dependencies/suggestions/{id}/reject` | Reject — stored, excluded from future suggestions on that board | 204 | 404 |
| `GET /boards/{id}/critical-path` | *(Layer 3, optional)* longest chain by duration | `{task_ids: [...], total_duration: N}` | 404 |

Fractional positions: on a drag, the new `position` is computed client-side
as the midpoint between the two neighboring cards' positions (or ±1 at an
end) and sent directly in `POST /tasks/{id}/move` — the backend just
stores the float, no reordering of other rows needed.

**Post-spec addition — auth routes.** `backend/routes/auth.py` adds
`POST /auth/register`, `POST /auth/login`, `GET /auth/me`, and
`GET /auth/boards` under the same `/api` prefix, none of which existed in
this original contract. Every route above additionally now runs through
`require_board_access` (see `docs/ARCHITECTURE.md` §8) before touching a
private board.

---

## 5. AI pipeline spec

### 5.1 Propose

One batched call per trigger (single task or whole board). System prompt
must include:
- The closed list of board tasks: `{id, title, description}` for every
  task on the board *except* ones already linked to the target.
- The instruction that ordering logic favors design → build → test →
  release patterns, with two worked examples embedded in the prompt.
- `temperature = 0`.
- Explicit instruction: if no clear prerequisite exists, return an empty
  list — this is a valid and preferred answer.

Required output JSON schema (strict, no prose outside the JSON):
```json
{"suggestions": [
  {"prerequisite_id": 4, "task_id": 7, "reason": "one sentence",
   "evidence_phrase": "exact substring from the task's own text",
   "confidence": 0.0}
]}
```

### 5.2 Challenge

One more batched call, all of the current call's surviving proposals at
once. System prompt: for each proposed link, decide `survived` or
`rejected`, checking specifically: (a) is the direction reversed, (b) is
this only a topical/thematic link rather than a true finish-to-start
dependency, (c) could the two tasks run in parallel with no real
ordering constraint. Output: `{"verdicts": [{"index": 0, "verdict":
"survived"|"rejected", "note": "..."}]}`. Anything `rejected` here is
dropped before the deterministic checks even run. If this call times out
or fails to parse, do not drop the suggestions — mark
`challenge_verdict='not_run'` and proceed to §5.3 unchallenged; the UI
shows these without a contested/clean badge either way.

### 5.3 Verify (deterministic, no LLM)

Run in this order, short-circuit on first failure per suggestion:
1. JSON schema valid.
2. `prerequisite_id` and `task_id` both exist on this board.
3. `prerequisite_id != task_id`.
4. Not a duplicate of an existing `dependency` row.
5. `evidence_phrase` is a literal substring (case-insensitive) of the
   source task's title or description. **Implementation note (confirmed
   during build):** "source task" means the *prerequisite* task
   specifically, not either task — the reason is supposed to quote what
   the prerequisite actually is, and checking both tasks would let a
   dependent's own description satisfy the check even when the claimed
   prerequisite has nothing to do with the quoted phrase. See
   `docs/ARCHITECTURE.md` §5 for the reasoning.
6. `confidence >= 0.5` (tune during testing; document the chosen
   threshold in `docs/ARCHITECTURE.md`).
7. `would_create_cycle(prerequisite_id, task_id, existing_edges)` is
   `False`. If it would create a cycle, drop the suggestion **and** write
   an `audit_log` row (`action='ai_suggestion_cycle_dropped'`) — never
   surface it to the human.

Suggestions passing all seven are stored as `ai_suggestion` rows with
`status='pending'`, `challenge_verdict` as set in §5.2.

### 5.4 Human review

Frontend renders each pending suggestion as a dashed "ghost" edge on the
board with the reason, evidence phrase, and a contested badge when
`challenge_verdict='contested'`. Two actions only: accept (calls `POST
/dependencies/suggestions/{id}/accept`, which internally goes through the
exact same `POST /dependencies` path and cycle check as a manually
created link — no special AI write path anywhere in the code) or reject
(`POST /dependencies/suggestions/{id}/reject`, which sets `status =
'rejected'` and excludes that exact `(prerequisite_id, task_id)` pair from
future proposals on this board).

### 5.5 Measure

Maintain a hand-labelled reference file (`tests/seed_dependency_labels.json`
— the "true" dependency set for the seed board in §1) and a script
(`scripts/measure_ai.py`) that runs the pipeline against the seed board and
reports: true positives, false positives, false negatives, precision,
recall, and acceptance rate (accepted / total shown). Reference targets:
precision ≥ 0.85, recall ≥ 0.70. This script's output is what the
synopsis's Section 5 metrics point to — run it and put the actual numbers
in `docs/ARCHITECTURE.md`, don't leave the targets unverified.

### 5.6 Failure handling

- Propose or Challenge call exceeds 12 seconds total → treat as failure.
- On Propose failure: one retry. If the retry also fails or returns
  unparseable JSON, fall back to a keyword heuristic (hard-coded ordered
  keyword list: requirements → schema/design → backend/api → frontend →
  test → docs → deploy → release; suggest a link when an earlier-keyword
  task's title/description contains a later-keyword task's obvious
  reference). Mark these suggestions with `model_name='heuristic-fallback'`
  and show a "heuristic" badge in the UI instead of a confidence score.
- Rate limiting: no more than one Propose/Challenge round in flight per
  board at a time; queue or reject a second concurrent trigger with `429`.
- The board and all non-AI functionality must work with the LLM API key
  entirely absent — verify this explicitly as a test case (§8).

---

## 6. Frontend spec

Screens/components (React + TypeScript + dnd-kit; styling per `design.md`):

- **Board** — four columns (Backlog, In Progress, Review, Done), cards
  draggable via dnd-kit. A card shows title, a Blocked/Ready chip, and (if
  Blocked) which prerequisite(s) are blocking it, by title.
- **Task detail panel** — opens on card click. Shows description,
  duration, dates, and the **Why Panel**: driving prerequisite and its
  finish date in a plain sentence, plus a list of other prerequisites with
  their slack in days. Fetches `GET /tasks/{id}/explanation`.
- **Ripple toast/list** — after any mutation that returns a non-empty list
  of changed tasks (§4), show a small list: task title, old date → new
  date, and its cause (driving prerequisite title).
- **Dependency editor** — add/remove dependency links from the task
  detail panel; surfaces `409 CYCLE_DETECTED` errors with the returned
  path rendered as "A → B → C → A", not a raw error dump.
- **AI suggestions panel** — lists pending `ai_suggestion` rows for the
  board with accept/reject buttons, reason, evidence phrase, and the
  contested badge.
- **Optimistic updates** — every mutation applies to local state
  immediately, then reconciles with the server response; on any error
  response, roll back to the pre-mutation state and show the error.
- **(Layer 3, optional)** Critical path highlight, impact-preview dry-run
  UI.

---

## 7. Phased build plan — definition of done per phase

Each phase below lists what "done" concretely means — move to the next
phase only when every box is true. All phases are complete as of
submission; see `docs/ARCHITECTURE.md` §9 for the current test and
measurement summary.

**Phase 1 — Foundation**
- [x] Repo structure (engine/, backend/, frontend/, tests/, scripts/, docs/) exists.
- [x] `.gitignore` committed before any other file.
- [x] DB schema (§2) created via migration/init script.
- [x] Seed script (§1) loads all 10 tasks and 13 dependencies correctly —
      verify by querying the DB, not just "script ran with no error."
- [x] `GET /boards/{id}` returns the seeded board with correct derived
      fields for every task.

**Phase 2 — Engine**
- [x] `engine/` has zero imports from `backend/`, `sqlalchemy`, or
      `fastapi` — verify with a grep, not by eye.
- [x] Cycle detection (§3.1), scheduler (§3.2), derivation (§3.3),
      regression (§3.4), and Invariant Gate (§3.5) implemented exactly as
      specified.
- [x] All tests in §8.1 pass.

**Phase 3 — API and board UI**
- [x] Every endpoint in §4 implemented and manually exercised at least
      once (curl or equivalent) against the seeded board.
- [x] Board renders, drag-and-drop works, Blocked cards refuse to enter
      In Progress with a visible error (not a silent no-op).
- [x] Task/dependency create/edit forms work end to end.

**Phase 4 — Wiring and persistence**
- [x] Refreshing the browser preserves board state exactly.
- [x] Blocked reason (which prerequisite, by title) shown on cards.
- [x] A second browser tab editing the same task triggers
      `409 VERSION_CONFLICT` correctly.

**Phase 5 — Minimal AI path**
- [x] Propose → Verify → Human works end to end for at least one real
      trigger against the seed board.
- [x] `AI_TOOL_DECLARATION.md` §1 filled in with the actual model/provider
      used (Groq / `allam-2-7b`).
- [x] Board fully functional with the AI API key unset (§5.6 test).

**Phase 6 — Differentiators**
- [x] Why Panel renders correct driving-prerequisite explanations,
      verified against the diamond in the seed set.
- [x] Challenge pass integrated; contested badge shows in the UI.
- [x] Ripple view shows after a multi-task-affecting change.

**Phase 7 — Optional extensions**
- [x] Critical path view.
- [x] Impact preview dry-run.

**Phase 8 — Delivery polish**
- [x] `docs/ARCHITECTURE.md` written against what was actually built.
- [x] `README.md` setup/run instructions.
- [x] `scripts/measure_ai.py` run, real numbers recorded.
- [x] Demo script prepared (`docs/TESTING_SCENARIOS.md`).
- [x] Deployed: Vercel (frontend), Render (API), Neon (PostgreSQL).

**Phase 9 — Post-plan addition (not in this spec's original scope)**
- [x] Multi-user JWT authentication with bcrypt password hashing.
- [x] Guest-bypass canonical board so evaluators are never blocked
      behind credentials.
- [x] Board-level authorization (`require_board_access`) enforced on
      every data route, not just the auth-listing routes.
- See `docs/ARCHITECTURE.md` §8 for why this was added and how it
  coexists with §0's single-shared-workspace assumption.

---

## 8. Test specification

### 8.1 Engine tests (`tests/engine/`) — required, Phase 2
- Cycle rejection: attempt T10→T2 — must be rejected with the correct
  path, and the dependency table unchanged afterward.
- Diamond math: delay T2 by 3 days (push its duration or pinned_start);
  assert T7's start moved by exactly 3 days, not 6; assert T4 is the
  returned driving prerequisite for T7 and T5's slack is reported as 3.
- Regression: move T2 from done back to in_progress after the whole chain
  was completed; assert T4, T5, T7, T6, T8, T9, T10 all become Blocked
  again where applicable, and any of them that were `done` are flagged
  `needs_reverification` in the audit log.
- Blocked-drag rejection: attempt to move a Blocked task to in_progress;
  assert `409 TASK_BLOCKED` and no column change persisted.
- Property test: generate 1,000 random valid DAGs (no cycles, random
  durations) with random schedule mutations; assert `recompute()` and the
  brute-force `oracle.py` always agree on every task's start/end.
- Self-dependency and duplicate-dependency both rejected.

### 8.2 API tests (`tests/api/`)
- Version conflict: PATCH with a stale `version` returns 409, DB
  unchanged.
- Full CRUD round-trip on tasks and dependencies.
- AI pipeline against seed board with the API key unset → falls back to
  heuristic, board still fully functional (§5.6).
- Uniform Pydantic-driven `400` error body (never a raw stack trace) on
  malformed requests.
- CORS headers present and scoped to the configured origin(s), never `*`.

### 8.3 Known failure cases to document (extra credit per the checklist)
List in `docs/ARCHITECTURE.md`: cases found but decided not to fix, and
why — e.g. very large boards beyond the tuned range, concurrent drag
races beyond what optimistic concurrency catches, LLM provider outages
beyond the retry/fallback window.

---

## 9. Edge case → implementation matrix

Direct mapping from the synopsis's Section 1 failure modes to where each
is implemented, so nothing gets forgotten:

| Failure mode (synopsis §1) | Implemented in |
|---|---|
| Converging paths / diamond | §3.2 `recompute()`, tested in §8.1 |
| Derived state (Blocked/Ready) | §3.3, never a DB column |
| Cycles | §3.1, enforced in `POST /dependencies` |
| Regression | §3.4 |
| Invalid drags | §3.3 enforcement + §4 `TASK_BLOCKED` |
| Trust in automation | §6 Why Panel + ripple view |
| AI trust | §5.3 deterministic Verify, §5.4 human approval |
| Persistence / simultaneous edits | §2 `version` column, §4 `VERSION_CONFLICT` |
| Self dependency, duplicate links | §3.1 note, DB constraints §2 |
| Deleting a task with dependents | `DELETE /tasks/{id}` cascades per §2's `ON DELETE CASCADE`; recompute affected descendants after |
| Tasks with no links | §3.2 falls back to `board.start_date` |
| Missing dates | not applicable — dates are always computed, never user-entered directly, except `pinned_start` which is optional and simply omitted from the max() candidates when null |

---

## 10. Decisions escalated during the build (resolved)

These were originally listed as "do not decide unilaterally." All were
confirmed before the relevant code was written; final decisions are
recorded here and in `docs/ARCHITECTURE.md`.

- **LLM provider/model:** Groq, model `allam-2-7b`. Falls back to the
  keyword heuristic automatically when `GROQ_API_KEY` is unset.
- **Deployment target:** Render (API), Vercel (frontend), Neon
  (managed PostgreSQL).
- **Submission branch name:** `main`.
- **`actual_end` semantics:** set to `planned_end` (not "today") when a
  task moves to Done, for test determinism. See
  `docs/ARCHITECTURE.md` §2.1 for the tradeoff this implies.
- **Auth as a scope addition:** confirmed and built as documented in
  §2 and §4's "post-spec addition" notes above.