"""Uniform-Cost Search solver for the Bloxorz project."""

# Các thư viện cần dùng để cài đặt UCS
import heapq
from itertools import count
import json
import sys

# Các hàm mô hình trò chơi và hỗ trợ truy vết
from bloxorz_model import (
    BloxorzModel,
    State,
    initial_state,  # Lấy trạng thái xuất phát
    is_goal,  # Kiểm tra xem có phải đích không
    next_states,  # Sinh trạng thái kế tiếp và hành động hợp lệ
    parse_stage,  # Kiểm tra dữ liệu và tạo mô hình bàn chơi
    reconstruct_path,  # Truy vết đường đi từ bảng parents
)

# Công cụ dùng để đo thời gian, bộ nhớ và số nút mở rộng
from solver_support import SearchMetrics

# Chi phí cơ bản cho mỗi hành động di chuyển hợp lệ (move cost).
MOVE_COST = 1

# Phụ phí khi phần khối vừa di chuyển đáp lên ô cầu B (bridge penalty).
# Cộng 1 tối đa một lần trong một bước, có thể cộng cùng phụ phí F.
BRIDGE_PENALTY = 1

# Phụ phí khi phần khối vừa di chuyển đáp lên ô dễ vỡ F (fragile penalty).
# Cộng 2 tối đa một lần trong một bước, kể cả khi đáp lên hai ô F.
FRAGILE_PENALTY = 2

# Phụ phí khi thực sự kích hoạt tách khối tại T (split penalty).
# Cộng 3 cho mỗi lần kích hoạt tách; nằm trên T hoặc đi khi đã tách không cộng phí này.
SPLIT_PENALTY = 3

# Độ thay đổi tọa độ (delta_row, delta_column) khi đi một ô theo từng hướng:
# U (Up): hàng -1; D (Down): hàng +1; L (Left): cột -1; R (Right): cột +1.
# Dùng để tính ô đích của cube đang di chuyển: (hàng + delta_row, cột + delta_column).
# Từ ô đích đó, action_cost kiểm tra F/B để cộng phụ phí cho đúng cube.
# Bảng này chỉ phục vụ tính cost; di chuyển thực tế và lăn khối nguyên do Replay xử lý.
DIRECTION_OFFSETS = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}


def action_cost(state: State, action: str, successor: State, model: BloxorzModel) -> int:
    """Tính cost của một chuyển tiếp hợp lệ: 1 + 1*B + 2*F + 3*T.

    F/B là chỉ báo có chạm loại ô đó, không phải số ô cùng loại chạm vào.
    T là chỉ báo thực sự kích hoạt tách khối, không phải chỉ chạm ô T.
    Các phụ phí cộng dồn, thể hiện ưu tiên hạn chế ô có điều kiện và thao tác
    tách khối; đây không phải xác suất thua trong game xác định hoàn toàn.
    Hàm chỉ nhận chuyển tiếp hợp lệ đã được next_states kiểm tra.
    """
    if state.split:
        # Chỉ tính ô đích của cube vừa di chuyển, không phạt cube đứng yên.
        # Không lấy trực tiếp successor.first/second: khi hai cube vừa ghép,
        # Replay sắp xếp lại tọa độ nên successor.first chưa chắc là cube 1 cũ.
        # Dùng vị trí trước bước đi + hướng đi để không tính nhầm phí cube đứng yên.
        origin = state.first if action[0] == "1" else state.second
        # Ví dụ cube 1 ở (2, 4), action = "1L": action[-1] là "L",
        # tra bảng được (dr, dc) = (0, -1), tức giữ hàng và giảm cột 1.
        dr, dc = DIRECTION_OFFSETS[action[-1]]
        # Ô đích là (2 + 0, 4 - 1) = (2, 3). Nếu ô này là sàn thường thì
        # cost = 1; là F thì cost = 1 + 2 = 3; là B thì cost = 1 + 1 = 2.
        landed = {(origin[0] + dr, origin[1] + dc)}
    else:
        # Khối nguyên: xét cả hai ô chiếm sau bước đi. Nếu vừa tách, đây là
        # hai điểm đến dịch chuyển; phụ phí F/B ở đó vẫn được tính.
        landed = {successor.first, successor.second}

    tile_types = {model.cells[cell] for cell in landed}
    # Điểm đến splitter không kề nhau nên bước kích hoạt luôn đổi False -> True.
    # Nằm trên T không đổi cờ split, do đó không có phụ phí tách.
    triggers_split = not state.split and successor.split
    return (
        MOVE_COST
        + FRAGILE_PENALTY * ("F" in tile_types)
        + BRIDGE_PENALTY * ("B" in tile_types)
        + SPLIT_PENALTY * triggers_split
    )


