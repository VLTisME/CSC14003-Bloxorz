"""BFS solver for the Bloxorz project."""

# Hàng đợi hai đầu dùng để cài đặt BFS
from collections import deque
import json
import sys

# Các hàm mô hình trò chơi và hỗ trợ truy vết
from bloxorz_model import (
    State,
    initial_state,  # Lấy trạng thái xuất phát
    is_goal,  # Kiểm tra xem có phải đích không
    next_states,  # Sinh trạng thái kế tiếp và hành động hợp lệ
    parse_stage,  # Kiểm tra dữ liệu và tạo mô hình bàn chơi
    reconstruct_path,  # Truy vết đường đi từ bảng parents
)

# Công cụ dùng để đo thời gian, bộ nhớ và số nút mở rộng
from solver_support import SearchMetrics


# Nhận vào dữ liệu màn chơi "Stage"
# Và object dùng để đo hiệu năng
# Trả về một loạt chuỗi hành động
def solve(stage: dict, metrics: SearchMetrics) -> list[str]:
    """Find a shortest valid action sequence for one Bloxorz stage."""
    # Khởi tạo luật chơi
    model = parse_stage(stage)
    # Trạng thái xuất phát
    start = initial_state(model)

    # Khởi tạo frontier theo kiểu hàng đợi FIFO: state vào trước được xét trước
    frontier = deque([start])
    # Lưu các state đã gặp để không duyệt lại cùng một trạng thái
    visited = {start}
    # Parents dùng để truy vết lại các nước đi
    parents: dict[State, tuple[State | None, str | None]] = {start: (None, None)}

    # Lặp đến khi frontier rỗng
    while frontier:
        # Lấy và xoá state ở đầu hàng đợi
        current_state = frontier.popleft()

        # Khi lấy state ra, nếu nó là Goal thì kết luận và truy vết đường đi
        if is_goal(current_state, model):
            return reconstruct_path(parents, current_state)

        # State hiện tại đã được mở rộng
        metrics.expanded()

        # Sinh từng trạng thái kế tiếp và hành động hợp lệ
        for successor_state, action in next_states(current_state, model):
            # Bỏ qua state đã được thăm để tránh lặp và giữ đường đi ngắn nhất
            if successor_state in visited:
                continue

            # Đánh dấu đã thăm ngay khi thêm vào frontier
            visited.add(successor_state)
            # Lưu state cha và hành động để truy vết khi tìm thấy Goal
            parents[successor_state] = (current_state, action)
            # Thêm vào cuối hàng đợi để duyệt theo từng mức độ sâu
            frontier.append(successor_state)

    raise RuntimeError("No solution found, although every supplied stage should be solvable.")


def main() -> None:
    """Read one stage from stdin and print one solution JSON object."""
    stage = json.load(sys.stdin)

    with SearchMetrics() as metrics:
        actions = solve(stage, metrics)

    metrics.print_solution(actions)


if __name__ == "__main__":
    main()
