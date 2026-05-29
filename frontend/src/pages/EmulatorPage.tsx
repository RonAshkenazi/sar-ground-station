import { useEffect, useMemo, useRef, useState } from 'react'
import { CircleMarker, MapContainer, Polyline, Rectangle, TileLayer, Tooltip, useMapEvents } from 'react-leaflet'
import {
  getGuidanceGrid,
  getGuidanceRecommendation,
  ingestGuidancePacket,
  initGuidance,
  resetGuidance,
  type GridCell,
  type GuidanceGridState,
  type GuidanceRecommendation,
} from '../api/airunit'
import './EmulatorPage.css'

type Point = [number, number]
type PoseRate = 0 | 0.5 | 1 | 2

const DEFAULT_CENTER: Point = [31.5, 34.8]

// Geometry -------------------------------------------------------------------
function _haversineM(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6_371_000
  const phi1 = (lat1 * Math.PI) / 180
  const phi2 = (lat2 * Math.PI) / 180
  const dPhi = ((lat2 - lat1) * Math.PI) / 180
  const dLambda = ((lon2 - lon1) * Math.PI) / 180
  const a = Math.sin(dPhi / 2) ** 2 + Math.cos(phi1) * Math.cos(phi2) * Math.sin(dLambda / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(a))
}

function _bearingDeg(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const phi1 = (lat1 * Math.PI) / 180
  const phi2 = (lat2 * Math.PI) / 180
  const dLambda = ((lon2 - lon1) * Math.PI) / 180
  const x = Math.sin(dLambda) * Math.cos(phi2)
  const y = Math.cos(phi1) * Math.sin(phi2) - Math.sin(phi1) * Math.cos(phi2) * Math.cos(dLambda)
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
  const u = Math.random() || 1e-10
  const v = Math.random() || 1e-10
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v)
}

function _simRssi(
  dLat: number,
  dLon: number,
  tLat: number,
  tLon: number,
  altM: number,
  rssiAt1m: number,
  n: number,
  noiseStd: number
): number {
  const horiz = _haversineM(dLat, dLon, tLat, tLon)
  const dist = Math.max(1, Math.sqrt(horiz ** 2 + altM ** 2))
  const mean = rssiAt1m - 10 * n * Math.log10(dist)
  return Math.max(-100, Math.min(-30, mean + _gauss() * noiseStd))
}

