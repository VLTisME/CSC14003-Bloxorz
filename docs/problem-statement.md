# Bloxorz Solver

Version 1.1 — 16 October 2026. Gameplay and stage inputs are unchanged; this revision adds submission commands and benchmark-output guidance.

## Problem

You are given a board and a rectangular block of size **1 × 1 × 2**. The block starts standing upright on the starting tile. Find a sequence of moves that makes the complete rectangular block stand upright on the goal.

**Every stage supplied with this project is solvable.** Different sequences may solve the same stage. Any sequence that reaches the goal without losing is accepted.

## How the block moves

The block can be upright, lying horizontally, or lying vertically. Each directional move rolls it 90 degrees around an edge:

- An upright block tips over and occupies the next two cells in that direction.
- A lying block rolled along its length stands upright on the next cell beyond its end.
- A lying block rolled sideways stays lying and shifts by one cell.

![The block tipping, rolling, and standing upright](assets/Bloxorz.gif)

The animation illustrates the movement. The input board specifies the actual layout of each stage.

## Tiles, switches, and small cubes

| Tile | Behaviour |
|---|---|
| Normal floor | Supports the block in every orientation |
| Void | No floor; moving any part of the block here loses |
| Goal | Only the complete 1 × 1 × 2 block standing upright here wins |
| Fragile floor | Supports a lying rectangular block or a small cube; breaks under the upright rectangular block, causing a loss |
| Bridge | Supports pieces when active; behaves like void when inactive |
| Soft switch | Pressed by any part of the piece that moves onto it, including a small cube |
| Heavy switch | Pressed only by the upright complete rectangular block |
| Splitter | When the complete block stands upright here, teleports it into two 1 × 1 × 1 cubes |

Switches can toggle a bridge, activate it, or deactivate it. Their effects remain after the block leaves. Different switches may control the same bridge.

After splitting, move either small cube one cell at a time. Small cubes may stand on fragile tiles and the goal. **A small cube on the goal does not win.** They can press soft switches, but cannot activate heavy switches or splitters. When the two cubes occupy horizontally or vertically adjacent cells, they automatically rejoin into a lying rectangular block. Diagonal contact does not join them.

A cube that remains on a soft switch does not press it again when the other cube moves.

## Moves and cost

Every directional move costs **1**. Changing which small cube is selected costs **0**. Teleportation, bridge changes, switch effects, and automatic rejoining also cost **0**. The total cost is the number of directional moves.

Moving off the board, onto void, or onto an inactive bridge loses the game. Standing the complete rectangular block on fragile floor also loses. These are recognizable game moves with losing outcomes, so a solver must avoid them in its answer.

BFS and UCS find a shortest solution under this unit-cost model. A* does so when its heuristic and implementation satisfy the usual optimality conditions. “Optimal cost” therefore means the fewest directional moves. DFS may find a longer solution. The checker accepts any winning path; solution lengths are compared separately in the experiments.

## Input

Read one JSON object from standard input:

```json
{
  "id": "sample04",
  "board": [
    "SO.BBBG",
    "#######"
  ],
  "bridges": [
    {"id": "b1", "cells": [[0, 3], [0, 4], [0, 5]], "active": false}
  ],
  "switches": [
    {"at": [0, 1], "effects": [{"bridge": "b1", "mode": "toggle"}]}
  ],
  "splitters": []
}
```

### Input fields

Every input object must contain the keys **`id`, `board`, `bridges`, `switches`, and `splitters`**. A stage may have no bridge, switch, or splitter ("[ ]").

- `id`: the stage's name or identifier.
- `board`: a two-dimensional board represented by an array of row strings.
- `bridges`: the cells in each bridge group and whether it is initially active.
- `switches`: the position and bridge effects of each soft/heavy switch.
- `splitters`: the position and two teleport destinations of each splitter.

Coordinates are **[row, column]**, starting at zero. Up decreases the row; right increases the column. All switch effects and teleport destinations are supplied; there is no hidden information.

### Board symbols

| Symbol | Meaning |
|---|---|
| `#` | Void |
| `.` | Normal floor |
| `S` | Start; normal floor after the block moves away |
| `G` | Goal |
| `F` | Fragile floor |
| `B` | Bridge cell |
| `O` | Soft switch |
| `X` | Heavy switch |
| `T` | Splitter |

### Bridges and switch effects

A bridge definition contains a unique `id`, a nonempty array of `cells`, and an initial boolean `active`. Active means the bridge supports a piece.

A switch's `at` identifies its cell. The board symbol determines whether it is soft or heavy. Each item in `effects` names a bridge and an operation:

- `toggle`: reverse its active state.
- `on`: set it active.
- `off`: set it inactive.

