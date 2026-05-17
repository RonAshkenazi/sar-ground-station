# Codex Handoff — Spatial Entropy Propagation + Interactive Emulator

## Requested Role

[SUPERVISOR → spawn Worker A (backend) and Worker B (frontend) in parallel, then integrate]

---

## Context

We are implementing spatial entropy propagation in the guidance engine (design spec in `docs/SPATIAL_ENTROPY_GUIDANCE.md`) and an interactive browser-based emulator that lets the operator manually control a drone dot on a Leaflet map and observe the grid updating in real time.

---

## Worker A — Backend (spatial entropy)

### Files to modify

```
backend/app/modules/guidance/config.py
backend/app/modules/guidance/models.py
backend/app/modules/guidance/scoring.py
backend/app/modules/guidance/state.py
backend/app/modules/guidance/engine.py
backend/tests/unit/test_skeleton.py
```

### Must NOT touch

- `backend/app/modules/guidance/grid.py` — correct as-is
- `backend/app/modules/guidance/recommendation.py` — Phase 2, skip
- Any frontend file

---

### Task A1 — `config.py`: add new parameters

Append to the existing file:

```python
# Spatial evidence propagation kernel
NEIGHBOR_EVIDENCE_ALPHA_ORTH: float = 0.25
NEIGHBOR_EVIDENCE_ALPHA_DIAG: float = 0.15

# Spatial coverage/dwell propagation
NEIGHBOR_COVERAGE_BETA: float = 0.20
NEIGHBOR_COVERAGE_ALPHA_ORTH: float = 1.00
NEIGHBOR_COVERAGE_ALPHA_DIAG: float = 0.70

# Evidence freshness decay (ms); 300 000 ms = 5 min
TAU_EVIDENCE_DECAY_MS: float = 300_000.0

# Minimum evidence for candidate target selection
E_TARGET_MIN: float = 0.05

# Entropy numerics
ENTROPY_EPSILON: float = 1e-6
ENTROPY_MIN_MASS: float = 0.05
```

---

### Task A2 — `models.py`: add fields to `GridCellState`

Add after `last_seen_ms`:

```python
    spatial_entropy: float = 1.0
    spatial_certainty: float = 0.0
    evidence_freshness: float = 0.0
    display_score: float = 0.0
```

---

### Task A3 — `scoring.py`: add entropy and freshness functions

Add `import time as _time` at the top of the file (module level, after existing imports).

Add these two functions after `compute_uncertainty()`. Do NOT modify any existing function.

```python
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
    """Returns (H_i, C_i). H=1 diffuse, H=0 sharp peak. C = 1 - H."""
    now_ms = _time.time() * 1000.0
    neighborhood = [cell_id] + get_neighbors(cell_id, grid)

    masses = []
    for nid in neighborhood:
        cs = cell_states.get(nid)
        if cs is None:
            masses.append(cfg.ENTROPY_EPSILON)
        else:
            age_ms = (now_ms - cs.last_seen_ms) if cs.last_seen_ms is not None else 1e9
            m = cs.evidence_score * math.exp(-age_ms / cfg.TAU_EVIDENCE_DECAY_MS)
            masses.append(max(m, cfg.ENTROPY_EPSILON))

    total = sum(masses)
    if total < cfg.ENTROPY_MIN_MASS:
        return 1.0, 0.0

    n = len(masses)
    entropy = -sum((m / total) * math.log(m / total) for m in masses)
    h = max(0.0, min(1.0, entropy / math.log(n)))
    return h, 1.0 - h
```

---

### Task A4 — `state.py`: propagate evidence and dwell to neighbors

#### 4a — `ingest_evidence()`: add neighbor evidence propagation

After `cs.last_seen_ms = now` (last line of the source-cell update block), add:

```python
    # Propagate evidence to 8-connected neighbors
    for neighbor_id in get_neighbors(cell_id, state.grid):
        ncs = state.cell_states.get(neighbor_id)
        source_cell = state.grid.cells.get(cell_id)
        neighbor_cell = state.grid.cells.get(neighbor_id)
        if ncs is None or source_cell is None or neighbor_cell is None:
            continue
        is_diagonal = (
            abs(source_cell.row - neighbor_cell.row) == 1
            and abs(source_cell.col - neighbor_cell.col) == 1
        )
        alpha = cfg.NEIGHBOR_EVIDENCE_ALPHA_DIAG if is_diagonal else cfg.NEIGHBOR_EVIDENCE_ALPHA_ORTH
        ncs.evidence_score = update_evidence_ema(ncs.evidence_score, alpha * raw_e)
        ncs.last_seen_ms = now
```

