# QA Review — Header Reactivity + Overview Page (Phase 1)

**Reviewer:** [QA] Claude  
**Date:** 2026-05-11  
**Codex result:** `.ai/codex_result.md`  
**Verdict:** **APPROVED** — one Low bug patched by Claude directly; no blockers remain

---

## Test Summary

| Check | Result |
|---|---|
| `cd backend && python -m pytest --tb=short -q` | **52 passed, 1 warning** |
| `cd frontend && npm run build` | **✓ 93 modules, zero TS errors** |
| Playwright smoke (`npx playwright test smoke.spec.ts`) | **22 passed, 11 skipped (cdp)** per Codex report |
| Path traversal on `POST /overview` with `../../etc/passwd` | **400** ✓ |
| Mode validation `PATCH /mode` with `"lte"` | **422** ✓ |

---

## Acceptance Criteria Check

| Criterion | Result |
|---|---|
| Header shows folder + mode after session creation | PASS — smoke test line 84–85 verifies `header-folder` and `header-mode-badge` update |
| `SessionContext.tsx` uses `useState` — reactive | PASS |
| `sessionStore.ts` deleted | PASS |
| `main.tsx` wraps with `<SessionProvider>` | PASS |
| `POST /overview` returns stats JSON | PASS |
| `POST /overview` 404 on unknown session | PASS |
| `POST /overview` 404 on missing CSV | PASS |
| `POST /overview` 400 on path traversal | PASS — validated against `folder_path`, not just `data_dir` (stricter than spec, intentional) |
| `active_overview_csv` updated in session state | PASS — `test_overview_endpoint_updates_session_state` confirms |
| Overview page: no-session state | PASS — dropdown disabled, "No active session" message |
| Overview page: CSV selected → stats cards, device table, Leaflet map | PASS |
| GPS points colored by RSSI | PASS — green >-60, amber >-75, red ≤-75 |
| Tooltip shows MAC, RSSI, timestamp | PASS |
| Device table: monospace MAC, `dir="ltr"` | PASS — line 127–128 of OverviewPage.tsx |
| `dir="auto"` on CSV filenames in dropdown | PASS — line 68 |

---

## Bug Found and Fixed

### Bug 1 — OverviewPage: empty-state and error showed together (FIXED by Claude)

**Severity:** Low  
**Component:** `frontend/src/pages/OverviewPage.tsx` line 79

When the inventory fetch failed (backend unreachable), both "Select a CSV file above to begin inspection." and the error banner rendered simultaneously — same pattern as the SessionStartPage bug from last sprint.

**Fix applied:**
```tsx
// before
{session && !selectedCsv && (
// after
{session && !selectedCsv && !error && (
```

Build confirmed clean after fix.

---

## Notes (No Fix Required)

### Note 1 — Overview RSSI Stats: All Rows vs GPS-Only
Codex computes RSSI stats from ALL rows in a single pass, not just GPS-fixed rows. This is cleaner and more complete than the handoff spec suggested. Approved.

### Note 2 — GPS Point Volume
For large scan files, all GPS points are serialized into the response JSON. At 50k GPS-fixed records this is ~5MB of JSON. Acceptable for Phase 1 field use (scan files are typically < 10k rows). Should be revisited if performance issues arise in Result Analysis.

### Note 3 — Leaflet Map Height
Map uses `min-height: 400px` fallback which prevents zero-height rendering. CSS flex chain (`overview-right: flex: 1`, `overview-map: height: 100%`) is correct. Acceptable.

### Note 4 — Smoke Test Header Reactivity Coverage
New E2E assertions (lines 84–85 of smoke.spec.ts) verify the Header reactivity fix end-to-end: after session creation, `header-folder` no longer says "No folder selected" and `header-mode-badge` shows the overridden mode. This is the exact regression test for the bug we fixed last sprint.

---

## Module Boundary Check

- `overview/stats.py` imports only stdlib (`csv`, `collections`, `pathlib`) — ✓ no forbidden deps
- `api/overview.py` imports from `session_navigation` (allowed) and `overview/stats` (own module) — ✓
- No algorithm modules imported from page/UI code — ✓

---

## Approved. Proceed to Calibration page.

---

# QA Review — Calibration Backend + Frontend (Phase 2)

**Reviewer:** [QA] Claude  
**Date:** 2026-05-11  
**Codex result:** `.ai/codex_result.md`  
**Verdict:** **APPROVED** — one Low bug patched by Claude directly; no blockers remain

