import pytest
from starlette.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_validation_error_pydantic_clean_400():
    """
    A request with a malformed/missing required field returns a clean
    Pydantic-driven 400, not a raw stack trace (BUILD_SPEC.md §8.2).
    """
    # duration_days must be gt=0, missing title
    bad_payload = {"board_id": 1, "duration_days": -5}
    resp = client.post("/api/tasks", json=bad_payload)
    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in data["error"]
    assert "errors" in data["error"]["details"]


def test_cors_origin_headers():
    """
    CORS configured to allow only the frontend's own origin, not '*' (BUILD_SPEC.md §7).
    """
    # Valid origin header
    resp_valid = client.options(
        "/api/boards/1",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp_valid.headers.get("access-control-allow-origin") == "http://localhost:5173"

    # Disallowed origin header
    resp_invalid = client.options(
        "/api/boards/1",
        headers={
            "Origin": "http://evil-site.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Origin from untrusted domain is NOT allowed
    assert resp_invalid.headers.get("access-control-allow-origin") != "http://evil-site.com"
    assert resp_invalid.headers.get("access-control-allow-origin") != "*"
