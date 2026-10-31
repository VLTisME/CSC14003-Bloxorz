# Runner và checker

Đặc tả v1.1 — 16/10/2026; cập nhật trạng thái triển khai ngày 24/10/2026. Checker phát lại, checker chạy bài nộp, runner theo bộ và hiển thị 2D trên terminal đã được triển khai. GUI Ursina 3D cũng có nút chạy A* và phát lại lời giải.

## Quy trình một lần chạy

1. Runner nạp stage được chọn và khởi chạy chương trình thuật toán Python được chọn.
2. Runner gửi JSON của stage qua stdin của chương trình.
3. Thuật toán in JSON kết quả ra stdout. Thuật toán không cần tự tạo file.
4. Runner thu đầu ra, thông báo lỗi, mã thoát và thời gian thực thi.
5. Checker phát lại hành động và trả về AC, WA hoặc RE.
6. Runner in kết quả từng stage và tổng số testcase vượt qua, sau đó ghi một file JSON tổng hợp cho toàn bộ lần chạy.

Thuật toán có thể dùng cách biểu diễn nội bộ tùy ý. Không bắt buộc dùng một lớp solver chung. Thuật toán không được đọc lời giải tham chiếu.

## Các lệnh

Đã sử dụng được:

```bash
python checker.py --input testcases/original/01.in.json --output answer.json
python checker.py --all
```

Lệnh thứ hai phát lại mọi lời giải tham chiếu được cung cấp, bao gồm cả ví dụ mẫu.

Để chạy trực tiếp một thuật toán sau khi đã triển khai:

```bash
python algorithms/DFS.py < testcases/original/01.in.json > answer.json
```

Các lệnh checker chạy bài nộp và runner:

```bash
python checker.py --algorithm algorithms/BFS.py --test 01 --timeout 10
python checker.py --algorithm algorithms/BFS.py --all --timeout 10
python run_tests.py --algorithm algorithms/DFS.py --all
python run_tests.py --algorithm algorithms/BFS.py --test 06 --visualize_2d
python run_tests.py --algorithm algorithms/BFS.py --suite samples --all
```

Bộ mặc định gồm 33 stage gốc; `--test 06` là stage gốc số 6. Muốn chạy ví dụ mẫu phải chọn bộ tương ứng. `--all` chạy mọi stage trong bộ được chọn. Bắt buộc có `--algorithm` và đúng một trong hai cờ `--test` hoặc `--all`. Cả hai công cụ nhận `--suite original|samples` và `--timeout SECONDS`; khi triển khai phải ghi rõ giới hạn thời gian mặc định. Mỗi stage chạy trong một tiến trình thuật toán mới. Giới hạn thời gian áp dụng riêng cho thực thi thuật toán trên từng stage, không gồm kiểm tra lời giải và hoạt ảnh.

Checker chạy bài nộp khởi chạy thuật toán, thu JSON được in, áp dụng giới hạn thời gian và báo AC/WA/RE/TLE từng stage, tổng số theo verdict và các ID stage tương ứng. Runner dùng chung logic thực thi/phát lại, bổ sung thống kê, file kết quả tổng hợp và tùy chọn hiển thị. Không triển khai hai bộ luật chơi hay logic thực thi độc lập cho hai công cụ.

Với một stage, runner hiển thị verdict, hành động trả về, số hành động và thời gian đo. Với toàn bộ bộ thử nghiệm, hiển thị thời gian/số hành động từng stage, tổng thời gian thực thi thuật toán và stage giải thành công nhanh nhất/chậm nhất kèm ID. Hiển thị riêng lỗi và trường hợp hết thời gian. Nếu không có stage nào giải thành công, thống kê stage thành công nhanh nhất/chậm nhất không có giá trị.

`--visualize_2d` chỉ dành cho runner và yêu cầu chọn một stage. GUI 3D có nút `Giải A*`; kết quả được checker phát lại kiểm tra trước khi animation bắt đầu. `checker.py --all` kiểm tra các lời giải tham chiếu đã lưu, còn `checker.py --algorithm ... --all` chạy chương trình thuật toán trên toàn bộ stage.

## Checker đơn giản

Checker kiểm tra sơ bộ cấu trúc đầu vào rồi phát lại danh sách hành động được nộp. Nó không tìm lời giải và không yêu cầu đáp án trùng chuỗi tham chiếu.

- AC: thắng mà không rơi; lời giải hợp lệ dài hơn cũng được chấp nhận.
- WA: thua, dừng trước đích, dùng hành động của loại khối không phù hợp trạng thái, tiếp tục sau khi thắng hoặc báo `unsolvable`/`limit` mà không có lời giải.
- RE: JSON/cấu trúc sai định dạng, mã hành động không được định nghĩa hoặc chương trình thuật toán gặp lỗi.
- TLE: do runner áp dụng, không suy ra từ câu trả lời của thuật toán.

