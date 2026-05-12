from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> bool:
        return False

load_dotenv()

from app.api import (  # noqa: E402
    calibration,
    enrichment,
    executions,
    inventory,
    localization,
    overview,
    reid,
    result_analysis,
    saved_sessions,
    sessions,
)
from app.storage.data_paths import (  # noqa: E402
    get_data_dir,
    get_saved_scans_dir,
    get_temp_dir,
)


LOGGER = logging.getLogger(__name__)
RUNTIME_PATHS = {
    "DATA_DIR": get_data_dir,
    "TEMP_DIR": get_temp_dir,
    "SAVED_SCANS_DIR": get_saved_scans_dir,
}


def warn_for_missing_runtime_paths() -> None:
    for env_name, path_factory in RUNTIME_PATHS.items():
        configured_path = path_factory()
        if not Path(configured_path).exists():
            LOGGER.warning("%s does not exist: %s", env_name, configured_path)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    warn_for_missing_runtime_paths()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="SAR Ground Station", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(sessions.router, prefix="/api")
    app.include_router(inventory.router, prefix="/api")
    app.include_router(overview.router, prefix="/api")
    app.include_router(calibration.router, prefix="/api")
    app.include_router(enrichment.router, prefix="/api")
    app.include_router(reid.router, prefix="/api")
    app.include_router(localization.router, prefix="/api")
    app.include_router(result_analysis.router, prefix="/api")
    app.include_router(saved_sessions.router, prefix="/api")
    app.include_router(executions.router, prefix="/api")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
