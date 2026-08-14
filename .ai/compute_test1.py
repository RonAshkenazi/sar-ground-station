#!/usr/bin/env python3
"""
compute_test1.py — offline recomputation of Test 1 (SAR Operational) and the
Combined score for saved sessions of project P-2026-078.

WHY THIS EXISTS
---------------
Test 2 (Research) is computed in the backend and persisted verbatim to
`evaluation.json` inside every saved session, so RUN_LOG.md already carries it.

Test 1 is computed in the browser (`ResultAnalysisPage.tsx`, `useMemo`) and is
never persisted: neither the score, nor the zone polygon, nor `expectedEmitters`,
nor `circleOverlapThreshold` are written to disk. It therefore cannot be read
back out of a saved session — it can only be RECOMPUTED from what was saved.

This script recomputes it from `localization.json` + `ground_truth.json`, using
a DETERMINISTIC zone derived from the ground-truth points rather than a
hand-drawn lasso, and emits RUN_LOG-shaped markdown blocks.

Every geometry function below is a line-by-line port of
`frontend/src/utils/geoUtils.ts`. Run `--selftest` to check the port against the
same cases as `geoUtils.test.ts` before trusting any output.

ZONE DEFINITION (the one input that did not exist during the field runs)
-----------------------------------------------------------------------
zone = axis-aligned bounding box of that capture's ground-truth points,
       expanded by --buffer-m metres on every side.

Chosen because it is reproducible, degenerates gracefully to a square for a
single-GT capture (S1), is identical across C0/C1/C2/C3 of the same capture by
construction, and can be stated in the report in one sentence. It is NOT what a
SAR operator would draw by hand; that difference must be disclosed wherever the
number is used.

USAGE
-----
    python compute_test1.py --selftest
    python compute_test1.py --saved-root "runtime/Saved Scans" --buffer-m 30

Outputs `test1_blocks.md` (append to RUN_LOG.md) and `test1_summary.json`.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

M_PER_DEG_LAT = 111320.0

# UI default in ResultAnalysisPage.tsx: useState(0.20)
DEFAULT_OVERLAP_THRESHOLD = 0.20
# unionCircleAreaWithinPolygonM2 default, as called by the page (no 3rd arg)
DEFAULT_MAX_SAMPLES = 40000
# circleIntersectionAreaM2 default, as called by the page (no gridN arg)
DEFAULT_GRID_N = 40


# --------------------------------------------------------------------------
# geoUtils.ts port — do not "improve" these; they must match the app exactly
# --------------------------------------------------------------------------

def point_in_polygon(lat: float, lon: float, polygon: list[tuple[float, float]]) -> bool:
    n = len(polygon)
    if n < 3:
        return False
    inside = False
    j = n - 1
    for i in range(n):
        lat_i, lon_i = polygon[i]
        lat_j, lon_j = polygon[j]
        if (lon_i > lon) != (lon_j > lon):
            if lon_j != lon_i:
                x = (lat_j - lat_i) * (lon - lon_i) / (lon_j - lon_i) + lat_i
                if lat < x:
                    inside = not inside
        j = i
    return inside


def polygon_area_m2(polygon: list[tuple[float, float]]) -> float:
    n = len(polygon)
    if n < 3:
        return 0.0
    cent_lat = sum(p[0] for p in polygon) / n
    m_per_deg_lon = M_PER_DEG_LAT * math.cos(math.radians(cent_lat))
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        xi = polygon[i][1] * m_per_deg_lon
        yi = polygon[i][0] * M_PER_DEG_LAT
        xj = polygon[j][1] * m_per_deg_lon
        yj = polygon[j][0] * M_PER_DEG_LAT
        area += xi * yj - xj * yi
    return abs(area) / 2.0


def circle_intersection_area_m2(
    center_lat: float,
    center_lon: float,
    radius_m: float,
    polygon: list[tuple[float, float]],
    grid_n: int = DEFAULT_GRID_N,
) -> float:
    if radius_m <= 0 or len(polygon) < 3:
        return 0.0
    cent_lat = sum(p[0] for p in polygon) / len(polygon)
    m_per_deg_lon = M_PER_DEG_LAT * math.cos(math.radians(cent_lat))
    cx = center_lon * m_per_deg_lon
    cy = center_lat * M_PER_DEG_LAT
    step = (2 * radius_m) / grid_n
    inside = 0
    total = 0
    for i in range(grid_n + 1):
        my = -radius_m + i * step
        for j in range(grid_n + 1):
            mx = -radius_m + j * step
            if mx * mx + my * my > radius_m * radius_m:
                continue
            total += 1
            p_lat = (cy + my) / M_PER_DEG_LAT
            p_lon = (cx + mx) / m_per_deg_lon
            if point_in_polygon(p_lat, p_lon, polygon):
                inside += 1
    return 0.0 if total == 0 else (inside / total) * math.pi * radius_m * radius_m


def union_circle_area_within_polygon_m2(
    circles: list[dict],
    polygon: list[tuple[float, float]],
    max_samples: int = DEFAULT_MAX_SAMPLES,
) -> float:
    valid = [c for c in circles if c["radiusM"] > 0]
    if not valid or len(polygon) < 3:
        return 0.0

    lats = [p[0] for p in polygon]
    lons = [p[1] for p in polygon]
    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)
    if lat_min == lat_max or lon_min == lon_max:
        return 0.0

    cent_lat = sum(lats) / len(polygon)
    m_per_deg_lon = M_PER_DEG_LAT * math.cos(math.radians(cent_lat))
    height_m = (lat_max - lat_min) * M_PER_DEG_LAT
    width_m = (lon_max - lon_min) * m_per_deg_lon
    aspect = width_m / height_m if width_m > 0 and height_m > 0 else 1.0

    n_lat = max(1, round(math.sqrt(max_samples / max(aspect, 0.0001))))
    n_lon = max(1, round(n_lat * aspect))
    while n_lat * n_lon > max_samples:
        n_lat = max(1, math.floor(n_lat * 0.95))
        n_lon = max(1, math.floor(n_lon * 0.95))

    lat_step = (lat_max - lat_min) / n_lat
    lon_step = (lon_max - lon_min) / n_lon
    cell_area = abs(lat_step * M_PER_DEG_LAT * lon_step * m_per_deg_lon)
    projected = [
        {"x": c["centerLon"] * m_per_deg_lon, "y": c["centerLat"] * M_PER_DEG_LAT, "r": c["radiusM"]}
        for c in valid
    ]

    covered = 0
    for lat_index in range(n_lat):
        cell_lat = lat_min + (lat_index + 0.5) * lat_step
        cell_y = cell_lat * M_PER_DEG_LAT
        for lon_index in range(n_lon):
            cell_lon = lon_min + (lon_index + 0.5) * lon_step
            if not point_in_polygon(cell_lat, cell_lon, polygon):
                continue
            cell_x = cell_lon * m_per_deg_lon
            for circle in projected:
                dx = cell_x - circle["x"]
                dy = cell_y - circle["y"]
                if dx * dx + dy * dy <= circle["r"] * circle["r"]:
                    covered += 1
                    break

    return min(covered * cell_area, polygon_area_m2(polygon))


# --------------------------------------------------------------------------
# Zone derivation
# --------------------------------------------------------------------------

def derive_zone(gt_points: list[dict], buffer_m: float) -> list[tuple[float, float]]:
    """Axis-aligned GT bounding box expanded by buffer_m on every side."""
    lats = [float(p["lat"]) for p in gt_points]
    lons = [float(p["lon"]) for p in gt_points]
    cent_lat = sum(lats) / len(lats)
    m_per_deg_lon = M_PER_DEG_LAT * math.cos(math.radians(cent_lat))
    d_lat = buffer_m / M_PER_DEG_LAT
    d_lon = buffer_m / m_per_deg_lon
    lat_min, lat_max = min(lats) - d_lat, max(lats) + d_lat
    lon_min, lon_max = min(lons) - d_lon, max(lons) + d_lon
    # counter-clockwise, same [lat, lon] ordering the app's lasso produces
    return [
        (lat_min, lon_min),
        (lat_min, lon_max),
        (lat_max, lon_max),
        (lat_max, lon_min),
    ]


# --------------------------------------------------------------------------
# Test 1 — port of the test1 useMemo in ResultAnalysisPage.tsx
# --------------------------------------------------------------------------

def compute_test1(
    localization: dict,
    zone: list[tuple[float, float]],
    expected_emitters: int,
    overlap_threshold: float,
) -> dict:
    successful = [
        c for c in localization.get("cluster_results", [])
        if c.get("status") == "success" and c.get("primary_peak")
    ]
    # UI defaults at the time of the runs: showStaticClusters=true, hiddenClusters empty.
    # So the only filter that applies is the zone test on the primary peak.
    visible = [
        c for c in successful
        if point_in_polygon(float(c["primary_peak"]["lat"]), float(c["primary_peak"]["lon"]), zone)
    ]

    n_circles = 0
    for cluster in visible:
        for region in cluster.get("uncertainty_regions", []):
            r = float(region["radius_m"])
            if r <= 0:
                continue
            full_area = math.pi * r * r
            in_area = circle_intersection_area_m2(
                float(region["center_lat"]), float(region["center_lon"]), r, zone
            )
            if in_area / full_area >= overlap_threshold:
                n_circles += 1

    s_count = max(0.0, 1 - abs(n_circles - expected_emitters) / expected_emitters)
    zone_area = polygon_area_m2(zone)
    circles = [
        {"centerLat": float(rg["center_lat"]), "centerLon": float(rg["center_lon"]), "radiusM": float(rg["radius_m"])}
        for c in visible
        for rg in c.get("uncertainty_regions", [])
        if float(rg["radius_m"]) > 0
    ]
    circle_area = union_circle_area_within_polygon_m2(circles, zone)
    area_ratio = circle_area / zone_area if zone_area > 0 else 1.0
    s_area = max(0.0, 1 - area_ratio * area_ratio)

    return {
        "total": (s_count + s_area) / 2,
        "s_count": s_count,
        "s_area": s_area,
        "n_circles": n_circles,
        "n_expected": expected_emitters,
        "circle_area_m2": circle_area,
        "zone_area_m2": zone_area,
        "area_ratio": area_ratio,
        "clusters_successful": len(successful),
        "clusters_in_zone": len(visible),
        "clusters_outside_zone": len(successful) - len(visible),
    }


# --------------------------------------------------------------------------
# Saved-session walking and reporting
# --------------------------------------------------------------------------

def read_json(path: Path):
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def process_save(save_dir: Path, buffer_m: float, overlap_threshold: float) -> dict:
    label = save_dir.name
    localization = read_json(save_dir / "localization.json")
    gt_points = read_json(save_dir / "ground_truth.json")
    evaluation = read_json(save_dir / "evaluation.json")

    record: dict = {"label": label, "path": str(save_dir)}

    if localization is None:
        record["error"] = "[MISSING: localization.json]"
        return record
    if not gt_points:
        record["error"] = "[MISSING: ground_truth.json — zone and expected_emitters cannot be derived]"
        return record

    zone = derive_zone(gt_points, buffer_m)
    test1 = compute_test1(localization, zone, len(gt_points), overlap_threshold)

    if evaluation is None:
        test2_total = None
        record["test2_note"] = "[MISSING: evaluation.json]"
    else:
        test2_total = evaluation.get("score", {}).get("total")

    record["zone_corners"] = [[round(lat, 9), round(lon, 9)] for lat, lon in zone]
    record["zone_rule"] = f"GT bbox + {buffer_m:g} m buffer"
    record["expected_emitters"] = len(gt_points)
    record["circle_overlap_threshold"] = overlap_threshold
    record["test1"] = test1
    record["test2_total"] = test2_total
    record["combined"] = (test1["total"] + test2_total) / 2 if test2_total is not None else None
    return record


def render_block(record: dict) -> str:
    label = record["label"]
    if "error" in record:
        return f"## {label}\n\n### Test 1 / Combined (recomputed offline)\n{record['error']}\n\n---\n"

    t1 = record["test1"]
    payload = {
        "provenance": "RECOMPUTED OFFLINE by fieldwork/compute_test1.py — not produced by the app. "
                      "Test 1 is browser-only state and was never persisted during the field runs.",
        "zone_rule": record["zone_rule"],
        "zone_corners_lat_lon": record["zone_corners"],
        "zone_area_m2": round(t1["zone_area_m2"], 1),
        "inputs": {
            "expected_emitters": record["expected_emitters"],
            "circle_overlap_threshold": record["circle_overlap_threshold"],
            "show_static_clusters": True,
            "hidden_clusters": [],
        },
        "cluster_accounting": {
            "successful_clusters": t1["clusters_successful"],
            "in_zone": t1["clusters_in_zone"],
            "outside_zone_excluded": t1["clusters_outside_zone"],
        },
        "test1": {
            "n_circles": t1["n_circles"],
            "n_expected": t1["n_expected"],
            "s_count": round(t1["s_count"], 4),
            "circle_union_area_m2": round(t1["circle_area_m2"], 1),
            "area_ratio": round(t1["area_ratio"], 4),
            "s_area": round(t1["s_area"], 4),
            "total": round(t1["total"], 4),
        },
        "test2_total": record["test2_total"],
        "combined": round(record["combined"], 4) if record["combined"] is not None else None,
    }
    body = json.dumps(payload, indent=2, ensure_ascii=False)
    return f"## {label}\n\n### Test 1 / Combined (recomputed offline)\n```json\n{body}\n```\n\n---\n"


# --------------------------------------------------------------------------
# Self-test — mirrors frontend/src/utils/geoUtils.test.ts
# --------------------------------------------------------------------------

def selftest() -> int:
    square = [(0.0, 0.0), (0.0, 0.001), (0.001, 0.001), (0.001, 0.0)]
    big_square = [(0.0, 0.0), (0.0, 0.01), (0.01, 0.01), (0.01, 0.0)]
    failures = []

    def check(name, condition):
        print(f"  {'PASS' if condition else 'FAIL'}  {name}")
        if not condition:
            failures.append(name)

    print("geoUtils port self-test (mirrors geoUtils.test.ts):")
    check("point inside polygon", point_in_polygon(0.0005, 0.0005, square) is True)
    check("point outside polygon", point_in_polygon(0.002, 0.0005, square) is False)
    check("empty polygon", point_in_polygon(0.0005, 0.0005, []) is False)
    check("polygon area 12000..13000 m2", 12000 < polygon_area_m2(square) < 13000)

    full = circle_intersection_area_m2(0.005, 0.005, 5, big_square)
    check("full circle inside ~ pi r^2", abs(full - math.pi * 25) < 1.0)
    check("circle outside ~ 0", circle_intersection_area_m2(0.005, 0.02, 5, square) < 1)

    half = circle_intersection_area_m2(0.0005, 0.001, 50, square)
    half_expected = math.pi * 2500 / 2
    check("half circle on edge ~ pi r^2 / 2", half_expected * 0.88 < half < half_expected * 1.12)

    circles = [
        {"centerLat": 0.004, "centerLon": 0.004, "radiusM": 20},
        {"centerLat": 0.006, "centerLon": 0.006, "radiusM": 20},
    ]
    union = union_circle_area_within_polygon_m2(circles, big_square, 80000)
    expected = sum(
        circle_intersection_area_m2(c["centerLat"], c["centerLon"], c["radiusM"], big_square) for c in circles
    )
    check("union of disjoint circles ~ sum", expected * 0.9 < union < expected * 1.1)

    dup = [
        {"centerLat": 0.005, "centerLon": 0.005, "radiusM": 25},
        {"centerLat": 0.005, "centerLon": 0.005, "radiusM": 25},
    ]
    union_dup = union_circle_area_within_polygon_m2(dup, big_square, 80000)
    expected_dup = circle_intersection_area_m2(0.005, 0.005, 25, big_square)
    check("identical circles counted once", expected_dup * 0.9 < union_dup < expected_dup * 1.1)

    oversized = union_circle_area_within_polygon_m2(
        [
            {"centerLat": 0.0005, "centerLon": 0.0005, "radiusM": 150},
            {"centerLat": 0.00045, "centerLon": 0.0005, "radiusM": 150},
            {"centerLat": 0.00055, "centerLon": 0.0005, "radiusM": 150},
        ],
        square,
        80000,
    )
    check("union never exceeds polygon area", oversized <= polygon_area_m2(square) + 1e-6)

    print(f"\n{'ALL PASS' if not failures else str(len(failures)) + ' FAILURE(S): ' + ', '.join(failures)}")
    return 0 if not failures else 1


# --------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--saved-root", default="runtime/Saved Scans",
                        help="root containing <folder_id>/<label>/ save directories")
    parser.add_argument("--buffer-m", type=float, default=30.0,
                        help="zone buffer around the GT bounding box, in metres (default 30)")
    parser.add_argument("--overlap-threshold", type=float, default=DEFAULT_OVERLAP_THRESHOLD,
                        help="circle overlap threshold, must match the UI default (0.20)")
    parser.add_argument("--out", default="test1_blocks.md")
    parser.add_argument("--json", dest="json_out", default="test1_summary.json")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    root = Path(args.saved_root)
    if not root.exists():
        print(f"ERROR: saved root not found: {root.resolve()}", file=sys.stderr)
        return 2

    save_dirs = sorted(p.parent for p in root.glob("*/*/localization.json"))
    if not save_dirs:
        print(f"ERROR: no saved sessions with localization.json under {root.resolve()}", file=sys.stderr)
        return 2

    records = [process_save(d, args.buffer_m, args.overlap_threshold) for d in save_dirs]

    Path(args.out).write_text("".join(render_block(r) for r in records), encoding="utf-8")
    Path(args.json_out).write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"{'LABEL':14s} {'T1':>7s} {'T2':>7s} {'COMB':>7s}  {'circles':>7s} {'ratio':>7s}")
    for record in records:
        if "error" in record:
            print(f"{record['label']:14s} {record['error']}")
            continue
        t1 = record["test1"]
        t2 = record["test2_total"]
        comb = record["combined"]
        print(
            f"{record['label']:14s} {t1['total']:7.4f} "
            f"{(f'{t2:.4f}' if t2 is not None else 'n/a'):>7s} "
            f"{(f'{comb:.4f}' if comb is not None else 'n/a'):>7s}  "
            f"{t1['n_circles']:>3d}/{t1['n_expected']:<3d} {t1['area_ratio']:7.4f}"
        )
    print(f"\nWrote {args.out} and {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
