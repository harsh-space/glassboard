# TaskFlow Pro — Agent Operating Document

This file is the source of truth for how this repository gets built. Read it
in full before writing any code. It exists so that every session — yours or
a future one — builds toward the same target instead of drifting from the
submitted synopsis or re-litigating decisions that are already made.

Solo hackathon build. Target: #1 prize spot, not just a passing submission.
Build window: 72 hours from selection. This file itself does not count
toward that window — writing it is setup, not build time.

---

## 0. What this project actually is

Two goals drive every design decision. Anything that doesn't serve one of
these two goals is out of scope until the must-have layer is done and tested:

1. **Correctness** — the board can never show a state that contradicts the
   dependency graph.
2. **Trust** — every automatic change the system makes can be explained.

The Kanban board is *only* the interface. The product is a dependency-aware
execution engine that decides what is ready, what is blocked, and what
moves when something changes. Four pillars serve the two goals above: a
deterministic DAG engine as the single source of truth, non-compounding
incremental scheduling, explainable automation (the Why Panel), and a
guardrailed AI dependency copilot that can propose but never write.

**Non-negotiable engineering rule:** the graph engine is a pure Python
module with zero database imports and zero web-framework imports. It must
be importable and fully testable with nothing running — no server, no DB.
If you find yourself importing `fastapi` or `sqlalchemy` inside the engine
package, stop — that import does not belong there.

---

## 1. Where the synopsis lives

The exact text submitted to the hackathon platform is in `docs/synopsis/`,
one file per section (`01-problem.md` through `06-risks.md`). That text is
frozen — do not rephrase it, "improve" it, or let this file's summaries
drift from it. If code and synopsis ever disagree, the synopsis is what
the judges already read, so either the code is wrong or the mandatory
architecture doc (see §7) needs to explain the deviation explicitly. Never
silently diverge.

One known gap: the submitted Section 4 (AI/LLM Usage) does not include the
sentence disclosing that an AI coding assistant is used during development.
That disclosure is still mandatory in practice — see §6, AI Tool
Declaration. Treat it as a repo requirement regardless of the synopsis text.

---

## 2. Evaluation weights — build in this order, not file-tree order

| Criterion | Weight | What actually earns the points |
|---|---|---|
| Functional Correctness | 20% | Cycle detection, diamond math (max not sum), rollback/regression, all working exactly as the synopsis describes |
| Code Quality & Architecture | 20% | Clean layer separation (engine has no DB/web imports), sound error handling, no dead code |
| AI/LLM Usage | 15% | The Propose→Challenge→Verify→Human pipeline working, AND a disclosed, honest AI Tool Declaration for the build process itself |
| Documentation & Explainability | 13% | The combined architecture/data-model/known-limitations doc (mandatory), clear setup steps, a demo that shows the Why Panel |
| Business Impact & Scalability | 12% | The metrics from Section 5 actually measured, not just claimed |
| Feasibility/Security/Prod Readiness | 10% | No secrets committed, `.gitignore` correct from commit 1, deployment story credible |
| Testing & Reliability | 10% | Tests for cycles, the diamond case, regression, and the 1,000-random-graph oracle comparison — written alongside the engine, not after |

Two consequences:

- **20 + 20 + 10 = 50%** of the grade is the engine and its tests. Nothing
  else matters if this is wrong. Build and test the engine completely
  before writing a single line of frontend code.
- **AI/LLM Usage is 15%, mandatory, and judged on responsible disclosed
  use** — this is not a bonus feature. A working minimal AI path (propose,
  verify, human approval) belongs in the survival scope, not the stretch
  goals.

---

## 3. Build order (the actual priority stack)

This is the priority order from Section 6 of the synopsis. Do not
reorder it. If time runs short, cut from the bottom, never skip ahead.

**Survival scope (must exist and be tested before anything else):**
1. Repository, schema, seed data (10 tasks, one diamond with a slack
   branch, one three-level chain), fixed API contract.
2. Graph engine: cycle detection, non-compounding propagation, Blocked/Ready
   derivation, regression/rollback — each with tests, including the
   diamond case and the brute-force oracle comparison on random graphs.
3. API endpoints and persistence, board UI with drag and drop, task and
   dependency forms, real error messages (not silent failures).
4. End-to-end wiring, Blocked reasons visible on cards, refresh
   persistence.
5. Minimal AI path: propose → deterministic verify → human approval.
   This is required, not optional, because AI usage is a graded criterion.

**Differentiators (build once survival scope is tested):**
6. Why Panel core (driving prerequisite + slack, explains every date).
7. AI challenge pass (the skeptic call) and the ripple view.

**Optional extensions (only if ahead of schedule):**
8. Critical path view, impact preview (dry run before confirming).

**Delivery polish (last, always):**
9. README with Key Assumptions and Limitations, demo run, deployment if
   ready, buffer time.

