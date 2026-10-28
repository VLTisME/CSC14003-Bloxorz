"""Unit tests for Solver Pause/Resume, Reset, and Stage Switch interactions in GUI."""
from __future__ import annotations

import builtins
import time
import unittest
from ursina import Ursina

from game.search_controller import SearchStatus
from game.ursina_ui.app import BloxorzUrsinaApp

if not hasattr(builtins, "base"):
    _app = Ursina(headless=True)


class TestSolverPauseResumeGUI(unittest.TestCase):
    """Kiểm tra toàn diện tính năng Pause/Resume solver trên giao diện GUI."""

    def setUp(self) -> None:
        self.app = BloxorzUrsinaApp(start_in_menu=False)
        self.app.load_stage_by_id("10")  # Stage 10 có không gian tìm kiếm đủ lớn

    def tearDown(self) -> None:
        self.app.search_controller.cancel()
        self.app.action_reset()

    def test_gui_pause_resume_multiple_times(self) -> None:
        """Kiểm tra người chơi bấm nút Pause và Resume nhiều lần trong lúc giải."""
        # 1. Bắt đầu giải (Lần nhấn 1)
        self.assertEqual(self.app.ui.btn_solve_astar.text, "Giải A*")
        self.app.action_solve_astar()

        self.assertTrue(self.app.search_controller.is_running)
        self.assertEqual(self.app.ui.btn_solve_astar.text, "Tạm Dừng")

        # 2. Tạm dừng lần 1 (Lần nhấn 2)
        time.sleep(0.015)
        self.app.action_solve_astar()
        self.assertTrue(self.app.search_controller.is_paused)
        self.assertEqual(self.app.ui.btn_solve_astar.text, "Tiếp Tục")

        nodes_pause_1 = self.app.search_controller.expanded_nodes
        time.sleep(0.05)
        # Khi đang pause, số node không đổi
        self.assertEqual(self.app.search_controller.expanded_nodes, nodes_pause_1)

        # 3. Tiếp tục lần 1 (Lần nhấn 3)
        self.app.action_solve_astar()
        self.assertTrue(self.app.search_controller.is_running)
        self.assertFalse(self.app.search_controller.is_paused)
        self.assertEqual(self.app.ui.btn_solve_astar.text, "Tạm Dừng")

        # 4. Tạm dừng lần 2 (Lần nhấn 4)
        time.sleep(0.015)
        self.app.action_solve_astar()
        self.assertTrue(self.app.search_controller.is_paused)
        self.assertEqual(self.app.ui.btn_solve_astar.text, "Tiếp Tục")
        nodes_pause_2 = self.app.search_controller.expanded_nodes
        self.assertGreater(nodes_pause_2, nodes_pause_1, "Solver không tiếp tục từ điểm dừng cũ mà bị restart")

        # 5. Tiếp tục lần 2 cho đến khi hoàn thành (Lần nhấn 5)
        self.app.action_solve_astar()
        self.assertTrue(self.app.search_controller.is_running)

        deadline = time.monotonic() + 10.0
        while self.app.search_controller.is_running and time.monotonic() < deadline:
            time.sleep(0.02)
            self.app._poll_astar_results()

        self.assertFalse(self.app.search_controller.is_running)
        self.assertTrue(len(self.app.replay_actions) > 0)
        self.assertTrue(self.app.is_replay_playing)

    def test_gui_reset_while_solver_paused(self) -> None:
        """Kiểm tra Reset ván chơi khi solver đang Pause: Hủy solver, không phát kết quả cũ."""
        self.app.action_solve_astar()
        time.sleep(0.015)
        # Bấm tạm dừng
        self.app.action_solve_astar()
        self.assertTrue(self.app.search_controller.is_paused)

        old_generation = self.app._solver_generation

        # Bấm Reset
        self.app.action_reset()

        self.assertGreater(self.app._solver_generation, old_generation)
        self.assertEqual(self.app.search_controller.status, SearchStatus.CANCELLED)
        self.assertEqual(self.app.ui.btn_solve_astar.text, "Giải A*")
        self.assertFalse(self.app.is_replay_playing)

        # Cập nhật poll để đảm bảo kết quả cũ không được kích hoạt
        self.app._poll_astar_results()
        self.assertFalse(self.app.is_replay_playing)
        self.assertEqual(self.app.ui.btn_solve_astar.text, "Giải A*")

    def test_gui_stage_change_while_solver_paused(self) -> None:
        """Kiểm tra Đổi màn khi solver đang Pause: Hủy solver, không phát lời giải của màn cũ lên màn mới."""
        self.app.action_solve_astar()
        time.sleep(0.015)
        self.app.action_solve_astar()
        self.assertTrue(self.app.search_controller.is_paused)

        old_gen = self.app._solver_generation

        # Đổi sang màn 01
        self.app.load_stage_by_id("01")

        self.assertEqual(self.app.engine.stage_id, "stage01")
        self.assertGreater(self.app._solver_generation, old_gen)
        self.assertEqual(self.app.search_controller.status, SearchStatus.CANCELLED)
        self.assertEqual(self.app.ui.btn_solve_astar.text, "Giải A*")

        # Poll không được nhận kết quả của stage 10
        self.app._poll_astar_results()
        self.assertFalse(self.app.is_replay_playing)
        self.assertNotEqual(self.app.current_replay_file, "stage10")


if __name__ == "__main__":
    unittest.main()
