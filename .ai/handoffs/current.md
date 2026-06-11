# Handoff: Zone Lasso Selection + Dual-Test SAR Scoring

## Requested Role
[DEV:frontend] + [DEV:backend]

## Goal

Add a freehand lasso tool to the **Localization page** that lets the user draw a polygon search zone on the map. The zone persists into **Result Analysis** where it:

1. Filters visible clusters to only those whose peak falls inside the zone
2. Powers **Test 1 (SAR Operational Score)** — computed entirely on the frontend from circle count vs expected target count + uncertainty area vs zone area
3. Scopes **Test 2 (Research Score)** — the existing evaluation, now zone-filtered by passing `cluster_ids` + `gt_ids` to the backend
4. Shows a **Combined Score** = mean(Test 1, Test 2)

No pipeline reruns. No new npm packages. No changes to the localization or re-ID engines.

---

## Codebase Context You Must Read First

Before writing a single line, read these files completely:

- `frontend/src/state/SessionContext.tsx` — shared state across pages; you will add `lassoPolygon` here
- `frontend/src/pages/LocalizationPage.tsx` — where the lasso is drawn; study `visibleClusters` useMemo and the `MapContainer` structure
- `frontend/src/pages/LocalizationPage.css` — match existing class naming conventions
- `frontend/src/pages/ResultAnalysisPage.tsx` — where Test 1 + combined score appear; study `visibleClusters`, `handleEvaluate`, and the score panel section (lines 706–738)
- `frontend/src/pages/ResultAnalysisPage.css` — match existing class naming conventions
- `frontend/src/api/sessions.ts` — `runEvaluation` function you will extend
- `backend/app/api/result_analysis.py` — `EvaluateRequest` model and endpoint you will extend

---

## Deliverables

### 1. New file: `frontend/src/utils/geoUtils.ts`

Three pure functions, zero imports from React or Leaflet:

```typescript
/**
 * Ray-casting point-in-polygon test.
 * polygon is an array of [lat, lon] pairs (closed or open — algorithm handles both).
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
 * Returns the approximate area in m² of a lat/lon polygon
 * using Shoelace + flat-earth projection at the centroid.
 * Accurate to < 0.5% for zones under 5 km².
 */
export function polygonAreaM2(polygon: [number, number][]): number {
  const n = polygon.length
  if (n < 3) return 0
  const centLat = polygon.reduce((s, p) => s + p[0], 0) / n
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

/**
 * Sum of π·r² for each cluster's first uncertainty region radius.
 * clusters must already be the filtered in-zone list.
 */
export function sumCircleAreasM2(clusters: Array<{ uncertainty_regions: Array<{ radius_m: number }> }>): number {
  return clusters.reduce((sum, c) => {
    const r = c.uncertainty_regions[0]?.radius_m ?? 0
    return sum + Math.PI * r * r
  }, 0)
}
```

---

### 2. New file: `frontend/src/components/LassoTool.tsx`

A react-leaflet component rendered **inside** `<MapContainer>`. When `active` is true it intercepts mouse events to build a freehand polygon.

```typescript
import { useEffect, useRef } from 'react'
import { Polyline, useMap, useMapEvents } from 'react-leaflet'

interface Props {
  active: boolean
  onComplete: (polygon: [number, number][]) => void
  onCancel: () => void
}

export default function LassoTool({ active, onComplete, onCancel }: Props) {
  const map = useMap()
  const drawing = useRef(false)
  const points = useRef<[number, number][]>([])
  const lastPixel = useRef<{ x: number; y: number } | null>(null)
  // livePoints drives the Polyline re-render; we use a separate ref for accumulation
  // to avoid re-render on every mousemove tick.
  // Use a state only for the rendered preview:
  // (implement with useState for livePoints, updated in throttled mousemove)
  ...
}
```

**Full requirements for LassoTool:**

- Props: `active: boolean`, `onComplete(polygon: [number,number][])`, `onCancel()`
- When `active` becomes true: call `map.dragging.disable()`; set `drawing.current = false`; clear `points.current`
- When `active` becomes false (or component unmounts): call `map.dragging.enable()`
- Use `useMapEvents` for:
  - `mousedown` → if active: set `drawing.current = true`, clear `points.current`, push first `[e.latlng.lat, e.latlng.lng]`
  - `mousemove` → if `drawing.current`: check pixel distance from `lastPixel.current` using `map.latLngToContainerPoint(e.latlng)`; if distance ≥ 8px, push point and update `lastPixel`; update React state for live preview
  - `mouseup` → if `drawing.current`: set `drawing.current = false`, call `map.dragging.enable()`, call `onComplete(points.current)` if ≥ 3 points, else `onCancel()`
