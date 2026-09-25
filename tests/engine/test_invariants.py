from datetime import date, timedelta
from engine.invariants import check_invariants


def test_invariants_pass_on_valid_seeded_graph(make_seed_graph):
    tasks, edges = make_seed_graph()
    violations = check_invariants(tasks, edges)
    assert violations == []


def test_invariants_detect_cycle(make_seed_graph):
    tasks, edges = make_seed_graph()
    # Add cycle T10 -> T2
    corrupted_edges = edges + [(10, 2)]
    violations = check_invariants(tasks, corrupted_edges)
    assert "GRAPH_HAS_CYCLE" in violations


def test_invariants_detect_schedule_violation(make_seed_graph):
    tasks, edges = make_seed_graph()
    task_map = {t.id: t for t in tasks}

    # Artificially set T4 start before T2 end
    # T2 planned_end is T2.planned_start + 3
    task_map[4].planned_start = task_map[2].planned_start  # earlier than T2 finish
    violations = check_invariants(tasks, edges)
    assert any(v.startswith("SCHEDULE_VIOLATION:4") for v in violations)


def test_invariants_detect_blocked_task_advanced(make_seed_graph):
    tasks, edges = make_seed_graph()
    task_map = {t.id: t for t in tasks}

    # T2 depends on T1. T1 is in backlog (not done).
    # Moving T2 to in_progress violates invariant
    task_map[2].column = "in_progress"
    violations = check_invariants(tasks, edges)
    assert "BLOCKED_TASK_ADVANCED:2" in violations
