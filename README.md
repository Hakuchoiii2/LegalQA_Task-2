# DSC2026 — LegalQA Task 2

Hệ thống sinh câu trả lời tiếng Việt từ câu hỏi và các đoạn context đã retrieval.
Pipeline production sử dụng **Qwen3-1.7B cùng adapter QLoRA V8.3 Full Hard**,
hỗ trợ chạy local hoặc trên Kaggle.

## Các thư mục trong repository

| Thư mục | Nội dung |
|---|---|
| [legalQA_Task2/](legalQA_Task2/README.md) | Code production, cấu hình mẫu, input ví dụ, công cụ Kaggle và tests. **Vào đây để chạy hệ thống.** |
| [docs/](docs/) | Tài liệu thiết kế và kế hoạch triển khai; một số tài liệu ghi lại cấu trúc cũ. |
| [reports/](reports/) | Báo cáo kết quả và phân tích các phiên bản model. |

`docs/` và `reports/` phục vụ tham khảo, không phải thành phần cần chạy.
Hướng dẫn hiện hành nằm trong [README production](legalQA_Task2/README.md).

## Chạy local

Chọn và kích hoạt môi trường Python phù hợp trên máy. Từ thư mục repository:

```powershell
cd legalQA_Task2
python -m pip install -r requirements.txt
python scripts/download_nltk_data.py
```

Lần thiết lập đầu tiên, nếu chưa có config cá nhân, copy
`configs/production.example.json` thành `configs/production.json`.
Đặt JSON retrieval vào `inputs/`, rồi sửa `input_json` trong config để chọn file.

Adapter local nằm tại `legalQA_Task2/models/adapter/`. Nếu đã có adapter thì dùng
luôn; nếu clone code từ GitHub và chưa có weights, làm theo mục tải adapter
trong [hướng dẫn production](legalQA_Task2/README.md).

Sau khi chuẩn bị input và adapter:

```powershell
# Sinh thử một câu; tự tải base model khi cache chưa có
python scripts/run_inference.py --limit 1

# Chạy theo config; limit=null để xử lý toàn bộ input
python scripts/run_inference.py

# Chọn file input khác trực tiếp
python scripts/run_inference.py --input-json "inputs/retrieval.json"
```

Base model được lưu trong `legalQA_Task2/.cache/huggingface/`. Lần đầu cần
Internet để tải nếu cache chưa có. Có thể dùng CPU hoặc GPU CUDA tùy môi trường.

## Input và output

Input là danh sách JSON gồm `id`, `question` và `contexts`; mỗi context có `text`.
Xem [input ví dụ](legalQA_Task2/inputs/example.json). Trường `reference_answer`
là tùy chọn, dùng để chấm điểm khi có đáp án tham chiếu.

Mỗi lần chạy tạo `legalQA_Task2/outputs/<run-id>/`:

- `answers.json`: đáp án theo cấu trúc `{"147194": {"answer": "..."}}`.
- `run_metrics.json`: thông tin lần chạy và điểm METEOR/ROUGE-L; điểm là `null`
  nếu không có reference.
- `details.jsonl`: context và thông tin generation cho từng câu.

## Chạy trên Kaggle

Vào `legalQA_Task2/`, cấu hình `kaggle/settings.json` từ file mẫu
`kaggle/settings.example.json`. Chọn input dataset và adapter dataset đã có
trên Kaggle. Quy trình build, upload, cập nhật dataset và tải kết quả được mô tả
trong [README production](legalQA_Task2/README.md#chạy-kaggle).

## Phạm vi Git

Khởi tạo Git ở **thư mục gốc DSC2026**, không khởi tạo thêm trong `legalQA_Task2/`.
`.gitignore` ngoài chỉ cho phép `legalQA_Task2/`, `docs/`, `reports/`, README
và chính file `.gitignore` được đưa vào repo. Các quy tắc trong
`legalQA_Task2/.gitignore` tiếp tục loại settings cá nhân, input thật, weights,
cache, build và outputs. File tạm Word `~$...` cũng được bỏ qua.

Vì vậy adapter và dữ liệu có trên máy local **không tự đi kèm bản clone GitHub**.
Các config mẫu và input giả lập vẫn được giữ để thiết lập trên máy khác.

```powershell
# Chạy tại DSC2026 khi bắt đầu quản lý repo
git init -b main
git add .
git status --short
```

Kiểm tra danh sách file trước khi commit và push. Giữ settings cá nhân trong các
file đã được ignore; chỉnh sửa nội dung tài liệu trước khi công khai nếu cần.
