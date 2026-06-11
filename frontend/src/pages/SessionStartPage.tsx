import { ChangeEvent, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  createSession,
  deleteSavedSession,
  getSavedSessions,
  getScanFolders,
  getSessionState,
  resumeSavedSession,
} from '../api/sessions'
import { useSession } from '../state/SessionContext'
import type { ScanFolder } from '../types'
import './SessionStartPage.css'

type SelectableMode = 'wifi' | 'ble'
type DetectedMode = SelectableMode | 'unknown'
type SavedSessionListItem = { saved_id: string; folder_id: string; saved_at_utc: string; mode: string }

export default function SessionStartPage() {
  const navigate = useNavigate()
  const { setSession } = useSession()
  const [folders, setFolders] = useState<ScanFolder[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedFolderId, setSelectedFolderId] = useState('')
  const [detectedMode, setDetectedMode] = useState<DetectedMode>('unknown')
  const [modeOverride, setModeOverride] = useState<SelectableMode | null>(null)
  const [creating, setCreating] = useState(false)
  const [savedSessions, setSavedSessions] = useState<SavedSessionListItem[]>([])
  const [resumingId, setResumingId] = useState('')
  const [deletingId, setDeletingId] = useState('')
  const [confirmDeleteId, setConfirmDeleteId] = useState('')

  useEffect(() => {
    getScanFolders()
      .then(({ folders: loadedFolders }) => setFolders(loadedFolders))
      .catch((err: unknown) => {
        const raw = String(err)
        setError(
          raw.includes('Failed to fetch') || raw.includes('NetworkError')
            ? 'Cannot reach the backend server (localhost:8000). Start it with: cd backend && uvicorn app.main:app --reload'
            : raw
        )
      })
      .finally(() => setLoading(false))

    getSavedSessions()
      .then(setSavedSessions)
      .catch(() => setSavedSessions([]))
  }, [])

  function handleFolderChange(event: ChangeEvent<HTMLSelectElement>) {
    const id = event.target.value
    setSelectedFolderId(id)
    setModeOverride(null)
    const folder = folders.find((item) => item.folder_id === id)
    setDetectedMode(folder?.detected_mode ?? 'unknown')
  }

  async function handleStart() {
    if (!selectedFolderId) return
    setCreating(true)
    setError(null)
    try {
      const effectiveMode = modeOverride ?? (detectedMode === 'unknown' ? undefined : detectedMode)
      const session = await createSession(selectedFolderId, effectiveMode)
      const state = await getSessionState(session.session_id)
      setSession(state)
      navigate('/overview')
    } catch (err: unknown) {
      setError(String(err))
    } finally {
      setCreating(false)
    }
  }

  function handleModeOverride(mode: SelectableMode) {
    setModeOverride(mode)
  }

  async function handleDelete(savedId: string) {
    setConfirmDeleteId('')
    setDeletingId(savedId)
    setError(null)
    try {
      await deleteSavedSession(savedId)
      setSavedSessions((prev) => prev.filter((s) => s.saved_id !== savedId))
    } catch (err: unknown) {
      setError(String(err))
    } finally {
      setDeletingId('')
    }
  }

  async function handleResume(savedId: string) {
    setResumingId(savedId)
    setError(null)
    try {
      const state = await resumeSavedSession(savedId)
      setSession(state)
      navigate('/localization')
    } catch (err: unknown) {
      setError(String(err))
    } finally {
      setResumingId('')
    }
  }

  const visibleMode = modeOverride ?? detectedMode

  return (
    <div className="session-start-page">
      <div className="session-start-card">
        <h1 className="page-title">Select Scan Folder</h1>

        {error && <p className="error-banner">{error}</p>}

        {loading ? (
          <p className="loading-hint">Loading scan folders...</p>
        ) : !error && folders.length === 0 ? (
          <p className="empty-state">
            No scan folders found. Add scan folders to <code>runtime/DATA/</code> to get
            started.
          </p>
        ) : (
          <>
            <label htmlFor="folder-select" className="field-label">
              Scan Folder
            </label>
            <select
              id="folder-select"
              className="folder-select"
              value={selectedFolderId}
              onChange={handleFolderChange}
            >
              <option value="">- Select a folder -</option>
              {folders.map((folder) => (
                <option key={folder.folder_id} value={folder.folder_id} dir="auto">
                  {folder.folder_name} ({folder.detected_mode})
                </option>
              ))}
            </select>

            {selectedFolderId && (
              <div className="mode-row">
                <span className="field-label">Detected mode:</span>
                <span className={`mode-badge mode-${visibleMode}`}>
                  {visibleMode.toUpperCase()}
                </span>
                <span className="field-label">Override:</span>
                <div className="segmented-control" role="group" aria-label="Mode override">
                  {(['wifi', 'ble'] as const).map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      className={`seg-btn${modeOverride === mode ? ' selected' : ''}`}
                      onClick={() => handleModeOverride(mode)}
                      aria-pressed={modeOverride === mode}
                    >
                      {mode === 'wifi' ? 'Wi-Fi' : 'BLE'}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <button
              className="btn-primary"
              disabled={!selectedFolderId || creating}
              onClick={handleStart}
            >
              {creating ? 'Starting...' : 'Start Session ->'}
            </button>

            {savedSessions.length > 0 && (
              <section className="saved-sessions-panel">
                <h2 className="panel-title">Resume from Saved Session</h2>
                <table className="saved-sessions-table">
                  <thead>
                    <tr>
                      <th>Folder</th>
                      <th>Date</th>
                      <th>Mode</th>
                      <th></th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {savedSessions.map((saved) => (
                      <tr key={`${saved.folder_id}-${saved.saved_id}`}>
                        <td dir="auto">{saved.folder_id}</td>
                        <td>{formatSavedAt(saved.saved_at_utc)}</td>
                        <td>{saved.mode.toUpperCase()}</td>
                        <td>
                          <button
                            className="btn-secondary"
                            disabled={!!resumingId || !!deletingId}
                            onClick={() => handleResume(saved.saved_id)}
                          >
                            {resumingId === saved.saved_id ? 'Resuming...' : 'Resume'}
                          </button>
                        </td>
                        <td>
                          {confirmDeleteId === saved.saved_id ? (
                            <span className="delete-confirm-row">
                              <span className="delete-confirm-label">Delete?</span>
                              <button
                                className="btn-danger"
                                disabled={!!deletingId}
                                onClick={() => handleDelete(saved.saved_id)}
                              >
                                {deletingId === saved.saved_id ? 'Deleting...' : 'Yes'}
                              </button>
                              <button
                                className="btn-secondary"
                                onClick={() => setConfirmDeleteId('')}
                              >
                                No
                              </button>
                            </span>
                          ) : (
                            <button
                              className="btn-danger"
                              disabled={!!resumingId || !!deletingId}
                              onClick={() => setConfirmDeleteId(saved.saved_id)}
                            >
                              Delete
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            )}
          </>
        )}

        <div className="live-mission-section">
          <h3>Live Mission</h3>
          <p>Connect to the airborne unit and run smart flight guidance in real time.</p>
          <button
            className="btn-live-mission"
            onClick={() => navigate('/airunit')}
          >
            Start Live Mission
          </button>
        </div>
      </div>
    </div>
  )
}

function formatSavedAt(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const dd = String(date.getDate()).padStart(2, '0')
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const yyyy = date.getFullYear()
  const hh = String(date.getHours()).padStart(2, '0')
  const min = String(date.getMinutes()).padStart(2, '0')
  return `${dd}/${mm}/${yyyy} ${hh}:${min}`
}
