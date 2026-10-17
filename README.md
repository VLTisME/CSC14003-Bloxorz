# CSC14003 Bloxorz Solver

Đặc tả giai đoạn 1, bộ testcase đã kiểm chứng và helper đo lường — bản tiếng Việt ngày 17/10/2026.

Bắt đầu với [phát biểu bài toán](docs/problem-statement.md), [hướng dẫn testcase](testcases/README.md) và [đặc tả runner/checker](docs/runner-proposal.md). Xem [các mốc tiến độ](docs/milestones.md) để theo dõi công việc và [nguồn dữ liệu stage](docs/stage-sources.md) để biết nguồn gốc dữ liệu.

## Những phần đã có

- Đặc tả dữ liệu vào/đầu ra JSON, hình minh họa chuyển động và các ví dụ có giải thích.
- 33 stage (màn chơi) gốc với lời giải tham chiếu đã kiểm chứng bằng phát lại, cùng sáu testcase (ca kiểm thử) mẫu có lời giải.
- Checker đơn giản kiểm tra bằng cách phát lại hành động, có thông báo lỗi và tổng số testcase vượt qua.
- Helper đo lường/in JSON dùng chung và template thuật toán có thể sao chép; xem [hướng dẫn triển khai thuật toán](docs/algorithm-guide.md).

```bash
python checker.py --all
python checker.py --input testcases/original/01.in.json --output answer.json
python -m unittest discover -s tests -v
```

Yêu cầu Python 3.10 trở lên; checker và helper chỉ dùng thư viện chuẩn. Lệnh `checker.py --all` hiện tại kiểm tra các lời giải tham chiếu đã lưu, không chạy một bài nộp thuật toán.

## Quy trình giai đoạn 1

Mỗi thuật toán là một chương trình Python độc lập. Chương trình đọc một stage JSON từ stdin (luồng nhập chuẩn) và in một kết quả JSON ra stdout (luồng xuất chuẩn). Người viết tự chọn cấu trúc dữ liệu nội bộ. Checker phát lại các hành động; runner sẽ gọi thuật toán và lưu một file JSON tổng hợp cho mỗi lần chạy. Game engine và phần hiển thị 2D trên terminal được triển khai trước GUI 3D cuối cùng.

Các lệnh dự kiến, chỉ dùng sau khi chương trình tương ứng được triển khai:

```bash
python algorithms/BFS.py < testcases/original/01.in.json > answer.json
python checker.py --algorithm algorithms/BFS.py --all --timeout 10
python run_tests.py --algorithm algorithms/DFS.py --all
python run_tests.py --algorithm algorithms/BFS.py --test 06 --visualize_2d
```

## Cấu trúc repo

```text
docs/
  problem-statement.md
  runner-proposal.md
  algorithm-guide.md
  milestones.md
  stage-sources.md
  assets/Bloxorz.gif
checker.py                  # implemented replay checker
tests/test_checker.py       # checker regression checks
tests/test_solver_support.py # helper and output regression checks
testcases/
  README.md
  manifest.json             # provenance, reference lengths, verification
  samples/                  # six .in.json / .out.json pairs
  original/                 # 33 .in.json / .out.json pairs
algorithms/
  solver_support.py         # implemented measurement/JSON helper
  template.py               # scaffold; solve() must be implemented
                            # planned: BFS.py, DFS.py, UCS.py, ASTAR.py
game/                       # planned: engine.py, visualize_2d.py, later gui/
run_tests.py                # planned batch runner
results/                    # generated datetime.json files; ignored by Git
```

Trong sơ đồ trên, `implemented` là phần đã triển khai, `planned` là phần dự kiến; `template.py` mới là khung code, chưa có thuật toán tìm kiếm. Giữ nguyên tên file và đường dẫn khi sử dụng.

Báo cáo được chỉnh sửa trên Prism trước. Bản nháp báo cáo cục bộ không nằm trong gói đưa lên GitHub. Phân công thành viên và phần trăm hoàn thành chỉ ghi trong báo cáo. Các mốc tiến độ được theo dõi tại đây và sau đó đồng bộ vào báo cáo.

Mỗi công việc triển khai đều phải có phần giải thích và bằng chứng kiểm chứng tương ứng trong báo cáo. Chưa đưa phân công nhiệm vụ lên GitHub.

Bài nộp phục vụ benchmark (đánh giá hiệu năng trên bộ thử nghiệm thống nhất) phải in kèm thời gian tìm kiếm, số nút được mở rộng và đỉnh cấp phát bộ nhớ Python được theo dõi trong JSON. Bài nộp chỉ kiểm tra tính đúng đắn và các lời giải tham chiếu có thể không có số liệu đo. Helper không triển khai thuật toán tìm kiếm; checker có khả năng chạy bài nộp, runner và phần hiển thị vẫn là công việc cần làm.

## Ghi nhận nguồn

Dữ liệu mã hóa stage và chuỗi hành động tham chiếu được chuyển đổi từ [tkoz0/bloxorz-solver](https://github.com/tkoz0/bloxorz-solver). Game gốc do Damien Clarke tạo ra. Phiên bản repo nguồn đã kiểm tra không nêu giấy phép; xem ghi chú nguồn để biết commit cụ thể, thông tin ghi nhận tác giả và bản sửa lời giải stage 15. GIF minh họa chuyển động do chủ dự án cung cấp; chưa xác định tác giả gốc và giấy phép của GIF trong tài liệu này.
