from __future__ import annotations

import math
import time as _time
from typing import Optional

from . import config as cfg
from .grid import get_neighbors, haversine_m
from .models import DroneState, GridCellState, GuidanceGrid


def norm_rssi(rssi_dbm: float) -> float:
    v = (rssi_dbm - cfg.RSSI_MIN_DBM) / (cfg.RSSI_MAX_DBM - cfg.RSSI_MIN_DBM)
    return max(0.0, min(1.0, v))


def compute_f_rssi(rssi_p95: float, rssi_max: float) -> float:
    return cfg.E_RSSI_P95_WEIGHT * norm_rssi(rssi_p95) + cfg.E_RSSI_MAX_WEIGHT * norm_rssi(rssi_max)


def compute_f_count(n: int) -> float:
    return min(1.0, math.log1p(n) / math.log1p(cfg.E_N_REF))


def compute_f_strong(n_strong: int) -> float:
    return min(1.0, math.log1p(n_strong) / math.log1p(cfg.E_N_STRONG_REF))


def compute_evidence_raw(
    rssi_p95: Optional[float],
    rssi_max: Optional[float],
    frames_total: int,
    frames_strong: int,
) -> float:
    if rssi_p95 is None or rssi_max is None:
        return 0.0
    f_rssi = compute_f_rssi(rssi_p95, rssi_max)
    f_count = compute_f_count(frames_total)
    f_strong = compute_f_strong(frames_strong)
    return cfg.E_RSSI_WEIGHT * f_rssi + cfg.E_STRONG_WEIGHT * f_strong + cfg.E_COUNT_WEIGHT * f_count


def update_evidence_ema(current_e: float, raw_e: float) -> float:
    return (1 - cfg.E_SMOOTHING_BETA) * current_e + cfg.E_SMOOTHING_BETA * raw_e


def update_coverage(current_v: float, dwell_ms: float) -> float:
    return min(1.0, current_v + dwell_ms / cfg.T_COV_MS)


def update_age(current_a: float, delta_ms: float) -> float:
    return min(1.0, current_a + delta_ms / cfg.T_AGE_MS)


def compute_uncertainty(v: float, a: float) -> float:
    return 0.6 * (1.0 - v) + 0.4 * a


def compute_evidence_freshness(evidence_score: float, last_seen_ms: Optional[float]) -> float:
    if last_seen_ms is None:
        return 0.0
    age_ms = _time.time() * 1000.0 - last_seen_ms
    return evidence_score * math.exp(-age_ms / cfg.TAU_EVIDENCE_DECAY_MS)


def compute_spatial_entropy(
    cell_id: int,
    cell_states: dict[int, GridCellState],
    grid: GuidanceGrid,
) -> tuple[float, float]:
    now_ms = _time.time() * 1000.0
    neighborhood = [cell_id] + get_neighbors(cell_id, grid)
    masses: list[float] = []
    raw_total = 0.0

    for nid in neighborhood:
        cs = cell_states.get(nid)
        if cs is None:
            masses.append(cfg.ENTROPY_EPSILON)
            continue
        age_ms = (now_ms - cs.last_seen_ms) if cs.last_seen_ms is not None else 1e9
        mass = cs.evidence_score * math.exp(-age_ms / cfg.TAU_EVIDENCE_DECAY_MS)
        raw_total += mass
        masses.append(max(mass, cfg.ENTROPY_EPSILON))

    if raw_total < cfg.ENTROPY_MIN_MASS:
        return 1.0, 0.0

    total = sum(masses)
    n = len(masses)
    entropy = -sum((m / total) * math.log(m / total) for m in masses)
    h = max(0.0, min(1.0, entropy / math.log(n)))
    return h, 1.0 - h


def compute_freshness_score(last_seen_ms: Optional[float], now_ms: float) -> float:
    if last_seen_ms is None:
        return 0.0
    age_ms = max(0.0, now_ms - last_seen_ms)
    return max(0.0, min(1.0, 1.0 - age_ms / cfg.EVIDENCE_FRESH_MS))


def compute_entropy_score(frames_strong: int, frames_total: int) -> float:
    if frames_total <= 0 or frames_strong <= 0 or frames_strong >= frames_total:
        return 0.0
    p = frames_strong / frames_total
    entropy = -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))
    return max(0.0, min(1.0, entropy))


def compute_peakness(
    cell_id: int,
    cell_states: dict[int, GridCellState],
    grid: GuidanceGrid,
) -> float:
    cs = cell_states.get(cell_id)
    if cs is None:
        return 0.0
    neighbors = get_neighbors(cell_id, grid)
    neighbor_evidences = [cell_states[n].evidence_score for n in neighbors if n in cell_states]
    if not neighbor_evidences:
        return 0.0
    mean_neighbor = sum(neighbor_evidences) / len(neighbor_evidences)
    return max(0.0, cs.evidence_score - mean_neighbor)


def compute_travel_cost(drone: DroneState, cell: GridCellState) -> float:
    if not drone.gps_valid or drone.lat == 0.0:
        return 0.5
    dist = haversine_m(drone.lat, drone.lon, cell.center_lat, cell.center_lon)
    return min(1.0, dist / cfg.D_MAX_M)


def compute_oscillation_penalty(
    cell_id: int,
    previous_target_id: Optional[int],
    grid: GuidanceGrid,
) -> float:
    if previous_target_id is None:
        return 0.0
    if cell_id == previous_target_id:
        return 0.0
    neighbors_of_prev = get_neighbors(previous_target_id, grid)
    far_jump = 0.0 if cell_id in neighbors_of_prev else 1.0
    return cfg.R_CHANGE_WEIGHT * 1.0 + cfg.R_FAR_JUMP_WEIGHT * far_jump


def compute_final_score(e: float, u: float, p: float, d: float, r: float, mode: str) -> float:
    if mode == "EXPLORE":
        return (
            cfg.W_E_EXPLORE * e
            + cfg.W_U_EXPLORE * u
            + cfg.W_P_EXPLORE * p
            - cfg.W_D_EXPLORE * d
            - cfg.W_R_EXPLORE * r
        )
    if mode == "REFINE":
        return (
            cfg.W_E_REFINE * e
            + cfg.W_U_REFINE * u
            + cfg.W_P_REFINE * p
            - cfg.W_D_REFINE * d
            - cfg.W_R_REFINE * r
        )
    return cfg.W_E * e + cfg.W_U * u + cfg.W_P * p - cfg.W_D * d - cfg.W_R * r
