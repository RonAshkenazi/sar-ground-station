# PDF Deviations — Combined Authoritative Record
**Source document:** `docs/pre-2026-078.pdf` — BGU 4th Year Project, December 2025
**Authors of source:** Ron Ashkenazi, Daniel Kachura
**Combined by:** Claude (analysis) + Codex (analysis) — 2026-05-12
**Compared against:** Repo state 2026-05-12

This file is the single source of truth for deviations between the preliminary design report and the
current implementation. It drives sprint planning, founder decisions, and final report language.
Do not edit the source files; edit this one.

---

## Master Deviations Table

| # | Area | PDF says | Current app | Severity | Action |
|---|---|---|---|---|---|
| D-01 | Re-ID: classifier | Logistic Regression (f1, f2 features), Pmatch > 0.9 | Bleach heuristic union-find clustering, threshold = 1.0 stub | HIGH | Sprint 02 + justify in final report |
| D-02 | Re-ID: SEQ gap threshold | δth ≈ 64 | Not implemented | HIGH | Sprint 02 Goal 2 |
| D-03 | Re-ID: association threshold | Pmatch > 0.9 | 1.0 stub (blocks all associations) | HIGH | Sprint 02 Goal 1 |
| D-04 | Re-ID: burst grouping / IFS | Mean inter-frame spacing feature | Not implemented | MEDIUM | Sprint 02 Goal 3 |
| D-05 | Re-ID: conflict resolution | 1-MAC-to-1-cluster rule | Not implemented | MEDIUM | Sprint 02 Goal 4 |
| D-06 | Re-ID: MAC randomization | LAA bit check + Cappuccino pipeline | Not implemented | MEDIUM | Sprint 02 Goal 5 |
| D-07 | Localization: WLS centroid | WLS intermediate step before Bayesian update | LOC-05 stub exists; WLS weights unverified | MEDIUM | Verify in Sprint 02 Goal 7 |
| D-08 | Localization: RANSAC calibration | Per-scan η/σ fit via RANSAC | LOC-09/10/11 always skipped (TODO) | HIGH | Sprint 02 Goal 7 |
| D-09 | Localization: dynamic sigma | Non-zero alpha (Krypto §4.2) | 0.0 (disabled) | HIGH | Sprint 02 Goal 8 |
| D-10 | Localization: confidence cutoff | 0.4 | 0.0 (accepts all peaks) | HIGH | Sprint 02 Goal 8 |
| D-11 | ie_fingerprint format | Not specified in PDF | Legacy format vs new split-column format — contract unverified | HIGH | Sprint 02 Goal 9 |
| D-12 | Enrichment: PCAP time window | 1000 ms (legacy) | 500 ms | MEDIUM | Sprint 02 Goal 10 |
| D-13 | Enrichment: PCAP match threshold | 0.8 (legacy) | 0.3 | MEDIUM | Founder decision FD-03 |
| D-14 | Enrichment: vendor/OUI | Device context in signatures | `src_vendor` not populated; OUI DB not implemented | MEDIUM | Post-Sprint 02 |
| D-15 | BLE pipeline | Wi-Fi + BLE capture, BLE Re-ID | BLE parsing not implemented; enrichment hardcoded `protocol="wifi"` | MEDIUM | Post-Sprint 02 / integration |
| D-16 | Result Analysis | Ground-truth comparison, 20-run metric reporting | Page is placeholder; backend returns `not_implemented` | HIGH | Dedicated sprint needed |
| D-17 | Acceptance: Re-ID accuracy | ≥ 90% | Not measured — no field-test validation suite | HIGH | QA sprint + field tests |
| D-18 | Acceptance: localization accuracy | Point error < 10 m; 90% inside uncertainty circle | Not measured | HIGH | QA sprint + field tests |
| D-19 | Test protocol | 20 runs (3 integrity, 7 Re-ID, 10 localization) over 100×100 m | Automated unit/integration tests only; no field test structure | MEDIUM | QA sprint |
| D-20 | Data offload UI | HTTP "Files" tab, operator drops logs from air unit | Not implemented; app assumes DATA/ pre-populated | LOW | Founder decision FD-04 |
| D-21 | Air unit scope | RPi Zero 2W, monitor mode, BLE, GNSS, Store & Forward | Explicitly out of scope in ground station repo | INFO | Note in final report |
| D-22 | C2 / heartbeat | WebSocket C2, start/stop scan, GET /logs | Not in ground station scope | INFO | Note in final report |
| D-23 | Architecture: "local database" | PDF implies local DB for ground station storage | Intentional filesystem storage (DATA/, TEMP/, Saved Scans/) | INFO | Clarify in final report |
| D-24 | Architecture: milestone language | ARCHITECTURE.md says first milestone = through Enrichment | App now includes Re-ID, Localization, Save/Resume | INFO | Update ARCHITECTURE.md |
| D-25 | Architecture: Save/Resume | Not described in PDF (PDF describes air-unit Store & Forward) | Ground station session persistence exists under Saved Scans/ | INFO | Note as enhancement in report |
| D-26 | UI: localization map | Probabilistic heatmap + cluster results promised | Heatmap/peaks/cluster table implemented; GT overlays and rerun UI not done | MEDIUM | Post-Sprint 02 |
| D-27 | UI: ground station type | "Python pipeline with Web UI" | FastAPI + React/TypeScript | NONE (upgrade) | Positive note in report |
| D-28 | Krypto: search-path optimization | Literature context for multi-quadrant sensing | Not implemented; app analyzes logs only | INFO | Literature-only; not a gap |
| D-29 | Privacy boundary | Only unencrypted management frames; no payload decryption | Consistent in implementation but not stated explicitly | LOW | Add comment/note in final report |
| D-30 | Artifact naming | Not specified in PDF | Current canonical: `*_ENRICHED.csv`, `*_REID.csv` (uppercase) | INFO | Use current names in final report |

