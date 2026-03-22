#!/usr/bin/env bash

# Author: Julian612
# License: MIT
# Source: https://github.com/Julian612/BinanceMCPserver

source /dev/stdin <<<"$FUNCTIONS_FILE_PATH"
color
verb_ip6
catch_errors
setting_up_container
network_check
update_os

msg_info "Installing Dependencies"
$STD apt-get install -y \
  curl \
  git \
  python3 \
  python3-pip \
  python3-venv \
  build-essential \
  ca-certificates
msg_ok "Installed Dependencies"

msg_info "Installing uv (Python package manager)"
$STD curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR="/usr/local/bin" sh
msg_ok "Installed uv"

msg_info "Cloning Binance MCP Server"
$STD git clone --branch main --single-branch \
  https://github.com/Julian612/BinanceMCPserver /opt/binance-mcp
msg_ok "Cloned Repository"

msg_info "Setting up Python environment"
cd /opt/binance-mcp
$STD uv venv
$STD uv sync
msg_ok "Python environment ready"

msg_info "Creating mcpuser and configuring permissions"
$STD useradd -r -s /bin/false -d /opt/binance-mcp mcpuser
cp /opt/binance-mcp/.env.example /opt/binance-mcp/.env
chmod 600 /opt/binance-mcp/.env
$STD chown -R mcpuser:mcpuser /opt/binance-mcp
msg_ok "Created mcpuser"

msg_info "Creating Service"
$STD cp /opt/binance-mcp/deploy/binance-mcp.service /etc/systemd/system/
$STD systemctl daemon-reload
$STD systemctl enable binance-mcp
msg_ok "Created Service (configure /opt/binance-mcp/.env before starting)"

motd_ssh
customize
cleanup_lxc
