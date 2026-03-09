"""
DEX Service - 1inch API Integration for Real Token Swaps
Provides swap quotes, transaction generation, and token approval handling
"""
import os
import logging
import asyncio
from typing import Dict, Any, Optional, List
import httpx
from decimal import Decimal

from chain_registry import (
    CHAIN_REGISTRY, get_chain, get_chain_name, is_supported,
    NATIVE_TOKEN_ADDRESS, register_on_refresh,
)

logger = logging.getLogger(__name__)

ONEINCH_API_BASE = "https://api.1inch.dev/swap/v6.0"
ONEINCH_TOKENS_API = "https://api.1inch.dev/token/v1.2"

# No hardcoded token addresses — all discovered from APIs


def _build_chain_ids() -> dict:
    return {v["name"].lower(): k for k, v in CHAIN_REGISTRY.items()}


def _build_common_tokens() -> dict:
    """Derive per-chain common token lists from CHAIN_REGISTRY (fully dynamic)."""
    tokens = {}
    for cid, data in CHAIN_REGISTRY.items():
        if data.get("is_testnet", False):
            continue
        ct = {}
        # Native token always included
        if data.get("symbol"):
            ct[data["symbol"]] = NATIVE_TOKEN_ADDRESS
        if data.get("usdt_address"):
            ct["USDT"] = data["usdt_address"]
        if data.get("usdc_address"):
            ct["USDC"] = data["usdc_address"]
        if ct:
            tokens[cid] = ct
    return tokens


# Module-level dicts — rebuilt when CHAIN_REGISTRY refreshes
CHAIN_IDS = _build_chain_ids()
COMMON_TOKENS = _build_common_tokens()


def _rebuild_dex_data():
    """Rebuild all module-level dicts from the refreshed CHAIN_REGISTRY."""
    global CHAIN_IDS, COMMON_TOKENS
    CHAIN_IDS = _build_chain_ids()
    COMMON_TOKENS = _build_common_tokens()
    logger.info(f"DEX data rebuilt: {len(CHAIN_IDS)} chain names, {len(COMMON_TOKENS)} token sets")

register_on_refresh(_rebuild_dex_data)


