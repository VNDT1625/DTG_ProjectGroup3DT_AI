"""Tao file CSV mau de thu ung dung (lay tu tap TEST - test da danh gia xong va da khoa).
Ket qua: data/samples/demo_labeled.csv, data/samples/demo_unlabeled.csv"""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MAU = ROOT / "data" / "samples"; MAU.mkdir(parents=True, exist_ok=True)
assert (ROOT / "models" / "test_lock.json").exists(), "Chi tao file mau SAU khi da danh gia test (Giai doan 7)."
FEAT = json.loads((ROOT / "models" / "feature_cols.json").read_text(encoding="utf-8"))
test = pd.read_parquet(ROOT / "data" / "processed" / "split" / "test.parquet")
# Lay 4.000 dong Benign + toi da 150 dong moi loai tan cong (lay het loai hiem)
parts = [test[test.Label == "Benign"].sample(4000, random_state=1)]
for lab, g in test[test.Label != "Benign"].groupby("Label"):
    parts.append(g.sample(min(len(g), 150), random_state=1))
demo = pd.concat(parts).sample(frac=1, random_state=1)[FEAT + ["Label"]]
demo.to_csv(MAU / "demo_labeled.csv", index=False)
demo[FEAT].to_csv(MAU / "demo_unlabeled.csv", index=False)
print(f"Da tao data/samples/demo_labeled.csv ({len(demo):,} dong, co cot Label)")
print(f"Da tao data/samples/demo_unlabeled.csv ({len(demo):,} dong, khong co cot Label)")
print(demo["Label"].value_counts().to_string())
