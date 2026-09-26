from datetime import date
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import Board, Task, Dependency, AuditLog, TaskColumn, AuditSource
from backend.auth import get_current_user_optional, require_board_access
from backend.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskMove,
    TaskResponse,
    TaskImpactPreview,
    TaskExplanationResponse,
    ImpactPreviewResponse,
    ImpactChangeItem,
    SlackItem,
)
from engine.graph import forward_closure
from engine.scheduler import recompute
from engine.derive import is_blocked, is_ready, handle_regression, derive_task_fields, get_blocking_prerequisites
from engine.invariants import check_invariants

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _task_to_response(
    t: Task,
    all_tasks: list[Task],
    all_edges: list[Dependency],
    board_start_date: date,
) -> TaskResponse:
    derived = derive_task_fields(t, all_tasks, all_edges, board_start_date)
    return TaskResponse(
        id=t.id,
        board_id=t.board_id,
        title=t.title,
        description=t.description,
        column=t.column,
        position=t.position,
        duration_days=t.duration_days,
        pinned_start=t.pinned_start,
        planned_start=t.planned_start,
        planned_end=t.planned_end,
        actual_end=t.actual_end,
        version=t.version,
        created_at=t.created_at,
        updated_at=t.updated_at,
        blocked=derived["blocked"],
        ready=derived["ready"],
        driving_prerequisite_id=derived["driving_prerequisite_id"],
        slack=[SlackItem(**s) for s in derived["slack"]],
        blocking_prerequisite_ids=derived["blocking_prerequisite_ids"],
    )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    board = db.query(Board).filter(Board.id == payload.board_id).first()
    if not board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BOARD_NOT_FOUND", "message": "Board not found."},
        )

    require_board_access(board, current_user)

    # Initial planned_start defaults to board start date or pinned_start
    initial_start = payload.pinned_start or board.start_date
    task = Task(
        board_id=payload.board_id,
        title=payload.title,
        description=payload.description or "",
        column=payload.column or "backlog",
        position=payload.position or 1.0,
        duration_days=payload.duration_days,
        pinned_start=payload.pinned_start,
        planned_start=initial_start,
        planned_end=initial_start,  # will be computed by recompute
        actual_end=None,
        version=1,
    )
    db.add(task)
    db.flush()

    all_tasks = db.query(Task).filter(Task.board_id == board.id).all()
    task_ids = [t.id for t in all_tasks]
    all_edges = db.query(Dependency).filter(Dependency.task_id.in_(task_ids)).all() if task_ids else []

    recompute(task.id, all_tasks, all_edges, board_start_date=board.start_date)

    violations = check_invariants(all_tasks, all_edges)
    if violations:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "INVARIANT_VIOLATION", "message": "Invariant check failed.", "details": {"violations": violations}},
        )

    # Audit log
    audit = AuditLog(
        action="task_created",
        payload={"task_id": task.id, "title": task.title},
        source=AuditSource.HUMAN.value,
    )
    db.add(audit)
    db.commit()

    return _task_to_response(task, all_tasks, all_edges, board.start_date)


@router.patch("/{task_id}")
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_NOT_FOUND", "message": f"Task {task_id} not found."},
        )

    # Optimistic concurrency check (BUILD_SPEC.md §4)
    if task.version != payload.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "VERSION_CONFLICT",
                "message": f"Task {task_id} version conflict. Current version is {task.version}, requested version was {payload.version}.",
                "details": {"current_version": task.version, "provided_version": payload.version},
            },
        )

    board = db.query(Board).filter(Board.id == task.board_id).first()
    require_board_access(board, current_user)

    all_tasks = db.query(Task).filter(Task.board_id == task.board_id).all()
    task_ids = [t.id for t in all_tasks]
    all_edges = db.query(Dependency).filter(Dependency.task_id.in_(task_ids)).all() if task_ids else []

    # Record pre-update starts to calculate downstream changes
    old_starts = {t.id: t.planned_start for t in all_tasks}

    if payload.title is not None:
        task.title = payload.title
    if payload.description is not None:
        task.description = payload.description

    schedule_changed = False
    if payload.duration_days is not None and payload.duration_days != task.duration_days:
        task.duration_days = payload.duration_days
        schedule_changed = True
    if payload.pinned_start != task.pinned_start:
        task.pinned_start = payload.pinned_start
        schedule_changed = True

    if schedule_changed:
        recompute(task.id, all_tasks, all_edges, board_start_date=board.start_date)

    violations = check_invariants(all_tasks, all_edges)
    if violations:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "INVARIANT_VIOLATION", "message": "Invariant check failed.", "details": {"violations": violations}},
        )

    task.version += 1

    changed_tasks = [
        {"task_id": t.id, "old_start": old_starts[t.id], "new_start": t.planned_start}
        for t in all_tasks
        if t.id != task.id and t.planned_start != old_starts[t.id]
    ]

    audit = AuditLog(
        action="task_updated",
        payload={"task_id": task.id, "changes": payload.model_dump(exclude_unset=True)},
        source=AuditSource.HUMAN.value,
    )
    db.add(audit)
    db.commit()

    return {
        "task": _task_to_response(task, all_tasks, all_edges, board.start_date),
        "downstream_changes": changed_tasks,
    }


