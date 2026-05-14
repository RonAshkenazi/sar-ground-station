# Codex Handoff — Ground Station: Air Unit Page + Smart Flight Guidance

## Requested Role

[SUPERVISOR → spawn 2 parallel workers, then integrate]

---

## Instructions for Codex Supervisor

Spawn Worker A and Worker B in parallel. Both are independent.

After both complete, do the Supervisor integration step (update `main.py`, run tests + build).

---

## Context

We are adding a Live Mission page (`/airunit`) to the Ground Station.

**Connection model:**
- The Raspberry Pi is the WebSocket **client**. It connects TO the GS backend: `ws://GS_IP:8000/api/airunit/ws`
- The GS frontend is also a WebSocket client, connecting to the GS backend relay: `ws://GS_IP:8000/api/airunit/frontend-ws`
- The GS backend sits in the middle: it receives Pi messages and relays them to all connected frontend clients, and routes guidance packets (POSE, EVIDENCE, HEALTH) to the guidance engine.
- Scan files live on the Pi. The GS backend proxies file listing and download via the Pi's HTTP server.

**Pi message types** (arrive on `/api/airunit/ws`):

| `type` | Direction | Meaning |
|---|---|---|
| `hello` | Pi→GS | Registers Pi IP + port |
| `log` | Pi→GS | Scan log line (`{line, count}`) |
| `status` | Pi→GS | Scan status string |
| `ble_log` | Pi→GS | BLE scan log line |
| `ble_status` | Pi→GS | BLE scan status |
| `POSE` | Pi→GS | PosePacket — GPS + sniffer health |
| `EVIDENCE` | Pi→GS | EvidencePacket — RSSI window summary |
| `HEALTH` | Pi→GS | HealthPacket — CPU, temp, system health |
| `pi_disconnected` | GS→frontend | Synthesized by GS when Pi WS closes |

**Command messages** (GS→Pi via the Pi WS):

```json
{ "type": "cmd", "cmd": "scan_start" }
{ "type": "cmd", "cmd": "scan_stop" }
{ "type": "cmd", "cmd": "ble_scan_start" }
{ "type": "cmd", "cmd": "ble_scan_stop" }
```

---

---

# WORKER A — Backend

## Files to create

```
backend/app/modules/guidance/__init__.py        (empty)
backend/app/modules/guidance/config.py
backend/app/modules/guidance/models.py
backend/app/modules/guidance/grid.py
backend/app/modules/guidance/scoring.py
backend/app/modules/guidance/state.py
backend/app/modules/guidance/recommendation.py
backend/app/modules/guidance/engine.py
backend/app/modules/guidance/logger.py
backend/app/api/guidance.py
backend/app/api/airunit.py
```

## Files to modify

```
backend/tests/unit/test_skeleton.py    (add guidance unit tests)
```

## Must NOT touch

- Any frontend file
- `backend/app/main.py` (Supervisor handles this)
- Any other existing backend file

---

## Task A1 — `backend/app/modules/guidance/config.py`

All algorithm parameters with defaults from spec:

```python
# RSSI normalization bounds
RSSI_MIN_DBM: float = -90.0
RSSI_MAX_DBM: float = -55.0

# Evidence score weights
E_RSSI_WEIGHT: float = 0.5
E_STRONG_WEIGHT: float = 0.3
E_COUNT_WEIGHT: float = 0.2
E_RSSI_P95_WEIGHT: float = 0.6     # within f_rssi
E_RSSI_MAX_WEIGHT: float = 0.4     # within f_rssi
E_N_REF: int = 30                  # reference frame count
E_N_STRONG_REF: int = 10           # reference strong frame count
E_SMOOTHING_BETA: float = 0.3      # EMA beta for evidence

# Coverage
T_COV_MS: float = 5000.0           # ms of dwell to reach V_i = 1

# Age / staleness
T_AGE_MS: float = 30_000.0         # ms until A_i reaches 1

# Travel cost
D_MAX_M: float = 500.0             # normalisation distance

# Oscillation penalty weights
R_CHANGE_WEIGHT: float = 0.5
R_FAR_JUMP_WEIGHT: float = 0.5

# Final score weights — MVP
W_E: float = 0.35
W_U: float = 0.30
W_P: float = 0.20
W_D: float = 0.15
W_R: float = 0.05

# EXPLORE mode weights
W_E_EXPLORE: float = 0.20
W_U_EXPLORE: float = 0.50
W_P_EXPLORE: float = 0.10
W_D_EXPLORE: float = 0.15
W_R_EXPLORE: float = 0.05

# REFINE mode weights
W_E_REFINE: float = 0.45
W_U_REFINE: float = 0.15
W_P_REFINE: float = 0.30
W_D_REFINE: float = 0.07
W_R_REFINE: float = 0.03

# Mode switching thresholds
REFINE_E_THRESHOLD: float = 0.65
REFINE_P_THRESHOLD: float = 0.20
REFINE_PERSIST_WINDOWS: int = 3
REFINE_MAX_DURATION_SEC: float = 30.0

# Default grid cell size
DEFAULT_CELL_SIZE_M: float = 30.0

# Recommendation interval
RECOMMENDATION_INTERVAL_SEC: float = 3.0

# Guidance history log path (relative to TEMP dir)
GUIDANCE_HISTORY_SUBPATH: str = "guidance/guidance_history.csv"
```

---

## Task A2 — `backend/app/modules/guidance/models.py`

