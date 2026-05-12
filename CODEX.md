# Codex Operating Guide

This file tells Codex how to work correctly in this repository.

## Project

SAR Ground Station: a backend/frontend application for Search and Rescue RF scan inspection, enrichment, Re-ID, localization, result analysis, and save/resume.

Stack target:

- Backend: Python + FastAPI
- Frontend: TypeScript + React
- E2E: Playwright

Current build phase: Phase 0, Repo & Skeleton.

## Source Of Truth

For product behavior and architecture, use these first:

1. `CLAUDE.md`
2. `docs/Part A.md`
3. `docs/Part B.md`
4. `docs/Part C.md`
5. `.codex/AGENTS.md`

Notes:

- `docs/Part A.md` defines the core system, modules, user flows, data models, and constraints.
- `docs/Part B.md` defines algorithms, parameters, rerun rules, and API contracts.
- `docs/Part C.md` defines implementation order and safe AI coding workflow.
- `docs/PRD.md` and `docs/ARCHITECTURE.md` are still scaffold placeholders unless later updated.

## Roles

Use the role files in `.codex/agents/`:

- CTO: `.codex/agents/cto.md`
- DEV: `.codex/agents/dev.md`
- DEV Backend: `.codex/agents/dev-backend.md`
- DEV Frontend: `.codex/agents/dev-frontend.md`
- DEV Algorithm: `.codex/agents/dev-algo.md`
- QA: `.codex/agents/qa.md`
- RESEARCHER: `.codex/agents/researcher.md`
- UX: `.codex/agents/ux.md`

Default role is `[DEV]` for implementation requests.

Use specialized developer roles when the scope is clear:

- `[DEV:backend]` for FastAPI, models, services, storage, API tests
- `[DEV:frontend]` for React, routes, components, state, API integration
- `[DEV:algo]` for Calibration, Enrichment, Re-ID, Localization engines

Use `[CTO]` when asked for:

- architecture
- planning
- technical decisions
- code review
- task breakdown

Use `[QA]` when asked for:

- testing
- bug discovery
- regression checks
- spec compliance review

Use `[RESEARCHER]` when asked for:

- legacy app review
- algorithm verification
- magic-number/default discovery
- side-by-side legacy vs new behavior planning

Use `[UX]` when asked for:

- page layout
- operational workflow design
- component behavior
- UI kit decisions

Start user-facing responses with the active role tag.

## Core Rules

- Do not add behavior not described in Part A or Part B.
- Do not invent numeric defaults marked `TBD`.
- If a detail is TBD, leave `TODO: TBD per spec Part B`.
- Keep backend and frontend separate.
- Page modules must not own algorithmic logic.
- Algorithm engines must not own rendering logic.
- Session state must not be hidden inside page code.
- Cross-module data must use canonical schemas.
- Artifact handling must be explicit.
- Existing `*_ENRICHED.csv` and `*_REID.csv` files are official artifacts.
- Save/resume must not depend on `TEMP` surviving.
- The Air Unit / Airborne side is reference-only and out of scope.
- The legacy app under `reference/legacy_app/` is read-only reference context unless the founder explicitly asks for changes there.

## Build Order

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

First milestone: operational Wi-Fi flow through Enrichment.

Do not ask Codex to build the whole system at once. Work in one module, one page plus one backend contract, or one execution flow.

## Quality Gates

A task is done only when:

- The implementation follows the relevant spec sections.
- Touched backend/frontend tests pass, or blockers are reported.
- New service logic has focused unit tests.
- Touched API endpoints have contract or integration coverage.
- User-facing flows have E2E or integration coverage where practical.
- Module boundaries remain intact.
- Artifact lifecycle rules are respected.
- New assumptions are documented.
- Important technical decisions are added to `docs/DECISIONS.md`.

## Common Commands

Check real project files before assuming commands exist.

```powershell
cd backend; uvicorn app.main:app --reload
cd backend; pytest
cd frontend; npm run dev
cd frontend; npm run build
cd frontend; npm test
npx playwright test
```

## Local Runtime And Reference Folders

Use these repo-local Windows development paths:

```text
runtime/DATA
runtime/TEMP
runtime/Saved Scans
reference/legacy_app
```

Copy scan folders into `runtime/DATA/`.
Copy the working legacy app into `reference/legacy_app/`.
These contents are ignored by git.

## Recommended Prompt Pattern

Use prompts like:

```text
Act as CTO.
Goal: Plan Phase 0 only.
Use CODEX.md, .codex/AGENTS.md, docs/Part A.md, docs/Part B.md, and docs/Part C.md.
Do not write code yet.
Return files affected, decisions, risks, DEV tasks, and tests needed.
```

```text
Act as DEV.
Goal: Implement MOD-002 Dataset Discovery & Artifact Resolver only.
Use CODEX.md, .codex/AGENTS.md, docs/Part A.md, docs/Part B.md, and docs/Part C.md.
Do not add unspecified behavior.
Do not invent TBD values.
Include tests.
```

```text
Act as QA.
Goal: Verify the current implementation against Part A and Part B.
Report bugs, spec mismatches, module boundary violations, and missing tests.
```

```text
Act as RESEARCHER.
Goal: Review the legacy Wi-Fi enrichment algorithm.
Use reference/legacy_app, docs/Part A.md, docs/Part B.md, and docs/Part C.md.
Do not modify legacy code.
Report hidden assumptions, magic values, spec mismatches, and side-by-side fixture needs.
```

## Claude / Codex Collaboration

Use `docs/AI_COLLABORATION.md`.

When Claude prepares `.ai/handoffs/current.md`, Codex should:

1. Read the handoff.
2. Read the required project docs.
3. Execute the scoped task.
4. Run the listed tests when possible.
5. Write `.ai/codex_result.md` for Claude review.

When Claude writes `.ai/reviews/claude_review.md`, Codex should apply accepted fixes, rerun relevant tests, and update `.ai/codex_result.md`.
