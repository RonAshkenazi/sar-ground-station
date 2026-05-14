# [RESEARCHER] Sprint 02 Legacy Constants Table

Source set read: current backend engines, `docs/Part B.md`, `docs/sprints/sprint_02/sprint_02_index.md`, and legacy files under `reference/legacy_app/ground_station/`.

Important source gap: `reference/legacy_app/ground_station/reid/pairing.py` is referenced by the handoff but is not present as source. A `pairing.pyc` exists, but this report does not decompile bytecode. Values below come from `reid/models.py`, `reid/clustering.py`, `reid/features.py`, `reid/pipeline.py`, `reid/pcap_features.py`, `core/likelihood_grid/*.py`, and the legacy implementation summary.

## Section 1 - Re-ID Scoring Weights

| Constant name (new backend) | Legacy variable name | Legacy value | Paper | Notes |
|---|---|---:|---|---|
| `_REID_WIFI_IE_FINGERPRINT_WEIGHT` | `ReidConfig.w_ie_total` | `0.75` | Bleach | Distributed across 5 IE tags, so effective per-tag weight is `0.15`. |
| `_REID_WIFI_FRAME_LEN_WEIGHT` | `ReidConfig.w_frame_len` | `0.20` | Bleach | Exact frame-length match with `< 1.0` tolerance gets full weight. |
| `_REID_WIFI_SSID_BONUS_WEIGHT` | `ReidConfig.w_ssid_bonus` | `0.10` | Bleach | Bonus only; mismatch is neutral. |
| `_REID_WIFI_SEQ_BONUS_WEIGHT` | `ReidConfig.w_seq_bonus` | `0.05` | Bleach | Bonus when sequence delta is positive and `< 128`. |
| `_REID_WIFI_IE_SIMILARITY_THRESHOLD` | `ReidConfig.ie_similarity_threshold` | `0.90` | Bleach | Bitwise hex similarity cutoff. Passing score is scaled by similarity. |
| `_REID_WIFI_MATCH_THRESHOLD` | `ReidConfig.match_threshold` | `0.80` | Bleach | Online cluster match threshold. |
| `_REID_WIFI_STRICT_THRESHOLD` | `NOT FOUND - implementation summary only` | `0.75` | Bleach | Mentioned as high-confidence/strict threshold in summary and sprint plan, but not present as a named source constant. |
| `_REID_ASSOCIATION_THRESHOLD` | `ReidConfig.match_threshold` | `0.80` | Bleach/Cappuccino | Best legacy equivalent for the new backend's overall association threshold. |

IE tags fingerprinted by legacy `ReidConfig.ie_tags_to_check`:

| Tag ID | Meaning from legacy comment |
|---:|---|
| `1` | Supported Rates |
| `50` | Extended Supported Rates |
| `45` | HT Capabilities |
| `127` | Extended Capabilities |
| `221` | Vendor Specific |

Legacy PCAP extraction additionally keeps IE tags `{1, 50, 45, 61, 127, 191, 192, 221}` in `pcap_features.py`, but Re-ID scoring checks only `{1, 50, 45, 127, 221}`.

## Section 2 - Re-ID Temporal & Sequence Parameters

