"""Run sliding-window object recognition from live AFE measurements."""

from __future__ import annotations

import argparse
import time
from collections import deque
from pathlib import Path

import joblib
import numpy as np
import serial

from ml.features import extract_features
from software.protocol import parse_afe_row


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--model", type=Path, default=Path("models/random_forest.joblib"))
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--threshold", type=float, default=0.55)
    parser.add_argument("--stride", type=int, default=5, help="Frames between predictions")
    return parser.parse_args()


def main() -> None:
    args = arguments()
    bundle = joblib.load(args.model)
    model = bundle["model"]
    window_size = int(bundle.get("window_size", 40))
    window: deque[tuple[float, ...]] = deque(maxlen=window_size)
    frames_since_prediction = 0

    with serial.Serial(args.port, args.baud, timeout=1) as device:
        time.sleep(2)
        device.reset_input_buffer()
        print(f"Connected to {args.port}. Press Ctrl+C to stop.")
        try:
            while True:
                line = device.readline().decode("utf-8", errors="ignore")
                frame = parse_afe_row(line)
                if frame is None or not frame.is_valid:
                    continue
                window.append(frame.filtered_ohm)
                frames_since_prediction += 1
                if len(window) < window_size or frames_since_prediction < args.stride:
                    continue
                frames_since_prediction = 0

                features = extract_features(np.asarray(window)).reshape(1, -1)
                probabilities = model.predict_proba(features)[0]
                winner = int(np.argmax(probabilities))
                confidence = float(probabilities[winner])
                label = str(model.classes_[winner])
                display = label if confidence >= args.threshold else "uncertain"
                print(f"\rObject: {display:<18} confidence: {confidence:6.1%}", end="", flush=True)
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
