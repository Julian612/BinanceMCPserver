"""
Options Trading Tools für den Binance MCP Server.

Binance European-Style Options werden über den 'option' defaultType
angesprochen. Symbols haben das Format 'BTC/USDT:BTC-YYYYMMDD-STRIKE-C/P'
(z.B. 'BTC/USDT:BTC-241227-100000-C' für eine BTC Call-Option).

Alle Funktionen erfordern gültige API-Credentials mit Options-Trading-
Berechtigung. Im Testnet-Modus werden Orders nur simuliert.
"""

from __future__ import annotations

import logging
from typing import Any

import ccxt

from binance_mcp.client import options_client
from binance_mcp.utils.formatting import format_error, format_market, format_order

logger = logging.getLogger(__name__)


async def get_option_chain(underlying: str) -> dict[str, Any]:
    """Gibt alle verfügbaren Options-Kontrakte für ein Underlying zurück.

    Listet alle aktiven Call- und Put-Optionen auf, gruppiert nach
    Verfallsdatum. Underlying ist die Basis-Währung (z.B. 'BTC', 'ETH').

    Args:
        underlying: Basis-Währung des Underlyings (z.B. 'BTC', 'ETH').
                    Gross-/Kleinschreibung wird ignoriert.

    Returns:
        Dict mit 'underlying', 'count', 'calls' und 'puts' (jeweils
        Listen von Markt-Dicts mit Strike, Expiry und Typ).
    """
    underlying_upper = underlying.upper()

    try:
        async with options_client() as exchange:
            markets = await exchange.load_markets()

            calls = []
            puts = []

            for symbol, market in markets.items():
                if not market.get("active"):
                    continue
                if market.get("type") != "option":
                    continue
                base = (market.get("base") or "").upper()
                if base != underlying_upper:
                    continue

                formatted = format_market(market)
                if market.get("optionType") == "call":
                    calls.append(formatted)
                elif market.get("optionType") == "put":
                    puts.append(formatted)

            # Nach Strike-Preis sortieren
            calls.sort(key=lambda m: (m.get("expiry") or "", m.get("strike") or 0))
            puts.sort(key=lambda m: (m.get("expiry") or "", m.get("strike") or 0))

            return {
                "underlying": underlying_upper,
                "count": len(calls) + len(puts),
                "calls_count": len(calls),
                "puts_count": len(puts),
                "calls": calls,
                "puts": puts,
            }
    except ccxt.NetworkError as exc:
        logger.error("Netzwerkfehler bei get_option_chain(%s): %s", underlying, exc)
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei get_option_chain(%s): %s", underlying, exc)
        return format_error(exc)


async def place_options_order(
    symbol: str,
    side: str,
    order_type: str,
    amount: float,
    price: float | None = None,
) -> dict[str, Any]:
    """Platziert eine Order auf dem Options-Markt.

    Optionen können nur gekauft (buy) oder verkauft (sell) werden.
    Das Options-Symbol enthält Verfallsdatum, Strike und Typ:
    z.B. 'BTC/USDT:BTC-241227-100000-C' (BTC Call, Strike 100000, Verfall 27.12.2024).

    Args:
        symbol: Options-Symbol im Binance-Format.
        side: Orderrichtung – 'buy' oder 'sell'.
        order_type: Order-Typ – 'market' oder 'limit'.
        amount: Kontraktmenge.
        price: Limit-Preis in der Quote-Währung (nur für order_type='limit').

    Returns:
        Dict mit Order-Details oder Fehler-Dict bei Misserfolg.
    """
    side = side.lower()
    order_type = order_type.lower()

    if side not in ("buy", "sell"):
        return {"error": f"Ungültige side '{side}'. Erlaubt: buy, sell", "type": "ValueError"}
    if order_type not in ("market", "limit"):
        return {
            "error": f"Ungültiger order_type '{order_type}'. Erlaubt: market, limit",
            "type": "ValueError",
        }
    if order_type == "limit" and price is None:
        return {"error": "Für Limit-Orders muss ein Preis angegeben werden.", "type": "ValueError"}

    try:
        async with options_client() as exchange:
            raw = await exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
            )
            return format_order(raw)
    except ccxt.AuthenticationError as exc:
        return format_error(exc)
    except ccxt.InsufficientFunds as exc:
        return format_error(exc)
    except ccxt.InvalidOrder as exc:
        return format_error(exc)
    except ccxt.BadSymbol as exc:
        return format_error(exc)
    except ccxt.NetworkError as exc:
        logger.error("Netzwerkfehler bei place_options_order(%s): %s", symbol, exc)
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei place_options_order(%s): %s", symbol, exc)
        return format_error(exc)


async def cancel_options_order(symbol: str, order_id: str) -> dict[str, Any]:
    """Storniert eine offene Options-Order anhand ihrer ID.

    Nur Orders mit Status 'open' können storniert werden. Verfallene
    oder bereits ausgeführte Options-Orders können nicht storniert werden.

    Args:
        symbol: Options-Symbol der Order (z.B. 'BTC/USDT:BTC-241227-100000-C').
        order_id: Die eindeutige Order-ID.

    Returns:
        Dict mit Stornierungsdetails oder Fehler-Dict bei Misserfolg.
    """
    try:
        async with options_client() as exchange:
            raw = await exchange.cancel_order(id=order_id, symbol=symbol)
            return format_order(raw)
    except ccxt.AuthenticationError as exc:
        return format_error(exc)
    except ccxt.OrderNotFound as exc:
        return format_error(exc)
    except ccxt.BadSymbol as exc:
        return format_error(exc)
    except ccxt.NetworkError as exc:
        logger.error(
            "Netzwerkfehler bei cancel_options_order(%s, %s): %s", symbol, order_id, exc
        )
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei cancel_options_order(%s, %s): %s", symbol, order_id, exc)
        return format_error(exc)
