from fastapi import APIRouter, Request, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
import logging
import time

from core.deps import db, get_current_user, limiter, dex_service
from core.redis_client import cache_get, cache_set
from chain_registry import get_chains_for_api, CHAIN_REGISTRY

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


class SwapQuoteRequest(BaseModel):
    src_token: str = Field(..., description="Source token address or symbol")
    dst_token: str = Field(..., description="Destination token address or symbol")
    amount: str = Field(..., description="Amount in wei (smallest unit)")
    chain_id: int = Field(1, description="Chain ID (1=Ethereum, 137=Polygon, etc)")


class SwapRequest(BaseModel):
    src_token: str = Field(..., description="Source token address")
    dst_token: str = Field(..., description="Destination token address")
    amount: str = Field(..., description="Amount in wei")
    slippage: float = Field(1.0, ge=0.1, le=50, description="Max slippage percentage")
    chain_id: int = Field(1, description="Chain ID")
    disable_estimate: bool = Field(True, description="Skip gas estimation (set to True to avoid balance check failures)")


class ApproveRequest(BaseModel):
    token_address: str = Field(..., description="Token to approve")
    amount: Optional[str] = Field(None, description="Amount to approve (None=unlimited)")
    chain_id: int = Field(1, description="Chain ID")


class SCSwapDataRequest(BaseModel):
    chain_id: int = Field(..., description="Chain ID")
    src_token: str = Field(..., description="Source token address")
    dst_token: str = Field(..., description="Destination token address")
    amount: str = Field(..., description="Amount in wei")
    sc_address: str = Field(..., description="Smart contract address")


class RecordTransactionRequest(BaseModel):
    tx_hash: str = Field(..., description="Transaction hash")
    from_token: str = Field(..., description="Source token symbol")
    to_token: str = Field(..., description="Destination token symbol")
    from_amount: float = Field(..., description="Amount of source token")
    to_amount: float = Field(..., description="Amount of destination token")
    chain_id: int = Field(..., description="Chain ID")
    action: str = Field("swap", description="Transaction type: buy, sell, or swap")


# ---- Token cache moved to Redis (key: dex:tokens:{chain_id}, TTL: 300s) ----


@router.get("/dex/chains")
@limiter.limit("30/minute")
async def get_supported_chains(
    request: Request,
    include_testnet: bool = Query(False, description="Include testnet chains"),
    current_user: dict = Depends(get_current_user)
):
    """Get all supported blockchain networks with metadata"""
    try:
        chains = get_chains_for_api(include_testnet)
        return {"success": True, "chains": chains}
    except Exception as e:
        logger.error(f"Error getting chains: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/dex/spender")
@limiter.limit("30/minute")
async def get_dex_spender(
    request: Request,
    chain_id: int = Query(..., description="Chain ID"),
    current_user: dict = Depends(get_current_user)
):
    """Get the 1inch router address that needs token approval"""
    try:
        result = await dex_service.get_spender_address(chain_id)
        return result
    except Exception as e:
        logger.error(f"Error getting spender address: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/dex/quote")
