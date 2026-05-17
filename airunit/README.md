# AirUnit — Raspberry Pi Air-Side Software

Runs on the drone-mounted Pi. Captures Wi-Fi and BLE RF frames, tags them with GPS, and streams scan data + guidance packets to the Ground Station.

---

## Files

| File | Purpose |
|---|---|
| `app.py` | FastAPI web app — scan control, status API, WebSocket broadcast |
| `scan_manager.py` | Wi-Fi sniffer lifecycle manager |
| `ble_scan_manager.py` | BLE sniffer lifecycle manager |
| `wifi_sniffer_logger.py` | Raw Wi-Fi frame capture → CSV rows |
| `ble_sniffer_logger.py` | Raw BLE frame capture → CSV rows |
| `gps_service.py` | GPS serial reader, shared GPS state |
| `guidance_sender.py` | Background service — posts POSE / EVIDENCE / HEALTH packets to Ground Station |
| `bridge.py` | WebSocket bridge — forwards airunit events to Ground Station |
| `provisioning.py` | Reads `network_config.json` for Ground Station URL at runtime |
| `config.py` | All tuneable constants (interfaces, intervals, CSV format) |
| `install.sh` | First-time systemd service setup |
| `deploy.sh` | Day-to-day deploy — syncs code to the Pi deploy folder and restarts services |
| `static/setup.html` | Fallback setup page served when no `index.html` exists yet |

---

## Services

Two systemd services run on the Pi:

| Service | What it does |
|---|---|
| `airunit-web` | Runs `uvicorn app:app` on port 8080 |
| `airunit-bridge` | Runs `bridge.py` — WebSocket relay to Ground Station |

---

## First-Time Setup

```bash
# On the Pi — run once after cloning
cd ~/Desktop/sar-ground-station/airunit
sudo bash install.sh [GROUND_HOST] [GROUND_PORT]
# Defaults: GROUND_HOST=192.168.1.100  GROUND_PORT=8000
```

---

## Updating Code (Day-to-Day)

```bash
# On your dev machine
git push

# On the Pi
cd ~/Desktop/sar-ground-station && git pull && sudo bash airunit/deploy.sh
```

`deploy.sh` stops services, rsyncs files to the deploy folder (`~/Desktop/airunit` by default), updates pip deps, and restarts services.

Override the deploy target if needed:
```bash
sudo DEPLOY_DIR=/custom/path bash airunit/deploy.sh
```

Skip dep install for fast code-only updates:
```bash
sudo SKIP_DEPS=1 bash airunit/deploy.sh
```

---

## Logs

```bash
journalctl -u airunit-web -f
journalctl -u airunit-bridge -f
```

Scan CSVs are written to `logs/` inside the deploy folder.

---

## Configuration

Key settings in `config.py`:

| Setting | Default | Notes |
|---|---|---|
| `WIFI_MONITOR_INTERFACE` | `wlan1` | Monitor-mode Wi-Fi adapter |
| `BLE_HCI_INTERFACE` | `hci0` | BLE HCI device |
| `GPS_SERIAL_DEVICE` | `/dev/ttyACM0` | GPS serial port |
| `HOP_ENABLED` | `False` | Channel hopping |
| `GROUND_STATION_URL` | `http://192.168.1.100:8000` | Overridden at runtime by `network_config.json` |

---

## PR Guidelines

- All airunit changes go in their own PR targeting `main`
- Do **not** mix airunit changes with frontend or backend changes in the same PR
- Test on the Pi before opening a PR: run `deploy.sh` and check `journalctl` for errors
- Tag PRs with the `airunit` label
