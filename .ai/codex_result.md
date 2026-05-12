# Codex Result - Localization Backend + Frontend Phase 6

## MOD-013 Follow-Up - Save Session Wiring

Completed the current `.ai/handoffs/current.md` follow-up.

- `LocalizationPage.tsx` now pre-fills `result` from `current_localization_result` when a resumed session loads, so the map and cluster table appear without re-running Localization.
- `LocalizationPage.tsx` already refreshes `SessionContext` after localization succeeds; verified this remains wired.
- `Header.tsx` now shows `Saving...` during save and `Saved ✓` for a short confirmation after success.
- `tests/e2e/demo.spec.ts` now verifies Save Session, saved-session listing, Resume, restored cluster table, and saves `demo_result_v3.png`.

Verification:
- `cd frontend && npm.cmd run build` passed.
- Headed Playwright demo passed: `1 passed`.
- `demo_result_v3.png` saved.
- Saved session API on the clean backend returned the new save for `scan - field test 1 - 19.1`.

Runtime note: stale backend listeners remained on ports `8000` and `8001`, so the final verification backend ran on `127.0.0.1:8002` and the frontend ran on `127.0.0.1:5173` with `VITE_API_URL=http://127.0.0.1:8002`.

## MOD-013 Save Session + Visual QA

Completed the current `.ai/handoffs/current.md` patch.

- Fixed map-control overlay contrast on Localization and Overview: overlay text and inactive layer buttons now use light text on the dark background.
- Implemented `POST /api/sessions/{session_id}/save`, `GET /api/saved-sessions`, and `POST /api/saved-sessions/{saved_id}/resume`.
- Save packages are written under `runtime/Saved Scans/{folder_id}/{saved_id}/` with `session_meta.json`, `calibration.json`, `localization.json`, and a copied REID CSV via `shutil.copy2`.
- Resume creates a new in-memory session, restores mode, approved calibration, localization result, and copies the saved REID CSV back into `DATA/` if needed.
- Header Save Session is enabled after localization state exists and shows `Saving...` while saving.
- Session Start now lists saved sessions and can resume directly to Localization.
- Demo now selects uppercase `_ENRICHED.csv` and `_REID.csv` artifacts from the current pipeline.

Visual QA sub-agent result:
- Headed demo passed.
- Screenshot saved as `demo_result_v2.png`.
- Overlay text is clearly readable with acceptable contrast.
- Cluster rows and swatches are visible.
- Save Session button appears enabled.

Known UI follow-up from the UI/UX reviewer: the 185-row cluster table is readable, but still not ergonomic for selective work because the left panel is narrow and the table can require horizontal scrolling. Search/filter/count controls should be handled in a future UX pass.

## Phase 6 Patch - Localization Map Fixes

Completed the targeted follow-up from `.ai/handoffs/current.md`.

- Localization map now calls `map.flyTo(...)` after a result arrives, so the founder lands on the result area instead of the default map center.
- Localization map controls are now an absolute overlay scoped to `.localization-right`, so they no longer consume layout height or push the map down.
- Grid capping warnings now report the actual resolved grid shape, for example `180x220 cells`, instead of the old hardcoded `200x200` wording.
- Added a regression test for partial cluster failure: one cluster can localize successfully while another fails with `insufficient_samples`.

## Live Demo Run - Full Pipeline

Created and ran the headed slow-motion Playwright demo requested in `.ai/handoffs/current.md`.

- Added `playwright.demo.config.ts` with headed Chromium, `slowMo: 900`, viewport `1400x900`, and one worker.
- Added `tests/e2e/demo.spec.ts` to drive Session Start, Calibration, Enrichment, Re-ID, and Localization.
- Demo folder: `scan - field test 1 - 19.1`.
- Calibration CSV: `scan_2026-01-19_11-14-13Z-calic_search1.csv`.
- Calibration MAC: `2c:59:8a:58:95:c1`.
- Enrichment CSV: `scan_2026-01-19_11-20-58Z-test-circle2.csv`.
- Enrichment PCAP match was found.
- Enrichment match rate shown in the demo: `0.0%`.
- Re-ID quality shown in the demo: `100` static clusters, `85` dynamic clusters.
- Localization completed with `185` cluster rows visible; the map result loaded after the run.
- Final screenshot saved as `demo_result.png`.

Runtime note: port `8000` had stale stub backend listeners on this machine, so the working demo backend was started on `127.0.0.1:8001` and the frontend was started with `VITE_API_URL=http://127.0.0.1:8001`. The frontend is available at `http://127.0.0.1:5173`.

Artifact note: this was fixed in the follow-up patch. Re-ID now strips `_enriched` before appending `_REID`, and the demo no longer copies a workaround file.

## Founder User Flow

