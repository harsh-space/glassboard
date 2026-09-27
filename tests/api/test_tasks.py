import pytest
from starlette.testclient import TestClient
from backend.main import app
from scripts.seed import seed_database
from backend.db import SessionLocal
from backend.models import Task

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    seed_database()


def test_create_task():
    payload = {
        "board_id": 1,
        "title": "New Integration Task",
        "description": "Task created via API",
        "duration_days": 3,
        "column": "backlog",
        "position": 11.0,
    }
    resp = client.post("/api/tasks", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "New Integration Task"
    assert data["duration_days"] == 3
    assert data["ready"] is True  # no prerequisites
    assert data["blocked"] is False
    assert data["version"] == 1


def test_update_task_optimistic_concurrency_version_conflict():
    """Stale version in PATCH returns 409 VERSION_CONFLICT and DB is unchanged."""
    resp = client.get("/api/boards/1")
    t1 = next(t for t in resp.json()["tasks"] if t["id"] == 1)
    current_version = t1["version"]

    # Attempt update with stale version
    patch_payload = {
        "title": "Updated Title That Should Fail",
        "version": current_version - 1,
    }
    resp_conflict = client.patch(f"/api/tasks/{t1['id']}", json=patch_payload)
    assert resp_conflict.status_code == 409
    err = resp_conflict.json()["error"]
    assert err["code"] == "VERSION_CONFLICT"

    # Confirm DB is unchanged
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == 1).first()
    assert task.title == t1["title"]
    db.close()


def test_update_task_valid():
    resp = client.get("/api/boards/1")
    t1 = next(t for t in resp.json()["tasks"] if t["id"] == 1)

    patch_payload = {
        "title": "Requirements Gathering Updated",
        "duration_days": 4,  # increased duration
        "version": t1["version"],
    }
    resp_ok = client.patch(f"/api/tasks/{t1['id']}", json=patch_payload)
    assert resp_ok.status_code == 200
    data = resp_ok.json()
    assert data["task"]["title"] == "Requirements Gathering Updated"
    assert data["task"]["duration_days"] == 4
    assert data["task"]["version"] == t1["version"] + 1
    # Downstream tasks shifted because T1 duration increased
    assert len(data["downstream_changes"]) > 0


def test_move_task_blocked_rejection():
    """Attempting to move a blocked task to in_progress returns 409 TASK_BLOCKED."""
    # T2 is blocked by T1 on seeded board
    move_payload = {
        "column": "in_progress",
        "version": 1,
    }
    resp = client.post("/api/tasks/2/move", json=move_payload)
    assert resp.status_code == 409
    data = resp.json()
    assert data["error"]["code"] == "TASK_BLOCKED"
    assert "blocked by unfinished prerequisite" in data["error"]["message"]

    # Verify column in DB remains backlog
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == 2).first()
    assert task.column == "backlog"
    db.close()


def test_move_task_success_when_ready():
    # T1 has no prereqs, so moving to in_progress succeeds
    move_payload = {
        "column": "in_progress",
        "version": 1,
    }
    resp = client.post("/api/tasks/1/move", json=move_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["task"]["column"] == "in_progress"
    assert data["task"]["version"] == 2


def test_task_explanation_why_panel():
    # T7 depends on T4 (driving) and T5 (slack=3)
    resp = client.get("/api/tasks/7/explanation")
    assert resp.status_code == 200
    data = resp.json()
    assert data["driving_prerequisite_id"] == 4
    assert "Backend API Development" in data["reason_text"]
    assert any(s["prerequisite_id"] == 5 and s["days"] == 3 for s in data["slack"])


def test_task_impact_preview_dry_run():
    # Dry run delaying T2 by 3 days
    resp = client.post("/api/tasks/2/impact-preview", json={"duration_days": 6})
    assert resp.status_code == 200
    data = resp.json()
    assert "would_change" in data
    # T7 should be in would_change
    t7_change = next((c for c in data["would_change"] if c["task_id"] == 7), None)
    assert t7_change is not None

    # Verify database was NOT changed by dry run
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == 2).first()
    assert task.duration_days == 3
    db.close()


