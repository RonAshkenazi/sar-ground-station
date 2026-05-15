# Codex Result - Air Unit Page + Smart Flight Guidance

Date: 2026-05-14

## Worker A - Backend

Created:
- `backend/app/modules/guidance/__init__.py`
- `backend/app/modules/guidance/config.py`
- `backend/app/modules/guidance/models.py`
- `backend/app/modules/guidance/grid.py`
- `backend/app/modules/guidance/scoring.py`
- `backend/app/modules/guidance/state.py`
- `backend/app/modules/guidance/recommendation.py`
- `backend/app/modules/guidance/engine.py`
- `backend/app/modules/guidance/logger.py`
- `backend/app/api/guidance.py`
- `backend/app/api/airunit.py`

Modified:
- `backend/tests/unit/test_skeleton.py`

Implemented:
- Smart guidance grid, scoring, state ingestion, recommendation engine, and history logger.
- Air Unit relay backend with Pi websocket, frontend websocket, command forwarding, status, file listing, and file download proxy.
- Guidance API endpoints:
  - `POST /api/guidance/init`
  - `POST /api/guidance/reset`
  - `GET /api/guidance/recommendation`
  - `GET /api/guidance/grid`
  - `POST /api/guidance/update`
- 11 guidance unit tests.

Worker verification:
- `python -m py_compile` passed for all new backend files.
- `python -m pytest tests/unit/test_skeleton.py -k guidance -q`: `11 passed`
- `python -m pytest tests/unit/ -q`: `121 passed`

Deviation:
- Worker implemented `/api/guidance/update` for packet ingestion. The final handoff text also mentions five guidance endpoints; no separate `/status` endpoint was added.

## Worker B - Frontend

Created:
- `frontend/src/api/airunit.ts`
- `frontend/src/pages/AirUnitPage.tsx`
- `frontend/src/pages/AirUnitPage.css`

Modified:
- `frontend/src/App.tsx`
- `frontend/src/pages/SessionStartPage.tsx`
- `frontend/src/pages/SessionStartPage.css`

Implemented:
- `/airunit` route.
- Air Unit API wrappers and types.
- Frontend websocket relay client with reconnect backoff.
- Pi connection bar and WiFi/BLE command buttons.
- Live guidance Leaflet map with boundary drawing, guidance grid overlay, drone marker, target marker, and target polyline.
- Guidance polling while running.
- Guidance status panel.
- Pi file table with download links.
- Last-200-lines log panel with autoscroll.
- Session Start “Live Mission” launcher.

Worker verification:
- `cd frontend && npm.cmd run build`: passed.

Deviation:
- Live Mission launcher is reachable even when no scan folders are available.

## Supervisor Integration

Modified:
- `backend/app/main.py`
  - Imported `guidance` and `airunit`.
  - Included both routers under `/api`.

Final verification:
- `cd backend && python -m pytest tests/unit/ -x -q`
- Result: `121 passed, 2 warnings`
- Warnings:
  - Existing pytest config warning for unknown `asyncio_mode`.
  - Pydantic V2 deprecation warning for class-based config in the new guidance update request model.

- `cd frontend && npm.cmd run build`
- Result: passed (`tsc && vite build`, 100 modules transformed).

Frontend build output tail:
```text
vite v5.4.21 building for production...
transforming...
✓ 100 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.40 kB │ gzip:   0.28 kB
dist/assets/index-Cf4MRVM_.css   42.62 kB │ gzip:  11.66 kB
dist/assets/index-DS66n7PR.js   394.90 kB │ gzip: 117.78 kB
✓ built in 1.34s
```

## Known Issues / Follow-Up

- The Air Unit page expects a Pi websocket client to connect to `/api/airunit/ws`; without a Pi, file listing and command forwarding report not connected.
- `backend/app/api/guidance.py` uses class-based Pydantic config for an open update model, which raises a deprecation warning under Pydantic v2. It does not fail tests.

---

# Codex Result - Spatial Entropy Propagation + Emulator

Date: 2026-05-15

## Worker A - Backend

Modified:
- `backend/app/modules/guidance/config.py`
- `backend/app/modules/guidance/models.py`
- `backend/app/modules/guidance/scoring.py`
- `backend/app/modules/guidance/state.py`
- `backend/app/modules/guidance/engine.py`
- `backend/app/modules/guidance/recommendation.py`
- `backend/tests/unit/test_skeleton.py`

Implemented:
- Spatial evidence propagation constants.
- Spatial coverage/dwell propagation constants.
- Evidence freshness decay constants.
- Spatial entropy and certainty fields on grid cells.
- `compute_evidence_freshness()` and `compute_spatial_entropy()`.
- Evidence propagation to 8-connected neighbors with orthogonal vs diagonal alpha.
- Dwell propagation to 8-connected neighbors.
- Grid API fields:
  - `spatial_entropy`
  - `spatial_certainty`
  - `evidence_freshness`
  - `display_score`
- Freshness/display refresh during grid snapshots and tick updates.
- Regression tests for evidence propagation, dwell propagation, entropy, and grid API fields.

Deviation:
- `backend/app/modules/guidance/recommendation.py` was touched even though the handoff marked it Phase 2. This was necessary because propagated neighbor evidence made echo cells eligible targets. Candidate selection now filters evidence cells with `E_TARGET_MIN` and a relative max-evidence threshold so weak echoes do not steal the target from the direct evidence cell.

## Worker B - Frontend

Created:
- `frontend/src/pages/EmulatorPage.tsx`
- `frontend/src/pages/EmulatorPage.css`

Modified:
- `frontend/src/api/airunit.ts`
- `frontend/src/App.tsx`

Implemented:
- `/emulator` route.
- Interactive Leaflet emulator page.
- Click-to-move drone marker.
- Draw-boundary workflow.
- Init/reset guidance controls.
- POSE packet timer with selectable rate.
- EVIDENCE packet timer with interval control.
- RSSI, frame count, and strong-ratio controls.
- Grid overlay colored by `display_score ?? evidence_score`.
- Cell tooltips showing E / fresh / U / H / C / J.
- Target line from drone to recommendation.
- Live sidebar stats and current drone-cell values.

## Supervisor Integration

Verified:
- `POST /api/guidance/update` exists and calls `get_engine().ingest(...)`.

Final verification:
- `python -m pytest backend/tests/unit/ -q`
- Result: `142 passed, 1 warning`
- Warning:
  - Pydantic V2 deprecation warning for class-based config in the guidance update request model.

- `cd frontend && npm.cmd run build`
- Result: passed (`tsc && vite build`, 102 modules transformed).

Frontend build output:
```text
dist/index.html                 0.40 kB | gzip:   0.27 kB
dist/assets/index-DLFl03y4.css 46.88 kB | gzip:  12.47 kB
dist/assets/index-Ba6DpkSl.js  406.29 kB | gzip: 120.55 kB
```

## Known Issues / Follow-Up

- Entropy is implemented for Phase 1 display/diagnostics. Full entropy-aware final scoring remains a later decision.
- `AirUnitPage.tsx` was intentionally not modified for this handoff.
