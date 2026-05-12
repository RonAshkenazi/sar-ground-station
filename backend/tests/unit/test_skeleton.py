import pytest
import struct
from pathlib import Path
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import create_app
from app.models.canonical_models import ReIDRecord, ScanRecord


def test_app_factory_creates_health_endpoint() -> None:
    app = create_app()

    assert any(route.path == "/health" for route in app.routes)


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/sessions/session-1/result-analysis"),
        ("post", "/api/sessions/session-1/result-analysis/ground-truth"),
        ("delete", "/api/sessions/session-1/result-analysis/ground-truth"),
        ("post", "/api/sessions/session-1/result-analysis/rerun"),
    ],
)
def test_stub_endpoints_return_not_implemented(method: str, path: str) -> None:
    client = TestClient(create_app())

    response = getattr(client, method)(path)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_implemented"
    assert body["endpoint"] == path


def test_scan_record_requires_src_mac() -> None:
    with pytest.raises(ValidationError):
        ScanRecord(
            timestamp_utc="2026-05-11T00:00:00Z",
            frame_type="probe",
            rssi_dbm=-50,
            gps_lat=32.0,
            gps_lon=34.0,
        )


def test_reid_record_requires_cluster_id() -> None:
    with pytest.raises(ValidationError):
        ReIDRecord(
            timestamp_utc="2026-05-11T00:00:00Z",
            frame_type="probe",
            src_mac="00:11:22:33:44:55",
            rssi_dbm=-50,
            gps_lat=32.0,
            gps_lon=34.0,
            cluster_type="static",
        )


def test_reid_record_preserves_internal_match_delta_alias() -> None:
    record = ReIDRecord(
        timestamp_utc="2026-05-11T00:00:00Z",
        frame_type="probe",
        src_mac="00:11:22:33:44:55",
        rssi_dbm=-50,
        gps_lat=32.0,
        gps_lon=34.0,
        cluster_id="cluster-1",
        cluster_type="dynamic",
        _match_delta_ms=12.5,
    )

    assert record.model_dump(by_alias=True)["_match_delta_ms"] == 12.5


def test_list_scan_folders_returns_folders(tmp_path) -> None:
    (tmp_path / "scan_mission_01").mkdir()
    (tmp_path / "ble_patrol_02").mkdir()
    (tmp_path / "unrelated").mkdir()

    from app.modules.dataset_discovery.discovery import list_scan_folders

    result = list_scan_folders(tmp_path)

    names = [folder["folder_id"] for folder in result]
    assert "scan_mission_01" in names
    assert "ble_patrol_02" in names
    assert "unrelated" in names


def test_mode_detection_wifi(tmp_path) -> None:
    (tmp_path / "scan_mission_01").mkdir()

    from app.modules.dataset_discovery.discovery import list_scan_folders

    result = list_scan_folders(tmp_path)

    assert result[0]["detected_mode"] == "wifi"


def test_mode_detection_ble(tmp_path) -> None:
    (tmp_path / "ble_patrol_02").mkdir()

    from app.modules.dataset_discovery.discovery import list_scan_folders

    result = list_scan_folders(tmp_path)

    assert result[0]["detected_mode"] == "ble"


def test_mode_detection_unknown(tmp_path) -> None:
    (tmp_path / "mission_alpha").mkdir()

    from app.modules.dataset_discovery.discovery import list_scan_folders

    result = list_scan_folders(tmp_path)

    assert result[0]["detected_mode"] == "unknown"


def test_list_scan_folders_missing_dir(tmp_path) -> None:
    from app.modules.dataset_discovery.discovery import list_scan_folders

    result = list_scan_folders(tmp_path / "does_not_exist")

    assert result == []


def test_subfolders_not_returned_as_scan_folders(tmp_path) -> None:
    (tmp_path / "scan_a").mkdir()
    (tmp_path / "not_a_folder.csv").write_text("data")

    from app.modules.dataset_discovery.discovery import list_scan_folders

    result = list_scan_folders(tmp_path)

    assert len(result) == 1
    assert result[0]["folder_id"] == "scan_a"


def test_session_creation_returns_session_id() -> None:
    client = TestClient(create_app())

    response = client.post("/api/sessions", json={"folder_id": "scan_test"})

    assert response.status_code == 200
    body = response.json()
    assert "session_id" in body
    assert body["folder_id"] == "scan_test"
    assert body["mode"] == "wifi"


def test_session_creation_ble_detection() -> None:
    client = TestClient(create_app())

    response = client.post("/api/sessions", json={"folder_id": "ble_patrol"})

    assert response.status_code == 200
    assert response.json()["mode"] == "ble"


def test_session_creation_manual_mode_override() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/sessions",
        json={"folder_id": "scan_test", "mode": "ble"},
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "ble"


def test_session_state_returns_correct_folder() -> None:
    client = TestClient(create_app())
    create_resp = client.post("/api/sessions", json={"folder_id": "scan_state_test"})
    session_id = create_resp.json()["session_id"]

    state_resp = client.get(f"/api/sessions/{session_id}/state")

    assert state_resp.status_code == 200
    assert state_resp.json()["folder_id"] == "scan_state_test"


def test_session_state_404_for_unknown() -> None:
    client = TestClient(create_app())

    response = client.get("/api/sessions/nonexistent-id/state")

    assert response.status_code == 404


def test_patch_mode_updates_session() -> None:
    client = TestClient(create_app())
    session_id = client.post(
        "/api/sessions",
        json={"folder_id": "scan_x"},
    ).json()["session_id"]

    patch_resp = client.patch(
        f"/api/sessions/{session_id}/mode",
        json={"mode": "ble"},
    )

    assert patch_resp.status_code == 200
    assert patch_resp.json()["mode"] == "ble"