File đầu vào lỗi được ghi là INPUT_ERROR, không được tính là WA của thuật toán. CLI hiện tại thoát với mã 0 nếu mọi lời giải được kiểm tra đều đạt; ngược lại trả về mã khác 0.

Cả 33 stage gốc đều có chuỗi hành động tham chiếu đã kiểm chứng bằng phát lại. Điều này xác nhận bộ được cung cấp có lời giải mà không cần checker chạy tìm kiếm. Stage tự sinh trong tương lai cần bước kiểm tra đầu vào riêng và xác nhận tồn tại lời giải. Checker đường đi hiện tại vẫn có thể kiểm tra lời giải cho chúng.

## Một file kết quả cho mỗi lần chạy

Ghi `results/YYYY-MM-DD_HH-MM-SS-ffffff.json`, dùng giờ Asia/Ho_Chi_Minh. Phần microsecond giúp tránh trùng tên trong trường hợp thông thường; nếu tên đã tồn tại, chọn thời điểm mới thay vì ghi đè.

Cấu trúc minh họa (các con số là ví dụ, không phải số liệu đo):

```json
{
  "run_id": "2026-10-15_20-00-00-123456",
  "started_at": "2026-10-15T20:00:00.123456+07:00",
  "algorithm": "BFS",
  "program": "algorithms/BFS.py",
  "suite": "original",
  "summary": {"total": 1, "passed": 1, "failed": 0},
  "tests": [
    {
      "test_id": "stage01",
      "verdict": "AC",
      "message": "solved with 7 steps",
      "actions": ["R", "D", "D", "R", "R", "D", "R"],
      "statistics": {
        "process_time_ms": 25.0,
        "search_time_ms": null,
        "peak_memory_bytes": null,
        "memory_method": null,
        "expanded_nodes": null,
        "solution_length": 7,
        "cost": 7,
        "reference_length": 7
      },
      "exit_code": 0,
      "stderr": ""
    }
  ]
}
```

Trong các lần chạy thực tế, ghi thêm giới hạn thời gian đã cấu hình và thông tin môi trường liên quan. Với RE, giữ thông báo chẩn đoán và nếu cần, một bản sao stdout thô có giới hạn kích thước. Với WA, giữ các hành động đã thử nhưng đặt solution_length/cost là null vì đó chưa phải lời giải thành công. Không thay đổi lời giải tham chiếu.

Đầu ra console nên dễ đọc, ví dụ sau vẫn giữ nguyên dạng thông báo kỹ thuật:

```text
stage01: AC — solved with 7 steps
R D D R R D R
stage02: WA — actions end before the goal
Passed 1/2 tests
Saved results/2026-10-15_20-00-00-123456.json
```

<a id="where-measurements-come-from"></a>

## Nguồn và cách thu thập số liệu đo

Runner đo thời gian toàn tiến trình từ khi khởi chạy đến khi kết thúc. Thời gian này gồm khởi động, phân tích đầu vào, tìm kiếm và chuyển kết quả thành dữ liệu để in; đặt tên là `process_time_ms`, không gọi là thời gian riêng cho tìm kiếm.

Runner tính `solution_length` và `cost` bằng số bước trong chuỗi hành động được chấp nhận. Với UCS có phụ phí, solver in thêm `metrics.weighted_cost` và runner sao chép sang `statistics.weighted_cost`; trường này phải là số nguyên không âm nếu có. Đây là giá trị solver báo cáo, cần kiểm chứng riêng bằng cộng chi phí từng bước khi phát lại. `--require-optimal` vẫn chỉ đối chiếu số bước tham chiếu, không dùng để đánh giá UCS mới. Xem [thiết kế UCS](ucs-design.md).

Runner không thể suy ra số nút mở rộng hay thời gian riêng cho tìm kiếm từ các hành động. Vì vậy, chương trình thuật toán in thêm đối tượng `metrics`:

```json
{
  "status": "solved",
  "actions": ["R", "R"],
  "metrics": {
    "search_time_ms": 0.42,
    "peak_memory_bytes": 12345,
    "memory_method": "tracemalloc",
    "expanded_nodes": 2
  }
}
```

Các con số chỉ minh họa trường dữ liệu. Các trường đầu ra benchmark cũng được mô tả trong phát biểu bài toán. Lời giải tham chiếu cố định và bài nộp chỉ kiểm tra tính đúng đắn có thể bỏ số liệu đo; bài nộp benchmark thực tế phải có. Không cần chuyển đổi các testcase hiện có.

