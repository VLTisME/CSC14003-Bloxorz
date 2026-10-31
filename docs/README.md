# Tài liệu dự án

| Thư mục | Nội dung |
|---|---|
| `prj/` | Bài toán, checker/runner, hướng dẫn GUI/demo và nguồn dữ liệu |
| `algorithms/` | Thiết kế bốn solver, heuristic A* và weighted cost UCS |
| `exp/` | Quy trình tái lập, cấu hình và số liệu tổng hợp của bộ 660 lượt |
| `assets/` | Hình minh họa, tài liệu thiết kế và ghi nhận tài nguyên GUI |

## Hướng dẫn và thiết kế

- [Phát biểu bài toán và đặc tả JSON](prj/problem-statement.md)
- [Checker, runner và đầu ra metrics](prj/runner-proposal.md)
- [GUI, điều khiển và demo](prj/report-and-demo-guide.md)
- [Nguồn dữ liệu stage](prj/stage-sources.md)
- [Thiết kế các solver và phép đo](algorithms/algorithm-guide.md)
- [A* và chứng minh heuristic](algorithms/astar-design.md)
- [UCS và hàm cost có phụ phí](algorithms/ucs-design.md)

## Thực nghiệm

- [Quy trình tái lập](exp/protocol.md)
- [Tổng quan bộ 28/10: BFS/DFS/UCS/A*](exp/2026-10-28-weighted-ucs/README.md)
- [CSV cho báo cáo](exp/2026-10-28-weighted-ucs/paper-data.csv)
- [Năm bảng chi tiết](exp/2026-10-28-weighted-ucs/paper-tables.md)

Chỉ giữ kết quả tổng hợp và cấu hình cần thiết trong tài liệu công bố. Log từng lượt, replay sinh ra, đầu ra kiểm thử và các batch lịch sử được lưu cục bộ ngoài tài liệu GitHub. Lệnh chạy mới ghi vào `results/`; các fixture trong `testcases/` vẫn là dữ liệu nguồn được theo dõi.
