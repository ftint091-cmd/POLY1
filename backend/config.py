from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.POLYMARKET_API_KEY: str = os.getenv("POLYMARKET_API_KEY", "")
        self.POLYMARKET_API_SECRET: str = os.getenv("POLYMARKET_API_SECRET", "")
        self.POLYMARKET_PASSPHRASE: str = os.getenv("POLYMARKET_PASSPHRASE", "")
        self.CLOB_API_URL: str = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")
        self.CHAIN_ID: int = int(os.getenv("CHAIN_ID", "137"))
        self.TARGET_WALLET_ADDRESS: str = os.getenv("TARGET_WALLET_ADDRESS", "")
        self.PRIVATE_KEY: str = os.getenv("PRIVATE_KEY", "")
        self.COPY_MULTIPLIER: float = float(os.getenv("COPY_MULTIPLIER", "1.0"))
        self.POLL_INTERVAL_SECONDS: int = int(os.getenv("POLL_INTERVAL_SECONDS", "10"))
        self.HOST: str = os.getenv("HOST", "0.0.0.0")
        self.PORT: int = int(os.getenv("PORT", "8000"))


@lru_cache()
def get_settings() -> Settings:
    return Settings()
