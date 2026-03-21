"""
USD-M Futures Trading Tools für den Binance MCP Server.

Alle Funktionen erfordern gültige API-Credentials mit Futures-Trading-
Berechtigung. Futures-Symbole haben das Format 'BTC/USDT:USDT'.

WARNUNG: Futures-Trading beinhaltet Hebel-Risiken. Im Testnet-Modus
(BINANCE_TESTNET=true) werden Orders nur simuliert.
"""

from __future__ import annotations

import logging
from typing import Any

import ccxt

from binance_mcp.client import futures_client
from binance_mcp.utils.formatting import format_error, format_order, format_position

logger = logging.getLogger(__name__)


async def place_futures_order(
    symbol: str,
    side: str,
    order_type: str,
    amount: float,
    price: float | None = None,
    reduce_only: bool = False,
) -> dict[str, Any]:
    """Platziert eine Order auf dem USD-M Futures-Markt.

    Für Limit-Orders muss ein Preis angegeben werden. Mit reduce_only=True
    wird die Order nur ausgeführt, wenn sie eine bestehende Position reduziert.
    Futures-Symbole haben das Format 'BTC/USDT:USDT'.

    Args:
        symbol: Futures-Symbol (z.B. 'BTC/USDT:USDT', 'ETH/USDT:USDT').
        side: Orderrichtung – 'buy' oder 'sell'.
        order_type: Order-Typ – 'market' oder 'limit'.
        amount: Kontraktmenge in der Basis-Währung (z.B. 0.001 BTC).
        price: Limit-Preis (nur für order_type='limit' erforderlich).
        reduce_only: True = Order schliesst/reduziert nur bestehende Positionen.
                     Standard: False.

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

    params: dict[str, Any] = {}
    if reduce_only:
        params["reduceOnly"] = True

    try:
        async with futures_client() as exchange:
            raw = await exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
                params=params,
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
        logger.error("Netzwerkfehler bei place_futures_order(%s): %s", symbol, exc)
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei place_futures_order(%s): %s", symbol, exc)
        return format_error(exc)


async def cancel_futures_order(symbol: str, order_id: str) -> dict[str, Any]:
    """Storniert eine offene Futures-Order anhand ihrer ID.

    Nur Orders mit Status 'open' können storniert werden.

    Args:
        symbol: Futures-Symbol der Order (z.B. 'BTC/USDT:USDT').
        order_id: Die eindeutige Order-ID.

    Returns:
        Dict mit Stornierungsdetails oder Fehler-Dict bei Misserfolg.
    """
    try:
        async with futures_client() as exchange:
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
            "Netzwerkfehler bei cancel_futures_order(%s, %s): %s", symbol, order_id, exc
        )
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei cancel_futures_order(%s, %s): %s", symbol, order_id, exc)
        return format_error(exc)


async def set_leverage(symbol: str, leverage: int) -> dict[str, Any]:
    """Setzt den Hebel für ein Futures-Symbol.

    Der Hebel gilt für alle neuen Orders auf diesem Symbol. Binance
    erlaubt Leverage-Werte von 1 bis 125, abhängig vom Symbol.

    Args:
        symbol: Futures-Symbol (z.B. 'BTC/USDT:USDT').
        leverage: Gewünschter Hebel (1–125).

    Returns:
        Dict mit 'symbol', 'leverage' und Bestätigungsdetails oder
        Fehler-Dict bei Misserfolg.
    """
    if not 1 <= leverage <= 125:
        return {
            "error": f"Leverage {leverage} ausserhalb des erlaubten Bereichs (1–125).",
            "type": "ValueError",
        }

    try:
        async with futures_client() as exchange:
            result = await exchange.set_leverage(leverage=leverage, symbol=symbol)
            return {
                "symbol": symbol,
                "leverage": leverage,
                "result": result,
            }
    except ccxt.AuthenticationError as exc:
        return format_error(exc)
    except ccxt.BadSymbol as exc:
        return format_error(exc)
    except ccxt.InvalidOrder as exc:
        return format_error(exc)
    except ccxt.NetworkError as exc:
        logger.error("Netzwerkfehler bei set_leverage(%s, %d): %s", symbol, leverage, exc)
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei set_leverage(%s, %d): %s", symbol, leverage, exc)
        return format_error(exc)


async def set_margin_mode(symbol: str, mode: str) -> dict[str, Any]:
    """Setzt den Margin-Modus für ein Futures-Symbol.

    'isolated': Jede Position hat eine separate Margin-Allokation.
    'cross': Alle Positionen teilen sich die verfügbare Margin.

    HINWEIS: Der Margin-Modus kann nur geändert werden, wenn keine
    offene Position oder Order für das Symbol existiert.

    Args:
        symbol: Futures-Symbol (z.B. 'BTC/USDT:USDT').
        mode: Margin-Modus – 'isolated' oder 'cross'.

    Returns:
        Dict mit 'symbol', 'mode' und Bestätigungsdetails oder
        Fehler-Dict bei Misserfolg.
    """
    mode = mode.lower()
    if mode not in ("isolated", "cross"):
        return {
            "error": f"Ungültiger Margin-Modus '{mode}'. Erlaubt: isolated, cross",
            "type": "ValueError",
        }

    try:
        async with futures_client() as exchange:
            result = await exchange.set_margin_mode(marginMode=mode, symbol=symbol)
            return {
                "symbol": symbol,
                "mode": mode,
                "result": result,
            }
    except ccxt.AuthenticationError as exc:
        return format_error(exc)
    except ccxt.BadSymbol as exc:
        return format_error(exc)
    except ccxt.NetworkError as exc:
        logger.error("Netzwerkfehler bei set_margin_mode(%s, %s): %s", symbol, mode, exc)
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei set_margin_mode(%s, %s): %s", symbol, mode, exc)
        return format_error(exc)


async def close_position(
    symbol: str, amount: float | None = None
) -> dict[str, Any]:
    """Schliesst eine offene Futures-Position ganz oder teilweise.

    Ohne amount-Angabe wird die gesamte Position zum Marktpreis geschlossen.
    Mit amount wird nur der angegebene Anteil geschlossen (Teilschliessung).

    Args:
        symbol: Futures-Symbol (z.B. 'BTC/USDT:USDT').
        amount: Optional – Zu schliessende Kontraktmenge. None = vollständig.

    Returns:
        Dict mit Order-Details der Schliessungsorder oder Fehler-Dict.
    """
    try:
        async with futures_client() as exchange:
            # Aktuelle Position abrufen
            positions = await exchange.fetch_positions(symbols=[symbol])
            open_pos = [
                p for p in positions if p.get("contracts") and float(p.get("contracts", 0)) != 0
            ]

            if not open_pos:
                return {
                    "error": f"Keine offene Position für Symbol '{symbol}' gefunden.",
                    "type": "PositionNotFound",
                }

            position = open_pos[0]
            pos_side = position.get("side")
            pos_contracts = abs(float(position.get("contracts", 0)))

            # Gegenseitige Seite für Schliessung
            close_side = "sell" if pos_side == "long" else "buy"
            close_amount = amount if amount is not None else pos_contracts

            raw = await exchange.create_order(
                symbol=symbol,
                type="market",
                side=close_side,
                amount=close_amount,
                params={"reduceOnly": True},
            )
            result = format_order(raw)
            result["closed_position_side"] = pos_side
            result["original_contracts"] = pos_contracts
            return result
    except ccxt.AuthenticationError as exc:
        return format_error(exc)
    except ccxt.InsufficientFunds as exc:
        return format_error(exc)
    except ccxt.InvalidOrder as exc:
        return format_error(exc)
    except ccxt.BadSymbol as exc:
        return format_error(exc)
    except ccxt.NetworkError as exc:
        logger.error("Netzwerkfehler bei close_position(%s): %s", symbol, exc)
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei close_position(%s): %s", symbol, exc)
        return format_error(exc)
