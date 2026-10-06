import pytest
from starlette.testclient import TestClient
from backend.main import app
from scripts.seed import seed_database
from backend.db import SessionLocal
from backend.models import Dependency, AISuggestion
from backend.ai.pipeline import BoardLockContext

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    seed_database()


def test_cycle_rejection_api_t10_to_t2():
    """
    Attempt T10 -> T2 via API (prerequisite_id=10, task_id=2).
    Must be rejected with 409 CYCLE_DETECTED, the loop path, and dependency table unchanged.
    """
    db = SessionLocal()
    initial_dep_count = db.query(Dependency).count()
    db.close()

    payload = {"prerequisite_id": 10, "task_id": 2}
    resp = client.post("/api/dependencies", json=payload)
    assert resp.status_code == 409
    data = resp.json()
    assert data["error"]["code"] == "CYCLE_DETECTED"
    assert "path" in data["error"]["details"]
    cycle_path = data["error"]["details"]["path"]
    assert cycle_path[0] == 2
    assert cycle_path[-1] == 2

    # Verify dependency table unchanged
    db = SessionLocal()
    current_dep_count = db.query(Dependency).count()
    assert current_dep_count == initial_dep_count
    db.close()


def test_self_dependency_rejection():
    payload = {"prerequisite_id": 2, "task_id": 2}
    resp = client.post("/api/dependencies", json=payload)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "SELF_DEPENDENCY"


def test_duplicate_dependency_rejection():
    # T1 -> T2 is already seeded
    payload = {"prerequisite_id": 1, "task_id": 2}
    resp = client.post("/api/dependencies", json=payload)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "DUPLICATE_DEPENDENCY"


def test_delete_dependency():
    db = SessionLocal()
    # Find edge T2 -> T5
    dep = db.query(Dependency).filter(Dependency.prerequisite_id == 2, Dependency.task_id == 5).first()
    dep_id = dep.id
    db.close()

    resp = client.delete(f"/api/dependencies/{dep_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted_dependency_id"] == dep_id

    # Confirm deleted from DB
    db = SessionLocal()
    assert db.query(Dependency).filter(Dependency.id == dep_id).first() is None
    db.close()


def test_ai_suggestions_heuristic_fallback_when_key_unset(monkeypatch):
    """
    With LLM key unset, the AI endpoint must return 200 with heuristic fallback
    suggestions marked model_name='heuristic-fallback' (BUILD_SPEC.md §5.6).
    """
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    payload = {"board_id": 1}
    resp = client.post("/api/dependencies/suggestions", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        first_sug = data[0]
        assert first_sug["model_name"] == "heuristic-fallback"
        assert first_sug["status"] == "pending"
        assert "evidence_phrase" in first_sug


def test_legacy_llm_suggestions_are_hidden_and_superseded(monkeypatch):
    """Old LLM output must not appear or block a regenerated pair."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    db = SessionLocal()
    legacy = AISuggestion(
        task_id=10,
        prerequisite_id=1,
        reason="Requirements Gathering must be completed before Frontend Implementation.",
        evidence_phrase="Requirements Gathering",
        proposer_confidence=0.95,
        challenge_verdict="survived",
        status="pending",
        model_name="groq/allam-2-7b",
        prompt_version="groq-allam-v1",
    )
    db.add(legacy)
    db.commit()
    db.refresh(legacy)
    legacy_id = legacy.id
    db.close()

    pending_response = client.get("/api/dependencies/suggestions", params={"board_id": 1})
    assert pending_response.status_code == 200
    assert legacy_id not in {item["id"] for item in pending_response.json()}

    generate_response = client.post("/api/dependencies/suggestions", json={"board_id": 1})
    assert generate_response.status_code == 200

    db = SessionLocal()
    refreshed_legacy = db.query(AISuggestion).filter(AISuggestion.id == legacy_id).first()
    assert refreshed_legacy.status == "superseded"
    db.close()


def test_pending_suggestion_reason_is_built_from_its_task_pair():
    """Stored LLM text cannot display task names that differ from the pair."""
    db = SessionLocal()
    suggestion = AISuggestion(
        task_id=4,
        prerequisite_id=1,
        reason="Requirements Gathering must be completed before Database Schema Design.",
        evidence_phrase="requirements",
        proposer_confidence=0.9,
        challenge_verdict="survived",
        status="pending",
        model_name="groq/allam-2-7b",
        prompt_version="groq-pair-grounded-v2",
    )
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)
    suggestion_id = suggestion.id
    db.close()

    response = client.get("/api/dependencies/suggestions", params={"board_id": 1})
    assert response.status_code == 200
    item = next(value for value in response.json() if value["id"] == suggestion_id)
    assert item["reason"] == "Requirements Gathering may need to finish before Backend API Development starts."


def test_ai_suggestions_live_groq_when_key_set():
    """
    When GROQ_API_KEY is configured, the endpoint returns suggestions from Groq allam-2-7b.
    """
    import os
    if not os.getenv("GROQ_API_KEY"):
        pytest.skip("GROQ_API_KEY not set")
    payload = {"board_id": 1}
    resp = client.post("/api/dependencies/suggestions", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        first_sug = data[0]
        assert "groq" in first_sug["model_name"]
        assert first_sug["status"] == "pending"


def test_ai_suggestion_accept_and_reject_flow():
    """
    Insert a synthetic pending suggestion, then:
      - Reject it via POST /suggestions/{id}/reject → 204
      - Confirm status == 'rejected' in DB
    This tests the accept/reject endpoint flow independently of the heuristic.
    """
    db = SessionLocal()
    sug = AISuggestion(
        task_id=5,
        prerequisite_id=3,
        reason="Test reason",
        evidence_phrase="test",
        proposer_confidence=0.9,
        challenge_verdict="survived",
        status="pending",
        model_name="heuristic-fallback",
        prompt_version="heuristic-v1",
    )
    db.add(sug)
    db.commit()
    db.refresh(sug)
    sug_id = sug.id
    db.close()

    # Reject suggestion
    resp_reject = client.post(f"/api/dependencies/suggestions/{sug_id}/reject")
    assert resp_reject.status_code == 204

    # Confirm marked rejected in DB
    db = SessionLocal()
    db_sug = db.query(AISuggestion).filter(AISuggestion.id == sug_id).first()
    assert db_sug.status == "rejected"
    db.close()



def test_ai_suggestions_rate_limiting():
    """Concurrently requesting suggestions on the same board triggers 429 RATE_LIMITED."""
    with BoardLockContext(1):
        resp = client.post("/api/dependencies/suggestions", json={"board_id": 1})
        assert resp.status_code == 429
        assert resp.json()["error"]["code"] == "RATE_LIMITED"
