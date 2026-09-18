"""
Đường dẫn & hằng số dùng chung cho toàn bộ pipeline.

Mọi module khác PHẢI import path từ đây, không hardcode path riêng —
để khi cấu trúc data/ đổi (vd có thêm private-official.json), chỉ sửa 1 chỗ.
"""
from pathlib import Path

# Gốc project = 2 cấp trên file này (src/common/config.py -> src/ -> PROJECT/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
# Trước đây trỏ vào path lồng 2 cấp trùng tên "data/selected-contexts/selected-contexts/"
# (nguyên trạng cấu trúc zip gốc của BTC) qua 1 symlink "data/corpus" từng bị
# hỏng (Input/output error) giữa 2 phiên do sync Windows<->sandbox không giữ
# được symlink (xem docs/EXPERIMENT_LOG.md entry [Infra] 06/08). Đã dọn dẹp
# 20/08: MOVE thật (không phải symlink) nội dung ra "data/corpus/" cho gọn —
# không còn rủi ro symlink vỡ vì đây là thư mục thật.
CORPUS_DIR = DATA_DIR / "corpus"

TRAIN_PATH = DATA_DIR / "train.json"
WARMUP_PATH = DATA_DIR / "warmup.json"
PUBLIC_OFFICIAL_PATH = DATA_DIR / "public-official.json"
# PRIVATE_OFFICIAL_PATH sẽ thêm khi BTC cấp (xem docs/DATA_NOTES.md mục 5)

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
EXPERIMENTS_DIR = PROJECT_ROOT / "experiments"

# Ngưỡng confidence B0 (giá trị khởi điểm theo handoff mục 5.B0 — CHƯA hiệu chỉnh bằng data thật)
B0_CONFIDENCE_DROP = 0.3
B0_CONFIDENCE_TRUST = 0.6

# Chuỗi rác biết trước cần lọc khi làm sạch passage (xem docs/DATA_NOTES.md mục 3)
KNOWN_NOISE_MARKERS = [
    "Bạn phải đăng nhập hoặc đăng ký Thành Viên TVPL Pro",
]
