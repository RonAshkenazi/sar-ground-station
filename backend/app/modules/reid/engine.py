from __future__ import annotations

import csv
import datetime as dt
import math
from pathlib import Path
from typing import Any


_REID_01_ASSOCIATION_THRESHOLD: float = 1.0  # TODO: TBD per spec Part B REID-01
_REID_02_CONFLICT_RESOLUTION = "greedy_best_valid_match"

_REID_WIFI_01_SEQ_GAP_THRESHOLD: float = 1.0  # TODO: TBD per spec Part B REID-WIFI-01 - extract from legacy app
_REID_WIFI_02_MAX_ROTATION_TIME_WINDOW_MS: float = 1.0  # TODO: TBD per spec Part B REID-WIFI-02
_REID_WIFI_03_TIME_GAP_WEIGHT: float = 1.0  # TODO: TBD per spec Part B REID-WIFI-03
_REID_WIFI_04_SEQ_GAP_WEIGHT: float = 1.0  # TODO: TBD per spec Part B REID-WIFI-04
_REID_WIFI_05_IE_SIMILARITY_WEIGHT: float = 1.0  # TODO: TBD per spec Part B REID-WIFI-05
_REID_WIFI_06_FINGERPRINT_WEIGHT: float = 1.0  # TODO: TBD per spec Part B REID-WIFI-06
_REID_WIFI_07_RSSI_CONTINUITY_WEIGHT: float = 1.0  # TODO: TBD per spec Part B REID-WIFI-07
_REID_WIFI_08_FRAME_LENGTH_WEIGHT: float = 1.0  # TODO: TBD per spec Part B REID-WIFI-08
_REID_WIFI_09_VENDOR_CONSISTENCY_WEIGHT: float = 1.0  # TODO: TBD per spec Part B REID-WIFI-09
_REID_WIFI_10_SPATIAL_CONTINUITY_WEIGHT: float = 1.0  # TODO: TBD per spec Part B REID-WIFI-10

REQUIRED_COLUMNS = {"timestamp_utc", "src_mac", "rssi_dbm", "gps_lat", "gps_lon", "match_found"}


def run_reid(enriched_csv_path: Path, protocol: str) -> dict[str, Any]:
    if not enriched_csv_path.exists() or not enriched_csv_path.is_file():
        raise ValueError(f"Enriched CSV not found: {enriched_csv_path}")
    if protocol not in ("wifi", "ble"):
        raise ValueError("protocol must be 'wifi' or 'ble'")

    with enriched_csv_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    missing = REQUIRED_COLUMNS.difference(fieldnames)
    if missing:
        raise ValueError(f"Enriched CSV missing required columns: {', '.join(sorted(missing))}")

    warnings: list[str] = []
    static_macs = {row["src_mac"] for row in rows if _is_static_mac(row.get("src_mac"))}
    assigned: dict[int, tuple[str, str]] = {}
    for index, row in enumerate(rows):
        mac = row.get("src_mac", "")
        if mac in static_macs:
            assigned[index] = (mac, "static")

    dynamic_units = _build_dynamic_units(rows, assigned)
    accepted: list[tuple[str, str, float]] = []
    if protocol == "ble":
        warnings.append("BLE Re-ID feature computation is not implemented; dynamic MACs remain singleton clusters")
    else:
        candidates = _generate_candidates(dynamic_units)
        associations = [
            (src, dst, score)
            for src, dst, score in (
                (src, dst, _association_score(dynamic_units[src], dynamic_units[dst]))
                for src, dst in candidates
            )
            if score >= _REID_01_ASSOCIATION_THRESHOLD
        ]
        accepted = _resolve_conflicts(associations)

    cluster_by_unit = _cluster_units(dynamic_units, accepted)
    for unit_id, cluster_id in cluster_by_unit.items():
        for row_index in dynamic_units[unit_id]["indices"]:
            assigned[row_index] = (str(cluster_id), "dynamic")

    output_rows = []
    for index, row in enumerate(rows):
        cluster_id, cluster_type = assigned[index]
        output = dict(row)
        output["cluster_id"] = cluster_id
        output["cluster_type"] = cluster_type
        output_rows.append(output)

    stem = enriched_csv_path.stem
    if stem.lower().endswith("_enriched"):
        stem = stem[: -len("_enriched")]
    output_path = enriched_csv_path.parent / f"{stem}_REID.csv"
    output_fields = fieldnames + [name for name in ("cluster_id", "cluster_type") if name not in fieldnames]
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=output_fields)
        writer.writeheader()
        writer.writerows(output_rows)

    dynamic_cluster_sizes: dict[str, int] = {}
    for unit_id, cluster_id in cluster_by_unit.items():
        dynamic_cluster_sizes.setdefault(str(cluster_id), 0)
        dynamic_cluster_sizes[str(cluster_id)] += 1

    return {
        "reid_csv_path": str(output_path.resolve()),
        "total_rows": len(rows),
        "static_cluster_count": len(static_macs),
        "dynamic_cluster_count": len(dynamic_cluster_sizes),
        "singleton_dynamic_count": sum(1 for size in dynamic_cluster_sizes.values() if size == 1),
        "warnings": warnings,
    }


