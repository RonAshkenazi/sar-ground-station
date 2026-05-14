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


def test_pcap_parser_ie_fingerprint_uses_legacy_hex_format() -> None:
    from app.modules.enrichment.pcap_parser import _parse_information_elements

    data = (
        bytes([1, 2]) + bytes.fromhex("aabb")
        + bytes([50, 2]) + bytes.fromhex("ccdd")
        + bytes([3, 1]) + bytes.fromhex("99")
        + bytes([221, 3]) + bytes.fromhex("001122")
    )

    result = _parse_information_elements(data)

    assert result["ie_ids"] == "1,50,3,221"
    assert result["ie_fingerprint"] == "1:aabb;50:ccdd;221:001122"
    assert "|" not in result["ie_fingerprint"]
    assert "3:99" not in result["ie_fingerprint"]


def test_radiotap_linktype_handled(tmp_path) -> None:
    def mac_bytes(mac: str) -> bytes:
        return bytes(int(part, 16) for part in mac.split(":"))

    pcap_file = tmp_path / "radiotap.pcap"
    radiotap_header = bytes([0, 0]) + struct.pack("<H", 36) + bytes(32)
    frame_control = (0b00 << 2) | (8 << 4)
    dot11 = (
        frame_control.to_bytes(2, "little")
        + b"\x00\x00"
        + mac_bytes("ff:ff:ff:ff:ff:ff")
        + mac_bytes("20:b0:01:36:65:77")
        + mac_bytes("20:b0:01:36:65:77")
        + b"\x10\x00"
        + bytes(12)
        + bytes([1, 2])
        + bytes.fromhex("aabb")
    )
    payload = radiotap_header + dot11
    with pcap_file.open("wb") as file:
        file.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 127))
        file.write(struct.pack("<IIII", 1767225600, 0, len(payload), len(payload)))
        file.write(payload)

    from app.modules.enrichment.pcap_parser import parse_wifi_pcap

    frames = parse_wifi_pcap(pcap_file)

    assert len(frames) == 1
    assert frames[0]["src_mac"] == "20:b0:01:36:65:77"
    assert frames[0]["dst_mac"] == "ff:ff:ff:ff:ff:ff"
    assert frames[0]["ie_fingerprint"] == "1:aabb"


def test_beacon_ie_offset() -> None:
    def mac_bytes(mac: str) -> bytes:
        return bytes(int(part, 16) for part in mac.split(":"))

    frame_control = (0b00 << 2) | (8 << 4)
    payload = (
        frame_control.to_bytes(2, "little")
        + b"\x00\x00"
        + mac_bytes("ff:ff:ff:ff:ff:ff")
        + mac_bytes("20:b0:01:36:65:77")
        + mac_bytes("20:b0:01:36:65:77")
        + b"\x10\x00"
        + bytes(12)
        + bytes([1, 2])
        + bytes.fromhex("aabb")
    )

    from app.modules.enrichment.pcap_parser import LINKTYPE_IEEE802_11, _parse_payload

    frame = _parse_payload(payload, LINKTYPE_IEEE802_11)

    assert frame["ie_ids"] == "1"
    assert frame["ie_fingerprint"] == "1:aabb"


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


def test_singleton_becomes_noise_cluster(tmp_path) -> None:
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
    output = (tmp_path / "scan_REID.csv").read_text(encoding="utf-8")

    assert result["dynamic_cluster_count"] == 0
    assert result["noise_cluster_count"] == 1
    assert ",noise,noise," in output


def test_persistent_singleton_mac_is_not_noise(tmp_path) -> None:
    enriched = tmp_path / "scan_ENRICHED.csv"
    _write_test_enriched_csv(
        enriched,
        [
            {
                "timestamp_utc": str(1000.0 + index * 5),
                "frame_type": "probe",
                "src_mac": "82:aa:bb:cc:dd:ee",
                "rssi_dbm": -65,
                "gps_lat": 32.0,
                "gps_lon": 34.0,
                "match_found": True,
            }
            for index in range(10)
        ],
    )

    from app.modules.reid.engine import run_reid

    result = run_reid(enriched, "wifi")
    with (tmp_path / "scan_REID.csv").open(newline="", encoding="utf-8") as file:
        import csv

        output_rows = list(csv.DictReader(file))

    assert result["noise_cluster_count"] == 0
    assert result["dynamic_cluster_count"] == 1
    assert all(row["cluster_type"] == "dynamic" for row in output_rows)
    assert all(row["cluster_id"].isdigit() for row in output_rows)


