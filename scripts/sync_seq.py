from sqlalchemy import text
from backend.db import SessionLocal

def sync():
    db = SessionLocal()
    items = [
        ('task', 'task_id_seq'),
        ('board', 'board_id_seq'),
        ('dependency', 'dependency_id_seq'),
        ('"user"', 'user_id_seq'),
    ]
    for tbl, seq in items:
        try:
            val = db.execute(text(f"SELECT setval('{seq}', COALESCE((SELECT MAX(id) FROM {tbl}), 1))")).scalar()
            print(f"Synced {seq} to {val}")
        except Exception as e:
            print(f"Skipped {seq}: {e}")
    db.commit()
    db.close()

if __name__ == "__main__":
    sync()