def _is_static_mac(mac: object) -> bool:
    if not mac:
        return False
    first = str(mac).split(":")[0]
    try:
        return int(first, 16) & 0x02 == 0
    except ValueError:
        return False


def _build_dynamic_units(rows: list[dict[str, str]], assigned: dict[int, tuple[str, str]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[tuple[int, dict[str, str]]]] = {}
    for index, row in enumerate(rows):
        if index in assigned:
            continue
        mac = row.get("src_mac", "")
        if not mac:
            # Rows with no src_mac (e.g. heartbeat frame_type) carry no device identity
            assigned[index] = ("", "static")
            continue
        grouped.setdefault(mac, []).append((index, row))

    units: dict[str, dict[str, Any]] = {}
    for mac, indexed_rows in grouped.items():
        indexed_rows.sort(key=lambda item: _parse_time(item[1].get("timestamp_utc")) or 0)
        units[mac] = {
            "id": mac,
            "mac": mac,
            "indices": [index for index, _ in indexed_rows],
            "rows": [row for _, row in indexed_rows],
            "first_time": _parse_time(indexed_rows[0][1].get("timestamp_utc")),
            "last_time": _parse_time(indexed_rows[-1][1].get("timestamp_utc")),
        }
    return units


def _generate_candidates(units: dict[str, dict[str, Any]]) -> list[tuple[str, str]]:
    candidates = []
    for left_id, left in units.items():
        for right_id, right in units.items():
            if left_id == right_id:
                continue
            if left["last_time"] is None or right["first_time"] is None:
                continue
            if left["last_time"] > right["first_time"]:
                continue
            gap_ms = (right["first_time"] - left["last_time"]) * 1000
            if gap_ms <= _REID_WIFI_02_MAX_ROTATION_TIME_WINDOW_MS:
                candidates.append((left_id, right_id))
    return candidates


def _association_score(left: dict[str, Any], right: dict[str, Any]) -> float:
    a = left["rows"][-1]
    b = right["rows"][0]
    gap_ms = ((_parse_time(b.get("timestamp_utc")) or 0) - (_parse_time(a.get("timestamp_utc")) or 0)) * 1000
    features = {
        "time": max(0.0, 1.0 - gap_ms / _REID_WIFI_02_MAX_ROTATION_TIME_WINDOW_MS),
        "seq": _seq_gap_score(a.get("seq_ctl"), b.get("seq_ctl")),
        "ie": _jaccard(_split_set(a.get("ie_ids")), _split_set(b.get("ie_ids"))),
        "fingerprint": _fingerprint_score(a.get("ie_fingerprint"), b.get("ie_fingerprint")),
        "rssi": max(0.0, 1.0 - abs(_mean_float(left["rows"], "rssi_dbm") - _mean_float(right["rows"], "rssi_dbm")) / 30),
        "frame_len": _frame_length_score(left["rows"], right["rows"]),
        "vendor": _vendor_score(left["mac"], right["mac"], a.get("src_vendor"), b.get("src_vendor")),
        "spatial": _spatial_score(a, b),
    }
    weighted = (
        features["time"] * _REID_WIFI_03_TIME_GAP_WEIGHT
        + features["seq"] * _REID_WIFI_04_SEQ_GAP_WEIGHT
        + features["ie"] * _REID_WIFI_05_IE_SIMILARITY_WEIGHT
        + features["fingerprint"] * _REID_WIFI_06_FINGERPRINT_WEIGHT
        + features["rssi"] * _REID_WIFI_07_RSSI_CONTINUITY_WEIGHT
        + features["frame_len"] * _REID_WIFI_08_FRAME_LENGTH_WEIGHT
        + features["vendor"] * _REID_WIFI_09_VENDOR_CONSISTENCY_WEIGHT
        + features["spatial"] * _REID_WIFI_10_SPATIAL_CONTINUITY_WEIGHT
    )
    total_weight = (
        _REID_WIFI_03_TIME_GAP_WEIGHT
        + _REID_WIFI_04_SEQ_GAP_WEIGHT
        + _REID_WIFI_05_IE_SIMILARITY_WEIGHT
        + _REID_WIFI_06_FINGERPRINT_WEIGHT
        + _REID_WIFI_07_RSSI_CONTINUITY_WEIGHT
        + _REID_WIFI_08_FRAME_LENGTH_WEIGHT
        + _REID_WIFI_09_VENDOR_CONSISTENCY_WEIGHT
        + _REID_WIFI_10_SPATIAL_CONTINUITY_WEIGHT
    )
    return weighted / total_weight if total_weight else 0.0


def _resolve_conflicts(associations: list[tuple[str, str, float]]) -> list[tuple[str, str, float]]:
    accepted = []
    predecessors: set[str] = set()
    successors: set[str] = set()
    for src, dst, score in sorted(associations, key=lambda item: item[2], reverse=True):
        if src in successors or dst in predecessors:
            continue
        accepted.append((src, dst, score))
        successors.add(src)
        predecessors.add(dst)
    return accepted


def _cluster_units(units: dict[str, dict[str, Any]], accepted: list[tuple[str, str, float]]) -> dict[str, int]:
    parent = {unit_id: unit_id for unit_id in units}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left: str, right: str) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for src, dst, _score in accepted:
        union(src, dst)

    roots = sorted({find(unit_id) for unit_id in units})
    cluster_ids = {root: index + 1 for index, root in enumerate(roots)}
    return {unit_id: cluster_ids[find(unit_id)] for unit_id in units}


