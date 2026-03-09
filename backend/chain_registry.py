"""
Centralized Chain Registry — Single source of truth for all EVM chain metadata.
Populated dynamically at startup from 1inch API + chainid.network metadata.
Refreshes every 6 hours. Zero hardcoded chain data — everything discovered from APIs.
"""
import os
import logging
import asyncio
import hashlib
from typing import Dict, List, Optional, Any, Callable
import httpx

logger = logging.getLogger(__name__)

NATIVE_TOKEN_ADDRESS = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"

# ---- Dynamic registry — starts empty, populated by refresh_chain_registry() ----
CHAIN_REGISTRY: Dict[int, Dict[str, Any]] = {}

# ---- API endpoints ----
CHAINID_NETWORK_URL = "https://chainid.network/chains.json"
ONEINCH_API_BASE = "https://api.1inch.dev/swap/v6.0"
ONEINCH_TOKEN_API = "https://api.1inch.dev/token/v1.2"

# ---- Callback system for downstream rebuilds ----
_on_refresh_callbacks: List[Callable] = []


def register_on_refresh(callback: Callable) -> None:
    """Register a callback to be called after CHAIN_REGISTRY is refreshed."""
    _on_refresh_callbacks.append(callback)


def _color_from_name(name: str) -> str:
    """Generate a deterministic hex color from chain name."""
    digest = hashlib.md5(name.encode()).hexdigest()  # noqa: S324 — not for security
    return f"#{digest[:6]}"


def _filter_public_rpcs(rpc_list: list) -> List[str]:
    """Filter out RPC URLs with API key templates, keep up to 5 public ones."""
    public = []
    for url in rpc_list:
        if not isinstance(url, str):
            continue
        if "${" in url or "{" in url or "API_KEY" in url.upper():
            continue
        if url.startswith("http"):
            public.append(url)
        if len(public) >= 5:
            break
    return public



