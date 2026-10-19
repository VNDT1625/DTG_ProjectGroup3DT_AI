"""Lightweight JSON, CSV and metadata helpers."""
from datetime import datetime, timezone
import json
from pathlib import Path
import numpy as np


def write_json(path: Path, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=json_default)


def read_json(path: Path) -> dict:
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


def json_default(item):
    if isinstance(item, np.integer):
        return int(item)
    if isinstance(item, np.floating):
        return float(item)
    if isinstance(item, np.ndarray):
        return item.tolist()
    raise TypeError(f"Cannot serialize: {type(item).__name__}")


def timestamp():
    return datetime.now(timezone.utc).isoformat()