function _sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export default function EmulatorPage() {
  const [dronePos, setDronePos] = useState<Point | null>(null)
  const [clickMode, setClickMode] = useState<'drone' | 'draw' | 'target'>('drone')
  const [drawCorner1, setDrawCorner1] = useState<Point | null>(null)
  const [drawCorner2, setDrawCorner2] = useState<Point | null>(null)
  const [gridInitialized, setGridInitialized] = useState(false)
  const [cellSizeM, setCellSizeM] = useState(5)
  const [gridState, setGridState] = useState<GuidanceGridState | null>(null)
  const [recommendation, setRecommendation] = useState<GuidanceRecommendation | null>(null)
  const [poseRate, setPoseRate] = useState<PoseRate>(1)
  const [evidenceOn, setEvidenceOn] = useState(true)
  const [evidenceInterval, setEvidenceInterval] = useState(3)
  const [rssiP95, setRssiP95] = useState(-65)
  const [framesTotal, setFramesTotal] = useState(20)
  const [strongRatio, setStrongRatio] = useState(0.4)
  const [poseSent, setPoseSent] = useState(0)
  const [evidenceSent, setEvidenceSent] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [targetPos, setTargetPos] = useState<Point | null>(null)
  const [simMode, setSimMode] = useState<'lawnmower' | 'adaptive' | 'both'>('both')
  const [simRunning, setSimRunning] = useState(false)
  const [simPhase, setSimPhase] = useState<'idle' | 'lawnmower' | 'adaptive' | 'done'>('idle')
  const [simProgress, setSimProgress] = useState({ done: 0, total: 0 })
  const [speedMps, setSpeedMps] = useState(8)
  const [altitudeM, setAltitudeM] = useState(10)
  const [rssiAt1m, setRssiAt1m] = useState(-35)
  const [pathLossN, setPathLossN] = useState(2.8)
  const [noiseStd, setNoiseStd] = useState(4)
  const [strongThrDbm, setStrongThrDbm] = useState(-65)
  const [adaptiveDurationS, setAdaptiveDurationS] = useState(300)
  const simStopRef = useRef(false)

  const rssiMax = rssiP95 + 7
  const framesStrong = Math.round(framesTotal * strongRatio)
  const drawBounds = useMemo(() => {
    if (!drawCorner1 || !drawCorner2) return null
    return {
      min_lat: Math.min(drawCorner1[0], drawCorner2[0]),
      max_lat: Math.max(drawCorner1[0], drawCorner2[0]),
      min_lon: Math.min(drawCorner1[1], drawCorner2[1]),
      max_lon: Math.max(drawCorner1[1], drawCorner2[1]),
    }
  }, [drawCorner1, drawCorner2])
  const gridCells = useMemo(() => buildGridCells(gridState), [gridState])
  const droneCell = useMemo(() => closestCell(gridState, dronePos), [gridState, dronePos])

  useEffect(() => {
    if (poseRate === 0 || !gridInitialized || !dronePos || simRunning) return
    const interval = window.setInterval(async () => {
      try {
        await ingestGuidancePacket({
          type: 'POSE',
          lat: dronePos[0],
          lon: dronePos[1],
          gps_valid: true,
          sniffer_alive: true,
        })
        setPoseSent((n) => n + 1)
      } catch (err) {
        setError(String(err))
      }
    }, 1000 / poseRate)
    return () => window.clearInterval(interval)
  }, [poseRate, gridInitialized, dronePos, simRunning])

  useEffect(() => {
    if (!evidenceOn || !gridInitialized || !dronePos || simRunning) return
    const interval = window.setInterval(async () => {
      try {
        await ingestGuidancePacket({
          type: 'EVIDENCE',
          lat: dronePos[0],
          lon: dronePos[1],
          dwell_ms: evidenceInterval * 1000,
          frames_total: framesTotal,
          frames_strong: framesStrong,
          rssi_max_dbm: rssiMax,
          rssi_p95_dbm: rssiP95,
          rssi_mean_dbm: rssiP95 - 5,
        })
        setEvidenceSent((n) => n + 1)
      } catch (err) {
        setError(String(err))
      }
    }, evidenceInterval * 1000)
    return () => window.clearInterval(interval)
  }, [evidenceOn, gridInitialized, dronePos, evidenceInterval, framesTotal, framesStrong, rssiMax, rssiP95, simRunning])

  useEffect(() => {
    return () => {
      simStopRef.current = true
    }
  }, [])

  useEffect(() => {
    if (!gridInitialized) return
    let cancelled = false
    async function poll() {
      try {
        const grid = await getGuidanceGrid()
        if (cancelled) return
        setGridState(grid)
        if (grid.initialized) {
          const rec = await getGuidanceRecommendation()
          if (!cancelled) setRecommendation('available' in rec && rec.available ? rec : null)
        }
      } catch (err) {
        if (!cancelled) setError(String(err))
      }
    }
    void poll()
    const interval = window.setInterval(poll, 2000)
    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [gridInitialized])

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
    if (!simRunning) setDronePos(next)
  }

  async function handleInit() {
    if (!drawBounds) return
    try {
      await resetGuidance()
      await initGuidance(drawBounds, cellSizeM)
      setGridState(await getGuidanceGrid())
      setGridInitialized(true)
      setRecommendation(null)
      setPoseSent(0)
      setEvidenceSent(0)
      setError(null)
    } catch (err) {
      setError(String(err))
    }
  }

  async function handleReset() {
    try {
      await resetGuidance()
      setGridInitialized(false)
      setGridState(null)
      setRecommendation(null)
      setPoseSent(0)
      setEvidenceSent(0)
      setError(null)
    } catch (err) {
      setError(String(err))
    }
  }

  async function runSimulation() {
    if (!drawBounds || !targetPos || !gridInitialized) return

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

    const { min_lat, max_lat, min_lon, max_lon } = cfg.bounds
    const latSpanM = _haversineM(min_lat, min_lon, max_lat, min_lon)
    const lonSpanM = _haversineM(min_lat, min_lon, min_lat, max_lon)
    const nRows = Math.max(1, Math.ceil(latSpanM / cfg.cellSize))
    const nCols = Math.max(1, Math.ceil(lonSpanM / cfg.cellSize))
    const latStep = (max_lat - min_lat) / nRows
    const lonStep = (max_lon - min_lon) / nCols
    const TICK = 250

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
        type: 'POSE',
        lat: drone[0],
        lon: drone[1],
        gps_valid: true,
        sniffer_alive: true,
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
        lat: drone[0],
        lon: drone[1],
        dwell_ms: 2000,
        win_ms: 2000,
        frames_total: rssiBuf.length,
        frames_strong: nStrong,
        rssi_max_dbm: Math.max(...rssiBuf),
        rssi_p95_dbm: p95,
        rssi_mean_dbm: mean,
      }).catch(() => {})
      setEvidenceSent((n) => n + 1)
      rssiBuf = []
    }

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

            const rssi = _simRssi(
              drone[0],
              drone[1],
              cfg.target[0],
              cfg.target[1],
              cfg.alt,
              cfg.rssiAt1m,
              cfg.n,
              cfg.noise
            )
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

    if ((cfg.mode === 'adaptive' || cfg.mode === 'both') && !simStopRef.current) {
      setSimPhase('adaptive')
      if (cfg.mode === 'both') await _sleep(1000)

      let elapsed = 0
      let recPollMs = 0
      let recTarget: Point = drone

      while (elapsed < cfg.adaptiveDuration && !simStopRef.current) {
        recPollMs += TICK
        elapsed += TICK

        if (recPollMs >= 1000) {
          recPollMs = 0
          try {
            const rec = await getGuidanceRecommendation()
            if ('available' in rec && rec.available) {
              recTarget = [rec.target_lat, rec.target_lon]
            }
          } catch {
            // Ignore transient recommendation failures during simulation.
          }
        }

        const dist = _haversineM(drone[0], drone[1], recTarget[0], recTarget[1])
        if (dist > 1) {
          const bear = _bearingDeg(drone[0], drone[1], recTarget[0], recTarget[1])
          const step = Math.min((cfg.speed * TICK) / 1000, dist)
          drone = _movePt(drone[0], drone[1], bear, step)
          setDronePos([...drone])
        }

        const rssi = _simRssi(
          drone[0],
          drone[1],
          cfg.target[0],
          cfg.target[1],
          cfg.alt,
          cfg.rssiAt1m,
          cfg.n,
          cfg.noise
        )
        tick(rssi)
        await flushPose()
        await flushEvidence()
        await _sleep(TICK)
      }
    }

    if (rssiBuf.length > 0) await flushEvidence()

    simStopRef.current = false
    setSimRunning(false)
    setSimPhase('done')
  }

  return (
    <div className="emu-page">
      <div className="emu-topbar">
        <span className="emu-title">Simulator</span>
        <button
          className={`emu-btn ${clickMode === 'draw' ? 'emu-btn-active' : ''}`}
          onClick={() => setClickMode((m) => (m === 'draw' ? 'drone' : 'draw'))}
        >
          {clickMode === 'draw' ? 'Click 2nd corner...' : 'Draw Boundary'}
        </button>
        <button
          className={`emu-btn ${clickMode === 'target' ? 'emu-btn-active' : ''}`}
          onClick={() => setClickMode((m) => (m === 'target' ? 'drone' : 'target'))}
          title="Click on the map to place the virtual RF target"
        >
          {clickMode === 'target' ? 'Click to place target...' : 'Set Target'}
        </button>
        <button className="emu-btn" onClick={handleReset} disabled={simRunning}>Reset</button>
        <button className="emu-btn" disabled={!drawBounds || simRunning} onClick={handleInit}>
          Init Grid {drawBounds ? `(${cellSizeM}m)` : '- draw first'}
        </button>
        <input
          type="number"
          min={2}
          max={50}
          value={cellSizeM}
          onChange={(event) => setCellSizeM(Number(event.target.value))}
          className="emu-cell-size-input"
          title="Cell size (m)"
          disabled={simRunning}
        />
        {!simRunning ? (
          <button
            className="emu-btn emu-btn-start"
            disabled={!gridInitialized || !targetPos}
            onClick={() => { void runSimulation() }}
            title={!targetPos ? 'Place a target first' : !gridInitialized ? 'Init grid first' : ''}
          >
            Start Sim
          </button>
        ) : (
          <button
            className="emu-btn emu-btn-stop"
            onClick={() => {
              simStopRef.current = true
              setSimRunning(false)
              setSimPhase('idle')
            }}
          >
            Stop
          </button>
        )}
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
            {gridState.n_rows}x{gridState.n_cols} - {gridState.mode}
          </span>
        )}
        {recommendation && (
          <span className="emu-rec-info">
            Cell {recommendation.target_cell_id} - {recommendation.distance_m.toFixed(0)}m - {recommendation.reason}
          </span>
        )}
        {error && <span className="emu-error">{error}</span>}
      </div>

      <div className="emu-body">
        <aside className="emu-sidebar">
          <div className="emu-sim-section">
            <div className="emu-label">Simulator Mode</div>
            <div className="emu-btn-row">
              {(['lawnmower', 'adaptive', 'both'] as const).map((mode) => (
                <button
                  key={mode}
                  className={`emu-btn ${simMode === mode ? 'emu-btn-active' : ''}`}
                  onClick={() => setSimMode(mode)}
                  disabled={simRunning}
                >
                  {mode === 'lawnmower' ? 'Lawn' : mode === 'adaptive' ? 'Adapt' : 'Both'}
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
            <Slider label={`Noise std: ${noiseStd} dB`} min={1} max={12} step={1} value={noiseStd} onChange={setNoiseStd} disabled={simRunning} />
            <Slider label={`Strong >= ${strongThrDbm} dBm`} min={-80} max={-55} step={1} value={strongThrDbm} onChange={setStrongThrDbm} disabled={simRunning} />
            <Slider label={`Adaptive: ${adaptiveDurationS}s`} min={30} max={600} step={30} value={adaptiveDurationS} onChange={setAdaptiveDurationS} disabled={simRunning} />

            <div className="emu-sim-divider" />
          </div>
          <div className="emu-control-group">
            <div className="emu-label">Drone</div>
            <div className="emu-stat-row"><span>lat</span><span>{dronePos ? dronePos[0].toFixed(6) : '-'}</span></div>
            <div className="emu-stat-row"><span>lon</span><span>{dronePos ? dronePos[1].toFixed(6) : '-'}</span></div>
            <div className="emu-drone-hint">Click the map to move the drone.</div>
          </div>
          <div className="emu-control-group">
            <div className="emu-label">Pose Rate</div>
            <div className="emu-btn-row">
              {([0, 0.5, 1, 2] as const).map((rate) => (
                <button key={rate} className={`emu-btn ${poseRate === rate ? 'emu-btn-active' : ''}`} onClick={() => setPoseRate(rate)}>
                  {rate === 0 ? 'Off' : `${rate}Hz`}
                </button>
              ))}
            </div>
          </div>
          <div className="emu-control-group">
            <div className="emu-label">Evidence</div>
            <button className={`emu-toggle ${evidenceOn ? 'emu-toggle-on' : ''}`} onClick={() => setEvidenceOn((v) => !v)}>
              {evidenceOn ? 'ON' : 'OFF'}
            </button>
            <div className="emu-label emu-gap-top">Interval</div>
            <div className="emu-btn-row">
              {[2, 3, 5, 10].map((seconds) => (
                <button key={seconds} className={`emu-btn ${evidenceInterval === seconds ? 'emu-btn-active' : ''}`} onClick={() => setEvidenceInterval(seconds)}>
                  {seconds}s
                </button>
              ))}
            </div>
          </div>
          <Slider label={`RSSI p95: ${rssiP95} dBm`} min={-90} max={-55} step={1} value={rssiP95} onChange={setRssiP95} />
          <Slider label={`Frames total: ${framesTotal}`} min={1} max={50} step={1} value={framesTotal} onChange={setFramesTotal} />
          <Slider label={`Strong ratio: ${Math.round(strongRatio * 100)}%`} min={0} max={1} step={0.05} value={strongRatio} onChange={setStrongRatio} />
          <div className="emu-control-group">
            <div className="emu-label">Stats</div>
            <div className="emu-stat-row"><span>POSE sent</span><span>{poseSent}</span></div>
            <div className="emu-stat-row"><span>EV sent</span><span>{evidenceSent}</span></div>
          </div>
          {droneCell && (
            <div className="emu-control-group">
              <div className="emu-label">Last Cell {droneCell.cell_id}</div>
              <ScoreRows cell={droneCell} />
            </div>
          )}
        </aside>
        <main className="emu-map-area">
          <MapContainer center={DEFAULT_CENTER} zoom={16} maxZoom={20} className="emu-map">
            <TileLayer
              attribution="Tiles &copy; Esri"
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            />
            <MapClickHandler onMapClick={handleMapClick} />
            {drawBounds && (
              <Rectangle
                bounds={[[drawBounds.min_lat, drawBounds.min_lon], [drawBounds.max_lat, drawBounds.max_lon]]}
                pathOptions={{ color: '#f97316', dashArray: '8 5', fillOpacity: 0.04, weight: 2 }}
              />
            )}
            {gridCells.map(({ cell, bounds }) => {
              const isTarget = cell.cell_id === recommendation?.target_cell_id
              return (
                <Rectangle
                  key={cell.cell_id}
                  bounds={bounds}
                  pathOptions={{
                    color: isTarget ? '#ffffff' : cellColor(cell),
                    fillColor: cellColor(cell),
                    fillOpacity: isTarget ? 0.52 : 0.36,
                    opacity: isTarget ? 0.95 : 0.78,
                    weight: isTarget ? 2 : 0.5,
                  }}
                >
                  <Tooltip sticky>
                    <div className="emu-tooltip">
                      <div>Cell {cell.cell_id}</div>
                      <ScoreRows cell={cell} />
                    </div>
                  </Tooltip>
                </Rectangle>
              )
            })}
            {dronePos && (
              <CircleMarker
                center={dronePos}
                radius={10}
                pathOptions={{ color: '#fff', fillColor: '#3b82f6', fillOpacity: 1, weight: 2 }}
              />
            )}
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
            {dronePos && recommendation && (
              <Polyline
                positions={[dronePos, [recommendation.target_lat, recommendation.target_lon]]}
                pathOptions={{ color: '#facc15', weight: 2, dashArray: '8 4' }}
              />
            )}
          </MapContainer>
        </main>
      </div>
    </div>
  )
}

function Slider({ label, min, max, step, value, onChange, disabled = false }: {
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
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="emu-slider"
        disabled={disabled}
      />
      <div className="emu-slider-labels"><span>{min}</span><span>{max}</span></div>
    </div>
  )
}

function ScoreRows({ cell }: { cell: GridCell }) {
  return (
    <>
      <div className="emu-stat-row"><span>E</span><span>{cell.evidence_score.toFixed(3)}</span></div>
      <div className="emu-stat-row"><span>fresh</span><span>{(cell.display_score ?? 0).toFixed(3)}</span></div>
      <div className="emu-stat-row"><span>U</span><span>{cell.uncertainty_score.toFixed(3)}</span></div>
      <div className="emu-stat-row"><span>H</span><span>{(cell.spatial_entropy ?? 1).toFixed(2)}</span></div>
      <div className="emu-stat-row"><span>C</span><span>{(cell.spatial_certainty ?? 0).toFixed(2)}</span></div>
      <div className="emu-stat-row"><span>J</span><span>{cell.final_score.toFixed(3)}</span></div>
    </>
  )
}

function MapClickHandler({ onMapClick }: { onMapClick: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(event) {
      onMapClick(event.latlng.lat, event.latlng.lng)
    },
  })
  return null
}