class DexService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ONEINCH_API_KEY")
        if not self.api_key:
            logger.warning("1inch API key not configured - DEX features will be limited")
        logger.info("DEX Service initialized (1inch API v6.0)")
    
    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def _request_with_retry(self, method: str, url: str, max_retries: int = 3, **kwargs) -> httpx.Response:
        kwargs.setdefault("timeout", 30)
        last_error = None
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    if method == "GET":
                        response = await client.get(url, **kwargs)
                    else:
                        response = await client.post(url, **kwargs)
                    
                    if response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", 2))
                        logger.warning(f"1inch API rate limited (429), retrying in {retry_after}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    return response
                    
            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
                last_error = e
                wait_time = (attempt + 1) * 2
                logger.warning(f"1inch API request failed: {e}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
            except Exception as e:
                last_error = e
                logger.error(f"1inch API unexpected error: {e}")
                break
        
        raise last_error or Exception("Max retries exceeded for 1inch API")
    
    async def get_supported_tokens(self, chain_id: int) -> Dict[str, Any]:
        try:
            response = await self._request_with_retry(
                "GET",
                f"{ONEINCH_API_BASE}/{chain_id}/tokens",
                headers=self._get_headers(),
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get tokens: {response.status_code} - {response.text[:200]}")
                return {"tokens": {}}
        except Exception as e:
            logger.error(f"Error fetching tokens: {e}")
            return {"tokens": {}}
    
    async def get_quote(
        self,
        src_token: str,
        dst_token: str,
        amount: str,
        chain_id: int
    ) -> Dict[str, Any]:
        if not self.api_key:
            return {"success": False, "error": "1inch API key not configured. Please add your ONEINCH_API_KEY."}
        
        if not src_token or not dst_token:
            return {"success": False, "error": "Source and destination tokens are required"}
        
        if not amount or str(amount) == "0":
            return {"success": False, "error": "Amount must be greater than 0"}
        
        try:
            params = {
                "src": src_token,
                "dst": dst_token,
                "amount": str(amount),
                "includeTokensInfo": "true",
                "includeProtocols": "true",
                "includeGas": "true",
            }
            
            logger.info(f"Getting quote: {src_token[:10]}... -> {dst_token[:10]}..., amount={amount}, chain={chain_id}")
            
            response = await self._request_with_retry(
                "GET",
                f"{ONEINCH_API_BASE}/{chain_id}/quote",
                params=params,
                headers=self._get_headers(),
            )
            
            if response.status_code == 200:
                data = response.json()
                dst_amount = data.get("dstAmount", "0")
                logger.info(f"Quote received: dstAmount={dst_amount}")
                return {
                    "success": True,
                    "srcToken": data.get("srcToken", {}),
                    "dstToken": data.get("dstToken", {}),
                    "srcAmount": str(amount),
                    "dstAmount": dst_amount,
                    "gas": data.get("gas"),
                    "protocols": data.get("protocols", []),
                }
            elif response.status_code == 400:
                error_data = {}
                try:
                    error_data = response.json()
                except Exception:
                    pass
                error_msg = error_data.get("description") or error_data.get("error") or f"Bad request (400)"
                logger.error(f"Quote failed (400): {error_msg}")
                return {"success": False, "error": f"Quote error: {error_msg}"}
            elif response.status_code == 422:
                error_data = {}
                try:
                    error_data = response.json()
                except Exception:
                    pass
                error_msg = error_data.get("description") or "Invalid token pair or amount"
                logger.error(f"Quote validation failed (422): {error_msg}")
                return {"success": False, "error": f"Invalid swap parameters: {error_msg}"}
            else:
                error_text = ""
                try:
                    error_data = response.json()
                    error_text = error_data.get("description", response.text[:200])
                except Exception:
                    error_text = response.text[:200]
                logger.error(f"Quote failed: {response.status_code} - {error_text}")
                return {
                    "success": False,
                    "error": f"Quote service error ({response.status_code}): {error_text}"
                }
                    
        except Exception as e:
            logger.error(f"Quote error: {e}")
            return {"success": False, "error": f"Failed to get quote: {str(e)}"}
    
    async def get_swap_data(
        self,
        src_token: str,
        dst_token: str,
        amount: str,
        from_address: str,
        chain_id: int,
        slippage: float = 1.0,
        disable_estimate: bool = True
    ) -> Dict[str, Any]:
        if not self.api_key:
            return {"success": False, "error": "1inch API key not configured"}
        
        if not from_address:
            return {"success": False, "error": "Wallet address is required for swap"}
        
        try:
            params = {
                "src": src_token,
                "dst": dst_token,
                "amount": str(amount),
                "from": from_address,
                "slippage": str(slippage),
                "disableEstimate": str(disable_estimate).lower(),
                "allowPartialFill": "false",
            }
            
            logger.info(f"Getting swap data: {src_token[:10]}... -> {dst_token[:10]}..., from={from_address[:10]}..., slippage={slippage}%, chain={chain_id}")
            
            response = await self._request_with_retry(
                "GET",
                f"{ONEINCH_API_BASE}/{chain_id}/swap",
                params=params,
                headers=self._get_headers(),
            )
            
            if response.status_code == 200:
                data = response.json()
                tx = data.get("tx", {})
                logger.info(f"Swap data generated successfully for {from_address[:10]}...")
                return {
                    "success": True,
                    "srcToken": data.get("srcToken", {}),
                    "dstToken": data.get("dstToken", {}),
                    "srcAmount": data.get("srcAmount"),
                    "dstAmount": data.get("dstAmount"),
                    "tx": {
                        "from": tx.get("from"),
                        "to": tx.get("to"),
                        "data": tx.get("data"),
                        "value": tx.get("value", "0"),
                        "gas": str(tx.get("gas", "0")),
                        "gasPrice": tx.get("gasPrice"),
                    }
                }
            elif response.status_code == 400:
                error_data = {}
                try:
                    error_data = response.json()
                except Exception:
                    pass
                error_msg = error_data.get("description") or error_data.get("error") or "Bad request"
                logger.error(f"Swap failed (400): {error_msg}")
                
                if "insufficient" in error_msg.lower() or "balance" in error_msg.lower():
                    return {"success": False, "error": "Insufficient token balance for this swap. Please check your wallet balance."}
                if "allowance" in error_msg.lower():
                    return {"success": False, "error": "Token approval required. Please approve the token first.", "code": "NEEDS_APPROVAL"}
                
                return {"success": False, "error": f"Swap error: {error_msg}"}
            elif response.status_code == 403:
                logger.error(f"Swap endpoint forbidden (403) - API key may lack swap permissions")
                return {
                    "success": False,
                    "error": "Swap execution requires an upgraded 1inch API plan. Your current API key supports quotes and approvals but not swap transaction generation.",
                    "code": "SWAP_PLAN_REQUIRED"
                }
            elif response.status_code == 422:
                error_data = {}
                try:
                    error_data = response.json()
                except Exception:
                    pass
                error_msg = error_data.get("description") or "Invalid swap parameters"
                logger.error(f"Swap validation failed (422): {error_msg}")
                return {"success": False, "error": f"Invalid swap: {error_msg}"}
            else:
                error_text = ""
                try:
                    error_data = response.json()
                    error_text = error_data.get("description", response.text[:200])
                except Exception:
                    error_text = response.text[:200]
                logger.error(f"Swap data failed: {response.status_code} - {error_text}")
                return {
                    "success": False,
                    "error": f"Swap service error ({response.status_code}): {error_text}"
                }
                    
        except Exception as e:
            logger.error(f"Swap data error: {e}")
            return {"success": False, "error": f"Failed to generate swap: {str(e)}"}
    
    async def get_spender_address(self, chain_id: int) -> Dict[str, Any]:
        if not self.api_key:
            return {"success": False, "error": "1inch API key not configured"}
        
        # Check Redis cache
        from core.redis_client import cache_get, cache_set
        redis_key = f"dex:spender:{chain_id}"
        cached = await cache_get(redis_key)
        if cached:
            return cached
        
        try:
            response = await self._request_with_retry(
                "GET",
                f"{ONEINCH_API_BASE}/{chain_id}/approve/spender",
                headers=self._get_headers(),
            )
            
            if response.status_code == 200:
                data = response.json()
                result = {
                    "success": True,
                    "address": data.get("address")
                }
                await cache_set(redis_key, result, 3600)
                return result
            else:
                logger.error(f"Spender address failed: {response.status_code}")
                return {"success": False, "error": f"Failed to get router address ({response.status_code})"}
                    
        except Exception as e:
            logger.error(f"Spender address error: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_allowance(
        self,
        token_address: str,
        wallet_address: str,
        chain_id: int
    ) -> Dict[str, Any]:
        if not self.api_key:
            return {"success": False, "error": "1inch API key not configured"}
        
        try:
            params = {
                "tokenAddress": token_address,
                "walletAddress": wallet_address,
            }
            
            response = await self._request_with_retry(
                "GET",
                f"{ONEINCH_API_BASE}/{chain_id}/approve/allowance",
                params=params,
                headers=self._get_headers(),
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "allowance": data.get("allowance", "0")
                }
            else:
                logger.error(f"Allowance check failed: {response.status_code}")
                return {"success": False, "error": f"Failed to check allowance ({response.status_code})"}
                    
        except Exception as e:
            logger.error(f"Allowance check error: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_approve_calldata(
        self,
        token_address: str,
        chain_id: int,
        amount: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self.api_key:
            return {"success": False, "error": "1inch API key not configured"}
        
        try:
            params = {"tokenAddress": token_address}
            if amount:
                params["amount"] = str(amount)
            
            response = await self._request_with_retry(
                "GET",
                f"{ONEINCH_API_BASE}/{chain_id}/approve/transaction",
                params=params,
                headers=self._get_headers(),
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "tx": {
                        "to": data.get("to"),
                        "data": data.get("data"),
                        "value": data.get("value", "0"),
                        "gas": data.get("gasLimit"),
                    }
                }
            else:
                logger.error(f"Approve calldata failed: {response.status_code}")
                return {"success": False, "error": f"Failed to get approval data ({response.status_code})"}
                    
        except Exception as e:
            logger.error(f"Approve calldata error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_token_address(self, symbol: str, chain_id: int) -> Optional[str]:
        chain_tokens = COMMON_TOKENS.get(chain_id, {})
        return chain_tokens.get(symbol.upper())
    
    def get_chain_id(self, chain_name: str) -> int:
        return CHAIN_IDS.get(chain_name.lower())

    def is_chain_supported(self, chain_id: int) -> bool:
        return is_supported(chain_id)
    
    async def get_liquidity_sources(self, chain_id: int) -> Dict[str, Any]:
        if not self.api_key:
            return {"success": False, "error": "1inch API key not configured"}
        
        try:
            response = await self._request_with_retry(
                "GET",
                f"{ONEINCH_API_BASE}/{chain_id}/liquidity-sources",
                headers=self._get_headers(),
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "protocols": data.get("protocols", [])
                }
            else:
                return {"success": False, "error": f"Failed to get liquidity sources ({response.status_code})"}
                    
        except Exception as e:
            logger.error(f"Liquidity sources error: {e}")
            return {"success": False, "error": str(e)}


    async def generate_swap_data_for_sc(
        self,
        chain_id: int,
        src_token: str,
        dst_token: str,
        amount: str,
        sc_address: str,
        slippage: float = 1.0,
    ) -> Dict[str, Any]:
        if not self.api_key:
            return {"success": False, "error": "1inch API key not configured"}

        if not sc_address:
            return {"success": False, "error": "Smart contract address is required"}

        try:
            params = {
                "src": src_token,
                "dst": dst_token,
                "amount": str(amount),
                "from": sc_address,
                "slippage": str(slippage),
                "disableEstimate": "true",
                "allowPartialFill": "false",
            }

            logger.info(
                f"Generating SC swap data: {src_token[:10]}... -> {dst_token[:10]}..., "
                f"sc={sc_address[:10]}..., chain={chain_id}"
            )

            response = await self._request_with_retry(
                "GET",
                f"{ONEINCH_API_BASE}/{chain_id}/swap",
                params=params,
                headers=self._get_headers(),
            )

            if response.status_code == 200:
                data = response.json()
                tx = data.get("tx", {})
                return {
                    "success": True,
                    "tx": {
                        "to": tx.get("to"),
                        "data": tx.get("data"),
                        "value": tx.get("value", "0"),
                        "gas": str(tx.get("gas", "0")),
                    },
                    "srcAmount": data.get("srcAmount"),
                    "dstAmount": data.get("dstAmount"),
                }
            else:
                error_text = ""
                try:
                    error_data = response.json()
                    error_text = error_data.get("description", response.text[:200])
                except Exception:
                    error_text = response.text[:200]
                logger.error(f"SC swap data failed: {response.status_code} - {error_text}")
                return {"success": False, "error": f"SC swap data error ({response.status_code}): {error_text}"}

        except Exception as e:
            logger.error(f"SC swap data error: {e}")
            return {"success": False, "error": f"Failed to generate SC swap data: {str(e)}"}


dex_service = None


def init_dex_service(api_key: Optional[str] = None) -> DexService:
    global dex_service
    dex_service = DexService(api_key)
    return dex_service
