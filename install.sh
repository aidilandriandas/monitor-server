#!/usr/bin/env bash
# ==============================================================================
# 🚀 SENTINEL NOC AGENT - 1-COMMAND AUTO-INSTALLER
# ==============================================================================
# Usage:
#   curl -sSL http://10.10.10.9:8888/install.sh | sudo bash
# ==============================================================================
set -e

SERVER_URL="${MONITOR_SERVER_URL:-http://10.10.10.9:8888}"
AGENT_URL="${SERVER_URL}/agent.py"
INSTALL_DIR="/opt/sentinel-agent"
SERVICE_FILE="/etc/systemd/system/sentinel-agent.service"

# Visual Banner
clear 2>/dev/null || true
echo -e "\033[1;36m"
echo "  ╔══════════════════════════════════════════════════════════════════╗"
echo "  ║            🛡️  AEGIS NOC - NODE AGENT AUTO-INSTALLER             ║"
echo "  ║      High-Fidelity Telemetry Daemon for Linux & Proxmox VE       ║"
echo "  ║              Engineered by AIDIL ANDRIANDAS                      ║"
echo "  ╚══════════════════════════════════════════════════════════════════╝"
echo -e "\033[0m"

echo -e "\033[1;34m[INFO]\033[0m Target Aegis Server    : \033[1;32m${SERVER_URL}\033[0m"
echo -e "\033[1;34m[INFO]\033[0m Current Node Hostname  : \033[1;37m$(hostname)\033[0m"

# 1. Check Root Privileges
if [ "$EUID" -ne 0 ]; then
  echo -e "\n\033[1;31m[ERROR]\033[0m Please run this installer as root or with sudo:"
  if command -v sudo &> /dev/null; then
    echo -e "        \033[1;33mcurl -sSL ${SERVER_URL}/install.sh | sudo bash\033[0m\n"
  else
    echo -e "        \033[1;33msu -c \"curl -sSL ${SERVER_URL}/install.sh | bash\"\033[0m\n"
  fi
  exit 1
fi

# 2. Check & Install Python 3 if missing
echo -e "\033[1;34m[1/5]\033[0m Checking Python 3 runtime..."
if ! command -v python3 &> /dev/null; then
    echo -e "      \033[1;33mPython 3 not found. Installing via system package manager...\033[0m"
    if command -v apt-get &> /dev/null; then
        apt-get update -y -qq && apt-get install -y -qq python3
    elif command -v yum &> /dev/null; then
        yum install -y -q python3
    elif command -v dnf &> /dev/null; then
        dnf install -y -q python3
    elif command -v apk &> /dev/null; then
        apk add --no-cache python3
    else
        echo -e "\033[1;31m[ERROR]\033[0m Package manager not supported. Please install python3 manually."
        exit 1
    fi
fi
PY_VER=$(python3 --version 2>&1)
echo -e "      \033[1;32m✔ Python runtime available: ${PY_VER}\033[0m"

# 3. Create Installation Directory
echo -e "\033[1;34m[2/5]\033[0m Preparing directory \033[1;37m${INSTALL_DIR}\033[0m..."
mkdir -p "${INSTALL_DIR}"

# 4. Download latest agent.py
echo -e "\033[1;34m[3/5]\033[0m Downloading Aegis Agent binary from \033[1;37m${AGENT_URL}\033[0m..."
if command -v curl &> /dev/null; then
    curl -sSL "${AGENT_URL}" -o "${INSTALL_DIR}/agent.py"
elif command -v wget &> /dev/null; then
    wget -q "${AGENT_URL}" -O "${INSTALL_DIR}/agent.py"
else
    python3 -c "import urllib.request; urllib.request.urlretrieve('${AGENT_URL}', '${INSTALL_DIR}/agent.py')"
fi

if [ ! -s "${INSTALL_DIR}/agent.py" ]; then
    echo -e "\033[1;31m[ERROR]\033[0m Failed to download agent.py from ${AGENT_URL}."
    exit 1
fi
chmod +x "${INSTALL_DIR}/agent.py"
echo -e "      \033[1;32m✔ Agent script installed and permissions granted.\033[0m"

# 5. Create Systemd Service
echo -e "\033[1;34m[4/5]\033[0m Creating systemd service \033[1;37m${SERVICE_FILE}\033[0m..."
cat <<EOF > "${SERVICE_FILE}"
[Unit]
Description=Aegis NOC Infrastructure Monitoring Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
Environment="MONITOR_SERVER_URL=${SERVER_URL}/api/v1/telemetry"
Environment="INTERVAL_SECONDS=5"
ExecStart=/usr/bin/python3 ${INSTALL_DIR}/agent.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 6. Enable and Start Agent Service
echo -e "\033[1;34m[5/5]\033[0m Starting & enabling Aegis Agent daemon..."
systemctl daemon-reload
systemctl enable --now sentinel-agent.service >/dev/null 2>&1

sleep 1.5
STATUS=$(systemctl is-active sentinel-agent.service 2>/dev/null || echo "unknown")

if [ "$STATUS" = "active" ]; then
    NODE_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    echo -e "\n\033[1;32m  🎉 SUCCESS! Aegis Agent is now ACTIVE and STREAMING!\033[0m"
    echo -e "  ══════════════════════════════════════════════════════════════════"
    echo -e "  Node Name   : \033[1;37m$(hostname)\033[0m"
    echo -e "  Node IP     : \033[1;37m${NODE_IP:-127.0.0.1}\033[0m"
    echo -e "  Service     : \033[1;32mactive (running)\033[0m"
    echo -e "  Dashboard   : \033[1;36m${SERVER_URL}\033[0m"
    echo -e "  ══════════════════════════════════════════════════════════════════"
    echo -e "  Check logs anytime with : \033[1;33mjournalctl -u sentinel-agent -f\033[0m"
    echo -e "  To stop agent           : \033[1;33msystemctl stop sentinel-agent\033[0m\n"
else
    echo -e "\n\033[1;31m[!] Service was created but reported status: ${STATUS}.\033[0m"
    echo -e "    Check logs: journalctl -u sentinel-agent -e\n"
fi
