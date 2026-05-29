import { forwardRef, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  CircleMarker,
  MapContainer,
  Polyline,
  Rectangle,
  TileLayer,
  Tooltip,
  useMap,
  useMapEvents,
} from 'react-leaflet'
import {
  getAirunitStatus,
  getGuidanceGrid,
  getGuidanceRecommendation,
  initGuidance,
  listPiFiles,
  resetGuidance,
  sendAirunitCommand,
  type GuidanceGridState,
  type GuidanceRecommendation,
  type PiFile,
} from '../api/airunit'
import './AirUnitPage.css'

type Point = { lat: number; lon: number }
type WsMessage = {
  type?: string
  connected?: boolean
  pi_info?: { ip: string; port: number } | null
  ip?: string
  port?: number
  line?: string
  status?: string
  lat?: number
  lon?: number
  lng?: number
  gps_valid?: boolean
}

const DEFAULT_CENTER: [number, number] = [31.5, 34.8]
const COLOR_PRESETS = [
  { name: 'Amber', value: '#fbbf24' },
  { name: 'Blue', value: '#3b82f6' },
  { name: 'Green', value: '#22c55e' },
  { name: 'Cyan', value: '#06b6d4' },
  { name: 'Violet', value: '#8b5cf6' },
  { name: 'Rose', value: '#f43f5e' },
  { name: 'White', value: '#f8fafc' },
  { name: 'Orange', value: '#f97316' },
  { name: 'Lime', value: '#84cc16' },
  { name: 'Sky', value: '#0ea5e9' },
  { name: 'Pink', value: '#ec4899' },
  { name: 'Slate', value: '#64748b' },
  { name: 'Teal', value: '#14b8a6' },
  { name: 'Red', value: '#ef4444' },
  { name: 'Yellow', value: '#eab308' },
] as const

export default function AirUnitPage() {
  const [piConnected, setPiConnected] = useState(false)
  const [piInfo, setPiInfo] = useState<{ ip: string; port: number } | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const [files, setFiles] = useState<PiFile[]>([])
  const [loadingFiles, setLoadingFiles] = useState(false)
  const [gridState, setGridState] = useState<GuidanceGridState | null>(null)
  const [recommendation, setRecommendation] = useState<GuidanceRecommendation | null>(null)
  const [dronePos, setDronePos] = useState<Point | null>(null)
  const [drawMode, setDrawMode] = useState(false)
  const [drawCorner1, setDrawCorner1] = useState<Point | null>(null)
  const [drawCorner2, setDrawCorner2] = useState<Point | null>(null)
  const [cellSizeM, setCellSizeM] = useState(30)
  const [guidanceRunning, setGuidanceRunning] = useState(false)
  const [mapCenter, setMapCenter] = useState<[number, number]>(DEFAULT_CENTER)
  const [mapZoom, setMapZoom] = useState(15)
  const [gsPos, setGsPos] = useState<Point | null>(null)
  const [gsLocationEnabled, setGsLocationEnabled] = useState(false)
  const [showGsMarker, setShowGsMarker] = useState(true)
  const [showPiMarker, setShowPiMarker] = useState(true)
  const [gsColor, setGsColor] = useState('#fbbf24')
  const [piColor, setPiColor] = useState('#3b82f6')
  const [openColorMenu, setOpenColorMenu] = useState<'gs' | 'pi' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const logRef = useRef<HTMLPreElement | null>(null)
  const gsMenuRef = useRef<HTMLDivElement | null>(null)
  const piMenuRef = useRef<HTMLDivElement | null>(null)

  const appendLog = useCallback((line: string) => {
    setLogs((previous) => [...previous, line].slice(-200))
  }, [])

  useEffect(() => {
    getAirunitStatus()
      .then((status) => {
        setPiConnected(status.pi_connected)
        setPiInfo(status.pi_info)
      })
      .catch((err: unknown) => appendLog(`[status] ${String(err)}`))
  }, [appendLog])

  useEffect(() => {
    getGuidanceGrid()
      .then((grid) => {
        if (grid.initialized) {
          setGridState(grid)
          setGuidanceRunning(true)
        }
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    let ws: WebSocket | null = null
    let closed = false
    let reconnectTimer: number | undefined
    let attempt = 0

    function connect() {
      ws = new WebSocket('ws://localhost:8000/api/airunit/frontend-ws')

      ws.onopen = () => {
        attempt = 0
        appendLog('[ws] connected to air unit relay')
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as WsMessage
          handleWsMessage(msg)
        } catch {
          appendLog(`[ws] ${String(event.data)}`)
        }
      }

      ws.onerror = () => {
        appendLog('[ws] relay connection error')
      }

      ws.onclose = () => {
        if (closed) return
        setPiConnected(false)
        const delay = Math.min(1000 * 2 ** attempt, 15000)
        attempt += 1
        appendLog(`[ws] disconnected; reconnecting in ${(delay / 1000).toFixed(0)}s`)
        reconnectTimer = window.setTimeout(connect, delay)
      }
    }

    function handleWsMessage(msg: WsMessage) {
      if (msg.type === 'pi_connected' || msg.type === 'pi_status') {
        const connected = msg.connected !== false
        setPiConnected(connected)
        setPiInfo(normalizePiInfo(msg))
        appendLog(connected ? '[pi] connected' : '[pi] disconnected')
        return
      }
      if (msg.type === 'pi_disconnected') {
        setPiConnected(false)
        setPiInfo(null)
        appendLog('[pi] disconnected')
        return
      }
      if (msg.type === 'log' || msg.type === 'ble_log') {
        appendLog(msg.line ?? '')
        return
      }
      if (msg.type === 'status' || msg.type === 'ble_status') {
        appendLog(`[status] ${msg.status ?? ''}`)
        return
      }
      if (msg.type === 'POSE') {
        const lon = msg.lon ?? msg.lng
        if (msg.gps_valid && typeof msg.lat === 'number' && typeof lon === 'number') {
          setDronePos({ lat: msg.lat, lon })
        }
      }
    }

    connect()
    return () => {
      closed = true
      if (reconnectTimer) window.clearTimeout(reconnectTimer)
      ws?.close()
    }
  }, [appendLog])

  useEffect(() => {
    if (!navigator.geolocation) {
      setGsLocationEnabled(false)
      return
    }

    setGsLocationEnabled(true)
    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        const next = { lat: pos.coords.latitude, lon: pos.coords.longitude }
        setGsPos(next)
      },
      () => {
        setGsLocationEnabled(false)
      },
      {
        enableHighAccuracy: true,
        maximumAge: 5000,
        timeout: 10000,
      },
    )

    return () => {
      navigator.geolocation.clearWatch(watchId)
    }
  }, [])

  useEffect(() => {
    if (!guidanceRunning) return

    let cancelled = false
    const loadRecommendation = async () => {
      try {
        const next = await getGuidanceRecommendation()
        if (!cancelled) setRecommendation('available' in next && next.available === false ? null : next)
      } catch (err: unknown) {
        appendLog(`[guidance] recommendation error: ${String(err)}`)
      }
    }
    void loadRecommendation()
    const interval = window.setInterval(loadRecommendation, 2000)
    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [appendLog, guidanceRunning])

  useEffect(() => {
    if (!guidanceRunning) return

    let cancelled = false
    const loadGrid = async () => {
      try {
        const next = await getGuidanceGrid()
        if (!cancelled) setGridState(next)
      } catch (err: unknown) {
        appendLog(`[guidance] grid error: ${String(err)}`)
      }
    }
    void loadGrid()
    const interval = window.setInterval(loadGrid, 3000)
    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [appendLog, guidanceRunning])

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [logs])

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      const target = event.target as Node
      const withinGs = gsMenuRef.current?.contains(target)
      const withinPi = piMenuRef.current?.contains(target)
      if (!withinGs && !withinPi) setOpenColorMenu(null)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const drawBounds = useMemo(() => {
    if (!drawCorner1 || !drawCorner2) return null
    return {
      min_lat: Math.min(drawCorner1.lat, drawCorner2.lat),
      max_lat: Math.max(drawCorner1.lat, drawCorner2.lat),
      min_lon: Math.min(drawCorner1.lon, drawCorner2.lon),
      max_lon: Math.max(drawCorner1.lon, drawCorner2.lon),
    }
  }, [drawCorner1, drawCorner2])

  const gridCells = useMemo(() => buildGridCells(gridState), [gridState])
  const piMarker = dronePos

  function gotoPoint(point: Point) {
    setMapCenter([point.lat, point.lon])
    setMapZoom(18)
  }

  function handleMapPick(point: Point) {
    if (!drawMode) return
    if (!drawCorner1 || drawCorner2) {
      setDrawCorner1(point)
      setDrawCorner2(null)
      return
    }
    setDrawCorner2(point)
    setDrawMode(false)
  }

  async function handleCommand(cmd: string) {
    setError(null)
    try {
      await sendAirunitCommand(cmd)
      appendLog(`[cmd] ${cmd}`)
    } catch (err: unknown) {
      setError(String(err))
      appendLog(`[cmd] ${cmd} failed: ${String(err)}`)
    }
  }

  async function refreshFiles() {
    setLoadingFiles(true)
    setError(null)
    try {
      const result = await listPiFiles()
      setFiles(result.files)
      if (result.error) appendLog(`[files] ${result.error}`)
    } catch (err: unknown) {
      setError(String(err))
    } finally {
      setLoadingFiles(false)
    }
  }

  async function handleStartGuidance() {
    if (!drawBounds) return
    setError(null)
    try {
      await initGuidance(drawBounds, cellSizeM)
      const nextGrid = await getGuidanceGrid()
      setGridState(nextGrid)
      setGuidanceRunning(true)
      appendLog('[guidance] started')
    } catch (err: unknown) {
      setError(String(err))
      appendLog(`[guidance] start failed: ${String(err)}`)
    }
  }

  async function handleResetGuidance() {
    setError(null)
    try {
      await resetGuidance()
      setGuidanceRunning(false)
      setGridState(null)
      setRecommendation(null)
      setDrawCorner1(null)
      setDrawCorner2(null)
      appendLog('[guidance] reset')
    } catch (err: unknown) {
      setError(String(err))
    }
  }

  return (
    <div className="airunit-page">
      <div className="airunit-connection-bar">
        <span className={piConnected ? 'pi-dot-connected' : 'pi-dot-disconnected'}>●</span>
        <strong>{piConnected ? 'Connected' : 'Not connected'}</strong>
        <span className="airunit-connection-detail">
          {piConnected && piInfo ? `Pi: ${piInfo.ip}:${piInfo.port}` : 'waiting for Pi...'}
        </span>
        <span className={gsPos ? 'gs-dot-connected' : 'gs-dot-disconnected'}>●</span>
        <strong>{gsPos ? 'GS live' : gsLocationEnabled ? 'Tracking GS...' : 'GS location off'}</strong>
        <span className="airunit-connection-detail">
          {gsPos ? `GS: ${gsPos.lat.toFixed(5)}, ${gsPos.lon.toFixed(5)}` : 'browser location'}
        </span>
        <div className="airunit-marker-controls">
          <label className="airunit-toggle">
            <input
              type="checkbox"
              checked={showGsMarker}
              onChange={(event) => setShowGsMarker(event.target.checked)}
            />
            GS
          </label>
          <ColorMenu
            ref={gsMenuRef}
            value={gsColor}
            onChange={setGsColor}
            label="GS marker color"
            open={openColorMenu === 'gs'}
            onToggle={() => setOpenColorMenu((current) => (current === 'gs' ? null : 'gs'))}
            buttonLabel="GS"
          />
          <label className="airunit-toggle">
            <input
              type="checkbox"
              checked={showPiMarker}
              onChange={(event) => setShowPiMarker(event.target.checked)}
            />
            Pi
          </label>
          <ColorMenu
            ref={piMenuRef}
            value={piColor}
            onChange={setPiColor}
            label="Pi marker color"
            open={openColorMenu === 'pi'}
            onToggle={() => setOpenColorMenu((current) => (current === 'pi' ? null : 'pi'))}
            buttonLabel="Pi"
          />
          <button
            type="button"
            disabled={!showGsMarker || !gsPos}
            onClick={() => gsPos && gotoPoint(gsPos)}
          >
            Go to GS
          </button>
          <button
            type="button"
            disabled={!showPiMarker || !piMarker}
            onClick={() => piMarker && gotoPoint(piMarker)}
          >
            Go to Pi
          </button>
        </div>
        {piConnected && (
          <div className="airunit-command-row">
            <button type="button" onClick={() => handleCommand('scan_start')}>
              Start WiFi
            </button>
            <button type="button" onClick={() => handleCommand('scan_stop')}>
              Stop WiFi
            </button>
            <button type="button" onClick={() => handleCommand('ble_scan_start')}>
              Start BLE
            </button>
            <button type="button" onClick={() => handleCommand('ble_scan_stop')}>
              Stop BLE
            </button>
          </div>
        )}
      </div>

      {error && <div className="airunit-error">{error}</div>}

      <div className="airunit-body">
        <aside className="airunit-sidebar">
          <section className="airunit-panel airunit-log-panel">
            <div className="airunit-panel-title">Status Log</div>
            <pre ref={logRef} className="airunit-log">
              {logs.length ? logs.join('\n') : 'Waiting for Air Unit events...'}
            </pre>
          </section>

          <section className="airunit-files">
            <div className="airunit-files-header">
              <div className="airunit-panel-title">Files</div>
              <button type="button" onClick={refreshFiles} disabled={loadingFiles}>
                {loadingFiles ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>
            <div className="airunit-cell-size">
              <label htmlFor="airunit-cell-size">Cell size</label>
              <input
                id="airunit-cell-size"
                type="number"
                min={5}
                step={5}
                value={cellSizeM}
                onChange={(event) => setCellSizeM(Number(event.target.value))}
              />
              <span>m</span>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>KB</th>
                  <th>Modified</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {files.length === 0 ? (
                  <tr>
                    <td colSpan={4}>No files loaded.</td>
                  </tr>
                ) : (
                  files.map((file) => (
                    <tr key={file.name}>
                      <td title={file.description || file.name}>{file.name}</td>
                      <td>{(file.size_bytes / 1024).toFixed(1)}</td>
                      <td>{formatMtime(file.mtime)}</td>
                      <td>
                        <a href={`/api/airunit/files/${encodeURIComponent(file.name)}`} download>
                          Download
                        </a>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </section>
        </aside>

        <main className="airunit-main">
          <MapContainer center={mapCenter} zoom={mapZoom} maxZoom={23} className="airunit-map">
            <SetMapCenter center={mapCenter} zoom={mapZoom} />
            <TileLayer
              attribution='Tiles &copy; Esri &mdash; Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, GIS User Community'
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              maxNativeZoom={18}
              maxZoom={23}
            />
            <MapClickHandler onPick={handleMapPick} />
            {drawBounds && (
              <Rectangle
                bounds={[
                  [drawBounds.min_lat, drawBounds.min_lon],
                  [drawBounds.max_lat, drawBounds.max_lon],
                ]}
                pathOptions={{ color: '#f97316', dashArray: '8 5', fillOpacity: 0.04, weight: 2 }}
              >
                <Tooltip>Guidance boundary</Tooltip>
              </Rectangle>
            )}
            {gridCells.map(({ cell, bounds }) => {
              const isTarget = cell.cell_id === recommendation?.target_cell_id
              const score = cell.display_score ?? cell.final_score
              return (
                <Rectangle
                  key={cell.cell_id}
                  bounds={bounds}
                  pathOptions={{
                    color: isTarget ? '#f8fafc' : scoreColor(score),
                    fillColor: scoreColor(score),
                    fillOpacity: isTarget ? 0.5 : 0.35,
                    opacity: isTarget ? 0.9 : 0.75,
                    weight: isTarget ? 2.5 : 0.5,
                  }}
                >
                  <Tooltip>
                    Cell {cell.cell_id}
                    <br />
                    Score {score.toFixed(2)}
                    <br />
                    E {cell.evidence_score.toFixed(2)} U {cell.uncertainty_score.toFixed(2)}
                  </Tooltip>
                </Rectangle>
              )
            })}
            {showGsMarker && gsPos && (
              <CircleMarker
                center={[gsPos.lat, gsPos.lon]}
                radius={9}
                pathOptions={{ color: gsColor, fillColor: gsColor, fillOpacity: 0.95, weight: 2 }}
              >
                <Tooltip>GS live location</Tooltip>
              </CircleMarker>
            )}
            {showPiMarker && piMarker && (
              <CircleMarker
                center={[piMarker.lat, piMarker.lon]}
                radius={8}
                pathOptions={{ color: piColor, fillColor: piColor, fillOpacity: 0.95, weight: 2 }}
              >
                <Tooltip>Pi GPS fix</Tooltip>
              </CircleMarker>
            )}
            {recommendation && (
              <CircleMarker
                center={[recommendation.target_lat, recommendation.target_lon]}
                radius={7}
                pathOptions={{ color: '#facc15', fillColor: '#facc15', fillOpacity: 0.9, weight: 2 }}
              >
                <Tooltip>Target cell {recommendation.target_cell_id}</Tooltip>
              </CircleMarker>
            )}
            {piMarker && recommendation && (
              <Polyline
                positions={[
                  [piMarker.lat, piMarker.lon],
                  [recommendation.target_lat, recommendation.target_lon],
                ]}
                pathOptions={{ color: '#facc15', weight: 3, dashArray: '8 4' }}
              />
            )}
          </MapContainer>

          <section className="airunit-guidance-panel">
            {guidanceRunning && recommendation ? (
              <>
                <span
                  className={`guidance-mode-badge ${
                    recommendation.mode === 'REFINE' ? 'guidance-mode-refine' : 'guidance-mode-explore'
                  }`}
                >
                  {recommendation.mode}
                </span>
                <GuidanceStat label="Target" value={`Cell ${recommendation.target_cell_id}`} />
                <GuidanceStat label="Distance" value={`${recommendation.distance_m.toFixed(0)}m`} />
                <GuidanceStat
                  label="Bearing"
                  value={`${recommendation.bearing_deg.toFixed(0)} deg ${compass(recommendation.bearing_deg)}`}
                />
                <GuidanceStat label="GPS" value={recommendation.gps_valid ? 'OK' : 'Invalid'} />
                <GuidanceStat label="Data" value={recommendation.data_fresh ? 'Fresh' : 'Stale'} />
                <GuidanceStat label="Score" value={recommendation.final_score.toFixed(2)} />
                <div className="guidance-reason">{recommendation.reason}</div>
              </>
            ) : guidanceRunning ? (
              <div className="guidance-empty">No valid target yet. Waiting for live Pi GPS and packet evidence.</div>
            ) : (
              <div className="guidance-empty">
                {drawMode
                  ? drawCorner1
                    ? 'Click the opposite map corner.'
                    : 'Click the first map corner.'
                  : drawBounds
                    ? 'Boundary ready. Start guidance to build recommendations.'
                    : 'Draw a boundary to initialize smart flight guidance.'}
              </div>
            )}
            <div className="guidance-controls">
              <button
                type="button"
                className={drawMode ? 'active' : ''}
                onClick={() => {
                  setDrawMode(true)
                  setDrawCorner1(null)
                  setDrawCorner2(null)
                }}
              >
                Draw Boundary
              </button>
              <button type="button" disabled={!drawBounds || guidanceRunning} onClick={handleStartGuidance}>
                Start
              </button>
              <button type="button" disabled={!guidanceRunning} onClick={() => setGuidanceRunning(false)}>
                Stop
              </button>
              <button type="button" onClick={handleResetGuidance}>
                Reset
              </button>
            </div>
          </section>
        </main>
      </div>
    </div>
  )
}

function normalizePiInfo(msg: WsMessage): { ip: string; port: number } | null {
  if (msg.pi_info) return msg.pi_info
  if (msg.ip && typeof msg.port === 'number') return { ip: msg.ip, port: msg.port }
  return null
}

function SetMapCenter({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap()
  useEffect(() => {
    map.setView(center, zoom)
  }, [center, map, zoom])
  return null
}

const ColorMenu = forwardRef<
  HTMLDivElement,
  {
    value: string
    onChange: (value: string) => void
    label: string
    open: boolean
    onToggle: () => void
    buttonLabel: string
  }
>(function ColorMenu({ value, onChange, label, open, onToggle, buttonLabel }, ref) {
  return (
    <div className="airunit-color-menu" ref={ref}>
      <button type="button" className="airunit-color-menu-button" onClick={onToggle}>
        {buttonLabel}
      </button>
      {open && (
        <div className="airunit-color-menu-panel">
          <div className="airunit-color-swatches" role="group" aria-label={`${label} presets`}>
            {COLOR_PRESETS.map((preset) => (
              <button
                key={preset.value}
                type="button"
                className={`airunit-color-swatch ${value === preset.value ? 'active' : ''}`}
                style={{ backgroundColor: preset.value }}
                onClick={() => onChange(preset.value)}
                aria-label={preset.name}
                title={preset.name}
              />
            ))}
          </div>
          <label className="airunit-color-custom">
            <span>Manual</span>
            <input
              className="airunit-color"
              type="color"
              value={value}
              onChange={(event) => onChange(event.target.value)}
              aria-label={`${label} manual color`}
            />
          </label>
        </div>
      )}
    </div>
  )
})

function MapClickHandler({ onPick }: { onPick: (point: Point) => void }) {
  useMapEvents({
    click(event) {
      onPick({ lat: event.latlng.lat, lon: event.latlng.lng })
    },
  })
  return null
}

function GuidanceStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="guidance-stat">
      <span className="guidance-stat-label">{label}</span>
      <span className="guidance-stat-value">{value}</span>
    </div>
  )
}

function buildGridCells(gridState: GuidanceGridState | null) {
  if (!gridState?.initialized || !gridState.bounds || !gridState.n_rows || !gridState.n_cols) {
    return []
  }
  const latHalf = (gridState.bounds.max_lat - gridState.bounds.min_lat) / gridState.n_rows / 2
  const lonHalf = (gridState.bounds.max_lon - gridState.bounds.min_lon) / gridState.n_cols / 2
  return gridState.cells.map((cell) => ({
    cell,
    bounds: [
      [cell.center_lat - latHalf, cell.center_lon - lonHalf],
      [cell.center_lat + latHalf, cell.center_lon + lonHalf],
    ] as [[number, number], [number, number]],
  }))
}

function scoreColor(score: number): string {
  if (score >= 0.7) return '#16a34a'
  if (score >= 0.35) return '#ca8a04'
  if (score > 0) return '#dc2626'
  return '#374151'
}

function compass(deg: number): string {
  const labels = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
  return labels[Math.round((((deg % 360) + 360) % 360) / 45) % labels.length]
}

function formatMtime(value: number): string {
  const millis = value > 10_000_000_000 ? value : value * 1000
  const date = new Date(millis)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })
}