def _seq_gap_score(left: object, right: object) -> float:
    left_value = _safe_float(left)
    right_value = _safe_float(right)
    if left_value is None and right_value is None:
        return 1.0
    if left_value is None or right_value is None:
        return 0.5
    return max(0.0, 1.0 - abs(right_value - left_value) / _REID_WIFI_01_SEQ_GAP_THRESHOLD)


def _fingerprint_score(left: object, right: object) -> float:
    if left and right:
        return 1.0 if str(left) == str(right) else 0.0
    if left or right:
        return 0.5
    return 0.5


def _frame_length_score(left_rows: list[dict[str, str]], right_rows: list[dict[str, str]]) -> float:
    left = _mean_optional(left_rows, "frame_len")
    right = _mean_optional(right_rows, "frame_len")
    if left is None or right is None:
        return 0.5
    return max(0.0, 1.0 - abs(left - right) / 200)


def _vendor_score(left_mac: str, right_mac: str, left_vendor: object, right_vendor: object) -> float:
    if ":".join(left_mac.split(":")[:3]) == ":".join(right_mac.split(":")[:3]):
        return 1.0
    if left_vendor and right_vendor and left_vendor == right_vendor:
        return 0.5
    return 0.0


def _spatial_score(left: dict[str, str], right: dict[str, str]) -> float:
    lat1 = _safe_float(left.get("gps_lat"))
    lon1 = _safe_float(left.get("gps_lon"))
    lat2 = _safe_float(right.get("gps_lat"))
    lon2 = _safe_float(right.get("gps_lon"))
    if None in (lat1, lon1, lat2, lon2):
        return 0.5
    return max(0.0, 1.0 - _haversine_m(lat1, lon1, lat2, lon2) / 50)


def _mean_float(rows: list[dict[str, str]], key: str) -> float:
    values = [_safe_float(row.get(key)) for row in rows]
    nums = [value for value in values if value is not None]
    return sum(nums) / len(nums) if nums else 0.0


def _mean_optional(rows: list[dict[str, str]], key: str) -> float | None:
    values = [_safe_float(row.get(key)) for row in rows]
    nums = [value for value in values if value is not None]
    return sum(nums) / len(nums) if nums else None


def _split_set(value: object) -> set[str]:
    if not value:
        return set()
    return {part.strip() for part in str(value).replace("|", ",").split(",") if part.strip()}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 0.0
    return len(left.intersection(right)) / len(left.union(right))


def _parse_time(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value))
    except ValueError:
        pass
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


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
