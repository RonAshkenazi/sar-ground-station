import { useState } from 'react'
import { saveSession } from '../../api/sessions'
import { useSession } from '../../state/SessionContext'
import './Header.css'

export default function Header() {
  const { session } = useSession()
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const warnings = session?.warnings.length ?? 0
  const hasLocalization = !!(session?.active_localization ?? session?.current_localization_result)
  const activeArtifact = session?.active_reid_artifact
    ? 'REID'
    : session?.active_enriched_artifact
      ? 'ENRICHED'
      : '-'

  return (
    <header className="header">
      <span className="header-app-name">SAR Ground Station</span>
      <span className="header-divider">|</span>
      <span className="header-folder" title={session?.folder_id ?? ''} dir="auto">
        {session?.folder_id ?? 'No folder selected'}
      </span>
      {session && (
        <span className={`header-mode-badge mode-${session.mode}`}>
          {session.mode.toUpperCase()}
        </span>
      )}
      <span className="header-artifact" title="Highest active artifact">
        Artifact: {activeArtifact}
      </span>
      <div className="header-spacer" />
      <span className={`header-warning-badge${warnings > 0 ? ' has-warnings' : ''}`}>
        Warnings: {warnings}
      </span>
      <button
        className="btn-save-session"
        disabled={!hasLocalization || saving}
        title={hasLocalization ? 'Save current session' : 'Available after localization'}
        onClick={handleSave}
      >
        {saving ? 'Saving...' : saved ? 'Saved ✓' : 'Save Session'}
      </button>
    </header>
  )

  async function handleSave() {
    if (!session?.session_id) return
    setSaving(true)
    setSaved(false)
    try {
      await saveSession(session.session_id)
      setSaved(true)
      window.setTimeout(() => setSaved(false), 3000)
    } finally {
      setSaving(false)
    }
  }
}
