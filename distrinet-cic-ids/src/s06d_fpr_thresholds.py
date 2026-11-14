"""Thi nghiem 6.6: NGUONG THEO FPR trong thi nghiem chia theo thoi gian (cua so 3 ngay).
Bao cao 3 nguong cho moi luot va moi mo hinh:
  - Nguong 0.5 (mac dinh)
  - Nguong FPR <= 1%   : chon tren BENIGN cua validation, CHI cac ngay huan luyen
  - Nguong FPR <= 0.1% : nhu tren
Chon nguong chi can du lieu Benign -> khong can biet truoc kieu tan cong moi.
Luot 1: hoc Thu Hai, Ba, Tu -> kiem tra Thu Nam      (bao cao Recall Attack)
Luot 2: hoc Thu Ba, Tu, Nam -> kiem tra Thu Sau      (bao cao Recall Attack)
Luot 3: hoc Thu Tu, Nam, Sau -> kiem tra Thu Hai     (toan Benign -> bao cao Recall Benign)
Chong ro ri:
  - Mo hinh + tien xu ly + can bang: hoc tren TRAIN cua 3 ngay huan luyen (giong thi nghiem 6.5).
  - Nguong FPR: tinh tren dong BENIGN cua VAL thuoc 3 ngay huan luyen (mo hinh chua thay, khong co ngay kiem tra).
  - Danh gia: dong cua TRAIN thuoc ngay kiem tra.
  - KHONG doc test.parquet.
Ket qua: reports/s06d_fpr_thresholds_summary.csv, reports/s06d_fpr_thresholds_by_label.csv,
         reports/s06d_fpr_thresholds.png, logs/s06d_fpr_thresholds.txt"""
import json, sys, time, warnings
from pathlib import Path
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ids_pipeline import build_preprocess, fit_row_counts, SEED  # noqa: E402

SPLIT, MODELS, LOGS, REP = (ROOT / "data" / "processed" / "split", ROOT / "models", ROOT / "logs", ROOT / "reports")

# ---- Chot chan: chi duoc doc train.parquet va val.parquet, TUYET DOI khong doc test ----
_doc_goc = pd.read_parquet
def _doc_an_toan(path, *a, **k):
    assert Path(path).name in ("train.parquet", "val.parquet"), f"KHONG DUOC DOC {Path(path).name}!"
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
MUC_TIEU_FPR = [0.01, 0.001]          # 1% va 0.1%
TEN_NGUONG = ["Nguong 0.5", "Nguong FPR 1%", "Nguong FPR 0.1%"]


def nguong_theo_fpr(diem_benign, fpr_muc_tieu):
    """Nguong t nho nhat sao cho ty le diem Benign >= t KHONG VUOT fpr_muc_tieu (lam tron theo huong an toan)."""
    s = np.sort(np.asarray(diem_benign))[::-1]           # giam dan
    k = int(np.floor(fpr_muc_tieu * len(s)))              # so dong Benign toi da duoc phep vuot nguong
    return float(np.nextafter(s[k], np.inf)) if k < len(s) else float(s[-1])


def chi_so(y, p, nguong):
    pred = (p >= nguong).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    co_tc = tp + fn > 0
    return pred, {"TP": int(tp), "FP": int(fp), "FN": int(fn), "TN": int(tn),
                  "Recall_Attack": tp / (tp + fn) if co_tc else np.nan,
                  "FNR": fn / (fn + tp) if co_tc else np.nan,
                  "Precision": tp / (tp + fp) if tp + fp else (np.nan if not co_tc else 0.0),
                  "F1": 2 * tp / (2 * tp + fp + fn) if co_tc else np.nan,
                  "Recall_Benign": tn / (tn + fp) if tn + fp else np.nan,
                  "FPR_thuc_te": fp / (fp + tn) if tn + fp else np.nan}


