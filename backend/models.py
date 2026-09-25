import enum
from datetime import datetime, date
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    JSON,
    func,
)
from sqlalchemy.orm import relationship
from backend.db import Base


class TaskColumn(str, enum.Enum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"


class ChallengeVerdict(str, enum.Enum):
    NOT_RUN = "not_run"
    SURVIVED = "survived"
    CONTESTED = "contested"
    REJECTED = "rejected"


class SuggestionStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class AuditSource(str, enum.Enum):
    HUMAN = "human"
    AI = "ai"


class Board(Base):
    __tablename__ = "board"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    start_date = Column(Date, nullable=False)

    tasks = relationship("Task", back_populates="board", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "task"

    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(Integer, ForeignKey("board.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False, default="")
    column = Column(String(50), nullable=False, default="backlog")
    position = Column(Float, nullable=False, default=1.0)
    duration_days = Column(Integer, nullable=False)
    pinned_start = Column(Date, nullable=True)
    planned_start = Column(Date, nullable=False)
    planned_end = Column(Date, nullable=False)
    actual_end = Column(Date, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    board = relationship("Board", back_populates="tasks")

    # In-memory only attributes (computed on read / recompute, never persisted)
    # blocked: bool
    # ready: bool
    # driving_prerequisite_id: int | None
    # slack_days: dict[int, int]

    __table_args__ = (
        CheckConstraint("duration_days > 0", name="check_positive_duration"),
    )


class Dependency(Base):
    __tablename__ = "dependency"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("task.id", ondelete="CASCADE"), nullable=False, index=True)
    prerequisite_id = Column(Integer, ForeignKey("task.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    task = relationship("Task", foreign_keys=[task_id])
    prerequisite = relationship("Task", foreign_keys=[prerequisite_id])

    __table_args__ = (
        UniqueConstraint("task_id", "prerequisite_id", name="uq_task_prerequisite"),
        CheckConstraint("task_id != prerequisite_id", name="check_no_self_dependency"),
    )


class AISuggestion(Base):
    __tablename__ = "ai_suggestion"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, nullable=False, index=True)
    prerequisite_id = Column(Integer, nullable=False, index=True)
    reason = Column(Text, nullable=False)
    evidence_phrase = Column(Text, nullable=False)
    proposer_confidence = Column(Float, nullable=False)
    challenge_verdict = Column(String(50), nullable=False, default="not_run")
    status = Column(String(50), nullable=False, default="pending")
    model_name = Column(String(100), nullable=False)
    prompt_version = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    source = Column(String(50), nullable=False)
    timestamp = Column(DateTime, nullable=False, server_default=func.now())
