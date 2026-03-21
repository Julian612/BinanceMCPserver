"""
ccxt Exchange-Instanzen für Spot, USD-M Futures und Options.

Alle drei Exchange-Instanzen werden lazy initialisiert und können als
async context manager oder direkt verwendet werden.
API Keys werden ausschliesslich aus Umgebungsvariablen geladen.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import ccxt.async_support as ccxt
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_API_KEY = os.getenv("BINANCE_API_KEY", "")
_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
_TESTNET = os.getenv("BINANCE_TESTNET", "false").lower() == "true"


def _build_exchange(default_type: str) -> ccxt.binance:
    """Erstellt eine ccxt.binance Instanz für den angegebenen Markttyp."""
    options: dict = {
        "defaultType": default_type,
        "enableRateLimit": True,
        "adjustForTimeDifference": True,
    }
    exchange = ccxt.binance(
        {
            "apiKey": _API_KEY,
            "secret": _API_SECRET,
            "enableRateLimit": True,
            "options": options,
        }
    )
    if _TESTNET:
        exchange.set_sandbox_mode(True)
        logger.info("Exchange '%s' läuft im TESTNET-Modus.", default_type)
    return exchange


@asynccontextmanager
async def spot_client() -> AsyncGenerator[ccxt.binance, None]:
    """Async context manager für die Spot-Exchange-Instanz."""
    exchange = _build_exchange("spot")
    try:
        yield exchange
    finally:
        await exchange.close()


@asynccontextmanager
async def futures_client() -> AsyncGenerator[ccxt.binance, None]:
    """Async context manager für die USD-M Futures-Exchange-Instanz."""
    exchange = _build_exchange("future")
    try:
        yield exchange
    finally:
        await exchange.close()


@asynccontextmanager
async def options_client() -> AsyncGenerator[ccxt.binance, None]:
    """Async context manager für die Options-Exchange-Instanz."""
    exchange = _build_exchange("option")
    try:
        yield exchange
    finally:
        await exchange.close()


def has_credentials() -> bool:
    """Gibt True zurück, wenn API Key und Secret konfiguriert sind."""
    return bool(_API_KEY and _API_SECRET)
