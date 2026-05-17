# Codex Handoff — Sprint 06: Simulator Auto-Flight

## Requested Role

[SUPERVISOR → single Worker, then verify build]

---

## Context

`EmulatorPage` already exists at `/emulator`. It has:
- Leaflet map with grid overlay, drone marker, recommendation arrow
- Manual drone placement (click on map)
- Manual packet injection (pose rate buttons, evidence sliders)
- Draw boundary → init grid
- Cell score tooltips

What is MISSING — and what this sprint adds:

1. **Auto-flight simulation** — the drone moves by itself:
   - **Lawnmower mode**: sweeps the grid in boustrophedon rows
   - **Adaptive mode**: polls the recommendation endpoint every 3s and flies toward the target cell
   - **Both**: lawnmower first, then adaptive
2. **Virtual RF target** — a configurable lat/lon representing the "person". The simulator
   computes realistic RSSI from drone-to-target distance using the log-distance path loss model
   plus Gaussian noise.
3. **Target marker** on the map (red circle).
4. **Simulator controls** in the sidebar: mode, speed, target config, start/stop, progress.
5. Page title updated from "Guidance Emulator" → **"Simulator"**.

All geometry runs in the browser. No new API endpoints. The sim loop calls the existing
`ingestGuidancePacket` and `getGuidanceRecommendation` wrappers.

---

## Files to modify

```
frontend/src/pages/EmulatorPage.tsx
frontend/src/pages/EmulatorPage.css
```

## Must NOT touch

- Any backend file
- Any other frontend file

---

# WORKER — EmulatorPage Simulator

## Task 1 — Pure utility functions (add OUTSIDE the component, near the top of the file)

Add these before the `export default function EmulatorPage()` line. They are pure math helpers used by the sim loop.

```typescript
// ── Geometry ──────────────────────────────────────────────────────────────────

function _haversineM(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6_371_000
  const φ1 = (lat1 * Math.PI) / 180, φ2 = (lat2 * Math.PI) / 180
  const dφ = ((lat2 - lat1) * Math.PI) / 180
  const dλ = ((lon2 - lon1) * Math.PI) / 180
  const a = Math.sin(dφ / 2) ** 2 + Math.cos(φ1) * Math.cos(φ2) * Math.sin(dλ / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(a))
}

function _bearingDeg(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const φ1 = (lat1 * Math.PI) / 180, φ2 = (lat2 * Math.PI) / 180
  const dλ = ((lon2 - lon1) * Math.PI) / 180
  const x = Math.sin(dλ) * Math.cos(φ2)
  const y = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(dλ)
  return ((Math.atan2(x, y) * 180) / Math.PI + 360) % 360
}

function _movePt(lat: number, lon: number, bearingDeg: number, distM: number): Point {
  const R = 6_371_000
  const ang = distM / R
  const br = (bearingDeg * Math.PI) / 180
  const la1 = (lat * Math.PI) / 180
  const lo1 = (lon * Math.PI) / 180
  const la2 = Math.asin(
    Math.sin(la1) * Math.cos(ang) + Math.cos(la1) * Math.sin(ang) * Math.cos(br)
  )
  const lo2 =
    lo1 +
    Math.atan2(
      Math.sin(br) * Math.sin(ang) * Math.cos(la1),
      Math.cos(ang) - Math.sin(la1) * Math.sin(la2)
    )
  return [(la2 * 180) / Math.PI, (lo2 * 180) / Math.PI]
}

function _gauss(): number {
  // Box-Muller
  const u = Math.random() || 1e-10, v = Math.random() || 1e-10
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v)
}

function _simRssi(
  dLat: number, dLon: number,
  tLat: number, tLon: number,
  altM: number, rssiAt1m: number, n: number, noiseStd: number
): number {
  const horiz = _haversineM(dLat, dLon, tLat, tLon)
  const dist = Math.max(1, Math.sqrt(horiz ** 2 + altM ** 2))
  const mean = rssiAt1m - 10 * n * Math.log10(dist)
  return Math.max(-100, Math.min(-30, mean + _gauss() * noiseStd))
}

function _sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}
```

---

## Task 2 — State additions inside the component

Add these new state variables and refs inside `EmulatorPage()`, alongside the existing ones.

