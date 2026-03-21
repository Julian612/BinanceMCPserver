"""
Öffentliche Marktdaten-Tools für den Binance MCP Server.

Alle Funktionen greifen ausschliesslich auf öffentliche Endpoints zu
und benötigen keine API-Authentifizierung.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import ccxt

from binance_mcp.client import futures_client, options_client, spot_client
from binance_mcp.utils.formatting import (
    format_error,
    format_market,
    format_ohlcv,
    format_orderbook,
    format_ticker,
)

logger = logging.getLogger(__name__)


async def get_price(symbol: str) -> dict[str, Any]:
    """Gibt den aktuellen Marktpreis für ein Symbol zurück.

    Ruft den letzten gehandelten Preis (last price) vom Spot-Markt ab.
    Beispiel-Symbol: 'BTC/USDT', 'ETH/USDT'.

    Args:
        symbol: Das Handelspaar im Format 'BASE/QUOTE' (z.B. 'BTC/USDT').

    Returns:
        Dict mit 'symbol', 'price' und 'timestamp'.
    """
    try:
        async with spot_client() as exchange:
            ticker = await exchange.fetch_ticker(symbol)
            return {
                "symbol": ticker.get("symbol"),
                "price": ticker.get("last"),
                "timestamp": ticker.get("datetime"),
            }
    except ccxt.BadSymbol as exc:
        return format_error(exc)
    except ccxt.NetworkError as exc:
        logger.error("Netzwerkfehler bei get_price(%s): %s", symbol, exc, file=sys.stderr)
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei get_price(%s): %s", symbol, exc)
        return format_error(exc)


async def get_ticker(symbol: str) -> dict[str, Any]:
    """Gibt den vollständigen Ticker für ein Symbol zurück.

    Enthält Bid/Ask, 24h-Volumen, Preis-Veränderung und weitere Marktdaten.
    Beispiel-Symbol: 'BTC/USDT', 'ETH/BTC'.

    Args:
        symbol: Das Handelspaar im Format 'BASE/QUOTE' (z.B. 'BTC/USDT').

    Returns:
        Dict mit symbol, last, bid, ask, high, low, volume, change_24h,
        change_pct_24h und timestamp.
    """
    try:
        async with spot_client() as exchange:
            raw = await exchange.fetch_ticker(symbol)
            return format_ticker(raw)
    except ccxt.BadSymbol as exc:
        return format_error(exc)
    except ccxt.NetworkError as exc:
        logger.error("Netzwerkfehler bei get_ticker(%s): %s", symbol, exc)
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei get_ticker(%s): %s", symbol, exc)
        return format_error(exc)


async def get_orderbook(symbol: str, limit: int = 20) -> dict[str, Any]:
    """Gibt das aktuelle Order Book für ein Symbol zurück.

    Liefert Bids (Kauforders) und Asks (Verkaufsorders) sortiert nach Preis.
    Jeder Eintrag ist [price, amount].

    Args:
        symbol: Das Handelspaar im Format 'BASE/QUOTE' (z.B. 'BTC/USDT').
        limit: Anzahl der Preislevels pro Seite (Standard: 20, max: 1000).

    Returns:
        Dict mit 'symbol', 'bids', 'asks', 'bid_count', 'ask_count' und
        'timestamp'.
    """
    try:
        async with spot_client() as exchange:
            raw = await exchange.fetch_order_book(symbol, limit=limit)
            return format_orderbook(raw, limit)
    except ccxt.BadSymbol as exc:
        return format_error(exc)
    except ccxt.NetworkError as exc:
        logger.error("Netzwerkfehler bei get_orderbook(%s): %s", symbol, exc)
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei get_orderbook(%s): %s", symbol, exc)
        return format_error(exc)


async def get_ohlcv(
    symbol: str, timeframe: str = "1h", limit: int = 100
) -> dict[str, Any]:
    """Gibt OHLCV-Candlestick-Daten für ein Symbol zurück.

    Unterstützte Timeframes: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h,
    12h, 1d, 3d, 1w, 1M.

    Args:
        symbol: Das Handelspaar im Format 'BASE/QUOTE' (z.B. 'BTC/USDT').
        timeframe: Kerzen-Intervall (Standard: '1h').
        limit: Anzahl der Kerzen (Standard: 100, max: 1000).

    Returns:
        Dict mit 'symbol', 'timeframe', 'count' und 'candles'. Jede Kerze
        enthält timestamp, open, high, low, close, volume.
    """
    try:
        async with spot_client() as exchange:
            raw = await exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            return format_ohlcv(raw, symbol, timeframe)
    except ccxt.BadSymbol as exc:
        return format_error(exc)
    except ccxt.BadRequest as exc:
        return format_error(exc)
    except ccxt.NetworkError as exc:
        logger.error("Netzwerkfehler bei get_ohlcv(%s): %s", symbol, exc)
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei get_ohlcv(%s): %s", symbol, exc)
        return format_error(exc)


async def get_markets(market_type: str = "spot") -> dict[str, Any]:
    """Gibt alle verfügbaren Märkte für den angegebenen Markttyp zurück.

    Liefert eine Liste aktiver Märkte mit Handelspaar, Gebühren und
    Präzisions-Informationen.

    Args:
        market_type: Markttyp – 'spot', 'future' oder 'option'.
                     Standard: 'spot'.

    Returns:
        Dict mit 'market_type', 'count' und 'markets' (Liste von Markt-Dicts).
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
            markets = await exchange.load_markets()
            filtered = [
                format_market(m)
                for m in markets.values()
                if m.get("active") and m.get("type") == market_type
            ]
            return {
                "market_type": market_type,
                "count": len(filtered),
                "markets": filtered,
            }
    except ccxt.NetworkError as exc:
        logger.error("Netzwerkfehler bei get_markets(%s): %s", market_type, exc)
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei get_markets(%s): %s", market_type, exc)
        return format_error(exc)


async def search_symbols(query: str, market_type: str = "spot") -> dict[str, Any]:
    """Sucht nach Handelssymbolen, die dem Suchbegriff entsprechen.

    Die Suche ist case-insensitiv und prüft ob der query-String im
    Symbol-Namen enthalten ist (z.B. 'BTC' findet 'BTC/USDT', 'BTC/BNB').

    Args:
        query: Suchbegriff (z.B. 'BTC', 'USDT', 'ETH').
        market_type: Markttyp – 'spot', 'future' oder 'option'.
                     Standard: 'spot'.

    Returns:
        Dict mit 'query', 'market_type', 'count' und 'symbols' (Liste von
        Symbol-Strings).
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
            markets = await exchange.load_markets()
            query_upper = query.upper()
            matches = [
                symbol
                for symbol, market in markets.items()
                if query_upper in symbol.upper()
                and market.get("active")
                and market.get("type") == market_type
            ]
            matches.sort()
            return {
                "query": query,
                "market_type": market_type,
                "count": len(matches),
                "symbols": matches,
            }
    except ccxt.NetworkError as exc:
        logger.error("Netzwerkfehler bei search_symbols(%s): %s", query, exc)
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei search_symbols(%s): %s", query, exc)
        return format_error(exc)
