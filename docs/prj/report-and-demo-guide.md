# GUI, replay và demo

- [Video demo](https://www.youtube.com/watch?v=HB6mtO96rz0)
- [Repository](https://github.com/VLTisME/CSC14003-Bloxorz)

## Kiến trúc

Engine tương tác dùng luật chuyển trạng thái từ `checker.Replay`; GUI Ursina hiển thị bàn chơi, hoạt ảnh và HUD. Bốn solver dùng mô hình tìm kiếm riêng. `SearchController` chạy solver trong worker, chuyển actions/metrics qua hàng đợi; luồng giao diện kiểm tra lời giải rồi phát replay. Bộ replay dùng chung cho output của BFS/DFS/UCS/A*.

`GameStatus` chỉ gồm PLAYING, WON, LOST. `Posture` gồm UPRIGHT, HORIZONTAL, VERTICAL, SPLIT; tách khối không phải trạng thái ván chơi riêng. Hoạt ảnh rơi do lớp animation quản lý. Cube đang chọn là `selected_cube`; engine giữ lịch sử Undo trong `history`.

## Khởi chạy

```bash
python -m pip install -r requirements.txt
python play.py
python play.py --stage 13
python play.py --suite samples --stage 04
python play.py --stage 01 --terminal
python algorithms/UCS.py < testcases/original/13.in.json > answer.json
python play.py --stage 13 --replay answer.json
```

Có thể thay UCS bằng BFS/DFS/ASTAR. File replay phải là output của một solver trên đúng màn, có `actions`; không dùng JSON tổng hợp nhiều testcase của runner làm replay.

## Điều khiển GUI cuối

- WASD hoặc mũi tên: lăn; Space: đổi cube khi tách.
- Z/U: Undo; R: Reset; Esc: menu.
- Con lăn chuột: zoom; C: trả camera về mặc định. Camera trực giao, không có chuyển phối cảnh bằng V.
- Chọn thuật toán rồi bấm Giải để chạy trực tiếp; nút đổi thành Tạm Dừng/Tiếp Tục khi đang tìm kiếm.
- Replay gồm Prev, Play/Pause, Next và tốc độ; P tạm dừng/tiếp tục replay.
- Cửa sổ benchmark chạy bốn solver trên cùng màn; Run phát lời giải của hàng đã chọn. Cột STEPS/COST ghi số bước cho các solver và cặp số bước/cost cho UCS.

GUI UCS hiển thị số bước và `weighted_cost` riêng, ví dụ stage13: 49 bước, cost 63. Cost này khác trường `cost` của checker (số bước). Đo nhanh trên GUI không thay bộ benchmark tiến trình riêng có tracemalloc.

## Kiểm thử và lưu trữ

Các kiểm thử engine/luật/solver ở `tests/`; kiểm thử giao diện ở `game/tests_ui/`. Có thể chạy GUI test bằng môi trường đồ họa thật hoặc `xvfb-run -a python -m unittest discover -s game/tests_ui -v` trên Linux có Xvfb.

Log và báo cáo ma trận tự sinh ghi trong `results/`; tiến độ chơi ở `game/progress.json`. Chúng không được Git theo dõi. Khi cần phiên chơi sạch, sao lưu rồi bỏ file tiến độ cục bộ; game tự tạo lại khi ghi chiến thắng.
