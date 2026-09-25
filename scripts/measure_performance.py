#!/usr/bin/env python3
"""
scripts/measure_performance.py - Performance benchmarks for docs/synopsis/05-impact.md targets.

Targets (05-impact.md):
  - Cycle check + propagation + Invariant Gate: < 100 ms on 1,000 tasks / 3,000 deps
  - Board load: < 300 ms at 500 tasks
  - Drag-drop persist: < 150 ms (measured as move-task API round-trip time)
  - AI suggestions: < 8 s (not benchmarked here - covered by test_ai_suggestions_live_groq_when_key_set)

Run from repo root:
    python scripts/measure_performance.py
"""
import time
import random
import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.graph import would_create_cycle, forward_closure
from engine.scheduler import recompute
from engine.derive import derive_task_fields
from engine.invariants import check_invariants


# --- Minimal in-memory task/edge types matching engine's expected interface ---

class FakeTask:
    """Minimal stand-in for engine EngineTask - only attributes the engine reads."""
    def __init__(self, id_, board_start):
        self.id = id_
        self.board_id = 1
        self.duration_days = random.randint(1, 10)
        self.pinned_start = None
        self.planned_start = board_start
        self.planned_end = board_start + timedelta(days=self.duration_days)
        self.actual_end = None
        self.column = "backlog"
        self.blocked = False
        self.ready = True
        self.driving_prerequisite_id = None
        self.slack = {}           # engine uses dict: {prereq_id: days}
        self.blocking_prerequisite_ids = []


class FakeEdge:
    def __init__(self, task_id, prerequisite_id):
        self.task_id = task_id
        self.prerequisite_id = prerequisite_id


def build_dag(n_tasks: int, n_edges: int, board_start: date):
    """
    Build a synthetic DAG of n_tasks tasks and up to n_edges edges.
    Edges are only added from lower-id to higher-id tasks to guarantee acyclicity.
    """
    tasks = [FakeTask(i, board_start) for i in range(1, n_tasks + 1)]
    task_map = {t.id: t for t in tasks}

    edges = []
    seen = set()
    attempts = 0
    while len(edges) < n_edges and attempts < n_edges * 10:
        attempts += 1
        # prerequisite_id < task_id guarantees DAG property
        prereq_id = random.randint(1, n_tasks - 1)
        task_id = random.randint(prereq_id + 1, n_tasks)
        key = (task_id, prereq_id)
        if key not in seen:
            seen.add(key)
            edges.append(FakeEdge(task_id, prereq_id))

    return tasks, edges


