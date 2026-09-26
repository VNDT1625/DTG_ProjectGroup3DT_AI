from pathlib import Path

import numpy as np
import pandas as pd


# CẤU HÌNH
PROJECT_DIR = Path(r"E:\distrinet-cic-ids")

RAW_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"

OUTPUT_FILE = PROCESSED_DIR / "cicids2017_binary.parquet"


DATA_FILES = {
    "Monday": "Benign-Monday.parquet",
    "Tuesday": "Bruteforce-Tuesday.parquet",
    "Wednesday": "DoS-Wednesday.parquet",
    "Thursday": "Infiltration-Webattacks-Thursday.parquet",
    "Friday": "Portscan-DDos-Botnet-Friday.parquet",
}

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# ĐỌC DATASET
dataframes = []
reference_columns = None

for day, filename in DATA_FILES.items():
    file_path = RAW_DIR / filename
    print("\n" + "=" * 70)
    print(f"Đang đọc: {filename}")
    print("=" * 70)
    if not file_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy file: {file_path}"
        )
    df_day = pd.read_parquet(file_path)
    print(f"Số dòng: {len(df_day):,}")
    print(f"Số cột : {len(df_day.columns)}")
    # Kiểm tra schema
    if reference_columns is None:
        reference_columns = list(df_day.columns)
    elif list(df_day.columns) != reference_columns:
        raise ValueError(
            f"Schema của {filename} không giống file đầu tiên."
        )
    # Thêm thông tin ngày nguồn
    df_day["SourceDay"] = day
    dataframes.append(df_day)

# GỘP 5 FILE
print("\n" + "=" * 70)
print("ĐANG GỘP 5 FILE")
print("=" * 70)

df = pd.concat(
    dataframes,
    ignore_index=True
)
print(f"Tổng số dòng: {len(df):,}")
print(f"Tổng số cột : {len(df.columns)}")

# KIỂM TRA LABEL
if "Label" not in df.columns:
    raise ValueError(
        "Không tìm thấy cột Label."
    )
print("\nPhân bố Label trước khi xử lý:")
print(
    df["Label"]
    .value_counts(dropna=False)
)

# LOẠI ATTEMPTED
attempted_mask = (
    df["Label"]
    .astype(str)
    .str.contains(
        "Attempted",
        case=False,
        na=False
    )
)
attempted_count = int(
    attempted_mask.sum()
)
print(
    f"\nSố dòng chứa 'Attempted': "
    f"{attempted_count:,}"
)
df = df.loc[
    ~attempted_mask
].copy()
print(
    f"Số dòng còn lại: "
    f"{len(df):,}"
)

# TẠO BINARY LABEL
df["BinaryLabel"] = (
    df["Label"]
    .astype(str)
    .str.strip()
    .str.casefold()
    .ne("benign")
    .astype("int8")
)
print("\nPhân bố BinaryLabel:")
print(
    df["BinaryLabel"]
    .value_counts()
    .sort_index()
)

# KIỂM TRA NaN
total_nan = int(
    df.isna().sum().sum()
)
print(
    f"\nTổng số NaN: "
    f"{total_nan:,}"
)

# KIỂM TRA INFINITY
numeric_columns = df.select_dtypes(
    include=[np.number]
).columns
inf_counts = {}
for column in numeric_columns:
    values = df[column].to_numpy()
    count = int(
        np.isinf(values).sum()
    )
    if count > 0:

        inf_counts[column] = count
print("\nCác cột chứa Infinity:")

if inf_counts:
    for column, count in inf_counts.items():
        print(
            f"{column}: "
            f"{count:,}"
        )

else:
    print(
        "Không phát hiện Infinity."
    )


# KIỂM TRA DUPLICATE
duplicate_check_columns = [
    column
    for column in df.columns
    if column not in [
        "SourceDay",
        "BinaryLabel"
    ]
]
duplicate_count = int(
    df.duplicated(
        subset=duplicate_check_columns
    ).sum()
)
print(
    f"\nSố dòng trùng hoàn toàn "
    f"theo dữ liệu gốc: "
    f"{duplicate_count:,}"
)

# THỐNG KÊ THEO NGÀY
day_summary = pd.crosstab(
    df["SourceDay"],
    df["BinaryLabel"]
)

print(
    "\nPhân bố BENIGN / ATTACK "
    "theo ngày:"
)
print(day_summary)

# LƯU FILE
df.to_parquet(
    OUTPUT_FILE,
    index=False
)

print("\n" + "=" * 70)
print("HOÀN TẤT PREPARE DATA")
print("=" * 70)
print(
    f"File đã lưu tại:\n"
    f"{OUTPUT_FILE}"
)
print(
    f"\nShape cuối cùng: "
    f"{df.shape}"
)