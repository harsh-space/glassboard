# TaskFlow Pro — Test Suite & Results

This file exists to satisfy the submission checklist's "full suite of test
cases you ran" item: it lists every automated test case in this repository
(by file and name), what each one actually checks, and the real console
output from the most recent full run — not a summary written from memory.

**Run environment:** Python 3.12.3, pytest-9.1.1, SQLite (test DB), no
`GROQ_API_KEY` set (AI pipeline tests exercise both the live-key and
no-key/heuristic-fallback code paths explicitly — see below).

**Command:**
```bash
python -m pytest -v
```

**Result:** `47 passed, 1 warning in 6.68s` — 100% pass rate, zero
failures, zero skips. The one warning is an unrelated upstream
`StarletteDeprecationWarning` about `httpx`/`starlette.testclient`, not a
problem with this codebase.

---

## Summary by module

| Module | File | Tests | What it covers |
|---|---|---|---|
| Engine | `tests/engine/test_cycle.py` | 4 | Cycle detection: acyclic seed graph, rejection of a cycle-forming edge, self-dependency rejection, valid edge acceptance |
| Engine | `tests/engine/test_diamond.py` | 2 | Non-compounding ("max-not-sum") scheduling across converging paths — duration delay and pinned-start delay |
| Engine | `tests/engine/test_blocked.py` | 2 | Initial Blocked/Ready derivation on the seed board; Invariant Gate rejection of advancing a blocked task |
| Engine | `tests/engine/test_invariants.py` | 4 | The Invariant Gate: valid graph passes, cycle is caught, schedule violation is caught, blocked-task advancement is caught |
| Engine | `tests/engine/test_regression.py` | 2 | Un-completing a task re-blocks downstream tasks and flags already-Done descendants for reverification |
| Engine | `tests/engine/test_oracle_property.py` | 1 | Property test: incremental scheduler agrees with the brute-force oracle across 1,000 randomly generated graphs |
| API | `tests/api/test_boards.py` | 2 | Board retrieval (seeded board, 404 for missing board) |
| API | `tests/api/test_tasks.py` | 7 | Task CRUD, optimistic-concurrency `409 VERSION_CONFLICT`, blocked-move rejection, valid move, Why Panel explanation endpoint, impact-preview dry run |
| API | `tests/api/test_dependencies.py` | 8 | Cycle rejection via the API, self/duplicate dependency rejection, dependency deletion, AI suggestion generation (both heuristic-fallback and live-Groq-key paths), accept/reject flow, rate limiting |
| API | `tests/api/test_authorization.py` | 8 | Guest board reachable with no token; private board returns `401`/`403`/`200` correctly for no-token / wrong-user / owner requests, across both board and task-creation endpoints |
| API | `tests/api/test_auth.py` | 1 | Full auth flow: register, login, token issuance |
| API | `tests/api/test_cors_and_errors.py` | 2 | Pydantic validation errors return clean `400`s; CORS headers are present and correct |
| AI | `tests/ai/test_evidence_check.py` | 4 | Deterministic verification step: valid evidence survives, hallucinated evidence (not present in the prerequisite's own text) is dropped, evidence found only in the dependent's text (not the prerequisite's) is dropped, and every drop is written to the audit log |

**Total: 47 / 47 passing.**

---

## Full test-by-test results (verbatim `pytest -v` output)

```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
collected 47 items

tests/ai/test_evidence_check.py::TestEvidenceCheckDropsBadProposals::test_hallucinated_evidence_not_in_prereq_text_is_dropped PASSED [  2%]
tests/ai/test_evidence_check.py::TestEvidenceCheckDropsBadProposals::test_valid_evidence_in_prereq_text_survives PASSED [  4%]
tests/ai/test_evidence_check.py::TestEvidenceCheckDropsBadProposals::test_evidence_only_in_dep_text_not_in_prereq_is_dropped PASSED [  6%]
tests/ai/test_evidence_check.py::TestEvidenceCheckDropsBadProposals::test_hallucinated_evidence_drop_is_written_to_audit_log PASSED [  8%]
tests/api/test_auth.py::test_auth_full_flow PASSED                       [ 10%]
tests/api/test_authorization.py::TestGuestBoardAlwaysAccessible::test_get_guest_board_no_token PASSED [ 12%]
tests/api/test_authorization.py::TestGuestBoardAlwaysAccessible::test_get_guest_board_ai_suggestions_no_token PASSED [ 14%]
tests/api/test_authorization.py::TestPrivateBoardEnforcement::test_no_token_gets_401 PASSED [ 17%]
tests/api/test_authorization.py::TestPrivateBoardEnforcement::test_wrong_user_gets_403 PASSED [ 19%]
tests/api/test_authorization.py::TestPrivateBoardEnforcement::test_owner_gets_200 PASSED [ 21%]
tests/api/test_authorization.py::TestPrivateBoardEnforcement::test_create_task_no_token_on_private_board_gets_401 PASSED [ 23%]
tests/api/test_authorization.py::TestPrivateBoardEnforcement::test_create_task_wrong_user_on_private_board_gets_403 PASSED [ 25%]
tests/api/test_authorization.py::TestPrivateBoardEnforcement::test_ai_suggestions_no_token_private_board_gets_401 PASSED [ 27%]
tests/api/test_boards.py::test_get_board_seeded PASSED                   [ 29%]
tests/api/test_boards.py::test_get_board_not_found PASSED                [ 31%]
tests/api/test_cors_and_errors.py::test_validation_error_pydantic_clean_400 PASSED [ 34%]
tests/api/test_cors_and_errors.py::test_cors_origin_headers PASSED       [ 36%]
tests/api/test_dependencies.py::test_cycle_rejection_api_t10_to_t2 PASSED [ 38%]
tests/api/test_dependencies.py::test_self_dependency_rejection PASSED    [ 40%]
tests/api/test_dependencies.py::test_duplicate_dependency_rejection PASSED [ 42%]
tests/api/test_dependencies.py::test_delete_dependency PASSED            [ 44%]
tests/api/test_dependencies.py::test_ai_suggestions_heuristic_fallback_when_key_unset PASSED [ 46%]
tests/api/test_dependencies.py::test_ai_suggestions_live_groq_when_key_set PASSED [ 48%]
tests/api/test_dependencies.py::test_ai_suggestion_accept_and_reject_flow PASSED [ 51%]
tests/api/test_dependencies.py::test_ai_suggestions_rate_limiting PASSED [ 53%]
tests/api/test_tasks.py::test_create_task PASSED                         [ 55%]
tests/api/test_tasks.py::test_update_task_optimistic_concurrency_version_conflict PASSED [ 57%]
tests/api/test_tasks.py::test_update_task_valid PASSED                   [ 59%]
tests/api/test_tasks.py::test_move_task_blocked_rejection PASSED         [ 61%]
tests/api/test_tasks.py::test_move_task_success_when_ready PASSED        [ 63%]
tests/api/test_tasks.py::test_task_explanation_why_panel PASSED          [ 65%]
tests/api/test_tasks.py::test_task_impact_preview_dry_run PASSED         [ 68%]
tests/engine/test_blocked.py::test_initial_board_blocked_states PASSED   [ 70%]
tests/engine/test_blocked.py::test_advancing_blocked_task_violates_invariants PASSED [ 72%]
tests/engine/test_cycle.py::test_seed_graph_is_acyclic PASSED            [ 74%]
tests/engine/test_cycle.py::test_cycle_rejection_t10_to_t2 PASSED        [ 76%]
tests/engine/test_cycle.py::test_cycle_self_dependency PASSED            [ 78%]
tests/engine/test_cycle.py::test_valid_dependency_no_cycle PASSED        [ 80%]
tests/engine/test_diamond.py::test_diamond_math_duration_delay PASSED    [ 82%]
tests/engine/test_diamond.py::test_diamond_math_pinned_start_delay PASSED [ 85%]
tests/engine/test_invariants.py::test_invariants_pass_on_valid_seeded_graph PASSED [ 87%]
tests/engine/test_invariants.py::test_invariants_detect_cycle PASSED [ 89%]
tests/engine/test_invariants.py::test_invariants_detect_schedule_violation PASSED [ 91%]
tests/engine/test_invariants.py::test_invariants_detect_blocked_task_advanced PASSED [ 93%]
tests/engine/test_oracle_property.py::test_property_1000_random_graphs_oracle_agreement PASSED [ 95%]
tests/engine/test_regression.py::test_regression_when_tasks_were_done PASSED [ 97%]
tests/engine/test_regression.py::test_regression_when_downstream_in_progress PASSED [100%]

=============================== warnings summary ===============================
../../../../usr/local/lib/python3.12/dist-packages/fastapi/testclient.py:1
  StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is
  deprecated; install `httpx2` instead.

======================== 47 passed, 1 warning in 6.68s =========================
```

---

## AI copilot offline accuracy (not a pytest test, but a measured result)

Run separately via `scripts/measure_ai.py` against the canonical 13-edge
seed board with a blank starting graph and no LLM key (pure heuristic
path). Included here because it's a "test case you ran" in the broader
sense, and the submission checklist doesn't distinguish between pytest
cases and standalone measurement scripts.

| Metric | Result | Target |
|---|---|---|
| Precision | 100.0% | ≥ 85% (MET) |
| Recall | 84.6% | ≥ 70% (MET) |
| F1 | 91.7% | — |

Command to reproduce:
```bash
python scripts/measure_ai.py
```

Full methodology and the two false negatives that remain are documented
in `../docs/ARCHITECTURE.md` §5.3.

---

## How to reproduce this file's results

```bash
git clone https://github.com/harsh-space/glassboard.git
cd glassboard
cp .env.example .env   # JWT_SECRET_KEY must be set; GROQ_API_KEY optional
pip install -r requirements.txt
python -m pytest -v
```

**See also:** [`../docs/TESTING_SCENARIOS.md`](../docs/TESTING_SCENARIOS.md)
for the manual/guided demo scenarios (Blocked/Ready, the Why Panel,
cycle prevention, the AI copilot, regression, critical path, impact
preview, concurrency, and multi-tenant authorization) that complement
this automated suite, and [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)
for how each tested behavior is implemented.