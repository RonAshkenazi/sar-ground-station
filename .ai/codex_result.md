# Codex Result - FD-S3 Two-Stage GT Matching

Date: 2026-08-14

## Summary

Implemented the FD-S3 amendment for two-stage GT matching in Result Analysis.

- Stage 1 keeps the existing clear-match classification and assignment behavior.
- `competed_away_gt_indices` is computed from the stage-1 matched GT set before stage-2 state is merged.
- Stage 2 runs a second joint `_linear_sum_assignment` over stage-1 leftover clusters and ambiguous GTs whose original ratio-window candidates have narrowed to a viable leftover candidate set.
- Stage-2 matches are merged into the final matched sets and reported with `association_status: "resolved_after_narrowing"`.
- Still-ambiguous GT reporting now narrows `competing_cluster_ids` to currently unclaimed and still-viable original ratio-window candidates.
- `false_positives` and `duplicates` now naturally use the final stage-1 plus stage-2 matched sets.

## Files Changed

- `backend/app/modules/result_analysis/engine.py`
- `backend/tests/unit/test_result_analysis_two_stage_matching.py`
- `.ai/codex_result.md`

## Tests Added

- No-ambiguity fixture preserves clear-match behavior.
- Simple rescue: ambiguous GT matches a free candidate after stage 1 claims the other candidate.
- Multi-GT chain: two ambiguous GTs contest one leftover cluster through the second assignment; exactly one gets it.
- Irreducible ambiguity: two still-unclaimed close candidates remain ambiguous.
- Narrowed reporting: stale claimed or non-viable candidates are not listed as remaining competitors.

## Validation

Passed:

- `cd backend; python -m pytest tests/unit/test_result_analysis_two_stage_matching.py tests/unit/test_result_analysis_reliability.py`
  - `9 passed`
- `cd backend; python -m py_compile app/modules/result_analysis/engine.py`
- `git diff --check`

Ran with existing failures:

- `cd backend; python -m pytest`
  - `164 passed, 9 failed`

The remaining 9 backend failures match the known unrelated set:

- Localization constant/default expectation mismatches.
- Existing Result Analysis ambiguity expectation mismatches.
- Guidance recommendation/config expectation mismatches.

The two existing skeleton ambiguous-GT failures remain in the failing set; this amendment did not change their outcome because those fixtures still classify as clear under the current `ratio_gate`.

## Founder Decisions

None. FD-S3 amendment covers this change.