---

## Test Summary

| Check | Result |
|---|---|
| `cd backend && python -m pytest --tb=short -q` | **57 passed, 1 warning** |
| `cd frontend && npm run build` | **✓ zero TS/Vite errors** |
| Playwright smoke (`npx playwright test smoke.spec.ts`) | **22 passed, 11 skipped (cdp)** |
| Path traversal on `POST /calibration/run` with `../other.csv` | **400** ✓ |
| Approve with no prior run | **422** ✓ |
| Fallback preset `"urban"` | `parameter_source: "fallback"` ✓ |

---

## Spec Compliance

| Criterion | Result |
|---|---|
| `POST /calibration/candidates` returns sorted unique MACs from CSV | PASS |
| `POST /calibration/run` stores `_pending_calibration`, returns success/failure JSON | PASS |
| `POST /calibration/approve` stores `SessionCalibration(parameter_source="derived")` | PASS |
| `POST /calibration/fallback` stores `SessionCalibration(parameter_source="fallback")` | PASS |
| Unknown session → 404 on all endpoints | PASS |
| Missing CSV → 404 | PASS |
| Path traversal outside session folder → 400 | PASS |
| `SessionCalibration.parameter_source` is `Literal["derived", "fallback"]` | PASS |
| CAL-07 (`_FIT_WARNING_MIN_SAMPLES`) left as `None` with TODO | PASS |
| CAL-08 (`_FIT_WARNING_MIN_INLIER_RATIO`) left as `None` with TODO | PASS |
| RANSAC uses fixed seed `random.Random(42)` (deterministic) | PASS |
| Haversine distance formula implemented correctly | PASS |
| `path_loss_n = -slope / 10.0` matches log-distance model `RSSI = rssi_at_1m - 10*n*log10(d)` | PASS |
| Sigma = std dev of residuals over inliers | PASS |
| Parameter clamping matches Part B ranges | PASS — gt_k[1,20], ransac_iterations[10,1000], threshold[1,15], floor[0.5,5] |
| Frontend `canRun` guard: disabled until CSV + MAC selected | PASS |
| Manual map mode also requires picked GT point before Run | PASS |
| Advanced params collapsed by default | PASS |
| SVG scatter: inliers filled, outliers hollow | PASS |
| Regression line drawn from `rssi_at_1m - 10*n*log10(d)` | PASS |
| Fallback panel always visible | PASS |

---

## Bug Found and Fixed

### Bug 1 — `btn-secondary` CSS class undefined (FIXED by Claude)

**Severity:** Low  
**Component:** `frontend/src/pages/CalibrationPage.tsx:365`, `CalibrationPage.css`

The "Use This Preset" button used `className="btn-secondary"` but this class was not defined anywhere in the project CSS. The button rendered with bare browser defaults.

**Fix applied:** Added `.btn-secondary`, `.btn-secondary:hover:not(:disabled)`, `.btn-secondary:disabled` to `CalibrationPage.css` as an outlined/ghost variant matching the existing `btn-primary` style contract.

---

## Notes (No Fix Required)

### Note 1 — GPS Track Loaded via `runOverview` (Codex Deviation — Approved)
The manual GT map in `CalibrationPage.tsx` loads GPS track points by calling `runOverview(sessionId, csv)` in parallel with `getCalibrationCandidates`. This reuses an existing endpoint rather than expanding the candidates API, which is a pragmatic and clean deviation. The side effect (setting `active_overview_csv` in session state) is harmless. Approved.

### Note 2 — RANSAC Quality: No test for RANSAC-path or gt_mode variations
Existing tests cover `enable_ransac=False` and `gt_mode="manual_map_click"`. The RANSAC code path and `mean_first_k`/`first_sample` GT modes are exercised only through the algorithm test indirectly. Not a blocker (the code is straightforward), but a coverage gap worth noting.

### Note 3 — Scatter Plot Performance
All scatter points are serialized into the `run` response JSON and rendered as individual SVG elements. For large CSVs with a single-MAC filter, this could mean thousands of SVG circles. Acceptable for Phase 1; no action needed.

---

## Module Boundary Check

- `engine.py` imports only stdlib (`csv`, `math`, `random`, `pathlib`) — ✓ no forbidden deps
- `api/calibration.py` imports from `session_navigation` (allowed), `calibration/engine` (own module), `canonical_models` (allowed) — ✓
- No algorithm modules imported from page/UI code — ✓

