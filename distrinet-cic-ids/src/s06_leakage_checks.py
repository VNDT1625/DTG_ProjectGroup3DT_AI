"""Giai doan 6: KIEM TRA RO RI (truoc khi mo khoa test). KHONG doc test.
6.1 Xao tron nhan train -> mo hinh phai ve muc co so tren val (neu khong => co ro ri).
6.2 Tung dac trung don le -> tim cot "qua tot" (gan nhu tu phan loai hoan hao).
6.3 So sanh diem tren train va val -> chenh lech lon = hoc vet.
6.4 (Them, tham khao) Chia THEO NGAY: hoc tren cac ngay khac, kiem tra tren 1 ngay chua thay.
    Moi lan deu hoc lai day chuyen tien xu ly + can bang tu dau tren cac ngay huan luyen.
    Chi dung cac dong thuoc train + val (khong dung dong nao cua test).
Ket qua: reports/s06_*.csv, logs/s06_leakage_checks.txt"""
import json, sys, time, warnings
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import average_precision_score, f1_score, recall_score, roc_auc_score
from sklearn.tree import DecisionTreeClassifier
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ids_pipeline import build_preprocess, SEED  # noqa: E402

SPLIT, S4, MODELS, LOGS, REP = (ROOT / "data" / "processed" / "split", ROOT / "data" / "processed" / "stage4",
                                ROOT / "models", ROOT / "logs", ROOT / "reports")
lines = []
def out(s=""):
    print(s, flush=True); lines.append(str(s))

t0 = time.time()
final = joblib.load(MODELS / "final_model.joblib")
info = json.loads((MODELS / "preprocess_info.json").read_text(encoding="utf-8"))
FEAT, thr = final["input_features"], final["threshold"]
model_tpl = final["pipeline"].named_steps["model"]
tr = pd.read_parquet(S4 / "train_bal.parquet")
va = pd.read_parquet(S4 / "val_tf.parquet")
F = [c for c in tr.columns if c not in ("y", "Label")]
out(f"Mo hinh dang kiem tra: {final['model_name']} | nguong {thr:.4f} | Test: KHONG DOC\n")

# ---------- 6.1 Xao tron nhan ----------
out("[6.1] XAO TRON NHAN TRAIN (mo hinh khong the hoc duoc gi that)")
rng = np.random.default_rng(SEED)
m = clone(model_tpl).fit(tr[F], rng.permutation(tr["y"].to_numpy()))
p = m.predict_proba(va[F])[:, 1]
pr, roc = average_precision_score(va["y"], p), roc_auc_score(va["y"], p)
base = va["y"].mean()
out(f"  PR-AUC = {pr:.4f} (muc co so = ty le tan cong {base:.4f}) | ROC-AUC = {roc:.4f} (muc co so = 0.5)")
ok61 = abs(roc - 0.5) < 0.05 and pr < base + 0.05
out(f"  => {'DAT: diem tut ve muc co so, khong co ro ri qua nhan' if ok61 else 'CANH BAO: van con diem cao => nghi ro ri'}")

# ---------- 6.2 Tung dac trung don le ----------
out("\n[6.2] TUNG DAC TRUNG DON LE (cay quyet dinh do sau 3, hoc tren train, cham tren val)")
rows = []
for c in F:
    dt = DecisionTreeClassifier(max_depth=3, random_state=SEED).fit(tr[[c]], tr["y"])
    rows.append({"Dac_trung": c, "ROC_AUC_val": roc_auc_score(va["y"], dt.predict_proba(va[[c]])[:, 1])})
single = pd.DataFrame(rows).sort_values("ROC_AUC_val", ascending=False)
single.to_csv(REP / "s06_single_feature_auc.csv", index=False, encoding="utf-8-sig")
out(single.head(8).to_string(index=False, float_format=lambda v: f"{v:.4f}"))
sus = single[single.ROC_AUC_val > 0.99]
out(f"  => {'DAT: khong co cot nao mot minh phan loai gan hoan hao (>0.99)' if sus.empty else 'CAN XEM: ' + ', '.join(sus.Dac_trung)}")

# ---------- 6.3 Train vs val ----------
out("\n[6.3] SO SANH DIEM TREN TRAIN (goc, chua can bang) VA VAL")
train_raw = pd.read_parquet(SPLIT / "train.parquet")
pipe = final["pipeline"]
def diem(df_):
    pp = pipe.predict_proba(df_[FEAT])[:, 1]
    return {"PR_AUC": average_precision_score(df_["y"], pp), "F1": f1_score(df_["y"], pp >= thr),
            "Recall": recall_score(df_["y"], pp >= thr)}
