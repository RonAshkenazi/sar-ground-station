from __future__ import annotations

import math

from .models import GridCell, GuidanceGrid


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres."""
    radius_m = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * radius_m * math.asin(math.sqrt(a))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing from point 1 to point 2, in degrees [0, 360)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_lambda = math.radians(lon2 - lon1)
    x = math.sin(d_lambda) * math.cos(phi2)
    y = (
        math.cos(phi1) * math.sin(phi2)
        - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
    )
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def create_grid(bounds: dict, cell_size_m: float) -> GuidanceGrid:
    min_lat = bounds["min_lat"]
    max_lat = bounds["max_lat"]
    min_lon = bounds["min_lon"]
    max_lon = bounds["max_lon"]

    height_m = haversine_m(min_lat, min_lon, max_lat, min_lon)
    width_m = haversine_m(min_lat, min_lon, min_lat, max_lon)

    n_rows = max(1, math.ceil(height_m / cell_size_m))
    n_cols = max(1, math.ceil(width_m / cell_size_m))

    lat_step = (max_lat - min_lat) / n_rows
    lon_step = (max_lon - min_lon) / n_cols

    cells: dict[int, GridCell] = {}
    for row in range(n_rows):
        for col in range(n_cols):
            cell_id = row * n_cols + col
            cells[cell_id] = GridCell(
                cell_id=cell_id,
                center_lat=min_lat + (row + 0.5) * lat_step,
                center_lon=min_lon + (col + 0.5) * lon_step,
                row=row,
                col=col,
            )

    return GuidanceGrid(
        bounds=bounds,
        cell_size_m=cell_size_m,
        n_rows=n_rows,
        n_cols=n_cols,
        cells=cells,
    )


def latlon_to_cell_id(lat: float, lon: float, grid: GuidanceGrid) -> int | None:
    b = grid.bounds
    if not (b["min_lat"] <= lat <= b["max_lat"] and b["min_lon"] <= lon <= b["max_lon"]):
        return None

    lat_step = (b["max_lat"] - b["min_lat"]) / grid.n_rows
    lon_step = (b["max_lon"] - b["min_lon"]) / grid.n_cols
    row = min(int((lat - b["min_lat"]) / lat_step), grid.n_rows - 1)
    col = min(int((lon - b["min_lon"]) / lon_step), grid.n_cols - 1)
    return row * grid.n_cols + col


def get_neighbors(cell_id: int, grid: GuidanceGrid) -> list[int]:
    n_rows = grid.n_rows
    n_cols = grid.n_cols
    row, col = divmod(cell_id, n_cols)
    neighbors = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            r2 = row + dr
            c2 = col + dc
            if 0 <= r2 < n_rows and 0 <= c2 < n_cols:
                neighbors.append(r2 * n_cols + c2)
    return neighbors
