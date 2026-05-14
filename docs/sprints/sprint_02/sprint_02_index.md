# Sprint 02 — Algorithm Quality: Re-ID, Localization & Legacy Alignment

| Field | Value |
|-------|-------|
| **Sprint** | 02 |
| **Goal** | Replace all stub `1.0` weights and TODO constants in Re-ID and Localization with real implementations derived from the legacy app and the four reference papers (Bleach, Cappuccino, Krypto, BlueFly) |
| **Status** | Planning |
| **Start** | 2026-05-12 |
| **Phase** | Phase 7 — Algorithm Quality Pass |

---

## Context

Sprint 01 and the Codex phases 1–6 delivered a running full-stack pipeline:
Session Start → Overview → Calibration → Enrichment → Re-ID → Localization → Save/Resume.

The pipeline runs end-to-end but the Re-ID and Localization engines use placeholder constants
(all scoring weights = `1.0`, thresholds = `0.0` or unconfigured). The legacy app
(`reference/legacy_app/`) contains the real Bleach-based implementation. This sprint extracts
the correct algorithm from the legacy and fills in all stubs, guided by the academic references.

---

## Reference Papers

| Nickname | Citation | What we need from it |
|---|---|---|
| **Bleach** | Mishra, Viana, Achir — *Ad Hoc Networks* 2024 | IE fingerprint scoring, burst grouping, union-find clustering weights, sequence continuity scoring |
| **Cappuccino** | He, Tan, Chan — *IEEE TMC* 2023 | Self-supervised MAC association for heavily randomized MACs; complements Bleach |
| **Krypto** | Ho, Chen, Chen — *ACM DroNet* 2015 | Grid resolution and localization design for UAV-collected WiFi; confidence cutoff rationale |
| **BlueFly** | Parsons Corp. 2025 | BLE pipeline requirements, protocol support, field deployment scan parameters |

---

## Sprint Goals

### Goal 1 — Re-ID: Real Bleach scoring weights (HIGH)

Replace all `_REID_WIFI_*` stubs currently set to `1.0` with the legacy Bleach values:

| Constant | Current | Target (legacy/Bleach) |
|---|---|---|
| IE fingerprint similarity weight | 1.0 | 0.75 (distributed across 5 IE tags: 1, 50, 45, 127, 221) |
| Frame length similarity weight | 1.0 | 0.20 |
| SSID match bonus weight | 1.0 | 0.10 |
| Sequence continuity bonus weight | 1.0 | 0.05 |
| IE similarity threshold (bitwise hex) | not implemented | 0.90 |
| Clustering score threshold (min) | 1.0 | 0.60 |
| Clustering score threshold (strict) | — | 0.75 |
| Match threshold | 1.0 | 0.80 |

**Reference:** `reference/legacy_app/reid/features.py`, `pairing.py`; Bleach paper Section 4.

---

### Goal 2 — Re-ID: Sequence continuity and temporal sanity checks (HIGH)

Implement the missing sequence-gap and time-gap scoring that Bleach uses to distinguish
continuous probe bursts from different devices:

| Constant | Target |
|---|---|
| `t_max_sec` (max time gap between associated probes) | 30 sec (tunable 3–30) |
| `seq_max_gap` (max WiFi sequence number gap) | 50 (tunable 20–200) |
| `seq_modulus` (rollover) | 4096 |
| `rssi_max_diff` (sanity: reject pairs with extreme RSSI delta) | 30 dBm |
| `sanity_time_window_sec` | 5.0 sec |

**Reference:** `reference/legacy_app/reid/features.py`; Bleach paper Section 3.2.

---

### Goal 3 — Re-ID: Burst grouping (MEDIUM)

Implement burst aggregation: group packets within a sliding 60-second window into burst
signatures (duration, RSSI stats, seq delta, inter-arrival timing) before the clustering pass.
This is the pre-processing step the legacy runs before `OnlineClusterer`.

**Reference:** `reference/legacy_app/reid/features.py::group_bursts`; Bleach paper Section 3.1.

---

### Goal 4 — Re-ID: Conflict resolution post-pass (MEDIUM)

After clustering, enforce the 1-MAC-to-1-cluster rule:
if two clusters share a MAC address, merge or resolve the conflict.

**Reference:** `reference/legacy_app/reid/pipeline.py::resolve_mac_conflicts`.

---

### Goal 5 — Re-ID: MAC randomization detection (MEDIUM)

Implement LAA bit checking to detect locally-administered (randomized) MACs before
the clustering pass. Randomized MACs feed the full Bleach pipeline; static/OUI-stable
MACs can be associated directly.

**Reference:** `reference/legacy_app/reid/vendor_lookup.py::is_randomized_mac`; Cappuccino paper Section 2.

---

### Goal 6 — Re-ID: Confidence output per cluster (LOW)

