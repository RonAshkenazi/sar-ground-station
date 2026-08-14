# RUN_LOG

C0-C3 ablation fieldwork, project P-2026-078. One `##` section per label, appended only —
existing sections are never rewritten or reordered. Every value is either copied verbatim
from its JSON source (key names unchanged) or explicitly marked `[MISSING: <key>]` /
`[NOT AVAILABLE: <reason>]`. No value in this file is inferred, interpolated, or guessed.

---

## S1-1_C0

### Session
```json
{
  "session_id": "68f426f6-f3e2-4067-bc75-affbd45478c5",
  "folder_id": "Scan - test protocol",
  "mode": "wifi",
  "created_at": "2026-08-13T19:39:42.662590+00:00"
}
```
- saved_id used (renamed from): `2026-08-13T20-00-36Z`
- saved_at_utc: `2026-08-13T20:00:36.037168Z`
- note: two additional saves (`2026-08-13T20-06-09Z`, `2026-08-13T20-06-13Z`) were created
  against this same session before this label was finalized; diffed byte-identical to the
  one kept (`calibration.json`, `localization.json` size, REID CSV) and were deleted by the
  operator. Save was already complete by the time "capture S1-1_C0" was sent, so this
  label's save was not triggered by the capture tool.

### Gate Check
- localization_result_exists_with_cluster: PASS (total_clusters=8, successful_clusters=1, failed_clusters=7)
- active_reid_csv_resolvable: PASS (`scan_S1_1_REID.csv`)
- ground_truth_exists: PASS (count=1)
- evaluation_exists: PASS (score.total=0.9933)

### Volatile Capture (live session state, pre/post-save — session still open)
```json
{
  "_pending_calibration": {
    "csv_filename": "scan_calib1.csv",
    "mac": "2c:59:8a:58:95:c1",
    "result.fit_quality": {
      "r2": 0.8397,
      "sample_count": 59,
      "inlier_count": 46,
      "inlier_ratio": 0.78,
      "sigma": 3.424
    },
    "result.scatter_point_count": 59
  },
  "active_enrichment.quality": "[MISSING: active_enrichment]",
  "active_reid.quality": {
    "total_rows": 118,
    "static_cluster_count": 7,
    "dynamic_cluster_count": 1,
    "unique_dynamic_mac_count": 6,
    "noise_cluster_count": 1,
    "cluster_confidence": {"1": "high"},
    "warnings": []
  },
  "current_localization_result.warnings": [
    "Cluster 1: RANSAC removed 4 outlier samples from cluster",
    "Cluster 1 uncertainty radius too large (200.9m, need <=35m)",
    "Cluster 2c:59:8a:58:95:c1: RANSAC removed 13 outlier samples from cluster",
    "Cluster 30:52:23:c0:f2:88 has insufficient samples",
    "Cluster 48:3f:da:2e:8b:23 has insufficient samples",
    "Cluster 9c:a3:a9:60:44:a4 insufficient movement (time=20.6s, need >=30s; baseline=19.0m, need >=5m)",
    "Cluster 9c:a3:a9:69:05:ef: RANSAC removed 12 outlier samples from cluster",
    "Cluster 9c:a3:a9:69:05:ef uncertainty radius too large (194.1m, need <=35m)",
    "Cluster bc:d5:ed:35:10:00 has insufficient samples",
    "Cluster e0:22:a1:ea:c7:24 has insufficient samples",
    "Noise cluster (1 rows) skipped - aggregate of unassociated MACs, not a single emitter"
  ],
  "execution_metadata": "[NOT AVAILABLE: no execution_id recoverable - current backend process (pid 15004) has no matching stdout/access log on disk; existing log files belong to a different, already-exited process]",
  "active_enriched_artifact": "C:\\projects\\test\\runtime\\DATA\\Scan - test protocol\\scan_S1_1_ENRICHED.csv",
  "active_reid_artifact": "C:\\projects\\test\\runtime\\DATA\\Scan - test protocol\\scan_S1_1_REID.csv"
}
```
Note: `active_enrichment` is absent as a key from session state entirely (not null) — this
session's `active_enriched_artifact` was activated as a pre-existing official artifact
rather than computed by an enrichment run in this session, so no `active_enrichment.quality`
block was ever produced for it to capture.

### REID CSV Stats (from saved copy, `scan_S1_1_REID.csv`)
```json
{
  "total_rows": 118,
  "distinct_src_mac": 14,
  "distinct_cluster_id": 9,
  "cluster_type_row_breakdown": {"static": 107, "dynamic": 10, "noise": 1},
  "per_cluster": [
    {"cluster_id": "1", "cluster_type": "dynamic", "row_count": 10, "distinct_src_mac": 6, "rssi_min": -85.0, "rssi_max": -76.0, "rssi_mean": -82.2},
    {"cluster_id": "2c:59:8a:58:95:c1", "cluster_type": "static", "row_count": 74, "distinct_src_mac": 1, "rssi_min": -87.0, "rssi_max": -48.0, "rssi_mean": -70.82432432432432},
    {"cluster_id": "30:52:23:c0:f2:88", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -88.0, "rssi_max": -88.0, "rssi_mean": -88.0},
    {"cluster_id": "48:3f:da:2e:8b:23", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -92.0, "rssi_max": -92.0, "rssi_mean": -92.0},
    {"cluster_id": "9c:a3:a9:60:44:a4", "cluster_type": "static", "row_count": 5, "distinct_src_mac": 1, "rssi_min": -87.0, "rssi_max": -84.0, "rssi_mean": -85.4},
    {"cluster_id": "9c:a3:a9:69:05:ef", "cluster_type": "static", "row_count": 23, "distinct_src_mac": 1, "rssi_min": -93.0, "rssi_max": -79.0, "rssi_mean": -85.73913043478261},
    {"cluster_id": "bc:d5:ed:35:10:00", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -89.0, "rssi_max": -85.0, "rssi_mean": -87.0},
    {"cluster_id": "e0:22:a1:ea:c7:24", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -87.0, "rssi_max": -87.0, "rssi_mean": -87.0},
    {"cluster_id": "noise", "cluster_type": "noise", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -88.0, "rssi_max": -88.0, "rssi_mean": -88.0}
  ]
}
```

### ENRICHED CSV Stats (live path — not copied to save dir)
Source: `C:\projects\test\runtime\DATA\Scan - test protocol\scan_S1_1_ENRICHED.csv`
```json
{
  "total_rows": 3521,
  "match_found_distribution": {"True": 3457, "False": 64},
  "match_found_rate": 0.981823345640443,
  "match_method_distribution": {"time_identity_best_match": 3457, "no_match": 64},
  "match_score": {"count": 3457, "missing": 64, "min": 1.999, "max": 2.5, "mean": 2.2429167196991613}
}
```

### Evaluation (`evaluation.json`, verbatim)
```json
{
  "metrics": {
    "recall": 1.0,
    "precision": 1.0,
    "coverage": 1.0,
    "median_error_m": 12.07,
    "p90_error_m": 12.07,
    "median_radius_m": 16.9,
    "count_error": 0
  },
  "score": {
    "total": 0.9933,
    "containment": 1.0,
    "distance": 0.9952,
    "count": 1.0,
    "radius": 0.9471
  },
  "eval_params": {
    "ratio_gate": 1.2,
    "max_match_dist_m": 30.0,
    "r_normalize_m": 30.0,
    "d_free_m": 10.0,
    "w_containment": 0.4,
    "w_distance": 0.3,
    "w_count": 0.2,
    "w_radius": 0.1,
    "min_reliable_samples": 10,
    "min_reliability_threshold": 0.3
  },
  "n_predictions": 1,
  "n_gt": 1
}
```

### Ground Truth (`ground_truth.json`, verbatim)
```json
[
  {
    "gt_id": "b06278b5-c15d-4392-95d2-4a372582889e",
    "lat": 31.280882213768113,
    "lon": 34.78731903260869,
    "label": "scan_GPS_S1"
  }
]
```

### Calibration (`calibration.json`, verbatim)
```json
{
  "parameter_source": "derived",
  "parameters": {
    "rssi_at_1m": -53.61,
    "path_loss_n": 1.5675,
    "sigma": 3.424
  },
  "approved": true,
  "calibration_csv_file": "scan_calib1.csv",
  "calibration_mac_address": "2c:59:8a:58:95:c1"
}
```

---

## S1-1_C1

**RETAKEN** — operator requested a redo on 2026-08-13 and asked me to verify the setup was
correct. Original capture (`saved_id=2026-08-13T20-14-04Z`, `gt_id=b06278b5-...`) has been
deleted from `Saved Scans/` at the operator's explicit request and is superseded below.

### Session
```json
{
  "session_id": "68f426f6-f3e2-4067-bc75-affbd45478c5",
  "folder_id": "Scan - test protocol",
  "mode": "wifi",
  "created_at": "2026-08-13T19:39:42.662590+00:00"
}
```
- saved_id used (renamed from): `2026-08-13T20-56-58Z`
- saved_at_utc: `2026-08-13T20:56:58.892184Z`
- note: same `session_id`, reused again after the S1-2 runs. By the time this capture was
  requested, the save already existed. Live session state at query time no longer matched
  it (had already moved on to S1-2's REID/calibration) - **this is expected for a retake
  read after the fact**, so this section's Volatile Capture fields below are taken from the
  save's own frozen files (`reid_quality.json`, `localization.json`, `evaluation.json`),
  not from a fresh live GET, except where noted.
- **verification requested ("check i did it right")**: diffed the retake's saved files
  against the original S1-1_C1 save. `calibration.json`, `scan_S1_1_REID.csv`, and
  `reid_quality.json` are byte-identical to the original. `localization.json` is identical
  size (210999 bytes) with identical `warnings` and cluster results. `evaluation.json`
  differs in exactly one field: `gt_id` (a freshly re-added GT point, new UUID, same
  lat/lon/label) - every metric and score value is unchanged. **Conclusion: yes, this was
  done right** - full reproduction of the original C1 config and result, calibration
  correctly distinct from C0's `"derived"` source (still `"fallback"/"open_field"`, as C1
  should be).

### Gate Check
- localization_result_exists_with_cluster: PASS (total_clusters=8, successful_clusters=3, failed_clusters=5)
- active_reid_csv_resolvable: PASS (`scan_S1_1_REID.csv`)
- ground_truth_exists: PASS (count=1)
- evaluation_exists: PASS (score.total=0.9248)

### Volatile Capture (sourced from the save's own frozen files, not a fresh live GET — see Session note above)
```json
{
  "_pending_calibration": "[NOT AVAILABLE: the fallback-preset endpoint used for this run's calibration (use_fallback()) never writes _pending_calibration, so there are no RANSAC fit diagnostics for a fallback config, structurally, regardless of what stale value might be sitting in the live session at any given moment. Not re-verified live for this retake since the session had already moved on to S1-2 by the time this was captured - the conclusion is unaffected either way.]",
  "active_enrichment.quality": "[MISSING: active_enrichment]",
  "active_reid.quality": {
    "total_rows": 118,
    "static_cluster_count": 7,
    "dynamic_cluster_count": 1,
    "unique_dynamic_mac_count": 6,
    "noise_cluster_count": 1,
    "cluster_confidence": {"1": "high"},
    "warnings": [],
    "note": "from this save's reid_quality.json (diff-verified byte-identical to both S1-1_C0's and the original S1-1_C1's) - Re-ID was not rerun for this retake"
  },
  "current_localization_result.warnings": [
    "Cluster 1: RANSAC found no valid inlier set for cluster; using all 10 samples",
    "Cluster 2c:59:8a:58:95:c1: RANSAC removed 26 outlier samples from cluster",
    "Cluster 30:52:23:c0:f2:88 has insufficient samples",
    "Cluster 48:3f:da:2e:8b:23 has insufficient samples",
    "Cluster 9c:a3:a9:60:44:a4 insufficient movement (time=20.6s, need >=30s; baseline=19.0m, need >=5m)",
    "Cluster 9c:a3:a9:69:05:ef: RANSAC found no valid inlier set for cluster; using all 23 samples",
    "Cluster bc:d5:ed:35:10:00 has insufficient samples",
    "Cluster e0:22:a1:ea:c7:24 has insufficient samples",
    "Noise cluster (1 rows) skipped - aggregate of unassociated MACs, not a single emitter"
  ],
  "execution_metadata": "[NOT AVAILABLE: no execution_id recoverable - current backend process (pid 15004) has no matching stdout/access log on disk; existing log files belong to a different, already-exited process]",
  "active_enriched_artifact": "C:\\projects\\test\\runtime\\DATA\\Scan - test protocol\\scan_S1_1_ENRICHED.csv",
  "active_reid_artifact": "C:\\projects\\test\\runtime\\DATA\\Scan - test protocol\\scan_S1_1_REID.csv"
}
```

### REID CSV Stats (from saved copy, `scan_S1_1_REID.csv` - byte-identical to S1-1_C0's and the original S1-1_C1's)
```json
{
  "total_rows": 118,
  "distinct_src_mac": 14,
  "distinct_cluster_id": 9,
  "cluster_type_row_breakdown": {"static": 107, "dynamic": 10, "noise": 1},
  "per_cluster": [
    {"cluster_id": "1", "cluster_type": "dynamic", "row_count": 10, "distinct_src_mac": 6, "rssi_min": -85.0, "rssi_max": -76.0, "rssi_mean": -82.2},
    {"cluster_id": "2c:59:8a:58:95:c1", "cluster_type": "static", "row_count": 74, "distinct_src_mac": 1, "rssi_min": -87.0, "rssi_max": -48.0, "rssi_mean": -70.82432432432432},
    {"cluster_id": "30:52:23:c0:f2:88", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -88.0, "rssi_max": -88.0, "rssi_mean": -88.0},
    {"cluster_id": "48:3f:da:2e:8b:23", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -92.0, "rssi_max": -92.0, "rssi_mean": -92.0},
    {"cluster_id": "9c:a3:a9:60:44:a4", "cluster_type": "static", "row_count": 5, "distinct_src_mac": 1, "rssi_min": -87.0, "rssi_max": -84.0, "rssi_mean": -85.4},
    {"cluster_id": "9c:a3:a9:69:05:ef", "cluster_type": "static", "row_count": 23, "distinct_src_mac": 1, "rssi_min": -93.0, "rssi_max": -79.0, "rssi_mean": -85.73913043478261},
    {"cluster_id": "bc:d5:ed:35:10:00", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -89.0, "rssi_max": -85.0, "rssi_mean": -87.0},
    {"cluster_id": "e0:22:a1:ea:c7:24", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -87.0, "rssi_max": -87.0, "rssi_mean": -87.0},
    {"cluster_id": "noise", "cluster_type": "noise", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -88.0, "rssi_max": -88.0, "rssi_mean": -88.0}
  ]
}
```

### ENRICHED CSV Stats (live path — not copied to save dir; unchanged mtime since S1-1_C0)
Source: `C:\projects\test\runtime\DATA\Scan - test protocol\scan_S1_1_ENRICHED.csv`
```json
{
  "total_rows": 3521,
  "match_found_distribution": {"True": 3457, "False": 64},
  "match_found_rate": 0.981823345640443,
  "match_method_distribution": {"time_identity_best_match": 3457, "no_match": 64},
  "match_score": {"count": 3457, "missing": 64, "min": 1.999, "max": 2.5, "mean": 2.2429167196991613}
}
```

