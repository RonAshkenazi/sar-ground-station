from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel


router = APIRouter()


class EnrichmentRunRequest(BaseModel):
    csv_filename: str


@router.post("/sessions/{session_id}/enrichment/run")
def run_enrichment_endpoint(
    session_id: str,
    body: EnrichmentRunRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    from app.api.executions import create_execution
    from app.modules.session_navigation.session_store import get_session

    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    csv_path = _resolve_session_csv_path(session_id, body.csv_filename)
    pcap_path = _find_matching_pcap(csv_path)
    if pcap_path is None:
        raise HTTPException(
            status_code=422,
            detail=f"No matching PCAP file found for {body.csv_filename}",
        )

    execution_id = create_execution("enrichment")
    background_tasks.add_task(_run_enrichment_task, execution_id, session_id, csv_path, pcap_path)
    return {"execution_id": execution_id, "status": "pending"}


def _run_enrichment_task(
    execution_id: str,
    session_id: str,
    csv_path: Path,
    pcap_path: Path,
) -> None:
    from app.api.executions import update_execution
    from app.modules.enrichment.engine import run_enrichment
    from app.modules.session_navigation.session_store import get_session

    update_execution(execution_id, status="running")
    try:
        result = run_enrichment(csv_path=csv_path, pcap_path=pcap_path, protocol="wifi")
        session = get_session(session_id)
        if session is not None:
            session["active_enrichment"] = {
                "enriched_csv_path": result["enriched_csv_path"],
                "quality": result,
            }
            session["active_enriched_artifact"] = result["enriched_csv_path"]
        update_execution(
            execution_id,
            status="success",
            warnings=result.get("warnings", []),
            result_metadata=result,
            error=None,
        )
    except Exception as exc:  # pragma: no cover - exercised through API failure state
        update_execution(execution_id, status="failed", error=str(exc))


def _resolve_session_csv_path(session_id: str, csv_filename: str) -> Path:
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


def _find_matching_pcap(csv_path: Path) -> Path | None:
    target_stem = csv_path.stem.lower()
    for candidate in csv_path.parent.iterdir():
        if candidate.is_file() and candidate.suffix.lower() == ".pcap":
            if candidate.stem.lower() == target_stem:
                return candidate
    return None
