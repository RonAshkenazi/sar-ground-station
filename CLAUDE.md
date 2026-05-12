# SAR Ground Station — Claude Code Project Context

> **Purpose:** Ground Station desktop application for SAR (Search and Rescue) RF scanning and device localization.
> **Stack:** Python backend (FastAPI) + TypeScript/React frontend. Strict Frontend + Backend separation.
> **Spec source of truth:** `docs/Part A.md` (architecture) and `docs/Part B.md` (algorithms, parameters, APIs).
> **Build order:** `docs/Part C.md` (phases 0–9). **Current phase: Phase 0 — Repo & Skeleton.**

---

## What This System Does

Processes drone-collected RF scan data (Wi-Fi and BLE) through a pipeline:

```
Scan Folder (DATA/) → Overview → Calibration → Enrichment (CSV+PCAP) → Re-ID → Localization → Map
```

Two user types:
- **Operational** — SAR field teams. Run the pipeline, inspect map results.
- **Research** — Dev/tuning team. Result Analysis, ground-truth comparison, parameter tuning.

---

## Commands

```bash
# Backend
cd backend && uvicorn app.main:app --reload     # Dev server (port 8000)
cd backend && pytest                            # All backend tests
cd backend && pytest tests/unit/               # Unit tests only
cd backend && pytest tests/integration/        # Integration tests only

# Frontend
cd frontend && npm run dev                     # Dev server (port 5173)
cd frontend && npm run build                   # Production build
cd frontend && npm test                        # Frontend unit tests

# E2E
npx playwright test                            # All E2E tests
npx playwright test --ui                       # Interactive mode
npx playwright test --debug                    # Debug mode
```

> Check `package.json` and `pyproject.toml` before inventing flags that may not exist.

---

## Architecture Rules — Never Violate

1. **Page modules do NOT own algorithmic logic** — UI calls backend via API only
2. **Algorithm engines do NOT own rendering logic** — they return data, never draw
3. **Session state is NOT hidden inside page code** — owned by MOD-001
4. **Artifact handling is explicit** — no silent reliance on TEMP reconstruction
5. **No cross-module imports** — modules communicate through canonical schemas only

---

## Storage Areas — Critical Distinction

| Area | Purpose | Persistence |
|---|---|---|
| `DATA/` | Scan folders + official scan artifacts | Permanent |
| `TEMP/` | Global working artifacts for active runtime | Non-persistent — may be cleared |
| `Saved Scans/` | Explicit save/resume packages | Persistent |

**Official artifacts** = `*_ENRICHED.csv` and `*_REID.csv`. When found in a scan folder they are immediately activatable — first-class inputs, not TEMP.

**Save Session** must export all required artifacts into `Saved Scans/`. Resume must work with zero TEMP dependency.

---

## Canonical Data Models

Defined in `backend/app/models/canonical_models.py`. Never invent schema for shared data.

| Model | Required fields |
|---|---|
| `ScanRecord` | `timestamp_utc`, `src_mac`, `rssi_dbm`, `gps_lat`, `gps_lon` |
| `EnrichedScanRecord` | All ScanRecord + enrichment fields + `match_found`, `match_delta_ms`, `match_score`, `match_method` |
| `ReIDRecord` | All EnrichedScanRecord + `cluster_id` (REQUIRED), `cluster_type` (`static`\|`dynamic`) |
| `SessionCalibration` | `scan_folder_id`, `parameter_source`, `parameters`, `approved` |
| `SavedSessionState` | `scan_folder_id`, `mode`, `saved_artifacts`, `saved_at_utc` |

---

## Module Map

Read a module's README before touching its code. The 14 modules:

