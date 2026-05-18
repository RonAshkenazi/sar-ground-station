"""
Global configuration for the airunit Wi-Fi + GPS sniffer + guidance sender.
Single dongle as monitor on wlan1. Optional channel hopping.
"""

import os
from pathlib import Path

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE_PREFIX = "scan_"

os.makedirs(LOG_DIR, exist_ok=True)

# --- Wi-Fi sniffer interface ---
WIFI_MONITOR_INTERFACE = "wlan1"

# Channel hopping controls
HOP_ENABLED = False
HOP_CHANNELS = [1, 6, 11]
HOP_INTERVAL_SEC = 0.5
HOP_BASE_CHANNEL = 1

# --- BLE sniffer interface ---
BLE_HCI_INTERFACE = "hci0"

# --- GPS settings ---
GPS_SERIAL_DEVICE = "/dev/ttyACM0"
GPS_BAUDRATE = 9600
MAX_GPS_AGE_SEC = 10.0

# --- Heartbeat (no-signal) logging ---
HEARTBEAT_ENABLED = True
HEARTBEAT_INTERVAL_SEC = 2.0

# --- CSV format ---
CSV_HEADER = (
    "timestamp_utc,frame_type,src_mac,dst_mac,bssid,ssid,rssi_dbm,"
    "channel,freq_mhz,gps_lat,gps_lon,gps_alt_m,gps_fix,gps_num_sats,"
    "gps_hdop,gps_age_ms"
)
FIELDNAMES = [f.strip() for f in CSV_HEADER.split(",") if f.strip()]

# --- BLE CSV format ---
BLE_CSV_HEADER = (
    "timestamp_utc,event_type,address,address_type,rssi_dbm,company_id,"
    "company_name,adv_data_hex,flags,tx_power,gps_lat,gps_lon,gps_alt_m,"
    "gps_fix,gps_num_sats,gps_hdop,gps_age_ms"
)
BLE_FIELDNAMES = [f.strip() for f in BLE_CSV_HEADER.split(",") if f.strip()]

# ─── Guidance Sender ──────────────────────────────────────────────────────────

# Ground Station URL — loaded from network_config.json at runtime; this default
# is used only if network_config.json is absent.
GROUND_STATION_URL = "http://192.168.1.100:8000"

# How often to send each packet type
GUIDANCE_POSE_INTERVAL_SEC = 0.5       # 2 Hz
GUIDANCE_EVIDENCE_INTERVAL_SEC = 2.0   # every 2 seconds
GUIDANCE_HEALTH_INTERVAL_SEC = 10.0    # every 10 seconds

# HTTP POST timeout for each guidance packet
GUIDANCE_HTTP_TIMEOUT_SEC = 2.0

# Evidence aggregation: frames with RSSI above this threshold count as "strong"
GUIDANCE_STRONG_RSSI_THRESHOLD_DBM = -70

# Number of most recent CSV rows to look back when computing evidence stats.
# At ~10 frames/sec and 2s windows, 60 is generous.
GUIDANCE_EVIDENCE_LOOKBACK_ROWS = 60