def test_patch_mode_rejects_invalid_mode() -> None:
    client = TestClient(create_app())
    session_id = client.post(
        "/api/sessions",
        json={"folder_id": "scan_x"},
    ).json()["session_id"]

    patch_resp = client.patch(
        f"/api/sessions/{session_id}/mode",
        json={"mode": "lte"},
    )

    assert patch_resp.status_code == 422


def test_artifact_resolver_classifies_raw_csv(tmp_path) -> None:
    (tmp_path / "scan_data.csv").write_text("timestamp_utc,src_mac\n")

    from app.modules.artifact_management.classifier import classify_folder

    result = classify_folder(tmp_path)

    assert len(result["raw_csvs"]) == 1
    assert result["raw_csvs"][0]["filename"] == "scan_data.csv"


def test_artifact_resolver_recognises_uppercase_enriched(tmp_path) -> None:
    (tmp_path / "scan_data_ENRICHED.csv").write_text("data")

    from app.modules.artifact_management.classifier import classify_folder

    result = classify_folder(tmp_path)

    assert len(result["enriched_artifacts"]) == 1
    assert result["enriched_artifacts"][0]["stage_jump_suggestion"] == "activate_for_reid"


def test_artifact_resolver_recognises_lowercase_enriched(tmp_path) -> None:
    (tmp_path / "scan_data_enriched.csv").write_text("data")

    from app.modules.artifact_management.classifier import classify_folder

    result = classify_folder(tmp_path)

    assert len(result["enriched_artifacts"]) == 1


def test_artifact_resolver_recognises_lowercase_reid(tmp_path) -> None:
    (tmp_path / "scan_data_reid.csv").write_text("data")

    from app.modules.artifact_management.classifier import classify_folder

    result = classify_folder(tmp_path)

    assert len(result["reid_artifacts"]) == 1
    assert result["reid_artifacts"][0]["stage_jump_suggestion"] == "activate_for_localization"


def test_artifact_resolver_excludes_doubled_reid(tmp_path) -> None:
    (tmp_path / "scan_data_reid_reid.csv").write_text("data")
    (tmp_path / "scan_data_reid_reid_reid.csv").write_text("data")

    from app.modules.artifact_management.classifier import classify_folder

    result = classify_folder(tmp_path)

    assert result["reid_artifacts"] == []
    assert result["raw_csvs"] == []


def test_artifact_resolver_excludes_localization_input(tmp_path) -> None:
    (tmp_path / "localization_input.csv").write_text("data")
    (tmp_path / "localization_input_reid.csv").write_text("data")

    from app.modules.artifact_management.classifier import classify_folder

    result = classify_folder(tmp_path)

    assert result["raw_csvs"] == []
    assert result["reid_artifacts"] == []


def test_artifact_resolver_excludes_enriched_reid(tmp_path) -> None:
    (tmp_path / "scan_data_enriched_reid.csv").write_text("data")

    from app.modules.artifact_management.classifier import classify_folder

    result = classify_folder(tmp_path)

    assert result["enriched_artifacts"] == []
    assert result["raw_csvs"] == []


def test_artifact_resolver_ignores_subfolders(tmp_path) -> None:
    (tmp_path / "subfolder").mkdir()
    (tmp_path / "subfolder" / "scan_data.csv").write_text("data")

    from app.modules.artifact_management.classifier import classify_folder

    result = classify_folder(tmp_path)

    assert result["raw_csvs"] == []


def test_artifact_resolver_classifies_pcap(tmp_path) -> None:
    (tmp_path / "scan_data.pcap").write_bytes(b"pcap")

    from app.modules.artifact_management.classifier import classify_folder

    result = classify_folder(tmp_path)

    assert len(result["pcap_files"]) == 1


def test_inventory_endpoint_404_for_unknown_session() -> None:
    client = TestClient(create_app())

    response = client.get("/api/sessions/bad-id/inventory")

    assert response.status_code == 404


def test_inventory_endpoint_rejects_path_traversal() -> None:
    client = TestClient(create_app())
    session_id = client.post(
        "/api/sessions",
        json={"folder_id": "../../etc"},
    ).json()["session_id"]

    response = client.get(f"/api/sessions/{session_id}/inventory")

    assert response.status_code == 400


def test_activate_artifact_updates_session() -> None:
    client = TestClient(create_app())
    session_id = client.post(
        "/api/sessions",
        json={"folder_id": "scan_activate_test"},
    ).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/artifacts/activate",
        json={
            "artifact_path": "/some/path_ENRICHED.csv",
            "artifact_type": "enriched",
        },
    )

    assert response.status_code == 200
    assert response.json()["active_enriched_artifact"] == "/some/path_ENRICHED.csv"


def test_activate_artifact_invalid_type_returns_422() -> None:
    client = TestClient(create_app())
    session_id = client.post(
        "/api/sessions",
        json={"folder_id": "scan_x"},
    ).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/artifacts/activate",
        json={"artifact_path": "/some/path.csv", "artifact_type": "invalid"},
    )

    assert response.status_code == 422


def test_overview_stats_basic(tmp_path) -> None:
    csv_content = (
        "timestamp_utc,src_mac,rssi_dbm,gps_lat,gps_lon\n"
        "2026-01-19T11:00:00Z,aa:bb:cc:dd:ee:01,-60,32.1,34.5\n"
        "2026-01-19T11:00:01Z,aa:bb:cc:dd:ee:01,-65,32.2,34.6\n"
        "2026-01-19T11:00:02Z,aa:bb:cc:dd:ee:02,-80,,\n"
    )
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    from app.modules.overview.stats import compute_overview_stats

    result = compute_overview_stats(csv_file)

    assert result["record_count"] == 3
    assert result["unique_macs"] == 2
    assert result["gps_fix_pct"] == pytest.approx(66.7, abs=0.1)
    assert result["rssi_min"] == -80
    assert result["rssi_max"] == -60
    assert result["rssi_mean"] == pytest.approx(-68.3, abs=0.1)
    assert len(result["gps_points"]) == 2
    assert len(result["device_table"]) == 2
    assert result["device_table"][0]["src_mac"] == "aa:bb:cc:dd:ee:01"
    assert result["device_table"][0]["packet_count"] == 2


