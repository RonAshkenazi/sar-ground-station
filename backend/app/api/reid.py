from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.modules.reid.engine import (
    _REID_01_ASSOCIATION_THRESHOLD,
    _REID_WIFI_BURST_WINDOW_SEC,
    _REID_WIFI_SEQ_GAP_MAX,
    _REID_WIFI_TIME_GAP_MAX_SEC,
)


router = APIRouter()


class ReIdRunRequest(BaseModel):
    enriched_csv_filename: str
    association_threshold: float = _REID_01_ASSOCIATION_THRESHOLD
    seq_gap_max: int = _REID_WIFI_SEQ_GAP_MAX
    time_gap_max_sec: float = _REID_WIFI_TIME_GAP_MAX_SEC
    burst_window_sec: float = _REID_WIFI_BURST_WINDOW_SEC
    probe_requests_only: bool = False


@router.post("/sessions/{session_id}/reid/run")
def run_reid_endpoint(
    session_id: str,
    body: ReIdRunRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    from app.api.executions import create_execution
    from app.modules.session_navigation.session_store import get_session

    if get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")

    enriched_csv_path = _resolve_enriched_csv_path(session_id, body.enriched_csv_filename)
    if not enriched_csv_path.name.lower().endswith("_enriched.csv"):
        raise HTTPException(status_code=422, detail="Input must be an ENRICHED CSV artifact")

    execution_id = create_execution("reid")
    background_tasks.add_task(
        _run_reid_task,
        execution_id,
        session_id,
        enriched_csv_path,
        body.association_threshold,
        body.seq_gap_max,
        body.time_gap_max_sec,
        body.burst_window_sec,
        body.probe_requests_only,
    )
    return {"execution_id": execution_id, "status": "pending"}


def _run_reid_task(
    execution_id: str,
    session_id: str,
    enriched_csv_path: Path,
    association_threshold: float,
    seq_gap_max: int,
    time_gap_max_sec: float,
    burst_window_sec: float,
    probe_requests_only: bool,
) -> None:
    from app.api.executions import update_execution
    from app.modules.reid.engine import run_reid
    from app.modules.session_navigation.session_store import get_session

    update_execution(execution_id, status="running")
    try:
        session = get_session(session_id)
        protocol = session["mode"] if session is not None else "wifi"
        result = run_reid(
            enriched_csv_path=enriched_csv_path,
            protocol=protocol,
            association_threshold=association_threshold,
            seq_gap_max=seq_gap_max,
            time_gap_max_sec=time_gap_max_sec,
            burst_window_sec=burst_window_sec,
            probe_requests_only=probe_requests_only,
        )
        if session is not None:
            session["active_reid"] = {
                "reid_csv_path": result["reid_csv_path"],
                "quality": result,
            }
            session["active_reid_artifact"] = result["reid_csv_path"]
        update_execution(
            execution_id,
            status="success",
            warnings=result.get("warnings", []),
            result_metadata=result,
            error=None,
        )
    except Exception as exc:  # pragma: no cover
        update_execution(execution_id, status="failed", error=str(exc))


def _resolve_enriched_csv_path(session_id: str, enriched_csv_filename: str) -> Path:
    from app.modules.session_navigation.session_store import get_session
    from app.storage.data_paths import get_data_dir

    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    data_dir = get_data_dir().resolve()
    folder_path = (data_dir / session["folder_id"]).resolve()
    if not folder_path.is_relative_to(data_dir):
        raise HTTPException(status_code=400, detail="Invalid folder_id")

    enriched_csv_path = (folder_path / enriched_csv_filename).resolve()
    if not enriched_csv_path.is_relative_to(folder_path):
        raise HTTPException(status_code=400, detail="Invalid enriched_csv_filename")
    if not enriched_csv_path.exists():
        raise HTTPException(status_code=404, detail=f"ENRICHED CSV not found: {enriched_csv_filename}")
    if not enriched_csv_path.is_file():
        raise HTTPException(status_code=400, detail="enriched_csv_filename must reference a file")
    return enriched_csv_path
