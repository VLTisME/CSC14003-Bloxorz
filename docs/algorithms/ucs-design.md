# UCS với chi phí có phụ phí

## Mục tiêu và quy tắc

UCS tìm đường có tổng chi phí nhỏ nhất. Mỗi chuyển tiếp hợp lệ có chi phí:

`step_cost = 1 + 2 × touches_fragile + touches_bridge + 3 × triggers_split`

Ba chỉ báo nhận giá trị 0/1. Phí cơ bản 1 ưu tiên ít bước; phụ phí F=2 hạn chế
ô có ràng buộc tư thế; B=1 hạn chế mặt sàn phụ thuộc công tắc; tách=3 hạn chế
số lần chuyển sang điều khiển hai khối riêng. Đây là trọng số ưu tiên do nhóm
chọn, không phải chi phí vật lý hay xác suất thua. Game vẫn xác định hoàn toàn.

- Khối nguyên: xét các ô chiếm sau bước đi. Mỗi loại phụ phí tính tối đa một
  lần trong một bước, kể cả khi chạm hai ô cùng loại; F và B cộng dồn.
- Khối đang tách: chỉ xét ô đích của cube vừa di chuyển, không tính phí cube
  đứng yên. Xác định ô này bằng ID trước bước đi và hướng di chuyển để không
  nhầm khi ghép lại làm tọa độ trong state được sắp xếp.
- Bước kích hoạt T: cộng 3 và xét phụ phí F/B tại cả hai điểm đến dịch chuyển.
  Nằm trên T không kích hoạt tách nên không cộng 3. Tự ghép không có phụ phí.
- O, X, sàn thường, S và G không có phụ phí riêng. Nước đi gây thua bị loại,
  không được biến thành cạnh hợp lệ có chi phí cao.

## Tính tối ưu và ví dụ

Heap ưu tiên tổng chi phí đã đi. `best_cost` lưu chi phí tốt nhất tới từng state;
khi tìm được đường rẻ hơn thì cập nhật cả chi phí và cha truy vết. Bản ghi heap
lỗi thời bị bỏ qua. Chỉ kết luận khi lấy đích khỏi heap, không dừng khi vừa sinh
đích. Với đồ thị trạng thái hữu hạn và mỗi cạnh có cost ít nhất 1, UCS tìm được
lời giải có tổng chi phí nhỏ nhất nếu có lời giải. Nó không đảm bảo ít bước nhất.

Màn nhỏ trong kiểm thử (không có cầu, công tắc hay splitter):

```text
SF.F.
.FFFF
F....
.F..G
```

| Solver | Hành động | Số bước | Tổng chi phí theo công thức UCS |
|---|---|---:|---:|
| BFS | D R R R R D | 6 | 16 |
| UCS | D D R R U R D | 7 | 15 |

Phép kiểm chứng độc lập duyệt đồ thị nhỏ rồi dùng Bellman-Ford để đối chiếu
chi phí tối ưu, không gọi hàm tính cost hoặc tìm kiếm của UCS.

## Đầu ra và cách chạy

`solve(stage, metrics)` giữ đầu ra danh sách hành động. `solve_with_cost` trả
`(actions, total_cost)`; tổng cost lấy ngay khi đích được lấy khỏi heap.
CLI giữ `status`, `actions`, các metrics đo lường và thêm `metrics.weighted_cost`.
Helper kiểm tra đây là số nguyên không âm nếu có; checker/runner sao chép sang
`statistics.weighted_cost`. `solution_length` và `cost` cũ vẫn bằng số bước.

```bash
python algorithms/UCS.py < testcases/samples/03.in.json
python run_tests.py --algorithm algorithms/UCS.py --all
python -m unittest discover -s tests -v
```

Không dùng `--require-optimal` cho UCS mới: cờ này chỉ so sánh số bước với
tham chiếu. AC chứng nhận lời giải hợp lệ, không chứng nhận chi phí tối ưu;
`weighted_cost` trong runner là giá trị solver báo cáo. Kiểm thử riêng cộng lại
chi phí theo từng bước và đối chiếu tối ưu trên các đồ thị nhỏ.

BFS, DFS và A* giữ nguyên mục tiêu hiện tại. Khi so sánh tổng chi phí, cần tính
lại lời giải của mọi solver theo cùng công thức trên, đồng thời báo cáo riêng
số bước. Các số đo thời gian/bộ nhớ UCS vẫn bao gồm tính cost và truy vết.

Lượt kiểm chứng UCS trên 33 stage gốc và 6 mẫu được lưu đè vào
`results/ucs-validation.json` sau khi thu thập đủ các ca, gồm cả thất bại nếu có.
File chứa công thức, môi trường, lời giải, số bước, tổng chi phí, metrics và
kết quả đối chiếu tổng chi phí khi phát lại; không yêu cầu bằng độ dài tham chiếu.
Runner thông thường vẫn tạo file theo thời điểm như trước.
