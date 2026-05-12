from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter()


class OverviewRequest(BaseModel):
    csv_filename: str


@router.post("/sessions/{session_id}/overview")
def run_overview(session_id: str, body: OverviewRequest) -> dict:
    from app.modules.overview.stats import compute_overview_stats
    from app.modules.session_navigation.session_store import get_session
    from app.storage.data_paths import get_data_dir

    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    data_dir = get_data_dir().resolve()
    folder_path = (data_dir / session["folder_id"]).resolve()
    if not folder_path.is_relative_to(data_dir):
        raise HTTPException(status_code=400, detail="Invalid folder_id")

    csv_path = (folder_path / body.csv_filename).resolve()
    if not csv_path.is_relative_to(folder_path):
        raise HTTPException(status_code=400, detail="Invalid csv_filename")

    if not csv_path.exists():
        raise HTTPException(status_code=404, detail=f"CSV not found: {body.csv_filename}")
    if not csv_path.is_file():
        raise HTTPException(status_code=400, detail="csv_filename must reference a file")

    session["active_overview_csv"] = body.csv_filename

    return compute_overview_stats(csv_path)