```python
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

    # Component scores
    evidence_score: float = 0.0    # E_i
    coverage_score: float = 0.0    # V_i
    age_score: float = 0.0         # A_i
    uncertainty_score: float = 0.0 # U_i
    peak_score: float = 0.0        # P_i
    travel_cost: float = 0.0       # D_i
    oscillation_penalty: float = 0.0  # R_i
    final_score: float = 0.0       # J_i

    # Raw evidence stats
    rssi_max: Optional[float] = None
    rssi_p95: Optional[float] = None
    rssi_mean: Optional[float] = None
    total_frames: int = 0
    total_strong_frames: int = 0
    total_dwell_ms: float = 0.0

    # Timing
    last_updated_ms: Optional[float] = None
    last_seen_ms: Optional[float] = None

    # Mode switching state
    refine_candidate_count: int = 0  # consecutive windows qualifying for REFINE


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
    bounds: dict                    # {min_lat, max_lat, min_lon, max_lon}
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
    mode: str = "EXPLORE"           # "EXPLORE" | "REFINE"
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
```

---

## Task A3 — `backend/app/modules/guidance/grid.py`

```python
import math
from .models import GuidanceGrid, GridCell

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres."""
    R = 6_371_000.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing from point 1 to point 2, in degrees [0, 360)."""
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dλ = math.radians(lon2 - lon1)
    x = math.sin(dλ) * math.cos(φ2)
    y = math.cos(φ1) * math.sin(φ2) - math.sin(φ1) * math.cos(φ2) * math.cos(dλ)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def create_grid(bounds: dict, cell_size_m: float) -> GuidanceGrid:
    """
    Build a grid of cells covering the bounding box.
    bounds keys: min_lat, max_lat, min_lon, max_lon
    Returns a GuidanceGrid with cells indexed by cell_id = row * n_cols + col.
    """
    min_lat = bounds["min_lat"]
    max_lat = bounds["max_lat"]
    min_lon = bounds["min_lon"]
    max_lon = bounds["max_lon"]

    height_m = haversine_m(min_lat, min_lon, max_lat, min_lon)
    width_m = haversine_m(min_lat, min_lon, min_lat, max_lon)

    n_rows = max(1, math.ceil(height_m / cell_size_m))
    n_cols = max(1, math.ceil(width_m / cell_size_m))

    lat_step = (max_lat - min_lat) / n_rows
    lon_step = (max_lon - min_lon) / n_cols

    cells: dict[int, GridCell] = {}
    for row in range(n_rows):
        for col in range(n_cols):
            cell_id = row * n_cols + col
            center_lat = min_lat + (row + 0.5) * lat_step
            center_lon = min_lon + (col + 0.5) * lon_step
            cells[cell_id] = GridCell(
                cell_id=cell_id,
                center_lat=center_lat,
                center_lon=center_lon,
                row=row,
                col=col,
            )

    return GuidanceGrid(
        bounds=bounds,
        cell_size_m=cell_size_m,
        n_rows=n_rows,
        n_cols=n_cols,
        cells=cells,
    )


def latlon_to_cell_id(lat: float, lon: float, grid: GuidanceGrid) -> int | None:
    """Map a lat/lon to the cell_id that contains it. Returns None if outside grid."""
    b = grid.bounds
    if not (b["min_lat"] <= lat <= b["max_lat"] and b["min_lon"] <= lon <= b["max_lon"]):
        return None
    lat_step = (b["max_lat"] - b["min_lat"]) / grid.n_rows
    lon_step = (b["max_lon"] - b["min_lon"]) / grid.n_cols
    row = min(int((lat - b["min_lat"]) / lat_step), grid.n_rows - 1)
    col = min(int((lon - b["min_lon"]) / lon_step), grid.n_cols - 1)
    return row * grid.n_cols + col


def get_neighbors(cell_id: int, grid: GuidanceGrid) -> list[int]:
    """Return 8-connected neighbour cell_ids that exist in the grid."""
    n_rows, n_cols = grid.n_rows, grid.n_cols
    row, col = divmod(cell_id, n_cols)
    neighbors = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            r2, c2 = row + dr, col + dc
            if 0 <= r2 < n_rows and 0 <= c2 < n_cols:
                neighbors.append(r2 * n_cols + c2)
    return neighbors
```

---

## Task A4 — `backend/app/modules/guidance/scoring.py`

Implement all component score functions exactly as specified.

```python
import math
from typing import Optional
from . import config as cfg
from .models import GridCellState, GuidanceGrid, DroneState
from .grid import haversine_m, get_neighbors


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
    """Exponential moving average: E_i ← (1−β)·E_i + β·E_raw"""
    return (1 - cfg.E_SMOOTHING_BETA) * current_e + cfg.E_SMOOTHING_BETA * raw_e


def update_coverage(current_v: float, dwell_ms: float) -> float:
    return min(1.0, current_v + dwell_ms / cfg.T_COV_MS)


def update_age(current_a: float, delta_ms: float) -> float:
    return min(1.0, current_a + delta_ms / cfg.T_AGE_MS)


def compute_uncertainty(v: float, a: float) -> float:
    return 0.6 * (1.0 - v) + 0.4 * a


def compute_peakness(
    cell_id: int,
    cell_states: dict[int, GridCellState],
    grid: GuidanceGrid,
) -> float:
    """P_i = max(0, E_i - mean(E_j for j in 8-neighbors))"""
    cs = cell_states.get(cell_id)
    if cs is None:
        return 0.0
    neighbors = get_neighbors(cell_id, grid)
    neighbor_evidences = [
        cell_states[n].evidence_score for n in neighbors if n in cell_states
    ]
    if not neighbor_evidences:
        return 0.0
    mean_neighbor = sum(neighbor_evidences) / len(neighbor_evidences)
    return max(0.0, cs.evidence_score - mean_neighbor)


def compute_travel_cost(
    drone: DroneState,
    cell: GridCellState,
) -> float:
    if not drone.gps_valid or drone.lat == 0.0:
        return 0.5  # unknown — neutral
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


def compute_final_score(
    e: float, u: float, p: float, d: float, r: float, mode: str
) -> float:
    if mode == "EXPLORE":
        return (
            cfg.W_E_EXPLORE * e + cfg.W_U_EXPLORE * u + cfg.W_P_EXPLORE * p
            - cfg.W_D_EXPLORE * d - cfg.W_R_EXPLORE * r
        )
    if mode == "REFINE":
        return (
            cfg.W_E_REFINE * e + cfg.W_U_REFINE * u + cfg.W_P_REFINE * p
            - cfg.W_D_REFINE * d - cfg.W_R_REFINE * r
        )
    # MVP default
    return cfg.W_E * e + cfg.W_U * u + cfg.W_P * p - cfg.W_D * d - cfg.W_R * r
```

