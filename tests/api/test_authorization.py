"""
tests/api/test_authorization.py

Verifies board-level access control on the data endpoints:
  - No token → 401 for a private board (owner_id set)
  - Wrong-user token → 403 for someone else's private board
  - Owner token → 200 for their own private board
  - No token → 200 for the canonical guest board (owner_id IS NULL, id=1)
"""
import pytest
import uuid
from fastapi.testclient import TestClient
from backend.main import app
from scripts.seed import seed_database


@pytest.fixture(autouse=True)
def setup_db():
    seed_database()


def _register(client: TestClient, suffix: str) -> dict:
    resp = client.post("/api/auth/register", json={
        "email": f"authtest_{suffix}@example.com",
        "username": f"authtest_{suffix}",
        "password": "password123",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_private_board(client: TestClient, token: str, suffix: str) -> int:
    resp = client.post("/api/auth/boards", headers=_auth_headers(token), json={
        "name": f"Private Board {suffix}",
        "start_date": "2026-10-01",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


class TestGuestBoardAlwaysAccessible:
    """Board id=1 (owner_id IS NULL) must be reachable with zero token."""

    def test_get_guest_board_no_token(self):
        with TestClient(app) as client:
            resp = client.get("/api/boards/1")
            assert resp.status_code == 200, resp.text

    def test_get_guest_board_ai_suggestions_no_token(self):
        """AI suggestions endpoint on public board must work without a token."""
        with TestClient(app) as client:
            resp = client.get("/api/dependencies/suggestions", params={"board_id": 1})
            assert resp.status_code == 200, resp.text


class TestPrivateBoardEnforcement:
    """Endpoints on a private board (owner_id set) must enforce JWT access."""

    def test_no_token_gets_401(self):
        with TestClient(app) as client:
            suffix = uuid.uuid4().hex[:8]
            data = _register(client, suffix)
            board_id = _create_private_board(client, data["access_token"], suffix)

            # No Authorization header → 401
            resp = client.get(f"/api/boards/{board_id}")
            assert resp.status_code == 401, resp.text
            body = resp.json()
            assert body["error"]["code"] == "UNAUTHORIZED"

    def test_wrong_user_gets_403(self):
        with TestClient(app) as client:
            # Owner creates board
            owner_suffix = uuid.uuid4().hex[:8]
            owner_data = _register(client, owner_suffix)
            board_id = _create_private_board(client, owner_data["access_token"], owner_suffix)

            # Different user tries to access it
            other_suffix = uuid.uuid4().hex[:8]
            other_data = _register(client, other_suffix)
            resp = client.get(f"/api/boards/{board_id}", headers=_auth_headers(other_data["access_token"]))
            assert resp.status_code == 403, resp.text
            body = resp.json()
            assert body["error"]["code"] == "FORBIDDEN"

    def test_owner_gets_200(self):
        with TestClient(app) as client:
            suffix = uuid.uuid4().hex[:8]
            data = _register(client, suffix)
            board_id = _create_private_board(client, data["access_token"], suffix)

            resp = client.get(f"/api/boards/{board_id}", headers=_auth_headers(data["access_token"]))
            assert resp.status_code == 200, resp.text

    def test_create_task_no_token_on_private_board_gets_401(self):
        with TestClient(app) as client:
            suffix = uuid.uuid4().hex[:8]
            data = _register(client, suffix)
            board_id = _create_private_board(client, data["access_token"], suffix)

            resp = client.post("/api/tasks", json={
                "board_id": board_id,
                "title": "Unauthorized Task",
                "duration_days": 1,
            })
            assert resp.status_code == 401, resp.text

    def test_create_task_wrong_user_on_private_board_gets_403(self):
        with TestClient(app) as client:
            owner_suffix = uuid.uuid4().hex[:8]
            owner_data = _register(client, owner_suffix)
            board_id = _create_private_board(client, owner_data["access_token"], owner_suffix)

            other_suffix = uuid.uuid4().hex[:8]
            other_data = _register(client, other_suffix)
            resp = client.post("/api/tasks", headers=_auth_headers(other_data["access_token"]), json={
                "board_id": board_id,
                "title": "Intruder Task",
                "duration_days": 1,
            })
            assert resp.status_code == 403, resp.text

    def test_ai_suggestions_no_token_private_board_gets_401(self):
        with TestClient(app) as client:
            suffix = uuid.uuid4().hex[:8]
            data = _register(client, suffix)
            board_id = _create_private_board(client, data["access_token"], suffix)

            resp = client.get("/api/dependencies/suggestions", params={"board_id": board_id})
            assert resp.status_code == 401, resp.text
