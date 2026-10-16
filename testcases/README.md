# Test cases

Final supplied set v1.0 — 15 October 2026.

- **original/**: all 33 original-game stages, converted to the project format.
- **samples/**: six small, solvable examples for understanding and debugging.
- **manifest.json**: provenance, stage IDs, passcodes, features, reference lengths, and verification details.

Each stage has `NN.in.json` and `NN.out.json`. The algorithm receives only the input file. The output file is one working reference path, not the only accepted answer. All 39 paths pass the replay checker.

```bash
python checker.py --all
python checker.py --input testcases/original/01.in.json --output answer.json
```

An accepted answer reaches the goal without losing. It may be longer than the reference. Report length comparisons separately from AC/WA. An `unsolvable` claim is WA for every supplied stage.

## Samples

| File number | Stage ID | Feature | Reference actions | Length |
|---|---|---|---|---:|
| 01 | sample01 | Basic rolling | R R | 2 |
| 02 | sample02 | Rolling sideways and turning | R D D D R | 5 |
| 03 | sample03 | Fragile tiles while lying | R R | 2 |
| 04 | sample04 | Soft switch toggles a bridge | R R R R | 4 |
| 05 | sample05 | Upright block presses a heavy switch | R R R R | 4 |
| 06 | sample06 | Teleport, select cube, merge | R R 1R R | 4 |

Every sample has multiple board rows. Sample 01 is distinct from original stage 1. The earlier unsolvable examples were removed from the supplied suite.

## Original-stage reference lengths

| Stages | Directional moves, in stage order |
|---|---|
| 01–10 | 7, 17, 19, 28, 33, 35, 44, 10, 24, 57 |
| 11–20 | 47, 65, 46, 67, 57, 28, 106, 85, 67, 56 |
| 21–30 | 71, 65, 75, 57, 55, 104, 71, 100, 104, 114 |
| 31–33 | 91, 129, 65 |

Total: 1,999 moves. These are published minimum-length claims except for the independently checked stage-15 replacement. All supplied paths are verified solutions, but replay does not prove minimum length for the other original stages.

## Stage 15

The original reference path turns off a bridge under a parked cube at move 27. It was replaced by a different valid 57-move path. See [the source notes](../docs/stage-sources.md) for the exact finding and provenance.

## Coverage and limits

The original set includes fragile tiles, soft and heavy switches, active and inactive bridges, toggle/on/off operations, splitters, and rejoining. The checker regression tests also cover losing paths, unknown actions, longer valid paths, small cubes on fragile/goal tiles, shared switch targets, and a bridge losing support under a stationary cube.

This suite is known solvable because each input has a replay-verified witness. The current checker does not decide solvability of an arbitrary new map.

## Sources

Stage data and published reference solutions: [tkoz0/bloxorz-solver](https://github.com/tkoz0/bloxorz-solver), commit d203a25170085054fb3f39bd81b3509ee8cd9e47. Original game: Damien Clarke. No license was stated in the inspected reference revision. See [source notes](../docs/stage-sources.md) and the manifest before publishing.
