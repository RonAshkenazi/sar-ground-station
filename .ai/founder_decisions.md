# Founder Decisions — Open Questions

This file aggregates every unanswered question that requires a founder decision before it can
be committed to code or the final report. Walk through these in order; each resolved decision
updates the code via a sprint task or handoff.

**Status key:** 🔴 Open · 🟡 Pre-filled (confirm or override) · ✅ Resolved (Sprint 01)

---

## Category 1 — Re-ID Algorithm Constants

These drive how MAC addresses are associated. Wrong values mean either no associations at all
(too strict) or false merges (too loose).

---

### FD-R1 · Association threshold — ✅ Resolved

**Decision: `0.80`** — UI-tunable, options: `0.75` / `0.80` / `0.90`

---

### FD-R2 · Sequence gap threshold — ✅ Resolved

**Decision: `64`** — UI-tunable, options: `50` / `64` / `128`

---

### FD-R3 · Maximum time gap between associated probes — ✅ Resolved

**Decision: `30 sec`** — UI-tunable, options: `10` / `30` / `60` sec

---

### FD-R4 · Low-confidence associations — ✅ Resolved

**Decision:** Any MAC that ends up unassociated (singleton after Bleach clustering) is
grouped into a single output cluster with `cluster_id = "noise"` and `cluster_type = "noise"`.
This keeps the map clean — operators see meaningful clusters + one noise cluster, not
dozens of singletons.

---

### FD-R5 · Burst grouping window — ✅ Resolved

**Decision: `60 sec`** — UI-tunable, options: `30` / `60` / `120` sec
Note: source file missing (pairing.pyc only); value from IMPLEMENTATION_SUMMARY prose.

---

### FD-R6 · Conflict resolution mode (`REID-02`) — ✅ Resolved

**Decision:** Default `conflict_resolution_mode` changes from `greedy_best_valid_match` to
`optimal_assignment` (bipartite maximum-weight matching, one predecessor/one successor per
dynamic unit, restricted to candidates already above `association_threshold`). Same weights,
same threshold, same candidate generation — only *which* above-threshold edges get accepted
when several compete for the same unit changes. `greedy_best_valid_match` stays in the code
as a legacy/reference mode, not exposed via API for now.

**Context:** Live investigation of a real field scan (`scan_S1`, 2026-08-10, operator carried
2 phones) found Re-ID splitting the session into 7 dynamic clusters. Root cause traced to
`_resolve_conflicts`: it sorts every candidate edge in the whole file by score and greedily
claims each one, so a unit with several valid above-threshold candidates can still end up
unmatched if all of them are claimed by other units first.

**Evidence:**
- One orphaned unit (`5e:62:09:c4:eb:89`, isolated as its own singleton cluster,
  `confidence: low`) had **13 candidate edges scoring 0.91–0.94** — all comfortably above the
  `0.80` threshold — yet none were accepted, including a 0.941-scoring edge to a MAC already
  inside the largest cluster.
- Re-running conflict resolution as a bipartite maximum-weight assignment (`scipy.optimize.
  linear_sum_assignment`), with every weight and the threshold left untouched, collapsed the
  same candidate scores from **7 dynamic clusters down to 2** — a single unbroken 36-MAC /
  349-row chain spanning the full scan with zero time overlap between consecutive MACs (one
  device, continuously rotating its MAC), plus one small 6-MAC / 10-row cluster.
- Also tested and **rejected**: raising `_REID_WIFI_FRAME_LEN_WEIGHT` (the operator's initial
  hypothesis). Every weight configuration tried that lowered the IE-fingerprint weight in
  favor of frame length made fragmentation dramatically worse (7 → 31 clusters), because
  frame length is a weak signal on this data — it varies by up to 20 bytes within a single
  device's own burst, almost as much as the gap seen between genuinely different devices.
  **The existing weights (0.75 / 0.20 / 0.10 / 0.05, sourced from the legacy Bleach
  implementation per `researcher_constants.md`) are unchanged by this decision.**

**Consequences:** `backend/app/modules/reid/engine.py::_resolve_conflicts` implementation
changes; `_REID_02_CONFLICT_RESOLUTION` constant value updates to reflect the new default;
`docs/Part B.md` §3.4 and Step 7 updated to match (done). No API/schema change, no weight
change, no change to any other pipeline stage.

---

## Category 2 — Enrichment Constants

---

### FD-E1 · PCAP matching time window — ✅ Resolved

