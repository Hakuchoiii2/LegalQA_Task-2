# Báo cáo V7 — Qwen3-1.7B, prompt V4 + retrieved 2-shot

## Thiết kế

- Chỉ chạy Qwen3-1.7B.
- Khôi phục đúng nhiệm vụ prompt V4:
  - Khối 1 do model sinh, tối đa 60 từ.
  - Khối 3 trả lời trực tiếp, tối đa 120 từ.
  - Khối 2 được chương trình chép nguyên văn từ oracle context.
- Mỗi câu nhận hai ví dụ lấy từ train.
- Ví dụ cùng dạng câu hỏi, không cùng `citation_group` với câu validation.
- Pool ban đầu có 1.447 mẫu train hợp lệ; 183 mẫu duy nhất được đóng gói để phục vụ 100 câu validation.
- 100 mẫu validation, seed 2026, giống V4.
- Context hiện tại giữ đúng budget V4; cửa sổ tổng được mở rộng chỉ để chứa ví dụ.

## Kết quả chính

| Chỉ số | V4 zero-shot | V7 2-shot | Chênh lệch |
|---|---:|---:|---:|
| METEOR toàn đáp án | **0.7774** | 0.7587 | -0.0187 |
| ROUGE toàn đáp án | 0.7888 | **0.8195** | +0.0307 |
| METEOR Khối 1 | 0.3651 | **0.4963** | +0.1312 |
| METEOR Khối 3 | **0.3965** | 0.3786 | -0.0180 |
| METEOR Khối 1+3 | **0.4853** | 0.4240 | -0.0613 |
| Đủ ba khối | 100% | 100% | 0 |

V7 cải thiện METEOR toàn đáp án ở 45 câu và làm giảm ở 55 câu.

## Độ dài và chi phí

| Chỉ số | V4 | V7 |
|---|---:|---:|
| Số từ Khối 3 trung bình | khoảng 50 | 50.5 |
| Số từ Khối 3 chuẩn | 86.1 | 86.1 |
| Input token trung bình | 727.6 | 1.6970 |
| Output token trung bình | 174.0 | 131.7 |
| Latency/câu | 7.35 giây | 6.08 giây |
| Context bị cắt | — | 0% |
| Retry | 12% | 6% |

Toàn job một model hoàn tất trong 704.8 giây, khoảng 11.7 phút.

## Kết quả theo dạng câu hỏi

| Dạng | Số câu | V4 METEOR | V7 METEOR | Chênh lệch |
|---|---:|---:|---:|---:|
| Điều kiện | 8 | 0.7545 | 0.7035 | -0.0510 |
| Số liệu/thời hạn | 11 | 0.7657 | 0.7106 | -0.0550 |
| Khác | 35 | 0.7814 | 0.7625 | -0.0189 |
| Trình tự/danh sách | 16 | 0.7631 | **0.7745** | **+0.0113** |
| Chủ thể | 9 | 0.8576 | 0.8463 | -0.0114 |
| Có/không | 21 | 0.7619 | 0.7489 | -0.0131 |

Chỉ nhóm trình tự/danh sách tăng điểm toàn đáp án. Nếu dùng một router thử nghiệm trên chính validation — V7 cho nhóm trình tự/danh sách, V4 cho các nhóm còn lại — METEOR ước tính khoảng 0.7792. Kết quả này phải được xác nhận trên tập độc lập vì quy tắc được rút ra từ chính validation.

## Kết quả theo độ dài Khối 3 chuẩn

| Độ dài chuẩn | Số câu | V4 METEOR | V7 METEOR | Chênh lệch |
|---|---:|---:|---:|---:|
| ≤ 40 từ | 27 | 0.8389 | **0.8491** | +0.0101 |
| 41–120 từ | 48 | **0.8017** | 0.7898 | -0.0119 |
| > 120 từ | 25 | **0.6643** | 0.6013 | -0.0629 |

Hai ví dụ ngắn theo giới hạn V4 khiến model ưu tiên câu trả lời gọn. Điều này có ích cho đáp án chuẩn ngắn, nhưng làm mất recall ở câu cần kết luận dài. Nhóm trên 120 từ chỉ sinh trung bình 51.8 từ trong khi đáp án chuẩn trung bình 183.6 từ.

## Kết luận

1. Retrieved 2-shot không nên bật toàn cục: METEOR giảm 0.0187.
2. Few-shot giúp model học rất tốt văn phong Khối 1 và tăng ROUGE, nhưng chưa giúp chọn đủ nội dung cho Khối 3.
3. V4 zero-shot Qwen3-1.7B vẫn là cấu hình METEOR tốt nhất: 0.7774.
4. Few-shot có tín hiệu tích cực ở câu trình tự/danh sách và đáp án ngắn.
5. Thực nghiệm kế tiếp hợp lý là **conditional few-shot**: chỉ dùng ví dụ cho câu trình tự/danh sách; các dạng khác dùng V4 zero-shot. Cần xác nhận trên split độc lập để tránh overfit.
6. Nếu tiếp tục thử few-shot toàn cục, nên thử 1-shot hoặc ví dụ chỉ chứa Khối 1 và một sơ đồ chọn ý, thay vì hai đáp án hoàn chỉnh đều bị giới hạn 120 từ.

