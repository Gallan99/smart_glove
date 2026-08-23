"""Capture labeled object-grasp trials from the five-channel AFE stream."""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

import serial

from software.protocol import parse_afe_row


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, help="Serial port, for example COM4 or /dev/ttyUSB0")
    parser.add_argument("--label", required=True, help="Object label written to the dataset")
    parser.add_argument("--trials", type=int, default=30, help="Number of independent grasps")
    parser.add_argument("--frames", type=int, default=40, help="Frames recorded per grasp")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--output", type=Path, help="Output CSV; defaults to data/object_recognition/<label>.csv")
    return parser.parse_args()


def main() -> None:
    args = arguments()
    if args.trials < 1 or args.frames < 2:
        raise SystemExit("--trials must be positive and --frames must be at least 2")

    output = args.output or Path("data") / "object_recognition" / f"{args.label}.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    write_header = not output.exists() or output.stat().st_size == 0

    with serial.Serial(args.port, args.baud, timeout=1) as device, output.open(
        "a", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.writer(handle)
        if write_header:
            writer.writerow(["Label", "Trial_ID", "Time", "S0", "S1", "S2", "S3", "S4"])

        time.sleep(2)
        device.reset_input_buffer()
        print(f"Connected to {args.port}; writing {output}")

        for trial_id in range(1, args.trials + 1):
            input(f"Prepare {args.label}; press Enter for trial {trial_id}/{args.trials}...")
            device.reset_input_buffer()
            first_time_ms: int | None = None
            collected = 0

            while collected < args.frames:
                line = device.readline().decode("utf-8", errors="ignore")
                frame = parse_afe_row(line)
                if frame is None or not frame.is_valid:
                    continue
                if first_time_ms is None:
                    first_time_ms = frame.time_ms
                relative_s = (frame.time_ms - first_time_ms) / 1000.0
                writer.writerow([args.label, trial_id, relative_s, *frame.filtered_ohm])
                handle.flush()
                collected += 1
                print(f"\r  frames {collected:02d}/{args.frames}", end="", flush=True)
            print("  complete")


if __name__ == "__main__":
    main()
