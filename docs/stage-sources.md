# Nguồn dữ liệu stage và kiểm chứng

Soạn ngày 15/10/2026; chuyển sang tiếng Việt ngày 17/10/2026.

## Bộ dữ liệu sử dụng

33 stage gốc được chuyển đổi từ [repo tkoz0/bloxorz-solver](https://github.com/tkoz0/bloxorz-solver) do người dùng cung cấp, tại commit **d203a25170085054fb3f39bd81b3509ee8cd9e47**.

- [coolmath.json](https://github.com/tkoz0/bloxorz-solver/blob/d203a25170085054fb3f39bd81b3509ee8cd9e47/coolmath.json): bố cục bàn chơi, xuất phát/đích, nhóm cầu, tác dụng công tắc và điểm đến dịch chuyển.
- [solution.txt](https://github.com/tkoz0/bloxorz-solver/blob/d203a25170085054fb3f39bd81b3509ee8cd9e47/solution.txt): chuỗi phím tham chiếu đã công bố và độ dài được tác giả tuyên bố là tối thiểu.
- [solver.py](https://github.com/tkoz0/bloxorz-solver/blob/d203a25170085054fb3f39bd81b3509ee8cd9e47/solver.py): tham khảo để hiểu tọa độ nguồn, trạng thái khối được chọn và cách mã hóa. Không sao chép phần triển khai tìm kiếm của nguồn vào dự án.
- Game gốc: Damien Clarke; [hướng dẫn Coolmath](https://www.coolmathgames.com/0-bloxorz).

Nội dung tải xuống đã được đối chiếu với Git blob ID của commit cố định. [Manifest](../testcases/manifest.json) ghi mã băm file, đường dẫn từng stage, mã truy cập màn chơi, đặc điểm, độ dài tham chiếu và trạng thái kiểm chứng.

## Chuyển đổi

Nguồn đã dùng tọa độ hàng/cột. Giữ nguyên tọa độ và chuyển đổi như sau:

| Nguồn | Dự án |
|---|---|
| Dấu cách | `#` khoảng trống |
| `.` | `.` ô thường |
| `-` | `F` ô dễ vỡ |
| `H` | `G` ô đích |
| `b` / `B` | `B`, trạng thái ban đầu lưu trong định nghĩa cầu |
| `S`, `O`, `X`, `T` | Giữ nguyên |
| Tác dụng cầu `swap` | `toggle` |

Dữ liệu dịch chuyển nguồn còn chỉ ra khối được chọn ban đầu. Thông tin này được dùng để chuyển đổi chuỗi phím đã công bố. Hành động của dự án gọi trực tiếp khối 1 hoặc khối 2, nên không cần trường lựa chọn trong đầu vào.

Dấu gạch dưới trong lời giải nguồn biểu thị thao tác đổi khối được chọn miễn phí. Nó không được tính vào số hành động và được chuyển thành mã tương ứng như `1U`/`2U`. ID luôn gắn với khối đó đến khi ghép lại.

## Những gì đã kiểm chứng

Toàn bộ **33 stage gốc và sáu ví dụ của dự án** có chuỗi hành động tham chiếu phát lại thành công theo luật của phát biểu bài toán v1.0. Điều này xác nhận mọi đầu vào được cung cấp đều có lời giải. Không có đầu ra tham chiếu nào là `unsolvable`.

Checker xác minh đường đi, không xác minh tuyên bố đường đi ngắn nhất. Với 32 stage gốc, độ dài tham chiếu là độ dài tối thiểu do tác giả nguồn công bố; chỉ phát lại không chứng minh tính tối ưu. Lời giải thay thế stage 15 được tìm bằng BFS đầy đủ theo luật của dự án, xác nhận độc lập độ dài tối thiểu 57 bước. Sáu ví dụ nhỏ có thể kiểm tra bằng tay và độ dài trước đó đã được kiểm tra bằng tìm kiếm đầy đủ.

Tổng độ dài lời giải tham chiếu của các stage gốc là **1.999 bước di chuyển theo hướng**. Chọn khối và tác dụng tự động không cộng thêm bước.

## Sửa lời giải stage 15

Chuỗi hành động stage 15 đã công bố thất bại tại bước di chuyển **27**, được chuyển thành `2D`. Khối nhỏ 1 đang ở ô cầu (1,10); khối nhỏ 2 đến công tắc nhẹ tại (3,8), làm cầu đó tắt. Vì vậy, bước kiểm tra khả năng đỡ khối sau tác dụng công tắc theo yêu cầu của dự án kết luận thua.

Solver tham chiếu kiểm tra khả năng đỡ khối trước tác dụng công tắc nhưng không thực hiện cùng bước kiểm tra sau đó. Đây là lý do chuỗi hành động được chấp nhận trong solver nguồn.

Đã tạo và phát lại một đường đi mới theo luật dự án. Đường đi cũng có **57 bước**, lưu trong original/15.out.json. Manifest ghi đây là lời giải thay thế do dự án tạo và giữ thông tin lỗi ban đầu. Kết luận này dựa trên bộ luật đã chọn, không phải bằng chứng về hành vi từng khung hình của mọi phiên bản game gốc.

## Các điểm khác đã làm rõ

Dữ liệu từ bản chuyển thể GBA và Frank-Buss trước đó khác nhau ở bố cục stage 3. Bộ cuối cùng dùng nhất quán cách mã hóa tkoz0 do người dùng cung cấp và đường đi đã kiểm chứng bằng phát lại; không âm thầm trộn bố cục từ nhiều bản chuyển thể.

Khối nhỏ được đứng trên ô dễ vỡ và ô đích, nhưng không thắng khi đứng trên ô đích. Một số điểm đến dịch chuyển là `X` hoặc `T` (đáng chú ý ở stage 16); khối nhỏ không kích hoạt các ô này, nên không có chuỗi tách khối hoặc nhấn công tắc nặng liên tiếp.

## Ghi nhận tác giả và tình trạng giấy phép

Phiên bản tkoz0 đã kiểm tra gồm bốn file, không có file LICENSE hay tuyên bố giấy phép rõ ràng trong README. Việc công khai mã nguồn và ghi nhận tác giả không đồng nghĩa đã có giấy phép phân phối lại. Cần ghi nhận điều này khi đưa bộ dữ liệu chuyển đổi lên repo; không gán nhãn MIT, GPL, public domain hoặc không hạn chế cho dữ liệu.

Ghi nhận tkoz0 cho dữ liệu mã hóa stage và lời giải tham chiếu, Damien Clarke cho Bloxorz. Thông tin này đã có trong repo và cũng cần xuất hiện trong báo cáo Prism. Giữ các thông báo bổ sung nếu chủ sở hữu nguồn cung cấp.

File docs/assets/Bloxorz.gif do chủ dự án cung cấp được dùng minh họa chuyển động. Chưa có thông tin tác giả gốc và điều kiện phân phối lại. Sáu ví dụ mẫu và checker được viết cho dự án này.

## Stage tự sinh trong tương lai

Checker hiện kiểm tra cấu trúc cơ bản và phát lại tất định. Nếu sau này dự án tạo stage tùy ý, cần thêm kiểm tra chuyên biệt cho quá trình sinh/đầu vào và một quy trình đáng tin cậy để xác nhận có lời giải. Khi yêu cầu lời giải ngắn nhất, cần tạo hoặc kiểm chứng thêm bằng chứng về độ dài tối ưu. Không suy ra stage tự sinh giải được chỉ vì nạp hoặc hiển thị được. Ghi phạm vi này trong phần hướng phát triển của báo cáo.
