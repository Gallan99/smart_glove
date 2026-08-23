"""Parser for the five-channel AFE firmware serial protocol."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass


NUM_SENSORS = 5
FIELDS_PER_SENSOR = 5
EXPECTED_FIELDS = 1 + NUM_SENSORS * FIELDS_PER_SENSOR


@dataclass(frozen=True)
class AFEFrame:
    """One synchronized frame produced by ``stable_current_5sensors.ino``."""

    time_ms: int
    adc: tuple[float, ...]
    voltage_v: tuple[float, ...]
    resistance_mohm: tuple[float, ...]
    filtered_mohm: tuple[float, ...]
    status: tuple[str, ...]

    @property
    def filtered_ohm(self) -> tuple[float, ...]:
        """Filtered resistance values converted to ohms for the ML pipeline."""

        return tuple(value * 1e6 for value in self.filtered_mohm)

    @property
    def is_valid(self) -> bool:
        return all(math.isfinite(value) for value in self.filtered_mohm)


def _number(value: str) -> float:
    value = value.strip()
    if value.lower() == "nan":
        return math.nan
    return float(value)


def parse_afe_row(line: str) -> AFEFrame | None:
    """Parse a firmware row; return ``None`` for headers or malformed input."""

    stripped = line.strip()
    if not stripped or stripped.startswith("t_ms"):
        return None

    try:
        fields = next(csv.reader([stripped]))
        if len(fields) != EXPECTED_FIELDS:
            return None

        time_ms = int(float(fields[0]))
        adc: list[float] = []
        voltage: list[float] = []
        resistance: list[float] = []
        filtered: list[float] = []
        status: list[str] = []

        for sensor_id in range(NUM_SENSORS):
            base = 1 + sensor_id * FIELDS_PER_SENSOR
            adc.append(_number(fields[base]))
            voltage.append(_number(fields[base + 1]))
            resistance.append(_number(fields[base + 2]))
            filtered.append(_number(fields[base + 3]))
            status.append(fields[base + 4].strip())

        return AFEFrame(
            time_ms=time_ms,
            adc=tuple(adc),
            voltage_v=tuple(voltage),
            resistance_mohm=tuple(resistance),
            filtered_mohm=tuple(filtered),
            status=tuple(status),
        )
    except (ValueError, csv.Error):
        return None


def compact_csv_header() -> list[str]:
    return ["t_ms", *(f"S{i}_MOhm" for i in range(NUM_SENSORS))]


def compact_csv_row(frame: AFEFrame) -> list[int | float]:
    return [frame.time_ms, *frame.filtered_mohm]