Add per-cluster confidence tier to Re-ID output:
- `high` — score ≥ 0.75
- `medium` — score 0.60–0.75
- `low` — score < 0.60

This maps to the `cluster_type` or a new `confidence` field in `ReIDRecord`.

---

### Goal 7 — Localization: RANSAC pre-filtering (HIGH)

Implement LOC-09/10/11 (currently always-skipped TODOs):

| Constant | Target (legacy) |
|---|---|
| RANSAC iterations | 100 |
| RANSAC inlier threshold | 10.0 dBm |
| Min RANSAC inlier ratio for early-exit | 0.80 |
| Min samples for RANSAC | 3 |

**Reference:** `reference/legacy_app/core/likelihood_grid/ransac.py`; Krypto paper Section 4.

---

### Goal 8 — Localization: Confidence cutoff and dynamic sigma (HIGH)

Re-enable the two localization parameters currently disabled:

| Constant | Current | Target |
|---|---|---|
| `_LOC_07_DYNAMIC_SIGMA_ALPHA` | 0.0 (disabled) | 0.05 |
| `_LOC_08_CONFIDENCE_CUTOFF` | 0.0 (accepts all peaks) | 0.40 |

**Reference:** `reference/legacy_app/core/likelihood_grid/grid.py`; Krypto paper Section 4.2.

---

### Goal 9 — Data format: ie_fingerprint compatibility (HIGH)

Verify that the `ie_fingerprint` format written by the Enrichment engine is exactly what
the Re-ID engine expects.

- Legacy format: `"TAG:HEX;TAG:HEX;..."` (e.g. `"1:aabbcc;45:ddeeff"`)
- New enrichment outputs: `ie_ids`, `ie_fingerprint`, `ie_vendor_ouis` as separate columns

If they differ, fix the Enrichment output or add a normalisation step in Re-ID input parsing.

---

### Goal 10 — Enrichment: Correct time window (MEDIUM)

Fix the enrichment PCAP matching time window:

| Constant | Current | Target |
|---|---|---|
| `_ENR_02_TIME_WINDOW_MS` | 500 ms | 1000 ms (legacy default) |

Also review `_ENR_01_MATCH_THRESHOLD` (currently 0.3 vs legacy 0.8) — may be intentional;
needs a founder decision if changed.

**Reference:** `reference/legacy_app/reid/pcap_features.py`.

---

## Researcher Pre-Work (before Codex starts)

Before any code is written, the Researcher role must:

1. Read `reference/legacy_app/reid/IMPLEMENTATION_SUMMARY.py` in full — this is the authoritative
   description of what the legacy Re-ID does.
2. Read `reference/legacy_app/reid/features.py` and `pairing.py` — extract every constant with
   its value and the code context.
3. Confirm the `ie_fingerprint` column format in the legacy enrichment output vs Re-ID input.
4. Flag any constant that differs between the legacy code and the Bleach/Cappuccino papers —
   these need a founder decision before they are committed.
5. Produce a single constants table (`docs/sprints/sprint_02/researcher_constants.md`) with:
   `constant | legacy value | paper value | source | recommended`.

---

## Exit Criteria

- [ ] All `_REID_WIFI_*` weights replaced with real Bleach values (no `1.0` stubs remaining)
- [ ] Sequence gap + time gap scoring implemented in Re-ID engine
- [ ] Burst grouping implemented
- [ ] MAC randomization detection implemented
- [ ] Conflict resolution post-pass implemented
- [ ] RANSAC pre-filtering active in Localization (LOC-09/10/11)
- [ ] `_LOC_07_DYNAMIC_SIGMA_ALPHA = 0.05` and `_LOC_08_CONFIDENCE_CUTOFF = 0.40`
- [ ] `ie_fingerprint` format verified compatible between Enrichment and Re-ID
- [ ] `_ENR_02_TIME_WINDOW_MS` corrected to 1000 ms
- [ ] `cd backend && python -m pytest --tb=short -q` passes (≥ 80 tests, no regressions)
- [ ] `cd frontend && npm run build` passes cleanly
- [ ] Researcher constants table committed to `docs/sprints/sprint_02/researcher_constants.md`

---

## Roles

| Goal | Role |
|---|---|
| Goals 1–6 (Re-ID engine) | DEV:algo |
| Goals 7–8 (Localization engine) | DEV:algo |
| Goal 9 (ie_fingerprint format) | DEV:backend + RESEARCHER |
| Goal 10 (Enrichment time window) | DEV:backend |
| Pre-work (constants table) | RESEARCHER |
| Test coverage | QA |

---

## Artifacts

- Constants table: `docs/sprints/sprint_02/researcher_constants.md`
- Report: `docs/sprints/sprint_02/reports/sprint_02_report.md`
