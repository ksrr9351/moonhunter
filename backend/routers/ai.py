from fastapi import APIRouter, Request, Depends, HTTPException, Query
import logging
from datetime import datetime, timezone, timedelta

from chain_registry import get_all_chain_ids

from core.deps import (
    db, get_current_user, limiter, recommendation_engine,
    dump_detection_engine, market_provider,
    auto_invest_scheduler, portfolio_engine, wallet_service
)
from core.schemas import (
    AutoInvestConfig, AutoInvestConfigUpdate,
    AIInvestRequest, AIAllocateRequest, AutoInvestCompleteRequest,
    CompletedSwapItem, CreatePositionRequest, ClosePositionRequest,
    RecordDexSwapRequest, CloseDexPositionRequest
)
from event_service import emit_ai_trade_executed, emit_auto_invest_executed

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")



# ==================== AUTO-INVEST CONFIG ====================

@router.get("/auto-invest/config")
@limiter.limit("60/minute")
async def get_auto_invest_config(request: Request, current_user: dict = Depends(get_current_user)):
    """Get user's auto-invest configuration"""
    try:
        config = await db.auto_invest_configs.find_one({"user_id": current_user["id"]}, {"_id": 0})
        
        if not config:
            auto_invest_config = AutoInvestConfig(user_id=current_user["id"])
            config_dict = auto_invest_config.model_dump()
            config_dict['created_at'] = config_dict['created_at'].isoformat()
            config_dict['updated_at'] = config_dict['updated_at'].isoformat()
            await db.auto_invest_configs.insert_one(config_dict)
            return auto_invest_config
        else:
            if isinstance(config.get('created_at'), str):
                config['created_at'] = datetime.fromisoformat(config['created_at'])
            if isinstance(config.get('updated_at'), str):
                config['updated_at'] = datetime.fromisoformat(config['updated_at'])
            return AutoInvestConfig(**config)
    except Exception as e:
        logger.error(f"Error fetching auto-invest config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/auto-invest/config")