---

## Approved. Proceed to Enrichment.

---

# QA Review — Enrichment Backend + Frontend (Phase 4)

**Reviewer:** [QA] Claude  
**Date:** 2026-05-12  
**Codex result:** `.ai/codex_result.md`  
**Verdict:** **APPROVED WITH FIXES** — four bugs found; two fixed by Claude directly (Low + Medium); two remaining as known gaps (Low + known limitation)

---

## Test Summary

| Check | Result |
|---|---|
| `cd backend && python -m pytest --tb=short -q` | **63 passed, 1 warning** |
| `cd frontend && npm run build` | **✓ zero TS/Vite errors** |
| Playwright smoke | **22 passed, 11 skipped (cdp)** |
| Manual browser: calic_search1.csv (no PCAP match) | **Blocked correctly** ✓ |
| Manual browser: test-circle2.csv (PCAP match) | Run button enabled ✓ |
| Execution polling: quality panel render | **Fixed in this review** (see Bug 1) |

---

## Spec Compliance

| Criterion | Result |
|---|---|
| `POST /sessions/{id}/enrichment/run` validates session, CSV, matching PCAP | PASS |
| Returns `{execution_id, status: "pending"}` immediately | PASS |
| Background task: pending → running → success/failed | PASS |
| Matching PCAP found case-insensitively by CSV stem in same folder | PASS |
| Path traversal on `csv_filename` → 400 | PASS |
| No matching PCAP → 422 | PASS |
| Unknown session → 404 | PASS |
| `GET /api/executions/{id}` returns status dict | PASS |
| Unknown execution → 404 | PASS |
| Output artifact `{stem}_ENRICHED.csv` written to scan folder | PASS |
| ENR-01 through ENR-06 all marked TODO, not invented | PASS |
| BLE parsing stubbed with TODO | PASS |
| Re-ID section is placeholder only | PASS |
| PCAP status panel: green if PCAP found, red if blocked | PASS |
| Existing enriched artifact detected and activatable | PASS (case-insensitive stem match) |
| Quality panel: total_rows, matched_rows, match_rate | PASS (after Bug 1 fix) |
| `canRun` guard: disabled without session + CSV + pcapMatch | PASS |

---

## Bugs Found

### Bug 1 — Polling useEffect: quality panel never rendered (FIXED by Claude)

**Severity:** High (not Critical — enrichment wrote correctly, only display was broken)  
**Component:** `frontend/src/pages/ReIdEnrichmentPage.tsx`

The polling `setInterval` callback called `setExecution(next)` **before** the status check. In React 18, this is in the same synchronous block as `setQuality(...)`, so they should batch together. However the `await refreshInventory()` between `setQuality` and `window.clearInterval` created a post-`await` continuation where the already-cleaned-up interval reference was used. More critically: `setExecution(next)` with `status='success'` triggers the useEffect cleanup (interval cleared) AND a re-run of the effect (guard fires, exits early). The `setQuality` call was after `await refreshInventory()` in the original code — it was reachable but the async continuation was racing with React's cleanup. Moving quality/error state updates before `setExecution(next)` and making `refreshInventory` fire-and-forget eliminates the race.

**Fix applied:**
```tsx
// Before — setExecution first, then await, then quality
setExecution(next)
if (next.status === 'success') {
  setQuality(next.result_metadata as unknown as EnrichmentQuality)
  await refreshInventory()      // await here before clearInterval
  window.clearInterval(interval)
}

// After — quality first, then setExecution terminates the interval via cleanup
if (next.status === 'success') {
  setQuality(next.result_metadata as unknown as EnrichmentQuality)
  setExecution(next)
  window.clearInterval(interval)
  void refreshInventory()       // fire-and-forget
}
```

---

### Bug 2 — `btn-secondary` CSS class undefined in ReIdEnrichmentPage (FIXED by Claude)

**Severity:** Low  
**Component:** `frontend/src/pages/ReIdEnrichmentPage.tsx:171`, `ReIdEnrichmentPage.css`

"Activate for Re-ID" button used `className="btn-secondary"` but the class was not defined in `ReIdEnrichmentPage.css`. Same gap as the CalibrationPage bug from Phase 2.

**Fix applied:** Added `.btn-secondary`, `.btn-secondary:hover:not(:disabled)`, `.btn-secondary:disabled` to `ReIdEnrichmentPage.css`.

