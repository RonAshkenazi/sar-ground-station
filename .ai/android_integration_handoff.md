# Android Integration Handoff — SAR Ground Station

**Target role:** Android developer  
**App intent:** Field operator companion — monitor live guidance, track the drone/Pi unit, view localization results, and receive next-waypoint recommendations during an active SAR mission  
**Not in scope for this app:** Running the enrichment/Re-ID/localization pipeline (that stays on the desktop)

---

## 1. System Overview

The SAR Ground Station is a two-component system:

```
[Laptop — Ground Station]
  ├── Python/FastAPI backend  (port 8000)
  └── React frontend          (port 5173, desktop only)

[Raspberry Pi — Air Unit / Drone]
  └── Connects to backend via WebSocket on /api/airunit/ws
      Streams: GPS pose + RF scan evidence + health pings

[Android App — Field Companion]
  └── Connects to backend REST + WebSocket on the same LAN
      OR connects to Pi WebSocket directly (see §7)
```

**Data flow summary:**
1. Pi flies, streams POSE + EVIDENCE packets to the backend in real time
2. Backend's guidance engine consumes the packets and maintains a scored grid of candidate cells
3. Backend yields a `recommendation` (next waypoint for the drone) — EXPLORE or REFINE mode
4. Android app reads the grid and recommendation, shows the map, relays commands back to Pi
5. After the scan mission, the desktop pipeline processes data → localization result (device positions)
6. Android can view those localization results once available

---

## 2. Network Setup (Same LAN)

### Finding the backend

The laptop and Android device must be on the same WiFi network. The backend runs on:

```
http://<LAPTOP_IP>:8000
```

There is no DNS discovery. The operator must know or configure the laptop's local IP (e.g. `192.168.1.42`). Recommended UX: a settings screen with a persistent IP:port field, defaulting to `http://192.168.1.42:8000`.

### CORS — required backend change before Android can connect

The current CORS whitelist only allows:
```
http://localhost:5173
http://127.0.0.1:5173
```

**The backend must be updated to accept Android requests.** Options:

**Option A — Allow all origins on trusted LAN** (simplest, appropriate for closed field network):
```python
# backend/app/main.py
allow_origins=["*"]
```

**Option B — Append the Android app's origin** (stricter):
```python
allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost",         # Android emulator
    "null",                     # Android WebView (file://)
]
```

> The CORS change is a 1-line edit in `backend/app/main.py`. It must be coordinated with the backend team before the first Android build.

### Connectivity health check

Use this endpoint on app startup to confirm the backend is reachable:

```
GET /api/airunit/status
→ { "pi_connected": bool, "pi_info": { "ip": "...", "port": 8001 } | null }
```

If this returns 200, the backend is up. If `pi_connected` is true, the drone unit is live.

---

## 3. Backend REST API — Base Conventions

| Convention | Value |
|---|---|
| Base URL | `http://<LAPTOP_IP>:8000` |
| Content-Type | `application/json` (all POST bodies) |
| Auth | None (trusted LAN — no tokens or API keys) |
| Long-running ops | Return `{ "execution_id": "..." }` immediately; poll for result |
| Error shape | `{ "detail": "message" }` with HTTP 4xx/5xx |

**Execution polling pattern** (used for enrichment, Re-ID, localization):
```
POST /api/sessions/{session_id}/<stage>/run
→ { "execution_id": "abc123", "status": "pending" }

loop:
  GET /api/executions/abc123
  → { "status": "pending"|"running"|"success"|"failed",
      "stage": "...",
      "result_metadata": {...},   ← populated on success
      "error": "...",             ← populated on failure
      "warnings": [...],
      "created_at": "...",
      "updated_at": "..." }
until status == "success" or "failed"
```

Recommended poll interval: **2 seconds**. There are no push notifications or server-sent events for execution completion.

---

## 4. Field Operator Workflow

From the Android operator's perspective, a live mission looks like this:

```
1. App opens → operator enters backend IP → health check passes
2. Check Pi status → confirm drone unit is connected
3. Open WebSocket to /api/airunit/frontend-ws → receive live stream
4. View guidance grid on map (colored cells, current recommendation)
5. Relay recommendation to drone operator verbally or via command
6. When scan complete → view session state / localization result
7. Optionally save session
```

---

## 5. REST Endpoints — Field Operator Relevant

### 5.1 Air Unit Status

```
GET /api/airunit/status

Response:
{
  "pi_connected": true,
  "pi_info": {
    "ip": "192.168.1.77",
    "port": 8001
  }
}
```

### 5.2 Send Command to Pi

```
POST /api/airunit/command
Body: { "cmd": "<command string>" }

Response: { "ok": true }
Errors: HTTP 503 if Pi not connected
```