> How many milliseconds on either side of a CSV row's timestamp to search for a matching
> PCAP frame?

**Decision: `1000 ms`**

---

### FD-E2 · PCAP match score threshold — ✅ Resolved

> What minimum combined score (time proximity + MAC identity + context) must a PCAP frame
> reach to be accepted as a match for a CSV row?

**Decision: `0.3`** — keep current heuristic; new-backend behavior, not in legacy.

---

## Category 2b — Calibration Constants

### CAL-07 · Minimum samples for fit warning — ✅ Resolved

**Decision: `10`** — warn "Low sample count" if fewer than 10 GPS+RSSI samples for the calibration MAC.

### CAL-08 · Minimum inlier ratio for fit warning — ✅ Resolved

**Decision: `0.70`** — warn "Low inlier ratio" if RANSAC inlier ratio falls below 70%.

---

## Category 3b — Result Analysis Constants

---

### FD-RA1 · Cluster reliability filter for GT matching (`RA-10`/`RA-11`/`RA-12`) — ✅ Resolved

**Decision:** Add a per-cluster **reliability score** to `evaluate()`, combining sample count
and uncertainty radius, used both to penalize a cluster's chance of winning a GT match and to
hard-exclude clusters that are too unreliable to be a real match candidate at all.

```
samples_term = min(1, num_samples / min_reliable_samples)        # RA-10, default 10
radius_term  = max(0, 1 - radius_m / max_uncertainty_radius_m)   # RA-11, default 40
reliability  = samples_term * radius_term                        # product, not weighted sum —
                                                                   # a cluster must be BOTH
                                                                   # well-sampled AND tight to
                                                                   # be trusted
```

- Clusters with `reliability < min_reliability_threshold` (RA-12, default `0.3`) are removed
  from the candidate pool entirely *before* matching — excluded from `dist_m`/cost
  construction, `matches`, `false_positives`, `duplicates`, and `possible_merges` alike. They
  are reported separately as a new `excluded_low_reliability` list in the `evaluate()` response
  (cluster_id, num_samples, radius_m, reliability) — **never silently dropped**.
- Clusters that pass the threshold still get their **matching cost inflated** proportional to
  unreliability (`cost = distance_m / reliability`) at the single point where a nearest-cluster
  cost is assigned to a GT column, so that when two candidate clusters are both within
  `max_match_dist_m` of the same GT point, the more reliable one wins the optimal assignment
  even if it's slightly farther away.
- `max_match_dist_m` gating and the `ratio_gate` ambiguity/pack-detection logic stay
  distance-only and are **not** touched by reliability — "too far away" and "too unreliable"
  are kept as distinct concepts.
- The existing `RA-05 score_weight_radius_size` / `s_radius` aggregate score term (median
  radius across *all* predictions) is **unchanged** — this decision does not touch it, to avoid
  double-penalizing the same signal. `median_radius_m` and `all_radii` keep including excluded
  clusters, so the diagnostic metric still reflects the full run, not just the trusted subset.

