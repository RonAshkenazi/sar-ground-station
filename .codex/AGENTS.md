# Codex Project Instructions

This folder adapts the repository's Claude-oriented role system for Codex.
The root `AGENTS.md`, `CLAUDE.md`, and `docs/Part A.md` / `docs/Part B.md` remain the source of truth.

## Project Identity

Project: SAR Ground Station

Purpose: desktop-oriented ground station for Search and Rescue RF scan inspection, enrichment, Re-ID, localization, result analysis, and save/resume.

Architecture: Python FastAPI backend plus TypeScript/React frontend with strict separation between UI, workflow/session orchestration, algorithms, artifacts, and canonical models.

Current phase: Phase 0, Repo & Skeleton. See `docs/Part C.md`.

## Required Reading Before Work

For any non-trivial task, read:

1. `CLAUDE.md`
2. `AGENTS.md`
3. `docs/Part A.md`
4. `docs/Part B.md`
5. `docs/Part C.md`
6. Relevant domain `AGENTS.md` files under `backend/` or `frontend/`
7. The README for the module being changed, if one exists

`docs/PRD.md` and `docs/ARCHITECTURE.md` are still scaffold placeholders. Prefer `CLAUDE.md`, `docs/Part A.md`, `docs/Part B.md`, and `docs/Part C.md` until those files are updated.

## Operating Roles

Use these role files when the founder asks for a specific role:

- CTO: `.codex/agents/cto.md`
- DEV: `.codex/agents/dev.md`
- DEV Backend: `.codex/agents/dev-backend.md`
- DEV Frontend: `.codex/agents/dev-frontend.md`
- DEV Algorithm: `.codex/agents/dev-algo.md`
- QA: `.codex/agents/qa.md`
- RESEARCHER: `.codex/agents/researcher.md`
- UX: `.codex/agents/ux.md`

Start user-facing updates and final responses with the active role tag:

- `[CTO]`
- `[DEV]`
- `[DEV:backend]`
- `[DEV:frontend]`
- `[DEV:algo]`
- `[QA]`
- `[RESEARCHER]`
- `[UX]`

Default to `[DEV]` for implementation requests unless the founder explicitly asks for architecture/review (`[CTO]`), backend (`[DEV:backend]`), frontend (`[DEV:frontend]`), algorithms (`[DEV:algo]`), testing/verification (`[QA]`), legacy algorithm investigation (`[RESEARCHER]`), or user experience (`[UX]`).

## Non-Negotiable System Rules

- Part A and Part B are the source of truth for behavior.
- Do not add behavior not described in the spec.
- Do not invent numeric defaults marked `TBD`; leave clear `TODO: TBD per spec Part B`.
- Page modules do not own algorithmic logic.
- Algorithm engines do not own rendering logic.
- Session state is not hidden inside page code.
- Artifact handling is explicit.
- Save/resume must not depend on `TEMP` surviving.
- Existing `*_ENRICHED.csv` and `*_REID.csv` files in a scan folder are official artifacts.
- Cross-module data must use canonical schemas.
- No direct cross-module imports except through approved public interfaces and canonical models.
- The Air Unit / Airborne side is reference-only and out of scope.
- The legacy app under `reference/legacy_app/` is reference-only unless the founder explicitly asks for changes there.

## Canonical Modules

- MOD-001 App Session & Navigation
- MOD-002 Dataset Discovery & Artifact Resolver
- MOD-003 Protocol & Schema Normalization
- MOD-004 Global Filter Engine
- MOD-005 Overview Module
- MOD-006 Calibration Module
- MOD-007 Enrichment Module
- MOD-008 Re-ID Engine
- MOD-009 Localization Engine
- MOD-010 Spatial Presentation Module
- MOD-011 Result Analysis Module
- MOD-012 Artifact Management
- MOD-013 Save / Resume Module
- MOD-014 Canonical Models & Schema Module

## Implementation Order

Follow `docs/Part C.md`:

1. Backend/frontend skeleton
2. Canonical models and session state
3. DATA inventory and artifact activation
4. Overview backend and frontend
5. Calibration backend and page
6. Enrichment backend
7. Re-ID backend
8. Localization backend
9. Spatial presentation map layer
10. Result Analysis backend and page
11. Save/resume
12. Hardening and regression comparisons

First milestone: operational Wi-Fi workflow through Enrichment.

Keep tasks small: one module, one page plus one backend contract, or one execution flow.

## Quality Gates

A task is complete only when:

- Touched backend/frontend commands run or any inability to run is reported.
- Unit tests exist for new service logic.
- API contract tests exist for touched endpoints.
- E2E or integration coverage exists for changed user flows where practical.
- Module boundaries remain intact.
- Artifact lifecycle rules are respected.
- New assumptions are documented.
- `docs/DECISIONS.md` is updated for material technical decisions.
- Legacy algorithm uncertainty is handled through `[RESEARCHER]` review before blindly preserving behavior.

## Common Commands

Check actual project files before assuming these exist.

```powershell
cd backend; uvicorn app.main:app --reload
cd backend; pytest
cd frontend; npm run dev
cd frontend; npm run build
cd frontend; npm test
npx playwright test
```