---

## Task A5 — `backend/app/modules/guidance/state.py`

```python
import time
from typing import Optional
from .models import GuidanceState, GridCellState, GuidanceGrid, DroneState, HealthState
from .grid import latlon_to_cell_id
from .scoring import (
    compute_evidence_raw, update_evidence_ema, update_coverage,
    update_age, compute_uncertainty,
)
from . import config as cfg


def _now_ms() -> float:
    return time.time() * 1000.0


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
    """Update drone position from a POSE packet."""
    if state.grid is None:
        return
    lat = packet.get("lat")
    lon = packet.get("lon")
    if lat is None or lon is None:
        return
    state.drone.lat = lat
    state.drone.lon = lon
    state.drone.gps_valid = bool(packet.get("gps_valid", False))
    state.drone.sniffer_alive = bool(packet.get("sniffer_alive", False))
    state.drone.last_pose_ms = _now_ms()
    state.drone.heading_deg = packet.get("heading_deg")
    state.drone.speed_mps = packet.get("speed_mps")


def ingest_evidence(state: GuidanceState, packet: dict) -> None:
    """Update cell evidence from an EVIDENCE packet. Packet contains lat/lon, not cell_id."""
    if state.grid is None:
        return
    lat = packet.get("lat")
    lon = packet.get("lon")
    if lat is None or lon is None:
        return

    cell_id = latlon_to_cell_id(lat, lon, state.grid)
    if cell_id is None:
        return  # outside grid

    cs = state.cell_states.get(cell_id)
    if cs is None:
        return

    now = _now_ms()
    dwell_ms = float(packet.get("dwell_ms", 0) or 0)
    frames_total = int(packet.get("frames_total", 0) or 0)
    frames_strong = int(packet.get("frames_strong", 0) or 0)
    rssi_max = packet.get("rssi_max_dbm")
    rssi_p95 = packet.get("rssi_p95_dbm")
    rssi_mean = packet.get("rssi_mean_dbm")

    # Update raw stats (running max/totals)
    cs.total_frames += frames_total
    cs.total_strong_frames += frames_strong
    cs.total_dwell_ms += dwell_ms
    if rssi_max is not None:
        cs.rssi_max = max(cs.rssi_max or -999, rssi_max)
    if rssi_p95 is not None:
        cs.rssi_p95 = rssi_p95
    if rssi_mean is not None:
        cs.rssi_mean = rssi_mean

    # Update evidence score (EMA)
    raw_e = compute_evidence_raw(cs.rssi_p95, cs.rssi_max, frames_total, frames_strong)
    cs.evidence_score = update_evidence_ema(cs.evidence_score, raw_e)

    # Update coverage
    cs.coverage_score = update_coverage(cs.coverage_score, dwell_ms)

    # Reset age
    cs.age_score = 0.0
    cs.last_updated_ms = now
    cs.last_seen_ms = now


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
    """Called periodically. Increments A_i for all cells not updated this tick."""
    now = _now_ms()
    for cs in state.cell_states.values():
        if cs.last_updated_ms is None or (now - cs.last_updated_ms) > 2000:
            cs.age_score = update_age(cs.age_score, delta_ms)
        cs.uncertainty_score = compute_uncertainty(cs.coverage_score, cs.age_score)
```

---

## Task A6 — `backend/app/modules/guidance/recommendation.py`

```python
import time
from typing import Optional
from .models import GuidanceState, GuidanceRecommendation, GridCellState
from .grid import haversine_m, bearing_deg, get_neighbors
from .scoring import (
    compute_peakness, compute_travel_cost,
    compute_oscillation_penalty, compute_final_score,
)
from . import config as cfg


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


def _check_mode_switch(state: GuidanceState, now_ms: float) -> None:
    """Update EXPLORE/REFINE mode based on current cell states."""
    if state.mode == "EXPLORE":
        # Check if any cell qualifies for REFINE
        for cs in state.cell_states.values():
            if cs.evidence_score > cfg.REFINE_E_THRESHOLD and cs.peak_score > cfg.REFINE_P_THRESHOLD:
                cs.refine_candidate_count += 1
                if cs.refine_candidate_count >= cfg.REFINE_PERSIST_WINDOWS:
                    state.mode = "REFINE"
                    state.refine_start_ms = now_ms
                    return
            else:
                cs.refine_candidate_count = 0
    else:  # REFINE
        if state.refine_start_ms is None:
            state.refine_start_ms = now_ms
        elapsed = (now_ms - state.refine_start_ms) / 1000.0
        if elapsed > cfg.REFINE_MAX_DURATION_SEC:
            state.mode = "EXPLORE"
            state.refine_start_ms = None
            return
        # Exit if no cell still qualifies
        any_peak = any(
            cs.evidence_score > cfg.REFINE_E_THRESHOLD and cs.peak_score > cfg.REFINE_P_THRESHOLD
            for cs in state.cell_states.values()
        )
        if not any_peak:
            state.mode = "EXPLORE"
            state.refine_start_ms = None


def compute_recommendation(state: GuidanceState) -> Optional[GuidanceRecommendation]:
    """Score all cells and return the best target. Returns None if grid not initialized."""
    if state.grid is None or not state.cell_states:
        return None

    now = _now_ms()
    _check_mode_switch(state, now)

    # Compute per-cell scores
    for cell_id, cs in state.cell_states.items():
        cs.peak_score = compute_peakness(cell_id, state.cell_states, state.grid)
        cs.travel_cost = compute_travel_cost(state.drone, cs)
        cs.oscillation_penalty = compute_oscillation_penalty(
            cell_id, state.previous_target_id, state.grid
        )
        cs.final_score = compute_final_score(
            cs.evidence_score, cs.uncertainty_score, cs.peak_score,
            cs.travel_cost, cs.oscillation_penalty, state.mode,
        )

    best_id = max(state.cell_states, key=lambda cid: state.cell_states[cid].final_score)
    best = state.cell_states[best_id]
    state.previous_target_id = best_id
    state.last_recommendation_ms = now

    dist = haversine_m(state.drone.lat, state.drone.lon, best.center_lat, best.center_lon)
    bear = bearing_deg(state.drone.lat, state.drone.lon, best.center_lat, best.center_lon)
    data_fresh = _is_data_fresh(state)
    stale = (now - state.last_recommendation_ms) > cfg.RECOMMENDATION_INTERVAL_SEC * 1000 * 3

    return GuidanceRecommendation(
        timestamp_ms=now,
        mode=state.mode,
        target_cell_id=best_id,
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
        data_fresh=data_fresh,
        recommendation_stale=stale,
        reason=_reason(state.mode, best),
    )
```