def test_ephemeral_singleton_mac_is_noise(tmp_path) -> None:
    enriched = tmp_path / "scan_ENRICHED.csv"
    _write_test_enriched_csv(
        enriched,
        [
            {
                "timestamp_utc": "1000.0",
                "frame_type": "probe",
                "src_mac": "82:aa:bb:cc:dd:ee",
                "rssi_dbm": -65,
                "gps_lat": 32.0,
                "gps_lon": 34.0,
                "match_found": True,
            },
            {
                "timestamp_utc": "1001.0",
                "frame_type": "probe",
                "src_mac": "82:aa:bb:cc:dd:ee",
                "rssi_dbm": -66,
                "gps_lat": 32.0,
                "gps_lon": 34.0,
                "match_found": True,
            },
        ],
    )

    from app.modules.reid.engine import run_reid

    result = run_reid(enriched, "wifi")

    assert result["noise_cluster_count"] == 1
    assert result["dynamic_cluster_count"] == 0


def test_multi_mac_cluster_keeps_numeric_id(tmp_path) -> None:
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
                "ie_ids": "1,50,45,127,221",
                "ie_fingerprint": "1:aabb;50:ccdd;45:eeff;127:1122;221:3344",
                "frame_len": 120,
            },
            {
                "timestamp_utc": "2026-01-01T00:00:01Z",
                "frame_type": "probe",
                "src_mac": "02:11:22:aa:bb:cc",
                "rssi_dbm": -60,
                "gps_lat": 32.0,
                "gps_lon": 34.0,
                "match_found": True,
                "seq_ctl": 20,
                "ie_ids": "1,50,45,127,221",
                "ie_fingerprint": "1:aabb;50:ccdd;45:eeff;127:1122;221:3344",
                "frame_len": 120,
            },
        ],
    )

    from app.modules.reid.engine import run_reid

    result = run_reid(enriched, "wifi")

    assert result["dynamic_cluster_count"] == 1
    assert result["noise_cluster_count"] == 0
    with (tmp_path / "scan_REID.csv").open(newline="", encoding="utf-8") as file:
        import csv

        output_rows = list(csv.DictReader(file))
    assert all(row["confidence"] == "high" for row in output_rows)
    assert all(row["cluster_type"] == "dynamic" for row in output_rows)
    assert all(row["cluster_id"].isdigit() for row in output_rows)
    assert len({row["cluster_id"] for row in output_rows}) == 1


def test_reid_unique_dynamic_mac_count(tmp_path) -> None:
    """unique_dynamic_mac_count equals distinct MACs in non-noise clusters."""
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
                "ie_ids": "1,50,45,127,221",
                "ie_fingerprint": "1:aabb;50:ccdd;45:eeff;127:1122;221:3344",
                "frame_len": 120,
            },
            {
                "timestamp_utc": "2026-01-01T00:00:01Z",
                "frame_type": "probe",
                "src_mac": "02:11:22:aa:bb:cc",
                "rssi_dbm": -60,
                "gps_lat": 32.0,
                "gps_lon": 34.0,
                "match_found": True,
                "seq_ctl": 20,
                "ie_ids": "1,50,45,127,221",
                "ie_fingerprint": "1:aabb;50:ccdd;45:eeff;127:1122;221:3344",
                "frame_len": 120,
            },
            {
                "timestamp_utc": "2026-01-01T00:00:20Z",
                "frame_type": "probe",
                "src_mac": "82:aa:bb:cc:dd:ee",
                "rssi_dbm": -70,
                "gps_lat": 32.0,
                "gps_lon": 34.0,
                "match_found": True,
            },
        ],
    )

    from app.modules.reid.engine import run_reid

    result = run_reid(enriched, "wifi")

    assert result["dynamic_cluster_count"] == 1
    assert result["noise_cluster_count"] == 1
    assert result["unique_dynamic_mac_count"] == 2