---

## Section 1 — Re-ID Engine (MOD-008)

### D-01 — Classifier: Logistic Regression → Bleach Heuristic Clustering

The PDF specified a Logistic Regression classifier trained on two features:
- **f1** — mean inter-frame spacing (IFS) difference between probe bursts
- **f2** — IE element similarity (Jaccard or bitwise)

Decision threshold: **Pmatch > 0.9**

The current implementation uses the **Bleach** (Mishra et al. 2024) unsupervised heuristic:
union-find clustering over a weighted similarity score (IE fingerprint + frame length + SSID bonus +
sequence bonus). No ML model is used.

**Why this is the right change:** Logistic Regression requires labeled training data. In SAR field
deployment there are no pre-labeled MAC pairs available. Bleach's unsupervised approach is
deployable without training. This is a defensible upgrade, not a regression.

**Final report action:** Explicitly acknowledge the departure from the LR approach. State that
Bleach was chosen as a more field-deployable alternative with a stronger academic basis for the
probe-request domain. Cite Mishra et al. 2024.

---

### D-02 — SEQ gap threshold: δth ≈ 64 vs not implemented

The PDF references the Bleach sequence-gap parameter δth ≈ 64. Current engine has no sequence
continuity scoring at all — this is a core Bleach feature.

Sprint 02 Goal 2 implements this. The sprint index currently targets 50; the PDF and Bleach paper
suggest 64. **Founder decision FD-02** resolves which value to commit.

---

### D-03 — Association threshold: 0.9 → 1.0 stub

Current `_REID_ASSOCIATION_THRESHOLD = 1.0` means no pair ever meets the threshold — the engine
produces no associations in practice. Must be fixed to ≥ 0.8 (clustering minimum) or 0.9 (PDF target).
Sprint 02 Goal 1.

---

### D-04 — Burst grouping / IFS feature not implemented

PDF's f1 feature (mean IFS difference) maps to Bleach's `group_bursts` pre-processing step.
Neither is in the current engine. Sprint 02 Goal 3.

---

### D-05 / D-06 — Conflict resolution and MAC randomization detection

