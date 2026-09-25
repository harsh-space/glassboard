The Taskflow brief reads like a request for a Kanban board, but the real problem is that ordinary Kanban treats cards as independent while real engineering work is a network of prerequisites. When the database schema slips, the backend API and the integration tests slip with it, and today someone must notice and re-edit every date by hand. My reading: the board is only the interface. The product is a dependency aware execution engine that decides what is ready, what is blocked and what moves when something changes. The users I have in mind are engineering teams, product teams and technical project leads.

Failure modes I identified and will design against:
1. Converging paths. This is the subtle one. In a diamond (A to B to D and A to C to D) a 3 day delay in A must move D by 3 days, not 6. Delay is decided by the latest finishing prerequisite, not by a sum over paths. Naive per path propagation compounds the shift, so a topological order alone is not enough.
2. Derived state. Blocked and Ready follow from the graph. If they are stored they go stale the moment a prerequisite changes, so I compute them and never persist them.
3. Cycles. A to B to C to A must be rejected before anything is saved, with a message naming the loop, and the stored graph must stay untouched.
4. Regression. Moving a Done task back to In Progress must re-block dependents at every downstream level.
5. Invalid drags. Dragging a Blocked card into In Progress must be refused by the engine, not just styled differently. A column change is a state transition that must respect the dependency model.
6. Trust in automation. Date changes nobody can explain get overridden by hand, so every automatic move must show its cause.
7. AI trust. An LLM can suggest dependencies but can also invent or reverse them, so a suggestion stays a proposal until deterministic checks and a human approve it.
8. Persistence and simultaneous edits. State must survive a refresh, and a stale client must not silently overwrite newer data.

Further edge cases I will handle: self dependency, duplicate links, deleting a task that has dependents, tasks with no links and missing dates.

Success means the board can never show a state that contradicts the dependency graph, and every automatic change can be explained.