def bench_engine_1000_tasks():
    """
    Benchmark: cycle check + full propagation recompute + Invariant Gate
    on 1,000 tasks and ~3,000 edges.
    Target: < 100 ms total.
    """
    board_start = date(2026, 1, 1)
    N_TASKS = 1000
    N_EDGES = 3000

    print(f"\n{'='*60}")
    print(f"BENCHMARK 1: Engine on {N_TASKS} tasks / {N_EDGES} deps")
    print(f"{'='*60}")

    tasks, edges = build_dag(N_TASKS, N_EDGES, board_start)
    actual_edges = len(edges)
    print(f"  Tasks built:  {len(tasks)}")
    print(f"  Edges built:  {actual_edges}  (target {N_EDGES}, may differ due to DAG constraints)")

    # Ensure the generated DAG starts with a valid topological schedule
    for t in tasks:
        p_ends = [tasks[e.prerequisite_id - 1].planned_end for e in edges if e.task_id == t.id]
        if p_ends:
            t.planned_start = max(p_ends)
            t.planned_end = t.planned_start + timedelta(days=t.duration_days)

    # Pick a random task to mutate and trigger recompute from
    changed_id = random.randint(1, N_TASKS // 2)
    tasks[changed_id - 1].duration_days += 3
    tasks[changed_id - 1].planned_end += timedelta(days=3)

    t0 = time.perf_counter()

    # 1. Cycle check: would adding (changed_id -> changed_id+1) create a cycle?
    would_create_cycle(changed_id, changed_id + 1, edges)

    # 2. Propagation: recompute from changed_id forward
    recompute(changed_id, tasks, edges, board_start_date=board_start)

    # 3. Invariant Gate: check acyclicity, precedence, blocked task invariants
    violations = check_invariants(tasks, edges)

    t1 = time.perf_counter()
    elapsed_ms = (t1 - t0) * 1000

    target_ms = 100.0
    status = "MET" if elapsed_ms < target_ms else "MISS"
    print(f"  Invariant violations found: {len(violations)}  (expected 0)")
    print(f"  Elapsed:  {elapsed_ms:.2f} ms")
    print(f"  Target:   < {target_ms:.0f} ms  ->  {status}")
    return elapsed_ms, status


def bench_board_load_500():
    """
    Benchmark: simulate what the board-load GET /boards/1 does in Python:
    build 500 tasks + edges and run derive_task_fields on all of them.
    Target: < 300 ms.

    Note: does NOT include SQLite I/O - measures pure Python engine cost.
    The real API adds SQLite query time on top; this measures the
    computation portion that scales with task count.
    """
    board_start = date(2026, 1, 1)
    N_TASKS = 500
    N_EDGES = 1000

    print(f"\n{'='*60}")
    print(f"BENCHMARK 2: Board-load derive on {N_TASKS} tasks / {N_EDGES} deps")
    print(f"{'='*60}")

    tasks, edges = build_dag(N_TASKS, N_EDGES, board_start)
    print(f"  Tasks: {len(tasks)},  Edges: {len(edges)}")

    # First recompute to get consistent schedule
    recompute(tasks[0].id, tasks, edges, board_start_date=board_start)

    t0 = time.perf_counter()
    for task in tasks:
        derive_task_fields(task, tasks, edges)
    t1 = time.perf_counter()

    elapsed_ms = (t1 - t0) * 1000
    target_ms = 300.0
    status = "MET" if elapsed_ms < target_ms else "MISS"
    print(f"  Elapsed:  {elapsed_ms:.2f} ms")
    print(f"  Target:   < {target_ms:.0f} ms  ->  {status}")
    return elapsed_ms, status


def bench_drag_drop_persist():
    """
    Benchmark: time the engine portion of a move-task operation
    (recompute + invariant gate only - no SQLite, no HTTP).
    Target: < 150 ms.
    """
    board_start = date(2026, 1, 1)
    N_TASKS = 100
    N_EDGES = 200

    print(f"\n{'='*60}")
    print(f"BENCHMARK 3: Drag-drop persist engine cost ({N_TASKS} tasks)")
    print(f"{'='*60}")

    tasks, edges = build_dag(N_TASKS, N_EDGES, board_start)
    changed_id = tasks[0].id

    RUNS = 50
    t0 = time.perf_counter()
    for _ in range(RUNS):
        recompute(changed_id, tasks, edges, board_start_date=board_start)
        check_invariants(tasks, edges)
    t1 = time.perf_counter()

    per_run_ms = ((t1 - t0) / RUNS) * 1000
    target_ms = 150.0
    status = "MET" if per_run_ms < target_ms else "MISS"
    print(f"  Avg over {RUNS} runs: {per_run_ms:.2f} ms/op")
    print(f"  Target:  < {target_ms:.0f} ms  ->  {status}")
    return per_run_ms, status


def main():
    print("TaskFlow Pro - Performance Benchmarks (docs/synopsis/05-impact.md)")
    print("Python:", sys.version)
    print("Note: all timings are pure Python engine, no SQLite or HTTP overhead.\n")

    r1_ms, r1_status = bench_engine_1000_tasks()
    r2_ms, r2_status = bench_board_load_500()
    r3_ms, r3_status = bench_drag_drop_persist()

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"  Engine 1k tasks/3k deps:  {r1_ms:6.2f} ms   target <100 ms   {r1_status}")
    print(f"  Board load 500 tasks:     {r2_ms:6.2f} ms   target <300 ms   {r2_status}")
    print(f"  Drag-drop engine cost:    {r3_ms:6.2f} ms   target <150 ms   {r3_status}")
    print()

    all_met = all(s == "MET" for s in [r1_status, r2_status, r3_status])
    if all_met:
        print("All performance targets MET.")
        return 0
    else:
        print("One or more targets MISSED - see numbers above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