def test_reid_cluster_confidence_in_result(tmp_path) -> None:
    """cluster_confidence maps non-noise dynamic cluster IDs to tier strings."""
    from app.modules.reid.engine import run_reid

    csv_path = tmp_path / "scan_ENRICHED.csv"
    rows = []
    base_time = 1_700_000_000.0
    for i in range(6):
        rows.append({
            "timestamp_utc": str(base_time + i),
            "src_mac": "02:aa:bb:cc:dd:01",
            "rssi_dbm": "-60",
            "gps_lat": "32.0",
            "gps_lon": "34.0",
            "frame_type": "probe",
        })
    for i in range(6):
        rows.append({
            "timestamp_utc": str(base_time + 100 + i),
            "src_mac": "02:aa:bb:cc:dd:02",
            "rssi_dbm": "-65",
            "gps_lat": "32.001",
            "gps_lon": "34.001",
            "frame_type": "probe",
        })
    import csv as csv_mod
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv_mod.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    result = run_reid(csv_path, protocol="wifi")

    assert "cluster_confidence" in result
    cc = result["cluster_confidence"]
    for cluster_id, tier in cc.items():
        assert tier in ("high", "medium", "low"), f"Unexpected tier {tier!r} for cluster {cluster_id}"
        assert cluster_id != "noise", "Noise clusters must not appear in cluster_confidence"


def test_probe_requests_only_filters_rows(tmp_path) -> None:
    enriched = tmp_path / "scan_ENRICHED.csv"
    _write_test_enriched_csv(
        enriched,
        [
            {
                "timestamp_utc": "2026-01-01T00:00:00Z",
                "frame_type": "probe-req",
                "src_mac": "02:11:22:33:44:55",
                "rssi_dbm": -60,
                "gps_lat": 32.0,
                "gps_lon": 34.0,
                "match_found": True,
            },
            {
                "timestamp_utc": "2026-01-01T00:00:01Z",
                "frame_type": "beacon",
                "src_mac": "02:11:22:aa:bb:cc",
                "rssi_dbm": -61,
                "gps_lat": 32.0,
                "gps_lon": 34.0,
                "match_found": True,
            },
        ],
    )

    from app.modules.reid.engine import run_reid

    result = run_reid(enriched, "wifi", probe_requests_only=True)
    output = (tmp_path / "scan_REID.csv").read_text(encoding="utf-8")

    assert result["total_rows"] == 1
    assert result["noise_cluster_count"] == 1
    assert "02:11:22:33:44:55" in output
    assert "02:11:22:aa:bb:cc" not in output


def test_reid_request_exposes_tunable_defaults() -> None:
    from app.api.reid import ReIdRunRequest

    request = ReIdRunRequest(enriched_csv_filename="scan_ENRICHED.csv")

    assert request.association_threshold == 0.8
    assert request.seq_gap_max == 64
    assert request.time_gap_max_sec == 30.0
    assert request.burst_window_sec == 60.0
    assert request.probe_requests_only is False


def test_all_key_constants() -> None:
    from app.modules.calibration.engine import _FIT_WARNING_MIN_INLIER_RATIO, _FIT_WARNING_MIN_SAMPLES
    from app.modules.localization.engine import _LOC_06_GRID_RESOLUTION_M, _LOC_UNCERTAINTY_ALPHA, _LOC_UNCERTAINTY_PARTICIPATION_FLOOR
    from app.modules.reid.engine import _REID_MIN_ROWS_SINGLETON

    assert _REID_MIN_ROWS_SINGLETON == 5
    assert _LOC_06_GRID_RESOLUTION_M == 2.0
    assert _LOC_UNCERTAINTY_PARTICIPATION_FLOOR == 0.50
    assert _LOC_UNCERTAINTY_ALPHA == 2.0
    assert _FIT_WARNING_MIN_SAMPLES == 10
    assert _FIT_WARNING_MIN_INLIER_RATIO == 0.70


def test_reid_bleach_scoring_helpers() -> None:
    from app.modules.reid.engine import (
        _association_score,
        _ie_fingerprint_score,
        _seq_continuity_bonus,
        _ssid_bonus,
    )

    fingerprint = "0:74657374;1:aabb;50:ccdd;45:eeff;127:1122;221:3344"
    assert _ie_fingerprint_score(fingerprint, fingerprint) == 1.0
    assert _seq_continuity_bonus(4090, 10) == 1.0
    assert _seq_continuity_bonus(10, 100) == 0.0
    assert _ssid_bonus(fingerprint, fingerprint) == 1.0

    left = {"rows": [{"timestamp_utc": "2026-01-01T00:00:00Z", "rssi_dbm": -50, "seq_ctl": 10, "ie_fingerprint": fingerprint, "frame_len": 120}]}
    right = {"rows": [{"timestamp_utc": "2026-01-01T00:00:01Z", "rssi_dbm": -51, "seq_ctl": 20, "ie_fingerprint": fingerprint, "frame_len": 120}]}

    assert _association_score(left, right) == pytest.approx(1.10)


