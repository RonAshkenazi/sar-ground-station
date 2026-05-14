from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any


_LOC_06_GRID_RESOLUTION_M: float = 2.0  # Founder decision: 2m grid resolution
_LOC_07_DYNAMIC_SIGMA_ALPHA: float = 0.05  # FD: Krypto-inspired dynamic sigma; legacy default
_LOC_08_CONFIDENCE_CUTOFF: float = 0.50  # FD-L2: legacy vis_thresh; operator-tunable
_LOC_UNCERTAINTY_PARTICIPATION_FLOOR: float = 0.50  # min posterior for a cell to enter spread calc
_LOC_UNCERTAINTY_ALPHA: float = 2.0  # radius = alpha * weighted_sigma; needs GT calibration
_LOC_13_MIN_SAMPLES_PER_CLUSTER: int = 3
_LOC_02_SEARCH_AREA_BUFFER_M: float = 20.0
_LOC_RANSAC_ITERATIONS: int = 100
_LOC_RANSAC_INLIER_THRESHOLD_DB: float = 10.0
_LOC_RANSAC_MIN_SAMPLES: int = 3
_LOC_RANSAC_EARLY_EXIT_INLIER_RATIO: float = 0.80

REQUIRED_COLUMNS = {"timestamp_utc", "src_mac", "rssi_dbm", "gps_lat", "gps_lon", "cluster_id", "cluster_type"}


def run_localization(
    reid_csv_path: Path,
    calibration: dict,
    bounds_mode: str = "auto_track_plus_buffer",
    buffer_m: float = _LOC_02_SEARCH_AREA_BUFFER_M,
    manual_bounds: dict | None = None,
    grid_resolution_m: float = _LOC_06_GRID_RESOLUTION_M,
    dynamic_sigma_alpha: float = _LOC_07_DYNAMIC_SIGMA_ALPHA,
    confidence_cutoff: float = _LOC_08_CONFIDENCE_CUTOFF,
    uncertainty_participation_floor: float = _LOC_UNCERTAINTY_PARTICIPATION_FLOOR,
    uncertainty_alpha: float = _LOC_UNCERTAINTY_ALPHA,
) -> dict[str, Any]:
    rows = _load_rows(reid_csv_path)
    _validate_calibration(calibration)
    if bounds_mode not in ("auto_track_plus_buffer", "manual_rectangle"):
        raise ValueError("bounds_mode must be auto_track_plus_buffer or manual_rectangle")
    if grid_resolution_m <= 0:
        raise ValueError("grid_resolution_m must be positive")

    usable_rows = [row for row in rows if _valid_sample(row)]
    if not usable_rows:
        raise ValueError("No usable rows in REID artifact")

    # TODO: apply global filters when MOD-004 is implemented
    grouped: dict[str, list[dict[str, str]]] = {}
    cluster_type_by_id: dict[str, str] = {}
    for row in usable_rows:
        cluster_id = str(row.get("cluster_id", ""))
        grouped.setdefault(cluster_id, []).append(row)
        cluster_type_by_id.setdefault(cluster_id, str(row.get("cluster_type", "")))

    bounds, cells, shape, effective_resolution, grid_warnings = _build_grid(
        usable_rows,
        bounds_mode,
        buffer_m,
        manual_bounds,
        grid_resolution_m,
    )
    run_warnings = list(grid_warnings)
    cluster_results = []

    for cluster_id, cluster_rows in sorted(grouped.items(), key=lambda item: item[0]):
        if cluster_id == "noise":
            run_warnings.append(
                f"Noise cluster ({len(cluster_rows)} rows) skipped - "
                "aggregate of unassociated MACs, not a single emitter"
            )
            continue
        if len(cluster_rows) < _LOC_13_MIN_SAMPLES_PER_CLUSTER:
            warning = f"Cluster {cluster_id} has insufficient samples"
            run_warnings.append(warning)
            cluster_results.append(_failed_cluster(cluster_id, cluster_type_by_id[cluster_id], len(cluster_rows), warning))
            continue

        cleaned_rows, ransac_warning = _ransac_filter_rows(cluster_rows, calibration)
        if ransac_warning:
            run_warnings.append(f"Cluster {cluster_id}: {ransac_warning}")
        result = _localize_cluster(
            cluster_id=cluster_id,
            cluster_type=cluster_type_by_id[cluster_id],
            rows=cleaned_rows,
            calibration=calibration,
            cells=cells,
            shape=shape,
            grid_resolution_m=effective_resolution,
            dynamic_sigma_alpha=dynamic_sigma_alpha,
            confidence_cutoff=confidence_cutoff,
            uncertainty_participation_floor=uncertainty_participation_floor,
            uncertainty_alpha=uncertainty_alpha,
        )
        cluster_results.append(result)

    successful = sum(1 for result in cluster_results if result["status"] == "success")
    failed = len(cluster_results) - successful
    if successful == 0:
        raise ValueError("All clusters failed localization")

    return {
        "cluster_results": cluster_results,
        "bounds": bounds,
        "total_clusters": len(cluster_results),
        "successful_clusters": successful,
        "failed_clusters": failed,
        "warnings": run_warnings,
    }


