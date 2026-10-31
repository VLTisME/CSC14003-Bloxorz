# Kết quả mới: BFS / DFS / UCS có phụ phí / A*

33 stage original × 4 thuật toán × 5 lượt = **660 lượt AC, đủ metrics và đối chiếu cost thành công**. Sáu sample được kiểm tra riêng: **24/24 AC**; không gộp vào thống kê. Bộ kiểm thử tự động tại thời điểm thu batch: **57/57 qua**. Đối chiếu Dijkstra viết riêng trên checker xác nhận UCS đạt cost tối ưu ở **33/33 stage original** (việc đối chiếu nằm ngoài phép đo).

## Bảng tổng quan

**Mỗi ô là median của 33 median theo stage**, không phải trung bình hoặc thống kê của 165 lượt gộp. IQR theo 5 lượt nằm trong paper-data.csv.

| Thuật toán | Thời gian ms | Peak MiB | Expanded | Số bước | Cost có phụ phí |
|---|---:|---:|---:|---:|---:|
| BFS | 35.789 | 0.218 | 474 | 57 | 68 |
| DFS | 18.845 | 0.153 | 282 | 98 | 110 |
| UCS (cost mới) | 40.015 | 0.209 | 493 | 57 | 68 |
| A* | 47.182 | 0.250 | 265 | 57 | 68 |

## Cách hiểu cost

Cost cạnh: **1 + 1×chạm B + 2×chạm F + 3×kích hoạt tách**. Các chỉ báo 0/1, mỗi loại tính tối đa một lần mỗi bước. Khối tách chỉ xét ô đến của cube di chuyển (trước khi tự ghép làm đổi thứ tự tọa độ). Khối nguyên xét hai ô cuối chuyển tiếp, kể cả các điểm đến splitter. Chạm T khi nằm không tính phí tách; tự ghép không có phụ phí.

BFS/A* tối ưu số bước; UCS tối ưu cost có phụ phí; DFS không bảo đảm tối ưu. **weighted_cost của cả bốn lời giải được tính lại bằng cùng công thức sau khi chạy solver**, ngoài cửa sổ đo. Cost UCS tự báo cáo phải khớp replay. Trường cost cũ trong summary.csv vẫn là số bước; khi viết báo cáo dùng solution_length và weighted_cost riêng.

## Các trường hợp UCS chọn đường rẻ hơn BFS

| Stage | Bước BFS | Cost BFS | Bước UCS | Cost UCS |
|---|---:|---:|---:|---:|
| stage13 | 46 | 68 | 49 | 63 |
| stage16 | 28 | 56 | 30 | 55 |
| stage23 | 75 | 133 | 76 | 128 |
| stage25 | 55 | 67 | 55 | 66 |

UCS có cost thấp hơn BFS ở 4/33 stage, bằng ở 29/33; dài hơn BFS ở 3 stage. Cùng median tổng quan không có nghĩa cost bằng nhau trên từng stage. BFS/A* có cùng độ dài trên 33/33 stage; phải đọc cost theo đường đi cụ thể, không gán tối ưu có phụ phí cho BFS/A*.

## Phạm vi đo và dùng trong báo cáo

- Chạy tuần tự, tiến trình Python mới cho mỗi lượt, warmup sample01 một lượt/thuật toán; timeout 60 giây, 5 vòng xáo trộn.
- Thời gian và peak memory A* bao gồm tiền xử lý heuristic; expanded nodes không tính pha tiền xử lý. Tracemalloc không phải RSS; thời gian có overhead instrumentation.
- IQR bộ nhớ, expanded, số bước và cost đều bằng 0 trong batch này; thời gian có IQR khác 0. Đây là kết quả của batch, không phải bảo đảm trên mọi môi trường.
- Dùng thống nhất batch này cho kết quả và phụ lục; không ghép số liệu của batch khác.

## Tệp công bố

- `paper-data.csv`: 132 cặp thuật toán–stage, median/IQR của năm chỉ tiêu cùng số lượt AC/đủ dữ liệu/đối chiếu cost.
- `overview.csv`: median của 33 median theo stage.
- `paper-tables.md`: năm bảng đầy đủ 33 stage cho báo cáo.
- `summary.csv/json`, `tables.md`: thống kê tổng hợp, gồm chỉ tiêu bổ sung của A*.
- `metadata.json`: cấu hình, môi trường và nguồn phiên bản của batch lịch sử.

Log từng lượt, replay sinh ra, warmup và kết quả validation chi tiết được lưu cục bộ ngoài repo. Không thay số liệu lịch sử bằng lượt kiểm thử hiện tại. Mã tìm kiếm, checker và fixture của bản tích hợp đã được đối chiếu với phiên bản dùng để đo; sửa hiển thị GUI không thay số liệu này.

Chạy lại theo [protocol](../protocol.md); đối chiếu độc lập bằng `python tools/validate_solvers.py`. CPU batch lịch sử: Ryzen 7 8845H; 16 CPU logic; RAM khoảng 27,21 GiB; CPython 3.12.3; Linux x86_64 kernel 7.0.0-38.
