from __future__ import annotations

import csv
import datetime as dt
import math
from pathlib import Path
from typing import Any


# --- Re-ID association ---
_REID_01_ASSOCIATION_THRESHOLD: float = 0.80  # FD-01: legacy value; Bleach match_threshold
_REID_02_CONFLICT_RESOLUTION = "greedy_best_valid_match"
_REID_MIN_ROWS_SINGLETON: int = 5  # singletons with fewer rows than this go to noise

# --- Bleach scoring weights (raw sum, not normalized) ---
_REID_WIFI_IE_FINGERPRINT_WEIGHT: float = 0.75
_REID_WIFI_FRAME_LEN_WEIGHT: float = 0.20
_REID_WIFI_SSID_BONUS_WEIGHT: float = 0.10
_REID_WIFI_SEQ_BONUS_WEIGHT: float = 0.05

# --- Bleach thresholds ---
_REID_WIFI_IE_SIMILARITY_THRESHOLD: float = 0.90
_REID_WIFI_STRICT_THRESHOLD: float = 0.75

# --- Temporal / sequence parameters ---
_REID_WIFI_TIME_GAP_MAX_SEC: float = 30.0  # FD: tunable 3-30; default 30 for SAR field scans
_REID_WIFI_SEQ_GAP_MAX: int = 64  # FD-02: Bleach paper delta_th approx 64; legacy source ambiguous
_REID_WIFI_SEQ_MODULUS: int = 4096
_REID_WIFI_RSSI_SANITY_MAX_DIFF_DB: float = 30.0
_REID_WIFI_SANITY_TIME_WINDOW_SEC: float = 5.0
_REID_WIFI_BURST_WINDOW_SEC: float = 60.0  # from IMPLEMENTATION_SUMMARY; source gap noted

# --- Feature tags ---
_REID_IE_TAGS: frozenset[int] = frozenset({1, 50, 45, 127, 221})

REQUIRED_COLUMNS = {"timestamp_utc", "src_mac", "rssi_dbm", "gps_lat", "gps_lon"}


def run_reid(
    enriched_csv_path: Path,
    protocol: str,
    *,
    association_threshold: float = _REID_01_ASSOCIATION_THRESHOLD,
    seq_gap_max: int = _REID_WIFI_SEQ_GAP_MAX,
    time_gap_max_sec: float = _REID_WIFI_TIME_GAP_MAX_SEC,
    burst_window_sec: float = _REID_WIFI_BURST_WINDOW_SEC,
    probe_requests_only: bool = False,
) -> dict[str, Any]:
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

    if probe_requests_only:
        rows = [row for row in rows if str(row.get("frame_type", "")).lower() in {"probe-req", "probe_req"}]
        if not rows:
            raise ValueError("No probe-request rows found after probe_requests_only filter")

    warnings: list[str] = []
    static_macs = {row["src_mac"] for row in rows if not _is_randomized_mac(str(row.get("src_mac", "")))}
    assigned: dict[int, tuple[str, str]] = {}
    confidence_by_row: dict[int, str] = {}
    for index, row in enumerate(rows):
        mac = row.get("src_mac", "")
        if mac in static_macs:
            assigned[index] = (mac, "static")
            confidence_by_row[index] = "static"

    dynamic_units = _build_dynamic_units(rows, assigned)
    _group_bursts(dynamic_units, burst_window_sec)
    accepted: list[tuple[str, str, float]] = []
    if protocol == "ble":
        warnings.append("BLE Re-ID feature computation is not implemented; dynamic MACs remain singleton clusters")
    else:
        candidates = _generate_candidates(dynamic_units, time_gap_max_sec)
        associations = [
            (src, dst, score)
            for src, dst, score in (
                (src, dst, _association_score(dynamic_units[src], dynamic_units[dst], seq_gap_max))
                for src, dst in candidates
            )
            if score >= association_threshold
        ]
        accepted = _resolve_conflicts(associations)

    cluster_by_unit = _cluster_units(dynamic_units, accepted)
    cluster_size: dict[int, int] = {}
    for cluster_id in cluster_by_unit.values():
        cluster_size[cluster_id] = cluster_size.get(cluster_id, 0) + 1
    cluster_row_count: dict[int, int] = {}
    for unit_id, cluster_id in cluster_by_unit.items():
        cluster_row_count[cluster_id] = cluster_row_count.get(cluster_id, 0) + len(dynamic_units[unit_id]["indices"])
    singleton_cluster_ids = {
        cluster_id
        for cluster_id, size in cluster_size.items()
        if size == 1 and cluster_row_count.get(cluster_id, 0) < _REID_MIN_ROWS_SINGLETON
    }
    confidence_by_cluster = _cluster_confidence(cluster_by_unit, accepted)
    for unit_id, cluster_id in cluster_by_unit.items():
        for row_index in dynamic_units[unit_id]["indices"]:
            if cluster_id in singleton_cluster_ids:
                assigned[row_index] = ("noise", "noise")
            else:
                assigned[row_index] = (str(cluster_id), "dynamic")
            confidence_by_row[row_index] = confidence_by_cluster.get(cluster_id, "low")

    output_rows = []
    for index, row in enumerate(rows):
        cluster_id, cluster_type = assigned[index]
        output = dict(row)
        output["cluster_id"] = cluster_id
        output["cluster_type"] = cluster_type
        output["confidence"] = confidence_by_row.get(index, "low")
        output_rows.append(output)

    stem = enriched_csv_path.stem
    if stem.lower().endswith("_enriched"):
        stem = stem[: -len("_enriched")]
    output_path = enriched_csv_path.parent / f"{stem}_REID.csv"
    output_fields = fieldnames + [name for name in ("cluster_id", "cluster_type", "confidence") if name not in fieldnames]
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=output_fields)
        writer.writeheader()
        writer.writerows(output_rows)

    dynamic_cluster_sizes = {
        str(cluster_id): size for cluster_id, size in cluster_size.items() if cluster_id not in singleton_cluster_ids
    }
    unique_dynamic_macs = {
        dynamic_units[unit_id]["mac"]
        for unit_id, cluster_id in cluster_by_unit.items()
        if cluster_id not in singleton_cluster_ids
    }
    noise_count = len(singleton_cluster_ids)

    return {
        "reid_csv_path": str(output_path.resolve()),
        "total_rows": len(rows),
        "static_cluster_count": len(static_macs),
        "dynamic_cluster_count": len(dynamic_cluster_sizes),
        "unique_dynamic_mac_count": len(unique_dynamic_macs),
        "noise_cluster_count": noise_count,
        "cluster_confidence": {
            str(cluster_id): tier
            for cluster_id, tier in confidence_by_cluster.items()
            if cluster_id not in singleton_cluster_ids
        },
        "warnings": warnings,
    }