- Also listen for `keydown` on `window` (not map): if `Escape` and `drawing.current`, cancel draw, call `onCancel()`
- During draw render: `<Polyline positions={livePoints} pathOptions={{ color: '#facc15', weight: 2, dashArray: '6 4', opacity: 0.85 }} />`
- After draw (component does NOT render the closed polygon — the parent does via `<Polygon>` from context)
- When `active` is false: return `null`

**Implementation notes:**
- Use a `useState<[number,number][]>([])` for the live preview polyline (updated in throttled mousemove)
- Use `useRef<[number,number][]>([])` for point accumulation (avoids closure stale state issues)
- The `useEffect` watching `active` handles drag enable/disable
- Clean up the window keydown listener in the effect's cleanup

---

### 3. Modify: `frontend/src/state/SessionContext.tsx`

Add `lassoPolygon` to the shared context so both pages can read/write it.

**Add to `SessionCtx` type:**
```typescript
lassoPolygon: [number, number][] | null
setLassoPolygon: (polygon: [number, number][] | null) => void
```

**Add `useState` in `SessionProvider`:**
```typescript
const [lassoPolygon, setLassoPolygon] = useState<[number, number][] | null>(null)
```

**Clear on session change:** In `SessionProvider`, add a `useEffect` that calls `setLassoPolygon(null)` when `session?.session_id` changes (i.e., a new folder is selected).

**Expose in context value:**
```typescript
lassoPolygon,
setLassoPolygon,
```

---

### 4. Modify: `frontend/src/pages/LocalizationPage.tsx`

#### 4a. Imports to add
```typescript
import { Polygon } from 'react-leaflet'  // add to existing react-leaflet import
import LassoTool from '../components/LassoTool'
import { pointInPolygon } from '../utils/geoUtils'
```

#### 4b. New local state
```typescript
const [lassoActive, setLassoActive] = useState(false)
```

#### 4c. Read/write lasso from context
```typescript
const { session, refreshSession, lassoPolygon, setLassoPolygon } = useSession()
```

#### 4d. Zone-filtered visibleClusters
Replace the existing `visibleClusters` useMemo to add the lasso filter as a third condition:

```typescript
const visibleClusters = useMemo(
  () =>
    (result?.cluster_results ?? []).filter((cluster) => {
      if (cluster.status !== 'success' || !cluster.primary_peak) return false
      if (hiddenClusters.has(cluster.cluster_id)) return false
      if (!showStaticClusters && cluster.cluster_type === 'static') return false
      if (!showNoiseClusters && cluster.cluster_type === 'noise') return false
      if (lassoPolygon && !pointInPolygon(cluster.primary_peak.lat, cluster.primary_peak.lon, lassoPolygon)) return false
      return true
    }),
  [result, hiddenClusters, showStaticClusters, showNoiseClusters, lassoPolygon],
)
```

**Note:** The existing code filters `cluster.status === 'success'` only when rendering, not in visibleClusters. Keep consistent with what the page already does — check the original carefully and preserve the `status` filter correctly.

#### 4e. Zone badge derived value
```typescript
const zoneClusterCount = lassoPolygon
  ? (result?.cluster_results ?? []).filter(
      (c) => c.status === 'success' && c.primary_peak &&
             pointInPolygon(c.primary_peak.lat, c.primary_peak.lon, lassoPolygon)
    ).length
  : null
```

#### 4f. Map controls UI additions

In the existing `<div className="map-controls">` block, add **before** the layer toggle divider:

```tsx
<div className="map-controls-divider" />

{!lassoPolygon ? (
  <button
    className={`layer-btn${lassoActive ? ' active' : ''}`}
    onClick={() => setLassoActive((v) => !v)}
    title="Draw a freehand zone to filter clusters"
  >
    {lassoActive ? 'Drawing...' : 'Select Zone'}
  </button>
) : (
  <>
    <span className="zone-badge">{zoneClusterCount} clusters in zone</span>
    <button
      className="layer-btn"
      onClick={() => { setLassoPolygon(null); setLassoActive(false) }}
    >
      Clear Zone
    </button>
  </>
)}
```

#### 4g. Inside `<MapContainer>` — add these two elements

**LassoTool** (anywhere inside, before closing tag):
```tsx
<LassoTool
  active={lassoActive}
  onComplete={(polygon) => {
    setLassoPolygon(polygon)
    setLassoActive(false)
  }}
  onCancel={() => setLassoActive(false)}
/>
```

