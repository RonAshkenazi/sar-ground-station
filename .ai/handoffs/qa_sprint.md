# Codex Handoff — QA: Code vs. Spec Audit

## Requested Role

[QA]

## Purpose

Audit the current codebase against the spec (`docs/Part A.md`, `docs/Part B.md`) and
the founder's decisions in `.ai/founder_decisions.md` and `.ai/decisions_pending.md`.
Report findings in `.ai/reviews/claude_review.md` — do NOT make any code changes.

---

## Required Reading (read ALL before auditing)

- `docs/Part A.md` — architecture, page/module spec
- `docs/Part B.md` — algorithms, parameters, API contracts
- `.ai/founder_decisions.md`
- `.ai/decisions_pending.md`
- `.ai/codex_pdf_deviations.md` (if exists)

## Files to Audit

- `backend/app/modules/reid/engine.py`
- `backend/app/api/result_analysis.py`
- `frontend/src/pages/OverviewPage.tsx`
- `frontend/src/pages/ReIdEnrichmentPage.tsx`
- `frontend/src/pages/ResultAnalysisPage.tsx`
- `frontend/src/api/sessions.ts`

---

## Audit Areas

### Area 1 — Re-ID stats
The founder wants to see in the Re-ID results panel:
- **Unique dynamic MAC count** — distinct `src_mac` values that ended up in a dynamic cluster (not noise)
- **Dynamic cluster count** — already returned as `dynamic_cluster_count`

Check:
1. Does `run_reid` in `engine.py` currently return `unique_dynamic_mac_count`?
2. Is it typed in `sessions.ts` `ReIdQuality` interface?
3. Is it displayed in `ReIdEnrichmentPage.tsx`?
4. What does Part B say about Re-ID output fields?

### Area 2 — Overview page client-side filtering
The founder wants: RSSI range filter, MAC prefix/OUI filter, minimum packet count filter,
time range filter, and sort control on the device table.

Check:
1. Does `OverviewPage.tsx` have any client-side filtering currently (beyond the heartbeat toggle)?
2. What does Part A / Part B specify for the Overview page filter capabilities?
3. Are any of these filters mentioned as global filters (MOD-004) vs. page-local?
4. Flag any inconsistency between what's coded and what's specced.

### Area 3 — Result Analysis map completeness
The founder says the map is not like the Localization page. The expected state is:
- Same heatmap (grid cells with heat color)
- Same cluster visibility toggles (individual + static/noise bulk)
- Uncertainty radii
- Peak markers
- GT markers (already present)
- Match lines (already present)
- Distinct markers for false positives (unmatched clusters) and false negatives (unmatched GT)

Check:
1. Does `ResultAnalysisPage.tsx` render heatmap grid cells?
2. Does it have per-cluster visibility toggles?
3. Are FP clusters and FN GT points visually distinguished from matched ones?
4. What does Part A spec for the Result Analysis map?

### Area 4 — Result Analysis rerun module
Currently `result_analysis.py` only supports `stage: 'localization'` and raises 422
for any other stage.

Check:
1. What does Part A / Part B specify for the rerun module (MOD-011)?
2. Should reruns be triggerable from Re-ID stage (Re-ID → Localization)?
3. What Re-ID parameters should be tunable on rerun?
4. What Localization parameters should be tunable on rerun (current list:
   `grid_resolution_m`, `dynamic_sigma_alpha`, `confidence_cutoff`,
   `uncertainty_participation_floor`, `uncertainty_alpha`)?
5. Does the rerun rerun table in CLAUDE.md (`Changed → Reruns from`) include a
   Re-ID-param change triggering Re-ID + Localization?

### Area 5 — General gaps
Scan for any other items that appear in the spec but are clearly missing or
stubbed (`# TODO: TBD`) in the implemented files above. List them briefly.

---

## Output Format

Write findings to `.ai/reviews/claude_review.md` using this structure:

```
# QA Audit — [date]

## Area 1 — Re-ID stats
- Status: [Missing / Partial / Done]
- Finding: ...
- Spec says: ...

## Area 2 — Overview filters
- Status: [Missing / Partial / Done]
- Finding: ...
- Spec says: ...

## Area 3 — Result Analysis map
- Status: [Missing / Partial / Done]
- Finding: ...
- Spec says: ...

## Area 4 — Result Analysis rerun
- Status: [Missing / Partial / Done]
- Finding: ...
- Spec says: ...

## Area 5 — General gaps
- [list]

## Summary
One paragraph overview of priority gaps.
```

Do NOT make any code changes. Report only.