```typescript
// ── Click mode (replaces drawMode) ───────────────────────────────────────────
const [clickMode, setClickMode] = useState<'drone' | 'draw' | 'target'>('drone')

// ── Simulator ─────────────────────────────────────────────────────────────────
const [targetPos, setTargetPos] = useState<Point | null>(null)
const [simMode, setSimMode] = useState<'lawnmower' | 'adaptive' | 'both'>('both')
const [simRunning, setSimRunning] = useState(false)
const [simPhase, setSimPhase] = useState<'idle' | 'lawnmower' | 'adaptive' | 'done'>('idle')
const [simProgress, setSimProgress] = useState({ done: 0, total: 0 })
const [speedMps, setSpeedMps] = useState(8)
const [altitudeM, setAltitudeM] = useState(30)
const [rssiAt1m, setRssiAt1m] = useState(-50)
const [pathLossN, setPathLossN] = useState(2.8)
const [noiseStd, setNoiseStd] = useState(4)
const [strongThrDbm, setStrongThrDbm] = useState(-65)
const [adaptiveDurationS, setAdaptiveDurationS] = useState(300)
const simStopRef = useRef(false)
```

**Also change the existing cell size default from 30 to 5:**
```typescript
// was: const [cellSizeM, setCellSizeM] = useState(30)
const [cellSizeM, setCellSizeM] = useState(5)
```

**Remove the existing `drawMode` state** — it is replaced by `clickMode`.

---

## Task 3 — Replace `handleMapClick`

Remove the existing `handleMapClick` function and replace with:

```typescript
function handleMapClick(lat: number, lng: number) {
  const next: Point = [lat, lng]
  if (clickMode === 'target') {
    setTargetPos(next)
    setClickMode('drone')
    return
  }
  if (clickMode === 'draw') {
    if (!drawCorner1 || drawCorner2) {
      setDrawCorner1(next)
      setDrawCorner2(null)
    } else {
      setDrawCorner2(next)
      setClickMode('drone')
    }
    return
  }
  // 'drone' mode — only allow manual placement when sim is not running
  if (!simRunning) setDronePos(next)
}
```

---

## Task 4 — Add `runSimulation` function inside the component

Add this async function inside `EmulatorPage()` (as a plain `async function`, not a `useEffect`).

