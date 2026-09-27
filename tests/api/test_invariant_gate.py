"""
API-layer coverage for the Invariant Gate's failure path (BUILD_SPEC.md §3.5).

tests/engine/test_invariants.py already exercises check_invariants() directly
at the engine level. What was missing — flagged in review — was a test that
drives an INVARIANT_VIOLATION through an actual API endpoint and asserts on
the full observable contract of that failure: the HTTP status code, that the
triggering write is fully rolled back, and that the one-way forensic audit
record for the event (`invariant_gate_failed`) is still written even though
the request's own transaction was rolled back.

Scenario: a task is advanced to 'done' while it has no unfinished
prerequisites (which is legal). A *new* dependency is then added, naming a
not-yet-done task as its prerequisite. That edge alone doesn't create a
cycle, so it clears cycle detection — but it does make the now-'done' task
BLOCKED_TASK_ADVANCED, which only the Invariant Gate catches, at commit time,
inside POST /dependencies.
"""
import pytest
from starlette.testclient import TestClient

from backend.main import app
from scripts.seed import seed_database
from backend.db import SessionLocal
from backend.models import Dependency, Task, AuditLog

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    seed_database()


def _move(task_id: int, column: str) -> dict:
    resp = client.get("/api/boards/1")
    task = next(t for t in resp.json()["tasks"] if t["id"] == task_id)
    resp = client.post(
        f"/api/tasks/{task_id}/move",
        json={"column": column, "version": task["version"]},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["task"]


def test_invariant_violation_via_new_dependency_on_advanced_task():
    # T1 has no prerequisites, so it can go straight to 'done'.
    _move(1, "done")
    # T3's only prerequisite (T1) is now done, so T3 is ready and can advance too.
    t3 = _move(3, "done")
    assert t3["column"] == "done"

    db = SessionLocal()
    initial_dep_count = db.query(Dependency).count()
    initial_audit_count = db.query(AuditLog).filter(AuditLog.action == "invariant_gate_failed").count()
    db.close()

    # T5 is still in 'backlog'. Wiring T5 -> T3 (prerequisite_id=5, task_id=3)
    # creates no cycle (T3's forward closure never reaches T5), so it passes
    # cycle detection -- but it makes 'done' task T3 blocked, which only the
    # Invariant Gate's rule #3 (BLOCKED_TASK_ADVANCED) catches.
    resp = client.post("/api/dependencies", json={"prerequisite_id": 5, "task_id": 3})

    assert resp.status_code == 409
    body = resp.json()
    assert body["error"]["code"] == "INVARIANT_VIOLATION"
    violations = body["error"]["details"]["violations"]
    assert any(v.startswith("BLOCKED_TASK_ADVANCED") for v in violations)

    db = SessionLocal()

    # The transaction must be fully rolled back: no new dependency row...
    assert db.query(Dependency).count() == initial_dep_count
    assert (
        db.query(Dependency)
        .filter(Dependency.prerequisite_id == 5, Dependency.task_id == 3)
        .first()
        is None
    )
    # ...and T3 must still be exactly as it was ('done'), not left half-updated.
    t3_row = db.query(Task).filter(Task.id == 3).first()
    assert t3_row.column == "done"

    # The failure must still leave a forensic trail: a new invariant_gate_failed
    # audit row, even though the request session that would normally have
    # written it was rolled back (backend/audit.py writes it on its own
    # independent session for exactly this reason).
    new_audit_count = db.query(AuditLog).filter(AuditLog.action == "invariant_gate_failed").count()
    assert new_audit_count == initial_audit_count + 1

    last_audit = (
        db.query(AuditLog)
        .filter(AuditLog.action == "invariant_gate_failed")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert last_audit.payload["route"] == "POST /dependencies"
    assert last_audit.payload["task_id"] == 3
    assert last_audit.payload["prerequisite_id"] == 5
    assert any(v.startswith("BLOCKED_TASK_ADVANCED") for v in last_audit.payload["violations"])

    db.close()