### Evaluation (`evaluation.json`, verbatim)
```json
{
  "metrics": {
    "recall": 1.0,
    "precision": 1.0,
    "coverage": 1.0,
    "median_error_m": 16.99,
    "p90_error_m": 16.99,
    "median_radius_m": 33.03,
    "count_error": 0
  },
  "score": {
    "total": 0.9248,
    "containment": 1.0,
    "distance": 0.9456,
    "count": 1.0,
    "radius": 0.4106
  },
  "eval_params": {
    "ratio_gate": 1.2,
    "max_match_dist_m": 30.0,
    "r_normalize_m": 30.0,
    "d_free_m": 10.0,
    "w_containment": 0.4,
    "w_distance": 0.3,
    "w_count": 0.2,
    "w_radius": 0.1,
    "min_reliable_samples": 10,
    "min_reliability_threshold": 0.3
  },
  "n_predictions": 1,
  "n_gt": 1
}
```

### Ground Truth (`ground_truth.json`, verbatim)
```json
[
  {
    "gt_id": "aa282876-1df3-4879-9d04-53eb20f63787",
    "lat": 31.280882213768113,
    "lon": 34.78731903260869,
    "label": "scan_GPS_S1"
  }
]
```
Note: `gt_id` differs from the original S1-1_C1 (`b06278b5-...`) - a freshly re-added point,
same lat/lon/label. All evaluation metrics/scores are unaffected (see Session note above).

### Calibration (`calibration.json`, verbatim)
```json
{
  "parameter_source": "fallback",
  "parameters": {
    "rssi_at_1m": -40.0,
    "path_loss_n": 2.0,
    "sigma": 4.0
  },
  "approved": true,
  "calibration_csv_file": null,
  "calibration_mac_address": null,
  "parameter_set_name": "open_field"
}
```

---

## S1-2_C0

