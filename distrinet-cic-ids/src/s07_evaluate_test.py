"""Giai doan 7: DANH GIA CUOI CUNG TREN TEST - CHI CHAY MOT LAN.
- Kiem tra dau van tay (hash) cua test.parquet: phai trung voi luc chia o Giai doan 3.
- Neu da tung chay (co models/test_lock.json) -> KHONG danh gia lai, chi in lai ket qua cu.
- Danh gia mo hinh cuoi cung (models/final_model.joblib) voi nguong da chon tren validation.
- 2 mo hinh con lai cung duoc cham tren test de so sanh trong bao cao (khong dung de chon).
Ket qua: reports/s07_*.csv, reports/s07_*.png, models/test_lock.json, logs/s07_test_evaluation.txt"""
import hashlib, json, sys, time, warnings
from datetime import datetime
from pathlib import Path
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, average_precision_score, confusion_matrix, f1_score,
                             precision_recall_curve, precision_score, recall_score, roc_auc_score, roc_curve)

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import ids_pipeline  # noqa: F401,E402

SPLIT, MODELS, LOGS, REP = ROOT / "data" / "processed" / "split", ROOT / "models", ROOT / "logs", ROOT / "reports"
LOCK = MODELS / "test_lock.json"
LOGF = LOGS / "s07_test_evaluation.txt"

# ---- Khoa: chi chay 1 lan ----
if LOCK.exists():
    print("TEST DA DUOC DANH GIA TRUOC DO - KHONG CHAY LAI (de dam bao chi dung test 1 lan).")
    print(json.loads(LOCK.read_text(encoding="utf-8")))
    if LOGF.exists():
        print("\n" + LOGF.read_text(encoding="utf-8"))
    sys.exit(0)

lines = []
def out(s=""):
    print(s, flush=True); lines.append(str(s))

# ---- Kiem tra test khong bi sua ----
f_test = SPLIT / "test.parquet"
h_now = hashlib.sha256(f_test.read_bytes()).hexdigest()
h_saved = json.loads((SPLIT / "hashes.json").read_text(encoding="utf-8"))["test"]
assert h_now == h_saved, "DAU VAN TAY TEST KHONG KHOP - file test da bi thay doi, DUNG LAI!"
out(f"OK  Dau van tay test khop voi luc chia ({h_now[:16]}...) => test chua bi sua")

t0 = time.time()
final = joblib.load(MODELS / "final_model.joblib")
FEAT, thr, name = final["input_features"], final["threshold"], final["model_name"]
test = pd.read_parquet(f_test)
y, lab = test["y"].to_numpy(), test["Label"].to_numpy()
out(f"Mo test lan dau luc {datetime.now():%Y-%m-%d %H:%M:%S} | {len(test):,} dong | ty le tan cong {y.mean()*100:.2f}%")
out(f"Mo hinh: {name} | nguong {thr:.4f} (chon tren validation, KHONG chinh lai)\n")


def metrics(y, p, thr):
    pred = (p >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {"Accuracy": accuracy_score(y, pred), "Precision": precision_score(y, pred, zero_division=0),
            "Recall": recall_score(y, pred), "F1": f1_score(y, pred), "ROC_AUC": roc_auc_score(y, p),
            "PR_AUC": average_precision_score(y, p), "Ty_le_bao_nham_FPR": fp / (fp + tn), "Ty_le_bo_sot_FNR": fn / (fn + tp),
            "TP": int(tp), "FP": int(fp), "FN": int(fn), "TN": int(tn)}


# ---- Mo hinh cuoi cung ----
p = final["pipeline"].predict_proba(test[FEAT])[:, 1]
m = metrics(y, p, thr)
out("[KET QUA MO HINH TREN TEST]")
for k, v in m.items():
    out(f"  {k:20s} {v:.4f}" if isinstance(v, float) else f"  {k:20s} {v:,}")
pred = (p >= thr).astype(int)

# ---- Theo tung loai ----
per = (pd.DataFrame({"Label": lab, "dung": pred == y}).groupby("Label")
       .agg(So_dong=("dung", "size"), Ty_le_dung=("dung", "mean")).sort_values("So_dong", ascending=False))
per.to_csv(REP / "s07_accuracy_by_label_test.csv", encoding="utf-8-sig")
out("\n[TY LE DOAN DUNG THEO TUNG LOAI - TEST]")
out(per.to_string(float_format=lambda v: f"{v:.4f}"))

# ---- 2 mo hinh con lai (KHONG dung de chon) ----
rows = [{"Mo_hinh": name, "Nguong": thr, **m}]
probs = {name: p}
val_cmp = pd.read_csv(REP / "s05_model_comparison_val.csv")
for cname in val_cmp["Mo_hinh"]:  # chi 3 mo hinh da so sanh o Giai doan 5
    f = MODELS / f"candidate_{cname}.joblib"
    if cname == name or not f.exists():
        continue
    cthr = float(val_cmp.loc[val_cmp.Mo_hinh == cname, "Nguong_toi_uu"].iloc[0])
    cp = joblib.load(f).predict_proba(test[FEAT])[:, 1]
    probs[cname] = cp
    rows.append({"Mo_hinh": cname, "Nguong": cthr, **metrics(y, cp, cthr)})
cmp_ = pd.DataFrame(rows)
cmp_.to_csv(REP / "s07_model_comparison_test.csv", index=False, encoding="utf-8-sig")
out("\n[CA 3 MO HINH TREN TEST - nguong cua moi mo hinh deu chon tren validation]")
out(cmp_[["Mo_hinh", "PR_AUC", "ROC_AUC", "F1", "Precision", "Recall", "Ty_le_bao_nham_FPR", "Ty_le_bo_sot_FNR"]]
    .to_string(index=False, float_format=lambda v: f"{v:.4f}"))

# ---- Bieu do (anh PNG cho bao cao) ----
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e6e5e0", "#fcfcfb"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]  # thu tu co dinh: xanh, cam, xanh ngoc
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.titlecolor": INK, "figure.facecolor": SURF,
                     "axes.facecolor": SURF, "axes.spines.top": False, "axes.spines.right": False})

