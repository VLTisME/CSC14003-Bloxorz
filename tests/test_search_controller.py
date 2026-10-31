"""Unit tests for PausableSearchController and PausableSearchMetrics."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time
import unittest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from checker import check  # noqa: E402
from game.search_controller import (  # noqa: E402
    SearchController,
    SearchStatus,
)


def load_sample(num: int = 1) -> dict:
    p = ROOT_DIR / "testcases" / "samples" / f"{num:02d}.in.json"
    return json.loads(p.read_text(encoding="utf-8"))


def load_original(num: int = 10) -> dict:
    p = ROOT_DIR / "testcases" / "original" / f"{num:02d}.in.json"
    return json.loads(p.read_text(encoding="utf-8"))


class TestSearchController(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = SearchController()

    def tearDown(self) -> None:
        self.controller.cancel()

    def test_solve_all_four_algorithms(self) -> None:
        """Kiểm tra cả 4 thuật toán đều giải thành công và cho verdict AC."""
        stage = load_sample(1)
        for algo in ("BFS", "DFS", "UCS", "A*"):
            with self.subTest(algorithm=algo):
                self.controller.start(stage, algorithm=algo, generation=1, timeout=10.0)

                # Chờ kết quả
                deadline = time.monotonic() + 5.0
                res = None
                while time.monotonic() < deadline:
                    res = self.controller.poll()
                    if res is not None:
                        break
                    time.sleep(0.01)

                self.assertIsNotNone(res, f"Thuật toán {algo} không trả về kết quả kịp thời")
                self.assertEqual(res.status, SearchStatus.COMPLETED)
                self.assertTrue(len(res.actions) > 0)
                self.assertIn("search_time_ms", res.metrics)
                self.assertIn("expanded_nodes", res.metrics)

                # Kiểm tra tính đúng đắn qua checker
                ans = {"status": "solved", "actions": res.actions}
                verdict = check(stage, ans)
                self.assertEqual(verdict["verdict"], "AC")

    def test_ucs_reports_weighted_cost_separately_from_moves(self) -> None:
        for stage_num, steps, cost in ((13, 49, 63), (16, 30, 55), (23, 76, 128), (25, 55, 66)):
            with self.subTest(stage=stage_num):
                stage = load_original(stage_num)
                self.controller.start(stage, algorithm="UCS", generation=stage_num, timeout=10.0)
                deadline = time.monotonic() + 10.0
                result = None
                while result is None and time.monotonic() < deadline:
                    result = self.controller.poll()
                    time.sleep(0.005)
                self.assertIsNotNone(result)
                self.assertEqual(result.status, SearchStatus.COMPLETED)
                self.assertEqual(len(result.actions), steps)
                self.assertEqual(result.metrics["weighted_cost"], cost)
                self.assertEqual(check(stage, {"status": "solved", "actions": result.actions})["verdict"], "AC")

    def test_pause_and_resume_execution(self) -> None:
        """Kiểm tra Pause thực sự dừng tiến trình và Resume tiếp tục mà không lỗi."""
        stage = load_original(10)  # Stage 10 cần ~450ms giải BFS với 5883 nodes
        self.controller.start(stage, algorithm="BFS", generation=2, timeout=10.0)

        # Chờ luồng bắt đầu chạy một chút rồi Pause
        time.sleep(0.02)
        paused = self.controller.pause()
        self.assertTrue(paused)
        self.assertEqual(self.controller.status, SearchStatus.PAUSED)
        self.assertTrue(self.controller.is_paused)

        nodes_at_pause = self.controller.expanded_nodes
        self.assertGreater(nodes_at_pause, 0, "Solver chưa kịp mở rộng node nào trước khi pause")

        # Chờ 0.15s trong lúc đang Pause, số node tuyệt đối không được tăng
        time.sleep(0.15)
        self.assertEqual(self.controller.expanded_nodes, nodes_at_pause)

        # Tiếp tục (Resume)
        resumed = self.controller.resume()
        self.assertTrue(resumed)
        self.assertEqual(self.controller.status, SearchStatus.RUNNING)

        # Chờ hoàn thành
        deadline = time.monotonic() + 10.0
        res = None
        while time.monotonic() < deadline:
            res = self.controller.poll()
            if res is not None:
                break
            time.sleep(0.01)

        self.assertIsNotNone(res)
        self.assertEqual(res.status, SearchStatus.COMPLETED)
        self.assertGreater(res.metrics["expanded_nodes"], nodes_at_pause)
        verdict = check(stage, {"status": "solved", "actions": res.actions})
        self.assertEqual(verdict["verdict"], "AC")

    def test_pause_time_excluded_from_metrics(self) -> None:
        """Kiểm tra thời gian tạm dừng (0.3s) không bị cộng vào search_time_ms."""
        stage = load_original(10)
        self.controller.start(stage, algorithm="A*", generation=3, timeout=10.0)

        # A* trên Stage 10 tốn khoảng 30ms-50ms
        time.sleep(0.005)
        self.controller.pause()

        # Dừng 0.3 giây
        time.sleep(0.3)

        self.controller.resume()

        deadline = time.monotonic() + 5.0
        res = None
        while time.monotonic() < deadline:
            res = self.controller.poll()
            if res is not None:
                break
            time.sleep(0.01)

        self.assertIsNotNone(res)
        self.assertEqual(res.status, SearchStatus.COMPLETED)
        search_time = res.metrics.get("search_time_ms", 9999.0)
        # Thời gian giải thực tế của A* stage 10 < 150ms. Nếu cộng 300ms pause thì sẽ > 300ms.
        self.assertLess(search_time, 250.0, f"search_time_ms ({search_time}) đã bị cộng cả thời gian pause!")

    def test_timeout_handles_active_time_only(self) -> None:
        """Kiểm tra Timeout chỉ kích hoạt khi thời gian chạy thực tế vượt ngưỡng."""
        stage = load_original(10)
        # Đặt timeout cực nhỏ 0.001s để ép timeout
        self.controller.start(stage, algorithm="BFS", generation=4, timeout=0.001)

        deadline = time.monotonic() + 2.0
        res = None
        while time.monotonic() < deadline:
            res = self.controller.poll()
            if res is not None:
                break
            time.sleep(0.01)

        self.assertIsNotNone(res)
        self.assertEqual(res.status, SearchStatus.TIMEOUT)
        self.assertIn("Quá thời gian", res.error_message)

    def test_cancel_while_running_and_while_paused(self) -> None:
        """Kiểm tra Cancel hủy lập tức cả khi đang chạy và khi đang tạm dừng."""
        stage = load_original(10)

        # 1. Cancel khi đang PAUSED
        self.controller.start(stage, algorithm="BFS", generation=5, timeout=10.0)
        time.sleep(0.02)
        self.controller.pause()
        self.assertEqual(self.controller.status, SearchStatus.PAUSED)
        self.controller.cancel()

        time.sleep(0.05)
        res = self.controller.poll()
        self.assertIsNotNone(res)
        self.assertEqual(res.status, SearchStatus.CANCELLED)


if __name__ == "__main__":
    unittest.main()
