import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("provisioning")

# --- Constants ---
HOTSPOT_SSID = "AirUnit-Setup"
HOTSPOT_INTERFACE = "wlan0"
HOTSPOT_IP = "192.168.4.1"
HOTSPOT_SUBNET = "192.168.4.0/24"
HOTSPOT_DHCP_START = "192.168.4.2"
HOTSPOT_DHCP_END = "192.168.4.20"
HOSTAPD_CONF_PATH = "/tmp/airunit_hostapd.conf"
DNSMASQ_CONF_PATH = "/tmp/airunit_dnsmasq.conf"
NETWORK_CONFIG_PATH = Path(__file__).resolve().parent / "network_config.json"
WIFI_CONNECT_TIMEOUT_SEC = 20


def _run(cmd: str, **kwargs) -> subprocess.CompletedProcess:
    """Run a shell command with check=False, capturing output."""
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False, **kwargs)


def load_network_config() -> Optional[dict]:
    """Read and return network_config.json as a dict.

    Returns None if file is missing, empty, or cannot be parsed.
    Required keys: ssid, ground_station_url.
    """
    try:
        if not NETWORK_CONFIG_PATH.exists():
            return None
        text = NETWORK_CONFIG_PATH.read_text(encoding="utf-8").strip()
        if not text:
            return None
        data = json.loads(text)
        if not isinstance(data, dict):
            return None
        if not data.get("ssid") or not data.get("ground_station_url"):
            return None
        return data
    except Exception as e:
        logger.error(f"load_network_config failed: {e}")
        return None


def save_network_config(ssid: str, password: str, ground_station_url: str) -> None:
    """Write network_config.json with the three fields. Creates file if missing."""
    try:
        data = {
            "ssid": ssid,
            "password": password,
            "ground_station_url": ground_station_url,
        }
        NETWORK_CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info(f"Saved network config: ssid={ssid}, gs_url={ground_station_url}")
    except Exception as e:
        logger.error(f"save_network_config failed: {e}")


def is_wifi_connected() -> bool:
    """Return True if wlan0 shows as connected via nmcli."""
    try:
        result = _run("nmcli -t -f GENERAL.STATE device show wlan0")
        return "connected" in result.stdout.lower()
    except Exception as e:
        logger.error(f"is_wifi_connected failed: {e}")
        return False


def get_current_ip() -> Optional[str]:
    """Return the current IPv4 address of wlan0, or None on failure."""
    try:
        result = _run("nmcli -t -f IP4.ADDRESS device show wlan0")
        for line in result.stdout.splitlines():
            line = line.strip()
            if line:
                # Format: IP4.ADDRESS[1]:192.168.x.x/24
                parts = line.split(":")
                if len(parts) >= 2:
                    addr = parts[-1].strip()
                    # Strip CIDR prefix length if present
                    ip = addr.split("/")[0]
                    if ip:
                        return ip
        return None
    except Exception as e:
        logger.error(f"get_current_ip failed: {e}")
        return None


def connect_to_wifi(ssid: str, password: str) -> bool:
    """Connect wlan0 to the given WiFi network.

    1. Stops hotspot first.
    2. Re-enables NetworkManager management of wlan0.
    3. Connects via nmcli.
    4. Polls is_wifi_connected() for up to WIFI_CONNECT_TIMEOUT_SEC seconds.
    Returns True if connected, False on timeout or error.
    """
    try:
        stop_hotspot()

        _run("sudo nmcli device set wlan0 managed yes")
        time.sleep(1)

        if password:
            cmd = f'sudo nmcli device wifi connect "{ssid}" password "{password}" ifname wlan0'
        else:
            cmd = f'sudo nmcli device wifi connect "{ssid}" ifname wlan0'

        result = _run(cmd)
        if result.returncode != 0:
            logger.warning(f"nmcli connect returned {result.returncode}: {result.stderr.strip()}")

        deadline = time.time() + WIFI_CONNECT_TIMEOUT_SEC
        while time.time() < deadline:
            if is_wifi_connected():
                logger.info(f"Connected to WiFi: {ssid}")
                return True
            time.sleep(2)

        logger.error(f"Timed out connecting to WiFi: {ssid}")
        return False
    except Exception as e:
        logger.error(f"connect_to_wifi failed: {e}")
        return False


def start_hotspot() -> bool:
    """Start the AirUnit-Setup hotspot on wlan0.

    1. Disables NetworkManager on wlan0.
    2. Brings interface up with a static IP.
    3. Writes hostapd and dnsmasq configs.
    4. Starts both services.
    Returns True if both started without error.
    """
    try:
        # 1. Disable NetworkManager control
        _run("sudo nmcli device set wlan0 managed no")

        # 2. Bring interface up and assign static IP
        _run("sudo ip link set wlan0 up")
        _run("sudo ip addr flush dev wlan0")
        _run(f"sudo ip addr add {HOTSPOT_IP}/24 dev wlan0")

        # 3. Write hostapd config
        hostapd_conf = (
            f"interface={HOTSPOT_INTERFACE}\n"
            "driver=nl80211\n"
            f"ssid={HOTSPOT_SSID}\n"
            "hw_mode=g\n"
            "channel=6\n"
            "wmm_enabled=0\n"
            "macaddr_acl=0\n"
            "auth_algs=1\n"
            "ignore_broadcast_ssid=0\n"
            "wpa=0\n"
        )
        Path(HOSTAPD_CONF_PATH).write_text(hostapd_conf)

        # 4. Write dnsmasq config
        dnsmasq_conf = (
            f"interface={HOTSPOT_INTERFACE}\n"
            "bind-interfaces\n"
            f"dhcp-range={HOTSPOT_DHCP_START},{HOTSPOT_DHCP_END},255.255.255.0,1h\n"
            f"address=/#/{HOTSPOT_IP}\n"
        )
        Path(DNSMASQ_CONF_PATH).write_text(dnsmasq_conf)

        # 5. Start hostapd
        r_hostapd = _run(f"sudo hostapd -B {HOSTAPD_CONF_PATH}")
        if r_hostapd.returncode != 0:
            logger.error(f"hostapd failed: {r_hostapd.stderr.strip()}")
            return False

        # 6. Start dnsmasq
        r_dnsmasq = _run(
            f"sudo dnsmasq -C {DNSMASQ_CONF_PATH} --pid-file=/tmp/airunit_dnsmasq.pid"
        )
        if r_dnsmasq.returncode != 0:
            logger.error(f"dnsmasq failed: {r_dnsmasq.stderr.strip()}")
            return False

        logger.info(f"Hotspot '{HOTSPOT_SSID}' started on {HOTSPOT_INTERFACE}")
        return True
    except Exception as e:
        logger.error(f"start_hotspot failed: {e}")
        return False


def stop_hotspot() -> None:
    """Kill hostapd and dnsmasq, flush IP, restore NetworkManager management."""
    try:
        _run("sudo pkill -f 'hostapd.*airunit_hostapd'")
        _run("sudo pkill -f 'dnsmasq.*airunit_dnsmasq'")
        _run("sudo ip addr flush dev wlan0")
        _run("sudo nmcli device set wlan0 managed yes")
        logger.info("Hotspot stopped")
    except Exception as e:
        logger.error(f"stop_hotspot failed: {e}")
