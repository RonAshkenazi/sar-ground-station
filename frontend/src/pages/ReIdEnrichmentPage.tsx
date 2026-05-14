import { useEffect, useMemo, useState } from 'react'
import {
  activateArtifact,
  getExecution,
  getInventory,
  runEnrichment,
  runReid,
  type EnrichmentQuality,
  type ExecutionStatus,
  type InventoryResult,
  type ReIdQuality,
} from '../api/sessions'
import { useSession } from '../state/SessionContext'
import './ReIdEnrichmentPage.css'

export default function ReIdEnrichmentPage() {
  const { session } = useSession()
  const [inventory, setInventory] = useState<InventoryResult | null>(null)
  const [selectedCsv, setSelectedCsv] = useState('')
  const [execution, setExecution] = useState<ExecutionStatus | null>(null)
  const [quality, setQuality] = useState<EnrichmentQuality | null>(null)
  const [loading, setLoading] = useState(false)
  const [activating, setActivating] = useState(false)
  const [activationMessage, setActivationMessage] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [selectedEnriched, setSelectedEnriched] = useState('')
  const [reidExecution, setReidExecution] = useState<ExecutionStatus | null>(null)
  const [reidQuality, setReidQuality] = useState<ReIdQuality | null>(null)
  const [reidError, setReidError] = useState<string | null>(null)
  const [reidLoading, setReidLoading] = useState(false)
  const [reidActivating, setReidActivating] = useState(false)
  const [reidActivationMessage, setReidActivationMessage] = useState('')
  const [reidSettings, setReidSettings] = useState({
    association_threshold: 0.8,
    seq_gap_max: 64,
    time_gap_max_sec: 30,
    burst_window_sec: 60,
    probe_requests_only: false,
  })

  useEffect(() => {
    if (!session?.session_id) {
      setInventory(null)
      setSelectedCsv('')
      resetReidState()
      return
    }
    refreshInventory()
  }, [session?.session_id])

  useEffect(() => {
    if (!execution || execution.status === 'success' || execution.status === 'failed') {
      return
    }

    const interval = window.setInterval(async () => {
      try {
        const next = await getExecution(execution.execution_id)
        if (next.status === 'success') {
          setQuality(next.result_metadata as unknown as EnrichmentQuality)
          setExecution(next)
          window.clearInterval(interval)
          void refreshInventory()
        } else if (next.status === 'failed') {
          setError(next.error ?? 'Enrichment failed')
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

  useEffect(() => {
    if (!reidExecution || reidExecution.status === 'success' || reidExecution.status === 'failed') {
      return
    }

    const interval = window.setInterval(async () => {
      try {
        const next = await getExecution(reidExecution.execution_id)
        if (next.status === 'success') {
          setReidQuality(next.result_metadata as unknown as ReIdQuality)
          setReidExecution(next)
          window.clearInterval(interval)
          void refreshInventory()
        } else if (next.status === 'failed') {
          setReidError(next.error ?? 'Re-ID failed')
          setReidExecution(next)
          window.clearInterval(interval)
        } else {
          setReidExecution(next)
        }
      } catch (err: unknown) {
        setReidError(String(err))
        window.clearInterval(interval)
      }
    }, 1500)

    return () => window.clearInterval(interval)
  }, [reidExecution?.execution_id, reidExecution?.status])

  async function refreshInventory() {
    if (!session?.session_id) return
    setError(null)
    try {
      setInventory(await getInventory(session.session_id))
    } catch (err: unknown) {
      setError(String(err))
    }
  }

  function handleCsvChange(filename: string) {
    setSelectedCsv(filename)
    setExecution(null)
    setQuality(null)
    setActivationMessage('')
    setError(null)
  }

  function resetReidState() {
    setSelectedEnriched('')
    setReidExecution(null)
    setReidQuality(null)
    setReidError(null)
    setReidActivationMessage('')
  }

  async function handleRun() {
    if (!session?.session_id || !selectedCsv || !pcapMatch) return

    setLoading(true)
    setError(null)
    setQuality(null)
    setExecution(null)
    try {
      const started = await runEnrichment(session.session_id, selectedCsv)
      setExecution({
        execution_id: started.execution_id,
        status: started.status as ExecutionStatus['status'],
        stage: 'enrichment',
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

  async function handleActivate() {
    if (!session?.session_id || !existingArtifact) return

    setActivating(true)
    setError(null)
    try {
      await activateArtifact(session.session_id, existingArtifact.path, 'enriched')
      setActivationMessage(`Activated for Re-ID: ${existingArtifact.filename}`)
    } catch (err: unknown) {
      setError(String(err))
    } finally {
      setActivating(false)
    }
  }

  function handleEnrichedChange(filename: string) {
    setSelectedEnriched(filename)
    setReidExecution(null)
    setReidQuality(null)
    setReidError(null)
    setReidActivationMessage('')
  }

  async function handleRunReid() {
    if (!session?.session_id || !selectedEnriched) return

    setReidLoading(true)
    setReidError(null)
    setReidQuality(null)
    setReidExecution(null)
    try {
      const started = await runReid(session.session_id, selectedEnriched, reidSettings)
      setReidExecution({
        execution_id: started.execution_id,
        status: started.status as ExecutionStatus['status'],
        stage: 'reid',
        warnings: [],
        result_metadata: null,
        error: null,
      })
    } catch (err: unknown) {
      setReidError(String(err))
    } finally {
      setReidLoading(false)
    }
  }

  async function handleActivateReid() {
    if (!session?.session_id || !existingReidArtifact) return

    setReidActivating(true)
    setReidError(null)
    try {
      await activateArtifact(session.session_id, existingReidArtifact.path, 'reid')
      setReidActivationMessage(`Activated for Localization: ${existingReidArtifact.filename}`)
    } catch (err: unknown) {
      setReidError(String(err))
    } finally {
      setReidActivating(false)
    }
  }

  const csvFiles = inventory?.raw_csvs ?? []
  const pcapMatch = useMemo(
    () => findMatchingPcap(selectedCsv, inventory?.pcap_files ?? []),
    [selectedCsv, inventory],
  )
  const existingArtifact = useMemo(
    () => findExistingEnriched(selectedCsv, inventory?.enriched_artifacts ?? []),
    [selectedCsv, inventory],
  )
  const running = execution?.status === 'pending' || execution?.status === 'running'
  const canRun = !!session && !!selectedCsv && !!pcapMatch && !running && !loading
  const enrichedArtifacts = inventory?.enriched_artifacts ?? []
  const existingReidArtifact = useMemo(
    () => findExistingReid(selectedEnriched, inventory?.reid_artifacts ?? []),
    [selectedEnriched, inventory],
  )
  const reidRunning = reidExecution?.status === 'pending' || reidExecution?.status === 'running'
  const canReid = !!session && !!selectedEnriched && !reidRunning && !reidLoading

  return (
    <div className="enrichment-page">
      <section className="enrichment-section">
        <h1 className="page-title">Re-ID & Enrichment</h1>

        {!session && (
          <p className="empty-state">No active session. Go to Session Start to select a folder.</p>
        )}
        {error && <p className="error-banner">{error}</p>}

        <div className="control-section">
          <label htmlFor="enrichment-csv" className="field-label">
            Scan CSV
          </label>
          <select
            id="enrichment-csv"
            className="folder-select"
            value={selectedCsv}
            onChange={(event) => handleCsvChange(event.target.value)}
            disabled={!session || loading || running}
          >
            <option value="">- Select scan CSV -</option>
            {csvFiles.map((file) => (
              <option key={file.filename} value={file.filename} dir="auto">
                {file.filename}
              </option>
            ))}
          </select>
        </div>

        {selectedCsv && (
          <div className={`status-panel ${pcapMatch ? 'status-ok' : 'status-blocked'}`}>
            {pcapMatch
              ? `PCAP found: ${pcapMatch.filename}`
              : 'No matching PCAP - enrichment blocked'}
          </div>
        )}

        {existingArtifact && (
          <div className="artifact-panel">
            <span>Existing ENRICHED artifact detected: {existingArtifact.filename}</span>
            <button className="btn-secondary" disabled={activating} onClick={handleActivate}>
              {activating ? 'Activating...' : 'Activate for Re-ID'}
            </button>
          </div>
        )}

        {activationMessage && <div className="success-banner">{activationMessage}</div>}

        <button className="btn-primary" disabled={!canRun} onClick={handleRun}>
          {running ? 'Enrichment running...' : 'Run Enrichment'}
        </button>

        {execution && running && (
          <p className="loading-hint">
            Enrichment running... <span className="mono">execution {execution.execution_id}</span>
          </p>
        )}

        {quality && (
          <div className="quality-panel">
            <h2 className="panel-title">Quality</h2>
            <dl className="quality-grid">
              <dt>Total rows</dt>
              <dd>{quality.total_rows.toLocaleString()}</dd>
              <dt>Matched rows</dt>
              <dd>{quality.matched_rows.toLocaleString()}</dd>
              <dt>Match rate</dt>
              <dd>{(quality.match_rate * 100).toFixed(1)}%</dd>
            </dl>
            {quality.warnings.map((warning) => (
              <div key={warning} className="warning-banner">
                {warning}
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="reid-section">
        <h2>Re-ID</h2>
        {reidError && <p className="error-banner">{reidError}</p>}

        <div className="control-section">
          <label htmlFor="reid-enriched" className="field-label">
            Enriched Artifact
          </label>
          <select
            id="reid-enriched"
            className="folder-select"
            value={selectedEnriched}
            onChange={(event) => handleEnrichedChange(event.target.value)}
            disabled={!session || reidLoading || reidRunning}
          >
            <option value="">- Select enriched artifact -</option>
            {enrichedArtifacts.map((artifact) => (
              <option key={artifact.filename} value={artifact.filename} dir="auto">
                {artifact.filename}
              </option>
            ))}
          </select>
        </div>

        {existingReidArtifact && (
          <div className="artifact-panel">
            <span>Existing REID artifact detected: {existingReidArtifact.filename}</span>
            <button className="btn-secondary" disabled={reidActivating} onClick={handleActivateReid}>
              {reidActivating ? 'Activating...' : 'Activate for Localization'}
            </button>
          </div>
        )}

        {reidActivationMessage && <div className="success-banner">{reidActivationMessage}</div>}

        <div className="settings-panel">
          <h3 className="panel-title">Re-ID Settings</h3>
          <div className="settings-grid">
            <label>
              Association
              <select
                value={reidSettings.association_threshold}
                onChange={(event) =>
                  setReidSettings((previous) => ({ ...previous, association_threshold: Number(event.target.value) }))
                }
              >
                <option value={0.75}>0.75</option>
                <option value={0.8}>0.80</option>
                <option value={0.9}>0.90</option>
              </select>
            </label>
            <label>
              Seq gap
              <select
                value={reidSettings.seq_gap_max}
                onChange={(event) => setReidSettings((previous) => ({ ...previous, seq_gap_max: Number(event.target.value) }))}
              >
                <option value={50}>50</option>
                <option value={64}>64</option>
                <option value={128}>128</option>
              </select>
            </label>
            <label>
              Time gap
              <select
                value={reidSettings.time_gap_max_sec}
                onChange={(event) =>
                  setReidSettings((previous) => ({ ...previous, time_gap_max_sec: Number(event.target.value) }))
                }
              >
                <option value={10}>10s</option>
                <option value={30}>30s</option>
                <option value={60}>60s</option>
              </select>
            </label>
            <label>
              Burst window
              <select
                value={reidSettings.burst_window_sec}
                onChange={(event) =>
                  setReidSettings((previous) => ({ ...previous, burst_window_sec: Number(event.target.value) }))
                }
              >
                <option value={30}>30s</option>
                <option value={60}>60s</option>
                <option value={120}>120s</option>
              </select>
            </label>
            <label className="settings-toggle">
              <input
                type="checkbox"
                checked={reidSettings.probe_requests_only}
                onChange={(event) =>
                  setReidSettings((previous) => ({ ...previous, probe_requests_only: event.target.checked }))
                }
              />
              Probe requests only
            </label>
          </div>
        </div>

        <button className="btn-primary" disabled={!canReid} onClick={handleRunReid}>
          {reidRunning ? 'Re-ID running...' : 'Run Re-ID'}
        </button>

        {reidExecution && reidRunning && (
          <p className="loading-hint">
            Re-ID running... <span className="mono">execution {reidExecution.execution_id}</span>
          </p>
        )}

        {reidQuality && (
          <div className="quality-panel">
            <h2 className="panel-title">Re-ID Quality</h2>
            <dl className="quality-grid">
              <dt>Total rows</dt>
              <dd>{reidQuality.total_rows.toLocaleString()}</dd>
              <dt>Static clusters</dt>
              <dd>{reidQuality.static_cluster_count.toLocaleString()}</dd>
              <dt>Unique dynamic MACs</dt>
              <dd>{reidQuality.unique_dynamic_mac_count?.toLocaleString() ?? '-'}</dd>
              <dt>Dynamic clusters</dt>
              <dd>{reidQuality.dynamic_cluster_count.toLocaleString()}</dd>
              <dt>Noise clusters</dt>
              <dd>{reidQuality.noise_cluster_count.toLocaleString()}</dd>
            </dl>
            {reidQuality.warnings.map((warning) => (
              <div key={warning} className="warning-banner">
                {warning}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

function findMatchingPcap(
  csvFilename: string,
  pcaps: Array<{ filename: string; path: string }>,
) {
  if (!csvFilename) return null
  const stem = fileStem(csvFilename).toLowerCase()
  return pcaps.find((pcap) => fileStem(pcap.filename).toLowerCase() === stem) ?? null
}

function findExistingEnriched(
  csvFilename: string,
  artifacts: Array<{ filename: string; path: string; stage_jump_suggestion: string }>,
) {
  if (!csvFilename) return null
  const stem = fileStem(csvFilename).toLowerCase()
  return (
    artifacts.find((artifact) => {
      const artifactStem = fileStem(artifact.filename).toLowerCase()
      return artifactStem === `${stem}_enriched`
    }) ?? null
  )
}

function findExistingReid(
  enrichedFilename: string,
  artifacts: Array<{ filename: string; path: string; stage_jump_suggestion: string }>,
) {
  if (!enrichedFilename) return null
  const stem = fileStem(enrichedFilename).toLowerCase()
  return (
    artifacts.find((artifact) => {
      const artifactStem = fileStem(artifact.filename).toLowerCase()
      return artifactStem === `${stem}_reid`
    }) ?? null
  )
}

function fileStem(filename: string): string {
  const dot = filename.lastIndexOf('.')
  return dot >= 0 ? filename.slice(0, dot) : filename
}
