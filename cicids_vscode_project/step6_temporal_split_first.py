"""Step 6 - Re-run temporal validation with split-FIRST duplicate handling.

Run from folder containing main.py and data/raw:
    python step6_temporal_split_first.py --jobs 4

This script does NOT evaluate Friday TEST and does NOT overwrite the prior models.
The trained models are based ONLY on Mon-Wed. Validation Thursday is used for
threshold selection; reported tuned F1 is *in-sample* validation F1.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve

from main import (
    META_NAMES, build_models, get_metrics, normalized, parse_timestamps,
    read_parquets, split_temporal,
)


# Avoid feature/label-dependent global de-duplication from the original
# main.prepare_data(): split by capture day FIRST.
def prepare_without_global_dedup(raw: pd.DataFrame):
    label_candidates = [
        c for c in raw.columns if normalized(c) in {"label", "attacklabel"}
    ]
    if len(label_candidates) != 1:
        raise ValueError(f"Cannot identify exactly one Label column: {label_candidates}")
    label_col = label_candidates[0]
    labels = raw[label_col].astype("string").str.strip()
    exclude = labels.isna() | labels.eq("") | labels.str.contains(
        "attempted", case=False, na=False
    )
    df = raw.loc[~exclude].copy()
    clean_labels = labels.loc[~exclude]
    df["__target"] = clean_labels.str.upper().ne("BENIGN").astype("int8")
    df["__timestamp"] = parse_timestamps(df)

    features = [
        c for c in df.select_dtypes(include="number").columns
        if not c.startswith("__")
        and normalized(c) not in META_NAMES
        and not normalized(c).endswith("label")
        and "attempt" not in normalized(c)
    ]
    if not features:
        raise ValueError("No numeric model features found")
    # Deterministic cell conversion (NOT learned from validation/test).
    df.loc[:, features] = df[features].replace([np.inf, -np.inf], np.nan)
    print(f"Excluded Attempted/missing labels by predefined rule: {int(exclude.sum()):,}")
    print(f"Numerical model features: {len(features)}")
    return df, features


def hash_features(frame: pd.DataFrame, feature_cols: list[str]) -> pd.Series:
    """Same consistent fingerprint for all splits. Not a classifier feature."""
    return pd.util.hash_pandas_object(frame[feature_cols], index=False)


def clean_train_only(train: pd.DataFrame, feature_cols: list[str]):
    """Only TRAIN labels may decide which conflicting examples to discard."""
    fp = hash_features(train, feature_cols)
    conflicts = train["__target"].groupby(fp, sort=False).nunique().gt(1)
    conflict_rows = fp.isin(conflicts.index[conflicts])
    n_conflicts = int(conflict_rows.sum())
    tr = train.loc[~conflict_rows].copy()
    hashes = fp.loc[~conflict_rows]
    redundant = hashes.duplicated(keep="first")
    n_duplicates = int(redundant.sum())
    tr = tr.loc[~redundant].copy()
    if tr["__target"].nunique() < 2:
        raise ValueError("Cleaned train has fewer than two classes")
    print(f"TRAIN conflict rows discarded (TRAIN labels only): {n_conflicts:,}")
    print(f"TRAIN same-vector extra copies removed: {n_duplicates:,}")
    print(f"TRAIN after cleaning: {len(tr):,}, attack rate={tr['__target'].mean():.2%}")
    return tr, {"train_conflict_rows": n_conflicts,
                "train_redundant_copies": n_duplicates,
                "train_final_rows": len(tr)}


def audit_and_filter_validation(
    train: pd.DataFrame, val: pd.DataFrame, feature_cols: list[str]
):
    """Use only X to exclude train overlap and repeated X in validation.

    All raw validation labels are retained in validation_raw. For the strict
    validation view, ambiguous repeated X are excluded *without looking at y*.
    This is a diagnostic protocol, not a substitute for external test data.
    """
    train_hash = pd.Index(hash_features(train, feature_cols).unique())
    val_hash = hash_features(val, feature_cols)
    is_overlap = val_hash.isin(train_hash)
    repeated_within_val = val_hash.duplicated(keep=False)
    unique_mask = ~(is_overlap | repeated_within_val)
    strict_val = val.loc[unique_mask].copy()
    report = {
        "validation_original_rows": int(len(val)),
        "validation_overlap_with_clean_train": int(is_overlap.sum()),
        "validation_rows_in_repeated_feature_groups": int(repeated_within_val.sum()),
        "validation_strict_rows": int(len(strict_val)),
    }
    print("\nVALIDATION duplicate audit (feature fingerprints only):")
    for key, value in report.items():
        print(f"  {key}: {value:,}")
    print(f"  Raw validation attack rate: {val['__target'].mean():.2%}")
    if len(strict_val):
        print(f"  Strict validation attack rate: {strict_val['__target'].mean():.2%}")
    if strict_val["__target"].nunique() != 2:
        raise ValueError("Strict validation has fewer than 2 classes")
    return strict_val, report


def best_threshold(y, scores) -> float:
    precision, recall, thresholds = precision_recall_curve(y, scores)
    if thresholds.size == 0:
        raise ValueError("No thresholds available")
    f1 = np.divide(
        2 * precision[:-1] * recall[:-1],
        precision[:-1] + recall[:-1],
        out=np.zeros_like(precision[:-1]),
        where=(precision[:-1] + recall[:-1]) > 0,
    )
    return float(thresholds[np.argmax(f1)])


def run(args):
    df, features = prepare_without_global_dedup(read_parquets(args.data_dir))
    # Do not use main.prepare_data (it drops conflicts based on ALL labels).
    train_raw, validation_raw, _friday_not_used = split_temporal(df)
    del df, _friday_not_used
    if not (train_raw["__capture_day"].isin([0, 1, 2]).all()
            and validation_raw["__capture_day"].eq(3).all()):
        raise ValueError("Expected Mon-Wed train and Thursday validation")

    print(f"\nBEFORE dedup: Train={len(train_raw):,}; Validation={len(validation_raw):,}")
    train, audit_train = clean_train_only(train_raw, features)
    del train_raw
    val_strict, audit_val = audit_and_filter_validation(train, validation_raw, features)
    result_dir = args.output_dir
    result_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    thresholds = {}

    X_train, y_train = train[features], train["__target"]
    X_val_raw, y_val_raw = validation_raw[features], validation_raw["__target"]
    X_val, y_val = val_strict[features], val_strict["__target"]
    for name, model in build_models(args.jobs, y_train).items():
        print(f"\nFitting {name} on TRAIN ONLY...")
        model.fit(X_train, y_train)
        val_score = model.predict_proba(X_val)[:, 1]
        if not np.isfinite(val_score).all():
            raise ValueError(f"Non-finite probabilities from {name}")
        threshold = best_threshold(y_val, val_score)
        thresholds[name] = threshold
        # Always state that optimized-threshold F1 is evaluated on SAME validation.
        m05 = get_metrics(y_val, (val_score >= 0.5).astype(int), val_score)
        mt = get_metrics(y_val, (val_score >= threshold).astype(int), val_score)
        raw_scores = model.predict_proba(X_val_raw)[:, 1]
        raw_m05 = get_metrics(y_val_raw, (raw_scores >= 0.5).astype(int), raw_scores)
        for view, setting, m, t in [
            ("validation_strict", "default_0.5", m05, 0.5),
            ("validation_strict", "tuned_same_validation", mt, threshold),
            ("validation_raw", "default_0.5", raw_m05, 0.5),
        ]:
            rows.append({"model": name, "view": view, "setting": setting,
                         "threshold": float(t), **m})
        print(f"  Validation strict: default F1={m05['f1']:.4f}, "
              f"tuned F1={mt['f1']:.4f}, Recall={mt['recall']:.4f}, "
              f"FP={mt['fp']:,}, FN={mt['fn']:,}, threshold={threshold:.8g}")
        print(f"  Validation raw: default F1={raw_m05['f1']:.4f}")
        joblib.dump(model, result_dir / f"{name}.joblib", compress=3)
        del model, val_score, raw_scores

    pd.DataFrame(rows).to_csv(result_dir / "validation_metrics.csv", index=False)
    info = {
        "protocol": "temporal_split_first_train_only_cleaning",
        "train_days": [0, 1, 2],
        "validation_day": 3,
        "test_day": 4,
        "test_evaluated": False,
        "threshold_selected_on": "validation_strict_Thursday",
        "threshold_f1_warning": "This score was optimized on the same validation set; it is not independent generalization evidence.",
        "prior_test_exposure_warning": "Friday test had been inspected in earlier project runs. A new untouched temporal holdout is needed for final unbiased estimates.",
        "features": features,
        "train_audit": audit_train,
        "validation_audit": audit_val,
        "thresholds": thresholds,
    }
    (result_dir / "audit_and_thresholds.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nSaved (no Friday evaluation): {result_dir.resolve()}")
    print("Do NOT compare tuned validation F1 to an untouched test F1.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/temporal_split_first"))
    parser.add_argument("--jobs", type=int, default=4)
    run(parser.parse_args())
