"""Mô hình luật Bloxorz dùng chung cho các solver.

Module này *không* chứa BFS, DFS, UCS, A* hay đo lường. Nó chỉ cung cấp một
giao diện nhỏ, thống nhất để các thuật toán sinh state kế tiếp từ cùng luật
với checker/game. Nhờ vậy, một đường đi mà solver coi là hợp lệ cũng sẽ được
checker và giao diện phát lại theo đúng các luật bridge, switch, splitter và
ghép hai cube.

Giao diện công khai:
    parse_stage(stage)                 -> model
    initial_state(model)               -> State
    next_states(state, model)          -> iterator[(State, action)]
    is_goal(state, model)              -> bool
    reconstruct_path(parents, goal)    -> list[action]

Quy ước cho người viết thuật toán:
* State đã là immutable/hashable, nên dùng trực tiếp trong ``visited`` và
  làm khóa cho ``parents``.
* ``next_states`` chỉ trả về nước đi không gây thua; mỗi action lăn có cost 1.
* Khi khối đã tách, action có dạng ``1U`` ... ``2R``; thứ tự cube ID được giữ
  nguyên bởi checker.Replay.
* Không sửa module này hoặc checker.py để phục vụ riêng một thuật toán nếu
  chưa thống nhất với nhóm, vì đây là điểm dùng chung của các solver.

Các thuật toán vẫn phải tự cài đặt search frontier, visited, parent map và
tiêu chí mở rộng node. Việc tái sử dụng model luật chơi không thay thế việc
tự cài BFS/DFS/UCS/A*.
"""
from __future__ import annotations

# Kiểu dữ liệu cho iterator trả về và bảng ánh xạ parents
from collections.abc import Iterator, Mapping
# Xác định thư mục gốc dự án để import checker.py
from pathlib import Path
import sys

# Khi chạy ``python algorithms/BFS.py``, Python chỉ tự thêm algorithms/ vào
# sys.path. Thêm thư mục gốc để import checker.py một cách ổn định.
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from checker import Lost, Replay, State


# Alias này giúp code solver diễn đạt rõ ý nghĩa hơn mà không bọc lại engine.
BloxorzModel = Replay
# Bốn hướng lăn block hợp lệ; thứ tự này cũng quyết định thứ tự sinh successor.
ACTION_DIRECTIONS = ("U", "D", "L", "R")


def parse_stage(stage: dict) -> BloxorzModel:
    """Kiểm tra dữ liệu stage và tạo model luật chơi chuẩn."""
    # Replay kiểm tra stage và giữ toàn bộ luật/chỉ số cần để mô phỏng màn chơi.
    return Replay(stage)


def initial_state(model: BloxorzModel) -> State:
    """Trả về state ban đầu của stage."""
    # State ban đầu do engine tạo sẵn, bao gồm vị trí và trạng thái tách/gộp cube.
    return model.initial


def next_states(state: State, model: BloxorzModel) -> Iterator[tuple[State, str]]:
    """Sinh các successor hợp lệ theo thứ tự xác định.

    Các action gây rơi, đi ra ngoài bàn, đứng trên fragile tile, hoặc làm
    bridge bên dưới cube tắt sẽ bị bỏ qua. ``Replay.step`` xử lý toàn bộ hiệu
    ứng sau khi di chuyển, gồm switch, splitter, kiểm tra support lần hai và
    tự ghép cube.
    """
    # Khi block tách, mỗi cube được di chuyển độc lập nên action kèm ID cube.
    if state.split:
        actions = (f"{cube}{direction}" for cube in (1, 2) for direction in ACTION_DIRECTIONS)
    else:
        # Block chưa tách chỉ cần chọn một trong bốn hướng lăn.
        actions = iter(ACTION_DIRECTIONS)

    # Thử từng action để tạo state kế tiếp.
    for action in actions:
        try:
            # Engine áp dụng đầy đủ luật Bloxorz rồi trả state sau khi di chuyển.
            successor, _ = model.step(state, action)
        except Lost:
            # Action làm thua không phải là cạnh hợp lệ trong không gian tìm kiếm.
            continue
        # Trả từng cặp (state mới, action dẫn tới state đó) cho thuật toán search.
        yield successor, action


def is_goal(state: State, model: BloxorzModel) -> bool:
    """True khi block nguyên đứng thẳng đúng ô goal."""
    # Dùng cùng điều kiện thắng với checker và gameplay.
    return model.won(state)


def reconstruct_path(
    parents: Mapping[State, tuple[State | None, str | None]],
    goal_state: State,
) -> list[str]:
    """Lần ngược parent map từ goal về start để trả chuỗi action theo thứ tự đi."""
    # Danh sách tạm được xây theo chiều từ goal về start.
    actions: list[str] = []
    # Bắt đầu truy vết từ state đích mà thuật toán vừa tìm thấy.
    state = goal_state

    # Dừng khi gặp state gốc (có previous là None).
    while True:
        try:
            # Mỗi state lưu state cha và action đã đi từ cha tới nó.
            previous, action = parents[state]
        except KeyError as exc:
            # Parent map thiếu state đích nghĩa là kết quả search không nhất quán.
            raise ValueError("goal_state không có trong parent map") from exc
        if previous is None:
            # Start phải là nút duy nhất không có cha và cũng không có action vào.
            if action is not None:
                raise ValueError("start state phải có parent/action là None")
            break
        if action is None:
            # Mọi state khác start đều phải được tạo bởi chính xác một action.
            raise ValueError("non-start state phải có action dẫn đến nó")
        # Ghi lại action theo chiều ngược và tiếp tục về state cha.
        actions.append(action)
        state = previous

    # Đảo lại để người chơi/solver nhận action theo thứ tự start -> goal.
    actions.reverse()
    return actions
