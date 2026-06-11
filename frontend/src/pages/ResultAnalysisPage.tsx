import { useEffect, useMemo, useRef, useState } from 'react'
import { divIcon } from 'leaflet'
import { Circle, CircleMarker, MapContainer, Marker, Polygon, Polyline, Rectangle, TileLayer, Tooltip, useMap, useMapEvents } from 'react-leaflet'
import {
  addGtPoint,
  deleteGtPoint,
  getExecution,
  getResultAnalysis,
  importGtPoints,
  rerunFromResultAnalysis,
  runEvaluation,
  type ExecutionStatus,
  type EvaluationResult,
  type GtPoint,
  type LocalizationRunResult,
  type ResultAnalysisState,
} from '../api/sessions'
import HelpTip from '../components/HelpTip'
import { HELP } from '../helpTexts'
import { useSession } from '../state/SessionContext'
import { circleIntersectionAreaM2, pointInPolygon, polygonAreaM2 } from '../utils/geoUtils'
import './ResultAnalysisPage.css'

type MapLayer = 'satellite' | 'osm'

const CLUSTER_COLORS = ['#1f6feb', '#15803d', '#b45309', '#b91c1c', '#7c3aed', '#0f766e']

export default function ResultAnalysisPage() {
  const { session, refreshSession, lassoPolygon, setLassoPolygon } = useSession()
  const [raState, setRaState] = useState<ResultAnalysisState | null>(null)
  const [evalResult, setEvalResult] = useState<EvaluationResult | null>(null)
  const [addingGt, setAddingGt] = useState(false)
  const [gtColors, setGtColors] = useState<Record<string, string>>({})
  const [mapLayer, setMapLayer] = useState<MapLayer>('satellite')
  const [showHeatmap, setShowHeatmap] = useState(true)
  const [showUncertaintyRadii, setShowUncertaintyRadii] = useState(true)
  const [showPeaks, setShowPeaks] = useState(true)
  const [heatmapStride, setHeatmapStride] = useState(1)
  const [showStaticClusters, setShowStaticClusters] = useState(true)
  const [hiddenClusters, setHiddenClusters] = useState<Set<string>>(new Set())
  const [expectedEmitters, setExpectedEmitters] = useState<number | ''>(1)
  const [circleOverlapThreshold, setCircleOverlapThreshold] = useState(0.20)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rerunStatus, setRerunStatus] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const csvInputRef = useRef<HTMLInputElement | null>(null)
  const [evalParams, setEvalParams] = useState({
    ratio_gate: 1.2,
    max_match_dist_m: 30,
    r_normalize_m: 30.0,
    d_free_m: 10.0,
    w_containment: 0.4,
    w_distance: 0.3,
    w_count: 0.2,
    w_radius: 0.1,
  })
  const [rerunStage, setRerunStage] = useState<'localization' | 'reid' | 'enrichment'>('localization')
  const [enrichmentParams, setEnrichmentParams] = useState({
    match_threshold: 0.3,
    time_window_ms: 1000.0,
    time_score_weight: 1.0,
    identity_score_weight: 1.0,
    context_weight: 0.5,
  })
  const [localizationParams, setLocalizationParams] = useState({
    grid_resolution_m: 2.0,
    dynamic_sigma_alpha: 0.05,
    confidence_cutoff: 0.75,
    uncertainty_participation_floor: 0.8,
    uncertainty_alpha: 1.5,
    buffer_m: 25.0,
  })
  const [reidParams, setReidParams] = useState({
    association_threshold: 0.6,
    seq_gap_max: 64,
    time_gap_max_sec: 30,
    burst_window_sec: 60,
    probe_requests_only: false,
  })

  function confidenceBadge(tier: string | undefined) {
    if (!tier) return null
    const cls = tier === 'high' ? 'conf-high' : tier === 'medium' ? 'conf-medium' : 'conf-low'
    return <span className={`conf-badge ${cls}`}>{tier}</span>
  }

  const localization = (session?.current_localization_result ?? session?.active_localization ?? null) as LocalizationRunResult | null
  const successfulClusters = useMemo(
    () => (localization?.cluster_results ?? []).filter((cluster) => cluster.status === 'success' && cluster.primary_peak),
    [localization],
  )
  const zoneClusterIds = useMemo<Set<string> | null>(() => {
    if (!lassoPolygon) return null
    return new Set(
      successfulClusters
        .filter((cluster) => cluster.primary_peak != null && pointInPolygon(cluster.primary_peak.lat, cluster.primary_peak.lon, lassoPolygon))
        .map((cluster) => cluster.cluster_id),
    )
  }, [successfulClusters, lassoPolygon])
  const visibleClusterIds = useMemo(
    () =>
      new Set(
        successfulClusters
          .filter((cluster) => showStaticClusters || cluster.cluster_type !== 'static')
          .filter((cluster) => !hiddenClusters.has(cluster.cluster_id))
          .filter((cluster) => !zoneClusterIds || zoneClusterIds.has(cluster.cluster_id))
          .map((cluster) => cluster.cluster_id),
      ),
    [successfulClusters, showStaticClusters, hiddenClusters, zoneClusterIds],
  )
  const visibleClusters = useMemo(
    () => successfulClusters.filter((cluster) => visibleClusterIds.has(cluster.cluster_id)),
    [successfulClusters, visibleClusterIds],
  )
  const zoneGtIds = useMemo<Set<string> | null>(() => {
    if (!lassoPolygon || !raState?.gt_points) return null
    return new Set(
      raState.gt_points
        .filter((point) => pointInPolygon(point.lat, point.lon, lassoPolygon))
        .map((point) => point.gt_id),
    )
  }, [raState?.gt_points, lassoPolygon])
  const test1 = useMemo(() => {
    if (!lassoPolygon || typeof expectedEmitters !== 'number' || expectedEmitters < 1) return null

    // Count circles (across all uncertainty_regions) where ≥ circleOverlapThreshold of the circle
    // is inside the zone. Only clusters whose peak is inside the zone (visibleClusters) are considered.
    let nCircles = 0
    for (const cluster of visibleClusters) {
      for (const region of cluster.uncertainty_regions) {
        if (region.radius_m <= 0) continue
        const fullArea = Math.PI * region.radius_m * region.radius_m
        const inArea = circleIntersectionAreaM2(region.center_lat, region.center_lon, region.radius_m, lassoPolygon)
        if (inArea / fullArea >= circleOverlapThreshold) nCircles++
      }
    }
    const nExpected = expectedEmitters
    const sCount = Math.max(0, 1 - Math.abs(nCircles - nExpected) / nExpected)
    const lassoArea = polygonAreaM2(lassoPolygon)
    // Area = sum of intersection areas for all circles of qualifying clusters.
    const circleArea = visibleClusters.reduce((sum, cluster) => {
      return sum + cluster.uncertainty_regions.reduce((s, region) => {
        if (region.radius_m <= 0) return s
        return s + circleIntersectionAreaM2(region.center_lat, region.center_lon, region.radius_m, lassoPolygon)
      }, 0)
    }, 0)
    const areaRatio = lassoArea > 0 ? circleArea / lassoArea : 1
    const sArea = Math.max(0, 1 - areaRatio * areaRatio)
    const total = (sCount + sArea) / 2

    return { total, sCount, sArea, nCircles, nExpected, circleArea, lassoArea, areaRatio }
  }, [lassoPolygon, expectedEmitters, circleOverlapThreshold, visibleClusters])
  const combinedScore = useMemo(() => {
    if (!test1 || !evalResult) return null
    return (test1.total + evalResult.score.total) / 2
  }, [test1, evalResult])
  const mapCenter: [number, number] = localization
    ? [(localization.bounds.lat_min + localization.bounds.lat_max) / 2, (localization.bounds.lon_min + localization.bounds.lon_max) / 2]
    : [32.0, 34.8]
  const possibleMergeIds = new Set(evalResult?.possible_merges.map((merge) => merge.cluster_id) ?? [])
  const falsePositiveIds = useMemo(() => new Set(evalResult?.false_positives.map((fp) => fp.cluster_id) ?? []), [evalResult])
  const falseNegativeIds = useMemo(() => new Set(evalResult?.false_negatives.map((fn) => fn.gt_id) ?? []), [evalResult])
  const fpSquareIcon = useMemo(
    () =>
      divIcon({
        className: 'fp-square-marker',
        html: '<span></span>',
        iconSize: [12, 12],
        iconAnchor: [6, 6],
      }),
    [],
  )
  const clusterColor = (clusterId: string) => {
    const index = successfulClusters.findIndex((cluster) => cluster.cluster_id === clusterId)
    return CLUSTER_COLORS[Math.max(index, 0) % CLUSTER_COLORS.length]
  }

  useEffect(() => {
    void loadState()
  }, [session?.session_id])

  useEffect(() => {
    const count = raState?.gt_points?.length ?? 0
    if (count > 0) setExpectedEmitters(count)
  }, [raState?.gt_points?.length])

  async function loadState() {
    if (!session?.session_id) {
      setRaState(null)
      setEvalResult(null)
      return
    }
    setError(null)
    try {
      const state = await getResultAnalysis(session.session_id)
      setRaState(state)
      setEvalResult(state.last_evaluation)
    } catch (err: unknown) {
      setError(String(err))
    }
  }

  async function handleAddGt(point: { lat: number; lon: number }) {
    if (!session?.session_id) return
    setLoading(true)
    setError(null)
    try {
      await addGtPoint(session.session_id, point.lat, point.lon)
      await loadState()
    } catch (err: unknown) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  async function handleDeleteGt(point: GtPoint) {
    if (!session?.session_id) return
    setLoading(true)
    setError(null)
    try {
      await deleteGtPoint(session.session_id, point.gt_id)
      await loadState()
    } catch (err: unknown) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  async function handleImportCsv(file: File | undefined) {
    if (!session?.session_id || !file) return
    setLoading(true)
    setError(null)
    try {
      const text = await file.text()
      const lines = text.split('\n').filter((line) => line.trim())
      if (lines.length < 2) throw new Error('CSV has no data rows')
      const headers = parseCsvRow(lines[0]).map((h) => h.trim().toLowerCase())
      const latIdx = headers.indexOf('gps_lat') !== -1 ? headers.indexOf('gps_lat') : headers.indexOf('lat')
      const lonIdx = headers.indexOf('gps_lon') !== -1 ? headers.indexOf('gps_lon') : headers.indexOf('lon')
      const gpsFixIdx = headers.indexOf('gps_fix')
      if (latIdx === -1 || lonIdx === -1) throw new Error('CSV must have gps_lat/gps_lon or lat/lon columns')
      let sumLat = 0,
        sumLon = 0,
        count = 0
      for (const line of lines.slice(1)) {
        const cols = parseCsvRow(line)
        if (gpsFixIdx !== -1 && cols[gpsFixIdx]?.trim() !== '1') continue
        const lat = parseFloat(cols[latIdx])
        const lon = parseFloat(cols[lonIdx])
        if (!isNaN(lat) && !isNaN(lon)) {
          sumLat += lat
          sumLon += lon
          count++
        }
      }
      if (count === 0) throw new Error('No valid GPS rows found in CSV')
      const label = file.name.replace(/\.[^.]+$/, '')
      await addGtPoint(session.session_id, sumLat / count, sumLon / count, label)
      await loadState()
    } catch (err: unknown) {
      setError(String(err))
    } finally {
      setLoading(false)
      if (csvInputRef.current) csvInputRef.current.value = ''
    }
  }

  async function handleImport(file: File | undefined) {
    if (!session?.session_id || !file) return
    setLoading(true)
    setError(null)
    try {
      const text = await file.text()
      const points = JSON.parse(text) as Array<{ lat: number; lon: number; label?: string }>
      await importGtPoints(session.session_id, points)
      await loadState()
    } catch (err: unknown) {
      setError(String(err))
    } finally {
      setLoading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  async function handleEvaluate() {
    if (!session?.session_id) return
    setLoading(true)
    setError(null)
    try {
      const params: Parameters<typeof runEvaluation>[1] = { ...evalParams }
      if (zoneClusterIds) params.cluster_ids = [...zoneClusterIds]
      if (zoneGtIds) params.gt_ids = [...zoneGtIds]
      const result = await runEvaluation(session.session_id, params)
      setEvalResult(result)
      await loadState()
    } catch (err: unknown) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  async function handleRerun() {
    if (!session?.session_id) return
    setLoading(true)
    setError(null)
    setRerunStatus(null)
    try {
      const started = await rerunFromResultAnalysis(
        session.session_id,
        rerunStage,
        localizationParams,
        rerunStage === 'reid' || rerunStage === 'enrichment' ? reidParams : undefined,
        rerunStage === 'enrichment' ? enrichmentParams : undefined,
      )
      const executionId = started.execution_id ?? started.localization_execution_id
      if (executionId) {
        setRerunStatus(`${started.status}: ${executionId}`)
        const execution = await waitForExecution(executionId, setRerunStatus)
        setRerunStatus(`rerun ${execution.status}`)
        if (execution.status === 'failed') {
          setError(execution.error ?? 'Rerun failed')
        }
      } else {
        setRerunStatus(started.status)
      }
      await refreshSession()
      await loadState()
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
    <div className="result-analysis-page">
      <div className="result-analysis-header">
        <h1 className="page-title">Result Analysis</h1>
        <span className="research-tag">Research / Tuning</span>
      </div>

      {!session && <p className="empty-state">No active session. Go to Session Start to select a folder.</p>}
      {error && <p className="error-banner">{error}</p>}

      <div className="result-analysis-layout">
        <aside className="result-analysis-left">
          <section className="ra-panel">
            <h2 className="panel-title">
              Ground Truth <HelpTip text={HELP.ground_truth} />
            </h2>
            <button className="btn-secondary" disabled={!session || loading} onClick={() => setAddingGt((value) => !value)}>
              {addingGt ? 'Click on map...' : 'Add from map'}
            </button>
            <button className="btn-secondary" disabled={!session || loading} onClick={() => fileInputRef.current?.click()}>
              Import JSON
            </button>
            <button className="btn-secondary" disabled={!session || loading} onClick={() => csvInputRef.current?.click()}>
              Import CSV (mean GPS)
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".json,application/json"
              hidden
              onChange={(event) => void handleImport(event.target.files?.[0])}
            />
            <input
              ref={csvInputRef}
              type="file"
              accept=".csv,text/csv"
              hidden
              onChange={(event) => void handleImportCsv(event.target.files?.[0])}
            />
            <div className="gt-list">
              {(raState?.gt_points ?? []).map((point, index) => (
                <div key={point.gt_id} className="gt-row">
                  <input
                    type="color"
                    className="gt-color-picker"
                    value={gtColors[point.gt_id] ?? '#ef4444'}
                    onChange={(event) => setGtColors((prev) => ({ ...prev, [point.gt_id]: event.target.value }))}
                    title="GT marker color"
                  />
                  <span>
                    {point.label || `GT #${index + 1}`} {point.lat.toFixed(5)}, {point.lon.toFixed(5)}
                  </span>
                  <button className="btn-icon" onClick={() => void handleDeleteGt(point)} aria-label={`Delete GT ${index + 1}`}>
                    x
                  </button>
                </div>
              ))}
            </div>
          </section>

          <section className="ra-panel">
            <h2 className="panel-title">Evaluation</h2>
            <div className="eval-param-row">
              <label>
                Ratio gate <HelpTip text={HELP.ratio_gate} />
              </label>
              <input
                type="number"
                step="0.1"
                min="1.0"
                value={evalParams.ratio_gate ?? 1.2}
                onChange={(event) => setEvalParams((previous) => ({ ...previous, ratio_gate: Number(event.target.value) }))}
              />
            </div>
            <p className="eval-param-hint">
              Lower = more permissive. 1.0 = always match nearest. 2.0 = strict (nearest must be 2x closer than second-nearest).
            </p>
            <div className="eval-param-row">
              <label>
                Max match dist (m) <HelpTip text={HELP.max_match_dist_m} />
              </label>
              <input
                type="number"
                step="10"
                min="0"
                value={evalParams.max_match_dist_m ?? 30}
                onChange={(event) => setEvalParams((previous) => ({ ...previous, max_match_dist_m: Number(event.target.value) }))}
              />
            </div>
            <div className="eval-param-row">
              <label>
                Free zone (m) <HelpTip text={HELP.d_free_m} />
              </label>
              <input
                type="number"
                step="1"
                min="0"
                value={evalParams.d_free_m}
                onChange={(event) => setEvalParams((previous) => ({ ...previous, d_free_m: Number(event.target.value) }))}
              />
            </div>
            <div className="eval-param-row">
              <label>
                Penalty scale (m) <HelpTip text={HELP.r_normalize_m} />
              </label>
              <input
                type="number"
                step="1"
                min="1"
                value={evalParams.r_normalize_m}
                onChange={(event) => setEvalParams((previous) => ({ ...previous, r_normalize_m: Number(event.target.value) }))}
              />
            </div>
            <p className="eval-param-hint">
              Distance/Radius: ≤ free zone → 100%. Beyond: score = 1 − ((d − free zone) / penalty scale)².
            </p>
            {(['w_containment', 'w_distance', 'w_count', 'w_radius'] as const).map((key) => (
              <label key={key} className="eval-param-row">
                <span>
                  {key} <HelpTip text={HELP[key]} />
                </span>
                <input
                  type="number"
                  step="0.1"
                  value={evalParams[key]}
                  onChange={(event) => setEvalParams((previous) => ({ ...previous, [key]: Number(event.target.value) }))}
                />
              </label>
            ))}
            <div className="eval-param-row">
              <label>
                Expected emitters (Test 1) <HelpTip text={HELP.expected_emitters} />
              </label>
              <input
                type="number"
                min="1"
                step="1"
                value={expectedEmitters}
                onChange={(event) => {
                  if (event.target.value === '') {
                    setExpectedEmitters('')
                    return
                  }
                  const nextValue = parseInt(event.target.value, 10)
                  setExpectedEmitters(Number.isNaN(nextValue) ? '' : Math.max(1, nextValue))
                }}
              />
            </div>
            <div className="eval-param-row">
              <label>
                Circle overlap threshold (Test 1) <HelpTip text={HELP.circle_overlap_threshold} />
              </label>
              <input
                type="number"
                min="0.01"
                max="1"
                step="0.05"
                value={circleOverlapThreshold}
                onChange={(event) => setCircleOverlapThreshold(Math.min(1, Math.max(0.01, Number(event.target.value))))}
              />
            </div>
            <button className="btn-primary" disabled={!session || loading || !raState?.localization_available} onClick={handleEvaluate}>
              Run Evaluation
            </button>
          </section>

          <section className="ra-panel">
            <div className="cluster-summary-header">
              <h2 className="panel-title">
                Clusters <HelpTip text={HELP.cluster_confidence} />
              </h2>
              <div className="cluster-bulk-actions">
                <button className="btn-text" onClick={() => setHiddenClusters(new Set())}>
                  Show all
                </button>
                <button className="btn-text" onClick={() => setHiddenClusters(new Set(successfulClusters.map((cluster) => cluster.cluster_id)))}>
                  Hide all
                </button>
              </div>
            </div>
            <label className="map-control-check cluster-static-toggle">
              <input
                type="checkbox"
                checked={showStaticClusters}
                onChange={(event) => setShowStaticClusters(event.target.checked)}
              />
              Show static
            </label>
            <div className="cluster-list">
              {successfulClusters.map((cluster) => (
                <label
                  key={cluster.cluster_id}
                  className={[
                    'cluster-row',
                    hiddenClusters.has(cluster.cluster_id) ? 'cluster-row-hidden' : '',
                    zoneClusterIds && !zoneClusterIds.has(cluster.cluster_id) ? 'cluster-row-out-of-zone' : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                >
                  <span className="cluster-swatch" style={{ background: clusterColor(cluster.cluster_id) }} />
                  <input
                    type="checkbox"
                    checked={!hiddenClusters.has(cluster.cluster_id)}
                    onChange={() => toggleCluster(cluster.cluster_id)}
                  />
                  <span className="cluster-confidence-slot">
                    {cluster.cluster_type === 'static'
                      ? null
                      : confidenceBadge(session?.active_reid?.quality?.cluster_confidence?.[cluster.cluster_id])}
                  </span>
                  <span className="mono">{cluster.cluster_id}</span>
                  <span>{cluster.uncertainty_regions[0]?.radius_m.toFixed(1) ?? '-'}m</span>
                </label>
              ))}
              {successfulClusters.length === 0 && <p className="empty-state">No successful clusters.</p>}
            </div>
          </section>

          <section className="ra-panel">
            <h2 className="panel-title">Rerun</h2>
            <div className="stage-selector">
              <label>
                <input
                  type="radio"
                  checked={rerunStage === 'localization'}
                  onChange={() => setRerunStage('localization')}
                />
                Localization only
              </label>
              <label>
                <input type="radio" checked={rerunStage === 'reid'} onChange={() => setRerunStage('reid')} />
                Re-ID + Loc
              </label>
              <label>
                <input
                  type="radio"
                  checked={rerunStage === 'enrichment'}
                  onChange={() => setRerunStage('enrichment')}
                />
                Enrichment + Re-ID + Loc
              </label>
            </div>
            <h3 className="param-heading">
              Localization params <HelpTip text={HELP.loc_grid_resolution_m} />
            </h3>
            {Object.entries(localizationParams).map(([key, value]) => (
              <label key={key} className="param-row">
                <span>
                  {key} <HelpTip text={localizationHelpText(key)} left />
                </span>
                <input
                  type="number"
                  step="0.01"
                  value={value}
                  onChange={(event) =>
                    setLocalizationParams((previous) => ({ ...previous, [key]: Number(event.target.value) }))
                  }
                />
              </label>
            ))}
            {rerunStage === 'enrichment' && (
              <>
                <h3 className="param-heading">Enrichment params</h3>
                {Object.entries(enrichmentParams).map(([key, value]) => (
                  <label key={key} className="param-row">
                    <span className="mono">{key}</span>
                    <input
                      type="number"
                      step="any"
                      value={value}
                      onChange={(event) =>
                        setEnrichmentParams((previous) => ({ ...previous, [key]: parseFloat(event.target.value) }))
                      }
                    />
                  </label>
                ))}
              </>
            )}
            {(rerunStage === 'reid' || rerunStage === 'enrichment') && (
              <>
                <h3 className="param-heading">Re-ID params</h3>
                {Object.entries(reidParams)
                  .filter(([key]) => key !== 'probe_requests_only')
                  .map(([key, value]) => (
                    <label key={key} className="param-row">
                      <span>
                        {key} <HelpTip text={reidHelpText(key)} left />
                      </span>
                      <input
                        type="number"
                        step="0.01"
                        value={value as number}
                        onChange={(event) => setReidParams((previous) => ({ ...previous, [key]: Number(event.target.value) }))}
                      />
                    </label>
                  ))}
                <label className="param-row">
                  <span>
                    probe_requests_only <HelpTip text={HELP.reid_probe_requests_only} left />
                  </span>
                  <input
                    type="checkbox"
                    checked={reidParams.probe_requests_only}
                    onChange={(event) => setReidParams((previous) => ({ ...previous, probe_requests_only: event.target.checked }))}
                  />
                </label>
              </>
            )}
            <button className="btn-secondary" disabled={!session || loading} onClick={handleRerun}>
              Rerun
            </button>
            {rerunStatus && <p className="loading-hint">{rerunStatus}</p>}
          </section>
        </aside>

        <main className="result-analysis-main">
          <div className="map-controls">
            <span className="map-ctrl-section">Layers</span>
            <label className="map-control-check">
              <input type="checkbox" checked={showHeatmap} onChange={(event) => setShowHeatmap(event.target.checked)} />
              Heatmap — signal strength grid <HelpTip text={HELP.heatmap} left />
            </label>
            <label className="map-control-check">
              <input type="checkbox" checked={showUncertaintyRadii} onChange={(event) => setShowUncertaintyRadii(event.target.checked)} />
              Radii — uncertainty circles <HelpTip text={HELP.radii} left />
            </label>
            <label className="map-control-check">
              <input type="checkbox" checked={showPeaks} onChange={(event) => setShowPeaks(event.target.checked)} />
              Peaks — estimated positions <HelpTip text={HELP.peaks} left />
            </label>
            <div className="map-controls-divider" />
            <span className="map-ctrl-section">Heatmap settings</span>
            <div className="map-ctrl-pair">
              <span className="map-ctrl-label">Dot stride</span>
              <input
                type="number" min={1} max={20} step={1}
                value={heatmapStride}
                onChange={(event) => setHeatmapStride(Math.min(20, Math.max(1, Number(event.target.value))))}
                className="heatmap-stride-input"
                title="Show every Nth dot. 1 = all dots (~2 m apart at default grid). 5 = every 5th dot (~10 m apart)."
              />
            </div>
            <div className="map-controls-divider" />
            <div className="map-legend">
              <span className="legend-ambiguous-gt" aria-hidden="true" />
              <span>
                Ambiguous GT <HelpTip text={HELP.ambiguous_gt} left />
              </span>
            </div>
            <div className="map-controls-divider" />
            <div className="layer-toggle">
              <button className={`layer-btn${mapLayer === 'satellite' ? ' active' : ''}`} onClick={() => setMapLayer('satellite')}>
                Satellite
              </button>
              <button className={`layer-btn${mapLayer === 'osm' ? ' active' : ''}`} onClick={() => setMapLayer('osm')}>
                Map
              </button>
            </div>
            <div className="map-controls-divider" />
            {lassoPolygon ? (
              <>
                <span className="zone-badge">{visibleClusters.length} clusters in zone</span>
                <button
                  className="layer-btn"
                  onClick={() => {
                    setLassoPolygon(null)
                    setEvalResult(null)
                  }}
                >
                  Clear Zone
                </button>
              </>
            ) : (
              <span className="zone-badge-empty">No zone - draw on Localization page</span>
            )}
          </div>
          <MapContainer center={mapCenter} zoom={15} maxZoom={23} className={`result-analysis-map${addingGt ? ' gt-adding-mode' : ''}`}>
            {localization && <SetView center={mapCenter} zoom={16} />}
            {mapLayer === 'satellite' ? (
              <TileLayer
                attribution="Tiles &copy; Esri"
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                maxNativeZoom={18}
                maxZoom={23}
              />
            ) : (
              <TileLayer
                attribution="&copy; OpenStreetMap"
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                maxNativeZoom={19}
                maxZoom={23}
              />
            )}
            <GtClickHandler enabled={addingGt} onAdd={handleAddGt} />
            {localization && (
              <Rectangle
                bounds={[[localization.bounds.lat_min, localization.bounds.lon_min], [localization.bounds.lat_max, localization.bounds.lon_max]]}
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
            {showHeatmap &&
              successfulClusters.flatMap((cluster) =>
                (visibleClusterIds.has(cluster.cluster_id) ? cluster.grid_cells : []).filter((_, idx) => idx % heatmapStride === 0).map((cell, idx) => (
                  <CircleMarker
                    key={`${cluster.cluster_id}-cell-${idx}`}
                    center={[cell.lat, cell.lon]}
                    radius={3}
                    pathOptions={{
                      fillColor: heatColor(cell.value),
                      fillOpacity: cell.value * 0.7,
                      weight: 0,
                      color: heatColor(cell.value),
                    }}
                  />
                )),
              )}
            {showUncertaintyRadii &&
              visibleClusters.map((cluster) => (
                <ClusterRadii
                  key={cluster.cluster_id}
                  cluster={cluster}
                  color={falsePositiveIds.has(cluster.cluster_id) ? '#f97316' : clusterColor(cluster.cluster_id)}
                  dashed={falsePositiveIds.has(cluster.cluster_id)}
                />
              ))}
            {showPeaks &&
              visibleClusters.map((cluster) => (
                <ClusterPeak key={cluster.cluster_id} cluster={cluster} color={clusterColor(cluster.cluster_id)} />
              ))}
            {evalResult?.false_positives
              .filter((fp) => visibleClusterIds.has(fp.cluster_id))
              .map((fp) => (
                <Marker key={`fp-${fp.cluster_id}`} position={[fp.lat, fp.lon]} icon={fpSquareIcon}>
                  <Tooltip>FP: cluster {fp.cluster_id}</Tooltip>
                </Marker>
              ))}
            {(raState?.gt_points ?? []).map((point) => {
              const gtColor = gtColors[point.gt_id] ?? '#ef4444'
              const isFn = falseNegativeIds.has(point.gt_id)
              const isOutOfZone = zoneGtIds !== null && !zoneGtIds.has(point.gt_id)
              const markerOpacity = isOutOfZone ? 0.3 : 1
              const markerFillOpacity = isOutOfZone ? 0.2 : isFn ? 0.15 : 0.92
              return (
                <CircleMarker
                  key={point.gt_id}
                  center={[point.lat, point.lon]}
                  radius={8}
                  pathOptions={
                    isFn
                      ? {
                          color: 'white',
                          fillColor: gtColor,
                          fillOpacity: markerFillOpacity,
                          opacity: markerOpacity,
                          weight: 2.5,
                          dashArray: '5 4',
                        }
                      : {
                          color: 'white',
                          fillColor: gtColor,
                          fillOpacity: markerFillOpacity,
                          opacity: markerOpacity,
                          weight: 2.5,
                        }
                  }
                >
                  <Tooltip>
                    {isFn ? 'FN: ' : ''}
                    {point.label || point.gt_id.slice(0, 8)}
                  </Tooltip>
                </CircleMarker>
              )
            })}
            {evalResult?.ambiguous_gts?.map((ag) => (
              <CircleMarker
                key={`ambig-${ag.gt_id}`}
                center={[ag.lat, ag.lon]}
                radius={8}
                pathOptions={{ color: '#f97316', fillColor: '#f97316', fillOpacity: 0, weight: 3, dashArray: '6 4' }}
              >
                <Tooltip>
                  <div>
                    <strong>Ambiguous GT{ag.label ? `: ${ag.label}` : ''}</strong>
                    <br />
                    Nearest: {ag.nearest_dist_m.toFixed(1)}m
                    <br />
                    Competing: {ag.competing_cluster_ids.join(', ')}
                  </div>
                </Tooltip>
              </CircleMarker>
            ))}
            {evalResult?.matches.filter((match) => visibleClusterIds.has(match.primary_cluster_id)).map((match) => (
              <Polyline
                key={`${match.gt_id}-${match.primary_cluster_id}`}
                positions={[
                  [match.cluster_lat, match.cluster_lon],
                  [match.gt_lat, match.gt_lon],
                ]}
                pathOptions={{
                  color: match.association_status === 'clear_match' ? '#16a34a' : '#f59e0b',
                  dashArray: '5 6',
                  weight: 2,
                }}
              />
            ))}
          </MapContainer>
        </main>
      </div>

      {test1 && (
        <section className="score-panel test1-panel">
          <div>
            <div className="score-label">Test 1 — SAR Operational</div>
            <div className="score-total">{(test1.total * 100).toFixed(1)}%</div>
          </div>
          <div className="score-grid">
            <div className="score-item">
              <span>Count ({test1.nCircles} circles / {test1.nExpected} expected)</span>
              <strong>{(test1.sCount * 100).toFixed(1)}%</strong>
            </div>
            <div className="score-item">
              <span>Area ({(test1.areaRatio * 100).toFixed(1)}% of zone)</span>
              <strong>{(test1.sArea * 100).toFixed(1)}%</strong>
            </div>
          </div>
          <div className="reliability-note">
            Zone: {(test1.lassoArea / 1e6).toFixed(4)} km² &nbsp;|&nbsp; Circles: {(test1.circleArea / 1e6).toFixed(4)} km²
          </div>
        </section>
      )}

      {evalResult && (
        <>
          <section className="score-panel test2-panel">
            <div>
              <div className="score-label">Test 2 — Research</div>
              <div className="score-total">{(evalResult.score.total * 100).toFixed(1)}%</div>
            </div>
            <div className="score-grid">
              <ScoreItem label="Containment" value={evalResult.score.containment} helpText={HELP.score_containment} />
              <ScoreItem label="Distance" value={evalResult.score.distance} helpText={HELP.score_distance} />
              <ScoreItem label="Count" value={evalResult.score.count} helpText={HELP.score_count} />
              <ScoreItem label="Radius" value={evalResult.score.radius} helpText={HELP.score_radius} />
            </div>
            <p className="reliability-note">{evalResult.radius_reliability_note}</p>
            <div className="metric-row">
              <span>
                Ambiguous GTs <HelpTip text={HELP.ambiguous_gt} />
              </span>
              <span>{evalResult?.ambiguous_gts?.length ?? 0}</span>
            </div>
            <div className="metrics-row">
              Recall <HelpTip text={HELP.recall} /> {pct(evalResult.metrics.recall)} | Precision{' '}
              <HelpTip text={HELP.precision} /> {pct(evalResult.metrics.precision)} | Coverage{' '}
              <HelpTip text={HELP.coverage} /> {pct(evalResult.metrics.coverage)} | Median error{' '}
              <HelpTip text={HELP.median_error} /> {fmt(evalResult.metrics.median_error_m)}m | P90{' '}
              <HelpTip text={HELP.p90_error} /> {fmt(evalResult.metrics.p90_error_m)}m | Count error{' '}
              <HelpTip text={HELP.count_error} /> {evalResult.metrics.count_error}
            </div>
          </section>

          {combinedScore !== null && (
            <section className="combined-score-panel">
              <span className="combined-score-label">Combined Score (Test 1 + Test 2)</span>
              <span className="combined-score-value">{(combinedScore * 100).toFixed(1)}%</span>
            </section>
          )}
          <Diagnostics result={evalResult} possibleMergeIds={possibleMergeIds} />
        </>
      )}
    </div>
  )
}

function ClusterRadii({
  cluster,
  color,
  dashed,
}: {
  cluster: LocalizationRunResult['cluster_results'][number]
  color: string
  dashed?: boolean
}) {
  return (
    <>
      {cluster.uncertainty_regions.map((region, index) => (
        <Circle
          key={`${cluster.cluster_id}-radius-${index}`}
          center={[region.center_lat, region.center_lon]}
          radius={region.radius_m}
          pathOptions={{ color, fillOpacity: 0.08, weight: 2, dashArray: dashed ? '6 6' : undefined }}
        />
      ))}
    </>
  )
}

function ClusterPeak({ cluster, color }: { cluster: LocalizationRunResult['cluster_results'][number]; color: string }) {
  if (!cluster.primary_peak) return null
  return (
    <CircleMarker
      center={[cluster.primary_peak.lat, cluster.primary_peak.lon]}
      radius={7}
      pathOptions={{ color, fillColor: color, fillOpacity: 0.9, weight: 2 }}
    >
      <Tooltip>
        Cluster {cluster.cluster_id} - peak value {cluster.primary_peak.value.toFixed(3)}
      </Tooltip>
    </CircleMarker>
  )
}

function GtClickHandler({ enabled, onAdd }: { enabled: boolean; onAdd: (point: { lat: number; lon: number }) => void }) {
  useMapEvents({
    click(event) {
      if (enabled) onAdd({ lat: event.latlng.lat, lon: event.latlng.lng })
    },
  })
  return null
}

function SetView({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap()
  useEffect(() => {
    map.flyTo(center, zoom)
  }, [center[0], center[1], map, zoom])
  return null
}

async function waitForExecution(
  executionId: string,
  onStatus: (message: string) => void,
): Promise<ExecutionStatus> {
  let latest = await getExecution(executionId)
  for (let attempt = 0; attempt < 120 && (latest.status === 'pending' || latest.status === 'running'); attempt += 1) {
    onStatus(`rerun ${latest.status}`)
    await sleep(1500)
    latest = await getExecution(executionId)
  }
  return latest
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

function ScoreItem({ label, value, helpText }: { label: string; value: number; helpText: string }) {
  return (
    <div className="score-item">
      <span>
        {label} <HelpTip text={helpText} />
      </span>
      <strong>{pct(value)}</strong>
    </div>
  )
}

function Diagnostics({ result, possibleMergeIds }: { result: EvaluationResult; possibleMergeIds: Set<string> }) {
  return (
    <section className="diagnostics-panel">
      <table className="diagnostics-table">
        <thead>
          <tr>
            <th>
              GT <HelpTip text={HELP.ground_truth} />
            </th>
            <th>Cluster</th>
            <th>Type</th>
            <th>
              Dist (m) <HelpTip text={HELP.median_error} />
            </th>
            <th>
              Radius (m) <HelpTip text={HELP.uncertainty_radius} />
            </th>
            <th>
              Covered <HelpTip text={HELP.score_containment} />
            </th>
            <th>
              Association <HelpTip text={HELP.association_clear} />
            </th>
            <th>
              Duplicates <HelpTip text={HELP.duplicates} />
            </th>
            <th>
              Merge <HelpTip text={HELP.possible_merge} />
            </th>
          </tr>
        </thead>
        <tbody>
          {result.matches.map((match) => (
            <tr key={`${match.gt_id}-${match.primary_cluster_id}`}>
              <td>{match.gt_label || match.gt_id.slice(0, 8)}</td>
              <td className="mono">{match.primary_cluster_id}</td>
              <td>{match.cluster_type}</td>
              <td>{match.distance_m.toFixed(1)}</td>
              <td>{match.uncertainty_radius_m?.toFixed(1) ?? '-'}</td>
              <td>{match.covered ? 'yes' : 'no'}</td>
              <td>
                <span className={match.association_status === 'clear_match' ? 'badge-clear' : 'badge-ambiguous'}>
                  {match.association_status}
                </span>
              </td>
              <td>{match.secondary_candidates.length}</td>
              <td>{possibleMergeIds.has(match.primary_cluster_id) ? 'yes' : ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="diagnostic-lists">
        <DiagnosticList title="False Positives" helpText={HELP.false_positives} items={result.false_positives.map((item) => item.cluster_id)} />
        <DiagnosticList title="False Negatives" helpText={HELP.false_negatives} items={result.false_negatives.map((item) => item.label || item.gt_id)} />
        <DiagnosticList title="Duplicates" helpText={HELP.duplicates} items={result.duplicates.map((item) => item.cluster_id)} />
      </div>
    </section>
  )
}

function DiagnosticList({ title, helpText, items }: { title: string; helpText: string; items: string[] }) {
  return (
    <div className="diagnostic-list">
      <h3>
        {title} <HelpTip text={helpText} />
      </h3>
      {items.length ? items.map((item) => <span key={item}>{item}</span>) : <span>None</span>}
    </div>
  )
}

function localizationHelpText(key: string): string {
  const helpByKey: Record<string, string> = {
    grid_resolution_m: HELP.loc_grid_resolution_m,
    dynamic_sigma_alpha: HELP.loc_dynamic_sigma_alpha,
    confidence_cutoff: HELP.loc_confidence_cutoff,
    uncertainty_participation_floor: HELP.loc_uncertainty_participation_floor,
    uncertainty_alpha: HELP.loc_uncertainty_alpha,
    buffer_m: HELP.loc_buffer_m,
  }
  return helpByKey[key] ?? HELP.loc_grid_resolution_m
}

function reidHelpText(key: string): string {
  const helpByKey: Record<string, string> = {
    association_threshold: HELP.reid_association_threshold,
    seq_gap_max: HELP.reid_seq_gap_max,
    time_gap_max_sec: HELP.reid_time_gap_max_sec,
    burst_window_sec: HELP.reid_burst_window_sec,
  }
  return helpByKey[key] ?? HELP.reid_association_threshold
}

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

function fmt(value: number | null): string {
  return value === null ? '-' : value.toFixed(1)
}

function parseCsvRow(line: string): string[] {
  const fields: string[] = []
  let current = ''
  let inQuotes = false
  for (let i = 0; i < line.length; i++) {
    const ch = line[i]
    if (inQuotes) {
      if (ch === '"' && line[i + 1] === '"') {
        current += '"'
        i++
      } else if (ch === '"') {
        inQuotes = false
      } else {
        current += ch
      }
    } else {
      if (ch === '"') {
        inQuotes = true
      } else if (ch === ',') {
        fields.push(current)
        current = ''
      } else {
        current += ch
      }
    }
  }
  fields.push(current)
  return fields
}

function heatColor(value: number): string {
  const h = (1 - Math.max(0, Math.min(1, value))) * 240
  return `hsl(${h.toFixed(0)}, 100%, 50%)`
}
