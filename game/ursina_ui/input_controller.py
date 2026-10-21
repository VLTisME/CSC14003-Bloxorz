"""Bộ điều khiển nhập liệu (InputController) cho Bloxorz Ursina UI.

Chịu trách nhiệm:
1. Ánh xạ toàn diện phím điều khiển (WASD, phím mũi tên đầy đủ tên Ursina, chữ hoa/thường).
2. Quản lý hàng đợi nước đi (Move Queue / Buffer) chống mất phím khi bấm nhanh.
3. Hỗ trợ giữ phím (Hold-to-repeat) với độ trễ và nhịp lặp tối ưu cho cảm giác lăn mượt mà.
4. Bộ giám sát an toàn (Watchdog Timer) tự động giải phóng cờ khóa nếu animation bị kẹt quá thời hạn.
5. Độc lập với UI window để có thể kiểm thử đơn vị thuần túy (pure unit test) trong game/tests_ui/.
"""
from __future__ import annotations

from typing import Callable


class InputController:
    """Quản lý và điều phối logic nhập liệu bàn phím, hàng đợi và watchdog an toàn."""

    # Bảng ánh xạ phím di chuyển sang 4 hướng U / D / L / R
    # Tên event bàn phím chuẩn của Ursina.
    MOVE_KEY_MAP: dict[str, str] = {
        "w": "U",
        "up arrow": "U",
        "s": "D",
        "down arrow": "D",
        "a": "L",
        "left arrow": "L",
        "d": "R",
        "right arrow": "R",
    }

    # Bảng nhận diện sự kiện nhả phím (key up) để ngắt cơ chế giữ phím
    KEY_UP_MAP: dict[str, str] = {
        "w up": "U",
        "up arrow up": "U",
        "s up": "D",
        "down arrow up": "D",
        "a up": "L",
        "left arrow up": "L",
        "d up": "R",
        "right arrow up": "R",
    }

    def __init__(
        self,
        on_move: Callable[[str], bool],
        is_busy_fn: Callable[[], bool],
        is_playing_fn: Callable[[], bool],
        on_watchdog_timeout: Callable[[], None] | None = None,
        max_queue_size: int = 2,
        initial_repeat_delay: float = 0.22,
        repeat_interval: float = 0.16,
        max_lock_duration: float = 1.0,
        enable_hold_repeat: bool = True,
        debug: bool = False,
    ) -> None:
        self.on_move = on_move
        self.is_busy_fn = is_busy_fn
        self.is_playing_fn = is_playing_fn
        self.on_watchdog_timeout = on_watchdog_timeout

        self.max_queue_size = max_queue_size
        self.initial_repeat_delay = initial_repeat_delay
        self.repeat_interval = repeat_interval
        self.max_lock_duration = max_lock_duration
        self.enable_hold_repeat = enable_hold_repeat
        self.debug = debug

        # Hàng đợi các nước đi đệm (buffer)
        self.queue: list[str] = []

        # Trạng thái giữ phím (hold-to-repeat)
        self.held_direction: str | None = None
        self.hold_time: float = 0.0
        self.last_repeat_time: float = 0.0

        # Bộ đếm giám sát chống kẹt animation (Watchdog)
        self.busy_timer: float = 0.0
        self.watchdog_triggered_count: int = 0

    def reset(self) -> None:
        """Đặt lại toàn bộ trạng thái hàng đợi và bộ đếm phím giữ."""
        self.queue.clear()
        self.held_direction = None
        self.hold_time = 0.0
        self.last_repeat_time = 0.0
        self.busy_timer = 0.0
        if self.debug:
            print("[INPUT_CONTROLLER] Đã đặt lại trạng thái nhập liệu.")

    def handle_key_down(self, key: str) -> bool:
        """Xử lý sự kiện nhấn phím xuống.
        
        Trả về True nếu phím là một phím di chuyển hợp lệ được tiếp nhận.
        """
        direction = self.MOVE_KEY_MAP.get(key)
        if direction is None:
            return False

        if not self.is_playing_fn():
            if self.debug:
                print(f"[INPUT_CONTROLLER] Từ chối phím '{key}' ({direction}): Ván chơi không ở trạng thái PLAYING.")
            return False

        # Chỉ lưu hướng đang giữ khi chế độ lặp được bật. GUI mặc định tắt
        # chế độ này để một lần nhấn chỉ tạo một nước đi.
        self.held_direction = direction if self.enable_hold_repeat else None
        self.hold_time = 0.0
        self.last_repeat_time = 0.0

        if self.is_busy_fn():
            # Đang chạy hoạt ảnh -> Thêm vào hàng đợi đệm nếu còn chỗ
            if len(self.queue) < self.max_queue_size:
                self.queue.append(direction)
                if self.debug:
                    print(f"[INPUT_CONTROLLER] Đệm nước đi: {direction} (Hàng đợi: {self.queue})")
                return True
            else:
                if self.debug:
                    print(f"[INPUT_CONTROLLER] Hàng đợi đầy ({self.max_queue_size}), bỏ qua nước đi: {direction}")
                return False

        # Thực hiện nước đi ngay lập tức
        if self.debug:
            print(f"[INPUT_CONTROLLER] Thực hiện nước đi: {direction}")
        return self.on_move(direction)

    def handle_key_up(self, key: str) -> bool:
        """Xử lý sự kiện nhả phím lên để dừng lặp nước đi."""
        released_dir = self.KEY_UP_MAP.get(key)
        if released_dir is not None and released_dir == self.held_direction:
            self.held_direction = None
            self.hold_time = 0.0
            self.last_repeat_time = 0.0
            if self.debug:
                print(f"[INPUT_CONTROLLER] Nhả phím hướng: {released_dir}")
            return True
        return False

    def on_animation_complete(self) -> None:
        """Gọi khi hoạt ảnh lăn hoàn tất, lấy nước đi tiếp theo từ hàng đợi nếu có."""
        self.busy_timer = 0.0
        if not self.is_playing_fn():
            self.queue.clear()
            return

        if self.queue:
            next_dir = self.queue.pop(0)
            if self.debug:
                print(f"[INPUT_CONTROLLER] Lấy nước đi từ hàng đợi: {next_dir} (Còn lại: {self.queue})")
            self.on_move(next_dir)

    def update(self, dt: float) -> None:
        """Vòng lặp cập nhật theo từng khung hình (xử lý giữ phím và watchdog an toàn)."""
        # 1. Giám sát an toàn (Watchdog timer)
        if self.is_busy_fn() and self.is_playing_fn():
            self.busy_timer += dt

            if self.busy_timer >= self.max_lock_duration:
                self.watchdog_triggered_count += 1
                if self.debug:
                    print(
                        f"[WATCHDOG] CẢNH BÁO: Khóa animation kéo dài quá {self.max_lock_duration}s! "
                        f"Tự động phá khóa để người chơi tiếp tục di chuyển."
                    )
                self.busy_timer = 0.0
                self.queue.clear()
                if self.on_watchdog_timeout:
                    self.on_watchdog_timeout()
        else:
            self.busy_timer = 0.0

        # 2. Xử lý giữ phím để lăn liên tục (Hold-to-repeat)
        if self.enable_hold_repeat and self.held_direction and self.is_playing_fn():
            self.hold_time += dt
            if self.hold_time >= self.initial_repeat_delay:
                time_since_repeat = self.hold_time - self.initial_repeat_delay - self.last_repeat_time
                if time_since_repeat >= self.repeat_interval:
                    self.last_repeat_time += self.repeat_interval
                    if not self.is_busy_fn():
                        if self.debug:
                            print(f"[INPUT_CONTROLLER] Lặp phím giữ: {self.held_direction}")
                        self.on_move(self.held_direction)
                    elif len(self.queue) < self.max_queue_size:
                        self.queue.append(self.held_direction)
