#!/usr/bin/env bash
# =============================================================================
#  MCP Host Manager – central control for all MCP services on this host
#  Usage: ./manage.sh [start|stop|status|restart|logs] [service|all]
#
#  Add new MCP servers to the SERVICES array below.
# =============================================================================
set -euo pipefail

# ── Registered services ───────────────────────────────────────────────────────
SERVICES=("binance-mcp")   # Extend as you add more MCP servers

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

usage() {
  echo ""
  echo -e "  ${BOLD}MCP Host Manager${NC}"
  echo ""
  echo -e "  Usage: $0 [command] [service|all]"
  echo ""
  echo -e "  ${BOLD}Commands:${NC}"
  echo -e "    start    – Start service(s)"
  echo -e "    stop     – Stop service(s)"
  echo -e "    restart  – Restart service(s)"
  echo -e "    status   – Show service status"
  echo -e "    logs     – Follow live logs (Ctrl+C to exit)"
  echo ""
  echo -e "  ${BOLD}Services:${NC} ${SERVICES[*]}"
  echo -e "  Use 'all' to target every registered service."
  echo ""
  exit 1
}

resolve_targets() {
  local target="${1:-all}"
  if [[ "$target" == "all" ]]; then
    echo "${SERVICES[@]}"
  else
    # Validate the named service exists
    local found=false
    for svc in "${SERVICES[@]}"; do
      if [[ "$svc" == "$target" ]]; then
        found=true
        break
      fi
    done
    if [[ "$found" == false ]]; then
      echo -e "${YELLOW}[!]${NC} Unknown service '$target'. Known: ${SERVICES[*]}" >&2
      exit 1
    fi
    echo "$target"
  fi
}

cmd_start() {
  local targets
  read -ra targets <<< "$(resolve_targets "${1:-all}")"
  for svc in "${targets[@]}"; do
    echo -e "${GREEN}[✓]${NC} Starting ${BOLD}$svc${NC}…"
    systemctl start "$svc"
  done
}

cmd_stop() {
  local targets
  read -ra targets <<< "$(resolve_targets "${1:-all}")"
  for svc in "${targets[@]}"; do
    echo -e "${YELLOW}[!]${NC} Stopping ${BOLD}$svc${NC}…"
    systemctl stop "$svc"
  done
}

cmd_restart() {
  local targets
  read -ra targets <<< "$(resolve_targets "${1:-all}")"
  for svc in "${targets[@]}"; do
    echo -e "${BLUE}[i]${NC} Restarting ${BOLD}$svc${NC}…"
    systemctl restart "$svc"
  done
}

cmd_status() {
  local targets
  read -ra targets <<< "$(resolve_targets "${1:-all}")"
  for svc in "${targets[@]}"; do
    echo ""
    echo -e "${BOLD}━━━ $svc ━━━${NC}"
    systemctl status "$svc" --no-pager || true
  done
}

cmd_logs() {
  local target="${1:-all}"
  if [[ "$target" == "all" ]]; then
    # Interleave logs from all services
    journalctl -f $(printf -- '-u %s ' "${SERVICES[@]}")
  else
    journalctl -u "$target" -f
  fi
}

# ── Entry point ───────────────────────────────────────────────────────────────
COMMAND="${1:-}"
SERVICE="${2:-all}"

case "$COMMAND" in
  start)   cmd_start   "$SERVICE" ;;
  stop)    cmd_stop    "$SERVICE" ;;
  restart) cmd_restart "$SERVICE" ;;
  status)  cmd_status  "$SERVICE" ;;
  logs)    cmd_logs    "$SERVICE" ;;
  *)       usage ;;
esac
