"""
tests/ai/test_propose_task_filter.py

Verifies BUILD_SPEC.md §5.1's Propose-call requirement: the prompt's task
list must include "every task on the board *except* ones already linked to
the target." A review of the submission found the live-LLM path sent every
task unfiltered; this test locks in the fix in `backend/ai/pipeline.py`.
"""
from datetime import date
from unittest.mock import patch

from backend.ai.pipeline import run_ai_pipeline
from tests.engine.conftest import EngineTask


def _make_task(id_, title, description=""):
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


def test_already_linked_task_excluded_from_propose_prompt():
    """
    Target task 2 already has an edge to task 1 (1 is 2's prerequisite).
    Task 3 has no edge with the target at all. The Propose prompt must
    include the target (2) and the unrelated task (3), but must NOT include
    task 1, since it's already linked to the target.
    """
    target = _make_task(2, "Backend API Development", "Build the REST endpoints.")
    already_linked = _make_task(1, "Requirements Gathering", "Collect stakeholder requirements.")
    unrelated = _make_task(3, "UI Wireframes", "Sketch the kanban board layout.")

    with patch("backend.ai.pipeline._call_groq_chat") as mock_call:
        # Return no suggestions -- we only care about what was sent, not what came back.
        mock_call.return_value = {"suggestions": []}
        with patch.dict("os.environ", {"GROQ_API_KEY": "fake-key-for-test"}):
            results = run_ai_pipeline(
                all_tasks=[target, already_linked, unrelated],
                existing_edges=[(1, 2)],  # (prerequisite_id, task_id): 1 -> 2
                rejected_pairs=set(),
                target_task_id=2,
            )

    assert results == []
    assert mock_call.call_count == 1  # propose call only; empty suggestions short-circuit before challenge

    propose_user_prompt = mock_call.call_args[0][4]
    assert "Requirements Gathering" not in propose_user_prompt, (
        "Task 1 is already linked to target task 2 and must be excluded from the prompt."
    )
    assert "Backend API Development" in propose_user_prompt
    assert "UI Wireframes" in propose_user_prompt


def test_whole_board_run_keeps_every_task_in_scope():
    """
    With no single target_task_id (a whole-board run), the "already linked
    to the target" exclusion doesn't apply -- there's no single target to
    exclude neighbors of -- so every task must stay in the prompt.
    """
    t1 = _make_task(1, "Requirements Gathering", "Collect stakeholder requirements.")
    t2 = _make_task(2, "Backend API Development", "Build the REST endpoints.")

    with patch("backend.ai.pipeline._call_groq_chat") as mock_call:
        mock_call.return_value = {"suggestions": []}
        with patch.dict("os.environ", {"GROQ_API_KEY": "fake-key-for-test"}):
            run_ai_pipeline(
                all_tasks=[t1, t2],
                existing_edges=[(1, 2)],
                rejected_pairs=set(),
                target_task_id=None,
            )

    propose_user_prompt = mock_call.call_args[0][4]
    assert "Requirements Gathering" in propose_user_prompt
    assert "Backend API Development" in propose_user_prompt