def can_bang(X, lab, info):
    cnt = pd.Series(lab).value_counts()
    if "Benign" in cnt:
        X, lab = RandomUnderSampler(sampling_strategy={"Benign": min(info["N_BENIGN_KEEP"], int(cnt["Benign"]))},
                                    random_state=SEED).fit_resample(X, lab)
    cnt = pd.Series(lab).value_counts()
    tgt = {c: info["MIN_PER_ATTACK"] for c, n in cnt.items() if c != "Benign" and 2 <= n < info["MIN_PER_ATTACK"]}
    if tgt:
        k = min(5, int(cnt[list(tgt)].min()) - 1)
        X, lab = SMOTE(sampling_strategy=tgt, k_neighbors=k, random_state=SEED).fit_resample(X, lab)
    return X, (pd.Series(lab) != "Benign").astype(int).to_numpy()


t0 = time.time()
info = json.loads((MODELS / "preprocess_info.json").read_text(encoding="utf-8"))
FEAT = info["input_features"]
MAU_MH = {m: clone(joblib.load(MODELS / f"candidate_{m}.joblib").named_steps["model"]) for m in TEN_MH}
train = pd.read_parquet(SPLIT / "train.parquet")
val = pd.read_parquet(SPLIT / "val.parquet")
val_benign = val[val["y"] == 0]          # chi giu Benign cua validation; bo het dong tan cong
del val
out(f"Train: {len(train):,} dong | Val (chi Benign): {len(val_benign):,} dong | Test: KHONG DOC")
out(f"Muc tieu FPR: {', '.join(f'{f*100:g}%' for f in MUC_TIEU_FPR)} | so sanh voi nguong mac dinh 0.5")

