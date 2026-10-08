from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import Board, Task, Dependency, AISuggestion, AuditLog, AuditSource
from backend.schemas import DependencyCreate, DependencyResponse
from backend.auth import get_current_user_optional, require_board_access
from backend.audit import log_invariant_gate_failure
from engine.graph import would_create_cycle
from engine.scheduler import recompute
from engine.invariants import check_invariants
from backend.ai.pipeline import (
    LLM_PROMPT_VERSION,
    BoardLockContext,
    BoardRateLimitError,
    generate_heuristic_suggestions,
    run_ai_pipeline,
)

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


def _suggestion_response(suggestion: AISuggestion, tasks_by_id: dict[int, Task]) -> dict:
    prerequisite = tasks_by_id.get(suggestion.prerequisite_id)
    dependent = tasks_by_id.get(suggestion.task_id)
    prerequisite_title = prerequisite.title if prerequisite else f"Task #{suggestion.prerequisite_id}"
    dependent_title = dependent.title if dependent else f"Task #{suggestion.task_id}"
    return {
        "id": suggestion.id,
        "task_id": suggestion.task_id,
        "prerequisite_id": suggestion.prerequisite_id,
        "reason": f"{prerequisite_title} may need to finish before {dependent_title} starts.",
        "evidence_phrase": suggestion.evidence_phrase,
        "proposer_confidence": suggestion.proposer_confidence,
        "challenge_verdict": suggestion.challenge_verdict,
        "status": suggestion.status,
        "model_name": suggestion.model_name,
    }


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
        log_invariant_gate_failure(
            route="POST /dependencies",
            violations=violations,
            context={"task_id": payload.task_id, "prerequisite_id": payload.prerequisite_id},
        )
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
        log_invariant_gate_failure(
            route="DELETE /dependencies/{dep_id}",
            violations=violations,
            context={"dependency_id": dep_id, "task_id": task_id},
        )
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
        .filter(
            Task.board_id == board_id,
            AISuggestion.status == "pending",
            (
                (AISuggestion.model_name == "heuristic-fallback")
                | (AISuggestion.prompt_version == LLM_PROMPT_VERSION)
            ),
        )
        .all()
    )
    tasks_by_id = {
        task.id: task
        for task in db.query(Task).filter(Task.board_id == board_id).all()
    }
    return [_suggestion_response(suggestion, tasks_by_id) for suggestion in rows]


@router.get("/suggestions/rejected", response_model=list[dict])
def list_rejected_suggestions(
    board_id: int = 1,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """Fetch previously rejected AI suggestions for the board, so the user can reconsider one."""
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
        .filter(Task.board_id == board_id, AISuggestion.status == "rejected")
        .all()
    )
    tasks_by_id = {
        task.id: task
        for task in db.query(Task).filter(Task.board_id == board_id).all()
    }
    return [_suggestion_response(suggestion, tasks_by_id) for suggestion in rows]


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

            # Old LLM suggestions may contain mismatched free-form reasons/evidence.
            # Preserve them for audit/history, but don't display them or let them block
            # a new suggestion for the same pair.
            (
                db.query(AISuggestion)
                .filter(
                    AISuggestion.task_id.in_(task_ids),
                    AISuggestion.status == "pending",
                    AISuggestion.model_name != "heuristic-fallback",
                    AISuggestion.prompt_version != LLM_PROMPT_VERSION,
                )
                .update(
                    {AISuggestion.status: "superseded"},
                    synchronize_session=False,
                )
            )

            # Exclude pairs that were previously rejected on this board
            rejected_rows = (
                db.query(AISuggestion.prerequisite_id, AISuggestion.task_id)
                .join(Task, Task.id == AISuggestion.task_id)
                .filter(Task.board_id == payload.board_id, AISuggestion.status == "rejected")
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
                .filter(
                    Task.board_id == payload.board_id,
                    AISuggestion.status == "pending",
                    (
                        (AISuggestion.model_name == "heuristic-fallback")
                        | (AISuggestion.prompt_version == LLM_PROMPT_VERSION)
                    ),
                )
                .all()
            )
            tasks_by_id = {task.id: task for task in all_tasks}
            return [_suggestion_response(suggestion, tasks_by_id) for suggestion in all_pending]

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


@router.post("/suggestions/{suggestion_id}/reconsider", response_model=dict)
def reconsider_suggestion(
    suggestion_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """Move a previously rejected suggestion back to pending, so it can be re-evaluated
    (accepted, rejected again, or left pending) without waiting for the AI to propose it again.
    A reconsidered suggestion is no longer counted as 'rejected', so it will not be excluded
    from future pipeline runs either."""
    sug = db.query(AISuggestion).filter(AISuggestion.id == suggestion_id).first()
    if not sug:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SUGGESTION_NOT_FOUND", "message": f"Suggestion {suggestion_id} not found."},
        )

    task, board = _resolve_board_for_task(sug.task_id, db)
    require_board_access(board, current_user)

    if sug.status != "rejected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_STATE", "message": "Only a rejected suggestion can be reconsidered."},
        )

    sug.status = "pending"
    db.commit()

    return {
        "id": sug.id,
        "task_id": sug.task_id,
        "prerequisite_id": sug.prerequisite_id,
        "reason": sug.reason,
        "evidence_phrase": sug.evidence_phrase,
        "proposer_confidence": sug.proposer_confidence,
        "challenge_verdict": sug.challenge_verdict,
        "status": sug.status,
        "model_name": sug.model_name,
    }