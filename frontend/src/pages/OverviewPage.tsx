import { useEffect, useState } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip } from 'react-leaflet'
import { getInventory, runOverview, type OverviewResult } from '../api/sessions'
import { useSession } from '../state/SessionContext'
import './OverviewPage.css'

type MapLayer = 'satellite' | 'osm'

export default function OverviewPage() {
  const { session } = useSession()
  const [csvFiles, setCsvFiles] = useState<Array<{ filename: string }>>([])
  const [selectedCsv, setSelectedCsv] = useState('')
  const [overview, setOverview] = useState<OverviewResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mapLayer, setMapLayer] = useState<MapLayer>('satellite')
  const [showHeartbeats, setShowHeartbeats] = useState(true)

  useEffect(() => {
    if (!session?.session_id) {
      setCsvFiles([])
      setSelectedCsv('')
      setOverview(null)
      return
    }

    setError(null)
    getInventory(session.session_id)
      .then((inventory) => setCsvFiles(inventory.raw_csvs))
      .catch((err: unknown) => setError(String(err)))
  }, [session?.session_id])

  async function handleCsvChange(filename: string) {
    setSelectedCsv(filename)
    setOverview(null)

    if (!session?.session_id || !filename) {
      return
    }

    setLoading(true)
    setError(null)
    try {
      const result = await runOverview(session.session_id, filename)
      setOverview(result)
    } catch (err: unknown) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  const allPoints = overview?.gps_points ?? []
  const visiblePoints = showHeartbeats
    ? allPoints
    : allPoints.filter((p) => p.frame_type !== 'heartbeat')

  const mapCenter: [number, number] = visiblePoints.length
    ? [visiblePoints[0].lat, visiblePoints[0].lon]
    : allPoints.length
      ? [allPoints[0].lat, allPoints[0].lon]
      : [32.0, 34.8]

  return (
    <div className="overview-page">
      <div className="overview-top-bar">
        <label htmlFor="overview-csv-select" className="field-label">
          Scan CSV
        </label>
        <select
          id="overview-csv-select"
          className="folder-select"
          value={selectedCsv}
          onChange={(event) => handleCsvChange(event.target.value)}
          disabled={!session}
        >
          <option value="">- Select a CSV file to begin inspection -</option>
          {csvFiles.map((file) => (
            <option key={file.filename} value={file.filename} dir="auto">
              {file.filename}
            </option>
          ))}
        </select>
      </div>

      {!session && (
        <p className="empty-state">No active session. Go to Session Start to select a folder.</p>
      )}

      {session && !selectedCsv && !error && (
        <p className="empty-state">Select a CSV file above to begin inspection.</p>
      )}

      {error && <p className="error-banner">{error}</p>}
      {loading && <p className="loading-hint">Loading CSV data...</p>}

      {overview && Array.isArray(overview.gps_points) && !loading && (
        <div className="overview-body">
          <div className="overview-left">
            {overview.warning && <div className="warning-banner">{overview.warning}</div>}

            <div className="stats-grid">
              <StatCard label="Records" value={overview.record_count.toLocaleString()} />
              <StatCard label="Unique MACs" value={overview.unique_macs.toLocaleString()} />
              <StatCard label="GPS Fix" value={`${overview.gps_fix_pct}%`} />
              <StatCard
                label="RSSI Range"
                value={
                  overview.rssi_min != null && overview.rssi_max != null
                    ? `${overview.rssi_min} to ${overview.rssi_max} dBm`
                    : '-'
                }
              />
              <StatCard
                label="RSSI Mean"
                value={overview.rssi_mean != null ? `${overview.rssi_mean} dBm` : '-'}
              />
            </div>

            <div className="panel">
              <h2 className="panel-title">Devices</h2>
              {overview.device_table.length === 0 ? (
                <p className="empty-state">No devices found in this CSV.</p>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>MAC Address</th>
                      <th>Packets</th>
                      <th>RSSI Min</th>
                      <th>RSSI Max</th>
                      <th>RSSI Mean</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview.device_table.map((row) => (
                      <tr key={row.src_mac || 'unknown-mac'}>
                        <td className="mono" dir="ltr">
                          {row.src_mac || '-'}
                        </td>
                        <td>{row.packet_count}</td>
                        <td>{row.rssi_min ?? '-'}</td>
                        <td>{row.rssi_max ?? '-'}</td>
                        <td>{row.rssi_mean ?? '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          <div className="overview-right">
            {overview.gps_points.length === 0 ? (
              <div className="map-empty-state">No GPS points in this CSV.</div>
            ) : (
              <>
                <div className="map-controls">
                  <label className="map-control-check">
                    <input
                      type="checkbox"
                      checked={showHeartbeats}
                      onChange={(e) => setShowHeartbeats(e.target.checked)}
                    />
                    Heartbeats
                  </label>
                  <div className="layer-toggle">
                    <button
                      className={`layer-btn${mapLayer === 'satellite' ? ' active' : ''}`}
                      onClick={() => setMapLayer('satellite')}
                    >
                      Satellite
                    </button>
                    <button
                      className={`layer-btn${mapLayer === 'osm' ? ' active' : ''}`}
                      onClick={() => setMapLayer('osm')}
                    >
                      Map
                    </button>
                  </div>
                </div>
                <MapContainer center={mapCenter} zoom={15} maxZoom={20} className="overview-map">
                  {mapLayer === 'satellite' ? (
                    <TileLayer
                      key="satellite"
                      attribution='Tiles &copy; Esri &mdash; Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, GIS User Community'
                      url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                      maxNativeZoom={18}
                      maxZoom={20}
                    />
                  ) : (
                    <TileLayer
                      key="osm"
                      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                      maxNativeZoom={19}
                      maxZoom={20}
                    />
                  )}
                  {visiblePoints.map((point, index) => (
                    <CircleMarker
                      key={`${point.timestamp_utc}-${point.src_mac}-${index}`}
                      center={[point.lat, point.lon]}
                      radius={4}
                      pathOptions={{
                        color: rssiToColor(point.rssi),
                        fillColor: rssiToColor(point.rssi),
                        fillOpacity: 0.8,
                        weight: 1,
                      }}
                    >
                      <Tooltip>
                        <span className="mono" dir="ltr">
                          {point.src_mac || '-'}
                        </span>
                        <br />
                        {point.rssi != null ? `${point.rssi} dBm` : 'no RSSI'}
                        <br />
                        {point.timestamp_utc}
                      </Tooltip>
                    </CircleMarker>
                  ))}
                </MapContainer>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat-card">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
    </div>
  )
}

function rssiToColor(rssi: number | null): string {
  if (rssi == null) return '#94a3b8'
  if (rssi > -60) return '#15803d'
  if (rssi > -75) return '#b45309'
  return '#b91c1c'
}