def _ransac_filter_rows(rows: list[dict], calibration: dict) -> tuple[list[dict], str | None]:
    """
    RANSAC-based outlier removal. Returns all rows if the deterministic
    consensus pass cannot keep enough samples for localization.
    """
    if len(rows) < _LOC_RANSAC_MIN_SAMPLES:
        return rows, None

    rssi_at_1m = float(calibration["rssi_at_1m"])
    path_loss_n = float(calibration["path_loss_n"])
    best_inlier_mask: list[bool] = [True] * len(rows)
    best_inlier_count = 0

    import random

    rng = random.Random(42)
    for _ in range(_LOC_RANSAC_ITERATIONS):
        sample_indices = rng.sample(range(len(rows)), _LOC_RANSAC_MIN_SAMPLES)
        sample_lats = [float(rows[index]["gps_lat"]) for index in sample_indices]
        sample_lons = [float(rows[index]["gps_lon"]) for index in sample_indices]
        center_lat = sum(sample_lats) / len(sample_lats)
        center_lon = sum(sample_lons) / len(sample_lons)
        inlier_mask = []
        inlier_count = 0
        for row in rows:
            dist = max(
                _haversine_m(
                    center_lat,
                    center_lon,
                    float(row["gps_lat"]),
                    float(row["gps_lon"]),
                ),
                1.0,
            )
            predicted_rssi = rssi_at_1m - 10 * path_loss_n * math.log10(dist)
            actual_rssi = float(row["rssi_dbm"])
            is_inlier = abs(actual_rssi - predicted_rssi) < _LOC_RANSAC_INLIER_THRESHOLD_DB
            inlier_mask.append(is_inlier)
            if is_inlier:
                inlier_count += 1
        if inlier_count > best_inlier_count:
            best_inlier_count = inlier_count
            best_inlier_mask = inlier_mask
        if inlier_count >= _LOC_RANSAC_EARLY_EXIT_INLIER_RATIO * len(rows):
            break

    cleaned = [row for row, keep in zip(rows, best_inlier_mask) if keep]
    if len(cleaned) < _LOC_RANSAC_MIN_SAMPLES:
        return rows, f"RANSAC found no valid inlier set for cluster; using all {len(rows)} samples"
    removed = len(rows) - len(cleaned)
    if removed > 0:
        return cleaned, f"RANSAC removed {removed} outlier samples from cluster"
    return cleaned, None


def _load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists() or not path.is_file():
        raise ValueError(f"REID CSV not found: {path}")
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        fieldnames = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS.difference(fieldnames)
        if missing:
            raise ValueError(f"REID CSV missing required columns: {', '.join(sorted(missing))}")
        return list(reader)


def _validate_calibration(calibration: dict) -> None:
    for key in ("rssi_at_1m", "path_loss_n", "sigma"):
        value = _safe_float(calibration.get(key))
        if value is None or not math.isfinite(value):
            raise ValueError(f"Calibration parameter {key} must be numeric")


def _valid_sample(row: dict[str, str]) -> bool:
    return (
        _safe_float(row.get("gps_lat")) is not None
        and _safe_float(row.get("gps_lon")) is not None
        and _safe_float(row.get("rssi_dbm")) is not None
    )


