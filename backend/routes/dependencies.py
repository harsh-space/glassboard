from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import Board, Task, Dependency, AISuggestion, AuditLog, AuditSource
from backend.schemas import DependencyCreate, DependencyResponse
from backend.auth import get_current_user_optional, require_board_access
from engine.graph import would_create_cycle
from engine.scheduler import recompute
from engine.invariants import check_invariants
from backend.ai.pipeline import BoardLockContext, BoardRateLimitError, generate_heuristic_suggestions, run_ai_pipeline

router = APIRouter(prefix="/dependencies", tags=["dependencies"])


class SuggestionsRequest(BaseModel):
    board_id: int
    task_id: Optional[int] = None


def _resolve_board_for_task(task_id: int, db: Session) -> tuple:
    """Return (task, board) or raise 404."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_NOT_FOUND", "message": f"Task {task_id} not found."},
        )
    board = db.query(Board).filter(Board.id == task.board_id).first()
    return task, board


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_dependency(
    payload: DependencyCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    # 1. Validation: Self-dependency
    if payload.task_id == payload.prerequisite_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "SELF_DEPENDENCY",
                "message": "A task cannot depend on itself.",
                "details": {"task_id": payload.task_id, "prerequisite_id": payload.prerequisite_id},
            },
        )

    task = db.query(Task).filter(Task.id == payload.task_id).first()
    prereq = db.query(Task).filter(Task.id == payload.prerequisite_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_NOT_FOUND", "message": f"Task {payload.task_id} not found."},
        )
    if not prereq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_NOT_FOUND", "message": f"Prerequisite task {payload.prerequisite_id} not found."},
        )

    if task.board_id != prereq.board_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BOARD_MISMATCH", "message": "Tasks must belong to the same board."},
        )

    board = db.query(Board).filter(Board.id == task.board_id).first()
    require_board_access(board, current_user)

    # 2. Validation: Duplicate
    existing = (
        db.query(Dependency)
        .filter(
            Dependency.task_id == payload.task_id,
            Dependency.prerequisite_id == payload.prerequisite_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "DUPLICATE_DEPENDENCY",
                "message": "Dependency already exists.",
                "details": {"task_id": payload.task_id, "prerequisite_id": payload.prerequisite_id},
            },
        )

    all_tasks = db.query(Task).filter(Task.board_id == task.board_id).all()
    task_ids = [t.id for t in all_tasks]
    all_edges = db.query(Dependency).filter(Dependency.task_id.in_(task_ids)).all() if task_ids else []

    # 3. Cycle Detection before write (BUILD_SPEC.md §3.1)
    cycle_result = would_create_cycle(payload.prerequisite_id, payload.task_id, all_edges)
    if cycle_result is not False:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CYCLE_DETECTED",
                "message": "Adding this dependency would create a cycle.",
                "details": {"path": cycle_result},
            },
        )

    old_starts = {t.id: t.planned_start for t in all_tasks}

    # 4. Insert dependency
    dep = Dependency(
        task_id=payload.task_id,
        prerequisite_id=payload.prerequisite_id,
    )
    db.add(dep)
    db.flush()

    # Refresh edges and recompute affected subgraph
    all_edges.append(dep)
    recompute(payload.task_id, all_tasks, all_edges, board_start_date=board.start_date)

    # 5. Invariant Gate check
    violations = check_invariants(all_tasks, all_edges)
    if violations:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "INVARIANT_VIOLATION", "message": "Invariant check failed.", "details": {"violations": violations}},
        )

    audit = AuditLog(
        action="dependency_created",
        payload={"dependency_id": dep.id, "task_id": dep.task_id, "prerequisite_id": dep.prerequisite_id},
        source=AuditSource.HUMAN.value,
    )
    db.add(audit)
    db.commit()

    changed_tasks = [
        {"task_id": t.id, "old_start": old_starts[t.id], "new_start": t.planned_start}
        for t in all_tasks
        if t.planned_start != old_starts[t.id]
    ]

    return {
        "dependency": DependencyResponse.model_validate(dep),
        "downstream_changes": changed_tasks,
    }


@router.delete("/{dep_id}", response_model=dict)
def delete_dependency(
    dep_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    dep = db.query(Dependency).filter(Dependency.id == dep_id).first()
    if not dep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DEPENDENCY_NOT_FOUND", "message": f"Dependency {dep_id} not found."},
        )

    task_id = dep.task_id
    task = db.query(Task).filter(Task.id == task_id).first()
    board = db.query(Board).filter(Board.id == task.board_id).first()
    require_board_access(board, current_user)

    all_tasks = db.query(Task).filter(Task.board_id == task.board_id).all()
    task_ids = [t.id for t in all_tasks]
    all_edges = db.query(Dependency).filter(Dependency.task_id.in_(task_ids)).all() if task_ids else []

    old_starts = {t.id: t.planned_start for t in all_tasks}

    # Delete
    db.delete(dep)
    db.flush()

    remaining_edges = [e for e in all_edges if e.id != dep_id]
    recompute(task_id, all_tasks, remaining_edges, board_start_date=board.start_date)

    violations = check_invariants(all_tasks, remaining_edges)
    if violations:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "INVARIANT_VIOLATION", "message": "Invariant check failed after dependency removal.", "details": {"violations": violations}},
        )

    audit = AuditLog(
        action="dependency_deleted",
        payload={"dependency_id": dep_id, "task_id": dep.task_id, "prerequisite_id": dep.prerequisite_id},
        source=AuditSource.HUMAN.value,
    )
    db.add(audit)
    db.commit()

    changed_tasks = [
        {"task_id": t.id, "old_start": old_starts[t.id], "new_start": t.planned_start}
        for t in all_tasks
        if t.planned_start != old_starts[t.id]
    ]

    return {
        "deleted_dependency_id": dep_id,
        "downstream_changes": changed_tasks,
    }


@router.get("/suggestions", response_model=list[dict])
def list_pending_suggestions(
    board_id: int = 1,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """Fetch currently pending AI suggestions for the board without re-triggering the pipeline."""
    board = db.query(Board).filter(Board.id == board_id).first()
    if not board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BOARD_NOT_FOUND", "message": "Board not found."},
        )
    require_board_access(board, current_user)

    rows = (
        db.query(AISuggestion)
        .join(Task, Task.id == AISuggestion.task_id)
        .filter(Task.board_id == board_id, AISuggestion.status == "pending")
        .all()
    )
    return [
        {
            "id": s.id,
            "task_id": s.task_id,
            "prerequisite_id": s.prerequisite_id,
            "reason": s.reason,
            "evidence_phrase": s.evidence_phrase,
            "proposer_confidence": s.proposer_confidence,
            "challenge_verdict": s.challenge_verdict,
            "status": s.status,
            "model_name": s.model_name,
        }
        for s in rows
    ]


@router.post("/suggestions", response_model=list[dict])
def get_ai_suggestions(
    payload: SuggestionsRequest,
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

    # Rate limiting per BUILD_SPEC.md §5.6
    try:
        with BoardLockContext(payload.board_id):
            all_tasks = db.query(Task).filter(Task.board_id == payload.board_id).all()
            task_ids = [t.id for t in all_tasks]
            all_edges = db.query(Dependency).filter(Dependency.task_id.in_(task_ids)).all() if task_ids else []

            # Exclude pairs that were previously rejected on this board
            rejected_rows = (
                db.query(AISuggestion.prerequisite_id, AISuggestion.task_id)
                .filter(AISuggestion.status == "rejected")
                .all()
            )
            rejected_pairs = {(r[0], r[1]) for r in rejected_rows}

            # Generate suggestions using full AI pipeline (Groq LLM or fallback heuristic)
            raw_suggestions = run_ai_pipeline(
                all_tasks=all_tasks,
                existing_edges=all_edges,
                rejected_pairs=rejected_pairs,
                target_task_id=payload.task_id,
                db=db,
            )

            for item in raw_suggestions:
                # Check if already present in pending state
                existing_sug = (
                    db.query(AISuggestion)
                    .filter(
                        AISuggestion.task_id == item["task_id"],
                        AISuggestion.prerequisite_id == item["prerequisite_id"],
                        AISuggestion.status == "pending",
                    )
                    .first()
                )
                if existing_sug:
                    continue

                sug = AISuggestion(
                    task_id=item["task_id"],
                    prerequisite_id=item["prerequisite_id"],
                    reason=item["reason"],
                    evidence_phrase=item["evidence_phrase"],
                    proposer_confidence=item["proposer_confidence"],
                    challenge_verdict=item["challenge_verdict"],
                    status="pending",
                    model_name=item["model_name"],
                    prompt_version=item["prompt_version"],
                )
                db.add(sug)
                db.flush()

            db.commit()

            # Return all currently pending suggestions so list never gets wiped
            all_pending = (
                db.query(AISuggestion)
                .join(Task, Task.id == AISuggestion.task_id)
                .filter(Task.board_id == payload.board_id, AISuggestion.status == "pending")
                .all()
            )
            return [
                {
                    "id": s.id,
                    "task_id": s.task_id,
                    "prerequisite_id": s.prerequisite_id,
                    "reason": s.reason,
                    "evidence_phrase": s.evidence_phrase,
                    "proposer_confidence": s.proposer_confidence,
                    "challenge_verdict": s.challenge_verdict,
                    "status": s.status,
                    "model_name": s.model_name,
                }
                for s in all_pending
            ]

    except BoardRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMITED", "message": str(e)},
        )


@router.post("/suggestions/{suggestion_id}/accept", response_model=dict)
def accept_suggestion(
    suggestion_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    sug = db.query(AISuggestion).filter(AISuggestion.id == suggestion_id).first()
    if not sug:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SUGGESTION_NOT_FOUND", "message": f"Suggestion {suggestion_id} not found."},
        )

    # Resolve board from suggestion's task and enforce access
    task, board = _resolve_board_for_task(sug.task_id, db)
    require_board_access(board, current_user)

    # Uses the exact same creation path and validations as POST /dependencies
    result = create_dependency(
        DependencyCreate(task_id=sug.task_id, prerequisite_id=sug.prerequisite_id),
        db=db,
        current_user=current_user,
    )

    sug.status = "accepted"
    db.commit()

    return result


@router.post("/suggestions/{suggestion_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
def reject_suggestion(
    suggestion_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    sug = db.query(AISuggestion).filter(AISuggestion.id == suggestion_id).first()
    if not sug:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SUGGESTION_NOT_FOUND", "message": f"Suggestion {suggestion_id} not found."},
        )

    task, board = _resolve_board_for_task(sug.task_id, db)
    require_board_access(board, current_user)

    sug.status = "rejected"
    db.commit()
    return None
