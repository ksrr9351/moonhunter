from fastapi import APIRouter, Request, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import logging
import uuid
from datetime import datetime, timezone
import httpx

from chain_registry import CHAIN_REGISTRY

from core.deps import (
    db, get_current_user, limiter, portfolio_engine,
    trading_bot, market_provider, dex_service, wallet_service
)
from core.schemas import (
    CreatePositionRequest, ClosePositionRequest,
    RecordDexSwapRequest, CloseDexPositionRequest,
    BotSettingsUpdate, SetPositionTriggerRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ==================== TRADING BOT ENDPOINTS ====================

@router.get("/trading-bot/status")
@limiter.limit("30/minute")
async def get_trading_bot_status(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get trading bot status and settings for current user"""
    try:
        status = await trading_bot.get_bot_status(current_user["id"])
        return status
    except Exception as e:
        logger.error(f"Error getting bot status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/trading-bot/settings")
@limiter.limit("30/minute")
async def get_trading_bot_settings(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get trading bot settings"""
    try:
        settings = await trading_bot.get_user_bot_settings(current_user["id"])
        return settings
    except Exception as e:
        logger.error(f"Error getting bot settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/trading-bot/settings")
@limiter.limit("10/minute")
async def update_trading_bot_settings(
    request: Request,
    settings_update: BotSettingsUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update trading bot settings"""
    try:
        updates = settings_update.model_dump(exclude_none=True)
        settings = await trading_bot.update_user_bot_settings(current_user["id"], updates)
        return settings
    except Exception as e:
        logger.error(f"Error updating bot settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/trading-bot/enable")
@limiter.limit("10/minute")
async def enable_trading_bot(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Enable the trading bot"""
    try:
        settings = await trading_bot.update_user_bot_settings(
            current_user["id"], 
            {"enabled": True}
        )
        return {"success": True, "enabled": True, "settings": settings}
    except Exception as e:
        logger.error(f"Error enabling bot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/trading-bot/disable")
@limiter.limit("10/minute")
async def disable_trading_bot(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Disable the trading bot"""
    try:
        settings = await trading_bot.update_user_bot_settings(
            current_user["id"], 
            {"enabled": False}
        )
        return {"success": True, "enabled": False, "settings": settings}
    except Exception as e:
        logger.error(f"Error disabling bot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/trading-bot/trigger/{position_id}")
@limiter.limit("20/minute")
async def set_position_trigger(
    request: Request,
    position_id: str,
    trigger_request: SetPositionTriggerRequest,
    current_user: dict = Depends(get_current_user)
):
    """Set stop-loss and take-profit triggers for a position"""
    try:
        position = await db.ai_positions.find_one(
            {"id": position_id, "user_id": current_user["id"], "status": "active"},
            {"_id": 0}
        )
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        existing_trigger = await db.position_triggers.find_one(
            {"position_id": position_id, "status": "active"}
        )
        
        if existing_trigger:
            await db.position_triggers.update_one(
                {"id": existing_trigger["id"]},
                {"$set": {"status": "cancelled"}}
            )
        
        import uuid
        stop_loss_price = None
        take_profit_price = None
        entry_price = position.get("entry_price", 0)
        
        if trigger_request.stop_loss_percent:
            stop_loss_price = entry_price * (1 - trigger_request.stop_loss_percent / 100)
        
        if trigger_request.take_profit_percent:
            take_profit_price = entry_price * (1 + trigger_request.take_profit_percent / 100)
        
        trigger = {
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "position_id": position_id,
            "entry_price": entry_price,
            "stop_loss_price": stop_loss_price,
            "take_profit_price": take_profit_price,
            "stop_loss_percent": trigger_request.stop_loss_percent,
            "take_profit_percent": trigger_request.take_profit_percent,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.position_triggers.insert_one(trigger)
        
        return {
            "success": True,
            "trigger": trigger,
            "message": f"Triggers set: SL=${stop_loss_price:.4f if stop_loss_price else 'N/A'}, TP=${take_profit_price:.4f if take_profit_price else 'N/A'}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting trigger: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/trading-bot/triggers")
@limiter.limit("30/minute")
async def get_position_triggers(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get all active position triggers for current user"""
    try:
        triggers = await db.position_triggers.find(
            {"user_id": current_user["id"], "status": "active"},
            {"_id": 0}
        ).to_list(100)
        
        return {"triggers": triggers, "count": len(triggers)}
    except Exception as e:
        logger.error(f"Error getting triggers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/trading-bot/trigger/{trigger_id}")
@limiter.limit("20/minute")
async def cancel_position_trigger(
    request: Request,
    trigger_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Cancel a position trigger"""
    try:
        result = await db.position_triggers.update_one(
            {"id": trigger_id, "user_id": current_user["id"], "status": "active"},
            {"$set": {"status": "cancelled", "cancelled_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Trigger not found or already cancelled")
        
        return {"success": True, "message": "Trigger cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling trigger: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/trading-bot/daily-stats")
@limiter.limit("30/minute")
async def get_trading_bot_daily_stats(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get today's trading statistics"""
    try:
        stats = await trading_bot.get_daily_stats(current_user["id"])
        return stats
    except Exception as e:
        logger.error(f"Error getting daily stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/trading-bot/pending-trades")
@limiter.limit("30/minute")
async def get_pending_bot_trades(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get pending bot trades awaiting user confirmation"""
    try:
        current_time = datetime.now(timezone.utc)
        pending = await db.pending_bot_trades.find(
            {
                "user_id": current_user["id"],
                "status": "awaiting_user_confirmation",
                "expires_at": {"$gt": current_time.isoformat()}
            },
            {"_id": 0}
        ).to_list(20)
        return {"pending_trades": pending, "count": len(pending)}
    except Exception as e:
        logger.error(f"Error getting pending trades: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


class ConfirmTradeRequest(BaseModel):
    tx_hash: str = Field(..., min_length=64, max_length=70, description="Transaction hash from wallet signing")


from chain_registry import register_on_refresh

def _build_rpc_urls() -> dict:
    return {
        cid: data["rpc_urls"][0]
        for cid, data in CHAIN_REGISTRY.items()
        if data.get("rpc_urls") and not data.get("is_testnet", False)
    }

CHAIN_RPC_URLS = _build_rpc_urls()

def _rebuild_positions_data():
    global CHAIN_RPC_URLS
    CHAIN_RPC_URLS = _build_rpc_urls()

register_on_refresh(_rebuild_positions_data)


ONEINCH_SWAP_SELECTORS = {
    "0x12aa3caf": "swap",
    "0x0502b1c5": "unoswap",
    "0x2e95b6c8": "unoswapTo",
    "0xe449022e": "uniswapV3Swap",
    "0xbc80f1a8": "uniswapV3SwapTo",
    "0x84bd6d29": "clipperSwap",
    "0x07ed2379": "swap (v5)"
}


async def verify_transaction_onchain(
    tx_hash: str,
    chain_id: int,
    expected_from: str,
    expected_to: str = None,
    expected_calldata: str = None
) -> dict:
    """Verify a transaction exists, succeeded, and matches the expected swap parameters"""
    rpc_url = CHAIN_RPC_URLS.get(chain_id)
    if not rpc_url:
        return {"verified": False, "error": f"Unsupported chain ID: {chain_id}"}
    
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            receipt_response = await client.post(rpc_url, json={
                "jsonrpc": "2.0",
                "method": "eth_getTransactionReceipt",
                "params": [tx_hash],
                "id": 1
            })
            
            if receipt_response.status_code != 200:
                return {"verified": False, "error": "RPC request failed"}
            
            receipt = receipt_response.json().get("result")
            
            if not receipt:
                return {"verified": False, "error": "Transaction not found or still pending"}
            
            tx_status = int(receipt.get("status", "0x0"), 16)
            if tx_status != 1:
                return {"verified": False, "error": "Transaction failed on-chain"}
            
            tx_from = receipt.get("from", "").lower()
            if tx_from != expected_from.lower():
                logger.warning(f"TX verification: from mismatch. Expected {expected_from}, got {tx_from}")
                return {"verified": False, "error": "Transaction from address does not match user wallet"}
            
            tx_to = receipt.get("to", "").lower()
            if expected_to:
                if tx_to != expected_to.lower():
                    logger.warning(f"TX verification: to mismatch. Expected {expected_to}, got {tx_to}")
                    return {"verified": False, "error": "Transaction to address does not match expected router"}
            
            tx_response = await client.post(rpc_url, json={
                "jsonrpc": "2.0",
                "method": "eth_getTransactionByHash",
                "params": [tx_hash],
                "id": 2
            })
            
            tx_input = None
            if tx_response.status_code == 200:
                tx_result = tx_response.json().get("result")
                if tx_result:
                    tx_input = tx_result.get("input", "")
                    
                    if tx_input and len(tx_input) >= 10:
                        selector = tx_input[:10].lower()
                        if selector not in ONEINCH_SWAP_SELECTORS:
                            logger.warning(f"TX verification: unrecognized function selector {selector}")
                            return {"verified": False, "error": "Transaction is not a recognized 1inch swap"}
                        
                        if expected_calldata:
                            expected_normalized = expected_calldata.lower()
                            actual_normalized = tx_input.lower()
                            
                            if expected_normalized != actual_normalized:
                                logger.warning(f"TX verification: calldata mismatch (lengths: expected={len(expected_calldata)}, actual={len(tx_input)})")
                                return {"verified": False, "error": "Transaction calldata does not match expected swap - possible replay attack"}
            
            block_hex = receipt.get("blockNumber", "0x0")
            current_block_response = await client.post(rpc_url, json={
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": 3
            })
            
            tx_age_blocks = 0
            if current_block_response.status_code == 200:
                current_block_result = current_block_response.json().get("result")
                if current_block_result:
                    tx_block = int(block_hex, 16)
                    current_block = int(current_block_result, 16)
                    tx_age_blocks = current_block - tx_block
                    
                    if tx_age_blocks > 1000:
                        logger.warning(f"TX verification: transaction too old ({tx_age_blocks} blocks)")
                        return {"verified": False, "error": "Transaction is too old (>1000 blocks)"}
            
            return {
                "verified": True,
                "block_number": int(block_hex, 16),
                "gas_used": int(receipt.get("gasUsed", "0x0"), 16),
                "from": tx_from,
                "to": tx_to,
                "tx_age_blocks": tx_age_blocks,
                "function_selector": tx_input[:10] if tx_input and len(tx_input) >= 10 else None,
                "calldata_verified": bool(expected_calldata)
            }
    except Exception as e:
        logger.error(f"On-chain verification error: {e}", exc_info=True)
        return {"verified": False, "error": str(e)}


@router.post("/trading-bot/confirm-trade/{trade_id}")
@limiter.limit("10/minute")
async def confirm_pending_trade(
    request: Request,
    trade_id: str,
    body: ConfirmTradeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Confirm a pending bot trade after user signs the transaction. Verifies tx_hash on-chain before activation."""
    try:
        tx_hash = body.tx_hash
        
        if not tx_hash or len(tx_hash) < 64:
            raise HTTPException(status_code=400, detail="Valid transaction hash required to confirm trade")
        
        if not tx_hash.startswith("0x"):
            tx_hash = "0x" + tx_hash
        
        trade = await db.pending_bot_trades.find_one({
            "id": trade_id,
            "user_id": current_user["id"],
            "status": "awaiting_user_confirmation"
        })
        
        if not trade:
            raise HTTPException(status_code=404, detail="Pending trade not found")
        
        current_time = datetime.now(timezone.utc)
        if datetime.fromisoformat(trade["expires_at"].replace("Z", "+00:00")) < current_time:
            await db.pending_bot_trades.update_one(
                {"id": trade_id},
                {"$set": {"status": "expired"}}
            )
            raise HTTPException(status_code=400, detail="Trade has expired")
        
        chain_id = trade.get("chain_id", 1)
        wallet_address = trade.get("wallet_address", "")
        tx_data = trade.get("tx_data", {})
        expected_router = tx_data.get("to", "")
        expected_calldata = tx_data.get("data", "")
        
        verification = await verify_transaction_onchain(
            tx_hash, chain_id, wallet_address, expected_router, expected_calldata
        )
        
        if not verification.get("verified"):
            logger.warning(f"Trade confirmation rejected: {verification.get('error')} for tx {tx_hash}")
            await db.pending_bot_trades.update_one(
                {"id": trade_id},
                {"$set": {
                    "last_verification_attempt": current_time.isoformat(),
                    "verification_error": verification.get("error")
                }}
            )
            raise HTTPException(status_code=400, detail=f"Transaction verification failed: {verification.get('error')}")
        
        await db.pending_bot_trades.update_one(
            {"id": trade_id},
            {"$set": {
                "status": "confirmed",
                "confirmed_at": current_time.isoformat(),
                "tx_hash": tx_hash,
                "verification": verification
            }}
        )
        
        await db.ai_positions.update_one(
            {"id": trade_id},
            {"$set": {
                "status": "active",
                "tx_hash": tx_hash,
                "confirmed_at": current_time.isoformat(),
                "block_number": verification.get("block_number")
            }}
        )
        
        logger.info(f"Trade {trade_id} confirmed with verified tx {tx_hash} at block {verification.get('block_number')}")
        
        return {
            "success": True,
            "message": "Trade verified and confirmed on-chain",
            "trade_id": trade_id,
            "tx_hash": tx_hash,
            "block_number": verification.get("block_number")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming trade: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/trading-bot/reject-trade/{trade_id}")
@limiter.limit("20/minute")
async def reject_pending_trade(
    request: Request,
    trade_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Reject a pending bot trade"""
    try:
        result = await db.pending_bot_trades.update_one(
            {
                "id": trade_id,
                "user_id": current_user["id"],
                "status": "awaiting_user_confirmation"
            },
            {"$set": {
                "status": "rejected",
                "rejected_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Pending trade not found")
        
        await db.ai_positions.update_one(
            {"id": trade_id},
            {"$set": {"status": "cancelled"}}
        )
        
        return {"success": True, "message": "Trade rejected", "trade_id": trade_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting trade: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
