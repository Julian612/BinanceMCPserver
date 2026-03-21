"""
Binance MCP Server – Einstiegspunkt.

Startet einen FastMCP-Server im stdio-Modus mit allen Trading-Tools
für Spot, USD-M Futures, Options und Marktdaten.

Logging geht ausschliesslich nach stderr, um das stdio MCP-Protokoll
nicht zu stören.
"""

import logging
import sys

from mcp.server.fastmcp import FastMCP

from binance_mcp.tools import account, futures, market_data, options, spot

# Logging NUR nach stderr – stdout ist für das MCP-Protokoll reserviert
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# FastMCP-Instanz
mcp = FastMCP("binance-trading")

# ── Marktdaten (öffentlich) ────────────────────────────────────────────────
mcp.tool()(market_data.get_price)
mcp.tool()(market_data.get_ticker)
mcp.tool()(market_data.get_orderbook)
mcp.tool()(market_data.get_ohlcv)
mcp.tool()(market_data.get_markets)
mcp.tool()(market_data.search_symbols)

# ── Account & Portfolio ────────────────────────────────────────────────────
mcp.tool()(account.get_balance)
mcp.tool()(account.get_open_orders)
mcp.tool()(account.get_order_history)
mcp.tool()(account.get_positions)
mcp.tool()(account.get_pnl_summary)

# ── Spot Trading ───────────────────────────────────────────────────────────
mcp.tool()(spot.place_spot_order)
mcp.tool()(spot.cancel_spot_order)
mcp.tool()(spot.cancel_all_spot_orders)

# ── USD-M Futures Trading ──────────────────────────────────────────────────
mcp.tool()(futures.place_futures_order)
mcp.tool()(futures.cancel_futures_order)
mcp.tool()(futures.set_leverage)
mcp.tool()(futures.set_margin_mode)
mcp.tool()(futures.close_position)

# ── Options Trading ────────────────────────────────────────────────────────
mcp.tool()(options.get_option_chain)
mcp.tool()(options.place_options_order)
mcp.tool()(options.cancel_options_order)


def main() -> None:
    """Startet den MCP Server im stdio-Modus."""
    logger.info("Binance MCP Server wird gestartet (stdio)…")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
