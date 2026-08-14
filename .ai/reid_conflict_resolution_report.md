# Re-ID Over-Segmentation: Root Cause and Fix (FD-R6)

**Scope:** Re-ID (MOD-008) association / conflict-resolution stage
**Trigger:** Field scan `scan_S1` (`Scan - test protocol`, 2026-08-10) — 2 phones carried during
collection, but Re-ID output showed 8 dynamic clusters
**Related:** `.ai/founder_decisions.md` → FD-R6, `docs/Part B.md` §3.4 / Step 7
**Status as of this report:** Implemented, reviewed, and validated live. See §7.

---

## 1. Problem

`scan_S1` was collected with exactly 2 Wi-Fi devices present in the field. The Re-ID stage
(Bleach-style MAC-rotation association) produced **8 dynamic clusters** instead of the
expected ~2, meaning a single physical device's sequence of randomized MAC addresses was
being split across multiple cluster IDs.

## 2. Investigation

Two independent lines of evidence were used, both without modifying any code:

**A. Cross-cluster identity comparison.** For each of the 8 dynamic clusters, the underlying
`ie_fingerprint` (802.11 information-element signature) and probed SSID list were compared.
Six of the eight clusters shared the same device fingerprint and the same remembered network
name (`"Carpedm Rooms 2.4GHZ"`) — including one case where a cluster's fingerprint matched
**byte-for-byte** a fingerprint already present in a different, larger cluster. This is strong
direct evidence that those clusters were fragments of the same one or two physical phones,
not genuinely distinct devices.

**B. Direct scoring-function replay.** The Re-ID engine's own candidate-generation and
scoring functions were run against the real enriched CSV outside of the normal pipeline (read
only, no files written) to see exactly why specific MACs failed to merge.

## 3. Root Cause

The orphaned MAC `5e:62:09:c4:eb:89` (isolated as its own singleton cluster, tagged
`confidence: low`) had **13 candidate matches scoring 0.91–0.94** — all comfortably above the
`0.80` association threshold, including a 0.941-scoring match to a MAC already inside the
largest cluster. None of these were accepted.

The cause is the conflict-resolution algorithm (`_resolve_conflicts`), which is a **greedy**
pass: it sorts every candidate pairing in the entire scan by score, then walks down the list
claiming each one — but only if neither side is already claimed. When many pairings compete
for the same MAC (as happens whenever two devices of the same phone model rotate MACs in the
same time window), the highest-scoring options elsewhere in the file "use up" the available
partners first, stranding otherwise-valid matches. This is a structural flaw in greedy
selection, not a scoring or threshold problem — the bug reproduces even when every weight and
the threshold stay exactly as documented.

## 4. Hypothesis Tested and Rejected: Reweighting Frame Length

Before settling on the conflict-resolution fix, the hypothesis that `frame_length` should
carry more weight in the association score was tested directly against the same real data.
Result: **raising the frame-length weight made fragmentation dramatically worse** (7 → 31
clusters), because frame length is a weak signal in this dataset — it varies by up to 20
bytes within a single device's own burst, nearly as much as the gap observed between
genuinely different devices. **No scoring weights were changed as part of this fix**; the
existing weights (IE fingerprint 0.75 / frame length 0.20 / SSID bonus 0.10 / sequence bonus
0.05) remain the legacy Bleach-paper-sourced values.

## 5. Fix and Validated Result

Replacing only the conflict-resolution step — from greedy selection to an **optimal
one-to-one assignment** (bipartite maximum-weight matching, computed with
`scipy.optimize.linear_sum_assignment`) — with every weight, threshold, and candidate-
generation rule left untouched, was tested offline against the same real S1 candidate scores:

| | Greedy (current default) | Optimal assignment |
|---|---:|---:|
| Dynamic clusters | 7 | **2** |
| Largest cluster | 91 rows / 9 MACs | 349 rows / 36 MACs, one unbroken chain, zero time overlap between consecutive MACs |

The 2-cluster result is consistent with the 2 phones known to have been carried during
collection.

## 6. Decision

Recorded as **FD-R6** in `.ai/founder_decisions.md`: default `REID-02
conflict_resolution_mode` changes from `greedy_best_valid_match` to `optimal_assignment`.
`docs/Part B.md` §3.4 and Step 7 were updated to document the new default and the rationale.
The legacy greedy mode is retained in code for reference but is no longer the default path.

## 7. Implementation Status

Implemented by Codex per the handoff (`.ai/handoffs/current.md`), scoped to
`backend/app/modules/reid/engine.py::_resolve_conflicts` only — `_resolve_conflicts` now
performs the bipartite maximum-weight assignment described above via
`scipy.optimize.linear_sum_assignment`; the legacy greedy pass is retained in code as
`_resolve_conflicts_greedy` for reference but is no longer the default path. Reviewed by
Claude (`.ai/reviews/claude_review.md`, verdict: **approved**) — diff matches the handoff
scope exactly, no weight/threshold/schema changes, regression tests (including the exact toy
example from §5) pass, and the 9 pre-existing unrelated test failures were confirmed present
on `main` independent of this change.

**Live confirmation:** re-ran `scan_S1` through the actual running application — a real
session, the real `POST /sessions/{id}/reid/run` endpoint, the real `scan_S1_ENRICHED.csv` —
not just the offline replay used for diagnosis. Result: `dynamic_cluster_count` **7 → 2**,
matching the offline analysis exactly (`total_rows: 467` unchanged, both clusters at `high`
confidence).
