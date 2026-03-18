from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional, Set

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from . import polymarket_client as pm_client
from .config import get_settings
from .models import CopiedOrder

logger = logging.getLogger(__name__)


class OrderTracker:
    """Periodically polls target wallet's orders and copies new ones."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._copied_ids: Set[str] = set()
        self._copied_orders: List[CopiedOrder] = []
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._running: bool = False
        self._last_poll: Optional[datetime] = None
        self._error_count: int = 0

    # ------------------------------------------------------------------ #
    # Public properties
    # ------------------------------------------------------------------ #

    @property
    def running(self) -> bool:
        return self._running

    @property
    def last_poll(self) -> Optional[datetime]:
        return self._last_poll

    @property
    def error_count(self) -> int:
        return self._error_count

    @property
    def copied_orders(self) -> List[CopiedOrder]:
        with self._lock:
            return list(self._copied_orders)

    @property
    def copied_count(self) -> int:
        return len(self._copied_orders)

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        if self._running:
            logger.warning("OrderTracker is already running.")
            return
        settings = get_settings()
        self._scheduler = AsyncIOScheduler()
        self._scheduler.add_job(
            self._poll,
            "interval",
            seconds=settings.POLL_INTERVAL_SECONDS,
            id="poll_target",
            replace_existing=True,
        )
        self._scheduler.start()
        self._running = True
        logger.info(
            "OrderTracker started (interval=%ds, target=%s)",
            settings.POLL_INTERVAL_SECONDS,
            settings.TARGET_WALLET_ADDRESS,
        )

    def stop(self) -> None:
        if not self._running:
            return
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        self._running = False
        logger.info("OrderTracker stopped.")

    # ------------------------------------------------------------------ #
    # Internal polling logic
    # ------------------------------------------------------------------ #

    async def _poll(self) -> None:
        settings = get_settings()
        target = settings.TARGET_WALLET_ADDRESS
        if not target:
            logger.warning("TARGET_WALLET_ADDRESS is not set; skipping poll.")
            return

        logger.debug("Polling orders for target: %s", target)
        try:
            orders: List[Dict[str, Any]] = await pm_client.fetch_target_orders(target)
            self._last_poll = datetime.now(timezone.utc)
        except Exception as exc:
            logger.error("Error during poll: %s", exc)
            self._error_count += 1
            return

        for order in orders:
            order_id: str = str(order.get("id") or order.get("order_id") or "")
            if not order_id:
                continue

            with self._lock:
                already_copied = order_id in self._copied_ids

            if already_copied:
                continue

            await self._copy_order(order_id, order, settings)

    async def _copy_order(
        self,
        order_id: str,
        order: Dict[str, Any],
        settings: Any,
    ) -> None:
        token_id: str = str(order.get("asset_id") or order.get("token_id") or "")
        side: str = str(order.get("side") or "BUY").upper()
        try:
            price = float(order.get("price", 0))
            size = float(order.get("original_size") or order.get("size") or 0)
        except (TypeError, ValueError):
            logger.error("Invalid price/size for order %s", order_id)
            return

        if not token_id or price <= 0 or size <= 0:
            logger.warning("Skipping invalid order %s", order_id)
            return

        copied_size = round(size * settings.COPY_MULTIPLIER, 6)

        copied = CopiedOrder(
            original_order_id=order_id,
            token_id=token_id,
            side=side,
            price=price,
            size=copied_size,
            status="pending",
        )

        logger.info(
            "Copying order %s: %s %s @ %s (size %s)",
            order_id,
            side,
            token_id,
            price,
            copied_size,
        )

        result = await pm_client.place_order(token_id, price, copied_size, side)

        with self._lock:
            self._copied_ids.add(order_id)
            if result:
                copied.copied_order_id = str(
                    result.get("orderID") or result.get("order_id") or ""
                )
                copied.status = "success"
                logger.info(
                    "Order %s copied successfully -> %s",
                    order_id,
                    copied.copied_order_id,
                )
            else:
                copied.status = "error"
                copied.error = "place_order returned None"
                self._error_count += 1
                logger.error("Failed to copy order %s", order_id)

            self._copied_orders.append(copied)
