"""BFS solver for the Bloxorz project."""

from collections import deque
import json
import sys

from bloxorz_model import (
    initial_state,
    is_goal,
    next_states,
    parse_stage,
    reconstruct_path,
)
from solver_support import SearchMetrics


def solve(stage: dict, metrics: SearchMetrics) -> list[str]:
    """Find a shortest valid action sequence for one Bloxorz stage."""
    model = parse_stage(stage)
    start = initial_state(model)

    frontier = deque([start])
    visited = {start}
    parents = {start: (None, None)}

    while frontier:
        current_state = frontier.popleft()

        if is_goal(current_state, model):
            return reconstruct_path(parents, current_state)

        metrics.expanded()

        for successor_state, action in next_states(current_state, model):
            if successor_state in visited:
                continue

            visited.add(successor_state)
            parents[successor_state] = (current_state, action)
            frontier.append(successor_state)

    raise RuntimeError("No solution found, although every supplied stage should be solvable.")


def main() -> None:
    """Read one stage from stdin and print one solution JSON object."""
    stage = json.load(sys.stdin)

    with SearchMetrics() as metrics:
        actions = solve(stage, metrics)

    metrics.print_solution(actions)


if __name__ == "__main__":
    main()