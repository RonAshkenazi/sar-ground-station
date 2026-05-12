# Sprint 01 — Repo Skeleton & Project Foundation

| Field | Value |
|-------|-------|
| **Sprint** | 01 |
| **Goal** | Running backend + frontend skeleton with session creation, folder discovery, and canonical models — no algorithms yet |
| **Status** | In Progress |
| **Start** | 2026-05-11 |
| **End** | 2026-05-11 |
| **Phase** | Phase 0 + Phase 1 (partial) per `docs/Part C.md` |

---

## Why This Goal

A skeleton that runs gives every role — backend, frontend, algo, UX — a place to work in parallel from tomorrow. It also validates the module structure before any algorithm code is written.

---

## Scope

### Must ship today
1. **Backend skeleton** — FastAPI app runs on port 8000, all API routes exist as stubs returning placeholder JSON
2. **Canonical models** — `ScanRecord`, `EnrichedScanRecord`, `ReIDRecord`, `SessionCalibration`, `SavedSessionState` defined in `backend/app/models/canonical_models.py`
3. **Session creation** — `POST /api/sessions` creates a session from a selected folder; `GET /api/sessions/{id}/state` returns current state
4. **Folder discovery** — `GET /api/scan-folders` lists subfolders under `DATA/`; detects Wi-Fi vs BLE mode from folder name
5. **Artifact resolver** — finds existing `*_ENRICHED.csv` and `*_REID.csv` in a selected folder; classifies them as official artifacts
6. **Frontend skeleton** — React app runs on port 5173, all 6 pages exist as stubs with correct routes
7. **App shell** — persistent header (session name, folder, mode, warnings badge), left nav with 6 stages
8. **Session Start page** — folder dropdown populated from backend, mode display, manual override

### Stretch (only if core is solid)
9. **Overview page stub** — CSV dropdown populated, empty state shown, no charts yet
10. **E2E smoke test** — Playwright test that loads the app, selects a folder, verifies Overview opens

---

## Exit Criteria

- [ ] `cd backend && uvicorn app.main:app --reload` starts without errors
- [ ] `cd frontend && npm run dev` starts without errors
- [ ] `GET /api/scan-folders` returns real folder list from `DATA/`
- [ ] `POST /api/sessions` creates a session and returns `session_id`
- [ ] `GET /api/sessions/{id}/state` returns current session state
- [ ] All 6 pages render without crashes (stub content is fine)
- [ ] App shell header shows active folder and mode after session creation
- [ ] All 14 module folders exist under `backend/app/modules/` with a `README.md`
- [ ] No forbidden imports (MOD-001 must not import algorithm engines)
- [ ] `cd backend && pytest` runs (even if only skeleton tests pass)

---

## Task Breakdown

| # | Task | Role | Size |
|---|------|------|------|
| 1 | Create full folder structure (backend + frontend + modules) | DEV:backend | S |
| 2 | Define all 5 canonical models in `canonical_models.py` | DEV:backend | S |
| 3 | Backend main.py + app factory + CORS config | DEV:backend | S |
| 4 | Stub all 10 API route files with correct endpoint signatures | DEV:backend | M |
| 5 | Implement `GET /api/scan-folders` (real DATA/ discovery + mode detection) | DEV:backend | S |
| 6 | Implement `POST /api/sessions` + `GET /api/sessions/{id}/state` | DEV:backend | M |
| 7 | Implement artifact resolver (find ENRICHED/REID in folder) | DEV:backend | S |
| 8 | React app scaffold + router + all 6 page stubs | DEV:frontend | S |
| 9 | App shell: persistent header + left nav component | DEV:frontend | M |
| 10 | Session Start page: folder dropdown + mode display + session creation | DEV:frontend | M |
| 11 | Write module READMEs for all 14 modules | CTO | M |
| 12 | Unit tests for folder discovery + session creation + artifact resolver | QA | M |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| DATA/ path not configured correctly on this machine | Medium | High | Set path in `.env`, document in README |
| Mode detection logic ambiguous (folder naming convention unclear) | Medium | Medium | Implement manual override first, refine detection later |
| Frontend API calls fail due to CORS | Low | High | Configure CORS in FastAPI from the start |
| Module structure diverges from spec before algorithms are written | Low | High | CTO reviews structure before any algorithm work begins |

---

## Artifacts

- Tasks: `todo/sprint_01_todo.md`
- Report: `reports/sprint_01_report.md`
- Review: `reviews/sprint_01_review.md`
