import pytest
pytest.importorskip('pyarrow')
import numpy as np
import pandas as pd
from src.data import prepare
from src.split import split_data


def test_prepare_split_temporal(synthetic_parquets, tmp_path):
    out = tmp_path / 'processed'
    df = prepare(synthetic_parquets, out)
    assert set(df.target.unique()) == {0, 1}
    assert not df['Label'].astype(str).str.contains('Attempted').any()
    features = [c for c in df if c not in ['Label', 'target', '_source_file']]
    assert len(features) == 4
    assert not df.duplicated(subset=features).any()
    splits = out / 'splits'
    stats, folds = split_data(out / 'ids_binary_clean.parquet', splits)
    train = pd.read_parquet(splits / 'train70.parquet')
    val = pd.read_parquet(splits / 'validation15.parquet')
    test = pd.read_parquet(splits / 'test15.parquet')
    assert len(train) + len(val) + len(test) == len(df)
    assert len(folds) == 3
    with np.load(splits / 'temporal_folds_train70.npz') as saved:
        for i in (1, 2, 3):
            tr = saved[f'fold{i}_train_pos']
            va = saved[f'fold{i}_val_pos']
            assert not np.intersect1d(tr, va).size
            assert len(tr) and len(va)
            from src.split import day_from_source
            assert max(day_from_source(v) for v in train.iloc[tr]['_source_file']) < min(day_from_source(v) for v in train.iloc[va]['_source_file'])