---

## Task A7 — `backend/app/modules/guidance/engine.py`

Thread-safe singleton engine. Uses a `threading.Lock` because the Pi WS handler
(FastAPI async context) and the recommendation endpoint both access state.

```python
import threading
import time
from typing import Optional
from dataclasses import asdict

from .models import GuidanceState, GuidanceGrid, GuidanceRecommendation
from .grid import create_grid
from .state import init_cell_states, ingest_pose, ingest_evidence, ingest_health, tick_age
from .recommendation import compute_recommendation
from .logger import GuidanceLogger
from . import config as cfg


class GuidanceEngine:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: Optional[GuidanceState] = None
        self._last_recommendation: Optional[GuidanceRecommendation] = None
        self._logger: Optional[GuidanceLogger] = None
        self._tick_thread = threading.Thread(target=self._tick_loop, daemon=True)
        self._tick_thread.start()

    # ── Public API ────────────────────────────────────────────────────────────

    def init_grid(self, bounds: dict, cell_size_m: float = cfg.DEFAULT_CELL_SIZE_M) -> dict:
        """Initialize a fresh guidance session with a new grid."""
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

    def ingest(self, packet: dict) -> None:
        """Route an incoming Pi packet to the appropriate state update."""
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
            if self._state is None:
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

    # ── Background age tick ───────────────────────────────────────────────────

    def _tick_loop(self) -> None:
        interval_ms = 3000.0
        while True:
            time.sleep(interval_ms / 1000.0)
            with self._lock:
                if self._state is not None:
                    tick_age(self._state, interval_ms)


# Module-level singleton
_engine = GuidanceEngine()


def get_engine() -> GuidanceEngine:
    return _engine
```

---

## Task A8 — `backend/app/modules/guidance/logger.py`

```python
import csv
import time
from pathlib import Path
from dataclasses import asdict

from .models import GuidanceRecommendation, DroneState


COLUMNS = [
    "timestamp_ms", "mode", "target_cell_id", "target_lat", "target_lon",
    "drone_lat", "drone_lon", "bearing_deg", "distance_m", "final_score",
    "evidence_score", "uncertainty_score", "peak_score", "travel_cost",
    "oscillation_penalty", "gps_valid", "data_fresh",
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
```

---

## Task A9 — `backend/app/api/guidance.py`

```python
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.modules.guidance.engine import get_engine

router = APIRouter(prefix="/guidance", tags=["guidance"])


class InitRequest(BaseModel):
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    cell_size_m: float = 30.0


@router.post("/init")
def init_guidance(body: InitRequest) -> dict:
    bounds = {
        "min_lat": body.min_lat, "max_lat": body.max_lat,
        "min_lon": body.min_lon, "max_lon": body.max_lon,
    }
    result = get_engine().init_grid(bounds, body.cell_size_m)
    return {"ok": True, **result}


@router.get("/recommendation")
def get_recommendation() -> dict:
    rec = get_engine().get_recommendation()
    if rec is None:
        return {"available": False}
    return {"available": True, **rec}


@router.get("/grid")
def get_grid() -> dict:
    grid = get_engine().get_grid_state()
    if grid is None:
        return {"initialized": False, "cells": []}
    return {"initialized": True, **grid}


@router.post("/reset")
def reset_guidance() -> dict:
    get_engine().reset()
    return {"ok": True}


@router.get("/status")
def guidance_status() -> dict:
    return {"initialized": get_engine().is_initialized()}
```

---

## Task A10 — `backend/app/api/airunit.py`

