#!/usr/bin/env bash
# =============================================================================
#  Binance MCP Server – Proxmox LXC Installer
#  Usage (one-liner):
#    bash -c "$(curl -fsSL https://raw.githubusercontent.com/Julian612/BinanceMCPserver/main/install.sh)"
#
#  Supported OS: Debian 11/12, Ubuntu 22.04/24.04
#  Requires: root or sudo
# =============================================================================
set -euo pipefail

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Colour

REPO_URL="https://github.com/Julian612/BinanceMCPserver.git"
INSTALL_DIR="/opt/binance-mcp"
SERVICE_NAME="binance-mcp"
SERVICE_USER="mcpuser"
LOG_FILE="/var/log/binance-mcp-install.log"
UV_BIN=""

# ── Logging ───────────────────────────────────────────────────────────────────
log()  { echo -e "${GREEN}[✓]${NC} $*" | tee -a "$LOG_FILE"; }
info() { echo -e "${BLUE}[i]${NC} $*" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YELLOW}[!]${NC} $*" | tee -a "$LOG_FILE"; }
die()  { echo -e "${RED}[✗]${NC} $*" | tee -a "$LOG_FILE"; exit 1; }

step() {
  echo "" | tee -a "$LOG_FILE"
  echo -e "${BOLD}${BLUE}━━━ $* ━━━${NC}" | tee -a "$LOG_FILE"
}

# ── Banner ────────────────────────────────────────────────────────────────────
print_banner() {
  echo ""
  echo -e "${BOLD}${GREEN}"
  echo "  ██████╗ ██╗███╗   ██╗ █████╗ ███╗   ██╗ ██████╗███████╗"
  echo "  ██╔══██╗██║████╗  ██║██╔══██╗████╗  ██║██╔════╝██╔════╝"
  echo "  ██████╔╝██║██╔██╗ ██║███████║██╔██╗ ██║██║     █████╗  "
  echo "  ██╔══██╗██║██║╚██╗██║██╔══██║██║╚██╗██║██║     ██╔══╝  "
  echo "  ██████╔╝██║██║ ╚████║██║  ██║██║ ╚████║╚██████╗███████╗"
  echo "  ╚═════╝ ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝╚══════╝"
  echo -e "${NC}"
  echo -e "  ${BOLD}MCP Server Installer${NC}  –  FastMCP + ccxt + Binance API"
  echo -e "  ${BLUE}https://github.com/Julian612/BinanceMCPserver${NC}"
  echo ""
}

# ── Root check ────────────────────────────────────────────────────────────────
check_root() {
  if [[ "$EUID" -ne 0 ]]; then
    die "This installer must be run as root. Try: sudo bash install.sh"
  fi
}

# ── OS detection ──────────────────────────────────────────────────────────────
check_os() {
  step "Checking operating system"
  if [[ ! -f /etc/os-release ]]; then
    die "Cannot detect OS. Only Debian/Ubuntu are supported."
  fi
  source /etc/os-release
  case "$ID" in
    debian|ubuntu) log "Detected: $PRETTY_NAME" ;;
    *) die "Unsupported OS: $PRETTY_NAME. Only Debian/Ubuntu are supported." ;;
  esac
}

# ── Apt dependencies ──────────────────────────────────────────────────────────
install_system_deps() {
  step "Installing system dependencies"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq >> "$LOG_FILE" 2>&1
  apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    ca-certificates >> "$LOG_FILE" 2>&1
  log "System packages installed."
}

# ── uv ────────────────────────────────────────────────────────────────────────
install_uv() {
  step "Installing uv (Python package manager)"
  if command -v uv &>/dev/null; then
    UV_BIN="$(command -v uv)"
    log "uv already installed at $UV_BIN"
    return
  fi

  # Install uv for root, binary lands in /root/.cargo/bin or /root/.local/bin
  curl -LsSf https://astral.sh/uv/install.sh | sh >> "$LOG_FILE" 2>&1

  # Locate the binary
  for candidate in /root/.local/bin/uv /root/.cargo/bin/uv /usr/local/bin/uv; do
    if [[ -x "$candidate" ]]; then
      UV_BIN="$candidate"
      break
    fi
  done

  if [[ -z "$UV_BIN" ]]; then
    die "uv installation succeeded but binary not found. Check $LOG_FILE for details."
  fi

  # Make uv globally accessible
  ln -sf "$UV_BIN" /usr/local/bin/uv
  UV_BIN="/usr/local/bin/uv"
  log "uv installed at $UV_BIN"
}

# ── System user ───────────────────────────────────────────────────────────────
create_service_user() {
  step "Creating service user '$SERVICE_USER'"
  if id "$SERVICE_USER" &>/dev/null; then
    warn "User '$SERVICE_USER' already exists – skipping."
  else
    useradd --system --no-create-home --shell /bin/false "$SERVICE_USER"
    log "User '$SERVICE_USER' created."
  fi
}

