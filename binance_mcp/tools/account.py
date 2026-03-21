"""
Account & Portfolio Tools für den Binance MCP Server.

Alle Funktionen erfordern gültige API-Credentials (BINANCE_API_KEY /
BINANCE_API_SECRET). Daten werden niemals mit Klartext-Keys zurückgegeben.
"""

from __future__ import annotations

import logging
from typing import Any

import ccxt

from binance_mcp.client import futures_client, options_client, spot_client
from binance_mcp.utils.formatting import (
    format_balance,
    format_error,
    format_order,
    format_position,
)

logger = logging.getLogger(__name__)


async def get_balance(market_type: str = "spot") -> dict[str, Any]:
    """Gibt das Guthaben für den angegebenen Markttyp zurück.

    Nur Assets mit einem Guthaben > 0 werden ausgegeben.
    Benötigt API-Credentials mit 'Read'-Berechtigung.

    Args:
        market_type: Markttyp – 'spot', 'future' oder 'option'.
                     Standard: 'spot'.

    Returns:
        Dict mit 'total', 'free', 'used' (jeweils nur non-zero Assets)
        und 'asset_count'.
    """
    valid_types = ("spot", "future", "option")
    if market_type not in valid_types:
        return {
            "error": f"Ungültiger market_type '{market_type}'. Erlaubt: {valid_types}",
            "type": "ValueError",
        }

    client_ctx = (
        spot_client()
        if market_type == "spot"
        else (futures_client() if market_type == "future" else options_client())
    )

    try:
        async with client_ctx as exchange:
            raw = await exchange.fetch_balance()
            result = format_balance(raw)
            result["market_type"] = market_type
            return result
    except ccxt.AuthenticationError as exc:
        return format_error(exc)
    except ccxt.PermissionDenied as exc:
        return format_error(exc)
    except ccxt.NetworkError as exc:
        logger.error("Netzwerkfehler bei get_balance(%s): %s", market_type, exc)
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei get_balance(%s): %s", market_type, exc)
        return format_error(exc)


async def get_open_orders(
    symbol: str | None = None, market_type: str = "spot"
) -> dict[str, Any]:
    """Gibt alle offenen Orders zurück, optional gefiltert nach Symbol.

    Offene Orders haben den Status 'open' und wurden noch nicht
    vollständig ausgeführt oder storniert.

    Args:
        symbol: Optional – Handelspaar filtern (z.B. 'BTC/USDT').
                None gibt alle offenen Orders zurück.
        market_type: Markttyp – 'spot', 'future' oder 'option'.
                     Standard: 'spot'.

    Returns:
        Dict mit 'symbol', 'market_type', 'count' und 'orders'.
    """
    valid_types = ("spot", "future", "option")
    if market_type not in valid_types:
        return {
            "error": f"Ungültiger market_type '{market_type}'. Erlaubt: {valid_types}",
            "type": "ValueError",
        }

    client_ctx = (
        spot_client()
        if market_type == "spot"
        else (futures_client() if market_type == "future" else options_client())
    )

    try:
        async with client_ctx as exchange:
            raw_orders = await exchange.fetch_open_orders(symbol=symbol)
            orders = [format_order(o) for o in raw_orders]
            return {
                "symbol": symbol,
                "market_type": market_type,
                "count": len(orders),
                "orders": orders,
            }
    except ccxt.AuthenticationError as exc:
        return format_error(exc)
    except ccxt.BadSymbol as exc:
        return format_error(exc)
    except ccxt.NetworkError as exc:
        logger.error("Netzwerkfehler bei get_open_orders: %s", exc)
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei get_open_orders: %s", exc)
        return format_error(exc)


