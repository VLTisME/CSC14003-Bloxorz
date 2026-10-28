"""Benchmark Modal Window for comparing all 4 search algorithms on a chosen stage."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import threading
from typing import Any, Callable
from ursina import (
    Entity,
    Text,
    Vec2,
    Vec3,
    camera,
    color,
    destroy,
)

from game.stage_catalog import StageCatalog
from game.ursina_ui.assets.theme import (
    DEFAULT_FONT_NAME,
    PALETTE,
)
from game.ursina_ui.pixel_widgets import (
    PixelButton,
    PixelPanel,
)

# Ensure algorithms directory is importable
ROOT_DIR = Path(__file__).resolve().parents[3]
ALGO_DIR = ROOT_DIR / "algorithms"
if str(ALGO_DIR) not in sys.path:
    sys.path.insert(0, str(ALGO_DIR))


class BenchmarkModal(PixelPanel):
    """Interactive benchmark window showing step-by-step metrics for A*, BFS, UCS, and DFS."""

    def __init__(
        self,
        catalog: StageCatalog,
        current_stage_id: str = "stage01",
        on_close: Callable[[], None] | None = None,
        on_load_solution: Callable[[list[str]], None] | None = None,
        parent: Entity | None = None,
        **kwargs: Any,
    ) -> None:
        self.catalog = catalog
        self.stage_id = current_stage_id
        self.on_load_solution = on_load_solution
        self._worker_thread: threading.Thread | None = None
        self._is_benchmarking = False
        self._results: dict[str, dict[str, Any]] = {}
        self._rows: dict[str, dict[str, Any]] = {}

        # Build stages list for navigation
        self.all_stage_ids = [s["id"] for s in catalog.original_stages] + [s["id"] for s in catalog.sample_stages]
        if self.stage_id not in self.all_stage_ids and self.all_stage_ids:
            self.stage_id = self.all_stage_ids[0]

        super().__init__(
            scale=(1.22, 0.78),
            position=(0, 0, -18),
            title="ALGORITHM BENCHMARK",
            subtitle="Performance comparison across all 4 search algorithms",
            close_button=True,
            on_close=on_close,
            parent=parent,
            **kwargs,
        )

        # 1. Top Controls Bar: Stage Selector & Run Button
        ctrl_y = 0.235
        self.btn_prev_stage = PixelButton(
            parent=self,
            text="< Prev",
            color_ramp="orange",
            scale=(0.10, 0.052),
            position=(-0.36, ctrl_y, -0.02),
            on_click=self._prev_stage,
        )

        self.txt_stage_display = Text(
            parent=self,
            text=f"Stage: {self.stage_id.upper()}",
            font=DEFAULT_FONT_NAME,
            scale=1.1,
            origin=(0, 0),
            position=(-0.16, ctrl_y, -0.02),
            color=color.hex(PALETTE["ink"]),
        )

        self.btn_next_stage = PixelButton(
            parent=self,
            text="Next >",
            color_ramp="orange",
            scale=(0.10, 0.052),
            position=(0.04, ctrl_y, -0.02),
            on_click=self._next_stage,
        )

        self.btn_run = PixelButton(
            parent=self,
            text="Run Benchmark",
            color_ramp="green",
            scale=(0.19, 0.052),
            position=(0.28, ctrl_y, -0.02),
            on_click=self.start_benchmark,
        )

        # 2. Table Column Headers
        head_y = 0.155
        headers = [
            ("ALGORITHM", -0.48, -0.5),
            ("STATUS", -0.16, 0),
            ("MOVES", -0.01, 0),
            ("NODES", 0.15, 0),
            ("TIME", 0.31, 0),
            ("ACTION", 0.46, 0),
        ]
        for title, hx, orig_x in headers:
            Text(
                parent=self,
                text=title,
                font=DEFAULT_FONT_NAME,
                scale=0.92,
                origin=(orig_x, 0),
                position=(hx, head_y, -0.02),
                color=color.hex(PALETTE["brick"]),
            )

        # Separator line
        self.sep_line = Entity(
            parent=self,
            model="quad",
            scale=(1.04, 0.003),
            position=(0, 0.125, -0.02),
            color=color.hex(PALETTE["tan"]),
        )

        # 3. Algorithm Rows
        algo_list = [
            ("A*", "A* (Heuristic)", "Manhattan dist"),
            ("BFS", "BFS (Breadth)", "Shortest path"),
            ("UCS", "UCS (Cost)", "Dijkstra optimal"),
            ("DFS", "DFS (Depth)", "Deep branch search"),
        ]

        row_start_y = 0.065
        row_dy = 0.095
        for i, (key, display_name, note) in enumerate(algo_list):
            ry = row_start_y - i * row_dy

            # Row background card
            bg = Entity(
                parent=self,
                model="quad",
                scale=(1.05, 0.082),
                position=(0, ry, -0.01),
                color=color.rgba(0.95, 0.94, 0.90, 0.5) if i % 2 == 0 else color.rgba(0.90, 0.88, 0.82, 0.5),
            )

            # Algorithm Name + Subtitle
            t_name = Text(
                parent=self,
                text=f"{display_name}\n({note})",
                font=DEFAULT_FONT_NAME,
                scale=0.80,
                origin=(-0.5, 0),
                position=(-0.49, ry, -0.02),
                color=color.hex(PALETTE["ink"]),
            )

            # Status
            t_status = Text(
                parent=self,
                text="READY",
                font=DEFAULT_FONT_NAME,
                scale=0.88,
                origin=(0, 0),
                position=(-0.16, ry, -0.02),
                color=color.hex(PALETTE["slate"]),
            )

            # Moves count
            t_moves = Text(
                parent=self,
                text="--",
                font=DEFAULT_FONT_NAME,
                scale=0.88,
                origin=(0, 0),
                position=(-0.01, ry, -0.02),
                color=color.hex(PALETTE["ink"]),
            )

            # Explored nodes
            t_nodes = Text(
                parent=self,
                text="--",
                font=DEFAULT_FONT_NAME,
                scale=0.88,
                origin=(0, 0),
                position=(0.15, ry, -0.02),
                color=color.hex(PALETTE["ink"]),
            )

            # Execution time
            t_time = Text(
                parent=self,
                text="--",
                font=DEFAULT_FONT_NAME,
                scale=0.88,
                origin=(0, 0),
                position=(0.31, ry, -0.02),
                color=color.hex(PALETTE["ink"]),
            )

            # Load solution button
            btn_load = PixelButton(
                parent=self,
                text="Replay",
                color_ramp="orange",
                scale=(0.10, 0.052),
                position=(0.46, ry, -0.02),
                disabled=True,
                on_click=lambda a=key: self._on_replay_solution(a),
            )

            self._rows[key] = {
                "status": t_status,
                "moves": t_moves,
                "nodes": t_nodes,
                "time": t_time,
                "btn_load": btn_load,
            }

        # 4. Bottom note
        self.txt_note = Text(
            parent=self,
            text="* A*, BFS, and UCS guarantee optimal solutions. DFS explores deep branches first.",
            font=DEFAULT_FONT_NAME,
            scale=0.76,
            origin=(0, 0),
            position=(0, -0.32, -0.02),
            color=color.hex(PALETTE["brick"]),
        )

        self._benchmark_gen = 0

        # Automatically kick off benchmark for current stage if not headless
        from ursina import application
        if not getattr(application, "headless", False):
            self.start_benchmark()

    def _prev_stage(self) -> None:
        """Switch to previous stage in catalog."""
        if not self.all_stage_ids:
            return
        idx = self.all_stage_ids.index(self.stage_id) if self.stage_id in self.all_stage_ids else 0
        self.stage_id = self.all_stage_ids[(idx - 1) % len(self.all_stage_ids)]
        self.txt_stage_display.text = f"Stage: {self.stage_id.upper()}"
        self.start_benchmark()

    def _next_stage(self) -> None:
        """Switch to next stage in catalog."""
        if not self.all_stage_ids:
            return
        idx = self.all_stage_ids.index(self.stage_id) if self.stage_id in self.all_stage_ids else 0
        self.stage_id = self.all_stage_ids[(idx + 1) % len(self.all_stage_ids)]
        self.txt_stage_display.text = f"Stage: {self.stage_id.upper()}"
        self.start_benchmark()

    def start_benchmark(self) -> None:
        """Run all 4 solvers in a background thread."""
        self._benchmark_gen += 1
        gen = self._benchmark_gen
        self._is_benchmarking = True
        self.btn_run.text = "Running..."
        self.btn_run.disabled = True

        for key, row in self._rows.items():
            row["status"].text = "QUEUED"
            row["status"].color = color.hex(PALETTE["slate"])
            row["moves"].text = "--"
            row["nodes"].text = "--"
            row["time"].text = "--"
            row["btn_load"].disabled = True

        # Fetch stage data
        stage_meta = self.catalog.stage_by_id.get(self.stage_id)
        if not stage_meta or not stage_meta.get("input_path") or not stage_meta["input_path"].exists():
            for key, row in self._rows.items():
                row["status"].text = "NO DATA"
                row["status"].color = color.hex(PALETTE["red"])
            self._is_benchmarking = False
            self.btn_run.text = "Run Benchmark"
            self.btn_run.disabled = False
            return

        stage_path = stage_meta["input_path"]
        stage_data = json.loads(stage_path.read_text(encoding="utf-8"))

        def _worker() -> None:
            if gen != self._benchmark_gen:
                return
            try:
                from solver_support import SearchMetrics
                from BFS import solve as bfs_solve
                from DFS import solve as dfs_solve
                from UCS import solve as ucs_solve
                from ASTAR import solve_with_breakdown as astar_solve
            except Exception as e:
                print(f"[BENCHMARK] Error importing solvers: {e}")
                self._is_benchmarking = False
                return

            solvers = [
                ("A*", astar_solve),
                ("BFS", bfs_solve),
                ("UCS", ucs_solve),
                ("DFS", dfs_solve),
            ]

            for key, fn in solvers:
                if not self.enabled:
                    break
                row = self._rows.get(key)
                if row:
                    row["status"].text = "RUNNING..."
                    row["status"].color = color.hex(PALETTE["tan"])

                m = SearchMetrics(track_memory=False)
                try:
                    with m:
                        if key == "A*":
                            actions, _ = fn(stage_data, m)
                        else:
                            actions = fn(stage_data, m)

                    d = m.as_dict()
                    self._results[key] = {
                        "status": "SOLVED" if actions else "NO_SOLUTION",
                        "steps": len(actions),
                        "nodes": d.get("expanded_nodes", 0),
                        "time_ms": round(d.get("search_time_ms", 0), 2),
                        "actions": actions,
                    }
                except Exception as e:
                    self._results[key] = {
                        "status": "TIMEOUT" if "timeout" in str(e).lower() else "ERROR",
                        "steps": 0,
                        "nodes": 0,
                        "time_ms": 0,
                        "actions": [],
                    }

                # Update UI row
                res = self._results[key]
                if row:
                    st = res["status"]
                    row["status"].text = st
                    if st == "SOLVED":
                        row["status"].color = color.hex(PALETTE["green"])
                        row["moves"].text = f"{res['steps']}"
                        row["nodes"].text = f"{res['nodes']:,}"
                        row["time"].text = f"{res['time_ms']} ms"
                        row["btn_load"].disabled = False
                    else:
                        row["status"].color = color.hex(PALETTE["red"])
                        row["moves"].text = "--"
                        row["nodes"].text = "--"
                        row["time"].text = "--"
                        row["btn_load"].disabled = True

            self._is_benchmarking = False
            self.btn_run.text = "Run Benchmark"
            self.btn_run.disabled = False

        self._worker_thread = threading.Thread(target=_worker, daemon=True)
        self._worker_thread.start()

    def _on_replay_solution(self, algo: str) -> None:
        """Load the chosen algorithm's solution into Replay and close benchmark modal."""
        res = self._results.get(algo)
        if res and res.get("actions") and self.on_load_solution:
            self.on_load_solution(res["actions"])
            self.close()
