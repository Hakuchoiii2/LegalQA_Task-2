# Báo cáo thực nghiệm V5 — mở rộng Khối 3

## 1. Mục tiêu

V5 kiểm tra giả thuyết: bỏ giới hạn 120 từ ở Khối 3 để mô hình diễn đạt đầy đủ hơn, tăng khả năng khớp các ý kết luận trong đáp án chuẩn.

Đây vẫn là baseline **zero-shot với oracle/gold context**:

- Mô hình sinh Khối 1 (câu dẫn căn cứ) và Khối 3 (kết luận).
- Khối 2 được chép nguyên văn từ context.
- Không fine-tune ở thí nghiệm này.

“Không giới hạn từ” nghĩa là không còn ràng buộc 120 từ trong prompt. Hệ thống vẫn cần giới hạn kỹ thuật để tránh sinh vô tận: tối đa 512 token cho lần sinh chính và 384 token cho lần sinh lại Khối 3.

## 2. Thay đổi so với V4

- Bỏ yêu cầu Khối 3 tối đa 120 từ.
- Tăng `max_new_tokens` của lần sinh chính từ 256 lên 512.
- Cho phép lần sinh lại Khối 3 tối đa 384 token.
- Yêu cầu kết luận bao phủ các ý liên quan trong context: chủ thể/hành vi, điều kiện/ngoại lệ, thời hạn/số liệu/tỷ lệ, thủ tục/thứ tự/ưu tiên và các mục liệt kê.
- Vẫn cấm đưa thông tin ngoài context, lặp ý và chép toàn bộ context thành kết luận.
- Bổ sung điểm riêng cho phần kết luận và thống kê độ dài.

## 3. Kết quả chính trên 100 mẫu validation

| Model | METEOR toàn đáp án V4 | METEOR toàn đáp án V5 | Chênh lệch | METEOR riêng Khối 3 V4 | METEOR riêng Khối 3 V5 | Số từ Khối 3 V5 | Số từ đáp án chuẩn |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-0.6B | 0.7501 | 0.7487 | -0.0014 | 0.3897 | 0.3754 | 71.6 | 86.1 |
| Qwen3-1.7B | **0.7774** | **0.7598** | -0.0176 | 0.3965 | **0.4752** | 121.1 | 86.1 |
| Qwen2.5-3B-Instruct | 0.7648 | 0.7584 | -0.0064 | 0.4089 | 0.4321 | 85.5 | 86.1 |

Cả 300/300 dự đoán đều có đủ ba khối sau bước kiểm tra và sinh lại có mục tiêu.

Kết quả cho thấy METEOR riêng Khối 3 tăng rõ ở Qwen3-1.7B và tăng nhẹ ở Qwen2.5-3B. Tuy nhiên, METEOR của toàn đáp án giảm ở cả ba model. Nguyên nhân chính là kết luận dài hơn làm tăng recall nhưng đồng thời giảm precision, tăng lặp hoặc thêm diễn đạt không có trong đáp án chuẩn.

## 4. Phân tích theo độ dài kết luận chuẩn

Tập validation có 25 mẫu mà Khối 3 chuẩn dài hơn 120 từ và 75 mẫu không quá 120 từ.

### 4.1. Nhóm kết luận chuẩn dài hơn 120 từ

| Model | METEOR Khối 3 V4 | METEOR Khối 3 V5 | Chênh lệch | Số từ sinh V4 | Số từ sinh V5 | Số từ chuẩn |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3-0.6B | 0.2947 | 0.2661 | -0.0286 | 73.6 | 66.5 | 183.6 |
| Qwen3-1.7B | 0.2889 | **0.4669** | **+0.1780** | 61.9 | 114.7 | 183.6 |
| Qwen2.5-3B-Instruct | 0.2546 | **0.3808** | **+0.1262** | 63.0 | 99.6 | 183.6 |

Ở nhóm này, giả thuyết của V5 được xác nhận mạnh với Qwen3-1.7B và Qwen2.5-3B: cho phép kết luận dài hơn giúp mô hình thu hồi thêm nhiều ý đúng. Qwen3-1.7B cải thiện ở 23/25 mẫu; Qwen2.5-3B cải thiện ở 20/25 mẫu.

### 4.2. Nhóm kết luận chuẩn không quá 120 từ

| Model | METEOR Khối 3 V4 | METEOR Khối 3 V5 | Chênh lệch | Số từ sinh V4 | Số từ sinh V5 | Số từ chuẩn |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3-0.6B | 0.4214 | 0.4118 | -0.0096 | — | — | 53.6 |
| Qwen3-1.7B | 0.4324 | 0.4780 | +0.0456 | 46.4 | 123.2 | 53.6 |
| Qwen2.5-3B-Instruct | 0.4603 | 0.4493 | -0.0110 | 52.2 | 80.8 | 53.6 |

Qwen3-1.7B vẫn tăng METEOR riêng Khối 3, nhưng trung bình sinh 123.2 từ cho đáp án chuẩn chỉ 53.6 từ. ROUGE của nhóm này giảm từ 0.4799 xuống 0.3968, cho thấy phần sinh thêm làm giảm độ chính xác theo chuỗi và tạo nhiều nội dung dư.

## 5. Chi phí và dấu hiệu chạm giới hạn token

- V5 chạy khoảng 54.3 phút; V4 khoảng 46.3 phút. V5 lâu hơn khoảng 17.3%.
- Qwen3-1.7B chạm giới hạn token ở 6% lần sinh chính.
- Trong sáu mẫu Qwen3-1.7B phải sinh lại kết luận, hai mẫu tiếp tục chạm giới hạn 384 token.
- Qwen3-0.6B không chạm giới hạn nhưng cũng không tận dụng được prompt mở rộng để tăng điểm.

## 6. Kết luận

V5 chứng minh rằng bỏ giới hạn cứng có ích đối với các câu hỏi có nhiều điều kiện, danh sách hoặc kết luận chuẩn dài. Lợi ích rõ nhất thuộc về Qwen3-1.7B. Tuy nhiên, áp dụng “sinh dài” cho mọi câu làm các trường hợp đơn giản bị dài quá mức, nên điểm chính thức trên toàn đáp án giảm.

Vì vậy:

- Chưa nên thay V4 bằng V5 làm baseline cuối cùng.
- V4 vẫn có METEOR toàn đáp án tốt nhất: Qwen3-1.7B đạt 0.7774.
- Qwen3-1.7B vẫn là ứng viên ưu tiên để fine-tune vì vừa dẫn đầu toàn đáp án, vừa cho thấy khả năng tăng recall mạnh ở kết luận dài.
- Kết quả V5 nên được dùng để thiết kế V6 với độ dài thích nghi: câu đơn giản sinh ngắn; context có nhiều khoản, điều kiện, số liệu hoặc mục liệt kê mới cho phép sinh dài.

## 7. Đề xuất V6

1. Phân loại độ phức tạp từ context bằng quy tắc: số khoản/mục, dấu liệt kê, số điều kiện, mốc thời gian và số liệu.
2. Với context đơn giản, yêu cầu một kết luận trực tiếp, mỗi ý chỉ xuất hiện một lần.
3. Với context phức tạp, cho phép liệt kê đầy đủ các ý trả lời được câu hỏi mà không đặt giới hạn 120 từ.
4. Dừng sinh ngay khi gặp thẻ đóng `</CONCLUSION>` để hạn chế phần kéo dài sau khi đã hoàn tất.
5. Đánh giá đồng thời METEOR toàn đáp án, METEOR riêng Khối 3, ROUGE và tỷ lệ độ dài dự đoán/đáp án chuẩn.