| Constant name (new backend) | Legacy variable name | Legacy value | Tunable range (if any) | Paper | Notes |
|---|---|---:|---|---|---|
| `_REID_WIFI_TIME_GAP_MAX_SEC` | `NOT FOUND in current source; implementation summary example uses ReidConfig(t_max_sec=30)` | `30 sec` | `3-30 sec` from sprint plan and summary discussion | Bleach | The source dataclass does not define `t_max_sec`, but the summary and examples reference it. Treat as required but source-incomplete. |
| `_REID_WIFI_SEQ_GAP_MAX` | `NOT FOUND as dataclass field; clustering uses hardcoded delta < 128` | `128 in source condition; 50 in summary/example` | `20-200` from sprint plan | Bleach | Conflict: source condition uses `< 128`; summary/example recommends `seq_max_gap=50`. Founder decision required. |
| `_REID_WIFI_SEQ_MODULUS` | `ReidConfig.seq_modulus` | `4096` | none found | 802.11 | Used by `_get_seq_delta(seq_new, seq_old)`. |
| `_REID_WIFI_RSSI_SANITY_MAX_DIFF_DB` | `ReidConfig.sanity_rssi_diff_db` | `30.0 dB` | none found | Bleach | If time gap is inside sanity window and RSSI delta exceeds this, match is invalid. |
| `_REID_WIFI_SANITY_TIME_WINDOW_SEC` | `ReidConfig.sanity_time_window_sec` | `5.0 sec` | none found | Bleach | Applies physics sanity check only for `0 <= dt < 5 sec`. |
| `_REID_WIFI_BURST_WINDOW_SEC` | `NOT FOUND in source dataclass; implementation summary says burst_window_sec` | `60 sec` | none found | Bleach | Summary says `group_bursts(df, burst_window_sec=60)`, but the checked `features.py` source does not contain `group_bursts`. |

## Section 3 - Localization Constants

| Constant name (new backend) | Legacy variable name | Legacy value | Paper | Notes |
|---|---|---:|---|---|
| `_LOC_07_DYNAMIC_SIGMA_ALPHA` | `params["alpha"]` in `LikelihoodGrid.update` | default `0.05` in code path | Krypto | Comment is conflicted: code uses `params.get("alpha", 0.05)`, while comments discuss `0.0` for backward compatibility. Effective default is `0.05`. |
| `_LOC_08_CONFIDENCE_CUTOFF` | `vis_thresh` in calibration/session params | `0.5` | Krypto | `calibration.py` stores `"vis_thresh": 0.5`; `LikelihoodGrid.detect_peaks` has no explicit confidence cutoff parameter. Sprint plan target says `0.40`, which is not confirmed in legacy source. |
| `_LOC_RANSAC_ITERATIONS` | `RANSACLocalization.__init__(iterations)` | `100` | Krypto | Constructor default. |
| `_LOC_RANSAC_INLIER_THRESHOLD_DB` | `RANSACLocalization.__init__(inlier_thresh_dbm)` | `10.0 dBm` | Krypto | Inlier if absolute RSSI prediction error is `< 10.0`. |
| `_LOC_RANSAC_MIN_SAMPLES` | `RANSACLocalization.__init__(min_samples)` | `3` | Krypto | Also used as random sample size. |
| `_LOC_RANSAC_EARLY_EXIT_INLIER_RATIO` | hardcoded in `RANSACLocalization.fit` | `0.8` | no citation found | Early exit if `max_inliers > 0.8 * num_points`. |

## Section 4 - Enrichment Constants

| Constant name (new backend) | Legacy variable name | Legacy value | Current new value | Match? |
|---|---|---:|---:|---|
| `_ENR_02_TIME_WINDOW_MS` | `enrich_csv_with_pcap(..., tolerance_ms)` | `1000 ms` | `500 ms` | No |
| `_ENR_01_MATCH_THRESHOLD` | `NOT FOUND` | `NOT FOUND - legacy merge_asof uses nearest match inside tolerance, no score threshold` | `0.3` | Needs founder decision |

`ie_fingerprint` column format verdict: **MISMATCH - needs fix before Re-ID scoring is ported.**

- Legacy Scapy path writes `ie_fingerprint` as semicolon-separated `TAG:HEX` pairs: `"{eid}:{info.hex()};{eid}:{info.hex()}"`.
- Legacy parser expects the same format in `features.parse_ie_fingerprint`: split on `;`, then split each part on `:`, cast tag to integer, lowercase the hex string.
- New backend parser currently writes `ie_fingerprint` as pipe-separated `TAG:LENGTH` pairs in `backend/app/modules/enrichment/pcap_parser.py`, for example `1:8|50:12`.
- New backend therefore does **not** preserve IE hex content and does **not** use the legacy delimiter.
- Required change: new enrichment parser should emit `TAG:HEX;TAG:HEX;...` for compatibility. Re-ID can also add a defensive normalizer, but the primary fix belongs in enrichment because the legacy feature signal needs the IE bytes, not only lengths.

