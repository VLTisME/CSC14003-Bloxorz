"""Pausable background search controller for Bloxorz solvers.

Supports true pausing, resuming, cancelling, and active-time measurement
for BFS, DFS, UCS, and A* solvers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
import queue
import sys
import threading
from time import perf_counter_ns
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
ALGORITHMS_DIR = ROOT_DIR / "algorithms"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(ALGORITHMS_DIR) not in sys.path:
    sys.path.insert(0, str(ALGORITHMS_DIR))

from solver_support import SearchMetrics  # noqa: E402


class SearchCancelledError(Exception):
    """Raised when search execution is cancelled early by the user."""


class SearchTimeoutError(Exception):
    """Raised when active search duration exceeds the allotted timeout."""


class SearchStatus(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


@dataclass
class SearchTaskResult:
    generation: int
    status: SearchStatus
    algorithm: str
    actions: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    error_message: str = ""


class PausableSearchMetrics(SearchMetrics):
    """SearchMetrics subclass supporting cooperative pause, resume, cancel, and timeout.

    Excludes all paused duration from search_time_ms and timeout calculations.
    """

    def __init__(
        self,
        *,
        pause_event: threading.Event,
        cancel_event: threading.Event,
        timeout_sec: float | None = None,
        track_memory: bool = False,
    ):
        super().__init__(track_memory=track_memory)
        self._pause_event = pause_event
        self._cancel_event = cancel_event
        self._timeout_sec = timeout_sec
        self._total_paused_ns: int = 0
        self._is_currently_paused: bool = False

    def expanded(self) -> None:
        """Cooperative checkpoint called on every node expansion."""
        # 1. Kiểm tra yêu cầu hủy bỏ (Reset / Đổi màn)
        if self._cancel_event.is_set():
            raise SearchCancelledError("Tìm kiếm đã bị hủy.")

        # 2. Kiểm tra yêu cầu tạm dừng (Pause)
        if not self._pause_event.is_set():
            self._is_currently_paused = True
            t0 = perf_counter_ns()
            self._pause_event.wait()
            self._is_currently_paused = False
            self._total_paused_ns += (perf_counter_ns() - t0)

            # Kiểm tra lại xem có bị hủy trong lúc đang Pause không
            if self._cancel_event.is_set():
                raise SearchCancelledError("Tìm kiếm đã bị hủy trong lúc tạm dừng.")

        # 3. Kiểm tra Timeout (Chỉ tính thời gian chạy thực tế)
        if self._timeout_sec is not None:
            active_ns = (perf_counter_ns() - self._start_ns) - self._total_paused_ns
            if active_ns >= self._timeout_sec * 1_000_000_000:
                raise SearchTimeoutError(
                    f"Quá thời gian tìm kiếm ({self._timeout_sec:.1f}s) sau {self._expanded_nodes} node."
                )

        # 4. Ghi nhận số node đã duyệt vào SearchMetrics
        super().expanded()

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        try:
            active_ns = (perf_counter_ns() - self._start_ns) - self._total_paused_ns
            self._elapsed_ms = max(0.0, active_ns / 1_000_000)
            if self._track_memory:
                import tracemalloc

                if tracemalloc.is_tracing():
                    self._peak_bytes = tracemalloc.get_traced_memory()[1]
            if exc_type is None:
                self._state = "finished"
            else:
                self._state = "failed"
        finally:
            if self._track_memory:
                import tracemalloc

                if tracemalloc.is_tracing():
                    tracemalloc.stop()
        return False

    @property
    def total_paused_ms(self) -> float:
        return self._total_paused_ns / 1_000_000

    @property
    def active_search_time_ms(self) -> float:
        if self._state == "new":
            return 0.0
        if self._elapsed_ms is not None:
            return self._elapsed_ms
        active_ns = (perf_counter_ns() - self._start_ns) - self._total_paused_ns
        return max(0.0, active_ns / 1_000_000)


class SearchController:
    """Manages off-thread pausable solver runs for Ursina GUI."""

    def __init__(self) -> None:
        self._status: SearchStatus = SearchStatus.IDLE
        self._current_algorithm: str = "A*"
        self._current_generation: int = 0
        self._pause_event = threading.Event()
        self._pause_event.set()  # Mặc định ở trạng thái không pause (unpaused)
        self._cancel_event = threading.Event()
        self._worker_thread: threading.Thread | None = None
        self._active_metrics: PausableSearchMetrics | None = None
        self._results_queue: queue.Queue[SearchTaskResult] = queue.Queue()
        self._lock = threading.RLock()

    @property
    def status(self) -> SearchStatus:
        return self._status

    @property
    def is_running(self) -> bool:
        return self._status in (SearchStatus.RUNNING, SearchStatus.PAUSED)

    @property
    def is_paused(self) -> bool:
        return self._status == SearchStatus.PAUSED

    @property
    def current_algorithm(self) -> str:
        return self._current_algorithm

    @property
    def current_generation(self) -> int:
        return self._current_generation

    @property
    def active_time_ms(self) -> float:
        if self._active_metrics is not None:
            return self._active_metrics.active_search_time_ms
        return 0.0

    @property
    def expanded_nodes(self) -> int:
        if self._active_metrics is not None:
            return self._active_metrics._expanded_nodes
        return 0

    def start(
        self,
        stage: dict,
        algorithm: str = "A*",
        generation: int = 0,
        timeout: float = 30.0,
    ) -> None:
        """Bắt đầu chạy solver trong luồng nền."""
        with self._lock:
            # Hủy tiến trình trước đó nếu có
            self.cancel()

            self._current_algorithm = algorithm
            self._current_generation = generation
            self._cancel_event.clear()
            self._pause_event.set()
            self._status = SearchStatus.RUNNING

            stage_copy = json.loads(json.dumps(stage))

            def _run() -> None:
                metrics = PausableSearchMetrics(
                    pause_event=self._pause_event,
                    cancel_event=self._cancel_event,
                    timeout_sec=timeout,
                    track_memory=False,
                )
                self._active_metrics = metrics

                algo = algorithm.upper().strip()
                result_actions: list[str] = []
                extra_details: dict[str, Any] = {}

                try:
                    with metrics:
                        if algo == "BFS":
                            from BFS import solve as bfs_solve

                            result_actions = bfs_solve(stage_copy, metrics)
                        elif algo == "DFS":
                            from DFS import solve as dfs_solve

                            result_actions = dfs_solve(stage_copy, metrics)
                        elif algo == "UCS":
                            from UCS import solve as ucs_solve

                            result_actions = ucs_solve(stage_copy, metrics)
                        elif algo in ("A*", "ASTAR"):
                            from ASTAR import solve_with_breakdown as astar_solve

                            result_actions, extra_details = astar_solve(stage_copy, metrics)
                        else:
                            raise ValueError(f"Thuật toán không hỗ trợ: {algorithm}")

                    output_metrics = metrics.as_dict()
                    output_metrics.update(extra_details)

                    with self._lock:
                        if not self._cancel_event.is_set():
                            self._status = SearchStatus.COMPLETED
                            self._results_queue.put(
                                SearchTaskResult(
                                    generation=generation,
                                    status=SearchStatus.COMPLETED,
                                    algorithm=algorithm,
                                    actions=result_actions,
                                    metrics=output_metrics,
                                )
                            )

                except SearchCancelledError:
                    with self._lock:
                        self._status = SearchStatus.CANCELLED
                        self._results_queue.put(
                            SearchTaskResult(
                                generation=generation,
                                status=SearchStatus.CANCELLED,
                                algorithm=algorithm,
                                error_message="Tìm kiếm đã bị hủy.",
                            )
                        )

                except SearchTimeoutError as exc:
                    with self._lock:
                        self._status = SearchStatus.TIMEOUT
                        self._results_queue.put(
                            SearchTaskResult(
                                generation=generation,
                                status=SearchStatus.TIMEOUT,
                                algorithm=algorithm,
                                error_message=str(exc),
                            )
                        )

                except Exception as exc:
                    with self._lock:
                        self._status = SearchStatus.FAILED
                        self._results_queue.put(
                            SearchTaskResult(
                                generation=generation,
                                status=SearchStatus.FAILED,
                                algorithm=algorithm,
                                error_message=f"{type(exc).__name__}: {exc}",
                            )
                        )

            self._worker_thread = threading.Thread(
                target=_run,
                name=f"bloxorz-solver-{algorithm.lower()}",
                daemon=True,
            )
            self._worker_thread.start()

    def pause(self) -> bool:
        """Tạm dừng solver nếu đang chạy."""
        with self._lock:
            if self._status == SearchStatus.RUNNING:
                self._pause_event.clear()
                self._status = SearchStatus.PAUSED
                return True
            return False

    def resume(self) -> bool:
        """Tiếp tục solver nếu đang tạm dừng."""
        with self._lock:
            if self._status == SearchStatus.PAUSED:
                self._pause_event.set()
                self._status = SearchStatus.RUNNING
                return True
            return False

    def toggle_pause(self) -> SearchStatus:
        """Chuyển đổi qua lại giữa RUNNING và PAUSED."""
        with self._lock:
            if self._status == SearchStatus.RUNNING:
                self._pause_event.clear()
                self._status = SearchStatus.PAUSED
            elif self._status == SearchStatus.PAUSED:
                self._pause_event.set()
                self._status = SearchStatus.RUNNING
            return self._status

    def cancel(self) -> None:
        """Hủy bỏ lượt tìm kiếm hiện tại."""
        with self._lock:
            self._cancel_event.set()
            self._pause_event.set()  # Đánh thức nếu đang bị block bởi pause
            if self._status in (SearchStatus.RUNNING, SearchStatus.PAUSED):
                self._status = SearchStatus.CANCELLED

    def poll(self) -> SearchTaskResult | None:
        """Lấy kết quả từ hàng đợi (Non-blocking)."""
        try:
            return self._results_queue.get_nowait()
        except queue.Empty:
            return None
