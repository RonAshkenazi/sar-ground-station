import uuid
from datetime import datetime, timezone
from typing import Optional


_sessions: dict[str, dict] = {}


def _detect_mode_from_name(folder_name: str) -> str:
    name = folder_name.lower()
    if "ble" in name:
        return "ble"
    if "scan" in name:
        return "wifi"
    return "unknown"


def create_session(folder_id: str, mode: Optional[str] = None) -> dict:
    session_id = str(uuid.uuid4())
    resolved_mode = mode if mode in ("wifi", "ble") else _detect_mode_from_name(folder_id)
    now = datetime.now(timezone.utc).isoformat()
    session = {
        "session_id": session_id,
        "folder_id": folder_id,
        "mode": resolved_mode,
        "created_at": now,
        "active_page": "session_start",
        "active_overview_csv": None,
        "active_calibration": None,
        "active_scan_csv": None,
        "active_enriched_artifact": None,
        "active_reid_artifact": None,
        "current_localization_result": None,
        "view_state": {},
        "warnings": [],
    }
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Optional[dict]:
    return _sessions.get(session_id)


def update_mode(session_id: str, mode: str) -> Optional[dict]:
    session = _sessions.get(session_id)
    if session is None:
        return None
    session["mode"] = mode
    return session


def set_active_artifact(
    session_id: str,
    artifact_type: str,
    artifact_path: str,
) -> Optional[dict]:
    session = _sessions.get(session_id)
    if session is None:
        return None
    if artifact_type == "enriched":
        session["active_enriched_artifact"] = artifact_path
    elif artifact_type == "reid":
        session["active_reid_artifact"] = artifact_path
    return session