**Polygon overlay** (render when polygon exists):
```tsx
{lassoPolygon && (
  <Polygon
    positions={lassoPolygon}
    pathOptions={{
      color: '#facc15',
      weight: 2,
      dashArray: '8 5',
      fillOpacity: 0.06,
      opacity: 0.9,
    }}
  />
)}
```

#### 4h. Map container cursor class

On the `<MapContainer>` element add the conditional class:
```tsx
className={`localization-map${lassoActive ? ' lasso-mode' : ''}`}
```

---

### 5. Modify: `frontend/src/pages/LocalizationPage.css`

Add at the end:

```css
.lasso-mode {
  cursor: crosshair !important;
}

.lasso-mode .leaflet-grab,
.lasso-mode .leaflet-crosshair {
  cursor: crosshair !important;
}

.zone-badge {
  font-size: 0.78rem;
  font-weight: 600;
  color: #facc15;
  background: rgba(250, 204, 21, 0.12);
  border: 1px solid rgba(250, 204, 21, 0.35);
  border-radius: 4px;
  padding: 2px 8px;
  white-space: nowrap;
}
```

---

### 6. Modify: `frontend/src/pages/ResultAnalysisPage.tsx`

#### 6a. Imports to add
```typescript
import { Polygon } from 'react-leaflet'   // add to existing react-leaflet import
import { pointInPolygon, polygonAreaM2, sumCircleAreasM2 } from '../utils/geoUtils'
```

#### 6b. Read lasso from context
```typescript
const { session, refreshSession, lassoPolygon, setLassoPolygon } = useSession()
```

#### 6c. New state for Test 1
```typescript
const [expectedEmitters, setExpectedEmitters] = useState<number | ''>(1)
```

#### 6d. Zone-filtered successfulClusters

The existing `successfulClusters` useMemo stays unchanged. Add a new derived value:

```typescript
const zoneClusterIds = useMemo<Set<string> | null>(() => {
  if (!lassoPolygon) return null
  return new Set(
    successfulClusters
      .filter((c) => c.primary_peak && pointInPolygon(c.primary_peak.lat, c.primary_peak.lon, lassoPolygon))
      .map((c) => c.cluster_id)
  )
}, [successfulClusters, lassoPolygon])
```

#### 6e. Modify visibleClusterIds useMemo

Add lasso filter as an additional condition after existing filters:

```typescript
const visibleClusterIds = useMemo(
  () =>
    new Set(
      successfulClusters
        .filter((c) => showStaticClusters || c.cluster_type !== 'static')
        .filter((c) => !hiddenClusters.has(c.cluster_id))
        .filter((c) => !zoneClusterIds || zoneClusterIds.has(c.cluster_id))
        .map((c) => c.cluster_id),
    ),
  [successfulClusters, showStaticClusters, hiddenClusters, zoneClusterIds],
)
```

#### 6f. In-zone GT points

```typescript
const zoneGtIds = useMemo<Set<string> | null>(() => {
  if (!lassoPolygon || !raState?.gt_points) return null
  return new Set(
    raState.gt_points
      .filter((g) => pointInPolygon(g.lat, g.lon, lassoPolygon))
      .map((g) => g.gt_id)
  )
}, [raState?.gt_points, lassoPolygon])
```

#### 6g. Modify handleEvaluate to pass zone filters

When a polygon is active, pass the filtered IDs:

```typescript
async function handleEvaluate() {
  if (!session?.session_id) return
  setLoading(true)
  setError(null)
  try {
    const params: Parameters<typeof runEvaluation>[1] = { ...evalParams }
    if (zoneClusterIds) params.cluster_ids = [...zoneClusterIds]
    if (zoneGtIds) params.gt_ids = [...zoneGtIds]
    const result = await runEvaluation(session.session_id, params)
    setEvalResult(result)
    await loadState()
  } catch (err: unknown) {
    setError(String(err))
  } finally {
    setLoading(false)
  }
}
```

#### 6h. Test 1 computed values (useMemo)

```typescript
const test1 = useMemo(() => {
  if (!lassoPolygon || typeof expectedEmitters !== 'number' || expectedEmitters < 1) return null

  const inZoneClusters = visibleClusters  // already filtered by zone via visibleClusterIds
  const nCircles = inZoneClusters.length
  const nExpected = expectedEmitters

  const sCount = Math.max(0, 1 - Math.abs(nCircles - nExpected) / nExpected)

  const lassoArea = polygonAreaM2(lassoPolygon)
  const circleArea = sumCircleAreasM2(inZoneClusters)
  const areaRatio = lassoArea > 0 ? circleArea / lassoArea : 1
  const sArea = Math.max(0, 1 - areaRatio * areaRatio)

  const total = (sCount + sArea) / 2

  return { total, sCount, sArea, nCircles, nExpected, circleArea, lassoArea, areaRatio }
}, [lassoPolygon, expectedEmitters, visibleClusters])
```

