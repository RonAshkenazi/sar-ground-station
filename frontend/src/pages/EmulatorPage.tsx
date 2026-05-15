import { useEffect, useMemo, useState } from 'react'
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

export default function EmulatorPage() {
  const [dronePos, setDronePos] = useState<Point | null>(null)
  const [drawMode, setDrawMode] = useState(false)
  const [drawCorner1, setDrawCorner1] = useState<Point | null>(null)
  const [drawCorner2, setDrawCorner2] = useState<Point | null>(null)
  const [gridInitialized, setGridInitialized] = useState(false)
  const [cellSizeM, setCellSizeM] = useState(30)
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
    if (poseRate === 0 || !gridInitialized || !dronePos) return
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
  }, [poseRate, gridInitialized, dronePos])

  useEffect(() => {
    if (!evidenceOn || !gridInitialized || !dronePos) return
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
  }, [evidenceOn, gridInitialized, dronePos, evidenceInterval, framesTotal, framesStrong, rssiMax, rssiP95])

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
    if (!drawMode) {
      setDronePos(next)
      return
    }
    if (!drawCorner1 || drawCorner2) {
      setDrawCorner1(next)
      setDrawCorner2(null)
      return
    }
    setDrawCorner2(next)
    setDrawMode(false)
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

  return (
    <div className="emu-page">
      <div className="emu-topbar">
        <span className="emu-title">Guidance Emulator</span>
        <button className={`emu-btn ${drawMode ? 'emu-btn-active' : ''}`} onClick={() => setDrawMode((v) => !v)}>
          {drawMode ? 'Click 2nd corner...' : 'Draw Boundary'}
        </button>
        <button className="emu-btn" onClick={handleReset}>Reset</button>
        <button className="emu-btn" disabled={!drawBounds} onClick={handleInit}>
          Init Grid {drawBounds ? `(${cellSizeM}m)` : '- draw first'}
        </button>
        <input
          type="number"
          min={10}
          max={100}
          value={cellSizeM}
          onChange={(event) => setCellSizeM(Number(event.target.value))}
          className="emu-cell-size-input"
          title="Cell size (m)"
        />
        {gridState?.initialized && (
          <span className="emu-grid-info">
            {gridState.n_rows}x{gridState.n_cols} cells - Mode: {gridState.mode}
          </span>
        )}
        {recommendation && (
          <span className="emu-rec-info">
            {'Rec -> Cell '}
            {recommendation.target_cell_id} - {recommendation.distance_m.toFixed(0)}m - {recommendation.reason}
          </span>
        )}
        {error && <span className="emu-error">{error}</span>}
      </div>

      <div className="emu-body">
        <aside className="emu-sidebar">
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

function Slider({ label, min, max, step, value, onChange }: {
  label: string
  min: number
  max: number
  step: number
  value: number
  onChange: (value: number) => void
}) {
  return (
    <div className="emu-control-group">
      <div className="emu-label">{label}</div>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} className="emu-slider" />
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