Then, before `diag.evidence_packets_ingested += 1`, recompute entropy for source + neighbors:

```python
    # Recompute entropy/freshness for source cell and all affected neighbors
    from .scoring import compute_spatial_entropy, compute_evidence_freshness
    for aid in [cell_id] + get_neighbors(cell_id, state.grid):
        acs = state.cell_states.get(aid)
        if acs is None:
            continue
        h, c = compute_spatial_entropy(aid, state.cell_states, state.grid)
        acs.spatial_entropy = h
        acs.spatial_certainty = c
        acs.evidence_freshness = compute_evidence_freshness(acs.evidence_score, acs.last_seen_ms)
        acs.display_score = acs.evidence_freshness
```

`get_neighbors` is already imported at the top of `state.py`. Add `from . import config as cfg` if it is not already imported there.

#### 4b — `ingest_pose()`: propagate dwell to neighbors

After `cs.last_updated_ms = now` in `ingest_pose()`, add:

```python
    # Propagate dwell weakly to 8-connected neighbors
    for neighbor_id in get_neighbors(cell_id, state.grid):
        ncs = state.cell_states.get(neighbor_id)
        source_cell = state.grid.cells.get(cell_id)
        neighbor_cell = state.grid.cells.get(neighbor_id)
        if ncs is None or source_cell is None or neighbor_cell is None:
            continue
        is_diagonal = (
            abs(source_cell.row - neighbor_cell.row) == 1
            and abs(source_cell.col - neighbor_cell.col) == 1
        )
        k_cov = cfg.NEIGHBOR_COVERAGE_ALPHA_DIAG if is_diagonal else cfg.NEIGHBOR_COVERAGE_ALPHA_ORTH
        ncs.coverage_score = update_coverage(ncs.coverage_score, cfg.NEIGHBOR_COVERAGE_BETA * k_cov * dwell_ms)
        ncs.uncertainty_score = compute_uncertainty(ncs.coverage_score, ncs.age_score)
```

---

### Task A5 — `engine.py`: expose new fields + refresh freshness in tick

**In `get_grid_state()`**, add four fields to the per-cell dict, after `"final_score"`:

```python
                        "spatial_entropy": cs.spatial_entropy,
                        "spatial_certainty": cs.spatial_certainty,
                        "evidence_freshness": cs.evidence_freshness,
                        "display_score": cs.display_score,
```

**In `_tick_loop()`**, after `tick_age(self._state, interval_ms)` add:

```python
                    from .scoring import compute_evidence_freshness
                    for cs in self._state.cell_states.values():
                        cs.evidence_freshness = compute_evidence_freshness(
                            cs.evidence_score, cs.last_seen_ms
                        )
                        cs.display_score = cs.evidence_freshness
```

---

### Task A6 — Unit tests

Add after the last existing guidance test in `backend/tests/unit/test_skeleton.py`:

