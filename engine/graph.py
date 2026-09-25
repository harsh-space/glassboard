from collections import deque
from typing import Any, Sequence, Union


def _edge_pair(edge: Any) -> tuple[int, int]:
    """Extract (prerequisite_id, task_id) from a tuple, dict, or object."""
    if isinstance(edge, tuple) and len(edge) >= 2:
        return int(edge[0]), int(edge[1])
    if isinstance(edge, dict):
        return int(edge["prerequisite_id"]), int(edge["task_id"])
    return int(getattr(edge, "prerequisite_id")), int(getattr(edge, "task_id"))


def successors_of(task_id: int, edges: Sequence[Any]) -> list[int]:
    """Find all tasks that directly depend on task_id (edges where prerequisite_id == task_id)."""
    successors = []
    for edge in edges:
        p_id, t_id = _edge_pair(edge)
        if p_id == task_id:
            successors.append(t_id)
    return successors


def prerequisites_of(task_id: int, edges: Sequence[Any]) -> list[int]:
    """Find all tasks that task_id directly depends on (edges where task_id == task_id)."""
    prereqs = []
    for edge in edges:
        p_id, t_id = _edge_pair(edge)
        if t_id == task_id:
            prereqs.append(p_id)
    return prereqs


def reconstruct_path(parent: dict[int, int | None], target: int) -> list[int]:
    """Reconstruct path from root to target using parent pointers."""
    path = []
    curr: int | None = target
    while curr is not None:
        path.append(curr)
        curr = parent.get(curr)
    path.reverse()
    return path


def would_create_cycle(p: int, t: int, existing_edges: Sequence[Any]) -> Union[bool, list[int]]:
    """
    Check if adding proposed edge P -> T (prerequisite_id=P, task_id=T) creates a cycle.
    Traverses forward from T through existing successors.
    If P is reachable from T, adding P -> T closes a loop: T -> ... -> P -> T.
    Returns:
        False if no cycle would be created.
        list[int] representing the full cycle [T, ..., P, T] if a cycle is detected.
    """
    if p == t:
        return [t, t]

    # Pre-build adjacency for fast lookup
    adj: dict[int, list[int]] = {}
    for edge in existing_edges:
        p_id, t_id = _edge_pair(edge)
        adj.setdefault(p_id, []).append(t_id)

    visited = {t}
    queue = deque([t])
    parent: dict[int, int | None] = {t: None}

    while queue:
        current = queue.popleft()
        for dependent in adj.get(current, []):
            if dependent == p:
                # Reconstruct path T -> ... -> P and append T to complete cycle
                base_path = reconstruct_path(parent, current)
                return base_path + [p, t]
            if dependent not in visited:
                visited.add(dependent)
                parent[dependent] = current
                queue.append(dependent)

    return False


def forward_closure(start_task_id: int, edges: Sequence[Any]) -> set[int]:
    """
    BFS through successors; finds all tasks that depend directly or transitively
    on start_task_id. Includes start_task_id itself.
    """
    adj: dict[int, list[int]] = {}
    for edge in edges:
        p_id, t_id = _edge_pair(edge)
        adj.setdefault(p_id, []).append(t_id)

    closure = {start_task_id}
    queue = deque([start_task_id])

    while queue:
        curr = queue.popleft()
        for succ in adj.get(curr, []):
            if succ not in closure:
                closure.add(succ)
                queue.append(succ)

    return closure


def is_acyclic(edges: Sequence[Any]) -> bool:
    """
    Check whether the entire directed graph formed by edges is acyclic using Kahn's algorithm.
    """
    # Collect all nodes
    nodes: set[int] = set()
    adj: dict[int, list[int]] = {}
    in_degree: dict[int, int] = {}

    for edge in edges:
        p_id, t_id = _edge_pair(edge)
        nodes.add(p_id)
        nodes.add(t_id)
        adj.setdefault(p_id, []).append(t_id)
        in_degree[t_id] = in_degree.get(t_id, 0) + 1
        in_degree.setdefault(p_id, 0)

    if not nodes:
        return True

    queue = deque([node for node in nodes if in_degree[node] == 0])
    visited_count = 0

    while queue:
        curr = queue.popleft()
        visited_count += 1
        for succ in adj.get(curr, []):
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                queue.append(succ)

    return visited_count == len(nodes)
