import pytest
from engine.derive import is_blocked, is_ready
from engine.invariants import check_invariants


def test_initial_board_blocked_states(make_seed_graph):
    """
    On initial seeded board, only T1 has no prerequisites.
    T1 is ready.
    All other tasks (T2..T10) have unsatisfied prerequisites and must be blocked.
    """
    tasks, edges = make_seed_graph()
    task_map = {t.id: t for t in tasks}

    assert is_ready(task_map[1], tasks, edges) is True
    assert is_blocked(task_map[1], tasks, edges) is False

    for t_id in range(2, 11):
        assert is_ready(task_map[t_id], tasks, edges) is False
        assert is_blocked(task_map[t_id], tasks, edges) is True


def test_advancing_blocked_task_violates_invariants(make_seed_graph):
    """
    Moving a blocked task into in_progress, review, or done triggers invariant violation.
    """
    tasks, edges = make_seed_graph()
    task_map = {t.id: t for t in tasks}

    # T4 is blocked by T2
    assert is_blocked(task_map[4], tasks, edges) is True

    for invalid_col in ["in_progress", "review", "done"]:
        task_map[4].column = invalid_col
        violations = check_invariants(tasks, edges)
        assert "BLOCKED_TASK_ADVANCED:4" in violations

    # Backlog is valid
    task_map[4].column = "backlog"
    assert "BLOCKED_TASK_ADVANCED:4" not in check_invariants(tasks, edges)
