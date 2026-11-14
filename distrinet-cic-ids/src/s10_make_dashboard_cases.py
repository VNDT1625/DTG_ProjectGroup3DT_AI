"""A3 - Tao 2 file mau cho cac truong hop dac biet cua giao dien (lay tu demo_labeled.csv):
  case_no_attack.csv   : chi gom 4.000 dong Benign -> giao dien phai bao "khong phat hien tan cong"
  case_all_invalid.csv : 200 dong, moi dong deu co o loi (vo cuc / trong / chu) -> giao dien phai bao loi ro rang
Truong hop "co tan cong" dung luon demo_labeled.csv."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MAU = ROOT / "data" / "samples"
demo = pd.read_csv(MAU / "demo_labeled.csv")

khong_tc = demo[demo["Label"] == "Benign"]
khong_tc.to_csv(MAU / "case_no_attack.csv", index=False)

loi = demo.head(200).copy()
loi["Flow Bytes/s"] = loi["Flow Bytes/s"].astype(object)
loi.loc[loi.index[0::3], "Flow Bytes/s"] = np.inf
loi.loc[loi.index[1::3], "Flow Bytes/s"] = np.nan
loi.loc[loi.index[2::3], "Flow Bytes/s"] = "abc"
loi.to_csv(MAU / "case_all_invalid.csv", index=False)

print(f"Da tao data/samples/case_no_attack.csv ({len(khong_tc):,} dong, toan Benign)")
print(f"Da tao data/samples/case_all_invalid.csv ({len(loi):,} dong, dong nao cung loi)")
