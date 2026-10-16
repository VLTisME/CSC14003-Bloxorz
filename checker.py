"""Replay-based Bloxorz checker. No search algorithm is used to judge a path."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--all", action="store_true", help="replay every supplied reference output")
    args = parser.parse_args()
    if args.all:
        if args.input or args.output:
            parser.error("use --all alone, or --input and --output together")
        root = Path(__file__).resolve().parent / "testcases"
        pairs = [(p, p.with_name(p.name.replace(".in.json", ".out.json"))) for p in sorted(root.glob("*/*.in.json"))]
    else:
        if not args.input or not args.output:
            parser.error("provide both --input and --output, or use --all")
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
