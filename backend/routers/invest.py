"""
Invest Router - Dump Opportunities Marketplace & Position Management
Endpoints for browsing dump opportunities, recording trades, managing positions,
setting SL/TP triggers, and generating P&L reports.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from chain_registry import get_all_chain_ids

from core.deps import (
    get_current_user, db, market_provider,
    portfolio_engine, dump_detection_engine, limiter
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/invest", tags=["invest"])


class RecordBuyRequest(BaseModel):
    symbol: str
    entry_price: float
    quantity: float
    tx_hash: str
    chain_id: int
    fee_amount: float = 0.0
    strategy: str = "dump_buy"
    trigger_reason: str = "Manual dump opportunity buy"


class RecordSellRequest(BaseModel):
    position_id: str
    exit_price: float
    exit_quantity: float
    tx_hash: str
    reason: str = "manual_sell"


class SetTriggersRequest(BaseModel):
    stop_loss_percent: Optional[float] = Field(default=10.0, ge=1.0, le=50.0)
    take_profit_percent: Optional[float] = Field(default=15.0, ge=1.0, le=200.0)
    enable_stop_loss: bool = True
    enable_take_profit: bool = True


@router.get("/opportunities")
@limiter.limit("30/minute")
async def get_dump_opportunities(
    request: Request,
    chain_id: Optional[int] = Query(default=None, description="Filter by chain ID"),
    user: dict = Depends(get_current_user)
):
    try:
        now = datetime.utcnow()

        query = {"expires_at": {"$gt": now}}
        if chain_id:
            query["supported_chains"] = chain_id

        opportunities = await db.dump_opportunities.find(
            query, {"_id": 0}
        ).sort("dump_percentage", 1).to_list(50)

        coins = await market_provider.get_coins_list(100)
        price_map = {c["symbol"]: c for c in coins}

        stored_symbols = {opp.get("symbol") for opp in opportunities}

        if len(opportunities) < 5 and dump_detection_engine:
            try:
                live_opps = await dump_detection_engine.get_dump_opportunities()
                for lo in live_opps:
                    symbol = lo.get("symbol", "")
                    if symbol in stored_symbols:
                        continue

                    dump_mag = lo.get("dump_magnitude", 0)
                    dump_window = lo.get("dump_window", "24h")
                    change_key = "change_1h" if dump_window == "1h" else "change_24h"
                    change_val = lo.get(change_key, 0)
                    dump_pct = change_val if change_val else -dump_mag

                    if abs(dump_pct) >= 10:
                        risk_score, risk_level = 0.8, "High"
                    elif abs(dump_pct) >= 5:
                        risk_score, risk_level = 0.5, "Moderate"
                    else:
                        risk_score, risk_level = 0.3, "Low"

                    expires_at_live = now + timedelta(hours=1)
                    opp_dict = {
                        "symbol": symbol,
                        "name": lo.get("name", symbol),
                        "current_price": lo.get("price_usdt", 0),
                        "dump_percentage": round(dump_pct, 2),
                        "detected_at": now,
                        "expires_at": expires_at_live,
                        "market_cap": lo.get("market_cap", 0),
                        "volume_24h": lo.get("volume_24h", 0),
                        "logo": lo.get("logo", ""),
                        "risk_score": risk_score,
                        "risk_level": risk_level,
                        "ai_recommendation": lo.get("reason", "Dump opportunity detected by AI engine"),
                        "reason": f"{symbol} dumped {abs(dump_pct):.1f}% in {dump_window}",
                        "supported_chains": get_all_chain_ids(),
                        "change_24h": round(lo.get("change_24h", 0), 2),
                        "source": f"dump_engine_live_{dump_window}"
                    }
                    
                    if lo.get("contract_address"):
                        opp_dict["contract_address"] = lo["contract_address"]
                        opp_dict["platform"] = lo.get("platform", "")
                    opportunities.append(opp_dict)
                    stored_symbols.add(symbol)

                    await db.dump_opportunities.update_one(
                        {"symbol": symbol, "expires_at": {"$gt": now}},
                        {"$setOnInsert": opp_dict},
                        upsert=True
                    )

                if chain_id:
                    opportunities = [o for o in opportunities if chain_id in o.get("supported_chains", [])]

                if live_opps:
                    logger.info(f"Live fallback: added {len([o for o in opportunities if o.get('source', '').startswith('dump_engine_live')])} opportunities from DumpDetectionEngine")
            except Exception as e:
                logger.warning(f"Live dump engine fallback failed: {e}")

        enriched = []
        for opp in opportunities:
            symbol = opp.get("symbol")
            live_coin = price_map.get(symbol)

            if live_coin:
                opp["current_price"] = live_coin.get("price", opp.get("current_price", 0))
                opp["market_cap"] = live_coin.get("marketCap", opp.get("market_cap", 0))
                opp["volume_24h"] = live_coin.get("volume24h", opp.get("volume_24h", 0))
                opp["logo"] = live_coin.get("logo", opp.get("logo", ""))
                if not opp.get("contract_address") and live_coin.get("contract_address"):
                    opp["contract_address"] = live_coin["contract_address"]
                    opp["platform"] = live_coin.get("platform", "")

            expires_at = opp.get("expires_at")
            if isinstance(expires_at, datetime):
                ea = expires_at.replace(tzinfo=None) if expires_at.tzinfo else expires_at
                remaining = (ea - now).total_seconds()
                opp["remaining_seconds"] = max(0, int(remaining))
                opp["expires_at"] = expires_at.isoformat() + "Z"
            elif isinstance(expires_at, str):
                try:
                    clean_ts = expires_at.replace("Z", "").replace("+00:00", "")
                    exp_dt = datetime.fromisoformat(clean_ts)
                    remaining = (exp_dt - now).total_seconds()
                    opp["remaining_seconds"] = max(0, int(remaining))
                    if not expires_at.endswith("Z") and "+00:00" not in expires_at:
                        opp["expires_at"] = expires_at + "Z"
                except (ValueError, TypeError):
                    opp["remaining_seconds"] = 0
            else:
                opp["remaining_seconds"] = 0

            detected_at = opp.get("detected_at")
            if isinstance(detected_at, datetime):
                opp["detected_at"] = detected_at.isoformat() + "Z"

            enriched.append(opp)

        return {
            "opportunities": enriched,
            "count": len(enriched),
            "fetched_at": now.isoformat() + "Z"
        }

    except Exception as e:
        logger.error(f"Error fetching opportunities: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch opportunities")


@router.get("/positions")
@limiter.limit("30/minute")
async def get_positions(
    request: Request,
    status: str = Query(default="active", description="Position status: active, closed, all"),
    user: dict = Depends(get_current_user)
):
    try:
        user_id = user.get("id") or user.get("wallet_address")
        portfolio = await portfolio_engine.get_user_portfolio(user_id)

        if status == "active":
            positions = portfolio.get("active_positions", [])
        elif status == "closed":
            positions = portfolio.get("closed_positions", [])
        else:
            positions = portfolio.get("active_positions", []) + portfolio.get("closed_positions", [])

        triggers = await db.position_triggers.find(
            {"user_id": user_id, "status": "active"}, {"_id": 0}
        ).to_list(1000)
        trigger_map = {t["position_id"]: t for t in triggers}

        for pos in positions:
            pid = pos.get("id")
            trigger = trigger_map.get(pid)
            if trigger:
                pos["has_stop_loss"] = trigger.get("stop_loss_price") is not None
                pos["has_take_profit"] = trigger.get("take_profit_price") is not None
                pos["stop_loss_price"] = trigger.get("stop_loss_price")
                pos["take_profit_price"] = trigger.get("take_profit_price")
                pos["stop_loss_percent"] = trigger.get("stop_loss_percent")
                pos["take_profit_percent"] = trigger.get("take_profit_percent")
            else:
                pos["has_stop_loss"] = False
                pos["has_take_profit"] = False
                pos["stop_loss_price"] = None
                pos["take_profit_price"] = None

        return {
            "positions": positions,
            "count": len(positions)
        }

    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch positions")


@router.get("/summary")
@limiter.limit("30/minute")
async def get_investment_summary(request: Request, user: dict = Depends(get_current_user)):
    try:
        user_id = user.get("id") or user.get("wallet_address")
        portfolio = await portfolio_engine.get_user_portfolio(user_id)

        summary = portfolio.get("summary", {})
        active = portfolio.get("active_positions", [])

        best_performer = None
        worst_performer = None

        if active:
            sorted_by_pnl = sorted(active, key=lambda p: p.get("pnl_percent", 0))
            worst_performer = {
                "symbol": sorted_by_pnl[0].get("symbol"),
                "pnl_percent": sorted_by_pnl[0].get("pnl_percent", 0)
            }
            best_performer = {
                "symbol": sorted_by_pnl[-1].get("symbol"),
                "pnl_percent": sorted_by_pnl[-1].get("pnl_percent", 0)
            }

        return {
            "total_invested": summary.get("total_invested_usdt", 0),
            "total_current_value": summary.get("total_current_value_usdt", 0),
            "total_pnl": summary.get("total_unrealized_pnl_usdt", 0),
            "total_pnl_percentage": summary.get("total_unrealized_pnl_percent", 0),
            "total_realized_pnl": summary.get("total_realized_pnl_usdt", 0),
            "active_positions_count": summary.get("active_position_count", 0),
            "closed_positions_count": summary.get("closed_position_count", 0),
            "best_performer": best_performer,
            "worst_performer": worst_performer
        }

    except Exception as e:
        logger.error(f"Error fetching summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch summary")


@router.post("/record-buy")
@limiter.limit("10/minute")
async def record_buy(request: Request, req: RecordBuyRequest, user: dict = Depends(get_current_user)):
    try:
        user_id = user.get("id") or user.get("wallet_address")

        result = await portfolio_engine.record_dex_swap(
            user_id=user_id,
            symbol=req.symbol,
            usdt_amount=req.entry_price * req.quantity,
            quantity=req.quantity,
            entry_price=req.entry_price,
            tx_hash=req.tx_hash,
            chain_id=req.chain_id,
            strategy=req.strategy,
            trigger_reason=req.trigger_reason
        )

        if result.get("position"):
            result["position"].pop("_id", None)

        if result.get("success") and req.fee_amount > 0:
            position = result.get("position", {})
            await db.ai_positions.update_one(
                {"id": position.get("id")},
                {"$set": {"fee_amount": req.fee_amount}}
            )

        return result

    except Exception as e:
        logger.error(f"Error recording buy: {e}")
        raise HTTPException(status_code=500, detail="Failed to record buy")


@router.post("/record-sell")
@limiter.limit("10/minute")
async def record_sell(request: Request, req: RecordSellRequest, user: dict = Depends(get_current_user)):
    try:
        user_id = user.get("id") or user.get("wallet_address")

        result = await portfolio_engine.close_position_with_dex(
            user_id=user_id,
            position_id=req.position_id,
            exit_price=req.exit_price,
            exit_quantity=req.exit_quantity,
            tx_hash=req.tx_hash,
            reason=req.reason
        )

        return result

    except Exception as e:
        logger.error(f"Error recording sell: {e}")
        raise HTTPException(status_code=500, detail="Failed to record sell")


@router.post("/positions/{position_id}/triggers")
@limiter.limit("10/minute")
async def set_position_triggers(
    request: Request,
    position_id: str,
    req: SetTriggersRequest,
    user: dict = Depends(get_current_user)
):
    try:
        user_id = user.get("id") or user.get("wallet_address")

        position = await db.ai_positions.find_one(
            {"id": position_id, "user_id": user_id, "status": "active"},
            {"_id": 0}
        )

        if not position:
            raise HTTPException(status_code=404, detail="Active position not found")

        entry_price = position.get("entry_price", 0)
        if entry_price <= 0:
            raise HTTPException(status_code=400, detail="Invalid entry price on position")

        stop_loss_price = entry_price * (1 - req.stop_loss_percent / 100) if req.enable_stop_loss else None
        take_profit_price = entry_price * (1 + req.take_profit_percent / 100) if req.enable_take_profit else None

        await db.position_triggers.delete_many(
            {"position_id": position_id, "user_id": user_id, "status": "active"}
        )

        import uuid
        trigger = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "position_id": position_id,
            "entry_price": entry_price,
            "stop_loss_price": stop_loss_price,
            "take_profit_price": take_profit_price,
            "stop_loss_percent": req.stop_loss_percent if req.enable_stop_loss else None,
            "take_profit_percent": req.take_profit_percent if req.enable_take_profit else None,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        await db.position_triggers.insert_one(trigger)

        logger.info(f"Set triggers for position {position_id[:8]}: SL={stop_loss_price}, TP={take_profit_price}")

        return {
            "success": True,
            "trigger": {
                "stop_loss_price": stop_loss_price,
                "take_profit_price": take_profit_price,
                "stop_loss_percent": req.stop_loss_percent if req.enable_stop_loss else None,
                "take_profit_percent": req.take_profit_percent if req.enable_take_profit else None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting triggers: {e}")
        raise HTTPException(status_code=500, detail="Failed to set triggers")


@router.delete("/positions/{position_id}/triggers")
@limiter.limit("10/minute")
async def cancel_position_triggers(
    request: Request,
    position_id: str,
    user: dict = Depends(get_current_user)
):
    try:
        user_id = user.get("id") or user.get("wallet_address")

        result = await db.position_triggers.update_many(
            {"position_id": position_id, "user_id": user_id, "status": "active"},
            {"$set": {"status": "cancelled", "cancelled_at": datetime.now(timezone.utc).isoformat()}}
        )

        return {
            "success": True,
            "cancelled_count": result.modified_count
        }

    except Exception as e:
        logger.error(f"Error cancelling triggers: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel triggers")


@router.get("/reports/summary")
@limiter.limit("5/minute")
async def get_report_summary(
    request: Request,
    period: str = Query(default="all", description="Period: weekly, monthly, all"),
    user: dict = Depends(get_current_user)
):
    try:
        user_id = user.get("id") or user.get("wallet_address")

        now = datetime.now(timezone.utc)
        if period == "weekly":
            start_date = now - timedelta(days=7)
        elif period == "monthly":
            start_date = now - timedelta(days=30)
        else:
            start_date = datetime(2020, 1, 1, tzinfo=timezone.utc)

        query = {"user_id": user_id}
        positions = await db.ai_positions.find(query, {"_id": 0}).to_list(10000)

        filtered = []
        for p in positions:
            created = p.get("created_at", "")
            if isinstance(created, str):
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if dt >= start_date:
                        filtered.append(p)
                except (ValueError, TypeError):
                    filtered.append(p)
            else:
                filtered.append(p)

        closed = [p for p in filtered if p.get("status") == "closed"]
        active = [p for p in filtered if p.get("status") == "active"]

        total_trades = len(filtered)
        winning = [p for p in closed if p.get("realized_pnl", 0) > 0]
        losing = [p for p in closed if p.get("realized_pnl", 0) <= 0]

        total_realized_pnl = sum(p.get("realized_pnl", 0) for p in closed)
        best_trade = max(closed, key=lambda p: p.get("realized_pnl", 0), default=None)
        worst_trade = min(closed, key=lambda p: p.get("realized_pnl", 0), default=None)

        hold_times = []
        for p in closed:
            created = p.get("created_at", "")
            closed_at = p.get("closed_at", "")
            if isinstance(created, str) and isinstance(closed_at, str):
                try:
                    c_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    cl_dt = datetime.fromisoformat(closed_at.replace("Z", "+00:00"))
                    hold_times.append((cl_dt - c_dt).total_seconds() / 3600)
                except (ValueError, TypeError):
                    pass

        avg_hold_hours = sum(hold_times) / len(hold_times) if hold_times else 0

        position_details = []
        for p in filtered:
            position_details.append({
                "symbol": p.get("symbol"),
                "name": p.get("name"),
                "entry_date": p.get("created_at"),
                "entry_price": p.get("entry_price"),
                "exit_date": p.get("closed_at"),
                "exit_price": p.get("exit_price"),
                "quantity": p.get("quantity"),
                "invested_usdt": p.get("invested_usdt"),
                "realized_pnl": p.get("realized_pnl"),
                "status": p.get("status"),
                "chain_id": p.get("chain_id"),
                "tx_hash": p.get("tx_hash"),
                "fee_amount": p.get("fee_amount", 0)
            })

        return {
            "period": period,
            "period_start": start_date.isoformat(),
            "period_end": now.isoformat(),
            "total_trades": total_trades,
            "active_trades": len(active),
            "closed_trades": len(closed),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": round(len(winning) / len(closed) * 100, 1) if closed else 0,
            "total_realized_pnl": round(total_realized_pnl, 2),
            "best_trade": {
                "symbol": best_trade.get("symbol"),
                "pnl": best_trade.get("realized_pnl", 0)
            } if best_trade else None,
            "worst_trade": {
                "symbol": worst_trade.get("symbol"),
                "pnl": worst_trade.get("realized_pnl", 0)
            } if worst_trade else None,
            "avg_hold_hours": round(avg_hold_hours, 1),
            "positions": position_details
        }

    except Exception as e:
        logger.error(f"Error generating report summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")


@router.get("/reports/export")
@limiter.limit("5/minute")
async def export_report(
    request: Request,
    format: str = Query(description="Export format: csv or pdf"),
    period: str = Query(default="all", description="Period: weekly, monthly, all"),
    user: dict = Depends(get_current_user)
):
    try:
        summary_resp = await get_report_summary(request=request, period=period, user=user)
        positions = summary_resp.get("positions", [])

        if format == "csv":
            from report_generator import generate_csv_report
            output = generate_csv_report(positions, summary_resp)
            return StreamingResponse(
                output,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=moonhunters_report_{period}.csv"}
            )

        elif format == "pdf":
            from report_generator import generate_pdf_report
            output = generate_pdf_report(positions, summary_resp)
            return StreamingResponse(
                output,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=moonhunters_report_{period}.pdf"}
            )

        else:
            raise HTTPException(status_code=400, detail="Invalid format. Use 'csv' or 'pdf'")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting report: {e}")
        raise HTTPException(status_code=500, detail="Failed to export report")
