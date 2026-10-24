# Các mốc tiến độ dự án

Cập nhật ngày 17/10/2026. Ngày tháng dùng múi giờ Asia/Ho_Chi_Minh. Chỉ đánh dấu hoàn thành khi đã có đủ sản phẩm được liệt kê và kiểm chứng thành công. Hoàn thành một mốc trong repo không có nghĩa nội dung tương ứng đã được chuyển vào Prism; việc đồng bộ báo cáo được theo dõi riêng bên dưới.

## Các bước chuẩn bị đã hoàn thành

- [x] **M0 — Chốt phát biểu bài toán v1.0.** Hoàn thành **2026-10-15**. Đã mô tả JSON đầu vào/đầu ra, minh họa di chuyển, ô đặc biệt, chọn khối nhỏ không tốn chi phí, mỗi bước theo hướng có chi phí một, hành vi của khối nhỏ trên ô dễ vỡ/ô đích và quy tắc AC/WA/RE. Cấu trúc báo cáo đã được duyệt. Bằng chứng: [phát biểu bài toán](problem-statement.md), [kế hoạch runner](runner-proposal.md). Nội dung sẵn sàng cho báo cáo: phát biểu bài toán và phạm vi trách nhiệm của các thành phần hệ thống.

- [x] **M1 — Xây dựng bộ testcase và checker đơn giản.** Hoàn thành **2026-10-15**. Đã có 33 cặp đầu vào/đầu ra stage gốc và sáu ví dụ có lời giải. Cả 39 chuỗi hành động tham chiếu vượt qua phát lại; mười bài kiểm thử hồi quy checker đều đạt. Stage 15 có lời giải thay thế 57 bước đã kiểm chứng cho chuỗi hành động nguồn có vấn đề. Đã ghi nguồn gốc và giới hạn của các tuyên bố về độ dài tham chiếu. Bằng chứng: [hướng dẫn testcase](../testcases/README.md), [manifest](../testcases/manifest.json), [ghi chú nguồn](stage-sources.md), [checker](../checker.py). Nội dung sẵn sàng cho báo cáo: nguồn dữ liệu, phương pháp checker và ghi chú kiểm chứng.

- [x] **M1.1 — Helper đo lường dùng chung và hướng dẫn bàn giao.** Hoàn thành **2026-10-16**. Đã thêm helper, template thuật toán có thể sao chép, các trường đầu ra benchmark bắt buộc, định nghĩa số liệu đo và hướng dẫn triển khai. Cả 21 bài kiểm thử hồi quy đều đạt, gồm 11 bài cho helper; cả 39 lời giải tham chiếu vẫn vượt qua phát lại. Các lệnh chạy bài nộp đã được mô tả nhưng chưa triển khai. Bằng chứng: [helper](../algorithms/solver_support.py), [template](../algorithms/template.py), [hướng dẫn](algorithm-guide.md), [kiểm thử](../tests/test_solver_support.py). Nội dung sẵn sàng cho báo cáo: quy trình đo, quy tắc kiểm tra tính đầy đủ của số liệu benchmark và bằng chứng kiểm chứng.

- [x] **M1.2 — Chuyển tài liệu repo sang tiếng Việt.** Hoàn thành **2026-10-17**. Đã dịch README, phát biểu bài toán, đặc tả runner/checker, hướng dẫn thuật toán, mốc tiến độ, ghi chú nguồn và hướng dẫn testcase theo quy ước thuật ngữ đã duyệt. Giữ nguyên code, lệnh, JSON, dữ liệu stage và các định danh; bảo toàn liên kết đến các mục đang được tham chiếu. Không thay đổi Google Docs hay báo cáo trên Prism.

## Các mốc còn lại

- [ ] **M2 — Phân công công việc và chuyển phần chuẩn bị vào Prism.** Ngày hoàn thành: chưa có. Phân công đủ bốn thuật toán và phần engine sau khi duyệt phát biểu bài toán/testcase. Chỉ ghi tên, checklist cá nhân và phần trăm hoàn thành trong báo cáo. Chỉ cập nhật Google Docs khi được yêu cầu riêng. Báo cáo: bảng kế hoạch, phát biểu bài toán, nguồn testcase và hướng phát triển.

- [ ] **M3 — Game engine và hiển thị 2D trên terminal.** Ngày hoàn thành: chưa có. Chơi thủ công và phát lại hoạt động với đầy đủ cơ chế yêu cầu; chuyển trạng thái khớp checker và ví dụ. Báo cáo: thiết kế trạng thái/chuyển trạng thái, các lựa chọn triển khai và bằng chứng kiểm chứng.