---

### Bug 3 — `src_vendor` missing from ENRICHMENT_COLUMNS and `_apply_match` (Known Gap)

**Severity:** Medium  
**Spec reference:** Enriched CSV schema in project memory (scan data deviations) and `EnrichedScanRecord`  
**Component:** `backend/app/modules/enrichment/engine.py`

Real `_enriched.csv` files include `src_vendor`. The engine omits it because OUI lookup requires a vendor database (MOD-003, not yet implemented). This is an acceptable gap for Phase 4 since MOD-003 is out of scope. `src_vendor` column will be missing from new `_ENRICHED.csv` outputs.

**No fix required now** — track as MOD-003 dependency.

---

### Bug 4 — `protocol="wifi"` hardcoded in `_run_enrichment_task` (Known Gap)

**Severity:** Low  
**Component:** `backend/app/api/enrichment.py:54`

Protocol is always `"wifi"` regardless of session mode. BLE enrichment is out of scope for this sprint (BLE PCAP parsing is a TODO stub). Acceptable for Phase 4.

**No fix required now** — will be addressed when BLE enrichment is scoped.

---

## Module Boundary Check

- `engine.py` imports only stdlib (`csv`, `datetime`, `pathlib`) + own `pcap_parser` — ✓
- `pcap_parser.py` imports only stdlib (`struct`, `pathlib`) — ✓
- `api/enrichment.py` imports from `session_navigation` (allowed), `enrichment/engine` (own module), `executions` (own API util) — ✓
- No algorithm modules imported from page/UI code — ✓

---

## Approved. Proceed to Re-ID sprint.

---

# QA Review — Re-ID Backend + Frontend (Phase 5)

**Reviewer:** [QA] Claude  
**Date:** 2026-05-12  
**Codex result:** `.ai/codex_result.md`  
**Verdict:** **APPROVED WITH FIX** — one Low bug patched by Claude directly; two known TBD placeholders documented; no blockers

---

## Test Summary

| Check | Result |
|---|---|
| `cd backend && python -m pytest --tb=short -q` | **70 passed, 1 warning** |
| `cd frontend && npm run build` | **✓ zero TS/Vite errors** (per Codex) |
| Playwright smoke | **22 passed, 11 skipped** (per Codex) |
| Static MAC bypass | PASS — `_is_static_mac` correctly checks locally-administered bit |
| Dynamic unit grouping | PASS — observation units keyed by src_mac |
| Greedy conflict resolution | PASS — sorted by score desc, predecessors/successors tracked |
| Union-find clustering | PASS — correct chain merging with path compression |
| REID artifact uppercase suffix | PASS — `_REID.csv` |

---

## Spec Compliance

| Criterion | Result |
|---|---|
| Step 1: Static MACs bypass dynamic pipeline | PASS |
| Step 1: `cluster_type = "static"` for static | PASS |
| Step 2: Observation unit per dynamic `src_mac` | PASS |
| Step 3: Candidate pairs by time proximity | PASS |
| Step 4: All 8 Wi-Fi feature families computed | PASS |
| Step 4: BLE stubs with warning | PASS |
| Step 5: Normalized weighted score | PASS |
| Step 6: Threshold filter | PASS |
| Step 7: Greedy best-valid-match resolution | PASS |
| Step 8: Union-find dynamic clusters | PASS |
| Step 9: Every row gets `cluster_id` + `cluster_type` | PASS (after Bug 1 fix) |
| Step 10: `_REID.csv` uppercase suffix | PASS |
| All REID-XX parameters as TODO constants | PASS — all `1.0` with TODO markers |
| `POST /sessions/{id}/reid/run` → 404/400/422 | PASS |
| Background task stores `active_reid_artifact` | PASS |
| Frontend: enriched artifact dropdown | PASS |
| Frontend: existing REID artifact activatable | PASS |
| Frontend: polling mirrors enrichment pattern | PASS |
| Frontend: quality panel shows 4 metrics | PASS |

---

## Bug Found and Fixed

### Bug 1 — Heartbeat rows grouped as dynamic cluster (FIXED by Claude)

**Severity:** Low  
**Component:** `backend/app/modules/reid/engine.py` — `_build_dynamic_units`

Rows with `frame_type = "heartbeat"` have no `src_mac` (empty string). These were being grouped into one observation unit keyed by `""` and assigned a dynamic integer `cluster_id`. Heartbeat rows carry no device identity and should not enter the MAC association pipeline.

