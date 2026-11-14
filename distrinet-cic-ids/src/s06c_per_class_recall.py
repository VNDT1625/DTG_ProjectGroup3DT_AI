"""Recall cua TUNG LOP cho thi nghiem 6.5 (tinh tu so TP/FP/FN/TN da luu, KHONG chay lai mo hinh).
  Recall Attack = TP / (TP + FN)  -> khong tinh duoc neu ngay kiem tra khong co tan cong (0/0)
  Recall Benign = TN / (TN + FP)  (= 1 - FPR)
Ket qua: reports/s06c_per_class_recall.csv, logs/s06c_per_class_recall.txt"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
th = pd.read_csv(ROOT / "reports" / "s06b_temporal_split_summary.csv", encoding="utf-8-sig")
th["So_dong_Attack"] = th.TP + th.FN
th["So_dong_Benign"] = th.TN + th.FP
th["Recall_Attack"] = th.apply(lambda r: r.TP / (r.TP + r.FN) if r.TP + r.FN > 0 else float("nan"), axis=1)
th["Recall_Benign"] = th.apply(lambda r: r.TN / (r.TN + r.FP) if r.TN + r.FP > 0 else float("nan"), axis=1)
cot = ["Luot", "Kiem_tra_tren", "Mo_hinh", "So_dong_Attack", "TP", "FN", "Recall_Attack",
       "So_dong_Benign", "TN", "FP", "Recall_Benign"]
th[cot].to_csv(ROOT / "reports" / "s06c_per_class_recall.csv", index=False, encoding="utf-8-sig")

lines = []
def out(s=""):
    print(s); lines.append(str(s))
for luot in th.Luot.unique():
    x = th[th.Luot == luot]
    out(f"===== {luot} (kiem tra {x.Kiem_tra_tren.iloc[0]}) =====")
    out("Bang 1 - Recall cua ATTACK = TP/(TP+FN)")
    for r in x.itertuples():
        v = "khong ap dung (0 dong tan cong)" if r.So_dong_Attack == 0 else f"{r.Recall_Attack*100:.4f}%"
        out(f"  {r.Mo_hinh:20s} so dong Attack={r.So_dong_Attack:>8,}  TP={r.TP:>8,}  FN={r.FN:>8,}  Recall={v}")
    out("Bang 2 - Recall cua BENIGN = TN/(TN+FP)")
    for r in x.itertuples():
        out(f"  {r.Mo_hinh:20s} so dong Benign={r.So_dong_Benign:>8,}  TN={r.TN:>8,}  FP={r.FP:>8,}  Recall={r.Recall_Benign*100:.4f}%")
    out()
(ROOT / "logs" / "s06c_per_class_recall.txt").write_text("\n".join(lines), encoding="utf-8")