tong_hop, theo_loai = [], []
for ten, ngay_hoc, ngay_kt in LUOT:
    out(f"\n{'=' * 100}\n{ten}: HOC tren {', '.join(ngay_hoc)}  ->  KIEM TRA tren {ngay_kt}")
    f_hoc = [NGAY[d] for d in ngay_hoc]
    hoc = train[train.Ngay.isin(f_hoc)]
    kt = train[train.Ngay == NGAY[ngay_kt]]
    hc = val_benign[val_benign.Ngay.isin(f_hoc)]      # du lieu chon nguong: Benign cua val, ngay huan luyen
    # ---- Kiem tra chong ro ri ----
    assert ngay_kt not in ngay_hoc and set(hoc.Ngay).isdisjoint(set(kt.Ngay))
    assert (hc["y"] == 0).all(), "Du lieu chon nguong phai toan Benign"
    assert set(hc.Ngay) <= set(f_hoc) and NGAY[ngay_kt] not in set(hc.Ngay)
    out(f"  Hoc (train): {len(hoc):,} dong | Chon nguong (val, chi Benign, ngay huan luyen): {len(hc):,} dong | "
        f"Kiem tra (train, {ngay_kt}): {len(kt):,} dong ({kt.y.mean()*100:.2f}% tan cong)")
    out("  OK  Du lieu chon nguong: toan Benign, chi thuoc ngay huan luyen, khong chua ngay kiem tra")

    pre = build_preprocess(k=info["K_FEATURES"], corr_threshold=info["CORR_THRESHOLD"])
    pre.fit(hoc[FEAT], hoc["y"])
    assert all(n is None or n == len(hoc) for n in fit_row_counts(pre).values())
    Xb, yb = can_bang(pre.transform(hoc[FEAT]), hoc["Label"].to_numpy(), info)
    Xk, yk, lk = pre.transform(kt[FEAT]), kt["y"].to_numpy(), kt["Label"].to_numpy()
    Xc = pre.transform(hc[FEAT])
    co_tc = yk.sum() > 0
    da_hoc = set(hoc["Label"]) - {"Benign"}

    for m in TEN_MH:
        mh = clone(MAU_MH[m]).fit(Xb, yb)
        p_kt = mh.predict_proba(Xk)[:, 1]
        p_c = mh.predict_proba(Xc)[:, 1]
        cac_nguong = [0.5] + [nguong_theo_fpr(p_c, f) for f in MUC_TIEU_FPR]
        auc = ({"PR_AUC": average_precision_score(yk, p_kt), "ROC_AUC": roc_auc_score(yk, p_kt)} if co_tc
               else {"PR_AUC": np.nan, "ROC_AUC": np.nan})
        out(f"  --- {m} ---" + (f"  (PR-AUC={auc['PR_AUC']:.4f}, ROC-AUC={auc['ROC_AUC']:.4f}, khong phu thuoc nguong)"
                               if co_tc else "  (PR-AUC, ROC-AUC: khong ap dung, khong co tan cong)"))
        for ten_ng, ng, muc_tieu in zip(TEN_NGUONG, cac_nguong, [np.nan] + MUC_TIEU_FPR):
            pred, cs = chi_so(yk, p_kt, ng)
            fpr_chon = float((p_c >= ng).mean())          # FPR tren chinh du lieu dung de chon nguong
            r = {"Luot": ten, "Hoc_tren": ", ".join(ngay_hoc), "Kiem_tra_tren": ngay_kt, "Mo_hinh": m,
                 "Loai_nguong": ten_ng, "Gia_tri_nguong": ng, "FPR_muc_tieu": muc_tieu,
                 "FPR_tren_du_lieu_chon_nguong": fpr_chon, **cs, **auc,
                 "Loai_Recall": "Attack" if co_tc else "Benign",
                 "Recall_chinh": cs["Recall_Attack"] if co_tc else cs["Recall_Benign"]}
            tong_hop.append(r)
            mt = f"muc tieu {muc_tieu*100:g}%" if muc_tieu == muc_tieu else "mac dinh"
            if co_tc:
                out(f"    {ten_ng:16s} nguong={ng:.6f} ({mt:13s})  Recall (Attack)={cs['Recall_Attack']*100:7.3f}%  "
                    f"FNR={cs['FNR']*100:7.3f}%  FPR thuc te={cs['FPR_thuc_te']*100:6.3f}%  "
                    f"Precision={cs['Precision']*100:7.3f}%  F1={cs['F1']:.4f}")
            else:
                out(f"    {ten_ng:16s} nguong={ng:.6f} ({mt:13s})  Recall (Benign)={cs['Recall_Benign']*100:7.3f}%  "
                    f"FPR thuc te={cs['FPR_thuc_te']*100:6.3f}% ({cs['FP']:,} luong bao nham)  "
                    f"[Recall (Attack): khong ap dung]")
            for lab in sorted(set(lk) - {"Benign"}):
                msk = lk == lab
                theo_loai.append({"Luot": ten, "Mo_hinh": m, "Loai_nguong": ten_ng, "Loai_tan_cong": lab,
                                  "So_dong": int(msk.sum()),
                                  "Da_hoc_o_ngay_huan_luyen": "Đã học" if lab in da_hoc else "Chưa học",
                                  "Ty_le_bat_duoc": float(pred[msk].mean())})
    if co_tc:
        bl = pd.DataFrame([x for x in theo_loai if x["Luot"] == ten and x["Mo_hinh"] == "XGBoost"])
        bl = bl.pivot_table(index=["Loai_tan_cong", "Da_hoc_o_ngay_huan_luyen", "So_dong"], columns="Loai_nguong",
                            values="Ty_le_bat_duoc")[TEN_NGUONG].reset_index()
        out("  XGBoost - ty le bat duoc theo tung loai tan cong o 3 nguong:")
        out("  " + bl.to_string(index=False, float_format=lambda v: f"{v:.3f}").replace("\n", "\n  "))

th = pd.DataFrame(tong_hop)
th.to_csv(REP / "s06d_fpr_thresholds_summary.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(theo_loai).to_csv(REP / "s06d_fpr_thresholds_by_label.csv", index=False, encoding="utf-8-sig")

# ---- Bieu do: 3 hang (mo hinh) x 2 cot (Recall chinh, FPR thuc te); moi khung 1 truc ----
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e6e5e0", "#fcfcfb"
MAU_NG = ["#2a78d6", "#eb6834", "#1baf7a"]          # 0.5, FPR 1%, FPR 0.1%
NHAN_NG = ["Ngưỡng 0,5", "Ngưỡng FPR ≤ 1%", "Ngưỡng FPR ≤ 0,1%"]
VN = {"Thu Hai": "Thứ Hai", "Thu Nam": "Thứ Năm", "Thu Sau": "Thứ Sáu"}
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.titlecolor": INK, "figure.facecolor": SURF, "axes.facecolor": SURF,
                     "axes.spines.top": False, "axes.spines.right": False})
