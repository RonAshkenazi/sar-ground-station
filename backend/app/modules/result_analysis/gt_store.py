"""In-memory ground-truth point store, keyed by session_id."""

from __future__ import annotations

import uuid
from typing import Optional


_gt_store: dict[str, list[dict]] = {}


def get_gt_points(session_id: str) -> list[dict]:
    return list(_gt_store.get(session_id, []))


def add_gt_point(
    session_id: str,
    lat: float,
    lon: float,
    label: Optional[str] = None,
) -> dict:
    point = {"gt_id": str(uuid.uuid4()), "lat": lat, "lon": lon, "label": label}
    _gt_store.setdefault(session_id, []).append(point)
    return point


def delete_gt_point(session_id: str, gt_id: str) -> bool:
    points = _gt_store.get(session_id, [])
    before = len(points)
    _gt_store[session_id] = [point for point in points if point["gt_id"] != gt_id]
    return len(_gt_store.get(session_id, [])) < before


def clear_gt_points(session_id: str) -> None:
    _gt_store[session_id] = []


def import_gt_points(session_id: str, raw_points: list[dict]) -> list[dict]:
    added = []
    for point in raw_points:
        added.append(add_gt_point(session_id, float(point["lat"]), float(point["lon"]), point.get("label")))
    return added