**Fix applied:** In `_build_dynamic_units`, rows with empty `src_mac` are immediately assigned `("", "static")` and skipped from unit grouping. They appear in the REID CSV with `cluster_id = ""` and `cluster_type = "static"` — unambiguous for downstream filtering.

---

## Known TBD Risks (No Fix Required — Phase 5 Scope)

### Risk 1 — Dynamic re-association unreachable with placeholder values

`_REID_01_ASSOCIATION_THRESHOLD = 1.0` requires a perfect normalized score. For real rotated MACs, vendor OUI always differs (`_vendor_score = 0.0`) → max achievable score = 7/8 = 0.875 < 1.0. Result: **all dynamic MACs become singletons in real data**. The `test_reid_engine_dynamic_association` test passes only because both test MACs share the `02:11:22` OUI prefix, making vendor score 1.0.

This is expected TBD behavior. When legacy defaults are extracted (REID-01, REID-09), the threshold and vendor weight will be calibrated such that cross-OUI pairs can link. No action until legacy parameter extraction.

### Risk 2 — 1ms time window eliminates all candidates in real data

`_REID_WIFI_02_MAX_ROTATION_TIME_WINDOW_MS = 1.0` means only observation units whose last/first timestamps differ by ≤1ms are candidates. Real scan data has second-resolution timestamps; MAC rotations happen over seconds. Result: `_generate_candidates` returns empty list for all real scans. Same TBD status as Risk 1.

---

## Module Boundary Check

- `reid/engine.py` imports: `csv`, `datetime`, `math`, `pathlib` (all stdlib) — ✓ no forbidden deps
- `api/reid.py` imports from `session_navigation` (allowed), `reid/engine` (own module), `executions` (own API util) — ✓
- No algorithm modules imported from page/UI code — ✓

---

## Approved. Proceed to Localization sprint.

---

# QA Review — Localization Backend + Frontend (Phase 6)

**Reviewer:** [QA] Claude  
**Date:** 2026-05-12  
**Codex result:** `.ai/codex_result.md`  
**Verdict:** **APPROVED WITH NOTES** — 78/78 backend tests pass, clean build, clean Playwright smoke. Two Medium UX issues documented for next sprint; no correctness blockers.

---

## Test Summary

| Check | Result |
|---|---|
| `cd backend && python -m pytest --tb=short -q` | **78 passed, 1 warning** |
| `cd frontend && npm run build` | **✓ zero TS/Vite errors** |
| Playwright smoke | **22 passed, 11 skipped (cdp)** |
| Engine: auto bounds expand GPS extrema | PASS — `result["bounds"]["lat_min"] < 32.0` |
| Engine: insufficient samples → ValueError | PASS — `"All clusters failed"` |
| Engine: multiple clusters both succeed | PASS — `total_clusters == 2` |
| API: 404 unknown session | PASS |
| API: 422 no approved calibration | PASS |
| API: 422 non-REID input | PASS |
| API: 400 path traversal | PASS |
| API: 200 returns execution_id | PASS |

---

## Spec Compliance

| Criterion | Result |
|---|---|
| LOC-02 auto bounds expand GPS track by buffer_m | PASS — lat/lon buffer correctly computed using `_meters_per_lon_degree(mean_lat)` |
| LOC-06 grid resolution 5m default, capped at 40,000 cells | PASS — while loop adjusts resolution |
| LOC-07 dynamic sigma alpha = 0.0 (TBD TODO) | PASS |
| LOC-08 confidence cutoff = 0.0 (TBD TODO) | PASS |
| LOC-09/10/11 RANSAC stub with TODO | PASS |
| LOC-12 uncertainty radius captures 68% posterior mass | PASS — walks outward from peak accumulating mass |
| LOC-13 min 3 samples per cluster | PASS — `_LOC_13_MIN_SAMPLES_PER_CLUSTER = 3` |
| All clusters fail → ValueError | PASS |
| One cluster fails, others compute (partial failure) | PASS — confirmed by logic: loop continues past `_failed_cluster` |
| Per-cluster `status: "success"/"failed"` in result | PASS |
| Top-500 grid cells by value | PASS — sorted descending, sliced `[:500]` |
| Primary peak = highest local maximum | PASS |
| Uncertainty regions limited to 3 | PASS — `merged[:3]` |
| API stores `active_localization` + `current_localization_result` in session | PASS |
| 422 on missing/unapproved calibration | PASS — `approved is not True` guard |
| Calibration key compatibility (`calibration` or `active_calibration`) | PASS — dual lookup; `active_calibration` is what approve/fallback endpoints write |
| Frontend: view-only controls do NOT hit API | PASS — all layer/cluster toggles are local state only |
| Frontend: satellite default, OSM toggle | PASS |
| Frontend: maxNativeZoom=18 on satellite (no grey tiles) | PASS |
| Frontend: calibration gate warning shown | PASS |
| Frontend: canRun requires session + REID + approved calibration | PASS |
| Frontend: polling follows same pattern as enrichment/re-id | PASS |
| Frontend: cluster summary table shows all clusters including failed | PASS |

