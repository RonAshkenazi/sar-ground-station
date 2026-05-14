from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path
from typing import Any

from app.modules.enrichment.pcap_parser import parse_ble_pcap, parse_wifi_pcap


_ENR_01_MATCH_THRESHOLD: float = 0.3  # FD-03: keep as new-backend heuristic; not legacy-equivalent
_ENR_02_TIME_WINDOW_MS: float = 1000.0  # FD: legacy default; 500 was a stub
_ENR_03_TIME_SCORE_WEIGHT: float = 1.0  # TODO: TBD per spec Part B ENR-03 - extract from legacy app
_ENR_04_IDENTITY_SCORE_WEIGHT: float = 1.0  # TODO: TBD per spec Part B ENR-04 - extract from legacy app
_ENR_05_WIFI_CONTEXT_WEIGHT: float = 0.5  # TODO: TBD per spec Part B ENR-05 - extract from legacy app
_ENR_06_BLE_CONTEXT_WEIGHT: float = 0.5  # TODO: TBD per spec Part B ENR-06 - extract from legacy app

ENRICHMENT_COLUMNS = [
    "dst_mac_pcap",
    "bssid_pcap",
    "seq_ctl",
    "frame_len",
    "ie_ids",
    "ie_fingerprint",
    "ie_vendor_ouis",
    "ble_event_type",
    "ble_mfr_data",
    "ble_service_uuids",
    "ble_local_name",
    "ble_tx_power_dbm",
    "ble_flags",
    "match_found",
    "match_delta_ms",
    "match_score",
    "match_method",
]


def run_enrichment(
    csv_path: Path,
    pcap_path: Path,
    protocol: str,
    match_threshold: float = _ENR_01_MATCH_THRESHOLD,
    time_window_ms: float = _ENR_02_TIME_WINDOW_MS,
    time_score_weight: float = _ENR_03_TIME_SCORE_WEIGHT,
    identity_score_weight: float = _ENR_04_IDENTITY_SCORE_WEIGHT,
    context_weight: float = _ENR_05_WIFI_CONTEXT_WEIGHT,
) -> dict[str, Any]:
    if not csv_path.exists() or not csv_path.is_file():
        raise ValueError(f"CSV file not found: {csv_path}")
    if not pcap_path.exists() or not pcap_path.is_file():
        raise ValueError(f"PCAP file not found: {pcap_path}")
    if protocol not in ("wifi", "ble"):
        raise ValueError("protocol must be 'wifi' or 'ble'")
    if time_window_ms <= 0:
        raise ValueError("time_window_ms must be positive")

    frames = parse_wifi_pcap(pcap_path) if protocol == "wifi" else parse_ble_pcap(pcap_path)
    normalized_frames = [_normalize_frame(frame) for frame in frames]
    frame_index = _build_index(normalized_frames)

    with csv_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        original_fields = list(reader.fieldnames or [])

    enriched_rows = []
    matched_rows = 0
    warnings: list[str] = []
    for row in rows:
        best = _find_best_match(
            row=row,
            frame_index=frame_index,
            time_window_ms=time_window_ms,
            match_threshold=match_threshold,
            time_score_weight=time_score_weight,
            identity_score_weight=identity_score_weight,
            context_weight=context_weight,
            protocol=protocol,
        )
        enriched = dict(row)
        if best is None:
            _apply_no_match(enriched)
        else:
            matched_rows += 1
            _apply_match(enriched, best)
        enriched_rows.append(enriched)

    if protocol == "ble":
        warnings.append("BLE PCAP parsing is not implemented yet")
    if frames and matched_rows == 0:
        warnings.append("No CSV rows matched PCAP frames with current ENR thresholds")
    if not frames:
        warnings.append("No frames parsed from PCAP")

    output_path = csv_path.parent / f"{csv_path.stem}_ENRICHED.csv"
    fieldnames = original_fields + [column for column in ENRICHMENT_COLUMNS if column not in original_fields]
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched_rows)

    total_rows = len(rows)
    return {
        "enriched_csv_path": str(output_path.resolve()),
        "total_rows": total_rows,
        "matched_rows": matched_rows,
        "match_rate": round(matched_rows / total_rows, 4) if total_rows else 0.0,
        "warnings": warnings,
    }


