Business impact: teams lose time and trust when dependency slips are noticed late or changed without explanation. TaskFlow Pro turns dependency tracking into an automatic, explainable guarantee. The targets below are internal evaluation targets that I will demonstrate on the seeded board and a scripted benchmark, not claims from field data.

Efficiency: in a chain of 10 tasks, one upstream change needs 1 edit instead of up to 9, because the engine propagates it to every descendant.

Correctness:
- Zero circular dependencies persisted; every cycle attempt in my test suite rejected with the stored graph unchanged.
- The diamond case moves D by exactly 3 days.
- No invalid graph or schedule state is ever persisted: every committed state passes the Invariant Gate.
- Engine and test oracle agree on 1,000 generated valid DAGs and their random schedule mutations.
- Every automatically moved task shows its cause in the Why Panel.

Performance targets:
- Cycle check, propagation and Invariant Gate together under 100 ms on 1,000 tasks and 3,000 dependencies.
- Board load under 300 ms at 500 tasks.
- Drag and drop persisted and confirmed in under 150 ms.
- AI suggestions within 8 seconds in the common case.

Reliability: board state survives a refresh; a stale edit is detected and rejected with HTTP 409; the board keeps working when the LLM is down.

AI: the primary metric is raw counts of correct, wrong and missed suggestions, plus acceptance rate, on the hand labelled seeded graph of about 10 tasks. Internal targets, not claims: 85 percent precision and 70 percent recall.

Scalability: the API is stateless and scales horizontally. The graph is scoped per board, which keeps each graph small. Incremental recompute touches only descendants of the changed task, and PostgreSQL indexes on task and prerequisite ids keep link lookups fast. Later extensions: working calendars and live sync.

Cost: the engine is provider independent, LLM use is optional and rate limited, and small managed services keep running cost low.