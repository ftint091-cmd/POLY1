"""Polymarket CLOB API client wrapper."""

import logging
from typing import Any, Dict, List, Optional

import httpx

from .config import settings

logger = logging.getLogger(__name__)


def get_client() -> Any:
    """Initialize and return a ClobClient with credentials from settings."""
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import ApiCreds

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


def fetch_target_orders(target_address: str) -> List[Dict[str, Any]]:
    """Fetch open orders of the target wallet via CLOB REST API.

    Uses GET /data/orders?maker=<address> endpoint.
    Returns a list of order dicts on success, empty list on error.
    """
    url = f"{settings.CLOB_API_URL}/data/orders"
    params: Dict[str, str] = {"maker": target_address}
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            # Some endpoints wrap the list in a "data" key
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            return []
    except httpx.HTTPStatusError as exc:
        logger.error(
            "HTTP error fetching target orders for %s: %s", target_address, exc
        )
    except httpx.RequestError as exc:
        logger.error(
            "Request error fetching target orders for %s: %s", target_address, exc
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Unexpected error fetching target orders for %s: %s", target_address, exc
        )
    return []


def place_order(
    token_id: str,
    price: float,
    size: float,
    side: str,
) -> Optional[Dict[str, Any]]:
    """Create and post an order copying the target's prediction.

    Returns the API response dict on success, None on failure.
    """
    from py_clob_client.clob_types import OrderArgs, OrderType
    from py_clob_client.constants import BUY, SELL

    try:
        client = get_client()
        side_const = BUY if side.upper() == "BUY" else SELL
        order_args = OrderArgs(
            token_id=token_id,
            price=price,
            size=size,
            side=side_const,
        )
        order_type = OrderType.GTC
        resp = client.create_and_post_order(order_args, order_type)
        logger.info(
            "Order placed: token=%s side=%s price=%s size=%s resp=%s",
            token_id,
            side,
            price,
            size,
            resp,
        )
        return resp
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Failed to place order token=%s side=%s price=%s size=%s: %s",
            token_id,
            side,
            price,
            size,
            exc,
        )
        return None


def get_open_orders() -> List[Dict[str, Any]]:
    """Fetch the bot's own open orders."""
    try:
        client = get_client()
        resp = client.get_orders()
        if isinstance(resp, list):
            return resp
        if isinstance(resp, dict) and "data" in resp:
            return resp["data"]
        return []
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to fetch own open orders: %s", exc)
        return []


def cancel_all_orders() -> bool:
    """Cancel all bot's open orders. Returns True on success."""
    try:
        client = get_client()
        client.cancel_all()
        logger.info("All orders cancelled.")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to cancel all orders: %s", exc)
        return False


def get_markets() -> List[Dict[str, Any]]:
    """Fetch available markets info."""
    try:
        client = get_client()
        resp = client.get_markets()
        if isinstance(resp, list):
            return resp
        if isinstance(resp, dict) and "data" in resp:
            return resp["data"]
        return []
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to fetch markets: %s", exc)
        return []
