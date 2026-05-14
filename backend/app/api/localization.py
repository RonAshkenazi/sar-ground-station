from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.modules.localization.engine import (
    _LOC_02_SEARCH_AREA_BUFFER_M,
    _LOC_06_GRID_RESOLUTION_M,
    _LOC_07_DYNAMIC_SIGMA_ALPHA,
    _LOC_08_CONFIDENCE_CUTOFF,
    _LOC_UNCERTAINTY_PARTICIPATION_FLOOR,
    _LOC_UNCERTAINTY_ALPHA,
)


router = APIRouter()


class LocalizationRunRequest(BaseModel):
    reid_csv_filename: str
    bounds_mode: Literal["auto_track_plus_buffer", "manual_rectangle"] = "auto_track_plus_buffer"
    buffer_m: float = _LOC_02_SEARCH_AREA_BUFFER_M
    manual_lat_min: float | None = None
    manual_lat_max: float | None = None
    manual_lon_min: float | None = None
    manual_lon_max: float | None = None
    grid_resolution_m: float | None = None
    dynamic_sigma_alpha: float = _LOC_07_DYNAMIC_SIGMA_ALPHA
    confidence_cutoff: float = _LOC_08_CONFIDENCE_CUTOFF
    uncertainty_participation_floor: float = _LOC_UNCERTAINTY_PARTICIPATION_FLOOR
    uncertainty_alpha: float = _LOC_UNCERTAINTY_ALPHA


@router.post("/sessions/{session_id}/localization/run")
def run_localization_endpoint(
    session_id: str,
    body: LocalizationRunRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    from app.api.executions import create_execution
    from app.modules.session_navigation.session_store import get_session

    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    reid_csv_path = _resolve_reid_csv_path(session_id, body.reid_csv_filename)
    if not reid_csv_path.name.lower().endswith("_reid.csv"):
        raise HTTPException(status_code=422, detail="Input must be a REID CSV artifact")

    calibration = session.get("calibration") or session.get("active_calibration")
    if not calibration or calibration.get("approved") is not True:
        raise HTTPException(status_code=422, detail="No approved calibration for this session")

    manual_bounds = None
    if body.bounds_mode == "manual_rectangle":
        if None in (body.manual_lat_min, body.manual_lat_max, body.manual_lon_min, body.manual_lon_max):
            raise HTTPException(status_code=422, detail="Manual bounds require lat_min, lat_max, lon_min, lon_max")
        manual_bounds = {
            "lat_min": body.manual_lat_min,
            "lat_max": body.manual_lat_max,
            "lon_min": body.manual_lon_min,
            "lon_max": body.manual_lon_max,
        }

    execution_id = create_execution("localization")
    background_tasks.add_task(
        _run_localization_task,
        execution_id,
        session_id,
        reid_csv_path,
        calibration["parameters"],
        body.bounds_mode,
        body.buffer_m,
        manual_bounds,
        body.grid_resolution_m or _LOC_06_GRID_RESOLUTION_M,
        body.dynamic_sigma_alpha,
        body.confidence_cutoff,
        body.uncertainty_participation_floor,
        body.uncertainty_alpha,
    )
    return {"execution_id": execution_id, "status": "pending"}


def _run_localization_task(
    execution_id: str,
    session_id: str,
    reid_csv_path: Path,
    calibration_parameters: dict,
    bounds_mode: str,
    buffer_m: float,
    manual_bounds: dict | None,
    grid_resolution_m: float,
    dynamic_sigma_alpha: float,
    confidence_cutoff: float,
    uncertainty_participation_floor: float = _LOC_UNCERTAINTY_PARTICIPATION_FLOOR,
    uncertainty_alpha: float = _LOC_UNCERTAINTY_ALPHA,
) -> None:
    from app.api.executions import update_execution
    from app.modules.localization.engine import run_localization
    from app.modules.session_navigation.session_store import get_session

    update_execution(execution_id, status="running")
    try:
        result = run_localization(
            reid_csv_path=reid_csv_path,
            calibration=calibration_parameters,
            bounds_mode=bounds_mode,
            buffer_m=buffer_m,
            manual_bounds=manual_bounds,
            grid_resolution_m=grid_resolution_m,
            dynamic_sigma_alpha=dynamic_sigma_alpha,
            confidence_cutoff=confidence_cutoff,
            uncertainty_participation_floor=uncertainty_participation_floor,
            uncertainty_alpha=uncertainty_alpha,
        )
        session = get_session(session_id)
        if session is not None:
            session["active_localization"] = result
            session["current_localization_result"] = result
        update_execution(
            execution_id,
            status="success",
            warnings=result.get("warnings", []),
            result_metadata=result,
            error=None,
        )
    except Exception as exc:  # pragma: no cover
        update_execution(execution_id, status="failed", error=str(exc))


def _resolve_reid_csv_path(session_id: str, reid_csv_filename: str) -> Path:
    from app.modules.session_navigation.session_store import get_session
    from app.storage.data_paths import get_data_dir

    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    data_dir = get_data_dir().resolve()
    folder_path = (data_dir / session["folder_id"]).resolve()
    if not folder_path.is_relative_to(data_dir):
        raise HTTPException(status_code=400, detail="Invalid folder_id")

    reid_csv_path = (folder_path / reid_csv_filename).resolve()
    if not reid_csv_path.is_relative_to(folder_path):
        raise HTTPException(status_code=400, detail="Invalid reid_csv_filename")
    if not reid_csv_path.exists():
        raise HTTPException(status_code=404, detail=f"REID CSV not found: {reid_csv_filename}")
    if not reid_csv_path.is_file():
        raise HTTPException(status_code=400, detail="reid_csv_filename must reference a file")
    return reid_csv_path
