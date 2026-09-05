# Báo cáo thực nghiệm V6 — Khối 3 theo trọng tâm câu hỏi

## 1. Thiết kế thí nghiệm

V6 giữ nguyên các thành phần để so sánh trực tiếp với V4/V5:

- Ba model: Qwen3-0.6B, Qwen3-1.7B và Qwen2.5-3B-Instruct.
- 100 mẫu validation, seed 2026.
- Oracle/gold context giống nhau.
- Model vẫn tự sinh Khối 1; không thay Khối 1 bằng template.
- Chương trình chép nguyên văn context làm Khối 2.
- Model sinh Khối 3.

Thay đổi duy nhất về chiến lược nội dung nằm ở Khối 3:

1. Xác định chính xác khía cạnh được hỏi.
2. Chọn tập mệnh đề nhỏ nhất trực tiếp trả lời câu hỏi.
3. Giữ sát từ ngữ và thứ tự của context.
4. Chỉ giữ điều kiện, ngoại lệ, số liệu hoặc thủ tục trực tiếp giới hạn câu trả lời.
5. Không đưa mọi quy định trong cùng Điều/Khoản vào kết luận nếu câu hỏi chỉ hỏi một khía cạnh.
6. Không đặt giới hạn 120 từ; độ dài phụ thuộc số mệnh đề thực sự cần dùng.

## 2. Kết quả chính

| Model | METEOR V4 | METEOR V5 | METEOR V6 | Δ V6–V4 | ROUGE V6 | Số từ Khối 3 V6 |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3-0.6B | 0.7501 | 0.7487 | **0.7669** | **+0.0168** | 0.7903 | 59.3 |
| Qwen3-1.7B | **0.7774** | 0.7598 | 0.7543 | -0.0231 | 0.7692 | 69.4 |
| Qwen2.5-3B-Instruct | 0.7648 | 0.7584 | **0.7753** | **+0.0105** | **0.8140** | 67.9 |

Khối 3 chuẩn dài trung bình 86.1 từ. Cả 300/300 dự đoán V6 đều đủ ba khối sau bước sinh lại có mục tiêu.

V6-Qwen2.5 chỉ thấp hơn mức METEOR tốt nhất hiện có của V4-Qwen3-1.7B khoảng **0.0021**, nhưng đạt ROUGE cao nhất trong tất cả các lượt chạy.

## 3. Chỉ số riêng cho phần model sinh

| Model V6 | METEOR Khối 1+3 | METEOR riêng Khối 3 | ROUGE riêng Khối 3 | Tỷ lệ độ dài dự đoán/chuẩn |
|---|---:|---:|---:|---:|
| Qwen3-0.6B | 0.4442 | 0.3759 | 0.4440 | 1.108 |
| Qwen3-1.7B | 0.4425 | 0.3870 | 0.4394 | 1.469 |
| Qwen2.5-3B-Instruct | **0.4850** | **0.4487** | **0.5039** | 1.196 |

Qwen2.5-3B làm theo hướng dẫn V6 tốt nhất: kết luận ngắn hơn V5, gần độ dài chuẩn hơn và tăng đồng thời METEOR/ROUGE của phần kết luận.

## 4. Phân tích từng mẫu V4 → V6

| Model | Toàn đáp án tăng | Toàn đáp án giảm | Khối 3 tăng | Khối 3 giảm |
|---|---:|---:|---:|---:|
| Qwen3-0.6B | 65 | 34 | 42 | 57 |
| Qwen3-1.7B | 33 | 66 | 53 | 45 |
| Qwen2.5-3B-Instruct | 53 | 47 | **59** | **37** |

Qwen3-0.6B tăng điểm toàn đáp án dù điểm riêng Khối 3 giảm nhẹ. Điều này cho thấy cách sinh Khối 1 và tương tác của toàn chuỗi với METEOR cũng ảnh hưởng đáng kể; không thể tối ưu chỉ bằng điểm Khối 3.

## 5. Qwen2.5-3B theo độ dài đáp án chuẩn

| Nhóm Khối 3 chuẩn | Số câu | METEOR toàn đáp án V4 | V6 | METEOR Khối 3 V4 | V6 | Số từ sinh V6 | Số từ chuẩn |
|---|---:|---:|---:|---:|---:|---:|---:|
| ≤ 40 từ | 27 | 0.8466 | 0.8463 | 0.4860 | 0.4531 | 57.0 | 27.3 |
| 41–120 từ | 48 | 0.7873 | 0.7925 | 0.4458 | 0.4825 | 65.0 | 68.4 |
| > 120 từ | 25 | 0.6333 | **0.6658** | 0.2546 | **0.3789** | 85.2 | 183.6 |