def _normalize_frame(frame: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(frame)
    for key in ("src_mac", "dst_mac", "bssid"):
        normalized[key] = _normalize_mac(normalized.get(key))
    normalized["_timestamp_s"] = _parse_time(normalized.get("timestamp_utc"))
    return normalized


def _build_index(frames: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for frame in frames:
        if frame.get("_timestamp_s") is None:
            continue
        for key in ("src_mac", "dst_mac", "bssid"):
            mac = frame.get(key)
            if mac:
                index.setdefault(mac, []).append(frame)
    for bucket in index.values():
        bucket.sort(key=lambda item: item["_timestamp_s"])
    return index


def _find_best_match(
    row: dict[str, str],
    frame_index: dict[str, list[dict[str, Any]]],
    time_window_ms: float,
    match_threshold: float,
    time_score_weight: float,
    identity_score_weight: float,
    context_weight: float,
    protocol: str,
) -> dict[str, Any] | None:
    row_time = _parse_time(row.get("timestamp_utc"))
    if row_time is None:
        return None
    row_macs = [_normalize_mac(row.get(key)) for key in ("src_mac", "dst_mac", "bssid")]
    lookup_macs = [mac for mac in row_macs if mac]
    candidates: dict[int, dict[str, Any]] = {}
    for mac in lookup_macs:
        for frame in frame_index.get(mac, []):
            delta_ms = abs(frame["_timestamp_s"] - row_time) * 1000
            if delta_ms <= time_window_ms:
                candidates[id(frame)] = frame

    best: dict[str, Any] | None = None
    for frame in candidates.values():
        scored = _score_candidate(
            row_macs=row_macs,
            row_time=row_time,
            frame=frame,
            time_window_ms=time_window_ms,
            time_score_weight=time_score_weight,
            identity_score_weight=identity_score_weight,
            context_weight=context_weight,
            protocol=protocol,
        )
        if scored["match_score"] >= match_threshold and (
            best is None or scored["match_score"] > best["match_score"]
        ):
            best = scored
    return best


def _score_candidate(
    row_macs: list[str | None],
    row_time: float,
    frame: dict[str, Any],
    time_window_ms: float,
    time_score_weight: float,
    identity_score_weight: float,
    context_weight: float,
    protocol: str,
) -> dict[str, Any]:
    delta_ms = abs(frame["_timestamp_s"] - row_time) * 1000
    time_score = max(0.0, 1.0 - (delta_ms / time_window_ms))
    frame_macs = [frame.get("src_mac"), frame.get("dst_mac"), frame.get("bssid")]
    identity_score = 1.0 if row_macs[0] and row_macs[0] in frame_macs else 0.0
    context_score = 0.0
    if protocol == "wifi":
        context_matches = sum(1 for mac in row_macs[1:] if mac and mac in frame_macs)
        context_score = min(1.0, context_matches / 2)
    score = (
        time_score * time_score_weight
        + identity_score * identity_score_weight
        + context_score * context_weight
    )
    scored = dict(frame)
    scored["match_delta_ms"] = round(delta_ms, 3)
    scored["match_score"] = round(score, 4)
    scored["match_method"] = "time_identity_best_match" if identity_score else "time_only_match"
    return scored


def _apply_match(row: dict[str, Any], frame: dict[str, Any]) -> None:
    row.update(
        {
            "dst_mac_pcap": frame.get("dst_mac"),
            "bssid_pcap": frame.get("bssid"),
            "seq_ctl": frame.get("seq_ctl"),
            "frame_len": frame.get("frame_len"),
            "ie_ids": frame.get("ie_ids"),
            "ie_fingerprint": frame.get("ie_fingerprint"),
            "ie_vendor_ouis": frame.get("ie_vendor_ouis"),
            "ble_event_type": frame.get("ble_event_type"),
            "ble_mfr_data": frame.get("ble_mfr_data"),
            "ble_service_uuids": frame.get("ble_service_uuids"),
            "ble_local_name": frame.get("ble_local_name"),
            "ble_tx_power_dbm": frame.get("ble_tx_power_dbm"),
            "ble_flags": frame.get("ble_flags"),
            "match_found": True,
            "match_delta_ms": frame.get("match_delta_ms"),
            "match_score": frame.get("match_score"),
            "match_method": frame.get("match_method"),
        }
    )


def _apply_no_match(row: dict[str, Any]) -> None:
    for column in ENRICHMENT_COLUMNS:
        row[column] = None
    row["match_found"] = False
    row["match_method"] = "no_match"


def _normalize_mac(value: object) -> str | None:
    if not value:
        return None
    raw = str(value).strip().lower().replace("-", ":")
    compact = raw.replace(":", "")
    if len(compact) == 12 and all(char in "0123456789abcdef" for char in compact):
        return ":".join(compact[index : index + 2] for index in range(0, 12, 2))
    return raw if raw else None


def _parse_time(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    try:
        return float(text)
    except ValueError:
        pass
    try:
        return dt.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None