```python
def test_evidence_propagates_to_neighbors() -> None:
    from app.modules.guidance.engine import GuidanceEngine
    from app.modules.guidance.grid import create_grid, latlon_to_cell_id, get_neighbors
    engine = GuidanceEngine()
    bounds = {"min_lat": 31.0, "max_lat": 31.05, "min_lon": 34.0, "max_lon": 34.05}
    engine.init_grid(bounds, cell_size_m=30.0)
    engine.ingest({
        "type": "EVIDENCE", "lat": 31.025, "lon": 34.025,
        "dwell_ms": 3000, "frames_total": 24, "frames_strong": 8,
        "rssi_max_dbm": -55.0, "rssi_p95_dbm": -62.0, "rssi_mean_dbm": -70.0,
    })
    grid = engine.get_grid_state()
    cells = {c["cell_id"]: c for c in grid["cells"]}
    grid_obj = create_grid(bounds, 30.0)
    from app.modules.guidance.grid import latlon_to_cell_id, get_neighbors
    center_id = latlon_to_cell_id(31.025, 34.025, grid_obj)
    center_e = cells[center_id]["evidence_score"]
    assert center_e > 0.0
    neighbors = get_neighbors(center_id, grid_obj)
    neighbor_evidences = [cells[n]["evidence_score"] for n in neighbors if n in cells]
    assert any(e > 0.0 for e in neighbor_evidences), "Neighbors must receive propagated evidence"
    assert all(e < center_e for e in neighbor_evidences if e > 0), "Neighbors must be weaker than center"


def test_diagonal_neighbors_weaker_than_orthogonal() -> None:
    from app.modules.guidance.engine import GuidanceEngine
    from app.modules.guidance.grid import create_grid, latlon_to_cell_id, get_neighbors
    engine = GuidanceEngine()
    bounds = {"min_lat": 31.0, "max_lat": 31.06, "min_lon": 34.0, "max_lon": 34.06}
    engine.init_grid(bounds, cell_size_m=30.0)
    for _ in range(5):
        engine.ingest({
            "type": "EVIDENCE", "lat": 31.03, "lon": 34.03,
            "dwell_ms": 3000, "frames_total": 24, "frames_strong": 10,
            "rssi_max_dbm": -53.0, "rssi_p95_dbm": -60.0, "rssi_mean_dbm": -67.0,
        })
    grid_state = engine.get_grid_state()
    cells = {c["cell_id"]: c for c in grid_state["cells"]}
    grid_obj = create_grid(bounds, 30.0)
    center_id = latlon_to_cell_id(31.03, 34.03, grid_obj)
    center_cell = grid_obj.cells[center_id]
    orth, diag = [], []
    for nid in get_neighbors(center_id, grid_obj):
        n = grid_obj.cells[nid]
        dr, dc = abs(center_cell.row - n.row), abs(center_cell.col - n.col)
        (diag if dr == 1 and dc == 1 else orth).append(cells[nid]["evidence_score"])
    if orth and diag:
        assert sum(orth) / len(orth) > sum(diag) / len(diag)


def test_entropy_high_for_uniform_evidence() -> None:
    from app.modules.guidance.scoring import compute_spatial_entropy
    from app.modules.guidance.grid import create_grid
    from app.modules.guidance.models import GridCellState
    import time
    bounds = {"min_lat": 31.0, "max_lat": 31.05, "min_lon": 34.0, "max_lon": 34.05}
    grid = create_grid(bounds, cell_size_m=30.0)
    now_ms = time.time() * 1000.0
    states = {
        cid: GridCellState(cell_id=cid, center_lat=c.center_lat, center_lon=c.center_lon,
                           evidence_score=0.5, last_seen_ms=now_ms)
        for cid, c in grid.cells.items()
    }
    center_id = list(grid.cells.keys())[len(grid.cells) // 2]
    h, c = compute_spatial_entropy(center_id, states, grid)
    assert h > 0.8
    assert c < 0.2


def test_entropy_low_for_single_peak() -> None:
    from app.modules.guidance.scoring import compute_spatial_entropy
    from app.modules.guidance.grid import create_grid, latlon_to_cell_id
    from app.modules.guidance.models import GridCellState
    import time
    bounds = {"min_lat": 31.0, "max_lat": 31.05, "min_lon": 34.0, "max_lon": 34.05}
    grid = create_grid(bounds, cell_size_m=30.0)
    now_ms = time.time() * 1000.0
    states = {
        cid: GridCellState(cell_id=cid, center_lat=c.center_lat, center_lon=c.center_lon)
        for cid, c in grid.cells.items()
    }
    peak_id = latlon_to_cell_id(31.025, 34.025, grid)
    states[peak_id].evidence_score = 0.9
    states[peak_id].last_seen_ms = now_ms
    h, c = compute_spatial_entropy(peak_id, states, grid)
    assert h < 0.5
    assert c > 0.5


def test_entropy_max_when_no_mass() -> None:
    from app.modules.guidance.scoring import compute_spatial_entropy
    from app.modules.guidance.grid import create_grid
    from app.modules.guidance.models import GridCellState
    bounds = {"min_lat": 31.0, "max_lat": 31.05, "min_lon": 34.0, "max_lon": 34.05}
    grid = create_grid(bounds, cell_size_m=30.0)
    states = {
        cid: GridCellState(cell_id=cid, center_lat=c.center_lat, center_lon=c.center_lon)
        for cid, c in grid.cells.items()
    }
    h, c = compute_spatial_entropy(list(grid.cells.keys())[0], states, grid)
    assert h == 1.0 and c == 0.0


def test_dwell_propagates_to_neighbors() -> None:
    from app.modules.guidance.engine import GuidanceEngine
    from app.modules.guidance.grid import create_grid, latlon_to_cell_id, get_neighbors
    engine = GuidanceEngine()
    bounds = {"min_lat": 31.0, "max_lat": 31.05, "min_lon": 34.0, "max_lon": 34.05}
    engine.init_grid(bounds, cell_size_m=30.0)
    for _ in range(10):
        engine.ingest({"type": "POSE", "lat": 31.025, "lon": 34.025, "gps_valid": True})
    grid_state = engine.get_grid_state()
    cells = {c["cell_id"]: c for c in grid_state["cells"]}
    grid_obj = create_grid(bounds, 30.0)
    center_id = latlon_to_cell_id(31.025, 34.025, grid_obj)
    neighbors = get_neighbors(center_id, grid_obj)
    center_cov = cells[center_id]["coverage_score"]
    assert center_cov > 0.0
    neighbor_covs = [cells[n]["coverage_score"] for n in neighbors if n in cells]
    assert any(v > 0.0 for v in neighbor_covs)
    assert center_cov > max(neighbor_covs)


def test_grid_api_returns_new_fields() -> None:
    from app.modules.guidance.engine import GuidanceEngine
    engine = GuidanceEngine()
    bounds = {"min_lat": 31.0, "max_lat": 31.05, "min_lon": 34.0, "max_lon": 34.05}
    engine.init_grid(bounds, cell_size_m=30.0)
    engine.ingest({
        "type": "EVIDENCE", "lat": 31.025, "lon": 34.025,
        "dwell_ms": 3000, "frames_total": 20, "frames_strong": 5,
        "rssi_max_dbm": -58.0, "rssi_p95_dbm": -65.0, "rssi_mean_dbm": -72.0,
    })
    grid = engine.get_grid_state()
    sample = grid["cells"][0]
    for field in ("spatial_entropy", "spatial_certainty", "evidence_freshness", "display_score"):
        assert field in sample, f"Missing field: {field}"
```

