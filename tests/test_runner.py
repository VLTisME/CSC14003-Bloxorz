"""Tests for Bloxorz test runner, execution wrapper, and checker extensions."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import checker
from checker import (
    execute_and_check,
    normalize_test_id,
    resolve_manifest_testcases,
    run_algorithm_subprocess,
)
import run_tests
from run_tests import get_hcm_datetime, make_result_path, parse_args, run


class RunnerIdAndManifestTests(unittest.TestCase):
    def test_normalize_test_id(self):
        # original suite
        self.assertEqual(normalize_test_id("01", "original"), "stage01")
        self.assertEqual(normalize_test_id("1", "original"), "stage01")
        self.assertEqual(normalize_test_id("stage01", "original"), "stage01")
        self.assertEqual(normalize_test_id("Stage05", "original"), "stage05")
        self.assertEqual(normalize_test_id("33", "original"), "stage33")
        self.assertEqual(normalize_test_id("01.in.json", "original"), "stage01")

        # samples suite
        self.assertEqual(normalize_test_id("01", "samples"), "sample01")
        self.assertEqual(normalize_test_id("6", "samples"), "sample06")
        self.assertEqual(normalize_test_id("sample02", "samples"), "sample02")
        self.assertEqual(normalize_test_id("03.in.json", "samples"), "sample03")

    def test_resolve_manifest_all(self):
        orig_cases = resolve_manifest_testcases(suite="original")
        self.assertEqual(len(orig_cases), 33)
        self.assertEqual(orig_cases[0]["id"], "stage01")
        self.assertEqual(orig_cases[-1]["id"], "stage33")

        sample_cases = resolve_manifest_testcases(suite="samples")
        self.assertEqual(len(sample_cases), 6)
        self.assertEqual(sample_cases[0]["id"], "sample01")
        self.assertEqual(sample_cases[-1]["id"], "sample06")

    def test_resolve_manifest_single(self):
        cases = resolve_manifest_testcases(suite="original", test_id="01")
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]["id"], "stage01")
        self.assertEqual(cases[0]["reference_length"], 7)

        cases_sample = resolve_manifest_testcases(suite="samples", test_id="sample06")
        self.assertEqual(len(cases_sample), 1)
        self.assertEqual(cases_sample[0]["id"], "sample06")

    def test_resolve_manifest_errors(self):
        with self.assertRaises(ValueError):
            resolve_manifest_testcases(suite="unknown_suite")

        with self.assertRaises(ValueError):
            resolve_manifest_testcases(suite="original", test_id="stage999")


class SubprocessAndExecutionTests(unittest.TestCase):
    def setUp(self):
        self.sample1_stage = json.loads((ROOT / "testcases" / "samples" / "01.in.json").read_text())

    def _create_mock_script(self, code: str) -> Path:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
        tmp.write(code)
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return Path(tmp.name)

    def test_subprocess_timeout_returns_tle(self):
        script = self._create_mock_script("import time\ntime.sleep(1.0)\n")
        res = execute_and_check(script, self.sample1_stage, timeout=0.1)
        self.assertEqual(res["verdict"], "TLE")
        self.assertIn("time limit exceeded", res["message"])
        self.assertFalse(res["metrics_complete"])
        self.assertIsNone(res["statistics"]["search_time_ms"])
        self.assertIsNone(res["statistics"]["peak_memory_bytes"])
        self.assertIsNone(res["statistics"]["expanded_nodes"])
        self.assertIsNone(res["statistics"]["solution_length"])
        self.assertIsNone(res["statistics"]["cost"])
        self.assertGreaterEqual(res["statistics"]["process_time_ms"], 100.0)

    def test_subprocess_crash_returns_re(self):
        script = self._create_mock_script("raise RuntimeError('unexpected crash')\n")
        res = execute_and_check(script, self.sample1_stage, timeout=5.0)
        self.assertEqual(res["verdict"], "RE")
        self.assertIn("process exited with return code", res["message"])
        self.assertFalse(res["metrics_complete"])
        self.assertIsNone(res["statistics"]["search_time_ms"])
        self.assertIsNone(res["statistics"]["peak_memory_bytes"])
        self.assertIsNone(res["statistics"]["expanded_nodes"])
        self.assertIsNone(res["statistics"]["solution_length"])
        self.assertIsNone(res["statistics"]["cost"])

    def test_subprocess_invalid_json_returns_re(self):
        script = self._create_mock_script("print('This is not json')\n")
        res = execute_and_check(script, self.sample1_stage, timeout=5.0)
        self.assertEqual(res["verdict"], "RE")
        self.assertIn("not valid JSON", res["message"])
        self.assertFalse(res["metrics_complete"])
        self.assertIsNone(res["statistics"]["search_time_ms"])

    def test_subprocess_wrong_answer_preserves_actions_null_length_and_cost(self):
        code = (
            "import json\n"
            "print(json.dumps({'status': 'solved', 'actions': ['R'], "
            "'metrics': {'search_time_ms': 1.5, 'expanded_nodes': 3, "
            "'peak_memory_bytes': 1000, 'memory_method': 'tracemalloc'}}))\n"
        )
        script = self._create_mock_script(code)
        res = execute_and_check(script, self.sample1_stage, timeout=5.0)
        self.assertEqual(res["verdict"], "WA")
        self.assertEqual(res["actions"], ["R"])
        self.assertIsNone(res["statistics"]["solution_length"])
        self.assertIsNone(res["statistics"]["cost"])
        # Search metrics are captured even for WA
        self.assertEqual(res["statistics"]["search_time_ms"], 1.5)
        self.assertEqual(res["statistics"]["expanded_nodes"], 3)
        self.assertTrue(res["metrics_complete"])

    def test_subprocess_ac_with_full_metrics(self):
        code = (
            "import json\n"
            "print(json.dumps({'status': 'solved', 'actions': ['R', 'R'], "
            "'metrics': {'search_time_ms': 2.5, 'expanded_nodes': 4, "
            "'peak_memory_bytes': 5000, 'memory_method': 'tracemalloc'}}))\n"
        )
        script = self._create_mock_script(code)
        res = execute_and_check(script, self.sample1_stage, timeout=5.0, reference_length=2)
        self.assertEqual(res["verdict"], "AC")
        self.assertEqual(res["actions"], ["R", "R"])
        self.assertEqual(res["statistics"]["solution_length"], 2)
        self.assertEqual(res["statistics"]["cost"], 2)
        self.assertEqual(res["statistics"]["reference_length"], 2)
        self.assertEqual(res["statistics"]["search_time_ms"], 2.5)
        self.assertEqual(res["statistics"]["expanded_nodes"], 4)
        self.assertEqual(res["statistics"]["peak_memory_bytes"], 5000)
        self.assertTrue(res["metrics_complete"])
        self.assertEqual(res["metrics_errors"], [])

    def test_subprocess_ac_without_metrics_is_still_ac_but_metrics_incomplete(self):
        code = (
            "import json\n"
            "print(json.dumps({'status': 'solved', 'actions': ['R', 'R']}))\n"
        )
        script = self._create_mock_script(code)
        res = execute_and_check(script, self.sample1_stage, timeout=5.0)
        self.assertEqual(res["verdict"], "AC")
        self.assertFalse(res["metrics_complete"])
        self.assertGreater(len(res["metrics_errors"]), 0)


class ResultFileAndRunTests(unittest.TestCase):
    def test_get_hcm_datetime_offset(self):
        dt = get_hcm_datetime()
        # Should be UTC+7 (+07:00)
        self.assertEqual(dt.utcoffset(), timedelta(hours=7))

    def test_make_result_path_collision_avoidance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)
            t0 = datetime(2026, 10, 21, 20, 0, 0, 123456, tzinfo=timezone(timedelta(hours=7)))
            p1 = make_result_path(dir_path, t0)
            p1.write_text("first")
            p2 = make_result_path(dir_path, t0)
            self.assertNotEqual(p1, p2)
            self.assertFalse(p2.exists())

    def test_run_tests_single_stage_with_mock_and_verify_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            res_dir = Path(tmpdir)
            code = (
                "import json\n"
                "print(json.dumps({'status': 'solved', 'actions': ['R', 'R'], "
                "'metrics': {'search_time_ms': 1.0, 'expanded_nodes': 2, "
                "'peak_memory_bytes': 3000, 'memory_method': 'tracemalloc'}}))\n"
            )
            tmp_algo = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
            tmp_algo.write(code)
            tmp_algo.close()
            self.addCleanup(lambda: Path(tmp_algo.name).unlink(missing_ok=True))

            args = parse_args([
                "--algorithm", tmp_algo.name,
                "--suite", "samples",
                "--test", "01",
                "--results_dir", str(res_dir),
            ])
            exit_code = run(args)
            self.assertEqual(exit_code, 0)

            saved_files = list(res_dir.glob("*.json"))
            self.assertEqual(len(saved_files), 1)
            payload = json.loads(saved_files[0].read_text(encoding="utf-8"))

            self.assertEqual(payload["suite"], "samples")
            self.assertEqual(payload["summary"]["total"], 1)
            self.assertEqual(payload["summary"]["passed"], 1)
            self.assertEqual(payload["summary"]["failed"], 0)
            self.assertEqual(payload["summary"]["ac"], 1)
            self.assertEqual(payload["summary"]["wa"], 0)
            self.assertEqual(payload["summary"]["fastest_test"], "sample01")
            self.assertEqual(payload["summary"]["slowest_test"], "sample01")

            test_item = payload["tests"][0]
            self.assertEqual(test_item["test_id"], "sample01")
            self.assertEqual(test_item["verdict"], "AC")
            self.assertEqual(test_item["actions"], ["R", "R"])
            self.assertEqual(test_item["statistics"]["solution_length"], 2)
            self.assertTrue(test_item["metrics_complete"])

    def test_run_tests_zero_ac_summary_has_null_fastest_and_slowest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            res_dir = Path(tmpdir)
            code = "import json\nprint(json.dumps({'status': 'unsolvable'}))\n"
            tmp_algo = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
            tmp_algo.write(code)
            tmp_algo.close()
            self.addCleanup(lambda: Path(tmp_algo.name).unlink(missing_ok=True))

            args = parse_args([
                "--algorithm", tmp_algo.name,
                "--suite", "samples",
                "--test", "01",
                "--results_dir", str(res_dir),
            ])
            exit_code = run(args)
            self.assertEqual(exit_code, 1)

            saved_files = list(res_dir.glob("*.json"))
            self.assertEqual(len(saved_files), 1)
            payload = json.loads(saved_files[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["passed"], 0)
            self.assertEqual(payload["summary"]["failed"], 1)
            self.assertIsNone(payload["summary"]["fastest_test"])
            self.assertIsNone(payload["summary"]["slowest_test"])


class CheckerCliTests(unittest.TestCase):
    def test_checker_cli_algorithm_single(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "checker.py"), "--algorithm", "algorithms/BFS.py", "--suite", "samples", "--test", "01"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("sample01: AC", proc.stdout)

    def test_checker_cli_validation_errors(self):
        # Algorithm without test or all
        proc = subprocess.run(
            [sys.executable, str(ROOT / "checker.py"), "--algorithm", "algorithms/BFS.py"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("specify either --all or --test", proc.stderr)

        # Algorithm with both test and all
        proc = subprocess.run(
            [sys.executable, str(ROOT / "checker.py"), "--algorithm", "algorithms/BFS.py", "--all", "--test", "01"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("use either --all or --test", proc.stderr)


if __name__ == "__main__":
    unittest.main()
