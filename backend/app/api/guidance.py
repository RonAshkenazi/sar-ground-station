from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.modules.guidance.engine import get_engine


router = APIRouter(prefix="/guidance", tags=["guidance"])


class InitRequest(BaseModel):
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    cell_size_m: float = 30.0


class UpdateRequest(BaseModel):
    type: str

    class Config:
        extra = "allow"


@router.post("/init")
def init_guidance(body: InitRequest) -> dict:
    bounds = {
        "min_lat": body.min_lat,
        "max_lat": body.max_lat,
        "min_lon": body.min_lon,
        "max_lon": body.max_lon,
    }
    result = get_engine().init_grid(bounds, body.cell_size_m)
    return {"ok": True, **result}


@router.post("/reset")
def reset_guidance() -> dict:
    get_engine().reset()
    return {"ok": True}


@router.get("/recommendation")
def get_recommendation() -> dict:
    rec = get_engine().get_recommendation()
    if rec is None:
        return {"available": False}
    return {"available": True, **rec}


@router.get("/grid")
def get_grid() -> dict:
    grid = get_engine().get_grid_state()
    if grid is None:
        return {"initialized": False, "cells": []}
    return {"initialized": True, **grid}


@router.post("/update")
def update_guidance(body: UpdateRequest) -> dict:
    get_engine().ingest(body.model_dump())
    return {"ok": True}