### Acceptance (Worker A)

- [ ] 8 new constants in `config.py`
- [ ] 4 new fields on `GridCellState`
- [ ] `compute_evidence_freshness` and `compute_spatial_entropy` in `scoring.py`
- [ ] `ingest_evidence` propagates evidence to 8 neighbors (orth vs diag alpha)
- [ ] `ingest_pose` propagates dwell to 8 neighbors
- [ ] Entropy/freshness recomputed on each evidence ingest
- [ ] `get_grid_state()` returns 4 new fields per cell
- [ ] `_tick_loop` refreshes freshness/display_score every tick
- [ ] All 121 existing tests pass
- [ ] All 7 new tests pass

---

## Worker B — Frontend (interactive emulator page)

### Files to create

```
frontend/src/pages/EmulatorPage.tsx
frontend/src/pages/EmulatorPage.css
```

### Files to modify

```
frontend/src/api/airunit.ts
frontend/src/App.tsx
```

### Must NOT touch

- `AirUnitPage.tsx` — do not modify
- Any backend file

---

### Task B1 — Update `airunit.ts`

Add `ingestGuidancePacket` function and update the `GridCell` interface to include the new fields:

```typescript
export const ingestGuidancePacket = (packet: Record<string, unknown>) =>
  apiFetch<{ ok: boolean }>('/api/guidance/update', {
    method: 'POST',
    body: JSON.stringify(packet),
  })
```

Update `GridCell` interface — add these fields (all optional for backward compat):

```typescript
  spatial_entropy?: number
  spatial_certainty?: number
  evidence_freshness?: number
  display_score?: number
```

---

### Task B2 — `EmulatorPage.tsx`

Full interactive guidance emulator. The user controls a drone dot on a Leaflet map by clicking, with a sidebar to tune packet parameters.

#### Layout

