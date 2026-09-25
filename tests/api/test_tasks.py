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
