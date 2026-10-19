"""Reproducible pipelines: LR baseline1, RF baseline2, XGBoost main model.

SMOTE changes only label=1, undersampling changes only label=0.
"""
from __future__ import annotations
import numpy as np
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler
from imblearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from .config import SEED, RESAMPLING_RATIO

CV_CONFIGS = ('original', 'weighted', 'under-0.5', 'smote-0.5')
FINAL_CONFIGS = {
    'lr': ('original', 'under-0.5'),
    'rf': ('original', 'under-0.5'),
    'xgb': ('original', 'weighted'),
}


def counts(y):
    y = np.asarray(y, dtype=np.int8)
    n0, n1 = int((y == 0).sum()), int((y == 1).sum())
    if n0 == 0 or n1 == 0:
        raise ValueError('Training requires both BENIGN (0) and ATTACK (1).')
    return n0, n1


def class_distribution_after(y, mode: str) -> tuple[int, int]:
    n0, n1 = counts(y)
    if mode == 'under-0.5':
        desired0 = int(np.ceil(n1 / RESAMPLING_RATIO))
        if desired0 > n0:
            raise ValueError(f'Cannot undersample BENIGN: only {n0}, target is {desired0}')
        return desired0, n1
    if mode == 'smote-0.5':
        desired1 = int(np.ceil(n0 * RESAMPLING_RATIO))
        if desired1 < n1:
            raise ValueError('Cannot SMOTE ATTACK downward; target already exceeded')
        return n0, desired1
    return n0, n1


def make_pipeline(family: str, mode: str, y_train, quick: bool = False, n_jobs: int = 2):
    if family not in ('lr', 'rf', 'xgb'):
        raise ValueError(f'Unknown model family {family}')
    if mode not in CV_CONFIGS:
        raise ValueError(f'Unknown mode {mode}; only resampling 0.5 is allowed')
    n0, n1 = counts(y_train)
    # Imputer learned only on train; inference uses the same trained imputer.
    steps = [('imputer', SimpleImputer(strategy='median'))]
    if family == 'lr':
        steps.append(('scaler', StandardScaler()))
    if mode == 'under-0.5':
        desired0, _ = class_distribution_after(y_train, mode)
        if desired0 < n0:
            steps.append(('sampler', RandomUnderSampler(
                sampling_strategy={0: desired0}, random_state=SEED)))
    elif mode == 'smote-0.5':
        _, desired1 = class_distribution_after(y_train, mode)
        if desired1 > n1:
            if n1 < 4:
                raise ValueError('SMOTE k_neighbors=3 requires >= 4 ATTACK rows')
            steps.append(('sampler', SMOTE(
                sampling_strategy={1: desired1}, k_neighbors=3, random_state=SEED)))

    if family == 'lr':
        estimator = LogisticRegression(
            solver='lbfgs', max_iter=350 if not quick else 120, C=1.0,
            class_weight='balanced' if mode == 'weighted' else None,
            random_state=SEED)
    elif family == 'rf':
        estimator = RandomForestClassifier(
            n_estimators=20 if quick else 100, max_depth=16,
            min_samples_leaf=2, max_features='sqrt', bootstrap=True,
            class_weight='balanced' if mode == 'weighted' else None,
            n_jobs=n_jobs, random_state=SEED)
    else:
        estimator = XGBClassifier(
            objective='binary:logistic', eval_metric='logloss',
            n_estimators=30 if quick else 220, max_depth=5,
            learning_rate=0.08, subsample=0.8, colsample_bytree=0.8,
            min_child_weight=3, reg_lambda=1.0, tree_method='hist',
            scale_pos_weight=n0 / n1 if mode == 'weighted' else 1.0,
            n_jobs=n_jobs, random_state=SEED)
    steps.append(('model', estimator))
    return Pipeline(steps)
