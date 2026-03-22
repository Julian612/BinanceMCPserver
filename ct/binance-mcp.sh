#!/usr/bin/env bash
source <(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/misc/build.func)
# Author: Julian612
# License: MIT
# Source: https://github.com/Julian612/BinanceMCPserver

APP="Binance-MCP"
var_tags="${var_tags:-mcp;trading;finance}"
var_cpu="${var_cpu:-2}"
var_ram="${var_ram:-1024}"
var_disk="${var_disk:-8}"
var_os="${var_os:-debian}"
var_version="${var_version:-12}"
var_unprivileged="${var_unprivileged:-1}"
var_install="${var_install:-binance-mcp}"

header_info "$APP"
variables
color
catch_errors

function update_script() {
  header_info
  check_container_storage
  check_container_resources

  if [[ ! -d /opt/binance-mcp ]]; then
    msg_error "No ${APP} Installation Found!"
    exit
  fi

  msg_info "Stopping Service"
  systemctl stop binance-mcp
  msg_ok "Stopped Service"

  msg_info "Updating Repository"
  git -C /opt/binance-mcp pull
  msg_ok "Updated Repository"

  msg_info "Updating Python Dependencies"
  cd /opt/binance-mcp && uv sync
  msg_ok "Updated Python Dependencies"

  msg_info "Starting Service"
  systemctl start binance-mcp
  msg_ok "Started Service"

  msg_ok "Updated ${APP} successfully!"
  exit
}

start
build_container
description

msg_ok "Completed successfully!\n"
echo -e "${CREATING}${GN}${APP} setup has been successfully initialized!${CL}"
echo -e "${INFO}${YW} Next step: configure your API keys:${CL}"
echo -e "${TAB}${BGN}nano /opt/binance-mcp/.env${CL}"
echo -e "${INFO}${YW} Then start the service:${CL}"
echo -e "${TAB}${BGN}systemctl start binance-mcp${CL}"
echo -e "${INFO}${YW} MCP Client config (Claude Desktop / Cline):${CL}"
echo -e "${TAB}${BGN}command: /opt/binance-mcp/.venv/bin/python${CL}"
echo -e "${TAB}${BGN}args:    [\"/opt/binance-mcp/server.py\"]${CL}"
