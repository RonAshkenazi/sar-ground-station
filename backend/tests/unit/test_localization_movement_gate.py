import csv

from app.modules.localization.engine import run_localization
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


def _row(cluster_id: str, index: int, timestamp: object, lat: float, lon: float) -> dict[str, object]:
    return {
        "timestamp_utc": timestamp,
        "frame_type": "probe",
        "src_mac": f"02:00:00:00:00:{index:02x}",
        "rssi_dbm": -60 - index,
        "gps_lat": lat,
        "gps_lon": lon,
        "cluster_id": cluster_id,
        "cluster_type": "dynamic",
    }


def _valid_cluster(cluster_id: str = "valid", base_lat: float = 32.0, base_lon: float = 34.0) -> list[dict[str, object]]:
    return [
        _row(cluster_id, 0, "2026-01-01T00:00:00Z", base_lat, base_lon),
        _row(cluster_id, 1, "2026-01-01T00:00:20Z", base_lat + 0.0001, base_lon),
        _row(cluster_id, 2, "2026-01-01T00:00:40Z", base_lat + 0.0002, base_lon),
    ]


def test_stationary_short_span_cluster_fails_movement_gate_and_is_not_extractable(tmp_path) -> None:
    reid = tmp_path / "scan_REID.csv"
    stationary = [
        _row("stationary", index, f"2026-01-01T00:00:{index:02d}Z", 32.01, 34.01)
        for index in range(11)
    ]
    _write_reid_csv(reid, stationary + _valid_cluster())

    result = run_localization(reid, _calibration_params(), grid_resolution_m=20)

    failed = next(cluster for cluster in result["cluster_results"] if cluster["cluster_id"] == "stationary")
    assert failed["status"] == "failed"
    assert failed["failure_reason"] == "insufficient_movement"
    assert failed["time_gap_sec"] == 10.0
    assert failed["baseline_m"] == 0.0
    assert "insufficient movement" in failed["warnings"][0]
    assert "stationary" not in {prediction["cluster_id"] for prediction in extract_predictions_from_localization_result(result)}


def test_long_span_real_spread_cluster_passes_movement_gate(tmp_path) -> None:
    reid = tmp_path / "scan_REID.csv"
    _write_reid_csv(reid, _valid_cluster("mobile"))

    result = run_localization(reid, _calibration_params(), grid_resolution_m=20)

    cluster = result["cluster_results"][0]
    assert cluster["cluster_id"] == "mobile"
    assert cluster["status"] == "success"
    assert cluster["failure_reason"] is None


def test_cluster_fails_when_only_time_gap_is_below_threshold(tmp_path) -> None:
    reid = tmp_path / "scan_REID.csv"
    short_time_with_spread = [
        _row("short", 0, 1000.0, 32.02, 34.02),
        _row("short", 1, 1001.0, 32.0201, 34.02),
        _row("short", 2, 1002.0, 32.0202, 34.02),
    ]
    _write_reid_csv(reid, short_time_with_spread + _valid_cluster())

    result = run_localization(reid, _calibration_params(), grid_resolution_m=20)

    failed = next(cluster for cluster in result["cluster_results"] if cluster["cluster_id"] == "short")
    assert failed["status"] == "failed"
    assert failed["failure_reason"] == "insufficient_movement"
    assert failed["time_gap_sec"] == 2.0
    assert failed["baseline_m"] >= 5.0


def test_default_behavior_matches_relaxed_gate_for_well_moving_cluster(tmp_path) -> None:
    reid = tmp_path / "scan_REID.csv"
    _write_reid_csv(reid, _valid_cluster("mobile"))

    default_result = run_localization(reid, _calibration_params(), grid_resolution_m=20)
    relaxed_result = run_localization(
        reid,
        _calibration_params(),
        grid_resolution_m=20,
        min_time_gap_sec=0.0,
        min_baseline_m=0.0,
    )

    assert default_result["successful_clusters"] == relaxed_result["successful_clusters"] == 1
    assert default_result["failed_clusters"] == relaxed_result["failed_clusters"] == 0
    assert default_result["cluster_results"][0]["primary_peak"] == relaxed_result["cluster_results"][0]["primary_peak"]
