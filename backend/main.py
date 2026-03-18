from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .models import BotStatus, ConfigUpdate, CopiedOrder, OrderInfo
from . import polymarket_client as pm_client
from .tracker import OrderTracker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Polymarket Copy Trader", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tracker = OrderTracker()

# ── Static files ──────────────────────────────────────────────────────────────
_frontend_dir = Path(__file__).parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_frontend_dir)), name="static")


@app.get("/", include_in_schema=False)
async def serve_index() -> FileResponse:
    index = _frontend_dir / "index.html"
    if index.exists():
        return FileResponse(str(index))
    raise HTTPException(status_code=404, detail="Frontend not found")


# ── Status / control ──────────────────────────────────────────────────────────

@app.get("/api/status", response_model=BotStatus)
async def get_status() -> BotStatus:
    settings = get_settings()
    return BotStatus(
        running=tracker.running,
        target_wallet=settings.TARGET_WALLET_ADDRESS,
        poll_interval=settings.POLL_INTERVAL_SECONDS,
        copy_multiplier=settings.COPY_MULTIPLIER,
        copied_count=tracker.copied_count,
        error_count=tracker.error_count,
        last_poll=tracker.last_poll,
    )


@app.post("/api/start")
async def start_bot() -> Dict[str, str]:
    if tracker.running:
        return {"status": "already running"}
    tracker.start()
    return {"status": "started"}


@app.post("/api/stop")
async def stop_bot() -> Dict[str, str]:
    if not tracker.running:
        return {"status": "already stopped"}
    tracker.stop()
    return {"status": "stopped"}


# ── Orders ────────────────────────────────────────────────────────────────────

@app.get("/api/orders/target")
async def get_target_orders() -> List[Dict[str, Any]]:
    settings = get_settings()
    if not settings.TARGET_WALLET_ADDRESS:
        raise HTTPException(status_code=400, detail="TARGET_WALLET_ADDRESS is not configured")
    return await pm_client.fetch_target_orders(settings.TARGET_WALLET_ADDRESS)


@app.get("/api/orders/copied", response_model=List[CopiedOrder])
async def get_copied_orders() -> List[CopiedOrder]:
    return tracker.copied_orders


@app.get("/api/orders/own")
async def get_own_orders() -> List[Dict[str, Any]]:
    return await pm_client.get_open_orders()


# ── Config / actions ──────────────────────────────────────────────────────────

@app.post("/api/config")
async def update_config(update: ConfigUpdate) -> Dict[str, str]:
    settings = get_settings()
    if update.target_wallet_address is not None:
        settings.TARGET_WALLET_ADDRESS = update.target_wallet_address
    if update.copy_multiplier is not None:
        settings.COPY_MULTIPLIER = update.copy_multiplier
    if update.poll_interval_seconds is not None:
        settings.POLL_INTERVAL_SECONDS = update.poll_interval_seconds
    if update.api_key is not None:
        settings.POLYMARKET_API_KEY = update.api_key
    if update.api_secret is not None:
        settings.POLYMARKET_API_SECRET = update.api_secret
    if update.passphrase is not None:
        settings.POLYMARKET_PASSPHRASE = update.passphrase
    if update.private_key is not None:
        settings.PRIVATE_KEY = update.private_key
    # Clear the lru_cache so the tracker picks up fresh settings
    get_settings.cache_clear()
    return {"status": "config updated"}


@app.post("/api/cancel-all")
async def cancel_all() -> Dict[str, Any]:
    success = await pm_client.cancel_all_orders()
    return {"success": success}


@app.get("/api/markets")
async def get_markets() -> List[Dict[str, Any]]:
    return await pm_client.get_markets()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=False)