#### 6i. Combined score (useMemo)

```typescript
const combinedScore = useMemo(() => {
  if (!test1 || !evalResult) return null
  return (test1.total + evalResult.score.total) / 2
}, [test1, evalResult])
```

#### 6j. Zone badge in map controls

In the existing `<div className="map-controls">`, add after the existing last divider:

```tsx
<div className="map-controls-divider" />
{lassoPolygon ? (
  <>
    <span className="zone-badge">{visibleClusters.length} clusters in zone</span>
    <button className="layer-btn" onClick={() => setLassoPolygon(null)}>
      Clear Zone
    </button>
  </>
) : (
  <span className="zone-badge-empty">No zone — draw on Localization page</span>
)}
```

#### 6k. Polygon overlay inside `<MapContainer>`

```tsx
{lassoPolygon && (
  <Polygon
    positions={lassoPolygon}
    pathOptions={{
      color: '#facc15',
      weight: 2,
      dashArray: '8 5',
      fillOpacity: 0.06,
      opacity: 0.9,
    }}
  />
)}
```

#### 6l. Cluster list — dim out-of-zone clusters

In the cluster list's `<label>` element, add `cluster-row-out-of-zone` class when the cluster is outside the zone:

```tsx
<label
  key={cluster.cluster_id}
  className={[
    'cluster-row',
    hiddenClusters.has(cluster.cluster_id) ? 'cluster-row-hidden' : '',
    zoneClusterIds && !zoneClusterIds.has(cluster.cluster_id) ? 'cluster-row-out-of-zone' : '',
  ].filter(Boolean).join(' ')}
>
```

#### 6m. Test 1 panel — add as a new `<section>` BEFORE the existing score panel (line ~706)

Place this above the `{evalResult && (...)}` block:

```tsx
{test1 && (
  <section className="score-panel test1-panel">
    <div className="test1-header">
      <span className="test1-label">Test 1 — SAR Operational</span>
      <span className="score-total">{(test1.total * 100).toFixed(1)}%</span>
    </div>
    <div className="score-grid">
      <div className="score-item">
        <span>Count ({test1.nCircles} circles / {test1.nExpected} expected)</span>
        <strong>{(test1.sCount * 100).toFixed(1)}%</strong>
      </div>
      <div className="score-item">
        <span>Area ({(test1.areaRatio * 100).toFixed(1)}% of zone covered)</span>
        <strong>{(test1.sArea * 100).toFixed(1)}%</strong>
      </div>
    </div>
    <div className="test1-area-info">
      Zone: {(test1.lassoArea / 1e6).toFixed(4)} km² &nbsp;|&nbsp;
      Circles: {(test1.circleArea / 1e6).toFixed(4)} km²
    </div>
  </section>
)}
```

#### 6n. Expected emitter input — add inside the existing `<section className="ra-panel">` for Evaluation, ABOVE the "Run Evaluation" button

```tsx
<div className="eval-param-row">
  <label>
    Expected emitters (Test 1) <HelpTip text={HELP.expected_emitters} />
  </label>
  <input
    type="number"
    min="1"
    step="1"
    value={expectedEmitters}
    onChange={(e) => setExpectedEmitters(e.target.value === '' ? '' : Math.max(1, parseInt(e.target.value, 10)))}
  />
</div>
```

#### 6o. Combined score — modify the existing score panel heading area

In the existing `{evalResult && (...)}` block, at the very top of the `<section className="score-panel">`, add:

```tsx
{combinedScore !== null && (
  <div className="combined-score-row">
    <span className="combined-score-label">Combined Score (Test 1 + Test 2)</span>
    <span className="combined-score-value">{(combinedScore * 100).toFixed(1)}%</span>
  </div>
)}
```

And change the "Total" label on the existing score block to "Test 2 — Research":

```tsx
<div>
  <div className="score-label">{combinedScore !== null ? 'Test 2 — Research' : 'Total'}</div>
  <div className="score-total">{(evalResult.score.total * 100).toFixed(1)}%</div>
</div>
```

---

### 7. Modify: `frontend/src/pages/ResultAnalysisPage.css`

Add at the end:

