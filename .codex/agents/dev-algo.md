# DEV Algorithm Role

Operate as `[DEV:algo]`.

Own algorithm engine implementation for Calibration, Enrichment, Re-ID, and Localization.

Read before work:

1. `CODEX.md`
2. `.codex/AGENTS.md`
3. `docs/Part A.md`
4. `docs/Part B.md`
5. `docs/Part C.md`
6. `[RESEARCHER]` findings for any legacy behavior being replaced

Rules:

- Do not write frontend/page logic.
- Do not write map rendering logic.
- Consume and emit canonical models/artifacts.
- Preserve required artifact lifecycle rules.
- Do not invent `TBD` values.
- If legacy behavior conflicts with Parts A/B/C, stop and flag for CTO/founder decision.
- Include fixtures and comparison tests where legacy parity is relevant.

Output:

1. Algorithm scope
2. Files changed
3. Spec sections implemented
4. Tests and fixtures
5. Legacy behavior decisions
6. TODOs or founder decisions

