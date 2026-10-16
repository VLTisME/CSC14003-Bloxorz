"""Shared measurements and JSON output; no search or game logic."""
from __future__ import annotations

import json
import math
from time import perf_counter_ns
import tracemalloc


def metrics_issues(metrics: object) -> list[str]:
    """Validate completeness for benchmarks, independently of game verdicts."""
    if not isinstance(metrics, dict):
        return ["metrics must be an object"]
    issues = []
    elapsed = metrics.get("search_time_ms")
    if (type(elapsed) not in (int, float) or elapsed < 0
            or (isinstance(elapsed, float) and not math.isfinite(elapsed))):
        issues.append("search_time_ms must be a finite nonnegative number")
    for key in ("expanded_nodes", "peak_memory_bytes"):
        value = metrics.get(key)
        if type(value) is not int or value < 0:
            issues.append(f"{key} must be a nonnegative integer")
    if metrics.get("memory_method") != "tracemalloc":
        issues.append("memory_method must be tracemalloc for the agreed baseline")
    return issues


class SearchMetrics:
    """Measure one solve, including all IDS iterations; do not nest or reuse.

    Parse input before entering. Build search structures and reconstruct the
    path inside. Print after exiting. Default timing includes tracing overhead.
    track_memory=False allows separate timing-only runs with null memory fields.
    Memory measures Python allocations since entry, not RSS or parsed input.
    """

    def __init__(self, *, track_memory: bool = True):
        if type(track_memory) is not bool:
            raise TypeError("track_memory must be a boolean")
        self._track_memory = track_memory
        self._state = "new"
        self._expanded_nodes = 0
        self._elapsed_ms = None
        self._peak_bytes = None

    def __enter__(self) -> SearchMetrics:
        if self._state != "new":
            raise RuntimeError("use a new SearchMetrics for each solve")
        if tracemalloc.is_tracing():
            raise RuntimeError("SearchMetrics requires no pre-existing memory tracing")
        if self._track_memory:
            tracemalloc.start()
        try:
            self._start_ns = perf_counter_ns()
        except BaseException:
            if self._track_memory:
                tracemalloc.stop()
            raise
        self._state = "running"
        return self

    def expanded(self) -> None:
        """Count one non-goal expansion immediately before generating successors."""
        if self._state != "running":
            raise RuntimeError("count expansions only inside the measurement context")
        self._expanded_nodes += 1

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self._state = "failed"
        try:
            self._elapsed_ms = (perf_counter_ns() - self._start_ns) / 1_000_000
            if self._track_memory:
                if not tracemalloc.is_tracing():
                    raise RuntimeError("do not stop memory tracing inside the search")
                self._peak_bytes = tracemalloc.get_traced_memory()[1]
            if exc_type is None:
                self._state = "finished"
        finally:
            if self._track_memory:
                tracemalloc.stop()
        return False  # Propagate errors; never print a fake successful solution.

    def as_dict(self) -> dict:
        if self._state != "finished":
            raise RuntimeError("metrics require a successfully completed measurement context")
        return {
            "search_time_ms": self._elapsed_ms,
            "expanded_nodes": self._expanded_nodes,
            "peak_memory_bytes": self._peak_bytes,
            "memory_method": "tracemalloc" if self._track_memory else None,
        }

    def print_solution(self, actions: list[str]) -> None:
        """Print one JSON object. Token validation does not replace path replay."""
        allowed = {p + d for p in ("", "1", "2") for d in "UDLR"}
        if not isinstance(actions, list) or any(
            not isinstance(a, str) or a not in allowed for a in actions
        ):
            raise ValueError("actions must be a list of recognized action strings")
        result = {"status": "solved", "actions": actions, "metrics": self.as_dict()}
        print(json.dumps(result, allow_nan=False))