def test_overview_stats_empty_csv(tmp_path) -> None:
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("timestamp_utc,src_mac,rssi_dbm,gps_lat,gps_lon\n", encoding="utf-8")

    from app.modules.overview.stats import compute_overview_stats

    result = compute_overview_stats(csv_file)

    assert result["record_count"] == 0
    assert result["warning"] == "CSV file is empty"


def test_overview_endpoint_404_unknown_session() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/sessions/bad-id/overview",
        json={"csv_filename": "test.csv"},
    )

    assert response.status_code == 404


def test_overview_endpoint_404_missing_csv() -> None:
    client = TestClient(create_app())
    session_id = client.post(
        "/api/sessions",
        json={"folder_id": "scan_overview_test"},
    ).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/overview",
        json={"csv_filename": "nonexistent.csv"},
    )

    assert response.status_code == 404


def test_overview_endpoint_rejects_csv_path_traversal(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "scan_overview_test").mkdir()
    (tmp_path / "other.csv").write_text(
        "timestamp_utc,src_mac,rssi_dbm,gps_lat,gps_lon\n",
        encoding="utf-8",
    )
    client = TestClient(create_app())
    session_id = client.post(
        "/api/sessions",
        json={"folder_id": "scan_overview_test"},
    ).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/overview",
        json={"csv_filename": "../other.csv"},
    )

    assert response.status_code == 400


def test_overview_endpoint_updates_session_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    folder = tmp_path / "scan_overview_test"
    folder.mkdir()
    (folder / "test.csv").write_text(
        "timestamp_utc,src_mac,rssi_dbm,gps_lat,gps_lon\n"
        "2026-01-19T11:00:00Z,aa:bb:cc:dd:ee:01,-60,32.1,34.5\n",
        encoding="utf-8",
    )
    client = TestClient(create_app())
    session_id = client.post(
        "/api/sessions",
        json={"folder_id": "scan_overview_test"},
    ).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/overview",
        json={"csv_filename": "test.csv"},
    )
    state_response = client.get(f"/api/sessions/{session_id}/state")

    assert response.status_code == 200
    assert response.json()["record_count"] == 1
    assert state_response.json()["active_overview_csv"] == "test.csv"


def test_list_macs_returns_sorted_unique(tmp_path) -> None:
    csv_content = (
        "timestamp_utc,src_mac,rssi_dbm,gps_lat,gps_lon\n"
        "2026-01-01T00:00:00Z,bb:bb:bb:bb:bb:bb,-60,32.0,34.0\n"
        "2026-01-01T00:00:01Z,aa:aa:aa:aa:aa:aa,-65,32.1,34.1\n"
        "2026-01-01T00:00:02Z,aa:aa:aa:aa:aa:aa,-70,32.2,34.2\n"
    )
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    from app.modules.calibration.engine import list_macs_in_csv

    macs = list_macs_in_csv(csv_file)

    assert macs == ["aa:aa:aa:aa:aa:aa", "bb:bb:bb:bb:bb:bb"]


def test_calibration_run_derives_parameters(tmp_path) -> None:
    import math

    rssi_at_1m = -40.0
    path_loss_n = 2.0
    rows = ["timestamp_utc,src_mac,rssi_dbm,gps_lat,gps_lon"]
    for index in range(1, 11):
        distance_m = float(index)
        rssi = rssi_at_1m - 10 * path_loss_n * math.log10(distance_m)
        lat = 32.0 + distance_m * 0.000009
        rows.append(
            f"2026-01-01T00:00:{index:02d}Z,aa:aa:aa:aa:aa:aa,{rssi:.1f},{lat},34.0"
        )
    csv_file = tmp_path / "cal.csv"
    csv_file.write_text("\n".join(rows), encoding="utf-8")

    from app.modules.calibration.engine import run_calibration

    result = run_calibration(
        csv_path=csv_file,
        mac="aa:aa:aa:aa:aa:aa",
        gt_mode="manual_map_click",
        manual_lat=32.0,
        manual_lon=34.0,
        enable_ransac=False,
    )

    assert result["success"] is True
    assert result["parameters"]["rssi_at_1m"] == pytest.approx(-40.0, abs=0.6)
    assert result["parameters"]["path_loss_n"] == pytest.approx(2.0, abs=0.2)
    assert result["fit_quality"]["r2"] > 0.9


def test_calibration_run_fails_no_rows(tmp_path) -> None:
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text(
        "timestamp_utc,src_mac,rssi_dbm,gps_lat,gps_lon\n",
        encoding="utf-8",
    )

    from app.modules.calibration.engine import run_calibration

    result = run_calibration(csv_path=csv_file, mac="aa:aa:aa:aa:aa:aa")

    assert result["success"] is False
    assert result["error"] is not None


def test_calibration_candidates_endpoint_404_unknown_session() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/sessions/bad-id/calibration/candidates",
        json={"csv_filename": "test.csv"},
    )

    assert response.status_code == 404


