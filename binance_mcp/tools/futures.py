"""
USD-M Futures trading tools – API key required for all functions.
"""

from __future__ import annotations

import ccxt
from binance_mcp.client import futures_client, has_credentials
from binance_mcp.utils.formatting import fmt_order, fmt_position

_NO_CREDS = {"error": "API credentials not configured.", "type": "AuthenticationError"}


async def place_futures_order(
    symbol: str,
    side: str,
    order_type: str,
    amount: float,
    price: float | None = None,
    reduce_only: bool = False,
) -> dict:
    """
    Place a USD-M futures order.

    Args:
        symbol: Trading pair, e.g. 'BTC/USDT'.
        side: 'buy' or 'sell'.
        order_type: 'market' or 'limit'.
        amount: Order quantity in base asset (contracts).
        price: Limit price (required for limit orders).
        reduce_only: If True, the order can only reduce an existing position.

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

    params: dict = {}
    if reduce_only:
        params["reduceOnly"] = True

    try:
        async with futures_client() as exchange:
            raw = await exchange.create_order(
                symbol, order_type, side, amount, price, params
            )
            return fmt_order(raw)
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}


async def cancel_futures_order(symbol: str, order_id: str) -> dict:
    """
    Cancel an open futures order by ID.

    Args:
        symbol: Trading pair, e.g. 'BTC/USDT'.
        order_id: The order ID string as returned by place_futures_order.

    Returns:
        Cancellation confirmation dict, or 'error'/'type' on failure.
    """
    if not has_credentials():
        return _NO_CREDS

    try:
        async with futures_client() as exchange:
            raw = await exchange.cancel_order(order_id, symbol)
            return {
                "cancelled": True,
                "order_id": raw.get("id"),
                "symbol": raw.get("symbol"),
                "status": raw.get("status"),
            }
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}


async def set_leverage(symbol: str, leverage: int) -> dict:
    """
    Set the leverage multiplier for a futures symbol.

    Args:
        symbol: Trading pair, e.g. 'BTC/USDT'.
        leverage: Leverage value between 1 and 125.

    Returns:
        Dict confirming the new leverage setting, or 'error'/'type' on failure.
    """
    if not has_credentials():
        return _NO_CREDS

    if not 1 <= leverage <= 125:
        return {
            "error": f"Leverage must be between 1 and 125, got {leverage}.",
            "type": "ValueError",
        }

    try:
        async with futures_client() as exchange:
            result = await exchange.set_leverage(leverage, symbol)
            return {
                "symbol": symbol,
                "leverage": leverage,
                "raw": result,
            }
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}


async def set_margin_mode(symbol: str, mode: str) -> dict:
    """
    Set the margin mode for a futures symbol.

    Args:
        symbol: Trading pair, e.g. 'BTC/USDT'.
        mode: 'isolated' or 'cross'.

    Returns:
        Dict confirming the margin mode change, or 'error'/'type' on failure.
    """
    if not has_credentials():
        return _NO_CREDS

    mode = mode.lower()
    if mode not in ("isolated", "cross"):
        return {
            "error": f"Invalid mode '{mode}'. Must be 'isolated' or 'cross'.",
            "type": "ValueError",
        }

    try:
        async with futures_client() as exchange:
            result = await exchange.set_margin_mode(mode, symbol)
            return {
                "symbol": symbol,
                "margin_mode": mode,
                "raw": result,
            }
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}


async def close_position(symbol: str, amount: float | None = None) -> dict:
    """
    Close an open futures position for a symbol.

    If amount is None, the entire position is closed.
    Uses a reduce_only market order on the opposite side.

    Args:
        symbol: Trading pair, e.g. 'BTC/USDT'.
        amount: Quantity to close. If None, closes the full position.

    Returns:
        Normalised order dict of the closing order, or 'error'/'type' on failure.
    """
    if not has_credentials():
        return _NO_CREDS

    try:
        async with futures_client() as exchange:
            positions = await exchange.fetch_positions([symbol])
            open_pos = [
                p for p in positions if float(p.get("contracts") or 0) != 0
            ]
            if not open_pos:
                return {"error": f"No open position found for {symbol}.", "type": "ValueError"}

            pos = open_pos[0]
            pos_side = pos.get("side", "long")
            close_side = "sell" if pos_side == "long" else "buy"
            close_amount = amount if amount is not None else abs(float(pos.get("contracts") or 0))

            raw = await exchange.create_order(
                symbol,
                "market",
                close_side,
                close_amount,
                None,
                {"reduceOnly": True},
            )
            return fmt_order(raw)
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}
