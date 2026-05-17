#!/usr/bin/env bash
# deploy.sh — copy updated airunit code to the Pi deploy folder and restart services.
#
# Usage (run from anywhere on the Pi after git pull):
#   sudo bash ~/sar-ground-station/airunit/deploy.sh
#
# Optional override:
#   sudo DEPLOY_DIR=/custom/path/airunit bash ~/sar-ground-station/airunit/deploy.sh
#
# ── CONFIGURE THIS ONCE ────────────────────────────────────────────────────────
# ───────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_USER="${SUDO_USER:-$USER}"
RUN_HOME="$(getent passwd "$RUN_USER" | cut -d: -f6)"
if [ -z "$RUN_HOME" ]; then
    echo "Could not resolve home directory for user: $RUN_USER" >&2
    exit 1
fi
DEPLOY_DIR="${DEPLOY_DIR:-$RUN_HOME/Desktop/airunit}"   # where the services actually run from

echo "=== AirUnit deploy ==="
echo "  Source : $SCRIPT_DIR"
echo "  Target : $DEPLOY_DIR"
echo

# ── 1. Stop services ──────────────────────────────────────────────────────────
echo "[1/4] Stopping services..."
systemctl stop airunit-bridge.service airunit-web.service || true

# ── 2. Sync source files ──────────────────────────────────────────────────────
echo "[2/4] Syncing files..."
mkdir -p "$DEPLOY_DIR"

rsync -av --delete \
    --exclude '__pycache__/' \
    --exclude '.venv/' \
    --exclude 'logs/' \
    --exclude 'deploy.sh' \
    --exclude 'install.sh' \
    "$SCRIPT_DIR/" "$DEPLOY_DIR/"

# ── 3. Install/update Python deps ────────────────────────────────────────────
VENV="$DEPLOY_DIR/.venv"
PYTHON="$VENV/bin/python"

if [ ! -x "$PYTHON" ]; then
    echo "[3/4] Creating venv..."
    python3 -m venv "$VENV"
else
    echo "[3/4] Updating deps..."
fi

"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$DEPLOY_DIR/requirements.txt"

# ── 4. Restart services ───────────────────────────────────────────────────────
echo "[4/4] Starting services..."
systemctl start airunit-web.service
systemctl start airunit-bridge.service

echo
echo "=== Done ==="
systemctl status airunit-web.service --no-pager -l | head -8
echo "---"
systemctl status airunit-bridge.service --no-pager -l | head -8
