"""Binary ATTACK=1 metrics, threshold search, day and original-label breakdown."""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, average_precision_score,
                             confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score)
from .config import THRESHOLDS


def attack_scores(pipe, x):
    classes = np.asarray(pipe.named_steps['model'].classes_)
    where = np.flatnonzero(classes == 1)
    if len(where) != 1:
        raise ValueError(f'Model must have ATTACK class 1; classes={classes}')
    return pipe.predict_proba(x)[:, int(where[0])]


def binary_metrics(y, scores, threshold: float = 0.5):
    y = np.asarray(y, dtype=np.int8)
    scores = np.asarray(scores, dtype=float)
    if len(y) != len(scores) or not np.isfinite(scores).all():
        raise ValueError('Label/score mismatch or non-finite scores')
    pred = (scores >= threshold).astype(np.int8)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    both = len(np.unique(y)) == 2
    return {
        'Threshold': float(threshold), 'Rows': len(y),
        'Accuracy': accuracy_score(y, pred),
        'Balanced_Accuracy': balanced_accuracy_score(y, pred) if both else float('nan'),
        'Precision_Attack': precision_score(y, pred, zero_division=0),
        'Recall_Attack': recall_score(y, pred, zero_division=0),
        'F1_Attack': f1_score(y, pred, zero_division=0),
        'FPR': fp / (fp + tn) if fp + tn else float('nan'),
        'FNR': fn / (fn + tp) if fn + tp else float('nan'),
        'ROC_AUC': roc_auc_score(y, scores) if both else float('nan'),
        'Average_Precision': average_precision_score(y, scores) if np.any(y == 1) else float('nan'),
        'TN': int(tn), 'FP': int(fp), 'FN': int(fn), 'TP': int(tp),
    }


def select_threshold(y, scores, fpr_limit: float = 0.01):
    """Choose best F1 on outer validation subject to FPR <= limit, never test."""
    grid = pd.DataFrame([binary_metrics(y, scores, t) for t in THRESHOLDS])
    eligible = grid.loc[grid['FPR'].fillna(1) <= fpr_limit]
    if eligible.empty:
        # Record unmet constraint rather than silently claiming success.
        chosen = grid.sort_values(['FPR', 'F1_Attack'], ascending=[True, False]).iloc[0]
        fulfilled = False
    else:
        chosen = eligible.sort_values(['F1_Attack', 'FPR'], ascending=[False, True]).iloc[0]
        fulfilled = True
    return dict(chosen), grid, fulfilled


def group_reports(frame: pd.DataFrame, y_pred, model_name: str):
    """Original Label is NOT used for prediction; per-type stats are attack recall only."""
    f = frame[['target', 'Label', '_source_file']].copy()
    f['pred'] = np.asarray(y_pred, dtype=np.int8)
    by_day = []
    for day, g in f.groupby('_source_file', observed=True):
        tn, fp, fn, tp = confusion_matrix(g['target'], g['pred'], labels=[0, 1]).ravel()
        by_day.append({'Model': model_name, 'Source_File': str(day), 'Rows': len(g),
                       'TP': int(tp), 'TN': int(tn), 'FP': int(fp), 'FN': int(fn),
                       'Recall_Attack': tp / (tp + fn) if tp + fn else float('nan'),
                       'FPR': fp / (fp + tn) if fp + tn else float('nan')})
    by_type = []
    only = f.loc[f['target'] == 1]
    for label, g in only.groupby('Label', observed=True):
        found = int((g['pred'] == 1).sum())
        by_type.append({'Model': model_name, 'Attack_Type': str(label), 'Actual_ATTACK': len(g),
                        'Detected_TP': found, 'Missed_FN': len(g) - found,
                        'Recall_Attack': found / len(g)})
    return pd.DataFrame(by_day), pd.DataFrame(by_type)
