from datetime import date, timedelta
from typing import Any, Sequence, Union
from engine.graph import _edge_pair, prerequisites_of
from engine.scheduler import _add_days, _diff_days, topological_sort


def recompute_from_scratch(
    all_tasks: Sequence[Any],
    all_edges: Sequence[Any],
    board_start_date: Union[date, int, None] = None,
) -> list[Any]:
    """
    Brute-force oracle reference implementation (TEST ONLY).
    Recomputes the entire schedule from scratch with no incremental shortcuts:
    Full topological sort of ALL tasks, applying the same max-not-sum rule.
    """
    task_map = {t.id: t for t in all_tasks}
    all_ids = set(task_map.keys())

    # Full topological sort of all tasks
    ordered_ids = topological_sort(all_ids, all_edges)

    for t_id in ordered_ids:
        task = task_map[t_id]
        candidates: list[tuple[Union[date, int], int | None]] = []

        prereq_ids = prerequisites_of(task.id, all_edges)
        for p_id in prereq_ids:
            prereq = task_map[p_id]
            finish = (
                prereq.actual_end
                if (prereq.column == "done" and prereq.actual_end is not None)
                else prereq.planned_end
            )
            candidates.append((finish, prereq.id))

        if getattr(task, "pinned_start", None) is not None:
            candidates.append((task.pinned_start, None))

        if not candidates:
            anchor_date = board_start_date
            if anchor_date is None and hasattr(task, "board_start_date"):
                anchor_date = task.board_start_date
            elif anchor_date is None and hasattr(task, "board") and task.board is not None:
                anchor_date = getattr(task.board, "start_date", None)
            if anchor_date is None:
                anchor_date = getattr(task, "planned_start", 0)
            candidates.append((anchor_date, None))

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

    return [task_map[t_id] for t_id in ordered_ids]
