"""Kiểm thử hồi quy cho module InputController (game/tests_ui/test_input.py).

Kiểm tra:
1. Ánh xạ phím mũi tên và WASD (cả thường lẫn hoa).
2. Hàng đợi nước đi (Move Queue) khi đang bận animation.
3. Chặn phím khi ván chơi không ở trạng thái PLAYING.
4. Bộ watchdog an toàn tự động phá khóa khi animation bị treo quá lâu.
5. Cơ chế giữ phím (Hold-to-repeat).
6. Khôi phục trạng thái sạch khi gọi reset().
"""
from __future__ import annotations

import unittest

from game.ursina_ui.input_controller import InputController


class TestInputController(unittest.TestCase):
    """Bộ kiểm thử đơn vị độc lập cho InputController."""

    def setUp(self) -> None:
        self.moves_executed: list[str] = []
        self.is_busy = False
        self.is_playing = True
        self.watchdog_called = False

        self.controller = InputController(
            on_move=self._on_move,
            is_busy_fn=lambda: self.is_busy,
            is_playing_fn=lambda: self.is_playing,
            on_watchdog_timeout=self._on_watchdog,
            max_queue_size=2,
            initial_repeat_delay=0.20,
            repeat_interval=0.15,
            max_lock_duration=1.0,
            debug=False,
        )

    def _on_move(self, direction: str) -> bool:
        self.moves_executed.append(direction)
        return True

    def _on_watchdog(self) -> None:
        self.watchdog_called = True
        self.is_busy = False

    def test_arrow_keys_and_wasd_mapping(self) -> None:
        """Kiểm tra toàn bộ các phím mũi tên và WASD kích hoạt đúng 4 hướng."""
        cases = [
            ("up arrow", "U"),
            ("w", "U"),
            ("down arrow", "D"),
            ("s", "D"),
            ("left arrow", "L"),
            ("a", "L"),
            ("right arrow", "R"),
            ("d", "R"),
        ]
        for key, expected_dir in cases:
            self.moves_executed.clear()
            accepted = self.controller.handle_key_down(key)
            self.assertTrue(accepted, f"Phím '{key}' phải được chấp nhận.")
            self.assertEqual(self.moves_executed, [expected_dir], f"Phím '{key}' phải kích hoạt hướng {expected_dir}.")

    def test_invalid_key_rejected(self) -> None:
        """Phím không liên quan không được kích hoạt di chuyển."""
        self.moves_executed.clear()
        accepted = self.controller.handle_key_down("f")
        self.assertFalse(accepted)
        self.assertEqual(len(self.moves_executed), 0)

    def test_reject_when_not_playing(self) -> None:
        """Khi game đã thắng, thua hoặc tạm dừng, không tiếp nhận nước đi."""
        self.is_playing = False
        accepted = self.controller.handle_key_down("right arrow")
        self.assertFalse(accepted)
        self.assertEqual(len(self.moves_executed), 0)

    def test_move_queue_when_busy(self) -> None:
        """Khi đang bận animation, nước đi được đưa vào hàng đợi và chạy khi animation xong."""
        # Nước đi đầu tiên khi rảnh
        self.controller.handle_key_down("right arrow")
        self.assertEqual(self.moves_executed, ["R"])

        # Đặt trạng thái bận
        self.is_busy = True

        # Nhấn tiếp 2 nước đi
        self.controller.handle_key_down("up arrow")
        self.controller.handle_key_down("left arrow")
        self.assertEqual(self.controller.queue, ["U", "L"])
        self.assertEqual(self.moves_executed, ["R"])  # Chưa thực hiện thêm

        # Animation thứ nhất xong
        self.is_busy = False
        self.controller.on_animation_complete()
        self.assertEqual(self.moves_executed, ["R", "U"])
        self.assertEqual(self.controller.queue, ["L"])

        # Animation thứ hai xong
        self.controller.on_animation_complete()
        self.assertEqual(self.moves_executed, ["R", "U", "L"])
        self.assertEqual(self.controller.queue, [])

    def test_queue_overflow_protection(self) -> None:
        """Hàng đợi chỉ lưu tối đa max_queue_size để chống tràn đệm."""
        self.is_busy = True
        self.assertTrue(self.controller.handle_key_down("w"))
        self.assertTrue(self.controller.handle_key_down("s"))
        # Nước đi thứ 3 bị từ chối vì hàng đợi đã đầy (max=2)
        self.assertFalse(self.controller.handle_key_down("d"))
        self.assertEqual(self.controller.queue, ["U", "D"])

    def test_arrow_key_release_stops_repeat_for_backend_variants(self) -> None:
        """Tên key-up khác nhau của backend không được để lại input đang giữ."""
        self.controller.handle_key_down("up arrow")
        self.assertEqual(self.controller.held_direction, "U")

        self.assertTrue(self.controller.handle_key_up("up arrow up"))
        self.assertIsNone(self.controller.held_direction)

        self.controller.update(1.0)
        self.assertEqual(self.moves_executed, ["U"])

    def test_watchdog_auto_unlock(self) -> None:
        """Watchdog kích hoạt và giải phóng khóa khi is_busy kéo dài quá 1.0 giây."""
        self.is_busy = True
        self.controller.queue.append("R")

        # Giả lập thời gian trôi qua 0.5s -> Chưa timeout
        self.controller.update(0.5)
        self.assertFalse(self.watchdog_called)

        # Trôi qua thêm 0.6s (tổng 1.1s > max_lock_duration 1.0s) -> Phải timeout
        self.controller.update(0.6)
        self.assertTrue(self.watchdog_called)
        self.assertFalse(self.is_busy)
        self.assertEqual(len(self.controller.queue), 0)
        self.assertEqual(self.controller.watchdog_triggered_count, 1)

    def test_reset_clears_all_buffers(self) -> None:
        """Hàm reset() dọn sạch hàng đợi và các bộ đếm."""
        self.is_busy = True
        self.controller.handle_key_down("w")
        self.controller.update(0.4)
        self.assertGreater(len(self.controller.queue), 0)

        self.controller.reset()
        self.assertEqual(len(self.controller.queue), 0)
        self.assertIsNone(self.controller.held_direction)
        self.assertEqual(self.controller.busy_timer, 0.0)

    def test_hold_to_repeat(self) -> None:
        """Giữ phím liên tục sẽ kích hoạt thêm nước đi sau khoảng trễ ban đầu."""
        self.controller.handle_key_down("right arrow")
        self.assertEqual(self.moves_executed, ["R"])

        # Chưa đủ thời gian trễ ban đầu (0.1s < 0.20s)
        self.controller.update(0.10)
        self.assertEqual(self.moves_executed, ["R"])

        # Đủ thời gian trễ ban đầu + nhịp lặp (0.20s + 0.15s = 0.35s)
        self.controller.update(0.26)
        self.assertEqual(self.moves_executed, ["R", "R"])

        # Nhả phím -> Dừng lặp
        self.controller.handle_key_up("right arrow up")
        self.controller.update(0.50)
        self.assertEqual(self.moves_executed, ["R", "R"])

    def test_repeat_can_be_disabled_for_single_press_controls(self) -> None:
        """Chế độ GUI một-nhấn-một-nước không tự lặp khi không có key-up."""
        self.controller = InputController(
            on_move=self._on_move,
            is_busy_fn=lambda: self.is_busy,
            is_playing_fn=lambda: self.is_playing,
            enable_hold_repeat=False,
        )

        self.assertTrue(self.controller.handle_key_down("up arrow"))
        self.controller.update(2.0)
        self.assertEqual(self.moves_executed, ["U"])


if __name__ == "__main__":
    unittest.main()
