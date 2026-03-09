from fastapi import APIRouter, Depends, HTTPException, Request
from datetime import datetime, timezone, timedelta
import logging

from core.deps import backtesting, limiter, get_current_user
from core.schemas import BacktestRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get("/backtest/strategies")
@limiter.limit("30/minute")
async def get_backtest_strategies(request: Request, user: dict = Depends(get_current_user)):
    """Get available backtesting strategies"""
    try:
        strategies = backtesting.get_available_strategies()
        return {"strategies": strategies}
    except Exception as e:
        logger.error(f"Error fetching strategies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/backtest/run")
@limiter.limit("5/minute")
async def run_backtest(request: Request, body: BacktestRequest, user: dict = Depends(get_current_user)):
    """Run a backtest simulation"""
    try:
        start_date = body.start_date or (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        end_date = body.end_date or datetime.now(timezone.utc).isoformat()
        
        result = await backtesting.run_backtest(
            strategy=body.strategy,
            initial_capital=body.initial_capital,
            start_date=start_date,
            end_date=end_date,
            params=body.params
        )
        return result
    except Exception as e:
        logger.error(f"Error running backtest: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
