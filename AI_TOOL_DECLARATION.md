# AI Tool Declaration

TaskFlow Pro uses AI in two distinct, unrelated ways. Conflating them would
misrepresent both, so they're kept fully separate below.

## 1. AI as a product feature — the dependency copilot

Full design in [`docs/synopsis/04-ai.md`](docs/synopsis/04-ai.md), full
implementation detail in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
In short: an LLM proposes candidate task dependencies from task titles and
descriptions, a second LLM call challenges each proposal, deterministic
code verifies the survivors (including running the engine's own cycle
check against every candidate), and a human approves or rejects every
link before it's written to the graph. The model has no direct write path
to the dependency graph anywhere in the code.

**Model/provider:** Groq API running `allam-2-7b`, with an automatic
keyword-heuristic fallback when no API key is configured.

## 2. AI assistance during development of this repository

An AI coding assistant was used substantially throughout the build — for
scaffolding, implementation of the algorithms specified in
[`BUILD_SPEC.md`](BUILD_SPEC.md), test-case generation, and documentation
drafting. Every file it touched was reviewed and is covered by the
automated test suite (`pytest -v`, 55 passing as of this revision — see
[`tests/README.md`](tests/README.md) for the exact, source-verified count
and how to reproduce it) before being considered
done; nothing generated-but-untested made it into the submission.

Roughly, by area:

- **Engine (`engine/`)** — all five modules (cycle detection, the
  max-not-sum scheduler, Blocked/Ready derivation, the Invariant Gate, and
  the brute-force oracle) were implemented with AI assistance directly
  against the algorithms specified in `BUILD_SPEC.md` §3, then verified
  against the property test comparing the incremental scheduler to the
  oracle across 1,000 random graphs.
- **Backend (`backend/`)** — FastAPI app setup, SQLAlchemy models,
  Pydantic schemas, all REST routes, the JWT auth layer, and the AI
  pipeline (`backend/ai/pipeline.py`) were built with AI assistance and
  are covered by the API and authorization test suites.
- **Frontend (`frontend/src/`)** — the Kanban board, drag-and-drop,
  the Why Panel, the AI suggestions drawer, and the login/auth screens
  were built and styled with AI assistance.
- **Tests (`tests/`)** — the full suite (engine, API, authorization, and
  AI-pipeline tests) was scaffolded with AI assistance; see
  [`tests/README.md`](tests/README.md) for the current count and how to
  verify it yourself rather than trusting a number in this file.
- **Documentation** — this file, `docs/ARCHITECTURE.md`,
  `docs/TESTING_SCENARIOS.md`, and this `README.md` were drafted with AI
  assistance and then corrected against the actual codebase.

## What was NOT AI-generated

The core engine design — the cycle-detection approach, the max-not-sum
scheduling rule, the Invariant Gate, the Why Panel concept, and the
Propose/Challenge/Verify/Human pipeline — originates from my own problem
analysis during the synopsis stage ([`docs/synopsis/`](docs/synopsis/)),
not from AI suggestion. AI assistance during the build is implementation
help against a design that was already fully specified; it is not design
authorship.

---

**See also:** [`README.md`](README.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for what the AI-assisted code above actually implements, and [`docs/synopsis/04-ai.md`](docs/synopsis/04-ai.md) for the original AI-copilot design this declaration's §1 summarizes.