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
            tick_age(self._state, 0.0)
            max_frames = max((cs.total_frames for cs in self._state.cell_states.values()), default=0)
            max_evidence = max((cs.evidence_score for cs in self._state.cell_states.values()), default=0.0)
            lat_step = (
                self._state.grid.bounds["max_lat"] - self._state.grid.bounds["min_lat"]
            ) / self._state.grid.n_rows
            lon_step = (
                self._state.grid.bounds["max_lon"] - self._state.grid.bounds["min_lon"]
            ) / self._state.grid.n_cols
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
                        "row": self._state.grid.cells[cs.cell_id].row,
                        "col": self._state.grid.cells[cs.cell_id].col,
                        "min_lat": cs.center_lat - lat_step / 2,
                        "max_lat": cs.center_lat + lat_step / 2,
                        "min_lon": cs.center_lon - lon_step / 2,
                        "max_lon": cs.center_lon + lon_step / 2,
                        "evidence_score": cs.evidence_score,
                        "uncertainty_score": cs.uncertainty_score,
                        "peak_score": cs.peak_score,
                        "spatial_entropy": cs.spatial_entropy,
                        "spatial_certainty": cs.spatial_certainty,
                        "evidence_freshness": cs.evidence_freshness,
                        "evidence_freshness_score": cs.evidence_freshness_score,
                        "entropy_score": cs.entropy_score,
                        "coverage_score": cs.coverage_score,
                        "age_score": cs.age_score,
                        "final_score": cs.final_score,
                        "display_score": cs.display_score,
                        "rssi_max": cs.rssi_max,
                        "rssi_p95": cs.rssi_p95,
                        "rssi_mean": cs.rssi_mean,
                        "total_frames": cs.total_frames,
                        "total_strong_frames": cs.total_strong_frames,
                        "total_dwell_ms": cs.total_dwell_ms,
                        "last_seen_ms": cs.last_seen_ms,
                    }
                    for cs in self._state.cell_states.values()
                ],
            }

    @staticmethod
    def _display_score(cs, max_frames: int, max_evidence: float) -> float:
        if cs.total_frames <= 0:
            return 0.0
        frame_ratio = cs.total_frames / max_frames if max_frames > 0 else 0.0
        evidence_ratio = cs.evidence_score / max_evidence if max_evidence > 0 else 0.0
        packet_presence = min(1.0, cs.total_frames / 10.0)
        return round(0.5 * packet_presence + 0.3 * frame_ratio + 0.2 * evidence_ratio, 4)

    def get_debug_state(self) -> dict:
        with self._lock:
            if self._state is None:
                return {"initialized": False}

            diag = self._state.evidence_diagnostics
            max_cell = None
            if self._state.cell_states:
                best = max(self._state.cell_states.values(), key=lambda cs: cs.evidence_score)
                max_cell = {
                    "cell_id": best.cell_id,
                    "evidence_score": best.evidence_score,
                    "center_lat": best.center_lat,
                    "center_lon": best.center_lon,
                    "last_seen_ms": best.last_seen_ms,
                }

            return {
                "initialized": self._state.grid is not None,
                "last_pose_ms": self._state.drone.last_pose_ms,
                "gps_valid": self._state.drone.gps_valid,
                "sniffer_alive": self._state.drone.sniffer_alive,
                "last_evidence_ms": diag.last_evidence_ms,
                "last_evidence_drop_reason": diag.last_evidence_drop_reason,
                "last_evidence_packet": diag.last_evidence_packet,
                "evidence_packets_ingested": diag.evidence_packets_ingested,
                "evidence_packets_dropped": diag.evidence_packets_dropped,
                "max_evidence_cell": max_cell,
            }

    def is_initialized(self) -> bool:
        with self._lock:
            return self._state is not None

    def get_status(self) -> dict:
        with self._lock:
            if self._state is None:
                return {"initialized": False}
            return {
                "initialized": True,
                "mode": self._state.mode,
                "n_cells": len(self._state.cell_states),
                "drone_gps_valid": self._state.drone.gps_valid,
                "evidence_packets_ingested": (
                    self._state.evidence_diagnostics.evidence_packets_ingested
                ),
                "evidence_packets_dropped": (
                    self._state.evidence_diagnostics.evidence_packets_dropped
                ),
                "last_evidence_drop_reason": (
                    self._state.evidence_diagnostics.last_evidence_drop_reason
                ),
            }

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