```
┌─────────────────────── top bar ────────────────────────────────────┐
│  Guidance Emulator  [Draw Boundary] [Reset] [Init Grid]            │
│  Grid: 12×9 (108 cells)   Mode: EXPLORE   Rec: Cell 43 → 185m NE  │
├─── sidebar (280px) ──────────┬──── map (flex 1, full height) ──────┤
│  ── DRONE ──                 │                                      │
│  lat 31.50042                │   Leaflet map                        │
│  lon 34.80031                │   Grid overlay (colored cells)       │
│  [Click map to move]         │   Orange boundary rectangle          │
│                              │   Blue drone CircleMarker            │
│  ── POSE RATE ──             │   Yellow dashed line to target       │
│  [Off][½Hz][1Hz][2Hz]       │                                      │
│                              │   Click anywhere → drone jumps there │
│  ── EVIDENCE ──              │                                      │
│  [● ON  / ○ OFF]             │                                      │
│  Interval  [2s][5s][10s]    │                                      │
│                              │                                      │
│  ── RSSI (p95 dBm) ──        │                                      │
│  -90 [████████──] -62        │                                      │
│                              │                                      │
│  ── FRAMES TOTAL ──          │                                      │
│  1 [██████────] 20           │                                      │
│                              │                                      │
│  ── STRONG RATIO ──          │                                      │
│  0% [████──────] 40%         │                                      │
│                              │                                      │
│  ── STATS ──                 │                                      │
│  POSE sent:      42          │                                      │
│  EVIDENCE sent:   8          │                                      │
│                              │                                      │
│  ── LAST CELL ──             │                                      │
│  E  0.42  fresh 0.39         │                                      │
│  U  0.31  H     0.58         │                                      │
│  C  0.42  J     0.36         │                                      │
└──────────────────────────────┴──────────────────────────────────────┘
```

#### State

```typescript
const [dronePos, setDronePos] = useState<[number, number] | null>(null)
const [drawMode, setDrawMode] = useState(false)
const [drawCorner1, setDrawCorner1] = useState<[number, number] | null>(null)
const [drawCorner2, setDrawCorner2] = useState<[number, number] | null>(null)
const [gridInitialized, setGridInitialized] = useState(false)
const [cellSizeM, setCellSizeM] = useState(30)
const [gridState, setGridState] = useState<GuidanceGridState | null>(null)
const [recommendation, setRecommendation] = useState<GuidanceRecommendation | null>(null)

// Pose controls
const [poseRate, setPoseRate] = useState<0 | 0.5 | 1 | 2>(1)   // Hz; 0 = off

// Evidence controls
const [evidenceOn, setEvidenceOn] = useState(true)
const [evidenceInterval, setEvidenceInterval] = useState(3)     // seconds

// Packet parameters
const [rssiP95, setRssiP95] = useState(-65)                      // dBm
const [framesTotal, setFramesTotal] = useState(20)
const [strongRatio, setStrongRatio] = useState(0.4)              // 0-1

// Stats
const [poseSent, setPoseSent] = useState(0)
const [evidenceSent, setEvidenceSent] = useState(0)

// Map center
const [mapCenter] = useState<[number, number]>([31.5, 34.8])
```

#### Derived values

```typescript
const rssiMax = rssiP95 + 7   // max is always ~7dBm stronger than p95
const framesStrong = Math.round(framesTotal * strongRatio)

const drawBounds = drawCorner1 && drawCorner2 ? {
  min_lat: Math.min(drawCorner1[0], drawCorner2[0]),
  max_lat: Math.max(drawCorner1[0], drawCorner2[0]),
  min_lon: Math.min(drawCorner1[1], drawCorner2[1]),
  max_lon: Math.max(drawCorner1[1], drawCorner2[1]),
} : null
```

#### Map click handler (inside a `MapClickHandler` component using `useMapEvents`)

```typescript
function MapClickHandler({ onMapClick }: { onMapClick: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(e) { onMapClick(e.latlng.lat, e.latlng.lng) },
  })
  return null
}
```

When NOT in draw mode: clicking the map moves the drone (`setDronePos([lat, lng])`).

When in draw mode: first click sets `drawCorner1`, second click sets `drawCorner2` and exits draw mode.

#### Pose timer

```typescript
useEffect(() => {
  if (poseRate === 0 || !gridInitialized || !dronePos) return
  const interval = setInterval(async () => {
    await ingestGuidancePacket({
      type: 'POSE', lat: dronePos[0], lon: dronePos[1],
      gps_valid: true, sniffer_alive: true,
    })
    setPoseSent(n => n + 1)
  }, 1000 / poseRate)
  return () => clearInterval(interval)
}, [poseRate, gridInitialized, dronePos])
```

#### Evidence timer

```typescript
useEffect(() => {
  if (!evidenceOn || !gridInitialized || !dronePos) return
  const interval = setInterval(async () => {
    await ingestGuidancePacket({
      type: 'EVIDENCE',
      lat: dronePos[0], lon: dronePos[1],
      dwell_ms: evidenceInterval * 1000,
      frames_total: framesTotal,
      frames_strong: framesStrong,
      rssi_max_dbm: rssiMax,
      rssi_p95_dbm: rssiP95,
      rssi_mean_dbm: rssiP95 - 5,
    })
    setEvidenceSent(n => n + 1)
  }, evidenceInterval * 1000)
  return () => clearInterval(interval)
}, [evidenceOn, gridInitialized, dronePos, evidenceInterval, framesTotal, framesStrong, rssiMax, rssiP95])
```

