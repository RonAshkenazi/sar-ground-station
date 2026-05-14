# PDF Inconsistencies — Claude Analysis
**Source:** `docs/pre-2026-078.pdf` — BGU 4th Year Project: "RF-Based Scanning and Localization System for SAR"
**Authors:** Ron Ashkenazi, Daniel Kachura — December 2025
**Compared against:** Current implementation in `backend/app/modules/` as of 2026-05-12

[RESEARCHER]

---

## Summary

The PDF is a preliminary design report written before the current codebase was built. Several algorithm choices and architectural patterns have since diverged — some intentionally upgraded, others incomplete stubs. Items are grouped by module and severity.

---

## 1 — Re-ID Engine (MOD-008)

### 1.1 Classifier type: Logistic Regression → Heuristic clustering

| | PDF spec | Current implementation |
|---|---|---|
| Method | Logistic Regression binary classifier on features f1, f2 | Union-find clustering with heuristic scoring weights |
| Features | f1 = mean inter-frame spacing diff, f2 = IE similarity | IE fingerprint, frame length, SSID bonus, seq bonus |
| Decision | Pmatch > 0.9 threshold | Configurable score threshold (stub = 1.0) |

**Severity: HIGH** — The algorithmic approach has fundamentally changed. The PDF describes a supervised ML approach (LR); the current implementation follows the **Bleach** paper (unsupervised heuristic clustering with union-find). This is not a bug — Bleach is a more recent and rigorous reference — but the final report must justify the departure and confirm Bleach was chosen over the LR approach.

**Recommendation:** Document in final report that LR was superseded by Bleach (Mishra et al. 2024) which uses unsupervised feature-based clustering, avoiding the need for labeled training data in field deployment.

---

### 1.2 SEQ gap threshold: δth ≈ 64 vs not implemented

| | PDF spec | Current implementation |
|---|---|---|
| δth (sequence gap threshold) | ≈ 64 (from Bleach paper Section 3.2) | NOT IMPLEMENTED — engine has no sequence continuity scoring at all |
| Tunable range | 20–200 per Bleach | — |

**Severity: HIGH** — Sequence continuity is a core Bleach feature. The sprint_02 index sets the target at 50; the PDF says ≈64. This is a **Founder Decision** already flagged in the sprint index.

---

### 1.3 Pmatch threshold: 0.9 vs 1.0 stub

| | PDF spec | Current implementation |
|---|---|---|
| `_REID_ASSOCIATION_THRESHOLD` | 0.9 | 1.0 (stub — effectively blocks all associations) |

**Severity: HIGH** — The 1.0 stub means no pair ever associates. The PDF target of 0.9 aligns with Bleach's clustering score threshold. Must be fixed in Sprint 02.

---

### 1.4 Feature f1 (mean IFS difference) — not implemented

| | PDF spec | Current implementation |
|---|---|---|
| f1 feature | Mean inter-frame spacing difference between probe bursts | Not present in new engine (burst grouping not yet implemented) |

**Severity: MEDIUM** — This feature maps to Bleach's burst grouping step (`group_bursts`). Sprint 02 Goal 3 covers this. Cross-check: the PDF calls it "mean IFS difference" whereas Bleach calls it burst duration / inter-arrival statistics. They are measuring the same underlying signal.

---

## 2 — Localization Engine (MOD-009)

### 2.1 WLS centroid step: present in PDF → unclear in new app

| | PDF spec | Current implementation |
|---|---|---|
| Centroid method | Weighted Least Squares (WLS) centroid as intermediate step before Bayesian update | `_LOC_05_*` stub exists but not verified as WLS |

**Severity: MEDIUM** — The PDF specifies WLS explicitly as the pre-Bayesian centroid. Current code has a centroid step but whether it uses WLS weights (1/σ²) or simple mean needs verification. Flag for Sprint 02 localization review.

---

### 2.2 Path-loss parameters: η and σ

