# AI Collaboration Protocol

## Purpose

This project can use both Claude and Codex without wasting founder time.

Recommended split:

- Claude acts mostly as supervisor: CTO, QA, Researcher, UX, or focused reviewer.
- Codex acts mostly as developer: reads broad context, edits files, runs tests, integrates review findings.

Claude cannot directly trigger Codex unless an external script/API integration is added. Until then, collaboration is file-based: Claude writes a handoff packet, Codex reads it, Codex implements, then writes a result packet for Claude to review.

## Roles

### Claude

Best for:

- architecture review
- task planning
- spec compliance review
- PRD/product questions
- QA review
- legacy algorithm research
- focused critique of Codex diffs

### Codex

Best for:

- implementation
- repo-wide inspection
- large-context codebase work
- running tests
- fixing review findings
- maintaining local project files

## Handoff Files

Use these local files:

```text
.ai/
  handoffs/
    current.md
    archive/
  reviews/
    claude_review.md
  codex_result.md
  decisions_pending.md
```

## Claude To Codex Trigger

When Claude believes Codex should implement or inspect something, Claude should write `.ai/handoffs/current.md`:

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
- relevant task/module files

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

Only list decisions that block progress.
```

Then Claude tells the founder:

```text
Codex handoff is ready in .ai/handoffs/current.md.
Ask Codex: "Read .ai/handoffs/current.md and execute it."
```

## Codex To Claude Trigger

After implementation, Codex writes `.ai/codex_result.md`:

```markdown
# Codex Result

## Goal Completed

...

## Files Changed

- ...

## Tests Run

- ...

## Spec Sections Used

- ...

## Assumptions / TODOs

- ...

## Review Request For Claude

Focus on:
- spec compliance
- module boundaries
- missing tests
- risky assumptions
```

Then Codex tells the founder:

```text
Claude review packet is ready in .ai/codex_result.md.
Ask Claude: "/project:qa Review .ai/codex_result.md and the changed files."
```

## Claude Review Output

Claude writes `.ai/reviews/claude_review.md`:

```markdown
# Claude Review

## Verdict

Approve / Fix first / Founder decision needed

## Findings

1. Severity: ...
   File: ...
   Issue: ...
   Recommendation: ...

## Missing Tests

- ...

## Spec Mismatches

- ...

## Founder Decisions

- ...
```

Codex then reads `.ai/reviews/claude_review.md`, applies accepted fixes, reruns tests, and updates `.ai/codex_result.md`.

## Founder Escalation Rule

Claude and Codex should not ask the founder for routine engineering decisions.

Escalate only:

- behavior not covered by Parts A/B/C
- irreversible architecture choices
- data-loss or security tradeoffs
- legacy behavior that conflicts with the new spec
- scope changes

## First Development Use

Claude should hand Codex Sprint 01 TASK-01 through TASK-04 first:

1. Backend package files
2. Canonical models
3. FastAPI app factory and health endpoint
4. Stub API routers