# 1. Ma tran nham lan
cm = confusion_matrix(y, pred, labels=[0, 1])
fig, ax = plt.subplots(figsize=(6, 4.6))
ax.imshow(cm / cm.sum(axis=1, keepdims=True), cmap=matplotlib.colors.LinearSegmentedColormap.from_list(
    "b", ["#cde2fb", "#1c5cab"]), vmin=0, vmax=1)
for i in range(2):
    for j in range(2):
        frac = cm[i, j] / cm[i].sum()
        ax.text(j, i, f"{cm[i, j]:,}\n({frac*100:.2f}%)", ha="center", va="center",
                color="#ffffff" if frac > 0.5 else INK, fontsize=11)
ax.set_xticks([0, 1], ["Dự đoán: Bình thường", "Dự đoán: Tấn công"])
ax.set_yticks([0, 1], ["Thực tế: Bình thường", "Thực tế: Tấn công"])
ax.set_title(f"Ma trận nhầm lẫn trên tập test – {name}", loc="left")
for s in ax.spines.values():
    s.set_visible(False)
fig.tight_layout(); fig.savefig(REP / "s07_confusion_matrix.png", dpi=160, bbox_inches="tight", pad_inches=0.2); plt.close(fig)

# 2. Duong ROC va 3. Duong Precision-Recall (moi bieu do 1 truc)
for kind in ("ROC", "PR"):
    fig, ax = plt.subplots(figsize=(5.6, 4.4))
    for i, (cn, cp) in enumerate(probs.items()):
        if kind == "ROC":
            fx, fy, _ = roc_curve(y, cp); sc = roc_auc_score(y, cp)
        else:
            pr_, rc_, _ = precision_recall_curve(y, cp); fx, fy = rc_, pr_; sc = average_precision_score(y, cp)
        ax.plot(fx, fy, color=SERIES[i], lw=2, label=f"{cn} ({kind}-AUC = {sc:.4f})")
    if kind == "ROC":
        ax.set_xscale("log"); ax.set_xlim(1e-5, 1)
        ax.set_xlabel("Tỉ lệ báo động nhầm (thang log)"); ax.set_ylabel("Tỉ lệ bắt được tấn công")
        ax.set_title("Đường ROC trên tập test", loc="left")
    else:
        ax.set_xlabel("Recall (tỉ lệ bắt được tấn công)"); ax.set_ylabel("Precision (độ chính xác cảnh báo)")
        ax.set_title("Đường Precision–Recall trên tập test", loc="left")
    ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="lower left" if kind == "PR" else "lower right", labelcolor=INK2)
    fig.tight_layout(); fig.savefig(REP / f"s07_{kind.lower()}_curve.png", dpi=160, bbox_inches="tight", pad_inches=0.2); plt.close(fig)

# 4. Ty le doan dung theo tung loai
pp = per.sort_values("Ty_le_dung")
fig, ax = plt.subplots(figsize=(7, 0.36 * len(pp) + 1.2))
ax.barh(range(len(pp)), pp["Ty_le_dung"] * 100, color=SERIES[0], height=0.6)
ax.set_yticks(range(len(pp)), [f"{l} (n={n:,})" for l, n in zip(pp.index, pp["So_dong"])])
for i, v in enumerate(pp["Ty_le_dung"] * 100):
    ax.text(min(v, 100) + 0.3, i, f"{v:.2f}%", va="center", color=INK2, fontsize=9)
ax.set_xlim(0, 108); ax.set_xlabel("Tỉ lệ đoán đúng (%)")
ax.set_title(f"Tỉ lệ đoán đúng theo từng loại trên tập test – {name}", loc="left")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
fig.tight_layout(); fig.savefig(REP / "s07_accuracy_by_label.png", dpi=160, bbox_inches="tight", pad_inches=0.2); plt.close(fig)

out("\nDa luu bieu do: reports/s07_confusion_matrix.png, s07_roc_curve.png, s07_pr_curve.png, s07_accuracy_by_label.png")
LOCK.write_text(json.dumps({"thoi_diem_mo_test": datetime.now().isoformat(timespec="seconds"),
                            "mo_hinh": name, "nguong": thr, "hash_test": h_now,
                            "ket_qua": {k: (round(v, 6) if isinstance(v, float) else v) for k, v in m.items()}},
                           indent=2, ensure_ascii=False), encoding="utf-8")
out("Da khoa: models/test_lock.json - tu nay script nay se KHONG danh gia lai test.")
out(f"Thoi gian chay: {time.time()-t0:.0f} giay")
LOGF.write_text("\n".join(lines), encoding="utf-8")