def _is_randomized_mac(mac: str) -> bool:
    if not mac:
        return False
    first = mac.split(":")[0]
    try:
        return int(first, 16) & 0x02 != 0
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
            "bursts": [],
        }
    return units


def _group_bursts(units: dict[str, dict[str, Any]], burst_window_sec: float = _REID_WIFI_BURST_WINDOW_SEC) -> None:
    for unit in units.values():
        rows = unit["rows"]
        if len(rows) <= 3:
            continue
        bursts: list[dict[str, Any]] = []
        current: list[dict[str, str]] = []
        start_time: float | None = None
        for row in rows:
            row_time = _parse_time(row.get("timestamp_utc"))
            if row_time is None:
                continue
            if start_time is None or row_time - start_time <= burst_window_sec:
                current.append(row)
                if start_time is None:
                    start_time = row_time
            else:
                bursts.append(_burst_signature(current))
                current = [row]
                start_time = row_time
        if current:
            bursts.append(_burst_signature(current))
        unit["bursts"] = bursts
        if bursts:
            unit["score_rows"] = bursts[-1]["rows"]


def _burst_signature(rows: list[dict[str, str]]) -> dict[str, Any]:
    times = [_parse_time(row.get("timestamp_utc")) for row in rows]
    valid_times = [time for time in times if time is not None]
    rssi_values = [_safe_float(row.get("rssi_dbm")) for row in rows]
    rssis = [value for value in rssi_values if value is not None]
    seq_values = [_safe_float(row.get("seq_ctl")) for row in rows]
    seqs = [int(value) for value in seq_values if value is not None]
    rssi_mean = sum(rssis) / len(rssis) if rssis else None
    rssi_std = math.sqrt(sum((value - rssi_mean) ** 2 for value in rssis) / len(rssis)) if rssis and rssi_mean is not None else None
    seq_delta = (seqs[-1] - seqs[0]) % _REID_WIFI_SEQ_MODULUS if len(seqs) >= 2 else 0
    return {
        "rows": rows,
        "duration_sec": max(valid_times) - min(valid_times) if valid_times else 0.0,
        "rssi_mean": rssi_mean,
        "rssi_std": rssi_std,
        "seq_delta": seq_delta,
        "packet_count": len(rows),
    }


def _generate_candidates(
    units: dict[str, dict[str, Any]],
    time_gap_max_sec: float = _REID_WIFI_TIME_GAP_MAX_SEC,
) -> list[tuple[str, str]]:
    candidates = []
    for left_id, left in units.items():
        for right_id, right in units.items():
            if left_id == right_id:
                continue
            if left["last_time"] is None or right["first_time"] is None:
                continue
            if left["last_time"] > right["first_time"]:
                continue
            gap_sec = right["first_time"] - left["last_time"]
            if gap_sec <= time_gap_max_sec:
                candidates.append((left_id, right_id))
    return candidates


