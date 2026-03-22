"""
Public market data tools – no API key required.

All functions use the spot exchange by default for public endpoints;
market_type parameter allows switching to futures/options where applicable.
"""

from __future__ import annotations

import ccxt
from binance_mcp.client import futures_client, options_client, spot_client


async def get_price(symbol: str) -> dict:
    """
    Fetch the current last traded price for a symbol.

    Args:
        symbol: Trading pair in ccxt format, e.g. 'BTC/USDT'.

    Returns:
        Dict with keys 'symbol' and 'price', or 'error'/'type' on failure.
    """
    try:
        async with spot_client() as exchange:
            ticker = await exchange.fetch_ticker(symbol)
            return {"symbol": symbol, "price": ticker["last"]}
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}


async def get_ticker(symbol: str) -> dict:
    """
    Fetch the full 24-hour ticker for a symbol.

    Returns bid, ask, last price, 24h volume and percentage change.

    Args:
        symbol: Trading pair in ccxt format, e.g. 'BTC/USDT'.

    Returns:
        Dict with ticker fields, or 'error'/'type' on failure.
    """
    try:
        async with spot_client() as exchange:
            t = await exchange.fetch_ticker(symbol)
            return {
                "symbol": t.get("symbol"),
                "bid": t.get("bid"),
                "ask": t.get("ask"),
                "last": t.get("last"),
                "open": t.get("open"),
                "high": t.get("high"),
                "low": t.get("low"),
                "volume": t.get("baseVolume"),
                "quote_volume": t.get("quoteVolume"),
                "change": t.get("change"),
                "percentage": t.get("percentage"),
                "timestamp": t.get("timestamp"),
                "datetime": t.get("datetime"),
            }
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}


async def get_orderbook(symbol: str, limit: int = 20) -> dict:
    """
    Fetch the current order book for a symbol.

    Args:
        symbol: Trading pair in ccxt format, e.g. 'BTC/USDT'.
        limit: Number of price levels to return per side (default 20).

    Returns:
        Dict with 'bids' and 'asks' lists ([price, amount] pairs),
        or 'error'/'type' on failure.
    """
    try:
        async with spot_client() as exchange:
            ob = await exchange.fetch_order_book(symbol, limit)
            return {
                "symbol": symbol,
                "bids": ob["bids"],
                "asks": ob["asks"],
                "timestamp": ob.get("timestamp"),
                "datetime": ob.get("datetime"),
            }
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}


async def get_ohlcv(
    symbol: str,
    timeframe: str = "1h",
    limit: int = 100,
) -> dict:
    """
    Fetch OHLCV (candlestick) data for a symbol.

    Args:
        symbol: Trading pair in ccxt format, e.g. 'BTC/USDT'.
        timeframe: Candle interval, e.g. '1m', '5m', '1h', '1d' (default '1h').
        limit: Number of candles to return (default 100, max 1000).

    Returns:
        Dict with 'candles' list of dicts (timestamp, open, high, low, close, volume),
        or 'error'/'type' on failure.
    """
    try:
        async with spot_client() as exchange:
            raw = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            candles = [
                {
                    "timestamp": c[0],
                    "open": c[1],
                    "high": c[2],
                    "low": c[3],
                    "close": c[4],
                    "volume": c[5],
                }
                for c in raw
            ]
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "candles": candles,
            }
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}


async def get_markets(market_type: str = "spot") -> dict:
    """
    Fetch all available markets for a given market type.

    Args:
        market_type: One of 'spot', 'future', 'option' (default 'spot').

    Returns:
        Dict with 'markets' list of dicts (id, symbol, base, quote, active, type),
        or 'error'/'type' on failure.
    """
    _client_map = {
        "spot": spot_client,
        "future": futures_client,
        "option": options_client,
    }
    client_fn = _client_map.get(market_type, spot_client)

    try:
        async with client_fn() as exchange:
            raw_markets = await exchange.load_markets()
            markets = [
                {
                    "id": m.get("id"),
                    "symbol": m.get("symbol"),
                    "base": m.get("base"),
                    "quote": m.get("quote"),
                    "active": m.get("active"),
                    "type": m.get("type"),
                }
                for m in raw_markets.values()
                if m.get("active")
            ]
            return {"market_type": market_type, "count": len(markets), "markets": markets}
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}


async def search_symbols(query: str, market_type: str = "spot") -> dict:
    """
    Search for symbols matching a query string.

    Case-insensitive search against symbol IDs and names.

    Args:
        query: Search string, e.g. 'BTC' or 'USDT'.
        market_type: One of 'spot', 'future', 'option' (default 'spot').

    Returns:
        Dict with 'results' list of matching symbols,
        or 'error'/'type' on failure.
    """
    _client_map = {
        "spot": spot_client,
        "future": futures_client,
        "option": options_client,
    }
    client_fn = _client_map.get(market_type, spot_client)
    q = query.upper()

    try:
        async with client_fn() as exchange:
            raw_markets = await exchange.load_markets()
            results = [
                {
                    "symbol": m.get("symbol"),
                    "base": m.get("base"),
                    "quote": m.get("quote"),
                    "type": m.get("type"),
                    "active": m.get("active"),
                }
                for m in raw_markets.values()
                if q in (m.get("symbol") or "").upper()
                or q in (m.get("base") or "").upper()
                or q in (m.get("quote") or "").upper()
            ]
            return {
                "query": query,
                "market_type": market_type,
                "count": len(results),
                "results": results,
            }
    except ccxt.BaseError as e:
        return {"error": str(e), "type": type(e).__name__}