def test_calibration_candidates_endpoint_returns_sorted_macs(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    folder = tmp_path / "scan_calibration_test"
    folder.mkdir()
    (folder / "test.csv").write_text(
        "timestamp_utc,src_mac,rssi_dbm,gps_lat,gps_lon\n"
        "2026-01-01T00:00:00Z,bb:bb:bb:bb:bb:bb,-60,32.0,34.0\n"
        "2026-01-01T00:00:01Z,aa:aa:aa:aa:aa:aa,-65,32.1,34.1\n",
        encoding="utf-8",
    )
    client = TestClient(create_app())
    session_id = client.post(
        "/api/sessions",
        json={"folder_id": "scan_calibration_test"},
    ).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/calibration/candidates",
        json={"csv_filename": "test.csv"},
    )

    assert response.status_code == 200
    assert response.json()["macs"] == ["aa:aa:aa:aa:aa:aa", "bb:bb:bb:bb:bb:bb"]


def test_calibration_run_endpoint_rejects_csv_path_traversal(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "scan_calibration_test").mkdir()
    (tmp_path / "other.csv").write_text(
        "timestamp_utc,src_mac,rssi_dbm,gps_lat,gps_lon\n",
        encoding="utf-8",
    )
    client = TestClient(create_app())
    session_id = client.post(
        "/api/sessions",
        json={"folder_id": "scan_calibration_test"},
    ).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/calibration/run",
        json={"csv_filename": "../other.csv", "mac": "aa:aa:aa:aa:aa:aa"},
    )

    assert response.status_code == 400


def test_calibration_approve_requires_run_first() -> None:
    client = TestClient(create_app())
    session_id = client.post(
        "/api/sessions",
        json={"folder_id": "scan_test"},
    ).json()["session_id"]

    response = client.post(f"/api/sessions/{session_id}/calibration/approve")

    assert response.status_code == 422


