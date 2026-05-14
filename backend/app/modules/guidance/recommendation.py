from __future__ import annotations

import time
from typing import Optional

from . import config as cfg
from .grid import bearing_deg, haversine_m, latlon_to_cell_id
from .models import GuidanceRecommendation, GuidanceState, GridCellState
from .scoring import (
    compute_final_score,
    compute_oscillation_penalty,
    compute_peakness,
    compute_travel_cost,
)


def _now_ms() -> float:
    return time.time() * 1000.0


def _is_data_fresh(state: GuidanceState) -> bool:
    if state.drone.last_pose_ms is None:
        return False
    return (_now_ms() - state.drone.last_pose_ms) < 10_000


def _reason(mode: str, cs: GridCellState) -> str:
    if mode == "REFINE":
        return f"Strong local RF peak (E={cs.evidence_score:.2f}, P={cs.peak_score:.2f})"
    if cs.uncertainty_score > 0.7:
        return "High uncertainty + low coverage"
    if cs.coverage_score < 0.3:
        return "Unvisited area"
    return "Best unexplored region"


def _gps_cell_id(state: GuidanceState) -> Optional[int]:
    if not state.drone.gps_valid or state.grid is None:
        return None
    return latlon_to_cell_id(state.drone.lat, state.drone.lon, state.grid)


def _make_recommendation(
    state: GuidanceState,
    cell_id: int,
    now_ms: float,
    reason: str,
) -> GuidanceRecommendation:
    best = state.cell_states[cell_id]
    previous_recommendation_ms = state.last_recommendation_ms
    state.previous_target_id = cell_id
    state.last_recommendation_ms = now_ms

    dist = haversine_m(state.drone.lat, state.drone.lon, best.center_lat, best.center_lon)
    bear = bearing_deg(state.drone.lat, state.drone.lon, best.center_lat, best.center_lon)
    stale = (
        previous_recommendation_ms is not None
        and (now_ms - previous_recommendation_ms) > cfg.RECOMMENDATION_INTERVAL_SEC * 1000 * 3
    )

    return GuidanceRecommendation(
        timestamp_ms=now_ms,
        mode=state.mode,
        target_cell_id=cell_id,
        target_lat=best.center_lat,
        target_lon=best.center_lon,
        bearing_deg=bear,
        distance_m=dist,
        final_score=best.final_score,
        evidence_score=best.evidence_score,
        uncertainty_score=best.uncertainty_score,
        peak_score=best.peak_score,
        travel_cost=best.travel_cost,
        oscillation_penalty=best.oscillation_penalty,
        gps_valid=state.drone.gps_valid,
        data_fresh=_is_data_fresh(state),
        recommendation_stale=stale,
        reason=reason,
    )


def _check_mode_switch(state: GuidanceState, now_ms: float) -> None:
    if state.mode == "EXPLORE":
        for cs in state.cell_states.values():
            if cs.evidence_score > cfg.REFINE_E_THRESHOLD and cs.peak_score > cfg.REFINE_P_THRESHOLD:
                cs.refine_candidate_count += 1
                if cs.refine_candidate_count >= cfg.REFINE_PERSIST_WINDOWS:
                    state.mode = "REFINE"
                    state.refine_start_ms = now_ms
                    return
            else:
                cs.refine_candidate_count = 0
    else:
        if state.refine_start_ms is None:
            state.refine_start_ms = now_ms
        elapsed = (now_ms - state.refine_start_ms) / 1000.0
        if elapsed > cfg.REFINE_MAX_DURATION_SEC:
            state.mode = "EXPLORE"
            state.refine_start_ms = None
            return
        any_peak = any(
            cs.evidence_score > cfg.REFINE_E_THRESHOLD and cs.peak_score > cfg.REFINE_P_THRESHOLD
            for cs in state.cell_states.values()
        )
        if not any_peak:
            state.mode = "EXPLORE"
            state.refine_start_ms = None


def compute_recommendation(state: GuidanceState) -> Optional[GuidanceRecommendation]:
    if state.grid is None or not state.cell_states:
        return None

    now = _now_ms()
    current_cell_id = _gps_cell_id(state)
    if current_cell_id is None or not state.drone.sniffer_alive:
        return None

    for cell_id, cs in state.cell_states.items():
        cs.peak_score = compute_peakness(cell_id, state.cell_states, state.grid)

    _check_mode_switch(state, now)

    for cell_id, cs in state.cell_states.items():
        cs.travel_cost = compute_travel_cost(state.drone, cs)
        cs.oscillation_penalty = compute_oscillation_penalty(
            cell_id,
            state.previous_target_id,
            state.grid,
        )
        cs.final_score = compute_final_score(
            cs.evidence_score,
            cs.uncertainty_score,
            cs.peak_score,
            cs.travel_cost,
            cs.oscillation_penalty,
            state.mode,
        )

    evidence_cell_ids = [
        cell_id for cell_id, cs in state.cell_states.items() if cs.evidence_score > 0.0
    ]
    if not evidence_cell_ids:
        return _make_recommendation(state, current_cell_id, now, "Current Pi GPS cell")

    best_id = max(evidence_cell_ids, key=lambda cid: state.cell_states[cid].final_score)
    best = state.cell_states[best_id]
    return _make_recommendation(state, best_id, now, _reason(state.mode, best))