```typescript
async function runSimulation() {
  if (!drawBounds || !targetPos || !gridInitialized) return

  // Capture config snapshot so mid-flight changes don't affect this run
  const cfg = {
    bounds: drawBounds,
    cellSize: cellSizeM,
    target: targetPos,
    speed: speedMps,
    alt: altitudeM,
    rssiAt1m,
    n: pathLossN,
    noise: noiseStd,
    strongThr: strongThrDbm,
    mode: simMode,
    adaptiveDuration: adaptiveDurationS * 1000,
  }

  simStopRef.current = false
  setSimRunning(true)
  setSimPhase('lawnmower')
  setSimProgress({ done: 0, total: 0 })

  // Compute grid dimensions
  const { min_lat, max_lat, min_lon, max_lon } = cfg.bounds
  const latSpanM = _haversineM(min_lat, min_lon, max_lat, min_lon)
  const lonSpanM = _haversineM(min_lat, min_lon, min_lat, max_lon)
  const nRows = Math.max(1, Math.ceil(latSpanM / cfg.cellSize))
  const nCols = Math.max(1, Math.ceil(lonSpanM / cfg.cellSize))
  const latStep = (max_lat - min_lat) / nRows
  const lonStep = (max_lon - min_lon) / nCols
  const TICK = 250 // ms per step

  let drone: Point = [(min_lat + max_lat) / 2, (min_lon + max_lon) / 2]
  setDronePos([...drone])

  let rssiBuf: number[] = []
  let poseMs = 0
  let evMs = 0

  function tick(rssi: number) {
    rssiBuf.push(rssi)
    poseMs += TICK
    evMs += TICK
  }

  async function flushPose() {
    if (poseMs < 500) return
    poseMs = 0
    await ingestGuidancePacket({
      type: 'POSE', lat: drone[0], lon: drone[1],
      gps_valid: true, sniffer_alive: true,
    }).catch(() => {})
    setPoseSent((n) => n + 1)
  }

  async function flushEvidence() {
    if (evMs < 2000 || rssiBuf.length === 0) return
    evMs = 0
    const sorted = [...rssiBuf].sort((a, b) => a - b)
    const p95 = sorted[Math.max(0, Math.floor(0.95 * sorted.length) - 1)]
    const nStrong = rssiBuf.filter((r) => r >= cfg.strongThr).length
    const mean = rssiBuf.reduce((s, r) => s + r, 0) / rssiBuf.length
    await ingestGuidancePacket({
      type: 'EVIDENCE',
      lat: drone[0], lon: drone[1],
      dwell_ms: 2000, win_ms: 2000,
      frames_total: rssiBuf.length,
      frames_strong: nStrong,
      rssi_max_dbm: Math.max(...rssiBuf),
      rssi_p95_dbm: p95,
      rssi_mean_dbm: mean,
    }).catch(() => {})
    setEvidenceSent((n) => n + 1)
    rssiBuf = []
  }

  // ── Lawnmower phase ──────────────────────────────────────────────────────
  if (cfg.mode === 'lawnmower' || cfg.mode === 'both') {
    const totalWP = nRows * nCols
    setSimProgress({ done: 0, total: totalWP })
    let wpDone = 0

    for (let row = 0; row < nRows; row++) {
      if (simStopRef.current) break
      const rowLat = min_lat + (row + 0.5) * latStep
      const cols =
        row % 2 === 0
          ? Array.from({ length: nCols }, (_, i) => i)
          : Array.from({ length: nCols }, (_, i) => nCols - 1 - i)

      for (const col of cols) {
        if (simStopRef.current) break
        const wpLon = min_lon + (col + 0.5) * lonStep

        while (!simStopRef.current) {
          const dist = _haversineM(drone[0], drone[1], rowLat, wpLon)
          if (dist < cfg.cellSize * 0.4) break
          const bear = _bearingDeg(drone[0], drone[1], rowLat, wpLon)
          const step = Math.min((cfg.speed * TICK) / 1000, dist)
          drone = _movePt(drone[0], drone[1], bear, step)
          setDronePos([...drone])

          const rssi = _simRssi(drone[0], drone[1], cfg.target[0], cfg.target[1], cfg.alt, cfg.rssiAt1m, cfg.n, cfg.noise)
          tick(rssi)
          await flushPose()
          await flushEvidence()
          await _sleep(TICK)
        }
        wpDone++
        setSimProgress({ done: wpDone, total: totalWP })
      }
    }
  }

  // ── Adaptive phase ───────────────────────────────────────────────────────
  if ((cfg.mode === 'adaptive' || cfg.mode === 'both') && !simStopRef.current) {
    setSimPhase('adaptive')
    if (cfg.mode === 'both') await _sleep(1000)

    let elapsed = 0
    let recPollMs = 0
    let recTarget: Point = drone

    while (elapsed < cfg.adaptiveDuration && !simStopRef.current) {
      recPollMs += TICK
      elapsed += TICK

      if (recPollMs >= 3000) {
        recPollMs = 0
        try {
          const rec = await getGuidanceRecommendation()
          if ('available' in rec && rec.available) {
            recTarget = [rec.target_lat, rec.target_lon]
          }
        } catch { /* ignore */ }
      }

      const dist = _haversineM(drone[0], drone[1], recTarget[0], recTarget[1])
      if (dist > 1) {
        const bear = _bearingDeg(drone[0], drone[1], recTarget[0], recTarget[1])
        const step = Math.min((cfg.speed * TICK) / 1000, dist)
        drone = _movePt(drone[0], drone[1], bear, step)
        setDronePos([...drone])
      }

      const rssi = _simRssi(drone[0], drone[1], cfg.target[0], cfg.target[1], cfg.alt, cfg.rssiAt1m, cfg.n, cfg.noise)
      tick(rssi)
      await flushPose()
      await flushEvidence()
      await _sleep(TICK)
    }
  }

  // Final flush
  if (rssiBuf.length > 0) await flushEvidence()

  simStopRef.current = false
  setSimRunning(false)
  setSimPhase('done')
}
```

---

## Task 5 — Add cleanup useEffect

