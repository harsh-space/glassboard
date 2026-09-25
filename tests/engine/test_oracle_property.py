import copy
import random
from datetime import date, timedelta
from engine.scheduler import recompute
from engine.oracle import recompute_from_scratch
from tests.engine.conftest import EngineTask


def generate_random_dag(num_nodes: int, edge_prob: float, base_date: date) -> tuple[list[EngineTask], list[tuple[int, int]]]:
    tasks = []
    for i in range(1, num_nodes + 1):
        dur = random.randint(1, 14)
        task = EngineTask(
            id=i,
            duration_days=dur,
            column="backlog",
            board_start_date=base_date,
        )
        tasks.append(task)

    edges = []
    for u in range(1, num_nodes + 1):
        for v in range(u + 1, num_nodes + 1):
            if random.random() < edge_prob:
                edges.append((u, v))

    return tasks, edges


def test_property_1000_random_graphs_oracle_agreement():
    """
    Generate 1,000 random valid DAGs with random schedule mutations.
    Assert recompute() and the brute-force oracle.py always agree on every task's start and end.
    """
    random.seed(42)
    base_date = date(2026, 1, 1)

    for i in range(1000):
        num_nodes = random.randint(5, 20)
        edge_prob = random.uniform(0.15, 0.4)
        tasks, edges = generate_random_dag(num_nodes, edge_prob, base_date)

        # Initial full schedule
        recompute_from_scratch(tasks, edges, board_start_date=base_date)

        # Randomly complete some tasks
        for t in tasks:
            if random.random() < 0.2:
                t.column = "done"
                t.actual_end = t.planned_end

        # Pick a random task to mutate
        mutated_task_id = random.randint(1, num_nodes)
        task_map = {t.id: t for t in tasks}
        target = task_map[mutated_task_id]

        mutation_type = random.choice(["duration", "pinned_start"])
        if mutation_type == "duration":
            target.duration_days += random.randint(1, 7)
        else:
            target.pinned_start = (target.planned_start or base_date) + timedelta(days=random.randint(1, 5))

        # Clone state for oracle
        tasks_for_oracle = [copy.deepcopy(t) for t in tasks]

        # 1. Run incremental recompute on mutated node
        recompute(mutated_task_id, tasks, edges, board_start_date=base_date)

        # 2. Run brute-force oracle on the clone
        recompute_from_scratch(tasks_for_oracle, edges, board_start_date=base_date)

        # 3. Assert exact agreement across all tasks
        oracle_map = {t.id: t for t in tasks_for_oracle}
        for t in tasks:
            o_task = oracle_map[t.id]
            assert t.planned_start == o_task.planned_start, (
                f"Graph {i}, Task {t.id}: planned_start mismatch "
                f"(incremental={t.planned_start}, oracle={o_task.planned_start})"
            )
            assert t.planned_end == o_task.planned_end, (
                f"Graph {i}, Task {t.id}: planned_end mismatch "
                f"(incremental={t.planned_end}, oracle={o_task.planned_end})"
            )
