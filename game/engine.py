"""Core game engine cho Bloxorz.

Module độc lập 100% với GUI, tái sử dụng logic chuyển trạng thái từ checker.py,
bổ sung quản lý phiên chơi tương tác: GameStatus, active cube, undo stack và helper thông tin.
"""
from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
import sys

# Đảm bảo import được checker từ thư mục gốc
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from checker import ACTIONS, DIRECTIONS, Lost, Replay, StageError, State


class GameStatus(str, Enum):
    """Trạng thái hiện tại của ván chơi."""
    PLAYING = "PLAYING"
    WON = "WON"
    LOST = "LOST"


class Posture(str, Enum):
    """Tư thế của khối hộp."""
    UPRIGHT = "UPRIGHT"       # Đứng thẳng (1 ô)
    HORIZONTAL = "HORIZONTAL" # Nằm ngang theo hàng (2 ô, row1 == row2, col1 != col2)
    VERTICAL = "VERTICAL"     # Nằm dọc theo cột (2 ô, row1 != row2, col1 == col2)
    SPLIT = "SPLIT"           # Đã tách thành 2 khối nhỏ 1x1x1


class BloxorzEngine:
    """Quản lý trạng thái và luật chơi tương tác của một màn Bloxorz."""

    def __init__(self, stage: dict | None = None) -> None:
        self.stage: dict | None = None
        self.replay: Replay | None = None
        self.state: State | None = None
        self.initial_state: State | None = None
        self.status: GameStatus = GameStatus.PLAYING
        self.lost_reason: str | None = None
        self.selected_cube: int = 1  # 1 hoặc 2 khi khối đang ở trạng thái tách (split)
        self.history: list[tuple[State, int, str, GameStatus, str | None]] = []
        self.move_count: int = 0
        self.last_split_at: tuple[int, int] | None = None

        if stage is not None:
            self.load_stage(stage)

    def load_stage(self, stage: dict) -> None:
        """Nạp cấu hình màn chơi từ dict JSON."""
        self.stage = stage
        self.replay = Replay(stage)
        self.initial_state = self.replay.initial
        self.reset()

    def reset(self) -> None:
        """Đặt lại màn chơi về trạng thái ban đầu."""
        if self.replay is None or self.initial_state is None:
            raise RuntimeError("Chưa nạp màn chơi nào vào engine.")
        self.state = self.initial_state
        self.status = GameStatus.PLAYING
        self.lost_reason = None
        self.selected_cube = 1
        self.history.clear()
        self.move_count = 0
        self.last_split_at = None

    def toggle_cube(self) -> int:
        """Chuyển đổi điều khiển giữa khối nhỏ 1 và 2 (khi đang tách). Chi phí 0 bước."""
        if self.state is not None and self.state.split:
            self.selected_cube = 2 if self.selected_cube == 1 else 1
        return self.selected_cube

    def normalize_action(self, action_or_dir: str) -> str:
        """Chuẩn hóa input: nếu chỉ truyền hướng (U/D/L/R) khi đang tách, tự gắn prefix khối."""
        act = action_or_dir.strip().upper()
        if self.state is not None and self.state.split:
            if act in DIRECTIONS:
                return f"{self.selected_cube}{act}"
        return act

    def step(self, action_or_dir: str) -> bool:
        """Thực hiện một hành động di chuyển.

        Trả về:
            True nếu bước đi thành công.
            False nếu bước đi gây thua (Lost) hoặc ván chơi đã kết thúc.
        """
        if self.replay is None or self.state is None:
            raise RuntimeError("Chưa nạp màn chơi vào engine.")

        if self.status != GameStatus.PLAYING:
            return False

        action = self.normalize_action(action_or_dir)
        if action not in ACTIONS:
            raise ValueError(f"Hành động không hợp lệ: {action_or_dir!r}")

        prev_state = self.state
        prev_cube = self.selected_cube
        prev_status = self.status
        prev_reason = self.lost_reason

        try:
            next_state, split_at = self.replay.step(prev_state, action)
            self.last_split_at = split_at
            self.history.append((prev_state, prev_cube, action, prev_status, prev_reason))
            self.state = next_state
            self.move_count += 1

            # Nếu đã ghép lại thì mặc định chọn khối 1
            if not self.state.split:
                self.selected_cube = 1

            if self.replay.won(self.state):
                self.status = GameStatus.WON

            return True

        except Lost as exc:
            # Lưu lại vào history để người chơi có thể Undo sau khi thua
            self.history.append((prev_state, prev_cube, action, prev_status, prev_reason))
            self.status = GameStatus.LOST
            self.lost_reason = str(exc)
            self.move_count += 1
            return False

    def undo(self) -> bool:
        """Hoàn tác bước đi gần nhất. Phục hồi trạng thái chơi nếu vừa bị thua."""
        if not self.history:
            return False

        prev_state, prev_cube, _, prev_status, prev_reason = self.history.pop()
        self.state = prev_state
        self.selected_cube = prev_cube
        self.status = prev_status
        self.lost_reason = prev_reason
        self.move_count = max(0, self.move_count - 1)
        return True

    def get_valid_actions(self) -> list[str]:
        """Trả về danh sách các action hợp lệ từ trạng thái hiện tại (không gây Lost)."""
        if self.replay is None or self.state is None or self.status != GameStatus.PLAYING:
            return []

        candidates: list[str]
        if self.state.split:
            candidates = [f"{self.selected_cube}{d}" for d in DIRECTIONS]
        else:
            candidates = list(DIRECTIONS)

        valid = []
        for act in candidates:
            try:
                self.replay.step(self.state, act)
                valid.append(act)
            except Lost:
                pass
        return valid

    # --- Các thuộc tính hỗ trợ vẽ giao diện (GUI helpers) ---

    @property
    def posture(self) -> Posture:
        """Xác định tư thế hiện tại của khối."""
        if self.state is None:
            return Posture.UPRIGHT
        if self.state.split:
            return Posture.SPLIT
        a, b = self.state.first, self.state.second
        if a == b:
            return Posture.UPRIGHT
        if a[0] == b[0]:
            return Posture.HORIZONTAL
        return Posture.VERTICAL

    @property
    def block_cells(self) -> list[tuple[int, int]]:
        """Trả về danh sách tọa độ các ô khối đang chiếm giữ."""
        if self.state is None:
            return []
        if self.state.split:
            return [self.state.first, self.state.second]
        if self.state.first == self.state.second:
            return [self.state.first]
        return [self.state.first, self.state.second]

    @property
    def is_split(self) -> bool:
        """Khối đang tách thành 2 khối nhỏ hay không."""
        return self.state.split if self.state is not None else False

    @property
    def is_won(self) -> bool:
        return self.status == GameStatus.WON

    @property
    def is_lost(self) -> bool:
        return self.status == GameStatus.LOST

    @property
    def is_playing(self) -> bool:
        return self.status == GameStatus.PLAYING

    @property
    def stage_id(self) -> str:
        return self.replay.stage_id if self.replay else ""

    @property
    def goal(self) -> tuple[int, int]:
        if self.replay is None:
            raise RuntimeError("Chưa nạp màn chơi.")
        return self.replay.goal

    @property
    def cells(self) -> dict[tuple[int, int], str]:
        if self.replay is None:
            raise RuntimeError("Chưa nạp màn chơi.")
        return self.replay.cells

    @property
    def dimensions(self) -> tuple[int, int]:
        """Trả về (số hàng, số cột) của bàn chơi."""
        if not self.replay:
            return (0, 0)
        rows = max(r for r, _ in self.replay.cells) + 1
        cols = max(c for _, c in self.replay.cells) + 1
        return (rows, cols)

    def is_bridge_active(self, bridge_index: int) -> bool:
        """Kiểm tra trạng thái bật/tắt của một nhóm cầu theo index."""
        if self.state is None:
            return False
        return self.state.bridges[bridge_index]

    def get_cell_type_at(self, r: int, c: int) -> str:
        """Lấy ký tự loại ô tại tọa độ (r, c). Trả về '#' nếu ngoài bàn cờ."""
        if self.replay is None:
            return "#"
        return self.replay.cells.get((r, c), "#")


