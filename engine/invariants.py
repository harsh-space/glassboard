from typing import Any, Sequence
from engine.graph import _edge_pair, is_acyclic
from engine.derive import is_blocked


def check_invariants(all_tasks: Sequence[Any], all_edges: Sequence[Any]) -> list[str]:
    """
    Invariant Gate assertions before committing any transaction (BUILD_SPEC.md §3.5):
    1. Graph must be acyclic.
    2. No task may have a planned_start earlier than any prerequisite finish date.
    3. No task in ('in_progress', 'review', 'done') may be blocked.
    Returns a list of violation strings. If empty, all invariants hold.
    """
    violations: list[str] = []

    # 1. Acyclicity
    if not is_acyclic(all_edges):
        violations.append("GRAPH_HAS_CYCLE")

    task_map = {t.id: t for t in all_tasks}

    # 2. Schedule precedence
    for edge in all_edges:
        p_id, t_id = _edge_pair(edge)
        prereq = task_map.get(p_id)
        dep = task_map.get(t_id)
        if prereq is None or dep is None:
            continue

        prereq_finish = (
            prereq.actual_end
            if (prereq.column == "done" and prereq.actual_end is not None)
            else prereq.planned_end
        )
        if dep.planned_start < prereq_finish:
            violations.append(f"SCHEDULE_VIOLATION:{t_id}")

    # 3. Blocked task state
    for task in all_tasks:
        if task.column in ("in_progress", "review", "done") and is_blocked(task, all_tasks, all_edges):
            violations.append(f"BLOCKED_TASK_ADVANCED:{task.id}")

    return violations
