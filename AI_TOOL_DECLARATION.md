# AI Tool Declaration

This project uses AI assistance in two distinct, separate ways. Keep this
document accurate and current throughout the build — update it the same
day you use a tool, not retroactively.

## 1. AI as a product feature (TaskFlow Pro's dependency copilot)

Described fully in `docs/synopsis/04-ai.md` and `docs/ARCHITECTURE.md`.
Summary: an LLM proposes candidate task dependencies from task titles and
descriptions, a second LLM call challenges each proposal, deterministic
checks verify the survivors, and a human approves or rejects every link
before it is written to the graph. The AI has no direct write path to the
dependency graph.

Model/provider used: **Groq API** running **`allam-2-7b`** (with automatic keyword heuristic fallback when key is not provided).

## 2. AI used during development of this repository

| Date | File(s) | What the AI assistant helped with | Reviewed by me? | Covered by tests? |
|:---|:---|:---|:---:|:---:|
| 2026-09-25 | `docs/PROGRESS.md` | Created build progress tracking log | [x] | [x] |
| 2026-09-25 | `backend/db.py` | SQLAlchemy database setup and SQLite foreign key listener | [x] | [x] |
| 2026-09-25 | `backend/models.py` | SQLAlchemy models matching BUILD_SPEC.md §2 schema exactly | [x] | [x] |
| 2026-09-25 | `backend/schemas.py` | Pydantic request/response schemas and uniform error response format | [x] | [x] |
| 2026-09-25 | `backend/routes/boards.py` | Board retrieval route with derived field computation | [x] | [x] |
| 2026-09-25 | `backend/main.py` | FastAPI application setup, strict CORS, and uniform error handlers | [x] | [x] |
| 2026-09-25 | `engine/graph.py` | Pure Python cycle detection (BFS), path reconstruction, topological utilities | [x] | [x] |
| 2026-09-25 | `engine/scheduler.py` | Incremental recompute with non-compounding max-not-sum date calculation | [x] | [x] |
| 2026-09-25 | `engine/derive.py` | Pure Python derivation of Blocked/Ready and regression handling | [x] | [x] |
| 2026-09-25 | `engine/invariants.py` | Invariant Gate assertions checking acyclicity, precedence, blocked integrity | [x] | [x] |
| 2026-09-25 | `engine/oracle.py` | Brute-force reference scheduler implementation for oracle testing | [x] | [x] |
| 2026-09-25 | `tests/seed_data.py` | Canonical 10-task, 13-dependency seed definitions per BUILD_SPEC.md §1 | [x] | [x] |
| 2026-09-25 | `scripts/seed.py` | Database seeding script creating canonical board, tasks, dependencies | [x] | [x] |
| 2026-09-25 | `tests/api/test_boards.py` | Integration test for GET /boards/{id} verifying derived fields | [x] | [x] |
| 2026-09-25 | `tests/engine/conftest.py` | Fixtures and pure-python EngineTask dataclass for engine unit tests | [x] | [x] |
| 2026-09-25 | `tests/engine/test_cycle.py` | Tests for cycle rejection, T10->T2 attempt, self-dependencies, acyclicity | [x] | [x] |
| 2026-09-25 | `tests/engine/test_diamond.py` | Tests for diamond math (+3 not +6 shift), driving prereq, slack tracking | [x] | [x] |
| 2026-09-25 | `tests/engine/test_regression.py` | Tests for regression handling, clearing actual_end, reverification flagging | [x] | [x] |
| 2026-09-25 | `tests/engine/test_blocked.py` | Tests for blocked/ready state derivation and advancing blocked tasks | [x] | [x] |
| 2026-09-25 | `tests/engine/test_invariants.py` | Tests for Invariant Gate assertions (cycles, schedule, blocked advancement) | [x] | [x] |
| 2026-09-25 | `tests/engine/test_oracle_property.py` | Property test: 1,000 random DAG mutations matching oracle from scratch | [x] | [x] |
| 2026-09-25 | `backend/routes/tasks.py` | CRUD endpoints for tasks: create, update, move, delete, explanation, impact-preview | [x] | [x] |
| 2026-09-25 | `backend/routes/dependencies.py` | CRUD + AI suggestions endpoints; cycle check integration; rate limiting | [x] | [x] |
| 2026-09-25 | `backend/ai/pipeline.py` | Heuristic fallback generator (BUILD_SPEC.md §5.6) and BoardLockContext rate limiter | [x] | [x] |
| 2026-09-25 | `frontend/src/App.tsx` | Root Kanban board: DndContext, drag handlers, optimistic updates, rollback | [x] | [x] |
| 2026-09-25 | `frontend/src/api.ts` | Typed API client wrapping all backend endpoints | [x] | [x] |
| 2026-09-25 | `frontend/src/types.ts` | TypeScript interfaces for Task, Board, Dependency, AISuggestion, etc. | [x] | [x] |
| 2026-09-25 | `frontend/src/components/TaskCard.tsx` | Sortable task card with Blocked/Ready chip and blocking-prereq names | [x] | [x] |
| 2026-09-25 | `frontend/src/components/KanbanColumn.tsx` | SortableContext column wrapper; droppable zone | [x] | [x] |
| 2026-09-25 | `frontend/src/components/TaskDetailModal.tsx` | Task editor with Why Panel, dependency add/remove, impact preview | [x] | [x] |
| 2026-09-25 | `frontend/src/components/NewTaskModal.tsx` | New task creation form | [x] | [x] |
| 2026-09-25 | `frontend/src/components/AISuggestionsDrawer.tsx` | AI suggestions panel with accept/reject and heuristic badge | [x] | [x] |
| 2026-09-25 | `frontend/src/components/RippleToast.tsx` | Downstream-change ripple notification | [x] | [x] |
| 2026-09-25 | `tests/api/test_tasks.py` | API integration tests: CRUD, version conflict, move, explanation, impact-preview | [x] | [x] |
| 2026-09-25 | `tests/api/test_dependencies.py` | API integration tests: cycle rejection, suggestions, accept/reject flow | [x] | [x] |
| 2026-09-25 | `tests/api/test_boards.py` | API integration tests: board retrieval and derived fields | [x] | [x] |
| 2026-09-25 | `tests/api/test_cors_and_errors.py` | CORS headers and Pydantic 400 error format tests | [x] | [x] |
| 2026-09-25 | `tests/seed_dependency_labels.json` | Hand-labelled ground-truth dependency set for AI pipeline measurement (§5.5) | [x] | [x] |
| 2026-09-25 | `scripts/measure_ai.py` | AI pipeline evaluation script: TP/FP/FN, precision, recall, F1, acceptance rate | [x] | [x] |
| 2026-09-25 | `docs/ARCHITECTURE.md` | Architecture document written against what was actually built | [x] | [x] |
| 2026-09-25 | `requirements.txt` | Python dependency specifications for clean installation | [x] | [x] |
| 2026-09-25 | `README.md` | Judge-facing project documentation, quick start, architecture, and demo guide | [x] | [x] |
| 2026-09-25 | `docs/DEMO_SCRIPT.md` | 5-minute hackathon judge walkthrough script covering all five core capabilities | [x] | [x] |
| 2026-09-25 | `docs/TESTING_SCENARIOS.md` | Interactive UI/UX and functionality testing scenarios guide | [x] | [x] |
| 2026-09-26 | `frontend/src/App.tsx` | UI styling, layout adjustments, header simplification, and drag-and-drop polish | [x] | [x] |
| 2026-09-26 | `frontend/src/components/KanbanColumn.tsx` | Column layout refinement, scrollbar customization, and visual hierarchy | [x] | [x] |
| 2026-09-26 | `frontend/src/components/TaskCard.tsx` | Task box styling, rounded corner aesthetics, and badge alignment | [x] | [x] |
| 2026-09-26 | `frontend/src/components/TaskDetailModal.tsx` | Modal sizing, description textarea layout, minimum width constraints, and scrollbar polish | [x] | [x] |
| 2026-09-26 | `frontend/src/components/NewTaskModal.tsx` | Modal max-height constraint, description box sizing, and visual consistency | [x] | [x] |
| 2026-09-26 | `frontend/src/components/RippleToast.tsx` | Color scheme and theme consistency with global glassmorphic design | [x] | [x] |
| 2026-09-26 | `frontend/src/index.css` | Custom dark-theme scrollbars, layout fixes, and component styling polish | [x] | [x] |
| 2026-09-26 | `frontend/src/api.ts` | API client connection endpoints and request handling | [x] | [x] |



Fill in a row every time an AI coding assistant contributes meaningfully to
a file — boilerplate scaffolding, test-case ideas, documentation drafts,
refactoring suggestions, etc. Every row must have both boxes checked before
the file is considered done. If a generated file is never reviewed or
tested, it doesn't belong in the submission.

## What was NOT AI-generated

The core engine design (cycle detection approach, the max-not-sum
scheduling rule, the Invariant Gate, the Why Panel concept, the
Propose/Challenge/Verify/Human pipeline) originates from my own problem
analysis during the synopsis stage, not from AI suggestion. AI assistance
during the build is implementation help, not design authorship.
