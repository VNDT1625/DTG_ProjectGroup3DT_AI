"""Giai doan 3: CHIA 70/15/15 co stratify (giu ty le nhan).
Stratify theo nhan chi tiet => tu dong giu ty le nhan nhi phan 0/1 va moi loai tan cong hiem
deu co mat o ca 3 phan. random_state = 42 de tai lap.
Ket qua: data/processed/split/{train,val,test}.parquet, data/processed/split/hashes.json"""
import json, hashlib
from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split

SEED = 42
ROOT = Path(__file__).resolve().parents[1]
PROC, LOGS = ROOT / "data" / "processed", ROOT / "logs"
SPLIT = PROC / "split"; SPLIT.mkdir(parents=True, exist_ok=True)
lines = []
def out(s=""):
    print(s); lines.append(str(s))

df = pd.read_parquet(PROC / "clean.parquet")
FEAT = json.loads((ROOT / "models" / "feature_cols.json").read_text(encoding="utf-8"))
out(f"Du lieu sach: {len(df):,} dong")

# Lan 1: 70% train / 30% con lai
train, tmp = train_test_split(df, test_size=0.30, stratify=df["Label"], random_state=SEED)
# Lan 2: chia doi 30% -> 15% val / 15% test
val, test = train_test_split(tmp, test_size=0.50, stratify=tmp["Label"], random_state=SEED)
del tmp

parts = {"train": train, "val": val, "test": test}
out("\n[KICH THUOC VA TY LE]")
for k, d in parts.items():
    out(f"  {k:5s}: {len(d):>9,} dong ({len(d)/len(df)*100:5.2f}%)  "
        f"nhan 1 = {d.y.sum():>7,}  ty le tan cong = {d.y.mean()*100:.3f}%")

# KIEM TRA TU DONG
out("\n[KIEM TRA CHONG RO RI]")
assert len(train) + len(val) + len(test) == len(df); out("  OK  Tong 3 phan = so dong ban dau")
ids = [set(d.index) for d in parts.values()]
assert not (ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2]); out("  OK  Khong dong nao (theo chi so) nam o 2 phan")
h = {k: set(pd.util.hash_pandas_object(d[FEAT], index=False).values) for k, d in parts.items()}
ov = {"train-val": len(h["train"] & h["val"]), "train-test": len(h["train"] & h["test"]),
      "val-test": len(h["val"] & h["test"])}
assert sum(ov.values()) == 0, ov; out(f"  OK  Khong co dong trung NOI DUNG giua cac phan {ov}")
r = [d.y.mean() for d in parts.values()]
assert max(r) - min(r) < 0.001; out("  OK  Ty le tan cong 3 phan chenh nhau < 0.1%")

out("\n[SO DONG THEO LOAI TAN CONG]")
tab = pd.DataFrame({k: d["Label"].value_counts() for k, d in parts.items()}).fillna(0).astype(int)
out(tab.to_string())
tab.to_csv(ROOT / "reports" / "s03_label_distribution.csv", encoding="utf-8-sig")

# Luu va ghi dau van tay
hashes = {}
for k, d in parts.items():
    f = SPLIT / f"{k}.parquet"
    d.reset_index(drop=True).to_parquet(f, index=False)
    hashes[k] = hashlib.sha256(f.read_bytes()).hexdigest()
(SPLIT / "hashes.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
out(f"\nDa luu train/val/test vao data/processed/split/ va dau van tay vao hashes.json")
out(f"Hash test (de kiem tra test khong bi sua): {hashes['test'][:16]}...")
out("TU DAY: file test.parquet bi KHOA, chi mo 1 lan o Giai doan 7.")
(LOGS / "s03_split.txt").write_text("\n".join(lines), encoding="utf-8")
