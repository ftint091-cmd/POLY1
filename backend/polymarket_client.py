from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from .config import get_settings

logger = logging.getLogger(__name__)


def get_client() -> Any:
    """Initialize and return a ClobClient with credentials."""
    try:
        from py_clob_client.client import ClobClient
        from py_clob_client.clob_types import ApiCreds

        settings = get_settings()
        creds = ApiCreds(
            api_key=settings.POLYMARKET_API_KEY,
            api_secret=settings.POLYMARKET_API_SECRET,
            api_passphrase=settings.POLYMARKET_PASSPHRASE,
        )
        client = ClobClient(
            host=settings.CLOB_API_URL,
            chain_id=settings.CHAIN_ID,
            key=settings.PRIVATE_KEY,
            creds=creds,
        )
        return client
    except Exception as exc:
        logger.error("Failed to initialize ClobClient: %s", exc)
        raise


async def fetch_target_orders(target_address: str) -> List[Dict[str, Any]]:
    """Fetch open orders of the target wallet using CLOB REST API."""
    settings = get_settings()
    url = f"{settings.CLOB_API_URL}/data/orders"
    params = {"maker": target_address}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            return data.get("data", [])
    except httpx.HTTPStatusError as exc:
        logger.error("HTTP error fetching target orders: %s", exc)
        return []
    except Exception as exc:
        logger.error("Error fetching target orders: %s", exc)
        return []


async def place_order(
    token_id: str,
    price: float,
    size: float,
    side: str,
) -> Optional[Dict[str, Any]]:
    """Create and post an order via py-clob-client."""
    try:
        from py_clob_client.clob_types import OrderArgs, OrderType

        client = get_client()
        order_args = OrderArgs(
            token_id=token_id,
            price=price,
            size=size,
            side=side,
        )
        signed_order = client.create_order(order_args)
        result = client.post_order(signed_order, OrderType.GTC)
        return result
    except Exception as exc:
        logger.error("Error placing order: %s", exc)
        return None


async def get_open_orders() -> List[Dict[str, Any]]:
    """Fetch the bot's own open orders."""
    try:
        client = get_client()
        result = client.get_orders()
        if isinstance(result, list):
            return result
        return result.get("data", [])
    except Exception as exc:
        logger.error("Error fetching own orders: %s", exc)
        return []


async def cancel_all_orders() -> bool:
    """Cancel all bot's open orders."""
    try:
        client = get_client()
        client.cancel_all()
        return True
    except Exception as exc:
        logger.error("Error cancelling orders: %s", exc)
        return False


async def get_markets() -> List[Dict[str, Any]]:
    """Fetch available markets info."""
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{settings.CLOB_API_URL}/markets")
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            return data.get("data", [])
    except Exception as exc:
        logger.error("Error fetching markets: %s", exc)
        return []