Common command strings are defined by the Pi firmware (out of scope here). Use this to relay operator instructions to the drone unit.

### 5.3 List Log Files on Pi

```
GET /api/airunit/files

Response:
{
  "files": [
    { "name": "scan_20260530.csv", "size_bytes": 14200, "mtime": 1748600000, "description": "..." }
  ],
  "error": null
}
```

### 5.4 Download Log File from Pi

```
GET /api/airunit/files/{filename}

Response: Binary octet-stream (file download)
```

The backend proxies this directly from the Pi's HTTP server at `pi_info.ip:pi_info.port/logs/{filename}`.

---

## 6. Guidance API — Live Map & Recommendations

The guidance engine runs on the backend, consuming POSE + EVIDENCE packets from the Pi and maintaining a scored grid. The Android app reads the grid and current recommendation to display the map.

### 6.1 Initialize Guidance Grid

Must be called once before the mission starts (or by the desktop — check if already initialized via `/api/guidance/status`).

```
POST /api/guidance/init
Body:
{
  "min_lat": 31.495,
  "max_lat": 31.510,
  "min_lon": 34.790,
  "max_lon": 34.810,
  "cell_size_m": 5.0      ← default 30, production uses 5
}

Response:
{
  "ok": true,
  "n_rows": 33,
  "n_cols": 44,
  "total_cells": 1452
}
```

### 6.2 Get Current Guidance Grid

Poll this every **2 seconds** to refresh the map.

```
GET /api/guidance/grid

Response:
{
  "initialized": true,
  "bounds": {
    "min_lat": 31.495, "max_lat": 31.510,
    "min_lon": 34.790, "max_lon": 34.810
  },
  "cell_size_m": 5.0,
  "n_rows": 33,
  "n_cols": 44,
  "mode": "EXPLORE",        ← current engine mode
  "cells": [
    {
      "cell_id": 0,
      "center_lat": 31.4953,
      "center_lon": 34.7902,
      "evidence_score": 0.72,      ← how much RF data has been seen here
      "uncertainty_score": 0.88,   ← how unexplored/unknown this cell is
      "peak_score": 0.0,           ← proximity to suspected signal peak
      "coverage_score": 0.65,
      "age_score": 0.91,           ← how recently this cell was visited
      "final_score": 0.831,        ← combined priority score for this cell
      "display_score": 0.831,      ← use this for coloring the cell
      "spatial_entropy": 0.72,
      "spatial_certainty": 0.28,
      "evidence_freshness": 0.80
    },
    ...
  ]
}
```

**Cell coloring guide** (matches desktop UI):

| display_score | Color |
|---|---|
| ≥ 0.60 | Green `#16a34a` |
| ≥ 0.30 | Yellow `#ca8a04` |
| ≥ 0.10 | Orange `#ea580c` |
| ≥ 0.01 | Red `#dc2626` |
| < 0.01 | Dark grey `#374151` (unvisited) |

The **recommended cell** should be highlighted with a white border and slightly higher opacity.

### 6.3 Get Current Recommendation

```
GET /api/guidance/recommendation

Response (when available):
{
  "available": true,
  "timestamp_ms": 1748600123456,
  "mode": "EXPLORE",               ← "EXPLORE" or "REFINE"
  "target_cell_id": 142,
  "target_lat": 31.5021,
  "target_lon": 34.7994,
  "bearing_deg": 127.4,            ← bearing from current drone position
  "distance_m": 83.2,              ← distance from current drone position
  "final_score": 0.912,
  "evidence_score": 0.78,
  "uncertainty_score": 0.95,
  "peak_score": 0.0,
  "travel_cost": 0.15,
  "oscillation_penalty": 0.0,
  "gps_valid": true,
  "data_fresh": true,
  "recommendation_stale": false,
  "reason": "EXPLORE: high uncertainty, low coverage"
}

Response (when not yet available):
{ "available": false }
```

**Mode interpretation:**
- `EXPLORE` — drone should cover new ground; target is the most uncertain unvisited cell
- `REFINE` — signal peak has been detected; drone should converge on the likely target location

### 6.4 Push POSE / EVIDENCE (if Android acts as data injector)

If the Android app can receive GPS or RF data from the drone over Bluetooth or another channel (not standard — coordinate with Pi firmware team), it can ingest directly:

```
POST /api/guidance/update
Body:
{
  "type": "POSE",
  "lat": 31.5021,
  "lon": 34.7994,
  "gps_valid": true,
  "sniffer_alive": true
}

POST /api/guidance/update
Body:
{
  "type": "EVIDENCE",
  "lat": 31.5021,
  "lon": 34.7994,
  "dwell_ms": 2000,
  "frames_total": 18,
  "frames_strong": 7,
  "rssi_max_dbm": -62,
  "rssi_p95_dbm": -68,
  "rssi_mean_dbm": -74
}

POST /api/guidance/update
Body:
{
  "type": "HEALTH",
  "lat": 31.5021,
  "lon": 34.7994,
  "battery_pct": 72,
  "uptime_sec": 345
}

Response: { "ok": true }
```

