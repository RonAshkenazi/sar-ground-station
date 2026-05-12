from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter()


class CreateSessionRequest(BaseModel):
    folder_id: str
    mode: Optional[str] = None


class UpdateModeRequest(BaseModel):
    mode: Literal["wifi", "ble"]


@router.get("/scan-folders")
def list_scan_folders_endpoint() -> dict:
    from app.modules.dataset_discovery.discovery import list_scan_folders
    from app.storage.data_paths import get_data_dir

    data_dir = get_data_dir()
    folders = list_scan_folders(data_dir)
    if not folders:
        return {
            "folders": [],
            "warning": f"No scan folders found in {data_dir}",
        }
    return {"folders": folders}


@router.post("/sessions")
def create_session(body: CreateSessionRequest) -> dict:
    from app.modules.session_navigation.session_store import create_session as _create

    session = _create(folder_id=body.folder_id, mode=body.mode)
    return {
        "session_id": session["session_id"],
        "folder_id": session["folder_id"],
        "mode": session["mode"],
        "created_at": session["created_at"],
    }


@router.patch("/sessions/{session_id}/mode")
def update_session_mode(session_id: str, body: UpdateModeRequest) -> dict:
    from app.modules.session_navigation.session_store import get_session, update_mode

    if get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    session = update_mode(session_id, body.mode)
    return {"session_id": session_id, "mode": session["mode"]}


@router.get("/sessions/{session_id}/state")
def get_session_state(session_id: str) -> dict:
    from app.modules.session_navigation.session_store import get_session

    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
