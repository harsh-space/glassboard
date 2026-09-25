from engine.derive import handle_regression, is_blocked, is_ready


def test_regression_when_tasks_were_done(make_seed_graph):
    """
    Regression test per BUILD_SPEC.md §3.4 & §8.1:
    1. Mark all tasks T1..T10 as 'done' with actual_end = planned_end.
    2. Move T2 from 'done' back to 'in_progress'.
    3. Run handle_regression(t2, tasks, edges).
    4. Assert T2.actual_end is cleared (None).
    5. Assert direct dependents T4 and T5 become Blocked (their prerequisite T2 is not done).
    6. Assert all downstream tasks that were 'done' (T4, T5, T6, T7, T8, T9, T10) are
       flagged in needs_reverification (and NOT auto-moved out of done).
    7. Assert upstream T1 and independent branch T3 remain done and ready.
    """
    tasks, edges = make_seed_graph()
    task_map = {t.id: t for t in tasks}

    for t in tasks:
        t.column = "done"
        t.actual_end = t.planned_end

    # All tasks are ready when all are done
    for t in tasks:
        assert is_ready(t, tasks, edges) is True

    # Move T2 back to in_progress
    task_map[2].column = "in_progress"

    # Handle regression
    reverification_ids = handle_regression(task_map[2], tasks, edges)

    # T2 actual_end is cleared
    assert task_map[2].actual_end is None

    # Direct dependents of T2 become Blocked because T2 is not done
    assert is_blocked(task_map[4], tasks, edges) is True
    assert is_blocked(task_map[5], tasks, edges) is True

    # Downstream done tasks must all be flagged for reverification
    downstream_ids = {4, 5, 6, 7, 8, 9, 10}
    assert set(reverification_ids) == downstream_ids

    # Tasks are not auto-moved out of done per spec §3.4
    for t_id in downstream_ids:
        assert task_map[t_id].column == "done"

    # Upstream T1 remains done and ready; T3 depends only on T1 (which is done)
    assert task_map[1].column == "done"
    assert is_ready(task_map[1], tasks, edges) is True
    assert is_ready(task_map[3], tasks, edges) is True


def test_regression_when_downstream_in_progress(make_seed_graph):
    """
    When downstream tasks were in_progress or backlog:
    Moving T2 back to in_progress leaves downstream tasks blocked.
    """
    tasks, edges = make_seed_graph()
    task_map = {t.id: t for t in tasks}

    # T1 is done
    task_map[1].column = "done"
    task_map[1].actual_end = task_map[1].planned_end

    # T2 is done
    task_map[2].column = "done"
    task_map[2].actual_end = task_map[2].planned_end

    # T4 and T5 are now ready
    assert is_ready(task_map[4], tasks, edges) is True
    assert is_ready(task_map[5], tasks, edges) is True

    # Now move T2 back to in_progress
    task_map[2].column = "in_progress"
    handle_regression(task_map[2], tasks, edges)

    # T4 and T5 become Blocked again
    assert is_blocked(task_map[4], tasks, edges) is True
    assert is_blocked(task_map[5], tasks, edges) is True

    # And since T4/T5 are not done, T6, T7, T8, T9, T10 are all blocked
    for t_id in [6, 7, 8, 9, 10]:
        assert is_blocked(task_map[t_id], tasks, edges) is True
