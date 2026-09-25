# TaskFlow Pro — Progress Log

Current Status: Phase 1 & Phase 2 Complete — Ready for Phase 3 (API & Board UI)
Last Updated: 2026-09-25

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
- [x] All tests in `tests/engine/` pass (§8.1) — 15 tests including 1,000 random graph oracle property test.


### Phase 3 — API and Board UI (PENDING)
- [ ] All API endpoints in `BUILD_SPEC.md` §4 implemented.
- [ ] Pydantic validation on all requests.
- [ ] CORS limited to frontend origin.
- [ ] AI endpoint rate limited.
- [ ] LLM API key server-side only.
- [ ] Board UI rendered with dnd-kit.
- [ ] Forms for tasks and dependencies.

### Phase 4 — Wiring and Persistence (PENDING)
- [ ] Refresh preserves board state.
- [ ] Blocked reasons shown on cards.
- [ ] Optimistic updates and rollback.
- [ ] `409 VERSION_CONFLICT` handling.

### Phase 5 — Minimal AI Path (PENDING)
- [ ] Propose → Verify → Human approval pipeline.
- [ ] Fallback heuristic if API key is unset or error occurs.
- [ ] `AI_TOOL_DECLARATION.md` updated with provider/model details.

### Phase 6 — Differentiators (PENDING)
- [ ] Why Panel core (driving prerequisite + slack).
- [ ] AI challenge pass (skeptic).
- [ ] Ripple view.

### Phase 7 — Optional Extensions (PENDING)
- [ ] Critical path view.
- [ ] Impact preview dry-run.

### Phase 8 — Delivery Polish (PENDING)
- [ ] `docs/ARCHITECTURE.md` written against actual build.
- [ ] `README.md` setup and run instructions.
- [ ] `scripts/measure_ai.py` benchmarks recorded.
- [ ] Clean security audit.
- [ ] Demo script prepared.

---

## Escalated Decisions Log (BUILD_SPEC.md §10)
1. **actual_end semantics**: Confirmed with user — use `planned_end` when task moved to Done for test determinism.
2. **Submission branch name**: Confirmed with user — proceed on `main`, create submission branch when requested.
3. **LLM provider**: To be finalized before Phase 5.
4. **Deployment target**: To be finalized before Phase 8.

---

## Current Activity
- Building Phase 1 foundation: Backend DB models (`backend/models.py`), database setup (`backend/db.py`), schemas (`backend/schemas.py`), seed script (`scripts/seed.py`), and board retrieval endpoint.
