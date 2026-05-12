# Sprint 01 — Task List

> **Goal:** Running skeleton — backend + frontend + canonical models + session + folder discovery
> **Date:** 2026-05-11

---

## TASK-01 — Create full folder structure
**Role:** DEV:backend
**Size:** Small
**Status:** [ ] Not started

Create all directories per spec (Part C Section 5):
```
backend/app/api/
backend/app/modules/ (all 14 module folders, each with __init__.py + README.md)
backend/app/models/
backend/app/storage/
backend/tests/unit/
backend/tests/integration/
frontend/src/pages/
frontend/src/components/layout/
frontend/src/components/maps/
frontend/src/components/charts/
frontend/src/components/tables/
frontend/src/components/forms/
frontend/src/components/filters/
frontend/src/components/status/
frontend/src/components/artifacts/
frontend/src/features/
frontend/src/api/
frontend/src/state/
frontend/src/types/
tests/e2e/
```

---

## TASK-02 — Canonical models
**Role:** DEV:backend
**Size:** Small
**Status:** [ ] Not started

Implement in `backend/app/models/canonical_models.py`:
- `ScanRecord`
- `EnrichedScanRecord`
- `ReIDRecord`
- `SessionCalibration`
- `SavedSessionState`

Use Pydantic v2. All required fields must be non-optional. TBD fields get `# TODO: TBD per spec Part B`.

---

## TASK-03 — Backend app factory
**Role:** DEV:backend
**Size:** Small
**Status:** [ ] Not started

`backend/app/main.py`:
- FastAPI app with CORS for localhost:5173
- Include all routers
- Health check: `GET /health` → `{"status": "ok"}`
- `requirements.txt`: fastapi, uvicorn, pydantic, pytest, httpx

---

## TASK-04 — Stub all API route files
**Role:** DEV:backend
**Size:** Medium
**Status:** [ ] Not started

Create stub routers in `backend/app/api/` — one per domain.
Each stub returns `{"status": "not_implemented", "endpoint": "<path>"}` with HTTP 200.
Endpoints to stub (from Part B Section 6):
- sessions.py: GET /api/scan-folders, POST /api/sessions, PATCH .../mode, GET .../state
- inventory.py: GET .../inventory, POST .../artifacts/activate
- overview.py: POST .../overview
- calibration.py: POST .../calibration/candidates, /run, /approve, /fallback
- enrichment.py: POST .../enrichment/run
- reid.py: POST .../reid/run
- localization.py: POST .../localization/run
- result_analysis.py: GET/POST .../result-analysis and sub-routes
- saved_sessions.py: POST .../save, GET /api/saved-sessions, POST .../resume
- executions.py: GET /api/executions/{execution_id}

---

## TASK-05 — Implement folder discovery + mode detection
**Role:** DEV:backend
**Size:** Small
**Status:** [ ] Not started

`GET /api/scan-folders`:
- Reads `DATA/` path from env var `DATA_DIR`
- Returns list of subfolders with: `folder_id`, `folder_name`, `detected_mode` (wifi/ble/unknown)
- Mode detection: look for "wifi" or "ble" in folder name (case-insensitive); default to "unknown"
- If DATA/ doesn't exist or is empty, return empty list with a warning

---

## TASK-06 — Implement session creation + state
**Role:** DEV:backend
**Size:** Medium
**Status:** [ ] Not started

`POST /api/sessions`:
- Body: `{ "folder_id": "...", "mode": "wifi|ble|null" }`
- Creates session, detects mode if not provided, stores in memory (dict for now, db later)
- Returns: `{ "session_id": "...", "folder_id": "...", "mode": "...", "created_at": "..." }`

`PATCH /api/sessions/{session_id}/mode`:
- Body: `{ "mode": "wifi|ble" }`
- Overrides detected mode

`GET /api/sessions/{session_id}/state`:
- Returns full current session state (active folder, mode, active artifacts, current page, warnings)

---

## TASK-07 — Artifact resolver
**Role:** DEV:backend
**Size:** Small
**Status:** [ ] Not started

`GET /api/sessions/{session_id}/inventory`:
- Scans active session folder
- Returns: all CSV files, all PCAP files, all ENRICHED artifacts (`*_ENRICHED.csv`), all REID artifacts (`*_REID.csv`)
- For each ENRICHED/REID artifact: includes `stage_jump_suggestion` ("can activate for re-id" / "can activate for localization")

`POST /api/sessions/{session_id}/artifacts/activate`:
- Body: `{ "artifact_path": "...", "artifact_type": "enriched|reid" }`
- Sets artifact as active in session state immediately

---

## TASK-08 — React scaffold + page stubs
**Role:** DEV:frontend
**Size:** Small
**Status:** [ ] Not started

- Vite + React + TypeScript setup
- React Router with 6 routes:
  - `/` → SessionStartPage
  - `/overview` → OverviewPage
  - `/calibration` → CalibrationPage
  - `/enrichment` → ReIdEnrichmentPage
  - `/localization` → LocalizationPage
  - `/analysis` → ResultAnalysisPage
- Each page: initial stub with page name + phase label until the real page is implemented
- `npm run dev` works on port 5173

---

## TASK-09 — App shell: header + left nav
**Role:** DEV:frontend
**Size:** Medium
**Status:** [ ] Not started

Persistent layout wrapping all pages:

**Header** (top): active session name | active folder | active mode | warnings badge | Save Session button
**Left nav**: list of 6 stages with icons — highlight current stage, show ✓ for completed, show ⚠ for warnings
**Main area**: page content

Header and nav read from session state store. Before session creation, show clear empty-state values.

---

## TASK-10 — Session Start page (functional)
**Role:** DEV:frontend
**Size:** Medium
**Status:** [ ] Not started

1. On mount: `GET /api/scan-folders` → populate folder dropdown
2. User selects folder: call `POST /api/sessions` → store `session_id` in state
3. Show detected mode with manual override dropdown (wifi / ble)
4. If mode overridden: call `PATCH /api/sessions/{id}/mode`
5. After session created: auto-navigate to `/overview`
6. Empty state: "No folders found in DATA/" with explanation

---

## TASK-11 — Module READMEs (all 14)
**Role:** CTO
**Size:** Medium
**Status:** [ ] Not started

Each `backend/app/modules/<name>/README.md` must contain:
- Module name and ID (MOD-00x)
- One-paragraph responsibility summary (from Part A Section 8)
- Owned state (if any)
- Allowed dependencies
- Forbidden dependencies
- Key public functions (stubs — to be implemented)

---

## TASK-12 — Tests for skeleton
**Role:** QA
**Size:** Medium
**Status:** [ ] Not started

Backend unit tests:
- `test_scan_folders`: DATA/ listing returns correct structure
- `test_mode_detection`: wifi/ble/unknown detected correctly from folder names
- `test_session_creation`: POST /api/sessions returns valid session_id
- `test_session_state`: GET state returns correct fields after creation
- `test_artifact_resolver`: ENRICHED and REID files classified correctly
- `test_canonical_models`: all 5 models instantiate with required fields; reject missing required fields

All tests in `backend/tests/unit/test_skeleton.py`.
