# Runner and checker

Specification v1.1 — 16 October 2026. The replay checker and shared measurement helper are implemented. The submission-executing checker, batch runner, and terminal visualizer remain Phase 1 deliverables.

## How a run works

1. The runner loads a selected stage and starts the selected Python algorithm.
2. It sends that stage's JSON through the program's standard input.
3. The algorithm prints the result JSON to standard output. It does not need to create a file itself.
4. The runner captures the output, error messages, exit code, and elapsed time.
5. The checker replays the actions and returns AC, WA, or RE.
6. The runner prints per-stage results and total tests passed, then writes one combined JSON file for the entire run.

The algorithm may use any internal representation. No shared solver class is required. It must not read reference answers.

## Commands

Available now:

```bash
python checker.py --input testcases/original/01.in.json --output answer.json
python checker.py --all
```

The second command replays every supplied reference answer, including the samples.

To run one future algorithm directly:

```bash
python algorithms/DFS.py < testcases/original/01.in.json > answer.json
```

Agreed submission-checker and runner commands (not yet implemented):

```bash
python checker.py --algorithm algorithms/BFS.py --test 01 --timeout 10
python checker.py --algorithm algorithms/BFS.py --all --timeout 10
python run_tests.py --algorithm algorithms/DFS.py --all
python run_tests.py --algorithm algorithms/BFS.py --test 06 --visualize_2d
python run_tests.py --algorithm algorithms/BFS.py --suite samples --all
```

The default suite is the 33 original stages; `--test 06` means original stage 6. Samples are selected explicitly. `--all` runs every stage in the selected suite. Require `--algorithm` and exactly one of `--test` or `--all`. Both tools accept `--suite original|samples` and `--timeout SECONDS`; document the default timeout when implementing it. Start a fresh algorithm process for each stage. The timeout applies separately to algorithm execution on each stage, excluding checking and animation.

The submission checker launches the algorithm, captures its printed JSON, enforces timeouts, and reports per-stage AC/WA/RE/TLE, totals by verdict, and the relevant stage IDs. The runner shares this execution and replay logic, adding statistics, a combined results file, and optional visualization. Do not duplicate game rules or execution logic between the two tools.

For one stage, the runner shows the verdict, returned actions, action count, and measured times. For all stages, show per-stage times and action counts, total algorithm elapsed time, and fastest/slowest successfully solved stages with their IDs. Show failures and timeouts separately. If no stage succeeds, fastest/slowest successful-stage statistics are unavailable.

`--visualize_2d` is runner-only and requires a single selected stage; reserve `--visualize_3d` for the later 3D implementation. The current `checker.py --all` remains a reference-data audit until the submission interface is implemented. Then move that audit to a separately named development command or test so the two meanings do not conflict.

## A simple checker

The checker performs inexpensive structural checks on the input and replays the submitted action list. It does not search for a solution and does not require the answer to equal a reference string.

- AC: wins without falling; longer valid solutions are also accepted.
- WA: loses, stops before the goal, uses a piece action in the wrong state, continues after winning, or reports `unsolvable`/`limit` without a solution.
- RE: malformed JSON/schema, an unknown action token, or a crashed algorithm.
- TLE: imposed by the runner, not inferred from the algorithm's answer.

A broken input file is INPUT_ERROR and must not be counted as an algorithm's WA. The current CLI exits with zero if all checked answers pass, otherwise nonzero.

All 33 original stages now have replay-verified reference paths. That establishes solvability for this supplied set without making the checker run a search. Future generated stages need separate input validation and a solvability certification step. The same path checker can still validate their answers.

## One output file per run

Write `results/YYYY-MM-DD_HH-MM-SS-ffffff.json`, using Asia/Ho_Chi_Minh time. The microseconds avoid ordinary filename collisions; if a name already exists, choose a new timestamp rather than overwriting it.

Illustrative structure (numbers are examples, not measurements):

```json
{
  "run_id": "2026-10-15_20-00-00-123456",
  "started_at": "2026-10-15T20:00:00.123456+07:00",
  "algorithm": "BFS",
  "program": "algorithms/BFS.py",
  "suite": "original",
  "summary": {"total": 1, "passed": 1, "failed": 0},
  "tests": [
    {
      "test_id": "stage01",
      "verdict": "AC",
      "message": "solved with 7 steps",
      "actions": ["R", "D", "D", "R", "R", "D", "R"],
      "statistics": {
        "process_time_ms": 25.0,
        "search_time_ms": null,
        "peak_memory_bytes": null,
        "memory_method": null,
        "expanded_nodes": null,
        "solution_length": 7,
        "cost": 7,
        "reference_length": 7
      },
      "exit_code": 0,
      "stderr": ""
    }
  ]
}
```

