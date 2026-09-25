from collections import deque
from datetime import date, timedelta
from typing import Any, Sequence, Union
from engine.graph import _edge_pair, forward_closure, prerequisites_of, successors_of


def _add_days(d: Union[date, int], days: int) -> Union[date, int]:
    if isinstance(d, date):
        return d + timedelta(days=days)
    return d + days


def _diff_days(d1: Union[date, int], d2: Union[date, int]) -> int:
    diff = d1 - d2
    if hasattr(diff, "days"):
        return diff.days
    return int(diff)


def topological_sort(subset_ids: set[int], edges: Sequence[Any]) -> list[int]:
    """
    Kahn's algorithm restricted to subset_ids.
    Only edges between two tasks both in subset_ids are considered for in-degrees.
    """
    in_degree = {t_id: 0 for t_id in subset_ids}
    adj: dict[int, list[int]] = {t_id: [] for t_id in subset_ids}

    for edge in edges:
        p_id, t_id = _edge_pair(edge)
        if p_id in subset_ids and t_id in subset_ids:
            adj[p_id].append(t_id)
            in_degree[t_id] += 1

    queue = deque([t_id for t_id in subset_ids if in_degree[t_id] == 0])
    ordered: list[int] = []

    while queue:
        curr = queue.popleft()
        ordered.append(curr)
        for succ in adj.get(curr, []):
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                queue.append(succ)

    if len(ordered) != len(subset_ids):
        raise ValueError("Cycle detected within subset during topological sort")

    return ordered


def recompute(
    changed_task_id: int,
    all_tasks: Sequence[Any],
    all_edges: Sequence[Any],
    board_start_date: Union[date, int, None] = None,
) -> list[Any]:
    """
    Incremental schedule recompute starting from changed_task_id.
    Follows BUILD_SPEC.md §3.2.
    Computes planned_start, planned_end, driving_prerequisite_id, and slack.
    Returns the list of recomputed task objects in topological order.
    """
    task_map = {t.id: t for t in all_tasks}
    if changed_task_id not in task_map:
        return []

    affected_ids = forward_closure(changed_task_id, all_edges)
    ordered_ids = topological_sort(affected_ids, all_edges)

    recomputed_tasks: list[Any] = []

    for t_id in ordered_ids:
        task = task_map[t_id]
        candidates: list[tuple[Union[date, int], int | None]] = []

        # Prerequisite candidates
        prereq_ids = prerequisites_of(task.id, all_edges)
        for p_id in prereq_ids:
            prereq = task_map.get(p_id)
            if prereq is None:
                continue
            finish = (
                prereq.actual_end
                if (prereq.column == "done" and prereq.actual_end is not None)
                else prereq.planned_end
            )
            candidates.append((finish, prereq.id))

        # Pinned start candidate
        if getattr(task, "pinned_start", None) is not None:
            candidates.append((task.pinned_start, None))

        # Unconstrained task anchors on board start date
        if not candidates:
            anchor_date = board_start_date
            if anchor_date is None and hasattr(task, "board_start_date"):
                anchor_date = task.board_start_date
            elif anchor_date is None and hasattr(task, "board") and task.board is not None:
                anchor_date = getattr(task.board, "start_date", None)
            if anchor_date is None:
                anchor_date = getattr(task, "planned_start", 0)
            candidates.append((anchor_date, None))

        # Select maximum candidate (max, not sum — prevents compounding)
        driving_finish, driving_id = max(candidates, key=lambda c: c[0])

        task.planned_start = driving_finish
        task.planned_end = _add_days(task.planned_start, task.duration_days)
        task.driving_prerequisite_id = driving_id

        if not hasattr(task, "slack") or task.slack is None:
            task.slack = {}
        else:
            task.slack.clear()

        for finish, p_cand_id in candidates:
            if p_cand_id is not None and p_cand_id != driving_id:
                task.slack[p_cand_id] = _diff_days(driving_finish, finish)

        recomputed_tasks.append(task)

    return recomputed_tasks