All three types can also be sent to dedicated endpoints: `POST /api/guidance/pose`, `POST /api/guidance/evidence`, `POST /api/guidance/health`.

---

## 7. WebSocket Connections

### 7.1 Backend Relay (Recommended — Path A)

The backend maintains a relay between the Pi and frontend clients. Connect here to receive all Pi messages without knowing the Pi's IP address.

```
WS ws://<LAPTOP_IP>:8000/api/airunit/frontend-ws
```

**On connect**, the backend immediately sends:
```json
{ "type": "pi_status", "connected": true|false, "pi_info": { "ip": "...", "port": 8001 } | null }
```

**Ongoing inbound messages** (backend → Android) — all Pi messages are relayed verbatim:

```json
{ "type": "pi_connected", "connected": true, "pi_info": { "ip": "...", "port": 8001 } }
{ "type": "pi_disconnected" }
{ "type": "pi_status", "connected": true, "pi_info": { ... } }

// Pi telemetry (relayed as-is):
{ "type": "POSE",     "lat": 31.502, "lon": 34.799, "gps_valid": true, "sniffer_alive": true }
{ "type": "EVIDENCE", "lat": 31.502, "lon": 34.799, "dwell_ms": 2000, "frames_total": 18, ... }
{ "type": "HEALTH",   "lat": 31.502, "lon": 34.799, "battery_pct": 72, "uptime_sec": 345 }
{ "type": "hello",    "ip": "192.168.1.77", "port": 8001 }
```

**Outbound messages** (Android → backend → Pi):
```json
{ "type": "cmd", "cmd": "<command string>" }
```

The backend only forwards `type: "cmd"` messages to the Pi. All other outbound message types are silently ignored.

### 7.2 Direct Pi Connection (Path B — Fallback / Low-Latency)

If the backend is unreachable or a direct low-latency path is needed, connect to the Pi's WebSocket directly. The Pi's IP and port are surfaced in the `pi_info` field from either `GET /api/airunit/status` or the relay WebSocket `pi_status` message.

```
WS ws://<PI_IP>:8001/ws
```

Message format is identical to the relayed Pi telemetry above (POSE / EVIDENCE / HEALTH / hello). Commands can be sent in the same `{ "type": "cmd", "cmd": "..." }` format.

> **Note:** Path B bypasses the backend's guidance engine — POSE/EVIDENCE packets from the Pi go directly to the backend via its own WebSocket connection. The Android app would need to additionally `POST /api/guidance/update` if it wants to inject data into the guidance engine while on Path B.

### 7.3 Reconnection Strategy

Both WebSocket paths drop without notice if the laptop goes to sleep or the network changes. Implement exponential backoff: retry after 1s, 2s, 4s, 8s, cap at 30s.

---

## 8. Session & Localization Results

After a mission, the desktop runs the enrichment → Re-ID → localization pipeline. The Android app can view the results once available.

### 8.1 List Available Sessions

```
GET /api/scan-folders
Response: { "folders": [{ "folder_id": "scan_20260530_beirut", "path": "...", ... }], "warning": null }
```

### 8.2 Create or Resume a Session

```
POST /api/sessions
Body: { "folder_id": "scan_20260530_beirut" }
Response: { "session_id": "sess_abc123", "folder_id": "...", "mode": "wifi", "created_at": "..." }
```

Keep `session_id` for all subsequent calls.

### 8.3 Get Full Session State

```
GET /api/sessions/{session_id}/state

Response (abbreviated):
{
  "session_id": "sess_abc123",
  "folder_id": "scan_20260530_beirut",
  "mode": "wifi",
  "calibration": { "approved": true, "parameters": { "rssi_at_1m": -35, "path_loss_n": 2.8 } },
  "active_enriched_artifact": "scan_20260530_beirut_ENRICHED.csv",
  "active_reid_artifact": "scan_20260530_beirut_REID.csv",
  "localization_result": { ... }   ← null until localization has run
}
```

### 8.4 Localization Result — Device Positions

If `localization_result` is populated in the session state, extract cluster positions for map display:

```json
{
  "cluster_results": [
    {
      "cluster_id": "C001",
      "cluster_type": "dynamic",    ← "dynamic" or "static"
      "status": "success",           ← skip if "failed"
      "sample_count": 247,
      "primary_peak": {
        "lat": 31.5021,
        "lon": 34.7994,
        "score": 0.912
      },
      "uncertainty_regions": [
        { "radius_m": 12.4, "mass_fraction": 0.68 }
      ]
    }
  ],
  "bounds": {
    "min_lat": 31.495, "max_lat": 31.510,
    "min_lon": 34.790, "max_lon": 34.810
  }
}
```