Include the configured timeout and relevant environment details in real runs. For RE, preserve the diagnostic and, when needed, a bounded copy of raw stdout. For WA, retain attempted actions but leave solution_length/cost null because they are not a successful solution. Keep reference answers unchanged.

Console output should be easy to scan, for example:

```text
stage01: AC — solved with 7 steps
R D D R R D R
stage02: WA — actions end before the goal
Passed 1/2 tests
Saved results/2026-10-15_20-00-00-123456.json
```

## Where measurements come from

The runner measures whole-process elapsed time from launch to exit. That includes startup, input parsing, searching, and serialization; call it `process_time_ms`, not search-only time.

The runner computes solution length and cost from an accepted action sequence. It cannot infer expanded nodes or search-only time from those actions. Algorithm implementations therefore additionally emit a `metrics` object:

```json
{
  "status": "solved",
  "actions": ["R", "R"],
  "metrics": {
    "search_time_ms": 0.42,
    "peak_memory_bytes": 12345,
    "memory_method": "tracemalloc",
    "expanded_nodes": 2
  }
}
```

The numbers only illustrate the fields. Benchmark output fields are also documented in the problem statement. Fixed reference outputs and basic correctness submissions may omit metrics; actual benchmark submissions require them. Existing fixtures do not need conversion.

Use [solver_support.py](../algorithms/solver_support.py) and [the template](../algorithms/template.py); the [algorithm guide](algorithm-guide.md) explains integration. `SearchMetrics` measures a single solve and prints a combined solution/metrics object. It has no search implementation and no dependency on the game checker. Authors remain responsible for counting expansions at the correct location and keeping all search setup inside the measured region.

For the future runner, `metrics_issues(answer.get("metrics"))` returns a list of missing/invalid measurement errors. Record these separately from the replay verdict, for example `metrics_complete` and `metrics_errors` in each saved test result. A winning path with incomplete metrics remains AC, but cannot supply a complete benchmark record. Validate nonnegative finite timing, nonnegative integer counts/bytes (not booleans), and the agreed memory method. Structural validation cannot prove that a solver counted honestly or placed measurements correctly; review each algorithm's instrumentation.

On a crash or timeout, preserve externally measured elapsed time and the verdict. Missing internal measurements are null, not zero; never infer them from a partial output or replace them with reference-answer values.

Use consistent definitions:

- Search time covers frontier setup, heuristic preprocessing for that solve, search, and path reconstruction. Exclude parsing, printing, checking, and animation.
- An expansion is a non-goal node whose successors are generated. Skip stale queue entries without counting them. Count genuine re-expansions again.
- The shared baseline is peak Python allocations traced with `tracemalloc`, started after JSON parsing and before search-state/frontier/heuristic construction. This includes allocations in instrumented Python search code and helper overhead, but excludes pre-existing allocations and is not whole-process resident memory. If process RSS is added later, record it separately with its method; do not mix it with traced allocation peaks.
- Unknown measurements are null, never fabricated zeroes.
- Record minimum-length comparisons as analysis, not AC/WA criteria. Published reference lengths are not automatically independent optimality proofs.

Default `SearchMetrics()` records time and memory together. Its `search_time_ms` includes memory-tracing overhead. Use this same baseline for all four algorithms; do not compare a traced timing against an untraced timing without labelling the difference.

For final experiments, prefer separate timing and memory runs. `SearchMetrics(track_memory=False)` supports an untraced timing run: memory fields are null, so it is intentionally incomplete as a standalone full benchmark record. Pair it with a separately identified default memory run using the same stage, algorithm version, settings, and successor order; retain both raw records and label the measurement mode in experiment configuration. The template defaults to full measurement; runner support for paired passes is future work. For short searches, repeat runs and document the aggregation policy.

## Terminal visualization

`--visualize_2d` replays the returned actions after search and checking. Show the board, both cube IDs when split, bridge states, move count, and outcome. The terminal view is sufficient for Phase 1; the final project still needs the required 3D GUI and automatic playback.

## Report progress

The runner/checker implementation contributes to system design and experimental methodology. Saved measurements feed results and discussion. Document the current known-solvable assumption and future generated-stage validation in the report, edited in Prism.
