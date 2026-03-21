"""
Hilfsfunktionen für die Formatierung und Normalisierung von API-Responses.

Alle Funktionen geben strukturierte Dicts zurück, die direkt als
MCP Tool Response genutzt werden können.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import ccxt

logger = logging.getLogger(__name__)


def format_error(exc: Exception) -> dict[str, str]:
    """Konvertiert eine Exception in ein strukturiertes Fehler-Dict.

    API Keys und Secrets werden niemals in der Fehlermeldung ausgegeben.

    Args:
        exc: Die aufgetretene Exception.

    Returns:
        Dict mit 'error' (Meldung) und 'type' (Klassenname).
    """
    message = str(exc)
    # Sicherheitsmassnahme: API-Credentials aus Fehlermeldung entfernen
    import os

    for secret in (
        os.getenv("BINANCE_API_KEY", ""),
        os.getenv("BINANCE_API_SECRET", ""),
    ):
        if secret:
            message = message.replace(secret, "***REDACTED***")

    return {"error": message, "type": type(exc).__name__}


def format_ticker(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalisiert einen ccxt-Ticker in ein lesbares Dict.

    Args:
        raw: Roher ccxt-Ticker.

    Returns:
        Strukturierter Ticker mit den wichtigsten Feldern.
    """
    return {
        "symbol": raw.get("symbol"),
        "last": raw.get("last"),
        "bid": raw.get("bid"),
        "ask": raw.get("ask"),
        "high": raw.get("high"),
        "low": raw.get("low"),
        "volume": raw.get("baseVolume"),
        "quote_volume": raw.get("quoteVolume"),
        "change_24h": raw.get("change"),
        "change_pct_24h": raw.get("percentage"),
        "timestamp": _ts_to_iso(raw.get("timestamp")),
    }


def format_orderbook(raw: dict[str, Any], limit: int) -> dict[str, Any]:
    """Normalisiert ein ccxt-Orderbuch.

    Args:
        raw: Rohes ccxt-Orderbuch.
        limit: Maximale Anzahl Levels pro Seite.

    Returns:
        Dict mit 'bids', 'asks' und Metadaten.
    """
    return {
        "symbol": raw.get("symbol"),
        "timestamp": _ts_to_iso(raw.get("timestamp")),
        "bids": raw.get("bids", [])[:limit],
        "asks": raw.get("asks", [])[:limit],
        "bid_count": len(raw.get("bids", [])),
        "ask_count": len(raw.get("asks", [])),
    }


def format_ohlcv(raw_candles: list[list], symbol: str, timeframe: str) -> dict[str, Any]:
    """Konvertiert OHLCV-Rohdaten in ein strukturiertes Dict.

    Args:
        raw_candles: Liste von [timestamp, open, high, low, close, volume].
        symbol: Handelspaar.
        timeframe: Zeitrahmen (z.B. '1h').

    Returns:
        Dict mit Metadaten und Liste von Candle-Dicts.
    """
    candles = [
        {
            "timestamp": _ts_to_iso(c[0]),
            "open": c[1],
            "high": c[2],
            "low": c[3],
            "close": c[4],
            "volume": c[5],
        }
        for c in raw_candles
    ]
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "count": len(candles),
        "candles": candles,
    }


def format_balance(raw: dict[str, Any]) -> dict[str, Any]:
    """Filtert Balance-Daten auf non-zero Assets.

    Args:
        raw: Rohe ccxt-Balance.

    Returns:
        Dict mit 'total', 'free', 'used' nur für Assets mit Guthaben > 0.
    """
    total: dict[str, float] = {}
    free: dict[str, float] = {}
    used: dict[str, float] = {}

    for asset, amount in raw.get("total", {}).items():
        if amount and float(amount) > 0:
            total[asset] = float(amount)
            free[asset] = float(raw.get("free", {}).get(asset, 0))
            used[asset] = float(raw.get("used", {}).get(asset, 0))

    return {
        "total": total,
        "free": free,
        "used": used,
        "asset_count": len(total),
    }


def format_order(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalisiert eine ccxt-Order.

    Args:
        raw: Rohe ccxt-Order.

    Returns:
        Strukturiertes Order-Dict.
    """
    return {
        "id": raw.get("id"),
        "client_order_id": raw.get("clientOrderId"),
        "symbol": raw.get("symbol"),
        "type": raw.get("type"),
        "side": raw.get("side"),
        "status": raw.get("status"),
        "price": raw.get("price"),
        "amount": raw.get("amount"),
        "filled": raw.get("filled"),
        "remaining": raw.get("remaining"),
        "cost": raw.get("cost"),
        "average": raw.get("average"),
        "reduce_only": raw.get("reduceOnly"),
        "timestamp": _ts_to_iso(raw.get("timestamp")),
        "last_update": _ts_to_iso(raw.get("lastUpdateTimestamp")),
    }


def format_position(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalisiert eine ccxt-Futures-Position.

    Args:
        raw: Rohe ccxt-Position.

    Returns:
        Strukturiertes Positions-Dict mit PnL-Informationen.
    """
    return {
        "symbol": raw.get("symbol"),
        "side": raw.get("side"),
        "contracts": raw.get("contracts"),
        "contract_size": raw.get("contractSize"),
        "entry_price": raw.get("entryPrice"),
        "mark_price": raw.get("markPrice"),
        "liquidation_price": raw.get("liquidationPrice"),
        "leverage": raw.get("leverage"),
        "margin_mode": raw.get("marginMode"),
        "initial_margin": raw.get("initialMargin"),
        "maintenance_margin": raw.get("maintenanceMargin"),
        "unrealized_pnl": raw.get("unrealizedPnl"),
        "realized_pnl": raw.get("realizedPnl"),
        "percentage": raw.get("percentage"),
        "notional": raw.get("notional"),
        "timestamp": _ts_to_iso(raw.get("timestamp")),
    }


def format_market(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalisiert ccxt-Marktdaten.

    Args:
        raw: Rohe ccxt-Markt-Info.

    Returns:
        Kompaktes Markt-Dict mit den wichtigsten Feldern.
    """
    return {
        "symbol": raw.get("symbol"),
        "base": raw.get("base"),
        "quote": raw.get("quote"),
        "type": raw.get("type"),
        "active": raw.get("active"),
        "spot": raw.get("spot"),
        "future": raw.get("future"),
        "option": raw.get("option"),
        "contract": raw.get("contract"),
        "settle": raw.get("settle"),
        "expiry": _ts_to_iso(raw.get("expiry")) if raw.get("expiry") else None,
        "strike": raw.get("strike"),
        "option_type": raw.get("optionType"),
        "taker_fee": raw.get("taker"),
        "maker_fee": raw.get("maker"),
        "min_amount": raw.get("limits", {}).get("amount", {}).get("min"),
        "precision_amount": raw.get("precision", {}).get("amount"),
        "precision_price": raw.get("precision", {}).get("price"),
    }


def _ts_to_iso(ts: int | float | None) -> str | None:
    """Konvertiert einen Unix-Timestamp (ms) in einen ISO-8601-String.

    Args:
        ts: Unix-Timestamp in Millisekunden oder None.

    Returns:
        ISO-8601-Zeitstring oder None.
    """
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts) / 1000, tz=timezone.utc).isoformat()
    except (ValueError, OSError, OverflowError):
        return None
