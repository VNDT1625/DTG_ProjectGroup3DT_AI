"""Temporal experiments, full-train candidate selection, and artifact export."""
from __future__ import annotations
import gc
import time
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from .config import (SPLIT_DIR, PROCESSED_DIR, MODEL_DIR, RESULT_DIR, MODEL_FILES,
                     MODEL_NAMES, SEED, RESAMPLING_RATIO)
from .metrics import binary_metrics, attack_scores, select_threshold, group_reports
from .models import CV_CONFIGS, FINAL_CONFIGS, class_distribution_after, make_pipeline
from .plots import bar_comparison, distribution_plot, final_plots
from .utils import read_json, write_json, timestamp


def load_feature_columns():
    cols = read_json(PROCESSED_DIR / 'feature_columns.json')['feature_columns']
    if len(set(cols)) != len(cols) or not cols:
        raise ValueError('Invalid feature schema')
    return cols


def to_xy(frame: pd.DataFrame, features: list[str]):
    if set(features) - set(frame.columns):
        raise ValueError(f'Missing model features: {sorted(set(features) - set(frame.columns))}')
    x = frame[features].to_numpy(dtype=np.float32, copy=True)
    x[~np.isfinite(x)] = np.nan  # Train-fitted imputer handles missing / invalid measurements
    y = frame['target'].to_numpy(dtype=np.int8)
    return x, y


def temporal_cv(family: str, max_train_rows: int = 50_000, quick: bool = False, n_jobs: int = 2):
    if max_train_rows != 0 and max_train_rows < 10:
        raise ValueError('max_train_rows must be >=10 or 0 for all rows')
    features = load_feature_columns()
    train70 = pd.read_parquet(SPLIT_DIR / 'train70.parquet')
    labels = train70['target'].to_numpy(dtype=np.int8)
    fold_path = SPLIT_DIR / 'temporal_folds_train70.npz'
    out = RESULT_DIR / 'temporal'
    out.mkdir(parents=True, exist_ok=True)
    results, distributions = [], []
    with np.load(fold_path) as folds:
        for fnum in (1, 2, 3):
            fold = f'fold{fnum}'
            tr = folds[f'{fold}_train_pos']
            va = folds[f'{fold}_val_pos']
            if max_train_rows and len(tr) > max_train_rows:
                tr, _ = train_test_split(tr, train_size=max_train_rows, stratify=labels[tr], random_state=SEED)
            xtr, ytr = to_xy(train70.iloc[tr], features)
            xva, yva = to_xy(train70.iloc[va], features)
            print(f'\n{MODEL_NAMES[family]} - {fold}: train={len(tr):,}; weekday validation={len(va):,}')
            for mode in CV_CONFIGS:
                current = f'{family.upper()}-{mode}'
                before0, before1 = int((ytr == 0).sum()), int((ytr == 1).sum())
                after0, after1 = class_distribution_after(ytr, mode)
                distributions.append({'Fold': fold, 'Config': current, 'BENIGN': after0, 'ATTACK': after1,
                                      'Before_BENIGN': before0, 'Before_ATTACK': before1})
                pipe = make_pipeline(family, mode, ytr, quick=quick, n_jobs=n_jobs)
                start = time.perf_counter()
                pipe.fit(xtr, ytr)
                seconds = time.perf_counter() - start
                scores = attack_scores(pipe, xva)
                stats = binary_metrics(yva, scores, 0.5)
                results.append({'Fold': fold, 'Config': current, 'Mode': mode,
                                'Train_Rows': len(ytr), 'Val_Rows': len(yva),
                                'Train_Seconds': seconds, **stats})
                print(f'  {current:19} F1={stats["F1_Attack"]:.4f} Recall={stats["Recall_Attack"]:.4f} FPR={stats["FPR"]:.5f}')
                pd.DataFrame(results).to_csv(out / f'{family}_temporal.csv', index=False)
                del pipe, scores
                gc.collect()
            del xtr, xva
            gc.collect()
    table = pd.DataFrame(results)
    mean = table.groupby('Config', as_index=False)[['F1_Attack', 'Recall_Attack', 'FPR',
           'FNR', 'Precision_Attack', 'Average_Precision', 'ROC_AUC']].mean().sort_values('F1_Attack', ascending=False)
    mean.to_csv(out / f'{family}_temporal_mean.csv', index=False)
    pd.DataFrame(distributions).to_csv(out / f'{family}_temporal_distributions.csv', index=False)
    for metric in ('F1_Attack', 'Recall_Attack', 'FPR'):
        bar_comparison(table, metric, out / f'{family}_temporal_{metric}.png')
    # Fold3 resampling class counts, comparable to original dataset
    last_fold = [d for d in distributions if d['Fold'] == 'fold3']
    distribution_plot(last_fold, out / f'{family}_fold3_class_distributions.png')
    print('\nThree-fold mean metrics:\n', mean.to_string(index=False))
    return table


