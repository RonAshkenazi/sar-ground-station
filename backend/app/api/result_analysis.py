from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel


router = APIRouter()


class AddGtPointRequest(BaseModel):
    lat: float
    lon: float
    label: str | None = None


class ImportGtPointsRequest(BaseModel):
    points: list[dict]


class EvaluateRequest(BaseModel):
    ratio_gate: float = 1.2
    max_match_dist_m: float = 200.0
    r_normalize_m: float = 30.0
    d_free_m: float = 10.0
    w_containment: float = 0.40
    w_distance: float = 0.30
    w_count: float = 0.20
    w_radius: float = 0.10


def _get_session_or_404(session_id: str) -> dict:
    from app.modules.session_navigation.session_store import get_session

    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/sessions/{session_id}/result-analysis")
def get_result_analysis(session_id: str) -> dict:
    from app.modules.result_analysis.gt_store import get_gt_points

    session = _get_session_or_404(session_id)
    return {
        "session_id": session_id,
        "gt_points": get_gt_points(session_id),
        "localization_available": session.get("current_localization_result") is not None,
        "last_evaluation": session.get("last_evaluation"),
    }


@router.post("/sessions/{session_id}/result-analysis/ground-truth/import")
def import_ground_truth(session_id: str, body: ImportGtPointsRequest) -> dict:
    from app.modules.result_analysis.gt_store import import_gt_points

    _get_session_or_404(session_id)
    if not body.points:
        raise HTTPException(status_code=422, detail="No points provided")
    added = import_gt_points(session_id, body.points)
    return {"added": len(added), "gt_points": added}


@router.post("/sessions/{session_id}/result-analysis/ground-truth")
def add_ground_truth_point(session_id: str, body: AddGtPointRequest) -> dict:
    from app.modules.result_analysis.gt_store import add_gt_point

    _get_session_or_404(session_id)
    return add_gt_point(session_id, body.lat, body.lon, body.label)


@router.delete("/sessions/{session_id}/result-analysis/ground-truth/{gt_id}")
def delete_ground_truth_point(session_id: str, gt_id: str) -> dict:
    from app.modules.result_analysis.gt_store import delete_gt_point

    _get_session_or_404(session_id)
    removed = delete_gt_point(session_id, gt_id)
    if not removed:
        raise HTTPException(status_code=404, detail="GT point not found")
    return {"deleted": gt_id}


@router.delete("/sessions/{session_id}/result-analysis/ground-truth")
def delete_ground_truth_legacy(session_id: str) -> dict:
    from app.modules.result_analysis.gt_store import clear_gt_points

    _get_session_or_404(session_id)
    clear_gt_points(session_id)
    return {"cleared": True}


@router.post("/sessions/{session_id}/result-analysis/ground-truth/clear")
def clear_ground_truth(session_id: str) -> dict:
    from app.modules.result_analysis.gt_store import clear_gt_points

    _get_session_or_404(session_id)
    clear_gt_points(session_id)
    return {"cleared": True}


@router.post("/sessions/{session_id}/result-analysis/evaluate")
def run_evaluation(session_id: str, body: EvaluateRequest) -> dict:
    from app.modules.result_analysis.engine import evaluate, extract_predictions_from_localization_result
    from app.modules.result_analysis.gt_store import get_gt_points

    session = _get_session_or_404(session_id)
    loc_result = session.get("current_localization_result")
    if not loc_result:
        raise HTTPException(status_code=422, detail="No localization result available for this session")

    gt_points = get_gt_points(session_id)
    if not gt_points:
        raise HTTPException(status_code=422, detail="No GT points defined. Add at least one GT point first.")

    result = evaluate(
        predictions=extract_predictions_from_localization_result(loc_result),
        gt_points=gt_points,
        ratio_gate=body.ratio_gate,
        max_match_dist_m=body.max_match_dist_m,
        r_normalize_m=body.r_normalize_m,
        d_free_m=body.d_free_m,
        w_containment=body.w_containment,
        w_distance=body.w_distance,
        w_count=body.w_count,
        w_radius=body.w_radius,
    )
    session["last_evaluation"] = result
    return result


