from pathlib import Path


_EXCLUDE_SUBSTRINGS = ("_reid_reid", "_enriched_reid")
_EXCLUDE_PREFIXES = ("localization_input",)


def _is_excluded(name: str) -> bool:
    lower = name.lower()
    for substring in _EXCLUDE_SUBSTRINGS:
        if substring in lower:
            return True
    for prefix in _EXCLUDE_PREFIXES:
        if lower.startswith(prefix):
            return True
    return False


def _is_enriched_artifact(name: str) -> bool:
    return name.lower().endswith("_enriched.csv")


def _is_reid_artifact(name: str) -> bool:
    return name.lower().endswith("_reid.csv")


def classify_folder(folder_path: Path) -> dict:
    """Classify all root-level files in folder_path into workflow buckets."""
    raw_csvs = []
    pcap_files = []
    enriched_artifacts = []
    reid_artifacts = []

    if not folder_path.exists():
        return {
            "raw_csvs": raw_csvs,
            "pcap_files": pcap_files,
            "enriched_artifacts": enriched_artifacts,
            "reid_artifacts": reid_artifacts,
            "warning": f"Folder not found: {folder_path}",
        }

    for entry in sorted(folder_path.iterdir()):
        if not entry.is_file():
            continue

        name = entry.name
        if _is_excluded(name):
            continue

        if entry.suffix.lower() == ".pcap":
            pcap_files.append({"filename": name, "path": str(entry)})
            continue

        if entry.suffix.lower() != ".csv":
            continue

        if _is_reid_artifact(name):
            reid_artifacts.append(
                {
                    "filename": name,
                    "path": str(entry),
                    "stage_jump_suggestion": "activate_for_localization",
                }
            )
        elif _is_enriched_artifact(name):
            enriched_artifacts.append(
                {
                    "filename": name,
                    "path": str(entry),
                    "stage_jump_suggestion": "activate_for_reid",
                }
            )
        else:
            raw_csvs.append({"filename": name, "path": str(entry)})

    return {
        "raw_csvs": raw_csvs,
        "pcap_files": pcap_files,
        "enriched_artifacts": enriched_artifacts,
        "reid_artifacts": reid_artifacts,
    }

