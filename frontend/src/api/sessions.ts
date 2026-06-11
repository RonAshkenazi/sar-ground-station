import { apiFetch } from './client'
import type { ScanFolder, Session, SessionState } from '../types'

export const getScanFolders = () =>
  apiFetch<{ folders: ScanFolder[]; warning?: string }>('/api/scan-folders')

export const createSession = (folder_id: string, mode?: string) =>
  apiFetch<Session>('/api/sessions', {
    method: 'POST',
    body: JSON.stringify({ folder_id, mode }),
  })

export const patchMode = (session_id: string, mode: 'wifi' | 'ble') =>
  apiFetch<{ session_id: string; mode: string }>(`/api/sessions/${session_id}/mode`, {
    method: 'PATCH',
    body: JSON.stringify({ mode }),
  })

export const getSessionState = (session_id: string) =>
  apiFetch<SessionState>(`/api/sessions/${session_id}/state`)

export const saveSession = (sessionId: string) =>
  apiFetch<{ saved_id: string; folder_id: string; saved_at_utc: string }>(`/api/sessions/${sessionId}/save`, {
    method: 'POST',
  })

export const getSavedSessions = () =>
  apiFetch<Array<{ saved_id: string; folder_id: string; saved_at_utc: string; mode: string }>>('/api/saved-sessions')

export const resumeSavedSession = (savedId: string) =>
  apiFetch<SessionState>(`/api/saved-sessions/${savedId}/resume`, {
    method: 'POST',
  })

export const deleteSavedSession = (savedId: string) =>
  apiFetch<{ deleted: string }>(`/api/saved-sessions/${savedId}`, {
    method: 'DELETE',
  })

export interface InventoryResult {
  raw_csvs: Array<{ filename: string; path: string }>
  enriched_artifacts: Array<{
    filename: string
    path: string
    stage_jump_suggestion: string
  }>
  reid_artifacts: Array<{
    filename: string
    path: string
    stage_jump_suggestion: string
  }>
  pcap_files: Array<{ filename: string; path: string }>
}

export interface OverviewResult {
  csv_filename: string
  record_count: number
  unique_macs: number
  gps_fix_pct: number
  rssi_min: number | null
  rssi_max: number | null
  rssi_mean: number | null
  gps_points: Array<{
    lat: number
    lon: number
    rssi: number | null
    src_mac: string
    timestamp_utc: string
    frame_type: string
  }>
  device_table: Array<{
    src_mac: string
    packet_count: number
    rssi_min: number | null
    rssi_max: number | null
    rssi_mean: number | null
  }>
  warning: string | null
}

export const getInventory = (session_id: string) =>
  apiFetch<InventoryResult>(`/api/sessions/${session_id}/inventory`)

export const runOverview = (session_id: string, csv_filename: string) =>
  apiFetch<OverviewResult>(`/api/sessions/${session_id}/overview`, {
    method: 'POST',
    body: JSON.stringify({ csv_filename }),
  })

export interface CalibrationRunResult {
  success: boolean
  error: string | null
  parameters: { rssi_at_1m: number; path_loss_n: number; sigma: number } | null
  fit_quality: {
    r2: number
    sample_count: number
    inlier_count: number
    inlier_ratio: number
    sigma: number
  } | null
  scatter: Array<{
    distance_m: number
    log10_distance: number
    rssi: number
    inlier: boolean
  }>
  gt_lat: number | null
  gt_lon: number | null
  warnings: string[]
}

export interface CalibrationState {
  scan_folder_id: string
  parameter_source: string
  parameters: { rssi_at_1m: number; path_loss_n: number; sigma: number }
  approved: boolean
  calibration_csv_file?: string | null
  calibration_mac_address?: string | null
  parameter_set_name?: string | null
}

export const getCalibrationCandidates = (session_id: string, csv_filename: string) =>
  apiFetch<{ csv_filename: string; macs: string[] }>(
    `/api/sessions/${session_id}/calibration/candidates`,
    { method: 'POST', body: JSON.stringify({ csv_filename }) },
  )

export const runCalibration = (
  session_id: string,
  params: {
    csv_filename: string
    mac: string
    gt_mode: 'mean_first_k' | 'first_sample' | 'manual_map_click'
    gt_k?: number
    manual_lat?: number
    manual_lon?: number
    enable_ransac?: boolean
    ransac_threshold_db?: number
    ransac_iterations?: number
    distance_floor_m?: number
  },
) =>
  apiFetch<CalibrationRunResult>(`/api/sessions/${session_id}/calibration/run`, {
    method: 'POST',
    body: JSON.stringify(params),
  })

