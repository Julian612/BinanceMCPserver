"""
Spot trading tools – API key required for all functions.
"""

from __future__ import annotations

import ccxt
from binance_mcp.client import has_credentials, spot_client
from binance_mcp.utils.formatting import fmt_order

_NO_CREDS = {"error": "API credentials not configured.", "type": "AuthenticationError"}


async def place_spot_order(
    symbol: str,
    side: str,
    order_type: str,
    amount: float,
    price: float | None = None,
) -> dict:
    """
    Place a spot market or limit order.

    Args:
        symbol: Trading pair, e.g. 'BTC/USDT'.
        side: 'buy' or 'sell'.
        order_type: 'market' or 'limit'.
        amount: Order quantity in base asset.
        price: Limit price (required for limit orders, ignored for market orders).

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
        async with spot_client() as exchange:
            raw = await exchange.create_order(
                symbol, order_type, side, amount, price
            )
            return fmt_order(raw)
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}


async def cancel_spot_order(symbol: str, order_id: str) -> dict:
    """
    Cancel an open spot order by ID.

    Args:
        symbol: Trading pair, e.g. 'BTC/USDT'.
        order_id: The order ID string as returned by place_spot_order or get_open_orders.

    Returns:
        Cancellation confirmation dict, or 'error'/'type' on failure.
    """
    if not has_credentials():
        return _NO_CREDS

    try:
        async with spot_client() as exchange:
            raw = await exchange.cancel_order(order_id, symbol)
            return {
                "cancelled": True,
                "order_id": raw.get("id"),
                "symbol": raw.get("symbol"),
                "status": raw.get("status"),
            }
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}


async def cancel_all_spot_orders(symbol: str | None = None) -> dict:
    """
    Cancel all open spot orders, optionally filtered to a single symbol.

    Args:
        symbol: Trading pair to filter by, e.g. 'BTC/USDT'.
                If None, cancels all open orders across all symbols.

    Returns:
        Dict with 'cancelled_count' and list of cancelled order IDs,
        or 'error'/'type' on failure.
    """
    if not has_credentials():
        return _NO_CREDS

    try:
        async with spot_client() as exchange:
            if symbol:
                result = await exchange.cancel_all_orders(symbol)
                cancelled = result if isinstance(result, list) else [result]
            else:
                open_orders = await exchange.fetch_open_orders()
                cancelled = []
                for order in open_orders:
                    try:
                        r = await exchange.cancel_order(order["id"], order["symbol"])
                        cancelled.append(r)
                    except ccxt.BaseError:
                        pass

            return {
                "cancelled_count": len(cancelled),
                "symbol": symbol,
                "cancelled_ids": [o.get("id") for o in cancelled if isinstance(o, dict)],
            }
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}