@router.post("/{task_id}/move")
def move_task(
    task_id: int,
    payload: TaskMove,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_NOT_FOUND", "message": f"Task {task_id} not found."},
        )

    # Optimistic concurrency check
    if task.version != payload.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "VERSION_CONFLICT",
                "message": f"Task {task_id} version conflict. Current version is {task.version}, requested version was {payload.version}.",
                "details": {"current_version": task.version, "provided_version": payload.version},
            },
        )

    board = db.query(Board).filter(Board.id == task.board_id).first()
    require_board_access(board, current_user)

    all_tasks = db.query(Task).filter(Task.board_id == task.board_id).all()
    task_ids = [t.id for t in all_tasks]
    all_edges = db.query(Dependency).filter(Dependency.task_id.in_(task_ids)).all() if task_ids else []

    old_starts = {t.id: t.planned_start for t in all_tasks}
    old_column = task.column
    new_column = payload.column or old_column

    if payload.position is not None:
        task.position = payload.position

    if new_column != old_column:
        # Check blocked state if advancing to in_progress, review, or done
        if new_column in ("in_progress", "review", "done") and is_blocked(task, all_tasks, all_edges):
            blocking = get_blocking_prerequisites(task, all_tasks, all_edges)
            blocking_titles = [p.title for p in blocking]
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "TASK_BLOCKED",
                    "message": f"Cannot move '{task.title}' to {new_column}: blocked by unfinished prerequisite(s): {', '.join(blocking_titles)}.",
                    "details": {
                        "task_id": task.id,
                        "blocking_prerequisites": [{"id": p.id, "title": p.title} for p in blocking],
                    },
                },
            )

        task.column = new_column

        # Regression: moving from done to anything else (BUILD_SPEC.md §3.4)
        if old_column == "done" and new_column != "done":
            reverification_ids = handle_regression(task, all_tasks, all_edges, board_start_date=board.start_date)
            for rev_id in reverification_ids:
                db.add(
                    AuditLog(
                        action="needs_reverification",
                        payload={"task_id": rev_id, "cause_task_id": task.id},
                        source=AuditSource.HUMAN.value,
                    )
                )

        # Transitioning into done: actual_end = planned_end (per user decision)
        elif new_column == "done":
            task.actual_end = task.planned_end
            recompute(task.id, all_tasks, all_edges, board_start_date=board.start_date)

    violations = check_invariants(all_tasks, all_edges)
    if violations:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "INVARIANT_VIOLATION", "message": "Invariant check failed.", "details": {"violations": violations}},
        )

    task.version += 1

    changed_tasks = [
        {"task_id": t.id, "old_start": old_starts[t.id], "new_start": t.planned_start}
        for t in all_tasks
        if t.id != task.id and t.planned_start != old_starts[t.id]
    ]

    audit = AuditLog(
        action="task_moved",
        payload={
            "task_id": task.id,
            "old_column": old_column,
            "new_column": new_column,
            "position": task.position,
        },
        source=AuditSource.HUMAN.value,
    )
    db.add(audit)
    db.commit()

    return {
        "task": _task_to_response(task, all_tasks, all_edges, board.start_date),
        "downstream_changes": changed_tasks,
    }


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_NOT_FOUND", "message": f"Task {task_id} not found."},
        )

    board_id = task.board_id
    board = db.query(Board).filter(Board.id == board_id).first()
    require_board_access(board, current_user)

    # Find affected successors before deletion
    all_tasks = db.query(Task).filter(Task.board_id == board_id).all()
    task_ids = [t.id for t in all_tasks]
    all_edges = db.query(Dependency).filter(Dependency.task_id.in_(task_ids)).all() if task_ids else []

    downstream_ids = list(forward_closure(task.id, all_edges) - {task.id})

    # Delete task (database ON DELETE CASCADE removes associated dependencies)
    db.delete(task)
    db.flush()

    remaining_tasks = db.query(Task).filter(Task.board_id == board_id).all()
    remaining_task_ids = [t.id for t in remaining_tasks]
    remaining_edges = (
        db.query(Dependency).filter(Dependency.task_id.in_(remaining_task_ids)).all()
        if remaining_task_ids
        else []
    )

    for d_id in downstream_ids:
        if d_id in remaining_task_ids:
            recompute(d_id, remaining_tasks, remaining_edges, board_start_date=board.start_date)

    violations = check_invariants(remaining_tasks, remaining_edges)
    if violations:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "INVARIANT_VIOLATION", "message": "Invariant check failed after task deletion.", "details": {"violations": violations}},
        )

    db.add(
        AuditLog(
            action="task_deleted",
            payload={"task_id": task_id},
            source=AuditSource.HUMAN.value,
        )
    )
    db.commit()
    return None


