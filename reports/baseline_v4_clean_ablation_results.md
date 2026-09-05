# Kết quả baseline v4 — clean ablation targeted retry

Ngày chạy: 2026-08-12  
Experiment: `baseline-v4-v2-prompt-targeted-retry`  
Tập đánh giá: cùng 100 mẫu validation của v2/v3  
Seed: `2026`

## Kiểm tra tính hợp lệ của ablation

- System prompt lượt đầu: nguyên văn v2.
- User prompt lượt đầu: nguyên văn v2.
- Context budget lượt đầu: tính bằng hai prompt v2 như cũ.
- Sampling và seed lượt đầu: giữ nguyên v2.
- Raw output lượt đầu v4 khớp v2: 300/300 mẫu.
- Prediction của các mẫu không retry khớp v2: 205/205 mẫu.
- Chỉ cơ chế retry được thay đổi từ sinh lại cả hai khối sang sinh đúng khối
  đang thiếu.

## Kết quả

| Model | METEOR v2 | METEOR v4 | Chênh lệch | Đủ 3 khối v2 | Đủ 3 khối v4 | Phục hồi Khối 3 | Template Khối 1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-0.6B | 0.7464 | 0.7501 | +0.0037 | 86% | 100% | 100% | 0% |
| Qwen3-1.7B | **0.7808** | **0.7774** | -0.0034 | 95% | 100% | 100% | 0% |
| Qwen2.5-3B-Instruct | 0.7533 | 0.7648 | +0.0115 | 82% | 100% | 100% | 0% |

Qwen3-1.7B vẫn có METEOR cao nhất và targeted retry giúp tăng độ đầy đủ lên
100%. Điểm giảm 0.0034 chỉ phát sinh trong 12 mẫu retry; 88 mẫu còn lại giống v2
tuyệt đối. Trong 12 mẫu đó, 1 mẫu tăng và 11 mẫu giảm. Việc bổ sung conclusion
khác câu chữ đáp án chuẩn có thể làm giảm precision/fragmentation của METEOR dù
câu trả lời hoàn chỉnh hơn về cấu trúc.

## Kết luận

V4 là cấu hình hợp lý nhất hiện tại: giữ chất lượng lượt sinh đầu của v2 và dùng
targeted retry để loại bỏ hoàn toàn lỗi thiếu khối. Qwen3-1.7B tiếp tục là model
cân bằng tốt nhất để chạy toàn bộ 285 mẫu validation hợp lệ trước fine-tuning.

Đây vẫn là zero-shot oracle-context hybrid baseline, chưa đánh giá retrieval
end-to-end.
