from pathlib import Path


def _detect_mode(folder_name: str) -> str:
    name = folder_name.lower()
    if "ble" in name:
        return "ble"
    if "scan" in name:
        return "wifi"
    return "unknown"


def list_scan_folders(data_dir: Path) -> list[dict]:
    """Return all direct subfolders of data_dir with detected mode."""
    if not data_dir.exists() or not data_dir.is_dir():
        return []

    folders = []
    for entry in sorted(data_dir.iterdir()):
        if entry.is_dir():
            folders.append(
                {
                    "folder_id": entry.name,
                    "folder_name": entry.name,
                    "detected_mode": _detect_mode(entry.name),
                }
            )
    return folders

