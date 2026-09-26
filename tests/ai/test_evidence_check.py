"""
tests/ai/test_evidence_check.py

Verifies that BUILD_SPEC.md §5.3 check 5 is correctly enforced:
A proposal whose evidence_phrase is NOT a literal substring of the
prerequisite task's title + description must be DROPPED, not substituted.
"""
import pytest
from unittest.mock import patch

from backend.ai.pipeline import run_ai_pipeline
from tests.engine.conftest import EngineTask


def _make_task(id_, title, description=""):
    """Create a minimal EngineTask-like object."""
    from datetime import date
    return EngineTask(
        id=id_,
        title=title,
        description=description,
        duration_days=3,
        column="backlog",
        pinned_start=None,
        planned_start=date(2026, 10, 1),
        planned_end=date(2026, 10, 3),
        actual_end=None,
        board_start_date=date(2026, 10, 1),
    )


class TestEvidenceCheckDropsBadProposals:

    def test_hallucinated_evidence_not_in_prereq_text_is_dropped(self):
        """
        When the LLM returns an evidence_phrase that does NOT appear anywhere
        in the prerequisite task's title or description, run_ai_pipeline must
        not return that suggestion.
        """
        prereq = _make_task(1, "Requirements Gathering", "Collect stakeholder requirements.")
        dep = _make_task(2, "Backend API Development", "Build the REST endpoints.")

        fabricated_evidence = "this phrase does not appear anywhere"

        fake_proposal = [{
            "prerequisite_id": 1,
            "task_id": 2,
            "reason": "Prereq must finish before dep starts.",
            "evidence_phrase": fabricated_evidence,
            "confidence": 0.9,
        }]
        fake_challenge = {"verdicts": [{"index": 0, "verdict": "survived", "note": "OK"}]}

        with patch("backend.ai.pipeline._call_groq_chat") as mock_call:
            # First call = propose, second call = challenge
            mock_call.side_effect = [
                {"suggestions": fake_proposal},
                fake_challenge,
            ]
            # Supply a fake GROQ_API_KEY so the LLM path is taken
            with patch.dict("os.environ", {"GROQ_API_KEY": "fake-key-for-test"}):
                results = run_ai_pipeline(
                    all_tasks=[prereq, dep],
                    existing_edges=[],
                    rejected_pairs=set(),
                    target_task_id=None,
                )

        # The hallucinated evidence phrase must have caused the proposal to be dropped
        assert results == [], (
            f"Expected empty list (proposal dropped), got: {results}"
        )

    def test_valid_evidence_in_prereq_text_survives(self):
        """
        When the evidence_phrase IS found in the prerequisite's text,
        the proposal should survive all other checks.
        """
        prereq = _make_task(1, "Requirements Gathering", "Collect stakeholder requirements.")
        dep = _make_task(2, "Backend API Development", "Build endpoints after requirements are done.")

        # "requirements" is in prereq title — should survive
        valid_evidence = "requirements"

        fake_proposal = [{
            "prerequisite_id": 1,
            "task_id": 2,
            "reason": "API dev needs requirements first.",
            "evidence_phrase": valid_evidence,
            "confidence": 0.9,
        }]
        fake_challenge = {"verdicts": [{"index": 0, "verdict": "survived", "note": "OK"}]}

        with patch("backend.ai.pipeline._call_groq_chat") as mock_call:
            mock_call.side_effect = [
                {"suggestions": fake_proposal},
                fake_challenge,
            ]
            with patch.dict("os.environ", {"GROQ_API_KEY": "fake-key-for-test"}):
                results = run_ai_pipeline(
                    all_tasks=[prereq, dep],
                    existing_edges=[],
                    rejected_pairs=set(),
                    target_task_id=None,
                )

        assert len(results) == 1, f"Expected 1 surviving suggestion, got: {results}"
        assert results[0]["evidence_phrase"] == valid_evidence

    def test_evidence_only_in_dep_text_not_in_prereq_is_dropped(self):
        """
        Evidence found only in the DEPENDENT task's text but NOT in the
        prerequisite's text must still be dropped (spec says prereq text only).
        """
        prereq = _make_task(1, "Schema Design", "Define the database tables.")
        dep = _make_task(2, "Frontend Implementation", "Build UI. Depends on api endpoints.")

        # "api" appears in dep description but NOT in prereq — must be dropped
        dep_only_evidence = "api"

        fake_proposal = [{
            "prerequisite_id": 1,
            "task_id": 2,
            "reason": "Schema must exist before frontend.",
            "evidence_phrase": dep_only_evidence,
            "confidence": 0.85,
        }]
        fake_challenge = {"verdicts": [{"index": 0, "verdict": "survived", "note": ""}]}

        with patch("backend.ai.pipeline._call_groq_chat") as mock_call:
            mock_call.side_effect = [
                {"suggestions": fake_proposal},
                fake_challenge,
            ]
            with patch.dict("os.environ", {"GROQ_API_KEY": "fake-key-for-test"}):
                results = run_ai_pipeline(
                    all_tasks=[prereq, dep],
                    existing_edges=[],
                    rejected_pairs=set(),
                    target_task_id=None,
                )

        assert results == [], (
            "Evidence found only in dep text should be dropped — prereq text check only."
        )

    def test_hallucinated_evidence_drop_is_written_to_audit_log(self):
        """
        When a proposal is dropped due to hallucinated evidence, an AuditLog
        record with action='ai_suggestion_evidence_rejected' and source='ai'
        must be added to the session.
        """
        from unittest.mock import MagicMock
        from backend.models import AuditLog

        prereq = _make_task(1, "Requirements Gathering", "Collect stakeholder requirements.")
        dep = _make_task(2, "Backend API Development", "Build endpoints.")

        fake_proposal = [{
            "prerequisite_id": 1,
            "task_id": 2,
            "reason": "Needs requirements first.",
            "evidence_phrase": "completely fabricated evidence phrase",
            "confidence": 0.9,
        }]
        fake_challenge = {"verdicts": [{"index": 0, "verdict": "survived", "note": "OK"}]}

        mock_db = MagicMock()

        with patch("backend.ai.pipeline._call_groq_chat") as mock_call:
            mock_call.side_effect = [
                {"suggestions": fake_proposal},
                fake_challenge,
            ]
            with patch.dict("os.environ", {"GROQ_API_KEY": "fake-key-for-test"}):
                results = run_ai_pipeline(
                    all_tasks=[prereq, dep],
                    existing_edges=[],
                    rejected_pairs=set(),
                    target_task_id=None,
                    db=mock_db,
                )

        assert results == []
        assert mock_db.add.called
        added_log = mock_db.add.call_args[0][0]
        assert isinstance(added_log, AuditLog)
        assert added_log.action == "ai_suggestion_evidence_rejected"
        assert added_log.source == "ai"
        assert added_log.payload["prerequisite_id"] == 1
        assert added_log.payload["task_id"] == 2
        assert added_log.payload["evidence_phrase"] == "completely fabricated evidence phrase"