---

## Issues Found

### Issue 1 — MapContainer center doesn't auto-pan after result arrives (Medium)

**Spec reference:** UF-006 (Localization map should show the result area)  
**Component:** `frontend/src/pages/LocalizationPage.tsx:247`

`mapCenter` is computed from result bounds, but `MapContainer.center` in react-leaflet is an **initial-only** prop — it is only applied on the first mount, not on re-renders. After localization completes, the map stays at the hardcoded default `[32.0, 34.8]`. Users must manually pan to find the heatmap/peaks.

**Fix:** Wrap MapContainer with a `key={result ? 'has-result' : 'default'}` to force a remount when results arrive, or use a `FlyToCenter` child component that calls `map.flyTo(center, zoom)` via `useMap()`.

---

### Issue 2 — Map controls sit above MapContainer in DOM — layout height not fill-parent (Medium)

**Component:** `frontend/src/pages/LocalizationPage.tsx:209–318`, `LocalizationPage.css:40–44`

`.localization-right` is `position: relative; overflow: hidden` but has no `display: flex; flex-direction: column`. The `map-controls` div and the `MapContainer` stack as regular block elements. The `.localization-map` CSS says `height: 100%` which tries to be 100% of `.localization-right`'s height — but with controls taking space above, the total content overflows and the map is clipped by `overflow: hidden`. The `min-height: 420px` provides a fallback minimum, but the map never expands to fill remaining space.

Compare: OverviewPage uses `position: absolute` floating overlay for its controls so the map gets full height.

**Fix:** Either make `.localization-right` `display: flex; flex-direction: column` and give the MapContainer `flex: 1`, or use absolute/floating positioning for `.map-controls` (same approach as OverviewPage).

---

### Issue 3 — Grid cap warning message says "200x200" but grid may not be square (Low)

**Component:** `backend/app/modules/localization/engine.py:157`

```python
warnings = [f"Grid capped at 200x200; effective resolution {grid_resolution_m:.2f}m"]
```

The cap is 40,000 total cells, but n_lat and n_lon are computed independently from bounds dimensions. A non-square search area could produce e.g. 320×125 cells and still trigger the cap. The "200x200" label is misleading.

**Fix:** Emit `f"Grid resolution adjusted to fit {n_lat}×{n_lon} cells; effective resolution {grid_resolution_m:.2f}m"` after the loop exits.

---

### Issue 4 — No test for partial cluster failure (Low)

**Spec reference:** SAR key scenario "One cluster fails localization → other clusters still compute"  
**Component:** `backend/tests/unit/test_skeleton.py`

No test exercises the path where one cluster in a REID CSV has ≥3 samples (succeeds) and another has <3 samples (fails). The code is correct — the loop continues past `_failed_cluster` — but the scenario is untested.

---

## Module Boundary Check

- `localization/engine.py` imports: `csv`, `math`, `pathlib` (all stdlib) — ✓ no forbidden deps
- `api/localization.py` imports `_LOC_06_GRID_RESOLUTION_M`, `_LOC_02_SEARCH_AREA_BUFFER_M` from engine (minor style note — these are private constants re-used as API defaults). Not a forbidden import; functionally correct.
- `api/localization.py` imports from `session_navigation` (allowed), `localization/engine` (own module), `executions` (own API util) — ✓
- No algorithm modules imported from page/UI code — ✓

---

## Approved. Issues 1 and 2 to be fixed in the next sprint handoff to Codex.

---

# QA Review — Localization Map Fixes (Phase 6 patch)