@limiter.limit("30/minute")
async def update_auto_invest_config(
    request: Request,
    update: AutoInvestConfigUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update auto-invest configuration"""
    try:
        config = await db.auto_invest_configs.find_one({"user_id": current_user["id"]}, {"_id": 0})
        
        if not config:
            raise HTTPException(status_code=404, detail="Auto-invest config not found")
        
        update_dict = {k: v for k, v in update.model_dump().items() if v is not None}
        update_dict['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        await db.auto_invest_configs.update_one(
            {"user_id": current_user["id"]},
            {"$set": update_dict}
        )
        
        updated_config = await db.auto_invest_configs.find_one({"user_id": current_user["id"]}, {"_id": 0})
        
        if isinstance(updated_config.get('created_at'), str):
            updated_config['created_at'] = datetime.fromisoformat(updated_config['created_at'])
        if isinstance(updated_config.get('updated_at'), str):
            updated_config['updated_at'] = datetime.fromisoformat(updated_config['updated_at'])
        
        return updated_config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating auto-invest config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/auto-invest/prepare")
@limiter.limit("10/minute")
async def prepare_auto_invest(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Prepare auto-invest execution plan for wallet approval"""
    try:
        result = await auto_invest_scheduler.prepare_investment(current_user["id"])
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to prepare investment"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error preparing auto-invest: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/auto-invest/approve/{execution_id}")
@limiter.limit("10/minute")
async def approve_auto_invest(
    request: Request,
    execution_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Approve auto-invest execution and get swap transactions"""
    try:
        user = await db.users.find_one({"id": current_user["id"]}, {"_id": 0})
        wallet_address = user.get("wallet_address")
        
        if not wallet_address:
            raise HTTPException(status_code=400, detail="No wallet connected to account")
        
        result = await auto_invest_scheduler.approve_execution(
            execution_id, 
            wallet_address, 
            current_user["id"]
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to approve execution"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving auto-invest: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/auto-invest/complete/{execution_id}")
@limiter.limit("10/minute")
async def complete_auto_invest(
    request: Request,
    execution_id: str,
    body: AutoInvestCompleteRequest,
    current_user: dict = Depends(get_current_user)
):
    """Mark auto-invest execution as complete"""
    try:
        completed_swaps = [swap.model_dump() for swap in body.completed_swaps]
        result = await auto_invest_scheduler.mark_execution_complete(
            execution_id, 
            completed_swaps,
            current_user["id"]
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to complete execution"))
        
        config = await auto_invest_scheduler.get_user_config(current_user["id"])
        await emit_auto_invest_executed(
            user_id=current_user["id"],
            cycle_type=config.get("frequency", "unknown"),
            trades_executed=completed_swaps
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing auto-invest: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/auto-invest/history")
@limiter.limit("30/minute")
async def get_auto_invest_history(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Get auto-invest execution history"""
    try:
        history = await auto_invest_scheduler.get_execution_history(current_user["id"], limit)
        return history
    except Exception as e:
        logger.error(f"Error fetching auto-invest history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== MOON HUNTERS AI ENGINE ENDPOINTS ====================

@router.get("/ai-engine/wallet-status")
@limiter.limit("30/minute")
async def get_ai_wallet_status(
    request: Request,
    current_user: dict = Depends(get_current_user),
    chain_id: int = Query(None, description="Chain ID to fetch balances from (optional, auto-detected if not provided)")
):
    """Get wallet status with USDT balance for AI Engine"""
    try:
        from wallet_service import SUPPORTED_CHAIN_IDS
        if chain_id is not None and chain_id not in SUPPORTED_CHAIN_IDS:
            raise HTTPException(status_code=400, detail=f"Unsupported chain_id={chain_id}")
        logger.info(f"Fetching wallet status for user={current_user['id'][:8]}... chain_id={chain_id}")
        status = await wallet_service.get_user_wallet_status(current_user["id"], chain_id=chain_id)
        return status
    except Exception as e:
        logger.error(f"Error fetching wallet status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")



@router.get("/ai-engine/dump-opportunities")
@limiter.limit("30/minute")
async def get_dump_opportunities(request: Request, current_user: dict = Depends(get_current_user)):
    """Get current dump buy opportunities from centralized dump_opportunities collection"""
    try:
        now = datetime.utcnow()

        stored_opps = await db.dump_opportunities.find(
            {"expires_at": {"$gt": now}}, {"_id": 0}
        ).sort("dump_percentage", 1).to_list(50)

        dump_opportunities = []
        for opp in stored_opps:
            source = opp.get("source", "")
            if "1h" in source:
                dump_window = "1h"
            elif "24h" in source:
                dump_window = "24h"
            else:
                dump_window = "24h"

            dump_pct = abs(opp.get("dump_percentage", 0))
            volume_24h = opp.get("volume_24h", 0)
            market_cap = opp.get("market_cap", 0)
            vol_mcap_ratio = (volume_24h / market_cap) if market_cap > 0 else 0

            if vol_mcap_ratio >= 0.01:
                volume_health = "healthy"
            elif vol_mcap_ratio > 0:
                volume_health = "low"
            else:
                volume_health = "unknown"

            dump_opportunities.append({
                "symbol": opp.get("symbol", ""),
                "name": opp.get("name", ""),
                "price_usdt": opp.get("current_price", 0),
                "change_1h": opp.get("dump_percentage", 0) if dump_window == "1h" else 0,
                "change_24h": opp.get("change_24h", opp.get("dump_percentage", 0)),
                "change_7d": 0,
                "volume_24h": volume_24h,
                "market_cap": market_cap,
                "rank": 0,
                "category": "dump_opportunity",
                "dump_magnitude": dump_pct,
                "dump_window": dump_window,
                "volume_health": volume_health,
                "risk_score": opp.get("risk_score", 0.5),
                "recommendation": "buy",
                "reason": opp.get("reason", f"5% dump detected ({dump_window}). Volume healthy."),
                "logo": opp.get("logo", "")
            })

        if len(dump_opportunities) < 3 and dump_detection_engine:
            try:
                live_opps = await dump_detection_engine.get_dump_opportunities()
                existing_symbols = {d["symbol"] for d in dump_opportunities}
                for lo in live_opps:
                    sym = lo.get("symbol", "")
                    if sym in existing_symbols:
                        continue
                    dump_opportunities.append(lo)
                    existing_symbols.add(sym)

                    dw = lo.get("dump_window", "24h")
                    change_key = "change_1h" if dw == "1h" else "change_24h"
                    change_val = lo.get(change_key, 0)
                    dp = change_val if change_val else -lo.get("dump_magnitude", 0)
                    mag = abs(dp)

                    if mag >= 10:
                        rs, rl = 0.8, "High"
                    elif mag >= 5:
                        rs, rl = 0.5, "Moderate"
                    else:
                        rs, rl = 0.3, "Low"

                    opp_doc = {
                        "symbol": sym,
                        "name": lo.get("name", sym),
                        "current_price": lo.get("price_usdt", 0),
                        "dump_percentage": round(dp, 2),
                        "detected_at": now,
                        "expires_at": now + timedelta(hours=1),
                        "market_cap": lo.get("market_cap", 0),
                        "volume_24h": lo.get("volume_24h", 0),
                        "logo": lo.get("logo", ""),
                        "risk_score": rs,
                        "risk_level": rl,
                        "ai_recommendation": lo.get("reason", "Dump opportunity detected"),
                        "reason": f"{sym} dumped {mag:.1f}% in {dw}",
                        "supported_chains": get_all_chain_ids(),
                        "change_24h": round(lo.get("change_24h", 0), 2),
                        "source": f"dump_engine_live_{dw}"
                    }
                    await db.dump_opportunities.update_one(
                        {"symbol": sym, "expires_at": {"$gt": now}},
                        {"$setOnInsert": opp_doc},
                        upsert=True
                    )
            except Exception as e:
                logger.warning(f"AI Engine live dump fallback failed: {e}")

        coins = await market_provider.get_coins_list(100)
        analysis = await dump_detection_engine.analyze_market(coins)

        return {
            "dump_opportunities": dump_opportunities,
            "pump_risks": analysis.get("pump_risks", []),
            "neutral": analysis.get("neutral", []),
            "avoid_list": analysis.get("avoid_list", []),
            "analysis_time": now.isoformat(),
            "total_analyzed": analysis.get("total_analyzed", 0)
        }
    except Exception as e:
        logger.error(f"Error detecting dumps: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/ai-engine/signals")
@limiter.limit("60/minute")
async def get_quick_signals(request: Request, current_user: dict = Depends(get_current_user)):
    """Get quick market signals for dashboard"""
    try:
        signals = await recommendation_engine.get_quick_signals()
        return signals
    except Exception as e:
        logger.error(f"Error getting signals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/ai-engine/recommendations")
@limiter.limit("20/minute")
async def get_ai_engine_recommendations(
    request: Request,
    invest_request: AIAllocateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Get AI-powered investment recommendations"""
    try:
        recommendations = await recommendation_engine.get_recommendations(
            user_id=current_user["id"],
            investment_amount=invest_request.usdt_amount
        )
        return recommendations
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/ai-engine/portfolio")
@limiter.limit("30/minute")
async def get_ai_portfolio(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get user's AI Engine portfolio with live PnL"""
    try:
        portfolio = await portfolio_engine.get_user_portfolio(current_user["id"])
        return portfolio
    except Exception as e:
        logger.error(f"Error fetching portfolio: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/ai-engine/rebalancing")
@limiter.limit("20/minute")
async def get_rebalancing_suggestions(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Get AI-driven portfolio rebalancing suggestions.
    Analyzes current allocations, PnL, and market momentum to suggest optimal actions.
    """
    try:
        suggestions = await portfolio_engine.get_rebalancing_suggestions(current_user["id"])
        return suggestions
    except Exception as e:
        logger.error(f"Error getting rebalancing suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/ai-engine/invest")
@limiter.limit("10/minute")
async def create_ai_investment(
    request: Request,
    position_request: CreatePositionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new investment position"""
    try:
        result = await portfolio_engine.create_investment(
            user_id=current_user["id"],
            symbol=position_request.symbol,
            usdt_amount=position_request.usdt_amount,
            strategy=position_request.strategy,
            trigger_reason=position_request.trigger_reason
        )
        
        if result.get("success"):
            await emit_ai_trade_executed(
                user_id=current_user["id"],
                tokens_traded=[position_request.symbol],
                allocations={position_request.symbol: position_request.usdt_amount},
                tx_hashes=[result.get("position", {}).get("tx_hash", "")]
            )
        
        return result
    except Exception as e:
        logger.error(f"Error creating investment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/ai-engine/invest-auto")
@limiter.limit("5/minute")
async def auto_invest_with_ai(
    request: Request,
    invest_request: AIInvestRequest,
    current_user: dict = Depends(get_current_user)
):
    """Automatically invest using AI recommendations"""
    try:
        recommendations = await recommendation_engine.get_recommendations(
            user_id=current_user["id"],
            investment_amount=invest_request.usdt_amount
        )
        
        if invest_request.strategy == "dump_buy":
            allocations = recommendations.get("dump_opportunities", [])
        elif invest_request.strategy == "trend_follow":
            allocations = recommendations.get("trend_candidates", [])
        else:
            allocations = (
                recommendations.get("dump_opportunities", []) +
                recommendations.get("trend_candidates", [])
            )
        
        if not allocations:
            return {
                "success": False,
                "error": "No suitable investment opportunities found",
                "recommendations": recommendations
            }
        
        result = await portfolio_engine.execute_allocations(
            user_id=current_user["id"],
            allocations=allocations[:5],
            strategy=invest_request.strategy
        )
        
        return {
            **result,
            "recommendations": recommendations
        }
    except Exception as e:
        logger.error(f"Error in auto-invest: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/ai-engine/close-position/{position_id}")
@limiter.limit("20/minute")
async def close_ai_position(
    request: Request,
    position_id: str,
    close_request: ClosePositionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Close an existing investment position"""
    try:
        result = await portfolio_engine.close_position(
            user_id=current_user["id"],
            position_id=position_id,
            reason=close_request.reason
        )
        return result
    except Exception as e:
        logger.error(f"Error closing position: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/ai-engine/record-dex-swap")
@limiter.limit("20/minute")
async def record_dex_swap(
    request: Request,
    swap_request: RecordDexSwapRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Record a real DEX swap as a portfolio position.
    Called after user executes a swap via the SwapModal.
    """
    try:
        result = await portfolio_engine.record_dex_swap(
            user_id=current_user["id"],
            symbol=swap_request.symbol,
            usdt_amount=swap_request.usdt_amount,
            quantity=swap_request.quantity,
            entry_price=swap_request.entry_price,
            tx_hash=swap_request.tx_hash,
            chain_id=swap_request.chain_id,
            strategy=swap_request.strategy,
            trigger_reason=swap_request.trigger_reason
        )
        
        if result.get("success"):
            await emit_ai_trade_executed(
                user_id=current_user["id"],
                tokens_traded=[swap_request.symbol],
                allocations={swap_request.symbol: swap_request.usdt_amount},
                tx_hashes=[swap_request.tx_hash or ""]
            )
        
        return result
    except Exception as e:
        logger.error(f"Error recording DEX swap: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/ai-engine/close-dex-position")
@limiter.limit("20/minute")
async def close_dex_position(
    request: Request,
    close_request: CloseDexPositionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Close a position after executing a real DEX sell swap.
    Records the sell transaction details and calculates realized PnL.
    """
    try:
        result = await portfolio_engine.close_position_with_dex(
            user_id=current_user["id"],
            position_id=close_request.position_id,
            exit_price=close_request.exit_price,
            exit_quantity=close_request.exit_quantity,
            tx_hash=close_request.tx_hash,
            reason=close_request.reason
        )
        
        if result.get("success"):
            position = await db.ai_positions.find_one({"id": close_request.position_id})
            if position:
                await emit_ai_trade_executed(
                    user_id=current_user["id"],
                    tokens_traded=[position.get("symbol", "")],
                    allocations={position.get("symbol", ""): result.get("exit_value", 0)},
                    tx_hashes=[close_request.tx_hash or ""]
                )
        
        return result
    except Exception as e:
        logger.error(f"Error closing DEX position: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


