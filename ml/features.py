"""Feature extraction shared by training and real-time inference."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


SENSOR_COLUMNS = [f"S{i}" for i in range(5)]
REQUIRED_COLUMNS = {"Label", "Trial_ID", *SENSOR_COLUMNS}
FEATURE_NAMES = [
    *(f"{column}_mean" for column in SENSOR_COLUMNS),
    *(f"{column}_std" for column in SENSOR_COLUMNS),
]


def extract_features(frames: np.ndarray) -> np.ndarray:
    """Return five means followed by five population standard deviations."""

    values = np.asarray(frames, dtype=float)
    if values.ndim != 2 or values.shape[1] != len(SENSOR_COLUMNS):
        raise ValueError("frames must have shape (n_samples, 5)")
    if len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("frames must contain at least two finite samples")
    return np.concatenate((values.mean(axis=0), values.std(axis=0, ddof=0)))


def load_dataset(data_dir: str | Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Load per-object CSV files and aggregate each trial into ten features."""

    root = Path(data_dir)
    files = sorted(root.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {root}")

    feature_rows: list[np.ndarray] = []
    labels: list[str] = []
    sources: list[str] = []

    for path in files:
        frame = pd.read_csv(path)
        missing = REQUIRED_COLUMNS.difference(frame.columns)
        if missing:
            raise ValueError(f"{path.name} is missing columns: {sorted(missing)}")

        frame[SENSOR_COLUMNS] = frame[SENSOR_COLUMNS].replace(0.0, np.nan)
        frame[SENSOR_COLUMNS] = frame.groupby("Trial_ID")[SENSOR_COLUMNS].ffill()
        frame[SENSOR_COLUMNS] = frame.groupby("Trial_ID")[SENSOR_COLUMNS].bfill()

        for trial_id, trial in frame.groupby("Trial_ID", sort=True):
            values = trial[SENSOR_COLUMNS].to_numpy(dtype=float)
            if len(values) < 10 or not np.isfinite(values).all():
                continue
            feature_rows.append(extract_features(values))
            labels.append(str(trial.iloc[0]["Label"]))
            sources.append(f"{path.name}:{trial_id}")

    if not feature_rows:
        raise ValueError("No valid trials were found")
    return np.vstack(feature_rows), np.asarray(labels), sources
