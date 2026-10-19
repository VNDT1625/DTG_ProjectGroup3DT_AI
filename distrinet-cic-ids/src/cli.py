"""VS Code terminal entrypoint: python -m src.cli <command>."""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
from .config import RAW_DIR, PROCESSED_DIR, SAMPLES_DIR, SPLIT_DIR, ensure_dirs
from .split import split_data
from .train import temporal_cv, fit_final
from .evaluate import evaluate_test
from .utils import read_json


def create_sample(rows: int = 100):
    """Make a genuine-schema, UNLABELED demo CSV from train70; no Test leakage."""
    features = read_json(PROCESSED_DIR / 'feature_columns.json')['feature_columns']
    path = SPLIT_DIR / 'train70.parquet'
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(path)
    batch = next(pf.iter_batches(batch_size=rows, columns=features), None)
    if batch is None:
        raise RuntimeError('Training partition is empty')
    df = batch.to_pandas()
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    output = SAMPLES_DIR / 'sample_input.csv'
    df.to_csv(output, index=False, encoding='utf-8-sig')
    print(f'Generated demo CSV ({len(df)} unlabeled flows): {output}')


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='DistriNet-CIC-IDS2017: binary network intrusion detection (ATTACK=1).')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('inspect', help='Show first five rows / metadata for each Parquet')
    sub.add_parser('prepare', help='Clean and save the five daily Parquet files')
    sub.add_parser('split', help='Stratified 70/15/15 and weekday temporal folds within train70')
    cv = sub.add_parser('cv', help='4 configs x 3 temporal folds, train sample 50k by default')
    cv.add_argument('--model', choices=['lr','rf','xgb','all'], default='all')
    cv.add_argument('--max-train-rows', type=int, default=50_000, help='0=all rows in each fold')
    cv.add_argument('--quick', action='store_true', help='Small estimators for technical smoke checks')
    cv.add_argument('--n-jobs', type=int, default=2)
    fit = sub.add_parser('fit-final', help='Fit full train70 and select candidate/threshold on validation15')
    fit.add_argument('--model', choices=['lr','rf','xgb','all'], default='all')
    fit.add_argument('--fpr-limit', type=float, default=0.01)
    fit.add_argument('--n-jobs', type=int, default=2)
    fit.add_argument('--quick', action='store_true', help='Technical smoke check ONLY; not final research result')
    sub.add_parser('evaluate', help='Evaluate frozen artifacts once on test15, no tuning')
    sample = sub.add_parser('sample', help='Create unlabeled demo CSV from train70')
    sample.add_argument('--rows', type=int, default=100)
    args = parser.parse_args(argv)
    ensure_dirs()
    if args.command == 'inspect':
        from .data import inspect_raw
        inspect_raw(RAW_DIR)
    elif args.command == 'prepare':
        from .data import prepare
        prepare(RAW_DIR, PROCESSED_DIR)
    elif args.command == 'split':
        split_data()
    elif args.command == 'cv':
        for family in ('lr','rf','xgb') if args.model == 'all' else (args.model,):
            temporal_cv(family, max_train_rows=args.max_train_rows, quick=args.quick, n_jobs=args.n_jobs)
    elif args.command == 'fit-final':
        for family in ('lr','rf','xgb') if args.model == 'all' else (args.model,):
            fit_final(family, fpr_limit=args.fpr_limit, quick=args.quick, n_jobs=args.n_jobs)
    elif args.command == 'evaluate':
        evaluate_test()
    elif args.command == 'sample':
        if args.rows < 1:
            parser.error('--rows must be positive')
        create_sample(args.rows)


if __name__ == '__main__':
    main()
