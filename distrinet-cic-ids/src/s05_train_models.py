"""Giai doan 5: HUAN LUYEN 3 MO HINH va CHON MO HINH - chi dung TRAIN (da can bang) + VALIDATION.
- 3 mo hinh: Logistic Regression, Random Forest, XGBoost; moi mo hinh thu vai cau hinh.
- Chon mo hinh theo PR-AUC tren VALIDATION; chon nguong canh bao toi uu F1 tren VALIDATION.
- KHONG doc test.
Ket qua: models/final_model.joblib, reports/s05_*.csv, logs/s05_training.txt"""
import json, sys, time, warnings
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix, f1_score,
                             precision_recall_curve, precision_score, recall_score, roc_auc_score)
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import ids_pipeline  # noqa: F401,E402  (de joblib nap duoc cac bo phan tien xu ly)
from ids_pipeline import SEED  # noqa: E402

S4, MODELS, LOGS, REP = (ROOT / "data" / "processed" / "stage4", ROOT / "models",
                         ROOT / "logs", ROOT / "reports")
lines = []
def out(s=""):
    print(s, flush=True); lines.append(str(s))

tr = pd.read_parquet(S4 / "train_bal.parquet")
va = pd.read_parquet(S4 / "val_tf.parquet")
FEATS = [c for c in tr.columns if c not in ("y", "Label")]
Xtr, ytr = tr[FEATS], tr["y"].to_numpy()
Xva, yva, lva = va[FEATS], va["y"].to_numpy(), va["Label"].to_numpy()
out(f"Train (can bang): {len(tr):,} dong | Val: {len(va):,} dong | {len(FEATS)} dac trung | Test: KHONG DOC")


def danh_gia(y, p, thr):
    pred = (p >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {"PR_AUC": average_precision_score(y, p), "ROC_AUC": roc_auc_score(y, p),
            "F1": f1_score(y, pred), "Precision": precision_score(y, pred, zero_division=0),
            "Recall": recall_score(y, pred), "Ty_le_bao_nham_FPR": fp / (fp + tn), "Ty_le_bo_sot_FNR": fn / (fn + tp),
            "TP": int(tp), "FP": int(fp), "FN": int(fn), "TN": int(tn)}


CANDIDATES = {
    "LogisticRegression": [LogisticRegression(C=c, max_iter=2000, random_state=SEED) for c in (0.1, 1.0, 10.0)],
    "RandomForest": [RandomForestClassifier(n_estimators=150, max_depth=d, min_samples_leaf=l,
                                            n_jobs=-1, random_state=SEED)
                     for d, l in ((None, 1), (25, 2))],
    "XGBoost": [XGBClassifier(n_estimators=400, learning_rate=0.1, max_depth=md, tree_method="hist",
                              eval_metric="logloss", random_state=SEED, n_jobs=-1)
                for md in (6, 10)],
}

rows, best_per_model = [], {}
for name, models in CANDIDATES.items():
    for i, m in enumerate(models):
        t0 = time.time()
        m.fit(Xtr, ytr)
        p = m.predict_proba(Xva)[:, 1]
        r = {"Mo_hinh": name, "Cau_hinh": i, "Tham_so": str({k: v for k, v in m.get_params().items()
                                                         if k in ("C", "max_depth", "min_samples_leaf")}),
             **danh_gia(yva, p, 0.5), "Giay": round(time.time() - t0, 1)}
        rows.append(r)
        out(f"  {name:20s} cau hinh {i} {r['Tham_so']:45s} PR-AUC={r['PR_AUC']:.4f} F1@0.5={r['F1']:.4f} ({r['Giay']}s)")
        if name not in best_per_model or r["PR_AUC"] > best_per_model[name][0]:
            best_per_model[name] = (r["PR_AUC"], m, p)

res = pd.DataFrame(rows)
res.to_csv(REP / "s05_all_configs_val.csv", index=False, encoding="utf-8-sig")

# Nguong toi uu F1 cho tung mo hinh (tren VAL)
out("\n[SO SANH 3 MO HINH TREN VALIDATION - cau hinh tot nhat moi mo hinh]")
summary = []
for name, (_, m, p) in best_per_model.items():
    prec, rec, thr = precision_recall_curve(yva, p)
    f1s = 2 * prec[:-1] * rec[:-1] / np.clip(prec[:-1] + rec[:-1], 1e-12, None)
    best_thr = float(thr[np.argmax(f1s)])
    summary.append({"Mo_hinh": name, "Nguong_toi_uu": round(best_thr, 4), **danh_gia(yva, p, best_thr)})
sm = pd.DataFrame(summary).sort_values("PR_AUC", ascending=False)
sm.to_csv(REP / "s05_model_comparison_val.csv", index=False, encoding="utf-8-sig")
cols = ["Mo_hinh", "PR_AUC", "ROC_AUC", "F1", "Precision", "Recall", "Ty_le_bao_nham_FPR", "Ty_le_bo_sot_FNR", "Nguong_toi_uu"]
out(sm[cols].to_string(index=False, float_format=lambda v: f"{v:.4f}"))

# Chon mo hinh tot nhat
best = sm.iloc[0]
bname, bthr = best["Mo_hinh"], float(best["Nguong_toi_uu"])
_, bmodel, bp = best_per_model[bname]
out(f"\n=> MO HINH DUOC CHON: {bname} | nguong canh bao = {bthr:.4f} (chon tren validation)")

# Ty le bat duoc theo tung loai tan cong (val)
pred = (bp >= bthr).astype(int)
per = (pd.DataFrame({"Label": lva, "dung": pred == yva}).groupby("Label")
       .agg(So_dong=("dung", "size"), Ty_le_dung=("dung", "mean")).sort_values("So_dong", ascending=False))
per.to_csv(REP / "s05_accuracy_by_label_val.csv", encoding="utf-8-sig")
out("\n[TY LE DOAN DUNG THEO TUNG LOAI - VALIDATION]")
out(per.to_string(float_format=lambda v: f"{v:.4f}"))

# Luu day chuyen HOAN CHINH: tien xu ly (da hoc tren train) + mo hinh
pre = joblib.load(MODELS / "preprocess.joblib")
info = json.loads((MODELS / "preprocess_info.json").read_text(encoding="utf-8"))
full = Pipeline([("pre", pre), ("model", bmodel)])
joblib.dump({"pipeline": full, "threshold": bthr, "model_name": bname,
             "input_features": info["input_features"], "selected_features": FEATS,
             "val_metrics": best.to_dict()}, MODELS / "final_model.joblib", compress=3)
for name, (_, m, _) in best_per_model.items():
    joblib.dump(Pipeline([("pre", pre), ("model", m)]), MODELS / f"candidate_{name}.joblib", compress=3)
out("\nDa luu: models/final_model.joblib (+ models/candidate_*.joblib), reports/s05_*.csv")
(LOGS / "s05_training.txt").write_text("\n".join(lines), encoding="utf-8")
