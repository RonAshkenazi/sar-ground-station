## Quick Start

### Ports

| Service  | Default port | Controlled by env var |
|----------|--------------|-----------------------|
| Backend  | 8000         | `BACKEND_PORT`        |
| Frontend | 5173         | `FRONTEND_PORT`       |

To change a port: edit `.env` (copy `.env.example` first), then update `playwright.config.ts` `baseURL` to match the new frontend port.

### Run

```bash
# 1. Copy and configure environment
cp .env.example .env

# 2. Backend (terminal 1)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. Frontend (terminal 2)
cd frontend
npm install
npm run dev

# 4. Tests
cd backend && pytest
npx playwright test
```

### Live Mission Pi Connectivity

For live mission mode, the backend must listen on all network interfaces:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Do not run the backend bound only to `127.0.0.1` or `localhost`. That allows the frontend on the same laptop to work, but the Pi cannot connect to the ground station at the laptop LAN IP, for example `192.168.1.100:8000`. If the frontend shows the Pi as disconnected while the Pi is powered on, first confirm the backend was started with `--host 0.0.0.0`.

---

# SAR Ground Station

Desktop application for Search and Rescue RF scanning and device localization. Processes drone-collected Wi-Fi and BLE scan data through a pipeline ending in a localization map.

**Stack:** Python + FastAPI (backend) · TypeScript + React (frontend) · Playwright (E2E)

---

## What It Does

```
Scan Folder (DATA/) → Overview → Calibration → Enrichment (CSV+PCAP) → Re-ID → Localization → Map
```

Two user types:
- **Operational** — SAR field teams. Run the pipeline, inspect map results.
- **Research** — Dev/tuning team. Result Analysis, ground-truth comparison, parameter tuning.

---

## Project Structure

```
.
├── CLAUDE.md                  # Project context and architecture rules (read first)
├── AGENTS.md                  # Role definitions for AI collaboration
├── CODEX.md                   # Codex operating guide
├── docs/
│   ├── Part A.md              # Architecture spec — source of truth
│   ├── Part B.md              # Algorithms, parameters, API contracts
│   ├── Part C.md              # Build order (Phases 0–9)
│   ├── AI_COLLABORATION.md    # Claude ↔ Codex handoff protocol
│   ├── ARCHITECTURE.md
│   ├── DECISIONS.md           # Decision log
│   └── sprints/               # Sprint indexes, todos, reports
├── backend/
│   └── app/
│       ├── api/               # FastAPI route files (one per domain)
│       ├── models/            # Canonical data models
│       ├── modules/           # 14 business logic modules (MOD-001 … MOD-014)
│       └── storage/           # Path resolution, TEMP, Saved Scans helpers
├── frontend/
│   └── src/
│       ├── pages/             # 6 workflow pages
│       ├── components/        # Shared UI components
│       ├── api/               # Backend API client
│       ├── state/             # Session state
│       └── types/             # Shared TypeScript types
├── tests/
│   └── e2e/                   # Playwright E2E tests
├── runtime/
│   ├── DATA/                  # Scan folders (permanent)
│   ├── TEMP/                  # Working artifacts (non-persistent)
│   └── Saved Scans/           # Save/resume packages (persistent)
└── reference/
    └── legacy_app/            # Read-only legacy reference — do not modify
```

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

---

## Slash Commands

| Command | Role | Use When |
|---|---|---|
| `/project:cto` | CTO | Architecture decisions, module design, code review |
| `/project:dev:backend` | DEV — Backend | FastAPI endpoints, Python modules, data models |
| `/project:dev:frontend` | DEV — Frontend | React pages, components, state, API integration |
| `/project:dev:algo` | DEV — Algorithms | Calibration, Enrichment, Re-ID, Localization engines |
| `/project:qa` | QA | Testing, regression checks, spec compliance |
| `/project:plan` | — | Force planning before complex work |
| `/project:codex-handoff` | — | Prepare a handoff packet for Codex |

---

## AI Collaboration

Claude and Codex work together via file-based handoffs. See `docs/AI_COLLABORATION.md`.

- **Claude** supervises: architecture review, spec compliance, QA, task planning
- **Codex** implements: writes code, runs tests, fixes review findings

Handoff files live in `.ai/`:
- `.ai/handoffs/current.md` — Claude → Codex work packet
- `.ai/codex_result.md` — Codex → Claude review request
- `.ai/reviews/claude_review.md` — Claude → Codex review findings

---

## Scan Data

Place scan folders in `runtime/DATA/`. Each scan session is one subfolder:

```
runtime/DATA/
  my-scan-2026-05-11/
    scan_2026-05-11_10-00-00Z.csv
    scan_2026-05-11_10-00-00Z.pcap     ← optional, required for enrichment
```

Official artifacts (`*_ENRICHED.csv`, `*_REID.csv`) found in a scan folder are treated as first-class inputs and can be activated without re-running earlier pipeline stages.

---

## Spec

All behavior is defined in `docs/Part A.md` and `docs/Part B.md`. Build order is in `docs/Part C.md`. Do not add behavior not described there.
