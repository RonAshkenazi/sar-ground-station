# Codex Handoff

## Requested Role

[DEV:algo]

## Goal

Implement two-stage GT matching in `evaluate()`, per the **FD-S3 amendment (2026-08-14,
"two-stage GT matching for ambiguous GTs")** in `.ai/founder_decisions.md`. Ambiguous GTs
(competing candidates too close in distance to call a clear winner) currently get zero chance
to match anything, even when one of their candidates ends up completely unclaimed after the
first pass resolves. Add a second optimal-assignment pass over just the leftover
(still-unclaimed) clusters, restricted to originally-ambiguous GTs.

## Required Reading

- CODEX.md
- `.ai/founder_decisions.md` → **FD-S3**, specifically the **"Amendment — two-stage GT matching
  for ambiguous GTs (2026-08-14)"** paragraph at the end of the FD-S3 entry — this is the full
  spec, read it before touching code, especially the multi-GT-chain example
- `backend/app/modules/result_analysis/engine.py` (whole file — short, ~355 lines; the change
  is entirely inside `evaluate()`, roughly lines 79-170 today, but read the whole function
  including `matches`/`ambiguous_gts`/`false_positives`/`duplicates` construction since all of
  them read from the matched-index sets you're changing)
- `backend/tests/unit/test_skeleton.py` — search for `test_evaluate_pack_produces_ambiguous_gt`
  and `test_evaluate_three_close_clusters_produces_ambiguous_gt`; these are two of the 9
  pre-existing failing tests in this file (unrelated, already failing before this handoff) —
  read them anyway since they exercise the exact ambiguous-GT code path you're changing, so you
  understand current expected shapes even though they're not passing today

## Scope

All changes confined to `backend/app/modules/result_analysis/engine.py::evaluate()`.

**1. Keep the existing classification loop (today's lines ~79-102) unchanged** — it still
populates `cost` for ratio-gate-passing GTs and tracks `pack_ambiguous_gt_indices` /
`far_fn_gt_indices` exactly as today.

**2. Run stage 1** exactly as today: `stage1_pairs = _linear_sum_assignment(cost)`,
`matched_pred_idx`/`matched_gt_idx` built from it.

**3. Compute `competed_away_gt_indices` here, right after stage 1**, using only stage-1's
`matched_gt_idx` — same formula as today, just make sure it's evaluated before stage 2 merges
anything in, so its meaning (a *clear* GT that lost its top candidate to a better-fitting GT)
doesn't shift.

**4. Add stage 2.** All of `pack_ambiguous_gt_indices` are guaranteed absent from
`matched_gt_idx` after stage 1 (they never got a cost cell below `_GATE_INF`), so no need to
subtract anything there. Build a second cost matrix over `leftover_pred_indices = [i for i in
range(n_pred) if i not in matched_pred_idx]` (rows) × `ambiguous_gt_list = sorted(pack_ambiguous_gt_indices)`
(cols): `cost2[row][col] = dist_m[i][j] / _reliability_for_pred(preds[i],
reliability_by_cluster_id)` wherever `dist_m[i][j] <= max_match_dist_m`, else leave at
`_GATE_INF` (guard the empty-list case — skip stage 2 entirely if either list is empty). Run
`_linear_sum_assignment(cost2)` and map the returned (row, col) indices back through
`leftover_pred_indices`/`ambiguous_gt_list` to get `stage2_pairs` in original `(i, j)` index
space.

**5. Merge state:** for each `(i, j)` in `stage2_pairs`, write `cost[i][j] =
dist_m[i][j] / _reliability_for_pred(preds[i], reliability_by_cluster_id)` into the **original**
cost matrix too (so the existing `matches`-building loop's `cost[i][j]` lookup keeps working
unchanged for stage-2 pairs). Then `all_pairs = stage1_pairs + stage2_pairs`,
`matched_pred_idx |= {i for i, _ in stage2_pairs}`, `matched_gt_idx |= {j for _, j in
stage2_pairs}`. Keep a `stage1_pairs_set = set(stage1_pairs)` for status-tagging.

**6. `matches` construction:** iterate `all_pairs` instead of `primary_pairs`. Everything else
in the loop body is unchanged **except** `"association_status"`, which becomes
`"clear_match"` if `(i, j) in stage1_pairs_set` else `"resolved_after_narrowing"`.

**7. `ambiguous_gts` construction:** the still-ambiguous set is `pack_ambiguous_gt_indices -
{j for _, j in stage2_pairs}`. Final `ambiguous_gt_indices = (still_ambiguous |
competed_away_gt_indices) - matched_gt_idx - far_fn_gt_indices` (same shape as today, just
built from the updated pieces). For each `j` in this set:
   - If `j` was in `still_ambiguous`: `competing_cluster_ids` should be the subset of the
     *original* ratio-gate-window candidates (same `d1 * ratio_gate` window logic as today)
     that are **also** currently in `leftover_pred_indices` (i.e. still unclaimed after both
     stages) — not the stale full original list.
   - If `j` was only in `competed_away_gt_indices` (never ambiguous, just lost its clear match):
     keep today's existing logic unchanged (nearest × `ratio_gate` window, no leftover
     filtering — this GT was never in the ambiguous pool, don't change its reported shape).

**8. `false_positives` and `duplicates`:** both currently key off `matched_pred_idx`/
`matched_gt_idx` — no code change needed here beyond the fact that those sets now include
stage-2 results (steps 5 already handles this), but double-check both blocks still read the
merged sets, not a stage-1-only snapshot.

**9. Everything else** (`false_negatives`, `possible_merges`, `errors`/`all_radii`/metrics/score
computation, `eval_params`, `excluded_low_reliability`, reliability filtering) — **unchanged**,
they don't depend on which stage a match came from.

## Out Of Scope

- Do not touch `_cluster_reliability`, `_reliability_for_pred`, the `excluded`/reliability
  filtering block, or anything from `FD-RA1`/`FD-RA2`.
- Do not touch Test 1 / `geoUtils.ts` / any frontend code — this is backend-only.
- Do not touch the localization engine or Re-ID engine.
- Do not add new parameters or API fields — `ratio_gate`/`max_match_dist_m` govern both stages,
  unchanged in meaning.
- Do not iterate ambiguous GTs one at a time with ad-hoc "if only one candidate left, assign
  it" logic — use a second joint `_linear_sum_assignment` call as specified, so multi-GT chains
  resolve correctly (see the FD-S3 amendment's worked example).

## Acceptance Criteria

- [ ] Stage 1 behavior is bit-for-bit unchanged when there are no ambiguous GTs (verify against
      a fixture with only clear matches — same `matches`, same scores, same `false_positives`
      as before this change)
- [ ] An ambiguous GT whose competing cluster(s) are otherwise unclaimed after stage 1 becomes
      a match with `association_status: "resolved_after_narrowing"`
- [ ] The multi-GT-chain scenario from the FD-S3 amendment (GT-A ambiguous {X,Y}, GT-B
      ambiguous {X,Z}, Y and Z claimed elsewhere in stage 1, X contested between A and B in
      stage 2) resolves via optimal assignment — whichever of A/B has lower cost for X gets it,
      the other remains in `ambiguous_gts` (or wherever it correctly lands, e.g. still
      unmatched) rather than both spuriously "matching" X or the tie being resolved by
      insertion order
- [ ] A GT still ambiguous after stage 2 reports a **narrowed** `competing_cluster_ids` (only
      currently-unclaimed candidates), not the original full list
- [ ] `competed_away_gt_indices` semantics unchanged — still computed from stage-1-only state
- [ ] `false_positives`/`duplicates` reflect the final (stage-1 ∪ stage-2) matched sets
- [ ] New test file (e.g. `backend/tests/unit/test_result_analysis_two_stage_matching.py`)
      covering at minimum:
  - [ ] No-ambiguity fixture: identical output to pre-change behavior
  - [ ] Simple rescue: one ambiguous GT, one of its two candidates claimed by a different clear
        GT, the other left free → ambiguous GT matches the free one,
        `association_status == "resolved_after_narrowing"`
  - [ ] Multi-GT chain: the two-ambiguous-GT-one-shared-leftover-cluster scenario — assert
        exactly one of the two GTs matches, the other does not spuriously match too
  - [ ] Genuinely irreducible ambiguity: two candidates remain unclaimed and still too close in
        distance/cost to resolve — GT stays in `ambiguous_gts` with both still listed in
        `competing_cluster_ids`
  - [ ] Narrowed reporting: an ambiguous GT with 3 original candidates, 2 of which get claimed
        by other GTs, 1 remains but distance is beyond `max_match_dist_m` (so it still can't
        match) → `competing_cluster_ids` is empty or reflects only truly-still-viable
        candidates, not the stale original 3
- [ ] `cd backend && pytest` passes, no regressions beyond the pre-existing 9 unrelated
      failures (note: `test_evaluate_pack_produces_ambiguous_gt` and
      `test_evaluate_three_close_clusters_produces_ambiguous_gt` are already in that failing-9
      set for unrelated reasons — check whether your change happens to fix them as a side
      effect or not, and note either way in `.ai/codex_result.md`, but do not treat fixing them
      as a requirement)

## Constraints

- Do not invent behavior beyond what the FD-S3 amendment specifies.
- Preserve module boundaries.
- Match existing code style/patterns in the file (list/set comprehensions, naming, etc.).

## Tests To Run

- `cd backend && pytest`

## Founder Decisions Needed

None — the FD-S3 amendment already covers this change. If the multi-GT-chain tie-break
produces a result that seems arbitrary (e.g. two candidates with genuinely identical cost),
that's expected — Hungarian assignment picks a deterministic but not specially-justified winner
in exact ties, same as it already does for stage-1 matches today. Don't try to add extra
tie-breaking logic beyond what's already there; flag it in `.ai/codex_result.md` if it seems
worth a follow-up decision.
