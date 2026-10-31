# CSC14003 — Bloxorz Solver

Đồ án Cơ sở Trí tuệ Nhân tạo: chơi Bloxorz trên giao diện 3D/terminal, giải bằng BFS, DFS, UCS và A*, kiểm tra lời giải và so sánh thực nghiệm.

- [Video demo](https://www.youtube.com/watch?v=HB6mtO96rz0)
- [Báo cáo PDF](https://github.com/VLTisME/CSC14003-Bloxorz/blob/main/Report.pdf)
- [Mã nguồn](https://github.com/VLTisME/CSC14003-Bloxorz)
- [Mục lục tài liệu](docs/README.md)
- [Benchmark bốn thuật toán, 660 lượt](docs/exp/2026-10-28-weighted-ucs/README.md)

## Cài đặt

GUI yêu cầu Python 3.12 trở lên (đã kiểm tra với 3.12.3; Ursina 8.3.0 yêu cầu Python >= 3.12). Chạy lệnh từ thư mục gốc repository hoặc thư mục `Source` trong gói nộp.

```bash
python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python play.py
```

GUI dùng Ursina 8.3.0, Panda3D 1.10.16, Pillow 13.0.0 và cần môi trường đồ họa OpenGL; khuyến nghị tỉ lệ cửa sổ 16:9 để hiển thị đầy đủ HUD. Solver/checker/terminal chỉ cần thư viện chuẩn Python (Python 3.10 trở lên). `.venv` là môi trường cục bộ, không phân phối cùng mã nguồn.

## Chơi và xem lời giải

```bash
python play.py --stage 01
python play.py --suite samples --stage 04
python play.py --stage 01 --terminal
python algorithms/UCS.py < testcases/original/13.in.json > answer.json
python checker.py --input testcases/original/13.in.json --output answer.json
python play.py --stage 13 --replay answer.json
```

GUI chọn trực tiếp A*, BFS, DFS, UCS rồi bấm Giải; lời giải hợp lệ được tự động phát lại. Nút Giải chuyển thành Tạm Dừng/Tiếp Tục khi solver chạy. HUD UCS hiển thị riêng số bước và weighted cost. Cửa sổ benchmark cho phép chạy bốn thuật toán trên cùng màn và chọn Run để phát lời giải.

- WASD/phím mũi tên: di chuyển; Space: đổi cube khi tách.
- Z/U: Undo; R: Reset; Esc: menu tạm dừng.
- Con lăn chuột: zoom; C: khôi phục camera. Bản GUI cuối dùng phép chiếu trực giao.
- Replay: Prev, Play/Pause, Next và tốc độ. Xem thêm [hướng dẫn GUI và demo](docs/prj/report-and-demo-guide.md).

## Chạy và kiểm tra thuật toán

Thay `UCS.py` bằng `BFS.py`, `DFS.py` hoặc `ASTAR.py` để chạy solver tương ứng. Đầu vào là JSON qua stdin; đầu ra là JSON gồm `status`, `actions`, `metrics`.

```bash
python -m unittest discover -s tests -v
python run_tests.py --algorithm algorithms/BFS.py --all --require-optimal
python run_tests.py --algorithm algorithms/ASTAR.py --all --require-optimal
python run_tests.py --algorithm algorithms/DFS.py --all
python run_tests.py --algorithm algorithms/UCS.py --all
python tools/validate_solvers.py
```

`--all` mặc định kiểm tra bộ original; thêm `--suite samples` để chạy sáu mẫu. Công cụ `validate_solvers.py` kiểm tra cả 39 testcase cho bốn solver và đối chiếu UCS với Dijkstra riêng trên mô hình checker.

BFS/A* tối ưu số bước. UCS tối ưu tổng `1 + 1×chạm cầu + 2×chạm ô dễ vỡ + 3×kích hoạt tách` trên từng bước; xem [quy tắc đầy đủ](docs/algorithms/ucs-design.md). DFS không bảo đảm tối ưu. `cost` của checker là số bước; `metrics.weighted_cost` của UCS là tổng cost có phụ phí. **Không dùng `--require-optimal` để chấm UCS mới**, vì cờ này chỉ so số bước tham chiếu. AC xác nhận đường đi hợp lệ, không tự chứng minh tối ưu weighted cost.

## Thực nghiệm

Bộ công bố ngày 28/10 gồm 33 original × 4 solver × 5 lượt = 660 lượt AC. [CSV dùng cho báo cáo](docs/exp/2026-10-28-weighted-ucs/paper-data.csv) và [năm bảng chi tiết](docs/exp/2026-10-28-weighted-ucs/paper-tables.md) giữ nguyên số liệu đã đo.

Chạy bộ mới vào thư mục kết quả cục bộ chưa tồn tại:

```bash
python tools/benchmark.py --algorithms BFS DFS UCS ASTAR --suite original --repeats 5 --timeout 60 --seed 20261028 --output results/benchmark-new
```

Mỗi lượt chạy trong tiến trình mới; báo cáo median/IQR. Thời gian và bộ nhớ A* gồm tiền xử lý heuristic, counter expanded chỉ tính tìm kiếm chính. Peak memory đo bằng tracemalloc, không phải RSS. Chi tiết tại [quy trình thực nghiệm](docs/exp/protocol.md).

Tùy chọn vẽ biểu đồ: cài `python -m pip install -r tools/requirements_plot.txt`, rồi chạy `python tools/plot_benchmark.py results/benchmark-new`. `benchmark_search.py` giữ tương thích với công cụ BFS/A* một lượt cũ, không dùng làm bộ benchmark chính.

## Cấu trúc

```text
algorithms/       BFS, DFS, UCS, A*, mô hình và metrics
checker.py        kiểm tra lời giải; dùng chung với runner
run_tests.py      chạy solver theo bộ testcase
play.py           mở GUI 3D hoặc terminal 2D
requirements.txt  thư viện chạy GUI
game/             engine, GUI, tài nguyên và test giao diện
testcases/        33 màn original + 6 samples, đáp án và manifest
tests/            kiểm thử thuật toán, luật, runner và tích hợp
tools/            benchmark, đối chiếu solver và tạo tài nguyên
docs/             tài liệu và số liệu thực nghiệm tổng hợp
results/          log/đầu ra cục bộ, không được Git theo dõi
```

Log, replay sinh ra khi chạy, `game/progress.json`, cache và môi trường ảo không được đưa lên GitHub. Tiến độ chơi được tạo tự động khi chơi. Báo cáo hoàn thiện được lưu dưới tên `Report.pdf` ở gốc repository; trong gói nộp, `Report.pdf` nằm cùng cấp với thư mục `Source`.

## Nguồn và ghi nhận

Dữ liệu stage/lời giải tham chiếu chuyển đổi từ [tkoz0/bloxorz-solver](https://github.com/tkoz0/bloxorz-solver); game Bloxorz do Damien Clarke tạo ra, được giới thiệu tại [Coolmath Games](https://www.coolmathgames.com/0-bloxorz). Xem [nguồn dữ liệu và điều chỉnh stage15](docs/prj/stage-sources.md). Ghi nhận font và tài nguyên giao diện tại [credits](docs/assets/pixel/CREDITS.md). Không tự gán giấy phép cho dữ liệu/tài nguyên bên ngoài khi nguồn chưa công bố rõ.
