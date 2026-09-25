import pytest
from starlette.testclient import TestClient
from backend.main import app
from scripts.seed import seed_database

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    seed_database()


def test_get_board_seeded():
    response = client.get("/api/boards/1")
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == 1
    assert data["name"] == "TaskFlow Pro Main Board"
    assert len(data["tasks"]) == 10
    assert len(data["dependencies"]) == 13

    # Check tasks: T1 has no prereqs, so should be ready and not blocked
    t1 = next(t for t in data["tasks"] if t["id"] == 1)
    assert t1["ready"] is True
    assert t1["blocked"] is False
    assert t1["driving_prerequisite_id"] is None

    # T2 depends on T1 (which is in backlog, not done), so T2 must be blocked
    t2 = next(t for t in data["tasks"] if t["id"] == 2)
    assert t2["ready"] is False
    assert t2["blocked"] is True
    assert t2["blocking_prerequisite_ids"] == [1]
    assert t2["driving_prerequisite_id"] == 1

    # T7 depends on T4 and T5
    # T4 finishes at start + 10 days, T5 finishes at start + 7 days
    # T4 is driving prerequisite, T5 has 3 days of slack!
    t7 = next(t for t in data["tasks"] if t["id"] == 7)
    assert t7["driving_prerequisite_id"] == 4
    slack_map = {s["prerequisite_id"]: s["days"] for s in t7["slack"]}
    assert slack_map.get(5) == 3


def test_get_board_not_found():
    response = client.get("/api/boards/999")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "BOARD_NOT_FOUND"
