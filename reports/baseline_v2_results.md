# Kết quả baseline v2 — retry và fallback Khối 1

Ngày chạy: 2026-08-12  
Experiment: `baseline-v2-retry-fallback`  
Tập đánh giá: 100 mẫu đầu của `validation/baseline_eligible.jsonl`  
Seed: `2026`  
Context: oracle context tách từ đáp án chuẩn

## Thay đổi

- Tách độc lập `<LEAD>` và `<CONCLUSION>` để không xóa khối hợp lệ còn lại.
- Retry một lần bằng greedy decoding nếu lần đầu không đủ hai thẻ.
- Nếu vẫn thiếu Khối 1, tạo câu dẫn từ metadata căn cứ.
- Ghi nguồn Khối 1: `model_initial`, `model_retry` hoặc `template_fallback`.
- Không tạo conclusion bằng template nếu cả hai lần model đều thiếu Khối 3.

## Kết quả

| Model | METEOR v1 | METEOR v2 | Tăng | Đủ ngay lần đầu | Đủ sau retry | Khối 1 fallback | Thiếu Khối 1 cuối cùng | Thiếu Khối 3 cuối cùng |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-0.6B | 0.6516 | 0.7464 | +0.0948 | 68% | 86% | 7% | 0% | 14% |
| Qwen3-1.7B | 0.7673 | 0.7808 | +0.0134 | 88% | 95% | 1% | 0% | 5% |
| Qwen2.5-3B-Instruct | 0.7511 | 0.7533 | +0.0022 | 49% | 82% | 0% | 0% | 18% |

Ba lượt v1/v2 sử dụng cùng đúng 100 ID. Tất cả prediction v2 đều có Khối 1.

## Kết luận sơ bộ

`Qwen/Qwen3-1.7B` đứng đầu cả METEOR toàn đáp án (0.7808), METEOR của hai khối
được sinh (0.4856), tỷ lệ đủ hai khối sau retry (95%) và tốc độ trung bình
(7.78 giây/mẫu). Đây là ứng viên nên chạy tiếp trên toàn bộ validation trước khi
quyết định fine-tuning.

Kết quả này chỉ đánh giá generator trong điều kiện oracle context; chưa đo chất
lượng retrieval end-to-end của thành viên B.
