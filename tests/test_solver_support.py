import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tracemalloc
import unittest
from unittest.mock import patch

from algorithms.solver_support import SearchMetrics, metrics_issues
from checker import check

ROOT = Path(__file__).resolve().parents[1]


class SolverSupportTests(unittest.TestCase):
    def test_clock_counter_and_peak(self):
        with patch("algorithms.solver_support.perf_counter_ns", side_effect=[1_000_000, 3_500_000]):
            with SearchMetrics() as metrics:
                allocation = bytearray(100_000)
                metrics.expanded()
                metrics.expanded()
            result = metrics.as_dict()
        self.assertEqual(result["search_time_ms"], 2.5)
        self.assertEqual(result["expanded_nodes"], 2)
        self.assertGreaterEqual(result["peak_memory_bytes"], len(allocation))
        self.assertEqual(metrics_issues(result), [])
        self.assertFalse(tracemalloc.is_tracing())

    def test_timing_only_has_unknown_memory_not_zero(self):
        with SearchMetrics(track_memory=False) as metrics:
            self.assertFalse(tracemalloc.is_tracing())
        result = metrics.as_dict()
        self.assertIsNone(result["peak_memory_bytes"])
        self.assertIsNone(result["memory_method"])
        self.assertEqual(result["expanded_nodes"], 0)
        self.assertTrue(metrics_issues(result))

    def test_exception_propagates_and_cleans_up(self):
        metrics = SearchMetrics()
        with self.assertRaisesRegex(ValueError, "search failed"):
            with metrics:
                raise ValueError("search failed")
        self.assertFalse(tracemalloc.is_tracing())
        with self.assertRaises(RuntimeError):
            metrics.as_dict()

    def test_existing_tracer_is_not_reset_or_stopped(self):
        tracemalloc.start()
        try:
            for tracking in (True, False):
                with self.assertRaises(RuntimeError):
                    with SearchMetrics(track_memory=tracking):
                        pass
                self.assertTrue(tracemalloc.is_tracing())
        finally:
            tracemalloc.stop()

    def test_lifecycle_guards(self):
        metrics = SearchMetrics()
        with self.assertRaises(RuntimeError):
            metrics.expanded()
        with self.assertRaises(RuntimeError):
            metrics.as_dict()
        with metrics:
            with self.assertRaises(RuntimeError):
                metrics.as_dict()
        with self.assertRaises(RuntimeError):
            metrics.expanded()
        with self.assertRaises(RuntimeError):
            with metrics:
                pass

    def test_sequential_solves_reset_counter(self):
        with SearchMetrics() as first:
            first.expanded()
        with SearchMetrics() as second:
            pass
        self.assertEqual(first.as_dict()["expanded_nodes"], 1)
        self.assertEqual(second.as_dict()["expanded_nodes"], 0)

    def test_printed_json_is_captured_and_replayed(self):
        # Known sample path: verifies interoperability, not search performance.
        with SearchMetrics() as metrics:
            actions = ["R", "R"]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            metrics.print_solution(actions)
        self.assertEqual(len(output.getvalue().splitlines()), 1)
        answer = json.loads(output.getvalue())
        stage = json.loads((ROOT / "testcases/samples/01.in.json").read_text())
        self.assertEqual(check(stage, answer)["verdict"], "AC")
        self.assertEqual(metrics_issues(answer["metrics"]), [])

    def test_invalid_actions_print_nothing(self):
        with SearchMetrics() as metrics:
            pass
        for actions in ("RR", ["JUMP"], [1], None):
            with self.subTest(actions=actions):
                output = io.StringIO()
                with contextlib.redirect_stdout(output), self.assertRaises(ValueError):
                    metrics.print_solution(actions)
                self.assertEqual(output.getvalue(), "")

    def test_metrics_validation(self):
        valid = {"search_time_ms": 0.5, "expanded_nodes": 2,
                 "peak_memory_bytes": 100, "memory_method": "tracemalloc"}
        self.assertEqual(metrics_issues(valid), [])
        for cost in (0, 15):
            self.assertEqual(metrics_issues({**valid, "weighted_cost": cost}), [])
        for value in (None, [], {}, {"expanded_nodes": 1}):
            self.assertTrue(metrics_issues(value))
        for key, values in {
            "search_time_ms": [True, -1, float("inf"), float("nan"), "1"],
            "heuristic_preprocessing_time_ms": [True, -1, float("inf"), "1"],
            "astar_search_time_ms": [True, -1, float("nan"), "1"],
            "expanded_nodes": [True, -1, 1.2],
            "relaxed_states": [True, -1, 1.2],
            "generated_nodes": [True, -1, 1.2],
            "weighted_cost": [True, -1, 1.2, None, "15"],
            "peak_memory_bytes": [True, -1, 1.2, None],
            "memory_method": [None, "RSS"],
        }.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    self.assertTrue(metrics_issues({**valid, key: value}))

    def test_metrics_errors_are_not_game_verdicts(self):
        stage = json.loads((ROOT / "testcases/samples/01.in.json").read_text())
        answer = {"status": "solved", "actions": ["R", "R"], "metrics": {}}
        self.assertEqual(check(stage, answer)["verdict"], "AC")
        self.assertTrue(metrics_issues(answer["metrics"]))

    def test_template_direct_script_import_and_no_fake_answer(self):
        result = subprocess.run(
            [sys.executable, "-B", str(ROOT / "algorithms/template.py")],
            input=(ROOT / "testcases/samples/01.in.json").read_text(),
            text=True, capture_output=True, timeout=10, cwd=ROOT.parent,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("NotImplementedError", result.stderr)
        self.assertNotIn("ModuleNotFoundError", result.stderr)


if __name__ == "__main__":
    unittest.main()
