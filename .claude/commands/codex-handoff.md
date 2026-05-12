# Prepare Codex Handoff

You are preparing work for Codex.

Codex is the primary implementation agent for this project. Claude should supervise, review, and create focused handoff packets.

## Required Output File

Write or update:

`.ai/handoffs/current.md`

## Before Writing

Read:

1. `docs/AI_COLLABORATION.md`
2. `CODEX.md`
3. `docs/PRD.md`
4. `docs/Part A.md`
5. `docs/Part B.md`
6. `docs/Part C.md`
7. Relevant sprint/module files

## Handoff Format

```markdown
# Codex Handoff

## Requested Role

[DEV:backend] / [DEV:frontend] / [DEV:algo] / [QA] / [RESEARCHER] / [UX]

## Goal

One concrete task or vertical slice.

## Required Reading

- CODEX.md
- docs/PRD.md
- docs/Part A.md
- docs/Part B.md
- docs/Part C.md
- ...

## Scope

Files or modules Codex may change.

## Out Of Scope

Things Codex must not touch.

## Acceptance Criteria

- [ ] ...

## Constraints

- Do not invent TBD values.
- Do not add behavior outside Parts A/B/C.
- Preserve module boundaries.

## Tests To Run

- ...

## Founder Decisions Needed

Only founder-level blockers.
```

## After Writing

Tell the founder:

```text
Codex handoff is ready in .ai/handoffs/current.md.
Ask Codex: "Read .ai/handoffs/current.md and execute it."
```

