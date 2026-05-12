from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.models.canonical_models import SavedSessionState
from app.storage.data_paths import get_data_dir, get_saved_scans_dir


router = APIRouter()


@router.post("/sessions/{session_id}/save")
def save_session(session_id: str) -> dict:
    from app.modules.session_navigation.session_store import get_session

    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    localization = session.get("active_localization")
    if not localization:
        raise HTTPException(status_code=422, detail="No localization result to save")

    reid_csv_path = _find_reid_csv(session)
    if reid_csv_path is None:
        raise HTTPException(status_code=422, detail="No REID CSV found for this session")

    now = datetime.now(timezone.utc)
    saved_id = now.strftime("%Y-%m-%dT%H-%M-%SZ")
    saved_at_utc = now.isoformat().replace("+00:00", "Z")
    save_dir = get_saved_scans_dir() / session["folder_id"] / saved_id
    save_dir.mkdir(parents=True, exist_ok=False)

    meta = SavedSessionState(
        scan_folder_id=session["folder_id"],
        mode=session["mode"],
        saved_artifacts={"reid_csv": reid_csv_path.name},
        saved_at_utc=saved_at_utc,
        session_calibration=session.get("active_calibration"),
    ).model_dump()

    _write_json(save_dir / "session_meta.json", meta)
    _write_json(save_dir / "calibration.json", session.get("active_calibration"))
    _write_json(save_dir / "localization.json", localization)
    shutil.copy2(reid_csv_path, save_dir / reid_csv_path.name)

    return {"saved_id": saved_id, "folder_id": session["folder_id"], "saved_at_utc": saved_at_utc}


@router.get("/saved-sessions")
def list_saved_sessions() -> list[dict]:
    root = get_saved_scans_dir()
    if not root.exists():
        return []

    saves = []
    for meta_path in root.glob("*/*/session_meta.json"):
        try:
            meta = _read_json(meta_path)
        except (OSError, json.JSONDecodeError):
            continue
        saves.append(
            {
                "saved_id": meta_path.parent.name,
                "folder_id": meta.get("scan_folder_id", meta_path.parent.parent.name),
                "saved_at_utc": meta.get("saved_at_utc", ""),
                "mode": meta.get("mode", "unknown"),
            }
        )
    return sorted(saves, key=lambda item: item["saved_at_utc"], reverse=True)


@router.post("/saved-sessions/{saved_id}/resume")
def resume_saved_session(saved_id: str) -> dict:
    from app.modules.session_navigation.session_store import create_session

    save_dir = _find_save_dir(saved_id)
    if save_dir is None:
        raise HTTPException(status_code=404, detail="Saved session not found")

    meta = _read_json(save_dir / "session_meta.json")
    calibration = _read_json(save_dir / "calibration.json")
    localization = _read_json(save_dir / "localization.json")
    folder_id = meta["scan_folder_id"]

    session = create_session(folder_id=folder_id, mode=meta.get("mode"))
    session["mode"] = meta.get("mode", session["mode"])
    session["active_calibration"] = calibration
    session["active_localization"] = localization
    session["current_localization_result"] = localization

    reid_name = (meta.get("saved_artifacts") or {}).get("reid_csv")
    if reid_name:
        saved_reid = save_dir / reid_name
        data_folder = (get_data_dir() / folder_id).resolve()
        data_folder.mkdir(parents=True, exist_ok=True)
        destination = (data_folder / reid_name).resolve()
        if not destination.exists() and destination.is_relative_to(data_folder):
            shutil.copy2(saved_reid, destination)
        session["active_reid_artifact"] = str(destination)

    return session


def _find_reid_csv(session: dict) -> Path | None:
    active = session.get("active_reid_artifact")
    if active:
        path = Path(active)
        if path.exists() and path.is_file():
            return path

    data_dir = get_data_dir().resolve()
    folder_path = (data_dir / session["folder_id"]).resolve()
    if not folder_path.is_relative_to(data_dir) or not folder_path.exists():
        return None
    candidates = [path for path in folder_path.iterdir() if path.is_file() and path.name.lower().endswith("_reid.csv")]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _find_save_dir(saved_id: str) -> Path | None:
    root = get_saved_scans_dir()
    if not root.exists():
        return None
    for candidate in root.glob(f"*/{saved_id}"):
        if candidate.is_dir() and (candidate / "session_meta.json").exists():
            return candidate
    return None


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))