def solve_with_cost(stage: dict, metrics: SearchMetrics) -> tuple[list[str], int]:
    """Trả lời giải và tổng chi phí nhỏ nhất, không nhất thiết ít bước nhất."""
    # Khởi tạo luật chơi
    model = parse_stage(stage)
    # Trạng thái xuất phát
    start = initial_state(model)

    # Khi bằng cost, ưu tiên bản ghi thêm trước; không so sánh trực tiếp State.
    counter = count()
    # Khởi tạo frontier
    frontier = [(0, next(counter), start)]
    # Tổng chi phí tốt nhất đến từng state, không phải số bước đã đi.
    best_cost = {start: 0}
    # Parents dùng để truy vết lại các nước đi
    parents: dict[State, tuple[State | None, str | None]] = {start: (None, None)}

    # Lặp đến khi frontier rỗng
    while frontier:
        # Lấy và xoá phần tử có cost nhỏ nhất ra khỏi heap
        # current_cost là chi phí của bản ghi đến current_state
        current_cost, _, current_state = heapq.heappop(frontier)

        # Bỏ bản ghi cũ nếu đã tìm được đường rẻ hơn tới cùng trạng thái.
        if current_cost > best_cost[current_state]:
            continue

        # Mọi cạnh có cost >= 1: đích lấy khỏi heap có tổng chi phí tối ưu.
        # Không dừng ngay khi sinh đích vì có thể còn đường rẻ hơn chưa xét.
        if is_goal(current_state, model):
            return reconstruct_path(parents, current_state), current_cost

        # Nếu không thuộc các trường hợp trên thì ta tăng node đã được expanded là + 1
        metrics.expanded()

        # Sinh từng trạng thái kế tiếp và hành động hợp lệ
        for successor_state, action in next_states(current_state, model):
            # Cộng chi phí thật của cạnh, gồm bước di chuyển và các phụ phí.
            new_cost = current_cost + action_cost(current_state, action, successor_state, model)
            # Bỏ qua nếu đã tìm được đường đến state này với chi phí không lớn hơn
            if successor_state in best_cost and new_cost >= best_cost[successor_state]:
                continue

            # Cho phép cải thiện state đã gặp: đường được tìm thấy đầu tiên
            # chưa chắc rẻ nhất khi các hành động có chi phí khác nhau.
            best_cost[successor_state] = new_cost
            parents[successor_state] = (current_state, action)
            heapq.heappush(frontier, (new_cost, next(counter), successor_state))

    raise RuntimeError("No solution found, although every supplied stage should be solvable.")


def solve(stage: dict, metrics: SearchMetrics) -> list[str]:
    """Giữ giao diện trả danh sách hành động cho các nơi gọi solve hiện có."""
    actions, _total_cost = solve_with_cost(stage, metrics)
    return actions


def main() -> None:
    """Đọc stage từ stdin, in lời giải và metrics kèm weighted_cost ra stdout."""
    stage = json.load(sys.stdin)
    with SearchMetrics() as metrics:
        actions, total_cost = solve_with_cost(stage, metrics)
    output_metrics = metrics.as_dict()
    output_metrics["weighted_cost"] = total_cost
    print(json.dumps({"status": "solved", "actions": actions, "metrics": output_metrics}, allow_nan=False))


if __name__ == "__main__":
    main()
