"""Central project configuration: paths and reproducible settings."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
SAMPLES_DIR = ROOT / "data" / "samples"
SPLIT_DIR = PROCESSED_DIR / "splits"
MODEL_DIR = ROOT / "models"
RESULT_DIR = ROOT / "results"

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
SEED = 42
RESAMPLING_RATIO = 0.5  # ATTACK / BENIGN after resampling; never 0.8
THRESHOLDS = [round(i / 100, 2) for i in range(1, 100)]

MODEL_FILES = {
    "lr": ("lr_baseline1_final.joblib", "lr_baseline1_metadata.json"),
    "rf": ("rf_baseline2_final.joblib", "rf_baseline2_metadata.json"),
    "xgb": ("xgb_main_final.joblib", "xgb_main_metadata.json"),
}
MODEL_NAMES = {"lr": "Logistic Regression", "rf": "Random Forest", "xgb": "XGBoost"}


def ensure_dirs():
    for folder in (RAW_DIR, PROCESSED_DIR, SAMPLES_DIR, SPLIT_DIR, MODEL_DIR, RESULT_DIR):
        folder.mkdir(parents=True, exist_ok=True)
