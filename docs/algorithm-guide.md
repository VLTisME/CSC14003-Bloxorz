# Hướng dẫn triển khai thuật toán

Soạn ngày 16/10/2026; chuyển sang tiếng Việt ngày 17/10/2026; cập nhật trạng thái ngày 24/10/2026. Các thuật toán và runner hiện đã có trong repo. Hướng dẫn dưới đây vẫn mô tả quy trình triển khai theo từng bước; với A*, xem thêm [thiết kế, chứng minh và benchmark](astar-design.md).

<a id="best-practice"></a>

## Cách làm khuyến nghị

Triển khai và kiểm tra thuật toán thuần trước, sau đó mới bổ sung đo lường. Không bắt buộc dùng helper khi kiểm tra tính đúng đắn; chỉ cần đầy đủ số liệu đo khi tạo kết quả benchmark để đưa vào báo cáo.

1. **Tạo file thuật toán riêng.** Viết `algorithms/BFS.py`, `DFS.py`, `UCS.py` hoặc `ASTAR.py`. Có thể sao chép `template.py` rồi tạm bỏ phần bọc đo lường, hoặc bắt đầu từ cấu trúc tối giản bên dưới. Giữ nguyên template dùng chung để các thành viên khác cũng có thể sao chép.
2. **Triển khai tìm kiếm và kiểm tra lời giải.** Đọc một stage từ stdin (luồng nhập chuẩn), tìm danh sách hành động dẫn đến chiến thắng và in JSON chứa `status` cùng `actions`. Giai đoạn này chưa cần số liệu đo hay code ghi file. Bắt đầu với testcase mẫu, sau đó kiểm tra các stage gốc; solver tuyệt đối không đọc lời giải tham chiếu.
3. **Bổ sung theo dõi sau khi lời giải vượt qua kiểm tra.** Giữ logic tìm kiếm, thêm khối `SearchMetrics`, truyền nó vào `solve` và gọi `metrics.expanded()` ngay trước khi sinh các trạng thái kế tiếp của một nút không phải đích. Tạo cấu trúc dữ liệu tìm kiếm và truy vết đường đi bên trong vùng được đo. Thay lệnh in JSON tối giản bằng `metrics.print_solution(actions)`.
4. **Kiểm tra lại tính đúng đắn trước khi benchmark.** Việc đo lường không được làm thay đổi lời giải. Kiểm tra vị trí tăng bộ đếm và ranh giới đo, rồi thu thập kết quả thực tế bằng cùng một quy trình cho tất cả thuật toán. Vượt qua testcase là bằng chứng kiểm thử, không thay thế việc giải thích các giả thiết về tính đầy đủ và tính tối ưu.
5. **Viết báo cáo song song với code.** Mô tả thiết kế thuật toán trong lúc triển khai, quy trình đo khi thêm bộ theo dõi và chỉ ghi kết quả sau khi đã đo thực tế.

Cấu trúc tối giản để bắt đầu với thuật toán thuần:

```python
import json
import sys


def solve(stage):
    # Implement your search and return a list of winning actions.
    raise NotImplementedError


def main():
    stage = json.load(sys.stdin)
    actions = solve(stage)
    print(json.dumps({"status": "solved", "actions": actions}))


if __name__ == "__main__":
    main()
```

Sau khi triển khai `solve`, chạy từ thư mục gốc của repo:

```bash
python algorithms/ASTAR.py < testcases/samples/01.in.json > answer.json
python checker.py --input testcases/samples/01.in.json --output answer.json
python run_tests.py --algorithm algorithms/ASTAR.py --test 01 --require-optimal
```

Shell lưu phần kết quả được in; thuật toán không mở file đầu ra. Checker phát lại kiểm tra đường đi; `run_tests.py` chạy thuật toán, áp dụng timeout, phát verdict và lưu JSON benchmark.

Khi sẵn sàng thêm đo lường, dùng cách tổ chức trong template bên dưới. Đặt file thuật toán cùng thư mục với `solver_support.py` để `from solver_support import SearchMetrics` hoạt động khi chạy `python algorithms/BFS.py`. Helper không cung cấp luật di chuyển, thuật toán tìm kiếm hay bằng chứng rằng lời giải sẽ thắng.

## Bắt đầu từ template

Sao chép `algorithms/template.py` thành file thuật toán trong cùng thư mục (BFS.py, DFS.py, UCS.py hoặc ASTAR.py). Giữ `solver_support.py` bên cạnh và triển khai `solve(stage, metrics)`. Template chủ động phát sinh `NotImplementedError` cho đến khi được thay bằng logic tìm kiếm thật; đây không phải solver mẫu đã hoạt động.

Phần chạy chính của template đã có cấu trúc:

```python
stage = json.load(sys.stdin)
with SearchMetrics() as metrics:
    actions = solve(stage, metrics)
metrics.print_solution(actions)
```

