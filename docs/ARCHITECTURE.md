# Technical Architecture

## 1. Purpose

SAR Ground Station is a Windows-first browser application with a Python/FastAPI backend and a TypeScript/React frontend.

The system processes drone-collected Wi-Fi RF scan data first, with BLE support preserved in the architecture for later phases. The first milestone is an operational SAR workflow through Wi-Fi Enrichment.

Detailed behavior is defined in:

- `docs/Part A.md` - core system, user flows, modules, data models, constraints
- `docs/Part B.md` - algorithms, parameters, rerun rules, API contracts
- `docs/Part C.md` - implementation order
- `docs/PRD.md` - product requirements and milestone scope

## 2. Tech Stack

| Layer | Technology | Why |
|-------|------------|-----|
| Frontend | React + TypeScript + Vite | Fast local development, typed UI, good fit for operational browser workflow |
| Backend | Python + FastAPI | Strong API ergonomics, Pydantic contracts, practical for RF/data-processing algorithms |
| Data validation | Pydantic v2 | Canonical runtime schemas and API validation |
| Runtime storage | Local filesystem | Scan folders, official artifacts, TEMP, and Saved Scans are file-based by spec |
| Tests | Pytest, frontend unit tests, Playwright | Unit/API/E2E coverage across backend, frontend, and workflows |
| Database | None for Phase 0-4 | In-memory/session-file state is enough until persistence requirements demand a DB |
| AI/LLM | Claude/Codex as development tools | Not part of runtime product behavior for the current milestone |
| Hosting | Local Windows development | Demo target is local operational workflow |

## 3. System Architecture

```text
React Browser App
  |
  | HTTP JSON API
  v
FastAPI Backend
  |
  +-- API routers
  +-- Session/workflow services
  +-- Canonical models
  +-- Domain modules
  |     +-- dataset_discovery
  |     +-- artifact_management
  |     +-- enrichment
  |     +-- reid
  |     +-- localization
  |     +-- ...
  |
  +-- Filesystem storage
        +-- runtime/DATA
        +-- runtime/TEMP
        +-- runtime/Saved Scans
```

## 4. Module Boundaries

Canonical modules are MOD-001 through MOD-014 from `docs/Part A.md`.

Hard rules:

- Page modules do not own algorithmic logic.
- Algorithm engines do not own rendering logic.
- Session state is owned by session/workflow backend modules, not page code.
- Cross-module data uses canonical schemas.
- Official artifacts are explicit first-class files.
- Save/resume does not depend on `TEMP`.
- Air Unit / Airborne code is out of scope.

Forbidden dependencies:

- MOD-001 must not import MOD-007, MOD-008, MOD-009, or MOD-010.
- Algorithm engines must not import frontend/page/UI modules.

## 5. Runtime Storage

Development defaults:

```text
runtime/
  DATA/          # scan folders and official scan artifacts
  TEMP/          # non-persistent working artifacts
  Saved Scans/   # persistent save/resume packages
reference/
  legacy_app/    # read-only reference copy of the legacy app
```

Environment variables:

- `DATA_DIR=runtime/DATA`
- `TEMP_DIR=runtime/TEMP`
- `SAVED_SCANS_DIR=runtime/Saved Scans`
- `LEGACY_APP_DIR=reference/legacy_app`

The data/reference contents are ignored by git.

## 6. Canonical Data Models

Defined in `backend/app/models/canonical_models.py`:

- `ScanRecord`
- `EnrichedScanRecord`
- `ReIDRecord`
- `SessionCalibration`
- `SavedSessionState`

Required fields and invariants come from `docs/Part A.md`.

Do not invent defaults for fields marked `TBD` in `docs/Part B.md`.

## 7. API Surface

API contracts come from `docs/Part B.md`.

Phase 0/1 endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Backend health check |
| GET | `/api/scan-folders` | List scan folders from `DATA_DIR` |
| POST | `/api/sessions` | Create session for folder/mode |
| PATCH | `/api/sessions/{session_id}/mode` | Override mode |
| GET | `/api/sessions/{session_id}/state` | Fetch session state |
| GET | `/api/sessions/{session_id}/inventory` | List CSV, PCAP, ENRICHED, REID files |
| POST | `/api/sessions/{session_id}/artifacts/activate` | Activate official artifact |

Long-running operations use `execution_id` and are polled through:

| Method | Path |
|--------|------|
| GET | `/api/executions/{execution_id}` |

## 8. Frontend Structure

Phase 0/1 frontend pages:

- `SessionStartPage`
- `OverviewPage`
- `CalibrationPage`
- `ReIdEnrichmentPage`
- `LocalizationPage`
- `ResultAnalysisPage`

Shared component folders:

- `layout`
- `maps`
- `charts`
- `tables`
- `forms`
- `filters`
- `status`
- `artifacts`

Frontend source of truth:

- Backend owns active session state.
- Frontend stores local UI state only.
- Execution endpoints are called only for real computations, not view-only controls.

## 9. First Milestone

Milestone: operational Wi-Fi workflow through Enrichment.

Must demonstrate:

1. App starts locally on Windows.
2. User selects a Wi-Fi scan folder from `runtime/DATA`.
3. Session is created and mode is detected or overridden.
4. Inventory lists CSV/PCAP and official artifacts.
5. User selects CSV for enrichment.
6. Backend finds matching PCAP.
7. Enrichment writes an official `*_ENRICHED.csv`.
8. Legacy Wi-Fi enrichment behavior has been reviewed by `[RESEARCHER]` before implementation choices are locked.

## 10. Key Decisions

See `docs/DECISIONS.md` for accepted decisions.

