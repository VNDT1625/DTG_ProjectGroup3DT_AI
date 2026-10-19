import numpy as np
import pandas as pd
import pytest
from pathlib import Path


@pytest.fixture
def synthetic_parquets(tmp_path):
    """Synthetic data ONLY for verifying the code (not scientific model results)."""
    folder = tmp_path / 'raw'
    folder.mkdir()
    days = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')
    rng = np.random.default_rng(42)
    for day in days:
        x = rng.normal(size=(80, 4))
        y = np.array(['Benign' if i % 5 else 'DDoS' for i in range(80)], dtype=object)
        x[y == 'DDoS', 0] += 2.0
        frame = pd.DataFrame(x, columns=['Flow Duration', 'Flow Bytes/s', 'SYN Flag Count', 'Total Fwd Packets'])
        frame['Label'] = y
        # Every file contains an Attempted row, one exact duplicate, and a conflicting pair.
        frame.loc[1, 'Label'] = 'Attempted-relabel-as-Benign'
        dupe = frame.iloc[[2]].copy()
        conflict = frame.iloc[[3]].copy()
        conflict['Label'] = 'DDoS'
        frame = pd.concat([frame, dupe, conflict], ignore_index=True)
        frame.to_parquet(folder / f'Synthetic-{day}.parquet', index=False)
    return folder
