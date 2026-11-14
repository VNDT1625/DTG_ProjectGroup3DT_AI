"""Giai doan 1: XEM TONG QUAN du lieu tho (chi doc, khong sua, khong quyet dinh).
Ket qua: logs/s01_overview.txt, reports/s01_*.csv, logs/s01_schema.json"""
import json, re, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, LOGS, REP = ROOT / "data" / "raw", ROOT / "logs", ROOT / "reports"
LOGS.mkdir(exist_ok=True); REP.mkdir(exist_ok=True)
lines = []
def out(s=""):
    print(s); lines.append(str(s))

t0 = time.time()
frames = []
for f in sorted(RAW.glob("*.parquet")):
    d = pd.read_parquet(f)
    d["__ngay__"] = f.stem
    frames.append(d)
    out(f"Doc {f.name}: {len(d):,} dong x {d.shape[1]-1} cot")
df = pd.concat(frames, ignore_index=True)
del frames
out(f"\nTONG: {len(df):,} dong x {df.shape[1]-1} cot (chua tinh cot __ngay__)")
out(f"Bo nho: {df.memory_usage(deep=True).sum()/2**30:.2f} GB")

# --- Cot va kieu du lieu
schema = {c: str(t) for c, t in df.dtypes.items() if c != "__ngay__"}
(LOGS / "s01_schema.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
out("\n[KIEU DU LIEU] " + str(pd.Series(schema).value_counts().to_dict()))
non_num = [c for c, t in schema.items() if not pd.api.types.is_numeric_dtype(df[c])]
out(f"Cot khong phai so: {non_num}")

# --- Cot nhan
label_col = next((c for c in df.columns if c.strip().lower() == "label"), None)
out(f"\nCot nhan: {label_col!r}")
lab = df[label_col].astype(str)
out("Cac gia tri nhan (nguyen ban, co ca khoang trang/hoa thuong):")
vc = lab.value_counts()
for k, v in vc.items():
    out(f"  {k!r:45s} {v:>10,}")
pd.crosstab(lab, df["__ngay__"]).to_csv(REP / "s01_labels_by_day.csv", encoding="utf-8-sig")
att = lab.str.contains("attempted", case=False)
out(f"So dong co chu 'Attempted': {att.sum():,}")

# --- Cot dinh danh nghi ngo
pat = re.compile(r"(flow\s*id|ip|port|timestamp|time\s*stamp|^id$)", re.I)
ident = [c for c in df.columns if pat.search(c)]
out(f"\n[COT DINH DANH NGHI NGO] {ident if ident else 'KHONG CO'}")

# --- O trong va vo cuc (chi dem)
feat = [c for c in df.columns if c not in (label_col, "__ngay__")]
num = [c for c in feat if pd.api.types.is_numeric_dtype(df[c])]
nan_c = df[feat].isna().sum()
inf_c = pd.Series({c: int(np.isinf(df[c].to_numpy(dtype="float64", na_value=np.nan)).sum()) for c in num})
bad = pd.DataFrame({"o_trong": nan_c, "vo_cuc": inf_c}).fillna(0).astype(int)
bad = bad[(bad.o_trong > 0) | (bad.vo_cuc > 0)]
out("\n[O TRONG / VO CUC THEO COT]")
out(bad.to_string() if len(bad) else "  Khong co")
row_bad = df[feat].isna().any(axis=1)
for c in num:
    row_bad |= np.isinf(df[c].to_numpy(dtype="float64", na_value=np.nan))
out(f"So dong co it nhat 1 o trong/vo cuc: {row_bad.sum():,} ({row_bad.mean()*100:.4f}%)")
if row_bad.any():
    out("Phan bo theo nhan cua cac dong nay:")
    out(lab[row_bad].value_counts().to_string())

# --- Trung lap (chi dem)
dup_all = df.duplicated(subset=feat + [label_col]).sum()
dup_feat = df.duplicated(subset=feat).sum()
out(f"\n[TRUNG LAP]")
out(f"Dong trung hoan toan (dac trung + nhan), tinh ban thu 2 tro di: {dup_all:,} ({dup_all/len(df)*100:.2f}%)")
out(f"Dong trung dac trung (bat ke nhan): {dup_feat:,}")
g = df.groupby(feat, dropna=False, sort=False)[label_col].nunique()
conflict_groups = int((g > 1).sum())
out(f"Nhom dac trung giong nhau nhung NHAN KHAC NHAU (mau thuan): {conflict_groups:,}")

# --- Mo ta so lieu tung cot (de tham khao)
df[num].describe().T.to_csv(REP / "s01_column_stats.csv", encoding="utf-8-sig")
out(f"\nDa luu: reports/s01_labels_by_day.csv, reports/s01_column_stats.csv, logs/s01_schema.json")
out(f"Thoi gian chay: {time.time()-t0:.0f} giay")
(LOGS / "s01_overview.txt").write_text("\n".join(lines), encoding="utf-8")