function buildGridCells(gridState: GuidanceGridState | null) {
  if (!gridState?.bounds || !gridState.n_rows || !gridState.n_cols) return []
  const latStep = (gridState.bounds.max_lat - gridState.bounds.min_lat) / gridState.n_rows
  const lonStep = (gridState.bounds.max_lon - gridState.bounds.min_lon) / gridState.n_cols
  return gridState.cells.map((cell) => ({
    cell,
    bounds: [
      [cell.center_lat - latStep / 2, cell.center_lon - lonStep / 2],
      [cell.center_lat + latStep / 2, cell.center_lon + lonStep / 2],
    ] as [[number, number], [number, number]],
  }))
}

function closestCell(gridState: GuidanceGridState | null, dronePos: Point | null) {
  if (!gridState?.cells || !dronePos) return null
  let best: GridCell | null = null
  let bestDist = Infinity
  for (const cell of gridState.cells) {
    const dist = Math.hypot(cell.center_lat - dronePos[0], cell.center_lon - dronePos[1])
    if (dist < bestDist) {
      best = cell
      bestDist = dist
    }
  }
  return best
}

function cellColor(cell: GridCell): string {
  const score = cell.display_score ?? cell.evidence_score ?? 0
  if (score >= 0.6) return '#16a34a'
  if (score >= 0.3) return '#ca8a04'
  if (score >= 0.1) return '#ea580c'
  if (score > 0.01) return '#dc2626'
  return '#374151'
}
