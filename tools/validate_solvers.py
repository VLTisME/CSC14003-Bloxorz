"""Check all solvers and independently validate UCS cost, outside benchmarks."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import heapq
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from checker import DIRECTIONS, Lost, Replay, execute_and_check, read_json, resolve_manifest_testcases


def transition(replay, state, action):
    """Independent scoring on checker transitions; do not import UCS/model costs."""
    successor, triggered_at = replay.step(state, action)
    if state.split:
        position = (state.first, state.second)[int(action[0]) - 1]
        dr, dc = DIRECTIONS[action[-1]]
        contacts = [(position[0] + dr, position[1] + dc)]
    else:
        contacts = (successor.first, successor.second)
    fee = 1
    for symbol, penalty in (("F", 2), ("B", 1)):
        if any(replay.cells[position] == symbol for position in contacts):
            fee += penalty
    if triggered_at is not None:
        fee += 3
    return successor, fee


def optimum(stage):
    """Dijkstra on checker states, independent of the solver implementation."""
    replay = Replay(stage)
    serial = itertools.count()
    frontier = [(0, next(serial), replay.initial)]
    best = {replay.initial: 0}
    while frontier:
        cost, _, state = heapq.heappop(frontier)
        if cost != best[state]:
            continue
        if replay.won(state):
            return cost
        for prefix in (("1", "2") if state.split else ("",)):
            for direction in DIRECTIONS:
                try:
                    successor, fee = transition(replay, state, prefix + direction)
                except Lost:
                    continue
                candidate = cost + fee
                if candidate < best.get(successor, float("inf")):
                    best[successor] = candidate
                    heapq.heappush(frontier, (candidate, next(serial), successor))
    raise ValueError("No weighted path to goal")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--output", type=Path, default=ROOT / "results" /
                        ("validation-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".json"))
    args = parser.parse_args()
    if args.timeout <= 0 or args.output.exists():
        parser.error("timeout must be positive; output must not already exist")
    rows = []
    for suite in ("samples", "original"):
        for case in resolve_manifest_testcases(suite):
            stage = read_json(ROOT / "testcases" / case["input"])
            expected = optimum(stage)
            for algorithm in ("BFS", "DFS", "UCS", "ASTAR"):
                result = execute_and_check(
                    ROOT / "algorithms" / (algorithm + ".py"), stage,
                    timeout=args.timeout, reference_length=case.get("reference_length"),
                    require_optimal=algorithm in ("BFS", "ASTAR"),
                )
                row = dict(suite=suite, stage=case["id"], algorithm=algorithm,
                           verdict=result["verdict"], metrics_complete=result["metrics_complete"],
                           reference_weighted_cost=expected, passed=False)
                if result["verdict"] == "AC" and result["metrics_complete"]:
                    answer = result["answer"]
                    replay = Replay(stage)
                    state, total = replay.initial, 0
                    for action in answer["actions"]:
                        state, fee = transition(replay, state, action)
                        total += fee
                    reported = answer.get("metrics", {}).get("weighted_cost")
                    row.update(solution_length=len(answer["actions"]), weighted_cost=total,
                               reported_weighted_cost=reported,
                               passed=replay.won(state) and total >= expected and
                               (algorithm != "UCS" or type(reported) is int and reported == total == expected))
                rows.append(row)
        print(suite, dict(Counter(r["verdict"] for r in rows if r["suite"] == suite)), flush=True)
    report = dict(total=len(rows), passed=sum(r["passed"] for r in rows),
                  method="Independent Dijkstra and path scoring on checker.Replay, outside timing measurements",
                  results=rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Passed {report['passed']}/{report['total']}; {args.output}")
    return 0 if all(r["passed"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
