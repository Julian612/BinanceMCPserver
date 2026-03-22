"""
ccxt Exchange client factory.

Provides three async context managers for spot, futures and options markets.
API credentials are read exclusively from environment variables.
Testnet support via BINANCE_TESTNET=true.
"""

import os
from contextlib import asynccontextmanager

import ccxt.async_support as ccxt
from dotenv import load_dotenv

load_dotenv()

_API_KEY = os.getenv("BINANCE_API_KEY", "")
_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
_TESTNET = os.getenv("BINANCE_TESTNET", "false").lower() == "true"


def has_credentials() -> bool:
    """Return True when both API key and secret are configured."""
    return bool(_API_KEY and _API_SECRET)


def _build_exchange(market_type: str) -> ccxt.binance:
    """
    Instantiate a ccxt.async_support.binance exchange for a given market type.

    Args:
        market_type: One of 'spot', 'future', 'option'.

    Returns:
        Configured ccxt.binance instance (not yet loaded).
    """
    config: dict = {
        "apiKey": _API_KEY,
        "secret": _API_SECRET,
        "enableRateLimit": True,
        "options": {
            "defaultType": market_type,
            "adjustForTimeDifference": True,
        },
    }

    exchange = ccxt.binance(config)

    if _TESTNET:
        exchange.set_sandbox_mode(True)

    return exchange


@asynccontextmanager
async def spot_client():
    """Async context manager for the Binance spot exchange."""
    exchange = _build_exchange("spot")
    try:
        yield exchange
    finally:
        await exchange.close()


@asynccontextmanager
async def futures_client():
    """Async context manager for the Binance USD-M futures exchange."""
    exchange = _build_exchange("future")
    try:
        yield exchange
    finally:
        await exchange.close()


@asynccontextmanager
async def options_client():
    """Async context manager for the Binance options exchange."""
    exchange = _build_exchange("option")
    try:
        yield exchange
    finally:
        await exchange.close()