V6 duy trì điểm của nhóm ngắn, tăng nhẹ ở nhóm trung bình và tăng mạnh ở nhóm dài. Đây là kết quả tốt hơn V5: V5 tăng độ dài rộng khắp, còn V6 tăng độ phủ có chọn lọc hơn.

Tuy nhiên, nhóm đáp án rất ngắn vẫn còn sinh dư: trung bình 57 từ cho đáp án chuẩn 27 từ. Đây là phần có thể tiếp tục tối ưu.

## 6. Qwen2.5-3B theo dạng câu hỏi

| Dạng câu hỏi | Số câu | METEOR toàn đáp án V4 | V6 | Nhận xét |
|---|---:|---:|---:|---|
| Chủ thể/ai | 9 | 0.8431 | **0.8517** | Tăng |
| Số liệu/thời hạn | 11 | 0.7168 | **0.7425** | Tăng rõ |
| Điều kiện/trường hợp | 8 | 0.7295 | 0.7294 | Gần như giữ nguyên |
| Trình tự/danh sách | 16 | 0.7592 | 0.7537 | Giảm nhẹ |
| Có/không | 21 | 0.7653 | 0.7588 | Giảm nhẹ |
| Nhóm còn lại | 35 | 0.7700 | **0.7963** | Tăng rõ |

V6 phù hợp nhất với câu hỏi cần lấy đúng thực thể, số liệu hoặc một kết luận trực tiếp. Với câu hỏi có/không, trình tự hoặc danh sách, yêu cầu “tập nhỏ nhất” đôi khi làm mất phần giải thích/điều kiện mà đáp án chuẩn vẫn giữ.

## 7. Vì sao Qwen3-1.7B giảm

Qwen3-1.7B không thực hiện chính sách độ dài ổn định như Qwen2.5:

- Nhóm đáp án chuẩn ≤ 40 từ vẫn sinh trung bình 85.2 từ.
- Nhóm đáp án chuẩn > 120 từ chỉ sinh trung bình 64.0 từ.
- Điểm giảm mạnh ở câu hỏi điều kiện và số liệu/thời hạn.
- 66/100 câu có METEOR toàn đáp án thấp hơn V4.

Vì vậy, lỗi không nằm ở ý tưởng giữ Khối 1 do model sinh. Nguyên nhân chính là prompt V6 không điều khiển được Qwen3-1.7B chọn đúng lượng mệnh đề: câu ngắn có lúc sinh dư, câu dài lại bỏ thiếu.

## 8. Khả năng kết hợp hai cấu hình tốt nhất

Hai ứng viên tốt nhất là:

- V4-Qwen3-1.7B: METEOR 0.7774.
- V6-Qwen2.5-3B: METEOR 0.7753, ROUGE 0.8140.

Xét riêng từng câu:

- V4-Qwen3-1.7B thắng 56 câu.
- V6-Qwen2.5-3B thắng 44 câu.
- Nếu có bộ chọn hoàn hảo, METEOR tối đa trên 100 mẫu này đạt khoảng 0.7992.

Một quy tắc thăm dò rất đơn giản — dùng V6-Qwen2.5 cho nhóm câu hỏi “khác”, dùng V4-Qwen3-1.7B cho các nhóm nhận dạng được — đạt khoảng 0.7826 trên chính validation. Con số này có nguy cơ overfit vì quy tắc được rút ra và chấm trên cùng một tập; phải kiểm tra trên một tập dev/validation độc lập trước khi dùng.

## 9. Kết luận và quyết định

1. **V6 thành công với Qwen2.5-3B và Qwen3-0.6B**, nhưng không cải thiện Qwen3-1.7B.
2. Nếu tiêu chí duy nhất là METEOR toàn đáp án, V4-Qwen3-1.7B vẫn đứng đầu với 0.7774.
3. V6-Qwen2.5 gần như hòa về METEOR, đồng thời có ROUGE tốt nhất và Khối 3 tốt nhất trong V6; đây là ứng viên rất đáng giữ.
4. Không nên áp dụng cùng một prompt cho mọi model rồi giả định phản ứng giống nhau.
5. Hướng tiếp theo có tiềm năng nhất là:
   - tinh chỉnh V6-Qwen2.5 riêng cho câu có/không và trình tự/danh sách;
   - hoặc xây bộ định tuyến giữa V4-Qwen3-1.7B và V6-Qwen2.5;
   - sau đó mới QLoRA trên cấu hình mục tiêu, học trực tiếp cặp câu hỏi + context → Khối 1 + Khối 3 chuẩn.

## 10. Chi phí chạy

- Thời gian toàn job: 3017.7 giây, khoảng 50.3 phút.
- GPU Kaggle: 2 × Tesla T4 15 GB.
- V5 mất khoảng 54.3 phút; V6 nhanh hơn khoảng 7.4%.