- [ ] **M4 — Bốn chương trình tìm kiếm Python độc lập.** Ngày hoàn thành: chưa có. BFS, DFS, UCS và A* đọc stage JSON, trả về JSON có thể phát lại. Mỗi chương trình ghi các số liệu tìm kiếm bắt buộc. Giải thích sự tương đương về mục tiêu giữa UCS/BFS khi mỗi hành động có chi phí một và lập luận cho heuristic của A*. Báo cáo: bốn phần thuật toán, chi phí, điều kiện đúng đắn và độ phức tạp.

  Phần code và kiểm thử: BFS, DFS, UCS, A* đều AC 33/33; metrics đầy đủ 33/33. BFS/UCS/A* đã qua đối chiếu độ dài tối ưu, A* có thêm kiểm thử heuristic và chứng minh trong [tài liệu thiết kế](astar-design.md). Nút Solve A* trong GUI 3D đã kiểm thử. Hoàn thành phần triển khai/kiểm chứng **2026-10-24**; M4 vẫn mở cho tới khi các phần báo cáo tương ứng được đưa vào Prism và nhóm rà soát.

- [ ] **M5 — Hoàn tất tích hợp giai đoạn 1.** Ngày hoàn thành: chưa có. Checker chạy bài nộp và runner dùng chung phần thực thi chương trình, giới hạn tài nguyên và phát lại. Cả hai thống kê verdict; runner ghi thêm mức độ đầy đủ của số liệu benchmark, thống kê, một file JSON theo thời điểm và phát lại trên terminal. Báo cáo: phương pháp thực nghiệm và các bảng đo đầu tiên; không tự tạo số liệu.

- [ ] **M6 — GUI 3D và đánh giá cuối cùng.** Ngày hoàn thành: chưa có. Chơi thủ công 3D và phát lại lời giải tự động hoạt động. Chạy một bộ benchmark cố định, tạo biểu đồ, thảo luận đánh đổi giữa thời gian/bộ nhớ/số nút mở rộng/độ dài lời giải. Báo cáo: mô tả GUI, kết quả cuối cùng và thảo luận.

  Đã tích hợp và kiểm thử nút Solve A*, chạy benchmark so sánh BFS/A* trên 33 stage và lưu kết quả theo từng stage trong [Markdown](astar-benchmark.md)/[CSV](astar-benchmark.csv) vào **2026-10-24**. Còn tạo biểu đồ, chạy đo lặp lại để kết luận hiệu năng và hoàn thiện nội dung báo cáo.

- [ ] **M7 — Gói nộp bài và demo.** Ngày hoàn thành: chưa có. Hoàn tất mã nguồn có thể tái chạy, hướng dẫn thiết lập, PDF, trích dẫn, phụ lục sử dụng AI, liên kết demo công khai có thuyết minh/phụ đề và file nén đúng tên. Báo cáo: đối chiếu lần cuối với tiêu chí chấm bài.

M3 và M4 có thể thực hiện song song sau khi phân công. Không đánh dấu hoàn thành mốc triển khai hay hiệu năng chỉ vì đã có kế hoạch. Khoảng 15–20/10 từng đề xuất cho giai đoạn 1 chỉ là mục tiêu lập kế hoạch; chưa xác minh hạn nộp chính thức.

## Trạng thái đưa lên GitHub

- [x] Chuẩn bị cục bộ gói tài liệu/testcase — **2026-10-15**.
- [x] Chuẩn bị bản cập nhật helper đo lường và hướng dẫn đầu ra — **2026-10-16**.
- [x] Người dùng duyệt lần cuối gói cập nhật — **2026-10-16**; bổ sung cách làm ưu tiên tính đúng đắn theo yêu cầu.
- [x] Đã đưa gói lên `origin/main` — hoàn thành **2026-10-16**, commit gói `b592fc0`. Bao gồm đặc tả, hướng dẫn ưu tiên tính đúng đắn, helper/template, checker, kiểm thử và 39 cặp đầu vào/lời giải tham chiếu. Không đưa bản nháp báo cáo và kết quả chạy sinh ra lên GitHub. Chưa phân công nhiệm vụ.
- [ ] Xác nhận điều kiện phân phối lại dữ liệu nguồn/GIF — phiên bản tkoz0 đã kiểm tra không nêu giấy phép, GIF người dùng cung cấp chưa có thông tin nguồn gốc. Đã ghi nhận tác giả; việc ghi nhận không tự tạo quyền sử dụng.
- [ ] Đồng bộ báo cáo Prism — chưa thực hiện.

Báo cáo hiện không nằm trong gói repo này. Các mốc tiến độ sẽ được phản ánh trong báo cáo, nhưng phân công cá nhân không được sao chép vào tài liệu GitHub hay issues.
