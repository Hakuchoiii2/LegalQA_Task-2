# Thực nghiệm Retrieval + LLM trên Kaggle

Hai chế độ dùng chung generator V8.3 và bộ chấm METEOR/ROUGE-L của production:

- **Cached (mặc định):** QA package có sẵn → base/adapter → điểm từng câu và so sánh ghép cặp.
- **Retrieval đầy đủ:** corpus → parser B1 → BM25 + BGE-M3 → reranker BGE → QA package → cùng bộ thực nghiệm.

Kernel riêng: `htnkhi/dsc2026-legalqa-experiments`. Dataset input riêng, private:
`htnkhi/dsc2026-legalqa-experiments-inputs`. Không sửa kernel production.

## Chạy

Từ thư mục `DSC2026`, dùng Python có dependencies:

```powershell
python -m pip install 'kaggle>=1.7,<2'
$env:KAGGLE_ENABLE_OAUTH = 'true'
$env:PYTHONIOENCODING = 'utf-8'
# Build local để xem dữ liệu và kernel trước khi gửi
python legalQA_Task2/experiments/kaggle.py --output legalQA_Task2/experiments/build/pilot
# Gửi một build mới; input dataset mặc định được tạo private
python legalQA_Task2/experiments/kaggle.py --output legalQA_Task2/experiments/build/pilot-send --push
```

Lần sau dataset đã tồn tại: thêm `--update-dataset`. Mỗi build phải dùng thư mục
mới. Cấu hình tài khoản/adapter lấy từ `legalQA_Task2/kaggle/settings.json`.
CLI OAuth dùng phiên đăng nhập sẵn có; nếu chưa có, chạy `python -m kaggle.cli auth login`.
Không đưa token vào source, config hay notebook.

```powershell
python -m kaggle.cli kernels status htnkhi/dsc2026-legalqa-experiments
python -m kaggle.cli kernels output htnkhi/dsc2026-legalqa-experiments -p legalQA_Task2/experiments/downloads/result
```

`config.json` mặc định chọn ngẫu nhiên 20/800 câu với seed 2026, top-1,
base và adapter cùng greedy decoding, prompt/quality retry theo production.
Đây là pilot kiểm tra pipeline; không đủ để kết luận chất lượng toàn tập.
Muốn chạy toàn bộ: copy config sang `full.local.json`, đặt `limit: null`, truyền
`--config legalQA_Task2/experiments/full.local.json`. Không train lại.

## Retrieval đầy đủ trên Kaggle

```powershell
python legalQA_Task2/experiments/kaggle.py --retrieve --corpus "legalQA_Task2/LegalQA - Public Test-20260811T164022Z-1-001/LegalQA - Public Test/selected-contexts.zip" --output legalQA_Task2/experiments/build/retrieval --push --update-dataset
```

Chế độ này rebuild BM25/embedding trên Kaggle lần đầu, có thể tốn vài giờ.
Giữ nguyên corpus đầy đủ, không lấy mẫu corpus. `limit` chỉ giới hạn phần đánh giá;
retrieval chạy toàn bộ câu trong package input. Context mặc định mở rộng cả Điều
chứa Khoản top-1. Lưu tài nguyên vào `/kaggle/working/retrieval_cache` để tải về;
cache local được kiểm tra hash corpus/code trước khi tái sử dụng. Kernel mới
không tự gắn cache của phiên Kaggle cũ.

Chạy bridge riêng khi có tài nguyên local hoặc trong notebook:

```powershell
python legalQA_Task2/scripts/run_retrieval.py --questions questions.json --corpus corpus --cache cache --output packages.json --top-k 1 --expand-article
python legalQA_Task2/scripts/run_inference.py --input-json packages.json
```

`questions.json` nhận dict `{id: {question, answer}}` hoặc list QAPackage.
Bridge giữ nguyên code B trong `ChanTaooDe--main`, dùng lại hàm hybrid và B6.
Thêm `context_id`, `unit_id`, `covered_unit_ids` vào context để đo độ phủ nhãn.
Lưu thứ hạng đầy đủ vào file `.retrieval.jsonl` bên cạnh package. Reference chỉ
được gắn vào output, không tham gia retrieval/rerank hoặc prompt generator.

## Bổ sung dữ liệu cho các phép đo còn lại