```python
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.modules.guidance.engine import get_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/airunit", tags=["airunit"])

# ── Connection state (module-level, single Pi + N frontend clients) ───────────

_pi_ws: Optional[WebSocket] = None
_pi_info: Optional[dict] = None          # {"ip": "...", "port": 8001}
_frontend_clients: set[WebSocket] = set()
_broadcast_lock = asyncio.Lock()


async def _relay_to_frontends(msg: dict) -> None:
    dead: list[WebSocket] = []
    for ws in list(_frontend_clients):
        try:
            await ws.send_text(json.dumps(msg))
        except Exception:
            dead.append(ws)
    for ws in dead:
        _frontend_clients.discard(ws)


# ── Pi WebSocket endpoint ─────────────────────────────────────────────────────

@router.websocket("/ws")
async def pi_ws(websocket: WebSocket) -> None:
    global _pi_ws, _pi_info
    await websocket.accept()
    _pi_ws = websocket
    logger.info("Pi connected")
    await _relay_to_frontends({"type": "pi_connected"})

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue

            # Register Pi address
            if msg.get("type") == "hello":
                _pi_info = {"ip": msg.get("ip"), "port": msg.get("port", 8001)}
                logger.info("Pi registered: %s", _pi_info)

            # Route guidance packets to engine (non-blocking)
            msg_type = msg.get("type") or msg.get("msg_type")
            if msg_type in ("POSE", "EVIDENCE", "HEALTH"):
                get_engine().ingest(msg)

            # Relay everything to frontend clients
            await _relay_to_frontends(msg)

    except WebSocketDisconnect:
        logger.info("Pi disconnected")
    finally:
        _pi_ws = None
        _pi_info = None
        await _relay_to_frontends({"type": "pi_disconnected"})


# ── Frontend WebSocket relay endpoint ─────────────────────────────────────────

@router.websocket("/frontend-ws")
async def frontend_ws(websocket: WebSocket) -> None:
    global _pi_ws
    await websocket.accept()
    _frontend_clients.add(websocket)
    # Send current Pi connection state immediately
    await websocket.send_text(json.dumps({
        "type": "pi_status",
        "connected": _pi_ws is not None,
        "pi_info": _pi_info,
    }))
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue
            # Forward commands to Pi
            if msg.get("type") == "cmd" and _pi_ws is not None:
                try:
                    await _pi_ws.send_text(json.dumps(msg))
                except Exception as e:
                    logger.warning("Failed to send command to Pi: %s", e)
    except WebSocketDisconnect:
        pass
    finally:
        _frontend_clients.discard(websocket)


# ── REST endpoints ─────────────────────────────────────────────────────────────

@router.get("/status")
def get_status() -> dict:
    return {
        "pi_connected": _pi_ws is not None,
        "pi_info": _pi_info,
    }


class CommandRequest(BaseModel):
    cmd: str


@router.post("/command")
async def send_command(body: CommandRequest) -> dict:
    if _pi_ws is None:
        raise HTTPException(status_code=503, detail="Pi not connected")
    try:
        await _pi_ws.send_text(json.dumps({"type": "cmd", "cmd": body.cmd}))
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/files")
async def list_files() -> dict:
    if _pi_info is None:
        return {"files": [], "error": "Pi not connected"}
    pi_url = f"http://{_pi_info['ip']}:{_pi_info['port']}/logs"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(pi_url)
            return resp.json()
    except Exception as e:
        return {"files": [], "error": str(e)}


@router.get("/files/{fname}")
async def download_file(fname: str) -> StreamingResponse:
    if _pi_info is None:
        raise HTTPException(status_code=503, detail="Pi not connected")
    pi_url = f"http://{_pi_info['ip']}:{_pi_info['port']}/logs/{fname}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(pi_url)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="File not found on Pi")
        return StreamingResponse(
            content=resp.aiter_bytes(),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{fname}"'},
        )
```

---

## Task A11 — Unit tests (add to `backend/tests/unit/test_skeleton.py`)

Add after the last existing test. All tests are pure Python — no network, no filesystem.

```python
# ── Guidance unit tests ────────────────────────────────────────────────────────

def test_guidance_haversine_known_distance() -> None:
    from app.modules.guidance.grid import haversine_m
    # ~111km per degree of latitude
    d = haversine_m(31.0, 34.0, 32.0, 34.0)
    assert 110_000 < d < 113_000, f"Expected ~111km, got {d:.0f}m"


def test_guidance_grid_cell_count() -> None:
    from app.modules.guidance.grid import create_grid
    bounds = {"min_lat": 31.0, "max_lat": 31.1, "min_lon": 34.0, "max_lon": 34.1}
    grid = create_grid(bounds, cell_size_m=30.0)
    # ~11km x ~9km → many cells
    assert grid.n_rows > 0 and grid.n_cols > 0
    assert len(grid.cells) == grid.n_rows * grid.n_cols


def test_guidance_latlon_to_cell_id_inside() -> None:
    from app.modules.guidance.grid import create_grid, latlon_to_cell_id
    bounds = {"min_lat": 31.0, "max_lat": 31.1, "min_lon": 34.0, "max_lon": 34.1}
    grid = create_grid(bounds, cell_size_m=30.0)
    cell_id = latlon_to_cell_id(31.05, 34.05, grid)
    assert cell_id is not None
    assert 0 <= cell_id < len(grid.cells)


def test_guidance_latlon_to_cell_id_outside() -> None:
    from app.modules.guidance.grid import create_grid, latlon_to_cell_id
    bounds = {"min_lat": 31.0, "max_lat": 31.1, "min_lon": 34.0, "max_lon": 34.1}
    grid = create_grid(bounds, cell_size_m=30.0)
    assert latlon_to_cell_id(32.0, 34.05, grid) is None


def test_guidance_norm_rssi_clamps() -> None:
    from app.modules.guidance.scoring import norm_rssi
    assert norm_rssi(-100) == 0.0
    assert norm_rssi(-40) == 1.0
    assert 0.0 < norm_rssi(-70) < 1.0


def test_guidance_coverage_accumulates() -> None:
    from app.modules.guidance.scoring import update_coverage
    v = 0.0
    v = update_coverage(v, 2500.0)  # half of T_cov
    assert abs(v - 0.5) < 0.01
    v = update_coverage(v, 3000.0)  # should clamp at 1.0
    assert v == 1.0


def test_guidance_uncertainty_formula() -> None:
    from app.modules.guidance.scoring import compute_uncertainty
    # fully covered, recently updated → low uncertainty
    assert compute_uncertainty(v=1.0, a=0.0) == 0.0
    # never covered, very stale → high uncertainty
    assert compute_uncertainty(v=0.0, a=1.0) == 1.0


def test_guidance_final_score_explore_prefers_uncertainty() -> None:
    from app.modules.guidance.scoring import compute_final_score
    # High uncertainty cell should beat low uncertainty in EXPLORE mode
    score_high_u = compute_final_score(e=0.0, u=1.0, p=0.0, d=0.0, r=0.0, mode="EXPLORE")
    score_low_u = compute_final_score(e=0.0, u=0.0, p=0.0, d=0.0, r=0.0, mode="EXPLORE")
    assert score_high_u > score_low_u


def test_guidance_final_score_refine_prefers_evidence() -> None:
    from app.modules.guidance.scoring import compute_final_score
    score_high_e = compute_final_score(e=1.0, u=0.0, p=0.0, d=0.0, r=0.0, mode="REFINE")
    score_low_e = compute_final_score(e=0.0, u=0.0, p=0.0, d=0.0, r=0.0, mode="REFINE")
    assert score_high_e > score_low_e


def test_guidance_engine_init_and_reset() -> None:
    from app.modules.guidance.engine import GuidanceEngine
    engine = GuidanceEngine()
    assert not engine.is_initialized()
    bounds = {"min_lat": 31.0, "max_lat": 31.05, "min_lon": 34.0, "max_lon": 34.05}
    engine.init_grid(bounds, cell_size_m=30.0)
    assert engine.is_initialized()
    engine.reset()
    assert not engine.is_initialized()


def test_guidance_engine_ingest_pose_and_recommend() -> None:
    from app.modules.guidance.engine import GuidanceEngine
    engine = GuidanceEngine()
    bounds = {"min_lat": 31.0, "max_lat": 31.05, "min_lon": 34.0, "max_lon": 34.05}
    engine.init_grid(bounds, cell_size_m=30.0)
    engine.ingest({"type": "POSE", "lat": 31.025, "lon": 34.025, "gps_valid": True, "sniffer_alive": True})
    rec = engine.get_recommendation()
    assert rec is not None
    assert rec["mode"] in ("EXPLORE", "REFINE")
    assert "target_lat" in rec
    assert "bearing_deg" in rec
```