An `on` or `off` operation does not lock the bridge forever; another switch may change it later. Leaving a switch does not undo its effect.

### Splitters

```json
{"at": [0, 3], "destinations": [[2, 0], [2, 2]]}
```

Standing upright on `T` at (0,3) splits the block. Cube **1** appears at (2,0), and cube **2** appears at (2,2). These IDs remain fixed until rejoining. A later split assigns IDs from that splitter's destination order.

## Constraints

- 1 ≤ number of rows, number of columns ≤ 30.
- The board contains exactly one `S` and one `G`, at different positions.
- Rows have equal lengths, use only the listed symbols, and all coordinates refer to cells inside the board.
- Every `B` belongs to exactly one bridge group. Groups do not overlap.
- Every `O`/`X` has exactly one switch definition. Every `T` has exactly one splitter definition.
- Each switch has a nonempty list of effects. Its bridge IDs exist and are not repeated within that switch's effects.
- Split destinations are distinct, non-adjacent tiles. They must support their cubes when the teleport occurs.
- Different switches may affect the same bridge.
- All supplied stages have a solution.

The 30 × 30 bound is the project's chosen input limit.

## Game resolution

1. Move the rectangular block, or move the selected small cube.
2. Check support using the current bridge states. A fall or an upright complete block on fragile floor loses. Small cubes may stand on `F` and `G`; neither position makes them win. Cubes cannot overlap.
3. Apply switches pressed by the piece that moved. A stationary cube does not press its switch again. If multiple switches are pressed, process them by increasing row, then column; within a switch, use the listed effect order.
4. If the complete block stands upright on a splitter, teleport and split it.
5. Check support again after bridge changes and teleportation, including any stationary cube. Losing support loses the game.
6. Join orthogonally adjacent small cubes. Joining does not press switches a second time.
7. Win if the complete block is upright on the goal. Otherwise await a move.

## Output

Print one JSON object containing `status` and `actions` to standard output. This minimal form is sufficient for correctness testing and fixed reference examples:

```json
{"status": "solved", "actions": ["R", "R", "R", "R"]}
```

Your algorithm only needs to print its answer; it does not need to create an output file. After constructing the Python list `actions`, use:

```python
import json

print(json.dumps({"status": "solved", "actions": actions}))
```

Print exactly one JSON object to standard output. The submission checker or runner will capture it directly; the runner saves the combined results file. Diagnostic messages should go to standard error, for example `print("Searching...", file=sys.stderr)` after importing `sys`.

### Required measurements for benchmarking

For benchmark runs used in the report, also include `metrics` in the same printed JSON object. The values below illustrate the format; they are not measured results:

```json
{
  "status": "solved",
  "actions": ["R", "R", "R", "R"],
  "metrics": {
    "search_time_ms": 0.42,
    "expanded_nodes": 8,
    "peak_memory_bytes": 12345,
    "memory_method": "tracemalloc"
  }
}
```

| Field | Meaning |
|---|---|
| `search_time_ms` | Finite, nonnegative elapsed milliseconds for search setup, heuristic preprocessing, search, and path reconstruction; excludes JSON parsing and printing |
| `expanded_nodes` | Nonnegative integer count of non-goal nodes whose successors are generated; skip stale/duplicate entries, but count actual re-expansions and all IDS iterations |
| `peak_memory_bytes` | Nonnegative integer peak of Python allocations traced during the search; excludes allocations made before measurement and is not total process memory |
| `memory_method` | `"tracemalloc"` for the shared measurement baseline |

Use the provided [algorithm template](../algorithms/template.py) and [helper guide](algorithm-guide.md) to collect these fields consistently. The helper times the search, tracks allocation peaks, and prints the JSON; you call `metrics.expanded()` immediately before generating each non-goal node's successors. It does not implement your search or constrain your state representation.

Missing or invalid metrics do not turn a winning path into WA. They make the run incomplete for benchmarking, which the future runner must flag separately. Reference outputs remain unchanged and omit measured values. The runner derives solution length and cost from the accepted actions and measures whole-process elapsed time itself. See [the runner specification](runner-proposal.md) for measurement overhead and separate timing runs.

### Actions

| Piece to move | Up | Down | Left | Right |
|---|---|---|---|---|
| Complete block | `U` | `D` | `L` | `R` |
| Small cube 1 | `1U` | `1D` | `1L` | `1R` |
| Small cube 2 | `2U` | `2D` | `2L` | `2R` |

For example, `1R` selects small cube 1 for free and moves it right at cost 1. There is no separate action for switching the selected cube.

Use small-cube actions only while split, and complete-block actions only while joined. Stop the action list when the goal is reached.

## Judging

### Running your algorithm