def test_calibration_approve_stores_derived_calibration(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    folder = tmp_path / "scan_calibration_test"
    folder.mkdir()
    rows = ["timestamp_utc,src_mac,rssi_dbm,gps_lat,gps_lon"]
    for index in range(1, 6):
        rows.append(
            f"2026-01-01T00:00:{index:02d}Z,aa:aa:aa:aa:aa:aa,-{40 + index},"
            f"{32.0 + index * 0.00001},34.0"
        )
    (folder / "cal.csv").write_text("\n".join(rows), encoding="utf-8")
    client = TestClient(create_app())
    session_id = client.post(
        "/api/sessions",
        json={"folder_id": "scan_calibration_test"},
    ).json()["session_id"]

    run_response = client.post(
        f"/api/sessions/{session_id}/calibration/run",
        json={
            "csv_filename": "cal.csv",
            "mac": "aa:aa:aa:aa:aa:aa",
            "gt_mode": "manual_map_click",
            "manual_lat": 32.0,
            "manual_lon": 34.0,
            "enable_ransac": False,
        },
    )
    approve_response = client.post(f"/api/sessions/{session_id}/calibration/approve")

    assert run_response.status_code == 200
    assert run_response.json()["success"] is True
    assert approve_response.status_code == 200
    assert approve_response.json()["parameter_source"] == "derived"
    assert approve_response.json()["approved"] is True
    assert approve_response.json()["calibration_csv_file"] == "cal.csv"


def test_calibration_fallback_activates_preset() -> None:
    client = TestClient(create_app())
    session_id = client.post(
        "/api/sessions",
        json={"folder_id": "scan_test"},
    ).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/calibration/fallback",
        json={"preset_name": "urban"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["parameter_source"] == "fallback"
    assert body["approved"] is True
    assert body["parameter_set_name"] == "urban"
    assert "rssi_at_1m" in body["parameters"]


def _write_test_pcap(path, src_mac: str, dst_mac: str, timestamp: float) -> None:
    def mac_bytes(mac: str) -> bytes:
        return bytes(int(part, 16) for part in mac.split(":"))

    payload = mac_bytes(dst_mac) + mac_bytes(src_mac) + b"\x08\x00" + b"payload"
    ts_sec = int(timestamp)
    ts_usec = int((timestamp - ts_sec) * 1_000_000)
    with path.open("wb") as file:
        file.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        file.write(struct.pack("<IIII", ts_sec, ts_usec, len(payload), len(payload)))
        file.write(payload)


def test_enrichment_engine_wifi_match(tmp_path) -> None:
    csv_file = tmp_path / "scan.csv"
    csv_file.write_text(
        "timestamp_utc,frame_type,src_mac,rssi_dbm,gps_lat,gps_lon,dst_mac,bssid\n"
        "2026-01-01T00:00:00Z,probe,aa:bb:cc:dd:ee:ff,-60,32.0,34.0,11:22:33:44:55:66,\n",
        encoding="utf-8",
    )
    pcap_file = tmp_path / "scan.pcap"
    _write_test_pcap(pcap_file, "aa:bb:cc:dd:ee:ff", "11:22:33:44:55:66", 1767225600.0)

    from app.modules.enrichment.engine import run_enrichment

    result = run_enrichment(csv_file, pcap_file, "wifi")
    output = tmp_path / "scan_ENRICHED.csv"

    assert result["matched_rows"] == 1
    assert result["match_rate"] == 1.0
    assert output.exists()
    assert "match_found" in output.read_text(encoding="utf-8")
    assert "True" in output.read_text(encoding="utf-8")


def test_enrichment_engine_no_match_rows_preserved(tmp_path) -> None:
    csv_file = tmp_path / "scan.csv"
    csv_file.write_text(
        "timestamp_utc,frame_type,src_mac,rssi_dbm,gps_lat,gps_lon\n"
        "2026-01-01T00:00:10Z,probe,aa:bb:cc:dd:ee:ff,-60,32.0,34.0\n",
        encoding="utf-8",
    )
    pcap_file = tmp_path / "scan.pcap"
    _write_test_pcap(pcap_file, "aa:bb:cc:dd:ee:ff", "11:22:33:44:55:66", 1767225600.0)

    from app.modules.enrichment.engine import run_enrichment

    result = run_enrichment(csv_file, pcap_file, "wifi")
    output_text = (tmp_path / "scan_ENRICHED.csv").read_text(encoding="utf-8")

    assert result["total_rows"] == 1
    assert result["matched_rows"] == 0
    assert "no_match" in output_text
    assert "False" in output_text


def test_enrichment_engine_writes_uppercase_suffix(tmp_path) -> None:
    csv_file = tmp_path / "scan.csv"
    csv_file.write_text(
        "timestamp_utc,frame_type,src_mac,rssi_dbm,gps_lat,gps_lon\n",
        encoding="utf-8",
    )
    pcap_file = tmp_path / "scan.pcap"
    _write_test_pcap(pcap_file, "aa:bb:cc:dd:ee:ff", "11:22:33:44:55:66", 1767225600.0)

    from app.modules.enrichment.engine import run_enrichment

    result = run_enrichment(csv_file, pcap_file, "wifi")

    assert result["enriched_csv_path"].endswith("_ENRICHED.csv")


def test_enrichment_endpoint_404_unknown_session() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/sessions/bad-id/enrichment/run",
        json={"csv_filename": "test.csv"},
    )

    assert response.status_code == 404


def test_enrichment_endpoint_422_no_pcap(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    folder = tmp_path / "scan_enrichment_test"
    folder.mkdir()
    (folder / "scan.csv").write_text(
        "timestamp_utc,frame_type,src_mac,rssi_dbm,gps_lat,gps_lon\n",
        encoding="utf-8",
    )
    client = TestClient(create_app())
    session_id = client.post(
        "/api/sessions",
        json={"folder_id": "scan_enrichment_test"},
    ).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/enrichment/run",
        json={"csv_filename": "scan.csv"},
    )

    assert response.status_code == 422


def test_enrichment_endpoint_returns_execution_id(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    folder = tmp_path / "scan_enrichment_test"
    folder.mkdir()
    (folder / "scan.csv").write_text(
        "timestamp_utc,frame_type,src_mac,rssi_dbm,gps_lat,gps_lon,dst_mac\n"
        "2026-01-01T00:00:00Z,probe,aa:bb:cc:dd:ee:ff,-60,32.0,34.0,11:22:33:44:55:66\n",
        encoding="utf-8",
    )
    _write_test_pcap(folder / "scan.pcap", "aa:bb:cc:dd:ee:ff", "11:22:33:44:55:66", 1767225600.0)
    client = TestClient(create_app())
    session_id = client.post(
        "/api/sessions",
        json={"folder_id": "scan_enrichment_test"},
    ).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/enrichment/run",
        json={"csv_filename": "scan.csv"},
    )
    body = response.json()
    execution_response = client.get(f"/api/executions/{body['execution_id']}")

    assert response.status_code == 200
    assert body["status"] == "pending"
    assert "execution_id" in body
    assert execution_response.status_code == 200
    assert execution_response.json()["status"] == "success"


def test_execution_endpoint_404_unknown() -> None:
    client = TestClient(create_app())

    response = client.get("/api/executions/bad-id")

    assert response.status_code == 404


def test_enrichment_endpoint_path_traversal_rejected(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    folder = tmp_path / "scan_enrichment_test"
    folder.mkdir()
    (tmp_path / "outside.csv").write_text(
        "timestamp_utc,frame_type,src_mac,rssi_dbm,gps_lat,gps_lon\n",
        encoding="utf-8",
    )
    client = TestClient(create_app())
    session_id = client.post(
        "/api/sessions",
        json={"folder_id": "scan_enrichment_test"},
    ).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/enrichment/run",
        json={"csv_filename": "../outside.csv"},
    )

    assert response.status_code == 400


def _write_test_enriched_csv(path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "timestamp_utc",
        "frame_type",
        "src_mac",
        "rssi_dbm",
        "gps_lat",
        "gps_lon",
        "match_found",
        "seq_ctl",
        "ie_ids",
        "ie_fingerprint",
        "frame_len",
        "src_vendor",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        import csv

        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_reid_engine_static_bypass(tmp_path) -> None:
    enriched = tmp_path / "scan_ENRICHED.csv"
    _write_test_enriched_csv(
        enriched,
        [
            {
                "timestamp_utc": "2026-01-01T00:00:00Z",
                "frame_type": "probe",
                "src_mac": "00:11:22:33:44:55",
                "rssi_dbm": -60,
                "gps_lat": 32.0,
                "gps_lon": 34.0,
                "match_found": True,
            }
        ],
    )

    from app.modules.reid.engine import run_reid

    result = run_reid(enriched, "wifi")
    output = (tmp_path / "scan_REID.csv").read_text(encoding="utf-8")

    assert result["static_cluster_count"] == 1
    assert "static" in output
    assert "00:11:22:33:44:55" in output


def test_reid_engine_dynamic_singleton(tmp_path) -> None:
    enriched = tmp_path / "scan_ENRICHED.csv"
    _write_test_enriched_csv(
        enriched,
        [
            {
                "timestamp_utc": "2026-01-01T00:00:00Z",
                "frame_type": "probe",
                "src_mac": "02:11:22:33:44:55",
                "rssi_dbm": -60,
                "gps_lat": 32.0,
                "gps_lon": 34.0,
                "match_found": True,
            }
        ],
    )

    from app.modules.reid.engine import run_reid

    result = run_reid(enriched, "wifi")

    assert result["dynamic_cluster_count"] == 1
    assert result["singleton_dynamic_count"] == 1


def test_reid_engine_dynamic_association(tmp_path) -> None:
    enriched = tmp_path / "scan_ENRICHED.csv"
    _write_test_enriched_csv(
        enriched,
        [
            {
                "timestamp_utc": "2026-01-01T00:00:00Z",
                "frame_type": "probe",
                "src_mac": "02:11:22:33:44:55",
                "rssi_dbm": -60,
                "gps_lat": 32.0,
                "gps_lon": 34.0,
                "match_found": True,
                "seq_ctl": 10,
                "ie_ids": "1,3,221",
                "ie_fingerprint": "fp",
                "frame_len": 120,
            },
            {
                "timestamp_utc": "2026-01-01T00:00:00Z",
                "frame_type": "probe",
                "src_mac": "02:11:22:aa:bb:cc",
                "rssi_dbm": -60,
                "gps_lat": 32.0,
                "gps_lon": 34.0,
                "match_found": True,
                "seq_ctl": 10,
                "ie_ids": "1,3,221",
                "ie_fingerprint": "fp",
                "frame_len": 120,
            },
        ],
    )

    from app.modules.reid.engine import run_reid

    result = run_reid(enriched, "wifi")

    assert result["dynamic_cluster_count"] == 1
    assert result["singleton_dynamic_count"] == 0


def test_reid_engine_uppercase_suffix(tmp_path) -> None:
    enriched = tmp_path / "scan_ENRICHED.csv"
    _write_test_enriched_csv(
        enriched,
        [
            {
                "timestamp_utc": "2026-01-01T00:00:00Z",
                "frame_type": "probe",
                "src_mac": "00:11:22:33:44:55",
                "rssi_dbm": -60,
                "gps_lat": 32.0,
                "gps_lon": 34.0,
                "match_found": True,
            }
        ],
    )

    from app.modules.reid.engine import run_reid

    result = run_reid(enriched, "wifi")

    assert result["reid_csv_path"].endswith("_REID.csv")


def test_reid_engine_output_strips_enriched_suffix(tmp_path) -> None:
    enriched = tmp_path / "scan_2026-01-19_11-20-58Z-test-circle2_enriched.csv"
    _write_test_enriched_csv(
        enriched,
        [
            {
                "timestamp_utc": "2026-01-01T00:00:00Z",
                "frame_type": "probe",
                "src_mac": "00:11:22:33:44:55",
                "rssi_dbm": -60,
                "gps_lat": 32.0,
                "gps_lon": 34.0,
                "match_found": True,
            }
        ],
    )

    from app.modules.reid.engine import run_reid

    result = run_reid(enriched, "wifi")

    assert Path(result["reid_csv_path"]).name == "scan_2026-01-19_11-20-58Z-test-circle2_REID.csv"
    assert (tmp_path / "scan_2026-01-19_11-20-58Z-test-circle2_REID.csv").exists()
    assert not (tmp_path / "scan_2026-01-19_11-20-58Z-test-circle2_enriched_REID.csv").exists()


def test_reid_api_404_unknown_session() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/sessions/bad-id/reid/run",
        json={"enriched_csv_filename": "scan_ENRICHED.csv"},
    )

    assert response.status_code == 404


def test_reid_api_422_not_enriched(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    folder = tmp_path / "scan_reid_test"
    folder.mkdir()
    (folder / "scan.csv").write_text("timestamp_utc,src_mac,rssi_dbm,gps_lat,gps_lon,match_found\n", encoding="utf-8")
    client = TestClient(create_app())
    session_id = client.post("/api/sessions", json={"folder_id": "scan_reid_test"}).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/reid/run",
        json={"enriched_csv_filename": "scan.csv"},
    )

    assert response.status_code == 422


def test_reid_api_200_returns_execution_id(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    folder = tmp_path / "scan_reid_test"
    folder.mkdir()
    _write_test_enriched_csv(
        folder / "scan_ENRICHED.csv",
        [
            {
                "timestamp_utc": "2026-01-01T00:00:00Z",
                "frame_type": "probe",
                "src_mac": "00:11:22:33:44:55",
                "rssi_dbm": -60,
                "gps_lat": 32.0,
                "gps_lon": 34.0,
                "match_found": True,
            }
        ],
    )
    client = TestClient(create_app())
    session_id = client.post("/api/sessions", json={"folder_id": "scan_reid_test"}).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/reid/run",
        json={"enriched_csv_filename": "scan_ENRICHED.csv"},
    )
    body = response.json()
    execution_response = client.get(f"/api/executions/{body['execution_id']}")

    assert response.status_code == 200
    assert "execution_id" in body
    assert execution_response.json()["status"] == "success"


def test_reid_api_400_path_traversal(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "scan_reid_test").mkdir()
    client = TestClient(create_app())
    session_id = client.post("/api/sessions", json={"folder_id": "scan_reid_test"}).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/reid/run",
        json={"enriched_csv_filename": "../outside_ENRICHED.csv"},
    )

    assert response.status_code == 400