## Section 5 - Founder Decisions Required

## Decision: `_REID_ASSOCIATION_THRESHOLD`
Legacy value: `0.80`
New app value: `1.0`
Paper says: Bleach uses logistic/confidence scoring; exact threshold not confirmed from paper in local files.
Options: keep strict `1.0` / use legacy `0.80`
Recommendation: use legacy `0.80`; `1.0` makes real dynamic MAC association effectively unreachable.

## Decision: `_REID_WIFI_SEQ_GAP_MAX`
Legacy value: source condition `< 128`; summary/example says `50`
New app value: `1.0`
Paper says: Bleach summary in project PDF mentions sequence threshold around `64`.
Options: `50` / `64` / `128`
Recommendation: use `64` for paper alignment unless legacy field data shows `50` performs better; do not keep `1.0`.

## Decision: `_REID_WIFI_TIME_GAP_MAX_SEC`
Legacy value: `30 sec` appears in summary/examples, but not in dataclass source.
New app value: `1 ms` equivalent via `_REID_WIFI_02_MAX_ROTATION_TIME_WINDOW_MS = 1.0`
Paper says: no exact citation found in local source; project sprint says tunable `3-30 sec`.
Options: default `30 sec` / stricter `3-5 sec`
Recommendation: expose as tunable with default `30 sec` for field SAR scans, and allow strict mode for dense indoor data.

## Decision: `_REID_WIFI_STRICT_THRESHOLD`
Legacy value: `0.75` from confidence/strict summary, not a named source constant.
New app value: not implemented.
Paper says: no citation found in local source.
Options: implement confidence tiers only / implement strict threshold as parameter
Recommendation: implement confidence tiers (`high >= 0.75`, `medium 0.60-0.75`) first; avoid using strict threshold to drop associations until validated.

## Decision: `_REID_WIFI_BURST_WINDOW_SEC`
Legacy value: summary says `60 sec`; source file checked does not contain `group_bursts`.
New app value: not implemented.
Paper says: no exact citation found in local source.
Options: implement 60 sec burst grouping / defer until field validation
Recommendation: implement as tunable default `60 sec`, but mark source gap in final report.

## Decision: `_LOC_07_DYNAMIC_SIGMA_ALPHA`
Legacy value: effective default `0.05`
New app value: `0.0`
Paper says: Krypto-inspired dynamic uncertainty; exact alpha not cited in local source.
Options: keep disabled / enable `0.05`
Recommendation: enable `0.05` as sprint plan states, but include parameter in result snapshot for repeatability.

## Decision: `_LOC_08_CONFIDENCE_CUTOFF`
Legacy value: `0.5` appears as `vis_thresh`; sprint plan target says `0.40`
New app value: `0.0`
Paper says: no exact citation found in local source.
Options: `0.40` / `0.50`
Recommendation: use `0.40` for operational demo to avoid hiding plausible peaks; validate against ground truth before final claims.

## Decision: `_ENR_02_TIME_WINDOW_MS`
Legacy value: `1000 ms`
New app value: `500 ms`
Paper says: no citation found.
Options: keep `500 ms` / change to `1000 ms`
Recommendation: change to `1000 ms` for legacy compatibility, then validate match rate and false matches.

## Decision: `_ENR_01_MATCH_THRESHOLD`
Legacy value: `NOT FOUND`; legacy does nearest timestamp/MAC merge inside tolerance, not score-threshold filtering.
New app value: `0.3`
Paper says: no citation found.
Options: keep `0.3` / raise to `0.8` / remove threshold for legacy merge-equivalent behavior
Recommendation: do not blindly set `0.8`; first compare against legacy merge behavior on the same scan. For now, use `0.3` only as a new-backend heuristic and document it as non-legacy.