def test_reid_rssi_sanity_rejects_impossible_pair() -> None:
    from app.modules.reid.engine import _association_score

    fingerprint = "1:aabb;50:ccdd;45:eeff;127:1122;221:3344"
    left = {"rows": [{"timestamp_utc": "2026-01-01T00:00:00Z", "rssi_dbm": -20, "seq_ctl": 10, "ie_fingerprint": fingerprint, "frame_len": 120}]}
    right = {"rows": [{"timestamp_utc": "2026-01-01T00:00:01Z", "rssi_dbm": -80, "seq_ctl": 20, "ie_fingerprint": fingerprint, "frame_len": 120}]}

    assert _association_score(left, right) == 0.0


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


def test_localization_engine_ransac_removes_outlier(tmp_path) -> None:
    reid = tmp_path / "scan_REID.csv"
    rows = [
        {"timestamp_utc": "2026-01-01T00:00:00Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -48, "gps_lat": 32.0, "gps_lon": 34.0, "cluster_id": "c1", "cluster_type": "static"},
        {"timestamp_utc": "2026-01-01T00:00:01Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -49, "gps_lat": 32.0001, "gps_lon": 34.0, "cluster_id": "c1", "cluster_type": "static"},
        {"timestamp_utc": "2026-01-01T00:00:02Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -50, "gps_lat": 32.0, "gps_lon": 34.0001, "cluster_id": "c1", "cluster_type": "static"},
        {"timestamp_utc": "2026-01-01T00:00:03Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -5, "gps_lat": 32.01, "gps_lon": 34.01, "cluster_id": "c1", "cluster_type": "static"},
    ]
    _write_test_reid_csv(reid, rows)

    from app.modules.localization.engine import run_localization

    result = run_localization(reid, _calibration_params(), grid_resolution_m=20)

    assert result["cluster_results"][0]["sample_count"] == 3
    assert any("RANSAC removed 1 outlier" in warning for warning in result["warnings"])


def test_localization_engine_dynamic_sigma_and_confidence_cutoff_constants() -> None:
    from app.modules.localization.engine import _LOC_07_DYNAMIC_SIGMA_ALPHA, _LOC_08_CONFIDENCE_CUTOFF

    assert _LOC_07_DYNAMIC_SIGMA_ALPHA == 0.05
    assert _LOC_08_CONFIDENCE_CUTOFF == 0.50


def test_localization_confidence_cutoff_filters_peaks(tmp_path) -> None:
    reid = tmp_path / "scan_REID.csv"
    _write_test_reid_csv(
        reid,
        [
            {"timestamp_utc": "2026-01-01T00:00:00Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -60, "gps_lat": 32.0, "gps_lon": 34.0, "cluster_id": "c1", "cluster_type": "static"},
            {"timestamp_utc": "2026-01-01T00:00:01Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -60, "gps_lat": 32.001, "gps_lon": 34.0, "cluster_id": "c1", "cluster_type": "static"},
            {"timestamp_utc": "2026-01-01T00:00:02Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -60, "gps_lat": 32.0, "gps_lon": 34.001, "cluster_id": "c1", "cluster_type": "static"},
            {"timestamp_utc": "2026-01-01T00:00:03Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -60, "gps_lat": 32.001, "gps_lon": 34.001, "cluster_id": "c1", "cluster_type": "static"},
        ],
    )

    from app.modules.localization.engine import run_localization

    low_cutoff = run_localization(reid, _calibration_params(), grid_resolution_m=10, confidence_cutoff=0.0)
    high_cutoff = run_localization(reid, _calibration_params(), grid_resolution_m=10, confidence_cutoff=1.0)

    assert len(low_cutoff["cluster_results"][0]["candidate_peaks"]) > len(high_cutoff["cluster_results"][0]["candidate_peaks"])


def test_localization_dynamic_sigma_increases_with_distance(tmp_path) -> None:
    reid = tmp_path / "scan_REID.csv"
    _write_test_reid_csv(
        reid,
        [
            {"timestamp_utc": "2026-01-01T00:00:00Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -60, "gps_lat": 32.0, "gps_lon": 34.0, "cluster_id": "c1", "cluster_type": "static"},
            {"timestamp_utc": "2026-01-01T00:00:01Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -60, "gps_lat": 32.001, "gps_lon": 34.0, "cluster_id": "c1", "cluster_type": "static"},
            {"timestamp_utc": "2026-01-01T00:00:02Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -60, "gps_lat": 32.0, "gps_lon": 34.001, "cluster_id": "c1", "cluster_type": "static"},
            {"timestamp_utc": "2026-01-01T00:00:03Z", "frame_type": "probe", "src_mac": "00:11:22:33:44:55", "rssi_dbm": -60, "gps_lat": 32.001, "gps_lon": 34.001, "cluster_id": "c1", "cluster_type": "static"},
        ],
    )

    from app.modules.localization.engine import run_localization

    fixed_sigma = run_localization(reid, _calibration_params(), grid_resolution_m=10, dynamic_sigma_alpha=0.0)
    dynamic_sigma = run_localization(reid, _calibration_params(), grid_resolution_m=10, dynamic_sigma_alpha=0.1)

    assert fixed_sigma["cluster_results"][0]["grid_cells"] != dynamic_sigma["cluster_results"][0]["grid_cells"]


def test_localization_request_exposes_tunable_defaults() -> None:
    from app.api.localization import LocalizationRunRequest

    request = LocalizationRunRequest(reid_csv_filename="scan_REID.csv")

    from app.modules.localization.engine import _LOC_06_GRID_RESOLUTION_M

    assert _LOC_06_GRID_RESOLUTION_M == 2.0
    assert request.dynamic_sigma_alpha == 0.05
    assert request.confidence_cutoff == 0.50
    assert request.uncertainty_participation_floor == 0.50
    assert request.uncertainty_alpha == 2.0


def test_uncertainty_region_weighted_spread_is_tight_for_peaked_posterior() -> None:
    from app.modules.localization.engine import _uncertainty_region

    cells = [(i * 0.000018, j * 0.000018) for i in range(-20, 20) for j in range(-20, 20)]
    peak = {"lat": 0.0, "lon": 0.0, "value": 1.0}
    posterior = []
    for lat, lon in cells:
        cell_dist = ((lat / 0.000018) ** 2 + (lon / 0.000018) ** 2) ** 0.5
        posterior.append(max(0.0, 1.0 - cell_dist / 5.0))

    region = _uncertainty_region(peak, cells, posterior, 2.0, participation_floor=0.05, alpha=2.0)

    assert region["radius_m"] < 20.0, f"Radius too large for peaked posterior: {region['radius_m']}m"
    assert region["radius_m"] >= 2.0


def test_uncertainty_region_all_below_floor_returns_grid_resolution() -> None:
    from app.modules.localization.engine import _uncertainty_region

    cells = [(i * 0.000018, j * 0.000018) for i in range(-5, 5) for j in range(-5, 5)]
    peak = {"lat": 0.0, "lon": 0.0, "value": 1.0}
    # All posteriors below participation_floor → total_w == 0 → fall back to grid resolution
    posterior = [0.02] * len(cells)

    region = _uncertainty_region(peak, cells, posterior, 5.0, participation_floor=0.05, alpha=2.0)

    assert region["radius_m"] == 5.0


def test_uncertainty_region_uses_peak_local_high_posterior_component() -> None:
    from app.modules.localization.engine import _uncertainty_region

    cells = [(0.0, j * 0.000018) for j in range(10)]
    posterior = [0.95, 0.94, 0.93, 0.1, 0.1, 0.1, 0.92, 0.91, 0.1, 0.1]
    primary_peak = {"lat": cells[0][0], "lon": cells[0][1], "value": posterior[0]}
    secondary_peak = {"lat": cells[6][0], "lon": cells[6][1], "value": posterior[6]}

    primary_region = _uncertainty_region(primary_peak, cells, posterior, 2.0, participation_floor=0.9, alpha=2.0, shape=(1, 10))
    secondary_region = _uncertainty_region(
        secondary_peak,
        cells,
        posterior,
        2.0,
        participation_floor=0.9,
        alpha=2.0,
        shape=(1, 10),
    )

    assert primary_region["radius_m"] < 6.0
    assert secondary_region["radius_m"] < 4.0


def test_uncertainty_region_below_floor_peak_does_not_use_other_peak_cells() -> None:
    from app.modules.localization.engine import _uncertainty_region

    cells = [(0.0, j * 0.000018) for j in range(10)]
    posterior = [1.0, 0.1, 0.1, 0.1, 0.1, 0.1, 0.84, 0.1, 0.1, 0.1]
    below_floor_peak = {"lat": cells[6][0], "lon": cells[6][1], "value": posterior[6]}

    region = _uncertainty_region(below_floor_peak, cells, posterior, 2.0, participation_floor=0.9, alpha=2.0, shape=(1, 10))

    assert region["radius_m"] == 2.0


def test_noise_cluster_not_localized(tmp_path) -> None:
    reid_csv = tmp_path / "test_REID.csv"
    _write_test_reid_csv(
        reid_csv,
        [
            *[
                {
                    "timestamp_utc": str(1000 + index),
                    "frame_type": "probe",
                    "src_mac": f"02:00:00:00:00:0{index}",
                    "rssi_dbm": -65,
                    "gps_lat": 32.0 + index * 0.001,
                    "gps_lon": 34.0 + index * 0.001,
                    "cluster_id": "noise",
                    "cluster_type": "noise",
                }
                for index in range(5)
            ],
            *[
                {
                    "timestamp_utc": str(2000 + index),
                    "frame_type": "probe",
                    "src_mac": "02:11:22:33:44:55",
                    "rssi_dbm": -60,
                    "gps_lat": 32.005 + index * 0.00001,
                    "gps_lon": 34.005 + index * 0.00001,
                    "cluster_id": "1",
                    "cluster_type": "dynamic",
                }
                for index in range(4)
            ],
        ],
    )

    from app.modules.localization.engine import run_localization

    result = run_localization(reid_csv, {"rssi_at_1m": -40.0, "path_loss_n": 3.0, "sigma": 6.0})
    cluster_ids = [cluster["cluster_id"] for cluster in result["cluster_results"]]

    assert "noise" not in cluster_ids
    assert "1" in cluster_ids
    assert any("noise" in warning.lower() for warning in result["warnings"])


def test_evaluate_single_match() -> None:
    from app.modules.result_analysis.engine import evaluate

    preds = [{"cluster_id": "c1", "lat": 0.0, "lon": 0.0, "radius_m": 12.0, "cluster_type": "dynamic", "num_samples": 5}]
    gts = [{"gt_id": "g1", "lat": 0.0, "lon": 0.0001, "label": None}]
    result = evaluate(preds, gts)

    assert len(result["matches"]) == 1
    assert result["matches"][0]["primary_cluster_id"] == "c1"
    assert result["matches"][0]["association_status"] == "clear_match"
    assert result["false_positives"] == []
    assert result["false_negatives"] == []
    assert "ratio_gate" in result["eval_params"]
    assert result["ambiguous_gts"] == []
    assert result["radius_reliability_note"]


def test_evaluate_false_negative_when_gt_too_far() -> None:
    from app.modules.result_analysis.engine import evaluate

    preds = [{"cluster_id": "c1", "lat": 0.0, "lon": 0.0, "radius_m": 5.0, "cluster_type": "dynamic", "num_samples": 5}]
    gts = [{"gt_id": "g1", "lat": 1.0, "lon": 1.0, "label": None}]
    result = evaluate(preds, gts)

    assert result["matches"] == []
    assert len(result["false_positives"]) == 1
    assert len(result["false_negatives"]) == 1
    assert result["ambiguous_gts"] == []


def test_evaluate_pack_produces_ambiguous_gt() -> None:
    from app.modules.result_analysis.engine import evaluate

    preds = [
        {"cluster_id": "c1", "lat": 0.0, "lon": 0.00002, "radius_m": 10.0, "cluster_type": "dynamic", "num_samples": 5},
        {"cluster_id": "c2", "lat": 0.0, "lon": 0.00003, "radius_m": 10.0, "cluster_type": "dynamic", "num_samples": 5},
    ]
    gts = [{"gt_id": "g1", "lat": 0.0, "lon": 0.0, "label": None}]
    result = evaluate(preds, gts)

    assert result["matches"] == []
    assert len(result["ambiguous_gts"]) == 1
    assert result["ambiguous_gts"][0]["gt_id"] == "g1"
    assert "c1" in result["ambiguous_gts"][0]["competing_cluster_ids"]
    assert "c2" in result["ambiguous_gts"][0]["competing_cluster_ids"]
    assert result["false_negatives"] == []


def test_evaluate_over_split() -> None:
    from app.modules.result_analysis.engine import evaluate

    preds = [
        {"cluster_id": "c1", "lat": 0.0, "lon": 0.00001, "radius_m": 10.0, "cluster_type": "dynamic", "num_samples": 5},
        {"cluster_id": "c2", "lat": 0.0, "lon": 0.00002, "radius_m": 10.0, "cluster_type": "dynamic", "num_samples": 5},
    ]
    gts = [{"gt_id": "g1", "lat": 0.0, "lon": 0.0, "label": "Device A"}]
    result = evaluate(preds, gts)

    assert len(result["matches"]) == 1
    assert len(result["false_positives"]) == 1
    assert len(result["duplicates"]) >= 1
    assert result["metrics"]["count_error"] == 1


def test_evaluate_dominant_match_sets_dominance_margin() -> None:
    from app.modules.result_analysis.engine import evaluate

    preds = [
        {"cluster_id": "c1", "lat": 0.0, "lon": 0.000009, "radius_m": 5.0, "cluster_type": "dynamic", "num_samples": 5},
        {"cluster_id": "c2", "lat": 0.0, "lon": 0.001, "radius_m": 5.0, "cluster_type": "dynamic", "num_samples": 5},
    ]
    gts = [{"gt_id": "g1", "lat": 0.0, "lon": 0.0, "label": None}]
    result = evaluate(preds, gts)

    assert len(result["matches"]) == 1
    assert result["matches"][0]["primary_cluster_id"] == "c1"
    assert result["matches"][0]["association_status"] == "clear_match"
    assert result["matches"][0]["dominance_margin"] is not None
    assert result["matches"][0]["dominance_margin"] >= 2.0
    assert result["ambiguous_gts"] == []


def test_evaluate_three_close_clusters_produces_ambiguous_gt() -> None:
    from app.modules.result_analysis.engine import evaluate

    preds = [
        {"cluster_id": "c1", "lat": 0.0, "lon": 0.000045, "radius_m": 20.0, "cluster_type": "dynamic", "num_samples": 5},
        {"cluster_id": "c2", "lat": 0.0, "lon": 0.000054, "radius_m": 20.0, "cluster_type": "dynamic", "num_samples": 5},
        {"cluster_id": "c3", "lat": 0.0, "lon": 0.000063, "radius_m": 20.0, "cluster_type": "dynamic", "num_samples": 5},
    ]
    gts = [{"gt_id": "g1", "lat": 0.0, "lon": 0.0, "label": "Person A"}]
    result = evaluate(preds, gts)

    assert result["matches"] == []
    assert len(result["ambiguous_gts"]) == 1
    assert result["ambiguous_gts"][0]["nearest_cluster_id"] == "c1"
    assert len(result["ambiguous_gts"][0]["competing_cluster_ids"]) >= 2


def test_evaluate_gt_beyond_max_match_dist_is_fn_not_ambiguous() -> None:
    from app.modules.result_analysis.engine import evaluate

    preds = [{"cluster_id": "c1", "lat": 0.0, "lon": 0.0, "radius_m": 5.0, "cluster_type": "dynamic", "num_samples": 5}]
    gts = [{"gt_id": "g1", "lat": 1.0, "lon": 1.0, "label": None}]
    result = evaluate(preds, gts)

    assert result["matches"] == []
    assert result["ambiguous_gts"] == []
    assert len(result["false_negatives"]) == 1


def test_evaluate_custom_ratio_gate() -> None:
    from app.modules.result_analysis.engine import evaluate

    preds = [
        {"cluster_id": "c1", "lat": 0.0, "lon": 0.00002, "radius_m": 10.0, "cluster_type": "dynamic", "num_samples": 5},
        {"cluster_id": "c2", "lat": 0.0, "lon": 0.00003, "radius_m": 10.0, "cluster_type": "dynamic", "num_samples": 5},
    ]
    gts = [{"gt_id": "g1", "lat": 0.0, "lon": 0.0, "label": None}]

    result_strict = evaluate(preds, gts, ratio_gate=2.0)
    assert result_strict["matches"] == []
    assert len(result_strict["ambiguous_gts"]) == 1

    result_loose = evaluate(preds, gts, ratio_gate=1.3)
    assert len(result_loose["matches"]) == 1
    assert result_loose["ambiguous_gts"] == []


def test_evaluate_empty_inputs() -> None:
    from app.modules.result_analysis.engine import evaluate

    result = evaluate([], [])

    assert result["matches"] == []
    assert result["metrics"]["recall"] == 0.0


def test_gt_store_add_delete() -> None:
    from app.modules.result_analysis.gt_store import add_gt_point, clear_gt_points, delete_gt_point, get_gt_points

    clear_gt_points("test_session_ra")
    point = add_gt_point("test_session_ra", 32.0, 34.0, "Device A")
    assert point["gt_id"] is not None
    assert len(get_gt_points("test_session_ra")) == 1
    assert delete_gt_point("test_session_ra", point["gt_id"])
    assert get_gt_points("test_session_ra") == []


def test_extract_predictions_from_loc_result() -> None:
    from app.modules.result_analysis.engine import extract_predictions_from_localization_result

    loc = {
        "cluster_results": [
            {
                "cluster_id": "c1",
                "cluster_type": "dynamic",
                "status": "success",
                "primary_peak": {"lat": 1.0, "lon": 2.0, "value": 0.9},
                "uncertainty_regions": [{"center_lat": 1.0, "center_lon": 2.0, "radius_m": 8.5}],
                "sample_count": 12,
            },
            {
                "cluster_id": "c2",
                "cluster_type": "static",
                "status": "failed",
                "primary_peak": None,
                "uncertainty_regions": [],
                "sample_count": 0,
            },
        ]
    }

    preds = extract_predictions_from_localization_result(loc)

    assert len(preds) == 1
    assert preds[0]["cluster_id"] == "c1"
    assert preds[0]["radius_m"] == 8.5


def test_result_analysis_api_evaluate(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "DATA"))
    folder = tmp_path / "DATA" / "scan_ra_test"
    folder.mkdir(parents=True)
    client = TestClient(create_app())
    session_id = client.post("/api/sessions", json={"folder_id": "scan_ra_test"}).json()["session_id"]

    from app.modules.session_navigation.session_store import get_session

    session = get_session(session_id)
    session["current_localization_result"] = {
        "cluster_results": [
            {
                "cluster_id": "c1",
                "cluster_type": "dynamic",
                "status": "success",
                "primary_peak": {"lat": 32.0, "lon": 34.0, "value": 0.9},
                "uncertainty_regions": [{"center_lat": 32.0, "center_lon": 34.0, "radius_m": 20.0}],
                "sample_count": 5,
            }
        ]
    }

    empty_response = client.post(f"/api/sessions/{session_id}/result-analysis/evaluate", json={})
    add_response = client.post(
        f"/api/sessions/{session_id}/result-analysis/ground-truth",
        json={"lat": 32.0, "lon": 34.0, "label": "Device A"},
    )
    eval_response = client.post(f"/api/sessions/{session_id}/result-analysis/evaluate", json={})
    state_response = client.get(f"/api/sessions/{session_id}/result-analysis")

    assert empty_response.status_code == 422
    assert add_response.status_code == 200
    assert eval_response.status_code == 200
    assert eval_response.json()["matches"][0]["primary_cluster_id"] == "c1"
    assert state_response.json()["last_evaluation"]["n_gt"] == 1


def test_rerun_reid_stage_accepted(tmp_path, monkeypatch) -> None:
    """Rerun endpoint accepts stage='reid' without 422."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    folder = tmp_path / "scan_ra_reid_test"
    folder.mkdir()
    enriched = folder / "scan_ENRICHED.csv"
    _write_test_enriched_csv(
        enriched,
        [
            {
                "timestamp_utc": f"2026-01-01T00:00:0{index}Z",
                "frame_type": "probe",
                "src_mac": "00:11:22:33:44:55",
                "rssi_dbm": -60 - index,
                "gps_lat": 32.0 + index * 0.0001,
                "gps_lon": 34.0 + index * 0.0001,
                "match_found": True,
            }
            for index in range(5)
        ],
    )
    client = TestClient(create_app())
    session_id = client.post("/api/sessions", json={"folder_id": "scan_ra_reid_test"}).json()["session_id"]

    from app.modules.session_navigation.session_store import get_session

    session = get_session(session_id)
    session["active_enriched_artifact"] = str(enriched)
    session["active_calibration"] = {"approved": True, "parameters": _calibration_params()}

    response = client.post(
        f"/api/sessions/{session_id}/result-analysis/rerun",
        json={"stage": "reid", "reid_params": {}, "localization_params": {"grid_resolution_m": 20}},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert "execution_id" in response.json()
    execution_response = client.get(f"/api/executions/{response.json()['execution_id']}")
    assert execution_response.json()["status"] == "success"


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