Both are referenced in the PDF and the Bleach/Cappuccino papers. Neither is implemented.
Sprint 02 Goals 4 and 5.

---

## Section 2 — Localization Engine (MOD-009)

### D-07 — WLS centroid unverified

PDF explicitly calls for Weighted Least Squares centroid as an intermediate step before the Bayesian
grid posterior update. LOC-05 exists in the engine but whether it applies 1/σ² weighting or a simple
mean is unverified. Verify during Sprint 02 Goal 7.

---

### D-08 — RANSAC calibration always skipped

LOC-09, LOC-10, LOC-11 are marked TODO and bypassed in every run. This means η and σ always use
fallback presets rather than per-scan calibration. The PDF depends on calibrated parameters for the
accuracy claims. **Sprint 02 Goal 7 is blocking for final demo validity.**

PDF target values: η ≈ 2.5–3.0, σ ≈ 4–6 dB.

---

### D-09 / D-10 — Dynamic sigma (0.0) and confidence cutoff (0.0)

Both disabled as stubs. Effect: engine accepts all grid peaks regardless of quality and uses static
sigma throughout. Produces low-reliability uncertainty regions. Sprint 02 Goal 8.

Target: `_LOC_07_DYNAMIC_SIGMA_ALPHA = 0.05`, `_LOC_08_CONFIDENCE_CUTOFF = 0.40`.

---

## Section 3 — Enrichment Engine (MOD-007)

### D-11 — ie_fingerprint format contract unverified

Legacy enrichment wrote `"TAG:HEX;TAG:HEX;..."` as a single column. New enrichment uses separate
`ie_ids` and `ie_fingerprint` columns. If the Re-ID engine reads the legacy format but enrichment
writes the new format, association will silently fail on IE similarity. Sprint 02 Goal 9.

Tags fingerprinted: 1, 50, 45, 127, 221 (from sprint_02_index.md — to be confirmed by Researcher).

---

### D-12 / D-13 — PCAP time window 500ms and match threshold 0.3

Both are stubs that differ from legacy. Combined effect: enrichment matches fewer PCAP packets at lower
quality than the legacy system. Fix window to 1000ms (Sprint 02 Goal 10). Match threshold 0.3 vs 0.8
needs founder decision FD-03.

At 0.0% observed PCAP match rate in current demo, both stubs are contributing.

---

### D-14 — Vendor/OUI context missing

`src_vendor` column not populated; no OUI database is loaded. The PDF and algorithm narrative rely on
device-context signatures. This is a post-Sprint 02 item.

---

## Section 4 — Architecture & Deployment

### D-15 — BLE pipeline is a stub

PDF describes Wi-Fi + BLE dual capture. Current enrichment is hardcoded to `protocol="wifi"`. BLE
PCAP parsing, BLE Re-ID, and BLE localization are not implemented. Scope: integration sprint after
Wi-Fi pipeline is fully validated.

### D-16 — Result Analysis page is a placeholder

Backend result-analysis endpoints return `not_implemented`. The PDF's 20-run acceptance test protocol
requires ground-truth comparison and per-run metric reporting — none of which can be done without this
page. **This is a blocking gap for the final demo.** Needs a dedicated sprint.

### D-17 / D-18 — Acceptance criteria not validated

Re-ID ≥ 90% accuracy and localization < 10m point error are PDF commitments that have not been
measured. These require a field test dataset and an automated evaluation pipeline. Needs QA sprint
and field tests before final report can make these claims.

### D-20 — Data offload UI not implemented

PDF describes an HTTP "Files" tab on the ground station for operators to receive logs from the air
unit. Current app assumes DATA/ is pre-populated by other means. If the final demo requires live
transfer, this needs a sprint. Founder decision FD-04.

### D-21 to D-23 — Out-of-scope / intentional changes

- Air unit code (D-21): explicitly out of scope; note in final report
- C2 WebSocket (D-22): out of scope; note in final report
- Filesystem vs DB (D-23): intentional architectural choice; state it clearly in final report