These are the agreed commands for the game designer to implement; they are **not available yet**. Run them from the repository root once implemented:

```bash
# Judge one original stage
python checker.py --algorithm algorithms/BFS.py --test 01 --timeout 10

# Judge all 33 original stages
python checker.py --algorithm algorithms/BFS.py --all --timeout 10

# Run one stage with statistics and terminal playback
python run_tests.py --algorithm algorithms/BFS.py --test 01 --visualize_2d

# Run all original stages and save combined statistics
python run_tests.py --algorithm algorithms/BFS.py --all
```

- `--algorithm PATH`: Python algorithm to execute.
- `--test NN`: one stage; use this or `--all`, not both.
- `--all`: every stage in the selected suite.
- `--suite original|samples`: suite to use; defaults to `original`.
- `--timeout SECONDS`: maximum algorithm execution time per stage, excluding checking and visualization. The implementation must document its default.
- `--visualize_2d`: runner-only playback for a single stage. A later `--visualize_3d` flag will provide 3D playback.

Both commands report per-stage verdicts and totals. The runner additionally displays statistics and saves one combined results JSON. A fresh algorithm process receives one stage through standard input and prints one JSON answer, even when the command selects all stages.

Until these commands are implemented, use the current file-based replay check:

```bash
python algorithms/BFS.py < testcases/original/01.in.json > answer.json
python checker.py --input testcases/original/01.in.json --output answer.json
```

The shell's `>` saves the printed answer; your algorithm still does not write a file itself. The current `python checker.py --all` only verifies stored reference answers, not a submission. See [the runner specification](runner-proposal.md) for implementation guidance.

### Verdicts

- **Accepted (AC):** replay finishes with the complete block upright on the goal and never loses.
- **Wrong Answer (WA):** the path loses, uses the wrong piece for the current state, stops before winning, continues after winning, or claims the stage is unsolvable.
- **Runtime Error (RE):** the program crashes, its output is malformed, or its action list contains an unknown token such as `JUMP`. The runner prints the error and identifies the offending action where possible.
- **Time Limit Exceeded (TLE):** the runner stops a program that exceeds its configured time limit.

The checker replays the actions. It does not compare action strings with a single expected answer, and it does not solve the stage itself. Reference outputs provide one working solution for each stage.

## Examples

These small examples are separate from the original game's 33 stages.

### Example 1 — rolling upright and sideways

Input:

```json
{
  "id": "sample02",
  "board": [
    "S..#",
    "#..#",
    "#..#",
    "#..G"
  ],
  "bridges": [],
  "switches": [],
  "splitters": []
}
```

Output:

```json
{"status":"solved","actions":["R","D","D","D","R"]}
```

Right makes the block lie across columns 1–2. Three down moves roll it sideways to row 3. The last right move stands it on the goal. Cost: 5.

### Example 2 — fragile floor

Input:

```json
{
  "id": "sample03",
  "board": [
    "SFFG",
    "####"
  ],
  "bridges": [],
  "switches": [],
  "splitters": []
}
```

Output:

```json
{"status":"solved","actions":["R","R"]}
```

The block lies on the fragile cells, then stands on the goal. Cost: 2.

### Example 3 — soft switch and bridge

Use the complete input shown in the Input section.

Output:

```json
{"status":"solved","actions":["R","R","R","R"]}
```

The first roll presses `O`, activating all three bridge cells. The remaining rolls cross them and reach the goal. Cost: 4.

### Example 4 — splitting and rejoining

Input:

```json
{
  "id": "sample06",
  "board": [
    "S..T",
    "####",
    "...G"
  ],
  "bridges": [],
  "switches": [],
  "splitters": [
    {"at":[0,3],"destinations":[[2,0],[2,2]]}
  ]
}
```

Output:

```json
{"status":"solved","actions":["R","R","1R","R"]}
```

Two right moves reach `T`. The cubes appear at (2,0) and (2,2). Cube 1 moves right, making them adjacent and joining them. The complete block then rolls right onto the goal. Cost: 4.

## Orientation reference

This table is for implementing movement. It does not prescribe internal classes. Horizontal(r,c) occupies (r,c),(r,c+1); Vertical(r,c) occupies (r,c),(r+1,c).

| Current placement | Up | Down | Left | Right |
|---|---|---|---|---|
| Upright(r,c) | Vertical(r−2,c) | Vertical(r+1,c) | Horizontal(r,c−2) | Horizontal(r,c+1) |
| Horizontal(r,c) | Horizontal(r−1,c) | Horizontal(r+1,c) | Upright(r,c−1) | Upright(r,c+2) |
| Vertical(r,c) | Upright(r−1,c) | Upright(r+2,c) | Vertical(r,c−1) | Vertical(r,c+1) |
