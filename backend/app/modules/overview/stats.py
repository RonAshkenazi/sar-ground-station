from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any


def compute_overview_stats(csv_path: Path) -> dict[str, Any]:
    """Read a scan CSV and compute Overview page statistics."""
    with csv_path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        return _empty_result(csv_path.name, warning="CSV file is empty")

    record_count = len(rows)
    gps_points = []
    rssi_values = []
    mac_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"packet_count": 0, "rssi_values": []}
    )

    for row in rows:
        src_mac = row.get("src_mac", "")
        rssi = _safe_float(row.get("rssi_dbm"))
        lat = _safe_float(row.get("gps_lat"))
        lon = _safe_float(row.get("gps_lon"))

        if rssi is not None:
            rssi_values.append(rssi)

        mac_stats[src_mac]["packet_count"] += 1
        if rssi is not None:
            mac_stats[src_mac]["rssi_values"].append(rssi)

        if lat is not None and lon is not None:
            gps_points.append(
                {
                    "lat": lat,
                    "lon": lon,
                    "rssi": rssi,
                    "src_mac": src_mac,
                    "timestamp_utc": row.get("timestamp_utc", ""),
                    "frame_type": row.get("frame_type") or "",
                }
            )

    gps_fix_pct = round(len(gps_points) / record_count * 100, 1)
    device_table = []
    for mac, stats in sorted(
        mac_stats.items(),
        key=lambda item: (-item[1]["packet_count"], item[0]),
    ):
        values = stats["rssi_values"]
        device_table.append(
            {
                "src_mac": mac,
                "packet_count": stats["packet_count"],
                "rssi_min": round(min(values), 1) if values else None,
                "rssi_max": round(max(values), 1) if values else None,
                "rssi_mean": round(sum(values) / len(values), 1) if values else None,
            }
        )

    warning = None
    if gps_fix_pct < 50:
        warning = f"Low GPS fix rate: {gps_fix_pct}% of records have valid coordinates"

    return {
        "csv_filename": csv_path.name,
        "record_count": record_count,
        "unique_macs": len(mac_stats),
        "gps_fix_pct": gps_fix_pct,
        "rssi_min": round(min(rssi_values), 1) if rssi_values else None,
        "rssi_max": round(max(rssi_values), 1) if rssi_values else None,
        "rssi_mean": round(sum(rssi_values) / len(rssi_values), 1)
        if rssi_values
        else None,
        "gps_points": gps_points,
        "device_table": device_table,
        "warning": warning,
    }


def _safe_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _empty_result(filename: str, warning: str) -> dict[str, Any]:
    return {
        "csv_filename": filename,
        "record_count": 0,
        "unique_macs": 0,
        "gps_fix_pct": 0.0,
        "rssi_min": None,
        "rssi_max": None,
        "rssi_mean": None,
        "gps_points": [],
        "device_table": [],
        "warning": warning,
    }
