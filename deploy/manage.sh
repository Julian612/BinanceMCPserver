#!/bin/bash
# Verwaltet alle MCP-Services auf diesem Host.
# Usage: ./manage.sh [start|stop|status|restart] [service|all]
#
# Beispiele:
#   ./manage.sh start all
#   ./manage.sh restart binance-mcp
#   ./manage.sh status

set -euo pipefail

SERVICES=("binance-mcp")   # Erweiterbar um weitere MCP-Services

usage() {
    echo "Usage: $0 [start|stop|status|restart] [service|all]"
    echo ""
    echo "Verfügbare Services: ${SERVICES[*]}"
    echo ""
    echo "Beispiele:"
    echo "  $0 start all"
    echo "  $0 restart binance-mcp"
    echo "  $0 status"
    exit 1
}

run_for_service() {
    local action="$1"
    local svc="$2"
    echo ">> systemctl $action $svc"
    systemctl "$action" "$svc"
}

ACTION="${1:-status}"
TARGET="${2:-all}"

case "$ACTION" in
    start|stop|status|restart) ;;
    *) echo "Unbekannte Aktion: $ACTION"; usage ;;
esac

if [[ "$TARGET" == "all" ]]; then
    for svc in "${SERVICES[@]}"; do
        run_for_service "$ACTION" "$svc"
    done
else
    # Prüfen ob Service bekannt ist
    found=false
    for svc in "${SERVICES[@]}"; do
        if [[ "$svc" == "$TARGET" ]]; then
            found=true
            break
        fi
    done
    if [[ "$found" == false ]]; then
        echo "Unbekannter Service: $TARGET"
        echo "Verfügbare Services: ${SERVICES[*]}"
        exit 1
    fi
    run_for_service "$ACTION" "$TARGET"
fi
