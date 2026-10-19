import numpy as np
import pandas as pd
import pytest
from src.models import make_pipeline, class_distribution_after
from src.inference import predict_frame, validate_input
from src.metrics import binary_metrics, select_threshold


def sample_xy(n=100):
    r = np.random.default_rng(42)
    y = np.r_[np.zeros(int(n * 0.8), dtype=np.int8), np.ones(n - int(n * 0.8), dtype=np.int8)]
    x = r.normal(size=(n, 4)).astype('float32')
    x[y == 1, 0] += 3
    return x, y


@pytest.mark.parametrize('family', ['lr', 'rf', 'xgb'])
@pytest.mark.parametrize('mode', ['original', 'weighted', 'under-0.5', 'smote-0.5'])
def test_pipeline_modes(family, mode):
    x, y = sample_xy()
    pipe = make_pipeline(family, mode, y, quick=True, n_jobs=1)
    pipe.fit(x, y)
    p = pipe.predict_proba(x[:5])
    assert p.shape == (5, 2)
    assert np.isfinite(p).all()
    if mode.startswith('under'):
        assert class_distribution_after(y, mode) == (40, 20)
    if mode.startswith('smote'):
        assert class_distribution_after(y, mode) == (80, 40)


def test_under_only_changes_benign_and_smote_only_attack():
    y = np.r_[np.zeros(80, dtype=np.int8), np.ones(20, dtype=np.int8)]
    assert class_distribution_after(y, 'under-0.5') == (40, 20)
    assert class_distribution_after(y, 'smote-0.5') == (80, 40)


def test_csv_schema_and_frozen_decision():
    x, y = sample_xy()
    pipe = make_pipeline('lr', 'original', y, quick=True)
    pipe.fit(x, y)
    features = ['one', 'two', 'three', 'four']
    input_df = pd.DataFrame(x, columns=features)
    meta = {'feature_columns': features, 'threshold': 0.5}
    results = predict_frame(input_df, pipe, meta)
    assert len(results) == 100 and set(results.predicted_target.unique()) <= {0, 1}
    with pytest.raises(ValueError, match='Missing'):
        validate_input(input_df.drop(columns=['one']), features)
    input_df['one'] = input_df['one'].astype(object)
    input_df.loc[0, 'one'] = 'invalid'
    with pytest.raises(ValueError, match='Non-numeric'):
        validate_input(input_df, features)


def test_threshold_selection():
    truth = np.array([0,0,0,1,1,1], dtype=np.int8)
    scores = np.array([.05,.2,.1,.8,.9,.65])
    selected, grid, feasible = select_threshold(truth, scores, fpr_limit=0.01)
    assert feasible
    assert selected['FPR'] == 0
    assert selected['F1_Attack'] == 1.0
    assert binary_metrics(truth, scores, .5)['FN'] == 0