1. Open the app and start at Session Start. Pick the scan folder from `DATA/`. The app creates an in-memory session and shows what artifacts already exist in that folder.
2. Go to Enrichment. Select the raw CSV and run enrichment. While it runs, the page shows progress through polling. When it finishes, an `*_ENRICHED.csv` artifact is written back into the scan folder.
3. Go to Re-ID. Select the enriched artifact and run Re-ID. When it finishes, a `*_REID.csv` artifact is written back into the same scan folder.
4. Go to Calibration. Review or run calibration and approve the calibration values. Localization stays blocked until calibration is approved, because the localization algorithm needs those radio model parameters.
5. Go to Localization. Select the REID artifact from the dropdown and click Run Localization. The page shows that localization is running, polls the backend execution, then displays the result when the backend reports success.

What Run Localization does: it sends the selected REID file and approved calibration to the backend, then polls the execution status until success or failure. On success, the map automatically flies to the computed result area. The map can show heatmap cells for likely transmitter locations, uncertainty circles around likely regions, and peak markers for the best candidate point per cluster. The cluster table lists each cluster, its type, status, sample count, and number of candidate peaks. Failed clusters remain visible in the table with their status, while successful clusters provide map layers.

Session persistence - updated: the active session still lives in backend memory during normal use, but after Localization the founder can now click Save Session. The saved package is written to `Saved Scans/` and can be resumed from Session Start.

Current workaround: the durable artifacts are the files written to disk. `*_ENRICHED.csv` and `*_REID.csv` are permanently saved in the scan folder under `DATA/`. After a restart, go to Session Start, pick the same folder, and the inventory should detect those artifacts and offer activation for Localization. That lets the founder skip re-running Enrichment and Re-ID. Calibration still needs to be re-approved, or a fallback preset must be used.

## Goal Completed

Implemented the Localization vertical slice requested in `.ai/handoffs/current.md`.

- Added localization engine with validation, bounds/grid construction, per-cluster posterior scoring, peak detection, uncertainty regions, and top-500 heatmap cells.
- Replaced the Localization API stub with a real background-task endpoint.
- Added a working Localization page with REID artifact selection, calibration gate, execution polling, cluster summary, and map layers.
- Added backend localization engine/API tests.

## Files Changed

- `backend/app/modules/localization/__init__.py` - new module marker.
- `backend/app/modules/localization/engine.py` - new localization algorithm.
- `backend/app/api/localization.py` - real `POST /api/sessions/{session_id}/localization/run` endpoint.
- `backend/tests/unit/test_skeleton.py` - added localization tests and removed localization from stub expectations.
- `frontend/src/api/sessions.ts` - added localization result types and `runLocalization`.
- `frontend/src/pages/LocalizationPage.tsx` - replaced stub with full map page.
- `frontend/src/pages/LocalizationPage.css` - localization page layout and table styles.

## Backend Behavior

- `run_localization(...)` returns the full Step 12 result schema.
- Auto bounds expand GPS extrema by the requested buffer.
- Grid caps at 40,000 cells and emits a warning if resolution is adjusted.
- Clusters with fewer than 3 usable samples fail with `failure_reason="insufficient_samples"`.
- If all clusters fail, the engine raises `ValueError`.
- API returns 404 for unknown session, 400 for traversal, 422 for non-REID input or missing approved calibration.
- API supports `manual_rectangle` request fields, though the frontend only exposes auto bounds mode.
- Successful API run stores `active_localization` and `current_localization_result` in session state.

## Frontend Behavior

- Localization page loads inventory and session state on session change.
- REID dropdown is populated from inventory.
- Calibration warning appears when no approved calibration exists.
- Run button is disabled without session + REID artifact + approved calibration.
- Polling updates result on success and error banner on failure.
- Map defaults to satellite with OSM toggle.
- Heatmap cells, uncertainty radii, and primary peaks are view-only toggles.
- Per-cluster visibility checkboxes hide/show map layers without API calls.

## Tests Run

- `npx.cmd playwright test tests/e2e/demo.spec.ts --config=playwright.demo.config.ts --reporter=list`
  - Result: `1 passed`.
  - Browser: headed Chromium with slow motion.

- `cd backend && python -m pytest --tb=short -q`
  - Result: `79 passed`, `1 warning`.
  - Existing warning remains: unknown pytest config option `asyncio_mode`.

- `cd frontend && npm.cmd run build`
  - Result: passed with zero TypeScript/Vite errors.

Previous Phase 6 full-run checks:

- `cd backend && python -m pytest --tb=short -q`
  - Result: `78 passed`, `1 warning`.
  - Existing warning remains: unknown pytest config option `asyncio_mode`.

- `cd frontend && npm.cmd run build`
  - Result: passed with zero TypeScript/Vite errors.

- `npx.cmd playwright test tests/e2e/smoke.spec.ts --reporter=list`
  - Result: `22 passed`, `11 skipped`, `0 failed`.

## Notes

- LOC-06/07/08 constants are present with TODO markers and the specified placeholders.
- LOC-09/10/11 RANSAC pre-cleaning is stubbed with a TODO and always skipped.
- No calibration, enrichment, Re-ID engine, routing, or Result Analysis changes were made.
- API accepts both legacy `active_calibration` session state and the handoff's `calibration` key for approved calibration lookup.

## Review Request For Claude

Ask Claude:

`/project:qa Review .ai/codex_result.md and the changed files.`
