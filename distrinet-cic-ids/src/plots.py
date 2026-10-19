"""Non-interactive figures saved to results/, suitable for reports."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import ConfusionMatrixDisplay, precision_recall_curve, roc_curve


def bar_comparison(table: pd.DataFrame, metric: str, output: Path):
    if table.empty:
        return
    pivot = table.pivot(index='Fold', columns='Config', values=metric)
    ax = pivot.plot.bar(figsize=(11, 5), rot=0)
    ax.set_ylabel(metric)
    ax.set_title(f'{metric} across weekday temporal folds')
    ax.grid(axis='y', alpha=.2)
    ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1))
    plt.tight_layout()
    plt.savefig(output, dpi=160, bbox_inches='tight')
    plt.close()


def distribution_plot(rows: list[dict], output: Path):
    if not rows:
        return
    df = pd.DataFrame(rows).drop_duplicates(subset=['Config']).set_index('Config')
    fig, ax = plt.subplots(figsize=(9, 5))
    df[['BENIGN', 'ATTACK']].plot(kind='bar', ax=ax, rot=0)
    ax.set_ylabel('Samples')
    ax.set_title('TRAIN class distribution (before / after resampling 0.5)')
    ax.grid(axis='y', alpha=.2)
    plt.tight_layout()
    plt.savefig(output, dpi=160, bbox_inches='tight')
    plt.close()


def final_plots(model_name: str, y, scores, threshold: float, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    p = (scores >= threshold).astype(int)
    fig, ax = plt.subplots(figsize=(5, 4))
    ConfusionMatrixDisplay.from_predictions(y, p, display_labels=['BENIGN (0)', 'ATTACK (1)'], ax=ax,
                                            colorbar=False, cmap='Blues')
    ax.set_title(f'{model_name} - Binary confusion matrix')
    plt.tight_layout()
    plt.savefig(output / f'{model_name}_confusion.png', dpi=160)
    plt.close()
    if len(set(y)) == 2:
        from sklearn.metrics import roc_auc_score, average_precision_score
        fig, ax = plt.subplots(figsize=(6, 4))
        fpr, tpr, _ = roc_curve(y, scores)
        ax.plot(fpr, tpr, label=f'ROC-AUC={roc_auc_score(y, scores):.4f}')
        ax.plot([0, 1], [0, 1], '--', alpha=.4)
        ax.set_xlabel('FPR'); ax.set_ylabel('TPR'); ax.legend(); ax.set_title(f'{model_name} ROC')
        plt.tight_layout(); plt.savefig(output / f'{model_name}_roc.png', dpi=160); plt.close()
        fig, ax = plt.subplots(figsize=(6, 4))
        precision, recall, _ = precision_recall_curve(y, scores)
        ax.plot(recall, precision, label=f'AP={average_precision_score(y, scores):.4f}')
        ax.set_xlabel('Recall Attack'); ax.set_ylabel('Precision Attack'); ax.legend()
        ax.set_title(f'{model_name} Precision-Recall')
        plt.tight_layout(); plt.savefig(output / f'{model_name}_pr.png', dpi=160); plt.close()
