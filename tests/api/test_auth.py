import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_auth_full_flow():
    import uuid
    suffix = uuid.uuid4().hex[:8]
    email = f"test_{suffix}@example.com"
    username = f"user_{suffix}"
    password = "securepassword123"

    # 1. Register
    reg_res = client.post("/api/auth/register", json={
        "email": email,
        "username": username,
        "password": password
    })
    assert reg_res.status_code == 201, reg_res.text
    data = reg_res.json()
    assert "access_token" in data
    assert data["email"] == email
    assert data["username"] == username
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Duplicate registration should 409
    dup_res = client.post("/api/auth/register", json={
        "email": email,
        "username": f"other_{suffix}",
        "password": password
    })
    assert dup_res.status_code == 409

    # 3. Login
    login_res = client.post("/api/auth/login", json={
        "email": email,
        "password": password
    })
    assert login_res.status_code == 200, login_res.text
    assert login_res.json()["access_token"]

    # 4. Check /me
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

    # 5. List boards (includes default/unowned board 1)
    boards_res = client.get("/api/auth/boards", headers=headers)
    assert boards_res.status_code == 200
    boards = boards_res.json()
    assert isinstance(boards, list)
    assert any(b["id"] == 1 for b in boards)

    # 6. Create board
    new_board_res = client.post("/api/auth/boards", headers=headers, json={
        "name": f"Project {suffix}",
        "start_date": "2026-10-01"
    })
    assert new_board_res.status_code == 201, new_board_res.text
    new_board = new_board_res.json()
    assert new_board["name"] == f"Project {suffix}"

    # 7. Register without username (auto-generated temp username)
    temp_suffix = uuid.uuid4().hex[:8]
    temp_reg = client.post("/api/auth/register", json={
        "email": f"temp_{temp_suffix}@example.com",
        "password": "password123"
    })
    assert temp_reg.status_code == 201, temp_reg.text
    temp_data = temp_reg.json()
    assert temp_data["username"].startswith("temp_")
    temp_token = temp_data["access_token"]
    temp_headers = {"Authorization": f"Bearer {temp_token}"}

    # 8. Update username to final chosen username
    final_username = f"final_user_{temp_suffix}"
    update_res = client.patch("/api/auth/username", headers=temp_headers, json={
        "username": final_username
    })
    assert update_res.status_code == 200, update_res.text
    assert update_res.json()["username"] == final_username

