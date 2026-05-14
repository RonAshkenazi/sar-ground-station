export interface ScanFolder {
  folder_id: string
  folder_name: string
  detected_mode: 'wifi' | 'ble' | 'unknown'
}

export interface Session {
  session_id: string
  folder_id: string
  mode: 'wifi' | 'ble' | 'unknown'
  created_at: string
}

export interface SessionState extends Session {
  active_page: string
  active_overview_csv: string | null
  active_calibration: unknown | null
  active_scan_csv: string | null
  active_enriched_artifact: string | null
  active_reid_artifact: string | null
  active_reid?: {
    reid_csv_path?: string
    quality?: {
      cluster_confidence?: Record<string, 'high' | 'medium' | 'low'>
    }
  } | null
  active_localization?: unknown | null
  current_localization_result: unknown | null
  view_state: Record<string, unknown>
  warnings: string[]
}