Dùng [solver_support.py](../algorithms/solver_support.py) và [template](../algorithms/template.py); xem [hướng dẫn thuật toán](algorithm-guide.md) để tích hợp. `SearchMetrics` đo một lần giải và in đối tượng kết hợp lời giải/số liệu đo. Nó không chứa thuật toán tìm kiếm và không phụ thuộc checker game. Người triển khai phải đếm mở rộng đúng chỗ và đặt toàn bộ khởi tạo tìm kiếm trong vùng được đo.

Đối với runner sau này, `metrics_issues(answer.get("metrics"))` trả về danh sách lỗi số liệu thiếu/không hợp lệ. Ghi chúng tách biệt với verdict phát lại, ví dụ bằng `metrics_complete` và `metrics_errors` trong kết quả từng testcase. Một đường đi thắng dù thiếu số liệu vẫn là AC, nhưng không tạo được bản ghi benchmark đầy đủ. Kiểm tra thời gian hữu hạn không âm, số lượng/byte là số nguyên không âm (không phải boolean) và phương pháp đo bộ nhớ đã thống nhất. Kiểm tra cấu trúc không chứng minh solver đếm đúng hay đặt ranh giới đo đúng; cần rà soát cách gắn bộ đo của từng thuật toán.

Khi chương trình gặp lỗi hoặc hết thời gian, giữ thời gian đo từ bên ngoài và verdict. Số liệu nội bộ không có phải là null, không phải 0; không suy ra từ đầu ra chưa hoàn chỉnh hay thay bằng giá trị trong lời giải tham chiếu.

Dùng các định nghĩa nhất quán:

- Thời gian tìm kiếm gồm khởi tạo frontier, tiền xử lý heuristic cho lần giải đó, tìm kiếm và truy vết đường đi. Không gồm phân tích đầu vào, in, chấm kết quả và hoạt ảnh.
- Một lần mở rộng là khi sinh các trạng thái kế tiếp của nút không phải đích. Bỏ qua phần tử hàng đợi lỗi thời mà không đếm. Các lần thực sự mở rộng lại được đếm thêm.
- Phương pháp cơ sở dùng chung là đỉnh cấp phát Python được theo dõi bằng `tracemalloc`, bắt đầu sau khi phân tích JSON và trước khi tạo trạng thái tìm kiếm/frontier/heuristic. Bao gồm các cấp phát trong code Python đang được đo và chi phí helper, nhưng không gồm cấp phát đã có trước đó và không phải toàn bộ bộ nhớ thường trú của tiến trình. Nếu bổ sung RSS tiến trình sau này, ghi riêng cùng phương pháp đo; không trộn với đỉnh cấp phát được theo dõi.
- Giá trị chưa biết là null, không tự điền 0.
- So sánh với độ dài tối thiểu thuộc phần phân tích, không phải tiêu chí AC/WA. Độ dài tham chiếu đã công bố không tự động là bằng chứng độc lập về tính tối ưu.

Mặc định, `SearchMetrics()` đo thời gian và bộ nhớ cùng lúc. `search_time_ms` khi đó gồm chi phí theo dõi bộ nhớ. Dùng cùng phương pháp cơ sở cho cả bốn thuật toán; không so sánh thời gian có theo dõi với thời gian không theo dõi mà không ghi rõ khác biệt.

Trong thực nghiệm cuối cùng, ưu tiên tách lần đo thời gian và lần đo bộ nhớ. `SearchMetrics(track_memory=False)` hỗ trợ đo thời gian không theo dõi cấp phát: các trường bộ nhớ là null, nên bản ghi riêng lẻ này cố ý chưa đủ cho benchmark đầy đủ. Ghép với một lần đo bộ nhớ mặc định được định danh riêng, dùng cùng stage, phiên bản thuật toán, cấu hình và thứ tự sinh trạng thái kế tiếp; giữ cả hai bản ghi thô và ghi chế độ đo trong cấu hình thực nghiệm. Template mặc định đo đầy đủ; runner hỗ trợ chạy theo cặp là công việc tương lai. Với tìm kiếm rất ngắn, chạy lặp lại và mô tả cách tổng hợp số liệu.

## Hiển thị trên terminal

`--visualize_2d` phát lại hành động trả về sau khi tìm kiếm và chấm kết quả. Hiển thị bàn chơi, ID cả hai khối khi đang tách, trạng thái cầu, số bước và kết quả. Hiển thị terminal đủ cho giai đoạn 1; sản phẩm cuối vẫn cần GUI 3D và phát lại tự động theo yêu cầu.

## Tiến độ báo cáo

Triển khai runner/checker đóng góp vào phần thiết kế hệ thống và phương pháp thực nghiệm. Số liệu đã lưu phục vụ phần kết quả/thảo luận. Ghi rõ giả thiết bộ stage hiện có đã biết là giải được và việc kiểm tra stage tự sinh trong tương lai vào báo cáo chỉnh sửa trên Prism.
