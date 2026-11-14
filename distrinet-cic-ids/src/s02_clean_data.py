"""Giai doan 2: LAM SACH - chi gom cac thao tac XU LY TUNG DONG / quy tac co dinh,
KHONG hoc bat ky thong ke nao tu du lieu => an toan khi lam truoc khi chia.
Thu tu: chuan hoa nhan -> bo 'Attempted' -> gan nhan 0/1 -> bo cot dinh danh
-> bo dong o trong/vo cuc (Cach 1) -> bo nhom mau thuan nhan -> bo dong trung.
Ket qua: data/processed/clean.parquet, models/feature_cols.json, logs/s02_cleaning.txt"""
import json, re
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, LOGS, MODELS = (ROOT / "data" / "raw", ROOT / "data" / "processed",
                          ROOT / "logs", ROOT / "models")
for d in (PROC, LOGS, MODELS):
    d.mkdir(parents=True, exist_ok=True)
lines = []
def out(s=""):
    print(s); lines.append(str(s))
def buoc(ten, truoc, sau):
    out(f"{ten:60s} {truoc:>10,} -> {sau:>10,}  (bo {truoc-sau:,})")

# 1. Doc du lieu goc (khong sua file goc)
frames = []
for f in sorted(RAW.glob("*.parquet")):
    d = pd.read_parquet(f); d["Ngay"] = f.stem; frames.append(d)
df = pd.concat(frames, ignore_index=True); del frames
out(f"Du lieu goc: {len(df):,} dong\n")

# 2. Chuan hoa nhan: bo khoang trang thua, gop khoang trang lien tiep
df["Label"] = df["Label"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)

# 3. Bo nhan co chu 'Attempted' (khong phan biet hoa/thuong)
n = len(df); df = df[~df["Label"].str.contains("attempted", case=False)]
buoc("Bo nhan chua 'Attempted'", n, len(df))

# 4. Gan nhan nhi phan: BENIGN (Benign) = 0, con lai = 1
df["y"] = (df["Label"].str.lower() != "benign").astype("int8")

# 5. Bo cot dinh danh (neu co) - quy tac theo TEN cot, khong hoc tu du lieu
META = ["Label", "y", "Ngay"]
pat = re.compile(r"(flow\s*id|\bip\b|src\s*ip|dst\s*ip|source\s*ip|destination\s*ip|port|timestamp|^id$)", re.I)
ident = [c for c in df.columns if c not in META and pat.search(c)]
df = df.drop(columns=ident)
out(f"{'Bo cot dinh danh':60s} {ident if ident else 'khong co cot nao'}")
FEAT = [c for c in df.columns if c not in META]
out(f"So cot dac trung con lai: {len(FEAT)}")

# 6. Cach 1: doi vo cuc thanh trong, roi BO dong co o trong
X = df[FEAT].replace([np.inf, -np.inf], np.nan)
bad = X.isna().any(axis=1)
n = len(df); df = df[~bad]
buoc("Bo dong co o trong/vo cuc (Cach 1)", n, len(df))

# 7. Bo cac nhom dac trung giong het nhau nhung NHAN 0/1 KHAC NHAU (mau thuan)
key = pd.util.hash_pandas_object(df[FEAT], index=False)
nun = df.groupby(key.values)["y"].transform("nunique").values
n = len(df); df = df[nun == 1]; key = key[nun == 1]
buoc("Bo nhom mau thuan nhan 0/1", n, len(df))

# 8. Bo dong trung (giong het dac trung + nhan 0/1), giu ban dau tien
dup = pd.Series(key.values).duplicated().values
n = len(df); df = df[~dup]
buoc("Bo dong trung lap", n, len(df))

# 9. Kiem tra va luu
df = df.reset_index(drop=True)
assert not df["Label"].str.contains("attempted", case=False).any()
assert not df.duplicated(subset=FEAT).any(), "Van con dong trung dac trung!"
assert not np.isinf(df[FEAT].to_numpy(dtype="float64")).any() and not df[FEAT].isna().any().any()
out(f"\nKET QUA: {len(df):,} dong, {len(FEAT)} dac trung")
out(f"  Nhan 0 (Benign): {(df.y==0).sum():,}   Nhan 1 (Tan cong): {(df.y==1).sum():,}   "
    f"Ty le tan cong: {df.y.mean()*100:.2f}%")
out("\nSo dong theo nhan chi tiet sau lam sach:")
out(df["Label"].value_counts().to_string())
df.to_parquet(PROC / "clean.parquet", index=False)
(MODELS / "feature_cols.json").write_text(json.dumps(FEAT, indent=2), encoding="utf-8")
out("\nDa luu: data/processed/clean.parquet, models/feature_cols.json")
out("Luu y: cot 'Label' (chi tiet) va 'Ngay' chi de PHAN TICH, KHONG dung de huan luyen.")
(LOGS / "s02_cleaning.txt").write_text("\n".join(lines), encoding="utf-8")
