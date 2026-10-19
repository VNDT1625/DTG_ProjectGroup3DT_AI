"""Outer stratified split and day-based expanding temporal folds within train70."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from .config import DAYS, PROCESSED_DIR, SPLIT_DIR, SEED
from .utils import read_json, write_json


def day_from_source(filename: str) -> int:
    matches = [i for i, day in enumerate(DAYS) if day.lower() in str(filename).lower()]
    if len(matches) != 1:
        raise ValueError(f"Cannot identify weekday from _source_file={filename!r}")
    return matches[0]


def split_data(source: Path = PROCESSED_DIR / "ids_binary_clean.parquet",
               out: Path = SPLIT_DIR, seed: int = SEED):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(source)
    y = df['target'].to_numpy(dtype=np.int8)
    all_idx = np.arange(len(df), dtype=np.int64)
    tr_idx, other_idx = train_test_split(all_idx, test_size=0.3, stratify=y, random_state=seed)
    va_idx, te_idx = train_test_split(other_idx, test_size=0.5, stratify=y[other_idx], random_state=seed)
    if len(np.unique(np.concatenate([tr_idx, va_idx, te_idx]))) != len(df):
        raise AssertionError("Outer datasets overlap")
    partitions = {"train70": tr_idx, "validation15": va_idx, "test15": te_idx}
    stats = []
    for name, idx in partitions.items():
        # Preserve order: NPZ positions in temporal folds refer to this saved order!
        df.iloc[idx].to_parquet(out / f"{name}.parquet", index=False)
        yy = y[idx]
        stats.append({"Split": name, "Rows": len(idx), "BENIGN": int((yy == 0).sum()),
                      "ATTACK": int((yy == 1).sum()), "Attack_Ratio": float(yy.mean())})
    np.savez_compressed(out / "outer_split_indices.npz", train_idx=tr_idx, val_idx=va_idx, test_idx=te_idx)

    tr_day = np.array([day_from_source(x) for x in df.iloc[tr_idx]['_source_file']], dtype=np.int8)
    tr_y = y[tr_idx]
    fold_arrays = {}
    folds_stats = []
    for val_day in (2, 3, 4):
        fold = f"fold{val_day-1}"
        tr = np.flatnonzero(tr_day < val_day)
        va = np.flatnonzero(tr_day == val_day)
        if len(tr) == 0 or len(va) == 0:
            raise ValueError(f"Empty {fold}; daily files may be missing")
        if set(np.unique(tr_y[tr])) != {0, 1}:
            raise ValueError(f"{fold} train must contain both 0 and 1")
        fold_arrays[f"{fold}_train_pos"] = tr.astype(np.int32)
        fold_arrays[f"{fold}_val_pos"] = va.astype(np.int32)
        folds_stats.append({"Fold": fold, "Train_Through": DAYS[val_day - 1],
                            "Validate_On": DAYS[val_day], "Train_Rows": len(tr),
                            "Validation_Rows": len(va), "Train_Attack_Ratio": float(tr_y[tr].mean()),
                            "Val_Attack_Ratio": float(tr_y[va].mean())})
    np.savez_compressed(out / "temporal_folds_train70.npz", **fold_arrays)
    columns = read_json(Path(source).parent / "feature_columns.json")["feature_columns"]
    write_json(out / "split_manifest.json", {
        "seed": seed, "method": "stratified outer 70/15/15; weekday expanding folds within train70",
        "feature_columns": columns, "outer_splits": stats, "temporal_folds": folds_stats,
        "warning": "Outer validation/test are random stratified, NOT future-date holdouts."
    })
    print(pd.DataFrame(stats).to_string(index=False))
    print(pd.DataFrame(folds_stats).to_string(index=False))
    return stats, folds_stats