`solve` có thể dùng bất kỳ cấu trúc dữ liệu nội bộ nào. Hàm trả về một danh sách như `["R", "R"]`; không trả về chuỗi JSON và không đọc lời giải tham chiếu. Helper in một đối tượng JSON chứa trạng thái, hành động và số liệu đo. Thuật toán không cần mở file đầu ra.

## Đếm số nút mở rộng nhất quán

Trong vòng lặp tìm kiếm, bỏ qua các phần tử lỗi thời hoặc trùng lặp mà bạn không định mở rộng, sau đó kiểm tra đích. Nếu nút chưa phải đích và bạn chuẩn bị sinh các trạng thái kế tiếp, gọi:

```python
metrics.expanded()
```

Đếm một lần cho nút cha, không đếm một lần cho mỗi trạng thái kế tiếp hay mỗi nước đi hợp lệ. Nếu thực sự mở rộng lại một nút, hãy đếm thêm lần đó. Với DFS giới hạn độ sâu, nút bị cắt tại giới hạn mà không sinh trạng thái kế tiếp không được tính là đã mở rộng. Với A*, tính lại một trạng thái được mở lại nếu bạn thực sự mở rộng nó lần nữa.

Helper không thể tự suy ra sự kiện này từ code solver bất kỳ. Khi so sánh thuật toán, cần cùng rà soát vị trí tăng bộ đếm.

## Ranh giới đo lường

Phân tích JSON đầu vào trước khi vào khối đo. Tạo trạng thái tìm kiếm ban đầu, frontier (tập trạng thái chờ mở rộng), cấu trúc phát hiện trùng lặp và bảng heuristic bên trong `solve`. Truy vết danh sách hành động cuối cùng trước khi trả về để công việc này được tính vào số liệu đo. Chỉ in kết quả sau khi thoát khỏi khối đo. Không tạo sẵn các cấu trúc tìm kiếm ở phạm vi toàn cục trước khi đo.

Theo mặc định, helper đo thời gian trôi qua và theo dõi đỉnh cấp phát bộ nhớ Python. Số liệu bao gồm chi phí theo dõi bộ nhớ và một phần chi phí nhỏ của helper; không bao gồm toàn bộ bộ nhớ tiến trình hay các cấp phát đầu vào đã tồn tại trước đó. Không tự bật/tắt theo dõi bộ nhớ trong solver hoặc lồng các khối đo. Mỗi lần giải cần một đối tượng helper mới.

Với thí nghiệm chỉ đo thời gian được ghi nhãn riêng, `SearchMetrics(track_memory=False)` tắt theo dõi cấp phát và trả về các trường bộ nhớ là null. Kết quả này không thay thế đầy đủ đầu ra benchmark mặc định. Nếu đo theo cặp, giữ cả bản ghi đo thời gian và bản ghi đo bộ nhớ; xem [đặc tả đo lường](runner-proposal.md#where-measurements-come-from).

## Kiểm tra thuật toán đã triển khai bằng công cụ hiện có

Sau khi triển khai thuật toán, chạy từ thư mục gốc của repo:

```bash
python algorithms/BFS.py < testcases/samples/01.in.json > answer.json
python checker.py --input testcases/samples/01.in.json --output answer.json
```

Shell lưu JSON được in vào `answer.json`; thuật toán không tự tạo file này. Checker phát lại chấm đường đi; checker/runner có cờ `--algorithm` để chạy chương trình, áp timeout và báo verdict. Dùng `--require-optimal` với BFS/UCS/A* để kiểm tra độ dài lời giải theo testcase.

Không in thông báo tiến độ ra stdout (luồng xuất chuẩn). Để debug, dùng `print("Searching...", file=sys.stderr)` sau khi nhập `sys`; stderr là luồng lỗi chuẩn. Không nuốt ngoại lệ để checker chạy bài nộp sau này có thể báo RE thay vì nhận một lời giải thành công giả.

## Tính đầy đủ của số liệu benchmark và cập nhật báo cáo

Lời giải đúng có thể nhận AC mà không có số liệu đo, nhưng bản ghi benchmark phải có đầy đủ các trường đã thống nhất. Hàm `metrics_issues(metrics_object)` được cung cấp để runner sau này phát hiện trường thiếu hoặc không hợp lệ, tách biệt với AC/WA. Helper kiểm tra định dạng mã hành động khi in; chỉ phát lại mới xác định được đường đi có thắng hay không.

Sau khi triển khai thuật toán, cập nhật phần tương ứng trong báo cáo: ý tưởng, mã giả, cấu trúc dữ liệu, xử lý trạng thái trùng lặp, giả thiết về tính đầy đủ/tối ưu và độ phức tạp. Ghi rõ vị trí đếm mở rộng và nội dung đo trong phương pháp thực nghiệm. Chỉ thêm kết quả sau các lần chạy thật; các bài kiểm thử helper không phải kết quả benchmark thuật toán.
