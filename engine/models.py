from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class EngineTask:
    id: int
    duration_days: int
    column: str = "backlog"
    title: str = ""
    description: str = ""
    pinned_start: Optional[date] = None
    planned_start: Optional[date] = None
    planned_end: Optional[date] = None
    actual_end: Optional[date] = None
    board_start_date: Optional[date] = None
    driving_prerequisite_id: Optional[int] = None
    slack: dict[int, int] = field(default_factory=dict)
