import { apiFetch } from './client'

export const getAirunitStatus = () =>
  apiFetch<{ pi_connected: boolean; pi_info: { ip: string; port: number } | null }>(
    '/api/airunit/status',
  )

export const sendAirunitCommand = (cmd: string) =>
  apiFetch<{ ok: boolean }>('/api/airunit/command', {
    method: 'POST',
    body: JSON.stringify({ cmd }),
  })

export const listPiFiles = () =>
  apiFetch<{ files: PiFile[]; error?: string }>('/api/airunit/files')

export const initGuidance = (
  bounds: { min_lat: number; max_lat: number; min_lon: number; max_lon: number },
  cell_size_m: number = 30,
) =>
  apiFetch<{ ok: boolean; n_rows: number; n_cols: number; total_cells: number }>(
    '/api/guidance/init',
    { method: 'POST', body: JSON.stringify({ ...bounds, cell_size_m }) },
  )

export const getGuidanceRecommendation = () =>
  apiFetch<GuidanceRecommendation | { available: false }>('/api/guidance/recommendation')

export const getGuidanceGrid = () => apiFetch<GuidanceGridState>('/api/guidance/grid')

export const resetGuidance = () =>
  apiFetch<{ ok: boolean }>('/api/guidance/reset', { method: 'POST' })

export const ingestGuidancePacket = (packet: Record<string, unknown>) =>
  apiFetch<{ ok: boolean }>('/api/guidance/update', {
    method: 'POST',
    body: JSON.stringify(packet),
  })

export interface PiFile {
  name: string
  size_bytes: number
  mtime: number
  description: string
}

export interface GuidanceRecommendation {
  available: true
  timestamp_ms: number
  mode: 'EXPLORE' | 'REFINE'
  target_cell_id: number
  target_lat: number
  target_lon: number
  bearing_deg: number
  distance_m: number
  final_score: number
  evidence_score: number
  uncertainty_score: number
  peak_score: number
  travel_cost: number
  oscillation_penalty: number
  gps_valid: boolean
  data_fresh: boolean
  recommendation_stale: boolean
  reason: string
}

export interface GridCell {
  cell_id: number
  center_lat: number
  center_lon: number
  evidence_score: number
  uncertainty_score: number
  peak_score: number
  coverage_score: number
  age_score: number
  final_score: number
  display_score?: number
  spatial_entropy?: number
  spatial_certainty?: number
  evidence_freshness?: number
}

export interface GuidanceGridState {
  initialized: boolean
  bounds?: { min_lat: number; max_lat: number; min_lon: number; max_lon: number }
  cell_size_m?: number
  n_rows?: number
  n_cols?: number
  mode?: string
  cells: GridCell[]
}