#### Grid polling

Every 2 seconds when `gridInitialized`:

```typescript
useEffect(() => {
  if (!gridInitialized) return
  const id = setInterval(async () => {
    const g = await getGuidanceGrid()
    setGridState(g)
    if (g.initialized) {
      const rec = await getGuidanceRecommendation()
      if ('available' in rec && rec.available) setRecommendation(rec as GuidanceRecommendation)
    }
  }, 2000)
  return () => clearInterval(id)
}, [gridInitialized])
```

#### Init button handler

```typescript
async function handleInit() {
  if (!drawBounds) return
  await resetGuidance()
  await initGuidance(drawBounds, cellSizeM)
  setGridInitialized(true)
  setPoseSent(0)
  setEvidenceSent(0)
}
```

#### Reset button handler

```typescript
async function handleReset() {
  await resetGuidance()
  setGridInitialized(false)
  setGridState(null)
  setRecommendation(null)
  setPoseSent(0)
  setEvidenceSent(0)
}
```

#### Grid cell coloring

Color cells by `display_score ?? evidence_score`. Use the researcher's evidence palette:

```typescript
function cellColor(cell: GridCell): string {
  const score = cell.display_score ?? cell.evidence_score ?? 0
  if (score >= 0.60) return '#16a34a'   // green
  if (score >= 0.30) return '#ca8a04'   // yellow
  if (score >= 0.10) return '#ea580c'   // orange
  if (score > 0.01)  return '#dc2626'   // red
  return '#374151'                       // dark gray — no evidence
}
```

Cell bounds from center ± half of the grid step (compute from `gridState.bounds` and `gridState.n_rows/n_cols`):

```typescript
const latStep = gridState.bounds
  ? (gridState.bounds.max_lat - gridState.bounds.min_lat) / (gridState.n_rows ?? 1)
  : 0
const lonStep = gridState.bounds
  ? (gridState.bounds.max_lon - gridState.bounds.min_lon) / (gridState.n_cols ?? 1)
  : 0
```

Per cell:
```typescript
const bounds: [[number, number], [number, number]] = [
  [cell.center_lat - latStep / 2, cell.center_lon - lonStep / 2],
  [cell.center_lat + latStep / 2, cell.center_lon + lonStep / 2],
]
```

Target cell gets `weight: 2, color: '#ffffff'`.

#### Cell tooltip (on hover)

Show a small tooltip on each cell rectangle:

```tsx
<Tooltip sticky>
  <div style={{ fontFamily: 'monospace', fontSize: 11 }}>
    <div>Cell {cell.cell_id}</div>
    <div>E {(cell.evidence_score ?? 0).toFixed(3)}</div>
    <div>fresh {(cell.display_score ?? 0).toFixed(3)}</div>
    <div>U {(cell.uncertainty_score ?? 0).toFixed(3)}</div>
    <div>H {(cell.spatial_entropy ?? 1).toFixed(2)}</div>
    <div>C {(cell.spatial_certainty ?? 0).toFixed(2)}</div>
    <div>J {(cell.final_score ?? 0).toFixed(3)}</div>
  </div>
</Tooltip>
```

#### Drone marker

```tsx
{dronePos && (
  <CircleMarker
    center={dronePos}
    radius={10}
    pathOptions={{ color: '#fff', fillColor: '#3b82f6', fillOpacity: 1, weight: 2 }}
  />
)}
```

#### Target line

```tsx
{dronePos && recommendation && (
  <Polyline
    positions={[dronePos, [recommendation.target_lat, recommendation.target_lon]]}
    pathOptions={{ color: '#facc15', weight: 2, dashArray: '8 4' }}
  />
)}
```

#### Sidebar — POSE RATE

```tsx
<div className="emu-control-group">
  <div className="emu-label">POSE RATE</div>
  <div className="emu-btn-row">
    {([0, 0.5, 1, 2] as const).map(r => (
      <button
        key={r}
        className={`emu-btn ${poseRate === r ? 'emu-btn-active' : ''}`}
        onClick={() => setPoseRate(r)}
      >
        {r === 0 ? 'Off' : `${r}Hz`}
      </button>
    ))}
  </div>
</div>
```

#### Sidebar — EVIDENCE toggle + interval

