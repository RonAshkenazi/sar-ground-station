from __future__ import annotations

import threading
import time
from dataclasses import asdict
from typing import Optional

from . import config as cfg
from .grid import create_grid
from .logger import GuidanceLogger
from .models import GuidanceRecommendation, GuidanceState
from .recommendation import compute_recommendation
from .state import init_cell_states, ingest_evidence, ingest_health, ingest_pose, tick_age


class GuidanceEngine:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: Optional[GuidanceState] = None
        self._last_recommendation: Optional[GuidanceRecommendation] = None
        self._logger: Optional[GuidanceLogger] = None
        self._tick_thread = threading.Thread(target=self._tick_loop, daemon=True)
        self._tick_thread.start()

    def init_grid(self, bounds: dict, cell_size_m: float = cfg.DEFAULT_CELL_SIZE_M) -> dict:
        grid = create_grid(bounds, cell_size_m)
        with self._lock:
            self._state = GuidanceState(grid=grid)
            self._state.cell_states = init_cell_states(grid)
            self._last_recommendation = None
            self._logger = GuidanceLogger()
        return {"n_rows": grid.n_rows, "n_cols": grid.n_cols, "total_cells": len(grid.cells)}

    def reset(self) -> None:
        with self._lock:
            self._state = None
            self._last_recommendation = None
            self._logger = None

    def ingest(self, packet: dict) -> None:
        msg_type = packet.get("type") or packet.get("msg_type")
        with self._lock:
            if self._state is None:
                return
            if msg_type == "POSE":
                ingest_pose(self._state, packet)
            elif msg_type == "EVIDENCE":
                ingest_evidence(self._state, packet)
            elif msg_type == "HEALTH":
                ingest_health(self._state, packet)

    def get_recommendation(self) -> Optional[dict]:
        with self._lock:
            if self._state is None:
                return None
            rec = compute_recommendation(self._state)
            if rec is not None:
                self._last_recommendation = rec
                if self._logger:
                    self._logger.log(rec, self._state.drone)
            return asdict(rec) if rec else None

    def get_grid_state(self) -> Optional[dict]:
        with self._lock:
            if self._state is None or self._state.grid is None:
                return None
            return {
                "bounds": self._state.grid.bounds,
                "cell_size_m": self._state.grid.cell_size_m,
                "n_rows": self._state.grid.n_rows,
                "n_cols": self._state.grid.n_cols,
                "mode": self._state.mode,
                "cells": [
                    {
                        "cell_id": cs.cell_id,
                        "center_lat": cs.center_lat,
                        "center_lon": cs.center_lon,
                        "evidence_score": cs.evidence_score,
                        "uncertainty_score": cs.uncertainty_score,
                        "peak_score": cs.peak_score,
                        "coverage_score": cs.coverage_score,
                        "age_score": cs.age_score,
                        "final_score": cs.final_score,
                    }
                    for cs in self._state.cell_states.values()
                ],
            }

    def is_initialized(self) -> bool:
        with self._lock:
            return self._state is not None

    def _tick_loop(self) -> None:
        interval_ms = 3000.0
        while True:
            time.sleep(interval_ms / 1000.0)
            with self._lock:
                if self._state is not None:
                    tick_age(self._state, interval_ms)


_engine = GuidanceEngine()


def get_engine() -> GuidanceEngine:
    return _engine