If you're an agent picking up work mid-build: check `docs/PROGRESS.md`
(create it if missing) to see which numbered item is current before
starting anything.

---

## 4. Repository structure

```
/
├── CLAUDE.md                  # this file
├── README.md                  # setup/run instructions (judge-facing)
├── .gitignore                 # see §6 before first commit
├── AI_TOOL_DECLARATION.md     # mandatory, updated as you go — see §6
├── docs/
│   ├── synopsis/               # frozen, verbatim submitted text
│   │   ├── 01-problem.md
│   │   ├── 02-solution.md
│   │   ├── 03-data.md
│   │   ├── 04-ai.md
│   │   ├── 05-impact.md
│   │   └── 06-risks.md
│   ├── ARCHITECTURE.md         # mandatory combined design doc — see §7
│   └── PROGRESS.md             # running log of which build-order item is done
├── engine/                     # pure Python, zero DB/web imports — see §0
│   ├── __init__.py
│   ├── graph.py                # cycle detection (BFS from T through successors)
│   ├── scheduler.py            # start/end computation, the max-not-sum rule
│   ├── derive.py                # Blocked/Ready, driving prerequisite, slack
│   ├── invariants.py           # the Invariant Gate assertions
│   └── oracle.py                # brute-force reference implementation, TEST ONLY
├── backend/
│   ├── main.py                  # FastAPI app
│   ├── models.py                # SQLAlchemy models: Task, Dependency, AISuggestion, AuditLog, Board
│   ├── schemas.py                # Pydantic request/response schemas
│   ├── routes/
│   ├── ai/                       # propose / challenge / verify pipeline
│   └── db.py
├── frontend/
│   ├── src/
│   └── ...                       # React + TypeScript + dnd-kit
├── tests/
│   ├── engine/                   # cycle tests, diamond test, regression test, random-graph oracle test
│   ├── api/
│   └── seed_data.py               # the 10-task seed with the diamond + chain
└── scripts/
    └── seed.py
```

Engine tests must be runnable with no server, no DB, no frontend build.
That separation is itself evidence for the Code Quality criterion — make
it easy for a judge skimming the repo to see it.

---

## 5. Design reference

A separate `design.md` (Anthropic's public style reference) sets the visual
language for the frontend: colors, typography, spacing. Use it for the
Kanban board's look and feel. It has no bearing on architecture or the
engine — don't let visual polish pull time away from the engine before
it's tested. Frontend work starts at build-order item 3, not before.

---

## 6. Prohibited content — check before every commit

Per the hackathon rules, none of the following may ever be committed:

- API keys, passwords, tokens, or certificates (LLM API key must only ever
  live in an environment variable, never in code, never in a committed
  `.env` file)
- Production or confidential business data
- Malware or unauthorized network tools
- Virtual environments or dependency directories (`venv/`, `node_modules/`,
  `__pycache__/`, etc.)
- Pirated licensed software or code
- Large model weights
- Large media files
- Unnecessary build artifacts

Set up `.gitignore` in the very first commit, before any code, covering at
minimum: `.env`, `venv/`, `node_modules/`, `__pycache__/`, `*.db`,
`dist/`, `build/`. Never commit `.env` — commit `.env.example` with dummy
values instead.

**AI Tool Declaration** (`AI_TOOL_DECLARATION.md`, mandatory in practice —
see §1): keep a running, honest list of what an AI coding assistant helped
with (boilerplate, test-case ideas, documentation drafts), and confirm each
generated file was reviewed and covered by tests. Update it as you go, not
retroactively at hour 71.

**Branch name**: final source code must be submitted via a specific branch
name in the public GitHub repo, per the submission checklist. Confirm the
required branch name from the hackathon platform and record it in
`docs/PROGRESS.md` — do not guess it.

---

## 7. The mandatory architecture/data-model/known-limitations doc

This is a required checklist item, separate from the README and separate
from the frozen synopsis. It documents what was *actually built*, which
will diverge from the plan in small ways as the 72 hours progress — that's
expected and fine, as long as it's documented rather than hidden. Draft
this once the engine and API exist; do not try to write it from the plan
alone. It should cover: the real data model (matching `backend/models.py`
exactly), the real architecture (matching the actual code layout), and an
honest known-limitations section — expand the synopsis's list if the build
surfaced more.

---

## 8. Key assumptions locked in the synopsis (do not silently change these)

- Dependency links are finish-to-start only.
- Dates are whole calendar days, no weekends or holidays modeled.
- A prerequisite is satisfied only when it is in the Done column.
- A task with no constraint starts on the board's start date.
- Marking a task Done early pulls its unpinned successors forward — and the
  Why Panel must state this as the reason when it happens, so it reads as a
  feature, not a bug.
- Each board holds exactly one graph.
- The demo uses one shared workspace; login/auth is a documented extension,
  not a build target.

If any of these needs to change during the build, update
`docs/synopsis-deviations.md` (create if needed) explaining why — don't
just change behavior silently.