# ── Clone / update repo ───────────────────────────────────────────────────────
clone_repo() {
  step "Setting up repository in $INSTALL_DIR"
  if [[ -d "$INSTALL_DIR/.git" ]]; then
    info "Repository already exists – pulling latest changes."
    git -C "$INSTALL_DIR" pull --ff-only >> "$LOG_FILE" 2>&1
    log "Repository updated."
  else
    mkdir -p "$INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR" >> "$LOG_FILE" 2>&1
    log "Repository cloned to $INSTALL_DIR."
  fi
}

# ── Python venv + dependencies ────────────────────────────────────────────────
setup_venv() {
  step "Creating virtual environment and installing dependencies"
  cd "$INSTALL_DIR"
  "$UV_BIN" venv --python python3 >> "$LOG_FILE" 2>&1
  "$UV_BIN" sync >> "$LOG_FILE" 2>&1
  log "Python environment ready."
}

# ── API key configuration ─────────────────────────────────────────────────────
configure_env() {
  step "Configuring API credentials"

  local env_file="$INSTALL_DIR/.env"

  if [[ -f "$env_file" ]]; then
    warn ".env already exists at $env_file"
    read -rp "  Overwrite existing .env? [y/N]: " overwrite
    if [[ ! "$overwrite" =~ ^[Yy]$ ]]; then
      info "Keeping existing .env."
      return
    fi
  fi

  echo ""
  echo -e "  ${YELLOW}Enter your Binance API credentials.${NC}"
  echo -e "  ${BLUE}Leave blank to skip (you can edit $env_file later).${NC}"
  echo ""

  read -rp "  BINANCE_API_KEY    : " api_key
  read -rsp "  BINANCE_API_SECRET : " api_secret
  echo ""

  local testnet="false"
  read -rp "  Use Binance Testnet? [y/N]: " use_testnet
  if [[ "$use_testnet" =~ ^[Yy]$ ]]; then
    testnet="true"
    warn "Testnet mode ENABLED – no real funds will be used."
  fi

  cat > "$env_file" <<EOF
BINANCE_API_KEY=${api_key}
BINANCE_API_SECRET=${api_secret}
BINANCE_TESTNET=${testnet}
EOF

  chmod 600 "$env_file"
  log ".env written and secured (chmod 600)."
}

# ── File permissions ──────────────────────────────────────────────────────────
set_permissions() {
  step "Setting file ownership"
  chown -R "$SERVICE_USER":"$SERVICE_USER" "$INSTALL_DIR"
  log "Ownership set to $SERVICE_USER."
}

# ── systemd service ───────────────────────────────────────────────────────────
install_service() {
  step "Installing systemd service"

  local service_src="$INSTALL_DIR/deploy/binance-mcp.service"
  local service_dst="/etc/systemd/system/${SERVICE_NAME}.service"

  if [[ ! -f "$service_src" ]]; then
    die "Service file not found at $service_src. Clone may be incomplete."
  fi

  cp "$service_src" "$service_dst"
  systemctl daemon-reload >> "$LOG_FILE" 2>&1
  systemctl enable "$SERVICE_NAME" >> "$LOG_FILE" 2>&1
  systemctl restart "$SERVICE_NAME" >> "$LOG_FILE" 2>&1

  # Give it a moment to start
  sleep 2

  if systemctl is-active --quiet "$SERVICE_NAME"; then
    log "Service '$SERVICE_NAME' is running."
  else
    warn "Service did not start cleanly. Check: journalctl -u $SERVICE_NAME -n 30"
  fi
}

# ── Final summary ─────────────────────────────────────────────────────────────
print_summary() {
  local python_bin="$INSTALL_DIR/.venv/bin/python"

  echo ""
  echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BOLD}${GREEN}  ✓  Binance MCP Server installed successfully!${NC}"
  echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  echo -e "  ${BOLD}Service control:${NC}"
  echo -e "    systemctl status  $SERVICE_NAME"
  echo -e "    systemctl restart $SERVICE_NAME"
  echo -e "    journalctl -u $SERVICE_NAME -f"
  echo ""
  echo -e "  ${BOLD}Edit API keys:${NC}"
  echo -e "    nano $INSTALL_DIR/.env"
  echo -e "    systemctl restart $SERVICE_NAME"
  echo ""
  echo -e "  ${BOLD}MCP Client config (Claude Desktop / Cline / OpenClaw):${NC}"
  echo -e "  ${BLUE}Add to your mcpServers config:${NC}"
  echo ""
  echo    '  {'
  echo    '    "mcpServers": {'
  echo    '      "binance": {'
  echo -e "        \"command\": \"${python_bin}\","
  echo -e "        \"args\": [\"${INSTALL_DIR}/server.py\"]"
  echo    '      }'
  echo    '    }'
  echo    '  }'
  echo ""
  echo -e "  ${BOLD}Install log:${NC} $LOG_FILE"
  echo ""
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
  # Initialise log file
  mkdir -p "$(dirname "$LOG_FILE")"
  echo "=== Binance MCP Install – $(date) ===" > "$LOG_FILE"

  print_banner
  check_root
  check_os
  install_system_deps
  install_uv
  create_service_user
  clone_repo
  setup_venv
  configure_env
  set_permissions
  install_service
  print_summary
}

main "$@"
