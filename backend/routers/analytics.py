from fastapi import APIRouter, HTTPException, Depends, Request, Query
import logging

from core.deps import db, get_current_user, analytics_engine, limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get("/analytics/performance")
@limiter.limit("30/minute")
async def get_performance_summary(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive performance summary"""
    try:
        summary = await analytics_engine.get_performance_summary(current_user["id"], days)
        return summary
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analytics/daily-returns")
@limiter.limit("30/minute")
async def get_daily_returns(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user)
):
    """Get daily returns for charting"""
    try:
        returns = await analytics_engine.get_daily_returns(current_user["id"], days)
        return {"returns": returns, "days": days}
    except Exception as e:
        logger.error(f"Error getting daily returns: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analytics/strategy-breakdown")
@limiter.limit("30/minute")
async def get_strategy_breakdown(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get performance breakdown by strategy"""
    try:
        breakdown = await analytics_engine.get_strategy_breakdown(current_user["id"])
        return {"strategies": breakdown}
    except Exception as e:
        logger.error(f"Error getting strategy breakdown: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analytics/coin-performance")
@limiter.limit("30/minute")
async def get_coin_performance(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Get performance breakdown by coin"""
    try:
        performance = await analytics_engine.get_coin_performance(current_user["id"], limit)
        return {"coins": performance}
    except Exception as e:
        logger.error(f"Error getting coin performance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analytics/bot-analytics")
@limiter.limit("30/minute")
async def get_bot_analytics(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get analytics specifically for bot trades"""
    try:
        analytics = await analytics_engine.get_bot_analytics(current_user["id"])
        return analytics
    except Exception as e:
        logger.error(f"Error getting bot analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
