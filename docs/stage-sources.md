# Stage sources and verification

Prepared 15 October 2026.

## Dataset used

The 33 original stages are adapted from the user-supplied [tkoz0/bloxorz-solver repository](https://github.com/tkoz0/bloxorz-solver) at commit **d203a25170085054fb3f39bd81b3509ee8cd9e47**.

- [coolmath.json](https://github.com/tkoz0/bloxorz-solver/blob/d203a25170085054fb3f39bd81b3509ee8cd9e47/coolmath.json): layouts, start/goal, bridge groups, switch effects, teleport destinations.
- [solution.txt](https://github.com/tkoz0/bloxorz-solver/blob/d203a25170085054fb3f39bd81b3509ee8cd9e47/solution.txt): published reference key sequences and claimed minimum lengths.
- [solver.py](https://github.com/tkoz0/bloxorz-solver/blob/d203a25170085054fb3f39bd81b3509ee8cd9e47/solver.py): consulted to understand source coordinates, selected-cube state, and encoding. Its search implementation was not copied into the project.
- Original game: Damien Clarke; [Coolmath instructions](https://www.coolmathgames.com/0-bloxorz).

Downloaded bytes were checked against the Git blob IDs for the pinned revision. The [manifest](../testcases/manifest.json) records file hashes, individual stage paths, passcodes, features, reference lengths, and verification status.

## Conversion

The source already uses row/column coordinates. We retain them and convert:

| Source | Project |
|---|---|
| space | `#` void |
| `.` | `.` floor |
| `-` | `F` fragile |
| `H` | `G` goal |
| `b` / `B` | `B`, with initial state stored in the bridge definition |
| `S`, `O`, `X`, `T` | unchanged |
| `swap` bridge effect | `toggle` |

Source teleports also identify the initially selected cube. That information is used to translate the published key sequences. Project actions name cube 1 or cube 2 directly, so no selection field is needed in the input.

An underscore in an upstream solution is a free cube-selection change. It is removed from the action count and translated into the appropriate `1U`/`2U`, etc. IDs stay attached to their cube until merging.

## What has been verified

All **33 original stages and six project examples** have reference paths that replay successfully under problem-statement v1.0. This establishes that every supplied input is solvable. No expected output is `unsolvable`.

The checker validates paths, not shortest-path claims. For 32 original stages, reference lengths are the upstream author's published minimum claims; replay alone does not prove optimality. Stage 15's replacement was found by exhaustive breadth-first search under our rules, independently confirming its 57-move minimum. The six small examples are hand-checkable and their earlier lengths were checked exhaustively.

The original-stage reference lengths sum to **1,999 directional moves**. Cube selection and automatic effects add no moves.

## Stage 15 correction

The published stage-15 path fails at directional move **27**, translated as `2D`. Cube 1 is on bridge cell (1,10); cube 2 lands on the soft switch at (3,8), turning that bridge off. Our required post-effect support check therefore loses the stage.

The reference solver checks support before switch effects but does not perform that same post-effect check. This explains why its path is accepted there.

A new path was generated and replayed under the project rules. It also takes **57 moves** and is stored in original/15.out.json. The manifest marks this output as a project-generated replacement and retains the original failure details. This is a statement about our selected rules, not proof of every version of the original game's frame-by-frame behaviour.

## Other research resolved

The earlier GBA-port and Frank-Buss data differed in stage 3's layout. The final set consistently uses the user-supplied tkoz0 encoding and its replay-verified path; it does not silently mix layouts from different ports.

Small cubes are allowed on fragile and goal tiles. They do not win on the goal. Some teleport destinations are `X` or `T` (notably stage 16); a small cube does not activate these, so there is no chain of splits or heavy-switch presses.

## Attribution and license status

The inspected tkoz0 revision has four files and no LICENSE file or explicit license declaration in its README. Public availability and attribution are not a stated redistribution license. Record this fact before publishing the adapted dataset; do not label the data MIT, GPL, public domain, or unrestricted.

Credit tkoz0 for stage encodings and reference solutions and Damien Clarke for Bloxorz. This credit is already present in the repository and should also appear in the Prism report. Preserve any additional notices supplied by the source owner.

The project owner's docs/assets/Bloxorz.gif is used as a movement illustration. Its original creator and redistribution terms were not provided. The six samples and checker were authored for this project.

## Future generated stages

The current checker performs basic structure checks and deterministic replay. If the project later creates arbitrary stages, add dedicated generation/input validation and a trusted solvability-certification process. Where a shortest answer is required, also produce or verify an optimal-length certificate. Do not infer that generated stages are solvable merely because they load or render. Record this scope in the report's future-work section.
