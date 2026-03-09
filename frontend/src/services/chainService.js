/**
 * Centralized Chain Service — fetches chain & token data from backend.
 * All components should use this instead of hardcoded chain lists.
 */
import axios from 'axios';

const API_URL = import.meta.env.VITE_BACKEND_URL || '';

const getAuthHeaders = () => {
  const token = localStorage.getItem('auth_token');
  return { Authorization: `Bearer ${token}` };
};

// ---- In-memory caches ----
let chainCache = null;
let chainCacheTs = 0;
const CHAIN_CACHE_TTL = 10 * 60 * 1000; // 10 min

const tokenCache = {}; // { [chainId]: { data, ts } }
const TOKEN_CACHE_TTL = 5 * 60 * 1000; // 5 min

// ---- Chain data ----

export async function getChains(includeTestnet = false) {
  const now = Date.now();
  if (chainCache && (now - chainCacheTs) < CHAIN_CACHE_TTL) {
    return includeTestnet
      ? chainCache
      : chainCache.filter(c => !c.is_testnet);
  }

  try {
    const res = await axios.get(`${API_URL}/api/dex/chains`, {
      headers: getAuthHeaders(),
      params: { include_testnet: true },
      timeout: 10000,
    });
    if (res.data?.success && Array.isArray(res.data.chains)) {
      chainCache = res.data.chains;
      chainCacheTs = now;
      return includeTestnet
        ? chainCache
        : chainCache.filter(c => !c.is_testnet);
    }
  } catch (err) {
    console.warn('[ChainService] Failed to fetch chains:', err.message);
  }

  // Return cached data even if expired, or empty array
  if (chainCache) return chainCache;
  return [];
}

export function getChainById(chainId) {
  if (!chainCache) return null;
  return chainCache.find(c => c.id === chainId) || null;
}

export function getExplorerUrl(chainId) {
  const chain = getChainById(chainId);
  return chain?.explorer || '';
}

export function getExplorerTxUrl(chainId, txHash) {
  const chain = getChainById(chainId);
  if (!chain) return '';
  return `${chain.explorer}${chain.explorer_tx_path || '/tx/'}${txHash}`;
}

export function getChainName(chainId) {
  const chain = getChainById(chainId);
  return chain?.name || `Chain ${chainId}`;
}

export function getChainColor(chainId) {
  const chain = getChainById(chainId);
  return chain?.color || '#888';
}

export function getNativeSymbol(chainId) {
  const chain = getChainById(chainId);
  return chain?.symbol || 'ETH';
}

// ---- Token data ----

export async function getTokens(chainId) {
  if (!chainId) return [];

  const now = Date.now();
  const cached = tokenCache[chainId];
  if (cached && (now - cached.ts) < TOKEN_CACHE_TTL) {
    return cached.data;
  }

  try {
    const res = await axios.get(`${API_URL}/api/dex/tokens`, {
      headers: getAuthHeaders(),
      params: { chain_id: chainId },
      timeout: 15000,
    });
    if (res.data?.success && Array.isArray(res.data.tokens)) {
      tokenCache[chainId] = { data: res.data.tokens, ts: now };
      return res.data.tokens;
    }
  } catch (err) {
    console.warn(`[ChainService] Failed to fetch tokens for chain ${chainId}:`, err.message);
  }

  // Return cached data if available, even if expired
  if (cached) return cached.data;
  return [];
}

export function clearCache() {
  chainCache = null;
  chainCacheTs = 0;
  Object.keys(tokenCache).forEach(k => delete tokenCache[k]);
}

// ---- Utility for backwards compat ----

export function isChainsLoaded() {
  return chainCache !== null;
}

export const chainService = {
  getChains,
  getTokens,
  getChainById,
  getExplorerUrl,
  getExplorerTxUrl,
  getChainName,
  getChainColor,
  getNativeSymbol,
  clearCache,
  isChainsLoaded,
};

export default chainService;
