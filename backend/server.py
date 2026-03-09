from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
import os
import logging
import uuid
import asyncio
from pathlib import Path

from core.config import validate_environment, ENV, DEMO_MODE
from core.deps import (
    db, mongo_client, limiter, market_provider,
    fast_movers_detector, trading_bot,
    dump_detection_engine, price_streaming_service
)
import core.deps as core_deps
from core.error_handlers import validation_exception_handler, http_exception_handler, generic_exception_handler
from market_provider import run_market_data_refresh_task
from fast_movers_detector import run_fast_movers_background_task
from trading_bot import run_trading_bot_background_task
from price_streaming import run_price_streaming_task
from ai_dump_alert_service import run_dump_alert_background_task
from chain_registry import refresh_chain_registry
from core.redis_client import init_redis, close_redis

from routers import (
    auth, alerts, portfolio, ai, positions,
    dex, crypto, social, backtest, events,
    analytics, intelligence, invest
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

validate_environment()

app = FastAPI(title="Moon Hunters API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    logger.info(f"[{request_id[:8]}] {request.method} {request.url.path}")
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(f"[{request_id[:8]}] Unhandled error: {e}")
        response = JSONResponse({"error": "Internal server error"}, status_code=500)
    response.headers["X-Request-ID"] = request_id
    logger.info(f"[{request_id[:8]}] Response: {response.status_code}")
    return response


@app.middleware("http")
async def add_security_headers_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(f"Security middleware caught error: {e}")
        response = JSONResponse({"error": "Internal server error"}, status_code=500)
    csp_directives = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://www.googletagmanager.com https://*.walletconnect.com https://*.walletconnect.org https://*.reown.com https://unpkg.com",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com data:",
        "img-src 'self' data: blob: https:",
        "connect-src 'self' https: wss: ws:",
        "frame-src 'self' https://*.walletconnect.com https://*.walletconnect.org https://*.reown.com",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'self'",
        "upgrade-insecure-requests"
    ]
    response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


@app.get("/health")
async def health_check():
    db_status = "unknown"
    try:
        await asyncio.wait_for(db.command("ping"), timeout=2.0)
        db_status = "connected"
    except asyncio.TimeoutError:
        db_status = "connecting"
    except Exception:
        db_status = "disconnected"

    ws_connections = price_streaming_service.get_connection_count()

    if db_status == "connected":
        status = "healthy"
    elif db_status == "connecting":
        status = "starting"
    else:
        status = "degraded"

    return {
        "status": status,
        "service": "moon-hunters-api",
        "environment": ENV,
        "demo_mode": DEMO_MODE,
        "database": db_status,
        "websocket_connections": ws_connections,
        "streaming_active": price_streaming_service.is_streaming,
    }


app.include_router(auth.router)
app.include_router(alerts.router)
app.include_router(portfolio.router)
app.include_router(ai.router)
app.include_router(positions.router)
app.include_router(dex.router)
app.include_router(crypto.router)
app.include_router(social.router)
app.include_router(backtest.router)
app.include_router(events.router)
app.include_router(analytics.router)
app.include_router(intelligence.router)
app.include_router(invest.router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', 'http://localhost:5000').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    token = websocket.query_params.get("token")
    authenticated = False
    if token:
        from wallet_auth import decode_wallet_jwt
        from auth_utils import decode_access_token
        wallet = decode_wallet_jwt(token)
        if wallet:
            authenticated = True
        else:
            payload = decode_access_token(token)
            if payload:
                authenticated = True

    if not authenticated:
        await websocket.close(code=4001, reason="Authentication required")
        logger.warning("WebSocket connection rejected: no valid token")
        return

    await price_streaming_service.connect(websocket)
    logger.info(f"WebSocket connected (authenticated={authenticated})")

    import time
    message_count = 0
    window_start = time.time()
    max_messages_per_minute = 60

    try:
        while True:
            data = await websocket.receive_text()
            now = time.time()
            if now - window_start >= 60:
                message_count = 0
                window_start = now
            message_count += 1
            if message_count > max_messages_per_minute:
                await websocket.send_text('{"error": "rate_limit_exceeded"}')
                continue
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        price_streaming_service.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        price_streaming_service.disconnect(websocket)


@app.get("/api/ws/status")
async def websocket_status():
    return {
        "active_connections": price_streaming_service.get_connection_count(),
        "is_streaming": price_streaming_service.is_streaming
    }


@app.on_event("startup")
async def startup_event():
    app.state.background_tasks = []
    app.state.startup_complete = False
    asyncio.create_task(_deferred_startup())
    logger.info("Server accepting requests — background initialization starting...")


async def _deferred_startup():
    # ---- Redis cache ----
    await init_redis()

    # ---- Chain Registry: must succeed before anything else ----
    for attempt in range(3):
        try:
            count = await refresh_chain_registry()
            logger.info(f"Chain registry ready: {count} chains (attempt {attempt + 1})")
            break
        except Exception as e:
            logger.error(f"Chain registry refresh failed (attempt {attempt + 1}/3): {e}")
            if attempt < 2:
                await asyncio.sleep(10)
            else:
                raise RuntimeError("Chain registry refresh failed after 3 attempts — cannot start") from e

    async def _chain_registry_loop():
        while True:
            await asyncio.sleep(6 * 3600)  # 6 hours
            try:
                count = await refresh_chain_registry()
                logger.info(f"Periodic chain registry refresh: {count} chains")
            except Exception as e:
                logger.error(f"Periodic chain registry refresh failed (keeping current data): {e}")

    asyncio.create_task(_chain_registry_loop())

    async def _init_indexes():
        try:
            from core.indexes import ensure_database_indexes
            await asyncio.wait_for(ensure_database_indexes(db), timeout=15.0)
        except asyncio.TimeoutError:
            logger.warning("Database index creation timed out after 15s, continuing without indexes")
        except Exception as e:
            logger.warning(f"Database index creation failed: {e}")

    asyncio.create_task(_init_indexes())

    async def delayed_start(name, coro, delay):
        try:
            await asyncio.sleep(delay)
            logger.info(f"Starting {name} (after {delay}s delay)...")
            await coro
        except asyncio.CancelledError:
            logger.info(f"{name} task cancelled")
            raise
        except Exception as e:
            logger.error(f"{name} background task failed: {e}")

    def _create_task(coro, name):
        task = asyncio.create_task(coro, name=name)
        app.state.background_tasks.append(task)
        return task

    try:
        logger.info("Starting centralized market data refresh task...")
        _create_task(run_market_data_refresh_task(market_provider, interval=60), "market_data_refresh")
    except Exception as e:
        logger.warning(f"Market data refresh task failed to start: {e}.")

    try:
        _create_task(delayed_start("Fast Movers", run_fast_movers_background_task(fast_movers_detector), 10), "fast_movers")
    except Exception as e:
        logger.warning(f"Fast Movers background task failed to start: {e}.")

    try:
        _create_task(delayed_start("Trading Bot", run_trading_bot_background_task(trading_bot), 15), "trading_bot")
    except Exception as e:
        logger.warning(f"Trading Bot background task failed to start: {e}.")

    try:
        _create_task(delayed_start("Price Streaming", run_price_streaming_task(market_provider, interval_seconds=30), 5), "price_streaming")
    except Exception as e:
        logger.warning(f"Price Streaming background task failed to start: {e}.")

    try:
        _create_task(delayed_start("AI Dump Alert", run_dump_alert_background_task(
            db=db,
            dump_detection_engine=dump_detection_engine,
            market_provider=market_provider,
            app_url="",
            interval_minutes=5
        ), 20), "ai_dump_alert")
    except Exception as e:
        logger.warning(f"AI Dump Alert background task failed to start: {e}.")

    try:
        from trading_intelligence.service import init_trading_intelligence, run_intelligence_background_task
        ti_service = init_trading_intelligence(db, market_provider)
        core_deps.ti_service = ti_service
        _create_task(delayed_start("Trading Intelligence", run_intelligence_background_task(ti_service), 25), "trading_intelligence")
    except Exception as e:
        logger.warning(f"Trading Intelligence background task failed to start: {e}.")

    app.state.startup_complete = True
    logger.info("Startup complete — all background tasks launched.")


@app.on_event("shutdown")
async def shutdown_db_client():
    await close_redis()
    mongo_client.close()


FRONTEND_BUILD_DIR = Path(__file__).parent.parent / "frontend" / "build"

if FRONTEND_BUILD_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_BUILD_DIR / "assets"), name="assets")

    @app.get("/")
    async def serve_root():
        try:
            index_file = FRONTEND_BUILD_DIR / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
            return JSONResponse({"error": "Frontend build not found"}, status_code=503)
        except Exception as e:
            logger.error(f"Error serving root: {e}")
            return JSONResponse({"error": "Service temporarily unavailable"}, status_code=503)

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path == "health" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        try:
            file_path = FRONTEND_BUILD_DIR / full_path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            index_file = FRONTEND_BUILD_DIR / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
            return JSONResponse({"error": "Frontend build not found"}, status_code=503)
        except Exception as e:
            logger.error(f"Error serving SPA route {full_path}: {e}")
            return JSONResponse({"error": "Service temporarily unavailable"}, status_code=503)
