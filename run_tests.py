"""Batch runner and benchmark tool for Bloxorz solver algorithms."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from checker import (
    DEFAULT_TIMEOUT,
    execute_and_check,
    read_json,
    resolve_manifest_testcases,
)


def get_hcm_datetime() -> datetime:
    """Return current datetime in Asia/Ho_Chi_Minh timezone."""
    try:
        import zoneinfo
        return datetime.now(zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh"))
    except Exception:
        return datetime.now(timezone(timedelta(hours=7)))


def make_result_path(results_dir: Path, dt: datetime) -> Path:
    """Generate a unique timestamped result JSON path in results_dir."""
    results_dir.mkdir(parents=True, exist_ok=True)
    current_dt = dt
    while True:
        filename = current_dt.strftime("%Y-%m-%d_%H-%M-%S-%f.json")
        target = results_dir / filename
        if not target.exists():
            return target
        current_dt = current_dt + timedelta(microseconds=1)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bloxorz batch test runner and benchmark tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--algorithm",
        type=Path,
        required=True,
        help="Path to algorithm Python program (e.g. algorithms/BFS.py)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all stages in the selected suite",
    )
    parser.add_argument(
        "--test",
        type=str,
        help="Specific test/stage ID to run (e.g. 01, 06, stage01, sample01)",
    )
    parser.add_argument(
        "--suite",
        type=str,
        choices=["original", "samples"],
        default="original",
        help="Suite to run: original (33 stages) or samples (6 stages)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Per-stage algorithm execution timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--require-optimal",
        action="store_true",
        help="Require solution length to equal each test's reference optimum (for BFS/UCS/A*)",
    )
    parser.add_argument(
        "--visualize_2d",
        action="store_true",
        help="Replay solution visually on 2D terminal after checking (requires --test)",
    )
    parser.add_argument(
        "--results_dir",
        type=Path,
        default=ROOT_DIR / "results",
        help="Directory to save JSON benchmark run results",
    )

    args = parser.parse_args(argv)

    if args.all and args.test:
        parser.error("use either --all or --test, not both")
    if not args.all and not args.test:
        parser.error("specify either --all or --test")
    if args.visualize_2d and args.all:
        parser.error("--visualize_2d requires selecting a single stage via --test")
    if not args.algorithm.exists():
        parser.error(f"algorithm program not found: {args.algorithm}")

    return args


def run(args: argparse.Namespace) -> int:
    started_at = get_hcm_datetime()
    run_id = started_at.strftime("%Y-%m-%d_%H-%M-%S-%f")
    algo_name = args.algorithm.stem

    try:
        testcases = resolve_manifest_testcases(suite=args.suite, test_id=args.test)
    except Exception as exc:
        print(f"Error resolving testcases: {exc}", file=sys.stderr)
        return 1

    if args.require_optimal and any(tc.get("reference_length") is None for tc in testcases):
        print("Error: --require-optimal needs a reference_length for every selected test.", file=sys.stderr)
        return 1

    results_list = []
    is_single_test = bool(args.test)

    for tc in testcases:
        stage_path = ROOT_DIR / "testcases" / tc["input"]
        try:
            stage_data = read_json(stage_path)
        except (OSError, ValueError) as exc:
            print(f"{tc['id']}: INPUT_ERROR — cannot read input stage: {exc}")
            results_list.append({
                "test_id": tc["id"],
                "verdict": "INPUT_ERROR",
                "message": f"cannot read input stage: {exc}",
                "actions": None,
                "statistics": {
                    "process_time_ms": 0.0,
                    "search_time_ms": None,
                    "peak_memory_bytes": None,
                    "memory_method": None,
                    "expanded_nodes": None,
                    "solution_length": None,
                    "cost": None,
                    "reference_length": tc.get("reference_length"),
                },
                "metrics_complete": False,
                "metrics_errors": [f"cannot read input stage: {exc}"],
                "exit_code": None,
                "stderr": "",
            })
            continue

        ref_len = tc.get("reference_length")
        res = execute_and_check(
            args.algorithm,
            stage_data,
            timeout=args.timeout,
            reference_length=ref_len,
            require_optimal=args.require_optimal,
        )
        results_list.append(res)

        test_id = res["test_id"]
        verdict = res["verdict"]
        message = res["message"]
        proc_time = res["statistics"]["process_time_ms"]

        if is_single_test:
            print(f"{test_id}: {verdict} — {message} ({proc_time:.2f} ms)")
            if res.get("actions"):
                print(" ".join(res["actions"]))
        else:
            print(f"{test_id}: {verdict} — {message} ({proc_time:.2f} ms)")

    total = len(testcases)
    passed = sum(1 for r in results_list if r["verdict"] == "AC")
    failed = total - passed
    ac = passed
    wa = sum(1 for r in results_list if r["verdict"] == "WA")
    re = sum(1 for r in results_list if r["verdict"] == "RE")
    tle = sum(1 for r in results_list if r["verdict"] == "TLE")
    input_error = sum(1 for r in results_list if r["verdict"] == "INPUT_ERROR")
    total_process_time_ms = round(sum(r["statistics"]["process_time_ms"] for r in results_list), 3)

    ac_tests = [r for r in results_list if r["verdict"] == "AC"]
    if ac_tests:
        fastest_test = min(ac_tests, key=lambda r: r["statistics"]["process_time_ms"])["test_id"]
        slowest_test = max(ac_tests, key=lambda r: r["statistics"]["process_time_ms"])["test_id"]
    else:
        fastest_test = None
        slowest_test = None

    print(f"Passed {passed}/{total} tests")
    if total > 1:
        print(f"Summary: AC={ac}, WA={wa}, RE={re}, TLE={tle}, INPUT_ERROR={input_error}")
        print(f"Total process time: {total_process_time_ms:.2f} ms")
        if ac > 0:
            fastest_item = min(ac_tests, key=lambda r: r["statistics"]["process_time_ms"])
            slowest_item = max(ac_tests, key=lambda r: r["statistics"]["process_time_ms"])
            print(f"Fastest solve: {fastest_item['test_id']} ({fastest_item['statistics']['process_time_ms']:.2f} ms)")
            print(f"Slowest solve: {slowest_item['test_id']} ({slowest_item['statistics']['process_time_ms']:.2f} ms)")
        else:
            print("No stages were solved successfully.")
        if failed > 0:
            failed_ids = [r["test_id"] for r in results_list if r["verdict"] != "AC"]
            print(f"Failed stages: {', '.join(failed_ids)}")

    # Clean tests for JSON serialization (remove internal fields)
    cleaned_tests = []
    for r in results_list:
        cleaned_tests.append({
            "test_id": r["test_id"],
            "verdict": r["verdict"],
            "message": r["message"],
            "actions": r["actions"],
            "statistics": r["statistics"],
            "metrics_complete": r["metrics_complete"],
            "metrics_errors": r["metrics_errors"],
            "exit_code": r["exit_code"],
            "stderr": r["stderr"],
        })

    payload = {
        "run_id": run_id,
        "started_at": started_at.isoformat(),
        "algorithm": algo_name,
        "program": str(args.algorithm),
        "suite": args.suite,
        "timeout_seconds": args.timeout,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "ac": ac,
            "wa": wa,
            "re": re,
            "tle": tle,
            "input_error": input_error,
            "total_process_time_ms": total_process_time_ms,
            "fastest_test": fastest_test,
            "slowest_test": slowest_test,
        },
        "tests": cleaned_tests,
    }

    result_path = make_result_path(args.results_dir, started_at)
    result_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        display_path = result_path.relative_to(Path.cwd())
    except ValueError:
        display_path = result_path
    print(f"Saved {display_path}")

    if args.visualize_2d and results_list and results_list[0]["verdict"] != "INPUT_ERROR":
        first_tc = testcases[0]
        first_res = results_list[0]
        actions = first_res.get("actions") or []
        if not actions:
            print("Cannot visualize: no actions returned by the algorithm.")
        else:
            stage_path = ROOT_DIR / "testcases" / first_tc["input"]
            stage_data = read_json(stage_path)
            try:
                from game.visualize_2d import replay_solution
                replay_solution(stage_data, {"actions": actions})
            except Exception as exc:
                print(f"Visualization error: {exc}", file=sys.stderr)

    return 0 if passed == total and input_error == 0 else 1


def main() -> int:
    args = parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