| | PDF spec | Current implementation |
|---|---|---|
| Path-loss exponent η | ≈ 2.5–3.0 | Present in `SessionCalibration` but RANSAC calibration step is TODO (LOC-09) |
| Shadow fading σ | ≈ 4–6 dB | Present in `SessionCalibration` |
| Derivation | RANSAC fit from calibration packets | RANSAC is always-skipped TODO in `localization/engine.py` |

**Severity: HIGH** — RANSAC calibration (LOC-09/10/11) is marked TODO and always skipped. Sprint 02 Goal 7 covers this. Until fixed, η and σ use fallback presets instead of per-scan calibration.

---

### 2.3 Dynamic sigma and confidence cutoff disabled

| | PDF spec | Current implementation |
|---|---|---|
| `_LOC_07_DYNAMIC_SIGMA_ALPHA` | Implied non-zero (Krypto Section 4.2) | 0.0 (disabled) |
| `_LOC_08_CONFIDENCE_CUTOFF` | 0.4 (inferred from legacy app) | 0.0 (accepts all peaks) |

**Severity: HIGH** — With both values at 0.0, the localization engine accepts all peaks regardless of quality and uses static sigma. This produces unreliable uncertainty regions. Sprint 02 Goal 8 must fix both.

---

## 3 — Architecture & Deployment

### 3.1 Ground station described as "Python pipeline with Web UI"

| | PDF spec | Current implementation |
|---|---|---|
| Ground station | Python-based pipeline with web UI | FastAPI (Python) + React/TypeScript frontend |

**Severity: NONE (upgrade)** — The PDF was written before the React frontend was added. FastAPI + React is architecturally consistent with "Python backend, Web UI." This is not an inconsistency — it is an implementation upgrade. Note for report.

---

### 3.2 Data offload UI ("Files" tab HTTP transfer)

| | PDF spec | Current implementation |
|---|---|---|
| Air unit → Ground transfer | HTTP file transfer UI, "Files" tab on ground station | Not implemented |

**Severity: LOW** — The PDF mentions a web-based file drop from the air unit. The current app assumes scan data already exists in `DATA/`. If the final demo requires live transfer from the drone, this is a missing feature. Likely deferred to integration testing.

---

### 3.3 Airborne software not in this repo

| | PDF spec | Current implementation |
|---|---|---|
| Airborne deliverable | Raspberry Pi Zero 2W, WiFi monitor mode ch 1/6/11, BLE dongle, GNSS, pcap capture, Store & Forward | `reference/legacy_app/` contains ground-side only |

**Severity: INFO** — The airborne side is explicitly out of scope for the ground station repo. `reference/legacy_app/` does not include the air unit software. The final report should clarify this split.

---

### 3.4 C2 WebSocket interface referenced

| | PDF spec | Current implementation |
|---|---|---|
| C2 channel | WebSocket-based command and control between ground station and air unit | Not in ground station scope |

**Severity: INFO** — Out of scope. Note for final report if integration with C2 is expected.

---

## 4 — Enrichment Engine (MOD-007)

### 4.1 PCAP matching time window: 500ms vs 1000ms

| | PDF spec (inferred from legacy) | Current implementation |
|---|---|---|
| `_ENR_02_TIME_WINDOW_MS` | 1000 ms (legacy default) | 500 ms (stub value) |

**Severity: MEDIUM** — Sprint 02 Goal 10. The PDF does not state this explicitly but the legacy implementation uses 1000ms. Current 500ms will miss valid PCAP matches at the window boundary.

---

### 4.2 PCAP match threshold: 0.3 vs legacy 0.8

| | Legacy app | Current implementation |
|---|---|---|
| `_ENR_01_MATCH_THRESHOLD` | 0.8 | 0.3 |

**Severity: MEDIUM** — The PDF doesn't specify this number explicitly but the legacy uses 0.8. Current 0.3 will accept poor-quality PCAP matches. Needs Founder Decision: was 0.3 intentional?

---