---

## Acceptance (Worker A)

- [ ] All 9 module files exist with content matching the spec
- [ ] `guidance.py` API file has all 5 endpoints
- [ ] `airunit.py` API file has both WS endpoints + 4 REST endpoints
- [ ] All 11 new unit tests added to `test_skeleton.py`
- [ ] `python -m py_compile` passes for all new files

---

---

# WORKER B — Frontend

## Files to create

```
frontend/src/pages/AirUnitPage.tsx
frontend/src/pages/AirUnitPage.css
frontend/src/api/airunit.ts
```

## Files to modify

```
frontend/src/App.tsx
frontend/src/pages/SessionStartPage.tsx
```

## Must NOT touch

- Any backend file
- Any other frontend file

---

## Task B1 — `frontend/src/api/airunit.ts`

```typescript
import { apiFetch } from './client'

// ── REST wrappers ─────────────────────────────────────────────────────────────

export const getAirunitStatus = () =>
  apiFetch<{ pi_connected: boolean; pi_info: { ip: string; port: number } | null }>(
    '/api/airunit/status'
  )

export const sendAirunitCommand = (cmd: string) =>
  apiFetch<{ ok: boolean }>('/api/airunit/command', {
    method: 'POST',
    body: JSON.stringify({ cmd }),
  })

export const listPiFiles = () =>
  apiFetch<{ files: PiFile[]; error?: string }>('/api/airunit/files')

export const initGuidance = (
  bounds: { min_lat: number; max_lat: number; min_lon: number; max_lon: number },
  cell_size_m: number = 30
) =>
  apiFetch<{ ok: boolean; n_rows: number; n_cols: number; total_cells: number }>(
    '/api/guidance/init',
    { method: 'POST', body: JSON.stringify({ ...bounds, cell_size_m }) }
  )

export const getGuidanceRecommendation = () =>
  apiFetch<GuidanceRecommendation | { available: false }>('/api/guidance/recommendation')

export const getGuidanceGrid = () =>
  apiFetch<GuidanceGridState>('/api/guidance/grid')

export const resetGuidance = () =>
  apiFetch<{ ok: boolean }>('/api/guidance/reset', { method: 'POST' })

// ── Types ─────────────────────────────────────────────────────────────────────

export interface PiFile {
  name: string
  size_bytes: number
  mtime: number
  description: string
}

export interface GuidanceRecommendation {
  available: true
  timestamp_ms: number
  mode: 'EXPLORE' | 'REFINE'
  target_cell_id: number
  target_lat: number
  target_lon: number
  bearing_deg: number
  distance_m: number
  final_score: number
  evidence_score: number
  uncertainty_score: number
  peak_score: number
  travel_cost: number
  oscillation_penalty: number
  gps_valid: boolean
  data_fresh: boolean
  recommendation_stale: boolean
  reason: string
}

export interface GridCell {
  cell_id: number
  center_lat: number
  center_lon: number
  evidence_score: number
  uncertainty_score: number
  peak_score: number
  coverage_score: number
  age_score: number
  final_score: number
}

export interface GuidanceGridState {
  initialized: boolean
  bounds?: { min_lat: number; max_lat: number; min_lon: number; max_lon: number }
  cell_size_m?: number
  n_rows?: number
  n_cols?: number
  mode?: string
  cells: GridCell[]
}
```

---

## Task B2 — `frontend/src/pages/AirUnitPage.tsx`

### Layout

