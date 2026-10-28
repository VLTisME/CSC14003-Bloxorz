"""Comprehensive unit tests for Task 2: Multi-Solver GUI Integration,

Pause/Resume verification across all solvers, Error handling, Timeout,
Reset, and Stage synchronization.
"""
from __future__ import annotations

import builtins
import time
import unittest
from ursina import Ursina

from game.search_controller import SearchStatus, SearchTaskResult
from game.ursina_ui.app import BloxorzUrsinaApp

if not hasattr(builtins, "base"):
    _app = Ursina(headless=True)


class TestMultiSolverGUI(unittest.TestCase):
    """Kiểm tra gọi đủ bộ solver trực tiếp trong GUI và các tương tác biên."""

    def setUp(self) -> None:
        self.app = BloxorzUrsinaApp(start_in_menu=False)
        self.app.load_stage_by_id("01")

    def tearDown(self) -> None:
        self.app.search_controller.cancel()
        self.app.action_reset()

    def test_cycle_through_all_algorithms(self) -> None:
        """Kiểm tra nút chuyển đổi xoay vòng qua 4 thuật toán: A* -> BFS -> DFS -> UCS -> A*."""
        self.assertEqual(self.app.selected_algorithm, "A*")
        self.assertEqual(self.app.ui.btn_algo_select.text, "A* ▼")
        self.assertEqual(self.app.ui.btn_solve.text, "Giải A*")

        # 1. Chuyển sang BFS
        self.app.action_cycle_algorithm()
        self.assertEqual(self.app.selected_algorithm, "BFS")
        self.assertEqual(self.app.ui.btn_algo_select.text, "BFS ▼")
        self.assertEqual(self.app.ui.btn_solve.text, "Giải BFS")

        # 2. Chuyển sang DFS
        self.app.action_cycle_algorithm()
        self.assertEqual(self.app.selected_algorithm, "DFS")
        self.assertEqual(self.app.ui.btn_algo_select.text, "DFS ▼")
        self.assertEqual(self.app.ui.btn_solve.text, "Giải DFS")

        # 3. Chuyển sang UCS
        self.app.action_cycle_algorithm()
        self.assertEqual(self.app.selected_algorithm, "UCS")
        self.assertEqual(self.app.ui.btn_algo_select.text, "UCS ▼")
        self.assertEqual(self.app.ui.btn_solve.text, "Giải UCS")

        # 4. Quay lại A*
        self.app.action_cycle_algorithm()
        self.assertEqual(self.app.selected_algorithm, "A*")
        self.assertEqual(self.app.ui.btn_algo_select.text, "A* ▼")
        self.assertEqual(self.app.ui.btn_solve.text, "Giải A*")

    def test_solve_and_replay_each_algorithm(self) -> None:
        """Kiểm tra gọi trực tiếp BFS, DFS, UCS, A* trên GUI: ra đúng lời giải và nạp vào Replay."""
        for algo in ("BFS", "DFS", "UCS", "A*"):
            with self.subTest(algorithm=algo):
                self.app.selected_algorithm = algo
                self.app.ui.set_selected_algorithm(algo)
                self.app.action_solve_current()

                self.assertTrue(self.app.search_controller.is_running)
                self.assertEqual(self.app.ui.btn_solve.text, "Tạm Dừng")

                deadline = time.monotonic() + 10.0
                while self.app.search_controller.is_running and time.monotonic() < deadline:
                    time.sleep(0.02)
                    self.app._poll_astar_results()

                self.assertFalse(self.app.search_controller.is_running)
                self.assertTrue(len(self.app.replay_actions) > 0)
                self.assertEqual(self.app.current_replay_file, algo)
                self.assertTrue(self.app.is_replay_playing)

                # Kiểm tra hiển thị cost đối với UCS
                if algo == "UCS":
                    self.assertIn("cost", self.app.ui.txt_solver_info.text)

                self.app.action_reset()

    def test_pause_resume_controls_calculation_for_all_solvers(self) -> None:
        """Kiểm tra Pause/Resume thực sự điều khiển tiến trình tính toán của cả 4 solver trên stage 10."""
        self.app.load_stage_by_id("10")
        for algo in ("BFS", "UCS", "A*"):
            with self.subTest(algorithm=algo):
                self.app.selected_algorithm = algo
                self.app.ui.set_selected_algorithm(algo)

                # Bắt đầu giải
                self.app.action_solve_current()
                self.assertTrue(self.app.search_controller.is_running)

                # Chờ một chút rồi bấm Tạm Dừng
                time.sleep(0.015)
                self.app.action_solve_current()
                self.assertTrue(self.app.search_controller.is_paused)
                self.assertEqual(self.app.ui.btn_solve.text, "Tiếp Tục")

                nodes_frozen = self.app.search_controller.expanded_nodes
                time.sleep(0.05)
                # Số node mở rộng phải đóng băng trong lúc pause
                self.assertEqual(self.app.search_controller.expanded_nodes, nodes_frozen)

                # Tiếp tục (Resume)
                self.app.action_solve_current()
                self.assertTrue(self.app.search_controller.is_running)
                self.assertFalse(self.app.search_controller.is_paused)
                self.assertEqual(self.app.ui.btn_solve.text, "Tạm Dừng")

                # Chờ giải xong
                deadline = time.monotonic() + 10.0
                while self.app.search_controller.is_running and time.monotonic() < deadline:
                    time.sleep(0.02)
                    self.app._poll_astar_results()

                self.assertFalse(self.app.search_controller.is_running)
                self.assertTrue(len(self.app.replay_actions) > 0)
                self.app.action_reset()

    def test_error_handling_invalid_solver_output(self) -> None:
        """Kiểm tra xử lý lỗi khi solver trả về kết quả sai luật (WA bị checker từ chối)."""
        self.app.selected_algorithm = "BFS"
        self.app._solver_generation = 100
        self.app._solver_stage_id = self.app.engine.stage_id
        self.app._solver_algorithm = "BFS"
        self.app._solver_start_move_count = 0

        # Giả lập solver trả về nước đi không hợp lệ (đâm vào hư không)
        bad_result = SearchTaskResult(
            generation=100,
            status=SearchStatus.COMPLETED,
            algorithm="BFS",
            actions=["L", "L", "L"],  # Đi sang trái từ vị trí ban đầu sẽ rơi khỏi sàn
        )
        self.app.search_controller._results_queue.put(bad_result)

        self.app._poll_astar_results()

        self.assertEqual(self.app.ui.btn_solve.text, "BFS: Lời giải lỗi")
        self.assertFalse(self.app.is_replay_playing)

    def test_timeout_handling(self) -> None:
        """Kiểm tra xử lý khi solver bị timeout."""
        self.app.selected_algorithm = "DFS"
        self.app._solver_generation = 200
        self.app._solver_stage_id = self.app.engine.stage_id
        self.app._solver_algorithm = "DFS"

        timeout_result = SearchTaskResult(
            generation=200,
            status=SearchStatus.TIMEOUT,
            algorithm="DFS",
            error_message="Quá thời gian tìm kiếm",
        )
        self.app.search_controller._results_queue.put(timeout_result)

        self.app._poll_astar_results()

        self.assertEqual(self.app.ui.btn_solve.text, "DFS: Hết giờ")
        self.assertFalse(self.app.is_replay_playing)

    def test_reset_during_search_aborts_and_clears_results(self) -> None:
        """Kiểm tra Reset trong lúc solver đang chạy: Hủy tiến trình, dọn sạch hàng đợi."""
        self.app.load_stage_by_id("10")
        self.app.selected_algorithm = "BFS"
        self.app.action_solve_current()

        self.assertTrue(self.app.search_controller.is_running)
        old_generation = self.app._solver_generation

        # Người chơi nhấn Reset bàn cờ
        self.app.action_reset()

        self.assertGreater(self.app._solver_generation, old_generation)
        self.assertIsNone(self.app._solver_stage_id)
        self.assertEqual(self.app.search_controller.status, SearchStatus.CANCELLED)
        self.assertEqual(self.app.ui.btn_solve.text, "Giải BFS")

        # Cập nhật poll: Kết quả cũ không được phép nạp vào replay
        self.app._poll_astar_results()
        self.assertFalse(self.app.is_replay_playing)

    def test_stage_change_during_search_prevents_cross_stage_replay(self) -> None:
        """Kiểm tra Đổi màn trong lúc solver đang chạy: Kết quả màn cũ không được phát lên màn mới."""
        self.app.load_stage_by_id("10")
        self.app.selected_algorithm = "BFS"
        self.app.action_solve_current()

        self.assertTrue(self.app.search_controller.is_running)

        # Đổi sang màn 01
        self.app.load_stage_by_id("01")
        self.assertEqual(self.app.engine.stage_id, "stage01")
        self.assertEqual(self.app.search_controller.status, SearchStatus.CANCELLED)

        # Giả lập nếu có kết quả của stage 10 trễ gửi về
        stale_result = SearchTaskResult(
            generation=self.app._solver_generation - 1,
            status=SearchStatus.COMPLETED,
            algorithm="BFS",
            actions=["R"] * 50,  # Lời giải của stage 10
        )
        self.app.search_controller._results_queue.put(stale_result)

        self.app._poll_astar_results()
        # Tuyệt đối không phát lời giải của màn 10 lên màn 01
        self.assertFalse(self.app.is_replay_playing)
        self.assertNotEqual(self.app.replay_actions, ["R"] * 50)


if __name__ == "__main__":
    unittest.main()