def _build_grid(
    rows: list[dict[str, str]],
    bounds_mode: str,
    buffer_m: float,
    manual_bounds: dict | None,
    grid_resolution_m: float,
) -> tuple[dict[str, float], list[tuple[float, float]], tuple[int, int], float, list[str]]:
    warnings: list[str] = []
    if bounds_mode == "manual_rectangle":
        if not manual_bounds:
            raise ValueError("manual_bounds required for manual_rectangle")
        bounds = {key: float(manual_bounds[key]) for key in ("lat_min", "lat_max", "lon_min", "lon_max")}
        if bounds["lat_min"] >= bounds["lat_max"] or bounds["lon_min"] >= bounds["lon_max"]:
            raise ValueError("manual_bounds are invalid")
    else:
        lats = [_safe_float(row["gps_lat"]) for row in rows]
        lons = [_safe_float(row["gps_lon"]) for row in rows]
        lat_min = min(v for v in lats if v is not None)
        lat_max = max(v for v in lats if v is not None)
        lon_min = min(v for v in lons if v is not None)
        lon_max = max(v for v in lons if v is not None)
        mean_lat = (lat_min + lat_max) / 2
        lat_buffer = buffer_m / 111_111
        lon_buffer = buffer_m / _meters_per_lon_degree(mean_lat)
        bounds = {
            "lat_min": lat_min - lat_buffer,
            "lat_max": lat_max + lat_buffer,
            "lon_min": lon_min - lon_buffer,
            "lon_max": lon_max + lon_buffer,
        }

    mean_lat = (bounds["lat_min"] + bounds["lat_max"]) / 2
    was_capped = False
    while True:
        lat_step_deg = grid_resolution_m / 111_111
        lon_step_deg = grid_resolution_m / _meters_per_lon_degree(mean_lat)
        n_lat = max(2, round((bounds["lat_max"] - bounds["lat_min"]) / lat_step_deg))
        n_lon = max(2, round((bounds["lon_max"] - bounds["lon_min"]) / lon_step_deg))
        if n_lat * n_lon <= 40_000:
            break
        was_capped = True
        grid_resolution_m *= math.sqrt((n_lat * n_lon) / 40_000)
    if was_capped:
        warnings = [f"Grid resolution adjusted to {n_lat}x{n_lon} cells; effective resolution {grid_resolution_m:.2f}m"]

    cell_lat_size = (bounds["lat_max"] - bounds["lat_min"]) / n_lat
    cell_lon_size = (bounds["lon_max"] - bounds["lon_min"]) / n_lon
    cells = [
        (bounds["lat_min"] + (i + 0.5) * cell_lat_size, bounds["lon_min"] + (j + 0.5) * cell_lon_size)
        for i in range(n_lat)
        for j in range(n_lon)
    ]
    return bounds, cells, (n_lat, n_lon), grid_resolution_m, warnings


def _localize_cluster(
    cluster_id: str,
    cluster_type: str,
    rows: list[dict[str, str]],
    calibration: dict,
    cells: list[tuple[float, float]],
    shape: tuple[int, int],
    grid_resolution_m: float,
    dynamic_sigma_alpha: float,
    confidence_cutoff: float,
    uncertainty_participation_floor: float,
    uncertainty_alpha: float,
) -> dict[str, Any]:
    score_map = [0.0 for _ in cells]
    rssi_at_1m = float(calibration["rssi_at_1m"])
    path_loss_n = float(calibration["path_loss_n"])
    sigma = float(calibration["sigma"])

    for row in rows:
        sample_lat = float(row["gps_lat"])
        sample_lon = float(row["gps_lon"])
        rssi = float(row["rssi_dbm"])
        for index, (lat, lon) in enumerate(cells):
            distance = max(_haversine_m(sample_lat, sample_lon, lat, lon), 1.0)
            mu = rssi_at_1m - 10 * path_loss_n * math.log10(distance)
            sigma_eff = max(sigma * (1 + dynamic_sigma_alpha * math.log10(distance)), 0.1)
            score_map[index] += math.exp(-0.5 * ((rssi - mu) / sigma_eff) ** 2)

    max_score = max(score_map) if score_map else 0.0
    warnings = []
    posterior = [value / max_score for value in score_map] if max_score else [0.0 for _ in score_map]
    if max_score == 0:
        warnings.append("Zero score map - no usable contributions")

    peak_indices = _find_peaks(posterior, shape, confidence_cutoff)
    peaks = [{"lat": cells[index][0], "lon": cells[index][1], "value": posterior[index]} for index in peak_indices[:3]]
    if not peaks and posterior:
        index = max(range(len(posterior)), key=lambda item: posterior[item])
        peaks = [{"lat": cells[index][0], "lon": cells[index][1], "value": posterior[index]}]

    regions = _merge_regions(
        [
            _uncertainty_region(
                peak,
                cells,
                posterior,
                grid_resolution_m,
                uncertainty_participation_floor,
                uncertainty_alpha,
                shape,
            )
            for peak in peaks
        ]
    )
    grid_cells = [
        {"lat": cells[index][0], "lon": cells[index][1], "value": posterior[index]}
        for index in sorted(range(len(posterior)), key=lambda item: posterior[item], reverse=True)[:500]
    ]
    return {
        "cluster_id": str(cluster_id),
        "cluster_type": str(cluster_type),
        "status": "success",
        "sample_count": len(rows),
        "primary_peak": peaks[0] if peaks else None,
        "candidate_peaks": peaks,
        "uncertainty_regions": regions,
        "grid_cells": grid_cells,
        "warnings": warnings,
        "failure_reason": None,
    }