def fit_final(family: str, fpr_limit: float = 0.01, quick: bool = False, n_jobs: int = 2,
              candidate_modes: tuple[str, ...] | None = None):
    """Train only on train70, select config + threshold only using outer validation15."""
    features = load_feature_columns()
    train = pd.read_parquet(SPLIT_DIR / 'train70.parquet')
    val = pd.read_parquet(SPLIT_DIR / 'validation15.parquet')
    xtr, ytr = to_xy(train, features)
    xva, yva = to_xy(val, features)
    modes = candidate_modes if candidate_modes is not None else FINAL_CONFIGS[family]
    out = RESULT_DIR / 'validation'
    out.mkdir(parents=True, exist_ok=True)
    candidates = []
    for mode in modes:
        print(f'\nFull train {family}/{mode}, rows={len(ytr):,} ...')
        pipe = make_pipeline(family, mode, ytr, quick=quick, n_jobs=n_jobs)
        start = time.perf_counter()
        pipe.fit(xtr, ytr)
        secs = time.perf_counter() - start
        scores = attack_scores(pipe, xva)
        selected, grid, feasible = select_threshold(yva, scores, fpr_limit=fpr_limit)
        grid.insert(0, 'Mode', mode)
        grid.to_csv(out / f'{family}_{mode}_threshold_grid.csv', index=False)
        name = f'{family}-{mode}'
        selected.update({'Config': name, 'Mode': mode, 'Train_Seconds': secs, 'FPR_Constraint_Met': feasible})
        candidates.append({'pipe': pipe, 'scores': scores, 'selected': selected})
        print(f'  Threshold={selected["Threshold"]:.2f} F1={selected["F1_Attack"]:.5f} FPR={selected["FPR"]:.5f}')
    feasible_candidates = [c for c in candidates if c['selected']['FPR_Constraint_Met']]
    considered = feasible_candidates if feasible_candidates else candidates
    chosen = sorted(considered, key=lambda a: (-a['selected']['F1_Attack'], a['selected']['FPR']))[0]
    rows = pd.DataFrame([c['selected'] for c in candidates])
    rows.to_csv(out / f'{family}_candidate_selection.csv', index=False)
    artifact_name, metadata_name = MODEL_FILES[family]
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_DIR / artifact_name
    joblib.dump(chosen['pipe'], model_path, compress=3)
    chosen_row = chosen['selected']
    metadata = {
        'model_family': family, 'model_name': MODEL_NAMES[family],
        'selected_config': chosen_row['Config'], 'threshold': float(chosen_row['Threshold']),
        'positive_class': 1, 'negative_class': 0,
        'feature_columns': features, 'n_features': len(features),
        'model_artifact': artifact_name,  # relative path, so moving project works
        'train_rows': len(ytr), 'validation_rows': len(yva),
        'train_distribution': {'BENIGN': int((ytr == 0).sum()), 'ATTACK': int((ytr == 1).sum())},
        'resampling_ratio_attack_over_benign': RESAMPLING_RATIO if chosen_row['Mode'] in ('under-0.5','smote-0.5') else None,
        'fpr_limit': fpr_limit, 'fpr_constraint_met': bool(chosen_row['FPR_Constraint_Met']),
        'validation_selected_metrics': {k: float(chosen_row[k]) for k in
            ('Accuracy','Precision_Attack','Recall_Attack','F1_Attack','FPR','FNR','Average_Precision','ROC_AUC')},
        'split_method': 'stratified outer 70/15/15; weekday temporal folds inside train70',
        'limitation': 'Outer validation and test are class-stratified random, NOT true future-date holdouts.',
        'test15_touched': False, 'saved_at_utc': timestamp(),
    }
    write_json(MODEL_DIR / metadata_name, metadata)
    again = joblib.load(model_path)  # only loads artifact we just wrote
    check = attack_scores(again, xva[:50])
    assert np.allclose(check, chosen['scores'][:50], atol=1e-6), 'Model reload mismatch'
    by_day, by_type = group_reports(val, chosen['scores'] >= chosen_row['Threshold'], MODEL_NAMES[family])
    by_day.to_csv(out / f'{family}_by_day.csv', index=False)
    by_type.to_csv(out / f'{family}_by_attack_type.csv', index=False)
    final_plots(family, yva, chosen['scores'], chosen_row['Threshold'], out)
    print(f'Saved {model_path}, {MODEL_DIR / metadata_name}')
    print(rows[['Config', 'Threshold', 'F1_Attack', 'Recall_Attack', 'FPR']].to_string(index=False))
    del train, val, xtr, xva
    gc.collect()
    return metadata
