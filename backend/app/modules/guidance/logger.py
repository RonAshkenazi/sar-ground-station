from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from .models import DroneState, GuidanceRecommendation


COLUMNS = [
    "timestamp_ms",
    "mode",
    "target_cell_id",
    "target_lat",
    "target_lon",
    "drone_lat",
    "drone_lon",
    "bearing_deg",
    "distance_m",
    "final_score",
    "evidence_score",
    "uncertainty_score",
    "peak_score",
    "travel_cost",
    "oscillation_penalty",
    "gps_valid",
    "data_fresh",
]


class GuidanceLogger:
    def __init__(self) -> None:
        from app.storage.data_paths import get_temp_dir
        from .config import GUIDANCE_HISTORY_SUBPATH

        path = Path(get_temp_dir()) / GUIDANCE_HISTORY_SUBPATH
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file = path.open("a", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=COLUMNS, extrasaction="ignore")
        if path.stat().st_size == 0:
            self._writer.writeheader()

    def log(self, rec: GuidanceRecommendation, drone: DroneState) -> None:
        try:
            row = asdict(rec)
            row["drone_lat"] = drone.lat
            row["drone_lon"] = drone.lon
            self._writer.writerow(row)
            self._file.flush()
        except Exception:
            pass
