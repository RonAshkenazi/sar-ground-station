from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter()


class ActivateArtifactRequest(BaseModel):
    artifact_path: str
    artifact_type: str


@router.get("/sessions/{session_id}/inventory")
def get_inventory(session_id: str) -> dict:
    from app.modules.artifact_management.classifier import classify_folder
    from app.modules.session_navigation.session_store import get_session
    from app.storage.data_paths import get_data_dir

    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    data_dir = get_data_dir().resolve()
    folder_path = (data_dir / session["folder_id"]).resolve()
    if not folder_path.is_relative_to(data_dir):
        raise HTTPException(status_code=400, detail="Invalid folder_id")

    return classify_folder(folder_path)


@router.post("/sessions/{session_id}/artifacts/activate")
def activate_artifact(session_id: str, body: ActivateArtifactRequest) -> dict:
    from app.modules.session_navigation.session_store import (
        get_session,
        set_active_artifact,
    )

    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if body.artifact_type not in ("enriched", "reid"):
        raise HTTPException(
            status_code=422,
            detail="artifact_type must be 'enriched' or 'reid'",
        )

    updated = set_active_artifact(session_id, body.artifact_type, body.artifact_path)
    return {
        "session_id": session_id,
        "activated": body.artifact_type,
        "path": body.artifact_path,
        "active_enriched_artifact": updated["active_enriched_artifact"],
        "active_reid_artifact": updated["active_reid_artifact"],
    }
