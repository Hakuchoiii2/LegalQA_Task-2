# Input retrieval

Đặt các JSON của thành viên B trực tiếp trong folder này. Các file dữ liệu thật
được Git bỏ qua; `example.json` là ví dụ tự tạo để minh họa schema.

Mỗi mẫu có `id`, `question`, `contexts` (mỗi context có `text`). Có thể thêm
`reference_answer` để tính METEOR và ROUGE-L. Không cần reference khi chạy bộ thi.