Add this `useEffect` alongside the existing ones (order doesn't matter):

```typescript
useEffect(() => {
  return () => {
    simStopRef.current = true
  }
}, [])
```

---

## Task 6 — Guard existing pose/evidence effects

The existing two `useEffect` hooks that send POSE and EVIDENCE packets at intervals should
be disabled when the simulator is running (to avoid double-sending).

Find the two existing effects that check `poseRate === 0 || !gridInitialized || !dronePos`
and `!evidenceOn || !gridInitialized || !dronePos`. Add `|| simRunning` to each guard:

```typescript
// Pose effect — change guard
if (poseRate === 0 || !gridInitialized || !dronePos || simRunning) return

// Evidence effect — change guard
if (!evidenceOn || !gridInitialized || !dronePos || simRunning) return
```

---

## Task 7 — Update the topbar

Replace the existing topbar content with the updated version below.
Key changes:
- Title changes to "Simulator"
- `drawMode` state replaced by `clickMode`
- New "Set Target" button
- New "Start Sim" / "Stop" buttons

```tsx
<div className="emu-topbar">
  <span className="emu-title">Simulator</span>

  {/* Boundary drawing */}
  <button
    className={`emu-btn ${clickMode === 'draw' ? 'emu-btn-active' : ''}`}
    onClick={() => setClickMode((m) => (m === 'draw' ? 'drone' : 'draw'))}
  >
    {clickMode === 'draw' ? 'Click 2nd corner…' : 'Draw Boundary'}
  </button>

  {/* Target placement */}
  <button
    className={`emu-btn ${clickMode === 'target' ? 'emu-btn-active' : ''}`}
    onClick={() => setClickMode((m) => (m === 'target' ? 'drone' : 'target'))}
    title="Click on the map to place the virtual RF target (the 'person')"
  >
    {clickMode === 'target' ? 'Click to place target…' : 'Set Target'}
  </button>

  <button className="emu-btn" onClick={handleReset} disabled={simRunning}>
    Reset
  </button>

  <button
    className="emu-btn"
    disabled={!drawBounds || simRunning}
    onClick={handleInit}
  >
    Init Grid {drawBounds ? `(${cellSizeM}m)` : '– draw first'}
  </button>

  <input
    type="number"
    min={2}
    max={50}
    value={cellSizeM}
    onChange={(e) => setCellSizeM(Number(e.target.value))}
    className="emu-cell-size-input"
    title="Cell size (m)"
    disabled={simRunning}
  />

  {/* Sim start/stop */}
  {!simRunning ? (
    <button
      className="emu-btn emu-btn-start"
      disabled={!gridInitialized || !targetPos}
      onClick={() => { void runSimulation() }}
      title={!targetPos ? 'Place a target first' : !gridInitialized ? 'Init grid first' : ''}
    >
      ▶ Start Sim
    </button>
  ) : (
    <button
      className="emu-btn emu-btn-stop"
      onClick={() => { simStopRef.current = true; setSimRunning(false); setSimPhase('idle') }}
    >
      ■ Stop
    </button>
  )}

  {/* Status chips */}
  {simRunning && (
    <span className="emu-sim-chip">
      {simPhase.toUpperCase()}
      {simPhase === 'lawnmower' && simProgress.total > 0
        ? ` ${simProgress.done}/${simProgress.total}`
        : ''}
    </span>
  )}
  {gridState?.initialized && (
    <span className="emu-grid-info">
      {gridState.n_rows}×{gridState.n_cols} · {gridState.mode}
    </span>
  )}
  {recommendation && (
    <span className="emu-rec-info">
      Cell {recommendation.target_cell_id} · {recommendation.distance_m.toFixed(0)}m · {recommendation.reason}
    </span>
  )}
  {error && <span className="emu-error">{error}</span>}
</div>
```

---

## Task 8 — Add Simulator section to sidebar

Add a new `<div className="emu-sim-section">` block inside `<aside className="emu-sidebar">`,
**before** the existing manual controls. Insert it right after the opening `<aside>` tag:

```tsx
<div className="emu-sim-section">
  <div className="emu-label">Simulator Mode</div>
  <div className="emu-btn-row">
    {(['lawnmower', 'adaptive', 'both'] as const).map((m) => (
      <button
        key={m}
        className={`emu-btn ${simMode === m ? 'emu-btn-active' : ''}`}
        onClick={() => setSimMode(m)}
        disabled={simRunning}
      >
        {m === 'lawnmower' ? 'Lawn' : m === 'adaptive' ? 'Adapt' : 'Both'}
      </button>
    ))}
  </div>

  <div className="emu-label emu-gap-top">Target</div>
  {targetPos ? (
    <div className="emu-stat-row emu-target-coords">
      <span>{targetPos[0].toFixed(5)}</span>
      <span>{targetPos[1].toFixed(5)}</span>
    </div>
  ) : (
    <div className="emu-hint">Use "Set Target" button, then click map</div>
  )}

  <Slider label={`Speed: ${speedMps} m/s`} min={1} max={20} step={1} value={speedMps} onChange={setSpeedMps} disabled={simRunning} />
  <Slider label={`Altitude: ${altitudeM} m`} min={5} max={120} step={5} value={altitudeM} onChange={setAltitudeM} disabled={simRunning} />

  <div className="emu-label emu-gap-top">RF Model</div>
  <Slider label={`RSSI@1m: ${rssiAt1m} dBm`} min={-70} max={-30} step={1} value={rssiAt1m} onChange={setRssiAt1m} disabled={simRunning} />
  <Slider label={`Path loss n: ${pathLossN}`} min={1.5} max={4.0} step={0.1} value={pathLossN} onChange={setPathLossN} disabled={simRunning} />
  <Slider label={`Noise σ: ${noiseStd} dB`} min={1} max={12} step={1} value={noiseStd} onChange={setNoiseStd} disabled={simRunning} />
  <Slider label={`Strong ≥ ${strongThrDbm} dBm`} min={-80} max={-55} step={1} value={strongThrDbm} onChange={setStrongThrDbm} disabled={simRunning} />
  <Slider label={`Adaptive: ${adaptiveDurationS}s`} min={30} max={600} step={30} value={adaptiveDurationS} onChange={setAdaptiveDurationS} disabled={simRunning} />

  <div className="emu-sim-divider" />
</div>
```

**Also update the `Slider` component** to accept an optional `disabled` prop:

```typescript
function Slider({
  label, min, max, step, value, onChange, disabled = false,
}: {
  label: string
  min: number
  max: number
  step: number
  value: number
  onChange: (value: number) => void
  disabled?: boolean
}) {
  return (
    <div className="emu-control-group">
      <div className="emu-label">{label}</div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="emu-slider"
        disabled={disabled}
      />
      <div className="emu-slider-labels"><span>{min}</span><span>{max}</span></div>
    </div>
  )
}
```

---

## Task 9 — Add target marker to map

Inside the `<MapContainer>`, after the drone `<CircleMarker>` block, add:

```tsx
{targetPos && (
  <CircleMarker
    center={targetPos}
    radius={10}
    pathOptions={{ color: '#fff', fillColor: '#ef4444', fillOpacity: 0.9, weight: 2 }}
  >
    <Tooltip permanent direction="top" offset={[0, -12]}>
      <span style={{ fontSize: 11 }}>Target</span>
    </Tooltip>
  </CircleMarker>
)}
```

---

## Task 10 — CSS additions (`EmulatorPage.css`)

Append to the end of `EmulatorPage.css`:

```css
.emu-sim-section {
  border-bottom: 1px solid #1e293b;
  padding-bottom: 12px;
  margin-bottom: 8px;
}

.emu-sim-divider {
  height: 1px;
  background: #1e293b;
  margin-top: 10px;
}

.emu-sim-chip {
  background: #1d4ed8;
  color: #bfdbfe;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.emu-btn-start {
  background: #16a34a;
  color: #fff;
  font-weight: 700;
}

.emu-btn-start:hover:not(:disabled) {
  background: #15803d;
}

.emu-btn-stop {
  background: #dc2626;
  color: #fff;
  font-weight: 700;
}

.emu-btn-stop:hover {
  background: #b91c1c;
}

.emu-btn:disabled,
.emu-slider:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.emu-hint {
  font-size: 11px;
  color: #64748b;
  font-style: italic;
  padding: 2px 0 4px;
}

.emu-target-coords {
  font-size: 11px;
  color: #fca5a5;
  font-family: monospace;
}
```

---

## Acceptance

- [ ] Page title in topbar shows "Simulator" (not "Guidance Emulator")
- [ ] "Set Target" button enters target-placement click mode; clicking the map places a red circle marker
- [ ] "Draw Boundary" still works correctly using `clickMode === 'draw'`
- [ ] Drone cannot be manually repositioned while sim is running
- [ ] "▶ Start Sim" disabled until both grid is initialized AND target is placed
- [ ] Starting sim with mode "lawnmower": drone sweeps rows automatically, grid lights up
- [ ] Starting sim with mode "adaptive": drone follows recommendation direction after each poll
- [ ] Starting sim with mode "both": lawnmower runs first, then switches to adaptive
- [ ] "■ Stop" button halts the simulation cleanly
- [ ] Grid overlay updates in real time while sim runs
- [ ] Recommendation arrow updates in real time while sim runs
- [ ] Manual pose/evidence effects do NOT fire while sim is running
- [ ] Cell size defaults to 5 (not 30)
- [ ] `cd frontend && npm.cmd run build` passes with no TypeScript errors

---

# SUPERVISOR

```bash
cd frontend && npm.cmd run build
```

Report in `.ai/codex_result.md`:
1. TypeScript errors (if any) and how resolved
2. Build output (module count, size)
3. Any deviations from the spec above
