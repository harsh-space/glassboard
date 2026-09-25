from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import Board, Task, Dependency
from backend.schemas import BoardResponse, TaskResponse, DependencyResponse, SlackItem
from engine.derive import derive_task_fields

router = APIRouter(prefix="/boards", tags=["boards"])


@router.get("/{board_id}", response_model=BoardResponse)
def get_board(board_id: int, db: Session = Depends(get_db)):
    board = db.query(Board).filter(Board.id == board_id).first()
    if not board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "BOARD_NOT_FOUND",
                "message": f"Board {board_id} not found.",
                "details": {"board_id": board_id},
            },
        )

    tasks = db.query(Task).filter(Task.board_id == board_id).order_by(Task.position).all()
    task_ids = [t.id for t in tasks]
    dependencies = (
        db.query(Dependency)
        .filter(Dependency.task_id.in_(task_ids))
        .all()
        if task_ids
        else []
    )

    # Derive fields for each task using pure engine function
    task_responses = []
    for t in tasks:
        derived = derive_task_fields(
            task=t,
            all_tasks=tasks,
            all_edges=dependencies,
            board_start_date=board.start_date,
        )
        task_responses.append(
            TaskResponse(
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
        )

    dep_responses = [
        DependencyResponse(
            id=d.id,
            task_id=d.task_id,
            prerequisite_id=d.prerequisite_id,
            created_at=d.created_at,
        )
        for d in dependencies
    ]

    return BoardResponse(
        id=board.id,
        name=board.name,
        start_date=board.start_date,
        tasks=task_responses,
        dependencies=dep_responses,
    )


@router.get("/{board_id}/critical-path")
def get_critical_path(board_id: int, db: Session = Depends(get_db)):
    board = db.query(Board).filter(Board.id == board_id).first()
    if not board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BOARD_NOT_FOUND", "message": f"Board {board_id} not found."},
        )

    tasks = db.query(Task).filter(Task.board_id == board_id).all()
    if not tasks:
        return {"task_ids": [], "total_duration": 0}

    task_ids = [t.id for t in tasks]
    dependencies = db.query(Dependency).filter(Dependency.task_id.in_(task_ids)).all() if task_ids else []

    from engine.scheduler import topological_sort
    from engine.graph import prerequisites_of

    all_ids = set(task_ids)
    ordered_ids = topological_sort(all_ids, dependencies)
    task_map = {t.id: t for t in tasks}

    # Dynamic programming for longest path by duration
    dist = {}
    parent = {}

    for t_id in ordered_ids:
        t = task_map[t_id]
        prereqs = prerequisites_of(t_id, dependencies)
        if not prereqs:
            dist[t_id] = t.duration_days
            parent[t_id] = None
        else:
            best_p = max(prereqs, key=lambda p: dist.get(p, 0))
            dist[t_id] = dist.get(best_p, 0) + t.duration_days
            parent[t_id] = best_p

    # Find overall end node with maximum path duration
    end_task_id = max(ordered_ids, key=lambda tid: dist[tid])
    total_duration = dist[end_task_id]

    path = []
    curr = end_task_id
    while curr is not None:
        path.append(curr)
        curr = parent.get(curr)
    path.reverse()

    return {"task_ids": path, "total_duration": total_duration}

