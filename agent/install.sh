#!/bin/bash

# PatchGuard Agent Installer for Linux (systemd)
# Usage: sudo ./install.sh <api_key> <server_url>

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

API_KEY=${1:-"default_key"}
SERVER_URL=${2:-"ws://localhost:8001/ws/agents"}
INSTALL_DIR="/opt/patchguard-agent"

echo "Installing PatchGuard Agent to $INSTALL_DIR..."

mkdir -p $INSTALL_DIR
cp -r . $INSTALL_DIR/

# Install dependencies
apt-get update && apt-get install -y python3-pip python3-venv
python3 -m venv $INSTALL_DIR/venv
$INSTALL_DIR/venv/bin/pip install -r $INSTALL_DIR/requirements.txt

# Create systemd service
cat <<EOF > /etc/systemd/system/patchguard-agent.service
[Unit]
Description=PatchGuard Device Management Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable patchguard-agent
# systemctl start patchguard-agent

echo "PatchGuard Agent installed successfully!"
echo "Service is enabled but not started. Edit $INSTALL_DIR/config.yaml if needed, then run: systemctl start patchguard-agent"
