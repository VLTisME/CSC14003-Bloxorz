# Quy trình thực nghiệm BFS/DFS/UCS/A*

## Bộ dữ liệu và mục tiêu

Batch công bố: [28/10/2026](2026-10-28-weighted-ucs/README.md), 33 original × 4 thuật toán × 5 lượt = 660 lượt. Sáu sample kiểm tra riêng, không gộp vào thống kê. Không trộn kết quả batch khác vào bảng này.

BFS/A* đối chiếu số action tham chiếu bằng `--require-optimal`; DFS chỉ yêu cầu lời giải thắng hợp lệ. UCS tối ưu weighted cost nên không áp cờ đối chiếu số bước. Công thức là `1 + 1×chạm B + 2×chạm F + 3×kích hoạt tách`, mỗi chỉ báo 0/1; xem [quy tắc đầy đủ](../algorithms/ucs-design.md).

## Chạy lại từ thư mục gốc

```bash
python -m unittest discover -s tests -v
python tools/validate_solvers.py
python tools/benchmark.py --algorithms BFS DFS UCS ASTAR --suite original --repeats 5 --timeout 60 --seed 20261028 --output results/benchmark-new
```

Thư mục output phải chưa tồn tại. Nếu bỏ `--output`, công cụ tạo thư mục có thời điểm trong `results/`. Log/đầu ra mới là dữ liệu cục bộ, không ghi đè số liệu công bố.

1. Dùng cùng máy, phiên bản solver và dữ liệu cho bốn thuật toán; đóng game/tác vụ nặng, ghi cấu hình môi trường.
2. Warmup một lượt sample01/solver trong tiến trình riêng, loại khỏi thống kê.
3. Chạy tuần tự năm vòng, mỗi vòng xáo trộn cặp thuật toán–stage với seed 20261028. Mỗi lượt dùng tiến trình Python mới, timeout 60 giây; không tái dùng bảng heuristic.
4. Sau khi solver kết thúc, checker replay để chấm lời giải. Công cụ benchmark tính lại weighted cost của cả bốn đường đi, đối chiếu cost UCS tự báo cáo. Công việc đánh giá này nằm ngoài thời gian/bộ nhớ search.
5. Theo từng cặp thuật toán–stage, tổng hợp median/IQR qua năm lượt AC đủ metrics. IQR = Q3−Q1 theo nội suy inclusive. Giữ riêng WA/RE/TLE, metrics thiếu và lỗi xác minh cost; không thay lỗi bằng 0.
6. Nếu thiếu lượt, ghi rõ số thành công/số đủ metrics trên tổng năm lượt. Median của 33 median theo stage chỉ là thống kê tổng quan qua stage, không phải median của 165 lượt gộp.

## Ranh giới đo

- `search_time_ms`: khởi tạo model, heuristic, tìm kiếm, dựng lời giải; không tính parse JSON, in JSON, checker hay GUI. Có overhead tracemalloc giống nhau cho bốn solver.
- `process_time_ms`: thời gian tiến trình, gồm startup và I/O; không đồng nhất với search.
- `peak_memory_bytes`: đỉnh cấp phát Python được tracemalloc theo dõi, không phải RSS. A* gồm cả tiền xử lý; không cộng peak các pha.
- `expanded_nodes`: tăng trước sinh successor của nút không phải đích, bỏ bản ghi lỗi thời trước khi đếm. A* không đếm đồ thị tiền xử lý trong counter này.
- `solution_length`/`cost`: số action. `weighted_cost`: tổng có phụ phí, được tính lại cho mọi đường đi; UCS phải khớp số tự báo cáo.
- AC/replay cost không tự chứng minh tối ưu weighted cost. `tools/validate_solvers.py` có Dijkstra riêng trên luật checker để đối chiếu ngoài benchmark.

## Tệp và công bố

`results/benchmark-new` chứa metadata, runs.jsonl, warmup, summary.csv/json, tables.md và replay lượt đầu. Đây là đầu ra cục bộ được ignore. GitHub chỉ giữ bảng/CSV tổng hợp, metadata cấu hình của batch đã chọn; log và các batch cũ được lưu riêng tại máy.

Batch lịch sử dùng Ryzen 7 8845H, 16 CPU logic, khoảng 27,21 GiB RAM, Python 3.12.3, Linux x86_64 kernel 7.0.0-38. Xem metadata để truy vết source. Chỉ chạy lại thí nghiệm khi thay đổi ảnh hưởng thuật toán hoặc phép đo; dùng thư mục mới và ghi môi trường thật.
