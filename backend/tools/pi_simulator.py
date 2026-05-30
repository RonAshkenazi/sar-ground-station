#!/usr/bin/env python3
"""
Pi Flight Simulator
Connects to the Ground Station WebSocket as if it were the Raspberry Pi.
Tests the Smart Flight Guidance algorithm without real hardware.

Usage:
    python backend/tools/pi_simulator.py \\
        --target-lat 31.2498 --target-lon 34.8061 \\
        --bounds "31.248,31.252,34.804,34.808" \\
        --mode both
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
import sys
from typing import Optional

try:
    import httpx
    import websockets
except ImportError:
    print("Missing dependencies. Run: pip install websockets httpx")
    sys.exit(1)

# Geometry helpers (no app imports; standalone script)

_R = 6_371_000.0


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * _R * math.asin(math.sqrt(a))


def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _move(lat: float, lon: float, bearing_deg: float, dist_m: float) -> tuple[float, float]:
    ang = dist_m / _R
    br = math.radians(bearing_deg)
    la1 = math.radians(lat)
    lo1 = math.radians(lon)
    la2 = math.asin(
        math.sin(la1) * math.cos(ang) + math.cos(la1) * math.sin(ang) * math.cos(br)
    )
    lo2 = lo1 + math.atan2(
        math.sin(br) * math.sin(ang) * math.cos(la1),
        math.cos(ang) - math.sin(la1) * math.sin(la2),
    )
    return math.degrees(la2), math.degrees(lo2)


# RF model

def _sim_rssi(
    dlat: float,
    dlon: float,
    tlat: float,
    tlon: float,
    alt_m: float,
    rssi_at_1m: float,
    n: float,
    noise_std: float,
) -> float:
    horiz = _haversine(dlat, dlon, tlat, tlon)
    dist = max(1.0, math.sqrt(horiz ** 2 + alt_m ** 2))
    mean = rssi_at_1m - 10 * n * math.log10(dist)
    return max(-100.0, min(-30.0, mean + random.gauss(0, noise_std)))


# Evidence window accumulator

class _Window:
    def __init__(self) -> None:
        self.obs: list[float] = []
        self.dwell_ms: float = 0.0

    def add(self, rssi: float, delta_ms: float) -> None:
        self.obs.append(rssi)
        self.dwell_ms += delta_ms

    def packet(self, lat: float, lon: float, strong_thr: float) -> Optional[dict]:
        if not self.obs:
            return None
        n = len(self.obs)
        n_strong = sum(1 for r in self.obs if r >= strong_thr)
        sorted_obs = sorted(self.obs)
        p95_idx = max(0, int(0.95 * n) - 1)
        return {
            "type": "EVIDENCE",
            "lat": lat,
            "lon": lon,
            "dwell_ms": self.dwell_ms,
            "win_ms": self.dwell_ms,
            "frames_total": n,
            "frames_strong": n_strong,
            "rssi_max_dbm": max(self.obs),
            "rssi_p95_dbm": sorted_obs[p95_idx],
            "rssi_mean_dbm": sum(self.obs) / n,
        }


# Messaging helpers

_sent = 0


async def _send(ws: websockets.WebSocketClientProtocol, msg: dict) -> None:
    global _sent
    _sent += 1
    await ws.send(json.dumps(msg))
    t = msg.get("type", "?")
    if t == "POSE":
        if _sent % 10 == 0:
            print(f"[sim] POSE  lat={msg['lat']:.5f} lon={msg['lon']:.5f}")
    elif t == "EVIDENCE":
        print(
            f"[sim] EVID  lat={msg['lat']:.5f} lon={msg['lon']:.5f} "
            f"rssi_max={msg['rssi_max_dbm']:.1f}dBm "
            f"frames={msg['frames_total']} strong={msg['frames_strong']}"
        )


# Lawnmower mode

async def run_lawnmower(
    ws: websockets.WebSocketClientProtocol,
    lat: float,
    lon: float,
    args: argparse.Namespace,
) -> tuple[float, float]:
    min_lat, max_lat, min_lon, max_lon = args.bounds

    lat_span = _haversine(min_lat, min_lon, max_lat, min_lon)
    lon_span = _haversine(min_lat, min_lon, min_lat, max_lon)
    n_rows = max(1, math.ceil(lat_span / args.cell_size))
    n_cols = max(1, math.ceil(lon_span / args.cell_size))
    lat_step = (max_lat - min_lat) / n_rows
    lon_step = (max_lon - min_lon) / n_cols

    tick_s = 0.25
    window = _Window()
    ev_elapsed = 0.0

    print(f"[sim] Lawnmower: {n_rows}x{n_cols} grid, {n_rows * n_cols} waypoints")

    for row in range(n_rows):
        row_lat = min_lat + (row + 0.5) * lat_step
        cols = range(n_cols) if row % 2 == 0 else range(n_cols - 1, -1, -1)
        for col in cols:
            wp_lon = min_lon + (col + 0.5) * lon_step
            while _haversine(lat, lon, row_lat, wp_lon) > args.cell_size * 0.4:
                dist = _haversine(lat, lon, row_lat, wp_lon)
                bear = _bearing(lat, lon, row_lat, wp_lon)
                step = min(args.speed_mps * tick_s, dist)
                lat, lon = _move(lat, lon, bear, step)

                rssi = _sim_rssi(
                    lat,
                    lon,
                    args.target_lat,
                    args.target_lon,
                    args.altitude_m,
                    args.rssi_at_1m,
                    args.path_loss_n,
                    args.noise_std,
                )
                window.add(rssi, tick_s * 1000)
                ev_elapsed += tick_s

                await _send(
                    ws,
                    {
                        "type": "POSE",
                        "lat": lat,
                        "lon": lon,
                        "gps_valid": True,
                        "sniffer_alive": True,
                        "speed_mps": args.speed_mps,
                    },
                )

                if ev_elapsed >= 2.0:
                    pkt = window.packet(lat, lon, args.strong_threshold_dbm)
                    if pkt:
                        await _send(ws, pkt)
                    window = _Window()
                    ev_elapsed = 0.0

                await asyncio.sleep(tick_s)

    pkt = window.packet(lat, lon, args.strong_threshold_dbm)
    if pkt:
        await _send(ws, pkt)

    print("[sim] Lawnmower complete.")
    return lat, lon


# Adaptive mode

async def run_adaptive(
    ws: websockets.WebSocketClientProtocol,
    lat: float,
    lon: float,
    args: argparse.Namespace,
) -> tuple[float, float]:
    tick_s = 0.25
    rec_interval_s = 3.0
    total_ticks = int(args.adaptive_duration_s / tick_s)
    window = _Window()
    ev_elapsed = 0.0
    rec_elapsed = 0.0
    target_lat = lat
    target_lon = lon

    print(f"[sim] Adaptive mode for {args.adaptive_duration_s:.0f}s. Following recommendations.")

    async def _poll_rec() -> None:
        nonlocal target_lat, target_lon
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(f"{args.api_url}/api/guidance/recommendation")
                data = r.json()
                if data.get("available"):
                    target_lat = data["target_lat"]
                    target_lon = data["target_lon"]
                    print(
                        f"[sim] REC   Cell {data['target_cell_id']}  "
                        f"bear={data['bearing_deg']:.0f} deg  "
                        f"dist={data['distance_m']:.0f}m  "
                        f"mode={data['mode']}  - {data['reason']}"
                    )
                else:
                    print("[sim] REC   (not available yet)")
        except Exception as exc:
            print(f"[sim] rec poll error: {exc}")

    for _ in range(total_ticks):
        if rec_elapsed >= rec_interval_s:
            await _poll_rec()
            rec_elapsed = 0.0

        dist = _haversine(lat, lon, target_lat, target_lon)
        if dist > 1.0:
            bear = _bearing(lat, lon, target_lat, target_lon)
            step = min(args.speed_mps * tick_s, dist)
            lat, lon = _move(lat, lon, bear, step)

        rssi = _sim_rssi(
            lat,
            lon,
            args.target_lat,
            args.target_lon,
            args.altitude_m,
            args.rssi_at_1m,
            args.path_loss_n,
            args.noise_std,
        )
        window.add(rssi, tick_s * 1000)
        ev_elapsed += tick_s
        rec_elapsed += tick_s

        await _send(
            ws,
            {
                "type": "POSE",
                "lat": lat,
                "lon": lon,
                "gps_valid": True,
                "sniffer_alive": True,
                "speed_mps": args.speed_mps,
            },
        )

        if ev_elapsed >= 2.0:
            pkt = window.packet(lat, lon, args.strong_threshold_dbm)
            if pkt:
                await _send(ws, pkt)
            window = _Window()
            ev_elapsed = 0.0

        await asyncio.sleep(tick_s)

    pkt = window.packet(lat, lon, args.strong_threshold_dbm)
    if pkt:
        await _send(ws, pkt)

    print("[sim] Adaptive mode complete.")
    return lat, lon


# Entry point

async def _run(args: argparse.Namespace) -> None:
    print(f"[sim] Connecting to {args.gs_url} ...")

    async with websockets.connect(args.gs_url) as ws:
        print("[sim] Connected.")
        await _send(ws, {"type": "hello", "ip": "127.0.0.1", "port": 8001})
        await asyncio.sleep(0.5)

        min_lat, max_lat, min_lon, max_lon = args.bounds
        lat = (min_lat + max_lat) / 2
        lon = (min_lon + max_lon) / 2

        if args.mode in ("lawnmower", "both"):
            lat, lon = await run_lawnmower(ws, lat, lon, args)

        if args.mode in ("adaptive", "both"):
            if args.mode == "both":
                await asyncio.sleep(2.0)
            lat, lon = await run_adaptive(ws, lat, lon, args)

    print(f"[sim] Done. Total packets sent: {_sent}")


def _parse_bounds(s: str) -> tuple[float, float, float, float]:
    parts = [float(x.strip()) for x in s.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("Expected 'min_lat,max_lat,min_lon,max_lon'")
    return (parts[0], parts[1], parts[2], parts[3])


def main() -> None:
    p = argparse.ArgumentParser(
        description="Pi Flight Simulator - tests Smart Flight Guidance without hardware"
    )
    p.add_argument("--gs-url", default="ws://localhost:8000/api/airunit/ws")
    p.add_argument("--api-url", default="http://localhost:8000")
    p.add_argument("--target-lat", type=float, required=True)
    p.add_argument("--target-lon", type=float, required=True)
    p.add_argument(
        "--bounds",
        type=_parse_bounds,
        required=True,
        metavar="min_lat,max_lat,min_lon,max_lon",
    )
    p.add_argument("--mode", choices=["lawnmower", "adaptive", "both"], default="both")
    p.add_argument("--cell-size", type=float, default=5.0, dest="cell_size")
    p.add_argument("--speed-mps", type=float, default=5.0)
    p.add_argument("--altitude-m", type=float, default=30.0)
    p.add_argument("--rssi-at-1m", type=float, default=-50.0)
    p.add_argument("--path-loss-n", type=float, default=2.8)
    p.add_argument("--noise-std", type=float, default=4.0)
    p.add_argument(
        "--strong-threshold-dbm",
        type=float,
        default=-65.0,
        dest="strong_threshold_dbm",
    )
    p.add_argument(
        "--adaptive-duration-s",
        type=float,
        default=300.0,
        dest="adaptive_duration_s",
    )
    args = p.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
