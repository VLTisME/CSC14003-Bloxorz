# CSC14003 Bloxorz Solver

Đặc tả giai đoạn 1, bộ testcase đã kiểm chứng và helper đo lường — bản tiếng Việt ngày 17/10/2026.

Bắt đầu với [phát biểu bài toán](docs/problem-statement.md), [hướng dẫn testcase](testcases/README.md) và [đặc tả runner/checker](docs/runner-proposal.md). Xem [các mốc tiến độ](docs/milestones.md) để theo dõi công việc và [nguồn dữ liệu stage](docs/stage-sources.md) để biết nguồn gốc dữ liệu.

## Những phần đã có

- Đặc tả dữ liệu vào/đầu ra JSON, hình minh họa chuyển động và các ví dụ có giải thích.
- 33 stage (màn chơi) gốc với lời giải tham chiếu đã kiểm chứng bằng phát lại, cùng sáu testcase (ca kiểm thử) mẫu có lời giải.
- Checker đơn giản kiểm tra bằng cách phát lại hành động, có thông báo lỗi và tổng số testcase vượt qua.
- Helper đo lường/in JSON dùng chung và template thuật toán có thể sao chép; xem [hướng dẫn triển khai thuật toán](docs/algorithm-guide.md).
- BFS, DFS, UCS và A* chạy độc lập; runner kiểm tra và lưu số liệu, còn A* có heuristic relaxed-graph đã kiểm thử tính tối ưu.
- Engine trò chơi, hiển thị 2D trên terminal và GUI Ursina 3D đã có; GUI có nút Solve A*.

- UCS tối ưu tổng chi phí có trọng số (weighted cost): `weighted_cost = số bước di chuyển + 2 × số bước đáp lên ô dễ vỡ + số bước đáp lên ô cầu + 3 × số lần kích hoạt tách khối`.
- Số bước đáp lên ô dễ vỡ `F` (fragile tile): số hành động mà phần khối vừa di chuyển đáp lên ít nhất một ô `F`; một hành động đáp lên hai ô `F` vẫn chỉ tính một lần.
- Số bước đáp lên ô cầu `B` (bridge tile): số hành động mà phần khối vừa di chuyển đáp lên ít nhất một ô `B`; một hành động đáp lên hai ô `B` vẫn chỉ tính một lần. Nếu một bước đáp lên cả `F` và `B`, hai phụ phí được cộng dồn.
- Số lần kích hoạt tách khối (block splitting): số hành động làm khối nguyên đứng thẳng trên ô tách `T` (splitter), dịch chuyển và tách thành hai khối nhỏ. Nằm trên `T` không được tính; các bước di chuyển sau khi đã tách và việc tự ghép lại (rejoining) không làm tăng số lần tách.
- Khi khối đã tách, chỉ xét ô đích của khối nhỏ vừa di chuyển (moving cube), không tính ô của khối đứng yên (stationary cube). Riêng bước kích hoạt tách, xét phụ phí `F`/`B` tại cả hai điểm đến dịch chuyển (teleport destinations). Xem [thiết kế chi phí UCS](docs/ucs-design.md) để biết đầy đủ quy tắc.
- BFS và A* vẫn tối ưu số bước. Chạy UCS bằng `python run_tests.py --algorithm algorithms/UCS.py --all`, không dùng `--require-optimal`: cờ này yêu cầu số bước bằng độ dài lời giải tham chiếu (reference solution length), không kiểm tra tổng chi phí có trọng số nhỏ nhất.
- `solution_length` (độ dài lời giải) và `cost` cũ vẫn bằng số bước; `statistics.weighted_cost` là tổng chi phí có trọng số UCS báo cáo. AC (Accepted) trong chế độ không bật `--require-optimal` chỉ xác nhận lời giải hợp lệ, không chứng minh chi phí tối ưu.

```bash
python run_tests.py --algorithm algorithms/ASTAR.py --all --require-optimal
python checker.py --input testcases/original/01.in.json --output answer.json
python -m unittest discover -s tests -v
```

Yêu cầu Python 3.10 trở lên; checker và helper chỉ dùng thư viện chuẩn. Cài giao diện 3D bằng `python -m pip install -r game/requirements_ui.txt`.

## Quy trình giai đoạn 1

