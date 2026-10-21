"""Uniform-Cost Search solver for the Bloxorz project."""

# Các thư viện cần dùng để cài đặt UCS
import heapq
from itertools import count
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
    """Find a minimum-cost path; every directional move costs one."""
    # Khởi tạo luật chơi
    model = parse_stage(stage)
    # Trạng thái xuất phát
    start = initial_state(model)

    # Khởi tạo biến đếm (Mục đích khi heap nó đều có chi phí như nhau thì sẽ dựa vào count để ưu tiên)
    counter = count()
    # Khởi tạo frontier
    frontier = [(0, next(counter), start)]
    # Bảng chi phí tốt nhất đến từng state
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

        # Khi mà lấy state ra rồi nếu nó là Goal thì ta kết luận
        if is_goal(current_state, model):
            # Trả về trạng thái Goal với parents để track ngược lại
            return reconstruct_path(parents, current_state)

        # Nếu không thuộc các trường hợp trên thì ta tăng node đã được expanded là + 1
        metrics.expanded()

        # Sinh từng trạng thái kế tiếp và hành động hợp lệ
        for successor_state, action in next_states(current_state, model):
            # Nếu có thì ta có new_cost = cost hiện tại + 1
            new_cost = current_cost + 1
            # Bỏ qua nếu đã tìm được đường đến state này với chi phí không lớn hơn
            if successor_state in best_cost and new_cost >= best_cost[successor_state]:
                continue

            # Cập nhật chi phí tốt nhất và đường truy vết tới trạng thái kế tiếp
            best_cost[successor_state] = new_cost
            parents[successor_state] = (current_state, action)
            heapq.heappush(frontier, (new_cost, next(counter), successor_state))

    raise RuntimeError("No solution found, although every supplied stage should be solvable.")


def main() -> None:
    """Read one stage from stdin and print solution JSON with metrics."""
    stage = json.load(sys.stdin)
    with SearchMetrics() as metrics:
        actions = solve(stage, metrics)
    metrics.print_solution(actions)


if __name__ == "__main__":
    main()
