# Thiết kế solver và giao tiếp

Cả bốn thuật toán nhận cùng JSON stage, dùng mô hình trạng thái trong `algorithms/bloxorz_model.py` và trả chuỗi action hợp lệ. Trạng thái gồm cờ tách/ghép, tọa độ hai phần khối và cờ cầu; lịch sử tìm kiếm và cube đang chọn trên GUI không thuộc khóa trạng thái.

| Solver | Frontier | Xử lý lặp | Mục tiêu |
|---|---|---|---|
| BFS | Hàng đợi FIFO | Seen khi thêm vào hàng đợi | Ít action nhất |
| DFS | Stack LIFO | Seen toàn cục khi thêm vào stack | Lời giải hợp lệ |
| UCS | Min-heap theo g | Best cost, bỏ bản ghi lỗi thời | Tổng weighted cost nhỏ nhất |
| A* | Min-heap theo g+h | Best g, bỏ bản ghi lỗi thời | Ít action nhất |

Xem [heuristic A*](astar-design.md) và [hàm cost UCS](ucs-design.md). Các chặn và bảo đảm lý thuyết phải xét đúng mục tiêu của từng solver; UCS mới không tương đương BFS.

## API và JSON

- `solve(stage, metrics)` trả danh sách action; GUI và CLI cùng dùng thuật toán này.
- UCS có `solve_with_cost(stage, metrics)` trả `(actions, total_cost)`; GUI nhận total_cost để hiển thị và CLI xuất `metrics.weighted_cost`.
- A* có `solve_with_breakdown(stage, metrics)` trả `(actions, details)`, gồm thời gian tiền xử lý/tìm kiếm và kích thước đồ thị thư giãn.
- CLI đọc stdin, in đúng một JSON kết quả; thông báo chẩn đoán đi ra stderr. Solver không đọc đáp án tham chiếu.
- `cost` và `solution_length` của checker/runner là số action. `weighted_cost` là tổng theo công thức UCS và phải được hiểu riêng.

## Phép đo

Dùng một `SearchMetrics` mới cho mỗi lần giải. Phân tích JSON trước khối đo; khởi tạo model/frontier, heuristic, tìm kiếm và dựng lời giải trong khối đo; in kết quả sau khi thoát.

Gọi `metrics.expanded()` sau khi bỏ bản ghi lỗi thời và kiểm tra goal, ngay trước khi sinh successor cho nút không phải đích. Counter A* không tính tiền xử lý, nhưng thời gian và bộ nhớ tổng có tính pha này. `tracemalloc` đo đỉnh cấp phát Python, không phải RSS. GUI tắt đo bộ nhớ; không dùng số liệu GUI thay batch thực nghiệm.

## Kiểm tra

```bash
python -m unittest discover -s tests -v
python run_tests.py --algorithm algorithms/BFS.py --all --require-optimal
python run_tests.py --algorithm algorithms/ASTAR.py --all --require-optimal
python run_tests.py --algorithm algorithms/DFS.py --all
python run_tests.py --algorithm algorithms/UCS.py --all
python tools/validate_solvers.py
```

Thêm `--suite samples` để chạy bộ mẫu. AC xác nhận lời giải hợp lệ; metrics đầy đủ được kiểm tra riêng. `--require-optimal` chỉ đối chiếu số bước, nên không áp dụng cho UCS mới. Đối chiếu weighted cost riêng không nằm trong vùng đo benchmark.