def self_test_all_reference_solutions() -> bool:
    """Hàm tự kiểm tra engine trên toàn bộ 39 màn tham chiếu."""
    testcases_dir = ROOT_DIR / "testcases"
    in_files = sorted(testcases_dir.glob("*/*.in.json"))
    if not in_files:
        print("[LỖI] Không tìm thấy testcase nào.")
        return False

    print(f"Đang kiểm tra {len(in_files)} màn tham chiếu với BloxorzEngine...")
    passed = 0
    engine = BloxorzEngine()

    for in_path in in_files:
        out_path = in_path.with_name(in_path.name.replace(".in.json", ".out.json"))
        stage_data = json.loads(in_path.read_text(encoding="utf-8"))
        ans_data = json.loads(out_path.read_text(encoding="utf-8"))

        engine.load_stage(stage_data)
        actions = ans_data.get("actions", [])

        # Kiểm tra replay từng bước
        for act in actions:
            success = engine.step(act)
            if not success:
                break

        if engine.is_won and engine.move_count == len(actions):
            # Test thử tính năng Undo và Reset
            engine.undo()
            if engine.is_playing and engine.move_count == len(actions) - 1:
                engine.step(actions[-1])
                if engine.is_won:
                    passed += 1
                    continue

        print(f"  [THẤT BẠI] {stage_data['id']}: status={engine.status}, moves={engine.move_count}/{len(actions)}")

    print(f"Kết quả kiểm tra: Đạt {passed}/{len(in_files)} màn!")
    return passed == len(in_files)


if __name__ == "__main__":
    success = self_test_all_reference_solutions()
    sys.exit(0 if success else 1)
