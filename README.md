# CSC14003 Bloxorz Solver

Phase 1 specification, verified test cases, and measurement helper — 16 October 2026.

Start with [the problem statement](docs/problem-statement.md), [the test-case guide](testcases/README.md), and [the runner/checker specification](docs/runner-proposal.md). See [milestones](docs/milestones.md) for progress and [stage sources](docs/stage-sources.md) for provenance.

## Available now

- JSON input/output specification, movement illustration, and worked examples.
- 33 original stages with replay-verified outputs, plus six solvable examples.
- A simple replay checker, including error messages and a total pass count.
- A shared measurement/JSON-output helper and a copyable algorithm template; start with [the algorithm guide](docs/algorithm-guide.md).

```bash
python checker.py --all
python checker.py --input testcases/original/01.in.json --output answer.json
python -m unittest discover -s tests -v
```

Requires Python 3.10 or later; the checker and helper use only the standard library. The current `checker.py --all` audits stored reference answers, not an algorithm submission.

## Phase 1 workflow

Each algorithm is a standalone Python program. It reads one JSON stage from stdin and prints one JSON result to stdout. Internal data structures are free choices. The checker replays actions; a runner will invoke algorithms and save one combined results JSON per run. The game engine and terminal 2D display come before the final 3D GUI.

Planned commands, after those programs are implemented:

```bash
python algorithms/BFS.py < testcases/original/01.in.json > answer.json
python checker.py --algorithm algorithms/BFS.py --all --timeout 10
python run_tests.py --algorithm algorithms/DFS.py --all
python run_tests.py --algorithm algorithms/BFS.py --test 06 --visualize_2d
```

## Repository structure

```text
docs/
  problem-statement.md
  runner-proposal.md
  algorithm-guide.md
  milestones.md
  stage-sources.md
  assets/Bloxorz.gif
checker.py                  # implemented replay checker
tests/test_checker.py       # checker regression checks
tests/test_solver_support.py # helper and output regression checks
testcases/
  README.md
  manifest.json             # provenance, reference lengths, verification
  samples/                  # six .in.json / .out.json pairs
  original/                 # 33 .in.json / .out.json pairs
algorithms/
  solver_support.py         # implemented measurement/JSON helper
  template.py               # scaffold; solve() must be implemented
                            # planned: BFS.py, DFS.py, UCS.py, ASTAR.py
game/                       # planned: engine.py, visualize_2d.py, later gui/
run_tests.py                # planned batch runner
results/                    # generated datetime.json files; ignored by Git
```

The report will be edited in Prism first. Local report drafts are excluded from this GitHub package. Member assignments and completion percentages belong only in the report. Milestones are tracked here and later mirrored in the report.

Every implementation task includes its corresponding report explanation and verification evidence. No task assignments have been added to GitHub.

Benchmark submissions include search time, expanded nodes, and peak traced Python allocations in their printed JSON. Basic correctness submissions and reference fixtures may omit metrics. The helper does not implement a search algorithm; the submission-executing checker, runner, and visualizers remain future work.

## Attribution

Stage encodings and reference paths are adapted from [tkoz0/bloxorz-solver](https://github.com/tkoz0/bloxorz-solver). The original game is by Damien Clarke. The reference repository does not state a license in the inspected revision; see the source notes for the exact revision, attribution, and the stage-15 path correction. The movement GIF was supplied by the project owner; its original creator/license has not been identified here.