### Session
```json
{
  "session_id": "68f426f6-f3e2-4067-bc75-affbd45478c5",
  "folder_id": "Scan - test protocol",
  "mode": "wifi",
  "created_at": "2026-08-13T19:39:42.662590+00:00"
}
```
- saved_id used (renamed from): `2026-08-13T20-35-54Z`
- saved_at_utc: `2026-08-13T20:35:54.692581Z`
- note: same `session_id` reused again, active REID switched to `scan_S1_2_REID.csv` (a
  different capture than S1-1's `scan_S1_1_REID.csv`). Operator picked this REID file
  pre-built rather than deriving it in-session, so `active_enriched_artifact` in session
  state stayed stale on `scan_S1_1_ENRICHED.csv` throughout - confirmed with operator this
  is expected, not an error. Step-4 ENRICHED stats below use `scan_S1_2_ENRICHED.csv`
  instead (naming-matched to the REID file, per operator confirmation), not the stale
  session pointer.
- **correction during capture**: an earlier save (`2026-08-13T20-24-14Z`) for this label had
  `calibration.parameter_source="fallback"/"open_field"` - identical to S1-1_C1's
  calibration, not distinct as a `C0` config should be. Flagged to operator before logging;
  operator fixed calibration back to `"derived"` (`scan_calib1.csv`) and re-ran
  localization/evaluation. That earlier save was deleted by the operator; this section
  captures only the corrected save (`2026-08-13T20-35-54Z`). The stray save is not logged
  under any label.

### Gate Check
- localization_result_exists_with_cluster: PASS (total_clusters=8, successful_clusters=1, failed_clusters=7)
- active_reid_csv_resolvable: PASS (`scan_S1_2_REID.csv`)
- ground_truth_exists: PASS (count=1)
- evaluation_exists: PASS (score.total=0.9995)

### Volatile Capture (live session state, pre/post-save — session still open)
```json
{
  "_pending_calibration": {
    "csv_filename": "scan_calib1.csv",
    "mac": "2c:59:8a:58:95:c1",
    "result.fit_quality": {
      "r2": 0.8397,
      "sample_count": 59,
      "inlier_count": 46,
      "inlier_ratio": 0.78,
      "sigma": 3.424
    },
    "result.scatter_point_count": 59,
    "note": "identical fit_quality to S1-1_C0 - same calibration source csv/mac, deterministic RANSAC fit, genuinely recomputed for this run (parameter_source=derived confirms calibration/run+approve was actually called here, unlike S1-1_C1/the deleted mismatched S1-2_C0 attempt where it stayed on fallback)"
  },
  "active_enrichment.quality": "[MISSING: active_enrichment]",
  "active_reid.quality": {
    "reid_csv_path": "C:\\projects\\test\\runtime\\DATA\\Scan - test protocol\\scan_S1_2_REID.csv",
    "total_rows": 393,
    "static_cluster_count": 6,
    "dynamic_cluster_count": 2,
    "unique_dynamic_mac_count": 42,
    "noise_cluster_count": 1,
    "cluster_confidence": {"1": "high", "2": "high"},
    "warnings": []
  },
  "current_localization_result.warnings": [
    "Cluster 1: RANSAC removed 4 outlier samples from cluster",
    "Cluster 1 uncertainty radius too large (153.9m, need <=35m)",
    "Cluster 2: RANSAC removed 45 outlier samples from cluster",
    "Cluster 30:52:23:c0:f2:88 has insufficient samples",
    "Cluster 48:3f:da:2e:8b:23 has insufficient samples",
    "Cluster 9c:a3:a9:60:44:a4 insufficient movement (time=20.6s, need >=30s; baseline=19.0m, need >=5m)",
    "Cluster 9c:a3:a9:69:05:ef: RANSAC removed 12 outlier samples from cluster",
    "Cluster 9c:a3:a9:69:05:ef uncertainty radius too large (177.9m, need <=35m)",
    "Cluster bc:d5:ed:35:10:00 has insufficient samples",
    "Cluster e0:22:a1:ea:c7:24 has insufficient samples",
    "Noise cluster (1 rows) skipped - aggregate of unassociated MACs, not a single emitter"
  ],
  "execution_metadata": "[NOT AVAILABLE: no execution_id recoverable - current backend process (pid 15004) has no matching stdout/access log on disk; existing log files belong to a different, already-exited process]",
  "active_enriched_artifact_session_field": "C:\\projects\\test\\runtime\\DATA\\Scan - test protocol\\scan_S1_1_ENRICHED.csv [STALE - see note above, not used for stats below]",
  "active_reid_artifact": "C:\\projects\\test\\runtime\\DATA\\Scan - test protocol\\scan_S1_2_REID.csv"
}
```

### REID CSV Stats (from saved copy, `scan_S1_2_REID.csv`)
```json
{
  "total_rows": 393,
  "distinct_src_mac": 49,
  "distinct_cluster_id": 9,
  "cluster_type_row_breakdown": {"dynamic": 359, "static": 33, "noise": 1},
  "per_cluster": [
    {"cluster_id": "1", "cluster_type": "dynamic", "row_count": 10, "distinct_src_mac": 6, "rssi_min": -85.0, "rssi_max": -76.0, "rssi_mean": -82.2},
    {"cluster_id": "2", "cluster_type": "dynamic", "row_count": 349, "distinct_src_mac": 36, "rssi_min": -86.0, "rssi_max": -58.0, "rssi_mean": -71.73065902578797},
    {"cluster_id": "30:52:23:c0:f2:88", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -88.0, "rssi_max": -88.0, "rssi_mean": -88.0},
    {"cluster_id": "48:3f:da:2e:8b:23", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -92.0, "rssi_max": -92.0, "rssi_mean": -92.0},
    {"cluster_id": "9c:a3:a9:60:44:a4", "cluster_type": "static", "row_count": 5, "distinct_src_mac": 1, "rssi_min": -87.0, "rssi_max": -84.0, "rssi_mean": -85.4},
    {"cluster_id": "9c:a3:a9:69:05:ef", "cluster_type": "static", "row_count": 23, "distinct_src_mac": 1, "rssi_min": -93.0, "rssi_max": -79.0, "rssi_mean": -85.73913043478261},
    {"cluster_id": "bc:d5:ed:35:10:00", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -89.0, "rssi_max": -85.0, "rssi_mean": -87.0},
    {"cluster_id": "e0:22:a1:ea:c7:24", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -87.0, "rssi_max": -87.0, "rssi_mean": -87.0},
    {"cluster_id": "noise", "cluster_type": "noise", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -88.0, "rssi_max": -88.0, "rssi_mean": -88.0}
  ]
}
```

### ENRICHED CSV Stats (live path — not copied to save dir)
Source: `C:\projects\test\runtime\DATA\Scan - test protocol\scan_S1_2_ENRICHED.csv` (naming-matched to the REID artifact, not the stale session field - see Session note above)
```json
{
  "total_rows": 3796,
  "match_found_distribution": {"True": 3732, "False": 64},
  "match_found_rate": 0.9831401475237092,
  "match_method_distribution": {"time_identity_best_match": 3732, "no_match": 64},
  "match_score": {"count": 3732, "missing": 64, "min": 1.999, "max": 2.5, "mean": 2.2304754555198283}
}
```

### Evaluation (`evaluation.json`, verbatim)
```json
{
  "metrics": {
    "recall": 1.0,
    "precision": 1.0,
    "coverage": 1.0,
    "median_error_m": 11.04,
    "p90_error_m": 11.04,
    "median_radius_m": 11.08,
    "count_error": 0
  },
  "score": {
    "total": 0.9995,
    "containment": 1.0,
    "distance": 0.9988,
    "count": 1.0,
    "radius": 0.9987
  },
  "eval_params": {
    "ratio_gate": 1.2,
    "max_match_dist_m": 30.0,
    "r_normalize_m": 30.0,
    "d_free_m": 10.0,
    "w_containment": 0.4,
    "w_distance": 0.3,
    "w_count": 0.2,
    "w_radius": 0.1,
    "min_reliable_samples": 10,
    "min_reliability_threshold": 0.3
  },
  "n_predictions": 1,
  "n_gt": 1
}
```

### Ground Truth (`ground_truth.json`, verbatim)
```json
[
  {
    "gt_id": "367526e9-b7a3-45f9-ad77-cd3e7134b57c",
    "lat": 31.280882213768113,
    "lon": 34.78731903260869,
    "label": "scan_GPS_S1"
  }
]
```

### Calibration (`calibration.json`, verbatim)
```json
{
  "parameter_source": "derived",
  "parameters": {
    "rssi_at_1m": -53.61,
    "path_loss_n": 1.5675,
    "sigma": 3.424
  },
  "approved": true,
  "calibration_csv_file": "scan_calib1.csv",
  "calibration_mac_address": "2c:59:8a:58:95:c1"
}
```

---

## S1-2_C2

### Session
```json
{
  "session_id": "68f426f6-f3e2-4067-bc75-affbd45478c5",
  "folder_id": "Scan - test protocol",
  "mode": "wifi",
  "created_at": "2026-08-13T19:39:42.662590+00:00"
}
```
- saved_id used (renamed from): `2026-08-13T20-41-02Z`
- saved_at_utc: `2026-08-13T20:41:02.490662Z`
- note: same `session_id` again. `calibration.json`, `ground_truth.json`, `reid_quality.json`,
  and the REID CSV are all byte-identical to `S1-2_C0`'s (diff-verified) - only
  `localization.json` and `evaluation.json` differ, so whatever "C2" changes lives entirely
  in the localization stage, not calibration or Re-ID clustering.
- **unexplained observation, recorded as-is, not interpreted**: the single successful
  cluster in this run is `cluster_id="1"` with `sample_count=338`. In the REID CSV,
  `cluster_id="1"` (dynamic) has only 10 rows and `cluster_id="2"` (dynamic) has 349 rows -
  338 matches neither individually. Not guessing at a mechanism (e.g. a cross-cluster merge)
  - flagging the number mismatch in case it matters for your analysis.

### Gate Check
- localization_result_exists_with_cluster: PASS (total_clusters=1, successful_clusters=1, failed_clusters=0)
- active_reid_csv_resolvable: PASS (`scan_S1_2_REID.csv`)
- ground_truth_exists: PASS (count=1)
- evaluation_exists: PASS (score.total=0.9991)

### Volatile Capture (live session state, pre/post-save — session still open)
```json
{
  "_pending_calibration": {
    "csv_filename": "scan_calib1.csv",
    "mac": "2c:59:8a:58:95:c1",
    "result.fit_quality": {
      "r2": 0.8397,
      "sample_count": 59,
      "inlier_count": 46,
      "inlier_ratio": 0.78,
      "sigma": 3.424
    },
    "result.scatter_point_count": 59,
    "note": "unchanged from S1-2_C0 - calibration was never touched between the two runs"
  },
  "active_enrichment.quality": "[MISSING: active_enrichment]",
  "active_reid.quality": {
    "reid_csv_path": "C:\\projects\\test\\runtime\\DATA\\Scan - test protocol\\scan_S1_2_REID.csv",
    "total_rows": 393,
    "static_cluster_count": 6,
    "dynamic_cluster_count": 2,
    "unique_dynamic_mac_count": 42,
    "noise_cluster_count": 1,
    "cluster_confidence": {"1": "high", "2": "high"},
    "warnings": []
  },
  "current_localization_result.warnings": [
    "Cluster 1: RANSAC removed 55 outlier samples from cluster"
  ],
  "execution_metadata": "[NOT AVAILABLE: no execution_id recoverable - current backend process (pid 15004) has no matching stdout/access log on disk; existing log files belong to a different, already-exited process]",
  "active_enriched_artifact_session_field": "C:\\projects\\test\\runtime\\DATA\\Scan - test protocol\\scan_S1_1_ENRICHED.csv [STALE - unchanged from S1-2_C0, not used for stats below]",
  "active_reid_artifact": "C:\\projects\\test\\runtime\\DATA\\Scan - test protocol\\scan_S1_2_REID.csv"
}
```

### REID CSV Stats (from saved copy, `scan_S1_2_REID.csv` - byte-identical to S1-2_C0's)
```json
{
  "total_rows": 393,
  "distinct_src_mac": 49,
  "distinct_cluster_id": 9,
  "cluster_type_row_breakdown": {"dynamic": 359, "static": 33, "noise": 1},
  "per_cluster": [
    {"cluster_id": "1", "cluster_type": "dynamic", "row_count": 10, "distinct_src_mac": 6, "rssi_min": -85.0, "rssi_max": -76.0, "rssi_mean": -82.2},
    {"cluster_id": "2", "cluster_type": "dynamic", "row_count": 349, "distinct_src_mac": 36, "rssi_min": -86.0, "rssi_max": -58.0, "rssi_mean": -71.73065902578797},
    {"cluster_id": "30:52:23:c0:f2:88", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -88.0, "rssi_max": -88.0, "rssi_mean": -88.0},
    {"cluster_id": "48:3f:da:2e:8b:23", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -92.0, "rssi_max": -92.0, "rssi_mean": -92.0},
    {"cluster_id": "9c:a3:a9:60:44:a4", "cluster_type": "static", "row_count": 5, "distinct_src_mac": 1, "rssi_min": -87.0, "rssi_max": -84.0, "rssi_mean": -85.4},
    {"cluster_id": "9c:a3:a9:69:05:ef", "cluster_type": "static", "row_count": 23, "distinct_src_mac": 1, "rssi_min": -93.0, "rssi_max": -79.0, "rssi_mean": -85.73913043478261},
    {"cluster_id": "bc:d5:ed:35:10:00", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -89.0, "rssi_max": -85.0, "rssi_mean": -87.0},
    {"cluster_id": "e0:22:a1:ea:c7:24", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -87.0, "rssi_max": -87.0, "rssi_mean": -87.0},
    {"cluster_id": "noise", "cluster_type": "noise", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -88.0, "rssi_max": -88.0, "rssi_mean": -88.0}
  ]
}
```

### ENRICHED CSV Stats (live path — not copied to save dir; unchanged mtime since S1-2_C0)
Source: `C:\projects\test\runtime\DATA\Scan - test protocol\scan_S1_2_ENRICHED.csv`
```json
{
  "total_rows": 3796,
  "match_found_distribution": {"True": 3732, "False": 64},
  "match_found_rate": 0.9831401475237092,
  "match_method_distribution": {"time_identity_best_match": 3732, "no_match": 64},
  "match_score": {"count": 3732, "missing": 64, "min": 1.999, "max": 2.5, "mean": 2.2304754555198283}
}
```

### Evaluation (`evaluation.json`, verbatim)
```json
{
  "metrics": {
    "recall": 1.0,
    "precision": 1.0,
    "coverage": 1.0,
    "median_error_m": 11.04,
    "p90_error_m": 11.04,
    "median_radius_m": 12.22,
    "count_error": 0
  },
  "score": {
    "total": 0.9991,
    "containment": 1.0,
    "distance": 0.9988,
    "count": 1.0,
    "radius": 0.9945
  },
  "eval_params": {
    "ratio_gate": 1.2,
    "max_match_dist_m": 30.0,
    "r_normalize_m": 30.0,
    "d_free_m": 10.0,
    "w_containment": 0.4,
    "w_distance": 0.3,
    "w_count": 0.2,
    "w_radius": 0.1,
    "min_reliable_samples": 10,
    "min_reliability_threshold": 0.3
  },
  "n_predictions": 1,
  "n_gt": 1
}
```

### Ground Truth (`ground_truth.json`, verbatim)
```json
[
  {
    "gt_id": "367526e9-b7a3-45f9-ad77-cd3e7134b57c",
    "lat": 31.280882213768113,
    "lon": 34.78731903260869,
    "label": "scan_GPS_S1"
  }
]
```

### Calibration (`calibration.json`, verbatim)
```json
{
  "parameter_source": "derived",
  "parameters": {
    "rssi_at_1m": -53.61,
    "path_loss_n": 1.5675,
    "sigma": 3.424
  },
  "approved": true,
  "calibration_csv_file": "scan_calib1.csv",
  "calibration_mac_address": "2c:59:8a:58:95:c1"
}
```

---

## S2_C0

### Session
```json
{
  "session_id": "65488e21-612a-4c12-ab06-51c75ba9a192",
  "folder_id": "Scan - test protocol",
  "mode": "wifi",
  "created_at": "2026-08-14T07:46:43.866118+00:00"
}
```
- saved_id used (renamed from): `2026-08-14T07-52-28Z`
- saved_at_utc: `2026-08-14T07:52:28.889598Z`
- note: new session_id (first change since S1-1/S1-2), first session to touch `scan_S2_REID.csv`.
- important disambiguation: two save directories existed under `Scan - test protocol` when
  this capture started - `2026-08-13T21-34-51Z` and `2026-08-14T07-52-28Z`. Both had
  saved_artifacts.reid_csv=scan_S2_REID.csv and identical calibration/GT count, but their
  evaluation.json differ substantially: the earlier one had recall=0.6667, precision=0.6667,
  score.total=0.9186, an ambiguous_gts entry, and a duplicates entry (GT scan_GPS_sams
  competing with GT scan_GPS_s22 for cluster 8, unresolved); the later one has recall=1.0,
  precision=1.0, score.total=0.9892, no ambiguous_gts, no duplicates, and one match carries
  association_status=resolved_after_narrowing. Did not guess which one to use: the live
  session (65488e21, created_at=07:46:43) was created 6 minutes before the later save, and
  its live last_evaluation (recall=1.0, median_error_m=6.83, score.total=0.9892) matches the
  later save exactly. The earlier save's timing predates this session and belongs to a
  different, no-longer-resolvable session_id - not used here. Only `2026-08-14T07-52-28Z` is
  captured under this label; the earlier one is untouched on disk (not renamed, not deleted,
  not logged under any label) in case it matters - the pattern (unresolved conflict cleanly
  resolved) matches the shape of a conflict-resolution fix landing between the two saves
  (git status at the start of this session showed result_analysis/engine.py,
  result_analysis.py API, and a new reid_conflict_resolution_report.md all modified/added),
  but that is not asserted as confirmed cause, only the observed timing and data.
- active_reid_artifact and active_enriched_artifact are both null in this session's live
  state (never explicitly activated) - the save still resolved scan_S2_REID.csv via
  _find_reid_csv()'s DATA-folder mtime fallback, not the session field. As with the S1-2
  runs, ENRICHED stats below use the naming-matched scan_S2_ENRICHED.csv, not a session
  pointer (there is none to distrust or trust here - it is simply unset).

### Gate Check
- localization_result_exists_with_cluster: PASS (total_clusters=21, successful_clusters=8, failed_clusters=13)
- active_reid_csv_resolvable: PASS via DATA-folder fallback (`scan_S2_REID.csv`) - NOT via the literal active_reid_artifact session field, which is null (see Session note)
- ground_truth_exists: PASS (count=3)
- evaluation_exists: PASS (score.total=0.9892)

### Volatile Capture (live session state at query time)
```json
{
  "_pending_calibration": {
    "csv_filename": "scan_calib1.csv",
    "mac": "2c:59:8a:58:95:c1",
    "result.fit_quality": {
      "r2": 0.8397,
      "sample_count": 59,
      "inlier_count": 46,
      "inlier_ratio": 0.78,
      "sigma": 3.424
    },
    "result.scatter_point_count": 59,
    "note": "identical fit to every prior derived-calibration run in this log - same source csv/mac, deterministic RANSAC fit"
  },
  "active_enrichment.quality": "[MISSING: active_enrichment]",
  "active_reid.quality": "[MISSING: active_reid - key absent from session state; active_reid_artifact is also null. REID stats below are computed independently from the saved REID CSV file, not from this field.]",
  "current_localization_result.warnings": [
    "Cluster 0c:29:8f:8d:0d:8a has insufficient samples",
    "Cluster 1: RANSAC removed 23 outlier samples from cluster",
    "Cluster 1 uncertainty radius too large (48.2m, need <=35m)",
    "Cluster 10: RANSAC removed 22 outlier samples from cluster",
    "Cluster 10:2c:6b:e5:8b:a2 has insufficient samples",
    "Cluster 14:ea:63:f5:14:1f has insufficient samples",
    "Cluster 20:9b:e6:13:c0:82 has insufficient samples",
    "Cluster 2c:59:8a:58:95:c1: RANSAC removed 4 outlier samples from cluster",
    "Cluster 30:52:23:c0:f2:88 has insufficient samples",
    "Cluster 40:91:51:75:87:83 has insufficient samples",
    "Cluster 44:ef:bf:84:67:21 has insufficient samples",
    "Cluster 48:3f:da:2e:8b:23: RANSAC found no valid inlier set for cluster; using all 7 samples",
    "Cluster 64:bb:1e:54:a7:2e has insufficient samples",
    "Cluster 7: RANSAC removed 2 outlier samples from cluster",
    "Cluster 7 uncertainty radius too large (39.0m, need <=35m)",
    "Cluster 8: RANSAC removed 25 outlier samples from cluster",
    "Cluster 88:a2:9e:09:94:05 insufficient movement (time=0.2s, need >=30s; baseline=0.0m, need >=5m)",
    "Cluster 98:86:b1:03:35:8e has insufficient samples",
    "Cluster 9c:a3:a9:60:44:a4: RANSAC removed 13 outlier samples from cluster",
    "Cluster 9c:a3:a9:69:05:ef: RANSAC removed 17 outlier samples from cluster",
    "Cluster bc:89:f8:cd:18:8a: RANSAC found no valid inlier set for cluster; using all 12 samples",
    "Cluster e0:22:a1:ea:c7:24 has insufficient samples",
    "Noise cluster (12 rows) skipped - aggregate of unassociated MACs, not a single emitter"
  ],
  "execution_metadata": "[NOT AVAILABLE: no execution_id recoverable - current backend process (pid 15004) has no matching stdout/access log on disk; existing log files belong to a different, already-exited process]",
  "active_enriched_artifact": null,
  "active_reid_artifact": null
}
```

### REID CSV Stats (from saved copy, `scan_S2_REID.csv`)
```json
{
  "total_rows": 671,
  "distinct_src_mac": 140,
  "distinct_cluster_id": 22,
  "cluster_type_row_breakdown": {"dynamic": 467, "static": 192, "noise": 12},
  "per_cluster": [
    {"cluster_id": "0c:29:8f:8d:0d:8a", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -87.0, "rssi_max": -84.0, "rssi_mean": -85.5},
    {"cluster_id": "1", "cluster_type": "dynamic", "row_count": 163, "distinct_src_mac": 32, "rssi_min": -92.0, "rssi_max": -62.0, "rssi_mean": -79.6441717791411},
    {"cluster_id": "10", "cluster_type": "dynamic", "row_count": 85, "distinct_src_mac": 50, "rssi_min": -87.0, "rssi_max": -50.0, "rssi_mean": -67.08235294117647},
    {"cluster_id": "10:2c:6b:e5:8b:a2", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -82.0, "rssi_max": -82.0, "rssi_mean": -82.0},
    {"cluster_id": "14:ea:63:f5:14:1f", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -85.0, "rssi_max": -85.0, "rssi_mean": -85.0},
    {"cluster_id": "20:9b:e6:13:c0:82", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -87.0, "rssi_max": -86.0, "rssi_mean": -86.5},
    {"cluster_id": "2c:59:8a:58:95:c1", "cluster_type": "static", "row_count": 80, "distinct_src_mac": 1, "rssi_min": -89.0, "rssi_max": -56.0, "rssi_mean": -71.5625},
    {"cluster_id": "30:52:23:c0:f2:88", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -89.0, "rssi_max": -89.0, "rssi_mean": -89.0},
    {"cluster_id": "40:91:51:75:87:83", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -92.0, "rssi_max": -87.0, "rssi_mean": -89.5},
    {"cluster_id": "44:ef:bf:84:67:21", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -88.0, "rssi_max": -88.0, "rssi_mean": -88.0},
    {"cluster_id": "48:3f:da:2e:8b:23", "cluster_type": "static", "row_count": 7, "distinct_src_mac": 1, "rssi_min": -93.0, "rssi_max": -85.0, "rssi_mean": -89.14285714285714},
    {"cluster_id": "64:bb:1e:54:a7:2e", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -88.0, "rssi_max": -88.0, "rssi_mean": -88.0},
    {"cluster_id": "6c:22:1a:c5:fa:82", "cluster_type": "static", "row_count": 7, "distinct_src_mac": 1, "rssi_min": -93.0, "rssi_max": -87.0, "rssi_mean": -90.14285714285714},
    {"cluster_id": "7", "cluster_type": "dynamic", "row_count": 12, "distinct_src_mac": 7, "rssi_min": -83.0, "rssi_max": -59.0, "rssi_mean": -73.0},
    {"cluster_id": "8", "cluster_type": "dynamic", "row_count": 207, "distinct_src_mac": 28, "rssi_min": -90.0, "rssi_max": -58.0, "rssi_mean": -73.31884057971014},
    {"cluster_id": "88:a2:9e:09:94:05", "cluster_type": "static", "row_count": 6, "distinct_src_mac": 1, "rssi_min": -44.0, "rssi_max": -35.0, "rssi_mean": -38.0},
    {"cluster_id": "98:86:b1:03:35:8e", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -89.0, "rssi_max": -84.0, "rssi_mean": -86.5},
    {"cluster_id": "9c:a3:a9:60:44:a4", "cluster_type": "static", "row_count": 17, "distinct_src_mac": 1, "rssi_min": -90.0, "rssi_max": -85.0, "rssi_mean": -87.0},
    {"cluster_id": "9c:a3:a9:69:05:ef", "cluster_type": "static", "row_count": 49, "distinct_src_mac": 1, "rssi_min": -92.0, "rssi_max": -77.0, "rssi_mean": -85.61224489795919},
    {"cluster_id": "bc:89:f8:cd:18:8a", "cluster_type": "static", "row_count": 12, "distinct_src_mac": 1, "rssi_min": -91.0, "rssi_max": -84.0, "rssi_mean": -87.25},
    {"cluster_id": "e0:22:a1:ea:c7:24", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -89.0, "rssi_max": -89.0, "rssi_mean": -89.0},
    {"cluster_id": "noise", "cluster_type": "noise", "row_count": 12, "distinct_src_mac": 6, "rssi_min": -89.0, "rssi_max": -79.0, "rssi_mean": -83.83333333333333}
  ]
}
```

### ENRICHED CSV Stats (live path — not copied to save dir)
Source: `C:\projects\test\runtime\DATA\Scan - test protocol\scan_S2_ENRICHED.csv` (naming-matched to the REID artifact; session has no active_enriched_artifact set at all - see Session note)
```json
{
  "total_rows": 5844,
  "match_found_distribution": {"True": 5614, "False": 230},
  "match_found_rate": 0.9606433949349761,
  "match_method_distribution": {"time_identity_best_match": 5614, "no_match": 230},
  "match_score": {"count": 5614, "missing": 230, "min": 1.999, "max": 2.5, "mean": 2.221775846099038}
}
```

### Evaluation (`evaluation.json`, verbatim)
```json
{
  "matches": [
    {"gt_id": "498be881-9ec4-4f79-9402-624c828ef796", "gt_label": "scan_GPS_s22", "primary_cluster_id": "10", "cluster_type": "dynamic", "num_samples": 63, "uncertainty_radius_m": 12.329, "distance_m": 2.1622392453671386, "covered": true, "dominance_margin": 2.78, "association_status": "clear_match"},
    {"gt_id": "32cb6427-0631-4e98-8101-6d153646b2b8", "gt_label": "scan_GPS_LG", "primary_cluster_id": "2c:59:8a:58:95:c1", "cluster_type": "static", "num_samples": 76, "uncertainty_radius_m": 19.871, "distance_m": 6.834129310619165, "covered": true, "dominance_margin": 4.043, "association_status": "clear_match"},
    {"gt_id": "15dbf9a5-15f1-4633-9464-a74f8efd29b2", "gt_label": "scan_GPS_sams", "primary_cluster_id": "8", "cluster_type": "dynamic", "num_samples": 182, "uncertainty_radius_m": 31.249, "distance_m": 25.928332085435915, "covered": true, "dominance_margin": 1.011, "association_status": "resolved_after_narrowing"}
  ],
  "false_positives": [],
  "false_negatives": [],
  "ambiguous_gts": [],
  "duplicates": [],
  "possible_merges": [
    {"cluster_id": "10", "candidate_gt_ids": ["32cb6427-0631-4e98-8101-6d153646b2b8", "15dbf9a5-15f1-4633-9464-a74f8efd29b2", "498be881-9ec4-4f79-9402-624c828ef796"], "distances_m": [27.632757809554683, 26.225169301492766, 2.1622392453671386]},
    {"cluster_id": "8", "candidate_gt_ids": ["15dbf9a5-15f1-4633-9464-a74f8efd29b2", "498be881-9ec4-4f79-9402-624c828ef796"], "distances_m": [25.928332085435915, 6.010044812965198]}
  ],
  "metrics": {"recall": 1.0, "precision": 1.0, "coverage": 1.0, "median_error_m": 6.83, "p90_error_m": 25.93, "median_radius_m": 19.87, "count_error": 0},
  "score": {"total": 0.9892, "containment": 1.0, "distance": 1.0, "count": 1.0, "radius": 0.8917},
  "eval_params": {
    "ratio_gate": 1.2,
    "max_match_dist_m": 30.0,
    "r_normalize_m": 30.0,
    "d_free_m": 10.0,
    "w_containment": 0.4,
    "w_distance": 0.3,
    "w_count": 0.2,
    "w_radius": 0.1,
    "min_reliable_samples": 10,
    "min_reliability_threshold": 0.3
  },
  "n_predictions": 3,
  "n_gt": 3
}
```

### Ground Truth (`ground_truth.json`, verbatim)
```json
[
  {"gt_id": "32cb6427-0631-4e98-8101-6d153646b2b8", "lat": 31.28087521018934, "lon": 34.78770612925769, "label": "scan_GPS_LG"},
  {"gt_id": "15dbf9a5-15f1-4633-9464-a74f8efd29b2", "lat": 31.280963255494484, "lon": 34.78742455769234, "label": "scan_GPS_sams"},
  {"gt_id": "498be881-9ec4-4f79-9402-624c828ef796", "lat": 31.280749738095224, "lon": 34.78746577619051, "label": "scan_GPS_s22"}
]
```

### Calibration (`calibration.json`, verbatim)
```json
{
  "parameter_source": "derived",
  "parameters": {
    "rssi_at_1m": -53.61,
    "path_loss_n": 1.5675,
    "sigma": 3.424
  },
  "approved": true,
  "calibration_csv_file": "scan_calib1.csv",
  "calibration_mac_address": "2c:59:8a:58:95:c1"
}
```

---

## S2_C1

### Session
```json
{
  "session_id": "82794d95-b12c-49ac-bb82-87129172e7bc",
  "folder_id": "Scan - test protocol",
  "mode": "wifi",
  "created_at": "2026-08-14T08:08:43.440602+00:00"
}
```
- saved_id used (renamed from): `2026-08-14T08-11-42Z`
- saved_at_utc: `2026-08-14T08:11:42.574247Z`
- note: third session_id in this log (new session for this label). Calibration switched
  derived -> fallback/open_field for C1, same as the S1-1 and S1-2 C0->C1 pattern.
  Enrichment untouched (operator: "it wont change anything in the result").
- **corrected retry, recorded for the audit trail**: a first save attempt for this label
  (`saved_id=2026-08-14T08-02-59Z`, session `65488e21-...`) bundled the wrong REID artifact -
  `scan_S2_(single cluster)_REID.csv` (671 rows all under one `cluster_id`) - picked by
  `_find_reid_csv()`'s DATA-folder mtime fallback because that file happened to be newer,
  even though `localization.json` in that same save was actually computed against the
  ordinary `scan_S2_REID.csv` (21-cluster structure, cross-checked and confirmed matching).
  Operator confirmed intent was `scan_S2_REID.csv` throughout, re-selected it explicitly
  (this session's `active_reid_artifact` is set, not null, unlike every prior S2 run) and
  re-saved. Verified this save's `localization.json`, `calibration.json` are byte-identical
  to the first attempt's (same underlying computation) - only `ground_truth.json`/
  `evaluation.json` differ, and only by `gt_id` (freshly re-added points, same
  lat/lon/labels/scores). **The mismatched first attempt is left untouched on disk
  (`2026-08-14T08-02-59Z`), not renamed, not logged under any label.**

### Gate Check
- localization_result_exists_with_cluster: PASS (total_clusters=21, successful_clusters=8, failed_clusters=13)
- active_reid_csv_resolvable: PASS (`scan_S2_REID.csv`, via explicit `active_reid_artifact` this time, not a fallback guess)
- ground_truth_exists: PASS (count=3)
- evaluation_exists: PASS (score.total=0.8234)

### Volatile Capture (live session state at query time)
```json
{
  "_pending_calibration": "[NOT AVAILABLE: session did compute a derived fit earlier (csv=scan_calib1.csv, mac=2c:59:8a:58:95:c1, fit_quality.r2=0.8397 - identical to every prior derived run in this log) before switching to the fallback preset for C1. Since the fallback endpoint never overwrites _pending_calibration, this stale derived-fit value is still sitting in session state, but it does not correspond to the active fallback/open_field calibration actually used for this run - not reported as this run's value, same reasoning as S1-1_C1.]",
  "active_enrichment.quality": "[MISSING: active_enrichment]",
  "active_reid.quality": {
    "reid_csv_path": "C:\\projects\\test\\runtime\\DATA\\Scan - test protocol\\scan_S2_REID.csv",
    "total_rows": 671,
    "static_cluster_count": 17,
    "dynamic_cluster_count": 4,
    "unique_dynamic_mac_count": 117,
    "noise_cluster_count": 6,
    "cluster_confidence": {"1": "high", "7": "high", "8": "high", "10": "high"},
    "warnings": []
  },
  "current_localization_result.warnings": [
    "Cluster 0c:29:8f:8d:0d:8a has insufficient samples",
    "Cluster 1: RANSAC removed 74 outlier samples from cluster",
    "Cluster 1 uncertainty radius too large (46.8m, need <=35m)",
    "Cluster 10: RANSAC removed 22 outlier samples from cluster",
    "Cluster 10:2c:6b:e5:8b:a2 has insufficient samples",
    "Cluster 14:ea:63:f5:14:1f has insufficient samples",
    "Cluster 20:9b:e6:13:c0:82 has insufficient samples",
    "Cluster 2c:59:8a:58:95:c1: RANSAC removed 28 outlier samples from cluster",
    "Cluster 2c:59:8a:58:95:c1 uncertainty radius too large (59.8m, need <=35m)",
    "Cluster 30:52:23:c0:f2:88 has insufficient samples",
    "Cluster 40:91:51:75:87:83 has insufficient samples",
    "Cluster 44:ef:bf:84:67:21 has insufficient samples",
    "Cluster 64:bb:1e:54:a7:2e has insufficient samples",
    "Cluster 7: RANSAC removed 4 outlier samples from cluster",
    "Cluster 8: RANSAC removed 89 outlier samples from cluster",
    "Cluster 88:a2:9e:09:94:05 insufficient movement (time=0.2s, need >=30s; baseline=0.0m, need >=5m)",
    "Cluster 98:86:b1:03:35:8e has insufficient samples",
    "Cluster 9c:a3:a9:69:05:ef: RANSAC removed 41 outlier samples from cluster",
    "Cluster e0:22:a1:ea:c7:24 has insufficient samples",
    "Noise cluster (12 rows) skipped - aggregate of unassociated MACs, not a single emitter"
  ],
  "execution_metadata": "[NOT AVAILABLE: no execution_id recoverable - current backend process (pid 15004) has no matching stdout/access log on disk; existing log files belong to a different, already-exited process]",
  "active_enriched_artifact": null,
  "active_reid_artifact": "C:\\projects\\test\\runtime\\DATA\\Scan - test protocol\\scan_S2_REID.csv"
}
```

### REID CSV Stats (from saved copy, `scan_S2_REID.csv` - byte-identical to S2_C0's)
```json
{
  "total_rows": 671,
  "distinct_src_mac": 140,
  "distinct_cluster_id": 22,
  "cluster_type_row_breakdown": {"dynamic": 467, "static": 192, "noise": 12},
  "per_cluster": [
    {"cluster_id": "0c:29:8f:8d:0d:8a", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -87.0, "rssi_max": -84.0, "rssi_mean": -85.5},
    {"cluster_id": "1", "cluster_type": "dynamic", "row_count": 163, "distinct_src_mac": 32, "rssi_min": -92.0, "rssi_max": -62.0, "rssi_mean": -79.6441717791411},
    {"cluster_id": "10", "cluster_type": "dynamic", "row_count": 85, "distinct_src_mac": 50, "rssi_min": -87.0, "rssi_max": -50.0, "rssi_mean": -67.08235294117647},
    {"cluster_id": "10:2c:6b:e5:8b:a2", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -82.0, "rssi_max": -82.0, "rssi_mean": -82.0},
    {"cluster_id": "14:ea:63:f5:14:1f", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -85.0, "rssi_max": -85.0, "rssi_mean": -85.0},
    {"cluster_id": "20:9b:e6:13:c0:82", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -87.0, "rssi_max": -86.0, "rssi_mean": -86.5},
    {"cluster_id": "2c:59:8a:58:95:c1", "cluster_type": "static", "row_count": 80, "distinct_src_mac": 1, "rssi_min": -89.0, "rssi_max": -56.0, "rssi_mean": -71.5625},
    {"cluster_id": "30:52:23:c0:f2:88", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -89.0, "rssi_max": -89.0, "rssi_mean": -89.0},
    {"cluster_id": "40:91:51:75:87:83", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -92.0, "rssi_max": -87.0, "rssi_mean": -89.5},
    {"cluster_id": "44:ef:bf:84:67:21", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -88.0, "rssi_max": -88.0, "rssi_mean": -88.0},
    {"cluster_id": "48:3f:da:2e:8b:23", "cluster_type": "static", "row_count": 7, "distinct_src_mac": 1, "rssi_min": -93.0, "rssi_max": -85.0, "rssi_mean": -89.14285714285714},
    {"cluster_id": "64:bb:1e:54:a7:2e", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -88.0, "rssi_max": -88.0, "rssi_mean": -88.0},
    {"cluster_id": "6c:22:1a:c5:fa:82", "cluster_type": "static", "row_count": 7, "distinct_src_mac": 1, "rssi_min": -93.0, "rssi_max": -87.0, "rssi_mean": -90.14285714285714},
    {"cluster_id": "7", "cluster_type": "dynamic", "row_count": 12, "distinct_src_mac": 7, "rssi_min": -83.0, "rssi_max": -59.0, "rssi_mean": -73.0},
    {"cluster_id": "8", "cluster_type": "dynamic", "row_count": 207, "distinct_src_mac": 28, "rssi_min": -90.0, "rssi_max": -58.0, "rssi_mean": -73.31884057971014},
    {"cluster_id": "88:a2:9e:09:94:05", "cluster_type": "static", "row_count": 6, "distinct_src_mac": 1, "rssi_min": -44.0, "rssi_max": -35.0, "rssi_mean": -38.0},
    {"cluster_id": "98:86:b1:03:35:8e", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -89.0, "rssi_max": -84.0, "rssi_mean": -86.5},
    {"cluster_id": "9c:a3:a9:60:44:a4", "cluster_type": "static", "row_count": 17, "distinct_src_mac": 1, "rssi_min": -90.0, "rssi_max": -85.0, "rssi_mean": -87.0},
    {"cluster_id": "9c:a3:a9:69:05:ef", "cluster_type": "static", "row_count": 49, "distinct_src_mac": 1, "rssi_min": -92.0, "rssi_max": -77.0, "rssi_mean": -85.61224489795919},
    {"cluster_id": "bc:89:f8:cd:18:8a", "cluster_type": "static", "row_count": 12, "distinct_src_mac": 1, "rssi_min": -91.0, "rssi_max": -84.0, "rssi_mean": -87.25},
    {"cluster_id": "e0:22:a1:ea:c7:24", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -89.0, "rssi_max": -89.0, "rssi_mean": -89.0},
    {"cluster_id": "noise", "cluster_type": "noise", "row_count": 12, "distinct_src_mac": 6, "rssi_min": -89.0, "rssi_max": -79.0, "rssi_mean": -83.83333333333333}
  ]
}
```

### ENRICHED CSV Stats (live path — not copied to save dir; unchanged mtime since S2_C0)
Source: `C:\projects\test\runtime\DATA\Scan - test protocol\scan_S2_ENRICHED.csv`
```json
{
  "total_rows": 5844,
  "match_found_distribution": {"True": 5614, "False": 230},
  "match_found_rate": 0.9606433949349761,
  "match_method_distribution": {"time_identity_best_match": 5614, "no_match": 230},
  "match_score": {"count": 5614, "missing": 230, "min": 1.999, "max": 2.5, "mean": 2.221775846099038}
}
```

### Evaluation (`evaluation.json`, verbatim)
```json
{
  "matches": [
    {"gt_id": "4809ea40-9d2a-4203-b5ac-54dc07f21ac6", "gt_label": "scan_GPS_LG", "primary_cluster_id": "10", "cluster_type": "dynamic", "num_samples": 63, "uncertainty_radius_m": 20.611, "distance_m": 17.353104441953008, "covered": true, "dominance_margin": 2.344, "association_status": "clear_match"},
    {"gt_id": "b4d6df22-f82d-4633-9c66-16594278c88a", "gt_label": "scan_GPS_s22", "primary_cluster_id": "7", "cluster_type": "dynamic", "num_samples": 8, "uncertainty_radius_m": 14.67, "distance_m": 22.715184004813853, "covered": false, "dominance_margin": 2.158, "association_status": "clear_match"},
    {"gt_id": "004fd208-dbb1-4697-ba93-8708fe44d615", "gt_label": "scan_GPS_sams", "primary_cluster_id": "8", "cluster_type": "dynamic", "num_samples": 118, "uncertainty_radius_m": 24.506, "distance_m": 19.599110803420626, "covered": true, "dominance_margin": 1.331, "association_status": "clear_match"}
  ],
  "false_positives": [],
  "false_negatives": [],
  "ambiguous_gts": [],
  "duplicates": [],
  "possible_merges": [
    {"cluster_id": "10", "candidate_gt_ids": ["4809ea40-9d2a-4203-b5ac-54dc07f21ac6", "b4d6df22-f82d-4633-9c66-16594278c88a", "004fd208-dbb1-4697-ba93-8708fe44d615"], "distances_m": [17.353104441953008, 10.526926451280632, 26.089033645598523]},
    {"cluster_id": "8", "candidate_gt_ids": ["b4d6df22-f82d-4633-9c66-16594278c88a", "004fd208-dbb1-4697-ba93-8708fe44d615"], "distances_m": [22.96995309826459, 19.599110803420626]}
  ],
  "metrics": {"recall": 1.0, "precision": 1.0, "coverage": 0.6667, "median_error_m": 19.6, "p90_error_m": 22.72, "median_radius_m": 20.61, "count_error": 0},
  "score": {"total": 0.8234, "containment": 0.6667, "distance": 0.8976, "count": 1.0, "radius": 0.8749},
  "eval_params": {
    "ratio_gate": 1.2,
    "max_match_dist_m": 30.0,
    "r_normalize_m": 30.0,
    "d_free_m": 10.0,
    "w_containment": 0.4,
    "w_distance": 0.3,
    "w_count": 0.2,
    "w_radius": 0.1,
    "min_reliable_samples": 10,
    "min_reliability_threshold": 0.3
  },
  "n_predictions": 3,
  "n_gt": 3
}
```

### Ground Truth (`ground_truth.json`, verbatim)
```json
[
  {"gt_id": "4809ea40-9d2a-4203-b5ac-54dc07f21ac6", "lat": 31.28087521018934, "lon": 34.78770612925769, "label": "scan_GPS_LG"},
  {"gt_id": "b4d6df22-f82d-4633-9c66-16594278c88a", "lat": 31.280749738095224, "lon": 34.78746577619051, "label": "scan_GPS_s22"},
  {"gt_id": "004fd208-dbb1-4697-ba93-8708fe44d615", "lat": 31.280963255494484, "lon": 34.78742455769234, "label": "scan_GPS_sams"}
]
```

### Calibration (`calibration.json`, verbatim)
```json
{
  "parameter_source": "fallback",
  "parameters": {
    "rssi_at_1m": -40.0,
    "path_loss_n": 2.0,
    "sigma": 4.0
  },
  "approved": true,
  "calibration_csv_file": null,
  "calibration_mac_address": null,
  "parameter_set_name": "open_field"
}
```

---

## S2_C2

### Session
```json
{
  "session_id": "84a7ac99-1083-4d39-90ca-f0c3c475a872",
  "folder_id": "Scan - test protocol",
  "mode": "wifi",
  "created_at": "2026-08-14T08:14:45.382166+00:00"
}
```
- saved_id used (renamed from): `2026-08-14T08-17-03Z`
- saved_at_utc: `2026-08-14T08:17:03.382243Z`
- note: fourth session_id in this log. Calibration back to `"derived"`/`scan_calib1.csv`,
  byte-identical to S2_C0's `calibration.json` - matches the established C0/C2-share-calibration
  pattern from S1-2. `scan_S2_REID.csv` diff-verified byte-identical to S2_C0/S2_C1's copy.
  Only `localization.json` and `evaluation.json` differ from S2_C0, same as the S1-2 C0/C2 pair.
- **same unexplained-but-now-repeated pattern as S1-2_C2**: the single successful cluster is
  `cluster_id="1"` with `sample_count=498` (RANSAC then removed 173 outliers from it). In the
  REID CSV, `cluster_id="1"` alone only has 163 rows; no single cluster or straightforward
  combination of clusters in the REID CSV sums to 498 either. This is the same shape of
  discrepancy flagged in S1-2_C2 (there: cluster "1"/338 samples, REID's cluster "1" had 10
  rows) - now observed on a second, unrelated scan (S2) under the same C2 label, which is
  circumstantial support for "C2 does something structural to how clusters get pooled for
  localization" as a real, repeatable behavior rather than a one-off glitch. Still not
  asserting a mechanism - recording the observation and the recurrence.
- `active_reid_artifact` is `null` in this session's live state again (same as every other
  S2 session so far except S2_C1, where it was explicitly set) - save resolved
  `scan_S2_REID.csv` via the DATA-folder mtime fallback, verified correct this time (no
  competing newer `*_REID.csv` file existed at save time).

### Gate Check
- localization_result_exists_with_cluster: PASS (total_clusters=1, successful_clusters=1, failed_clusters=0)
- active_reid_csv_resolvable: PASS via DATA-folder fallback (`scan_S2_REID.csv`) - active_reid_artifact session field is `null`
- ground_truth_exists: PASS (count=3)
- evaluation_exists: PASS (score.total=0.7667)

### Volatile Capture (live session state at query time)
```json
{
  "_pending_calibration": {
    "csv_filename": "scan_calib1.csv",
    "mac": "2c:59:8a:58:95:c1",
    "result.fit_quality": {
      "r2": 0.8397,
      "sample_count": 59,
      "inlier_count": 46,
      "inlier_ratio": 0.78,
      "sigma": 3.424
    },
    "note": "matches active_calibration (both derived/scan_calib1.csv) - not stale this time"
  },
  "active_enrichment.quality": "[MISSING: active_enrichment]",
  "active_reid.quality": "[MISSING: active_reid - key absent from session state; active_reid_artifact is also null. REID stats below are computed independently from the saved REID CSV file.]",
  "current_localization_result.warnings": [
    "Cluster 1: RANSAC removed 173 outlier samples from cluster"
  ],
  "execution_metadata": "[NOT AVAILABLE: no execution_id recoverable - current backend process (pid 15004) has no matching stdout/access log on disk; existing log files belong to a different, already-exited process]",
  "active_enriched_artifact": null,
  "active_reid_artifact": null
}
```

### REID CSV Stats (from saved copy, `scan_S2_REID.csv` - byte-identical to S2_C0/S2_C1's)
```json
{
  "total_rows": 671,
  "distinct_src_mac": 140,
  "distinct_cluster_id": 22,
  "cluster_type_row_breakdown": {"dynamic": 467, "static": 192, "noise": 12},
  "per_cluster": [
    {"cluster_id": "0c:29:8f:8d:0d:8a", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -87.0, "rssi_max": -84.0, "rssi_mean": -85.5},
    {"cluster_id": "1", "cluster_type": "dynamic", "row_count": 163, "distinct_src_mac": 32, "rssi_min": -92.0, "rssi_max": -62.0, "rssi_mean": -79.6441717791411},
    {"cluster_id": "10", "cluster_type": "dynamic", "row_count": 85, "distinct_src_mac": 50, "rssi_min": -87.0, "rssi_max": -50.0, "rssi_mean": -67.08235294117647},
    {"cluster_id": "10:2c:6b:e5:8b:a2", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -82.0, "rssi_max": -82.0, "rssi_mean": -82.0},
    {"cluster_id": "14:ea:63:f5:14:1f", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -85.0, "rssi_max": -85.0, "rssi_mean": -85.0},
    {"cluster_id": "20:9b:e6:13:c0:82", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -87.0, "rssi_max": -86.0, "rssi_mean": -86.5},
    {"cluster_id": "2c:59:8a:58:95:c1", "cluster_type": "static", "row_count": 80, "distinct_src_mac": 1, "rssi_min": -89.0, "rssi_max": -56.0, "rssi_mean": -71.5625},
    {"cluster_id": "30:52:23:c0:f2:88", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -89.0, "rssi_max": -89.0, "rssi_mean": -89.0},
    {"cluster_id": "40:91:51:75:87:83", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -92.0, "rssi_max": -87.0, "rssi_mean": -89.5},
    {"cluster_id": "44:ef:bf:84:67:21", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -88.0, "rssi_max": -88.0, "rssi_mean": -88.0},
    {"cluster_id": "48:3f:da:2e:8b:23", "cluster_type": "static", "row_count": 7, "distinct_src_mac": 1, "rssi_min": -93.0, "rssi_max": -85.0, "rssi_mean": -89.14285714285714},
    {"cluster_id": "64:bb:1e:54:a7:2e", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -88.0, "rssi_max": -88.0, "rssi_mean": -88.0},
    {"cluster_id": "6c:22:1a:c5:fa:82", "cluster_type": "static", "row_count": 7, "distinct_src_mac": 1, "rssi_min": -93.0, "rssi_max": -87.0, "rssi_mean": -90.14285714285714},
    {"cluster_id": "7", "cluster_type": "dynamic", "row_count": 12, "distinct_src_mac": 7, "rssi_min": -83.0, "rssi_max": -59.0, "rssi_mean": -73.0},
    {"cluster_id": "8", "cluster_type": "dynamic", "row_count": 207, "distinct_src_mac": 28, "rssi_min": -90.0, "rssi_max": -58.0, "rssi_mean": -73.31884057971014},
    {"cluster_id": "88:a2:9e:09:94:05", "cluster_type": "static", "row_count": 6, "distinct_src_mac": 1, "rssi_min": -44.0, "rssi_max": -35.0, "rssi_mean": -38.0},
    {"cluster_id": "98:86:b1:03:35:8e", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -89.0, "rssi_max": -84.0, "rssi_mean": -86.5},
    {"cluster_id": "9c:a3:a9:60:44:a4", "cluster_type": "static", "row_count": 17, "distinct_src_mac": 1, "rssi_min": -90.0, "rssi_max": -85.0, "rssi_mean": -87.0},
    {"cluster_id": "9c:a3:a9:69:05:ef", "cluster_type": "static", "row_count": 49, "distinct_src_mac": 1, "rssi_min": -92.0, "rssi_max": -77.0, "rssi_mean": -85.61224489795919},
    {"cluster_id": "bc:89:f8:cd:18:8a", "cluster_type": "static", "row_count": 12, "distinct_src_mac": 1, "rssi_min": -91.0, "rssi_max": -84.0, "rssi_mean": -87.25},
    {"cluster_id": "e0:22:a1:ea:c7:24", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -89.0, "rssi_max": -89.0, "rssi_mean": -89.0},
    {"cluster_id": "noise", "cluster_type": "noise", "row_count": 12, "distinct_src_mac": 6, "rssi_min": -89.0, "rssi_max": -79.0, "rssi_mean": -83.83333333333333}
  ]
}
```

### ENRICHED CSV Stats (live path — not copied to save dir; unchanged mtime since S2_C0)
Source: `C:\projects\test\runtime\DATA\Scan - test protocol\scan_S2_ENRICHED.csv`
```json
{
  "total_rows": 5844,
  "match_found_distribution": {"True": 5614, "False": 230},
  "match_found_rate": 0.9606433949349761,
  "match_method_distribution": {"time_identity_best_match": 5614, "no_match": 230},
  "match_score": {"count": 5614, "missing": 230, "min": 1.999, "max": 2.5, "mean": 2.221775846099038}
}
```

### Evaluation (`evaluation.json`, verbatim)
```json
{
  "matches": [
    {"gt_id": "782c4a06-a032-4585-8dd3-c25f0dda8ec9", "gt_label": "scan_GPS_s22", "primary_cluster_id": "1", "cluster_type": "dynamic", "num_samples": 498, "uncertainty_radius_m": 44.42, "distance_m": 8.186936162416565, "covered": true, "dominance_margin": null, "association_status": "clear_match"}
  ],
  "false_positives": [],
  "false_negatives": [
    {"gt_id": "c9c23a86-1613-44da-853c-40c223e47fbe", "lat": 31.28087521018934, "lon": 34.78770612925769, "label": "scan_GPS_LG"},
    {"gt_id": "8c04925d-2010-4193-82dc-5d9344b293af", "lat": 31.280963255494484, "lon": 34.78742455769234, "label": "scan_GPS_sams"}
  ],
  "ambiguous_gts": [],
  "duplicates": [],
  "possible_merges": [],
  "metrics": {"recall": 0.3333, "precision": 1.0, "coverage": 1.0, "median_error_m": 8.19, "p90_error_m": 8.19, "median_radius_m": 44.42, "count_error": -2},
  "score": {"total": 0.7667, "containment": 1.0, "distance": 1.0, "count": 0.3333, "radius": 0.0},
  "eval_params": {
    "ratio_gate": 1.2,
    "max_match_dist_m": 30.0,
    "r_normalize_m": 30.0,
    "d_free_m": 10.0,
    "w_containment": 0.4,
    "w_distance": 0.3,
    "w_count": 0.2,
    "w_radius": 0.1,
    "min_reliable_samples": 10,
    "min_reliability_threshold": 0.3
  },
  "n_predictions": 1,
  "n_gt": 3
}
```

### Ground Truth (`ground_truth.json`, verbatim)
```json
[
  {"gt_id": "c9c23a86-1613-44da-853c-40c223e47fbe", "lat": 31.28087521018934, "lon": 34.78770612925769, "label": "scan_GPS_LG"},
  {"gt_id": "8c04925d-2010-4193-82dc-5d9344b293af", "lat": 31.280963255494484, "lon": 34.78742455769234, "label": "scan_GPS_sams"},
  {"gt_id": "782c4a06-a032-4585-8dd3-c25f0dda8ec9", "lat": 31.280749738095224, "lon": 34.78746577619051, "label": "scan_GPS_s22"}
]
```

### Calibration (`calibration.json`, verbatim)
```json
{
  "parameter_source": "derived",
  "parameters": {
    "rssi_at_1m": -53.61,
    "path_loss_n": 1.5675,
    "sigma": 3.424
  },
  "approved": true,
  "calibration_csv_file": "scan_calib1.csv",
  "calibration_mac_address": "2c:59:8a:58:95:c1"
}
```

---

## S2_C3

### Session
```json
{
  "session_id": "d7e28a7e-8034-4406-bdd2-94be783a68d7",
  "folder_id": "Scan - test protocol",
  "mode": "wifi",
  "created_at": "2026-08-14T08:22:41.561186+00:00"
}
```
- saved_id used (renamed from): `2026-08-14T08-24-29Z`
- saved_at_utc: `2026-08-14T08:24:29.264199Z`
- note: fifth session_id in this log. Calibration `fallback`/`open_field`, byte-identical to
  S2_C1's `calibration.json` - confirms the pattern seen across this log so far: odd-numbered
  C labels (C1, C3) use the fallback preset, even-numbered (C0, C2) use the derived fit.
  `scan_S2_REID.csv` diff-verified byte-identical to every prior S2 run's copy.
- same single-merged-cluster shape as S2_C2/S1-2_C2 (`cluster_id="1"`, `sample_count=403`,
  RANSAC removed 268 outliers) but with a different peak location and larger uncertainty
  radius (49.16m vs C2's 44.42m) - a distinct result, not a repeat of C2's, consistent with
  C3 being its own configuration rather than a duplicate.
- `active_reid_artifact` is `null` in this session's live state (same as C0/C2, unlike C1);
  save resolved `scan_S2_REID.csv` via the DATA-folder mtime fallback, verified correct
  (byte-identical, no competing file).

### Gate Check
- localization_result_exists_with_cluster: PASS (total_clusters=1, successful_clusters=1, failed_clusters=0)
- active_reid_csv_resolvable: PASS via DATA-folder fallback (`scan_S2_REID.csv`)
- ground_truth_exists: PASS (count=3)
- evaluation_exists: PASS (evaluation ran; result is a total miss - score.total=0.0, see below)

### Volatile Capture (live session state at query time)
```json
{
  "_pending_calibration": "[MISSING: key entirely absent from session state - this session never called calibration/run (unlike S2_C1's session, which had a leftover derived-fit value); it went straight to the fallback preset]",
  "active_enrichment.quality": "[MISSING: active_enrichment]",
  "active_reid.quality": "[MISSING: active_reid - key absent from session state; active_reid_artifact is also null]",
  "current_localization_result.warnings": [
    "Cluster 1: RANSAC removed 268 outlier samples from cluster"
  ],
  "execution_metadata": "[NOT AVAILABLE: no execution_id recoverable - current backend process (pid 15004) has no matching stdout/access log on disk; existing log files belong to a different, already-exited process]",
  "active_enriched_artifact": null,
  "active_reid_artifact": null
}
```

### REID CSV Stats (from saved copy, `scan_S2_REID.csv` - byte-identical to every prior S2 run's)
```json
{
  "total_rows": 671,
  "distinct_src_mac": 140,
  "distinct_cluster_id": 22,
  "cluster_type_row_breakdown": {"dynamic": 467, "static": 192, "noise": 12},
  "per_cluster": [
    {"cluster_id": "0c:29:8f:8d:0d:8a", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -87.0, "rssi_max": -84.0, "rssi_mean": -85.5},
    {"cluster_id": "1", "cluster_type": "dynamic", "row_count": 163, "distinct_src_mac": 32, "rssi_min": -92.0, "rssi_max": -62.0, "rssi_mean": -79.6441717791411},
    {"cluster_id": "10", "cluster_type": "dynamic", "row_count": 85, "distinct_src_mac": 50, "rssi_min": -87.0, "rssi_max": -50.0, "rssi_mean": -67.08235294117647},
    {"cluster_id": "10:2c:6b:e5:8b:a2", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -82.0, "rssi_max": -82.0, "rssi_mean": -82.0},
    {"cluster_id": "14:ea:63:f5:14:1f", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -85.0, "rssi_max": -85.0, "rssi_mean": -85.0},
    {"cluster_id": "20:9b:e6:13:c0:82", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -87.0, "rssi_max": -86.0, "rssi_mean": -86.5},
    {"cluster_id": "2c:59:8a:58:95:c1", "cluster_type": "static", "row_count": 80, "distinct_src_mac": 1, "rssi_min": -89.0, "rssi_max": -56.0, "rssi_mean": -71.5625},
    {"cluster_id": "30:52:23:c0:f2:88", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -89.0, "rssi_max": -89.0, "rssi_mean": -89.0},
    {"cluster_id": "40:91:51:75:87:83", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -92.0, "rssi_max": -87.0, "rssi_mean": -89.5},
    {"cluster_id": "44:ef:bf:84:67:21", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -88.0, "rssi_max": -88.0, "rssi_mean": -88.0},
    {"cluster_id": "48:3f:da:2e:8b:23", "cluster_type": "static", "row_count": 7, "distinct_src_mac": 1, "rssi_min": -93.0, "rssi_max": -85.0, "rssi_mean": -89.14285714285714},
    {"cluster_id": "64:bb:1e:54:a7:2e", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -88.0, "rssi_max": -88.0, "rssi_mean": -88.0},
    {"cluster_id": "6c:22:1a:c5:fa:82", "cluster_type": "static", "row_count": 7, "distinct_src_mac": 1, "rssi_min": -93.0, "rssi_max": -87.0, "rssi_mean": -90.14285714285714},
    {"cluster_id": "7", "cluster_type": "dynamic", "row_count": 12, "distinct_src_mac": 7, "rssi_min": -83.0, "rssi_max": -59.0, "rssi_mean": -73.0},
    {"cluster_id": "8", "cluster_type": "dynamic", "row_count": 207, "distinct_src_mac": 28, "rssi_min": -90.0, "rssi_max": -58.0, "rssi_mean": -73.31884057971014},
    {"cluster_id": "88:a2:9e:09:94:05", "cluster_type": "static", "row_count": 6, "distinct_src_mac": 1, "rssi_min": -44.0, "rssi_max": -35.0, "rssi_mean": -38.0},
    {"cluster_id": "98:86:b1:03:35:8e", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -89.0, "rssi_max": -84.0, "rssi_mean": -86.5},
    {"cluster_id": "9c:a3:a9:60:44:a4", "cluster_type": "static", "row_count": 17, "distinct_src_mac": 1, "rssi_min": -90.0, "rssi_max": -85.0, "rssi_mean": -87.0},
    {"cluster_id": "9c:a3:a9:69:05:ef", "cluster_type": "static", "row_count": 49, "distinct_src_mac": 1, "rssi_min": -92.0, "rssi_max": -77.0, "rssi_mean": -85.61224489795919},
    {"cluster_id": "bc:89:f8:cd:18:8a", "cluster_type": "static", "row_count": 12, "distinct_src_mac": 1, "rssi_min": -91.0, "rssi_max": -84.0, "rssi_mean": -87.25},
    {"cluster_id": "e0:22:a1:ea:c7:24", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -89.0, "rssi_max": -89.0, "rssi_mean": -89.0},
    {"cluster_id": "noise", "cluster_type": "noise", "row_count": 12, "distinct_src_mac": 6, "rssi_min": -89.0, "rssi_max": -79.0, "rssi_mean": -83.83333333333333}
  ]
}
```

### ENRICHED CSV Stats (live path — not copied to save dir; unchanged mtime since S2_C0)
Source: `C:\projects\test\runtime\DATA\Scan - test protocol\scan_S2_ENRICHED.csv`
```json
{
  "total_rows": 5844,
  "match_found_distribution": {"True": 5614, "False": 230},
  "match_found_rate": 0.9606433949349761,
  "match_method_distribution": {"time_identity_best_match": 5614, "no_match": 230},
  "match_score": {"count": 5614, "missing": 230, "min": 1.999, "max": 2.5, "mean": 2.221775846099038}
}
```

### Evaluation (`evaluation.json`, verbatim)
```json
{
  "matches": [],
  "false_positives": [
    {"cluster_id": "1", "lat": 31.28056739517375, "lon": 34.787721800669246, "cluster_type": "dynamic"}
  ],
  "false_negatives": [
    {"gt_id": "63bae575-5b4b-4f74-8dff-6eb9d845f473", "lat": 31.28087521018934, "lon": 34.78770612925769, "label": "scan_GPS_LG"},
    {"gt_id": "4a0c0f26-5f39-478b-b8c8-2e3a2c9cb9f7", "lat": 31.280749738095224, "lon": 34.78746577619051, "label": "scan_GPS_s22"},
    {"gt_id": "bb2febeb-7328-4309-9ad4-628d119ced75", "lat": 31.280963255494484, "lon": 34.78742455769234, "label": "scan_GPS_sams"}
  ],
  "ambiguous_gts": [],
  "duplicates": [],
  "possible_merges": [],
  "metrics": {"recall": 0.0, "precision": 0.0, "coverage": 0.0, "median_error_m": null, "p90_error_m": null, "median_radius_m": 49.16, "count_error": -2},
  "score": {"total": 0.0, "containment": 0.0, "distance": 0.0, "count": 0.0, "radius": 0.0},
  "eval_params": {
    "ratio_gate": 1.2,
    "max_match_dist_m": 30.0,
    "r_normalize_m": 30.0,
    "d_free_m": 10.0,
    "w_containment": 0.4,
    "w_distance": 0.3,
    "w_count": 0.2,
    "w_radius": 0.1,
    "min_reliable_samples": 10,
    "min_reliability_threshold": 0.3
  },
  "n_predictions": 1,
  "n_gt": 3
}
```

### Ground Truth (`ground_truth.json`, verbatim)
```json
[
  {"gt_id": "63bae575-5b4b-4f74-8dff-6eb9d845f473", "lat": 31.28087521018934, "lon": 34.78770612925769, "label": "scan_GPS_LG"},
  {"gt_id": "4a0c0f26-5f39-478b-b8c8-2e3a2c9cb9f7", "lat": 31.280749738095224, "lon": 34.78746577619051, "label": "scan_GPS_s22"},
  {"gt_id": "bb2febeb-7328-4309-9ad4-628d119ced75", "lat": 31.280963255494484, "lon": 34.78742455769234, "label": "scan_GPS_sams"}
]
```

### Calibration (`calibration.json`, verbatim)
```json
{
  "parameter_source": "fallback",
  "parameters": {
    "rssi_at_1m": -40.0,
    "path_loss_n": 2.0,
    "sigma": 4.0
  },
  "approved": true,
  "calibration_csv_file": null,
  "calibration_mac_address": null,
  "parameter_set_name": "open_field"
}
```

---

## S3_C0

### Session
```json
{
  "session_id": "b3699540-df0d-428f-bb01-04badf13e5fe",
  "folder_id": "Scan - test protocol",
  "mode": "wifi",
  "created_at": "2026-08-14T08:49:32.551319+00:00"
}
```
- saved_id used (renamed from): `2026-08-14T08-51-02Z`
- saved_at_utc: `2026-08-14T08:51:02.366753Z`
- note: sixth session_id in this log; first session to touch `scan_S3_REID.csv`. Calibration
  `derived`/`scan_calib1.csv`, same fit as every other derived run in this log.
- **corrected after two failed save attempts, recorded for the audit trail**: the first two
  attempts for this label (`saved_id=2026-08-14T08-44-46Z`, session `ea5ae451-...`; and
  `saved_id=2026-08-14T08-47-36Z`, session `2c69b558-...`) both bundled `scan_S2_REID.csv`
  instead of `scan_S3_REID.csv` - `_find_reid_csv()`'s DATA-folder mtime fallback kept
  picking S2's file (touched more recently, during the S2_C1 fix) over S3's (untouched since
  Aug 13). Cross-checked both times that `localization.json` itself was still correctly
  computed against real S3 data (its cluster IDs matched `scan_S3_REID.csv`, not S2's) - the
  bug was purely in which file got bundled into the save, not in the underlying computation.
  Neither of the two mismatched attempts is renamed or logged under any label; both sit
  untouched on disk under their timestamps. This third attempt has `active_reid_artifact`
  explicitly set to `scan_S3_REID.csv` in live state (unlike the first two, where it was
  `null`) and the saved `scan_S3_REID.csv` has a fresh mtime (11:49, today) - resolved
  correctly, and cross-checked: `localization.json`'s 15 cluster IDs match
  `scan_S3_REID.csv`'s exactly.

### Gate Check
- localization_result_exists_with_cluster: PASS (total_clusters=15, successful_clusters=5, failed_clusters=10)
- active_reid_csv_resolvable: PASS (`scan_S3_REID.csv`, explicit `active_reid_artifact`)
- ground_truth_exists: PASS (count=3)
- evaluation_exists: PASS (score.total=0.9897)

### Volatile Capture (live session state at query time)
```json
{
  "_pending_calibration": {
    "csv_filename": "scan_calib1.csv",
    "mac": "2c:59:8a:58:95:c1",
    "result.fit_quality": {
      "r2": 0.8397,
      "sample_count": 59,
      "inlier_count": 46,
      "inlier_ratio": 0.78,
      "sigma": 3.424
    },
    "note": "matches active_calibration (both derived/scan_calib1.csv) - not stale"
  },
  "active_enrichment.quality": "[MISSING: active_enrichment]",
  "active_reid.quality": {
    "reid_csv_path": "C:\\projects\\test\\runtime\\DATA\\Scan - test protocol\\scan_S3_REID.csv",
    "total_rows": 754,
    "static_cluster_count": 10,
    "dynamic_cluster_count": 5,
    "unique_dynamic_mac_count": 90,
    "noise_cluster_count": 8,
    "cluster_confidence": {"3": "high", "6": "high", "8": "high", "9": "high", "10": "high"},
    "warnings": []
  },
  "current_localization_result.warnings": [
    "Cluster 10: RANSAC removed 2 outlier samples from cluster",
    "Cluster 10 uncertainty radius too large (34.3m, need <=30m)",
    "Cluster 2c:59:8a:58:95:c1: RANSAC removed 27 outlier samples from cluster",
    "Cluster 3: RANSAC removed 5 outlier samples from cluster",
    "Cluster 30:52:23:c0:f2:88 has insufficient samples",
    "Cluster 44:ef:bf:84:67:21 has insufficient samples",
    "Cluster 48:3f:da:2e:8b:23 has insufficient samples",
    "Cluster 6: RANSAC removed 12 outlier samples from cluster",
    "Cluster 6 uncertainty radius too large (43.7m, need <=30m)",
    "Cluster 8: RANSAC removed 77 outlier samples from cluster",
    "Cluster 88:a2:9e:09:94:05 insufficient movement (time=0.6s, need >=30s; baseline=0.0m, need >=5m)",
    "Cluster 9 has insufficient samples",
    "Cluster 9c:a3:a9:60:44:a4: RANSAC removed 6 outlier samples from cluster",
    "Cluster 9c:a3:a9:60:44:a4 uncertainty radius too large (84.4m, need <=30m)",
    "Cluster 9c:a3:a9:69:05:ef: RANSAC removed 14 outlier samples from cluster",
    "Cluster bc:89:f8:cd:18:8a: RANSAC found no valid inlier set for cluster; using all 4 samples",
    "Cluster bc:d5:ed:35:10:00 has insufficient samples",
    "Cluster c0:74:ad:93:c3:79 has insufficient samples",
    "Noise cluster (8 rows) skipped - aggregate of unassociated MACs, not a single emitter"
  ],
  "execution_metadata": "[NOT AVAILABLE: no execution_id recoverable - current backend process (pid 15004) has no matching stdout/access log on disk; existing log files belong to a different, already-exited process]",
  "active_enriched_artifact": null,
  "active_reid_artifact": "C:\\projects\\test\\runtime\\DATA\\Scan - test protocol\\scan_S3_REID.csv"
}
```

### REID CSV Stats (from saved copy, `scan_S3_REID.csv`)
```json
{
  "total_rows": 754,
  "distinct_src_mac": 108,
  "distinct_cluster_id": 16,
  "cluster_type_row_breakdown": {"dynamic": 533, "static": 213, "noise": 8},
  "per_cluster": [
    {"cluster_id": "10", "cluster_type": "dynamic", "row_count": 23, "distinct_src_mac": 15, "rssi_min": -85.0, "rssi_max": -65.0, "rssi_mean": -75.82608695652173},
    {"cluster_id": "2c:59:8a:58:95:c1", "cluster_type": "static", "row_count": 147, "distinct_src_mac": 1, "rssi_min": -88.0, "rssi_max": -43.0, "rssi_mean": -72.0952380952381},
    {"cluster_id": "3", "cluster_type": "dynamic", "row_count": 31, "distinct_src_mac": 18, "rssi_min": -88.0, "rssi_max": -58.0, "rssi_mean": -72.7741935483871},
    {"cluster_id": "30:52:23:c0:f2:88", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -92.0, "rssi_max": -90.0, "rssi_mean": -91.0},
    {"cluster_id": "44:ef:bf:84:67:21", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -88.0, "rssi_max": -88.0, "rssi_mean": -88.0},
    {"cluster_id": "48:3f:da:2e:8b:23", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -90.0, "rssi_max": -90.0, "rssi_mean": -90.0},
    {"cluster_id": "6", "cluster_type": "dynamic", "row_count": 109, "distinct_src_mac": 15, "rssi_min": -92.0, "rssi_max": -61.0, "rssi_mean": -76.24770642201835},
    {"cluster_id": "8", "cluster_type": "dynamic", "row_count": 368, "distinct_src_mac": 40, "rssi_min": -90.0, "rssi_max": -44.0, "rssi_mean": -68.55163043478261},
    {"cluster_id": "88:a2:9e:09:94:05", "cluster_type": "static", "row_count": 11, "distinct_src_mac": 1, "rssi_min": -74.0, "rssi_max": -22.0, "rssi_mean": -52.18181818181818},
    {"cluster_id": "9", "cluster_type": "dynamic", "row_count": 2, "distinct_src_mac": 2, "rssi_min": -90.0, "rssi_max": -89.0, "rssi_mean": -89.5},
    {"cluster_id": "9c:a3:a9:60:44:a4", "cluster_type": "static", "row_count": 9, "distinct_src_mac": 1, "rssi_min": -90.0, "rssi_max": -84.0, "rssi_mean": -87.0},
    {"cluster_id": "9c:a3:a9:69:05:ef", "cluster_type": "static", "row_count": 35, "distinct_src_mac": 1, "rssi_min": -91.0, "rssi_max": -59.0, "rssi_mean": -85.45714285714286},
    {"cluster_id": "bc:89:f8:cd:18:8a", "cluster_type": "static", "row_count": 4, "distinct_src_mac": 1, "rssi_min": -92.0, "rssi_max": -84.0, "rssi_mean": -88.5},
    {"cluster_id": "bc:d5:ed:35:10:00", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -90.0, "rssi_max": -89.0, "rssi_mean": -89.5},
    {"cluster_id": "c0:74:ad:93:c3:79", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -87.0, "rssi_max": -87.0, "rssi_mean": -87.0},
    {"cluster_id": "noise", "cluster_type": "noise", "row_count": 8, "distinct_src_mac": 8, "rssi_min": -94.0, "rssi_max": -81.0, "rssi_mean": -86.625}
  ]
}
```

### ENRICHED CSV Stats (live path — not copied to save dir)
Source: `C:\projects\test\runtime\DATA\Scan - test protocol\scan_S3_ENRICHED.csv`
```json
{
  "total_rows": 4384,
  "match_found_distribution": {"True": 4237, "False": 147},
  "match_found_rate": 0.9664689781021898,
  "match_method_distribution": {"time_identity_best_match": 4237, "no_match": 147},
  "match_score": {"count": 4237, "missing": 147, "min": 1.999, "max": 2.4999, "mean": 2.2058362048619307}
}
```

### Evaluation (`evaluation.json`, verbatim)
```json
{
  "matches": [
    {"gt_id": "5dafac09-8e69-48a3-8edf-9d0630394882", "gt_label": "scan_GPS_S3_LG", "primary_cluster_id": "2c:59:8a:58:95:c1", "cluster_type": "static", "num_samples": 120, "uncertainty_radius_m": 19.627, "distance_m": 7.601906169579789, "covered": true, "dominance_margin": 1.56, "association_status": "clear_match"},
    {"gt_id": "e3e64f02-68ea-493a-ba4a-98fcd52406ae", "gt_label": "scan_GPS_S3_sams", "primary_cluster_id": "3", "cluster_type": "dynamic", "num_samples": 26, "uncertainty_radius_m": 27.156, "distance_m": 17.54295156821755, "covered": true, "dominance_margin": 2.756, "association_status": "clear_match"},
    {"gt_id": "45916f62-09dc-4b37-b3c5-7c2284e7f469", "gt_label": "scan_GPS_S3_s22", "primary_cluster_id": "8", "cluster_type": "dynamic", "num_samples": 291, "uncertainty_radius_m": 14.385, "distance_m": 3.222861461894068, "covered": true, "dominance_margin": 2.497, "association_status": "clear_match"}
  ],
  "false_positives": [],
  "false_negatives": [],
  "ambiguous_gts": [],
  "duplicates": [],
  "possible_merges": [
    {"cluster_id": "2c:59:8a:58:95:c1", "candidate_gt_ids": ["5dafac09-8e69-48a3-8edf-9d0630394882", "45916f62-09dc-4b37-b3c5-7c2284e7f469", "e3e64f02-68ea-493a-ba4a-98fcd52406ae"], "distances_m": [7.601906169579789, 8.047930817427213, 8.99741925043905]},
    {"cluster_id": "3", "candidate_gt_ids": ["5dafac09-8e69-48a3-8edf-9d0630394882", "45916f62-09dc-4b37-b3c5-7c2284e7f469", "e3e64f02-68ea-493a-ba4a-98fcd52406ae"], "distances_m": [20.265791842623003, 18.713583136882164, 17.54295156821755]},
    {"cluster_id": "8", "candidate_gt_ids": ["5dafac09-8e69-48a3-8edf-9d0630394882", "45916f62-09dc-4b37-b3c5-7c2284e7f469", "e3e64f02-68ea-493a-ba4a-98fcd52406ae"], "distances_m": [4.873294905471458, 3.222861461894068, 3.2645458200434865]}
  ],
  "metrics": {"recall": 1.0, "precision": 1.0, "coverage": 1.0, "median_error_m": 7.6, "p90_error_m": 17.54, "median_radius_m": 19.63, "count_error": 0},
  "score": {"total": 0.9897, "containment": 1.0, "distance": 1.0, "count": 1.0, "radius": 0.897},
  "eval_params": {
    "ratio_gate": 1.2,
    "max_match_dist_m": 30.0,
    "r_normalize_m": 30.0,
    "d_free_m": 10.0,
    "w_containment": 0.4,
    "w_distance": 0.3,
    "w_count": 0.2,
    "w_radius": 0.1,
    "min_reliable_samples": 10,
    "min_reliability_threshold": 0.3
  },
  "n_predictions": 3,
  "n_gt": 3
}
```

### Ground Truth (`ground_truth.json`, verbatim)
```json
[
  {"gt_id": "5dafac09-8e69-48a3-8edf-9d0630394882", "lat": 31.28089, "lon": 34.78743999999999, "label": "scan_GPS_S3_LG"},
  {"gt_id": "45916f62-09dc-4b37-b3c5-7c2284e7f469", "lat": 31.280909999999974, "lon": 34.78742999999999, "label": "scan_GPS_S3_s22"},
  {"gt_id": "e3e64f02-68ea-493a-ba4a-98fcd52406ae", "lat": 31.28092000000001, "lon": 34.787420000000004, "label": "scan_GPS_S3_sams"}
]
```

### Calibration (`calibration.json`, verbatim)
```json
{
  "parameter_source": "derived",
  "parameters": {
    "rssi_at_1m": -53.61,
    "path_loss_n": 1.5675,
    "sigma": 3.424
  },
  "approved": true,
  "calibration_csv_file": "scan_calib1.csv",
  "calibration_mac_address": "2c:59:8a:58:95:c1"
}
```

---

## S3_C2

### Session
```json
{
  "session_id": "ee505457-10f3-4172-891f-89513c5c06be",
  "folder_id": "Scan - test protocol",
  "mode": "wifi",
  "created_at": "2026-08-14T08:54:21.309091+00:00"
}
```
- saved_id used (renamed from): `2026-08-14T08-56-50Z`
- saved_at_utc: `2026-08-14T08:56:50.854961Z`
- note: seventh session_id in this log. Calibration byte-identical to S3_C0's (derived,
  scan_calib1.csv).
- **REID artifact is a distinctly-named file this time, verified deliberate, not a repeat of
  the S3_C0/S2_C1 mismatch bug**: saved artifact is `scan_S3_(single cluster)_REID.csv`
  (754 rows, `dynamic:533/static:213/noise:8` breakdown), not the plain `scan_S3_REID.csv`
  used for C0. Checked closely because of the two prior false starts on this scan: this file
  has the exact same row count and cluster_type breakdown as `scan_S3_REID.csv` (754 rows
  total) but every row's `cluster_id` is forced to `"1"` - a purpose-built pre-merged
  variant, not a stray leftover. Its mtime (11:53) is genuinely newer than
  `scan_S3_REID.csv`'s (11:49), so the DATA-folder fallback resolved correctly. This differs
  from how S1-2_C2/S2_C2 got their single-cluster result (there, the *same* REID file as C0
  was reused and the merge happened only at the localization stage) - here a dedicated REID
  variant does the merging instead. Recording the mechanism difference, not asserting why.
- **third occurrence of the recurring sample_count discrepancy**: `cluster_id="1"`'s
  `sample_count=576` in `localization.json`, but the single-cluster REID file backing it has
  754 rows total (all under that one cluster_id). 576 doesn't match 754, nor
  533 (dynamic-only), nor 746 (non-noise). Same unexplained shape as S1-2_C2 (338 vs 10) and
  S2_C2 (498 vs 163) - now a third data point, on a third scan, still not interpreted.

### Gate Check
- localization_result_exists_with_cluster: PASS (total_clusters=1, successful_clusters=1, failed_clusters=0)
- active_reid_csv_resolvable: PASS via DATA-folder fallback (`scan_S3_(single cluster)_REID.csv`, verified correct)
- ground_truth_exists: PASS (count=3)
- evaluation_exists: PASS (score.total=0.857)

### Volatile Capture (live session state at query time)
```json
{
  "_pending_calibration": {
    "csv_filename": "scan_calib1.csv",
    "mac": "2c:59:8a:58:95:c1",
    "result.fit_quality": {
      "r2": 0.8397,
      "sample_count": 59,
      "inlier_count": 46,
      "inlier_ratio": 0.78,
      "sigma": 3.424
    },
    "note": "matches active_calibration - not stale"
  },
  "active_enrichment.quality": "[MISSING: active_enrichment]",
  "active_reid.quality": "[MISSING: active_reid - key absent from session state; active_reid_artifact is also null]",
  "current_localization_result.warnings": [
    "Cluster 1: RANSAC removed 178 outlier samples from cluster"
  ],
  "execution_metadata": "[NOT AVAILABLE: no execution_id recoverable - current backend process (pid 15004) has no matching stdout/access log on disk; existing log files belong to a different, already-exited process]",
  "active_enriched_artifact": "C:\\projects\\test\\runtime\\DATA\\Scan - test protocol\\scan_S3_ENRICHED.csv",
  "active_reid_artifact": null
}
```
Note: unlike every other S1-2/S2 session, `active_enriched_artifact` *is* explicitly set here
(to `scan_S3_ENRICHED.csv`) - it just happens to match the naming-matched file I'd have used
anyway.

### REID CSV Stats (from saved copy, `scan_S3_(single cluster)_REID.csv`)
```json
{
  "total_rows": 754,
  "distinct_src_mac": 108,
  "distinct_cluster_id": 1,
  "cluster_type_row_breakdown": {"dynamic": 533, "static": 213, "noise": 8},
  "per_cluster": [
    {"cluster_id": "1", "cluster_type": "mixed (dynamic/static/noise rows all under this id)", "row_count": 754, "distinct_src_mac": 108, "rssi_min": -94.0, "rssi_max": -22.0, "rssi_mean": -72.06366047745358}
  ]
}
```

### ENRICHED CSV Stats (live path — not copied to save dir; unchanged mtime since S3_C0)
Source: `C:\projects\test\runtime\DATA\Scan - test protocol\scan_S3_ENRICHED.csv`
```json
{
  "total_rows": 4384,
  "match_found_distribution": {"True": 4237, "False": 147},
  "match_found_rate": 0.9664689781021898,
  "match_method_distribution": {"time_identity_best_match": 4237, "no_match": 147},
  "match_score": {"count": 4237, "missing": 147, "min": 1.999, "max": 2.4999, "mean": 2.2058362048619307}
}
```

### Evaluation (`evaluation.json`, verbatim)
```json
{
  "matches": [
    {"gt_id": "c69b8c46-6045-4859-a31b-d08a84a0ad86", "gt_label": "scan_GPS_S3_s22", "primary_cluster_id": "1", "cluster_type": "dynamic", "num_samples": 576, "uncertainty_radius_m": 19.344, "distance_m": 3.2231533569855952, "covered": true, "dominance_margin": null, "association_status": "clear_match"}
  ],
  "false_positives": [],
  "false_negatives": [],
  "ambiguous_gts": [
    {"gt_id": "81491465-73b8-4a93-9f4b-0db4cdd6cdfd", "label": "scan_GPS_S3_LG", "nearest_cluster_id": "1", "nearest_dist_m": 4.87, "competing_cluster_ids": ["1"]},
    {"gt_id": "b281faa6-07a5-463a-b5e5-840276576570", "label": "scan_GPS_S3_sams", "nearest_cluster_id": "1", "nearest_dist_m": 3.26, "competing_cluster_ids": ["1"]}
  ],
  "duplicates": [],
  "possible_merges": [
    {"cluster_id": "1", "candidate_gt_ids": ["81491465-73b8-4a93-9f4b-0db4cdd6cdfd", "c69b8c46-6045-4859-a31b-d08a84a0ad86", "b281faa6-07a5-463a-b5e5-840276576570"], "distances_m": [4.873657083844768, 3.2231533569855952, 3.2647077485687834]}
  ],
  "metrics": {"recall": 0.3333, "precision": 1.0, "coverage": 1.0, "median_error_m": 3.22, "p90_error_m": 3.22, "median_radius_m": 19.34, "count_error": -2},
  "score": {"total": 0.857, "containment": 1.0, "distance": 1.0, "count": 0.3333, "radius": 0.903},
  "eval_params": {
    "ratio_gate": 1.2,
    "max_match_dist_m": 30.0,
    "r_normalize_m": 30.0,
    "d_free_m": 10.0,
    "w_containment": 0.4,
    "w_distance": 0.3,
    "w_count": 0.2,
    "w_radius": 0.1,
    "min_reliable_samples": 10,
    "min_reliability_threshold": 0.3
  },
  "n_predictions": 1,
  "n_gt": 3
}
```

### Ground Truth (`ground_truth.json`, verbatim)
```json
[
  {"gt_id": "81491465-73b8-4a93-9f4b-0db4cdd6cdfd", "lat": 31.28089, "lon": 34.78743999999999, "label": "scan_GPS_S3_LG"},
  {"gt_id": "c69b8c46-6045-4859-a31b-d08a84a0ad86", "lat": 31.280909999999974, "lon": 34.78742999999999, "label": "scan_GPS_S3_s22"},
  {"gt_id": "b281faa6-07a5-463a-b5e5-840276576570", "lat": 31.28092000000001, "lon": 34.787420000000004, "label": "scan_GPS_S3_sams"}
]
```

### Calibration (`calibration.json`, verbatim)
```json
{
  "parameter_source": "derived",
  "parameters": {
    "rssi_at_1m": -53.61,
    "path_loss_n": 1.5675,
    "sigma": 3.424
  },
  "approved": true,
  "calibration_csv_file": "scan_calib1.csv",
  "calibration_mac_address": "2c:59:8a:58:95:c1"
}
```

---

## S4_C0

### Session
```json
{
  "session_id": "74ef2106-6e24-4828-be54-68226a751774",
  "folder_id": "Scan - test protocol",
  "mode": "wifi",
  "created_at": "2026-08-14T09:13:37.670309+00:00"
}
```
- saved_id used (renamed from): `2026-08-14T09-16-23Z`
- saved_at_utc: `2026-08-14T09:16:23.790868Z`
- note: eighth session_id in this log; first session to touch `scan_S4_REID.csv`. Calibration
  `derived`/`scan_calib1.csv`, same fit as every other derived run in this log.
- **clean run, no artifact-resolution issues this time**: unlike S3_C0/S3_C2, both
  `active_reid_artifact` and `active_enriched_artifact` were explicitly set in live state to
  the correct `scan_S4_*` files from the start - no DATA-folder mtime fallback needed.
  Cross-checked `localization.json`'s 11 cluster IDs against `scan_S4_REID.csv`'s - exact
  match (excluding noise).

### Gate Check
- localization_result_exists_with_cluster: PASS (total_clusters=11, successful_clusters=7, failed_clusters=4)
- active_reid_csv_resolvable: PASS (`scan_S4_REID.csv`, explicit `active_reid_artifact`)
- ground_truth_exists: PASS (count=3)
- evaluation_exists: PASS (score.total=0.8474)

### Volatile Capture (live session state at query time)
```json
{
  "_pending_calibration": {
    "csv_filename": "scan_calib1.csv",
    "mac": "2c:59:8a:58:95:c1",
    "result.fit_quality": {
      "r2": 0.8397,
      "sample_count": 59,
      "inlier_count": 46,
      "inlier_ratio": 0.78,
      "sigma": 3.424
    },
    "note": "matches active_calibration - not stale"
  },
  "active_enrichment.quality": "[MISSING: active_enrichment]",
  "active_reid.quality": {
    "reid_csv_path": "C:\\projects\\test\\runtime\\DATA\\Scan - test protocol\\scan_S4_REID.csv",
    "total_rows": 550,
    "static_cluster_count": 8,
    "dynamic_cluster_count": 3,
    "unique_dynamic_mac_count": 69,
    "noise_cluster_count": 5,
    "cluster_confidence": {"2": "high", "3": "high", "6": "high"},
    "warnings": []
  },
  "current_localization_result.warnings": [
    "Cluster 14:ea:63:f5:14:1f has insufficient samples",
    "Cluster 2 insufficient movement (time=4.9s, need >=30s; baseline=2.7m, need >=5m)",
    "Cluster 2c:59:8a:58:95:c1: RANSAC removed 11 outlier samples from cluster",
    "Cluster 3: RANSAC removed 36 outlier samples from cluster",
    "Cluster 30:52:23:c0:f2:88: RANSAC found no valid inlier set for cluster; using all 6 samples",
    "Cluster 6: RANSAC removed 9 outlier samples from cluster",
    "Cluster 9c:a3:a9:69:05:ef: RANSAC removed 29 outlier samples from cluster",
    "Cluster bc:d5:ed:35:10:00 has insufficient samples",
    "Cluster c8:2e:18:bf:86:c8 has insufficient samples",
    "Noise cluster (6 rows) skipped - aggregate of unassociated MACs, not a single emitter"
  ],
  "execution_metadata": "[NOT AVAILABLE: no execution_id recoverable - current backend process (pid 15004) has no matching stdout/access log on disk; existing log files belong to a different, already-exited process]",
  "active_enriched_artifact": "C:\\projects\\test\\runtime\\DATA\\Scan - test protocol\\scan_S4_ENRICHED.csv",
  "active_reid_artifact": "C:\\projects\\test\\runtime\\DATA\\Scan - test protocol\\scan_S4_REID.csv"
}
```

### REID CSV Stats (from saved copy, `scan_S4_REID.csv`)
```json
{
  "total_rows": 550,
  "distinct_src_mac": 82,
  "distinct_cluster_id": 12,
  "cluster_type_row_breakdown": {"static": 123, "dynamic": 421, "noise": 6},
  "per_cluster": [
    {"cluster_id": "14:ea:63:f5:14:1f", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -90.0, "rssi_max": -90.0, "rssi_mean": -90.0},
    {"cluster_id": "2", "cluster_type": "dynamic", "row_count": 4, "distinct_src_mac": 2, "rssi_min": -79.0, "rssi_max": -76.0, "rssi_mean": -78.0},
    {"cluster_id": "2c:59:8a:58:95:c1", "cluster_type": "static", "row_count": 59, "distinct_src_mac": 1, "rssi_min": -94.0, "rssi_max": -63.0, "rssi_mean": -76.13559322033899},
    {"cluster_id": "3", "cluster_type": "dynamic", "row_count": 385, "distinct_src_mac": 46, "rssi_min": -89.0, "rssi_max": -61.0, "rssi_mean": -72.46753246753246},
    {"cluster_id": "30:52:23:c0:f2:88", "cluster_type": "static", "row_count": 6, "distinct_src_mac": 1, "rssi_min": -94.0, "rssi_max": -84.0, "rssi_mean": -88.66666666666667},
    {"cluster_id": "44:ef:bf:84:67:21", "cluster_type": "static", "row_count": 3, "distinct_src_mac": 1, "rssi_min": -90.0, "rssi_max": -88.0, "rssi_mean": -89.33333333333333},
    {"cluster_id": "6", "cluster_type": "dynamic", "row_count": 32, "distinct_src_mac": 21, "rssi_min": -90.0, "rssi_max": -68.0, "rssi_mean": -78.75},
    {"cluster_id": "9c:a3:a9:60:44:a4", "cluster_type": "static", "row_count": 8, "distinct_src_mac": 1, "rssi_min": -91.0, "rssi_max": -87.0, "rssi_mean": -89.375},
    {"cluster_id": "9c:a3:a9:69:05:ef", "cluster_type": "static", "row_count": 43, "distinct_src_mac": 1, "rssi_min": -92.0, "rssi_max": -84.0, "rssi_mean": -87.55813953488372},
    {"cluster_id": "bc:d5:ed:35:10:00", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -82.0, "rssi_max": -82.0, "rssi_mean": -82.0},
    {"cluster_id": "c8:2e:18:bf:86:c8", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -87.0, "rssi_max": -87.0, "rssi_mean": -87.0},
    {"cluster_id": "noise", "cluster_type": "noise", "row_count": 6, "distinct_src_mac": 5, "rssi_min": -93.0, "rssi_max": -68.0, "rssi_mean": -84.5}
  ]
}
```

### ENRICHED CSV Stats (live path — not copied to save dir)
Source: `C:\projects\test\runtime\DATA\Scan - test protocol\scan_S4_ENRICHED.csv`
```json
{
  "total_rows": 5794,
  "match_found_distribution": {"True": 5660, "False": 134},
  "match_found_rate": 0.9768726268553676,
  "match_method_distribution": {"time_identity_best_match": 5660, "no_match": 134},
  "match_score": {"count": 5660, "missing": 134, "min": 1.999, "max": 2.5, "mean": 2.2281703180212014}
}
```

### Evaluation (`evaluation.json`, verbatim)
```json
{
  "matches": [
    {"gt_id": "8e31965a-8edc-4278-ae00-b251b63f03c4", "gt_label": "scan_GPS_S4_LG", "primary_cluster_id": "2c:59:8a:58:95:c1", "cluster_type": "static", "num_samples": 48, "uncertainty_radius_m": 27.502, "distance_m": 25.81373876380671, "covered": true, "dominance_margin": 1.733, "association_status": "clear_match"},
    {"gt_id": "cfca478c-3d6f-47a0-bf87-536e33b4724a", "gt_label": "scan_GPS_S4_sams", "primary_cluster_id": "3", "cluster_type": "dynamic", "num_samples": 349, "uncertainty_radius_m": 11.86, "distance_m": 11.918204512782577, "covered": false, "dominance_margin": 1.451, "association_status": "clear_match"},
    {"gt_id": "47de8e44-184c-4dc5-bdab-6bbfd3d6353b", "gt_label": "scan_GPS_S4_s22", "primary_cluster_id": "6", "cluster_type": "dynamic", "num_samples": 23, "uncertainty_radius_m": 22.758, "distance_m": 11.863351003960037, "covered": true, "dominance_margin": 2.398, "association_status": "clear_match"}
  ],
  "false_positives": [],
  "false_negatives": [],
  "ambiguous_gts": [],
  "duplicates": [],
  "possible_merges": [
    {"cluster_id": "2c:59:8a:58:95:c1", "candidate_gt_ids": ["cfca478c-3d6f-47a0-bf87-536e33b4724a", "8e31965a-8edc-4278-ae00-b251b63f03c4", "47de8e44-184c-4dc5-bdab-6bbfd3d6353b"], "distances_m": [17.29917331276585, 25.81373876380671, 28.442492178042183]},
    {"cluster_id": "6", "candidate_gt_ids": ["8e31965a-8edc-4278-ae00-b251b63f03c4", "47de8e44-184c-4dc5-bdab-6bbfd3d6353b"], "distances_m": [14.893399030244606, 11.863351003960037]}
  ],
  "metrics": {"recall": 1.0, "precision": 1.0, "coverage": 0.6667, "median_error_m": 11.92, "p90_error_m": 25.81, "median_radius_m": 22.76, "count_error": 0},
  "score": {"total": 0.8474, "containment": 0.6667, "distance": 0.9959, "count": 1.0, "radius": 0.8191},
  "eval_params": {
    "ratio_gate": 1.2,
    "max_match_dist_m": 30.0,
    "r_normalize_m": 30.0,
    "d_free_m": 10.0,
    "w_containment": 0.4,
    "w_distance": 0.3,
    "w_count": 0.2,
    "w_radius": 0.1,
    "min_reliable_samples": 10,
    "min_reliability_threshold": 0.3
  },
  "n_predictions": 3,
  "n_gt": 3
}
```

### Ground Truth (`ground_truth.json`, verbatim)
```json
[
  {"gt_id": "cfca478c-3d6f-47a0-bf87-536e33b4724a", "lat": 31.280690000000025, "lon": 34.78742999999999, "label": "scan_GPS_S4_sams"},
  {"gt_id": "8e31965a-8edc-4278-ae00-b251b63f03c4", "lat": 31.28062, "lon": 34.787150000000004, "label": "scan_GPS_S4_LG"},
  {"gt_id": "47de8e44-184c-4dc5-bdab-6bbfd3d6353b", "lat": 31.280610000000017, "lon": 34.78711999999999, "label": "scan_GPS_S4_s22"}
]
```

### Calibration (`calibration.json`, verbatim)
```json
{
  "parameter_source": "derived",
  "parameters": {
    "rssi_at_1m": -53.61,
    "path_loss_n": 1.5675,
    "sigma": 3.424
  },
  "approved": true,
  "calibration_csv_file": "scan_calib1.csv",
  "calibration_mac_address": "2c:59:8a:58:95:c1"
}
```

---

## S4_C1

### Session
```json
{
  "session_id": "aef0c684-f1fd-4181-97f9-9e611631017f",
  "folder_id": "Scan - test protocol",
  "mode": "wifi",
  "created_at": "2026-08-14T09:18:38.868530+00:00"
}
```
- saved_id used (renamed from): `2026-08-14T09-22-14Z`
- saved_at_utc: `2026-08-14T09:22:14.435396Z`
- note: ninth and final session_id in this log. Calibration `fallback`/`open_field`, matching
  the odd-C-label pattern seen throughout (C1/C3 = fallback, C0/C2 = derived).
  `active_reid_artifact`/`active_enriched_artifact` both explicitly correct from the start,
  no fallback-resolution issue. `scan_S4_REID.csv` diff-verified byte-identical to S4_C0's.
  Cross-checked `localization.json`'s 11 cluster IDs against the REID CSV - exact match.

### Gate Check
- localization_result_exists_with_cluster: PASS (total_clusters=11, successful_clusters=5, failed_clusters=6)
- active_reid_csv_resolvable: PASS (`scan_S4_REID.csv`, explicit `active_reid_artifact`)
- ground_truth_exists: PASS (count=3)
- evaluation_exists: PASS (score.total=0.8052)

### Volatile Capture (live session state at query time)
```json
{
  "_pending_calibration": "[MISSING: key entirely absent from session state - this session never called calibration/run, went straight to the fallback preset]",
  "active_enrichment.quality": "[MISSING: active_enrichment]",
  "active_reid.quality": {
    "reid_csv_path": "C:\\projects\\test\\runtime\\DATA\\Scan - test protocol\\scan_S4_REID.csv",
    "total_rows": 550,
    "static_cluster_count": 8,
    "dynamic_cluster_count": 3,
    "unique_dynamic_mac_count": 69,
    "noise_cluster_count": 5,
    "cluster_confidence": {"2": "high", "3": "high", "6": "high"},
    "warnings": []
  },
  "current_localization_result.warnings": [
    "Cluster 14:ea:63:f5:14:1f has insufficient samples",
    "Cluster 2 insufficient movement (time=4.9s, need >=30s; baseline=2.7m, need >=5m)",
    "Cluster 2c:59:8a:58:95:c1: RANSAC removed 34 outlier samples from cluster",
    "Cluster 3: RANSAC removed 123 outlier samples from cluster",
    "Cluster 3 uncertainty radius too large (43.5m, need <=40m)",
    "Cluster 6: RANSAC removed 22 outlier samples from cluster",
    "Cluster 6 uncertainty radius too large (116.5m, need <=40m)",
    "Cluster bc:d5:ed:35:10:00 has insufficient samples",
    "Cluster c8:2e:18:bf:86:c8 has insufficient samples",
    "Noise cluster (6 rows) skipped - aggregate of unassociated MACs, not a single emitter"
  ],
  "execution_metadata": "[NOT AVAILABLE: no execution_id recoverable - current backend process (pid 15004) has no matching stdout/access log on disk; existing log files belong to a different, already-exited process]",
  "active_enriched_artifact": "C:\\projects\\test\\runtime\\DATA\\Scan - test protocol\\scan_S4_ENRICHED.csv",
  "active_reid_artifact": "C:\\projects\\test\\runtime\\DATA\\Scan - test protocol\\scan_S4_REID.csv"
}
```

### REID CSV Stats (from saved copy, `scan_S4_REID.csv` - byte-identical to S4_C0's)
```json
{
  "total_rows": 550,
  "distinct_src_mac": 82,
  "distinct_cluster_id": 12,
  "cluster_type_row_breakdown": {"static": 123, "dynamic": 421, "noise": 6},
  "per_cluster": [
    {"cluster_id": "14:ea:63:f5:14:1f", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -90.0, "rssi_max": -90.0, "rssi_mean": -90.0},
    {"cluster_id": "2", "cluster_type": "dynamic", "row_count": 4, "distinct_src_mac": 2, "rssi_min": -79.0, "rssi_max": -76.0, "rssi_mean": -78.0},
    {"cluster_id": "2c:59:8a:58:95:c1", "cluster_type": "static", "row_count": 59, "distinct_src_mac": 1, "rssi_min": -94.0, "rssi_max": -63.0, "rssi_mean": -76.13559322033899},
    {"cluster_id": "3", "cluster_type": "dynamic", "row_count": 385, "distinct_src_mac": 46, "rssi_min": -89.0, "rssi_max": -61.0, "rssi_mean": -72.46753246753246},
    {"cluster_id": "30:52:23:c0:f2:88", "cluster_type": "static", "row_count": 6, "distinct_src_mac": 1, "rssi_min": -94.0, "rssi_max": -84.0, "rssi_mean": -88.66666666666667},
    {"cluster_id": "44:ef:bf:84:67:21", "cluster_type": "static", "row_count": 3, "distinct_src_mac": 1, "rssi_min": -90.0, "rssi_max": -88.0, "rssi_mean": -89.33333333333333},
    {"cluster_id": "6", "cluster_type": "dynamic", "row_count": 32, "distinct_src_mac": 21, "rssi_min": -90.0, "rssi_max": -68.0, "rssi_mean": -78.75},
    {"cluster_id": "9c:a3:a9:60:44:a4", "cluster_type": "static", "row_count": 8, "distinct_src_mac": 1, "rssi_min": -91.0, "rssi_max": -87.0, "rssi_mean": -89.375},
    {"cluster_id": "9c:a3:a9:69:05:ef", "cluster_type": "static", "row_count": 43, "distinct_src_mac": 1, "rssi_min": -92.0, "rssi_max": -84.0, "rssi_mean": -87.55813953488372},
    {"cluster_id": "bc:d5:ed:35:10:00", "cluster_type": "static", "row_count": 1, "distinct_src_mac": 1, "rssi_min": -82.0, "rssi_max": -82.0, "rssi_mean": -82.0},
    {"cluster_id": "c8:2e:18:bf:86:c8", "cluster_type": "static", "row_count": 2, "distinct_src_mac": 1, "rssi_min": -87.0, "rssi_max": -87.0, "rssi_mean": -87.0},
    {"cluster_id": "noise", "cluster_type": "noise", "row_count": 6, "distinct_src_mac": 5, "rssi_min": -93.0, "rssi_max": -68.0, "rssi_mean": -84.5}
  ]
}
```

### ENRICHED CSV Stats (live path — not copied to save dir; unchanged mtime since S4_C0)
Source: `C:\projects\test\runtime\DATA\Scan - test protocol\scan_S4_ENRICHED.csv`
```json
{
  "total_rows": 5794,
  "match_found_distribution": {"True": 5660, "False": 134},
  "match_found_rate": 0.9768726268553676,
  "match_method_distribution": {"time_identity_best_match": 5660, "no_match": 134},
  "match_score": {"count": 5660, "missing": 134, "min": 1.999, "max": 2.5, "mean": 2.2281703180212014}
}
```

### Evaluation (`evaluation.json`, verbatim)
```json
{
  "matches": [
    {"gt_id": "18ccd9a9-5423-4c4e-865e-95a9cb0b0aac", "gt_label": "scan_GPS_S4_s22", "primary_cluster_id": "2c:59:8a:58:95:c1", "cluster_type": "static", "num_samples": 25, "uncertainty_radius_m": 33.512, "distance_m": 5.767404520390147, "covered": true, "dominance_margin": null, "association_status": "clear_match"}
  ],
  "false_positives": [],
  "false_negatives": [
    {"gt_id": "8fd93e3d-9eec-4814-a00b-d83968437e2a", "lat": 31.280690000000025, "lon": 34.78742999999999, "label": "scan_GPS_S4_sams"}
  ],
  "ambiguous_gts": [
    {"gt_id": "a9e255ad-6ac6-4d79-9d49-432c3e25f77a", "label": "scan_GPS_S4_LG", "nearest_cluster_id": "2c:59:8a:58:95:c1", "nearest_dist_m": 7.58, "competing_cluster_ids": ["2c:59:8a:58:95:c1"]}
  ],
  "duplicates": [],
  "possible_merges": [
    {"cluster_id": "2c:59:8a:58:95:c1", "candidate_gt_ids": ["a9e255ad-6ac6-4d79-9d49-432c3e25f77a", "18ccd9a9-5423-4c4e-865e-95a9cb0b0aac"], "distances_m": [7.584718532723062, 5.767404520390147]}
  ],
  "metrics": {"recall": 0.3333, "precision": 1.0, "coverage": 1.0, "median_error_m": 5.77, "p90_error_m": 5.77, "median_radius_m": 33.51, "count_error": -2},
  "score": {"total": 0.8052, "containment": 1.0, "distance": 1.0, "count": 0.3333, "radius": 0.3858},
  "eval_params": {
    "ratio_gate": 1.2,
    "max_match_dist_m": 30.0,
    "r_normalize_m": 30.0,
    "d_free_m": 10.0,
    "w_containment": 0.4,
    "w_distance": 0.3,
    "w_count": 0.2,
    "w_radius": 0.1,
    "min_reliable_samples": 10,
    "min_reliability_threshold": 0.3
  },
  "n_predictions": 1,
  "n_gt": 3
}
```

### Ground Truth (`ground_truth.json`, verbatim)
```json
[
  {"gt_id": "a9e255ad-6ac6-4d79-9d49-432c3e25f77a", "lat": 31.28062, "lon": 34.787150000000004, "label": "scan_GPS_S4_LG"},
  {"gt_id": "18ccd9a9-5423-4c4e-865e-95a9cb0b0aac", "lat": 31.280610000000017, "lon": 34.78711999999999, "label": "scan_GPS_S4_s22"},
  {"gt_id": "8fd93e3d-9eec-4814-a00b-d83968437e2a", "lat": 31.280690000000025, "lon": 34.78742999999999, "label": "scan_GPS_S4_sams"}
]
```

### Calibration (`calibration.json`, verbatim)
```json
{
  "parameter_source": "fallback",
  "parameters": {
    "rssi_at_1m": -40.0,
    "path_loss_n": 2.0,
    "sigma": 4.0
  },
  "approved": true,
  "calibration_csv_file": null,
  "calibration_mac_address": null,
  "parameter_set_name": "open_field"
}
```
