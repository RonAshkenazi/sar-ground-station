from __future__ import annotations

import time

from .grid import latlon_to_cell_id
from .models import GridCellState, GuidanceGrid, GuidanceState
from .scoring import (
    compute_evidence_raw,
    compute_uncertainty,
    update_age,
    update_coverage,
    update_evidence_ema,
)


EVIDENCE_PACKET_SUMMARY_KEYS = (
    "type",
    "msg_type",
    "lat",
    "lon",
    "dwell_ms",
    "win_ms",
    "frames_total",
    "frames_strong",
    "rssi_max_dbm",
    "rssi_p95_dbm",
    "rssi_mean_dbm",
)


def _now_ms() -> float:
    return time.time() * 1000.0


def _packet_summary(packet: dict, cell_id: int | None = None) -> dict:
    summary = {key: packet.get(key) for key in EVIDENCE_PACKET_SUMMARY_KEYS if key in packet}
    if cell_id is not None:
        summary["cell_id"] = cell_id
    return summary


def _drop_evidence(state: GuidanceState, packet: dict, reason: str, cell_id: int | None = None) -> None:
    diag = state.evidence_diagnostics
    diag.evidence_packets_dropped += 1
    diag.last_evidence_drop_reason = reason
    diag.last_evidence_packet = _packet_summary(packet, cell_id)


def init_cell_states(grid: GuidanceGrid) -> dict[int, GridCellState]:
    return {
        cell_id: GridCellState(
            cell_id=cell_id,
            center_lat=cell.center_lat,
            center_lon=cell.center_lon,
        )
        for cell_id, cell in grid.cells.items()
    }


def ingest_pose(state: GuidanceState, packet: dict) -> None:
    if state.grid is None:
        return
    lat = packet.get("lat")
    lon = packet.get("lon")
    if lat is None or lon is None:
        return
    now = _now_ms()
    previous_pose_ms = state.drone.last_pose_ms
    state.drone.lat = float(lat)
    state.drone.lon = float(lon)
    state.drone.gps_valid = bool(packet.get("gps_valid", False))
    if "sniffer_alive" in packet:
        state.drone.sniffer_alive = bool(packet["sniffer_alive"])
    state.drone.last_pose_ms = now
    state.drone.heading_deg = packet.get("heading_deg")
    state.drone.speed_mps = packet.get("speed_mps")

    if not state.drone.gps_valid:
        return

    cell_id = latlon_to_cell_id(state.drone.lat, state.drone.lon, state.grid)
    if cell_id is None:
        return
    cs = state.cell_states.get(cell_id)
    if cs is None:
        return

    dwell_ms = 0.0
    if previous_pose_ms is not None:
        dwell_ms = max(0.0, min(now - previous_pose_ms, 2000.0))
    cs.coverage_score = update_coverage(cs.coverage_score, dwell_ms)
    cs.age_score = 0.0
    cs.uncertainty_score = compute_uncertainty(cs.coverage_score, cs.age_score)
    cs.total_dwell_ms += dwell_ms
    cs.last_updated_ms = now


def ingest_evidence(state: GuidanceState, packet: dict) -> None:
    if state.grid is None:
        _drop_evidence(state, packet, "grid_not_initialized")
        return
    lat = packet.get("lat")
    lon = packet.get("lon")
    if lat is None or lon is None:
        _drop_evidence(state, packet, "missing_lat_lon")
        return

    try:
        cell_id = latlon_to_cell_id(float(lat), float(lon), state.grid)
    except (TypeError, ValueError):
        _drop_evidence(state, packet, "invalid_lat_lon")
        return
    if cell_id is None:
        _drop_evidence(state, packet, "outside_grid")
        return

    cs = state.cell_states.get(cell_id)
    if cs is None:
        _drop_evidence(state, packet, "missing_cell_state", cell_id)
        return

    try:
        dwell_ms = float(packet.get("dwell_ms", packet.get("win_ms", 0)) or 0)
        frames_total = int(packet.get("frames_total", 0) or 0)
        frames_strong = int(packet.get("frames_strong", 0) or 0)
        rssi_max = packet.get("rssi_max_dbm")
        rssi_p95 = packet.get("rssi_p95_dbm")
        rssi_mean = packet.get("rssi_mean_dbm")
        rssi_max_value = float(rssi_max) if rssi_max is not None else None
        rssi_p95_value = float(rssi_p95) if rssi_p95 is not None else None
        rssi_mean_value = float(rssi_mean) if rssi_mean is not None else None
    except (TypeError, ValueError):
        _drop_evidence(state, packet, "invalid_evidence_values", cell_id)
        return

    now = _now_ms()
    cs.total_frames += frames_total
    cs.total_strong_frames += frames_strong
    cs.total_dwell_ms += dwell_ms
    if rssi_max_value is not None:
        cs.rssi_max = max(cs.rssi_max or -999, rssi_max_value)
    if rssi_p95_value is not None:
        cs.rssi_p95 = rssi_p95_value
    if rssi_mean_value is not None:
        cs.rssi_mean = rssi_mean_value

    raw_e = compute_evidence_raw(cs.rssi_p95, cs.rssi_max, frames_total, frames_strong)
    cs.evidence_score = update_evidence_ema(cs.evidence_score, raw_e)
    cs.coverage_score = update_coverage(cs.coverage_score, dwell_ms)
    cs.age_score = 0.0
    cs.uncertainty_score = compute_uncertainty(cs.coverage_score, cs.age_score)
    cs.last_updated_ms = now
    cs.last_seen_ms = now

    diag = state.evidence_diagnostics
    diag.evidence_packets_ingested += 1
    diag.last_evidence_ms = now
    diag.last_evidence_drop_reason = None
    diag.last_evidence_packet = _packet_summary(packet, cell_id)


def ingest_health(state: GuidanceState, packet: dict) -> None:
    h = state.health
    h.cpu_pct = packet.get("cpu_pct")
    h.temp_c = packet.get("temp_c")
    h.gps_valid = bool(packet.get("gps_valid", False))
    h.sniffer_alive = bool(packet.get("sniffer_alive", False))
    h.uplink_queue_len = int(packet.get("uplink_queue_len", 0) or 0)
    h.dropped_msgs = int(packet.get("dropped_msgs", 0) or 0)
    h.last_health_ms = _now_ms()


def tick_age(state: GuidanceState, delta_ms: float) -> None:
    now = _now_ms()
    for cs in state.cell_states.values():
        if cs.last_updated_ms is None or (now - cs.last_updated_ms) > 2000:
            cs.age_score = update_age(cs.age_score, delta_ms)
        cs.uncertainty_score = compute_uncertainty(cs.coverage_score, cs.age_score)