export const approveCalibration = (session_id: string) =>
  apiFetch<CalibrationState>(`/api/sessions/${session_id}/calibration/approve`, {
    method: 'POST',
  })

export const useFallbackPreset = (session_id: string, preset_name: string) =>
  apiFetch<CalibrationState>(`/api/sessions/${session_id}/calibration/fallback`, {
    method: 'POST',
    body: JSON.stringify({ preset_name }),
  })

export interface EnrichmentQuality {
  enriched_csv_path?: string
  total_rows: number
  matched_rows: number
  match_rate: number
  warnings: string[]
}

export interface ExecutionStatus {
  execution_id: string
  status: 'pending' | 'running' | 'success' | 'failed'
  stage: string
  warnings: string[]
  result_metadata: Record<string, unknown> | null
  error: string | null
}

export const runEnrichment = (session_id: string, csv_filename: string) =>
  apiFetch<{ execution_id: string; status: string }>(
    `/api/sessions/${session_id}/enrichment/run`,
    { method: 'POST', body: JSON.stringify({ csv_filename }) },
  )

export const getExecution = (execution_id: string) =>
  apiFetch<ExecutionStatus>(`/api/executions/${execution_id}`)

export const activateArtifact = (
  session_id: string,
  artifact_path: string,
  artifact_type: 'enriched' | 'reid',
) =>
  apiFetch<{
    session_id: string
    activated: string
    path: string
    active_enriched_artifact: string | null
    active_reid_artifact: string | null
  }>(`/api/sessions/${session_id}/artifacts/activate`, {
    method: 'POST',
    body: JSON.stringify({ artifact_path, artifact_type }),
  })

export interface ReIdQuality {
  reid_csv_path?: string
  cluster_confidence?: Record<string, 'high' | 'medium' | 'low'>
  total_rows: number
  static_cluster_count: number
  dynamic_cluster_count: number
  unique_dynamic_mac_count?: number
  noise_cluster_count: number
  warnings: string[]
}

export const runReid = (
  session_id: string,
  enriched_csv_filename: string,
  params: {
    association_threshold?: number
    seq_gap_max?: number
    time_gap_max_sec?: number
    burst_window_sec?: number
    probe_requests_only?: boolean
  } = {},
) =>
  apiFetch<{ execution_id: string; status: string }>(
    `/api/sessions/${session_id}/reid/run`,
    { method: 'POST', body: JSON.stringify({ enriched_csv_filename, ...params }) },
  )

export interface LocalizationClusterResult {
  cluster_id: string
  cluster_type: string
  status: 'success' | 'failed'
  sample_count: number
  primary_peak: { lat: number; lon: number; value: number } | null
  candidate_peaks: Array<{ lat: number; lon: number; value: number }>
  uncertainty_regions: Array<{ center_lat: number; center_lon: number; radius_m: number }>
  grid_cells: Array<{ lat: number; lon: number; value: number }>
  warnings: string[]
  failure_reason: string | null
}

export interface LocalizationRunResult {
  cluster_results: LocalizationClusterResult[]
  bounds: { lat_min: number; lat_max: number; lon_min: number; lon_max: number }
  total_clusters: number
  successful_clusters: number
  failed_clusters: number
  warnings: string[]
}

export const runLocalization = (
  session_id: string,
  body: {
    reid_csv_filename: string
    bounds_mode?: 'auto_track_plus_buffer' | 'manual_rectangle'
    buffer_m?: number
    grid_resolution_m?: number
    dynamic_sigma_alpha?: number
    confidence_cutoff?: number
    uncertainty_participation_floor?: number
    uncertainty_alpha?: number
  },
) =>
  apiFetch<{ execution_id: string; status: string }>(
    `/api/sessions/${session_id}/localization/run`,
    { method: 'POST', body: JSON.stringify(body) },
  )

export interface GtPoint {
  gt_id: string
  lat: number
  lon: number
  label: string | null
}

export interface MatchDiagnostic {
  gt_id: string
  gt_lat: number
  gt_lon: number
  gt_label: string | null
  primary_cluster_id: string
  cluster_lat: number
  cluster_lon: number
  cluster_type: string | null
  num_samples: number | null
  uncertainty_radius_m: number | null
  distance_m: number
  covered: boolean
  association_cost: number
  dominance_margin: number | null
  association_status: 'clear_match' | 'ambiguous_match'
  secondary_candidates: Array<{ cluster_id: string; distance_m: number; cost?: number }>
}