**Reviewer:** [QA] Claude  
**Date:** 2026-05-12  
**Codex result:** `.ai/codex_result.md`  
**Verdict:** **APPROVED** — all 4 fixes correctly implemented; 79/79 tests pass; clean build; no regressions.

---

## Test Summary

| Check | Result |
|---|---|
| `cd backend && python -m pytest --tb=short -q` | **79 passed, 1 warning** (up from 78) |
| `cd frontend && npm run build` | **✓ zero TS/Vite errors** |

---

## Fix Verification

### Fix 1 — MapContainer auto-pan ✓

`SetViewOnResult` component added at `LocalizationPage.tsx:325–331`. Imports `useMap` from react-leaflet correctly (line 2). Rendered as `{result && <SetViewOnResult center={mapCenter} zoom={16} />}` at line 248 — inside `<MapContainer>` as required by react-leaflet's context rules. `useEffect` deps: `[center[0], center[1], map, zoom]` — exhaustive and correct. Fires on result arrival, re-fires if center changes (second run), unmounts when `result` is cleared on REID dropdown change. No spurious flyTo on cluster toggle (mapCenter derives from `result.bounds`, not from `visibleClusters`). ✓

### Fix 2 — Map controls layout ✓

`.localization-right .map-controls` now has `position: absolute; top: 10px; right: 10px; z-index: 1000` in CSS (lines 52–66). `.localization-right` retains `position: relative` as the positioning context. `.localization-map` keeps `height: 100%; min-height: 420px` — now works correctly since nothing in normal flow sits above the map. Matches OverviewPage pattern exactly. ✓

### Fix 3 — Grid warning message ✓

Engine now uses a `was_capped` boolean flag (line 149), emits warning after the loop with actual `n_lat`×`n_lon` values: `"Grid resolution adjusted to {n_lat}x{n_lon} cells; effective resolution {grid_resolution_m:.2f}m"`. No longer hardcodes "200x200". ✓

### Fix 4 — Partial failure test ✓

`test_localization_engine_partial_failure` added at line 1149. Asserts `total_clusters==2`, `successful_clusters==1`, `failed_clusters==1`, c1 `status=="success"`, c2 `status=="failed"` with `failure_reason=="insufficient_samples"`. ✓

---

## Approved. Proceed to next sprint.

---

# QA Review — REID Naming Fix + Localization UX (patch sprint)

**Reviewer:** [QA] Claude  
**Date:** 2026-05-12  
**Codex result:** `.ai/codex_result.md` (note: file was NOT updated this sprint — stale Phase 6 content remains. Low issue.)  
**Verdict:** **APPROVED WITH TWO NEW BUGS** — all four acceptance criteria passed; two new issues discovered by the founder in live use.

---

## Acceptance Criteria Check

| Criterion | Result |
|---|---|
| REID engine output `scan_..._enriched.csv` → `scan_..._REID.csv` (no `_enriched` in name) | PASS — `engine.py:79–82` strips `_enriched` suffix |
| New naming test passes | PASS — `test_reid_engine_output_strips_enriched_suffix` asserts correct name AND asserts old name does NOT exist |
| `demo.spec.ts` removes `copyFileSync` workaround | PASS — `REID_ARTIFACT` is now `scan_..._REID.csv` directly, no file copy |
| Map overlay contains only Heatmap / Radii / Peaks / divider / Satellite+Map toggle | PASS — cluster loop removed from `map-controls` |
| Cluster checkboxes are in the left-panel table | PASS — `cluster-table tbody` has swatch + checkbox + 5 columns |
| Show all / Hide all buttons work | PASS — correct state callbacks |
| Color swatches in cluster rows | PASS — `cluster-swatch` div with `CLUSTER_COLORS[index % 6]` |
| Hidden cluster rows are dimmed | PASS — `cluster-row-hidden` class at `opacity: 0.45` |
| Backend tests pass | PASS — 80 passed (1 new naming test added) |
| Frontend build clean | PASS |
| Demo runs end-to-end without file copy | PASS — `1 passed` |

---

## Bug 1 — Map overlay text invisible on dark background (High)

**Severity:** High  
**Component:** `frontend/src/pages/LocalizationPage.css:52–66`, `frontend/src/pages/OverviewPage.css`

The `.map-controls` overlay uses `background: rgba(20, 20, 20, 0.82)` (near-black). The `.map-control-check` labels inherit `color: var(--color-text-muted)` from `OverviewPage.css:170` which resolves to `#5d6b7a` — a medium dark grey-blue. Contrast ratio is approximately **1.9:1** against the black background, far below WCAG AA (4.5:1). Text is effectively invisible.

