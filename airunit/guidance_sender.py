import csv
import logging
import threading
import time
from pathlib import Path
from typing import Optional

import requests

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

import config
from gps_service import start_gps

logger = logging.getLogger("guidance_sender")


def _now_ms() -> int:
    return int(time.time() * 1000)


def _read_cpu_temp() -> Optional[float]:
    """Read CPU temperature from sysfs. Returns None on non-Pi or missing file."""
    try:
        temp_raw = Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()
        return float(temp_raw) / 1000.0
    except Exception:
        return None


def _percentile_95(values: list) -> float:
    """Return the 95th percentile of a list of floats."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = min(int(len(sorted_vals) * 0.95), len(sorted_vals) - 1)
    return sorted_vals[idx]


class GuidanceSender:
    """Background service that sends pose, evidence, and health packets to the Ground Station."""

    def __init__(self, ground_station_url: str, scan_manager):
        self._gs_url = ground_station_url.rstrip("/")
        self._scan_manager = scan_manager
        self._gps_state, self._gps_stop, self._gps_thread = start_gps()
        self._seq = 0
        self._packets_sent = 0
        self._dropped_msgs = 0
        self._last_error: Optional[str] = None
        self._stop_event = threading.Event()
        self._threads: list = []

    def start(self) -> None:
        """Start the three background threads."""
        self._stop_event.clear()
        pose_thread = threading.Thread(target=self._pose_loop, name="guidance-pose", daemon=True)
        evidence_thread = threading.Thread(target=self._evidence_loop, name="guidance-evidence", daemon=True)
        health_thread = threading.Thread(target=self._health_loop, name="guidance-health", daemon=True)
        self._threads = [pose_thread, evidence_thread, health_thread]
        for t in self._threads:
            t.start()
        logger.info(f"GuidanceSender started → {self._gs_url}")

    def stop(self) -> None:
        """Signal all threads to stop and join them (timeout 3s each)."""
        self._stop_event.set()
        for t in self._threads:
            t.join(timeout=3)
        try:
            self._gps_stop()
            self._gps_thread.join(timeout=3)
        except Exception as e:
            logger.error(f"Error stopping GPS service: {e}")
        self._threads = []
        logger.info("GuidanceSender stopped")

    @property
    def is_running(self) -> bool:
        """True while sender threads are active."""
        return not self._stop_event.is_set() and any(t.is_alive() for t in self._threads)

    @property
    def packets_sent(self) -> int:
        """Total packets successfully POSTed since start."""
        return self._packets_sent

    @property
    def last_error(self) -> Optional[str]:
        """Most recent error message, or None."""
        return self._last_error

    # ─── Internal loops ───────────────────────────────────────────────────────

    def _pose_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                gps = self._gps_state.get()
                self._seq += 1
                sniffer_alive = self._scan_manager.status().startswith("running")
                packet = {
                    "msg_type": "POSE",
                    "seq": self._seq,
                    "t_ms": _now_ms(),
                    "lat": getattr(gps, "lat", None),
                    "lon": getattr(gps, "lon", None),
                    "alt_m": getattr(gps, "alt_m", None),
                    "heading_deg": None,
                    "speed_mps": None,
                    "gps_valid": getattr(gps, "fix", 0) >= 1,
                    "sniffer_alive": sniffer_alive,
                    "battery_mv": None,
                }
                self._post("/api/guidance/pose", packet)
            except Exception as e:
                logger.error(f"_pose_loop error: {e}")
            self._stop_event.wait(config.GUIDANCE_POSE_INTERVAL_SEC)

    def _evidence_loop(self) -> None:
        csv_reader_state: dict = {"file": None, "path": None}
        while not self._stop_event.is_set():
            try:
                t_start = _now_ms()
                self._stop_event.wait(config.GUIDANCE_EVIDENCE_INTERVAL_SEC)
                if self._stop_event.is_set():
                    break
                t_end = _now_ms()

                rows = self._read_new_csv_rows(csv_reader_state)
                rssi_values = [
                    float(r["rssi_dbm"])
                    for r in rows
                    if r.get("rssi_dbm") and r["rssi_dbm"] != "" and r.get("frame_type") != "heartbeat"
                ]

                frames_total = len(rssi_values)
                frames_strong = sum(
                    1 for v in rssi_values if v > config.GUIDANCE_STRONG_RSSI_THRESHOLD_DBM
                )

                if rssi_values:
                    rssi_max: Optional[float] = max(rssi_values)
                    rssi_p95: Optional[float] = _percentile_95(rssi_values)
                    rssi_mean: Optional[float] = sum(rssi_values) / len(rssi_values)
                else:
                    rssi_max = rssi_p95 = rssi_mean = None

                gps = self._gps_state.get()
                self._seq += 1
                packet = {
                    "msg_type": "EVIDENCE",
                    "seq": self._seq,
                    "t_start_ms": t_start,
                    "t_end_ms": t_end,
                    "win_ms": t_end - t_start,
                    "lat": getattr(gps, "lat", None),
                    "lon": getattr(gps, "lon", None),
                    "frames_total": frames_total,
                    "frames_strong": frames_strong,
                    "rssi_max_dbm": rssi_max,
                    "rssi_p95_dbm": rssi_p95,
                    "rssi_mean_dbm": rssi_mean,
                }
                self._post("/api/guidance/evidence", packet)
            except Exception as e:
                logger.error(f"_evidence_loop error: {e}")

    def _health_loop(self) -> None:
        while not self._stop_event.is_set():
            self._stop_event.wait(config.GUIDANCE_HEALTH_INTERVAL_SEC)
            if self._stop_event.is_set():
                break
            try:
                cpu_pct = psutil.cpu_percent(interval=0.5) if _PSUTIL_AVAILABLE else None
                temp_c = _read_cpu_temp()
                gps = self._gps_state.get()
                sniffer_alive = self._scan_manager.status().startswith("running")
                self._seq += 1
                packet = {
                    "msg_type": "HEALTH",
                    "seq": self._seq,
                    "t_ms": _now_ms(),
                    "cpu_pct": cpu_pct,
                    "temp_c": temp_c,
                    "gps_valid": getattr(gps, "fix", 0) >= 1,
                    "sniffer_alive": sniffer_alive,
                    "uplink_queue_len": 0,
                    "dropped_msgs": self._dropped_msgs,
                }
                self._post("/api/guidance/health", packet)
            except Exception as e:
                logger.error(f"_health_loop error: {e}")

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _post(self, endpoint: str, data: dict) -> bool:
        """POST data to the Ground Station. Never raises. Returns True on success."""
        url = self._gs_url + endpoint
        try:
            resp = requests.post(url, json=data, timeout=config.GUIDANCE_HTTP_TIMEOUT_SEC)
            resp.raise_for_status()
            self._packets_sent += 1
            return True
        except Exception as e:
            self._last_error = str(e)
            self._dropped_msgs += 1
            return False

    def _read_new_csv_rows(self, state: dict) -> list:
        """Read new rows appended to the most recently modified CSV in LOG_DIR.

        Handles missing file, new file rotation, and encoding errors gracefully.
        Returns list of dicts, capped at GUIDANCE_EVIDENCE_LOOKBACK_ROWS.
        """
        try:
            csv_files = list(config.LOG_DIR.glob("*.csv"))
            if not csv_files:
                return []

            newest_path = max(csv_files, key=lambda p: p.stat().st_mtime)

            # New scan file detected — reopen and seek to end
            if newest_path != state.get("path"):
                if state.get("file"):
                    try:
                        state["file"].close()
                    except Exception:
                        pass
                f = open(newest_path, newline="", encoding="utf-8", errors="replace")
                f.seek(0, 2)  # seek to end; we only want new rows going forward
                state["file"] = f
                state["path"] = newest_path
                return []

            f = state["file"]
            if f is None:
                return []

            new_content = f.read()
            if not new_content:
                return []

            # Split into lines; drop last partial line if file mid-write
            lines = new_content.split("\n")
            complete_lines = lines[:-1] if not new_content.endswith("\n") else lines
            complete_lines = [l for l in complete_lines if l.strip()]
            if not complete_lines:
                return []

            # Parse with csv.DictReader using the fieldnames from config
            import io
            text_block = "\n".join(complete_lines)
            reader = csv.DictReader(io.StringIO(text_block), fieldnames=config.FIELDNAMES)
            rows = [row for row in reader]

            # Cap to most recent N rows
            return rows[-config.GUIDANCE_EVIDENCE_LOOKBACK_ROWS:]

        except Exception as e:
            logger.error(f"_read_new_csv_rows error: {e}")
            return []