## 5 — Test Plan

### 5.1 PDF test plan not reflected in current test suite

| | PDF spec | Current implementation |
|---|---|---|
| Test runs | 20 runs (3 integrity, 7 Re-ID, 10 localization) | Unit/integration tests exist but no field test scenarios |
| Area | 100×100 m test area | No spatial test fixtures |
| Acceptance: Re-ID | ≥ 90% accuracy | Not validated by any test |
| Acceptance: Localization | Point accuracy < 10 m, 90% within uncertainty circle | Not validated by any test |

**Severity: MEDIUM** — The acceptance criteria from the PDF are not yet codified as automated tests. This is expected at this stage but must be addressed before the final demo. QA sprint needed.

---

## 6 — IE Fingerprint Format

### 6.1 Tag set and format not verified

| | PDF spec | Current implementation |
|---|---|---|
| IE tags fingerprinted | Not specified in PDF | Tags 1, 50, 45, 127, 221 (from sprint_02_index.md) |
| ie_fingerprint format | Not specified in PDF | `"TAG:HEX;TAG:HEX"` (legacy) vs separate `ie_ids`/`ie_fingerprint` columns (new enrichment) |

**Severity: HIGH** — The PDF doesn't specify the column format, but the legacy → new migration may have broken the format contract between Enrichment and Re-ID. Sprint 02 Goal 9 must verify this.

---

## 7 — Summary Table

| # | Area | PDF says | Current app | Severity | Sprint 02 goal |
|---|---|---|---|---|---|
| 1.1 | Re-ID classifier | Logistic Regression | Bleach heuristic clustering | HIGH (intentional change) | — (justify in report) |
| 1.2 | SEQ gap threshold | δth ≈ 64 | Not implemented | HIGH | Goal 2 |
| 1.3 | Pmatch threshold | 0.9 | 1.0 stub | HIGH | Goal 1 |
| 1.4 | f1 feature (IFS) | Mean IFS diff | Not implemented | MEDIUM | Goal 3 |
| 2.1 | WLS centroid | WLS | Unverified | MEDIUM | Verify in Goal 7 |
| 2.2 | RANSAC calibration | Per-scan fit | Always skipped | HIGH | Goal 7 |
| 2.3 | Dynamic sigma / cutoff | Non-zero | 0.0 / 0.0 | HIGH | Goal 8 |
| 3.2 | Data offload UI | HTTP Files tab | Not implemented | LOW | Deferred |
| 3.3 | Airborne software | In repo | Out of scope | INFO | — |
| 4.1 | PCAP time window | 1000 ms | 500 ms | MEDIUM | Goal 10 |
| 4.2 | PCAP match threshold | 0.8 | 0.3 | MEDIUM | Founder decision |
| 5.1 | Acceptance tests | 20-run field tests | Not automated | MEDIUM | Future QA sprint |
| 6.1 | ie_fingerprint format | Unspecified | Possible mismatch | HIGH | Goal 9 |

---

## 8 — Founder Decisions Surfaced

1. **LR vs Bleach heuristic** — Report must justify choosing Bleach over the PDF's LR approach. Recommend: Bleach requires no labeled training data, which is impractical in SAR field deployment. Bleach is the stronger academic reference for this use case.

2. **δth = 64 (PDF) vs 50 (sprint_02_index)** — Which value to commit? Legacy Bleach paper says ≈64; the sprint index chose 50 as the target. Recommend: use legacy app value (confirmed from `reference/legacy_app/`) and document deviation from PDF.

3. **`_ENR_01_MATCH_THRESHOLD` = 0.3 vs 0.8** — Was 0.3 intentional or is it an unreviewed stub? Recommend: treat as Founder decision; if it was intentional, add a comment; if not, revert to legacy 0.8.

4. **Data offload UI** — Is HTTP file transfer from air unit to ground station in scope for the final demo? If yes, needs a sprint. If no, document the assumption that `DATA/` is pre-populated.