def _write_test_reid_csv(path, rows: list[dict[str, object]]) -> None:
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
        import csv

        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _calibration_params() -> dict:
    return {"rssi_at_1m": -40.0, "path_loss_n": 2.0, "sigma": 6.0}


def test_localization_engine_auto_bounds(tmp_path) -> None:
    reid = tmp_path / "scan_REID.csv"
    _write_test_reid_csv(
        reid,
        [
            {"timestamp_utc": "2026-01-01T00:00:00Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -60, "gps_lat": 32.0, "gps_lon": 34.0, "cluster_id": "c1", "cluster_type": "static"},
            {"timestamp_utc": "2026-01-01T00:00:01Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -61, "gps_lat": 32.0009, "gps_lon": 34.0, "cluster_id": "c1", "cluster_type": "static"},
            {"timestamp_utc": "2026-01-01T00:00:02Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -62, "gps_lat": 32.0009, "gps_lon": 34.0011, "cluster_id": "c1", "cluster_type": "static"},
            {"timestamp_utc": "2026-01-01T00:00:03Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -63, "gps_lat": 32.0, "gps_lon": 34.0011, "cluster_id": "c1", "cluster_type": "static"},
        ],
    )

    from app.modules.localization.engine import run_localization

    result = run_localization(reid, _calibration_params(), grid_resolution_m=25)

    assert result["successful_clusters"] == 1
    assert result["bounds"]["lat_min"] < 32.0
    assert result["bounds"]["lat_max"] > 32.0009
    assert result["cluster_results"][0]["primary_peak"] is not None


def test_localization_engine_insufficient_samples(tmp_path) -> None:
    reid = tmp_path / "scan_REID.csv"
    _write_test_reid_csv(
        reid,
        [
            {"timestamp_utc": "2026-01-01T00:00:00Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -60, "gps_lat": 32.0, "gps_lon": 34.0, "cluster_id": "c1", "cluster_type": "static"},
            {"timestamp_utc": "2026-01-01T00:00:01Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -61, "gps_lat": 32.0001, "gps_lon": 34.0001, "cluster_id": "c1", "cluster_type": "static"},
        ],
    )

    from app.modules.localization.engine import run_localization

    with pytest.raises(ValueError, match="All clusters failed"):
        run_localization(reid, _calibration_params())


def test_localization_engine_multiple_clusters(tmp_path) -> None:
    reid = tmp_path / "scan_REID.csv"
    rows = []
    for cluster_id, base_lat in (("c1", 32.0), ("c2", 32.01)):
        for index in range(3):
            rows.append({"timestamp_utc": f"2026-01-01T00:00:0{index}Z", "frame_type": "probe", "src_mac": f"00:11:22:33:44:{index:02x}", "rssi_dbm": -60, "gps_lat": base_lat + index * 0.00001, "gps_lon": 34.0, "cluster_id": cluster_id, "cluster_type": "static"})
    _write_test_reid_csv(reid, rows)

    from app.modules.localization.engine import run_localization

    result = run_localization(reid, _calibration_params(), grid_resolution_m=50)

    assert result["total_clusters"] == 2
    assert result["successful_clusters"] == 2


def test_localization_engine_partial_failure(tmp_path) -> None:
    reid = tmp_path / "scan_REID.csv"
    rows = [
        {"timestamp_utc": "2026-01-01T00:00:00Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -60, "gps_lat": 32.0, "gps_lon": 34.0, "cluster_id": "c1", "cluster_type": "static"},
        {"timestamp_utc": "2026-01-01T00:00:01Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -61, "gps_lat": 32.0001, "gps_lon": 34.0, "cluster_id": "c1", "cluster_type": "static"},
        {"timestamp_utc": "2026-01-01T00:00:02Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -62, "gps_lat": 32.0002, "gps_lon": 34.0, "cluster_id": "c1", "cluster_type": "static"},
        {"timestamp_utc": "2026-01-01T00:00:03Z", "frame_type": "probe", "src_mac": "aa:bb:cc:dd:ee:ff", "rssi_dbm": -70, "gps_lat": 32.01, "gps_lon": 34.01, "cluster_id": "c2", "cluster_type": "static"},
        {"timestamp_utc": "2026-01-01T00:00:04Z", "frame_type": "probe", "src_mac": "aa:bb:cc:dd:ee:ff", "rssi_dbm": -71, "gps_lat": 32.011, "gps_lon": 34.01, "cluster_id": "c2", "cluster_type": "static"},
    ]
    _write_test_reid_csv(reid, rows)

    from app.modules.localization.engine import run_localization

    result = run_localization(reid, _calibration_params(), grid_resolution_m=50)

    assert result["total_clusters"] == 2
    assert result["successful_clusters"] == 1
    assert result["failed_clusters"] == 1
    c1 = next(c for c in result["cluster_results"] if c["cluster_id"] == "c1")
    c2 = next(c for c in result["cluster_results"] if c["cluster_id"] == "c2")
    assert c1["status"] == "success"
    assert c2["status"] == "failed"
    assert c2["failure_reason"] == "insufficient_samples"


def test_localization_engine_uppercase_csv(tmp_path) -> None:
    reid = tmp_path / "scan_reid.csv"
    _write_test_reid_csv(
        reid,
        [
            {"timestamp_utc": "2026-01-01T00:00:00Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -60, "gps_lat": 32.0, "gps_lon": 34.0, "cluster_id": "c1", "cluster_type": "static"},
            {"timestamp_utc": "2026-01-01T00:00:01Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -61, "gps_lat": 32.0001, "gps_lon": 34.0001, "cluster_id": "c1", "cluster_type": "static"},
            {"timestamp_utc": "2026-01-01T00:00:02Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -62, "gps_lat": 32.0002, "gps_lon": 34.0002, "cluster_id": "c1", "cluster_type": "static"},
        ],
    )

    from app.modules.localization.engine import run_localization

    assert run_localization(reid, _calibration_params())["successful_clusters"] == 1


def test_localization_api_404_unknown_session() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/sessions/bad-id/localization/run",
        json={"reid_csv_filename": "scan_REID.csv"},
    )

    assert response.status_code == 404


def test_localization_api_422_no_calibration(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    folder = tmp_path / "scan_loc_test"
    folder.mkdir()
    _write_test_reid_csv(folder / "scan_REID.csv", [])
    client = TestClient(create_app())
    session_id = client.post("/api/sessions", json={"folder_id": "scan_loc_test"}).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/localization/run",
        json={"reid_csv_filename": "scan_REID.csv"},
    )

    assert response.status_code == 422


def test_localization_api_422_not_reid(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    folder = tmp_path / "scan_loc_test"
    folder.mkdir()
    (folder / "scan.csv").write_text("timestamp_utc,src_mac,rssi_dbm,gps_lat,gps_lon,cluster_id,cluster_type\n", encoding="utf-8")
    client = TestClient(create_app())
    session_id = client.post("/api/sessions", json={"folder_id": "scan_loc_test"}).json()["session_id"]
    from app.modules.session_navigation.session_store import get_session
    get_session(session_id)["active_calibration"] = {"approved": True, "parameters": _calibration_params()}

    response = client.post(
        f"/api/sessions/{session_id}/localization/run",
        json={"reid_csv_filename": "scan.csv"},
    )

    assert response.status_code == 422


def test_localization_api_200_returns_execution_id(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    folder = tmp_path / "scan_loc_test"
    folder.mkdir()
    _write_test_reid_csv(
        folder / "scan_REID.csv",
        [
            {"timestamp_utc": "2026-01-01T00:00:00Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -60, "gps_lat": 32.0, "gps_lon": 34.0, "cluster_id": "c1", "cluster_type": "static"},
            {"timestamp_utc": "2026-01-01T00:00:01Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -61, "gps_lat": 32.0001, "gps_lon": 34.0001, "cluster_id": "c1", "cluster_type": "static"},
            {"timestamp_utc": "2026-01-01T00:00:02Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -62, "gps_lat": 32.0002, "gps_lon": 34.0002, "cluster_id": "c1", "cluster_type": "static"},
        ],
    )
    client = TestClient(create_app())
    session_id = client.post("/api/sessions", json={"folder_id": "scan_loc_test"}).json()["session_id"]
    from app.modules.session_navigation.session_store import get_session
    get_session(session_id)["active_calibration"] = {"approved": True, "parameters": _calibration_params()}

    response = client.post(
        f"/api/sessions/{session_id}/localization/run",
        json={"reid_csv_filename": "scan_REID.csv", "grid_resolution_m": 20},
    )
    body = response.json()
    execution_response = client.get(f"/api/executions/{body['execution_id']}")

    assert response.status_code == 200
    assert "execution_id" in body
    assert execution_response.json()["status"] == "success"


def test_localization_api_400_path_traversal(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "scan_loc_test").mkdir()
    client = TestClient(create_app())
    session_id = client.post("/api/sessions", json={"folder_id": "scan_loc_test"}).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/localization/run",
        json={"reid_csv_filename": "../outside_REID.csv"},
    )

    assert response.status_code == 400


def test_save_session_requires_localization(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "DATA"))
    monkeypatch.setenv("SAVED_SCANS_DIR", str(tmp_path / "Saved Scans"))
    folder = tmp_path / "DATA" / "scan_save_test"
    folder.mkdir(parents=True)
    client = TestClient(create_app())
    session_id = client.post("/api/sessions", json={"folder_id": "scan_save_test"}).json()["session_id"]

    response = client.post(f"/api/sessions/{session_id}/save")

    assert response.status_code == 422


def test_save_list_and_resume_session(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "DATA"
    saved_dir = tmp_path / "Saved Scans"
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("SAVED_SCANS_DIR", str(saved_dir))
    folder = data_dir / "scan_save_test"
    folder.mkdir(parents=True)
    reid_path = folder / "scan_REID.csv"
    _write_test_reid_csv(
        reid_path,
        [
            {"timestamp_utc": "2026-01-01T00:00:00Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -60, "gps_lat": 32.0, "gps_lon": 34.0, "cluster_id": "c1", "cluster_type": "static"},
            {"timestamp_utc": "2026-01-01T00:00:01Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -61, "gps_lat": 32.0001, "gps_lon": 34.0001, "cluster_id": "c1", "cluster_type": "static"},
            {"timestamp_utc": "2026-01-01T00:00:02Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -62, "gps_lat": 32.0002, "gps_lon": 34.0002, "cluster_id": "c1", "cluster_type": "static"},
        ],
    )
    client = TestClient(create_app())
    session_id = client.post("/api/sessions", json={"folder_id": "scan_save_test", "mode": "wifi"}).json()["session_id"]

    from app.modules.session_navigation.session_store import get_session

    session = get_session(session_id)
    session["active_calibration"] = {"approved": True, "parameters": _calibration_params()}
    session["active_reid_artifact"] = str(reid_path)
    session["active_localization"] = {"cluster_results": [{"cluster_id": "c1"}], "bounds": {"lat_min": 32, "lat_max": 33, "lon_min": 34, "lon_max": 35}}
    session["current_localization_result"] = session["active_localization"]

    save_response = client.post(f"/api/sessions/{session_id}/save")
    saved = save_response.json()
    list_response = client.get("/api/saved-sessions")
    resume_response = client.post(f"/api/saved-sessions/{saved['saved_id']}/resume")
    resumed = resume_response.json()

    assert save_response.status_code == 200
    assert (saved_dir / "scan_save_test" / saved["saved_id"] / "session_meta.json").exists()
    assert (saved_dir / "scan_save_test" / saved["saved_id"] / "calibration.json").exists()
    assert (saved_dir / "scan_save_test" / saved["saved_id"] / "localization.json").exists()
    assert (saved_dir / "scan_save_test" / saved["saved_id"] / "scan_REID.csv").exists()
    assert list_response.status_code == 200
    assert list_response.json()[0]["saved_id"] == saved["saved_id"]
    assert resume_response.status_code == 200
    assert resumed["folder_id"] == "scan_save_test"
    assert resumed["mode"] == "wifi"
    assert resumed["active_calibration"]["approved"] is True
    assert resumed["active_localization"]["cluster_results"][0]["cluster_id"] == "c1"
