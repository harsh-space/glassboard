Two goals drive the design: correctness (the board never contradicts the dependency graph) and trust (every automatic change can be explained). Four pillars serve them: a deterministic DAG engine as source of truth, non compounding incremental scheduling, explainable automation and a guardrailed AI copilot. Stack: React, TypeScript, dnd-kit, FastAPI, SQLAlchemy, SQLite locally, PostgreSQL in deployment. The engine is pure Python with no database or web code, so I can test it alone first. Every change is one transaction ending in the Invariant Gate.

Layer 1, must have (the engine)
1. Cycle prevention. For a proposed link from P to T, I traverse from T through its existing successors. If P is reachable, the link would close a cycle, so the API rejects it with HTTP 409 and the loop path. Nothing is written.
2. Scheduling. End is start plus duration. Start is the latest of the pinned earliest start and, for each prerequisite, its actual finish if Done, else its planned end. Because this is a maximum and not a sum, each task is computed once, so the diamond gives D plus 3 days, never plus 6. On a change I recompute only the affected descendants in topological order, with work proportional to the affected subgraph.
3. Blocked and Ready. Derived, never stored: Blocked if any prerequisite is not Done, else Ready. The engine refuses to move a Blocked card into In Progress. On regression (Done back to In Progress) I walk downstream: dependents become Blocked and Done dependents are flagged for re-verification.

Layer 2, differentiators (the AI copilot is in Section 4)
4. Why Panel (explainability). Each recompute records the driving prerequisite of every task and the slack on the others. Clicking a card explains its date, for example: moved 3 days because Backend API ended later, Schema Design had 2 days of slack. A ripple view after an edit lists moved tasks, their causes and the tasks that absorbed the change.
5. Invariant Gate (validation). Before commit, cheap assertions check the new schedule: graph acyclic, no start earlier than a prerequisite end, Blocked flags consistent. A failure aborts the transaction. A brute force oracle exists only in tests.

Layer 3, optional extensions: critical path view and impact preview. Deployment is delivery polish.

API: GET board; POST and PATCH tasks; POST task move; POST and DELETE dependencies; POST dependency suggestions; GET task explanation.