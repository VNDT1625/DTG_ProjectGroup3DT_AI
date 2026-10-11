## 1. Giới thiệu dự án

Dự án sử dụng các đặc trưng của luồng lưu lượng mạng để nhận biết một luồng là **bình thường** hay **tấn công**. Ba mô hình được sử dụng:

| Mô hình | Vai trò | Ý nghĩa |
|---|---|---|
| **Logistic Regression (LR)** | Baseline 1 | Mô hình tuyến tính đơn giản, dễ dùng để so sánh. |
| **Random Forest (RF)** | Baseline 2 | Mô hình cây quyết định; cấu hình RF được lựa chọn bằng Temporal Cross-Validation. |
| **XGBoost** | Mô hình chính | Mô hình boosting cần đánh giá và so sánh với hai baseline. |

**Kết quả cần thu được:** Accuracy, Precision, Recall, F1-score, PR-AUC (Average Precision), ROC-AUC và số dự đoán sai FP/FN.

> **Lưu ý:** Đây là bài toán **phân loại nhị phân**, không phải phân loại tên từng kiểu tấn công. Một mẫu được gán nhãn tấn công khi nhãn ban đầu không phải `BENIGN` và không thuộc nhóm cần loại bỏ.

## 2. Bộ dữ liệu sử dụng

**Nguồn:** [DistriNet CIC-IDS2017 trên Kaggle](https://www.kaggle.com/datasets/dhoogla/distrinetcicids2017)

- Sử dụng **bản CIC-IDS2017 đã sửa lỗi của DistriNet**, ở định dạng **`.parquet`**.
- **Không sử dụng bản CIC-IDS2017 gốc** hoặc thay bằng một dataset cùng tên khác.
- Bộ dữ liệu gồm 5 tệp đại diện cho **thứ Hai đến thứ Sáu**; chương trình nhận biết ngày từ **tên tệp**.

### Quy tắc gán nhãn

| Nhãn ban đầu | Nhãn dùng cho mô hình |
|---|---:|
| `BENIGN` | `0` |
| Các nhãn tấn công khác | `1` |
| Nhãn có chứa `Attempted` | **Loại bỏ** |
| Nhãn rỗng hoặc thiếu | **Loại bỏ** |

Chương trình sử dụng các đặc trưng luồng mạng dạng **số**; không đưa nhãn, ngày thu thập, timestamp hoặc các trường định danh như IP/port vào bộ dự đoán. Với dữ liệu của lần chạy được trình bày trong README, chương trình phát hiện **82 đặc trưng số**.

## 3. Cấu trúc thư mục

Tối thiểu, dự án cần có cấu trúc như sau:

```text
cicids_vscode_project/
│
├── main.py                                    # Hàm đọc dữ liệu, tạo mô hình, đo chỉ số
├── step6_temporal_split_first.py             # Hàm hỗ trợ làm sạch sau chia tập
├── step13_stratified_then_temporal_cv_updated.py  # CHƯƠNG TRÌNH CHÍNH
├── requirements.txt                           # Danh sách thư viện
├── README.md                                  # Tài liệu này
│
├── data/
│   └── raw/
│       ├── Benign-Monday.parquet
│       ├── Bruteforce-Tuesday.parquet
│       ├── DoS-Wednesday.parquet
│       ├── Infiltration-Webattacks-Thursday.parquet
│       └── Portscan-DDos-Botnet-Friday.parquet
│
└── results/                                   # Kết quả được tạo tự động sau khi chạy
```

## 4. Cài đặt và chạy trong VS Code (Windows)

### Bước 1 — Cài Python và mở dự án

python --version


### Bước 2 — Tạo môi trường ảo

py -3 -m venv .venv

.\.venv\Scripts\Activate.ps1


### Bước 3 — Cài thư viện

python -m pip install --upgrade pip

python -m pip install -r requirements.txt


### Bước 4 — Tải dữ liệu

1. Mở link [dataset trên Kaggle](https://www.kaggle.com/datasets/dhoogla/distrinetcicids2017).
2. Tải và giải nén dataset.
3. Chép **đủ 5 file `.parquet`** vào thư mục `data/raw/`.
4. Giữ tên file có thông tin ngày; **không** dùng file `.csv` từ bản gốc để thay thế.

Có thể kiểm tra nhanh trong PowerShell:

```powershell
Get-ChildItem .\data\raw -Recurse -Filter *.parquet
```

### Bước 5 — Chạy quy trình chính (không đánh giá test)

```powershell
python step13_stratified_then_temporal_cv_updated.py --jobs 4
```

### Bước 6 — Xem kết quả Validation

```powershell
python -c "import pandas as pd; print(pd.read_csv('results/stratified_then_temporal_cv_diagnostics/validation_metrics.csv').to_string(index=False))"
```

### Bước 7 — Đánh giá Test (chỉ khi đã khóa mô hình)

```powershell
python step13_stratified_then_temporal_cv_updated.py --jobs 4 --evaluate-test
```

```powershell
python -c "import pandas as pd; print(pd.read_csv('results/stratified_then_temporal_cv_diagnostics/exploratory_test_metrics.csv').to_string(index=False))"
```


## 5. Quy trình xử lý dữ liệu và huấn luyện

Chương trình chính tuân theo thứ tự sau:

```text
5 file Parquet CIC-IDS2017 (DistriNet)
               │
               ▼
Bỏ nhãn Attempted/rỗng → mã hóa BENIGN=0, ATTACK=1
               │
               ▼
STRATIFIED SPLIT 70% / 15% / 15%  (seed = 42)
               │
       ┌───────┼───────────────┐
       ▼       ▼               ▼
   TRAIN 70%  VALIDATION 15%   TEST 15%
       │       │               │
       │       │           Giữ riêng
       ▼       │
Temporal CV trong TRAIN 70% để chọn RF
       │       │
       ▼       │
Làm sạch TRAIN, kiểm tra trùng bằng vector đặc trưng
       │       │
       ▼       ▼
Huấn luyện LR/RF/XGB → chọn ngưỡng trên VALIDATION
               │
               ▼
        Khóa cấu hình mô hình
               │
               ▼
     Đánh giá TEST (nếu bật cờ)
```