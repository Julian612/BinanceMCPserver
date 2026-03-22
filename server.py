"""
Binance MCP Server – entry point.

Runs via stdio so ALL logging goes exclusively to stderr.
Never write to stdout – it breaks the MCP protocol.
"""

import logging
import sys

from mcp.server.fastmcp import FastMCP

from binance_mcp.tools import account, futures, market_data, options, spot

# ── Logging: stderr only ──────────────────────────────────────────────────────
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("binance-mcp")

# ── FastMCP server ────────────────────────────────────────────────────────────
mcp = FastMCP("binance-trading")

# ── Market Data tools (public) ────────────────────────────────────────────────
mcp.tool()(market_data.get_price)
mcp.tool()(market_data.get_ticker)
mcp.tool()(market_data.get_orderbook)
mcp.tool()(market_data.get_ohlcv)
mcp.tool()(market_data.get_markets)
mcp.tool()(market_data.search_symbols)

# ── Account tools ─────────────────────────────────────────────────────────────
mcp.tool()(account.get_balance)
mcp.tool()(account.get_open_orders)
mcp.tool()(account.get_order_history)
mcp.tool()(account.get_positions)
mcp.tool()(account.get_pnl_summary)

# ── Spot trading tools ────────────────────────────────────────────────────────
mcp.tool()(spot.place_spot_order)
mcp.tool()(spot.cancel_spot_order)
mcp.tool()(spot.cancel_all_spot_orders)

# ── Futures trading tools ─────────────────────────────────────────────────────
mcp.tool()(futures.place_futures_order)
mcp.tool()(futures.cancel_futures_order)
mcp.tool()(futures.set_leverage)
mcp.tool()(futures.set_margin_mode)
mcp.tool()(futures.close_position)

# ── Options trading tools ─────────────────────────────────────────────────────
mcp.tool()(options.get_option_chain)
mcp.tool()(options.place_options_order)
mcp.tool()(options.cancel_options_order)


def main() -> None:
    """Start the MCP server on stdio transport."""
    logger.info("Binance MCP Server starting (stdio transport)…")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
