import { useEffect, useMemo, useState } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMapEvents } from 'react-leaflet'
import {
  approveCalibration,
  getCalibrationCandidates,
  getInventory,
  runCalibration,
  runOverview,
  useFallbackPreset,
  type CalibrationRunResult,
  type CalibrationState,
  type OverviewResult,
} from '../api/sessions'
import HelpTip from '../components/HelpTip'
import { HELP } from '../helpTexts'
import { useSession } from '../state/SessionContext'
import './CalibrationPage.css'

type GtMode = 'mean_first_k' | 'first_sample' | 'manual_map_click'
type FallbackName = 'urban' | 'open_field' | 'mixed_outdoor'

const FALLBACK_PRESETS: Record<
  FallbackName,
  { label: string; rssi_at_1m: number; path_loss_n: number; sigma: number }
> = {
  urban: { label: 'Urban', rssi_at_1m: -40, path_loss_n: 3.5, sigma: 8 },
  open_field: { label: 'Open Field', rssi_at_1m: -40, path_loss_n: 2, sigma: 4 },
  mixed_outdoor: { label: 'Mixed Outdoor', rssi_at_1m: -40, path_loss_n: 2.7, sigma: 6 },
}

export default function CalibrationPage() {
  const { session } = useSession()
  const [csvFiles, setCsvFiles] = useState<Array<{ filename: string }>>([])
  const [selectedCsv, setSelectedCsv] = useState('')
  const [macs, setMacs] = useState<string[]>([])
  const [selectedMac, setSelectedMac] = useState('')
  const [gtMode, setGtMode] = useState<GtMode>('mean_first_k')
  const [gtK, setGtK] = useState(5)
  const [manualPoint, setManualPoint] = useState<{ lat: number; lon: number } | null>(null)
  const [track, setTrack] = useState<OverviewResult['gps_points']>([])
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [enableRansac, setEnableRansac] = useState(true)
  const [ransacThreshold, setRansacThreshold] = useState(4)
  const [ransacIterations, setRansacIterations] = useState(100)
  const [distanceFloor, setDistanceFloor] = useState(1)
  const [result, setResult] = useState<CalibrationRunResult | null>(null)
  const [approved, setApproved] = useState<CalibrationState | null>(null)
  const [fallbackName, setFallbackName] = useState<FallbackName>('urban')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!session?.session_id) {
      setCsvFiles([])
      return
    }

    setError(null)
    getInventory(session.session_id)
      .then((inventory) => setCsvFiles(inventory.raw_csvs))
      .catch((err: unknown) => setError(String(err)))
  }, [session?.session_id])

  async function handleCsvChange(filename: string) {
    setSelectedCsv(filename)
    setSelectedMac('')
    setMacs([])
    setTrack([])
    setResult(null)
    setApproved(null)
    setManualPoint(null)
    if (!session?.session_id || !filename) return

    setLoading(true)
    setError(null)
    try {
      const [candidateResult, overviewResult] = await Promise.all([
        getCalibrationCandidates(session.session_id, filename),
        runOverview(session.session_id, filename),
      ])
      setMacs(candidateResult.macs)
      setTrack(Array.isArray(overviewResult.gps_points) ? overviewResult.gps_points : [])
    } catch (err: unknown) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  async function handleRun() {
    if (!session?.session_id || !selectedCsv || !selectedMac) return

    setLoading(true)
    setError(null)
    setApproved(null)
    try {
      const calibration = await runCalibration(session.session_id, {
        csv_filename: selectedCsv,
        mac: selectedMac,
        gt_mode: gtMode,
        gt_k: gtK,
        manual_lat: manualPoint?.lat,
        manual_lon: manualPoint?.lon,
        enable_ransac: enableRansac,
        ransac_threshold_db: ransacThreshold,
        ransac_iterations: ransacIterations,
        distance_floor_m: distanceFloor,
      })
      setResult(calibration)
    } catch (err: unknown) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  async function handleApprove() {
    if (!session?.session_id || !result?.success) return

    setLoading(true)
    setError(null)
    try {
      setApproved(await approveCalibration(session.session_id))
    } catch (err: unknown) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  async function handleFallback() {
    if (!session?.session_id) return

    setLoading(true)
    setError(null)
    try {
      setApproved(await useFallbackPreset(session.session_id, fallbackName))
    } catch (err: unknown) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  const canRun =
    !!session &&
    !!selectedCsv &&
    !!selectedMac &&
    (gtMode !== 'manual_map_click' || manualPoint !== null)
  const mapCenter: [number, number] = track.length ? [track[0].lat, track[0].lon] : [32, 34.8]

  return (
    <div className="calibration-page">
      <div className="calibration-left">
        <h1 className="page-title">Calibration</h1>

        {!session && (
          <p className="empty-state">No active session. Go to Session Start to select a folder.</p>
        )}
        {error && <p className="error-banner">{error}</p>}

        <section className="control-section">
          <label htmlFor="calibration-csv" className="field-label">
            Calibration CSV <HelpTip text={HELP.calibration_csv} />
          </label>
          <select
            id="calibration-csv"
            className="folder-select"
            value={selectedCsv}
            onChange={(event) => handleCsvChange(event.target.value)}
            disabled={!session || loading}
          >
            <option value="">- Select calibration CSV -</option>
            {csvFiles.map((file) => (
              <option key={file.filename} value={file.filename} dir="auto">
                {file.filename}
              </option>
            ))}
          </select>

          <label htmlFor="calibration-mac" className="field-label">
            MAC Address
          </label>
          <select
            id="calibration-mac"
            className="folder-select"
            value={selectedMac}
            onChange={(event) => {
              setSelectedMac(event.target.value)
              setResult(null)
              setApproved(null)
            }}
            disabled={!selectedCsv || loading}
          >
            <option value="">- Select MAC -</option>
            {macs.map((mac) => (
              <option key={mac} value={mac} dir="ltr">
                {mac}
              </option>
            ))}
          </select>
        </section>

        <section className="control-section">
          <span className="field-label">Ground Truth</span>
          <div className="segmented-control" role="group" aria-label="Ground truth mode">
            <button
              type="button"
              className={`seg-btn${gtMode === 'mean_first_k' ? ' selected' : ''}`}
              onClick={() => setGtMode('mean_first_k')}
            >
              Mean of first K
            </button>
            <button
              type="button"
              className={`seg-btn${gtMode === 'first_sample' ? ' selected' : ''}`}
              onClick={() => setGtMode('first_sample')}
            >
              First sample
            </button>
            <button
              type="button"
              className={`seg-btn${gtMode === 'manual_map_click' ? ' selected' : ''}`}
              onClick={() => setGtMode('manual_map_click')}
            >
              Manual map click
            </button>
          </div>

          {gtMode === 'mean_first_k' && (
            <label className="inline-field">
              <span className="field-label">K samples</span>
              <input
                type="number"
                min={1}
                max={20}
                value={gtK}
                onChange={(event) => setGtK(Number(event.target.value))}
              />
            </label>
          )}

          {gtMode === 'manual_map_click' && (
            <div className="manual-map-panel">
              <p className="hint-text">Click the map to set the ground-truth point.</p>
              <MapContainer center={mapCenter} zoom={15} maxZoom={23} className="calibration-map">
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  maxNativeZoom={19}
                  maxZoom={23}
                />
                <ManualClickHandler onPick={(lat, lon) => setManualPoint({ lat, lon })} />
                {track.map((point, index) => (
                  <CircleMarker
                    key={`${point.timestamp_utc}-${point.src_mac}-${index}`}
                    center={[point.lat, point.lon]}
                    radius={3}
                    pathOptions={{ color: '#64748b', fillColor: '#64748b', fillOpacity: 0.55 }}
                  />
                ))}
                {manualPoint && (
                  <CircleMarker
                    center={[manualPoint.lat, manualPoint.lon]}
                    radius={8}
                    pathOptions={{
                      color: '#b91c1c',
                      fillColor: '#fef2f2',
                      fillOpacity: 0.9,
                      weight: 3,
                    }}
                  >
                    <Tooltip permanent>GT</Tooltip>
                  </CircleMarker>
                )}
              </MapContainer>
              <p className="coordinate-readout" dir="ltr">
                {manualPoint
                  ? `${manualPoint.lat.toFixed(6)}, ${manualPoint.lon.toFixed(6)}`
                  : 'No manual point selected'}
              </p>
            </div>
          )}
        </section>

        <section className="control-section">
          <button
            type="button"
            className="link-button"
            onClick={() => setShowAdvanced((value) => !value)}
            aria-expanded={showAdvanced}
          >
            {showAdvanced ? 'Hide' : 'Show'} advanced parameters
          </button>
          {showAdvanced && (
            <div className="advanced-grid">
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={enableRansac}
                  onChange={(event) => setEnableRansac(event.target.checked)}
                />
                Enable RANSAC <HelpTip text={HELP.ransac} />
              </label>
              <NumberField label="Threshold dB" value={ransacThreshold} min={1} max={15} onChange={setRansacThreshold} />
              <NumberField label="Iterations" value={ransacIterations} min={10} max={1000} onChange={setRansacIterations} />
              <NumberField label="Distance floor m" value={distanceFloor} min={0.5} max={5} step={0.5} onChange={setDistanceFloor} />
            </div>
          )}
        </section>

        <button className="btn-primary" disabled={!canRun || loading} onClick={handleRun}>
          {loading ? 'Working...' : 'Run Calibration'}
        </button>

        {result && (
          <section className="result-panel">
            <h2 className="panel-title">Derived Parameters</h2>
            {!result.success ? (
              <p className="error-banner">{result.error}</p>
            ) : (
              <>
                {result.warnings.map((warning) => (
                  <div key={warning} className="warning-banner">
                    {warning}
                  </div>
                ))}
                <ParameterTable state={result} />
                <button
                  className="btn-primary"
                  disabled={!result.success || loading}
                  onClick={handleApprove}
                >
                  Approve
                </button>
              </>
            )}
          </section>
        )}

        {approved && (
          <div className="success-banner">
            Calibration approved from {approved.parameter_source}
            {approved.parameter_set_name ? ` preset: ${approved.parameter_set_name}` : ''}.
          </div>
        )}

        <section className="fallback-panel">
          <h2 className="panel-title">Fallback Presets</h2>
          <p className="hint-text">Use if derivation fails or is skipped.</p>
          {(Object.keys(FALLBACK_PRESETS) as FallbackName[]).map((name) => {
            const preset = FALLBACK_PRESETS[name]
            return (
              <label key={name} className="preset-row">
                <input
                  type="radio"
                  name="fallback-preset"
                  value={name}
                  checked={fallbackName === name}
                  onChange={() => setFallbackName(name)}
                />
                <span>{preset.label}</span>
                <span className="preset-values">
                  {preset.rssi_at_1m} dBm, n={preset.path_loss_n}, sigma={preset.sigma}
                </span>
              </label>
            )
          })}
          <button className="btn-secondary" disabled={!session || loading} onClick={handleFallback}>
            Use This Preset
          </button>
        </section>
      </div>

      <div className="calibration-right">
        <ScatterPlot result={result} />
      </div>
    </div>
  )
}

function ManualClickHandler({ onPick }: { onPick: (lat: number, lon: number) => void }) {
  useMapEvents({
    click(event) {
      onPick(event.latlng.lat, event.latlng.lng)
    },
  })
  return null
}

function NumberField({
  label,
  value,
  min,
  max,
  step,
  onChange,
  helpText,
}: {
  label: string
  value: number
  min: number
  max: number
  step?: number
  onChange: (value: number) => void
  helpText?: string
}) {
  return (
    <label className="inline-field">
      <span className="field-label">
        {label} {helpText && <HelpTip text={helpText} />}
      </span>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step ?? 1}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  )
}

function ParameterTable({ state }: { state: CalibrationRunResult }) {
  if (!state.parameters || !state.fit_quality) return null

  return (
    <table className="parameter-table">
      <tbody>
        <tr>
          <th>
            RSSI at 1m <HelpTip text={HELP.rssi_at_1m} />
          </th>
          <td>{state.parameters.rssi_at_1m} dBm</td>
        </tr>
        <tr>
          <th>
            Path loss n <HelpTip text={HELP.path_loss_n} />
          </th>
          <td>{state.parameters.path_loss_n}</td>
        </tr>
        <tr>
          <th>
            Sigma <HelpTip text={HELP.calib_sigma} />
          </th>
          <td>{state.parameters.sigma}</td>
        </tr>
        <tr>
          <th>
            R² <HelpTip text={HELP.r_squared} />
          </th>
          <td>{state.fit_quality.r2}</td>
        </tr>
        <tr>
          <th>
            Inliers <HelpTip text={HELP.inliers} />
          </th>
          <td>
            {state.fit_quality.inlier_count} / {state.fit_quality.sample_count} (
            {(state.fit_quality.inlier_ratio * 100).toFixed(1)}%)
          </td>
        </tr>
      </tbody>
    </table>
  )
}

function ScatterPlot({ result }: { result: CalibrationRunResult | null }) {
  const plot = useMemo(() => buildPlot(result), [result])

  if (!result?.scatter.length || !plot) {
    return (
      <div className="scatter-empty">
        <h2>Calibration Fit</h2>
        <p>Select a CSV and MAC, then run calibration.</p>
      </div>
    )
  }

  return (
    <div className="scatter-panel">
      <h2>Calibration Fit</h2>
      <svg viewBox="0 0 680 440" role="img" aria-label="Calibration scatter plot">
        <line x1="56" y1="24" x2="56" y2="384" className="axis-line" />
        <line x1="56" y1="384" x2="640" y2="384" className="axis-line" />
        <text x="348" y="426" className="axis-label">
          log10(distance)
        </text>
        <text x="18" y="210" className="axis-label axis-label-y">
          RSSI
        </text>
        {plot.line && (
          <line
            x1={plot.line.x1}
            y1={plot.line.y1}
            x2={plot.line.x2}
            y2={plot.line.y2}
            className="regression-line"
          />
        )}
        {plot.points.map((point, index) => (
          <circle
            key={index}
            cx={point.cx}
            cy={point.cy}
            r="4"
            className={point.inlier ? 'scatter-inlier' : 'scatter-outlier'}
          />
        ))}
      </svg>
    </div>
  )
}

function buildPlot(result: CalibrationRunResult | null) {
  if (!result?.scatter.length) return null

  const width = 584
  const height = 360
  const left = 56
  const top = 24
  const xs = result.scatter.map((point) => point.log10_distance)
  const ys = result.scatter.map((point) => point.rssi)
  const minX = Math.min(0, ...xs)
  const maxX = Math.max(2, ...xs)
  const minY = Math.min(-100, ...ys)
  const maxY = Math.max(-30, ...ys)
  const scaleX = (x: number) => left + ((x - minX) / (maxX - minX || 1)) * width
  const scaleY = (y: number) => top + (1 - (y - minY) / (maxY - minY || 1)) * height
  const points = result.scatter.map((point) => ({
    cx: scaleX(point.log10_distance),
    cy: scaleY(point.rssi),
    inlier: point.inlier,
  }))

  const params = result.parameters
  const line = params
    ? {
        x1: scaleX(minX),
        y1: scaleY(params.rssi_at_1m - 10 * params.path_loss_n * minX),
        x2: scaleX(maxX),
        y2: scaleY(params.rssi_at_1m - 10 * params.path_loss_n * maxX),
      }
    : null

  return { points, line }
}
