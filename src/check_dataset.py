from pathlib import Path
import pandas as pd

# 1. Đường dẫn dataset
DATA_DIR = Path(r"E:\distrinet-cic-ids\data\raw")

# 2. Tìm tất cả file parquet
files = sorted(DATA_DIR.rglob("*.parquet"))

print("=" * 70)
print("KIỂM TRA DATASET DISTRINET-CIC-IDS2017")
print("=" * 70)

print(f"\nThư mục dataset: {DATA_DIR}")
print(f"Số file parquet tìm thấy: {len(files)}")


if len(files) == 0:
    print("\nKHÔNG TÌM THẤY FILE PARQUET!")
    print("Hãy kiểm tra lại đường dẫn.")
    raise SystemExit

# 3. Đọc từng file
for index, file in enumerate(files, start=1):

    print("\n" + "=" * 70)
    print(f"FILE {index}: {file.name}")
    print("=" * 70)

    try:
        df = pd.read_parquet(file)

        print(f"Số dòng : {df.shape[0]:,}")
        print(f"Số cột  : {df.shape[1]}")

        print("\nDanh sách cột:")

        for i, column in enumerate(df.columns, start=1):
            print(f"{i:02d}. {column}")

        # Tìm cột label
        label_columns = [
            column
            for column in df.columns
            if "label" in str(column).lower()
        ]

        print("\nCột có khả năng là LABEL:")
        print(label_columns)

        # Hiển thị phân bố label
        for label_column in label_columns:

            print(f"\nPhân bố nhãn [{label_column}]:")

            print(
                df[label_column]
                .value_counts(dropna=False)
                .to_string()
            )

        # Kiểm tra missing value
        missing = df.isna().sum().sum()

        print(f"\nTổng giá trị NaN: {missing:,}")

    except Exception as error:

        print("LỖI KHI ĐỌC FILE:")
        print(error)


print("\n" + "=" * 70)
print("HOÀN TẤT KIỂM TRA DATASET")
print("=" * 70)