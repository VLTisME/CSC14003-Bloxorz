"""Admissible relaxed-graph heuristic for the project's Bloxorz rules.

The relaxation changes fragile tiles, bridges, and switches into ordinary floor,
but keeps block orientation, split-cube positions/IDs, and splitter destinations.
Every real move therefore has a same-cost relaxed successor. Exact reverse-BFS
distances in that supergraph are lower bounds on real remaining move counts.
"""
from __future__ import annotations

from collections import defaultdict, deque

from bloxorz_model import BloxorzModel, State, is_goal, next_states, parse_stage


def make_relaxed_stage(stage: dict) -> dict:
    """Return a copy with dynamic support restrictions removed, splitters kept."""
    relaxed = dict(stage)
    relaxed["board"] = [row.translate(str.maketrans({"F": ".", "B": ".", "O": ".", "X": "."}))
                        for row in stage["board"]]
    relaxed["bridges"] = []
    relaxed["switches"] = []
    relaxed["splitters"] = [dict(splitter) for splitter in stage["splitters"]]
    return relaxed


def project_state(state: State) -> State:
    """Forget bridge flags while retaining all positional/future-relevant geometry."""
    return State(state.split, state.first, state.second, ())


def build_relaxed_distances(stage: dict) -> tuple[dict[State, int], int, int]:
    """Build exact goal distances over the relaxed graph using reverse BFS.

    The forward pass explores states reachable from this stage's relaxed start
    and records predecessor edges. A reverse BFS from every relaxed goal then
    computes exact unit-cost distance-to-goal values. ``edge_count`` counts
    distinct directed relaxed state edges.
    """
    model: BloxorzModel = parse_stage(make_relaxed_stage(stage))
    start = project_state(model.initial)
    reachable = {start}
    forward = deque([start])
    predecessors: dict[State, set[State]] = defaultdict(set)
    edge_count = 0

    while forward:
        state = forward.popleft()
        for successor, _action in next_states(state, model):
            if successor not in predecessors or state not in predecessors[successor]:
                predecessors[successor].add(state)
                edge_count += 1
            if successor not in reachable:
                reachable.add(successor)
                forward.append(successor)

    goals = [state for state in reachable if is_goal(state, model)]
    if not goals:
        raise ValueError("The relaxed Bloxorz graph has no reachable goal state")

    distances = {goal: 0 for goal in goals}
    reverse = deque(goals)
    while reverse:
        state = reverse.popleft()
        for previous in predecessors.get(state, ()):
            if previous not in distances:
                distances[previous] = distances[state] + 1
                reverse.append(previous)

    return distances, len(reachable), edge_count


def relaxed_distance(state: State, distances: dict[State, int]) -> float | int:
    """Return h(state); infinity proves no real solution can exist from it."""
    from math import inf

    return distances.get(project_state(state), inf)
