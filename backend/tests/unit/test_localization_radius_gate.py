import csv

from app.modules.result_analysis.engine import extract_predictions_from_localization_result


def _calibration_params() -> dict:
    return {"rssi_at_1m": -40.0, "path_loss_n": 2.0, "sigma": 6.0}


def _write_reid_csv(path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "timestamp_utc",
        "frame_type",
        "src_mac",
        "rssi_dbm",
        "gps_lat",
        "gps_lon",
        "cluster_id",
        "cluster_type",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _rows_for_cluster(cluster_id: str, base_lat: float) -> list[dict[str, object]]:
    return [
        {
            "timestamp_utc": f"2026-01-01T00:00:{index * 20:02d}Z",
            "frame_type": "probe",
            "src_mac": f"02:00:00:00:00:{index:02x}",
            "rssi_dbm": -60 - index,
            "gps_lat": base_lat + index * 0.0001,
            "gps_lon": 34.0,
            "cluster_id": cluster_id,
            "cluster_type": "dynamic",
        }
        for index in range(3)
    ]


def _fake_localize_cluster(**kwargs) -> dict:
    cluster_id = kwargs["cluster_id"]
    radius_m = 40.0 if cluster_id == "wide" else 20.0
    return {
        "cluster_id": cluster_id,
        "cluster_type": kwargs["cluster_type"],
        "status": "success",
        "sample_count": len(kwargs["rows"]),
        "primary_peak": {"lat": float(kwargs["rows"][0]["gps_lat"]), "lon": float(kwargs["rows"][0]["gps_lon"]), "value": 1.0},
        "candidate_peaks": [],
        "uncertainty_regions": [{"center_lat": float(kwargs["rows"][0]["gps_lat"]), "center_lon": float(kwargs["rows"][0]["gps_lon"]), "radius_m": radius_m}],
        "grid_cells": [],
        "warnings": [],
        "failure_reason": None,
    }


def test_oversized_uncertainty_radius_cluster_fails_and_is_not_extractable(tmp_path, monkeypatch) -> None:
    from app.modules.localization import engine as localization_engine

    monkeypatch.setattr(localization_engine, "_localize_cluster", _fake_localize_cluster)
    reid = tmp_path / "scan_REID.csv"
    _write_reid_csv(reid, _rows_for_cluster("wide", 32.0) + _rows_for_cluster("ok", 32.01))

    result = localization_engine.run_localization(reid, _calibration_params(), grid_resolution_m=20)

    wide = next(cluster for cluster in result["cluster_results"] if cluster["cluster_id"] == "wide")
    assert wide["status"] == "failed"
    assert wide["failure_reason"] == "uncertainty_radius_too_large"
    assert wide["radius_m"] == 40.0
    assert "uncertainty radius too large" in wide["warnings"][0]
    assert "wide" not in {prediction["cluster_id"] for prediction in extract_predictions_from_localization_result(result)}


def test_radius_at_threshold_is_unaffected(tmp_path, monkeypatch) -> None:
    from app.modules.localization import engine as localization_engine

    monkeypatch.setattr(localization_engine, "_localize_cluster", _fake_localize_cluster)
    reid = tmp_path / "scan_REID.csv"
    _write_reid_csv(reid, _rows_for_cluster("wide", 32.0))

    result = localization_engine.run_localization(reid, _calibration_params(), grid_resolution_m=20, max_uncertainty_radius_m=40.0)

    cluster = result["cluster_results"][0]
    assert cluster["cluster_id"] == "wide"
    assert cluster["status"] == "success"
    assert cluster["failure_reason"] is None


def test_default_radius_gate_behavior_unchanged_for_small_radius_fixture(tmp_path, monkeypatch) -> None:
    from app.modules.localization import engine as localization_engine

    monkeypatch.setattr(localization_engine, "_localize_cluster", _fake_localize_cluster)
    reid = tmp_path / "scan_REID.csv"
    _write_reid_csv(reid, _rows_for_cluster("ok", 32.0))

    default_result = localization_engine.run_localization(reid, _calibration_params(), grid_resolution_m=20)
    relaxed_result = localization_engine.run_localization(
        reid,
        _calibration_params(),
        grid_resolution_m=20,
        max_uncertainty_radius_m=100.0,
    )

    assert default_result["successful_clusters"] == relaxed_result["successful_clusters"] == 1
    assert default_result["failed_clusters"] == relaxed_result["failed_clusters"] == 0
    assert default_result["cluster_results"][0]["uncertainty_regions"] == relaxed_result["cluster_results"][0]["uncertainty_regions"]
