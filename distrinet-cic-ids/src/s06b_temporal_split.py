"""Thi nghiem 6.5: CHIA THEO THOI GIAN (cua so truot 3 ngay) - CHI dung phan 70% TRAIN.
  Luot 1: hoc Thu Hai, Thu Ba, Thu Tu      -> kiem tra Thu Nam
  Luot 2: hoc Thu Ba, Thu Tu, Thu Nam      -> kiem tra Thu Sau
  Luot 3: hoc Thu Tu, Thu Nam, Thu Sau     -> kiem tra Thu Hai
          (Thu Hai chi co Benign: luot nay bao cao Recall (Benign) = TN/(TN+FP) va FPR.
           Luot 1-2 bao cao Recall (Attack) = TP/(TP+FN).
           Ve ban chat luot 3 hoc tu ngay SAU de doan ngay TRUOC, nen khong phai temporal theo nghia chat.)
Moi luot: hoc lai day chuyen tien xu ly + can bang du lieu TU DAU, chi tren 3 ngay hoc.
3 mo hinh giu DUNG cau hinh da chon o Giai doan 5 (khong chinh them). Nguong co dinh 0.5.
KHONG mo val.parquet / test.parquet. KHONG thay doi mo hinh cuoi cung hay ung dung.
Ket qua: reports/s06b_temporal_split_summary.csv, reports/s06b_temporal_split_by_label.csv,
         reports/s06b_temporal_split.png, logs/s06b_temporal_split.txt"""
