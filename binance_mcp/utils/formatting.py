"""
Response formatting helpers.

Normalise raw ccxt dicts into clean, consistent structures
that are safe to return from MCP tool functions (no raw API keys,
no internal ccxt metadata noise).
"""

from __future__ import annotations

from typing import Any


def fmt_order(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Normalise a ccxt order dict to a clean MCP-friendly structure.

    Args:
        raw: Raw order dict as returned by ccxt.

    Returns:
        Cleaned order dict with standardised keys.
    """
    return {
        "id": raw.get("id"),
        "symbol": raw.get("symbol"),
        "side": raw.get("side"),
        "type": raw.get("type"),
        "status": raw.get("status"),
        "amount": raw.get("amount"),
        "price": raw.get("price"),
        "average": raw.get("average"),
        "filled": raw.get("filled"),
        "remaining": raw.get("remaining"),
        "cost": raw.get("cost"),
        "timestamp": raw.get("timestamp"),
        "datetime": raw.get("datetime"),
        "reduce_only": raw.get("reduceOnly"),
        "time_in_force": raw.get("timeInForce"),
    }


def fmt_position(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Normalise a ccxt position dict to a clean MCP-friendly structure.

    Args:
        raw: Raw position dict as returned by ccxt.

    Returns:
        Cleaned position dict with standardised keys.
    """
    return {
        "symbol": raw.get("symbol"),
        "side": raw.get("side"),
        "size": raw.get("contracts"),
        "notional": raw.get("notional"),
        "entry_price": raw.get("entryPrice"),
        "mark_price": raw.get("markPrice"),
        "liquidation_price": raw.get("liquidationPrice"),
        "leverage": raw.get("leverage"),
        "margin_mode": raw.get("marginMode"),
        "unrealized_pnl": raw.get("unrealizedPnl"),
        "percentage": raw.get("percentage"),
        "collateral": raw.get("collateral"),
        "margin_ratio": raw.get("marginRatio"),
    }


def fmt_balance(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Filter and format a ccxt balance dict, returning only non-zero assets.

    Args:
        raw: Raw balance dict as returned by ccxt (contains 'total', 'free', 'used').

    Returns:
        Dict with 'assets' list (non-zero only) and summary totals.
    """
    total: dict = raw.get("total", {})
    free: dict = raw.get("free", {})
    used: dict = raw.get("used", {})

    assets = []
    for currency, amount in total.items():
        if currency in ("info", "timestamp", "datetime", "free", "used", "total"):
            continue
        try:
            if float(amount or 0) > 0:
                assets.append(
                    {
                        "asset": currency,
                        "total": float(amount or 0),
                        "free": float(free.get(currency) or 0),
                        "used": float(used.get(currency) or 0),
                    }
                )
        except (TypeError, ValueError):
            continue

    return {"assets": sorted(assets, key=lambda x: x["total"], reverse=True)}
