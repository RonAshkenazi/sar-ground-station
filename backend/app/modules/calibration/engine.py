from __future__ import annotations

import csv
import math
import random
from pathlib import Path
from typing import Any


FALLBACK_PRESETS = {
    "urban": {"rssi_at_1m": -40.0, "path_loss_n": 3.5, "sigma": 8.0},
    "open_field": {"rssi_at_1m": -40.0, "path_loss_n": 2.0, "sigma": 4.0},
    "mixed_outdoor": {"rssi_at_1m": -40.0, "path_loss_n": 2.7, "sigma": 6.0},
}

_FIT_WARNING_MIN_SAMPLES: int = 10
_FIT_WARNING_MIN_INLIER_RATIO: float = 0.70


def list_macs_in_csv(csv_path: Path) -> list[str]:
    """Return sorted unique non-empty src_mac values found in csv_path."""
    with csv_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        macs = {row.get("src_mac", "").strip() for row in reader}
    return sorted(mac for mac in macs if mac)


def run_calibration(
    csv_path: Path,
    mac: str,
    gt_mode: str = "mean_first_k",
    gt_k: int = 5,
    manual_lat: float | None = None,
    manual_lon: float | None = None,
    enable_ransac: bool = True,
    ransac_threshold_db: float = 4.0,
    ransac_iterations: int = 100,
    distance_floor_m: float = 1.0,
) -> dict[str, Any]:
    """Run the calibration algorithm from Part B Section 5.4."""
    with csv_path.open(newline="", encoding="utf-8") as file:
        all_rows = list(csv.DictReader(file))

    mac_rows = [row for row in all_rows if row.get("src_mac", "").strip() == mac]
    if not mac_rows:
        return _fail("No rows found for selected MAC address")

    gt_k = max(1, min(gt_k, 20))
    ransac_iterations = max(10, min(ransac_iterations, 1000))
    ransac_threshold_db = max(1.0, min(ransac_threshold_db, 15.0))
    distance_floor_m = max(0.5, min(distance_floor_m, 5.0))

    gt = _resolve_gt(mac_rows, gt_mode, gt_k, manual_lat, manual_lon)
    if gt is None:
        return _fail("Cannot resolve ground-truth point - missing GPS data or manual coordinates")

    gt_lat, gt_lon = gt
    scatter: list[dict[str, Any]] = []
    for row in mac_rows:
        rssi = _safe_float(row.get("rssi_dbm"))
        lat = _safe_float(row.get("gps_lat"))
        lon = _safe_float(row.get("gps_lon"))
        if rssi is None or lat is None or lon is None:
            continue
        distance_m = max(_haversine_m(gt_lat, gt_lon, lat, lon), distance_floor_m)
        scatter.append(
            {
                "distance_m": round(distance_m, 3),
                "log10_distance": round(math.log10(distance_m), 4),
                "rssi": rssi,
                "inlier": True,
            }
        )

    if len(scatter) < 2:
        return _fail("Too few usable rows for regression (need GPS + RSSI in at least 2 rows)")

    xs = [point["log10_distance"] for point in scatter]
    ys = [point["rssi"] for point in scatter]
    inlier_indices = list(range(len(scatter)))

    if enable_ransac:
        inlier_indices = _ransac(xs, ys, ransac_threshold_db, ransac_iterations)
        inlier_set = set(inlier_indices)
        for index, point in enumerate(scatter):
            point["inlier"] = index in inlier_set

    if len(inlier_indices) < 2:
        return _fail("RANSAC left fewer than 2 inliers - calibration cannot continue")

    in_xs = [xs[index] for index in inlier_indices]
    in_ys = [ys[index] for index in inlier_indices]
    intercept, slope, r2 = _linear_fit(in_xs, in_ys)

    rssi_at_1m = round(intercept, 2)
    path_loss_n = round(-slope / 10.0, 4)
    residuals = [y - (intercept + slope * x) for x, y in zip(in_xs, in_ys)]
    mean_residual = sum(residuals) / len(residuals)
    sigma = round(
        math.sqrt(
            sum((residual - mean_residual) ** 2 for residual in residuals)
            / max(len(residuals) - 1, 1)
        ),
        3,
    )

    total = len(scatter)
    inlier_count = len(inlier_indices)
    inlier_ratio = round(inlier_count / total, 3)

    warnings: list[str] = []
    if _FIT_WARNING_MIN_SAMPLES is not None and total < _FIT_WARNING_MIN_SAMPLES:
        warnings.append(f"Low sample count: {total}")
    if (
        _FIT_WARNING_MIN_INLIER_RATIO is not None
        and inlier_ratio < _FIT_WARNING_MIN_INLIER_RATIO
    ):
        warnings.append(f"Low inlier ratio: {inlier_ratio:.1%}")

    return {
        "success": True,
        "error": None,
        "parameters": {
            "rssi_at_1m": rssi_at_1m,
            "path_loss_n": path_loss_n,
            "sigma": sigma,
        },
        "fit_quality": {
            "r2": r2,
            "sample_count": total,
            "inlier_count": inlier_count,
            "inlier_ratio": inlier_ratio,
            "sigma": sigma,
        },
        "scatter": scatter,
        "gt_lat": gt_lat,
        "gt_lon": gt_lon,
        "warnings": warnings,
    }