**Rendering guidance:**
- Plot each cluster's `primary_peak` as a pin on the map
- Draw a circle of `uncertainty_regions[0].radius_m` around the peak
- `cluster_type: "dynamic"` = likely a person/moving target (prioritize)
- `cluster_type: "static"` = fixed RF source (lower priority — may be AP or infrastructure)

### 8.5 List Saved Sessions

```
GET /api/saved-sessions
Response: [{ "saved_id": "...", "folder_id": "...", "saved_at_utc": "2026-05-30T14:22:00Z", "mode": "wifi" }]
```

### 8.6 Resume a Saved Session

```
POST /api/saved-sessions/{saved_id}/resume
Response: Full session object (same shape as §8.3)
```

---

## 9. Key Data Models (JSON Reference)

### POSE packet

```json
{
  "type": "POSE",
  "lat": 31.5021,
  "lon": 34.7994,
  "gps_valid": true,
  "sniffer_alive": true
}
```

### EVIDENCE packet

```json
{
  "type": "EVIDENCE",
  "lat": 31.5021,
  "lon": 34.7994,
  "dwell_ms": 2000,
  "win_ms": 2000,
  "frames_total": 18,
  "frames_strong": 7,
  "rssi_max_dbm": -62,
  "rssi_p95_dbm": -68,
  "rssi_mean_dbm": -74
}
```

`frames_strong` = frames with RSSI ≥ strong threshold (typically -65 dBm). The ratio `frames_strong / frames_total` is used by the guidance engine to estimate signal strength at this cell.

### HEALTH packet

```json
{
  "type": "HEALTH",
  "lat": 31.5021,
  "lon": 34.7994,
  "battery_pct": 72,
  "uptime_sec": 345
}
```

### GridCell

```json
{
  "cell_id": 142,
  "center_lat": 31.5021,
  "center_lon": 34.7994,
  "evidence_score": 0.72,
  "uncertainty_score": 0.88,
  "peak_score": 0.41,
  "coverage_score": 0.65,
  "age_score": 0.91,
  "final_score": 0.831,
  "display_score": 0.831,
  "spatial_entropy": 0.72,
  "spatial_certainty": 0.28,
  "evidence_freshness": 0.80
}
```

### GuidanceRecommendation (available)

```json
{
  "available": true,
  "mode": "EXPLORE",
  "target_cell_id": 142,
  "target_lat": 31.5021,
  "target_lon": 34.7994,
  "bearing_deg": 127.4,
  "distance_m": 83.2,
  "reason": "EXPLORE: high uncertainty, low coverage"
}
```

---

## 10. Suggested Android Screen Map

| Screen | Primary data source | Refresh |
|---|---|---|
| **Connect** | `GET /api/airunit/status` | On open + retry |
| **Live Map** | `GET /api/guidance/grid` + `GET /api/guidance/recommendation` | Poll 2s |
| **Drone Status** | WebSocket `/api/airunit/frontend-ws` (POSE / HEALTH messages) | Real-time |
| **Results Map** | `GET /api/sessions/{id}/state` → `localization_result` | On demand |
| **Saved Missions** | `GET /api/saved-sessions` | On demand |
| **Settings** | Local storage (backend IP, cell color thresholds) | — |

---

## 11. Integration Checklist

- [ ] Backend CORS updated to accept Android origin (§2)
- [ ] Settings screen stores and persists backend IP:port
- [ ] Startup health check via `GET /api/airunit/status`
- [ ] WebSocket to `/api/airunit/frontend-ws` with reconnect backoff
- [ ] Live map polls `GET /api/guidance/grid` every 2s
- [ ] Recommendation polls `GET /api/guidance/recommendation` every 2s
- [ ] POSE messages from WebSocket used to animate drone position on map
- [ ] Cluster positions rendered from `localization_result.cluster_results`
- [ ] Uncertainty circle drawn per cluster (`uncertainty_regions[0].radius_m`)
- [ ] `cluster_type: "dynamic"` visually distinct from `"static"`
- [ ] Command send via `POST /api/airunit/command`
- [ ] Direct Pi fallback path (Path B) documented for offline/edge cases

---

## 12. Out of Scope for Android (Desktop Only)

- Running Enrichment / Re-ID / Localization pipeline
- Calibration parameter derivation
- Uploading scan files (CSV/PCAP) — file system access not available to Android
- Result Analysis ground-truth editing and evaluation scoring
- Emulator / simulation mode
