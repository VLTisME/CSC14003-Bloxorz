"""Copy to BFS.py, DFS.py, UCS.py, or ASTAR.py and implement solve().

Run as a script: python algorithms/BFS.py < testcases/original/01.in.json
This template deliberately fails until a real search is implemented.
"""
import json
import sys

from solver_support import SearchMetrics


def solve(stage: dict, metrics: SearchMetrics) -> list[str]:
    # Build the initial state, frontier, and any heuristic tables here.
    # Skip stale/duplicate entries and check the goal before counting expansion.
    # Immediately before generating a non-goal node's successors, call:
    # metrics.expanded()
    # Count real re-expansions, including across all iterations of IDS.
    # Reconstruct and return the winning action list before leaving solve().
    raise NotImplementedError("Implement your search algorithm; do not read reference answers")


def main() -> None:
    stage = json.load(sys.stdin)
    with SearchMetrics() as metrics:
        actions = solve(stage, metrics)
    metrics.print_solution(actions)


if __name__ == "__main__":
    main()
