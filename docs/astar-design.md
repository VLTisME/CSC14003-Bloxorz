# Thiết kế A* và lập luận về tính tối ưu

## Trạng thái và mục tiêu

A* dùng `State` bất biến, chuẩn hóa của dự án: khối đang tách hay ghép, tọa độ hai phần (bằng nhau khi đứng thẳng) và trạng thái mở/đóng của từng cầu. Cờ cầu thuộc trạng thái thật vì chúng ảnh hưởng các nước đi hợp lệ tiếp theo. `bloxorz_model.py` dùng chung chịu trách nhiệm đọc stage, sinh trạng thái kế tiếp hợp lệ, xử lý tách/ghép và xác định chính xác trạng thái thắng. Mỗi hành động theo hướng có chi phí 1, nên mục tiêu là tìm lời giải có ít hành động nhất. Chọn khối nhỏ để di chuyển được mã hóa trong token hành động, không tính thành hành động riêng.

## Heuristic trên đồ thị thư giãn

Với mỗi stage, A* tạo một bản thư giãn trong đó ô dễ vỡ, ô cầu và ô công tắc trở thành sàn thường, an toàn. Định nghĩa cầu và công tắc được bỏ đi. Tư thế khối, tọa độ hai khối nhỏ, ô tách và tọa độ đích sau khi tách được giữ nguyên. Vì vậy cơ chế tách, dịch chuyển tới vị trí định trước và ghép vẫn dùng chính hàm chuyển trạng thái của game.

Solver duyệt các trạng thái thư giãn có thể đến từ trạng thái đầu, lưu cạnh ngược rồi chạy BFS ngược từ tất cả trạng thái đích thư giãn có thể đến. Khoảng cách tìm được là `h(s)` chính xác trên đồ thị thư giãn và được tra cứu theo state trong lần giải đó. Nếu state không có trong bảng khoảng cách ngược, ngay cả game thư giãn cũng không thể tới goal; do đó game thật cũng không thể tới goal từ state ấy.

### Tính admissible và consistent

Gọi `P` là phép chiếu từ state thật sang cấu hình giữ nguyên phần tách/ghép, tư thế và tọa độ nhưng quên cờ cầu. Mọi chuyển tiếp thật `s -> s'` có chi phí 1 đều được mô phỏng bởi một chuyển tiếp thư giãn `P(s) -> P(s')` cũng có chi phí 1:

- Nếu một bước thật đáp xuống ô dễ vỡ thì ô đó vẫn được đỡ trong game thư giãn.
- Nếu bước thật đáp xuống cầu thì ô đó được xem là sàn trong game thư giãn, bất kể cờ cầu thật đang bật hay tắt.
- Công tắc chỉ đổi cờ cầu trong game thật; phép chiếu quên các cờ này nên cấu hình vị trí vẫn trùng.
- Quy tắc tách tại splitter, dịch chuyển đến hai tọa độ đã định và ghép khối được giữ nguyên.

Vì vậy, mọi đường đi thật được chiếu thành đường đi thư giãn có cùng độ dài. Khoảng cách ngắn nhất trong đồ thị thư giãn không thể lớn hơn khoảng cách ngắn nhất trong game thật: `h(s) <= d*(s)`. Do đó heuristic admissible. Trên mỗi cạnh thật, bất đẳng thức tam giác của khoảng cách ngắn nhất thư giãn cho `h(s) <= 1 + h(s')`, nên heuristic cũng consistent. Với cạnh dương đơn vị và kiểm tra goal khi lấy state khỏi heap, A* trả lời giải có ít hành động nhất. Cài đặt vẫn cho phép tìm thấy `g` tốt hơn và bỏ entry cũ trong heap; không phụ thuộc vào mẹo đóng state thiếu điều kiện.

`tests/test_astar.py` kiểm tra tính chất mô phỏng trên mọi state/action có thể tới trong sáu stage mẫu. Bộ test cũng tính khoảng cách tối ưu thật trên các stage đó, rồi xác nhận admissibility và consistency cho mọi state/cạnh đã duyệt. Chạy toàn bộ stage gốc đối chiếu độ dài A* với độ dài tham chiếu; benchmark so sánh thêm độc lập với BFS.

## Số liệu

`search_time_ms` và `peak_memory_bytes` chuẩn bao gồm cả tiền xử lý đồ thị thư giãn. Các trường riêng của A* tách thời gian tiền xử lý với thời gian tìm kiếm trên heap, đồng thời ghi số state/cạnh thư giãn, state được sinh và kích thước frontier lớn nhất. Runner chuyển các trường này vào JSON kết quả. Bộ nhớ đỉnh dùng `tracemalloc` của Python, không phải RSS của tiến trình.

Chạy A* trực tiếp: `python algorithms/ASTAR.py < testcases/samples/01.in.json`. Chạy một stage có checker: `python run_tests.py --algorithm algorithms/ASTAR.py --test 01 --require-optimal`. Tạo so sánh BFS/A* cho cả bộ: `python benchmark_search.py --suite original`.

## Phạm vi và giới hạn

Cài đặt này hướng tới các stage được cung cấp trong dự án, vốn đều có lời giải. Chưa bổ sung validator tổng quát cho stage do người dùng tự tạo hay chứng minh vô nghiệm cho mọi map tùy ý. Đồ thị thư giãn được dựng lại ở mỗi lần giải; thời gian và bộ nhớ tiền xử lý được tính vào tổng đã báo cáo. Thời gian benchmark hiện là quan sát một lượt, không nên dùng để khẳng định mức tăng tốc ổn định nếu chưa chạy lặp lại trên máy được mô tả rõ.
