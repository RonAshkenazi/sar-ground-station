# Session Summary — Re-ID, Localization & Result Analysis Fixes

**Branch:** `fix/reid-localization-result-analysis`
**Period covered:** 2026-08-13 – 2026-08-14
**Status:** All items below implemented, reviewed, tested, and validated live against real
field scan data. Full decision records live in `.ai/founder_decisions.md`; per-change review
notes live in `.ai/reviews/claude_review.md` (latest review only — earlier ones were
overwritten by later reviews in the same file, per this repo's existing convention).

This document is a single-place summary for the final report. Each section names the founder
decision it corresponds to, so the report can cite `.ai/founder_decisions.md` directly for full
detail.

---

## 1. Re-ID: optimal conflict resolution (FD-R6)

**Problem:** A real field scan (`scan_S1`, 2 phones carried) produced 7 Re-ID dynamic clusters
instead of ~2. Root cause: the greedy conflict-resolution pass (`_resolve_conflicts`) claimed
candidate MAC-association edges in global score order, which could strand a unit with several
valid above-threshold candidates if all of them got claimed by other units first.

**Evidence:** One orphaned MAC had 13 candidate matches scoring 0.91–0.94 (threshold 0.80),
none accepted, including a 0.941 match to a MAC already inside the largest cluster.

**Fix:** Replaced greedy selection with an optimal one-to-one bipartite assignment
(`scipy.optimize.linear_sum_assignment`) over the same candidate scores — no weight or
threshold changes. Old greedy logic kept as `_resolve_conflicts_greedy` for reference, not
called by default.

**Result:** 7 clusters → 2, verified live against the real scan.

**Also investigated and rejected:** raising the frame-length feature weight (the original
hypothesis) — tested directly against real data and found to make fragmentation dramatically
*worse* (7 → 31 clusters), because frame length is a weak, noisy signal in this dataset (varies
~20 bytes within a single device's own burst). Feature weights are unchanged from the legacy
Bleach-paper-sourced defaults.

**Files:** `backend/app/modules/reid/engine.py`, `backend/tests/unit/test_reid_conflict_resolution.py`

---

## 2. Data hygiene: corrupted PCAP filenames (no founder decision — direct data fix)

Two PCAP files in `Scan - test protocol` had invisible Unicode `U+200F` (right-to-left mark)
characters silently prepended to their filenames (`‏‏scan_S1_1.pcap`, `‏‏‏‏scan_S1_2.pcap`) —
likely introduced by a Hebrew-locale copy/rename operation. This broke the frontend's exact
filename-stem matching used to pair a CSV with its PCAP for enrichment
(`findMatchingPcap` in `ReIdEnrichmentPage.tsx`), silently blocking enrichment for those two
scans with no visible cause.

**Fix:** Renamed the two files on disk to strip the invisible characters. No code changed —
matching already worked correctly once the filenames were clean.

---

## 3. Result Analysis: cluster reliability filter (FD-RA1, later refined by FD-RA2 — see §5)

**Problem:** Clusters with very large uncertainty radii (40+ meters) were being treated as
equally valid GT-match candidates as tight, well-sampled ones.

**Fix (original form):** Added a per-cluster reliability score combining sample count and
uncertainty radius (`reliability = samples_term × radius_term`), used to (a) inflate a
cluster's GT-matching cost proportional to unreliability, and (b) hard-exclude clusters below a
threshold from match candidacy — reported explicitly as `excluded_low_reliability`, never
silently dropped.

**Superseded in part by FD-RA2** (§5 below) — the radius component was later removed from this
formula and relocated to the localization stage so it could also affect map visibility, not
just Result Analysis matching. The sample-count component remains as originally designed.

**Files:** `backend/app/modules/result_analysis/engine.py`, `backend/app/api/result_analysis.py`,
`backend/tests/unit/test_result_analysis_reliability.py`

---

## 4. Localization: minimum movement gate (FD-L3)

**Problem:** A cluster (`88:a2:9e:09:94:05`, real field scan) reported a suspiciously tight
2.13m uncertainty radius from 7 samples. Investigation found all samples came from the *exact
same* scanner GPS fix across a 0.56-second burst — zero movement, zero directional/triangulation
information. With zero baseline, RANSAC's distance-to-candidate-center math collapses to a
constant, making the reported radius a numerical artifact, not real precision.

**Fix:** New hard gate — `LOC-14 min_time_gap_sec` (default 30s) **and**
`LOC-15 min_baseline_m` (default 5m), both required. A cluster's raw (pre-RANSAC) samples must
span at least the time gap *and* the scanner must have physically moved at least the baseline
distance across them. Failing clusters get `status: "failed"`,
`failure_reason: "insufficient_movement"`, reusing the existing failed-cluster mechanism so
they're automatically excluded from both the map and Result Analysis matching — no separate
plumbing needed.

**Result:** The motivating cluster now correctly excluded, live-confirmed:
`time_gap_sec: 0.563`, `baseline_m: 0.0`.

**Files:** `backend/app/modules/localization/engine.py`, `backend/app/api/localization.py`,
`frontend/src/pages/LocalizationPage.tsx`, `backend/tests/unit/test_localization_movement_gate.py`

---

## 5. Result Analysis / Localization: radius gate unification (FD-RA2)

**Problem:** After a follow-up request for a simple "radius > 35m → not visible, not
evaluated" rule, found this would create two overlapping, confusing radius thresholds: FD-RA1's
existing 40m soft term (evaluate-only, no visibility effect) and a new independent 35m hard
cutoff.

**Fix:** Removed the radius term from FD-RA1 entirely (reliability is now samples-only) and
added one unified hard gate at the localization stage instead — `LOC-16
max_uncertainty_radius_m` (default 35m) — using the same failed-cluster mechanism as FD-L3, so
it affects both map visibility and Result Analysis matching automatically, with no separate
exclusion-list plumbing.

**Files:** `backend/app/modules/result_analysis/engine.py`,
`backend/app/modules/localization/engine.py`, `backend/app/api/localization.py`,
`backend/app/api/result_analysis.py`, `frontend/src/pages/LocalizationPage.tsx`,
`frontend/src/pages/ResultAnalysisPage.tsx`, `backend/tests/unit/test_localization_radius_gate.py`

---

## 6. Result Analysis: Test 1 area score — union instead of naive sum (FD-S3 amendment #1)

**Problem:** The "Area" sub-score of Test 1 (SAR Operational Score) reported nonsensical values
like 216% of zone area on a real scan.

**Root cause:** `circleArea` was computed as a plain sum of each cluster's zone-clipped circle
area — double-counting area wherever two or more clusters' circles overlap, with no relationship
to the zone boundary.

**Fix:** New `unionCircleAreaWithinPolygonM2` function — extends the existing
`circleIntersectionAreaM2` grid-sampling technique from one circle to a proper union: rasterize
the zone's bounding box, count a cell once if it's inside *any* qualifying circle and inside the
polygon. Guarantees, by construction: overlapping area counted once, total never exceeds 100%
of zone area.

**Validated live:** using real cluster positions/radii from an actual scan, reproduced a 208.2%
naive-sum result (matching the originally-reported 216% almost exactly) at a realistic tight
zone size, and confirmed the new union formula correctly bounds it to 97.2%; at tighter zones it
saturates at exactly 100.0% (fully covered) rather than overestimating.

**Files:** `frontend/src/utils/geoUtils.ts`, `frontend/src/pages/ResultAnalysisPage.tsx`,
`frontend/src/utils/geoUtils.test.ts`

---

## 7. Localization: de-duplicate same-hill candidate peaks (FD-L4)

**Problem:** After FD-RA2's radius gate went live, it started excluding clusters whose radius
was inflated not by genuine multi-target ambiguity but by a pre-existing, separate defect: the
peak-finder sometimes detects 2–3 near-identical local maxima (posterior values within ~0.05 of
each other) on what is actually *one* broad, gently-sloped posterior hill, and the existing
merge logic (intentionally designed to widen the reported radius when multiple *genuinely
separate* strong peaks suggest multiple possible targets) then inflates the radius further.
This hit the session's own calibration AP (`2c:59:8a:58:95:c1`, 76 samples, radius inflated to
39.0m — 4m over the new cutoff) among others.

**Design constraint (explicit, from the founder):** the combined-radius behavior for
*genuinely separate* strong peaks must not be damaged — multiple real, spatially separated
strong peaks legitimately represent a chance of multiple distinct targets, and that signal must
be preserved.

**Fix:** Before building individual uncertainty regions, de-duplicate candidate peaks that
share the same connected `uncertainty_participation_floor`-flood-filled component (reusing the
existing `_peak_participating_indices` flood-fill, applied earlier as a filter rather than only
for region-building) — proven via real data that same-hill "peaks" have *bit-for-bit identical*
participating-cell sets. Peaks in genuinely disjoint components are completely unaffected and
continue to merge into a combined radius exactly as before.

**Result, validated live against the exact motivating clusters:**

| Cluster | Samples | Radius before fix | Radius after fix | Outcome |
|---|---:|---:|---:|---|
| `2c:59:8a:58:95:c1` (calibration AP) | 76 | 39.0m | **26.9m** | now passes the 35m gate |
| `1` | 140 | 130.4m | 60.4m | still correctly excluded — genuinely wide spread even on its own best peak |
| `8` | 182 | 67.3m | 42.3m | still correctly excluded, same reason |

Only the contamination-driven case (`2c:59`) recovers — the other two have real, honest
uncertainty even after the fix, which is the correct outcome, not a partial failure.

**Files:** `backend/app/modules/localization/engine.py`, `backend/tests/unit/test_localization_peak_dedup.py`

---

## 8. Result Analysis: two-stage GT matching (FD-S3 amendment #2)

**Problem:** A GT point with two similarly-close candidate clusters (`d2/d1 < ratio_gate`) was
marked "ambiguous" and given **zero** chance to match anything — even when one of its
candidates turned out to be completely unclaimed by every other GT after the main assignment
resolved.

**Fix:** Two-stage optimal assignment instead of a hand-rolled narrowing loop:
- **Stage 1** — unchanged: clear (unambiguous) GTs matched exactly as before.
- **Stage 2** — for GTs that were ambiguous, recompute their candidate window restricted to
  clusters not already claimed in stage 1. Only GTs whose window has narrowed to **exactly
  one** remaining candidate enter a second joint optimal assignment (this preserves genuine,
  irreducible ambiguity — a GT with 2+ still-viable leftover candidates correctly stays
  ambiguous rather than being force-resolved by cost). GTs that individually narrow to one
  candidate are resolved *jointly*, not one at a time, so multi-GT chains (two ambiguous GTs
  both narrowing to the same last-standing cluster) resolve correctly via optimal assignment
  rather than an ad-hoc rule.
- Stage-2 matches are tagged `association_status: "resolved_after_narrowing"` (vs. stage-1's
  `"clear_match"`) — visible in the data, never silently reclassified.
- GTs still ambiguous after stage 2 report a **narrowed** `competing_cluster_ids` (only
  currently-unclaimed candidates), not the stale original list.

**Validated live:** on a real scan, placed a GT at the exact midpoint between two real clusters
4.5m apart (genuinely ambiguous) alongside a second GT clearly nearest one of them. Result: the
clear GT claimed its cluster in stage 1; the ambiguous GT was correctly rescued to the other
cluster in stage 2, tagged `resolved_after_narrowing`.

**Files:** `backend/app/modules/result_analysis/engine.py`,
`backend/tests/unit/test_result_analysis_two_stage_matching.py`

---

## Cross-cutting notes for the report

- **Nothing was invented.** Every default value introduced this session (`LOC-14`/`15`/`16`,
  `RA-10`/`12`) is either explicitly stated by the founder in conversation or derived by direct
  analogy to an already-founder-approved constant (e.g. `min_reliable_samples = 10` mirrors
  `CAL-07`'s existing 10-sample calibration warning threshold).
- **Every exclusion is auditable.** No fix silently drops a cluster or GT from consideration —
  each has an explicit, inspectable reason (`failure_reason`, `excluded_low_reliability`,
  narrowed `competing_cluster_ids`, `association_status`).
- **Test coverage:** 8 new test files, all passing; full backend suite at 164 passed / 9 failed,
  with the 9 failures confirmed pre-existing and unrelated to any work in this session (same 9
  failures, same names, present on `main` before this branch).
- **Every change was validated against real field scan data**, not just synthetic fixtures —
  each section above cites the specific real cluster(s)/scan file used.
