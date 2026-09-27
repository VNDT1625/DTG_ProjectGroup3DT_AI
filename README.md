# DTG - CICIDS2017 Intrusion Detection System (IDS)

Dự án nghiên cứu và xây dựng hệ thống phát hiện xâm nhập mạng (Intrusion Detection System) sử dụng tập dữ liệu **CICIDS2017** kết hợp các mô hình Machine Learning.

## Cấu trúc thư mục dự án
```text
distrinet-cic-ids/
│
├── cicids2017_data/              # Chứa các file dữ liệu parquet (Thứ Hai đến Thứ Sáu)
│   ├── Benign-Monday.parquet
│   ├── Bruteforce-Tuesday.parquet
│   ├── DoS-Wednesday.parquet
│   ├── Infiltration-Webattacks-Thursday.parquet
│   └── Portscan-DDos-Botnet-Friday.parquet
│
├── results/                      # Kết quả huấn luyện và lưu trữ mô hình
│   ├── models/                   # Các file trọng số mô hình (.pkl)
│   │   ├── 1_Baseline_Logistic_Regression.pkl
│   │   ├── 2_Tabular_ML_1_Random_Forest.pkl
│   │   ├── 3_Tabular_ML_2_XGBoost.pkl
│   │   └── feature_columns.pkl
│   ├── model_results.csv         # Bảng tổng hợp đánh giá hiệu suất mô hình
│   └── test_predictions.csv      # Kết quả dự đoán trên tập test
│
├── train_model.ipynb             # Jupyter Notebook chính dùng để xử lý dữ liệu và huấn luyện
├── distrinetcicids2017.zip       # File nén dữ liệu gốc
└── README.md