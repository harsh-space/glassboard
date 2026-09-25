from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# --- Error Schema ---
class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail


# --- Task Schemas ---
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = ""
    duration_days: int = Field(gt=0)
    pinned_start: Optional[date] = None


class TaskCreate(TaskBase):
    board_id: int
    column: Optional[str] = "backlog"
    position: Optional[float] = 1.0


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    duration_days: Optional[int] = Field(default=None, gt=0)
    pinned_start: Optional[date] = None
    version: int


class TaskMove(BaseModel):
    column: Optional[str] = None
    position: Optional[float] = None
    version: int


class TaskImpactPreview(BaseModel):
    duration_days: Optional[int] = Field(default=None, gt=0)
    pinned_start: Optional[date] = None


class SlackItem(BaseModel):
    prerequisite_id: int
    days: int


class TaskResponse(BaseModel):
    id: int
    board_id: int
    title: str
    description: str
    column: str
    position: float
    duration_days: int
    pinned_start: Optional[date] = None
    planned_start: date
    planned_end: date
    actual_end: Optional[date] = None
    version: int
    created_at: datetime
    updated_at: datetime
    # Derived fields (never stored in DB)
    blocked: bool
    ready: bool
    driving_prerequisite_id: Optional[int] = None
    slack: list[SlackItem] = Field(default_factory=list)
    blocking_prerequisite_ids: list[int] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# --- Dependency Schemas ---
class DependencyCreate(BaseModel):
    task_id: int
    prerequisite_id: int


class DependencyResponse(BaseModel):
    id: int
    task_id: int
    prerequisite_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Board Schemas ---
class BoardBase(BaseModel):
    name: str
    start_date: date


class BoardCreate(BoardBase):
    pass


class BoardResponse(BaseModel):
    id: int
    name: str
    start_date: date
    tasks: list[TaskResponse]
    dependencies: list[DependencyResponse]

    model_config = {"from_attributes": True}


# --- Mutation / Explanation Responses ---
class TaskExplanationResponse(BaseModel):
    driving_prerequisite_id: Optional[int] = None
    reason_text: str
    slack: list[SlackItem] = Field(default_factory=list)


class ImpactChangeItem(BaseModel):
    task_id: int
    old_start: date
    new_start: date


class ImpactPreviewResponse(BaseModel):
    would_change: list[ImpactChangeItem]
