/**
 * Ray-casting point-in-polygon test.
 * polygon is an array of [lat, lon] pairs. Closed and open polygons both work.
 */
export function pointInPolygon(lat: number, lon: number, polygon: [number, number][]): boolean {
  const n = polygon.length
  if (n < 3) return false
  let inside = false
  for (let i = 0, j = n - 1; i < n; j = i++) {
    const [lati, loni] = polygon[i]
    const [latj, lonj] = polygon[j]
    const intersects =
      loni > lon !== lonj > lon &&
      lat < ((latj - lati) * (lon - loni)) / (lonj - loni) + lati
    if (intersects) inside = !inside
  }
  return inside
}

/**
 * Approximate area in square metres using Shoelace + flat-earth projection
 * at the polygon centroid. Suitable for small operational search zones.
 */
export function polygonAreaM2(polygon: [number, number][]): number {
  const n = polygon.length
  if (n < 3) return 0
  const centLat = polygon.reduce((sum, point) => sum + point[0], 0) / n
  const mPerDegLat = 111320
  const mPerDegLon = 111320 * Math.cos((centLat * Math.PI) / 180)
  let area = 0
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n
    const xi = polygon[i][1] * mPerDegLon
    const yi = polygon[i][0] * mPerDegLat
    const xj = polygon[j][1] * mPerDegLon
    const yj = polygon[j][0] * mPerDegLat
    area += xi * yj - xj * yi
  }
  return Math.abs(area) / 2
}

function distPointToSegmentM(cx: number, cy: number, ax: number, ay: number, bx: number, by: number): number {
  const dx = bx - ax
  const dy = by - ay
  const lenSq = dx * dx + dy * dy
  if (lenSq === 0) return Math.hypot(cx - ax, cy - ay)
  const t = Math.max(0, Math.min(1, ((cx - ax) * dx + (cy - ay) * dy) / lenSq))
  return Math.hypot(cx - (ax + t * dx), cy - (ay + t * dy))
}

/**
 * Returns true if a circle (center in lat/lon, radius in metres) overlaps the polygon.
 * Handles: centre inside polygon, polygon edge within radius.
 */
export function circleIntersectsPolygon(
  centerLat: number,
  centerLon: number,
  radiusM: number,
  polygon: [number, number][],
): boolean {
  const n = polygon.length
  if (n < 3) return false
  if (pointInPolygon(centerLat, centerLon, polygon)) return true
  const centLat = polygon.reduce((s, p) => s + p[0], 0) / n
  const mPerDegLat = 111320
  const mPerDegLon = 111320 * Math.cos((centLat * Math.PI) / 180)
  const cx = centerLon * mPerDegLon
  const cy = centerLat * mPerDegLat
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n
    const ax = polygon[i][1] * mPerDegLon
    const ay = polygon[i][0] * mPerDegLat
    const bx = polygon[j][1] * mPerDegLon
    const by = polygon[j][0] * mPerDegLat
    if (distPointToSegmentM(cx, cy, ax, ay, bx, by) <= radiusM) return true
  }
  return false
}

/**
 * Sum of pi*r^2 for each cluster's first uncertainty region radius.
 * Clusters must already be filtered to the active zone.
 */
export function sumCircleAreasM2(clusters: Array<{ uncertainty_regions: Array<{ radius_m: number }> }>): number {
  return clusters.reduce((sum, cluster) => {
    const r = cluster.uncertainty_regions[0]?.radius_m ?? 0
    return sum + Math.PI * r * r
  }, 0)
}

/**
 * Area (m²) of the intersection between a circle and a polygon.
 * Uses a regular grid of sample points inside the circle; fraction inside the
 * polygon × πr² gives the intersection area.
 * gridN=40 → ~1 260 samples, < 0.5 % relative error for typical SAR circles.
 */
export function circleIntersectionAreaM2(
  centerLat: number,
  centerLon: number,
  radiusM: number,
  polygon: [number, number][],
  gridN = 40,
): number {
  if (radiusM <= 0 || polygon.length < 3) return 0
  const centLat = polygon.reduce((s, p) => s + p[0], 0) / polygon.length
  const mPerDegLat = 111320
  const mPerDegLon = 111320 * Math.cos((centLat * Math.PI) / 180)
  const cx = centerLon * mPerDegLon
  const cy = centerLat * mPerDegLat
  const step = (2 * radiusM) / gridN
  let inside = 0
  let total = 0
  for (let i = 0; i <= gridN; i++) {
    const my = -radiusM + i * step
    for (let j = 0; j <= gridN; j++) {
      const mx = -radiusM + j * step
      if (mx * mx + my * my > radiusM * radiusM) continue
      total++
      const pLat = (cy + my) / mPerDegLat
      const pLon = (cx + mx) / mPerDegLon
      if (pointInPolygon(pLat, pLon, polygon)) inside++
    }
  }
  return total === 0 ? 0 : (inside / total) * Math.PI * radiusM * radiusM
}
