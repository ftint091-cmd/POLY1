from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class OrderInfo(BaseModel):
    order_id: str
    market: str
    token_id: str
    side: str
    price: float
    size: float
    size_matched: float = 0.0
    status: str
    created_at: Optional[datetime] = None


class CopiedOrder(BaseModel):
    original_order_id: str
    copied_order_id: Optional[str] = None
    token_id: str
    side: str
    price: float
    size: float
    status: str = "pending"
    error: Optional[str] = None
    copied_at: datetime = Field(default_factory=datetime.utcnow)


class BotStatus(BaseModel):
    running: bool
    target_wallet: str
    poll_interval: int
    copy_multiplier: float
    copied_count: int
    error_count: int
    last_poll: Optional[datetime] = None


class ConfigUpdate(BaseModel):
    target_wallet_address: Optional[str] = None
    copy_multiplier: Optional[float] = None
    poll_interval_seconds: Optional[int] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None
    private_key: Optional[str] = None
