"""FastAPI application for the Polymarket Copy-Trading Bot."""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .models import BotStatus, ConfigUpdate, CopiedOrder
from . import polymarket_client as pm_client
from .tracker import OrderTracker

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
tracker = OrderTracker()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("=== Polymarket Copy-Trading Bot starting ===")
    logger.info("CLOB API URL   : %s", settings.CLOB_API_URL)
    logger.info("Chain ID       : %s", settings.CHAIN_ID)
    logger.info("Target wallet  : %s", settings.TARGET_WALLET_ADDRESS)
    logger.info("Copy multiplier: %.2f", settings.COPY_MULTIPLIER)
    logger.info("Poll interval  : %ds", settings.POLL_INTERVAL_SECONDS)
    logger.info("API key present: %s", bool(settings.POLYMARKET_API_KEY))
    yield
    if tracker.is_running:
        tracker.stop()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Polymarket Copy-Trading Bot", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Static files (frontend)
# ---------------------------------------------------------------------------
_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=_FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
async def serve_index() -> FileResponse:
    index_path = os.path.join(_FRONTEND_DIR, "index.html")
    return FileResponse(index_path)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup() -> None:
    logger.info("=== Polymarket Copy-Trading Bot starting ===")
    logger.info("CLOB API URL  : %s", settings.CLOB_API_URL)
    logger.info("Chain ID      : %s", settings.CHAIN_ID)
    logger.info("Target wallet : %s", settings.TARGET_WALLET_ADDRESS)
    logger.info("Copy multiplier: %.2f", settings.COPY_MULTIPLIER)
    logger.info("Poll interval : %ds", settings.POLL_INTERVAL_SECONDS)
    logger.info("API key present: %s", bool(settings.POLYMARKET_API_KEY))


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@app.get("/api/status", response_model=BotStatus)
async def get_status() -> BotStatus:
    return BotStatus(
        is_running=tracker.is_running,
        target_address=tracker.target_address,
        copy_multiplier=tracker.copy_multiplier,
        poll_interval=tracker.poll_interval,
        total_copied=tracker.total_copied,
        last_poll_time=tracker.last_poll_time,
    )


@app.post("/api/start")
async def start_bot() -> Dict[str, str]:
    if tracker.is_running:
        return {"message": "Bot is already running"}
    tracker.start()
    return {"message": "Bot started"}


@app.post("/api/stop")
async def stop_bot() -> Dict[str, str]:
    if not tracker.is_running:
        return {"message": "Bot is not running"}
    tracker.stop()
    return {"message": "Bot stopped"}


@app.get("/api/orders/target", response_model=List[Dict[str, Any]])
async def get_target_orders() -> List[Dict[str, Any]]:
    if not tracker.target_address:
        raise HTTPException(status_code=400, detail="Target address not configured")
    return pm_client.fetch_target_orders(tracker.target_address)


@app.get("/api/orders/copied", response_model=List[CopiedOrder])
async def get_copied_orders() -> List[CopiedOrder]:
    return tracker.get_history()


@app.get("/api/orders/own", response_model=List[Dict[str, Any]])
async def get_own_orders() -> List[Dict[str, Any]]:
    return pm_client.get_open_orders()


@app.post("/api/config")
async def update_config(update: ConfigUpdate) -> Dict[str, str]:
    if update.target_address is not None:
        tracker.target_address = update.target_address
        logger.info("Config updated: target_address=%s", update.target_address)
    if update.copy_multiplier is not None:
        tracker.copy_multiplier = update.copy_multiplier
        logger.info("Config updated: copy_multiplier=%.2f", update.copy_multiplier)
    if update.poll_interval is not None:
        tracker.poll_interval = update.poll_interval
        logger.info("Config updated: poll_interval=%ds", update.poll_interval)
    return {"message": "Configuration updated"}


@app.post("/api/cancel-all")
async def cancel_all_orders() -> Dict[str, str]:
    success = pm_client.cancel_all_orders()
    if success:
        return {"message": "All orders cancelled"}
    raise HTTPException(status_code=500, detail="Failed to cancel orders")


@app.get("/api/markets", response_model=List[Dict[str, Any]])
async def get_markets() -> List[Dict[str, Any]]:
    return pm_client.get_markets()