Mỗi thuật toán là một chương trình Python độc lập. Chương trình đọc một stage JSON từ stdin (luồng nhập chuẩn) và in một kết quả JSON ra stdout (luồng xuất chuẩn). Người viết tự chọn cấu trúc dữ liệu nội bộ. Checker phát lại các hành động; runner sẽ gọi thuật toán và lưu một file JSON tổng hợp cho mỗi lần chạy. Game engine và phần hiển thị 2D trên terminal được triển khai trước GUI 3D cuối cùng.

Các lệnh chạy thuật toán, kiểm tra và mở GUI:

```bash
python algorithms/BFS.py < testcases/original/01.in.json > answer.json
python checker.py --algorithm algorithms/BFS.py --all --timeout 10
python run_tests.py --algorithm algorithms/ASTAR.py --all --require-optimal
python run_tests.py --algorithm algorithms/ASTAR.py --test 06 --visualize_2d
python play.py --stage testcases/original/01.in.json
```

## Cấu trúc repo

```text
docs/
  problem-statement.md
  runner-proposal.md
  algorithm-guide.md
  milestones.md
  stage-sources.md
  astar-design.md
  astar-benchmark.md
  assets/Bloxorz.gif
checker.py                  # implemented replay checker
tests/test_checker.py        # checker regression checks
tests/test_solver_support.py # helper and output regression checks
tests/test_astar.py          # heuristic and A* correctness tests
testcases/
  README.md
  manifest.json             # provenance, reference lengths, verification
  samples/                  # six .in.json / .out.json pairs
  original/                 # 33 .in.json / .out.json pairs
algorithms/
  solver_support.py         # implemented measurement/JSON helper
  template.py               # reusable solver scaffold
  ASTAR.py                  # optimal A* with relaxed-graph heuristic
  astar_heuristic.py        # relaxation, graph build and reverse BFS
  BFS.py, DFS.py, UCS.py    # additional independent solvers
game/                       # rules engine, terminal visualizer and Ursina 3D GUI
run_tests.py                # batch checker/runner and JSON results
benchmark_search.py         # repeatable per-stage BFS/A* CSV and Markdown
results/                    # generated datetime.json files; ignored by Git
```

Xem [lập luận A*](docs/astar-design.md) và [kết quả benchmark](docs/astar-benchmark.md) để biết chi tiết về heuristic và cách tái lập phép đo.

Báo cáo được chỉnh sửa trên Prism trước. Bản nháp báo cáo cục bộ không nằm trong gói đưa lên GitHub. Phân công thành viên và phần trăm hoàn thành chỉ ghi trong báo cáo. Các mốc tiến độ được theo dõi tại đây và sau đó đồng bộ vào báo cáo.

Mỗi công việc triển khai đều phải có phần giải thích và bằng chứng kiểm chứng tương ứng trong báo cáo. Chưa đưa phân công nhiệm vụ lên GitHub.

Kết quả runner lưu verdict, thời gian, số nút mở rộng, bộ nhớ Python và các số liệu riêng của A* trong JSON. Checker chấm đường đi độc lập với việc số liệu benchmark có đầy đủ hay không.

## Ghi nhận nguồn

Dữ liệu mã hóa stage và chuỗi hành động tham chiếu được chuyển đổi từ [tkoz0/bloxorz-solver](https://github.com/tkoz0/bloxorz-solver). Game gốc do Damien Clarke tạo ra. Phiên bản repo nguồn đã kiểm tra không nêu giấy phép; xem ghi chú nguồn để biết commit cụ thể, thông tin ghi nhận tác giả và bản sửa lời giải stage 15. GIF minh họa chuyển động do chủ dự án cung cấp; chưa xác định tác giả gốc và giấy phép của GIF trong tài liệu này.
# Chạy A*

Solver A* đọc JSON của một stage từ stdin và in câu trả lời JSON đã thống nhất:

```bash
python algorithms/ASTAR.py < testcases/samples/01.in.json
python run_tests.py --algorithm algorithms/ASTAR.py --test 01 --require-optimal
python run_tests.py --algorithm algorithms/ASTAR.py --all --require-optimal
```

Checker phát lại từng hành động; `--require-optimal` còn so sánh độ dài lời giải với số bước tham chiếu của testcase. Xem [thiết kế và chứng minh A*](docs/astar-design.md) cùng [kết quả BFS/A*](docs/astar-benchmark.md).
