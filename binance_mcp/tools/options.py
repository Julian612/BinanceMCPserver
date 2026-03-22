"""
Options trading tools – API key required for authenticated functions.
get_option_chain is public (no auth needed).
"""

from __future__ import annotations

import ccxt
from binance_mcp.client import has_credentials, options_client
from binance_mcp.utils.formatting import fmt_order

_NO_CREDS = {"error": "API credentials not configured.", "type": "AuthenticationError"}


async def get_option_chain(underlying: str) -> dict:
    """
    Fetch all available option contracts for an underlying asset.

    Args:
        underlying: Base asset symbol, e.g. 'BTC' or 'ETH'.

    Returns:
        Dict with 'contracts' list of available option symbols, grouped by expiry,
        or 'error'/'type' on failure.
    """
    underlying = underlying.upper()

    try:
        async with options_client() as exchange:
            markets = await exchange.load_markets()
            contracts = [
                {
                    "symbol": m.get("symbol"),
                    "id": m.get("id"),
                    "base": m.get("base"),
                    "quote": m.get("quote"),
                    "expiry": m.get("expiry"),
                    "strike": m.get("strike"),
                    "option_type": m.get("optionType"),
                    "active": m.get("active"),
                }
                for m in markets.values()
                if (m.get("base") or "").upper() == underlying
                and m.get("type") == "option"
            ]

            contracts.sort(key=lambda x: (x.get("expiry") or "", x.get("strike") or 0))

            return {
                "underlying": underlying,
                "count": len(contracts),
                "contracts": contracts,
            }
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}


async def place_options_order(
    symbol: str,
    side: str,
    order_type: str,
    amount: float,
    price: float | None = None,
) -> dict:
    """
    Place an options order (buy or sell a contract).

    Args:
        symbol: Full option symbol, e.g. 'BTC/USDT-240329-70000-C'.
        side: 'buy' or 'sell'.
        order_type: 'market' or 'limit'.
        amount: Number of contracts.
        price: Limit price per contract (required for limit orders).

    Returns:
        Normalised order dict, or 'error'/'type' on failure.
    """
    if not has_credentials():
        return _NO_CREDS

    side = side.lower()
    order_type = order_type.lower()

    if side not in ("buy", "sell"):
        return {"error": f"Invalid side '{side}'. Must be 'buy' or 'sell'.", "type": "ValueError"}
    if order_type not in ("market", "limit"):
        return {"error": f"Invalid order_type '{order_type}'. Must be 'market' or 'limit'.", "type": "ValueError"}
    if order_type == "limit" and price is None:
        return {"error": "Price is required for limit orders.", "type": "ValueError"}

    try:
        async with options_client() as exchange:
            raw = await exchange.create_order(symbol, order_type, side, amount, price)
            return fmt_order(raw)
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}


async def cancel_options_order(symbol: str, order_id: str) -> dict:
    """
    Cancel an open options order by ID.

    Args:
        symbol: Full option symbol, e.g. 'BTC/USDT-240329-70000-C'.
        order_id: The order ID string as returned by place_options_order.

    Returns:
        Cancellation confirmation dict, or 'error'/'type' on failure.
    """
    if not has_credentials():
        return _NO_CREDS

    try:
        async with options_client() as exchange:
            raw = await exchange.cancel_order(order_id, symbol)
            return {
                "cancelled": True,
                "order_id": raw.get("id"),
                "symbol": raw.get("symbol"),
                "status": raw.get("status"),
            }
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}
