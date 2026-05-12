from fastapi import APIRouter


router = APIRouter()


@router.get("/sessions/{session_id}/result-analysis")
def get_result_analysis(session_id: str) -> dict[str, str]:
    return {
        "status": "not_implemented",
        "endpoint": f"/api/sessions/{session_id}/result-analysis",
    }


@router.post("/sessions/{session_id}/result-analysis/ground-truth")
def create_ground_truth(session_id: str) -> dict[str, str]:
    return {
        "status": "not_implemented",
        "endpoint": f"/api/sessions/{session_id}/result-analysis/ground-truth",
    }


@router.delete("/sessions/{session_id}/result-analysis/ground-truth")
def delete_ground_truth(session_id: str) -> dict[str, str]:
    return {
        "status": "not_implemented",
        "endpoint": f"/api/sessions/{session_id}/result-analysis/ground-truth",
    }


@router.post("/sessions/{session_id}/result-analysis/rerun")
def rerun_result_analysis(session_id: str) -> dict[str, str]:
    return {
        "status": "not_implemented",
        "endpoint": f"/api/sessions/{session_id}/result-analysis/rerun",
    }