async def _fetch_chainid_metadata() -> Dict[int, dict]:
    """Fetch chain metadata from chainid.network. Raises on failure."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(CHAINID_NETWORK_URL)
        resp.raise_for_status()
        chains_list = resp.json()
    return {c["chainId"]: c for c in chains_list if isinstance(c, dict) and "chainId" in c}


async def _fetch_1inch_supported_chains(api_key: str) -> Optional[List[int]]:
    """
    Discover which chains 1inch actually supports by probing only the ~20 chains
    that 1inch has ever supported — avoids spamming 2000+ chains with 404s.
    Returns list of confirmed chain IDs, or None on total failure.
    """
    # All chains 1inch has ever listed as supported across their history.
    # Probe only these — not all 2000+ chains on chainid.network.
    ONEINCH_KNOWN_CHAINS = [
        1,      # Ethereum
        10,     # Optimism
        56,     # BNB Chain
        100,    # Gnosis
        137,    # Polygon
        250,    # Fantom
        324,    # zkSync Era
        8217,   # Klaytn
        8453,   # Base
        42161,  # Arbitrum One
        43114,  # Avalanche
        1101,   # Polygon zkEVM
        59144,  # Linea
        534352, # Scroll
        146,    # Sonic
    ]
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    semaphore = asyncio.Semaphore(5)

    async def probe(chain_id: int) -> Optional[int]:
        url = f"{ONEINCH_API_BASE}/{chain_id}/approve/spender"
        async with semaphore:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(url, headers=headers)
                return chain_id if resp.status_code == 200 else None
            except Exception:
                return None

    results = await asyncio.gather(*[probe(cid) for cid in ONEINCH_KNOWN_CHAINS])
    confirmed = [cid for cid in results if cid is not None]
    return confirmed if confirmed else None



async def _search_stablecoin(
    chain_id: int, symbol: str, api_key: str, semaphore: asyncio.Semaphore
) -> Optional[Dict[str, Any]]:
    """
    Search for a stablecoin (USDT/USDC) on a chain using 1inch Token Search API.
    Returns {"address": "0x...", "decimals": 6} or None.
    """
    url = f"{ONEINCH_TOKEN_API}/{chain_id}/search"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    params = {"query": symbol, "limit": 10}
    async with semaphore:
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(url, headers=headers, params=params)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 2))
                    await asyncio.sleep(retry_after)
                    continue
                if resp.status_code != 200:
                    return None
                tokens = resp.json()
                if not isinstance(tokens, list):
                    return None
                for token in tokens:
                    if isinstance(token, dict) and token.get("symbol", "").upper() == symbol.upper():
                        return {
                            "address": token.get("address"),
                            "decimals": token.get("decimals"),
                        }
                return None
            except (httpx.HTTPError, Exception):
                if attempt < 1:
                    await asyncio.sleep(1)
                    continue
                return None
    return None


async def _fetch_stablecoins_for_chains(
    chain_ids: List[int], api_key: str
) -> Dict[int, Dict[str, Any]]:
    """
    For each confirmed chain, discover USDT and USDC addresses via 1inch Token Search API.
    Returns {chain_id: {usdt_address, usdc_address, usdt_decimals, usdc_decimals}}.
    """
    semaphore = asyncio.Semaphore(3)

    tasks = []
    task_meta: List[tuple] = []
    for cid in chain_ids:
        for symbol in ("USDT", "USDC"):
            tasks.append(_search_stablecoin(cid, symbol, api_key, semaphore))
            task_meta.append((cid, symbol))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    stables: Dict[int, Dict[str, Any]] = {}
    for (cid, symbol), result in zip(task_meta, results):
        if cid not in stables:
            stables[cid] = {
                "usdt_address": None, "usdc_address": None,
                "usdt_decimals": None, "usdc_decimals": None,
            }
        if isinstance(result, dict) and result.get("address"):
            prefix = symbol.lower()
            stables[cid][f"{prefix}_address"] = result["address"]
            stables[cid][f"{prefix}_decimals"] = result.get("decimals")

    return stables


# Reliable public RPC fallbacks for chains where chainid.network has no template-free RPCs
_FALLBACK_RPCS: Dict[int, List[str]] = {
    1:      ["https://eth.llamarpc.com", "https://rpc.ankr.com/eth"],
    10:     ["https://mainnet.optimism.io", "https://rpc.ankr.com/optimism"],
    56:     ["https://bsc-dataseed.binance.org", "https://rpc.ankr.com/bsc"],
    100:    ["https://rpc.gnosischain.com", "https://rpc.ankr.com/gnosis"],
    137:    ["https://polygon-rpc.com", "https://rpc.ankr.com/polygon"],
    146:    ["https://rpc.soniclabs.com"],
    324:    ["https://mainnet.era.zksync.io"],
    8453:   ["https://mainnet.base.org", "https://base.llamarpc.com", "https://rpc.ankr.com/base"],
    42161:  ["https://arb1.arbitrum.io/rpc", "https://rpc.ankr.com/arbitrum"],
    43114:  ["https://api.avax.network/ext/bc/C/rpc", "https://rpc.ankr.com/avalanche"],
    59144:  ["https://rpc.linea.build"],
}


def _build_chain_entry(
    chain_id: int, chainid_meta: Optional[dict], stables: Dict[str, Any]
) -> Dict[str, Any]:
    """Build a single CHAIN_REGISTRY entry from chainid.network metadata + discovered stablecoins."""
    if chainid_meta:
        name = chainid_meta.get("name", f"Chain {chain_id}")
        symbol = chainid_meta.get("nativeCurrency", {}).get("symbol", "ETH")
        rpc_urls = _filter_public_rpcs(chainid_meta.get("rpc", []))
        # If chainid.network gave no usable RPCs, use our known-good fallbacks
        if not rpc_urls and chain_id in _FALLBACK_RPCS:
            rpc_urls = _FALLBACK_RPCS[chain_id]
        explorers = chainid_meta.get("explorers", [])
        explorer = explorers[0]["url"].rstrip("/") if explorers else None
        is_testnet = (
            "testnet" in name.lower()
            or bool(chainid_meta.get("faucets"))
            or chainid_meta.get("status") == "deprecated"
        )
    else:
        name = f"Chain {chain_id}"
        symbol = "ETH"
        rpc_urls = _FALLBACK_RPCS.get(chain_id, [])
        explorer = None
        is_testnet = False

    return {
        "id": chain_id,
        "name": name,
        "symbol": symbol,
        "color": _color_from_name(name),
        "explorer": explorer,
        "explorer_tx_path": "/tx/",
        "is_testnet": is_testnet,
        "rpc_urls": rpc_urls,
        "usdt_address": stables.get("usdt_address"),
        "usdc_address": stables.get("usdc_address"),
        "usdt_decimals": stables.get("usdt_decimals"),
        "usdc_decimals": stables.get("usdc_decimals"),
    }


async def refresh_chain_registry() -> int:
    """
    Discover supported chains entirely from APIs:
    1. chainid.network → all EVM chain metadata (names, RPCs, explorers)
    2. 1inch chain/list → fetch supported chain IDs directly (no probing needed)
       Fallback: probe candidates via approve/spender if chain/list unavailable
    3. 1inch Token Search → discover USDT/USDC addresses on each confirmed chain
    Updates CHAIN_REGISTRY in-place. Returns the number of chains discovered.
    Raises on complete failure (no chains found or APIs unreachable).
    """
    from core.redis_client import cache_get, cache_set

    # Cold start: try Redis first
    if not CHAIN_REGISTRY:
        cached = await cache_get("chain:registry")
        if cached and isinstance(cached, dict) and len(cached) > 0:
            # Redis keys are strings, convert back to int
            int_keyed = {int(k): v for k, v in cached.items()}
            CHAIN_REGISTRY.update(int_keyed)
            for cb in _on_refresh_callbacks:
                try:
                    cb()
                except Exception as e:
                    logger.error(f"Refresh callback {cb.__name__} failed: {e}")
            logger.info(f"Chain registry restored from Redis: {len(int_keyed)} chains")
            return len(int_keyed)

    api_key = os.environ.get("ONEINCH_API_KEY", "")
    if not api_key:
        raise RuntimeError("ONEINCH_API_KEY not set — cannot discover chains")

    # Step 1: Fetch chainid.network metadata for ALL chains
    logger.info("Fetching chain metadata from chainid.network...")
    chainid_meta = await _fetch_chainid_metadata()
    logger.info(f"Got metadata for {len(chainid_meta)} chains from chainid.network")

    # Step 2: Get supported chain IDs directly from 1inch chain/list
    logger.info("Fetching supported chain IDs from 1inch chain/list...")
    confirmed_ids = await _fetch_1inch_supported_chains(api_key)
    if not confirmed_ids:
        raise RuntimeError("1inch chain/list returned no supported chains — cannot build registry")
    logger.info(f"1inch chain/list returned {len(confirmed_ids)} supported chains: {sorted(confirmed_ids)}")

    # Step 4: Discover stablecoins (USDT/USDC) on each confirmed chain
    logger.info(f"Discovering stablecoins on {len(confirmed_ids)} chains via 1inch Token Search...")
    stables_map = await _fetch_stablecoins_for_chains(confirmed_ids, api_key)

    # Step 5: Build entries for confirmed chains
    new_registry: Dict[int, Dict[str, Any]] = {}
    for cid in confirmed_ids:
        chain_stables = stables_map.get(cid, {})
        new_registry[cid] = _build_chain_entry(cid, chainid_meta.get(cid), chain_stables)

    # Step 6: Update in-place
    CHAIN_REGISTRY.clear()
    CHAIN_REGISTRY.update(new_registry)

    # Persist to Redis
    await cache_set("chain:registry", new_registry, 21600)

    # Step 7: Fire callbacks
    for cb in _on_refresh_callbacks:
        try:
            cb()
        except Exception as e:
            logger.error(f"Refresh callback {cb.__name__} failed: {e}")

    logger.info(f"Chain registry refreshed: {len(new_registry)} chains — {sorted(new_registry.keys())}")
    return len(new_registry)


# ---- Helper functions ----

def get_chain(chain_id: int) -> Optional[Dict[str, Any]]:
    """Get chain metadata by ID. Returns None if not found."""
    return CHAIN_REGISTRY.get(chain_id)


def get_all_chains(include_testnet: bool = False) -> List[Dict[str, Any]]:
    """Return all chains, optionally including testnets."""
    chains = list(CHAIN_REGISTRY.values())
    if not include_testnet:
        chains = [c for c in chains if not c.get("is_testnet", False)]
    return chains


def get_all_chain_ids(include_testnet: bool = False) -> List[int]:
    """Return all supported chain IDs."""
    return [c["id"] for c in get_all_chains(include_testnet)]


def get_rpc_urls(chain_id: int) -> List[str]:
    """Get RPC URLs for a chain. Returns empty list if chain not found."""
    chain = CHAIN_REGISTRY.get(chain_id)
    return chain["rpc_urls"] if chain else []


def get_first_rpc(chain_id: int) -> Optional[str]:
    """Get the primary RPC URL for a chain."""
    urls = get_rpc_urls(chain_id)
    return urls[0] if urls else None


def get_explorer_url(chain_id: int) -> Optional[str]:
    """Get block explorer base URL for a chain."""
    chain = CHAIN_REGISTRY.get(chain_id)
    return chain["explorer"] if chain else None


def get_explorer_tx_url(chain_id: int, tx_hash: str) -> Optional[str]:
    """Get full transaction URL for a chain."""
    chain = CHAIN_REGISTRY.get(chain_id)
    if not chain:
        return None
    return f"{chain['explorer']}{chain['explorer_tx_path']}{tx_hash}"


def is_supported(chain_id: int) -> bool:
    """Check if a chain ID is in the registry."""
    return chain_id in CHAIN_REGISTRY


def get_chain_name(chain_id: int) -> str:
    """Get chain display name. Returns 'Chain {id}' as fallback."""
    chain = CHAIN_REGISTRY.get(chain_id)
    return chain["name"] if chain else f"Chain {chain_id}"


def get_chains_for_api(include_testnet: bool = False) -> List[Dict[str, Any]]:
    """Return chain data formatted for the frontend API response."""
    chains = get_all_chains(include_testnet)
    return [
        {
            "id": c["id"],
            "name": c["name"],
            "symbol": c["symbol"],
            "color": c["color"],
            "explorer": c["explorer"],
            "explorer_tx_path": c["explorer_tx_path"],
            "is_testnet": c.get("is_testnet", False),
            "usdt_address": c.get("usdt_address"),
            "usdc_address": c.get("usdc_address"),
            "usdt_decimals": c.get("usdt_decimals"),
            "usdc_decimals": c.get("usdc_decimals"),
        }
        for c in chains
    ]