@router.get("/{task_id}/explanation", response_model=TaskExplanationResponse)
def get_task_explanation(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_NOT_FOUND", "message": f"Task {task_id} not found."},
        )

    board = db.query(Board).filter(Board.id == task.board_id).first()
    require_board_access(board, current_user)

    all_tasks = db.query(Task).filter(Task.board_id == task.board_id).all()
    task_ids = [t.id for t in all_tasks]
    all_edges = db.query(Dependency).filter(Dependency.task_id.in_(task_ids)).all() if task_ids else []

    derived = derive_task_fields(task, all_tasks, all_edges, board.start_date)
    driving_id = derived["driving_prerequisite_id"]
    task_map = {t.id: t for t in all_tasks}

    # Construct plain-language sentence reason per BUILD_SPEC.md §4 & §6
    if driving_id is not None and driving_id in task_map:
        driving_prereq = task_map[driving_id]
        reason_text = (
            f"Planned start is {task.planned_start} because prerequisite "
            f"'{driving_prereq.title}' completes on {driving_prereq.planned_end}."
        )
    elif task.pinned_start is not None and task.planned_start == task.pinned_start:
        reason_text = f"Planned start is {task.planned_start} because it is pinned to that date."
    else:
        reason_text = f"Planned start is {task.planned_start} anchored on board start date with no driving prerequisites."

    return TaskExplanationResponse(
        driving_prerequisite_id=driving_id,
        reason_text=reason_text,
        slack=[SlackItem(**s) for s in derived["slack"]],
    )


@router.post("/{task_id}/impact-preview", response_model=ImpactPreviewResponse)
def get_impact_preview(
    task_id: int,
    payload: TaskImpactPreview,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_NOT_FOUND", "message": f"Task {task_id} not found."},
        )

    board = db.query(Board).filter(Board.id == task.board_id).first()
    require_board_access(board, current_user)

    all_tasks = db.query(Task).filter(Task.board_id == task.board_id).all()
    task_ids = [t.id for t in all_tasks]
    all_edges = db.query(Dependency).filter(Dependency.task_id.in_(task_ids)).all() if task_ids else []

    # Dry-run: deep clone task data in-memory without committing
    from tests.engine.conftest import EngineTask
    import copy

    cloned_tasks = [
        EngineTask(
            id=t.id,
            duration_days=t.duration_days,
            column=t.column,
            title=t.title,
            description=t.description,
            pinned_start=t.pinned_start,
            planned_start=t.planned_start,
            planned_end=t.planned_end,
            actual_end=t.actual_end,
            board_start_date=board.start_date,
        )
        for t in all_tasks
    ]
    cloned_edges = [(d.prerequisite_id, d.task_id) for d in all_edges]
    cloned_map = {t.id: t for t in cloned_tasks}

    target = cloned_map[task_id]
    if payload.duration_days is not None:
        target.duration_days = payload.duration_days
    if payload.pinned_start is not None:
        target.pinned_start = payload.pinned_start

    # Run recompute on cloned state
    recompute(task_id, cloned_tasks, cloned_edges, board_start_date=board.start_date)

    original_map = {t.id: t for t in all_tasks}
    changes = []
    for ct in cloned_tasks:
        orig = original_map[ct.id]
        if ct.planned_start != orig.planned_start:
            changes.append(
                ImpactChangeItem(
                    task_id=ct.id,
                    old_start=orig.planned_start,
                    new_start=ct.planned_start,
                )
            )

    return ImpactPreviewResponse(would_change=changes)