@router.post("/sessions/{session_id}/result-analysis/rerun")
def rerun_from_result_analysis(session_id: str, body: dict, background_tasks: BackgroundTasks) -> dict:
    from app.api.executions import create_execution
    from app.api.localization import (
        _LOC_06_GRID_RESOLUTION_M,
        _LOC_UNCERTAINTY_ALPHA,
        _LOC_UNCERTAINTY_PARTICIPATION_FLOOR,
        _run_localization_task,
    )
    from app.modules.reid.engine import (
        _REID_01_ASSOCIATION_THRESHOLD,
        _REID_WIFI_BURST_WINDOW_SEC,
        _REID_WIFI_SEQ_GAP_MAX,
        _REID_WIFI_TIME_GAP_MAX_SEC,
    )

    session = _get_session_or_404(session_id)
    stage = body.get("stage", "localization")
    reid_params = body.get("reid_params") or {}
    loc_params = body.get("localization_params") or {}
    if stage not in {"localization", "reid"}:
        raise HTTPException(status_code=422, detail="Only localization or reid rerun is supported")
    if stage == "reid":
        enriched_artifact = session.get("active_enriched_artifact")
        if not enriched_artifact:
            raise HTTPException(status_code=422, detail="No active ENRICHED artifact available for Re-ID rerun")
        calibration = session.get("calibration") or session.get("active_calibration")
        if not calibration or calibration.get("approved") is not True:
            raise HTTPException(status_code=422, detail="No calibration available for Re-ID rerun")

        execution_id = create_execution("reid_localization")
        background_tasks.add_task(
            _run_reid_then_localization_task,
            execution_id,
            session_id,
            Path(enriched_artifact),
            calibration["parameters"],
            {
                "association_threshold": reid_params.get("association_threshold", _REID_01_ASSOCIATION_THRESHOLD),
                "seq_gap_max": reid_params.get("seq_gap_max", _REID_WIFI_SEQ_GAP_MAX),
                "time_gap_max_sec": reid_params.get("time_gap_max_sec", _REID_WIFI_TIME_GAP_MAX_SEC),
                "burst_window_sec": reid_params.get("burst_window_sec", _REID_WIFI_BURST_WINDOW_SEC),
                "probe_requests_only": reid_params.get("probe_requests_only", False),
            },
            loc_params,
        )
        session["last_evaluation"] = None
        return {"status": "pending", "execution_id": execution_id}

    reid_artifact = session.get("active_reid_artifact")
    if not reid_artifact:
        raise HTTPException(status_code=422, detail="No active REID artifact available for localization rerun")
    calibration = session.get("calibration") or session.get("active_calibration")
    if not calibration or calibration.get("approved") is not True:
        raise HTTPException(status_code=422, detail="No calibration available for localization rerun")

    execution_id = create_execution("localization")
    background_tasks.add_task(
        _run_localization_task,
        execution_id,
        session_id,
        Path(reid_artifact),
        calibration["parameters"],
        loc_params.get("bounds_mode", "auto_track_plus_buffer"),
        loc_params.get("buffer_m", 20.0),
        None,
        loc_params.get("grid_resolution_m", _LOC_06_GRID_RESOLUTION_M),
        loc_params.get("dynamic_sigma_alpha", 0.05),
        loc_params.get("confidence_cutoff", 0.50),
        loc_params.get("uncertainty_participation_floor", _LOC_UNCERTAINTY_PARTICIPATION_FLOOR),
        loc_params.get("uncertainty_alpha", _LOC_UNCERTAINTY_ALPHA),
    )
    session["last_evaluation"] = None
    return {"status": "pending", "localization_execution_id": execution_id}


def _run_reid_then_localization_task(
    execution_id: str,
    session_id: str,
    enriched_csv_path: Path,
    calibration_parameters: dict,
    reid_params: dict,
    loc_params: dict,
) -> None:
    from app.api.executions import update_execution
    from app.modules.localization.engine import (
        _LOC_02_SEARCH_AREA_BUFFER_M,
        _LOC_06_GRID_RESOLUTION_M,
        _LOC_07_DYNAMIC_SIGMA_ALPHA,
        _LOC_08_CONFIDENCE_CUTOFF,
        _LOC_UNCERTAINTY_ALPHA,
        _LOC_UNCERTAINTY_PARTICIPATION_FLOOR,
        run_localization,
    )
    from app.modules.reid.engine import run_reid
    from app.modules.session_navigation.session_store import get_session

    update_execution(execution_id, status="running")
    try:
        session = get_session(session_id)
        protocol = session["mode"] if session is not None else "wifi"
        reid_result = run_reid(enriched_csv_path=enriched_csv_path, protocol=protocol, **reid_params)
        reid_csv_path = Path(reid_result["reid_csv_path"])
        loc_result = run_localization(
            reid_csv_path=reid_csv_path,
            calibration=calibration_parameters,
            bounds_mode=loc_params.get("bounds_mode", "auto_track_plus_buffer"),
            buffer_m=loc_params.get("buffer_m", _LOC_02_SEARCH_AREA_BUFFER_M),
            manual_bounds=None,
            grid_resolution_m=loc_params.get("grid_resolution_m", _LOC_06_GRID_RESOLUTION_M),
            dynamic_sigma_alpha=loc_params.get("dynamic_sigma_alpha", _LOC_07_DYNAMIC_SIGMA_ALPHA),
            confidence_cutoff=loc_params.get("confidence_cutoff", _LOC_08_CONFIDENCE_CUTOFF),
            uncertainty_participation_floor=loc_params.get(
                "uncertainty_participation_floor",
                _LOC_UNCERTAINTY_PARTICIPATION_FLOOR,
            ),
            uncertainty_alpha=loc_params.get("uncertainty_alpha", _LOC_UNCERTAINTY_ALPHA),
        )
        session = get_session(session_id)
        if session is not None:
            session["active_reid"] = {
                "reid_csv_path": reid_result["reid_csv_path"],
                "quality": reid_result,
            }
            session["active_reid_artifact"] = reid_result["reid_csv_path"]
            session["active_localization"] = loc_result
            session["current_localization_result"] = loc_result
        update_execution(
            execution_id,
            status="success",
            warnings=[*reid_result.get("warnings", []), *loc_result.get("warnings", [])],
            result_metadata={"reid": reid_result, "localization": loc_result},
            error=None,
        )
    except Exception as exc:  # pragma: no cover
        update_execution(execution_id, status="failed", error=str(exc))
