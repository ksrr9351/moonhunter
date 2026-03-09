"""
Wallet Service - Fetches real token balances across multiple EVM chains
"""
import os
import httpx
import logging
import asyncio
import time
from typing import Dict, Any, Optional, List
from decimal import Decimal

logger = logging.getLogger(__name__)

from chain_registry import CHAIN_REGISTRY, get_rpc_urls, register_on_refresh

# No hardcoded token addresses — all derived from CHAIN_REGISTRY (USDT/USDC)


def _build_rpc_providers() -> dict:
    return {
        cid: data["rpc_urls"]
        for cid, data in CHAIN_REGISTRY.items()
        if data.get("rpc_urls") and not data.get("is_testnet", False)
    }


def _build_chain_tokens() -> dict:
    """Derive per-chain token configs from CHAIN_REGISTRY."""
    tokens = {}
    for cid, data in CHAIN_REGISTRY.items():
        if data.get("is_testnet", False):
            continue
        ct = {}
        if data.get("usdt_address"):
            ct["USDT"] = {"address": data["usdt_address"], "decimals": data.get("usdt_decimals", 6)}
        if data.get("usdc_address"):
            ct["USDC"] = {"address": data["usdc_address"], "decimals": data.get("usdc_decimals", 6)}
        if ct:
            tokens[cid] = ct
    return tokens


# Module-level dicts — rebuilt when CHAIN_REGISTRY refreshes
CHAIN_RPC_PROVIDERS = _build_rpc_providers()
CHAIN_TOKENS = _build_chain_tokens()
SUPPORTED_CHAIN_IDS = set(CHAIN_RPC_PROVIDERS.keys())


def _rebuild_wallet_data():
    """Rebuild all module-level dicts from the refreshed CHAIN_REGISTRY."""
    global CHAIN_RPC_PROVIDERS, CHAIN_TOKENS, SUPPORTED_CHAIN_IDS
    CHAIN_RPC_PROVIDERS = _build_rpc_providers()
    CHAIN_TOKENS = _build_chain_tokens()
    SUPPORTED_CHAIN_IDS = set(CHAIN_RPC_PROVIDERS.keys())
    logger.info(f"Wallet data rebuilt: {len(CHAIN_RPC_PROVIDERS)} chains, {len(CHAIN_TOKENS)} token sets")
    # Also update the live WalletService instance so it uses fresh RPCs
    if wallet_service is not None:
        wallet_service.chain_rpc_providers = {cid: rpcs.copy() for cid, rpcs in CHAIN_RPC_PROVIDERS.items()}

register_on_refresh(_rebuild_wallet_data)