Đường dẫn trong config tính từ thư mục chứa config. Builder tự copy các file
được chỉ định vào dataset input.

**Train–heldout:** `split_manifest` trỏ JSON:

```json
{"source": "đường dẫn/export training đã xác minh với adapter", "train_ids": ["31"], "heldout_ids": ["99"]}
```

Chỉ đưa vào `heldout_ids` các câu không dùng fine-tune, chọn checkpoint hoặc tune
prompt. Validation từng dùng chọn model không phải test độc lập. Runner chặn ID
trùng và câu hỏi giống nhau sau chuẩn hóa giữa train/heldout trong input. Không
có split → ghi `unverified`, gap bằng `null`. Cần kiểm tra near-duplicate và lịch
sử sử dụng dữ liệu bên ngoài runner; kiểm tra câu giống nhau chưa loại hết leakage.

**Nhãn retrieval:** `labels` trỏ dict theo ID:

```json
{"99": {"source": "manual corpus evidence", "gold_unit_ids": ["123_4_2", "456_3_1"]}}
```

Hit yêu cầu đủ mọi gold unit, kể cả các Khoản được bao phủ bởi context cả Điều.
Package cũ thiếu unit IDs sẽ có kết quả `unknown`, không suy từ điểm retrieval.
Đây là proxy độ phủ theo ID, không phải chứng minh suy luận đúng. Nếu generator
cắt context theo token budget thì bucket giữ `unknown`.

**Oracle:** `oracle_packages` trỏ list QAPackage cùng ID/question/reference với
retrieval, thêm `oracle_source` ghi nguồn bằng chứng. Context phải là đoạn luật
được xác minh; không dùng nguyên đáp án mẫu. Có thể cung cấp một tập con: báo
coverage và chỉ so sánh retrieved/oracle trên đúng giao các ID. Vẫn áp dụng cùng
`top_k`/budget; chuẩn bị đủ bằng chứng trong số context đó. Context lấy từ đáp án
cần ghi rõ nguồn và chỉ diễn giải là đối chứng có thông tin đáp án.

## Kết quả

Trong `/kaggle/working/experiment_results/`:

- `manifest.json`: trạng thái, ID được chọn, hash input/source/adapter, split,
  cấu hình generation, thời gian và dữ liệu còn thiếu.
- `{base,adapter}_{retrieved,oracle}.jsonl`: đáp án, context, trace generation,
  điểm từng câu, bucket hit/miss × high/low, nguồn nhãn và cờ cắt context.
- `*_answers.json`: đáp án theo schema cuộc thi.
- `*_summary.json`: điểm và bootstrap CI 95%, gap train–heldout khi đủ dữ liệu;
  điểm phần mở/kết riêng khi tách được reference với confidence cao.
- `comparisons.json`: delta adapter−base và oracle−retrieved ghép cặp theo ID,
  bootstrap CI 95% (1.000 lượt).

`score_threshold=0.5` chỉ chia METEOR cao/thấp để xem lỗi, **không phải nhãn đúng/sai**.
Ngưỡng này chưa hiệu chuẩn. Không diễn giải generalization gap là “lượng học vẹt”.
Điểm toàn đáp án bao gồm đoạn luật được chép từ context, nên cần xem cả điểm mở/kết.
Mỗi câu được flush ra đĩa; job lỗi giữ các câu đã xong và manifest failed. Không
tự resume; chạy lại dùng output mới.

## Kiểm tra local

```powershell
python -m unittest discover -s legalQA_Task2/experiments -p "test_*.py" -v
python -m unittest discover -s legalQA_Task2/tests -v
```

Kết quả local kiểm tra logic và build, không thay thế kiểm tra GPU thực tế.

## Kiểm tra dữ liệu ngày 17/09/2026

File `qa_packages_heldout_2026-08-31.json` có 800 câu và reference đầy đủ. Đối
chiếu dataset Kaggle `htnkhi/dsc2026-legalqa-qlora-v8-data`: 261 ID nằm trong
train, 31 trong validation. Chưa xác minh dataset này là toàn bộ dữ liệu của
adapter production hiện tại; không tự gán 508 câu còn lại là heldout.
`oracle_context.source_type` của dữ liệu QLoRA là `oracle_from_reference`.
Do đó cấu hình mặc định để cả split, nhãn retrieval và oracle là null.
