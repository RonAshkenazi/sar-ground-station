# Claude Review — Two-Stage GT Matching (FD-S3 Amendment, 2026-08-14)

**Reviewer:** [CTO] Claude
**Date:** 2026-08-14
**Codex result:** `.ai/codex_result.md`
**Handoff:** `.ai/handoffs/current.md`
**Verdict:** **APPROVED**

---

## Verdict

Approve. This is the most algorithmically involved change reviewed this session, and Codex's
implementation includes a meaningful, correct deviation from my literal handoff that I
independently hand-verified and confirmed fixes a real flaw in my own design.

## The deviation, and why it's correct

My handoff specified: feed *all* originally-ambiguous GTs into a single joint stage-2
`_linear_sum_assignment` over the leftover clusters. Codex instead pre-filters: only GTs whose
ratio-window candidate set, restricted to leftover (unclaimed) clusters, has narrowed to
**exactly one** remaining candidate enter stage 2 at all (`_ratio_window_candidate_indices`
gates entry via `len(...) == 1`).

I traced this by hand against `test_irreducible_ambiguity_with_two_leftover_candidates_stays_ambiguous`:
two candidates equidistant from one GT, neither claimed by anything else in stage 1. Under my
literal spec, this GT would still enter stage 2 with both candidates as columns, and Hungarian
would force a pick (whichever has marginally lower cost) — reporting a confident "match" where
genuine, irreducible ambiguity exists. That directly contradicts the user's own stated intent
("if only one stays, it's a match" implies if more than one stays, it's still not) and my own
acceptance criterion for irreducible ambiguity. Codex's `==1` gate correctly leaves this case
unmatched and still reported in `ambiguous_gts`.

I then hand-verified the multi-GT-chain case still resolves correctly under this stricter gate
(`test_multi_gt_chain_resolves_shared_leftover_cluster_by_second_assignment`): two GTs whose
*individual* windows each narrow to exactly one candidate — coincidentally the *same* one —
both pass the `==1` gate individually and both enter stage 2, where the joint assignment
correctly awards it to whichever fits better and leaves the other GT genuinely unmatched. Full
worked arithmetic (distances, ratios, window computation, cost values) checked against the test
fixture — matches exactly. This is a strict improvement over my spec, not a regression.

## Diff Review

- Stage 1 classification loop: byte-for-byte unchanged.
- `competed_away_gt_indices` computed immediately after stage 1, from stage-1-only
  `matched_gt_idx` — confirmed unchanged in meaning.
- `stage2_candidate_indices_by_gt` / `ambiguous_gt_list` / `cost2` construction: matches the
  `==1`-gated design described above; `max_match_dist_m` is correctly re-checked when building
  `cost2` cells (so a narrowed-to-one candidate that's still out of range never gets a real
  cost, confirmed via `test_still_ambiguous_reporting_uses_narrowed_viable_leftover_candidates`).
- `cost[i][j]` correctly back-filled for stage-2 pairs so the existing `matches`-building loop
  needs no branching for `association_cost`.
- `association_status` correctly tagged via `stage1_pairs_set` membership.
- `ambiguous_gts` reporting correctly branches: `still_ambiguous` GTs get narrowed
  (leftover-filtered) `competing_cluster_ids`; `competed_away` GTs keep the original unfiltered
  logic (never ambiguous to begin with, shape intentionally unchanged).
- `false_positives`/`duplicates` correctly read the final merged `matched_pred_idx`/
  `matched_gt_idx`.
- Nothing touched outside `evaluate()` and the new `_ratio_window_candidate_indices` helper —
  confirmed no changes to `_cluster_reliability`, `_reliability_for_pred`, Test 1, localization,
  or Re-ID code.

## Test Summary

| Check | Result |
|---|---|
| `pytest tests/unit/test_result_analysis_two_stage_matching.py tests/unit/test_result_analysis_reliability.py` | **9 passed** — all 5 new tests hand-verified by full manual arithmetic trace before running, not just read |
| `pytest` (full backend suite) | **164 passed, 9 failed** |
| Failures pre-exist, unrelated | **Confirmed** — identical 9 failures/names as every prior review this session. Per the handoff's explicit ask, Codex checked whether this change incidentally fixed `test_evaluate_pack_produces_ambiguous_gt` / `test_evaluate_three_close_clusters_produces_ambiguous_gt` (the two ambiguous-GT-related pre-existing failures) — it does not, because those fixtures classify as *clear* (not ambiguous) under the current `ratio_gate`, so this change never touches their code path. Correctly reported rather than silently left unexplained. |

## Live Validation

Restarted the backend cleanly (confirmed on-disk code matched a fresh Python import first, per
the now-familiar `--reload` flakiness pattern). Built a real session against `scan_S1_REID.csv`
with real calibration and localization, giving 3 real successful clusters — two of them
(`2` and `2c:59:8a:58:95:c1`) only **4.5m apart**.

Placed one GT exactly at the midpoint between those two clusters (genuinely ambiguous) and a
second GT very close to cluster `2` specifically (clear match). Live `evaluate()` result:

```
gt-clear-near-c2  -> cluster 2                  clear_match             (1.50m)
gt-ambiguous      -> cluster 2c:59:8a:58:95:c1  resolved_after_narrowing (2.25m)
```

Exactly the designed behavior: the clear GT claimed cluster `2` in stage 1, and the ambiguous
GT — which originally had both clusters as viable candidates — was correctly rescued to the one
remaining unclaimed cluster in stage 2, tagged transparently as
`resolved_after_narrowing`. `ambiguous_gts` came back empty (both resolved), and the third,
unrelated cluster correctly landed in `false_positives`.

## Missing Tests

None blocking.

## Spec Mismatches

None — the FD-S3 amendment documents the design Codex implemented (including the rationale for
why a joint second assignment is needed over a naive one-at-a-time rule); the `==1` entry gate
is a legitimate refinement within that spec's intent, not a deviation from it in substance.

## Founder Decisions

None needed. Worth a note for the record (not a blocking decision): Codex's `==1` gate is
arguably worth writing back into the founder decision text itself, since my original amendment
paragraph technically describes the less-correct version. Not required — the code and tests are
correct and this review documents the reasoning — but if the founder decisions doc is meant to
be the durable source of truth going forward, it'd be worth tightening.
