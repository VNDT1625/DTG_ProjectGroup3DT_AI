"""Frozen final test evaluation. Do not tune models using its outputs."""
from __future__ import annotations
from pathlib import Path
import time
import numpy as np
import pandas as pd
from .config import SPLIT_DIR, RESULT_DIR, MODEL_NAMES
from .inference import load_trusted_model, predict_frame
from .metrics import binary_metrics, group_reports
from .plots import final_plots


def evaluate_test():
    test = pd.read_parquet(SPLIT_DIR / 'test15.parquet')
    y = test['target'].to_numpy(dtype=np.int8)
    out = RESULT_DIR / 'test_final'
    out.mkdir(parents=True, exist_ok=True)
    rows, preds, days, types = [], pd.DataFrame({'true_target': y}), [], []
    for family in ('lr', 'rf', 'xgb'):
        pipe, meta = load_trusted_model(family)
        start = time.perf_counter()
        pred = predict_frame(test, pipe, meta)
        secs = time.perf_counter() - start
        labels = pred['predicted_target'].to_numpy(dtype=np.int8)
        scores = pred['attack_score'].to_numpy(dtype=float)
        metrics = binary_metrics(y, scores, float(meta['threshold']))
        rows.append({'Model': MODEL_NAMES[family], 'Config': meta.get('selected_config', meta.get('model_name')),
                     'Predict_Seconds': secs, 'Milliseconds_per_flow': secs * 1000 / len(y), **metrics})
        preds[f'{family}_score'] = scores
        preds[f'{family}_prediction'] = labels
        d, t = group_reports(test, labels, MODEL_NAMES[family])
        days.append(d); types.append(t)
        final_plots(family, y, scores, float(meta['threshold']), out)
        print(MODEL_NAMES[family], 'F1=', round(metrics['F1_Attack'], 5), 'FPR=', round(metrics['FPR'], 5))
    table = pd.DataFrame(rows)
    table.to_csv(out / 'final_test_metrics_3models.csv', index=False)
    preds.to_csv(out / 'final_test_predictions.csv', index=False)
    pd.concat(days, ignore_index=True).to_csv(out / 'final_test_by_day.csv', index=False)
    pd.concat(types, ignore_index=True).to_csv(out / 'final_test_by_attack_type.csv', index=False)
    print('\nFINAL TEST (no tuning):\n', table.to_string(index=False))
    return table
