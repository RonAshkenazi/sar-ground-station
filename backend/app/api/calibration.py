from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter()


class CandidatesRequest(BaseModel):
    csv_filename: str


class RunCalibrationRequest(BaseModel):
    csv_filename: str
    mac: str
    gt_mode: Literal["mean_first_k", "first_sample", "manual_map_click"] = "mean_first_k"
    gt_k: int = 5
    manual_lat: Optional[float] = None
    manual_lon: Optional[float] = None
    enable_ransac: bool = True
    ransac_threshold_db: float = 4.0
    ransac_iterations: int = 100
    distance_floor_m: float = 1.0


class FallbackRequest(BaseModel):
    preset_name: Literal["urban", "open_field", "mixed_outdoor"]


@router.post("/sessions/{session_id}/calibration/candidates")
def get_calibration_candidates(session_id: str, body: CandidatesRequest) -> dict:
    from app.modules.calibration.engine import list_macs_in_csv

    csv_path = _resolve_session_csv_path(session_id, body.csv_filename)
    return {
        "csv_filename": body.csv_filename,
        "macs": list_macs_in_csv(csv_path),
    }


@router.post("/sessions/{session_id}/calibration/run")
def run_calibration(session_id: str, body: RunCalibrationRequest) -> dict:
    from app.modules.calibration.engine import run_calibration as _run
    from app.modules.session_navigation.session_store import get_session

    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    csv_path = _resolve_session_csv_path(session_id, body.csv_filename)

    result = _run(
        csv_path=csv_path,
        mac=body.mac,
        gt_mode=body.gt_mode,
        gt_k=body.gt_k,
        manual_lat=body.manual_lat,
        manual_lon=body.manual_lon,
        enable_ransac=body.enable_ransac,
        ransac_threshold_db=body.ransac_threshold_db,
        ransac_iterations=body.ransac_iterations,
        distance_floor_m=body.distance_floor_m,
    )
    session["_pending_calibration"] = {
        "csv_filename": body.csv_filename,
        "mac": body.mac,
        "result": result,
    }
    return result


@router.post("/sessions/{session_id}/calibration/approve")
def approve_calibration(session_id: str) -> dict:
    from app.models.canonical_models import SessionCalibration
    from app.modules.session_navigation.session_store import get_session

    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    pending = session.get("_pending_calibration")
    if not pending or not pending["result"].get("success"):
        raise HTTPException(status_code=422, detail="No successful calibration run to approve")

    calibration = SessionCalibration(
        scan_folder_id=session["folder_id"],
        parameter_source="derived",
        parameters=pending["result"]["parameters"],
        approved=True,
        calibration_csv_file=pending["csv_filename"],
        calibration_mac_address=pending["mac"],
    )
    session["active_calibration"] = calibration.model_dump()
    return session["active_calibration"]


@router.post("/sessions/{session_id}/calibration/fallback")
def use_fallback(session_id: str, body: FallbackRequest) -> dict:
    from app.models.canonical_models import SessionCalibration
    from app.modules.calibration.engine import FALLBACK_PRESETS
    from app.modules.session_navigation.session_store import get_session

    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    calibration = SessionCalibration(
        scan_folder_id=session["folder_id"],
        parameter_source="fallback",
        parameters=FALLBACK_PRESETS[body.preset_name],
        approved=True,
        parameter_set_name=body.preset_name,
    )
    session["active_calibration"] = calibration.model_dump()
    return session["active_calibration"]


def _resolve_session_csv_path(session_id: str, csv_filename: str):
    from app.modules.session_navigation.session_store import get_session
    from app.storage.data_paths import get_data_dir

    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    data_dir = get_data_dir().resolve()
    folder_path = (data_dir / session["folder_id"]).resolve()
    if not folder_path.is_relative_to(data_dir):
        raise HTTPException(status_code=400, detail="Invalid folder_id")

    csv_path = (folder_path / csv_filename).resolve()
    if not csv_path.is_relative_to(folder_path):
        raise HTTPException(status_code=400, detail="Invalid csv_filename")
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail=f"CSV not found: {csv_filename}")
    if not csv_path.is_file():
        raise HTTPException(status_code=400, detail="csv_filename must reference a file")
    return csv_path