async def get_order_history(
    symbol: str, market_type: str = "spot", limit: int = 50
) -> dict[str, Any]:
    """Gibt die Order-History für ein Symbol zurück.

    Liefert abgeschlossene, stornierte und teilweise ausgeführte Orders.
    Benötigt API-Credentials mit 'Read'-Berechtigung.

    Args:
        symbol: Handelspaar (z.B. 'BTC/USDT'). Pflichtfeld.
        market_type: Markttyp – 'spot', 'future' oder 'option'.
                     Standard: 'spot'.
        limit: Maximale Anzahl zurückgegebener Orders (Standard: 50,
               max: 1000).

    Returns:
        Dict mit 'symbol', 'market_type', 'count' und 'orders'.
    """
    valid_types = ("spot", "future", "option")
    if market_type not in valid_types:
        return {
            "error": f"Ungültiger market_type '{market_type}'. Erlaubt: {valid_types}",
            "type": "ValueError",
        }

    client_ctx = (
        spot_client()
        if market_type == "spot"
        else (futures_client() if market_type == "future" else options_client())
    )

    try:
        async with client_ctx as exchange:
            raw_orders = await exchange.fetch_orders(symbol=symbol, limit=limit)
            orders = [format_order(o) for o in raw_orders]
            return {
                "symbol": symbol,
                "market_type": market_type,
                "count": len(orders),
                "orders": orders,
            }
    except ccxt.AuthenticationError as exc:
        return format_error(exc)
    except ccxt.BadSymbol as exc:
        return format_error(exc)
    except ccxt.NetworkError as exc:
        logger.error("Netzwerkfehler bei get_order_history(%s): %s", symbol, exc)
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei get_order_history(%s): %s", symbol, exc)
        return format_error(exc)


async def get_positions(symbol: str | None = None) -> dict[str, Any]:
    """Gibt alle offenen Futures-Positionen zurück, optional nach Symbol gefiltert.

    Zeigt nur Positionen mit einer Kontraktgrösse > 0. Enthält Einstiegspreis,
    Mark-Preis, Liquidierungspreis, unrealisierten PnL und Leverage.

    Args:
        symbol: Optional – Futures-Symbol filtern (z.B. 'BTC/USDT:USDT').
                None gibt alle offenen Positionen zurück.

    Returns:
        Dict mit 'symbol', 'count' und 'positions' (Liste von Positions-Dicts).
    """
    try:
        async with futures_client() as exchange:
            symbols = [symbol] if symbol else None
            raw_positions = await exchange.fetch_positions(symbols=symbols)
            # Nur Positionen mit tatsächlichen Kontrakten
            open_positions = [
                format_position(p)
                for p in raw_positions
                if p.get("contracts") and float(p.get("contracts", 0)) != 0
            ]
            return {
                "symbol": symbol,
                "count": len(open_positions),
                "positions": open_positions,
            }
    except ccxt.AuthenticationError as exc:
        return format_error(exc)
    except ccxt.BadSymbol as exc:
        return format_error(exc)
    except ccxt.NetworkError as exc:
        logger.error("Netzwerkfehler bei get_positions: %s", exc)
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei get_positions: %s", exc)
        return format_error(exc)


async def get_pnl_summary() -> dict[str, Any]:
    """Gibt eine PnL-Zusammenfassung über alle offenen Futures-Positionen zurück.

    Aggregiert unrealisierten und realisierten PnL (sofern verfügbar)
    über alle offenen Positionen. Gibt eine Übersicht pro Position sowie
    die Gesamtsummen aus.

    Returns:
        Dict mit 'total_unrealized_pnl', 'positions_count' und
        'positions' (Liste mit symbol, side, unrealized_pnl, realized_pnl,
        percentage, leverage).
    """
    try:
        async with futures_client() as exchange:
            raw_positions = await exchange.fetch_positions()
            open_positions = [
                p
                for p in raw_positions
                if p.get("contracts") and float(p.get("contracts", 0)) != 0
            ]

            total_unrealized = 0.0
            total_realized = 0.0
            summaries = []

            for pos in open_positions:
                upnl = float(pos.get("unrealizedPnl") or 0)
                rpnl = float(pos.get("realizedPnl") or 0)
                total_unrealized += upnl
                total_realized += rpnl
                summaries.append(
                    {
                        "symbol": pos.get("symbol"),
                        "side": pos.get("side"),
                        "contracts": pos.get("contracts"),
                        "entry_price": pos.get("entryPrice"),
                        "mark_price": pos.get("markPrice"),
                        "unrealized_pnl": upnl,
                        "realized_pnl": rpnl,
                        "percentage": pos.get("percentage"),
                        "leverage": pos.get("leverage"),
                        "notional": pos.get("notional"),
                    }
                )

            return {
                "positions_count": len(summaries),
                "total_unrealized_pnl": round(total_unrealized, 8),
                "total_realized_pnl": round(total_realized, 8),
                "combined_pnl": round(total_unrealized + total_realized, 8),
                "positions": summaries,
            }
    except ccxt.AuthenticationError as exc:
        return format_error(exc)
    except ccxt.NetworkError as exc:
        logger.error("Netzwerkfehler bei get_pnl_summary: %s", exc)
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei get_pnl_summary: %s", exc)
        return format_error(exc)
