import os
import sys
from datetime import date

# Ensure root directory is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import Base, engine, SessionLocal
from backend.models import Board, Task, Dependency, TaskColumn
from tests.seed_data import SEED_TASKS, SEED_DEPENDENCIES
from engine.scheduler import recompute
from engine.invariants import check_invariants


def seed_database(target_date: date | None = None) -> tuple[int, int, int]:
    """
    Seeds the database with canonical 10 tasks and 13 dependencies.
    Returns (board_id, task_count, dependency_count).
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Clear existing data for fresh seed
        db.query(Dependency).delete()
        db.query(Task).delete()
        db.query(Board).delete()
        db.commit()

        start_date = target_date or date.today()

        # 1. Create Board
        board = Board(
            id=1,
            name="TaskFlow Pro Main Board",
            start_date=start_date,
        )
        db.add(board)
        db.flush()

        # 2. Create Tasks
        task_objects = {}
        for item in SEED_TASKS:
            t = Task(
                id=item["id"],
                board_id=board.id,
                title=item["title"],
                description=item["description"],
                column=TaskColumn.BACKLOG.value,
                position=float(item["id"]),
                duration_days=item["duration_days"],
                pinned_start=None,
                planned_start=start_date,
                planned_end=start_date,  # will be computed
                actual_end=None,
                version=1,
            )
            t.board = board
            task_objects[item["id"]] = t
            db.add(t)

        db.flush()

        # 3. Create 13 Dependencies
        dep_objects = []
        for prereq_id, task_id in SEED_DEPENDENCIES:
            dep = Dependency(
                task_id=task_id,
                prerequisite_id=prereq_id,
            )
            dep_objects.append(dep)
            db.add(dep)

        db.flush()

        # 4. Compute initial schedule using engine
        recompute(
            changed_task_id=1,
            all_tasks=list(task_objects.values()),
            all_edges=dep_objects,
            board_start_date=start_date,
        )

        # 5. Invariant Gate check before commit
        violations = check_invariants(list(task_objects.values()), dep_objects)
        if violations:
            raise RuntimeError(f"Invariant gate failed during seeding: {violations}")

        db.commit()

        # Verify counts in DB
        db_board_count = db.query(Board).count()
        db_task_count = db.query(Task).count()
        db_dep_count = db.query(Dependency).count()

        print(f"Database seeded successfully:")
        print(f"  Boards: {db_board_count}")
        print(f"  Tasks: {db_task_count}")
        print(f"  Dependencies: {db_dep_count}")

        return board.id, db_task_count, db_dep_count

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
