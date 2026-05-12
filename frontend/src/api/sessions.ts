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
  total_rows: number
  static_cluster_count: number
  dynamic_cluster_count: number
  singleton_dynamic_count: number
  warnings: string[]
}

export const runReid = (session_id: string, enriched_csv_filename: string) =>
  apiFetch<{ execution_id: string; status: string }>(
    `/api/sessions/${session_id}/reid/run`,
    { method: 'POST', body: JSON.stringify({ enriched_csv_filename }) },
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
  },
) =>
  apiFetch<{ execution_id: string; status: string }>(
    `/api/sessions/${session_id}/localization/run`,
    { method: 'POST', body: JSON.stringify(body) },
  )
