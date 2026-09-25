Data model (five tables).
Task: id, board id, title, description, column, position (fractional), duration in days, pinned start (optional), planned start, planned end, actual end (set when moved to Done), version number, timestamps.
Dependency: id, task id, prerequisite id, unique pair constraint, a check that the two ids differ, cascade delete with the task.
AI Suggestion: id, task id, candidate prerequisite id, reason, evidence phrase, proposer confidence, challenge verdict, status (pending, accepted, rejected), model name, prompt version.
Audit Log: id, action, payload, timestamp, source (human or AI). It supports change history and the AI declaration.
Board: id, name, start date.
Blocked and Ready, driving prerequisite and slack are recomputed on every change and returned by the API, never stored, so they cannot go stale.

Key assumptions: links are finish to start; dates are whole calendar days with no weekends or holidays; a prerequisite is satisfied only when it is in Done; a task with no constraint starts on the board start date; marking a task Done early pulls unpinned successors forward, and the Why Panel states that reason; each board holds one graph; the demo uses one shared workspace, and login is a documented extension.

Security and privacy: I validate all input with Pydantic schemas, use SQLAlchemy parameterized queries, rely on React output escaping, limit CORS to the frontend origin and rate limit the AI endpoint. The LLM API key stays in server environment variables and never reaches the browser. Only the task titles and descriptions needed for dependency reasoning are sent to the model; secrets, credentials and unrelated project data are excluded. Optimistic concurrency control returns HTTP 409 when a stale client tries to overwrite a newer task version, and each dependency write is validated and committed atomically.

Feasibility in the sprint window: as a solo builder I fix the API contract in the first hours and build in layers, so the engine, interface and AI pipeline can each be built and tested independently. The Why Panel only reads data the recompute already produces. My seed script loads 10 tasks, including a diamond with one slack branch and a three level chain, so I can exercise the board from day one. If I reach deployment it uses a managed PostgreSQL instance; SQLite is for local development only.