**Fix:** Add explicit white text to the overlay context:
```css
.localization-right .map-controls,
.overview-right .map-controls {
  color: rgba(255, 255, 255, 0.92);
}
```
Also update `.layer-btn` text within the overlay context.

---

## Bug 2 — Save Session button permanently disabled (Critical product gap)

**Severity:** Critical (product — blocks the user's ability to resume work)  
**Component:** `frontend/src/components/layout/Header.tsx:32`, `backend/app/api/saved_sessions.py`

`Header.tsx` renders the button as `disabled` unconditionally with `title="Available after localization"`. All three `saved_sessions.py` endpoints return `{"status": "not_implemented"}`. The founder cannot save or resume a session — the pipeline result is lost on any browser refresh or server restart.

**No fix in this sprint** — tracked as the next sprint below.

---

# QA Review — Live Demo Script (Phase 6 demo)

**Reviewer:** [QA] Claude  
**Date:** 2026-05-12  
**Codex result:** `.ai/codex_result.md`  
**Verdict:** **APPROVED WITH CRITICAL BUG** — demo ran successfully (1 passed, headed Chromium), but a pipeline-breaking naming collision was exposed by the run. Must be fixed before the real pipeline can work without a workaround.

---

## Demo Results

| Stage | Result |
|---|---|
| Folder | `scan - field test 1 - 19.1` ✓ |
| Calibration CSV | `scan_2026-01-19_11-14-13Z-calic_search1.csv` ✓ |
| Calibration MAC | `2c:59:8a:58:95:c1` selected and approved ✓ |
| Enrichment CSV | `scan_2026-01-19_11-20-58Z-test-circle2.csv` ✓ |
| PCAP match | Found ✓ |
| Enrichment match rate | 0.0% (PCAP matching logic stub — known gap from Phase 4) |
| Re-ID static clusters | 100 |
| Re-ID dynamic clusters | 85 |
| Localization clusters | 185 rows in cluster table ✓ |
| Map auto-pan | Fired on result arrival ✓ |
| Screenshot | `demo_result.png` saved ✓ |

---

## Critical Bug — REID output naming collides with inventory exclusion rule

**Severity:** Critical  
**Spec reference:** Part A R-005 (artifact naming), `classifier.py:4`  
**Component:** `backend/app/modules/reid/engine.py:79`, `backend/app/modules/artifact_management/classifier.py`

**Root cause:** The REID engine builds its output filename as:
```python
output_path = enriched_csv_path.parent / f"{enriched_csv_path.stem}_REID.csv"
```
When fed a `*_enriched.csv` input (e.g. `scan_..._enriched.csv`), the stem is `scan_..._enriched`, producing `scan_..._enriched_REID.csv`.

The artifact classifier has:
```python
_EXCLUDE_SUBSTRINGS = ("_reid_reid", "_enriched_reid")
```
`scan_..._enriched_REID.csv` → lowercased → contains `_enriched_reid` → **excluded from inventory**.

The demo masked this by `copyFileSync`-ing the artifact to `*_demo_reid.csv`. In real field use, the REID output is invisible to the Localization page — the dropdown is empty.

**Fix:** Strip the `_enriched` / `_ENRICHED` suffix from the stem in the REID engine before appending `_REID.csv`:
```python
stem = enriched_csv_path.stem
if stem.lower().endswith('_enriched'):
    stem = stem[:-len('_enriched')]
output_path = enriched_csv_path.parent / f"{stem}_REID.csv"
```
This produces `scan_..._REID.csv` — clean, canonical, classifier-accepted.

---

## Demo Script Quality

| Check | Result |
|---|---|
| `playwright.demo.config.ts` — headed, slowMo 900, 1 worker | ✓ |
| `demo.spec.ts` — discovers files, waits for backend completion | ✓ |
| Pauses between steps for visibility | ✓ (1200ms standard, 4000ms at end) |
| Console + pageerror logging | ✓ |
| Screenshot captured | ✓ `demo_result.png` |
| `copyFileSync` workaround | Acceptable for demo only — see Critical Bug above |

---

## UX Note (agent dispatched)

A sub-agent has been spawned to review the localization map controls overlay (checkboxes for 185 clusters). Findings will be reported separately and fed into the next sprint handoff.
