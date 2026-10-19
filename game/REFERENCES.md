# TÀI LIỆU THAM KHẢO VÀ NGUỒN GỐC DỮ LIỆU
## Bloxorz 3D Game & Simulation Studio
**Dự án:** Bloxorz Game Logic & 3D Interactive Visualization  
**Học phần:** CSC14003 - Cơ sở Trí tuệ Nhân tạo (AI Foundations)  
**Đơn vị:** Khoa Công nghệ Thông tin, Trường Đại học Khoa học Tự nhiên, ĐHQG-HCM  

---

### 1. Nguồn gốc Trò chơi và Bản quyền (Original Game Attribution)
* **Tác giả:** Damien Clarke (DX Interactive, 2007).
* **Nền tảng phát hành:** Xuất bản ban đầu dưới dạng Web Flash Game trên [Coolmath Games](https://www.coolmathgames.com/0-bloxorz).
* **Đóng góp học thuật:** Thiết kế bài toán câu đố không gian (spatial puzzle) nổi tiếng với cơ chế lật khối hộp kích thước 1×1×2 trên lưới rời rạc, tích hợp các cơ chế tương tác phức tạp:
  - Ô công tắc mềm (`O`): kích hoạt bởi bất kỳ bề mặt nào của khối.
  - Ô công tắc nặng (`X`): đòi hỏi khối hộp phải đứng thẳng với trọng tâm dồn lên 1 ô.
  - Hệ thống cầu nối (`B`): đóng/mở động theo trạng thái của công tắc.
  - Ô dễ vỡ (`F`): sụp đổ nếu khối 1×1×2 đứng thẳng lên trên.
  - Ô tách khối (`T`): chia tách khối hộp thành hai khối nhỏ 1×1×1 độc lập có thể điều khiển riêng rẽ và tái hợp nhất khi đứng kề nhau.

---

### 2. Nguồn dữ liệu Màn chơi và Chuỗi Lời giải (Stage Dataset & Solutions)
* **Tác giả số hóa:** tkoz0 (2018).
* **Kho mã nguồn:** [tkoz0/bloxorz-solver (GitHub)](https://github.com/tkoz0/bloxorz-solver).
* **Commit tham chiếu cố định:** `d203a25170085054fb3f39bd81b3509ee8cd9e47`.
* **Các tệp tin chuyển đổi:**
  - `coolmath.json`: Lưu trữ ma trận cấu hình 33 màn chơi gốc, vị trí xuất phát, đích đến, các cầu nối và điểm dịch chuyển khi tách khối.
  - `solution.txt`: Chuỗi hành động tham chiếu công bố với tổng cộng **1.999 bước di chuyển**.
  - `solver.py`: Tài liệu tham khảo cấu trúc mã hóa tọa độ hàng/cột và hành động.
* **Tình trạng giấy phép:** Kho mã nguồn của tkoz0 không chứa tệp tin `LICENSE` chính thức. Vì vậy, tập dữ liệu được chuyển đổi trong dự án này phục vụ hoàn toàn cho mục đích giáo dục, nghiên cứu thuật toán học thuật trong khuôn khổ môn học CSC14003; tuyệt đối không tự ý gán nhãn giấy phép thương mại hay tái phân phối trái phép.
* **Hiệu đính kỹ thuật đặc biệt (Stage 15):** 
  - Chuỗi lời giải gốc công bố của tkoz0 cho màn 15 bị lỗi tại bước 27 (`2D`) do solver nguồn chỉ kiểm tra điều kiện đỡ khối *trước* khi công tắc bật tắt cầu, dẫn đến khối nhỏ 1 bị rơi khi khối nhỏ 2 tắt cầu dưới chân nó.
  - Dự án này đã tiến hành chạy thuật toán tìm kiếm Breadth-First Search (BFS) toàn diện độc lập và xác minh thành công một lời giải thay thế hợp lệ chuẩn xác đạt đúng **57 bước** (bằng với độ dài tối thiểu được tuyên bố).

---

### 3. Cơ sở Toán học Phép chiếu Xiên (Oblique / Cavalier Projection)
* **Tác giả:** YellowAfterlife (yal.cc, 2018).
* **Chuyên đề:** *Axonometric and Oblique Projections in 2D/3D Video Games*.
* **Tài liệu trực tuyến:** [Understanding Isometric and Oblique Projections](https://yal.cc/understanding-isometric-and-oblique-projections/).
* **Đóng góp kỹ thuật:** 
  - Khắc phục triệt để nhược điểm của phép chiếu Trục đo (Isometric $45^\circ$) truyền thống — nơi người chơi thường bị nhầm lẫn phương hướng vì phím mũi tên thẳng (Up/Down) di chuyển chéo trên màn hình.
  - Ứng dụng phép chiếu Xiên (Oblique Projection) với ma trận biến đổi:
    $$\begin{cases} x = c \cdot W + r \cdot (W \cdot \text{skew}_x) \\ y = r \cdot (W \cdot \text{tilt}) - z \cdot H \end{cases}$$
    giúp phương ngang ($c$) thẳng hoàn toàn theo trục X màn hình và phương dọc ($r$) chạy thẳng đứng theo trục Y, mang lại trải nghiệm điều khiển tự nhiên, trực quan 100% cho người chơi.

---

### 4. Kỹ thuật Dựng hình Lưới Isometric và Sắp xếp Chiều sâu (Depth Sorting)
* **Tác giả:** Amit Patel (Red Blob Games, 2014–2020).
* **Chuyên đề:** *Isometric Tiles Math and Painter's Algorithm in Grids*.
* **Tài liệu trực tuyến:** [Red Blob Games - Isometric Grid Rendering](https://www.redblobgames.com/grids/parts/#isometric).
* **Đóng góp kỹ thuật:**
  - Áp dụng thuật toán của họa sĩ (Painter's Algorithm) để phân lớp vẽ từ xa tới gần mà không cần Depth Buffer phần cứng:
    $$\text{DepthKey}(r, c, z) = (r + c) \times 1000 + z$$
  - Kỹ thuật tính toán đa giác bóng đổ dưới đáy khối hộp và ánh sáng 3 mặt (Top, South, East faces) với các sắc độ màu sắc tương phản giúp tạo cảm giác chiều sâu 3D chân thực.

---

### 5. Nghiên cứu Mô hình hóa Không gian Trạng thái Bloxorz (State Space Search)
* **Tác giả / Học viện:** 
  - Martin Odersky et al. (École Polytechnique Fédérale de Lausanne - EPFL): *Functional Program Design in Scala - Bloxorz Solver Assignment*.
  - Stanford University CS109: *Search Algorithms and State Representation Case Study*.
* **Đóng góp kỹ thuật:**
  - Mô hình hóa toán học cho trạng thái Bloxorz thành trạng thái hữu hạn rời rạc $S = (\text{cube}_1, \text{cube}_2, \text{posture}, \text{bridge\_state})$.
  - Định nghĩa các hành vi chuyển trạng thái không gian (State Transitions) chuẩn hóa theo 4 hướng lăn cơ bản ($U, D, L, R$), xử lý va chạm và các trường hợp biên của bài toán tìm kiếm đường đi tối ưu (Shortest Path Finding).

---

### 6. Tài liệu Thư viện Đồ họa Chuẩn Python (Tkinter GUI Reference)
* **Tác giả:** Python Software Foundation (2024).
* **Tài liệu chính thức:** [Tkinter 8.6 Reference Manual - The Canvas Widget](https://docs.python.org/3/library/tkinter.html).
* **Đóng góp kỹ thuật:**
  - Kỹ thuật vẽ đồ họa vector 2D trên Canvas widget thông qua phương thức `create_polygon()`, `create_line()`, `create_oval()`.
  - Quản lý vòng lặp hoạt ảnh lăn mượt (Smooth Animation Loop) 60 FPS bằng cơ chế `widget.after(ms, callback)` không gây nghẽn luồng chính (non-blocking event loop).
  - Sử dụng hệ thống widget `ttk` hiện đại (`Notebook`, `Combobox`, `Scrollbar`) để tạo giao diện Pop-up thẩm mỹ, chuyên nghiệp và phản hồi tức thì.