class WalletService:
    """Service for fetching real wallet balances across multiple EVM chains"""
    
    CHAIN_CACHE_TTL = 120
    
    def __init__(self, db):
        self.db = db
        self.chain_rpc_providers = {cid: rpcs.copy() for cid, rpcs in CHAIN_RPC_PROVIDERS.items()}
        self._chain_cache = {}
        logger.info("WalletService initialized with %d supported chains", len(self.chain_rpc_providers))
    
    def _get_rpc_list(self, chain_id: int) -> list:
        # First try instance snapshot (built at init time)
        if chain_id in self.chain_rpc_providers and self.chain_rpc_providers[chain_id]:
            return self.chain_rpc_providers[chain_id]
        # Fallback: live CHAIN_REGISTRY (populated after startup by refresh_chain_registry)
        live_rpcs = get_rpc_urls(chain_id)
        if live_rpcs:
            self.chain_rpc_providers[chain_id] = live_rpcs  # cache for next time
            return live_rpcs
        logger.warning(f"No RPC providers configured for chain {chain_id}")
        return []

    async def _rpc_call_with_failover(self, payload: dict, chain_id: int, max_retries: int = 3) -> Optional[dict]:
        """Make RPC call with automatic failover to backup providers"""
        rpc_list = self._get_rpc_list(chain_id)
        if not rpc_list:
            logger.error(f"No RPC providers for chain {chain_id}")
            return None

        last_error = None
        
        for attempt in range(max_retries):
            for i, rpc_url in enumerate(rpc_list):
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.post(rpc_url, json=payload)
                        
                        if response.status_code in (502, 503):
                            logger.warning(f"RPC {rpc_url} returned {response.status_code}, trying next...")
                            continue
                        
                        if response.status_code != 200:
                            logger.warning(f"RPC {rpc_url} returned {response.status_code}")
                            continue
                        
                        result = response.json()
                        
                        if "error" in result:
                            logger.warning(f"RPC {rpc_url} error: {result['error']}")
                            continue
                        
                        if i != 0:
                            rpc_list[0], rpc_list[i] = rpc_list[i], rpc_list[0]
                            logger.info(f"Promoted {rpc_url} to primary RPC for chain {chain_id}")
                        
                        return result
                        
                except httpx.TimeoutException:
                    logger.warning(f"RPC {rpc_url} timed out")
                    last_error = "timeout"
                except Exception as e:
                    logger.warning(f"RPC {rpc_url} error: {e}")
                    last_error = str(e)
            
            if attempt < max_retries - 1:
                wait_time = 0.5 * (attempt + 1)
                logger.info(f"All RPCs for chain {chain_id} failed, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
        
        logger.error(f"All RPC providers for chain {chain_id} failed after {max_retries} attempts. Last error: {last_error}")
        return None
    
    async def get_eth_balance(self, wallet_address: str, chain_id: int) -> Dict[str, Any]:
        """Get native ETH balance using public RPC with failover"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getBalance",
                "params": [wallet_address, "latest"],
                "id": 1
            }
            
            result = await self._rpc_call_with_failover(payload, chain_id=chain_id)
            
            if result and "result" in result:
                balance_wei = int(result.get("result", "0x0"), 16)
                balance_eth = balance_wei / (10 ** 18)
                
                return {
                    "symbol": "ETH",
                    "balance": balance_eth,
                    "balance_raw": str(balance_wei)
                }
            
            return {"symbol": "ETH", "balance": 0, "balance_raw": "0"}
        except Exception as e:
            logger.error(f"Error fetching ETH balance on chain {chain_id}: {e}")
            return {"symbol": "ETH", "balance": 0, "balance_raw": "0"}
    
    async def get_usdt_balance(self, wallet_address: str, chain_id: int) -> Dict[str, Any]:
        """Get USDT (ERC-20) balance - THE SOURCE OF TRUTH FOR INVESTING"""
        return await self._get_token_balance(wallet_address, "USDT", chain_id=chain_id)
    
    async def _get_token_balance(self, wallet_address: str, token_symbol: str, chain_id: int) -> Dict[str, Any]:
        """Get ERC-20 token balance using public RPC with failover"""
        tokens_for_chain = CHAIN_TOKENS.get(chain_id, {})
        token_info = tokens_for_chain.get(token_symbol)
        if not token_info:
            return {"symbol": token_symbol, "balance": 0, "balance_raw": "0"}
        
        try:
            balance_of_sig = "0x70a08231"
            padded_address = wallet_address[2:].lower().zfill(64)
            data = f"{balance_of_sig}{padded_address}"
            
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [
                    {
                        "to": token_info["address"],
                        "data": data
                    },
                    "latest"
                ],
                "id": 1
            }
            
            result = await self._rpc_call_with_failover(payload, chain_id=chain_id)
            
            if result and "result" in result:
                balance_raw = result.get("result", "0x0")
                
                if balance_raw == "0x" or balance_raw == "0x0":
                    balance = 0
                else:
                    balance_int = int(balance_raw, 16)
                    balance = balance_int / (10 ** token_info["decimals"])
                
                return {
                    "symbol": token_symbol,
                    "balance": balance,
                    "balance_raw": str(int(balance_raw, 16) if balance_raw not in ["0x", "0x0"] else 0)
                }
            
            return {"symbol": token_symbol, "balance": 0, "balance_raw": "0"}
        except Exception as e:
            logger.error(f"Error fetching {token_symbol} balance on chain {chain_id}: {e}")
            return {"symbol": token_symbol, "balance": 0, "balance_raw": "0"}
    
    async def get_all_balances(self, wallet_address: str, chain_id: int) -> Dict[str, Any]:
        """Get all relevant balances for the wallet on the specified chain"""
        eth_balance = await self.get_eth_balance(wallet_address, chain_id=chain_id)

        tokens_for_chain = CHAIN_TOKENS.get(chain_id, {})

        # Fetch ALL stablecoins present on this chain, then pick the one with highest balance
        stable_candidates = []
        for sym in ("USDT", "USDC"):
            if sym in tokens_for_chain:
                bal = await self._get_token_balance(wallet_address, sym, chain_id=chain_id)
                stable_candidates.append(bal)

        if not stable_candidates:
            stablecoin_balance = {"symbol": "USDT", "balance": 0, "balance_raw": "0"}
        else:
            # Use whichever has a non-zero balance; if both non-zero, prefer USDC (more common on Base/L2s)
            non_zero = [b for b in stable_candidates if b["balance"] > 0]
            if non_zero:
                # Prefer USDC if available, else take the first non-zero
                usdc_bal = next((b for b in non_zero if b["symbol"] == "USDC"), None)
                stablecoin_balance = usdc_bal if usdc_bal else non_zero[0]
            else:
                stablecoin_balance = stable_candidates[0]

        # Build full token list (stablecoin first, then any other tokens with balance > 0)
        tokens = [stablecoin_balance]
        for symbol in tokens_for_chain:
            if symbol == stablecoin_balance["symbol"]:
                continue
            # Skip stablecoins already checked above
            if symbol in ("USDT", "USDC"):
                other = next((b for b in stable_candidates if b["symbol"] == symbol), None)
                if other and other["balance"] > 0 and other["symbol"] != stablecoin_balance["symbol"]:
                    tokens.append(other)
                continue
            token_balance = await self._get_token_balance(wallet_address, symbol, chain_id=chain_id)
            if token_balance["balance"] > 0:
                tokens.append(token_balance)

        return {
            "wallet_address": wallet_address,
            "chain_id": chain_id,
            "eth": eth_balance,
            "stablecoin": stablecoin_balance,
            "tokens": tokens,
            "available_usdt": stablecoin_balance["balance"]
        }
    
    async def get_user_wallet_status(self, user_id: str, chain_id: int = None) -> Dict[str, Any]:
        """Get complete wallet status for a user including invested amounts.
        Uses chain_id if provided, else falls back to user's saved chain_id in DB,
        else scans all supported chains to find balance."""
        user = await self.db.users.find_one({"id": user_id}, {"_id": 0})
        if not user or not user.get("wallet_address"):
            return {
                "connected": False,
                "wallet_address": None,
                "available_usdt": 0,
                "invested_usdt": 0,
                "locked_usdt": 0,
                "total_usdt": 0
            }

        wallet_address = user["wallet_address"]
        # Resolve chain: caller > user's saved chain > cache > scan
        resolved_chain_id = chain_id or user.get("chain_id") or None
        cache_key = wallet_address.lower()

        cached = self._chain_cache.get(cache_key)
        if cached and (time.time() - cached["ts"]) < self.CHAIN_CACHE_TTL:
            best_chain_id = cached["chain_id"]
            logger.info(f"Using cached chain {best_chain_id} for {wallet_address[:10]}...")
            best_balances = await self.get_all_balances(wallet_address, chain_id=best_chain_id)
        elif resolved_chain_id:
            balances = await self.get_all_balances(wallet_address, chain_id=resolved_chain_id)
            best_chain_id = resolved_chain_id
            best_balances = balances

            if float(balances["eth"]["balance"]) == 0 and float(balances["available_usdt"]) == 0:
                logger.info(f"Zero balance on chain {resolved_chain_id} for {wallet_address[:10]}..., scanning all chains")
                other_chains = [c for c in SUPPORTED_CHAIN_IDS if c != resolved_chain_id]
                scan_tasks = [self.get_all_balances(wallet_address, chain_id=c) for c in other_chains]
                results = await asyncio.gather(*scan_tasks, return_exceptions=True)

                for c, result in zip(other_chains, results):
                    if isinstance(result, Exception):
                        logger.warning(f"Failed to scan chain {c}: {result}")
                        continue
                    eth_bal = float(result["eth"]["balance"])
                    usdt_bal = float(result["available_usdt"])
                    if eth_bal > 0 or usdt_bal > 0:
                        logger.info(f"Found balance on chain {c}: ETH={eth_bal}, stablecoin={usdt_bal}")
                        if eth_bal > float(best_balances["eth"]["balance"]) or usdt_bal > float(best_balances["available_usdt"]):
                            best_chain_id = c
                            best_balances = result

            self._chain_cache[cache_key] = {"chain_id": best_chain_id, "ts": time.time()}
        else:
            # No chain info at all — scan all supported chains
            logger.info(f"No chain_id available for {wallet_address[:10]}..., scanning all supported chains")
            best_chain_id = next(iter(SUPPORTED_CHAIN_IDS))
            best_balances = {"eth": {"balance": 0}, "available_usdt": 0, "tokens": []}
            scan_tasks = [self.get_all_balances(wallet_address, chain_id=c) for c in SUPPORTED_CHAIN_IDS]
            results = await asyncio.gather(*scan_tasks, return_exceptions=True)

            for c, result in zip(SUPPORTED_CHAIN_IDS, results):
                if isinstance(result, Exception):
                    continue
                eth_bal = float(result["eth"]["balance"])
                usdt_bal = float(result["available_usdt"])
                if eth_bal > float(best_balances["eth"]["balance"]) or usdt_bal > float(best_balances["available_usdt"]):
                    best_chain_id = c
                    best_balances = result

            self._chain_cache[cache_key] = {"chain_id": best_chain_id, "ts": time.time()}
        
        positions = await self.db.ai_positions.find(
            {"user_id": user_id, "status": "active"},
            {"_id": 0}
        ).to_list(1000)
        
        invested_usdt = sum(pos.get("invested_usdt", 0) for pos in positions)
        
        return {
            "connected": True,
            "wallet_address": wallet_address,
            "chain_id": best_chain_id,
            "eth_balance": best_balances["eth"]["balance"],
            "available_usdt": best_balances["available_usdt"],
            "invested_usdt": invested_usdt,
            "locked_usdt": 0,
            "total_usdt": best_balances["available_usdt"] + invested_usdt,
            "tokens": best_balances["tokens"]
        }


wallet_service = None

def init_wallet_service(db):
    global wallet_service
    wallet_service = WalletService(db)
    return wallet_service
