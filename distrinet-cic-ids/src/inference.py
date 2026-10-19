"""Shared strict CSV schema validation and safe (trusted local) model inference."""
from __future__ import annotations
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from .config import MODEL_DIR, MODEL_FILES
from .metrics import attack_scores
from .utils import read_json


def load_trusted_model(family: str, model_dir: Path = MODEL_DIR):
    """Joblib is pickle-based; NEVER load untrusted files from users/uploads."""
    if family not in MODEL_FILES:
        raise ValueError(f'Model must be one of {list(MODEL_FILES)}')
    artifact_name, meta_name = MODEL_FILES[family]
    directory = Path(model_dir)
    meta = read_json(directory / meta_name)
    if meta.get('positive_class') != 1 or meta.get('negative_class') != 0:
        raise ValueError('Metadata label convention mismatch: ATTACK must equal 1')
    feats = meta['feature_columns']
    if meta.get('n_features') != len(feats) or len(set(feats)) != len(feats):
        raise ValueError('Invalid model feature schema')
    threshold = float(meta['threshold'])
    if not np.isfinite(threshold) or not (0 < threshold < 1):
        raise ValueError('Invalid frozen model threshold')
    # Resolve file name from our allowlisted mapping, not from metadata's arbitrary model_artifact.
    pipe = joblib.load(directory / artifact_name)
    return pipe, meta


def validate_input(frame: pd.DataFrame, features: list[str]):
    """Reject missing columns and invalid nonnumeric values; accept NaN/inf for train-fitted imputer."""
    missing = [col for col in features if col not in frame.columns]
    if missing:
        raise ValueError(f'Missing {len(missing)} required feature(s): {missing[:20]}')
    if len(frame) == 0:
        raise ValueError('CSV is empty')
    if frame.columns.duplicated().any():
        raise ValueError('Duplicate CSV column names')
    numeric = frame[features].apply(pd.to_numeric, errors='coerce')
    invalid = numeric.isna() & frame[features].notna()  # string text -> NaN, not valid missing
    if invalid.any().any():
        bad = invalid.stack()[lambda s: s].index.tolist()[:8]
        raise ValueError(f'Non-numeric feature data, sample (row_index, column): {bad}')
    x = numeric.to_numpy(dtype=np.float32)
    x[~np.isfinite(x)] = np.nan
    if np.isnan(x).all(axis=1).any():
        raise ValueError('At least one row has no valid numeric measurements')
    return x


def predict_frame(frame: pd.DataFrame, pipe, meta: dict, batch_size: int = 20_000):
    features = meta['feature_columns']
    x = validate_input(frame, features)
    threshold = float(meta['threshold'])
    scores = np.concatenate([attack_scores(pipe, x[i:i+batch_size]) for i in range(0, len(x), batch_size)])
    prediction = (scores >= threshold).astype(np.int8)
    out = pd.DataFrame({
        'row_id': np.arange(1, len(frame) + 1),
        'predicted_target': prediction,
        'predicted_label': np.where(prediction == 1, 'ATTACK', 'BENIGN'),
        'attack_score': scores,
        'threshold': threshold,
    })
    return out
