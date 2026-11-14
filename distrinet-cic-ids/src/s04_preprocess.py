"""Giai doan 4: TIEN XU LY - CHI HOC TREN TRAIN.
- Doc train va val. KHONG doc test (test van bi khoa).
- Hoc day chuyen tien xu ly tren train, ap dung (transform) cho train va val.
- Can bang du lieu (undersampling + SMOTE) CHI tren train da bien doi. Val giu nguyen.
Ket qua: models/preprocess.joblib, data/processed/stage4/{train_bal,val_tf}.parquet,
         reports/s04_*.csv, logs/s04_preprocessing.txt"""
import json, sys, time
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ids_pipeline import build_preprocess, fit_row_counts, SEED  # noqa: E402

SPLIT, OUTD = ROOT / "data" / "processed" / "split", ROOT / "data" / "processed" / "stage4"
MODELS, LOGS, REP = ROOT / "models", ROOT / "logs", ROOT / "reports"
OUTD.mkdir(parents=True, exist_ok=True)

# ---- Tham so (co the chinh o Giai doan 5 dua tren VALIDATION) ----
K_FEATURES = 30          # so dac trung giu lai
CORR_THRESHOLD = 0.95    # nguong loai cot tuong quan cao
N_BENIGN_KEEP = 400_000  # giam so dong Benign trong train xuong con bao nhieu
MIN_PER_ATTACK = 2_000   # SMOTE: moi loai tan cong co it nhat bao nhieu dong

lines = []
def out(s=""):
    print(s); lines.append(str(s))

t0 = time.time()
FEAT = json.loads((MODELS / "feature_cols.json").read_text(encoding="utf-8"))
train = pd.read_parquet(SPLIT / "train.parquet")
val = pd.read_parquet(SPLIT / "val.parquet")
out(f"Train: {len(train):,} dong | Val: {len(val):,} dong | Test: KHONG DOC (dang khoa)")

# ---- 1. Hoc day chuyen tren TRAIN ----
pre = build_preprocess(k=K_FEATURES, corr_threshold=CORR_THRESHOLD)
pre.fit(train[FEAT], train["y"])
counts = fit_row_counts(pre)
out("\n[KIEM CHUNG: moi bo phan da hoc tren bao nhieu dong]")
for name, n in counts.items():
    flag = "OK" if n == len(train) else "!!"
    out(f"  {flag}  {name:15s} {n:,}" if n is not None else f"  --  {name:15s} (ham co dinh)")
    if n is not None:
        assert n == len(train), f"{name} da hoc tren {n} dong, khac so dong train!"

st = pre.named_steps
out(f"\n[KET QUA HOC TREN TRAIN]")
out(f"  Protocol: cac gia tri gap trong train = {list(st['encoder'].ohe_.categories_[0])}")
out(f"  Cot hang bi bo ({len(st['drop_constant'].dropped_)}): {st['drop_constant'].dropped_}")
out(f"  Cot tuong quan > {CORR_THRESHOLD} bi bo ({len(st['corr_filter'].dropped_)}): {st['corr_filter'].dropped_}")
out(f"  {K_FEATURES} dac trung duoc chon: {st['select'].keep_}")
st["select"].importances_.rename("do_quan_trong").to_csv(REP / "s04_feature_importance.csv",
                                                         encoding="utf-8-sig")

# ---- 2. Ap dung (KHONG hoc lai) cho train va val ----
Xtr = pre.transform(train[FEAT])
Xva = pre.transform(val[FEAT])
out(f"\nSau bien doi: train {Xtr.shape}, val {Xva.shape}")

# ---- 3. Can bang du lieu CHI TREN TRAIN ----
# Dung nhan chi tiet cua TRAIN de: giam Benign, va SMOTE tung loai tan cong hiem
# (de loai hiem nhu Heartbleed khong bi "chim"). Nhan nhi phan y suy ra lai tu nhan chi tiet.
lab = train["Label"].to_numpy()
before = pd.Series(lab).value_counts()
rus = RandomUnderSampler(sampling_strategy={"Benign": min(N_BENIGN_KEEP, int(before["Benign"]))},
                         random_state=SEED)
Xu, lu = rus.fit_resample(Xtr, lab)
cnt = pd.Series(lu).value_counts()
target = {c: MIN_PER_ATTACK for c, n in cnt.items() if c != "Benign" and n < MIN_PER_ATTACK}
smallest = int(cnt[list(target)].min()) if target else 6
sm = SMOTE(sampling_strategy=target, k_neighbors=min(5, smallest - 1), random_state=SEED)
Xb, lb = sm.fit_resample(Xu, lu) if target else (Xu, lu)
yb = (pd.Series(lb) != "Benign").astype("int8").to_numpy()
after = pd.Series(lb).value_counts()
tab = pd.DataFrame({"train_goc": before, "train_can_bang": after}).fillna(0).astype(int)
out("\n[CAN BANG - CHI TREN TRAIN]")
out(tab.to_string())
out(f"  Train sau can bang: {len(yb):,} dong | nhan 0: {(yb==0).sum():,} | nhan 1: {(yb==1).sum():,} "
    f"| ty le tan cong {yb.mean()*100:.1f}%")
out(f"  Val GIU NGUYEN: {len(Xva):,} dong | ty le tan cong {val['y'].mean()*100:.2f}% (phan anh thuc te)")
tab.to_csv(REP / "s04_train_balancing.csv", encoding="utf-8-sig")

# ---- 4. Kiem tra cuoi ----
assert len(Xva) == len(val) and list(Xva.columns) == list(Xtr.columns)
assert not np.isnan(Xb.to_numpy()).any() and not np.isnan(Xva.to_numpy()).any()
out("\n  OK  Val khong bi can bang, khong mat dong; khong co o trong sau bien doi")

# ---- 5. Luu ----
trb = Xb.reset_index(drop=True).copy(); trb["y"] = yb; trb["Label"] = lb
vat = Xva.reset_index(drop=True).copy(); vat["y"] = val["y"].to_numpy(); vat["Label"] = val["Label"].to_numpy()
trb.to_parquet(OUTD / "train_bal.parquet", index=False)
vat.to_parquet(OUTD / "val_tf.parquet", index=False)
joblib.dump(pre, MODELS / "preprocess.joblib")
info = {"K_FEATURES": K_FEATURES, "CORR_THRESHOLD": CORR_THRESHOLD, "N_BENIGN_KEEP": N_BENIGN_KEEP,
        "MIN_PER_ATTACK": MIN_PER_ATTACK, "fit_rows": counts, "train_rows": len(train),
        "selected_features": st["select"].keep_, "input_features": FEAT}
(MODELS / "preprocess_info.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
out(f"\nDa luu: models/preprocess.joblib, data/processed/stage4/, reports/s04_*.csv")
out(f"Thoi gian chay: {time.time()-t0:.0f} giay")
(LOGS / "s04_preprocessing.txt").write_text("\n".join(lines), encoding="utf-8")
