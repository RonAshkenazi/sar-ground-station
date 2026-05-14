#!/usr/bin/env bash
# install.sh — deploy airunit services on any Pi, any username/path.
# Run from the directory where this script lives.
#
# Usage:
#   sudo bash install.sh [GROUND_HOST] [GROUND_PORT]
#
# Defaults: GROUND_HOST=192.168.1.100  GROUND_PORT=8000
#
# What it does:
#   1. Creates a Python venv (if absent) and installs requirements.
#   2. Writes /etc/systemd/system/airunit-web.service
#   3. Writes /etc/systemd/system/airunit-bridge.service
#   4. Enables + starts both services.

set -euo pipefail

GROUND_HOST="${1:-192.168.1.100}"
GROUND_PORT="${2:-8000}"
AIRUNIT_PORT=8080

# Resolve the real install directory (works regardless of where sudo is called from)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
PYTHON="$VENV/bin/python"

echo "=== AirUnit installer ==="
echo "  Install dir : $SCRIPT_DIR"
echo "  Ground host : $GROUND_HOST:$GROUND_PORT"
echo "  AirUnit port: $AIRUNIT_PORT"
echo

# ── 1. Venv + deps ──────────────────────────────────────────────────────────
if [ ! -x "$PYTHON" ]; then
    echo "[1/4] Creating venv at $VENV ..."
    python3 -m venv "$VENV"
else
    echo "[1/4] Venv already exists at $VENV"
fi

echo "      Installing requirements..."
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"
"$VENV/bin/pip" install --quiet websockets httpx

# ── 2. airunit-web.service ───────────────────────────────────────────────────
echo "[2/4] Writing airunit-web.service..."
cat > /etc/systemd/system/airunit-web.service <<EOF
[Unit]
Description=AirUnit Web Control
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$SCRIPT_DIR
ExecStart=$PYTHON -m uvicorn app:app --host 0.0.0.0 --port $AIRUNIT_PORT
Restart=always
RestartSec=3
User=root
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# ── 3. airunit-bridge.service ────────────────────────────────────────────────
echo "[3/4] Writing airunit-bridge.service..."
cat > /etc/systemd/system/airunit-bridge.service <<EOF
[Unit]
Description=AirUnit Ground-Station Bridge
After=network-online.target airunit-web.service
Wants=network-online.target
Requires=airunit-web.service

[Service]
Type=simple
WorkingDirectory=$SCRIPT_DIR
Environment=GROUND_HOST=$GROUND_HOST
Environment=GROUND_PORT=$GROUND_PORT
Environment=AIRUNIT_LOCAL_PORT=$AIRUNIT_PORT
ExecStart=$PYTHON -u $SCRIPT_DIR/bridge.py
Restart=always
RestartSec=3
User=root
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# ── 4. Enable + start ────────────────────────────────────────────────────────
echo "[4/4] Enabling and starting services..."
systemctl daemon-reload
systemctl enable --now airunit-web.service
systemctl enable --now airunit-bridge.service

echo
echo "=== Done ==="
echo "  airunit-web   -> http://$(hostname -I | awk '{print $1}'):$AIRUNIT_PORT"
echo "  bridge target -> ws://$GROUND_HOST:$GROUND_PORT/api/airunit/ws"
echo
echo "Watch logs:"
echo "  journalctl -u airunit-web -f"
echo "  journalctl -u airunit-bridge -f"