```css
.test1-panel {
  border-left: 3px solid #facc15;
}

.test1-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.test1-label {
  font-weight: 650;
  font-size: 0.9rem;
  color: #facc15;
}

.test1-area-info {
  font-size: 0.78rem;
  color: var(--color-text-muted);
  margin-top: 4px;
}

.combined-score-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 8px;
  margin-bottom: 8px;
  border-bottom: 1px solid var(--color-border);
}

.combined-score-label {
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.combined-score-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text);
}

.cluster-row-out-of-zone {
  opacity: 0.35;
}

.zone-badge {
  font-size: 0.78rem;
  font-weight: 600;
  color: #facc15;
  background: rgba(250, 204, 21, 0.12);
  border: 1px solid rgba(250, 204, 21, 0.35);
  border-radius: 4px;
  padding: 2px 8px;
  white-space: nowrap;
}

.zone-badge-empty {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  font-style: italic;
}
```

---

### 8. Modify: `frontend/src/api/sessions.ts`

Find `runEvaluation` and add two optional fields to its params argument:

```typescript
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
    cluster_ids?: string[]   // ← ADD
    gt_ids?: string[]        // ← ADD
  },
) =>
```

The body already spreads `params` into the JSON — no other changes needed in this function.

---

### 9. Modify: `frontend/src/helpTexts.ts`

Add one entry:

```typescript
expected_emitters:
  'Number of real-world targets (people/devices) you expect in the search zone. Used for Test 1 count score: penalty is proportional to how far the detected circle count deviates from this.',
```

---

### 10. Modify: `backend/app/api/result_analysis.py`

#### 10a. Extend `EvaluateRequest`

Find the `EvaluateRequest` model and add two optional fields:

```python
cluster_ids: list[str] | None = None
gt_ids: list[str] | None = None
```

#### 10b. Filter in the evaluate endpoint

Find the evaluate endpoint handler. It currently builds `predictions` from the session's localization result and `gt_points` from the session's stored GT. After both lists are built, add the filters **before** the call to `evaluate(...)`:

```python
if body.cluster_ids is not None:
    allowed = set(body.cluster_ids)
    predictions = [p for p in predictions if p["cluster_id"] in allowed]

if body.gt_ids is not None:
    allowed = set(body.gt_ids)
    gt_points = [g for g in gt_points if g["gt_id"] in allowed]
```

No other changes to the backend.

---

## Behavior Contract

| Scenario | Expected |
|---|---|
| No lasso drawn | All clusters visible on both pages. No Test 1. Score panel shows Test 2 only. |
| Lasso drawn, no expected count | Zone filter active on both pages. Test 1 panel not shown (input empty). |
| Lasso drawn + expected count ≥ 1 | Test 1 panel visible with count + area sub-scores. |
| Lasso + GT points + Run Evaluation | Backend filters to zone clusters + zone GT. Test 2 is zone-scoped. Combined score shown. |
| No lasso + GT + Run Evaluation | Backend runs on all clusters + all GT. Existing behavior unchanged. |
| Navigate away and back | Lasso polygon persists (lives in SessionContext). |
| New session/folder selected | Lasso polygon is cleared automatically. |
| Escape during draw | Draw cancelled. Map pan re-enabled. No polygon set. |
| Fewer than 3 points on mouseup | Draw cancelled. No polygon set. |

---

## Definition of Done

- [ ] `geoUtils.ts` exports `pointInPolygon`, `polygonAreaM2`, `sumCircleAreasM2` with correct results
- [ ] Freehand lasso tool draws on Localization map; polygon persists after mouseup
- [ ] Map drag disabled during draw; re-enabled after completion or cancel
- [ ] Escape cancels in-progress draw
- [ ] Drawn polygon visible as dashed yellow overlay on both Localization and Result Analysis maps
- [ ] "Clear Zone" removes polygon from both pages simultaneously
- [ ] Clusters outside zone are hidden on map and dimmed in sidebar list (both pages)
- [ ] Test 1 panel appears on Result Analysis when polygon + expected count are both set
- [ ] Count score formula: `max(0, 1 − |n_circles − n_expected| / n_expected)`
- [ ] Area score formula: `max(0, 1 − (circleArea / lassoArea)²)`
- [ ] Combined score = `(test1.total + evalResult.score.total) / 2`, shown only when both exist
- [ ] Run Evaluation passes `cluster_ids` and `gt_ids` when zone is active
- [ ] Backend filters predictions + GT correctly; existing behavior unchanged when no IDs passed
- [ ] Frontend tests pass (`npm test`)
- [ ] Backend tests pass (`pytest tests/`)
- [ ] No TypeScript errors (`npm run build`)
