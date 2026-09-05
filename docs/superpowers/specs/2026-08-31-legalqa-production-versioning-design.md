# LegalQA Production Versioning Design

## Mục tiêu

Đóng băng code hiện tại thành `legalqa_baseline/v8_3_full_hard`, giữ dữ liệu dùng
chung tại `legalqa_baseline/data`, và tạo ứng dụng `model_production` có thể chọn
phiên bản model bằng config để sinh submission từ JSON retrieval của thành viên B.

## Cấu trúc

- `legalqa_baseline/data`: dữ liệu train/validation dùng chung.
- `legalqa_baseline/v8_3_full_hard`: config, source, script, test, tài liệu và runs
  của V8.3 Full Hard.
- `model_production`: input retrieval, output, config, runner, test và công cụ build
  kernel production.
- `.kaggle`: tiếp tục quản lý kernel thực nghiệm; build lấy source từ phiên bản
  `v8_3_full_hard` nhưng bundle về layout runtime cũ để không đổi hành vi kernel.

## Luồng production

`production.json` chọn `model_version`, `input_json`, `top_k`, seed, adapter local
và adapter Kaggle. Runner xác thực danh sách package, ghép text của top-k context,
tổng hợp citation metadata, nạp Qwen3-1.7B cùng adapter QLoRA, rồi dùng đúng pipeline
V8.3 Full Hard để sinh lead/conclusion và ghép context vào đáp án.

Mỗi lần chạy tạo một thư mục timestamp chứa:

- `answers.json`: `{ "<id>": { "answer": "..." } }`.
- `run_metrics.json`: thời gian, hash input, phiên bản code, model/adapter, tham số,
  thống kê trạng thái và điểm.
- `details.jsonl`: trace kỹ thuật để kiểm tra lỗi.

Nếu mọi mẫu có `reference_answer`, runner gọi nguyên `score_submission` hiện có.
Nếu không có reference, `meteor` và `rouge_l` là `null`, với
`scoring_status = "not_available_no_reference"`.

## Kaggle production

Kernel `dsc2026-legalqa-v83-full-hard-production` tách biệt kernel thực nghiệm.
Một private dataset production-inputs chứa JSON được chọn. Kernel gắn hai dataset:
input retrieval và adapter QLoRA, giải nén bundle source rồi gọi cùng runner.

## Kiểm thử

Unit test bao phủ schema input, chọn top-k, citation metadata, submission, scoring
có/không reference, chọn phiên bản và build metadata kernel. Sau đó chạy toàn bộ test
V8.3 và kiểm tra bundle kernel.
