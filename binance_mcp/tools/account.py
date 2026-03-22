"""
Account & portfolio tools – API key required for all functions.
"""

from __future__ import annotations

import ccxt
from binance_mcp.client import futures_client, has_credentials, options_client, spot_client
from binance_mcp.utils.formatting import fmt_balance, fmt_order, fmt_position

_NO_CREDS = {"error": "API credentials not configured.", "type": "AuthenticationError"}


async def get_balance(market_type: str = "spot") -> dict:
    """
    Fetch account balance for a given market type, returning only non-zero assets.

    Args:
        market_type: One of 'spot', 'future', 'option' (default 'spot').

    Returns:
        Dict with 'assets' list of non-zero balances (asset, total, free, used),
        or 'error'/'type' on failure.
    """
    if not has_credentials():
        return _NO_CREDS

    _client_map = {
        "spot": spot_client,
        "future": futures_client,
        "option": options_client,
    }
    client_fn = _client_map.get(market_type, spot_client)

    try:
        async with client_fn() as exchange:
            raw = await exchange.fetch_balance()
            result = fmt_balance(raw)
            result["market_type"] = market_type
            return result
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}


async def get_open_orders(symbol: str | None = None, market_type: str = "spot") -> dict:
    """
    Fetch all currently open orders, optionally filtered by symbol.

    Args:
        symbol: Trading pair to filter by, e.g. 'BTC/USDT'. None returns all symbols.
        market_type: One of 'spot', 'future', 'option' (default 'spot').

    Returns:
        Dict with 'orders' list of open order dicts,
        or 'error'/'type' on failure.
    """
    if not has_credentials():
        return _NO_CREDS

    _client_map = {
        "spot": spot_client,
        "future": futures_client,
        "option": options_client,
    }
    client_fn = _client_map.get(market_type, spot_client)

    try:
        async with client_fn() as exchange:
            raw_orders = await exchange.fetch_open_orders(symbol)
            return {
                "symbol": symbol,
                "market_type": market_type,
                "count": len(raw_orders),
                "orders": [fmt_order(o) for o in raw_orders],
            }
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}


async def get_order_history(
    symbol: str,
    market_type: str = "spot",
    limit: int = 50,
) -> dict:
    """
    Fetch historical orders for a symbol (both filled and cancelled).

    Args:
        symbol: Trading pair, e.g. 'BTC/USDT'.
        market_type: One of 'spot', 'future', 'option' (default 'spot').
        limit: Maximum number of orders to return (default 50).

    Returns:
        Dict with 'orders' list of order dicts sorted newest first,
        or 'error'/'type' on failure.
    """
    if not has_credentials():
        return _NO_CREDS

    _client_map = {
        "spot": spot_client,
        "future": futures_client,
        "option": options_client,
    }
    client_fn = _client_map.get(market_type, spot_client)

    try:
        async with client_fn() as exchange:
            raw_orders = await exchange.fetch_orders(symbol, limit=limit)
            return {
                "symbol": symbol,
                "market_type": market_type,
                "count": len(raw_orders),
                "orders": [fmt_order(o) for o in raw_orders],
            }
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}


async def get_positions(symbol: str | None = None) -> dict:
    """
    Fetch all open futures positions with unrealized PnL.

    Args:
        symbol: Filter to a specific symbol, e.g. 'BTC/USDT'. None returns all positions.

    Returns:
        Dict with 'positions' list of position dicts including unrealized PnL,
        or 'error'/'type' on failure.
    """
    if not has_credentials():
        return _NO_CREDS

    try:
        async with futures_client() as exchange:
            symbols = [symbol] if symbol else None
            raw_positions = await exchange.fetch_positions(symbols)
            open_positions = [
                fmt_position(p)
                for p in raw_positions
                if float(p.get("contracts") or 0) != 0
            ]
            return {
                "symbol": symbol,
                "count": len(open_positions),
                "positions": open_positions,
            }
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}


async def get_pnl_summary() -> dict:
    """
    Fetch a summary of unrealized and realized PnL across all open futures positions.

    Returns:
        Dict with total_unrealized_pnl, total_positions count, and per-position breakdown,
        or 'error'/'type' on failure.
    """
    if not has_credentials():
        return _NO_CREDS

    try:
        async with futures_client() as exchange:
            raw_positions = await exchange.fetch_positions()
            open_positions = [
                fmt_position(p)
                for p in raw_positions
                if float(p.get("contracts") or 0) != 0
            ]
            total_unrealized = sum(
                float(p.get("unrealized_pnl") or 0) for p in open_positions
            )
            return {
                "total_unrealized_pnl": round(total_unrealized, 4),
                "total_positions": len(open_positions),
                "positions": open_positions,
            }
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}
