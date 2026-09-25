from datetime import date, timedelta
from engine.scheduler import recompute


def test_diamond_math_duration_delay(make_seed_graph):
    """
    Diamond math: T2 -> T4 -> T7 and T2 -> T5 -> T7.
    T4 takes 5 days, T5 takes 2 days.
    Delaying T2 by 3 days must move T7's start by exactly 3 days, NOT 6 (max not sum).
    T4 must be the driving prerequisite for T7.
    T5's slack must be reported as 3 days.
    """
    base_date = date(2026, 1, 1)
    tasks, edges = make_seed_graph(base_date)
    task_map = {t.id: t for t in tasks}

    initial_t7_start = task_map[7].planned_start

    # Delay T2 by 3 days by increasing its duration from 3 to 6
    task_map[2].duration_days += 3
    recompute(2, tasks, edges, board_start_date=base_date)

    new_t7_start = task_map[7].planned_start
    shift_days = (new_t7_start - initial_t7_start).days

    assert shift_days == 3, f"Expected T7 to shift by 3 days, but shifted by {shift_days}"
    assert task_map[7].driving_prerequisite_id == 4
    assert task_map[7].slack.get(5) == 3


def test_diamond_math_pinned_start_delay(make_seed_graph):
    """
    Delaying T2 by setting pinned_start 3 days later also shifts T7 by exactly 3 days, not 6.
    """
    base_date = date(2026, 1, 1)
    tasks, edges = make_seed_graph(base_date)
    task_map = {t.id: t for t in tasks}

    initial_t7_start = task_map[7].planned_start

    # T2 initial planned_start was base_date + 2 = Jan 3
    # Pin T2 to Jan 6 (3 days delay)
    task_map[2].pinned_start = task_map[2].planned_start + timedelta(days=3)
    recompute(2, tasks, edges, board_start_date=base_date)

    new_t7_start = task_map[7].planned_start
    shift_days = (new_t7_start - initial_t7_start).days

    assert shift_days == 3, f"Expected T7 to shift by 3 days, but shifted by {shift_days}"
    assert task_map[7].driving_prerequisite_id == 4
    assert task_map[7].slack.get(5) == 3
