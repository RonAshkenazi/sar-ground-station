from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GridCell:
    cell_id: int
    center_lat: float
    center_lon: float
    row: int
    col: int


@dataclass
class GridCellState:
    cell_id: int
    center_lat: float
    center_lon: float

    evidence_score: float = 0.0
    coverage_score: float = 0.0
    age_score: float = 0.0
    uncertainty_score: float = 0.0
    peak_score: float = 0.0
    travel_cost: float = 0.0
    oscillation_penalty: float = 0.0
    final_score: float = 0.0

    rssi_max: Optional[float] = None
    rssi_p95: Optional[float] = None
    rssi_mean: Optional[float] = None
    total_frames: int = 0
    total_strong_frames: int = 0
    total_dwell_ms: float = 0.0

    last_updated_ms: Optional[float] = None
    last_seen_ms: Optional[float] = None

    refine_candidate_count: int = 0


@dataclass
class DroneState:
    lat: float = 0.0
    lon: float = 0.0
    gps_valid: bool = False
    sniffer_alive: bool = False
    last_pose_ms: Optional[float] = None
    heading_deg: Optional[float] = None
    speed_mps: Optional[float] = None


@dataclass
class HealthState:
    cpu_pct: Optional[float] = None
    temp_c: Optional[float] = None
    gps_valid: bool = False
    sniffer_alive: bool = False
    uplink_queue_len: int = 0
    dropped_msgs: int = 0
    last_health_ms: Optional[float] = None


@dataclass
class GuidanceGrid:
    bounds: dict
    cell_size_m: float
    n_rows: int
    n_cols: int
    cells: dict[int, GridCell] = field(default_factory=dict)


@dataclass
class GuidanceState:
    grid: Optional[GuidanceGrid] = None
    cell_states: dict[int, GridCellState] = field(default_factory=dict)
    drone: DroneState = field(default_factory=DroneState)
    health: HealthState = field(default_factory=HealthState)
    mode: str = "EXPLORE"
    previous_target_id: Optional[int] = None
    refine_start_ms: Optional[float] = None
    last_recommendation_ms: Optional[float] = None


@dataclass
class GuidanceRecommendation:
    timestamp_ms: float
    mode: str
    target_cell_id: int
    target_lat: float
    target_lon: float
    bearing_deg: float
    distance_m: float
    final_score: float
    evidence_score: float
    uncertainty_score: float
    peak_score: float
    travel_cost: float
    oscillation_penalty: float
    gps_valid: bool
    data_fresh: bool
    recommendation_stale: bool
    reason: str