fig, axs = plt.subplots(3, 2, figsize=(13, 10.5))
x = np.arange(len(LUOT)); w = 0.26
for hang, m in enumerate(TEN_MH):
    for cot, (truong, tieu_de) in enumerate([("Recall_chinh", "Recall (lượt 1–2: Attack; lượt 3: Benign)"),
                                             ("FPR_thuc_te", "FPR thực tế trên ngày kiểm tra")]):
        ax = axs[hang, cot]
        for i, ten_ng in enumerate(TEN_NGUONG):
            v = [th[(th.Luot == t) & (th.Mo_hinh == m) & (th.Loai_nguong == ten_ng)][truong].iloc[0] * 100
                 for t, _, _ in LUOT]
            bars = ax.bar(x + (i - 1) * w, v, w * 0.9, color=MAU_NG[i], label=NHAN_NG[i])
            for j, (b, a) in enumerate(zip(bars, v)):
                if truong == "Recall_chinh" and LUOT[j][2] == "Thu Hai":
                    b.set_hatch("///"); b.set_edgecolor(SURF)
                ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                        f"{a:.1f}" if truong == "Recall_chinh" else f"{a:.2f}",
                        ha="center", va="bottom", fontsize=7, color=INK2)
        if truong == "FPR_thuc_te":
            for f, c in zip(MUC_TIEU_FPR, MAU_NG[1:]):
                ax.axhline(f * 100, color=c, ls="--", lw=1)
            ax.set_ylim(0, max(1.5, ax.get_ylim()[1] * 1.15))
        else:
            ax.set_ylim(0, 112)
        nhan = [f"{t.replace('Luot', 'Lượt')}: {VN[k]}" + (f"\nRecall {'Benign' if k == 'Thu Hai' else 'Attack'}"
                if truong == "Recall_chinh" else "") for t, _, k in LUOT]
        ax.set_xticks(x, nhan); ax.set_ylabel("%")
        ax.set_title(f"{m}: {tieu_de}", loc="left", fontsize=10)
        ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
fig.legend(*axs[0, 0].get_legend_handles_labels(), frameon=False, loc="upper right", ncol=3, labelcolor=INK2,
           bbox_to_anchor=(0.995, 1.0))
fig.suptitle("Ngưỡng 0,5 và ngưỡng theo FPR (chọn trên Benign của validation thuộc các ngày huấn luyện)\n"
             "Vạch đứt: mức FPR mục tiêu", x=0.01, ha="left", fontsize=11.5, color=INK)
fig.tight_layout(); fig.savefig(REP / "s06d_fpr_thresholds.png", dpi=150, bbox_inches="tight", pad_inches=0.2)
plt.close(fig)

# ---- Tom tat ----
out(f"\n{'=' * 100}\nTOM TAT (XGBoost va RandomForest)")
for t, _, k in LUOT:
    for m in ("XGBoost", "RandomForest"):
        x_ = th[(th.Luot == t) & (th.Mo_hinh == m)].set_index("Loai_nguong")
        loai = x_["Loai_Recall"].iloc[0]
        out(f"  {t} ({k}) {m:13s} Recall ({loai}): " + " | ".join(
            f"{n}: {x_.loc[n, 'Recall_chinh']*100:.2f}% (FPR thuc te {x_.loc[n, 'FPR_thuc_te']*100:.3f}%)"
            for n in TEN_NGUONG))
out("\nDa luu: reports/s06d_fpr_thresholds_summary.csv, reports/s06d_fpr_thresholds_by_label.csv, reports/s06d_fpr_thresholds.png")
out(f"Thoi gian chay: {time.time()-t0:.0f} giay")
(LOGS / "s06d_fpr_thresholds.txt").write_text("\n".join(lines), encoding="utf-8")
