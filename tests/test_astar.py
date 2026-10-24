"""Correctness tests for A* and its relaxed-graph heuristic."""
from __future__ import annotations

from collections import defaultdict, deque
import json
from math import inf
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
ALGORITHMS = ROOT / "algorithms"
sys.path.insert(0, str(ALGORITHMS))
sys.path.insert(0, str(ROOT))

from astar_heuristic import (  # noqa: E402
    build_relaxed_distances,
    make_relaxed_stage,
    project_state,
    relaxed_distance,
)
from bloxorz_model import is_goal, next_states, parse_stage  # noqa: E402
from checker import Lost, execute_and_check, read_json, resolve_manifest_testcases  # noqa: E402


def reachable_graph(stage: dict):
    model = parse_stage(stage)
    start = model.initial
    states = {start}
    queue = deque([start])
    predecessors = defaultdict(set)
    while queue:
        current = queue.popleft()
        for successor, _action in next_states(current, model):
            predecessors[successor].add(current)
            if successor not in states:
                states.add(successor)
                queue.append(successor)
    goals = [state for state in states if is_goal(state, model)]
    distances_to_goal = {goal: 0 for goal in goals}
    reverse = deque(goals)
    while reverse:
        current = reverse.popleft()
        for previous in predecessors[current]:
            if previous not in distances_to_goal:
                distances_to_goal[previous] = distances_to_goal[current] + 1
                reverse.append(previous)
    return model, states, predecessors, distances_to_goal


class RelaxedHeuristicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples = [
            read_json(ROOT / "testcases" / item["input"])
            for item in resolve_manifest_testcases("samples")
        ]

    def test_relaxation_projects_each_real_edge_to_same_cost_edge(self):
        for stage in self.samples:
            with self.subTest(stage=stage["id"]):
                real_model, real_states, _, _ = reachable_graph(stage)
                relaxed_model = parse_stage(make_relaxed_stage(stage))
                for state in real_states:
                    projected = project_state(state)
                    for action in (f"{i}{d}" for i in (1, 2) for d in "UDLR") if state.split else "UDLR":
                        try:
                            real_next, _ = real_model.step(state, action)
                        except Lost:
                            continue
                        relaxed_next, _ = relaxed_model.step(projected, action)
                        self.assertEqual(project_state(real_next), relaxed_next)

    def test_reverse_bfs_heuristic_is_admissible_and_consistent(self):
        for stage in self.samples:
            with self.subTest(stage=stage["id"]):
                distances, _relaxed_states, _relaxed_edges = build_relaxed_distances(stage)
                model, states, _, real_goal_distances = reachable_graph(stage)
                for state in states:
                    h_value = relaxed_distance(state, distances)
                    real_distance = real_goal_distances.get(state, inf)
                    self.assertLessEqual(h_value, real_distance)
                    for successor, _action in next_states(state, model):
                        next_h = relaxed_distance(successor, distances)
                        self.assertLessEqual(h_value, 1 + next_h)

    def test_astar_solves_all_samples_and_matches_reference_optimum(self):
        for testcase in resolve_manifest_testcases("samples"):
            stage = read_json(ROOT / "testcases" / testcase["input"])
            with self.subTest(stage=testcase["id"]):
                result = execute_and_check(
                    ALGORITHMS / "ASTAR.py",
                    stage,
                    reference_length=testcase["reference_length"],
                    require_optimal=True,
                )
                self.assertEqual(result["verdict"], "AC", result["message"])
                self.assertTrue(result["metrics_complete"], result["metrics_errors"])
                metrics = result["answer"]["metrics"]
                self.assertGreaterEqual(metrics["relaxed_states"], 1)
                self.assertGreaterEqual(metrics["relaxed_edges"], 0)
                self.assertGreaterEqual(metrics["heuristic_preprocessing_time_ms"], 0)
                self.assertGreaterEqual(metrics["astar_search_time_ms"], 0)
                self.assertGreaterEqual(metrics["generated_nodes"], 1)
                self.assertGreaterEqual(metrics["max_frontier_size"], 1)
                self.assertEqual(result["statistics"]["relaxed_states"], metrics["relaxed_states"])
                self.assertEqual(result["statistics"]["heuristic_preprocessing_time_ms"],
                                 metrics["heuristic_preprocessing_time_ms"])


if __name__ == "__main__":
    unittest.main()