def test_task_regression_downgrades_downstream_task():
    """
    Issue 1: When Task E (done) -> Task F (done) and E regresses to in_progress,
    the request must succeed (no 409), E.column == 'in_progress',
    F.column is downgraded to 'backlog', and is_blocked(F) == True.
    """
    from backend.models import Dependency, AuditLog
    from engine.derive import is_blocked

    db = SessionLocal()
    # T1 -> T2 on seeded board (T1 is prerequisite of T2)
    t1 = db.query(Task).filter(Task.id == 1).first()
    t2 = db.query(Task).filter(Task.id == 2).first()
    t1.column = "done"
    t1.actual_end = t1.planned_end
    t2.column = "done"
    t2.actual_end = t2.planned_end
    db.commit()
    t1_version = t1.version
    db.close()

    # Move T1 from done to in_progress via the API
    move_payload = {
        "column": "in_progress",
        "version": t1_version,
    }
    resp = client.post("/api/tasks/1/move", json=move_payload)
    assert resp.status_code == 200, resp.json()
    data = resp.json()
    assert data["task"]["column"] == "in_progress"

    # Verify downstream changes include T2
    assert any(c["task_id"] == 2 for c in data["downstream_changes"])

    # Check DB state
    db = SessionLocal()
    t1_db = db.query(Task).filter(Task.id == 1).first()
    t2_db = db.query(Task).filter(Task.id == 2).first()
    all_tasks = db.query(Task).filter(Task.board_id == 1).all()
    all_edges = db.query(Dependency).all()

    assert t1_db.column == "in_progress"
    assert t2_db.column == "backlog"
    assert is_blocked(t2_db, all_tasks, all_edges) is True

    # Check audit log
    logs = db.query(AuditLog).filter(AuditLog.action == "task_regressed_downstream").all()
    assert any(log.payload.get("task_id") == 2 for log in logs)
    db.close()


def test_task_move_invalid_column_rejected():
    """
    Issue 2: POST to move task with invalid column string must return 422.
    """
    resp = client.post("/api/tasks/1/move", json={"column": "not_a_real_column", "version": 1})
    assert resp.status_code == 422


def test_task_create_invalid_column_rejected():
    """
    Issue 2: POST to create task with invalid column string must return 422.
    """
    payload = {
        "board_id": 1,
        "title": "Invalid Column Task",
        "duration_days": 2,
        "column": "invalid_column",
    }
    resp = client.post("/api/tasks", json=payload)
    assert resp.status_code == 422


def test_same_column_reorder_persists():
    """
    Issue 5: Moving a task within the same column to a new position updates
    the position field and persists across board fetches.
    """
    board_resp = client.get("/api/boards/1")
    assert board_resp.status_code == 200
    t2 = next(t for t in board_resp.json()["tasks"] if t["id"] == 2)
    t1 = next(t for t in board_resp.json()["tasks"] if t["id"] == 1)
    assert t2["position"] > t1["position"]

    # Reorder T2 above T1 by setting its position to 0.5 in the same column
    move_payload = {
        "column": t2["column"],
        "position": 0.5,
        "version": t2["version"],
    }
    resp = client.post("/api/tasks/2/move", json=move_payload)
    assert resp.status_code == 200
    assert resp.json()["task"]["position"] == 0.5

    # Fetch board again (simulating page reload) and verify order
    reload_resp = client.get("/api/boards/1")
    assert reload_resp.status_code == 200
    tasks = reload_resp.json()["tasks"]
    t2_reloaded = next(t for t in tasks if t["id"] == 2)
    t1_reloaded = next(t for t in tasks if t["id"] == 1)
    assert t2_reloaded["position"] == 0.5
    t2_idx = tasks.index(t2_reloaded)
    t1_idx = tasks.index(t1_reloaded)
    assert t2_idx < t1_idx