```tsx
<div className="emu-control-group">
  <div className="emu-label">EVIDENCE</div>
  <button
    className={`emu-toggle ${evidenceOn ? 'emu-toggle-on' : ''}`}
    onClick={() => setEvidenceOn(v => !v)}
  >
    {evidenceOn ? '● ON' : '○ OFF'}
  </button>
  <div className="emu-label" style={{ marginTop: 8 }}>Interval</div>
  <div className="emu-btn-row">
    {[2, 5, 10].map(s => (
      <button
        key={s}
        className={`emu-btn ${evidenceInterval === s ? 'emu-btn-active' : ''}`}
        onClick={() => setEvidenceInterval(s)}
      >
        {s}s
      </button>
    ))}
  </div>
</div>
```

#### Sidebar — RSSI slider

Range: -90 to -55 dBm. Display current value next to slider.

```tsx
<div className="emu-control-group">
  <div className="emu-label">RSSI p95: {rssiP95} dBm</div>
  <input
    type="range" min={-90} max={-55} step={1}
    value={rssiP95}
    onChange={e => setRssiP95(Number(e.target.value))}
    className="emu-slider"
  />
  <div className="emu-slider-labels"><span>-90</span><span>-55</span></div>
</div>
```

#### Sidebar — Frames total + strong ratio (same pattern with range sliders)

- Frames total: min=1, max=50, step=1
- Strong ratio: min=0, max=1, step=0.05, display as `{Math.round(strongRatio*100)}%`

#### Sidebar — Stats

```tsx
<div className="emu-control-group">
  <div className="emu-label">STATS</div>
  <div className="emu-stat-row"><span>POSE sent</span><span>{poseSent}</span></div>
  <div className="emu-stat-row"><span>EV sent</span><span>{evidenceSent}</span></div>
</div>
```

#### Sidebar — Last cell scores (find the cell nearest dronePos)

```typescript
const droneCell = useMemo(() => {
  if (!gridState?.cells || !dronePos) return null
  // find closest cell center to dronePos
  let best: GridCell | null = null
  let bestDist = Infinity
  for (const c of gridState.cells) {
    const d = Math.hypot(c.center_lat - dronePos[0], c.center_lon - dronePos[1])
    if (d < bestDist) { bestDist = d; best = c }
  }
  return best
}, [gridState, dronePos])
```

Display in sidebar when `droneCell` is not null:

```tsx
<div className="emu-stat-row"><span>E</span><span>{droneCell.evidence_score.toFixed(3)}</span></div>
<div className="emu-stat-row"><span>fresh</span><span>{(droneCell.display_score ?? 0).toFixed(3)}</span></div>
<div className="emu-stat-row"><span>U</span><span>{droneCell.uncertainty_score.toFixed(3)}</span></div>
<div className="emu-stat-row"><span>H</span><span>{(droneCell.spatial_entropy ?? 1).toFixed(2)}</span></div>
<div className="emu-stat-row"><span>C</span><span>{(droneCell.spatial_certainty ?? 0).toFixed(2)}</span></div>
<div className="emu-stat-row"><span>J</span><span>{droneCell.final_score.toFixed(3)}</span></div>
```

#### Top bar

```tsx
<div className="emu-topbar">
  <span className="emu-title">Guidance Emulator</span>
  <button className={`emu-btn ${drawMode ? 'emu-btn-active' : ''}`} onClick={() => setDrawMode(v => !v)}>
    {drawMode ? 'Click 2nd corner...' : 'Draw Boundary'}
  </button>
  <button className="emu-btn" onClick={handleReset}>Reset</button>
  <button className="emu-btn" disabled={!drawBounds} onClick={handleInit}>
    Init Grid {drawBounds ? `(${cellSizeM}m)` : '— draw first'}
  </button>
  <input
    type="number" min={10} max={100} value={cellSizeM}
    onChange={e => setCellSizeM(Number(e.target.value))}
    className="emu-cell-size-input"
    title="Cell size (m)"
  />
  {gridState?.initialized && (
    <span className="emu-grid-info">
      {gridState.n_rows}×{gridState.n_cols} cells · Mode: {gridState.mode}
    </span>
  )}
  {recommendation && (
    <span className="emu-rec-info">
      Rec → Cell {recommendation.target_cell_id} · {recommendation.distance_m.toFixed(0)}m · {recommendation.reason}
    </span>
  )}
</div>
```

---

### Task B3 — `EmulatorPage.css`

