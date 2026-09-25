from typing import Any, Sequence, Union
from datetime import date
from engine.graph import prerequisites_of, forward_closure
from engine.scheduler import recompute


def is_ready(task: Any, all_tasks: Sequence[Any], all_edges: Sequence[Any]) -> bool:
    """
    A task is ready if and only if all its direct prerequisites are in 'done' column.
    A task with no prerequisites is always ready.
    """
    prereq_ids = prerequisites_of(task.id, all_edges)
    if not prereq_ids:
        return True
    task_map = {t.id: t for t in all_tasks}
    return all(
        task_map[p_id].column == "done"
        for p_id in prereq_ids
        if p_id in task_map
    )


def is_blocked(task: Any, all_tasks: Sequence[Any], all_edges: Sequence[Any]) -> bool:
    """A task is blocked if it is not ready."""
    return not is_ready(task, all_tasks, all_edges)


def get_blocking_prerequisites(
    task: Any, all_tasks: Sequence[Any], all_edges: Sequence[Any]
) -> list[Any]:
    """Return all direct prerequisites of task that are not in the 'done' column."""
    prereq_ids = prerequisites_of(task.id, all_edges)
    task_map = {t.id: t for t in all_tasks}
    return [
        task_map[p_id]
        for p_id in prereq_ids
        if p_id in task_map and task_map[p_id].column != "done"
    ]


def handle_regression(
    task: Any,
    all_tasks: Sequence[Any],
    all_edges: Sequence[Any],
    board_start_date: Union[date, int, None] = None,
) -> list[int]:
    """
    When a task's column moves from 'done' to anything else:
    1. Clear task.actual_end
    2. Recompute downstream schedule
    3. Return list of downstream task IDs that were in 'done' column (needs_reverification).
    """
    task.actual_end = None
    recompute(task.id, all_tasks, all_edges, board_start_date=board_start_date)
    downstream_ids = forward_closure(task.id, all_edges) - {task.id}
    task_map = {t.id: t for t in all_tasks}

    needs_reverification_ids = [
        t_id
        for t_id in downstream_ids
        if t_id in task_map and task_map[t_id].column == "done"
    ]
    return needs_reverification_ids


def derive_task_fields(
    task: Any,
    all_tasks: Sequence[Any],
    all_edges: Sequence[Any],
    board_start_date: Union[date, int, None] = None,
) -> dict[str, Any]:
    """
    Computes all derived fields for a single task given current board state.
    Derived fields are never persisted in the database.
    """
    task_map = {t.id: t for t in all_tasks}
    prereq_ids = prerequisites_of(task.id, all_edges)

    ready = is_ready(task, all_tasks, all_edges)
    blocked = not ready
    blocking_prereq_ids = [
        p_id for p_id in prereq_ids
        if p_id in task_map and task_map[p_id].column != "done"
    ]

    candidates: list[tuple[Union[date, int], int | None]] = []
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

    slack_list = []
    for finish, p_cand_id in candidates:
        if p_cand_id is not None and p_cand_id != driving_id:
            diff = driving_finish - finish
            days = diff.days if hasattr(diff, "days") else int(diff)
            slack_list.append({"prerequisite_id": p_cand_id, "days": days})

    return {
        "blocked": blocked,
        "ready": ready,
        "driving_prerequisite_id": driving_id,
        "slack": slack_list,
        "blocking_prerequisite_ids": blocking_prereq_ids,
    }

