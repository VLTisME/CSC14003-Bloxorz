"""Sequential repeated benchmarks; preserve failures and reproducibility evidence."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from checker import DIRECTIONS, Replay, execute_and_check, read_json, resolve_manifest_testcases

METRICS = ("search_time_ms", "process_time_ms", "peak_memory_bytes", "expanded_nodes",
           "solution_length", "cost", "weighted_cost", "heuristic_preprocessing_time_ms", "astar_search_time_ms")


def replay_weighted_cost(stage, actions):
    """Independently score a valid path; do not call UCS's cost function.

    Joined moves charge final occupied cells (including splitter destinations).
    Split moves charge only the moving cube, before any identity-losing merge.
    This validates a path's cost, not global weighted optimality.
    """
    replay = Replay(stage)
    state, total = replay.initial, 0
    for action in actions:
        successor, split_at = replay.step(state, action)
        if state.split:
            origin = (state.first, state.second)[int(action[0]) - 1]
            dr, dc = DIRECTIONS[action[-1]]
            landed = [(origin[0] + dr, origin[1] + dc)]
        else:
            landed = [successor.first, successor.second]
        total += (1 + int(any(replay.cells[p] == 'B' for p in landed))
                  + 2 * int(any(replay.cells[p] == 'F' for p in landed))
                  + 3 * int(split_at is not None))
        state = successor
    if not replay.won(state):
        raise ValueError('weighted replay did not end at goal')
    return total


def validate_weighted_cost(result, stage, algo):
    if result['verdict'] != 'AC':
        return dict(status='not_applicable')
    answer = result.get('answer')
    if not isinstance(answer, dict):
        return dict(status='missing_answer')
    try:
        total = replay_weighted_cost(stage, answer['actions'])
    except (ValueError, KeyError, TypeError) as exc:
        return dict(status='error', message=str(exc))
    reported = answer.get('metrics', {}).get('weighted_cost')
    result['statistics']['weighted_cost'] = total
    valid = algo != 'UCS' or (type(reported) is int and reported == total)
    return dict(status='passed' if valid else 'mismatch', replayed=total,
                reported=reported, interpretation='path cost verified; optimality is not certified by replay')


def describe(values):
    values = [x for x in values if isinstance(x, (int, float)) and not isinstance(x, bool)]
    if not values:
        return {k: None for k in ("median", "mean", "stdev", "min", "max", "iqr")}
    q = statistics.quantiles(values, n=4, method="inclusive") if len(values) > 1 else [values[0]] * 3
    return dict(median=statistics.median(values), mean=statistics.mean(values),
                stdev=statistics.stdev(values) if len(values) > 1 else 0,
                min=min(values), max=max(values), iqr=q[2] - q[0])


def environment():
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    def read_optional(path):
        try:
            return Path(path).read_text().strip()
        except OSError:
            return None
    cpu = next((s.split(":", 1)[1].strip() for s in (read_optional('/proc/cpuinfo') or '').splitlines()
                if s.startswith('model name')), platform.processor())
    files = [ROOT / "checker.py", Path(__file__), ROOT / "testcases/manifest.json"]
    files += sorted((ROOT / 'algorithms').glob('*.py'))
    files += sorted((ROOT / 'testcases').glob('*/*.in.json'))
    return dict(python=sys.version, executable=sys.executable, platform=platform.platform(),
                cpu=cpu, logical_cpus=os.cpu_count(), meminfo=read_optional('/proc/meminfo'),
                cpu_quota=read_optional('/sys/fs/cgroup/cpu.max'),
                memory_limit=read_optional('/sys/fs/cgroup/memory.max'),
                git_head=git('rev-parse', 'HEAD'), git_status=git('status', '--short'),
                source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--algorithms', nargs='+', choices=['BFS', 'DFS', 'UCS', 'ASTAR'], default=['BFS', 'DFS', 'UCS', 'ASTAR'])
    p.add_argument('--suite', choices=['original', 'samples'], default='original')
    p.add_argument('--repeats', type=int, default=5)
    p.add_argument('--timeout', type=float, default=60)
    p.add_argument('--seed', type=int, default=20261028)
    p.add_argument('--output', type=Path,
                   default=ROOT / 'results' / ('benchmark-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f')))
    args = p.parse_args()
    if args.repeats < 2 or args.timeout <= 0 or len(set(args.algorithms)) != len(args.algorithms):
        p.error('need >=2 repeats, positive timeout, distinct algorithms')
    if args.output.exists():
        p.error('output must be a new directory; preserve previous measurements')
    args.output.mkdir(parents=True)
    (args.output / 'replays').mkdir()
    config = dict(started_at=datetime.now().astimezone().isoformat(), algorithms=args.algorithms,
                  suite=args.suite, repeats=args.repeats, timeout_seconds=args.timeout, seed=args.seed,
                  warmup='one sample01 solve per algorithm; separate process; excluded from summaries',
                  execution='sequential fresh subprocess per stage/run; seeded shuffled order per repeat',
                  instrumentation='SearchMetrics, tracemalloc on all solvers; search includes A* preprocessing',
                  shortest_path_check=['BFS', 'ASTAR'],
                  weighted_cost='1 + 1*bridge + 2*fragile + 3*split; each feature charged at most once per move',
                  weighted_cost_validation='independent checker replay outside search/process timers; UCS reported cost must match',
                  aggregation='per-stage successful complete runs: median + IQR; mean/sample SD also retained; failures explicit',
                  environment=environment())
    (args.output / 'metadata.json').write_text(json.dumps(config, indent=2, ensure_ascii=False))
    records, warmups = [], []
    cases = resolve_manifest_testcases(args.suite)
    for algo in args.algorithms:
        stage = read_json(ROOT / 'testcases/samples/01.in.json')
        result = execute_and_check(ROOT / f'algorithms/{algo}.py', stage,
                         timeout=args.timeout, reference_length=7, require_optimal=algo in ('BFS', 'ASTAR'))
        result['weighted_cost_validation'] = validate_weighted_cost(result, stage, algo)
        warmups.append(dict(algorithm=algo, result=result))
    (args.output / 'warmup.json').write_text(json.dumps(warmups, ensure_ascii=False))
    rng = random.Random(args.seed)
    with (args.output / 'runs.jsonl').open('w') as stream:
        for repeat in range(1, args.repeats + 1):
            jobs = [(case, algo) for case in cases for algo in args.algorithms]
            rng.shuffle(jobs)
            for case, algo in jobs:
                stage = read_json(ROOT / 'testcases' / case['input'])
                result = execute_and_check(ROOT / f'algorithms/{algo}.py', stage, timeout=args.timeout,
                                          reference_length=case.get('reference_length'), require_optimal=algo in ('BFS', 'ASTAR'))
                result['weighted_cost_validation'] = validate_weighted_cost(result, stage, algo)
                answer = result.pop('answer', None)
                row = dict(repeat=repeat, algorithm=algo, stage=case['id'], require_optimal=algo in ('BFS', 'ASTAR'), **result)
                records.append(row)
                stream.write(json.dumps(row, ensure_ascii=False) + '\n')
                stream.flush()
                if repeat == 1 and isinstance(answer, dict):
                    (args.output / 'replays' / f'{algo}-{case["id"]}.json').write_text(json.dumps(answer))
            print(f'repeat {repeat}/{args.repeats}: {len(records)} runs, verdicts {dict(Counter(r["verdict"] for r in records))}', flush=True)
    summary = []
    for case in cases:
        for algo in args.algorithms:
            rows = [r for r in records if r['stage'] == case['id'] and r['algorithm'] == algo]
            complete = [r for r in rows if r['verdict'] == 'AC' and r['metrics_complete']]
            item = dict(stage=case['id'], algorithm=algo, runs=len(rows), ac=sum(r['verdict'] == 'AC' for r in rows),
                        complete=len(complete), reference_length=case.get('reference_length'),
                        cost_verified=sum(r['weighted_cost_validation']['status'] == 'passed' for r in rows),
                        verdicts=dict(Counter(r['verdict'] for r in rows)))
            for metric in METRICS:
                metric_rows = [r for r in complete if metric != 'weighted_cost' or r['weighted_cost_validation']['status'] == 'passed']
                item.update({f'{metric}_{k}': v for k, v in describe([r['statistics'].get(metric) for r in metric_rows]).items()})
            summary.append(item)
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2))
    with (args.output / 'summary.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=summary[0].keys())
        writer.writeheader()
        writer.writerows(summary)
    lines = ['# Repeated benchmark', '', 'Per stage: median search time and IQR across complete AC runs; failures retained in runs.jsonl.', '',
             '| Stage | Algorithm | AC / runs | Complete | Search ms (median) | IQR ms | Python peak MiB (median) | Expanded | Moves |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    def fmt(x):
        return 'NA' if x is None else f'{x:.3f}'
    for r in summary:
        mem = r['peak_memory_bytes_median']
        lines.append(f'| {r["stage"]} | {r["algorithm"]} | {r["ac"]}/{r["runs"]} | {r["complete"]} | {fmt(r["search_time_ms_median"])} | {fmt(r["search_time_ms_iqr"])} | {fmt(mem / 2**20 if mem is not None else None)} | {fmt(r["expanded_nodes_median"])} | {fmt(r["solution_length_median"])} |')
    (args.output / 'tables.md').write_text('\n'.join(lines) + '\n')
    config['finished_at'] = datetime.now().astimezone().isoformat()
    config['verdicts'] = dict(Counter(r['verdict'] for r in records))
    config['metrics_complete'] = sum(r['metrics_complete'] for r in records)
    (args.output / 'metadata.json').write_text(json.dumps(config, indent=2, ensure_ascii=False))
    print(args.output)
    config['weighted_cost_validation'] = dict(Counter(r['weighted_cost_validation']['status'] for r in records))
    (args.output / 'metadata.json').write_text(json.dumps(config, indent=2, ensure_ascii=False))
    return 0 if all(r['verdict'] == 'AC' and r['metrics_complete'] and r['weighted_cost_validation']['status'] == 'passed' for r in records) else 1


if __name__ == '__main__':
    raise SystemExit(main())
