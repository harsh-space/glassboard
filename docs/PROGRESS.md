# TaskFlow Pro — Progress & Submission Log

**Status:** Complete — All 8 Core Phases + Pre-Submission Audit Verified  
**Branch:** `my_sub` (Submission) | `main`  
**Test Suite:** 47/47 Tests Passing (`pytest -v`)  
**Live Production:** [Vercel Frontend](https://glassboard-ten.vercel.app) | [Render API](https://glassboard-backend.onrender.com/docs) | Neon PostgreSQL  

---

## 1. Phase Completion Summary

| Phase | Milestone | Scope Delivered | Status |
| :--- | :--- | :--- | :--- |
| **Phase 1: Foundation** | Schema & Seeds | 10 tasks, 13 dependencies, SQLite/PostgreSQL support, zero secrets | **DONE** |
| **Phase 2: Engine** | Pure DAG Core | Cycle detection (BFS), max-not-sum scheduler, Invariant Gate, oracle test | **DONE** |
| **Phase 3: API & UI** | REST & Kanban | FastAPI CRUD, dnd-kit board, optimistic updates, rate limits, Pydantic v2 | **DONE** |
| **Phase 4: Persistence** | State & Invariants | Version conflict checks (`409`), blocked card reasons, refresh persistence | **DONE** |
| **Phase 5: AI Pipeline** | Copilot Guardrails | Propose → Challenge → Verify → Human approval, heuristic fallback | **DONE** |
| **Phase 6: Differentiators** | Explainability | Why Panel (driving prereqs + slack), skeptic badge, Ripple Toast | **DONE** |
| **Phase 7: Extensions** | Advanced Views | Critical path highlight, dry-run impact preview modal | **DONE** |
| **Phase 8: Polish** | Delivery Docs | Architecture doc, walkthrough demo script, AI measurement benchmarks | **DONE** |
| **Phase 9: Final Audit** | Security & AI Check | Board-level auth enforcement, prerequisite evidence validation | **DONE** |

---

## 2. Test Verification Matrix (47 Passed)

- **Engine Tests (15 passed):** Cycle rejection, diamond math (max-not-sum), rollback & regression, Invariant Gate, 1,000 random-graph oracle property test.
- **API Tests (20 passed):** Board loading, CRUD, drag/move rejection on blocked cards, Why Panel explanation, impact preview, rate limiting, CORS.
- **Authorization Tests (8 passed):** Public guest bypass (`board_id=1`), 401 unauthenticated on private boards, 403 cross-tenant rejection, owner access.
- **AI Pipeline Tests (4 passed):** Fabricated evidence rejection, prerequisite text substring check, audit log trail recording (`action='ai_suggestion_evidence_rejected'`).

---

## 3. Key Architecture & Submission Decisions

1. **Pure Engine Isolation:** Zero DB/web imports in `engine/`. Engine is independently testable without database or server.
2. **Deterministic Max-Not-Sum:** Delays propagate through the driving prerequisite only; parallel slack does not compound artificially.
3. **Guest Bypass with Private Enforcement:** Canonical demo board (`id=1`, `owner_id=NULL`) is open for instant evaluation; user-created boards require JWT authentication.
4. **AI Trust Guardrail:** Evidence phrases must strictly be a literal substring of the prerequisite task's text; hallucinations are dropped and logged to `audit_log`.
5. **AI Metrics:** Heuristic pipeline achieves **100.0% precision** and **84.6% recall** against the canonical seed board (measured via `scripts/measure_ai.py`).