import json, sys, time, warnings
from pathlib import Path
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import (average_precision_score, confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ids_pipeline import build_preprocess, fit_row_counts, SEED  # noqa: E402

SPLIT, MODELS, LOGS, REP = (ROOT / "data" / "processed" / "split", ROOT / "models", ROOT / "logs", ROOT / "reports")
NGUONG = 0.5

# ---- Chot chan: chi duoc doc train.parquet ----
_doc_goc = pd.read_parquet
def _doc_an_toan(path, *a, **k):
    assert Path(path).name == "train.parquet", f"KHONG DUOC DOC {Path(path).name} trong thi nghiem nay!"
    return _doc_goc(path, *a, **k)
pd.read_parquet = _doc_an_toan

lines = []
def out(s=""):
    print(s, flush=True); lines.append(str(s))

NGAY = {"Thu Hai": "Benign-Monday", "Thu Ba": "Bruteforce-Tuesday", "Thu Tu": "DoS-Wednesday",
        "Thu Nam": "Infiltration-Webattacks-Thursday", "Thu Sau": "Portscan-DDos-Botnet-Friday"}
LUOT = [("Luot 1", ["Thu Hai", "Thu Ba", "Thu Tu"], "Thu Nam"),
        ("Luot 2", ["Thu Ba", "Thu Tu", "Thu Nam"], "Thu Sau"),
        ("Luot 3", ["Thu Tu", "Thu Nam", "Thu Sau"], "Thu Hai")]
TEN_MH = ["LogisticRegression", "RandomForest", "XGBoost"]

t0 = time.time()
info = json.loads((MODELS / "preprocess_info.json").read_text(encoding="utf-8"))
FEAT = info["input_features"]
# Cau hinh mo hinh: lay dung tham so da chon o Giai doan 5 (chi lay cau hinh, khong lay trong so da hoc)
MAU_MH = {m: clone(joblib.load(MODELS / f"candidate_{m}.joblib").named_steps["model"]) for m in TEN_MH}
train = pd.read_parquet(SPLIT / "train.parquet")
out(f"Chi dung train.parquet: {len(train):,} dong | val va test: KHONG DOC | nguong co dinh {NGUONG}")
out("Cau hinh 3 mo hinh (tu Giai doan 5): " + "; ".join(
    f"{m} {dict((k, v) for k, v in MAU_MH[m].get_params().items() if k in ('C', 'max_depth', 'min_samples_leaf', 'n_estimators'))}"
    for m in TEN_MH))
out("\nSo dong moi ngay trong train: " + ", ".join(f"{d}={(train.Ngay == f).sum():,}" for d, f in NGAY.items()))


def can_bang(X, lab):
    cnt = pd.Series(lab).value_counts()
    if "Benign" in cnt:
        X, lab = RandomUnderSampler(sampling_strategy={"Benign": min(info["N_BENIGN_KEEP"], int(cnt["Benign"]))},
                                    random_state=SEED).fit_resample(X, lab)
    cnt = pd.Series(lab).value_counts()
    tgt = {c: info["MIN_PER_ATTACK"] for c, n in cnt.items() if c != "Benign" and 2 <= n < info["MIN_PER_ATTACK"]}
    if tgt:
        k = min(5, int(cnt[list(tgt)].min()) - 1)
        X, lab = SMOTE(sampling_strategy=tgt, k_neighbors=k, random_state=SEED).fit_resample(X, lab)
    return X, (pd.Series(lab) != "Benign").astype(int).to_numpy(), lab


tong_hop, theo_loai = [], []
for ten, ngay_hoc, ngay_kt in LUOT:
    out(f"\n{'=' * 90}\n{ten}: HOC tren {', '.join(ngay_hoc)}  ->  KIEM TRA tren {ngay_kt}")
    hoc = train[train.Ngay.isin([NGAY[d] for d in ngay_hoc])]
    kt = train[train.Ngay == NGAY[ngay_kt]]
    # Kiem tra chong ro ri
    assert ngay_kt not in ngay_hoc and set(hoc.Ngay).isdisjoint(set(kt.Ngay))
    assert not set(hoc.index) & set(kt.index)
    out(f"  Hoc: {len(hoc):,} dong ({hoc.y.mean()*100:.2f}% tan cong) | Kiem tra: {len(kt):,} dong "
        f"({kt.y.mean()*100:.2f}% tan cong)")
    pre = build_preprocess(k=info["K_FEATURES"], corr_threshold=info["CORR_THRESHOLD"])
    pre.fit(hoc[FEAT], hoc["y"])
    dem = fit_row_counts(pre)
    assert all(n is None or n == len(hoc) for n in dem.values()), dem
    out(f"  OK  Moi khau tien xu ly chi hoc tren {len(hoc):,} dong cua cac ngay hoc")
    Xb, yb, lb = can_bang(pre.transform(hoc[FEAT]), hoc["Label"].to_numpy())
    out(f"  OK  Can bang chi tren ngay hoc: {len(yb):,} dong ({yb.mean()*100:.1f}% tan cong); ngay kiem tra giu nguyen")
    Xk, yk, lk = pre.transform(kt[FEAT]), kt["y"].to_numpy(), kt["Label"].to_numpy()
    da_hoc = set(hoc["Label"]) - {"Benign"}
    co_tan_cong = yk.sum() > 0
    for m in TEN_MH:
        t1 = time.time()
        mh = clone(MAU_MH[m]).fit(Xb, yb)
        p = mh.predict_proba(Xk)[:, 1]
        pred = (p >= NGUONG).astype(int)
        tn, fp, fn, tp = confusion_matrix(yk, pred, labels=[0, 1]).ravel()
        r = {"Luot": ten, "Hoc_tren": ", ".join(ngay_hoc), "Kiem_tra_tren": ngay_kt, "Mo_hinh": m,
             "So_dong_kiem_tra": len(kt), "TP": int(tp), "FP": int(fp), "FN": int(fn), "TN": int(tn),
             "FPR": fp / (fp + tn) if fp + tn else np.nan}
        if co_tan_cong:
            r.update(Recall=recall_score(yk, pred), Precision=precision_score(yk, pred, zero_division=0),
                     F1=f1_score(yk, pred), FNR=fn / (fn + tp), PR_AUC=average_precision_score(yk, p),
                     ROC_AUC=roc_auc_score(yk, p))
        else:
            r.update(Recall=np.nan, Precision=np.nan, F1=np.nan, FNR=np.nan, PR_AUC=np.nan, ROC_AUC=np.nan)
            q = np.quantile(p, [0.5, 0.99, 0.999])
            r.update(XS_trung_vi=q[0], XS_phan_vi_99=q[1], XS_phan_vi_99_9=q[2], So_luong_XS_tren_0_9=int((p >= 0.9).sum()))
        r["Recall_Attack"] = r["Recall"]                              # TP/(TP+FN), khong tinh duoc neu 0 tan cong
        r["Recall_Benign"] = tn / (tn + fp) if tn + fp else np.nan   # TN/(TN+FP) = 1 - FPR
        r["Loai_Recall"] = "Attack" if co_tan_cong else "Benign"     # luot 1-2: Attack; luot 3: Benign
        r["Recall_chinh"] = r["Recall_Attack"] if co_tan_cong else r["Recall_Benign"]
        r["Giay"] = round(time.time() - t1, 1)
        tong_hop.append(r)
        if co_tan_cong:
            out(f"  {m:20s} Recall (Attack)={r['Recall_Attack']:.4f}  FNR={r['FNR']:.4f}  FPR={r['FPR']:.4f}  "
                f"F1={r['F1']:.4f}  PR-AUC={r['PR_AUC']:.4f}  ({r['Giay']}s)")
        else:
            out(f"  {m:20s} Recall (Benign)={r['Recall_Benign']*100:.4f}% ({tn:,}/{fp + tn:,} nhan dung)  "
                f"FPR={r['FPR']*100:.4f}% ({fp:,} luong bi bao nham)  "
                f"xac suat tan cong: trung vi {q[0]:.4f}, phan vi 99% {q[1]:.4f}  "
                f"[Recall (Attack), FNR, F1, PR-AUC: khong ap dung vi khong co tan cong]  ({r['Giay']}s)")
        for lab in sorted(set(lk) - {"Benign"}):
            msk = lk == lab
            theo_loai.append({"Luot": ten, "Mo_hinh": m, "Loai_tan_cong": lab, "So_dong": int(msk.sum()),
                              "Da_hoc_o_ngay_huan_luyen": "Đã học" if lab in da_hoc else "Chưa học",
                              "Ty_le_bat_duoc": float(pred[msk].mean())})
    if co_tan_cong:
        bl = pd.DataFrame([x for x in theo_loai if x["Luot"] == ten])
        bl = bl.pivot_table(index=["Loai_tan_cong", "Da_hoc_o_ngay_huan_luyen", "So_dong"], columns="Mo_hinh",
                            values="Ty_le_bat_duoc").reset_index()
        out("  Ty le bat duoc theo tung loai tan cong:")
        out("  " + bl.to_string(index=False, float_format=lambda v: f"{v:.3f}").replace("\n", "\n  "))

th = pd.DataFrame(tong_hop)
th.to_csv(REP / "s06b_temporal_split_summary.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(theo_loai).to_csv(REP / "s06b_temporal_split_by_label.csv", index=False, encoding="utf-8-sig")

# ---- Bieu do: 3 khung, moi khung 1 truc ----
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e6e5e0", "#fcfcfb"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
plt.rcParams.update({"font.size": 9.5, "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.titlecolor": INK, "figure.facecolor": SURF, "axes.facecolor": SURF,
                     "axes.spines.top": False, "axes.spines.right": False})
fig, axs = plt.subplots(1, 3, figsize=(13, 4.2))
VN = {"Thu Hai": "Thứ Hai", "Thu Ba": "Thứ Ba", "Thu Tu": "Thứ Tư", "Thu Nam": "Thứ Năm", "Thu Sau": "Thứ Sáu"}
nhan_luot = [f"{t.replace('Luot', 'Lượt')}\nkiểm tra {VN[k]}" for t, _, k in LUOT]
x = np.arange(len(LUOT)); w = 0.26
for ax, (cot, tieu_de) in zip(axs, [("Recall_chinh", "Recall (lượt 1–2: Attack; lượt 3: Benign)"),
                                    ("FNR", "FNR (tỉ lệ bỏ sót tấn công)"),
                                    ("FPR", "FPR (tỉ lệ báo động nhầm)")]):
    for i, m in enumerate(TEN_MH):
        v = [th[(th.Luot == t) & (th.Mo_hinh == m)][cot].iloc[0] for t, _, _ in LUOT]
        vv = [0 if np.isnan(a) else a * 100 for a in v]
        bars = ax.bar(x + (i - 1) * w, vv, w * 0.9, color=SERIES[i], label=m)
        if cot == "Recall_chinh":   # luot co Recall Benign: to soc de khong nham voi Recall Attack
            for b, (t, _, _) in zip(bars, LUOT):
                if th[th.Luot == t]["Loai_Recall"].iloc[0] == "Benign":
                    b.set_hatch("///"); b.set_edgecolor(SURF)
        for b, a in zip(bars, v):
            if not np.isnan(a):
                ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{a*100:.1f}",
                        ha="center", va="bottom", fontsize=7.5, color=INK2)
    for j, (t, _, _) in enumerate(LUOT):   # 1 nhan duy nhat cho luot khong tinh duoc chi so
        if th[(th.Luot == t)][cot].isna().all():
            ax.text(j, 0, "không áp dụng\n(không có tấn công)", ha="center", va="bottom", fontsize=8, color=MUTED)
    if cot == "Recall_chinh":
        ax.set_xticks(x, [f"{n}\nRecall {th[th.Luot == t]['Loai_Recall'].iloc[0]}" for n, (t, _, _) in zip(nhan_luot, LUOT)])
    else:
        ax.set_xticks(x, nhan_luot)
    ax.set_ylabel("%"); ax.set_title(tieu_de, loc="left", fontsize=10.5)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    ax.set_ylim(0, 108 if cot in ("Recall", "Recall_chinh") else max(5, ax.get_ylim()[1] * 1.15))
fig.legend(*axs[0].get_legend_handles_labels(), frameon=False, loc="upper right", ncol=3, labelcolor=INK2,
           bbox_to_anchor=(0.995, 1.0))
fig.suptitle("Thí nghiệm chia theo thời gian (cửa sổ 3 ngày, chỉ dùng tập train, ngưỡng 0,5)", x=0.01, ha="left",
             fontsize=12, color=INK)
fig.tight_layout(); fig.savefig(REP / "s06b_temporal_split.png", dpi=160, bbox_inches="tight", pad_inches=0.2); plt.close(fig)

out(f"\n{'=' * 90}\nTOM TAT")
for t, _, k in LUOT:
    x_ = th[th.Luot == t].set_index("Mo_hinh")
    if x_["Recall"].notna().any():
        out(f"  {t} (kiem tra {k}): Recall (Attack) XGBoost = {x_.loc['XGBoost', 'Recall_Attack']*100:.1f}%, "
            f"FPR XGBoost = {x_.loc['XGBoost', 'FPR']*100:.3f}%")
    else:
        out(f"  {t} (kiem tra {k}, toan Benign): Recall (Benign) XGBoost = {x_.loc['XGBoost', 'Recall_Benign']*100:.3f}%, "
            f"RandomForest = {x_.loc['RandomForest', 'Recall_Benign']*100:.3f}%, LogisticRegression = "
            f"{x_.loc['LogisticRegression', 'Recall_Benign']*100:.3f}%")
tl = pd.DataFrame(theo_loai)
for nhom in ("Đã học", "Chưa học"):
    s = tl[(tl.Mo_hinh == "XGBoost") & (tl.Da_hoc_o_ngay_huan_luyen == nhom)]
    if len(s):
        out(f"  XGBoost - loai tan cong {nhom.lower()}: ty le bat duoc trung binh (theo so dong) "
            f"{np.average(s.Ty_le_bat_duoc, weights=s.So_dong)*100:.1f}% tren {s.So_dong.sum():,} dong")
out("\nDa luu: reports/s06b_temporal_split_summary.csv, reports/s06b_temporal_split_by_label.csv, reports/s06b_temporal_split.png")
out(f"Thoi gian chay: {time.time()-t0:.0f} giay")
(LOGS / "s06b_temporal_split.txt").write_text("\n".join(lines), encoding="utf-8")
