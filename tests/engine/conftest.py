from dataclasses import dataclass, field
from datetime import date
from typing import Optional
import pytest
from tests.seed_data import SEED_TASKS, SEED_DEPENDENCIES
from engine.scheduler import recompute


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


@pytest.fixture
def make_seed_graph():
    def _maker(start_date: Optional[date] = None):
        base_date = start_date or date(2026, 1, 1)
        tasks = [
            EngineTask(
                id=t["id"],
                duration_days=t["duration_days"],
                title=t["title"],
                description=t["description"],
                board_start_date=base_date,
            )
            for t in SEED_TASKS
        ]
        edges = list(SEED_DEPENDENCIES)
        recompute(1, tasks, edges, board_start_date=base_date)
        return tasks, edges
    return _maker
