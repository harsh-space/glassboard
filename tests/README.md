# TaskFlow Pro — Test Suite & Results

This file lists every automated test case in this repository, by file and
name, and how to independently verify the count and results yourself
rather than trusting a static claim (see "How to verify the count
yourself" below).

**Run environment:** Python 3.12+, pytest 8.x, SQLite (test DB), no
`GROQ_API_KEY` set (AI pipeline tests exercise both the live-key and
no-key/heuristic-fallback code paths explicitly — see below).

**Command:**
```bash
python -m pytest -v
```

**Expected result:** `55 passed` (0 failures, 0 skips). If you see a
`StarletteDeprecationWarning` about `httpx`/`starlette.testclient`, that's
an unrelated upstream warning, not a problem with this codebase.

---

## Summary by module

| Module | File | Tests | What it covers |
|---|---|---|---|
| Engine | `tests/engine/test_cycle.py` | 4 | Cycle detection: acyclic seed graph, rejection of a cycle-forming edge, self-dependency rejection, valid edge acceptance |
| Engine | `tests/engine/test_diamond.py` | 2 | Non-compounding ("max-not-sum") scheduling across converging paths — duration delay and pinned-start delay |
| Engine | `tests/engine/test_blocked.py` | 2 | Initial Blocked/Ready derivation on the seed board; Invariant Gate rejection of advancing a blocked task |
| Engine | `tests/engine/test_invariants.py` | 4 | The Invariant Gate at the engine level: valid graph passes, cycle is caught, schedule violation is caught, blocked-task advancement is caught |
| Engine | `tests/engine/test_regression.py` | 2 | Un-completing a task re-blocks downstream tasks and flags already-Done descendants for reverification |
| Engine | `tests/engine/test_oracle_property.py` | 1 | Property test: incremental scheduler agrees with the brute-force oracle across 1,000 randomly generated graphs |
| API | `tests/api/test_boards.py` | 2 | Board retrieval (seeded board, 404 for missing board) |
| API | `tests/api/test_tasks.py` | 11 | Task CRUD, optimistic-concurrency `409 VERSION_CONFLICT`, blocked-move rejection, valid move, Why Panel explanation endpoint, impact-preview dry run, regression downgrade of downstream tasks, invalid-column rejection on move and create, same-column reorder |
| API | `tests/api/test_dependencies.py` | 8 | Cycle rejection via the API, self/duplicate dependency rejection, dependency deletion, AI suggestion generation (both heuristic-fallback and live-Groq-key paths), accept/reject flow, rate limiting |
| API | `tests/api/test_invariant_gate.py` | 1 | **New.** Drives an `INVARIANT_VIOLATION` (`BLOCKED_TASK_ADVANCED`) through the actual `POST /dependencies` endpoint — not just the engine — and asserts the 409, full transaction rollback (no dependency row persisted, task state untouched), and that the `invariant_gate_failed` audit record is still written on its own independent session despite the rollback |
| API | `tests/api/test_authorization.py` | 8 | Guest board reachable with no token; private board returns `401`/`403`/`200` correctly for no-token / wrong-user / owner requests, across both board and task-creation endpoints |
| API | `tests/api/test_auth.py` | 1 | Full auth flow: register, login, token issuance |
| API | `tests/api/test_cors_and_errors.py` | 2 | Pydantic validation errors return clean `400`s; CORS headers are present and correct |
| AI | `tests/ai/test_evidence_check.py` | 5 | Deterministic verification step: valid evidence survives, hallucinated evidence (not present in the prerequisite's own text) is dropped, evidence found only in the dependent's text (not the prerequisite's) is dropped, every drop is written to the audit log, and a Challenge-call failure resolves to a `not_run` verdict rather than crashing |
| AI | `tests/ai/test_propose_task_filter.py` | 2 | **New.** BUILD_SPEC.md §5.1's Propose-call task filter: a task already linked to the target task by an existing dependency edge is excluded from the prompt; a whole-board run (no single target) keeps every task in scope |

**Total: 55 / 55.**

---

## How to verify the count yourself

Don't take the table above on faith either — regenerate it from the actual
files:

```bash
python - <<'EOF'
import ast, os

total = 0
for root, _dirs, files in os.walk("tests"):
    for fn in sorted(files):
        if fn.startswith("test_") and fn.endswith(".py"):
            path = os.path.join(root, fn)
            with open(path) as f:
                tree = ast.parse(f.read(), filename=path)
            names = [n.name for n in ast.walk(tree)
                     if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
            print(f"{path}: {len(names)}")
            total += len(names)
print("TOTAL:", total)
EOF
```

This counts test functions directly from source (including ones nested in
`Test*` classes), independent of whatever pytest actually collects and
independent of whatever this file claims — so it can't drift the way the
old "47" count did.

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

## Verbatim output (captured 2026-09-28)

All **55 tests passed** successfully across the AI, API, and core Engine modules.

| Metric | Status / Value |
|---|---|
| Total Tests | 55 passed |
| Execution Time | 12.84s |
| Python Version | 3.13.15 |
| Pytest Version | 9.1.1 |

```
PS C:\Users\Harsh\Documents\GitHub\glassboard> python -m pytest -v
=============================================== test session starts ===============================================
platform win32 -- Python 3.13.15, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\Harsh\AppData\Local\Programs\Python\Python313\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\Harsh\Documents\GitHub\glassboard
plugins: anyio-4.13.0, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 55 items                                                                                                 

tests/ai/test_evidence_check.py::TestEvidenceCheckDropsBadProposals::test_hallucinated_evidence_not_in_prereq_text_is_dropped PASSED [  1%]
tests/ai/test_evidence_check.py::TestEvidenceCheckDropsBadProposals::test_valid_evidence_in_prereq_text_survives PASSED [  3%]
tests/ai/test_evidence_check.py::TestEvidenceCheckDropsBadProposals::test_evidence_only_in_dep_text_not_in_prereq_is_dropped PASSED [  5%]
tests/ai/test_evidence_check.py::TestEvidenceCheckDropsBadProposals::test_hallucinated_evidence_drop_is_written_to_audit_log PASSED [  7%]
tests/ai/test_evidence_check.py::TestEvidenceCheckDropsBadProposals::test_challenge_call_failure_results_in_not_run_verdict PASSED [  9%]
tests/ai/test_propose_task_filter.py::test_already_linked_task_excluded_from_propose_prompt PASSED           [ 10%] 
tests/ai/test_propose_task_filter.py::test_whole_board_run_keeps_every_task_in_scope PASSED                  [ 12%] 
tests/api/test_auth.py::test_auth_full_flow PASSED                                                           [ 14%]
tests/api/test_authorization.py::TestGuestBoardAlwaysAccessible::test_get_guest_board_no_token PASSED        [ 16%]
tests/api/test_authorization.py::TestGuestBoardAlwaysAccessible::test_get_guest_board_ai_suggestions_no_token PASSED [ 18%]
tests/api/test_authorization.py::TestPrivateBoardEnforcement::test_no_token_gets_401 PASSED                  [ 20%]
tests/api/test_authorization.py::TestPrivateBoardEnforcement::test_wrong_user_gets_403 PASSED                [ 21%]
tests/api/test_authorization.py::TestPrivateBoardEnforcement::test_owner_gets_200 PASSED                     [ 23%]
tests/api/test_authorization.py::TestPrivateBoardEnforcement::test_create_task_no_token_on_private_board_gets_401 PASSED [ 25%]
tests/api/test_authorization.py::TestPrivateBoardEnforcement::test_create_task_wrong_user_on_private_board_gets_403 PASSED [ 27%]
tests/api/test_authorization.py::TestPrivateBoardEnforcement::test_ai_suggestions_no_token_private_board_gets_401 PASSED [ 29%]
tests/api/test_boards.py::test_get_board_seeded PASSED                                                       [ 30%]
tests/api/test_boards.py::test_get_board_not_found PASSED                                                    [ 32%]
tests/api/test_cors_and_errors.py::test_validation_error_pydantic_clean_400 PASSED                           [ 34%] 
tests/api/test_cors_and_errors.py::test_cors_origin_headers PASSED                                           [ 36%]
tests/api/test_dependencies.py::test_cycle_rejection_api_t10_to_t2 PASSED                                    [ 38%]
tests/api/test_dependencies.py::test_self_dependency_rejection PASSED                                        [ 40%]
tests/api/test_dependencies.py::test_duplicate_dependency_rejection PASSED                                   [ 41%]
tests/api/test_dependencies.py::test_delete_dependency PASSED                                                [ 43%]
tests/api/test_dependencies.py::test_ai_suggestions_heuristic_fallback_when_key_unset PASSED                 [ 45%]
tests/api/test_dependencies.py::test_ai_suggestions_live_groq_when_key_set PASSED                            [ 47%]
tests/api/test_dependencies.py::test_ai_suggestion_accept_and_reject_flow PASSED                             [ 49%]
tests/api/test_dependencies.py::test_ai_suggestions_rate_limiting PASSED                                     [ 50%]
tests/api/test_invariant_gate.py::test_invariant_violation_via_new_dependency_on_advanced_task PASSED        [ 52%]
tests/api/test_tasks.py::test_create_task PASSED                                                             [ 54%]
tests/api/test_tasks.py::test_update_task_optimistic_concurrency_version_conflict PASSED                     [ 56%]
tests/api/test_tasks.py::test_update_task_valid PASSED                                                       [ 58%]
tests/api/test_tasks.py::test_move_task_blocked_rejection PASSED                                             [ 60%]
tests/api/test_tasks.py::test_move_task_success_when_ready PASSED                                            [ 61%]
tests/api/test_tasks.py::test_task_explanation_why_panel PASSED                                              [ 63%]
tests/api/test_tasks.py::test_task_impact_preview_dry_run PASSED                                             [ 65%]
tests/api/test_tasks.py::test_task_regression_downgrades_downstream_task PASSED                              [ 67%]
tests/api/test_tasks.py::test_task_move_invalid_column_rejected PASSED                                       [ 69%]
tests/api/test_tasks.py::test_task_create_invalid_column_rejected PASSED                                     [ 70%]
tests/api/test_tasks.py::test_same_column_reorder_persists PASSED                                            [ 72%]
tests/engine/test_blocked.py::test_initial_board_blocked_states PASSED                                       [ 74%] 
tests/engine/test_blocked.py::test_advancing_blocked_task_violates_invariants PASSED                         [ 76%] 
tests/engine/test_cycle.py::test_seed_graph_is_acyclic PASSED                                                [ 78%] 
tests/engine/test_cycle.py::test_cycle_rejection_t10_to_t2 PASSED                                            [ 80%] 
tests/engine/test_cycle.py::test_cycle_self_dependency PASSED                                                [ 81%] 
tests/engine/test_cycle.py::test_valid_dependency_no_cycle PASSED    [ 83%]
tests/engine/test_diamond.py::test_diamond_math_duration_delay PASSED                                        [ 85%]
tests/engine/test_diamond.py::test_diamond_math_pinned_start_delay PASSED                                    [ 87%]
tests/engine/test_invariants.py::test_invariants_pass_on_valid_seeded_graph PASSED                           [ 89%]
tests/engine/test_invariants.py::test_invariants_detect_cycle PASSED                                         [ 90%]
tests/engine/test_invariants.py::test_invariants_detect_schedule_violation PASSED                            [ 92%]
tests/engine/test_invariants.py::test_invariants_detect_blocked_task_advanced PASSED                         [ 94%]
tests/engine/test_oracle_property.py::test_property_1000_random_graphs_oracle_agreement PASSED               [ 96%]
tests/engine/test_regression.py::test_regression_when_tasks_were_done PASSED                                 [ 98%]
tests/engine/test_regression.py::test_regression_when_downstream_in_progress PASSED                          [100%]

=============================================== 55 passed in 12.84s ===============================================

```


**See also:** [`../docs/TESTING_SCENARIOS.md`](../docs/TESTING_SCENARIOS.md)
for the manual/guided demo scenarios (Blocked/Ready, the Why Panel,
cycle prevention, the AI copilot, regression, critical path, impact
preview, concurrency, and multi-tenant authorization) that complement
this automated suite, and [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)
for how each tested behavior is implemented.