val_raw = pd.read_parquet(SPLIT / "val.parquet")
d_tr, d_va = diem(train_raw), diem(val_raw)
cmp_ = pd.DataFrame({"Train": d_tr, "Val": d_va}); cmp_["Chenh_lech"] = cmp_.Train - cmp_.Val
out(cmp_.to_string(float_format=lambda v: f"{v:.4f}"))
ok63 = cmp_["Chenh_lech"].abs().max() < 0.02
out(f"  => {'DAT: chenh lech < 0.02, khong hoc vet' if ok63 else 'CANH BAO: chenh lech lon, co dau hieu hoc vet'}")

# ---------- 6.4 Chia theo ngay ----------
out("\n[6.4] (THAM KHAO) HOC TREN CAC NGAY KHAC, KIEM TRA TREN 1 NGAY CHUA THAY - chi dung train+val")
pool = pd.concat([train_raw, val_raw], ignore_index=True)
del train_raw
def can_bang(X, lab):
    cnt = pd.Series(lab).value_counts()
    rus = RandomUnderSampler(sampling_strategy={"Benign": min(info["N_BENIGN_KEEP"], int(cnt["Benign"]))},
                             random_state=SEED)
    X, lab = rus.fit_resample(X, lab)
    cnt = pd.Series(lab).value_counts()
    tgt = {c: info["MIN_PER_ATTACK"] for c, n in cnt.items()
           if c != "Benign" and 2 <= n < info["MIN_PER_ATTACK"]}
    if tgt:
        k = min(5, int(cnt[list(tgt)].min()) - 1)
        X, lab = SMOTE(sampling_strategy=tgt, k_neighbors=k, random_state=SEED).fit_resample(X, lab)
    return X, (pd.Series(lab) != "Benign").astype(int).to_numpy()

rows = []
for day in sorted(pool["Ngay"].unique()):
    hold, fit_ = pool[pool.Ngay == day], pool[pool.Ngay != day]
    pre = build_preprocess(k=info["K_FEATURES"], corr_threshold=info["CORR_THRESHOLD"])
    pre.fit(fit_[FEAT], fit_["y"])
    Xb, yb = can_bang(pre.transform(fit_[FEAT]), fit_["Label"].to_numpy())
    mm = clone(model_tpl).fit(Xb, yb)
    ph = mm.predict_proba(pre.transform(hold[FEAT]))[:, 1]
    pred = ph >= thr
    unseen = sorted(set(hold.Label) - set(fit_.Label) - {"Benign"})
    r = {"Ngay_kiem_tra": day, "So_dong": len(hold), "Ty_le_tan_cong": hold.y.mean(),
         "Recall": recall_score(hold.y, pred) if hold.y.any() else np.nan,
         "F1": f1_score(hold.y, pred) if hold.y.any() else np.nan,
         "Bao_nham_FPR": pred[hold.y.to_numpy() == 0].mean(),
         "Loai_tan_cong_chua_tung_hoc": ", ".join(unseen) if unseen else "-"}
    rows.append(r)
    out(f"  {day:40s} Recall={r['Recall']:.4f}  F1={r['F1']:.4f}  FPR={r['Bao_nham_FPR']:.4f}  "
        f"chua tung hoc: {r['Loai_tan_cong_chua_tung_hoc']}")
    per = (pd.DataFrame({"Label": hold.Label, "bat_duoc": pred}).query("Label != 'Benign'")
           .groupby("Label")["bat_duoc"].mean())
    if len(per):
        out("      ty le bat duoc tung loai: " + ", ".join(f"{k}={v:.2f}" for k, v in per.items()))
pd.DataFrame(rows).to_csv(REP / "s06_day_split.csv", index=False, encoding="utf-8-sig")
out("  Ghi chu: moi ngay CIC-IDS2017 la cac kieu tan cong KHAC NHAU, nen diem tut manh o day")
out("  chu yeu do mo hinh gap kieu tan cong chua tung hoc - day la HAN CHE can neu trong bao cao.")

out(f"\nTONG KET: 6.1 {'DAT' if ok61 else 'CANH BAO'} | 6.2 {'DAT' if sus.empty else 'CAN XEM'} | "
    f"6.3 {'DAT' if ok63 else 'CANH BAO'} | 6.4 tham khao")
out(f"Thoi gian chay: {time.time()-t0:.0f} giay")
(LOGS / "s06_leakage_checks.txt").write_text("\n".join(lines), encoding="utf-8")
