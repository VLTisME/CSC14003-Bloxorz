"""A* solver using exact distances in a proven relaxed Bloxorz state graph."""
from __future__ import annotations

import heapq
from itertools import count
import json
import sys
from time import perf_counter_ns

from astar_heuristic import build_relaxed_distances, relaxed_distance
from bloxorz_model import (
    State,
    initial_state,
    is_goal,
    next_states,
    parse_stage,
    reconstruct_path,
)
from solver_support import SearchMetrics


def solve_with_breakdown(stage: dict, metrics: SearchMetrics) -> tuple[list[str], dict]:
    """Solve a stage and return actions plus preprocessing/search measurements."""
    model = parse_stage(stage)
    start = initial_state(model)

    preprocessing_started = perf_counter_ns()
    distances, relaxed_states, relaxed_edges = build_relaxed_distances(stage)
    preprocessing_ms = (perf_counter_ns() - preprocessing_started) / 1_000_000

    start_h = relaxed_distance(start, distances)
    if start_h == float("inf"):
        raise RuntimeError("No solution exists in the relaxed graph, hence none exists in the real game")

    order = count()
    frontier: list[tuple[int, int, int, State]] = [(start_h, next(order), 0, start)]
    generated_nodes = 1
    max_frontier_size = 1
    g_score = {start: 0}
    parents: dict[State, tuple[State | None, str | None]] = {start: (None, None)}

    search_started = perf_counter_ns()
    while frontier:
        _f_score, _tie_breaker, queued_g, state = heapq.heappop(frontier)
        if queued_g != g_score.get(state):
            continue

        if is_goal(state, model):
            actions = reconstruct_path(parents, state)
            search_ms = (perf_counter_ns() - search_started) / 1_000_000
            return actions, {
                "heuristic_preprocessing_time_ms": preprocessing_ms,
                "astar_search_time_ms": search_ms,
                "relaxed_states": relaxed_states,
                "relaxed_edges": relaxed_edges,
                "generated_nodes": generated_nodes,
                "max_frontier_size": max_frontier_size,
            }

        metrics.expanded()
        tentative_g = queued_g + 1
        for successor, action in next_states(state, model):
            if tentative_g >= g_score.get(successor, float("inf")):
                continue
            h_score = relaxed_distance(successor, distances)
            if h_score == float("inf"):
                # A real solution would project to a relaxed path, so this state
                # provably cannot reach a real goal either.
                continue
            g_score[successor] = tentative_g
            parents[successor] = (state, action)
            heapq.heappush(frontier, (tentative_g + h_score, next(order), tentative_g, successor))
            generated_nodes += 1
            max_frontier_size = max(max_frontier_size, len(frontier))

    raise RuntimeError("No solution found, although every supplied stage should be solvable.")


def solve(stage: dict, metrics: SearchMetrics) -> list[str]:
    """Compatibility entry point following the other solver modules."""
    actions, _details = solve_with_breakdown(stage, metrics)
    return actions


def main() -> None:
    """Read one stage from stdin and print a single JSON answer to stdout."""
    stage = json.load(sys.stdin)
    with SearchMetrics() as metrics:
        actions, details = solve_with_breakdown(stage, metrics)
    output_metrics = metrics.as_dict()
    output_metrics.update(details)
    print(json.dumps({"status": "solved", "actions": actions, "metrics": output_metrics}, allow_nan=False))


if __name__ == "__main__":
    main()
