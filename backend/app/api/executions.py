from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException


router = APIRouter()
_executions: dict[str, dict] = {}


def create_execution(stage: str) -> str:
    execution_id = str(uuid.uuid4())
    _executions[execution_id] = {
        "execution_id": execution_id,
        "status": "pending",
        "stage": stage,
        "warnings": [],
        "result_metadata": None,
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    return execution_id


def update_execution(execution_id: str, **kwargs) -> None:
    execution = _executions.get(execution_id)
    if execution is None:
        return
    execution.update(kwargs)
    execution["updated_at"] = datetime.now(timezone.utc).isoformat()


def get_execution(execution_id: str) -> dict | None:
    return _executions.get(execution_id)


@router.get("/executions/{execution_id}")
def get_execution_endpoint(execution_id: str) -> dict:
    execution = get_execution(execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution
