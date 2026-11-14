"""Bo sung FPR va FNR cho ket qua DA CO cua validation (Giai doan 5) va test (Giai doan 7).
CHI TINH TU CAC SO TP/FP/FN/TN DA LUU - KHONG mo lai tap test, KHONG du doan lai.
  FPR (ty le bao dong nham) = FP / (FP + TN)   - mau so: cac luong THUC TE binh thuong
  FNR (ty le bo sot)        = FN / (FN + TP)   - mau so: cac luong THUC TE la tan cong  (= 1 - Recall)
Ket qua: reports/s07b_fpr_fnr.csv, logs/s07b_fpr_fnr.txt"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REP, LOGS = ROOT / "reports", ROOT / "logs"
lines = []
def out(s=""):
    print(s); lines.append(str(s))

bang = []
for tap, f in (("Validation", "s05_model_comparison_val.csv"), ("Test", "s07_model_comparison_test.csv")):
    d = pd.read_csv(REP / f, encoding="utf-8-sig")
    for r in d.itertuples():
        tp, fp, fn, tn = int(r.TP), int(r.FP), int(r.FN), int(r.TN)
        bang.append({"Tap": tap, "Mo_hinh": r.Mo_hinh, "TP": tp, "FP": fp, "FN": fn, "TN": tn,
                     "FPR": fp / (fp + tn), "FNR": fn / (fn + tp), "Recall": tp / (tp + fn),
                     "Kiem_tra_FNR_bang_1_tru_Recall": abs(fn / (fn + tp) - (1 - tp / (tp + fn))) < 1e-12})
b = pd.DataFrame(bang)
assert b["Kiem_tra_FNR_bang_1_tru_Recall"].all()
b.drop(columns="Kiem_tra_FNR_bang_1_tru_Recall").to_csv(REP / "s07b_fpr_fnr.csv", index=False, encoding="utf-8-sig")

for tap in ("Validation", "Test"):
    x = b[b.Tap == tap]
    out(f"[{tap.upper()}]")
    out(f"{'Mo hinh':20s} {'FP':>6s} {'TN':>9s} {'FPR':>9s}   {'FN':>6s} {'TP':>7s} {'FNR':>9s}")
    for r in x.itertuples():
        out(f"{r.Mo_hinh:20s} {r.FP:>6,} {r.TN:>9,} {r.FPR*100:>8.4f}%   {r.FN:>6,} {r.TP:>7,} {r.FNR*100:>8.4f}%")
    out()
out("FPR = FP/(FP+TN): ty le luong binh thuong bi bao nham la tan cong.")
out("FNR = FN/(FN+TP): ty le luong tan cong bi bo sot. Da kiem tra: FNR = 1 - Recall.")
out("Da luu: reports/s07b_fpr_fnr.csv")
(LOGS / "s07b_fpr_fnr.txt").write_text("\n".join(lines), encoding="utf-8")
