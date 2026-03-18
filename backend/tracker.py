"""Order tracker — periodically polls and copies target wallet orders."""

import logging
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from apscheduler.schedulers.background import BackgroundScheduler

from . import polymarket_client as pm_client
from .config import settings
from .models import CopiedOrder

logger = logging.getLogger(__name__)


class OrderTracker:
    """Polls target wallet orders and copies new ones to the bot's account."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._copied_ids: Set[str] = set()
        self._history: List[CopiedOrder] = []
        self._scheduler: Optional[BackgroundScheduler] = None
        self._is_running: bool = False
        self._last_poll_time: Optional[datetime] = None

        # Mutable config (can be updated via API)
        self.target_address: str = settings.TARGET_WALLET_ADDRESS
        self.copy_multiplier: float = settings.COPY_MULTIPLIER
        self.poll_interval: int = settings.POLL_INTERVAL_SECONDS

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def last_poll_time(self) -> Optional[datetime]:
        return self._last_poll_time

    @property
    def total_copied(self) -> int:
        with self._lock:
            return len(self._history)

    def get_history(self) -> List[CopiedOrder]:
        with self._lock:
            return list(self._history)

    def start(self) -> None:
        """Start the periodic polling scheduler."""
        if self._is_running:
            logger.warning("Tracker is already running.")
            return
        self._scheduler = BackgroundScheduler()
        self._scheduler.add_job(
            self._poll,
            "interval",
            seconds=self.poll_interval,
            id="poll_job",
            max_instances=1,
            coalesce=True,
        )
        self._scheduler.start()
        self._is_running = True
        logger.info(
            "OrderTracker started. target=%s interval=%ds multiplier=%.2f",
            self.target_address,
            self.poll_interval,
            self.copy_multiplier,
        )

    def stop(self) -> None:
        """Stop the periodic polling scheduler."""
        if not self._is_running:
            logger.warning("Tracker is not running.")
            return
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
        self._is_running = False
        logger.info("OrderTracker stopped.")

    # ------------------------------------------------------------------
    # Internal polling logic
    # ------------------------------------------------------------------

    def _poll(self) -> None:
        """Poll target orders and copy any new ones."""
        now = datetime.now(tz=timezone.utc)
        self._last_poll_time = now

        if not self.target_address:
            logger.warning("No target address configured — skipping poll.")
            return

        logger.debug("Polling orders for %s", self.target_address)
        try:
            orders = pm_client.fetch_target_orders(self.target_address)
        except Exception as exc:  # noqa: BLE001
            logger.error("Error during poll: %s", exc)
            return

        for order in orders:
            self._process_order(order)

    def _process_order(self, order: Dict) -> None:
        """Process a single order dict from the target wallet."""
        order_id: Optional[str] = order.get("id") or order.get("order_id")
        if not order_id:
            logger.debug("Order without ID skipped: %s", order)
            return

        with self._lock:
            if order_id in self._copied_ids:
                logger.debug("Order %s already copied — skipping.", order_id)
                return

        token_id: str = order.get("asset_id") or order.get("token_id") or ""
        side: str = (order.get("side") or "BUY").upper()
        try:
            price = float(order.get("price", 0))
            size = float(order.get("original_size") or order.get("size") or 0)
        except (TypeError, ValueError):
            logger.warning("Cannot parse price/size for order %s", order_id)
            return

        if not token_id or price <= 0 or size <= 0:
            logger.warning(
                "Skipping order %s — invalid token/price/size: token=%s price=%s size=%s",
                order_id,
                token_id,
                price,
                size,
            )
            return

        copied_size = round(size * self.copy_multiplier, 6)
        logger.info(
            "Copying order %s: token=%s side=%s price=%s size=%s → copied_size=%s",
            order_id,
            token_id,
            side,
            price,
            size,
            copied_size,
        )

        resp = pm_client.place_order(
            token_id=token_id,
            price=price,
            size=copied_size,
            side=side,
        )

        copied_order_id: Optional[str] = None
        status = "error"
        if resp:
            copied_order_id = (
                resp.get("orderID")
                or resp.get("order_id")
                or resp.get("id")
            )
            status = "placed" if copied_order_id else "submitted"

        copied = CopiedOrder(
            original_order_id=order_id,
            copied_order_id=copied_order_id,
            token_id=token_id,
            side=side,
            price=price,
            original_size=size,
            copied_size=copied_size,
            timestamp=datetime.now(tz=timezone.utc),
            status=status,
        )

        with self._lock:
            self._copied_ids.add(order_id)
            self._history.append(copied)

        logger.info("Order %s copy status: %s", order_id, status)
