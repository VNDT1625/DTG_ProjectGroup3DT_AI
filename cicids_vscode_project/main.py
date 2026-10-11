"""CIC-IDS2017 DistriNet: duplicate audit + stratified / temporal experiments.

Run:
    python main.py --mode inspect
    python main.py --mode stratified
    python main.py --mode temporal
    python main.py --mode all

Only .parquet files under data/raw are used. No fitting on validation/test.
"""

from __future__ import annotations

import argparse
import json
import re
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_selection import VarianceThreshold
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

SEED = 42
DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
META_NAMES = {
    "label", "attacklabel", "binarylabel", "target", "attemptedcategory",
    "attackcategory", "flowid", "srcip", "sourceip", "dstip", "destinationip",
    "srcport", "sourceport", "dstport", "destinationport",
    "timestamp", "timestart", "timeend", "timestartutc", "timeendutc",
    "date", "day", "captureday", "index", "unnamed0",
}


def normalized(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.casefold())


def get_day_from_filename(path: Path) -> int | None:
    name = path.name.casefold()
    for n, d in enumerate(DAY_NAMES):
        if d.casefold() in name:
            return n
    # Only recognize explicit CIC-IDS2017 dates (July 3-7, 2017).
    m = re.search(r"2017[-_.]07[-_.]0([3-7])", name)
    return int(m.group(1)) - 3 if m else None


def read_parquets(raw_dir: Path) -> pd.DataFrame:
    paths = sorted(raw_dir.rglob("*.parquet"))
    if not paths:
        raise FileNotFoundError(
            f"Không tìm thấy .parquet trong {raw_dir.resolve()}. "
            "Hãy giải nén đúng dataset dhoogla/distrinetcicids2017 vào data/raw/."
        )
    print(f"\nĐã tìm thấy {len(paths)} file parquet:")
    parts = []
    schema = None
    for path in paths:
        part = pd.read_parquet(path)
        part.columns = [str(c).strip().lstrip("\ufeff") for c in part.columns]
        if not part.columns.is_unique:
            raise ValueError(f"Tên cột bị trùng sau khi strip(): {path.name}")
        now = tuple(part.columns)
        if schema is not None and set(now) != set(schema):
            raise ValueError(
                f"Cấu trúc cột không giống nhau ở file {path.name}. "
                "Cần kiểm tra lại đúng bộ parquet đã tải."
            )
        if schema is None:
            schema = now
        part["__capture_day"] = get_day_from_filename(path)
        parts.append(part)
        print(f"  {path.name}: {len(part):,} dòng; ngày={part['__capture_day'].iloc[0] if len(part) else 'N/A'}")
    return pd.concat(parts, ignore_index=True)


def parse_timestamps(df: pd.DataFrame) -> pd.Series:
    candidates = [c for c in df.columns if normalized(c) in {"timestamp", "timestart", "timestartutc", "flowstarttime", "flowstart"}]
    if not candidates:
        return pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]")
    s = df[candidates[0]]
    if pd.api.types.is_datetime64_any_dtype(s):
        return pd.to_datetime(s, errors="coerce", utc=True)
    if pd.api.types.is_numeric_dtype(s):
        valid = pd.to_numeric(s, errors="coerce").dropna()
        if valid.empty:
            return pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]")
        v = float(valid.abs().median())
        unit = "ns" if v > 1e17 else "us" if v > 1e14 else "ms" if v > 1e11 else "s"
        return pd.to_datetime(s, unit=unit, errors="coerce", utc=True)
    return pd.to_datetime(s, errors="coerce", dayfirst=True, utc=True)