def _association_score(
    left: dict[str, Any],
    right: dict[str, Any],
    seq_gap_max: int = _REID_WIFI_SEQ_GAP_MAX,
) -> float:
    left_rows = left.get("score_rows") or left["rows"]
    right_rows = right.get("score_rows") or right["rows"]
    a = left_rows[-1]
    b = right_rows[0]

    dt_sec = ((_parse_time(b.get("timestamp_utc")) or 0) - (_parse_time(a.get("timestamp_utc")) or 0))
    if 0 <= dt_sec < _REID_WIFI_SANITY_TIME_WINDOW_SEC:
        rssi_a = _safe_float(a.get("rssi_dbm"))
        rssi_b = _safe_float(b.get("rssi_dbm"))
        if rssi_a is not None and rssi_b is not None:
            if abs(rssi_a - rssi_b) > _REID_WIFI_RSSI_SANITY_MAX_DIFF_DB:
                return 0.0

    return (
        _ie_fingerprint_score(a.get("ie_fingerprint"), b.get("ie_fingerprint"))
        * _REID_WIFI_IE_FINGERPRINT_WEIGHT
        + _frame_length_score(left_rows, right_rows)
        * _REID_WIFI_FRAME_LEN_WEIGHT
        + _ssid_bonus(a.get("ie_fingerprint"), b.get("ie_fingerprint"))
        * _REID_WIFI_SSID_BONUS_WEIGHT
        + _seq_continuity_bonus(a.get("seq_ctl"), b.get("seq_ctl"), seq_gap_max)
        * _REID_WIFI_SEQ_BONUS_WEIGHT
    )


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


def _cluster_confidence(cluster_by_unit: dict[str, int], accepted: list[tuple[str, str, float]]) -> dict[int, str]:
    max_scores: dict[int, float] = {}
    for src, dst, score in accepted:
        cluster_id = cluster_by_unit.get(src) or cluster_by_unit.get(dst)
        if cluster_id is not None:
            max_scores[cluster_id] = max(score, max_scores.get(cluster_id, 0.0))
    return {cluster_id: _confidence_tier(max_scores.get(cluster_id, 0.0)) for cluster_id in set(cluster_by_unit.values())}


def _confidence_tier(score: float) -> str:
    if score >= _REID_WIFI_STRICT_THRESHOLD:
        return "high"
    if score >= 0.60:
        return "medium"
    return "low"


def _seq_continuity_bonus(
    left: object,
    right: object,
    seq_gap_max: int = _REID_WIFI_SEQ_GAP_MAX,
) -> float:
    left_value = _safe_float(left)
    right_value = _safe_float(right)
    if left_value is None or right_value is None:
        return 0.0
    delta = (int(right_value) - int(left_value)) % _REID_WIFI_SEQ_MODULUS
    return 1.0 if 0 < delta <= seq_gap_max else 0.0


def _ie_fingerprint_score(left: object, right: object) -> float:
    if not left or not right:
        return 0.0
    left_map = _parse_ie_fingerprint(str(left))
    right_map = _parse_ie_fingerprint(str(right))
    if not left_map or not right_map:
        return 0.0
    qualifying = 0
    for tag in _REID_IE_TAGS:
        hex_a = left_map.get(tag)
        hex_b = right_map.get(tag)
        if hex_a is None or hex_b is None:
            continue
        if _hex_similarity(hex_a, hex_b) >= _REID_WIFI_IE_SIMILARITY_THRESHOLD:
            qualifying += 1
    return qualifying / len(_REID_IE_TAGS)


def _parse_ie_fingerprint(fp: str) -> dict[int, str]:
    result: dict[int, str] = {}
    for part in fp.split(";"):
        part = part.strip()
        if ":" not in part:
            continue
        tag_str, hex_str = part.split(":", 1)
        try:
            result[int(tag_str)] = hex_str.lower()
        except ValueError:
            pass
    return result


def _hex_similarity(a: str, b: str) -> float:
    try:
        bytes_a = bytes.fromhex(a) if len(a) % 2 == 0 else b""
        bytes_b = bytes.fromhex(b) if len(b) % 2 == 0 else b""
    except ValueError:
        return 0.0
    if not bytes_a or not bytes_b:
        return 0.0
    length = max(len(bytes_a), len(bytes_b))
    matching = sum(x == y for x, y in zip(bytes_a, bytes_b))
    return matching / length


def _ssid_bonus(left: object, right: object) -> float:
    if not left or not right:
        return 0.0
    left_map = _parse_ie_fingerprint(str(left))
    right_map = _parse_ie_fingerprint(str(right))
    ssid_a = left_map.get(0)
    ssid_b = right_map.get(0)
    if ssid_a is None or ssid_b is None:
        return 0.0
    return 1.0 if ssid_a == ssid_b else 0.0


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
