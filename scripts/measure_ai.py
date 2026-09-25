#!/usr/bin/env python3
"""
scripts/measure_ai.py — AI pipeline evaluation against the canonical seed board.

Usage:
    python scripts/measure_ai.py

Runs the AI suggestions pipeline against the seeded board (board_id=1) and
reports precision, recall, F1, and acceptance rate relative to the hand-labelled
ground-truth in tests/seed_dependency_labels.json.

Requires the backend app to be importable (run from repo root).
Does NOT require a running server — calls the pipeline functions directly.

BUILD_SPEC.md §5.5 reference metrics target: precision ≥ 0.85, recall ≥ 0.70.
Document actual numbers in docs/ARCHITECTURE.md.
"""
import json
import sys
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.seed import seed_database
from backend.db import SessionLocal
from backend.models import Task, Dependency, AISuggestion
from backend.ai.pipeline import generate_heuristic_suggestions


LABELS_PATH = Path(__file__).parent.parent / "tests" / "seed_dependency_labels.json"


def load_ground_truth() -> set[tuple[int, int]]:
    with open(LABELS_PATH) as f:
        data = json.load(f)
    return {(dep["prerequisite_id"], dep["task_id"]) for dep in data["true_dependencies"]}


def run_pipeline_against_empty_graph(db) -> list[dict]:
    """
    Run heuristic against board 1 with ALL existing edges cleared so the
    heuristic has a blank slate to propose from. This is the correct way
    to measure recall — we want to know which of the 13 ground-truth edges
    the pipeline would discover independently.

    Does NOT modify the database — uses in-memory edge_pairs = set().
    """
    tasks = db.query(Task).filter(Task.board_id == 1).all()

    suggestions = generate_heuristic_suggestions(
        all_tasks=tasks,
        existing_edges=[],   # blank slate: no existing edges
        rejected_pairs=set(),
        target_task_id=None,
    )
    return suggestions


def compute_metrics(
    suggested: set[tuple[int, int]],
    ground_truth: set[tuple[int, int]],
    accepted: set[tuple[int, int]],
) -> dict:
    tp = suggested & ground_truth
    fp = suggested - ground_truth
    fn = ground_truth - suggested

    precision = len(tp) / len(suggested) if suggested else 0.0
    recall = len(tp) / len(ground_truth) if ground_truth else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    acceptance_rate = len(accepted) / len(suggested) if suggested else 0.0

    return {
        "total_suggested": len(suggested),
        "true_positives": len(tp),
        "false_positives": len(fp),
        "false_negatives": len(fn),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "acceptance_rate": round(acceptance_rate, 4),
        "tp_pairs": sorted(tp),
        "fp_pairs": sorted(fp),
        "fn_pairs": sorted(fn),
    }


def main():
    print("TaskFlow Pro — AI Pipeline Measurement (BUILD_SPEC.md §5.5)")
    print("=" * 60)

    # Ensure a fresh seeded DB
    seed_database()

    ground_truth = load_ground_truth()
    print(f"Ground truth dependencies loaded: {len(ground_truth)}")

    db = SessionLocal()
    try:
        suggestions = run_pipeline_against_empty_graph(db)
    finally:
        db.close()

    suggested_pairs = {(s["prerequisite_id"], s["task_id"]) for s in suggestions}

    # For acceptance_rate: in offline mode, assume all TP suggestions would be accepted
    accepted_pairs = suggested_pairs & ground_truth

    metrics = compute_metrics(suggested_pairs, ground_truth, accepted_pairs)

    print(f"\nSuggestions generated:  {metrics['total_suggested']}")
    print(f"  True Positives:       {metrics['true_positives']}")
    print(f"  False Positives:      {metrics['false_positives']}")
    print(f"  False Negatives:      {metrics['false_negatives']}")
    print(f"\nPrecision:             {metrics['precision']:.1%}")
    print(f"Recall:                {metrics['recall']:.1%}")
    print(f"F1:                    {metrics['f1']:.1%}")
    print(f"Acceptance rate:       {metrics['acceptance_rate']:.1%}  (TP / total shown)")

    print("\n--- True Positives (correct proposals) ---")
    for pair in metrics["tp_pairs"]:
        print(f"  T{pair[0]} -> T{pair[1]}")

    print("\n--- False Positives (wrong proposals) ---")
    for pair in metrics["fp_pairs"]:
        print(f"  T{pair[0]} -> T{pair[1]}")

    print("\n--- False Negatives (missed ground truth) ---")
    for pair in metrics["fn_pairs"]:
        print(f"  T{pair[0]} -> T{pair[1]}")

    print("\nBUILD_SPEC.md §5.5 targets: precision >= 0.85, recall >= 0.70")
    p_ok = metrics["precision"] >= 0.85
    r_ok = metrics["recall"] >= 0.70
    print(f"  Precision target:  {'MET' if p_ok else 'MISS'} ({metrics['precision']:.1%})")
    print(f"  Recall target:     {'MET' if r_ok else 'MISS'} ({metrics['recall']:.1%})")

    return 0 if (p_ok and r_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
