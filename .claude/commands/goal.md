# /goal — Persistent Goal Tracking

Set or manage a goal that stays active across the whole session.

## Usage

- `/goal <describe what you want done>` — set a new goal and start working on it
- `/goal status` — report current goal and progress
- `/goal pause` — pause and summarise where things stand
- `/goal resume` — pick up from the last pause point
- `/goal clear` — clear the current goal and return to normal

## Arguments

$ARGUMENTS

## Behaviour

When a goal is set:

1. **Echo the goal back** in one sentence so the user can confirm it.
2. **Break it into steps** — list them before starting, numbered, with the first marked `→ NOW`.
3. **Work step by step**, checking off each step as it completes: `✓ Step 1 done`.
4. **Stay on task** — do not go off on tangents or make unrequested changes. If something unexpected blocks a step, pause and report it rather than improvising.
5. **Guard against runaway work** — after completing each step, output a one-line status: `[Goal: N/M steps done — next: <step name>]`. If all steps are done, declare the goal complete and stop.

## Handling sub-commands

| Input | Action |
|---|---|
| `/goal status` | Print current goal, steps done/remaining, last blocker if any |
| `/goal pause` | Write a one-paragraph handoff note: goal, steps done, next step, any blockers |
| `/goal resume` | Read the handoff note and continue from the next step |
| `/goal clear` | Acknowledge the goal is cleared; return to normal assistant behaviour |

## Rules

- Never silently expand the goal scope — if extra work is needed, ask first.
- Never skip a step to save time.
- If a step fails, report the error and stop — do not automatically retry with a different approach unless the user says to.
- Keep responses tight during execution. One-line step completions, not paragraphs.
