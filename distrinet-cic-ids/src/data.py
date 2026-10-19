"""Inspect and clean corrected DistriNet-CIC-IDS2017 Parquet datasets.

The original label is preserved ONLY for descriptive per-attack-type recall.
No model may use Label, target or _source_file as a feature.
"""
from __future__ import annotations
import gc
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from .config import RAW_DIR, PROCESSED_DIR, ensure_dirs
from .utils import write_json

EXCLUDED = ("Label", "target", "_source_file")


def find_parquets(folder: Path = RAW_DIR):
    paths = sorted(x for x in Path(folder).rglob("*") if x.is_file() and x.suffix.lower() in (".parquet", ".pq"))
    if not paths:
        raise FileNotFoundError(f"No Parquet files found in {folder}. Put the 5 Kaggle files there.")
    return paths


def inspect_raw(folder: Path = RAW_DIR) -> pd.DataFrame:
    """Print per-file metadata and first five rows without loading whole files."""
    rows = []
    for path in find_parquets(folder):
        pf = pq.ParquetFile(path)
        names = pf.schema_arrow.names
        head = next(pf.iter_batches(batch_size=5), None)
        print(f"\n{'='*72}\n{path.name} | {pf.metadata.num_rows:,} rows | {len(names)} columns")
        print('Columns:', names)
        if head is not None:
            print(head.to_pandas().to_string(index=False, max_cols=12))
        rows.append({"File": path.name, "Rows": pf.metadata.num_rows, "Columns": len(names)})
    summary = pd.DataFrame(rows)
    print('\nDATASET SUMMARY\n', summary.to_string(index=False))
    print('Total rows:', f"{summary['Rows'].sum():,}")
    return summary


def prepare(folder: Path = RAW_DIR, output_dir: Path = PROCESSED_DIR) -> pd.DataFrame:
    """Notebook-equivalent cleaning; memory needs RAM for the merged dataset.

    1. Drop missing/Attempted labels.
    2. Assign binary target Benign=0, other known attack labels=1.
    3. Remove *all* groups where identical features have conflicting targets.
    4. Deduplicate exact features, keeping one representative.
    NaN/Infinity numeric features are retained as NaN for train-only imputers.
    """
    ensure_dirs()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = find_parquets(folder)
    if len(paths) != 5:
        print(f"WARNING: expected 5 daily files, found {len(paths)}")
    all_frames = []
    common_names = None
    for path in paths:
        part = pd.read_parquet(path)
        label_candidates = [c for c in part.columns if c.strip().lower() == "label"]
        if len(label_candidates) != 1:
            raise ValueError(f"Expected exactly one Label column in {path.name}; got {label_candidates}")
        if label_candidates[0] != "Label":
            part = part.rename(columns={label_candidates[0]: "Label"})
        names = list(part.columns)
        if common_names is None:
            common_names = names
        if set(names) != set(common_names):
            raise ValueError(f"Schema mismatch: {path.name}; missing/extra columns")
        part = part[common_names]
        part["_source_file"] = path.name
        all_frames.append(part)
        print(f"Loaded {path.name}: {len(part):,} rows")
    df = pd.concat(all_frames, ignore_index=True, copy=False)
    del all_frames
    gc.collect()
    n_initial = len(df)

    labels = df["Label"].astype("string").str.strip()
    valid = labels.notna() & labels.ne("").fillna(False)
    attempted = labels.str.contains("Attempted", case=False, regex=False, na=False)
    removed_missing_label = int((~valid).sum())
    removed_attempted = int((valid & attempted).sum())
    df = df.loc[valid & ~attempted].copy()
    df["Label"] = labels.loc[df.index].astype(str)
    df["target"] = (df["Label"].str.casefold() != "benign").astype("int8")

    features = [c for c in common_names if c != "Label"]
    if not features:
        raise ValueError("No numeric features found")
    for feature in features:
        if not pd.api.types.is_numeric_dtype(df[feature]):
            df[feature] = pd.to_numeric(df[feature], errors="coerce")
    # Convert infinities to NaN (median imputed on TRAIN only).
    df[features] = df[features].replace([np.inf, -np.inf], np.nan)
    missing_feature_values = int(df[features].isna().sum().sum())
    before_conflicts = len(df)

    # Only duplicate groups need the expensive groupby consistency check.
    duplicated = df.duplicated(subset=features, keep=False)
    dup = df.loc[duplicated, features + ["target"]]
    if not dup.empty:
        conflict = dup.groupby(features, dropna=False, sort=False)["target"].transform("nunique") > 1
        conflict_idx = dup.index[conflict]
    else:
        conflict_idx = pd.Index([])
    df = df.drop(index=conflict_idx)
    removed_conflicting = before_conflicts - len(df)
    before_dedup = len(df)
    df = df.drop_duplicates(subset=features, keep="first").reset_index(drop=True)
    removed_duplicates = before_dedup - len(df)
    if df.duplicated(subset=features).any():
        raise AssertionError("Duplicate feature vectors remain")
    if set(df["target"].unique()) != {0, 1}:
        raise ValueError("Cleaned dataset needs both classes BENIGN=0, ATTACK=1")

    df["Label"] = df["Label"].astype("category")
    df["_source_file"] = df["_source_file"].astype("category")
    df.to_parquet(output_dir / "ids_binary_clean.parquet", index=False)
    write_json(output_dir / "feature_columns.json", {
        "feature_columns": features, "target_column": "target", "benign_label": 0,
        "attack_label": 1, "excluded_from_model": list(EXCLUDED)
    })
    report = {
        "raw_rows": n_initial, "removed_missing_label_rows": removed_missing_label,
        "removed_attempted_rows": removed_attempted,
        "rows_after_label_filter": before_conflicts,
        "removed_conflicting_rows": removed_conflicting,
        "removed_duplicate_rows": removed_duplicates,
        "remaining_rows": len(df), "num_features": len(features),
        "remaining_benign": int((df["target"] == 0).sum()),
        "remaining_attack": int((df["target"] == 1).sum()),
        "missing_feature_values_to_impute_in_train_pipeline": missing_feature_values,
    }
    write_json(output_dir / "cleaning_report.json", report)
    print('CLEANING REPORT:', report)
    return df