| ID | Folder name | What it owns |
|---|---|---|
| MOD-001 | `session_navigation` | Active folder, mode, page, warnings, readiness |
| MOD-002 | `dataset_discovery` | Folder listing, CSV/PCAP matching, artifact resolution, stage-jump hints |
| MOD-003 | `normalization` | Raw input → canonical schema conversion |
| MOD-004 | `global_filters` | Filter definitions — defined once, applied everywhere |
| MOD-005 | `overview` | CSV-level inspection, stats, charts — no heavy processing |
| MOD-006 | `calibration` | Parameter derivation, RANSAC fit, fallback presets, approval |
| MOD-007 | `enrichment` | CSV + matching PCAP → `*_ENRICHED.csv` |
| MOD-008 | `reid` | ENRICHED → `*_REID.csv` with `cluster_id` + `cluster_type` |
| MOD-009 | `localization` | REID → per-cluster heatmap, peak, uncertainty regions |
| MOD-010 | `spatial_presentation` | Shared map rendering layer (Overview, Localization, Analysis) |
| MOD-011 | `result_analysis` | GT management, quality scoring, rerun orchestration |
| MOD-012 | `artifact_management` | Naming, overwrite rules, activation, export to Saved Scans |
| MOD-013 | `save_resume` | Session persistence — no TEMP dependency |
| MOD-014 | `canonical_models` | Single schema source of truth |

**Forbidden dependencies:**
- MOD-001 must NOT import from MOD-007, MOD-008, MOD-009, or MOD-010
- Algorithm engines (MOD-006 through MOD-009) must NOT import from page/UI modules

---

## API Design

- Session-centric: all workflow operations carry `session_id`
- Long-running ops (enrichment, re-id, localization, rerun) use `execution_id`
- Poll status: `GET /api/executions/{execution_id}`
- View-only controls (layers, zoom, basemap) do **not** hit execution endpoints and do **not** trigger rerun

---

## Rerun Rules

| Changed | Reruns from |
|---|---|
| Global filter | First downstream stage consuming filtered data |
| Calibration parameter | Localization → Result Analysis |
| Enrichment parameter | Enrichment → Re-ID → Localization → Result Analysis |
| Re-ID parameter | Re-ID → Localization → Result Analysis |
| Localization parameter | Localization → Result Analysis |
| View-only control | **Nothing** |

---

## Definition of Done

- [ ] Backend logic works, server runs without errors
- [ ] Unit tests pass for all touched modules
- [ ] API contract tests pass for touched endpoints
- [ ] No regressions in existing tests
- [ ] No forbidden module imports introduced
- [ ] TBD values are `# TODO: TBD per spec Part B` — never invented

---

## What NOT to Do

- Do not invent numeric defaults for parameters marked `TBD` in the spec
- Do not add behavior not in `docs/Part A.md` or `docs/Part B.md`
- Do not make localization engine render anything — returns data only
- Do not make page modules run algorithms — they call the API
- Do not make Save Session depend on TEMP surviving
- Do not touch the Air Unit / Airborne side — reference only, out of scope

---

## Roles & Slash Commands

| Command | Role | Owns |
|---|---|---|
| `/project:cto` | CTO | Architecture, spec compliance, module boundaries, technical decisions |
| `/project:dev:backend` | DEV — Backend | FastAPI endpoints, Python modules, data models, storage |
| `/project:dev:frontend` | DEV — Frontend | React pages, components, state management, API integration |
| `/project:dev:algo` | DEV — Algorithms | Enrichment, Re-ID, Localization, Calibration engines (spec-critical) |
| `/project:ux` | UX Designer | Page layouts, map UI, component design, user flows, UI kit |
| `/project:qa` | QA Engineer | Unit tests, integration tests, E2E, spec compliance review |
| `/project:researcher` | Researcher | Legacy algorithm review, magic values, spec alignment |
| `/project:codex-handoff` | Supervisor | Prepare `.ai/handoffs/current.md` so Codex can implement |
| `/project:plan` | — | Force planning before any complex task |

## Claude / Codex Collaboration

Use `docs/AI_COLLABORATION.md` as the protocol.

Default split:
- Claude supervises, reviews, researches, and writes focused handoffs.
- Codex implements, runs tests, and prepares compact result packets.

Claude should prepare Codex work in `.ai/handoffs/current.md`.
Codex should report results in `.ai/codex_result.md`.
Claude should write review findings in `.ai/reviews/claude_review.md`.
