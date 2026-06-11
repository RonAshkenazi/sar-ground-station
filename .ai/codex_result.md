# Codex Result - Zone Lasso Selection + Dual-Test SAR Scoring

Date: 2026-06-03

## Summary

Implemented the handoff scope:

- Added a freehand lasso zone tool on the Localization map.
- Persisted the lasso polygon in `SessionContext` across page navigation and cleared it on session changes.
- Applied zone filtering to Localization and Result Analysis cluster visibility.
- Added Test 1 SAR Operational score in Result Analysis.
- Added Combined Score = mean(Test 1, Test 2).
- Scoped backend evaluation with optional `cluster_ids` and `gt_ids`.
- Added focused frontend and backend tests.

## Files Changed

- `frontend/src/components/LassoTool.tsx`
- `frontend/src/utils/geoUtils.ts`
- `frontend/src/utils/geoUtils.test.ts`
- `frontend/src/state/SessionContext.tsx`
- `frontend/src/pages/LocalizationPage.tsx`
- `frontend/src/pages/LocalizationPage.css`
- `frontend/src/pages/ResultAnalysisPage.tsx`
- `frontend/src/pages/ResultAnalysisPage.css`
- `frontend/src/api/sessions.ts`
- `frontend/src/helpTexts.ts`
- `backend/app/api/result_analysis.py`
- `backend/tests/unit/test_skeleton.py`

Note: `.ai/handoffs/current.md` was already modified by the incoming handoff and was not treated as an implementation file.

## Implementation Notes

- `LassoTool` disables map dragging while active, samples mousemove points at >=8px spacing, renders a dashed yellow live polyline, completes on mouseup with >=3 points, and cancels on Escape or short drawings.
- The persisted polygon is rendered as a dashed yellow overlay on both Localization and Result Analysis maps.
- Localization keeps existing cluster visibility when no lasso is active. When a lasso is active, only successful clusters with a primary peak inside the polygon remain visible.
- Result Analysis computes:
  - `Test 1` count score: `max(0, 1 - abs(n_circles - n_expected) / n_expected)`
  - `Test 1` area score: `max(0, 1 - (circleArea / lassoArea)^2)`
  - `Combined Score`: `(test1.total + evalResult.score.total) / 2`
- `runEvaluation` now accepts optional `cluster_ids` and `gt_ids`; backend filters predictions and GT before calling the existing engine.

## Validation

Passed:

- `cd frontend && npm.cmd run build`
- `cd frontend && npm.cmd test -- --run`
- `cd backend && python -m pytest tests/unit/test_skeleton.py::test_result_analysis_api_evaluate_filters_by_cluster_and_gt_ids`

Full backend suite:

- `cd backend && python -m pytest tests/`
- Result: 142 passed, 9 failed, 1 warning.

The 9 failing tests match the known existing failures from before this handoff:

- Localization constant/default expectation mismatches.
- Result-analysis ambiguity expectation mismatches.
- Guidance recommendation/config expectation mismatches.

## Open Items

- Manual browser verification of freehand drawing was not performed in this run.
- Full backend test suite remains blocked by pre-existing expectation failures unrelated to the lasso/filter implementation.

## Follow-up Fixes

Applied 2026-06-03:

- Result Analysis Clear Zone now also clears `evalResult`, preventing stale zone-scoped scores after the zone is removed.
- Localization zone badge now uses `visibleClusters.length`, so the count respects hidden clusters and static/noise visibility toggles.
- Result Analysis GT markers outside the active zone now render with lower stroke opacity and fill opacity.

Validation after each fix:

- `cd frontend && npm.cmd run build` passed after all three fixes.
- `cd backend && python -m pytest tests/` was run after all three fixes and remained at the same known result: 142 passed, 9 failed, 1 warning.
