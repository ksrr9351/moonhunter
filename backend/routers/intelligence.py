from fastapi import APIRouter, HTTPException, Depends, Request, Query
import logging

import core.deps as core_deps
from core.deps import get_current_user, limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _get_ti_service():
    if core_deps.ti_service is None:
        raise HTTPException(status_code=503, detail="Trading intelligence service is still initializing")
    return core_deps.ti_service


@router.get("/intelligence/signal/{symbol}")
@limiter.limit("60/minute")
async def get_trading_signal(
    request: Request,
    symbol: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        result = await _get_ti_service().get_signal(symbol.upper())
        return result
    except Exception as e:
        logger.error(f"Error getting signal for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/intelligence/signals")
@limiter.limit("30/minute")
async def get_all_trading_signals(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    try:
        results = await _get_ti_service().get_all_signals(limit=limit)
        return {"success": True, "signals": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error getting all signals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/intelligence/top-signals")
@limiter.limit("30/minute")
async def get_top_signals(
    request: Request,
    signal_type: str = Query("BUY", description="Signal type: BUY, SELL, HOLD"),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    try:
        results = await _get_ti_service().get_top_signals(signal_type=signal_type, limit=limit)
        return {"success": True, "signals": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error getting top signals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/intelligence/anomalies")
@limiter.limit("30/minute")
async def get_anomalies(
    request: Request,
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    try:
        results = await _get_ti_service().get_anomalies(limit=limit)
        return {"success": True, "anomalies": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error getting anomalies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/intelligence/pump-dump-alerts")
@limiter.limit("30/minute")
async def get_pump_dump_alerts(
    request: Request,
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    try:
        results = await _get_ti_service().get_pump_dump_alerts(limit=limit)
        return {"success": True, "alerts": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error getting pump/dump alerts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/intelligence/stats")
@limiter.limit("30/minute")
async def get_intelligence_stats(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    try:
        stats = await _get_ti_service().get_engine_stats()
        return {"success": True, **stats}
    except Exception as e:
        logger.error(f"Error getting intelligence stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
