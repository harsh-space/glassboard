# TaskFlow Pro — Progress Log

Current Status: Phase 8 Complete — Ready for Submission
Last Updated: 2026-09-26

---

## Build-Order Checklist (CLAUDE.md §3 / BUILD_SPEC.md §7)

### Phase 1 — Foundation (DONE)
- [x] Repo structure initialized per `CLAUDE.md` §4.
- [x] `.gitignore` committed before any other file.
- [x] No secrets present in repo (verified with grep).
- [x] `.env.example` committed with dummy values.
- [x] DB schema (`backend/models.py`, `backend/db.py`) created.
- [x] Seed script (`scripts/seed.py`) loads all 10 tasks and 13 dependencies.
- [x] `GET /boards/{id}` returns the seeded board with correct derived fields.

### Phase 2 — Engine (DONE)
- [x] `engine/` pure Python module with zero DB or web imports (verified with grep).
- [x] Cycle detection (`engine/graph.py`).
- [x] Scheduling recompute (`engine/scheduler.py`).
- [x] Blocked/Ready derivation (`engine/derive.py`).
- [x] Regression handling (`engine/derive.py` + `scheduler.py`).
- [x] Invariant Gate (`engine/invariants.py`).
- [x] Brute-force test oracle (`engine/oracle.py`).
- [x] All tests pass (§8.1) — 34 tests total (15 in `tests/engine/`, 19 in `tests/api/`), including the 1,000 random graph oracle property test.


### Phase 3 — API and Board UI (DONE)
- [x] All API endpoints in `BUILD_SPEC.md` §4 implemented.
- [x] Pydantic validation on all requests.
- [x] CORS limited to frontend origin.
- [x] AI endpoint rate limited (1 req / 5s per board).
- [x] LLM API key server-side only.
- [x] Board UI rendered with dnd-kit.
- [x] Forms for tasks and dependencies.
- [x] All 34 unit and integration tests passing (`pytest -v`).

### Phase 4 — Wiring and Persistence (DONE)
- [x] Refresh preserves board state (verified via DB persistence).
- [x] Blocked reasons shown on cards (`blocking_prerequisite_ids`).
- [x] Optimistic updates and rollback.
- [x] `409 VERSION_CONFLICT` handling in UI & API.

### Phase 5 — Minimal AI Path (DONE)
- [x] Propose → Verify → Human approval pipeline (Groq allam-2-7b integration).
- [x] Fallback heuristic if API key is unset or error occurs (tested & passing).
- [x] `AI_TOOL_DECLARATION.md` updated with provider/model details (`allam-2-7b` via Groq).

### Phase 6 — Differentiators (DONE)
- [x] Why Panel core (driving prerequisite + slack) (API + UI implemented).
- [x] AI challenge pass (skeptic badge rendered in UI).
- [x] Ripple view (`RippleToast` component implemented).

### Phase 7 — Optional Extensions (DONE)
- [x] Critical path view (API endpoint + UI toggle implemented).
- [x] Impact preview dry-run (API endpoint + UI modal implemented).

### Phase 8 — Delivery Polish (DONE)
- [x] `docs/ARCHITECTURE.md` written against actual build.
- [x] `README.md` setup and run instructions.
- [x] `scripts/measure_ai.py` benchmarks recorded.
- [x] Clean security audit (verified zero secrets, git ignores active).
- [x] Demo script prepared (`docs/DEMO_SCRIPT.md`).


---

## Escalated Decisions Log (BUILD_SPEC.md §10)
1. **`actual_end` semantics**: Confirmed by user (2026-09-25) — set `actual_end = planned_end` when task is moved to Done.
2. **Submission branch name**: Confirmed by user (2026-09-25) — `main` is final.
3. **LLM provider**: Confirmed by user (2026-09-25) — Groq API with `allam-2-7b`.
4. **Deployment target**: [PROPOSED] SQLite locally, PostgreSQL on managed platform (Render / Fly / Railway) — awaiting decision before final deployment.

---

## Current Activity
- Configured Groq API integration with model `allam-2-7b` in `backend/ai/pipeline.py` and `.env.example`.
- Verified 34/34 test suite passes; system operates with Groq LLM when key is provided, or heuristic fallback if unset.



