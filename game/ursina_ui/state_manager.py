"""Bộ quản lý trạng thái trò chơi (State Machine) cho Bloxorz Ursina UI.

Quản lý chuyển đổi giữa các màn hình và trạng thái ván chơi:
- MAIN_MENU: Màn hình chính
- LEVEL_SELECT: Màn hình / Modal chọn màn chơi
- PLAYING: Trạng thái đang chơi màn
- PAUSED: Tạm dừng ván chơi (Pause Menu)
- WIN: Màn hình chúc mừng chiến thắng
- LOSE: Màn hình thông báo thất bại / rơi vực
- SETTINGS: Cài đặt âm thanh, đồ họa, chủ đề
- HELP: Hướng dẫn chơi và danh sách phím tắt
- REPLAY: Đang phát lại lời giải tự động
"""
from __future__ import annotations

from enum import Enum, auto
from typing import Any, Callable


class GameState(Enum):
    """Định nghĩa các trạng thái cốt lõi của game."""
    MAIN_MENU = "MAIN_MENU"
    LEVEL_SELECT = "LEVEL_SELECT"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    WIN = "WIN"
    LOSE = "LOSE"
    SETTINGS = "SETTINGS"
    HELP = "HELP"
    REPLAY = "REPLAY"


class StateManager:
    """Máy trạng thái (Finite State Machine) quản lý luồng màn hình."""

    def __init__(self, initial_state: GameState = GameState.PLAYING) -> None:
        self._current_state: GameState = initial_state
        self._previous_state: GameState | None = None
        self._state_stack: list[GameState] = [initial_state]

        # Callbacks đăng ký: dict[GameState, list[Callable]]
        self._enter_hooks: dict[GameState, list[Callable[..., None]]] = {s: [] for s in GameState}
        self._exit_hooks: dict[GameState, list[Callable[..., None]]] = {s: [] for s in GameState}
        self._change_listeners: list[Callable[[GameState, GameState], None]] = []

    @property
    def current_state(self) -> GameState:
        """Trạng thái hoạt động hiện tại."""
        return self._current_state

    @property
    def previous_state(self) -> GameState | None:
        """Trạng thái trước đó."""
        return self._previous_state

    def is_state(self, state: GameState) -> bool:
        """Kiểm tra xem có đang ở trạng thái chỉ định không."""
        return self._current_state == state

    @property
    def is_playing(self) -> bool:
        """Kiểm tra xem người chơi có đang trực tiếp lăn khối không."""
        return self._current_state == GameState.PLAYING

    def on_enter(self, state: GameState, callback: Callable[..., None]) -> None:
        """Đăng ký hook khi bước vào một trạng thái."""
        self._enter_hooks[state].append(callback)

    def on_exit(self, state: GameState, callback: Callable[..., None]) -> None:
        """Đăng ký hook khi rời khỏi một trạng thái."""
        self._exit_hooks[state].append(callback)

    def on_change(self, callback: Callable[[GameState, GameState], None]) -> None:
        """Đăng ký listener mỗi khi có bất kỳ sự thay đổi trạng thái nào."""
        self._change_listeners.append(callback)

    def transition_to(self, new_state: GameState, **kwargs: Any) -> bool:
        """Chuyển đổi trạng thái trực tiếp."""
        if self._current_state == new_state:
            return False

        old_state = self._current_state
        self._previous_state = old_state

        # 1. Gọi các hook thoát khỏi trạng thái cũ
        for hook in self._exit_hooks.get(old_state, []):
            try:
                hook()
            except Exception as e:
                print(f"[StateManager] Lỗi khi gọi exit hook của {old_state}: {e}")

        # 2. Cập nhật trạng thái mới
        self._current_state = new_state
        self._state_stack[-1] = new_state

        # 3. Thông báo cho các change listeners
        for listener in self._change_listeners:
            try:
                listener(old_state, new_state)
            except Exception as e:
                print(f"[StateManager] Lỗi khi gọi change listener: {e}")

        # 4. Gọi các hook bước vào trạng thái mới
        for hook in self._enter_hooks.get(new_state, []):
            try:
                hook(**kwargs)
            except TypeError:
                # Nếu hook không nhận kwargs
                hook()
            except Exception as e:
                print(f"[StateManager] Lỗi khi gọi enter hook của {new_state}: {e}")

        return True

    def push_state(self, new_state: GameState, **kwargs: Any) -> bool:
        """Đẩy một trạng thái overlay lên đỉnh stack (ví dụ PAUSED, HELP)."""
        if self._current_state == new_state:
            return False

        old_state = self._current_state
        self._previous_state = old_state

        for hook in self._exit_hooks.get(old_state, []):
            try:
                hook()
            except Exception as e:
                print(f"[StateManager] Lỗi khi gọi exit hook của {old_state}: {e}")

        self._state_stack.append(new_state)
        self._current_state = new_state

        for listener in self._change_listeners:
            try:
                listener(old_state, new_state)
            except Exception as e:
                print(f"[StateManager] Lỗi khi gọi change listener: {e}")

        for hook in self._enter_hooks.get(new_state, []):
            try:
                hook(**kwargs)
            except TypeError:
                hook()
            except Exception as e:
                print(f"[StateManager] Lỗi khi gọi enter hook của {new_state}: {e}")

        return True

    def pop_state(self) -> GameState | None:
        """Quay lại trạng thái trước đó trên stack."""
        if len(self._state_stack) <= 1:
            return None

        old_state = self._state_stack.pop()
        self._previous_state = old_state

        for hook in self._exit_hooks.get(old_state, []):
            try:
                hook()
            except Exception as e:
                print(f"[StateManager] Lỗi khi gọi exit hook của {old_state}: {e}")

        target_state = self._state_stack[-1]
        self._current_state = target_state

        for listener in self._change_listeners:
            try:
                listener(old_state, target_state)
            except Exception as e:
                print(f"[StateManager] Lỗi khi gọi change listener: {e}")

        for hook in self._enter_hooks.get(target_state, []):
            try:
                hook()
            except Exception as e:
                print(f"[StateManager] Lỗi khi gọi enter hook của {target_state}: {e}")

        return target_state