```css
.emu-page { display: flex; flex-direction: column; height: 100%; background: #0f172a; color: #f1f5f9; }

.emu-topbar {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 14px; background: #1e293b; border-bottom: 1px solid #334155;
  flex-shrink: 0; flex-wrap: wrap;
}
.emu-title { font-weight: 700; font-size: 14px; color: #93c5fd; margin-right: 6px; }
.emu-grid-info { font-size: 12px; color: #64748b; }
.emu-rec-info { font-size: 12px; color: #94a3b8; font-style: italic; }
.emu-cell-size-input {
  width: 54px; padding: 3px 6px; border-radius: 4px;
  background: #0f172a; border: 1px solid #475569; color: #f1f5f9; font-size: 13px;
}

.emu-body { display: flex; flex: 1; min-height: 0; overflow: hidden; }

.emu-sidebar {
  width: 240px; min-width: 200px; flex-shrink: 0;
  overflow-y: auto; padding: 12px 10px; display: flex; flex-direction: column; gap: 14px;
  border-right: 1px solid #1e293b; background: #0f172a;
}
.emu-map-area { flex: 1; min-width: 0; }

.emu-control-group { display: flex; flex-direction: column; gap: 5px; }
.emu-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: #475569; }

.emu-btn-row { display: flex; gap: 4px; flex-wrap: wrap; }
.emu-btn {
  padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; cursor: pointer;
  background: #1e293b; border: 1px solid #334155; color: #94a3b8;
}
.emu-btn:hover { background: #334155; color: #f1f5f9; }
.emu-btn-active { background: #2563eb !important; border-color: #3b82f6 !important; color: #fff !important; }
.emu-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.emu-toggle {
  padding: 5px 14px; border-radius: 4px; font-size: 12px; font-weight: 700; cursor: pointer;
  background: #1e293b; border: 1px solid #334155; color: #94a3b8; align-self: flex-start;
}
.emu-toggle-on { background: #14532d; border-color: #16a34a; color: #86efac; }

.emu-slider { width: 100%; accent-color: #3b82f6; }
.emu-slider-labels { display: flex; justify-content: space-between; font-size: 10px; color: #475569; margin-top: -2px; }

.emu-stat-row {
  display: flex; justify-content: space-between;
  font-size: 12px; padding: 2px 0; border-bottom: 1px solid #1e293b;
}
.emu-stat-row span:first-child { color: #64748b; }
.emu-stat-row span:last-child { color: #f1f5f9; font-weight: 600; font-family: monospace; }

.emu-drone-hint { font-size: 11px; color: #334155; font-style: italic; }
```

---

### Task B4 — Update `App.tsx`

Add import and route:

```tsx
import EmulatorPage from './pages/EmulatorPage'
// inside <Route element={<AppShell />}>:
<Route path="/emulator" element={<EmulatorPage />} />
```

---

### Acceptance (Worker B)

- [ ] `/emulator` route renders without TypeScript errors
- [ ] Clicking on map moves the drone blue dot
- [ ] Draw Boundary captures two clicks and draws an orange rectangle
- [ ] Init Grid button calls `/api/guidance/init` with drawBounds
- [ ] Grid overlay renders cells colored by `display_score ?? evidence_score`
- [ ] Cell tooltips show E / fresh / U / H / C / J
- [ ] Pose timer fires at selected rate and posts POSE packets
- [ ] Evidence timer fires at selected interval when toggled ON
- [ ] RSSI / frames / ratio sliders update packet parameters immediately
- [ ] Stats count POSE and EVIDENCE sent
- [ ] Drone cell panel shows live scores for current cell
- [ ] Reset clears grid and stops all timers
- [ ] `npm run build` passes

---

## Supervisor — Integration

After both workers complete:

1. Verify `backend/app/api/guidance.py` has a `POST /api/guidance/update` endpoint that calls `get_engine().ingest(packet)`. If it is missing, add it:

```python
@router.post("/update")
async def update_guidance(request: Request) -> dict:
    body = await request.json()
    get_engine().ingest(body)
    return {"ok": True}
```

(Use `from fastapi import Request` — no Pydantic model needed here since the packet schema is open.)

2. Run:
```bash
cd backend && python -m pytest tests/unit/ -x -q
cd frontend && npm.cmd run build
```

3. Report in `.ai/codex_result.md`.

---

## Tests to Run

```bash
cd backend && python -m pytest tests/unit/ -q          # must be 128+ passed
cd frontend && npm.cmd run build                         # must pass
```