def _safe_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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


def _resolve_gt(
    rows: list[dict[str, str]],
    gt_mode: str,
    gt_k: int,
    manual_lat: float | None,
    manual_lon: float | None,
) -> tuple[float, float] | None:
    if gt_mode == "manual_map_click":
        if manual_lat is None or manual_lon is None:
            return None
        return (manual_lat, manual_lon)

    usable = [
        row
        for row in rows
        if _safe_float(row.get("gps_lat")) is not None
        and _safe_float(row.get("gps_lon")) is not None
    ]
    if not usable:
        return None

    if gt_mode == "first_sample":
        lat = _safe_float(usable[0].get("gps_lat"))
        lon = _safe_float(usable[0].get("gps_lon"))
        if lat is None or lon is None:
            return None
        return (lat, lon)

    selected_rows = usable[:gt_k]
    valid = [
        (lat, lon)
        for lat, lon in (
            (_safe_float(row.get("gps_lat")), _safe_float(row.get("gps_lon")))
            for row in selected_rows
        )
        if lat is not None and lon is not None
    ]
    if not valid:
        return None
    return (
        sum(lat for lat, _ in valid) / len(valid),
        sum(lon for _, lon in valid) / len(valid),
    )


def _linear_fit(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    count = len(xs)
    if count < 2:
        return (0.0, 0.0, 0.0)
    mean_x = sum(xs) / count
    mean_y = sum(ys) / count
    ss_xx = sum((x - mean_x) ** 2 for x in xs)
    ss_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    ss_yy = sum((y - mean_y) ** 2 for y in ys)
    if ss_xx == 0:
        return (mean_y, 0.0, 0.0)
    slope = ss_xy / ss_xx
    intercept = mean_y - slope * mean_x
    r2 = ss_xy**2 / (ss_xx * ss_yy) if ss_yy > 0 else 1.0
    return (intercept, slope, round(r2, 4))


def _ransac(
    xs: list[float],
    ys: list[float],
    threshold_db: float,
    iterations: int,
) -> list[int]:
    count = len(xs)
    if count < 2:
        return list(range(count))

    best_inliers: list[int] = []
    rng = random.Random(42)

    for _ in range(iterations):
        first, second = rng.sample(range(count), 2)
        if xs[first] == xs[second]:
            continue
        intercept, slope, _ = _linear_fit(
            [xs[first], xs[second]],
            [ys[first], ys[second]],
        )
        inliers = [
            index
            for index in range(count)
            if abs(ys[index] - (intercept + slope * xs[index])) <= threshold_db
        ]
        if len(inliers) > len(best_inliers):
            best_inliers = inliers

    return best_inliers if best_inliers else list(range(count))


def _fail(error: str) -> dict[str, Any]:
    return {
        "success": False,
        "error": error,
        "parameters": None,
        "fit_quality": None,
        "scatter": [],
        "gt_lat": None,
        "gt_lon": None,
        "warnings": [],
    }
