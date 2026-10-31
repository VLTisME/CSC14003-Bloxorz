# Bộ testcase

Bộ dữ liệu chốt v1.0 — 15/10/2026; hướng dẫn tiếng Việt ngày 17/10/2026.

- **original/**: đủ 33 stage của game gốc, đã chuyển sang định dạng dự án.
- **samples/**: sáu ví dụ nhỏ có lời giải để tìm hiểu và debug.
- **manifest.json**: nguồn gốc, ID stage, mã truy cập màn chơi, đặc điểm, độ dài tham chiếu và thông tin kiểm chứng.

Mỗi stage có `NN.in.json` và `NN.out.json`. Thuật toán chỉ nhận file đầu vào. File đầu ra chứa một chuỗi hành động tham chiếu hợp lệ, không phải lời giải duy nhất được chấp nhận. Cả 39 chuỗi đều vượt qua checker phát lại.

```bash
python checker.py --all
python checker.py --input testcases/original/01.in.json --output answer.json
```

Lời giải được chấp nhận phải đến đích mà không thua. Lời giải có thể dài hơn tham chiếu. So sánh độ dài cần được báo cáo riêng, không gộp vào AC/WA. Báo `unsolvable` là WA đối với mọi stage được cung cấp.

## Các ví dụ mẫu

| Số file | ID stage | Đặc điểm | Hành động tham chiếu | Độ dài |
|---|---|---|---|---:|
| 01 | sample01 | Lăn cơ bản | R R | 2 |
| 02 | sample02 | Lăn sang bên và đổi hướng | R D D D R | 5 |
| 03 | sample03 | Nằm trên ô dễ vỡ | R R | 2 |
| 04 | sample04 | Công tắc nhẹ đảo trạng thái cầu | R R R R | 4 |
| 05 | sample05 | Khối đứng thẳng nhấn công tắc nặng | R R R R | 4 |
| 06 | sample06 | Dịch chuyển, chọn khối nhỏ và ghép lại | R R 1R R | 4 |

Mỗi ví dụ mẫu có nhiều hàng trên bàn chơi. Sample 01 không phải stage gốc số 1. Các ví dụ không có lời giải trước đó đã được loại khỏi bộ cung cấp.

## Độ dài tham chiếu của các stage gốc

| Stage | Số bước di chuyển theo hướng, theo thứ tự stage |
|---|---|
| 01–10 | 7, 17, 19, 28, 33, 35, 44, 10, 24, 57 |
| 11–20 | 47, 65, 46, 67, 57, 28, 106, 85, 67, 56 |
| 21–30 | 71, 65, 75, 57, 55, 104, 71, 100, 104, 114 |
| 31–33 | 91, 129, 65 |

Tổng cộng: 1.999 bước. Đây là các độ dài được nguồn công bố là tối thiểu, trừ lời giải thay thế stage 15 đã được kiểm tra độc lập. Mọi đường đi được cung cấp đều là lời giải đã kiểm chứng, nhưng phát lại không chứng minh độ dài tối thiểu cho các stage gốc còn lại.

## Stage 15

Đường đi tham chiếu ban đầu tắt cầu dưới khối đứng yên ở bước 27. Đã thay bằng đường đi hợp lệ khác gồm 57 bước. Xem [ghi chú nguồn](../docs/prj/stage-sources.md) để biết phát hiện cụ thể và nguồn gốc.

## Phạm vi bao phủ và giới hạn

Bộ stage gốc có ô dễ vỡ, công tắc nhẹ/nặng, cầu bật/tắt ban đầu, thao tác toggle/on/off, tách khối và ghép lại. Các bài kiểm thử hồi quy checker còn bao phủ đường đi gây thua, mã hành động không được định nghĩa, đường đi hợp lệ dài hơn, khối nhỏ trên ô dễ vỡ/ô đích, nhiều công tắc cùng tác động một cầu và cầu mất khả năng đỡ khối đang đứng yên.

Bộ testcase được xác nhận có lời giải vì mỗi đầu vào có một chuỗi hành động minh chứng đã phát lại thành công. Checker hiện tại không quyết định được một bản đồ mới tùy ý có lời giải hay không.

## Nguồn

Dữ liệu stage và lời giải tham chiếu đã công bố: [tkoz0/bloxorz-solver](https://github.com/tkoz0/bloxorz-solver), commit d203a25170085054fb3f39bd81b3509ee8cd9e47. Game gốc: Damien Clarke. Phiên bản nguồn đã kiểm tra không nêu giấy phép. Xem [ghi chú nguồn](../docs/prj/stage-sources.md) và manifest khi đưa dữ liệu lên repo.