def _find_peaks(values: list[float], shape: tuple[int, int], confidence_cutoff: float) -> list[int]:
    n_lat, n_lon = shape
    peaks = []
    for i in range(n_lat):
        for j in range(n_lon):
            index = i * n_lon + j
            current = values[index]
            neighbours = []
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if di == 0 and dj == 0:
                        continue
                    ni, nj = i + di, j + dj
                    if 0 <= ni < n_lat and 0 <= nj < n_lon:
                        neighbours.append(values[ni * n_lon + nj])
                    else:
                        neighbours.append(0.0)
            if all(current > neighbour for neighbour in neighbours) and current >= confidence_cutoff:
                peaks.append(index)
    return sorted(peaks, key=lambda item: values[item], reverse=True)


def _uncertainty_region(
    peak: dict[str, float],
    cells: list[tuple[float, float]],
    posterior: list[float],
    grid_resolution_m: float,
    participation_floor: float,
    alpha: float,
    shape: tuple[int, int] | None = None,
) -> dict[str, float]:
    # Weighted spread: radius = alpha * sqrt( sum(w*d^2) / sum(w) ) over the
    # high-posterior component that contains this peak. Using a peak-local component
    # prevents a secondary peak from measuring distance to a different peak's high
    # posterior cells when the floor is raised.
    participating_indices = _peak_participating_indices(peak, cells, posterior, participation_floor, shape)
    total_w = 0.0
    sigma_sq = 0.0
    for index in participating_indices:
        lat, lon = cells[index]
        w = posterior[index]
        d = _haversine_m(peak["lat"], peak["lon"], lat, lon)
        sigma_sq += w * d * d
        total_w += w
    if total_w == 0.0:
        return {"center_lat": peak["lat"], "center_lon": peak["lon"], "radius_m": round(grid_resolution_m, 3)}
    radius = max(alpha * math.sqrt(sigma_sq / total_w), grid_resolution_m)
    return {"center_lat": peak["lat"], "center_lon": peak["lon"], "radius_m": round(radius, 3)}


def _peak_participating_indices(
    peak: dict[str, float],
    cells: list[tuple[float, float]],
    posterior: list[float],
    participation_floor: float,
    shape: tuple[int, int] | None,
) -> set[int]:
    peak_index = _cell_index_for_peak(peak, cells)
    if peak_index is None or posterior[peak_index] < participation_floor:
        return set()
    if shape is None:
        return {index for index, value in enumerate(posterior) if value >= participation_floor}

    n_lat, n_lon = shape
    high_posterior = {index for index, value in enumerate(posterior) if value >= participation_floor}
    component: set[int] = set()
    stack = [peak_index]
    while stack:
        index = stack.pop()
        if index in component or index not in high_posterior:
            continue
        component.add(index)
        i, j = divmod(index, n_lon)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di == 0 and dj == 0:
                    continue
                ni, nj = i + di, j + dj
                if 0 <= ni < n_lat and 0 <= nj < n_lon:
                    stack.append(ni * n_lon + nj)
    return component


def _cell_index_for_peak(peak: dict[str, float], cells: list[tuple[float, float]]) -> int | None:
    for index, (lat, lon) in enumerate(cells):
        if lat == peak["lat"] and lon == peak["lon"]:
            return index
    return None


def _merge_regions(regions: list[dict[str, float]]) -> list[dict[str, float]]:
    merged: list[dict[str, float]] = []
    for region in regions:
        combined = False
        for existing in merged:
            distance = _haversine_m(existing["center_lat"], existing["center_lon"], region["center_lat"], region["center_lon"])
            if distance < existing["radius_m"] + region["radius_m"]:
                existing["center_lat"] = (existing["center_lat"] + region["center_lat"]) / 2
                existing["center_lon"] = (existing["center_lon"] + region["center_lon"]) / 2
                existing["radius_m"] = max(existing["radius_m"], region["radius_m"]) + distance / 2
                combined = True
                break
        if not combined:
            merged.append(dict(region))
    return merged[:3]


def _failed_cluster(cluster_id: str, cluster_type: str, sample_count: int, reason: str) -> dict[str, Any]:
    return {
        "cluster_id": str(cluster_id),
        "cluster_type": str(cluster_type),
        "status": "failed",
        "sample_count": sample_count,
        "primary_peak": None,
        "candidate_peaks": [],
        "uncertainty_regions": [],
        "grid_cells": [],
        "warnings": [reason],
        "failure_reason": "insufficient_samples",
    }


def _safe_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _meters_per_lon_degree(lat: float) -> float:
    return max(111_111 * math.cos(math.radians(lat)), 1.0)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6_371_000.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