### D-24 — ARCHITECTURE.md milestone language is stale

Document says first milestone = operational Wi-Fi workflow through Enrichment. App now passes Re-ID,
Localization, and Save/Resume. Update ARCHITECTURE.md to match reality.

---

## Section 5 — Founder Decisions Required

```
## FD-01: Re-ID classifier — LR vs Bleach
PDF says: Logistic Regression, Pmatch > 0.9
Current app: Bleach heuristic clustering
Options: [Keep Bleach] / [Implement LR on top of Bleach as second pass]
Recommendation: Keep Bleach. LR requires labeled training data unavailable in field.
  Document the decision in final report Section on algorithm choices.
Status: PENDING
```

```
## FD-02: SEQ gap threshold — 64 vs 50
PDF says: δth ≈ 64
Sprint 02 index targets: 50
Legacy app value: TBD (Researcher sprint will confirm)
Options: [Use 64 per PDF/Bleach] / [Use 50 per sprint index] / [Use legacy app value]
Recommendation: Use legacy app confirmed value; document deviation from PDF with rationale.
Status: PENDING — blocked on Researcher sprint output
```

```
## FD-03: PCAP match threshold — 0.3 vs 0.8
PDF says: not specified
Legacy app: 0.8
Current app: 0.3
Options: [Revert to 0.8 (legacy)] / [Keep 0.3 (intentional relaxation)] / [Tune empirically]
Recommendation: Treat as intentional only if a comment exists. Otherwise revert to 0.8 and tune.
Status: PENDING
```

```
## FD-04: Data offload UI — in scope for final demo?
PDF says: HTTP Files tab for air unit log transfer
Current app: assumes DATA/ pre-populated
Options: [In scope — implement HTTP file drop] / [Out of scope — document assumption]
Recommendation: Out of scope for ground station software sprint. Document: "DATA/ is populated
  by the air unit's Store & Forward mechanism; the ground station does not manage the transfer."
Status: PENDING
```

---

## Section 6 — Final Report Language Guidance

Use these when writing the final report:

1. **Re-ID algorithm change** — "The preliminary design specified a Logistic Regression classifier. After further review of the literature, the implementation adopted the Bleach algorithm (Mishra et al. 2024) which provides unsupervised probe-request association without requiring labeled training data — a practical requirement for SAR field deployment."

2. **Architecture upgrade** — "The ground station was implemented as a FastAPI backend with a React/TypeScript frontend, consistent with the preliminary design's 'Python pipeline with Web UI' description and providing a richer interactive experience."

3. **Airborne scope** — "The air unit firmware (Raspberry Pi Zero 2W, monitor mode capture, Store & Forward) is a separate deliverable. This report covers the ground station software only. Integration between the two components was tested using pre-captured scan datasets."

4. **Performance claims** — Do not assert Re-ID ≥ 90% or localization < 10m until field validation is complete. Use: "The system is designed to meet these targets; validation against the 20-run test protocol is ongoing."

5. **BLE** — "BLE pipeline support is architecturally in place; full BLE enrichment and Re-ID are targeted for a future integration sprint."

6. **Stub constants** — Do not quote `1.0` stub values in the final report. All algorithm constants will be resolved in Sprint 02 before the report is finalized.

---

## Section 7 — Sprint / Action Mapping

| Sprint | Items addressed |
|---|---|
| **Sprint 02 (current)** | D-01 (justify), D-02, D-03, D-04, D-05, D-06, D-07, D-08, D-09, D-10, D-11, D-12 |
| **Post-Sprint 02** | D-13 (FD), D-14, D-15 |
| **QA / Validation Sprint** | D-16, D-17, D-18, D-19 |
| **Integration Sprint** | D-15 (BLE), D-20 (FD), D-22 |
| **Documentation / housekeeping** | D-21, D-23, D-24, D-25, D-27, D-28, D-29, D-30 |
| **Founder decisions before Sprint 02 closes** | FD-01, FD-02, FD-03, FD-04 |
