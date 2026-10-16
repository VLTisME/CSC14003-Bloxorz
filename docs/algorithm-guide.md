# Algorithm author quick start

Prepared 16 October 2026. The helper is ready; the algorithm implementations and submission runner are not implemented yet.

## Best practice

Implement and check the pure algorithm first, then add measurements. The helper is optional for correctness testing; complete metrics are required for benchmark results used in the report.

1. **Create your own algorithm file.** Write `algorithms/BFS.py`, `DFS.py`, `UCS.py`, or `ASTAR.py`. You may copy `template.py` and temporarily remove its measurement wrapper, or start with the minimal structure below. Leave the shared template unchanged so teammates can copy it too.
2. **Implement the search and check its answers.** Read one stage from standard input, find a winning action list, and print JSON containing `status` and `actions`. No metrics and no file-writing code are required at this stage. Begin with the samples, then check the original stages; never read reference answers from your solver.
3. **Add tracking after correctness checks pass.** Keep the search logic, add the `SearchMetrics` wrapper, pass it to `solve`, and call `metrics.expanded()` immediately before generating a non-goal node's successors. Build search structures and reconstruct the path inside the measured region. Use `metrics.print_solution(actions)` instead of the minimal JSON print.
4. **Repeat correctness tests before benchmarking.** Instrumentation should not change the answers. Check the counter placement and measurement boundaries, then collect actual benchmark results using the same protocol across all algorithms. Passing test cases is evidence, not a substitute for explaining completeness and optimality assumptions.
5. **Write the report alongside the code.** Document the algorithm design while implementing it, the measurement protocol when adding tracking, and results only after collecting them.

A minimal pure-algorithm starting point is:

```python
import json
import sys


def solve(stage):
    # Implement your search and return a list of winning actions.
    raise NotImplementedError


def main():
    stage = json.load(sys.stdin)
    actions = solve(stage)
    print(json.dumps({"status": "solved", "actions": actions}))


if __name__ == "__main__":
    main()
```

After implementing `solve`, test it from the repository root:

```bash
python algorithms/BFS.py < testcases/samples/01.in.json > answer.json
python checker.py --input testcases/samples/01.in.json --output answer.json
```

The shell saves the printed answer; the algorithm does not open an output file. A correct path can receive AC without metrics. These current commands check one selected stage; `checker.py --all` currently audits stored reference paths, not your algorithm. The submission-running commands remain planned.

When ready to add tracking, use the template pattern below. Keep the algorithm file beside `solver_support.py` so `from solver_support import SearchMetrics` works when running `python algorithms/BFS.py`. The helper does not supply movement rules, a search algorithm, or proof that a path wins.

## Start from the template

Copy `algorithms/template.py` to your algorithm's file in the same directory (BFS.py, DFS.py, UCS.py, or ASTAR.py). Keep `solver_support.py` beside it and implement `solve(stage, metrics)`. The template intentionally raises `NotImplementedError` until replaced with real search logic; it is not a sample solver.

The template's entry point already follows this pattern:

```python
stage = json.load(sys.stdin)
with SearchMetrics() as metrics:
    actions = solve(stage, metrics)
metrics.print_solution(actions)
```

`solve` may use any internal data structures. It returns a list such as `["R", "R"]`; do not return a JSON string and do not read reference answers. The helper prints one JSON object containing status, actions, and metrics. No output file needs to be opened by the algorithm.

## Count expansions consistently

In your search loop, skip stale entries or duplicates that will not be expanded, then check the goal. If the node is not a goal and you are about to generate its successors, call:

```python
metrics.expanded()
```

Count the parent once, not once per successor or legal move. Count a genuine re-expansion again. For IDS, keep one measurement context around all depth iterations; do not reset the counter each iteration. A node cut off at a depth limit without generating successors is not expanded. For A*, count a reopened state if you actually expand it again.

The helper cannot automatically infer this event from arbitrary solver code. Review counter placement together when comparing algorithms.

## Measurement boundaries

Parse the stage JSON before entering the context. Build the initial search state, frontier, duplicate-detection structures, and heuristic tables inside `solve`. Reconstruct the final action list before returning, so that work is included. Print only after leaving the context. Do not build search structures globally before measurement.

The default helper uses an elapsed-time clock and traces Python allocation peaks. It includes memory-tracing and small helper overheads; it does not measure all process memory or pre-existing input allocations. Do not start/stop memory tracing inside your solver or nest measurement contexts. A new helper instance is required for each solve.

For separately labelled timing-only experiments, `SearchMetrics(track_memory=False)` disables tracing and reports null memory fields. It is not a complete replacement for the default benchmark output. Keep both timing-only and memory-run records if using paired measurements; see [the measurement specification](runner-proposal.md#where-measurements-come-from).

## Test a completed algorithm now

From the repository root, after implementing your algorithm:

```bash
python algorithms/BFS.py < testcases/samples/01.in.json > answer.json
python checker.py --input testcases/samples/01.in.json --output answer.json
```

The shell captures printed JSON in `answer.json`; the algorithm does not create it. The current replay checker accepts the added metrics but only judges the path. It does not execute your algorithm or enforce a timeout. The agreed future submission-checker and runner commands are listed in [Judging](problem-statement.md#judging).

Do not print progress messages to standard output. For debug messages, use `print("Searching...", file=sys.stderr)` after importing `sys`. Exceptions should propagate so the future submission checker can report RE instead of a fake successful answer.

## Benchmark completeness and report updates

A correct path can receive AC without metrics, but a benchmark record requires all agreed fields. `metrics_issues(metrics_object)` is provided for the future runner to identify incomplete/invalid fields separately from AC/WA. The helper checks action-token formatting when printing; only replay can establish that the path wins.

After implementing an algorithm, update its report subsection with the idea, pseudocode, data structures, duplicate handling, completeness/optimality assumptions, and complexity. Record where you count expansions and what you measure in experimental methodology. Add measured results only after real runs; the helper's tests are not algorithm benchmarks.
