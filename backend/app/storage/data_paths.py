import os
from pathlib import Path


_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _resolve(env_var: str, default: str) -> Path:
    raw = os.getenv(env_var, default)
    path = Path(raw)
    if not path.is_absolute():
        path = _PROJECT_ROOT / path
    return path.resolve()


def get_data_dir() -> Path:
    return _resolve("DATA_DIR", "runtime/DATA")


def get_temp_dir() -> Path:
    return _resolve("TEMP_DIR", "runtime/TEMP")


def get_saved_scans_dir() -> Path:
    return _resolve("SAVED_SCANS_DIR", "runtime/Saved Scans")

