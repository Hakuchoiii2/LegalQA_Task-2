# Kết quả baseline v3 — targeted retry

Ngày chạy: 2026-08-12  
Experiment: `baseline-v3-targeted-retry`  
Tập đánh giá: cùng 100 mẫu `validation/baseline_eligible.jsonl` của v1/v2  
Seed: `2026`  
Context: oracle context tách từ đáp án chuẩn

## Cơ chế v3

1. Lần đầu sinh chung Khối 1 (`LEAD`) và Khối 3 (`CONCLUSION`).
2. Nếu thiếu Khối 1, retry chỉ Khối 1 bằng greedy decoding.
3. Nếu thiếu Khối 3, retry chỉ Khối 3 bằng greedy decoding.
4. Trong lượt chuyên biệt, plain text không rỗng được chấp nhận nếu model quên
   thẻ XML; nội dung có thẻ của khối còn lại bị từ chối.
5. Chỉ Khối 1 mới có template fallback; Khối 3 không được backend tự tạo.

## Kết quả v3

| Model | METEOR | ROUGE-L | Đủ 3 khối cuối cùng | Retry Khối 1 | Phục hồi Khối 1 | Retry Khối 3 | Phục hồi Khối 3 | Template Khối 1 | Thời gian/mẫu |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-0.6B | 0.7470 | 0.7822 | 100% | 12% | 100% | 49% | 100% | 0% | 7.84 giây |
| Qwen3-1.7B | **0.7690** | 0.7942 | 100% | 2% | 100% | 11% | 100% | 0% | **6.81 giây** |
| Qwen2.5-3B-Instruct | 0.7564 | **0.8020** | 100% | 0% | N/A | 47% | 100% | 0% | 8.54 giây |

Toàn bộ 300 prediction đều có đủ Khối 1, Khối 2 và Khối 3. Targeted retry phục
hồi 100% các Khối 3 bị thiếu trong lượt đầu ở cả ba model.

## So với v2

| Model | Đủ 3 khối v2 | Đủ 3 khối v3 | METEOR v2 | METEOR v3 |
|---|---:|---:|---:|---:|
| Qwen3-0.6B | 86% | 100% | 0.7464 | 0.7470 |
| Qwen3-1.7B | 95% | 100% | 0.7808 | 0.7690 |
| Qwen2.5-3B-Instruct | 82% | 100% | 0.7533 | 0.7564 |

V3 mất 2.531 giây (42,2 phút), nhanh hơn v2 khoảng 16% dù tạo đủ ba khối cho
mọi mẫu. METEOR của Qwen3-1.7B giảm nhẹ so với v2 vì system prompt và prompt
retry đã thay đổi; do đó không nên diễn giải chênh lệch điểm là tác động riêng
của targeted retry.

## Kết luận

Targeted retry giải quyết hoàn toàn lỗi thiếu Khối 3 trên mẫu thử. Qwen3-1.7B
vẫn là ứng viên cân bằng tốt nhất: METEOR cao nhất, đủ ba khối 100%, ít retry
nhất và nhanh nhất trong lần chạy v3. Cần chạy Qwen3-1.7B trên toàn bộ 285 mẫu
validation hợp lệ trước khi chốt model để fine-tuning.

Đây là oracle-context zero-shot hybrid baseline, chưa phải đánh giá retrieval
end-to-end.