```
┌─────────────────── Connection bar (full width) ───────────────────────────┐
│  ● Connected — Pi: 192.168.1.42:8001   [scan_start] [scan_stop]           │
│  ○ Not connected — waiting for Pi...                                       │
└───────────────────────────────────────────────────────────────────────────┘
┌───── Status Log ──────────┐  ┌────────── Guidance Map (main area) ────────┐
│ scrolling terminal        │  │ Leaflet map                                 │
│ [log lines from Pi]       │  │ [grid overlay] [drone] [target] [arrow]    │
│                           │  │                                             │
├───── Files ───────────────┤  ├────────── Guidance Panel ──────────────────┤
│ [Refresh] [cell_size: 30] │  │ Mode: EXPLORE  Cell 143  260m NE           │
│ name | size | date | ↓    │  │ Reason: High uncertainty + low coverage    │
│ ...                       │  │ GPS: OK  Data: Fresh                       │
└───────────────────────────┘  │ [Draw Boundary] [Start] [Stop] [Reset]     │
                               └────────────────────────────────────────────┘
```

### State

```typescript
const [piConnected, setPiConnected] = useState(false)
const [piInfo, setPiInfo] = useState<{ ip: string; port: number } | null>(null)
const [logs, setLogs] = useState<string[]>([])          // last 200 lines
const [files, setFiles] = useState<PiFile[]>([])
const [loadingFiles, setLoadingFiles] = useState(false)
const [gridState, setGridState] = useState<GuidanceGridState | null>(null)
const [recommendation, setRecommendation] = useState<GuidanceRecommendation | null>(null)
const [dronePos, setDronePos] = useState<{ lat: number; lon: number } | null>(null)
const [drawMode, setDrawMode] = useState(false)         // user is drawing boundary
const [drawCorner1, setDrawCorner1] = useState<{ lat: number; lon: number } | null>(null)
const [drawCorner2, setDrawCorner2] = useState<{ lat: number; lon: number } | null>(null)
const [cellSizeM, setCellSizeM] = useState(30)
const [guidanceRunning, setGuidanceRunning] = useState(false)
const [mapCenter, setMapCenter] = useState<[number, number]>([31.5, 34.8])  // default
```

### WebSocket connection

On mount, connect to `ws://localhost:8000/api/airunit/frontend-ws`.
On each message:
- `type: "pi_connected"` or `type: "pi_status"` with `connected: true` → `setPiConnected(true)`, `setPiInfo(...)`
- `type: "pi_disconnected"` → `setPiConnected(false)`, `setPiInfo(null)`
- `type: "log"` → append `msg.line` to `logs` (cap at 200 entries)
- `type: "status"` → append `[status] ${msg.status}` to logs
- `type: "POSE"` → if `msg.gps_valid && msg.lat`, call `setDronePos({ lat: msg.lat, lon: msg.lon })`

Reconnect with exponential backoff if WS closes.

On unmount, close WS.

### Geolocation on mount

```typescript
useEffect(() => {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (pos) => setMapCenter([pos.coords.latitude, pos.coords.longitude]),
      () => {}  // silently ignore if denied
    )
  }
}, [])
```

### Polling

While `guidanceRunning`:
- Every 2s: call `getGuidanceRecommendation()` → update `recommendation`
- Every 3s: call `getGuidanceGrid()` → update `gridState`

Use `useEffect` with `setInterval`. Clean up on unmount or when `guidanceRunning` flips to false.

### Draw boundary interaction

When `drawMode` is true, the Leaflet map captures clicks:
- First click → set `drawCorner1`
- Second click → set `drawCorner2`, exit draw mode, show the rectangle

Use a `Rectangle` component from `react-leaflet` to render the drawn bounds (orange dashed).

Once both corners set, `drawBounds` is computed as:
```typescript
const drawBounds = {
  min_lat: Math.min(drawCorner1.lat, drawCorner2.lat),
  max_lat: Math.max(drawCorner1.lat, drawCorner2.lat),
  min_lon: Math.min(drawCorner1.lon, drawCorner2.lon),
  max_lon: Math.max(drawCorner1.lon, drawCorner2.lon),
}
```

### "Start Guidance" button

Calls `initGuidance(drawBounds, cellSizeM)` → on success sets `guidanceRunning = true`.

### Grid overlay

When `gridState` is initialized, render each cell as a `Rectangle` in react-leaflet.
Color mapping based on `final_score`:
- `>= 0.6` → `#16a34a` (green, high value target)
- `>= 0.3` → `#ca8a04` (yellow, medium)
- `> 0` → `#dc2626` (red, low)
- `= 0` → `#374151` (dark gray, unvisited)
- Highlighted target cell (`cell_id === recommendation?.target_cell_id`): bright white border, opacity 0.9

Each cell `Rectangle` uses `[[min_lat, min_lon], [max_lat, max_lon]]` computed from center ± half step.
Use `fillOpacity: 0.35`, `weight: 0.5`.

### Drone marker

When `dronePos` is set, render a `CircleMarker` at drone position:
- radius 8, fill `#3b82f6` (blue), weight 2, white border

### Target arrow

When both `dronePos` and `recommendation` are set, render a `Polyline` from drone to target cell center:
- color `#facc15` (yellow), weight 3, dashArray `"8 4"`

### Guidance panel (sidebar)

Show only when `guidanceRunning && recommendation`:

```
Mode: [EXPLORE badge / REFINE badge]
Target: Cell {id}
Distance: {distance_m.toFixed(0)}m
Bearing: {bearing_deg.toFixed(0)}° {compass(bearing_deg)}
Reason: {reason}
GPS: {gps_valid ? "✓ OK" : "✗ Invalid"}
Data: {data_fresh ? "Fresh" : "Stale"}
Score: {final_score.toFixed(2)}
```

`compass(deg)` → returns N / NE / E / SE / S / SW / W / NW based on 45° buckets.

### Scan controls (connection bar)

