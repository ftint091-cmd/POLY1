"""Configuration loader for the Polymarket Copy-Trading Bot."""

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def _get_float(key: str, default: float) -> float:
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_int(key: str, default: int) -> int:
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


class Settings:
    """Application settings loaded from environment variables."""

    POLYMARKET_API_KEY: str = os.getenv("POLYMARKET_API_KEY", "")
    POLYMARKET_API_SECRET: str = os.getenv("POLYMARKET_API_SECRET", "")
    POLYMARKET_PASSPHRASE: str = os.getenv("POLYMARKET_PASSPHRASE", "")
    PRIVATE_KEY: str = os.getenv("PRIVATE_KEY", "")

    CLOB_API_URL: str = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")
    CHAIN_ID: int = _get_int("CHAIN_ID", 137)

    TARGET_WALLET_ADDRESS: str = os.getenv("TARGET_WALLET_ADDRESS", "")

    COPY_MULTIPLIER: float = _get_float("COPY_MULTIPLIER", 1.0)
    POLL_INTERVAL_SECONDS: int = _get_int("POLL_INTERVAL_SECONDS", 10)

    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = _get_int("PORT", 8000)


settings = Settings()
