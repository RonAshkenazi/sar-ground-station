import { useEffect, useMemo, useState } from 'react'
import { Circle, CircleMarker, MapContainer, Polygon, Rectangle, TileLayer, Tooltip, useMap } from 'react-leaflet'
import {
  getExecution,
  getInventory,
  getSessionState,
  runLocalization,
  type ExecutionStatus,
  type InventoryResult,
  type LocalizationRunResult,
} from '../api/sessions'
import HelpTip from '../components/HelpTip'
import LassoTool from '../components/LassoTool'
import { HELP } from '../helpTexts'
import { useSession } from '../state/SessionContext'
import type { SessionState } from '../types'
import { pointInPolygon } from '../utils/geoUtils'
import './LocalizationPage.css'

type MapLayer = 'satellite' | 'osm'

const CLUSTER_COLORS = ['#1f6feb', '#15803d', '#b45309', '#b91c1c', '#7c3aed', '#0f766e']

export default function LocalizationPage() {
  const { session, refreshSession, lassoPolygon, setLassoPolygon } = useSession()
  const [inventory, setInventory] = useState<InventoryResult | null>(null)
  const [sessionState, setSessionState] = useState<SessionState | null>(null)
  const [selectedReid, setSelectedReid] = useState('')
  const [execution, setExecution] = useState<ExecutionStatus | null>(null)
  const [result, setResult] = useState<LocalizationRunResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mapLayer, setMapLayer] = useState<MapLayer>('satellite')
  const [showHeatmap, setShowHeatmap] = useState(false)
  const [showUncertaintyRadii, setShowUncertaintyRadii] = useState(false)
  const [showPeaks, setShowPeaks] = useState(false)
  const [heatmapStride, setHeatmapStride] = useState(1)
  const [showStaticClusters, setShowStaticClusters] = useState(true)
  const [showNoiseClusters, setShowNoiseClusters] = useState(true)
  const [hiddenClusters, setHiddenClusters] = useState<Set<string>>(new Set())
  const [settingsOpen, setSettingsOpen] = useState(true)
  const [lassoActive, setLassoActive] = useState(false)
  const [locSettings, setLocSettings] = useState({
    grid_resolution_m: 2.0,
    dynamic_sigma_alpha: 0.05,
    confidence_cutoff: 0.75,
    uncertainty_participation_floor: 0.8,
    uncertainty_alpha: 1.5,
  })

  function confidenceBadge(tier: string | undefined) {
    if (!tier) return null
    const cls = tier === 'high' ? 'conf-high' : tier === 'medium' ? 'conf-medium' : 'conf-low'
    return <span className={`conf-badge ${cls}`}>{tier}</span>
  }

  useEffect(() => {
    setInventory(null)
    setSessionState(null)
    setSelectedReid('')
    setExecution(null)
    setResult(null)
    setError(null)
    setHiddenClusters(new Set())

    if (!session?.session_id) return
    Promise.all([getInventory(session.session_id), getSessionState(session.session_id)])
      .then(([nextInventory, nextState]) => {
        setInventory(nextInventory)
        setSessionState(nextState)
        const saved = nextState?.current_localization_result
        if (saved) {
          setResult(saved as unknown as LocalizationRunResult)
        }
      })
      .catch((err: unknown) => setError(String(err)))
  }, [session?.session_id])

  useEffect(() => {
    if (!execution || execution.status === 'success' || execution.status === 'failed') return

    const interval = window.setInterval(async () => {
      try {
        const next = await getExecution(execution.execution_id)
        if (next.status === 'success') {
          setResult(next.result_metadata as unknown as LocalizationRunResult)
          setExecution(next)
          void refreshSession()
          window.clearInterval(interval)
        } else if (next.status === 'failed') {
          setError(next.error ?? 'Localization failed')
          setExecution(next)
          window.clearInterval(interval)
        } else {
          setExecution(next)
        }
      } catch (err: unknown) {
        setError(String(err))
        window.clearInterval(interval)
      }
    }, 1500)

    return () => window.clearInterval(interval)
  }, [execution?.execution_id, execution?.status])

  const calibration = sessionState?.active_calibration as
    | { approved?: boolean; parameter_source?: string; parameters?: { path_loss_n: number; rssi_at_1m: number } }
    | null
    | undefined
  const calibrationApproved = calibration?.approved === true
  const running = execution?.status === 'pending' || execution?.status === 'running'
  const canRun = !!session && !!selectedReid && !running && !loading && calibrationApproved
  const mapCenter: [number, number] = result
    ? [(result.bounds.lat_min + result.bounds.lat_max) / 2, (result.bounds.lon_min + result.bounds.lon_max) / 2]
    : [32.0, 34.8]
  const visibleClusters = useMemo(
    () =>
      (result?.cluster_results ?? []).filter((cluster) => {
        if (hiddenClusters.has(cluster.cluster_id)) return false
        if (!showStaticClusters && cluster.cluster_type === 'static') return false
        if (!showNoiseClusters && cluster.cluster_type === 'noise') return false
        if (lassoPolygon) {
          if (cluster.status !== 'success' || !cluster.primary_peak) return false
          if (!pointInPolygon(cluster.primary_peak.lat, cluster.primary_peak.lon, lassoPolygon)) return false
        }
        return true
      }),
    [result, hiddenClusters, showStaticClusters, showNoiseClusters, lassoPolygon],
  )
  const zoneClusterCount = lassoPolygon ? visibleClusters.length : null

  async function handleRun() {
    if (!session?.session_id || !selectedReid) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const started = await runLocalization(session.session_id, {
        reid_csv_filename: selectedReid,
        bounds_mode: 'auto_track_plus_buffer',
        grid_resolution_m: locSettings.grid_resolution_m,
        dynamic_sigma_alpha: locSettings.dynamic_sigma_alpha,
        confidence_cutoff: locSettings.confidence_cutoff,
        uncertainty_participation_floor: locSettings.uncertainty_participation_floor,
        uncertainty_alpha: locSettings.uncertainty_alpha,
      })
      setExecution({
        execution_id: started.execution_id,
        status: started.status as ExecutionStatus['status'],
        stage: 'localization',
        warnings: [],
        result_metadata: null,
        error: null,
      })
    } catch (err: unknown) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  function toggleCluster(clusterId: string) {
    setHiddenClusters((previous) => {
      const next = new Set(previous)
      if (next.has(clusterId)) next.delete(clusterId)
      else next.add(clusterId)
      return next
    })
  }

  return (
    <div className="localization-page">
      <div className="localization-top-bar">
        <label htmlFor="localization-reid-select" className="field-label">
          REID Artifact <HelpTip text={HELP.reid_artifact} />
        </label>
        <select
          id="localization-reid-select"
          className="folder-select"
          value={selectedReid}
          onChange={(event) => {
            setSelectedReid(event.target.value)
            setResult(null)
            setExecution(null)
            setError(null)
          }}
          disabled={!session || loading || running}
        >
          <option value="">- Select REID artifact -</option>
          {(inventory?.reid_artifacts ?? []).map((artifact) => (
            <option key={artifact.filename} value={artifact.filename} dir="auto">
              {artifact.filename}
            </option>
          ))}
        </select>
      </div>

      {!session && <p className="empty-state">No active session. Go to Session Start to select a folder.</p>}
      {session && !calibrationApproved && (
        <div className="warning-banner">No approved calibration. Run and approve Calibration before Localization.</div>
      )}
      {error && <p className="error-banner">{error}</p>}

      <div className="localization-body">
        <div className="localization-left">
          <h1 className="page-title">Localization</h1>
          <div className="calibration-info">
            {calibrationApproved && calibration?.parameters
              ? `Using: ${calibration.parameter_source ?? 'approved'} calibration - n=${calibration.parameters.path_loss_n.toFixed(2)}, rssi_1m=${calibration.parameters.rssi_at_1m.toFixed(1)} dBm`
              : 'No calibration'}
          </div>

          <div className="settings-panel">
            <button className="settings-toggle-button" type="button" onClick={() => setSettingsOpen((value) => !value)}>
              Localization Settings {settingsOpen ? 'v' : '>'}
            </button>
            {settingsOpen && (
              <div className="localization-settings-grid">
                <label className="loc-param-row">
                  <span>
                    grid_resolution_m <HelpTip text={HELP.loc_grid_resolution_m} />
                  </span>
                  <input
                    type="number"
                    step="0.5"
                    min="0.5"
                    value={locSettings.grid_resolution_m}
                    onChange={(event) =>
                      setLocSettings((previous) => ({
                        ...previous,
                        grid_resolution_m: Math.max(0.5, Number(event.target.value)),
                      }))
                    }
                  />
                </label>
                <label className="loc-param-row">
                  <span>
                    dynamic_sigma_alpha <HelpTip text={HELP.loc_dynamic_sigma_alpha} />
                  </span>
                  <input
                    type="number"
                    step="0.01"
                    value={locSettings.dynamic_sigma_alpha}
                    onChange={(event) =>
                      setLocSettings((previous) => ({
                        ...previous,
                        dynamic_sigma_alpha: Number(event.target.value),
                      }))
                    }
                  />
                </label>
                <label className="loc-param-row">
                  <span>
                    confidence_cutoff <HelpTip text={HELP.loc_confidence_cutoff} />
                  </span>
                  <input
                    type="number"
                    step="0.01"
                    value={locSettings.confidence_cutoff}
                    onChange={(event) =>
                      setLocSettings((previous) => ({
                        ...previous,
                        confidence_cutoff: Number(event.target.value),
                      }))
                    }
                  />
                </label>
                <label className="loc-param-row">
                  <span>
                    participation_floor <HelpTip text={HELP.loc_uncertainty_participation_floor} />
                  </span>
                  <input
                    type="number"
                    step="0.01"
                    value={locSettings.uncertainty_participation_floor}
                    onChange={(event) =>
                      setLocSettings((previous) => ({
                        ...previous,
                        uncertainty_participation_floor: Number(event.target.value),
                      }))
                    }
                  />
                </label>
                <label className="loc-param-row">
                  <span>
                    uncertainty_alpha <HelpTip text={HELP.loc_uncertainty_alpha} />
                  </span>
                  <input
                    type="number"
                    step="0.01"
                    value={locSettings.uncertainty_alpha}
                    onChange={(event) =>
                      setLocSettings((previous) => ({
                        ...previous,
                        uncertainty_alpha: Number(event.target.value),
                      }))
                    }
                  />
                </label>
              </div>
            )}
          </div>

          <button className="btn-primary" disabled={!canRun} onClick={handleRun}>
            {running ? 'Localization running...' : 'Run Localization'}
          </button>

          {execution && running && (
            <p className="loading-hint">
              Localization running... <span className="mono">execution {execution.execution_id}</span>
            </p>
          )}

          {result && (
            <div className="cluster-summary">
              <div className="cluster-summary-header">
                <h2 className="panel-title">Clusters</h2>
                <div className="cluster-bulk-actions">
                  <button className="btn-text" onClick={() => setHiddenClusters(new Set())}>
                    Show all
                  </button>
                  <button
                    className="btn-text"
                    onClick={() => setHiddenClusters(new Set(result.cluster_results.map((cluster) => cluster.cluster_id)))}
                  >
                    Hide all
                  </button>
                </div>
              </div>
              <table className="cluster-table">
                <thead>
                  <tr>
                    <th></th>
                    <th></th>
                    <th>Cluster ID</th>
                    <th>
                      Type <HelpTip text={HELP.cluster_type_static} />
                    </th>
                    <th>Status</th>
                    <th>Samples</th>
                    <th>Peaks</th>
                    <th>
                      Radius (m) <HelpTip text={HELP.uncertainty_radius} />
                    </th>
                    <th>
                      Confidence <HelpTip text={HELP.cluster_confidence} />
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {result.cluster_results.map((cluster, index) => (
                    <tr
                      key={cluster.cluster_id}
                      className={hiddenClusters.has(cluster.cluster_id) ? 'cluster-row-hidden' : ''}
                    >
                      <td>
                        <div
                          className="cluster-swatch"
                          style={{ background: CLUSTER_COLORS[index % CLUSTER_COLORS.length] }}
                        />
                      </td>
                      <td>
                        <input
                          type="checkbox"
                          checked={!hiddenClusters.has(cluster.cluster_id)}
                          onChange={() => toggleCluster(cluster.cluster_id)}
                          aria-label={`Toggle cluster ${cluster.cluster_id}`}
                        />
                      </td>
                      <td className="mono">{cluster.cluster_id}</td>
                      <td>{cluster.cluster_type}</td>
                      <td>{cluster.status}</td>
                      <td>{cluster.sample_count}</td>
                      <td>{cluster.candidate_peaks.length}</td>
                      <td>{cluster.uncertainty_regions[0]?.radius_m.toFixed(1) ?? '-'}</td>
                      <td>
                        {cluster.cluster_type === 'static' ? (
                          <span className="conf-badge conf-static">static</span>
                        ) : (
                          confidenceBadge(session?.active_reid?.quality?.cluster_confidence?.[cluster.cluster_id])
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="localization-right">
          <div className="map-toggles">
            <label>
              <input
                type="checkbox"
                checked={showStaticClusters}
                onChange={(event) => setShowStaticClusters(event.target.checked)}
              />
              Show static clusters <HelpTip text={HELP.show_static_clusters} left />
            </label>
            <label>
              <input
                type="checkbox"
                checked={showNoiseClusters}
                onChange={(event) => setShowNoiseClusters(event.target.checked)}
              />
              Show noise cluster <HelpTip text={HELP.show_noise_cluster} left />
            </label>
          </div>
          <div className="map-controls">
            <span className="map-ctrl-section">Layers</span>
            <label className="map-control-check">
              <input type="checkbox" checked={showHeatmap} onChange={(e) => setShowHeatmap(e.target.checked)} />
              Heatmap — signal strength grid <HelpTip text={HELP.heatmap} left />
            </label>
            <label className="map-control-check">
              <input type="checkbox" checked={showUncertaintyRadii} onChange={(e) => setShowUncertaintyRadii(e.target.checked)} />
              Radii — uncertainty circles <HelpTip text={HELP.radii} left />
            </label>
            <label className="map-control-check">
              <input type="checkbox" checked={showPeaks} onChange={(e) => setShowPeaks(e.target.checked)} />
              Peaks — estimated positions <HelpTip text={HELP.peaks} left />
            </label>
            <div className="map-controls-divider" />
            <span className="map-ctrl-section">Heatmap settings</span>
            <div className="map-ctrl-pair">
              <span className="map-ctrl-label">Dot stride</span>
              <input
                type="number" min={1} max={20} step={1}
                value={heatmapStride}
                onChange={(e) => setHeatmapStride(Math.min(20, Math.max(1, Number(e.target.value))))}
                className="heatmap-stride-input"
                title="Show every Nth dot. 1 = all dots (~2 m apart at default grid). 5 = every 5th dot (~10 m apart)."
              />
            </div>
            <div className="map-controls-divider" />
            {!lassoPolygon ? (
              <button
                className={`lasso-btn${lassoActive ? ' active' : ''}`}
                onClick={() => setLassoActive((value) => !value)}
                title="Draw a freehand zone to filter clusters"
              >
                {lassoActive ? 'Drawing...' : 'Select Zone'}
              </button>
            ) : (
              <>
                <span className="zone-badge">{zoneClusterCount} clusters in zone</span>
                <button
                  className="layer-btn"
                  onClick={() => {
                    setLassoPolygon(null)
                    setLassoActive(false)
                  }}
                >
                  Clear Zone
                </button>
              </>
            )}
            <div className="map-controls-divider" />
            <div className="layer-toggle">
              <button className={`layer-btn${mapLayer === 'satellite' ? ' active' : ''}`} onClick={() => setMapLayer('satellite')}>
                Satellite
              </button>
              <button className={`layer-btn${mapLayer === 'osm' ? ' active' : ''}`} onClick={() => setMapLayer('osm')}>
                Map
              </button>
            </div>
          </div>

          <MapContainer center={mapCenter} zoom={15} maxZoom={23} className={`localization-map${lassoActive ? ' lasso-mode' : ''}`}>
            {result && <FitBoundsOnResult bounds={result.bounds} />}
            {mapLayer === 'satellite' ? (
              <TileLayer
                key="satellite"
                attribution='Tiles &copy; Esri &mdash; Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, GIS User Community'
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                maxNativeZoom={18}
                maxZoom={23}
              />
            ) : (
              <TileLayer
                key="osm"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                maxNativeZoom={19}
                maxZoom={23}
              />
            )}

            {showHeatmap &&
              visibleClusters.flatMap((cluster) =>
                cluster.status === 'success'
                  ? cluster.grid_cells.filter((_, index) => index % heatmapStride === 0).map((cell, index) => (
                      <CircleMarker
                        key={`${cluster.cluster_id}-cell-${index}`}
                        center={[cell.lat, cell.lon]}
                        radius={3}
                        pathOptions={{
                          fillColor: heatColor(cell.value),
                          fillOpacity: cell.value * 0.7,
                          weight: 0,
                          color: heatColor(cell.value),
                        }}
                      />
                    ))
                  : [],
              )}

            {showUncertaintyRadii &&
              visibleClusters.flatMap((cluster) =>
                cluster.uncertainty_regions.map((region, index) => (
                  <Circle
                    key={`${cluster.cluster_id}-radius-${index}`}
                    center={[region.center_lat, region.center_lon]}
                    radius={region.radius_m}
                    pathOptions={{ color: 'rgba(255,200,0,0.8)', fillOpacity: 0.1, weight: 2 }}
                  />
                )),
              )}

            {showPeaks &&
              visibleClusters.map((cluster, index) =>
                cluster.primary_peak ? (
                  <CircleMarker
                    key={`${cluster.cluster_id}-peak`}
                    center={[cluster.primary_peak.lat, cluster.primary_peak.lon]}
                    radius={8}
                    pathOptions={{
                      color: CLUSTER_COLORS[index % CLUSTER_COLORS.length],
                      fillColor: CLUSTER_COLORS[index % CLUSTER_COLORS.length],
                      fillOpacity: 0.9,
                      weight: 2,
                    }}
                  >
                    <Tooltip>
                      Cluster {cluster.cluster_id} - peak value {cluster.primary_peak.value.toFixed(3)}
                    </Tooltip>
                  </CircleMarker>
                ) : null,
              )}
            {result && (
              <Rectangle
                bounds={[[result.bounds.lat_min, result.bounds.lon_min], [result.bounds.lat_max, result.bounds.lon_max]]}
                pathOptions={{ color: '#94a3b8', weight: 1.5, dashArray: '6 4', fillOpacity: 0, opacity: 0.7 }}
              />
            )}
            {lassoPolygon && (
              <Polygon
                positions={lassoPolygon}
                pathOptions={{
                  color: '#facc15',
                  weight: 2,
                  dashArray: '8 5',
                  fillOpacity: 0.06,
                  opacity: 0.9,
                }}
              />
            )}
            <LassoTool
              active={lassoActive}
              onComplete={(polygon) => {
                setLassoPolygon(polygon)
                setLassoActive(false)
                setShowHeatmap(true)
                setShowUncertaintyRadii(true)
                setShowPeaks(true)
              }}
              onCancel={() => setLassoActive(false)}
            />
          </MapContainer>
        </div>
      </div>
    </div>
  )
}

function FitBoundsOnResult({ bounds }: { bounds: { lat_min: number; lat_max: number; lon_min: number; lon_max: number } }) {
  const map = useMap()
  useEffect(() => {
    map.fitBounds(
      [[bounds.lat_min, bounds.lon_min], [bounds.lat_max, bounds.lon_max]],
      { padding: [40, 40], maxZoom: 19 },
    )
  }, [bounds.lat_min, bounds.lat_max, bounds.lon_min, bounds.lon_max, map])
  return null
}

function heatColor(value: number): string {
  const h = (1 - Math.max(0, Math.min(1, value))) * 240
  return `hsl(${h.toFixed(0)}, 100%, 50%)`
}