export interface EvaluationResult {
  matches: MatchDiagnostic[]
  false_positives: Array<{ cluster_id: string; lat: number; lon: number; cluster_type: string | null }>
  false_negatives: Array<{ gt_id: string; lat: number; lon: number; label: string | null }>
  ambiguous_gts: Array<{
    gt_id: string
    lat: number
    lon: number
    label: string | null
    nearest_cluster_id: string | null
    nearest_dist_m: number
    competing_cluster_ids: string[]
  }>
  duplicates: Array<{ cluster_id: string; competing_for_gt_id: string; distance_m: number; cost: number }>
  possible_merges: Array<{ cluster_id: string; candidate_gt_ids: string[]; distances_m: number[] }>
  metrics: {
    recall: number
    precision: number
    coverage: number
    median_error_m: number | null
    p90_error_m: number | null
    median_radius_m: number | null
    count_error: number
  }
  score: {
    total: number
    containment: number
    distance: number
    count: number
    radius: number
  }
  eval_params: {
    ratio_gate: number
    max_match_dist_m: number
    r_normalize_m: number
    d_free_m: number
    w_containment: number
    w_distance: number
    w_count: number
    w_radius: number
  }
  n_predictions: number
  n_gt: number
  radius_reliability_note: string
}

export interface ResultAnalysisState {
  session_id: string
  gt_points: GtPoint[]
  localization_available: boolean
  last_evaluation: EvaluationResult | null
}

export const getResultAnalysis = (session_id: string) =>
  apiFetch<ResultAnalysisState>(`/api/sessions/${session_id}/result-analysis`)

export const addGtPoint = (session_id: string, lat: number, lon: number, label?: string) =>
  apiFetch<GtPoint>(`/api/sessions/${session_id}/result-analysis/ground-truth`, {
    method: 'POST',
    body: JSON.stringify({ lat, lon, label: label ?? null }),
  })

export const importGtPoints = (session_id: string, points: Array<{ lat: number; lon: number; label?: string }>) =>
  apiFetch<{ added: number; gt_points: GtPoint[] }>(
    `/api/sessions/${session_id}/result-analysis/ground-truth/import`,
    { method: 'POST', body: JSON.stringify({ points }) },
  )

export const deleteGtPoint = (session_id: string, gt_id: string) =>
  apiFetch<{ deleted: string }>(`/api/sessions/${session_id}/result-analysis/ground-truth/${gt_id}`, {
    method: 'DELETE',
  })

export const clearGtPoints = (session_id: string) =>
  apiFetch<{ cleared: boolean }>(`/api/sessions/${session_id}/result-analysis/ground-truth/clear`, {
    method: 'POST',
  })

export const runEvaluation = (
  session_id: string,
  params: {
    ratio_gate?: number
    max_match_dist_m?: number
    r_normalize_m?: number
    d_free_m?: number
    w_containment?: number
    w_distance?: number
    w_count?: number
    w_radius?: number
    cluster_ids?: string[]
    gt_ids?: string[]
  } = {},
) =>
  apiFetch<EvaluationResult>(`/api/sessions/${session_id}/result-analysis/evaluate`, {
    method: 'POST',
    body: JSON.stringify(params),
  })

export const rerunFromResultAnalysis = (
  session_id: string,
  stage: 'localization' | 'reid' | 'enrichment',
  localization_params?: {
    grid_resolution_m?: number
    dynamic_sigma_alpha?: number
    confidence_cutoff?: number
    uncertainty_participation_floor?: number
    uncertainty_alpha?: number
    buffer_m?: number
  },
  reid_params?: {
    association_threshold?: number
    seq_gap_max?: number
    time_gap_max_sec?: number
    burst_window_sec?: number
    probe_requests_only?: boolean
  },
  enrichment_params?: {
    match_threshold?: number
    time_window_ms?: number
    time_score_weight?: number
    identity_score_weight?: number
    context_weight?: number
  },
) =>
  apiFetch<{ status: string; execution_id?: string; localization_execution_id?: string }>(
    `/api/sessions/${session_id}/result-analysis/rerun`,
    {
      method: 'POST',
      body: JSON.stringify({ stage, localization_params, reid_params, enrichment_params }),
    },
  )
