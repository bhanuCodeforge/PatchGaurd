#!/bin/bash
set -e

# PatchGuard Agent Installer for Linux (systemd)
# Usage: sudo ./install.sh [API_KEY] [SERVER_URL]

if [ "$EUID" -ne 0 ]; then
  echo "Error: Please run as root (sudo)."
  exit 1
fi

API_KEY=${1}
SERVER_URL=${2:-"ws://localhost:8001/ws/agent"}
INSTALL_DIR="/opt/patchguard-agent"
LOG_DIR="/var/log/patchguard-agent"

echo "--- PatchGuard Agent Installation ---"

# 1. Create Directories
echo "[1/6] Creating installation directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$LOG_DIR"
cp -r . "$INSTALL_DIR/"

# 2. Install Dependencies
echo "[2/6] Installing system dependencies..."
if command -v apt-get >/dev/null; then
    apt-get update -qq && apt-get install -y -qq python3-pip python3-venv python3-dev build-essential
elif command -v yum >/dev/null; then
    yum install -y -q python3-pip python3-devel gcc
fi

# 3. Setup Virtual Environment
echo "[3/6] Setting up Python virtual environment..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip -q
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q

# 4. Configure Agent
echo "[4/6] Configuring agent..."
if [ ! -f "$INSTALL_DIR/config.yaml" ]; then
    cp "$INSTALL_DIR/config.yaml.example" "$INSTALL_DIR/config.yaml" 2>/dev/null || true
fi

if [ -n "$API_KEY" ]; then
    # Update API key in config if provided
    sed -i "s/api_key: .*/api_key: \"$API_KEY\"/" "$INSTALL_DIR/config.yaml"
fi
sed -i "s|server_url: .*|server_url: \"$SERVER_URL\"|" "$INSTALL_DIR/config.yaml"

# 5. Create systemd service
echo "[5/6] Registering systemd service..."
cat <<EOF > /etc/systemd/system/patchguard-agent.service
[Unit]
Description=PatchGuard Device Management Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment=PYTHONPATH=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/agent.py
Restart=always
RestartSec=10
StandardOutput=append:$LOG_DIR/agent.log
StandardError=append:$LOG_DIR/agent.log

[Install]
WantedBy=multi-user.target
EOF

# 6. Start Service
echo "[6/6] Starting agent..."
systemctl daemon-reload
systemctl enable patchguard-agent
systemctl start patchguard-agent

echo "--- Installation Complete ---"
echo "Status: $(systemctl is-active patchguard-agent)"
echo "Logs: tail -f $LOG_DIR/agent.log"
