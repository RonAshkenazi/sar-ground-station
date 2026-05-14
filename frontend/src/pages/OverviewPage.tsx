import { useEffect, useMemo, useState } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip } from 'react-leaflet'
import { getInventory, runOverview, type OverviewResult } from '../api/sessions'
import { useSession } from '../state/SessionContext'
import './OverviewPage.css'

type MapLayer = 'satellite' | 'osm'
type SortColumn = 'src_mac' | 'packet_count' | 'rssi_mean'
type DeviceRow = OverviewResult['device_table'][number]
type GpsPoint = OverviewResult['gps_points'][number]

export default function OverviewPage() {
  const { session } = useSession()
  const [csvFiles, setCsvFiles] = useState<Array<{ filename: string }>>([])
  const [selectedCsv, setSelectedCsv] = useState('')
  const [overview, setOverview] = useState<OverviewResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mapLayer, setMapLayer] = useState<MapLayer>('satellite')
  const [showHeartbeats, setShowHeartbeats] = useState(true)
  const [filtersOpen, setFiltersOpen] = useState(true)
  const [filterRssiMin, setFilterRssiMin] = useState<string>('')
  const [filterRssiMax, setFilterRssiMax] = useState<string>('')
  const [filterMacPrefix, setFilterMacPrefix] = useState('')
  const [filterMinPackets, setFilterMinPackets] = useState<string>('')
  const [filterTimeStart, setFilterTimeStart] = useState('')
  const [filterTimeEnd, setFilterTimeEnd] = useState('')
  const [sortColumn, setSortColumn] = useState<SortColumn>('packet_count')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

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
  const visiblePoints = useMemo(
    () => (showHeartbeats ? allPoints : allPoints.filter((p) => p.frame_type !== 'heartbeat')),
    [allPoints, showHeartbeats],
  )

  const pointFilteredMacs = useMemo(() => {
    if (!filterTimeStart && !filterTimeEnd) return null
    return new Set(
      allPoints
        .filter((point) => isPointInTimeRange(point, filterTimeStart, filterTimeEnd))
        .map((point) => point.src_mac),
    )
  }, [allPoints, filterTimeStart, filterTimeEnd])

  const filteredDevices = useMemo(() => {
    let rows = (overview?.device_table ?? []).filter((row) => passesDeviceFilters(row, {
      macPrefix: filterMacPrefix,
      minPackets: filterMinPackets,
      rssiMin: filterRssiMin,
      rssiMax: filterRssiMax,
    }))
    if (pointFilteredMacs) rows = rows.filter((row) => pointFilteredMacs.has(row.src_mac))
    rows = [...rows].sort((a, b) => {
      const comparison = compareDevices(a, b, sortColumn)
      return sortDir === 'asc' ? comparison : -comparison
    })
    return rows
  }, [overview, filterMacPrefix, filterMinPackets, filterRssiMin, filterRssiMax, pointFilteredMacs, sortColumn, sortDir])

  const filteredDeviceMacs = useMemo(
    () => new Set(filteredDevices.map((row) => row.src_mac)),
    [filteredDevices],
  )

  const filteredPoints = useMemo(() => {
    return visiblePoints.filter((point) => {
      if (!filteredDeviceMacs.has(point.src_mac)) return false
      if (!passesPointFilters(point, { macPrefix: filterMacPrefix, rssiMin: filterRssiMin, rssiMax: filterRssiMax })) {
        return false
      }
      return isPointInTimeRange(point, filterTimeStart, filterTimeEnd)
    })
  }, [visiblePoints, filteredDeviceMacs, filterMacPrefix, filterRssiMin, filterRssiMax, filterTimeStart, filterTimeEnd])

  const mapCenter: [number, number] = filteredPoints.length
    ? [filteredPoints[0].lat, filteredPoints[0].lon]
    : allPoints.length
      ? [allPoints[0].lat, allPoints[0].lon]
      : [32.0, 34.8]

  function clearFilters() {
    setFilterRssiMin('')
    setFilterRssiMax('')
    setFilterMacPrefix('')
    setFilterMinPackets('')
    setFilterTimeStart('')
    setFilterTimeEnd('')
    setSortColumn('packet_count')
    setSortDir('desc')
  }

  function handleSort(column: SortColumn) {
    if (sortColumn === column) {
      setSortDir((value) => (value === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortColumn(column)
      setSortDir(column === 'src_mac' ? 'asc' : 'desc')
    }
  }

  function sortIndicator(column: SortColumn) {
    if (sortColumn !== column) return ''
    return sortDir === 'asc' ? ' ^' : ' v'
  }

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
              <div className="panel-title-row">
                <h2 className="panel-title">Devices</h2>
                <button className="filter-toggle" type="button" onClick={() => setFiltersOpen((value) => !value)}>
                  Filters {filtersOpen ? '^' : 'v'}
                </button>
              </div>
              {filtersOpen && (
                <div className="filter-bar">
                  <label>
                    MAC prefix
                    <input type="text" value={filterMacPrefix} onChange={(event) => setFilterMacPrefix(event.target.value)} />
                  </label>
                  <label>
                    Min packets
                    <input type="number" value={filterMinPackets} onChange={(event) => setFilterMinPackets(event.target.value)} />
                  </label>
                  <label>
                    RSSI min
                    <input type="number" value={filterRssiMin} onChange={(event) => setFilterRssiMin(event.target.value)} />
                  </label>
                  <label>
                    RSSI max
                    <input type="number" value={filterRssiMax} onChange={(event) => setFilterRssiMax(event.target.value)} />
                  </label>
                  <label>
                    Time from
                    <input type="text" value={filterTimeStart} onChange={(event) => setFilterTimeStart(event.target.value)} />
                  </label>
                  <label>
                    Time to
                    <input type="text" value={filterTimeEnd} onChange={(event) => setFilterTimeEnd(event.target.value)} />
                  </label>
                  <label>
                    Sort by
                    <select value={sortColumn} onChange={(event) => setSortColumn(event.target.value as SortColumn)}>
                      <option value="packet_count">Packets</option>
                      <option value="src_mac">MAC Address</option>
                      <option value="rssi_mean">RSSI Mean</option>
                    </select>
                  </label>
                  <label>
                    Direction
                    <select value={sortDir} onChange={(event) => setSortDir(event.target.value as 'asc' | 'desc')}>
                      <option value="desc">Descending</option>
                      <option value="asc">Ascending</option>
                    </select>
                  </label>
                  <button className="btn-secondary clear-filters" type="button" onClick={clearFilters}>
                    Clear filters
                  </button>
                </div>
              )}
              {overview.device_table.length === 0 ? (
                <p className="empty-state">No devices found in this CSV.</p>
              ) : (
                <>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>
                          <button className="sort-header" type="button" onClick={() => handleSort('src_mac')}>
                            MAC Address{sortIndicator('src_mac')}
                          </button>
                        </th>
                        <th>
                          <button className="sort-header" type="button" onClick={() => handleSort('packet_count')}>
                            Packets{sortIndicator('packet_count')}
                          </button>
                        </th>
                        <th>RSSI Min</th>
                        <th>RSSI Max</th>
                        <th>
                          <button className="sort-header" type="button" onClick={() => handleSort('rssi_mean')}>
                            RSSI Mean{sortIndicator('rssi_mean')}
                          </button>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredDevices.map((row) => (
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
                  <div className="row-count-hint">
                    Showing {filteredDevices.length.toLocaleString()} of {overview.device_table.length.toLocaleString()} devices
                  </div>
                </>
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
                  {filteredPoints.map((point, index) => (
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

function passesDeviceFilters(
  row: DeviceRow,
  filters: { macPrefix: string; minPackets: string; rssiMin: string; rssiMax: string },
): boolean {
  if (filters.macPrefix && !row.src_mac?.toLowerCase().startsWith(filters.macPrefix.toLowerCase())) return false
  if (filters.minPackets !== '' && row.packet_count < Number(filters.minPackets)) return false
  if (filters.rssiMin !== '' && (row.rssi_mean == null || row.rssi_mean < Number(filters.rssiMin))) return false
  if (filters.rssiMax !== '' && (row.rssi_mean == null || row.rssi_mean > Number(filters.rssiMax))) return false
  return true
}

function passesPointFilters(
  point: GpsPoint,
  filters: { macPrefix: string; rssiMin: string; rssiMax: string },
): boolean {
  if (filters.macPrefix && !point.src_mac?.toLowerCase().startsWith(filters.macPrefix.toLowerCase())) return false
  if (filters.rssiMin !== '' && (point.rssi == null || point.rssi < Number(filters.rssiMin))) return false
  if (filters.rssiMax !== '' && (point.rssi == null || point.rssi > Number(filters.rssiMax))) return false
  return true
}

function isPointInTimeRange(point: GpsPoint, start: string, end: string): boolean {
  if (start && point.timestamp_utc < start) return false
  if (end && point.timestamp_utc > end) return false
  return true
}

function compareDevices(a: DeviceRow, b: DeviceRow, column: SortColumn): number {
  if (column === 'src_mac') return (a.src_mac || '').localeCompare(b.src_mac || '')

  const av = a[column]
  const bv = b[column]
  if (av == null && bv == null) return 0
  if (av == null) return 1
  if (bv == null) return -1
  return av - bv
}
