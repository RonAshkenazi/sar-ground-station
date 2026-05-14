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

## Category 3 — Localization Constants

---

### FD-L1 · Dynamic sigma alpha — ✅ Resolved

**Decision: `0.05`** — UI-tunable, options: `0.0` / `0.05` / `0.10`

---

### FD-L2 · Localization confidence cutoff — ✅ Resolved

**Decision: `0.50`** — UI-tunable, options: `0.40` / `0.50` / `0.60`

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
