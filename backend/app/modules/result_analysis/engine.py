"""MOD-011 Result Analysis evaluation engine."""

from __future__ import annotations

import math
import statistics


_RA_RATIO_GATE: float = 1.2
_RA_MAX_MATCH_DIST_M: float = 200.0
_RA_R_NORMALIZE_M: float = 30.0
_RA_DISTANCE_FREE_M: float = 10.0
_RA_W_CONTAINMENT: float = 0.40
_RA_W_DISTANCE: float = 0.30
_RA_W_COUNT: float = 0.20
_RA_W_RADIUS: float = 0.10
_GATE_INF: float = 1e9


def _dist_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_m = 6_371_000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    mlat = math.radians((lat1 + lat2) / 2.0)
    return math.hypot(dlon * math.cos(mlat) * earth_radius_m, dlat * earth_radius_m)


def evaluate(
    predictions: list[dict],
    gt_points: list[dict],
    ratio_gate: float = _RA_RATIO_GATE,
    max_match_dist_m: float = _RA_MAX_MATCH_DIST_M,
    r_normalize_m: float = _RA_R_NORMALIZE_M,
    d_free_m: float = _RA_DISTANCE_FREE_M,
    w_containment: float = _RA_W_CONTAINMENT,
    w_distance: float = _RA_W_DISTANCE,
    w_count: float = _RA_W_COUNT,
    w_radius: float = _RA_W_RADIUS,
) -> dict:
    preds = [pred for pred in predictions if pred.get("lat") is not None and pred.get("lon") is not None]
    gts = list(gt_points)
    n_pred = len(preds)
    n_gt = len(gts)

    dist_m = [
        [_dist_m(float(preds[i]["lat"]), float(preds[i]["lon"]), float(gts[j]["lat"]), float(gts[j]["lon"])) for j in range(n_gt)]
        for i in range(n_pred)
    ]
    cost = [[_GATE_INF] * n_gt for _ in range(n_pred)]
    pack_ambiguous_gt_indices: set[int] = set()
    far_fn_gt_indices: set[int] = set()

    for j in range(n_gt):
        sorted_clusters = sorted(range(n_pred), key=lambda i: dist_m[i][j])
        d1 = dist_m[sorted_clusters[0]][j] if n_pred > 0 else float("inf")

        if n_pred == 0 or d1 > max_match_dist_m:
            far_fn_gt_indices.add(j)
            continue

        nearest_i = sorted_clusters[0]
        if n_pred == 1:
            cost[nearest_i][j] = d1
            continue

        d2 = dist_m[sorted_clusters[1]][j]
        ratio = (d2 / d1) if d1 > 0 else float("inf")
        if ratio >= ratio_gate:
            cost[nearest_i][j] = d1
        else:
            pack_ambiguous_gt_indices.add(j)

    primary_pairs = _linear_sum_assignment(cost)
    matched_pred_idx = {i for i, _ in primary_pairs}
    matched_gt_idx = {j for _, j in primary_pairs}

    matches = []
    for i, j in primary_pairs:
        pred = preds[i]
        gt = gts[j]
        raw_radius = pred.get("radius_m")
        distance = dist_m[i][j]
        sorted_for_j = sorted(range(n_pred), key=lambda ii: dist_m[ii][j])
        d1_check = dist_m[sorted_for_j[0]][j]
        if d1_check > 0 and len(sorted_for_j) > 1:
            d2_check = dist_m[sorted_for_j[1]][j]
            dominance_margin = round(d2_check / d1_check, 3)
        else:
            dominance_margin = None

        matches.append(
            {
                "gt_id": gt["gt_id"],
                "gt_lat": gt["lat"],
                "gt_lon": gt["lon"],
                "gt_label": gt.get("label"),
                "primary_cluster_id": pred["cluster_id"],
                "cluster_lat": pred["lat"],
                "cluster_lon": pred["lon"],
                "cluster_type": pred.get("cluster_type"),
                "num_samples": pred.get("num_samples"),
                "uncertainty_radius_m": raw_radius,
                "distance_m": distance,
                "covered": distance <= (float(raw_radius or 0.0)),
                "association_cost": distance,
                "dominance_margin": dominance_margin,
                "association_status": "clear_match",
                "secondary_candidates": [],
            }
        )

    competed_away_gt_indices = {
        j
        for j in range(n_gt)
        if j not in matched_gt_idx
        and j not in far_fn_gt_indices
        and j not in pack_ambiguous_gt_indices
        and n_pred > 0
    }
    ambiguous_gt_indices = (pack_ambiguous_gt_indices | competed_away_gt_indices) - matched_gt_idx - far_fn_gt_indices
    ambiguous_gts = []
    for j in sorted(ambiguous_gt_indices):
        gt = gts[j]
        sorted_clusters = sorted(range(n_pred), key=lambda i: dist_m[i][j])
        nearest_i = sorted_clusters[0]
        d1 = dist_m[nearest_i][j]
        ambiguous_gts.append(
            {
                "gt_id": gt["gt_id"],
                "lat": gt["lat"],
                "lon": gt["lon"],
                "label": gt.get("label"),
                "nearest_cluster_id": preds[nearest_i]["cluster_id"],
                "nearest_dist_m": round(d1, 2),
                "competing_cluster_ids": [
                    preds[i]["cluster_id"] for i in sorted_clusters if dist_m[i][j] <= d1 * ratio_gate
                ],
            }
        )

    false_positives = [
        {
            "cluster_id": preds[i]["cluster_id"],
            "lat": preds[i]["lat"],
            "lon": preds[i]["lon"],
            "cluster_type": preds[i].get("cluster_type"),
        }
        for i in range(n_pred)
        if i not in matched_pred_idx
    ]
    false_negatives = [
        {"gt_id": gts[j]["gt_id"], "lat": gts[j]["lat"], "lon": gts[j]["lon"], "label": gts[j].get("label")}
        for j in sorted(far_fn_gt_indices)
    ]

    duplicates = []
    for i in range(n_pred):
        if i in matched_pred_idx:
            continue
        for j in matched_gt_idx:
            if dist_m[i][j] <= max_match_dist_m:
                duplicates.append(
                    {
                        "cluster_id": preds[i]["cluster_id"],
                        "competing_for_gt_id": gts[j]["gt_id"],
                        "distance_m": round(dist_m[i][j], 2),
                        "cost": dist_m[i][j],
                    }
                )

    possible_merges = []
    for i in range(n_pred):
        candidate_gt_indices = [j for j in range(n_gt) if dist_m[i][j] <= max_match_dist_m]
        if len(candidate_gt_indices) >= 2:
            possible_merges.append(
                {
                    "cluster_id": preds[i]["cluster_id"],
                    "candidate_gt_ids": [gts[j]["gt_id"] for j in candidate_gt_indices],
                    "distances_m": [dist_m[i][j] for j in candidate_gt_indices],
                }
            )

    errors = [match["distance_m"] for match in matches]
    all_radii = [float(pred.get("radius_m") or 0.0) for pred in preds]
    coverage = sum(1 for match in matches if match["covered"]) / max(len(matches), 1) if matches else 0.0
    median_error = statistics.median(errors) if errors else None
    p90_error = sorted(errors)[max(0, int(math.ceil(0.9 * len(errors))) - 1)] if errors else None
    median_radius = statistics.median(all_radii) if all_radii else None
    recall = len(matches) / n_gt if n_gt > 0 else 0.0
    precision = len(matches) / n_pred if n_pred > 0 else 0.0
    count_error = n_pred - n_gt

    s_containment = coverage
    if median_error is None:
        s_distance = 0.0
    elif median_error <= d_free_m:
        s_distance = 1.0
    else:
        s_distance = max(0.0, 1.0 - ((median_error - d_free_m) / r_normalize_m) ** 2)
    s_count = recall
    if median_radius is None:
        s_radius = 0.0
    elif median_radius <= d_free_m:
        s_radius = 1.0
    else:
        s_radius = max(0.0, 1.0 - ((median_radius - d_free_m) / r_normalize_m) ** 2)
    total_score = w_containment * s_containment + w_distance * s_distance + w_count * s_count + w_radius * s_radius

    return {
        "matches": matches,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "ambiguous_gts": ambiguous_gts,
        "duplicates": duplicates,
        "possible_merges": possible_merges,
        "metrics": {
            "recall": round(recall, 4),
            "precision": round(precision, 4),
            "coverage": round(coverage, 4),
            "median_error_m": round(median_error, 2) if median_error is not None else None,
            "p90_error_m": round(p90_error, 2) if p90_error is not None else None,
            "median_radius_m": round(median_radius, 2) if median_radius is not None else None,
            "count_error": count_error,
        },
        "score": {
            "total": round(total_score, 4),
            "containment": round(s_containment, 4),
            "distance": round(s_distance, 4),
            "count": round(s_count, 4),
            "radius": round(s_radius, 4),
        },
        "eval_params": {
            "ratio_gate": ratio_gate,
            "max_match_dist_m": max_match_dist_m,
            "r_normalize_m": r_normalize_m,
            "d_free_m": d_free_m,
            "w_containment": w_containment,
            "w_distance": w_distance,
            "w_count": w_count,
            "w_radius": w_radius,
        },
        "n_predictions": n_pred,
        "n_gt": n_gt,
        "radius_reliability_note": (
            "Current uncertainty radii are not yet calibrated. "
            "The 'covered' field and radius-based scoring should be treated as indicative only."
        ),
    }


