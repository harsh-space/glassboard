import pytest
from engine.graph import would_create_cycle, is_acyclic
from tests.seed_data import SEED_DEPENDENCIES


def test_seed_graph_is_acyclic():
    assert is_acyclic(SEED_DEPENDENCIES) is True


def test_cycle_rejection_t10_to_t2():
    """
    Attempt T10 -> T2 (prerequisite_id=10, task_id=2).
    Must be rejected with a cycle path starting and ending at 2, with 10 before 2.
    """
    cycle_path = would_create_cycle(10, 2, SEED_DEPENDENCIES)
    assert cycle_path is not False
    assert isinstance(cycle_path, list)
    # The cycle starts at 2 and closes back at 2 via 10 -> 2
    assert cycle_path[0] == 2
    assert cycle_path[-1] == 2
    assert cycle_path[-2] == 10
    assert len(cycle_path) >= 3


def test_cycle_self_dependency():
    """Attempting T2 -> T2 is a self-cycle."""
    cycle_path = would_create_cycle(2, 2, SEED_DEPENDENCIES)
    assert cycle_path == [2, 2]


def test_valid_dependency_no_cycle():
    """Adding an edge that does not form a cycle returns False."""
    # T1 -> T4 is already transitively present, but T1 -> T10 does not form a cycle
    res = would_create_cycle(1, 10, SEED_DEPENDENCIES)
    assert res is False