Only shown when `piConnected`. Four buttons that call `sendAirunitCommand`:
- "Start WiFi" → `cmd: "scan_start"`
- "Stop WiFi" → `cmd: "scan_stop"`
- "Start BLE" → `cmd: "ble_scan_start"`
- "Stop BLE" → `cmd: "ble_scan_stop"`

### File panel

- "Refresh" button calls `listPiFiles()` → updates `files`
- Table: Name | Size (KB) | Modified | Download
- Download link: direct `<a href={/api/airunit/files/${file.name}} download>` — proxied through GS backend

### Log panel

- Scrolling `<pre>` with monospace font, dark background
- Auto-scroll to bottom on new lines (useRef + scrollTop)
- Show last 200 lines

---

## Task B3 — `frontend/src/pages/AirUnitPage.css`

Key styles (dark theme matching the app):

```css
.airunit-page { display: flex; flex-direction: column; height: 100%; gap: 0; }
.airunit-connection-bar { padding: 8px 16px; background: #1e293b; border-bottom: 1px solid #334155; display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.pi-dot-connected { color: #22c55e; font-size: 1.2rem; }
.pi-dot-disconnected { color: #6b7280; font-size: 1.2rem; }
.airunit-body { display: flex; flex: 1; min-height: 0; overflow: hidden; }
.airunit-sidebar { width: 300px; min-width: 260px; display: flex; flex-direction: column; border-right: 1px solid #334155; overflow: hidden; }
.airunit-log { flex: 1; overflow-y: auto; background: #0f172a; padding: 8px; font-family: monospace; font-size: 11px; color: #94a3b8; min-height: 0; }
.airunit-files { flex-shrink: 0; max-height: 220px; overflow-y: auto; border-top: 1px solid #334155; padding: 8px; }
.airunit-files table { width: 100%; border-collapse: collapse; font-size: 12px; }
.airunit-files th, .airunit-files td { padding: 3px 6px; border-bottom: 1px solid #1e293b; }
.airunit-main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.airunit-map { flex: 1; min-height: 0; }
.airunit-guidance-panel { flex-shrink: 0; padding: 12px 16px; background: #1e293b; border-top: 1px solid #334155; display: flex; gap: 24px; align-items: center; flex-wrap: wrap; }
.guidance-mode-badge { padding: 3px 10px; border-radius: 4px; font-weight: 700; font-size: 0.75rem; letter-spacing: 0.05em; text-transform: uppercase; }
.guidance-mode-explore { background: #1d4ed8; color: #bfdbfe; }
.guidance-mode-refine { background: #7c3aed; color: #ede9fe; }
.guidance-stat { display: flex; flex-direction: column; font-size: 12px; }
.guidance-stat-label { color: #64748b; font-size: 10px; text-transform: uppercase; }
.guidance-stat-value { color: #f1f5f9; font-weight: 600; }
.guidance-reason { font-size: 12px; color: #94a3b8; font-style: italic; max-width: 220px; }
.guidance-controls { display: flex; gap: 8px; margin-left: auto; }
```

---

## Task B4 — Update `frontend/src/App.tsx`

Add `import AirUnitPage from './pages/AirUnitPage'` and add the route inside `<Route element={<AppShell />}>`:

```tsx
<Route path="/airunit" element={<AirUnitPage />} />
```

---

## Task B5 — Update `frontend/src/pages/SessionStartPage.tsx`

Add a "Start Live Mission" section below the existing session start form (before the saved sessions section or at the bottom of the page).

```tsx
<div className="live-mission-section">
  <h3>Live Mission</h3>
  <p>Connect to the airborne unit and run smart flight guidance in real time.</p>
  <button
    className="btn-live-mission"
    onClick={() => navigate('/airunit')}
  >
    Start Live Mission
  </button>
</div>
```

Add CSS in `SessionStartPage.css` (find and edit the existing file):
```css
.live-mission-section { margin-top: 32px; padding: 20px; background: #1e3a5f; border-radius: 8px; border: 1px solid #2563eb; }
.live-mission-section h3 { margin: 0 0 8px; color: #93c5fd; }
.live-mission-section p { margin: 0 0 16px; color: #94a3b8; font-size: 14px; }
.btn-live-mission { background: #2563eb; color: white; border: none; border-radius: 6px; padding: 10px 24px; font-size: 14px; font-weight: 600; cursor: pointer; }
.btn-live-mission:hover { background: #1d4ed8; }
```

---

## Acceptance (Worker B)

- [ ] `airunit.ts` has all API wrappers and types
- [ ] `AirUnitPage.tsx` renders without TypeScript errors
- [ ] WebSocket connects to `/api/airunit/frontend-ws`, logs display, drone position updates
- [ ] Grid overlay renders colored cells based on `final_score`
- [ ] Draw boundary mode captures two map clicks and computes bounds
- [ ] Guidance panel shows mode/target/distance/bearing/reason when guidance is running
- [ ] Scan control buttons send commands to Pi via `sendAirunitCommand`
- [ ] File table shows Pi files with download links
- [ ] `/airunit` route added to App.tsx
- [ ] SessionStartPage has "Start Live Mission" section with navigation

---

---

# SUPERVISOR — Integration

## Update `backend/app/main.py`

Add the two new routers to `create_app()`:

```python
from app.api import (
    # ... existing imports ...
    guidance,
    airunit,
)

# Inside create_app(), after existing router includes:
app.include_router(guidance.router, prefix="/api")
app.include_router(airunit.router, prefix="/api")
```

## Run checks

```bash
cd backend && python -m pytest tests/unit/ -x -q
cd frontend && npm.cmd run build
```

## Report in `.ai/codex_result.md`

1. Worker A: files created, test count (before and after), any deviations
2. Worker B: TypeScript errors (if any), build output
3. Supervisor: router integration, final test + build results
4. Any known issues or follow-up items