def prepare_data(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Global, deterministic cleaning BEFORE splitting. No estimator is fit here."""
    label_candidates = [c for c in df.columns if normalized(c) in {"label", "attacklabel"}]
    if len(label_candidates) != 1:
        raise ValueError(f"Cần đúng 1 cột Label; tìm được: {label_candidates}. Cột hiện có: {df.columns.tolist()}")
    label_col = label_candidates[0]
    n_loaded = len(df)
    raw_duplicate_count = int(df.drop(columns="__capture_day").duplicated().sum())
    print(f"\nSố dòng trùng hệt nhau trên dữ liệu parquet nguồn (trừ tên file): {raw_duplicate_count:,}")

    raw_labels = df[label_col].astype("string").str.strip()
    print("\nCác nhãn ban đầu (10 loại nhiều nhất):")
    print(raw_labels.value_counts(dropna=False).head(10).to_string())
    attempted = raw_labels.str.contains("attempted", case=False, na=False)
    missing_labels = raw_labels.isna() | (raw_labels == "")
    print(f"Số nhãn chứa 'Attempted' cần bỏ: {int(attempted.sum()):,}")
    print(f"Số nhãn null/rỗng cần bỏ: {int(missing_labels.sum()):,}")
    keep = ~(attempted | missing_labels)
    df = df.loc[keep].copy().reset_index(drop=True)
    labels = raw_labels.loc[keep].reset_index(drop=True)
    df["__target"] = np.where(labels.str.upper() == "BENIGN", 0, 1).astype("int8")
    print("\nPhân phối nhãn nhị phân sau loại Attempted:")
    print(df["__target"].value_counts().rename(index={0: "BENIGN (0)", 1: "ATTACK (1)"}).to_string())

    df["__timestamp"] = parse_timestamps(df)
    feature_cols = [
        c for c in df.select_dtypes(include="number").columns
        if not c.startswith("__") and normalized(c) not in META_NAMES
        and not normalized(c).endswith("label")
        and "attempt" not in normalized(c)
    ]
    if not feature_cols:
        raise ValueError("Không còn đặc trưng số nào sau khi loại metadata/nhãn.")
    excluded_objects = [
        c for c in df.columns if c not in feature_cols
        and c not in {label_col, "__capture_day", "__timestamp", "__target"}
    ]
    print(f"\nSố đặc trưng số dùng huấn luyện: {len(feature_cols)}")
    print(f"Cột không đưa vào mô hình (metadata/phi số): {excluded_objects[:25]}")
    print("Lưu ý: không đưa nhãn, timestamp, IP, port, hoặc ngày thu thập vào mô hình.")

    missing_cells = int(df[feature_cols].isna().sum().sum())
    # Some corrected parquet versions are already clean, but verify anyway.
    inf_cells = int(np.isinf(df[feature_cols].to_numpy(dtype=np.float64, copy=False)).sum())
    print(f"\nÔ thiếu trước xử lý: {missing_cells:,}; ô ±inf: {inf_cells:,}")
    df[feature_cols] = df[feature_cols].replace([np.inf, -np.inf], np.nan)
    # Do NOT impute here: SimpleImputer.fit is later called on TRAIN only.

    # Hash numeric predictor vectors to audit duplicates efficiently on large data.
    fingerprints = pd.util.hash_pandas_object(df[feature_cols], index=False)
    same_label_hash = pd.util.hash_pandas_object(
        pd.DataFrame({"fingerprint": fingerprints, "target": df["__target"]}), index=False
    )
    n_exact_dup = int(same_label_hash.duplicated(keep="first").sum())
    mixed = df["__target"].groupby(fingerprints, sort=False).nunique()
    ambiguous_hashes = mixed.index[mixed > 1]
    conflict_mask = fingerprints.isin(ambiguous_hashes)
    print(f"\nBản ghi trùng đặc trưng + cùng nhãn (bản sao dư): {n_exact_dup:,}")
    print(f"Bản ghi có đặc trưng trùng nhưng nhãn mâu thuẫn: {int(conflict_mask.sum()):,}")
    print(f"Số nhóm đặc trưng mang nhãn mâu thuẫn: {len(ambiguous_hashes):,}")

    # Remove ALL inconsistent feature vectors, then keep a single copy of the rest.
    df = df.loc[~conflict_mask].copy()
    fingerprints = fingerprints.loc[~conflict_mask]
    duplicate_mask = fingerprints.duplicated(keep="first")
    print(f"Bản ghi trùng cùng nhãn bị loại: {int(duplicate_mask.sum()):,}")
    df = df.loc[~duplicate_mask].reset_index(drop=True)
    assert not df[feature_cols].duplicated().any(), "Còn bản ghi trùng đặc trưng!"
    print(f"Sau làm sạch và loại trùng: {len(df):,} dòng")
    df.attrs["audit"] = {
        "raw_rows": n_loaded,
        "raw_exact_duplicate_rows": raw_duplicate_count,
        "attempted_label_rows_removed": int(attempted.sum()),
        "missing_label_rows_removed": int(missing_labels.sum()),
        "missing_feature_cells_before_processing": missing_cells,
        "infinite_feature_cells_before_processing": inf_cells,
        "duplicate_predictors_and_same_target": n_exact_dup,
        "conflicting_target_rows_removed": int(conflict_mask.sum()),
        "conflicting_predictor_groups_removed": len(ambiguous_hashes),
        "same_label_duplicate_rows_removed": int(duplicate_mask.sum()),
        "remaining_unique_rows": len(df),
        "number_of_features": len(feature_cols),
    }
    print("Kết luận kiểm tra: không còn hàng nào có cùng toàn bộ đặc trưng đầu vào.")
    return df, feature_cols


def split_stratified(df: pd.DataFrame):
    train_idx, rest_idx = train_test_split(
        df.index.to_numpy(), test_size=0.30, random_state=SEED,
        stratify=df["__target"],
    )
    valid_idx, test_idx = train_test_split(
        rest_idx, test_size=0.50, random_state=SEED,
        stratify=df.loc[rest_idx, "__target"],
    )
    return df.loc[train_idx], df.loc[valid_idx], df.loc[test_idx]


def split_temporal(df: pd.DataFrame):
    days = df["__capture_day"]
    if days.notna().all() and set(days.unique()) == {0, 1, 2, 3, 4}:
        print("Temporal split dùng ngày ghi trong TÊN FILE: Mon-Wed / Thu / Fri.")
        tr = df.loc[days.isin([0, 1, 2])]
        va = df.loc[days == 3]
        te = df.loc[days == 4]
        return tr, va, te

    time = df["__timestamp"]
    if time.notna().all() and time.nunique() > 3:
        print("Temporal split theo Timestamp: 70% cũ nhất / 15% kế tiếp / 15% mới nhất.")
        ordered = df.sort_values("__timestamp", kind="stable")
        n = len(ordered)
        a, b = int(n * 0.70), int(n * 0.85)
        return ordered.iloc[:a], ordered.iloc[a:b], ordered.iloc[b:]
    raise ValueError(
        "Không thể tạo temporal split đáng tin cậy: thiếu ngày trong tên file "
        "và thiếu Timestamp hợp lệ. KHÔNG dùng thứ tự dòng hoặc split ngẫu nhiên "
        "rồi gọi đó là temporal. Hãy kiểm tra file parquet nguồn."
    )


def distribution(name, data, total):
    rate = float(data["__target"].mean()) if len(data) else float("nan")
    print(f"  {name:<10} n={len(data):>9,} | {len(data)/total:6.2%} | attack={rate:6.2%}")
    if data["__target"].nunique() != 2:
        raise ValueError(f"Tập {name} chỉ có một lớp. Không thể đánh giá nhị phân đúng yêu cầu.")


def build_models(n_jobs: int, y_train: pd.Series):
    n_pos = int(y_train.sum())
    n_neg = len(y_train) - n_pos
    xgb_weight = n_neg / n_pos

    def initial_steps():
        return [
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("feature_selection", VarianceThreshold(threshold=0.0)),
        ]

    return {
        "LogisticRegression": Pipeline(initial_steps() + [
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(
                max_iter=400, solver="lbfgs", class_weight="balanced", random_state=SEED
            )),
        ]),
        "RandomForest": Pipeline(initial_steps() + [
            ("classifier", RandomForestClassifier(
                n_estimators=120, max_depth=18, min_samples_leaf=3,
                class_weight="balanced_subsample", n_jobs=n_jobs, random_state=SEED
            )),
        ]),
        "XGBoost": Pipeline(initial_steps() + [
            ("classifier", XGBClassifier(
                n_estimators=250, max_depth=6, learning_rate=0.08,
                subsample=0.85, colsample_bytree=0.85,
                objective="binary:logistic", eval_metric="logloss",
                tree_method="hist", scale_pos_weight=xgb_weight,
                n_jobs=n_jobs, random_state=SEED,
            )),
        ]),
    }


def get_metrics(y_true, predicted, proba) -> dict:
    out = {
        "accuracy": accuracy_score(y_true, predicted),
        "precision": precision_score(y_true, predicted, zero_division=0),
        "recall": recall_score(y_true, predicted, zero_division=0),
        "f1": f1_score(y_true, predicted, zero_division=0),
        "pr_auc": average_precision_score(y_true, proba),
    }
    out["roc_auc"] = roc_auc_score(y_true, proba) if len(np.unique(y_true)) == 2 else float("nan")
    tn, fp, fn, tp = confusion_matrix(y_true, predicted, labels=[0, 1]).ravel()
    out.update({"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)})
    return out


def run_experiment(df, feature_cols, protocol, n_jobs, train_limit, result_root: Path):
    print(f"\n{'='*22} THÍ NGHIỆM: {protocol.upper()} {'='*22}")
    tr, va, te = split_stratified(df) if protocol == "stratified" else split_temporal(df)
    print("Phân phối của từng tập (train/val/test không có hàng trùng do dedup toàn cục):")
    for title, frame in [("Train", tr), ("Validation", va), ("Test", te)]:
        distribution(title, frame, len(df))
    if train_limit is not None and train_limit < len(tr):
        print(f"\nCHẠY THỬ: chỉ lấy {train_limit:,} mẫu train (KHÔNG dùng kết quả để báo cáo).")
        tr, _ = train_test_split(
            tr, train_size=train_limit, stratify=tr["__target"], random_state=SEED
        )

    X_tr, y_tr = tr[feature_cols], tr["__target"]
    X_va, y_va = va[feature_cols], va["__target"]
    X_te, y_te = te[feature_cols], te["__target"]
    out_dir = result_root / protocol
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    trained = {}

    for name, pipeline in build_models(n_jobs, y_tr).items():
        print(f"\nĐang FIT {name} ... (fit mọi bộ xử lý trên TRAIN)")
        pipeline.fit(X_tr, y_tr)
        valid_probability = pipeline.predict_proba(X_va)[:, 1]
        valid_pred = (valid_probability >= 0.5).astype(int)
        metric = get_metrics(y_va, valid_pred, valid_probability)
        print(f"  Validation: F1={metric['f1']:.4f} | Recall={metric['recall']:.4f} "
              f"| PR-AUC={metric['pr_auc']:.4f} | ROC-AUC={metric['roc_auc']:.4f}")
        rows.append({"model": name, **{f"val_{k}": v for k, v in metric.items()}})
        trained[name] = pipeline

    # Choose hyperparameters/model using VALIDATION only; TEST remains untouched so far.
    rank = pd.DataFrame(rows).sort_values(
        ["val_f1", "val_pr_auc"], ascending=[False, False]
    ).reset_index(drop=True)
    selected = str(rank.loc[0, "model"])
    print(f"\nMô hình có Validation F1 tốt nhất ({protocol}): {selected}")
    print("TEST chỉ được đánh giá 1 lần, sau khi quyết định cấu hình mô hình.")

    # One-time final test reporting for ALL prespecified models (not for tuning).
    test_rows = []
    for name, pipeline in trained.items():
        proba = pipeline.predict_proba(X_te)[:, 1]
        pred = (proba >= 0.5).astype(int)
        result = get_metrics(y_te, pred, proba)
        print(f"  Test {name}: F1={result['f1']:.4f} | Recall={result['recall']:.4f} "
              f"| PR-AUC={result['pr_auc']:.4f} | FP={result['fp']:,} | FN={result['fn']:,}")
        test_rows.append({"model": name, **{f"test_{k}": v for k, v in result.items()}})
        joblib.dump(pipeline, out_dir / f"{name}.joblib", compress=3)
        if name in {"RandomForest", "XGBoost"}:
            kept = np.array(feature_cols)[pipeline.named_steps["feature_selection"].get_support()]
            importance = pipeline.named_steps["classifier"].feature_importances_
            pd.DataFrame({"feature": kept, "importance": importance}).sort_values(
                "importance", ascending=False
            ).to_csv(out_dir / f"{name}_feature_importance.csv", index=False)

    final_report = rank.merge(pd.DataFrame(test_rows), on="model", validate="one_to_one")
    final_report.to_csv(out_dir / "model_metrics.csv", index=False)
    summary = {
        "protocol": protocol,
        "selected_on_validation": selected,
        "random_state": SEED,
        "n_features_before_variance_selection": len(feature_cols),
        "train_rows_used": len(tr), "validation_rows": len(va), "test_rows": len(te),
        "test_used_for_tuning": False,
        "feature_columns": feature_cols,
    }
    (out_dir / "experiment_info.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nĐã lưu bảng kết quả, model và feature importance vào {out_dir.resolve()}")
    print(final_report[["model", "val_f1", "val_recall", "test_f1", "test_recall", "test_pr_auc"]].to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description="DistriNet CIC-IDS2017 ML benchmark")
    parser.add_argument("--mode", choices=["inspect", "stratified", "temporal", "all"], default="inspect")
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--result-dir", type=Path, default=Path("results"))
    parser.add_argument("--jobs", type=int, default=4, help="Số CPU threads cho RF/XGBoost")
    parser.add_argument("--train-limit", type=int, default=None, help="Chỉ dùng để CHẠY THỬ, không báo cáo")
    args = parser.parse_args()
    if args.train_limit is not None and args.train_limit < 20:
        parser.error("--train-limit phải >=20")
    with warnings.catch_warnings():
        warnings.simplefilter("default")
        df, features = prepare_data(read_parquets(args.data_dir))
    args.result_dir.mkdir(parents=True, exist_ok=True)
    (args.result_dir / "data_audit.json").write_text(
        json.dumps(df.attrs["audit"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Đã lưu kiểm toán dữ liệu tại {(args.result_dir / 'data_audit.json').resolve()}")
    if args.mode == "inspect":
        print("\nĐã kiểm tra xong. Tiếp theo chạy --mode stratified hoặc temporal.")
        return
    modes = ["stratified", "temporal"] if args.mode == "all" else [args.mode]
    for protocol in modes:
        run_experiment(df, features, protocol, args.jobs, args.train_limit, args.result_dir)


if __name__ == "__main__":
    main()
