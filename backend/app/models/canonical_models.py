from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class ScanRecord(BaseModel):
    timestamp_utc: str
    frame_type: str
    src_mac: str
    rssi_dbm: float
    gps_lat: float
    gps_lon: float
    dst_mac: Optional[str] = None
    bssid: Optional[str] = None
    ssid: Optional[str] = None
    channel: Optional[int] = None
    freq_mhz: Optional[float] = None
    gps_alt_m: Optional[float] = None
    gps_fix: Optional[Union[str, int]] = None
    gps_num_sats: Optional[int] = None
    gps_hdop: Optional[float] = None
    gps_age_ms: Optional[float] = None


class EnrichedScanRecord(ScanRecord):
    src_vendor: Optional[str] = None
    dst_mac_pcap: Optional[str] = None
    bssid_pcap: Optional[str] = None
    seq_ctl: Optional[Union[float, str]] = None
    frame_len: Optional[float] = None
    ie_ids: Optional[str] = None
    ie_fingerprint: Optional[str] = None
    ie_vendor_ouis: Optional[str] = None
    match_found: Optional[bool] = None
    match_delta_ms: Optional[float] = None
    match_score: Optional[float] = None
    match_method: Optional[str] = None
    ble_event_type: Optional[str] = None
    ble_mfr_data: Optional[str] = None
    ble_service_uuids: Optional[str] = None
    ble_local_name: Optional[str] = None
    ble_tx_power_dbm: Optional[float] = None
    ble_flags: Optional[str] = None


class ReIDRecord(EnrichedScanRecord):
    model_config = ConfigDict(populate_by_name=True)

    cluster_id: Union[str, int]
    cluster_type: Literal["static", "dynamic"]
    match_delta_ms_internal: Optional[float] = Field(
        default=None,
        alias="_match_delta_ms",
    )
    dst_vendor_pcap: Optional[str] = None
    bssid_vendor_pcap: Optional[str] = None
    seq_num: Optional[float] = None


class SessionCalibration(BaseModel):
    scan_folder_id: str
    parameter_source: Literal["derived", "fallback"]
    parameters: dict
    approved: bool
    calibration_csv_file: Optional[str] = None
    calibration_mac_address: Optional[str] = None
    parameter_set_name: Optional[str] = None
    # TODO: TBD per spec Part B - fit warning thresholds remain unapproved.


class SavedSessionState(BaseModel):
    scan_folder_id: str
    mode: str
    saved_artifacts: Union[dict, list]
    saved_at_utc: str
    selected_calibration_csv: Optional[str] = None
    selected_calibration_mac: Optional[str] = None
    session_calibration: Optional[dict] = None
    selected_scan_csv: Optional[str] = None
    temp_enriched_csv_path: Optional[str] = None
    temp_reid_csv_path: Optional[str] = None
    computed_localization_result_path: Optional[str] = None
    localization_parameters: Optional[dict] = None
    view_state: Optional[dict] = None
    final_analysis_parameters: Optional[dict] = None
    ground_truth_state: Optional[dict] = None