**Context:** Field observation that some clusters carry 40+ meter uncertainty radii — the
`evaluate()` engine already ships a `radius_reliability_note` admitting *"Current uncertainty
radii are not yet calibrated... should be treated as indicative only"* — so radius alone is a
weak signal. Combining it with sample count (a more direct measure of how much RF evidence
backs the estimate, same reasoning already used for `CAL-07`'s 10-sample calibration warning)
gives a materially more defensible filter than a radius-only cutoff.

**Defaults:** `min_reliable_samples = 10` (RA-10, mirrors `CAL-07`), `max_uncertainty_radius_m
= 40` (RA-11), `min_reliability_threshold = 0.3` (RA-12). All three UI-tunable, matching the
existing eval-param pattern (`ratio_gate`, `max_match_dist_m`, etc.).

**Consequences:** `backend/app/modules/result_analysis/engine.py::evaluate()` implementation
changes (new params, reliability calc, exclusion + cost inflation, new response field);
`backend/app/api/result_analysis.py` `EvaluateRequest` gains 3 new optional fields;
`frontend/src/pages/ResultAnalysisPage.tsx` gains 3 new tunable inputs plus a display for
`excluded_low_reliability`; `docs/Part B.md` §3.7 gains `RA-10`/`RA-11`/`RA-12`.

---

### FD-RA2 · Retire radius from FD-RA1; unify with a localization-stage gate (`LOC-16`) — ✅ Resolved

**Decision:** `RA-11 max_uncertainty_radius_m` is removed from the `evaluate()` reliability
formula. `FD-RA1`'s reliability score becomes samples-only:
`reliability = min(1, num_samples / min_reliable_samples)`, still compared against
`min_reliability_threshold` (`RA-12`), still evaluate()-only. In its place, a new **hard**
gate is added at the localization stage — `LOC-16 max_uncertainty_radius_m`, default `35` —
applied right after a cluster's `uncertainty_regions` are computed: a cluster whose primary
uncertainty radius exceeds it is converted to a failed cluster
(`failure_reason: "uncertainty_radius_too_large"`, radius attached for auditability), reusing
the same failed-cluster mechanism as `FD-L3`. This gets both "not visible" (map/Zone) and "not
a match candidate" (Result Analysis) for free, with no separate exclusion-list plumbing —
exactly the same pattern `FD-L3` already established.

**Context:** Operator request for a simple, visibility-aware radius cutoff (default 35m)
surfaced that `FD-RA1`'s existing `max_uncertainty_radius_m` (40m) already did something
similar but only as a soft term inside a sample-weighted score, evaluate()-only, with no
visibility effect — building a second, independent 35m cutoff alongside it would have left two
overlapping, confusing radius thresholds. Removing radius from `FD-RA1` and relocating it to
the localization stage (where visibility can actually be affected) gives one clean gate per
concern instead: "too few samples" (evaluate-only, `FD-RA1`) and "too much uncertainty"
(visibility + evaluate, this decision) are now fully independent.

**Default:** `max_uncertainty_radius_m = 35` (`LOC-16`), UI-tunable, same style as `LOC-14`/`LOC-15`.

**Consequences:** `backend/app/modules/result_analysis/engine.py::evaluate()` — remove
`max_uncertainty_radius_m` param and the `radius_term` from `_cluster_reliability`.
`backend/app/api/result_analysis.py` `EvaluateRequest` — remove `max_uncertainty_radius_m`
field. `backend/app/modules/localization/engine.py` — new `_LOC_16_MAX_UNCERTAINTY_RADIUS_M`
constant and gate in the main cluster loop, right after `_localize_cluster()` returns.
`backend/app/api/localization.py` — new optional field, threaded through the same way as
`LOC-14`/`LOC-15`. Frontend: the "Max radius" input moves out of
`ResultAnalysisPage.tsx`'s "Cluster reliability filter" section and into
`LocalizationPage.tsx`'s settings panel (plus the generic `localizationParams` rerun panel),
mirroring `LOC-14`/`LOC-15` exactly. `docs/Part B.md` §3.5 gains `LOC-16`; §3.7's `RA-11` entry
is marked superseded; §5.1 Step 3 gains a mention alongside the movement-gate note.

---

## Category 3 — Localization Constants

---

### FD-L1 · Dynamic sigma alpha — ✅ Resolved

**Decision: `0.05`** — UI-tunable, options: `0.0` / `0.05` / `0.10`

---

### FD-L2 · Localization confidence cutoff — ✅ Resolved

**Decision: `0.50`** — UI-tunable, options: `0.40` / `0.50` / `0.60`

---

### FD-L3 · Minimum movement gate for cluster validity (`LOC-14`/`LOC-15`) — ✅ Resolved

**Decision:** Add a hard pass/fail gate to Step 3 (Cluster Validation) requiring genuine
scanner movement across a cluster's samples, on top of the existing 3-sample minimum:

```
time_gap_sec = last_sample_time - first_sample_time     (raw cluster_rows, pre-RANSAC)
baseline_m   = max pairwise haversine distance between scanner GPS positions across
               the cluster's raw samples

passes gate  ⟺  time_gap_sec >= min_time_gap_sec (LOC-14, default 30s)
             AND baseline_m   >= min_baseline_m   (LOC-15, default 5m)
```

Both conditions required (AND) — each alone has a blind spot the other covers: a time-only
gate false-passes a hovering platform that racks up seconds without moving; a distance-only
gate doesn't need help but combining costs nothing.

A cluster failing the gate is treated exactly like today's "insufficient samples" failure —
`status: "failed"`, `failure_reason: "insufficient_movement"`, with `time_gap_sec` and
`baseline_m` attached to the failed-cluster object for auditability. Because failed clusters
are already excluded from both `extract_predictions_from_localization_result` (Result
Analysis matching) and the frontend's `status === 'success'` visibility filters, this
automatically satisfies "not counted to show or to evaluate" **with no new plumbing** on
either the Result Analysis or frontend-filtering side — it reuses the existing failed-cluster
mechanism rather than inventing a parallel one.

**Context:** Live investigation of cluster `88:a2:9e:09:94:05` (field scan, `scan_S3`, 2026)
found `uncertainty_radius_m = 2.13` reported with high apparent confidence, despite all 11 raw
samples sharing the *exact same* scanner GPS fix (zero baseline) across a ~0.56 second burst.
Traced the mechanism: with zero GPS movement, RANSAC's distance-to-candidate-center collapses
to a constant 1m floor for every iteration, so `predicted_rssi` becomes a fixed value and
"inlier" selection degenerates into "which raw readings happen to sit within the dB threshold
of that one number" — 7 of 11 did, matching the reported `sample_count`. The resulting
~1.3m-implied-distance ring around the single fixed vantage point has nowhere to spread
because it's smaller than the grid cell size, so it numerically collapses into 1-2 adjacent
cells next to the scanner's own position — reading as high confidence when it's actually zero
directional information. This cluster scored `reliability ≈ 0.66` under `FD-RA1` (comfortable
sample count + small radius), confirming FD-RA1 alone cannot catch this failure mode — it has
no concept of geometric/angular diversity, only sample count and radius size.

**Defaults:** `min_time_gap_sec = 30` (LOC-14), `min_baseline_m = 5` (LOC-15) — chosen to
stay meaningfully above the default `LOC-06 grid_resolution_m = 2m`; a baseline smaller than
the grid cell size can't be geometrically resolved regardless of threshold. Both UI-tunable.

**Consequences:** Unlike `FD-RA1` (a free Result-Analysis-only re-evaluation), this requires
raw per-row GPS/timestamps that only exist at the localization stage, so `min_time_gap_sec`/
`min_baseline_m` are **Localization parameters** — changing them triggers a full localization
rerun (→ cascades to Result Analysis), not a lightweight re-evaluate. `backend/app/modules/
localization/engine.py` gains the gate in the Step 3 loop; `_failed_cluster` is generalized to
accept a `failure_reason` and extra diagnostic fields; `backend/app/api/localization.py`
`LocalizationRunRequest` gains 2 new optional fields; `frontend/src/pages/LocalizationPage.tsx`
and the rerun panel in `ResultAnalysisPage.tsx` gain 2 new tunable inputs; `docs/Part B.md`
§3.5 gains `LOC-14`/`LOC-15` and §5.1 Step 3 documents the gate.

---

### FD-L4 · De-duplicate same-component candidate peaks — ✅ Resolved

**Decision:** In Step 8 (Detect and Retain Candidate Peaks), de-duplicate local maxima that
belong to the same connected `uncertainty_participation_floor`-flood-filled component *before*
building individual uncertainty regions or merging. Iterate candidates in their existing
strongest-first order; for each, compute its participating component via the flood-fill already
used later for region-building (`_peak_participating_indices`); skip any candidate whose cell
already belongs to a stronger, previously-kept peak's component; otherwise keep it and mark its
whole component as covered. Cap at 3 as before, now applied post-dedup.

**Explicitly preserved, unchanged:** two candidate peaks whose components are genuinely
disjoint (a real posterior valley between them, dropping below the participation floor) are
untouched by this decision — they remain independent, each still gets its own uncertainty
region via Step 9, and `_merge_regions` still combines them into a wider reported circle when
those regions overlap, per the original design intent: multiple genuinely separated strong
peaks represent a real chance of multiple distinct targets, and that signal must not be lost.
This decision only removes candidates that were never actually separate to begin with.

**Context:** `FD-RA2`'s new `LOC-16` radius gate (default 35m) started excluding clusters whose
reported radius was inflated not by genuine multi-target ambiguity but by grid-discretization
noise on one broad, gently-sloped posterior hill — confirmed on 3 real clusters from `scan_S2`,
including the session's own calibration MAC (`2c:59:8a:58:95:c1`, 76 samples): all 3 had 2-3
near-tied candidate peaks (posterior 0.94-1.0) whose flood-filled participating components were
**bit-for-bit identical** across all peaks in each cluster — proof they're one feature, not
several:

| Cluster | Samples | Peak values | Merged (buggy) radius | Peak-0-only radius after fix |
|---|---:|---|---:|---:|
| `2c:59:8a:58:95:c1` | 76 | 1.000 / 0.9996 / 0.9562 | 39.0m | **26.9m — now passes `LOC-16`** |
| `1` | 140 | 1.000 / 0.9999 / 0.9837 | 130.4m | 60.4m — still fails `LOC-16`, honestly |
| `8` | 182 | 1.000 / 0.9716 / 0.9351 | 67.3m | 42.3m — still fails `LOC-16`, honestly |

Note the expected outcome is not that all three flip to passing — `1` and `8`'s own single
strongest peak genuinely has a wide spread even once contamination is removed (weak RSSI
geometry for those links), so they correctly remain excluded. Only `2c:59` was purely a
contamination artifact.

**Consequences:** `backend/app/modules/localization/engine.py::_localize_cluster` — peak
candidate list is de-duplicated between `_find_peaks` and the `_uncertainty_region`/
`_merge_regions` calls. No parameter changes, no new API fields, no frontend changes — this is
a correctness fix to existing behavior, not a new tunable. `docs/Part B.md` §5.1 Step 8
documents the de-duplication rule.

---

## Category 4 — Re-ID Algorithm Approach (Final Report)

---

### FD-A1 · LR classifier vs Bleach heuristic — needs report justification

> The preliminary design report (pre-2026-078) described a Logistic Regression classifier
> for Re-ID. The current implementation uses the Bleach unsupervised algorithm instead.
> This deviation must be explicitly addressed in the final report.

**Context:** LR requires labeled training data (known MAC-to-person pairs). In SAR field
deployment, no such labeled data exists ahead of time. Bleach is unsupervised and deployable
without training.

**This is not a code decision** — the code already uses Bleach. This is a report-writing decision.

**What do you want the final report to say?**

- A: "The LR approach was evaluated and rejected in favor of Bleach due to the training-data
  requirement. Bleach is better suited to unsupervised SAR field deployment." (Recommended)
- B: "The LR approach remains a planned future enhancement; Bleach is the MVP implementation."
- C: Other framing — describe: ______

**→ Choose framing: ______**

---

## Category 5 — Scope & Architecture Decisions

---

### FD-S1 · Data offload UI — ✅ Resolved

**Decision: No.** `DATA/` is populated manually. Document in final report that file transfer is out of scope; ground station processes data only.

---

### FD-S2 · BLE pipeline — ✅ Resolved

**Decision: Future milestone.** Wi-Fi only for this submission. BLE stubs remain; document as planned future work in the report. Full BLE pipeline to be built in a later sprint.

---

### FD-S3 · Result Analysis page — ✅ Resolved

**Decision: Yes — required.** Build the Result Analysis page for the 20-run validation protocol.

**Score weights (RA-Q1):** Containment `0.40` / Euclidean distance `0.30` / Emitter count `0.20` / Radius size `0.10`. All four weights are operator-adjustable.

**GT matching (RA-Q2):** Gap-aware nearest-neighbor. For each GT point find d1 (nearest peak) and d2 (second-nearest). If d2−d1 ≥ gap_threshold → unambiguous match. If two GT points both match the same cluster → emitter count fail for that pair. Gap threshold: **TBD — pending founder confirmation (suggested 8m).**

**Rerun from Result Analysis (RA-Q3):** Yes — operator can rerun any stage (Re-ID, Localization, or both) with updated parameters from the Result Analysis page. Follows existing rerun propagation rules from Part B Section 4.

**Amendment — Test 1 area score bug fix (2026-08-13):** The Test 1 "Area" sub-score computed
`circleArea` as a plain sum of each cluster's zone-clipped circle area
(`Σ circleIntersectionAreaM2(...)`), which double-counts area where two or more clusters'
circles overlap — observed producing nonsensical values like 216% of zone area on a real scan.
Fixed to a proper **union** area: rasterize the zone's own bounding box and count a grid cell
once if it falls inside *any* qualifying circle AND inside the zone polygon (extends the
existing `circleIntersectionAreaM2` grid-sampling approach from one circle to a union of
circles, same technique, no new dependencies). This guarantees, by construction rather than by
clamping: (a) overlapping circles' shared area is counted once, and (b) total covered area can
never exceed the zone's own area, so `areaRatio` is now mathematically bounded to `[0, 1]`.
`nCircles`/the Count sub-score is unaffected — this only touches the Area sub-score's
`circleArea` computation. New function `unionCircleAreaWithinPolygonM2` in
`frontend/src/utils/geoUtils.ts`; `sumCircleAreasM2` (already unused in the actual page —
`ResultAnalysisPage.tsx` was calling `circleIntersectionAreaM2` per-circle, not
`sumCircleAreasM2`) is left in place but should not be used going forward.

**Amendment — two-stage GT matching for ambiguous GTs (2026-08-14):** `RA-Q2`'s gap-aware
matching today gives an ambiguous GT (nearest and second-nearest cluster too close in distance,
`d2/d1 < ratio_gate`) **zero** chance to match anything — it never enters the assignment
problem, even when one of its close candidates turns out to be completely unclaimed by every
other GT. Fixed with a second optimal-assignment pass instead of a hand-rolled narrowing loop:

- **Stage 1 (unchanged):** exactly today's logic — GTs that clear `ratio_gate` get cost cells
  for every candidate within `max_match_dist_m`, resolved via the existing
  `_linear_sum_assignment`. `competed_away_gt_indices` (a clear GT whose top candidate got
  claimed by a better-fitting GT) is computed here, using only stage-1's matched set, so its
  meaning is unchanged.
- **Stage 2 (new):** for each GT that was ambiguous in stage 1, recompute its ratio-gate
  candidate window restricted to clusters **not already claimed in stage 1**. Only GTs whose
  restricted window has narrowed to **exactly one** remaining candidate enter the stage-2
  assignment problem at all — a GT that still has 2+ genuinely viable leftover candidates stays
  ambiguous rather than being force-resolved by cost. (An earlier draft of this decision
  proposed feeding *every* originally-ambiguous GT into stage 2 regardless of remaining count;
  that would let Hungarian break real, irreducible ties by cost alone — reporting a confident
  match where none is warranted. The `==1` gate is the correct reading of "if only one stays,
  it's a match": more than one staying means it isn't.) GTs that individually narrow to exactly
  one candidate then go into a **joint** `_linear_sum_assignment` over just that reduced
  sub-problem — not resolved one GT at a time — so multi-GT chains still work correctly (e.g.
  GT-A narrows to {X}, GT-B narrows to {X} too, because Y and Z were claimed elsewhere in stage
  1: both entered stage 2, and the joint assignment awards X to whichever fits better, leaving
  the other genuinely unmatched — a one-at-a-time rule applied per GT independently could not
  express that contest correctly).
- Stage-2 matches carry `association_status: "resolved_after_narrowing"` (vs. stage-1's
  `"clear_match"`) — visible in the data, never silently reclassified.
- GTs still ambiguous after stage 2 report their **narrowed** `competing_cluster_ids` (clusters
  within the original ratio-gate window that are *still unclaimed* after both stages), not the
  stale original set — more accurate to a researcher reading the result afterward.
- `false_positives`/`duplicates` are computed from the **final** (stage-1 ∪ stage-2) matched
  sets, so a cluster correctly rescued in stage 2 stops being miscounted as a false positive.
- `possible_merges` is unaffected (distance-only, not matching-state-dependent).

Scope: `backend/app/modules/result_analysis/engine.py::evaluate()` only — no new parameters,
no API changes, no changes to `FD-RA1`/`FD-RA2` reliability filtering, Test 1, or any
localization-stage code.

---

### FD-S4 · Final validation — ✅ Resolved

**Decision: Field experiments after build is complete.** No validation sprint until the full pipeline is working and stable. Date TBD.

---

## Category 6 — Resolved (Sprint 01 — no action needed)

These were decided before Sprint 01. Listed here for completeness.

| # | Decision | Resolution |
|---|---|---|
| ✅ S1-1 | Nested scan folders | Top-level only; no recursion |
| ✅ S1-2 | Mode detection from folder name | `"ble"` → BLE; `"scan"` → Wi-Fi; else unknown |
| ✅ S1-3 | Artifact naming | New pipeline: UPPERCASE (`_ENRICHED.csv`); legacy: recognized but not written |
| ✅ S1-4 | Port configuration | Env-var driven; documented in README |

---

## How to Use This File

In the next session, say: **"Open `founder_decisions.md` and let's resolve the open questions."**

I will walk through each 🔴 Open and 🟡 Pre-filled item in sequence and update the file
as you answer. Once all items have a confirmed answer, I will write updated handoffs and
update `decisions_pending.md` to close them out.

**Open decisions remaining:** 10 (6 algorithm/constants + 4 scope)
