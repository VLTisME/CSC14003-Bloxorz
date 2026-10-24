"""Replay-based Bloxorz checker. No search algorithm is used to judge a path."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter_ns

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from algorithms.solver_support import metrics_issues
except ImportError:
    def metrics_issues(metrics: object) -> list[str]:
        return ["cannot import solver_support.metrics_issues"]

DIRECTIONS = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}
ACTIONS = set(DIRECTIONS) | {str(i) + d for i in (1, 2) for d in DIRECTIONS}


class StageError(ValueError):
    """Broken input data; not a wrong answer by the algorithm."""


class Lost(ValueError):
    """A recognized game action loses or cannot be applied in this state."""


@dataclass(frozen=True)
class State:
    split: bool
    first: tuple[int, int]
    second: tuple[int, int]
    bridges: tuple[bool, ...]


class Replay:
    """Small deterministic replay model used by the checker and data audit."""

    def __init__(self, stage: dict):
        if not isinstance(stage, dict):
            raise StageError("input must be a JSON object")
        required = {"id", "board", "bridges", "switches", "splitters"}
        if not required <= stage.keys():
            raise StageError("missing input fields: " + ", ".join(sorted(required - stage.keys())))
        if not isinstance(stage["id"], str) or not stage["id"]:
            raise StageError("id must be a nonempty string")
        rows = stage["board"]
        if not isinstance(rows, list) or not rows or not all(isinstance(r, str) and r for r in rows):
            raise StageError("board must be a nonempty array of nonempty row strings")
        if len({len(r) for r in rows}) != 1 or len(rows) > 30 or len(rows[0]) > 30:
            raise StageError("board must be rectangular and at most 30 by 30")
        text = "".join(rows)
        if set(text) - set("#.SGFBOXT") or text.count("S") != 1 or text.count("G") != 1:
            raise StageError("board symbols, start, or goal are invalid")
        self.cells = {(r, c): ch for r, row in enumerate(rows) for c, ch in enumerate(row)}
        self.stage_id = stage["id"]
        self.goal = next(p for p, ch in self.cells.items() if ch == "G")

        def coordinate(value):
            if not isinstance(value, list) or len(value) != 2 or not all(type(v) is int for v in value):
                raise StageError("coordinates must be [row, column] integer pairs")
            p = tuple(value)
            if p not in self.cells:
                raise StageError(f"coordinate outside board: {value}")
            return p

        for field in ("bridges", "switches", "splitters"):
            if not isinstance(stage[field], list):
                raise StageError(f"{field} must be an array")
        self.bridge_cells = {}
        bridge_ids = {}
        initial_flags = []
        try:
            for index, bridge in enumerate(stage["bridges"]):
                name = bridge["id"]
                if not isinstance(name, str) or not name or name in bridge_ids:
                    raise StageError("bridge IDs must be unique nonempty strings")
                if type(bridge["active"]) is not bool or not isinstance(bridge["cells"], list) or not bridge["cells"]:
                    raise StageError("bridge needs nonempty cells and a boolean active value")
                bridge_ids[name] = index
                initial_flags.append(bridge["active"])
                for value in bridge["cells"]:
                    p = coordinate(value)
                    if self.cells[p] != "B" or p in self.bridge_cells:
                        raise StageError("bridge cells must be distinct B cells")
                    self.bridge_cells[p] = index
            if set(self.bridge_cells) != {p for p, ch in self.cells.items() if ch == "B"}:
                raise StageError("every B cell must have a bridge definition")
            self.switches = {}
            for switch in stage["switches"]:
                p = coordinate(switch["at"])
                if self.cells[p] not in "OX" or p in self.switches:
                    raise StageError("switch definitions must match distinct O/X cells")
                if not isinstance(switch["effects"], list) or not switch["effects"]:
                    raise StageError("switch needs a nonempty effects array")
                effects = []
                targeted = set()
                for effect in switch["effects"]:
                    name, mode = effect["bridge"], effect["mode"]
                    if name not in bridge_ids or name in targeted or mode not in ("on", "off", "toggle"):
                        raise StageError("invalid or duplicate bridge effect")
                    targeted.add(name)
                    effects.append((bridge_ids[name], mode))
                self.switches[p] = effects
            if set(self.switches) != {p for p, ch in self.cells.items() if ch in "OX"}:
                raise StageError("every O/X cell needs a switch definition")
            self.splitters = {}
            for splitter in stage["splitters"]:
                p = coordinate(splitter["at"])
                if self.cells[p] != "T" or p in self.splitters:
                    raise StageError("splitter definitions must match distinct T cells")
                destinations = splitter["destinations"]
                if not isinstance(destinations, list) or len(destinations) != 2:
                    raise StageError("splitter needs two destinations")
                a, b = map(coordinate, destinations)
                if self.cells[a] == "#" or self.cells[b] == "#" or abs(a[0]-b[0]) + abs(a[1]-b[1]) <= 1:
                    raise StageError("split destinations must be distinct, non-adjacent tiles")
                self.splitters[p] = (a, b)
            if set(self.splitters) != {p for p, ch in self.cells.items() if ch == "T"}:
                raise StageError("every T cell needs a splitter definition")
        except (KeyError, TypeError, IndexError) as exc:
            raise StageError(f"malformed feature definition: {exc}") from exc
        start = next(p for p, ch in self.cells.items() if ch == "S")
        self.initial = State(False, start, start, tuple(initial_flags))

    def won(self, state: State) -> bool:
        return not state.split and state.first == state.second == self.goal

    def _supported(self, state: State):
        if state.split and state.first == state.second:
            raise Lost("two small cubes overlap")
        for p in {state.first, state.second}:
            tile = self.cells.get(p, "#")
            if tile == "#":
                raise Lost(f"block falls into void or outside the board at {p}")
            if tile == "B" and not state.bridges[self.bridge_cells[p]]:
                raise Lost(f"block falls through inactive bridge at {p}")
            if tile == "F" and not state.split and state.first == state.second:
                raise Lost(f"upright rectangular block breaks fragile tile at {p}")

    def step(self, state: State, action: str) -> tuple[State, tuple[int, int] | None]:
        """Return resolved state and splitter coordinate, if a split occurred."""
        if action not in ACTIONS:
            raise ValueError(f"unknown action {action!r}")
        if self.won(state):
            raise Lost("action appears after the stage was already won")
        a, b = state.first, state.second
        dr, dc = DIRECTIONS[action[-1]]
        def shift(p, distance=1):
            return p[0] + distance*dr, p[1] + distance*dc
        if state.split:
            if len(action) != 2:
                raise Lost("select cube 1 or 2 in the action while the block is split")
            if action[0] == "1":
                a = shift(a)
                landed = [a]
            else:
                b = shift(b)
                landed = [b]
        else:
            if len(action) != 1:
                raise Lost("a small-cube action was used while the block was joined")
            if a == b:
                a, b = sorted((shift(a), shift(a, 2)))
            elif (a[0] == b[0] and dc) or (a[1] == b[1] and dr):
                leading = max((a, b), key=lambda p: dr*p[0] + dc*p[1])
                a = b = shift(leading)
            else:
                a, b = sorted((shift(a), shift(b)))
            landed = sorted({a, b})
        candidate = State(state.split, a, b, state.bridges)
        self._supported(candidate)
        flags = list(state.bridges)
        # Stable row/column order defines the result even if two switches share a target.
        for p in sorted(landed):
            tile = self.cells[p]
            if tile == "O" or (tile == "X" and not candidate.split and a == b):
                for index, mode in self.switches[p]:
                    flags[index] = not flags[index] if mode == "toggle" else mode == "on"
        split_at = None
        split = candidate.split
        if not split and a == b and self.cells[a] == "T":
            split_at = a
            a, b = self.splitters[a]
            split = True
        candidate = State(split, a, b, tuple(flags))
        self._supported(candidate)
        if split and abs(a[0]-b[0]) + abs(a[1]-b[1]) == 1:
            a, b = sorted((a, b))
            candidate = State(False, a, b, tuple(flags))
        return candidate, split_at


def check(stage: dict, answer: object) -> dict:
    model = Replay(stage)
    result = {"test_id": model.stage_id, "verdict": "RE", "message": "", "steps_checked": 0,
              "solution_length": None, "cost": None}
    if not isinstance(answer, dict) or not isinstance(answer.get("status"), str):
        result["message"] = "output must be an object with a string status"
        return result
    if answer["status"] in ("unsolvable", "limit"):
        result.update(verdict="WA", message="all supplied stages are solvable; no solution was returned")
        return result
    if answer["status"] != "solved":
        result["message"] = "unknown output status"
        return result
    actions = answer.get("actions")
    if not isinstance(actions, list) or not all(isinstance(a, str) for a in actions):
        result["message"] = "actions must be an array of action strings"
        return result
    for i, action in enumerate(actions, 1):
        if action not in ACTIONS:
            result["message"] = f"action {i}: unknown token {action!r}"
            return result
    state = model.initial
    for i, action in enumerate(actions, 1):
        try:
            state, _ = model.step(state, action)
        except Lost as exc:
            result.update(verdict="WA", message=f"action {i} ({action}): {exc}", steps_checked=i)
            return result
        result["steps_checked"] = i
    if not model.won(state):
        result.update(verdict="WA", message="actions end before the rectangular block stands on the goal")
        return result
    result.update(verdict="AC", message=f"solved with {len(actions)} steps", solution_length=len(actions), cost=len(actions))
    return result


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


DEFAULT_TIMEOUT: float = 10.0


def normalize_test_id(raw_id: str, suite: str = "original") -> str:
    cleaned = raw_id.strip()
    cleaned = Path(cleaned).name
    for ext in (".in.json", ".out.json", ".json"):
        if cleaned.endswith(ext):
            cleaned = cleaned[:-len(ext)]
            break

    prefix = "sample" if suite == "samples" else "stage"
    low = cleaned.lower()
    if low.startswith("stage") or low.startswith("sample"):
        num_part = low.replace("stage", "").replace("sample", "")
        if num_part.isdigit():
            return f"{prefix}{int(num_part):02d}"
        return low

    if low.isdigit():
        return f"{prefix}{int(low):02d}"

    return cleaned


def resolve_manifest_testcases(
    suite: str = "original",
    test_id: str | None = None,
    manifest_path: Path | None = None,
) -> list[dict]:
    if manifest_path is None:
        manifest_path = ROOT_DIR / "testcases" / "manifest.json"

    if manifest_path.exists():
        manifest = read_json(manifest_path)
        all_cases = manifest.get("testcases", [])
        suite_cases = [
            tc for tc in all_cases
            if tc.get("input", "").startswith(f"{suite}/")
        ]
    else:
        suite_dir = ROOT_DIR / "testcases" / suite
        suite_cases = []
        if suite_dir.exists():
            for p in sorted(suite_dir.glob("*.in.json")):
                stem = p.name.replace(".in.json", "")
                prefix = "sample" if suite == "samples" else "stage"
                case_id = f"{prefix}{int(stem):02d}" if stem.isdigit() else stem
                suite_cases.append({
                    "id": case_id,
                    "input": f"{suite}/{p.name}",
                    "output": f"{suite}/{stem}.out.json",
                    "reference_length": None,
                })

    if not suite_cases:
        raise ValueError(f"No test cases found for suite {suite!r}")

    if test_id is not None:
        target_id = normalize_test_id(test_id, suite)
        matched = [
            tc for tc in suite_cases
            if tc.get("id") == target_id
            or tc.get("input") == f"{suite}/{test_id}.in.json"
            or Path(tc.get("input", "")).stem.replace(".in", "") == test_id
        ]
        if not matched:
            valid_ids = [tc.get("id") for tc in suite_cases]
            raise ValueError(
                f"Test case {test_id!r} (normalized {target_id!r}) not found in suite {suite!r}. "
                f"Available tests: {valid_ids[:5]}... (total {len(valid_ids)})"
            )
        return matched

    return suite_cases


def run_algorithm_subprocess(
    algorithm_path: Path | str,
    stage_data: dict,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    algo_path = Path(algorithm_path).resolve()
    if not algo_path.exists():
        raise FileNotFoundError(f"Algorithm program not found: {algo_path}")

    stage_json = json.dumps(stage_data)
    t_start = perf_counter_ns()
    try:
        proc = subprocess.run(
            [sys.executable, str(algo_path)],
            input=stage_json,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        elapsed_ms = (perf_counter_ns() - t_start) / 1_000_000
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timed_out": False,
            "process_time_ms": elapsed_ms,
        }
    except subprocess.TimeoutExpired as exc:
        elapsed_ms = (perf_counter_ns() - t_start) / 1_000_000
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return {
            "exit_code": None,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": True,
            "process_time_ms": max(timeout * 1000.0, elapsed_ms),
        }
    except Exception as exc:
        elapsed_ms = (perf_counter_ns() - t_start) / 1_000_000
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
            "timed_out": False,
            "process_time_ms": elapsed_ms,
        }


def execute_and_check(
    algorithm_path: Path | str,
    stage_data: dict,
    timeout: float = DEFAULT_TIMEOUT,
    reference_length: int | None = None,
) -> dict:
    test_id = stage_data.get("id", "unknown")
    run_res = run_algorithm_subprocess(algorithm_path, stage_data, timeout=timeout)
    process_time_ms = run_res["process_time_ms"]
    exit_code = run_res["exit_code"]
    stderr = run_res["stderr"]
    raw_stdout = run_res["stdout"]

    if run_res["timed_out"]:
        return {
            "test_id": test_id,
            "verdict": "TLE",
            "message": f"time limit exceeded ({timeout}s)",
            "actions": None,
            "statistics": {
                "process_time_ms": round(process_time_ms, 3),
                "search_time_ms": None,
                "peak_memory_bytes": None,
                "memory_method": None,
                "expanded_nodes": None,
                "solution_length": None,
                "cost": None,
                "reference_length": reference_length,
            },
            "metrics_complete": False,
            "metrics_errors": [f"time limit exceeded ({timeout}s)"],
            "exit_code": None,
            "stderr": stderr,
            "answer": None,
        }

    if exit_code != 0:
        return {
            "test_id": test_id,
            "verdict": "RE",
            "message": f"process exited with return code {exit_code}",
            "actions": None,
            "statistics": {
                "process_time_ms": round(process_time_ms, 3),
                "search_time_ms": None,
                "peak_memory_bytes": None,
                "memory_method": None,
                "expanded_nodes": None,
                "solution_length": None,
                "cost": None,
                "reference_length": reference_length,
            },
            "metrics_complete": False,
            "metrics_errors": [f"process exited with return code {exit_code}"],
            "exit_code": exit_code,
            "stderr": stderr,
            "answer": None,
        }

    try:
        answer = json.loads(raw_stdout)
    except json.JSONDecodeError as exc:
        return {
            "test_id": test_id,
            "verdict": "RE",
            "message": f"output is not valid JSON: {exc}",
            "actions": None,
            "statistics": {
                "process_time_ms": round(process_time_ms, 3),
                "search_time_ms": None,
                "peak_memory_bytes": None,
                "memory_method": None,
                "expanded_nodes": None,
                "solution_length": None,
                "cost": None,
                "reference_length": reference_length,
            },
            "metrics_complete": False,
            "metrics_errors": [f"JSON decode error: {exc}"],
            "exit_code": 0,
            "stderr": stderr,
            "answer": None,
        }

    check_res = check(stage_data, answer)
    verdict = check_res["verdict"]
    message = check_res["message"]
    actions = answer.get("actions") if isinstance(answer, dict) and isinstance(answer.get("actions"), list) else None

    metrics_data = answer.get("metrics") if isinstance(answer, dict) else None
    issues = metrics_issues(metrics_data)
    metrics_complete = (len(issues) == 0)

    if verdict == "AC":
        search_time_ms = metrics_data.get("search_time_ms") if isinstance(metrics_data, dict) else None
        peak_memory_bytes = metrics_data.get("peak_memory_bytes") if isinstance(metrics_data, dict) else None
        memory_method = metrics_data.get("memory_method") if isinstance(metrics_data, dict) else None
        expanded_nodes = metrics_data.get("expanded_nodes") if isinstance(metrics_data, dict) else None
        solution_length = check_res.get("solution_length")
        cost = check_res.get("cost")
    elif verdict == "WA":
        search_time_ms = metrics_data.get("search_time_ms") if isinstance(metrics_data, dict) else None
        peak_memory_bytes = metrics_data.get("peak_memory_bytes") if isinstance(metrics_data, dict) else None
        memory_method = metrics_data.get("memory_method") if isinstance(metrics_data, dict) else None
        expanded_nodes = metrics_data.get("expanded_nodes") if isinstance(metrics_data, dict) else None
        solution_length = None
        cost = None
    else:  # RE
        search_time_ms = None
        peak_memory_bytes = None
        memory_method = None
        expanded_nodes = None
        solution_length = None
        cost = None
        metrics_complete = False

    statistics = {
        "process_time_ms": round(process_time_ms, 3),
        "search_time_ms": search_time_ms,
        "peak_memory_bytes": peak_memory_bytes,
        "memory_method": memory_method,
        "expanded_nodes": expanded_nodes,
        "solution_length": solution_length,
        "cost": cost,
        "reference_length": reference_length,
    }

    return {
        "test_id": test_id,
        "verdict": verdict,
        "message": message,
        "actions": actions,
        "statistics": statistics,
        "metrics_complete": metrics_complete,
        "metrics_errors": issues,
        "exit_code": 0,
        "stderr": stderr,
        "answer": answer,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Path to input stage JSON")
    parser.add_argument("--output", type=Path, help="Path to answer JSON")
    parser.add_argument("--all", action="store_true", help="Replay every test / reference")
    parser.add_argument("--algorithm", type=Path, help="Path to algorithm Python program")
    parser.add_argument("--test", type=str, help="Stage ID or number (e.g. 01, stage01)")
    parser.add_argument("--suite", type=str, choices=["original", "samples"], default="original", help="Test suite to run (default: original)")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help=f"Timeout per test in seconds (default: {DEFAULT_TIMEOUT})")
    args = parser.parse_args()

    if args.algorithm:
        if args.input or args.output:
            parser.error("cannot combine --algorithm with --input or --output")
        if args.all and args.test:
            parser.error("use either --all or --test, not both")
        if not args.all and not args.test:
            parser.error("specify either --all or --test when using --algorithm")

        try:
            cases = resolve_manifest_testcases(suite=args.suite, test_id=args.test)
        except Exception as exc:
            parser.error(str(exc))

        counts = {"AC": 0, "WA": 0, "RE": 0, "TLE": 0}
        for tc in cases:
            input_path = ROOT_DIR / "testcases" / tc["input"]
            try:
                stage = read_json(input_path)
            except (OSError, ValueError) as exc:
                print(f"{tc['id']}: INPUT_ERROR — cannot read input stage: {exc}")
                continue

            ref_len = tc.get("reference_length")
            res = execute_and_check(args.algorithm, stage, timeout=args.timeout, reference_length=ref_len)
            verdict = res["verdict"]
            counts[verdict] = counts.get(verdict, 0) + 1
            print(f"{res['test_id']}: {verdict} — {res['message']}")

        total = len(cases)
        passed = counts["AC"]
        print(f"Passed {passed}/{total} tests (AC: {counts['AC']}, WA: {counts['WA']}, RE: {counts['RE']}, TLE: {counts['TLE']})")
        return 0 if passed == total else 1

    if args.test:
        parser.error("--test requires --algorithm")

    if args.all:
        if args.input or args.output:
            parser.error("use --all alone, or --input and --output together")
        root = ROOT_DIR / "testcases"
        pairs = [(p, p.with_name(p.name.replace(".in.json", ".out.json"))) for p in sorted(root.glob("*/*.in.json"))]
    else:
        if not args.input or not args.output:
            parser.error("provide both --input and --output, or use --all, or specify --algorithm")
        pairs = [(args.input, args.output)]

    if not pairs:
        parser.error("no test cases found")

    passed = 0
    for input_path, output_path in pairs:
        try:
            stage = read_json(input_path)
            Replay(stage)
        except (OSError, ValueError) as exc:
            print(f"{input_path.name}: INPUT_ERROR — {exc}")
            continue
        try:
            answer = read_json(output_path)
        except (OSError, ValueError) as exc:
            print(f"{stage['id']}: RE — cannot read output JSON: {exc}")
            continue
        result = check(stage, answer)
        passed += result["verdict"] == "AC"
        print(f"{result['test_id']}: {result['verdict']} — {result['message']}")

    print(f"Passed {passed}/{len(pairs)} tests")
    return 0 if passed == len(pairs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
