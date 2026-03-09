/**
 * React hooks for dynamic chain & token data from the backend.
 * Wraps chainService with React state management.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { chainService } from '../services/chainService';

/**
 * Hook to fetch all supported chains from backend.
 * Returns { chains, loading, error, refetch, getChain }
 */
export function useChains(includeTestnet = false) {
  const [chains, setChains] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const mountedRef = useRef(true);

  const fetchChains = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await chainService.getChains(includeTestnet);
      if (mountedRef.current) {
        setChains(data);
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err.message || 'Failed to load chains');
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [includeTestnet]);

  useEffect(() => {
    mountedRef.current = true;
    fetchChains();
    return () => { mountedRef.current = false; };
  }, [fetchChains]);

  const getChain = useCallback((chainId) => {
    return chains.find(c => c.id === chainId) || null;
  }, [chains]);

  return { chains, loading, error, refetch: fetchChains, getChain };
}

/**
 * Hook to fetch tokens for a specific chain from 1inch API (via backend).
 * Returns { tokens, loading, error, refetch }
 */
export function useChainTokens(chainId) {
  const [tokens, setTokens] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const mountedRef = useRef(true);

  const fetchTokens = useCallback(async () => {
    if (!chainId) {
      setTokens([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await chainService.getTokens(chainId);
      if (mountedRef.current) {
        setTokens(data);
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err.message || 'Failed to load tokens');
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [chainId]);

  useEffect(() => {
    mountedRef.current = true;
    fetchTokens();
    return () => { mountedRef.current = false; };
  }, [fetchTokens]);

  return { tokens, loading, error, refetch: fetchTokens };
}