def extract_predictions_from_localization_result(loc_result: dict) -> list[dict]:
    predictions = []
    for cluster in loc_result.get("cluster_results", []):
        if cluster.get("status") == "failed":
            continue
        peak = cluster.get("primary_peak")
        if not peak:
            continue
        regions = cluster.get("uncertainty_regions", [])
        predictions.append(
            {
                "cluster_id": cluster["cluster_id"],
                "cluster_type": cluster.get("cluster_type"),
                "lat": peak["lat"],
                "lon": peak["lon"],
                "radius_m": regions[0]["radius_m"] if regions else None,
                "num_samples": cluster.get("sample_count"),
            }
        )
    return predictions


def _linear_sum_assignment(cost: list[list[float]]) -> list[tuple[int, int]]:
    if not cost or not cost[0]:
        return []
    try:
        import numpy as np
        from scipy.optimize import linear_sum_assignment

        row_ind, col_ind = linear_sum_assignment(np.array(cost))
        return [(int(row), int(col)) for row, col in zip(row_ind, col_ind) if cost[int(row)][int(col)] < _GATE_INF]
    except ModuleNotFoundError:
        return _greedy_assignment(cost)


def _greedy_assignment(cost: list[list[float]]) -> list[tuple[int, int]]:
    pairs: list[tuple[float, int, int]] = []
    for i, row in enumerate(cost):
        for j, value in enumerate(row):
            if value < _GATE_INF:
                pairs.append((value, i, j))
    matched_rows: set[int] = set()
    matched_cols: set[int] = set()
    selected: list[tuple[int, int]] = []
    for _value, i, j in sorted(pairs):
        if i in matched_rows or j in matched_cols:
            continue
        matched_rows.add(i)
        matched_cols.add(j)
        selected.append((i, j))
    return selected
