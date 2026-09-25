Technical risks and mitigations:
1. Compounding or stale schedule bug (highest risk). Maximum based start rule, engine built first as a pure module, the Invariant Gate, a brute force test oracle, randomized graph tests, and fixed tests for the diamond and multi level chains.
2. Concurrent edits or drag races. One transaction per change, atomic dependency validation, version field returning HTTP 409, optimistic interface with rollback.
3. LLM hallucination, wrong link direction, latency, outage or cost. Closed id list, evidence check, challenge pass, engine cycle check, timeout, retry, heuristic fallback, rate limit and human approval.
4. Ephemeral disks on hosted platforms lose SQLite data. Managed PostgreSQL in deployment, SQLite only locally.
5. Scope creep. Priority order: (1) survival scope: engine with Invariant Gate, cycle detection, propagation, Blocked and Ready, regression, persistence, Kanban board and a minimal AI path (propose, verify, human approval), since AI use is required; (2) Why Panel core; (3) challenge pass and ripple view; (4) critical path and impact preview. Deployment is delivery polish. If I fall behind I cut from the bottom up.

Known limitations: finish to start links only; whole day durations; calendar days with no holidays; one graph per board; basic access control; no resource leveling; AI quality depends on clear task titles; boards beyond several thousand tasks are not tuned.

Execution plan across the sprint window:
1) repository, schema, seed of 10 tasks, API contract, test setup.
2) engine with tests for cycles, propagation, Blocked and Ready, regression, plus the test oracle and random graph tests. Driving prerequisite and slack tracked.
3) FastAPI endpoints and persistence, board with drag and drop, task and dependency forms, error messages.
4) end to end wiring, Blocked reasons on cards, Why Panel core, refresh persistence checks.
5) AI pipeline (propose, challenge, verify), ghost links, fallback, AI declaration.
6) ripple view, then optional extensions as time allows (critical path view, impact preview), plus empty states and responsive layout.
7) delivery polish: README with Key Assumptions and Limitations, demo run, deployment if ready, buffer.