@limiter.limit("60/minute")
async def get_swap_quote(
    request: Request,
    quote_request: SwapQuoteRequest,
    current_user: dict = Depends(get_current_user)
):
    """Get a swap quote without generating transaction data"""
    try:
        src = quote_request.src_token
        dst = quote_request.dst_token
        
        if not src.startswith("0x"):
            src = dex_service.get_token_address(src, quote_request.chain_id) or src
        if not dst.startswith("0x"):
            dst = dex_service.get_token_address(dst, quote_request.chain_id) or dst
        
        if not src or not dst:
            raise HTTPException(status_code=400, detail="Invalid token addresses")
        
        logger.info(f"[DEX] Quote request: {src[:10]}... -> {dst[:10]}..., amount={quote_request.amount}, chain={quote_request.chain_id}")
        
        result = await dex_service.get_quote(
            src_token=src,
            dst_token=dst,
            amount=quote_request.amount,
            chain_id=quote_request.chain_id
        )
        
        if not result.get("success"):
            logger.warning(f"[DEX] Quote failed: {result.get('error')}")
            raise HTTPException(status_code=502, detail=result.get("error", "Quote failed"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DEX] Quote exception: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Quote service error")


@router.post("/dex/swap")
@limiter.limit("30/minute")
async def get_swap_transaction(
    request: Request,
    swap_request: SwapRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate swap transaction data for wallet signing"""
    try:
        wallet_address = current_user.get("wallet_address")
        if not wallet_address:
            raise HTTPException(status_code=400, detail="Wallet address not found. Please reconnect your wallet.")
        
        src = swap_request.src_token
        dst = swap_request.dst_token
        
        if not src.startswith("0x"):
            src = dex_service.get_token_address(src, swap_request.chain_id) or src
        if not dst.startswith("0x"):
            dst = dex_service.get_token_address(dst, swap_request.chain_id) or dst
        
        if not src or not dst:
            raise HTTPException(status_code=400, detail="Invalid token addresses")
        
        logger.info(f"[DEX] Swap request: {src[:10]}... -> {dst[:10]}..., from={wallet_address[:10]}..., amount={swap_request.amount}, slippage={swap_request.slippage}%, chain={swap_request.chain_id}")
        
        result = await dex_service.get_swap_data(
            src_token=src,
            dst_token=dst,
            amount=swap_request.amount,
            from_address=wallet_address,
            slippage=swap_request.slippage,
            chain_id=swap_request.chain_id,
            disable_estimate=swap_request.disable_estimate
        )
        
        if result.get("success"):
            logger.info(f"[DEX] Swap tx generated successfully for {wallet_address[:10]}...")
        else:
            logger.warning(f"[DEX] Swap failed: {result.get('error')} (code: {result.get('code')})")
            raise HTTPException(status_code=502, detail=result.get("error", "Swap failed"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DEX] Swap exception: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Swap service error")


@router.get("/dex/allowance")
@limiter.limit("60/minute")
async def check_token_allowance(
    request: Request,
    token_address: str = Query(..., description="Token address to check"),
    chain_id: int = Query(..., description="Chain ID"),
    current_user: dict = Depends(get_current_user)
):
    """Check token allowance for 1inch router"""
    try:
        wallet_address = current_user.get("wallet_address")
        if not wallet_address:
            raise HTTPException(status_code=400, detail="Wallet address required")
        
        result = await dex_service.get_allowance(
            token_address=token_address,
            wallet_address=wallet_address,
            chain_id=chain_id
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking allowance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/dex/approve")
@limiter.limit("30/minute")
async def get_approve_transaction(
    request: Request,
    approve_request: ApproveRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate approval transaction data for wallet signing"""
    try:
        result = await dex_service.get_approve_calldata(
            token_address=approve_request.token_address,
            amount=approve_request.amount,
            chain_id=approve_request.chain_id
        )
        return result
    except Exception as e:
        logger.error(f"Error generating approve transaction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/dex/tokens")
@limiter.limit("30/minute")
async def get_supported_tokens(
    request: Request,
    chain_id: int = Query(..., description="Chain ID"),
    current_user: dict = Depends(get_current_user)
):
    """Get list of supported tokens for swapping (cached, sorted)"""
    try:
        # Check Redis cache
        redis_key = f"dex:tokens:{chain_id}"
        cached = await cache_get(redis_key)
        if cached:
            return {"success": True, "tokens": cached}

        result = await dex_service.get_supported_tokens(chain_id)
        raw_tokens = result.get("tokens", {})

        # Get popular symbols for this chain from dex_service fallback
        from dex_service import COMMON_TOKENS
        popular_symbols = set()
        chain_popular = COMMON_TOKENS.get(chain_id, {})
        for sym, addr in chain_popular.items():
            popular_symbols.add(addr.lower())

        # Transform to a clean list
        STABLECOIN_SYMBOLS = {"USDT", "USDC", "DAI", "BUSD", "FRAX", "TUSD", "LUSD", "GUSD", "USDP", "USDD"}
        token_list = []
        for addr, info in raw_tokens.items():
            sym = info.get("symbol", "")
            token_list.append({
                "address": addr,
                "symbol": sym,
                "name": info.get("name", ""),
                "decimals": info.get("decimals", 18),
                "logoURI": info.get("logoURI", ""),
                "popular": addr.lower() in popular_symbols,
                "is_stablecoin": sym.upper() in STABLECOIN_SYMBOLS,
            })

        # Sort: popular first, then stablecoins, then alphabetical
        token_list.sort(key=lambda t: (
            not t["popular"],
            not t["is_stablecoin"],
            t["symbol"].lower(),
        ))

        # Cache the result in Redis
        await cache_set(redis_key, token_list, 300)

        return {"success": True, "tokens": token_list}
    except Exception as e:
        logger.error(f"Error getting supported tokens: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/dex/liquidity-sources")
@limiter.limit("30/minute")
async def get_liquidity_sources(
    request: Request,
    chain_id: int = Query(..., description="Chain ID"),
    current_user: dict = Depends(get_current_user)
):
    """Get available DEX protocols for routing"""
    try:
        result = await dex_service.get_liquidity_sources(chain_id)
        return result
    except Exception as e:
        logger.error(f"Error getting liquidity sources: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/dex/record-transaction")
@limiter.limit("30/minute")
async def record_dex_transaction(
    request: Request,
    body: RecordTransactionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Record a completed DEX swap transaction for transaction history."""
    try:
        from datetime import datetime, timezone

        wallet_address = current_user.get("wallet_address", "").lower()
        if not wallet_address:
            raise HTTPException(status_code=400, detail="No wallet address found")

        # Determine action type
        STABLECOINS = {"USDT", "USDC", "DAI", "BUSD", "FRAX", "TUSD"}
        from_stable = body.from_token.upper() in STABLECOINS
        to_stable = body.to_token.upper() in STABLECOINS

        if from_stable and not to_stable:
            action = "buy"
        elif not from_stable and to_stable:
            action = "sell"
        else:
            action = "swap"

        # Use the destination token as the primary symbol for buy/swap, source for sell
        token_symbol = body.to_token if action != "sell" else body.from_token
        amount_usdt = body.from_amount if from_stable else (body.to_amount if to_stable else body.from_amount)

        tx_record = {
            "wallet_address": wallet_address,
            "user_id": current_user["id"],
            "hash": body.tx_hash,
            "action": action,
            "token_symbol": token_symbol,
            "from_token": body.from_token,
            "to_token": body.to_token,
            "from_amount": body.from_amount,
            "to_amount": body.to_amount,
            "amount_usdt": amount_usdt,
            "chain_id": body.chain_id,
            "status": "confirmed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        await db.dex_transactions.insert_one(tx_record)
        logger.info(f"Recorded DEX tx: {action} {body.from_token}→{body.to_token} (tx: {body.tx_hash[:10]}...)")

        return {"success": True, "message": "Transaction recorded"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording DEX transaction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/dex/transactions")
@limiter.limit("30/minute")
async def get_dex_transactions(
    request: Request,
    wallet: str = Query(..., description="Wallet address"),
    limit: int = Query(20, description="Number of transactions to return"),
    current_user: dict = Depends(get_current_user)
):
    """Get recent DEX transactions for a wallet"""
    try:
        wallet_lower = wallet.lower()
        user_wallet = current_user.get("wallet_address", "").lower()
        
        if wallet_lower != user_wallet:
            raise HTTPException(status_code=403, detail="Cannot view other wallets")
        
        transactions = await db.dex_transactions.find(
            {"wallet_address": wallet_lower},
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit).to_list(limit)
        
        return {"transactions": transactions, "count": len(transactions)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching DEX transactions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/dex/swap-data-for-sc")
@limiter.limit("20/minute")
async def get_swap_data_for_sc(
    request: Request,
    body: SCSwapDataRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        result = await dex_service.generate_swap_data_for_sc(
            chain_id=body.chain_id,
            src_token=body.src_token,
            dst_token=body.dst_token,
            amount=body.amount,
            sc_address=body.sc_address,
        )
        return result
    except Exception as e:
        logger.error(f"Error generating SC swap data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
