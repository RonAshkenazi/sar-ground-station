# Codex Role Setup

This directory mirrors the project role workflow for Codex.

## How To Use

Ask Codex to work in a role:

- `Act as CTO and design the Phase 0 architecture skeleton.`
- `Act as DEV and implement MOD-002 Dataset Discovery.`
- `Act as QA and test the current implementation against Part A and Part B.`

Codex should then apply:

- `.codex/AGENTS.md` for project-wide rules
- `.codex/agents/cto.md` for architecture, planning, and review
- `.codex/agents/dev.md` for implementation
- `.codex/agents/qa.md` for verification

## Source Of Truth

Use these docs first:

1. `CLAUDE.md`
2. `docs/Part A.md`
3. `docs/Part B.md`
4. `docs/Part C.md`
5. `backend/AGENTS.md` or `frontend/AGENTS.md` when working in those domains

`docs/PRD.md` and `docs/ARCHITECTURE.md` are still scaffold placeholders.

