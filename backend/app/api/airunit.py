from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from app.modules.guidance.engine import get_engine


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/airunit", tags=["airunit"])

_pi_ws: Optional[WebSocket] = None
_pi_info: Optional[dict] = None
_frontend_clients: set[WebSocket] = set()
_broadcast_lock = asyncio.Lock()


async def _relay_to_frontends(msg: dict) -> None:
    async with _broadcast_lock:
        dead: list[WebSocket] = []
        payload = json.dumps(msg)
        for ws in list(_frontend_clients):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            _frontend_clients.discard(ws)


@router.websocket("/ws")
async def pi_ws(websocket: WebSocket) -> None:
    global _pi_ws, _pi_info
    await websocket.accept()
    _pi_ws = websocket
    logger.info("Pi connected")
    await _relay_to_frontends({"type": "pi_connected", "connected": True, "pi_info": _pi_info})

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue

            if msg.get("type") == "hello":
                _pi_info = {"ip": msg.get("ip"), "port": msg.get("port", 8001)}
                logger.info("Pi registered: %s", _pi_info)
                await _relay_to_frontends(
                    {"type": "pi_status", "connected": True, "pi_info": _pi_info}
                )

            msg_type = msg.get("type") or msg.get("msg_type")
            if msg_type in ("POSE", "EVIDENCE", "HEALTH"):
                get_engine().ingest(msg)

            await _relay_to_frontends(msg)
    except WebSocketDisconnect:
        logger.info("Pi disconnected")
    finally:
        _pi_ws = None
        _pi_info = None
        await _relay_to_frontends({"type": "pi_disconnected"})


@router.websocket("/frontend-ws")
async def frontend_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    _frontend_clients.add(websocket)
    await websocket.send_text(
        json.dumps(
            {
                "type": "pi_status",
                "connected": _pi_ws is not None,
                "pi_info": _pi_info,
            }
        )
    )
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue
            if msg.get("type") == "cmd" and _pi_ws is not None:
                try:
                    await _pi_ws.send_text(json.dumps(msg))
                except Exception as exc:
                    logger.warning("Failed to send command to Pi: %s", exc)
    except WebSocketDisconnect:
        pass
    finally:
        _frontend_clients.discard(websocket)


@router.get("/status")
def get_status() -> dict:
    return {
        "pi_connected": _pi_ws is not None,
        "pi_info": _pi_info,
    }


class CommandRequest(BaseModel):
    cmd: str


@router.post("/command")
async def send_command(body: CommandRequest) -> dict:
    if _pi_ws is None:
        raise HTTPException(status_code=503, detail="Pi not connected")
    try:
        await _pi_ws.send_text(json.dumps({"type": "cmd", "cmd": body.cmd}))
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/files")
async def list_files() -> dict:
    if _pi_info is None:
        return {"files": [], "error": "Pi not connected"}
    pi_url = f"http://{_pi_info['ip']}:{_pi_info['port']}/logs"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(pi_url)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        return {"files": [], "error": str(exc)}


@router.get("/files/{fname}")
async def download_file(fname: str) -> Response:
    if _pi_info is None:
        raise HTTPException(status_code=503, detail="Pi not connected")
    pi_url = f"http://{_pi_info['ip']}:{_pi_info['port']}/logs/{fname}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(pi_url)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="File not found on Pi")
    return StreamingResponse(
        iter([resp.content]),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
