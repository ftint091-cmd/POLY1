"""Pydantic models for the Polymarket Copy-Trading Bot."""

from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class OrderInfo(BaseModel):
    """Represents an order from Polymarket."""

    id: str
    token_id: str
    market_slug: Optional[str] = None
    side: str
    price: float
    size: float
    status: str
    timestamp: Optional[datetime] = None


class CopiedOrder(BaseModel):
    """Represents an order that was copied by the bot."""

    original_order_id: str
    copied_order_id: Optional[str] = None
    token_id: str
    side: str
    price: float
    original_size: float
    copied_size: float
    timestamp: datetime
    status: str


class BotStatus(BaseModel):
    """Current status of the copy-trading bot."""

    is_running: bool
    target_address: str
    copy_multiplier: float
    poll_interval: int
    total_copied: int
    last_poll_time: Optional[datetime] = None


class ConfigUpdate(BaseModel):
    """Request body for updating bot configuration."""

    target_address: Optional[str] = None
    copy_multiplier: Optional[float] = None
    poll_interval: Optional[int] = None
