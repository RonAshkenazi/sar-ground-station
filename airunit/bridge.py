"""
Ground-station bridge for the Air Unit.

Runs on the Pi alongside the existing airunit-web.service (port 8080).

- Opens an outbound WebSocket to the ground-station backend
  (ws://GROUND_HOST:GROUND_PORT/api/airunit/ws) and sends a `hello`
  so the backend can advertise this Pi to frontend clients.

- Subscribes to the local airunit-web /ws (port 8080) and forwards
  every event upstream.

- Translates inbound `cmd` messages into REST calls against the local
  airunit-web (scan_start, scan_stop, ble_scan_start, ble_scan_stop).

- Reconnects with backoff if either side drops.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket

import httpx
import websockets

GROUND_HOST = os.environ.get("GROUND_HOST", "192.168.1.100")
GROUND_PORT = int(os.environ.get("GROUND_PORT", "8000"))
LOCAL_PORT = int(os.environ.get("AIRUNIT_LOCAL_PORT", "8080"))

UPSTREAM_URL = f"ws://{GROUND_HOST}:{GROUND_PORT}/api/airunit/ws"
LOCAL_WS_URL = f"ws://127.0.0.1:{LOCAL_PORT}/ws"
LOCAL_HTTP = f"http://127.0.0.1:{LOCAL_PORT}"

CMD_TO_PATH = {
    "scan_start": "/scan/start",
    "scan_stop": "/scan/stop",
    "ble_scan_start": "/ble/scan/start",
    "ble_scan_stop": "/ble/scan/stop",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("airunit-bridge")


def local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((GROUND_HOST, 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


async def run_local_to_upstream(upstream) -> None:
    """Subscribe to local /ws and forward each message upstream."""
    while True:
        try:
            async with websockets.connect(LOCAL_WS_URL, ping_interval=20) as local:
                log.info("Connected to local /ws")
                async for raw in local:
                    try:
                        await upstream.send(raw)
                    except Exception as exc:
                        log.warning("upstream send failed: %s", exc)
                        return
        except Exception as exc:
            log.warning("local /ws error: %s — retrying in 3s", exc)
            await asyncio.sleep(3)


async def handle_cmd(msg: dict) -> None:
    cmd = msg.get("cmd")
    path = CMD_TO_PATH.get(cmd)
    if not path:
        log.warning("unknown cmd: %s", cmd)
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(LOCAL_HTTP + path)
            log.info("cmd %s -> %s %s", cmd, resp.status_code, resp.text[:200])
    except Exception as exc:
        log.warning("cmd %s failed: %s", cmd, exc)


async def upstream_loop() -> None:
    """Maintain the outbound WebSocket. Reconnect with backoff."""
    backoff = 1
    while True:
        try:
            log.info("Connecting to %s ...", UPSTREAM_URL)
            async with websockets.connect(UPSTREAM_URL, ping_interval=20) as upstream:
                log.info("Upstream connected")
                backoff = 1
                hello = {"type": "hello", "ip": local_ip(), "port": LOCAL_PORT}
                await upstream.send(json.dumps(hello))

                forwarder = asyncio.create_task(run_local_to_upstream(upstream))
                try:
                    async for raw in upstream:
                        try:
                            msg = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        if msg.get("type") == "cmd":
                            asyncio.create_task(handle_cmd(msg))
                finally:
                    forwarder.cancel()
                    try:
                        await forwarder
                    except asyncio.CancelledError:
                        pass
        except Exception as exc:
            log.warning("upstream error: %s — retry in %ds", exc, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)


if __name__ == "__main__":
    asyncio.run(upstream_loop())
