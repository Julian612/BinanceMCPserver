"""
Spot Trading Tools für den Binance MCP Server.

Alle Funktionen erfordern gültige API-Credentials mit Trading-Berechtigung.
Orders werden direkt auf dem Binance Spot-Markt platziert.

WARNUNG: Diese Tools führen echte Trades aus. Im Testnet-Modus
(BINANCE_TESTNET=true) werden Orders nur simuliert.
"""

from __future__ import annotations

import logging
from typing import Any

import ccxt

from binance_mcp.client import spot_client
from binance_mcp.utils.formatting import format_error, format_order

logger = logging.getLogger(__name__)


async def place_spot_order(
    symbol: str,
    side: str,
    order_type: str,
    amount: float,
    price: float | None = None,
) -> dict[str, Any]:
    """Platziert eine Order auf dem Spot-Markt.

    Für Limit-Orders muss ein Preis angegeben werden. Market-Orders
    werden sofort zum aktuellen Marktpreis ausgeführt.

    Args:
        symbol: Handelspaar (z.B. 'BTC/USDT').
        side: Orderrichtung – 'buy' oder 'sell'.
        order_type: Order-Typ – 'market' oder 'limit'.
        amount: Menge in der Basis-Währung (z.B. 0.001 für 0.001 BTC).
        price: Limit-Preis (nur für order_type='limit' erforderlich).

    Returns:
        Dict mit Order-Details (id, symbol, type, side, status, price,
        amount, filled) oder Fehler-Dict bei Misserfolg.
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
        async with spot_client() as exchange:
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
        logger.error("Netzwerkfehler bei place_spot_order(%s): %s", symbol, exc)
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei place_spot_order(%s): %s", symbol, exc)
        return format_error(exc)


async def cancel_spot_order(symbol: str, order_id: str) -> dict[str, Any]:
    """Storniert eine offene Spot-Order anhand ihrer ID.

    Nur Orders mit Status 'open' können storniert werden. Bereits
    ausgeführte oder stornierte Orders können nicht erneut storniert werden.

    Args:
        symbol: Handelspaar der Order (z.B. 'BTC/USDT').
        order_id: Die eindeutige Order-ID (wird beim Platzieren zurückgegeben).

    Returns:
        Dict mit Stornierungsdetails oder Fehler-Dict bei Misserfolg.
    """
    try:
        async with spot_client() as exchange:
            raw = await exchange.cancel_order(id=order_id, symbol=symbol)
            return format_order(raw)
    except ccxt.AuthenticationError as exc:
        return format_error(exc)
    except ccxt.OrderNotFound as exc:
        return format_error(exc)
    except ccxt.BadSymbol as exc:
        return format_error(exc)
    except ccxt.NetworkError as exc:
        logger.error("Netzwerkfehler bei cancel_spot_order(%s, %s): %s", symbol, order_id, exc)
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei cancel_spot_order(%s, %s): %s", symbol, order_id, exc)
        return format_error(exc)


async def cancel_all_spot_orders(symbol: str | None = None) -> dict[str, Any]:
    """Storniert alle offenen Spot-Orders, optional gefiltert nach Symbol.

    Ohne Symbol-Angabe werden alle offenen Orders auf dem Spot-Markt
    storniert. Mit Symbol wird nur dieses Handelspaar berücksichtigt.

    Args:
        symbol: Optional – nur Orders dieses Handelspaars stornieren
                (z.B. 'BTC/USDT'). None storniert alle offenen Orders.

    Returns:
        Dict mit 'cancelled_count' und 'results' (Liste der stornierten
        Orders) oder Fehler-Dict bei Misserfolg.
    """
    try:
        async with spot_client() as exchange:
            if symbol:
                # ccxt cancel_all_orders mit Symbol
                results = await exchange.cancel_all_orders(symbol=symbol)
            else:
                # Alle offenen Orders holen und einzeln stornieren
                open_orders = await exchange.fetch_open_orders()
                results = []
                for order in open_orders:
                    try:
                        cancelled = await exchange.cancel_order(
                            id=order["id"], symbol=order["symbol"]
                        )
                        results.append(format_order(cancelled))
                    except ccxt.OrderNotFound:
                        # Order bereits storniert oder ausgeführt
                        pass
                    except Exception as inner_exc:
                        logger.warning(
                            "Konnte Order %s nicht stornieren: %s", order.get("id"), inner_exc
                        )
                return {
                    "symbol": symbol,
                    "cancelled_count": len(results),
                    "results": results,
                }

            formatted = (
                [format_order(r) for r in results] if isinstance(results, list) else []
            )
            return {
                "symbol": symbol,
                "cancelled_count": len(formatted),
                "results": formatted,
            }
    except ccxt.AuthenticationError as exc:
        return format_error(exc)
    except ccxt.BadSymbol as exc:
        return format_error(exc)
    except ccxt.NetworkError as exc:
        logger.error("Netzwerkfehler bei cancel_all_spot_orders: %s", exc)
        return format_error(exc)
    except Exception as exc:
        logger.error("Fehler bei cancel_all_spot_orders: %s", exc)
        return format_error(exc)
