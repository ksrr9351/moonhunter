import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ArrowDown, RefreshCw, AlertTriangle, Check, Loader2, ExternalLink, Wallet, Info, Search } from 'lucide-react';
import { dexService } from '../services/dexService';
import { useWalletAuth } from '../contexts/WalletAuthContext';
import { useChains, useChainTokens } from '../hooks/useChains';

const formatSwapError = (err) => {
  const msg = err?.message || err?.toString() || '';

  if (err?.code === 4001 || /rejected|denied|user rejected/i.test(msg)) {
    return 'Transaction was rejected. Please try again when ready.';
  }
  if (/insufficient liquidity/i.test(msg) || /502/.test(msg)) {
    return 'Insufficient liquidity for this amount. Try a larger amount (min ~$1) or a different token pair.';
  }
  if (/insufficient.*eth.*balance|insufficient base.*balance|not enough.*gas|insufficient funds for gas/i.test(msg)) {
    return 'Not enough ETH/native token for gas fees. Please add a small amount of ETH to your wallet to cover gas (≈$0.01 worth).';
  }
  if (/insufficient funds/i.test(msg)) {
    return 'Insufficient funds for this transaction. Please check your wallet balance.';
  }
  if (/gas/i.test(msg) && /exceed|too low|underpriced/i.test(msg)) {
    return 'Transaction failed due to gas estimation. Try increasing slippage or adjusting the amount.';
  }
  if (/nonce/i.test(msg)) {
    return 'Transaction nonce conflict. Please reset your wallet or wait for pending transactions.';
  }
  if (/execution reverted/i.test(msg)) {
    return 'Transaction would fail on-chain. The swap route may have changed — please refresh the quote and try again.';
  }
  if (/could not coalesce/i.test(msg) || /CALL_EXCEPTION/i.test(msg)) {
    return 'Swap could not be completed. The price may have moved beyond your slippage tolerance. Try increasing slippage or reducing the amount.';
  }
  if (/code.*-32000/i.test(msg) || /code.*-32603/i.test(msg)) {
    return 'The network rejected this transaction. Please try again with a higher slippage or smaller amount.';
  }
  if (/timeout|timed? ?out/i.test(msg)) {
    return 'The request timed out. Please check your connection and try again.';
  }
  if (/network|chain/i.test(msg) && /switch|wrong|mismatch/i.test(msg)) {
    return msg;
  }
  if (/approval|approve/i.test(msg)) {
    return 'Token approval is needed before swapping. Please approve the token first.';
  }
  if (/SWAP_PLAN_REQUIRED/i.test(msg) || /premium/i.test(msg)) {
    return 'This swap requires a premium API plan. Quotes are available but execution needs an upgraded key.';
  }
  if (msg.length > 120) {
    return 'Something went wrong with this transaction. Please try again with different settings or a smaller amount.';
  }
  return msg || 'Swap failed. Please try again.';
};

const NATIVE_TOKEN = '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE';

export function SwapModal({ isOpen, onClose, initialFromToken, initialToToken, initialAmount, initialChainId, onSwapComplete }) {
  const { 
    walletAddress, 
    sendTransaction, 
    switchNetwork,
    walletProvider, 
    ensureWalletConnection, 
    connectWallet,
    signerReady,
    currentChainId: contextChainId,
    SUPPORTED_CHAINS
  } = useWalletAuth();

  // Dynamic chain and token data from backend
  const { chains: chainOptions, loading: chainsLoading } = useChains();
  
  const [chainId, setChainId] = useState(null);
  const { tokens: dynamicTokens, loading: tokensLoading } = useChainTokens(chainId);
  const [fromToken, setFromToken] = useState(null);
  const [toToken, setToToken] = useState(null);
  const [amount, setAmount] = useState('');
  const [slippage, setSlippage] = useState(1.0);
  const [slippageInput, setSlippageInput] = useState('1.0');
  
  const [quote, setQuote] = useState(null);
  const [loading, setLoading] = useState(false);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [quoteError, setQuoteError] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  
  const [needsApproval, setNeedsApproval] = useState(false);
  const [approving, setApproving] = useState(false);
  const [swapping, setSwapping] = useState(false);
  const [txHash, setTxHash] = useState('');
  const [walletReady, setWalletReady] = useState(false);
  const [currentWalletChain, setCurrentWalletChain] = useState(null);
  const [signerValidated, setSignerValidated] = useState(false);
  
  const initAttemptRef = useRef(0);
  const quoteTimerRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      setError('');
      setSuccess('');
      setStatusMessage('');
      setTxHash('');
      setQuote(null);
      setQuoteError('');
      setNeedsApproval(false);
      initAttemptRef.current = 0;

      // Priority: initialChainId (from parent) > wallet's live chain > first supported chain
      const detectedChain = initialChainId || contextChainId || null;
      const effectiveChain = (detectedChain && chainOptions.find(c => c.id === detectedChain))
        ? detectedChain
        : (chainOptions[0]?.id || null);
      setChainId(effectiveChain);
      if (effectiveChain) setCurrentWalletChain(effectiveChain);

      setFromToken(resolveToken(initialFromToken, dynamicTokens, 0));
      setToToken(resolveToken(initialToToken, dynamicTokens, 1));

      if (walletProvider) {
        initializeWallet();
      }
    }
  }, [isOpen]);

  // Set initial tokens when dynamic token list loads
  useEffect(() => {
    if (isOpen && dynamicTokens.length > 0 && !fromToken && !toToken) {
      setFromToken(resolveToken(initialFromToken, dynamicTokens, 0));
      setToToken(resolveToken(initialToToken, dynamicTokens, 1));
    }
  }, [dynamicTokens, isOpen]);

  // Once chainOptions are loaded, re-apply the correct chain
  // (handles case where modal opened before chains API responded)
  useEffect(() => {
    if (!isOpen || chainsLoading || chainOptions.length === 0) return;
    const preferred = initialChainId || contextChainId || null;
    if (preferred && chainOptions.find(c => c.id === preferred)) {
      setChainId(preferred);
    } else if (!chainId) {
      setChainId(chainOptions[0]?.id || null);
    }
  }, [chainsLoading, chainOptions, isOpen]);

  // Auto-detect: if wallet switches network while modal is open, follow it
  useEffect(() => {
    if (!isOpen || !contextChainId) return;
    if (chainOptions.length > 0 && chainOptions.find(c => c.id === contextChainId)) {
      if (chainId !== contextChainId) {
        console.log('[SWAP] Wallet chain changed, auto-switching to:', contextChainId);
        setChainId(contextChainId);
        setCurrentWalletChain(contextChainId);
        setQuote(null);
        setQuoteError('');
        setFromToken(null);
        setToToken(null);
        setNeedsApproval(false);
      }
    }
  }, [contextChainId, isOpen, chainOptions]);

  // Update from/to tokens when chain changes & new tokens arrive
  useEffect(() => {
    if (isOpen && dynamicTokens.length > 0 && chainId) {
      // Always use the new chain's token metadata (fixes symbol mismatch e.g. POL→ETH on Base)
      const fromMatch = fromToken && dynamicTokens.find(t => t.address.toLowerCase() === fromToken.address.toLowerCase());
      const toMatch = toToken && dynamicTokens.find(t => t.address.toLowerCase() === toToken.address.toLowerCase());
      setFromToken(fromMatch || dynamicTokens[0] || null);
      setToToken(toMatch || dynamicTokens[1] || null);
    }
  }, [chainId, dynamicTokens]);

  useEffect(() => {
    if (isOpen && walletProvider && !walletReady) {
      initializeWallet();
    }
  }, [walletProvider, signerReady]);

  const initializeWallet = async () => {
    if (!walletProvider) {
      setWalletReady(false);
      setSignerValidated(false);
      return;
    }
    
    try {
      setLoading(true);
      setError('');
      setStatusMessage('Connecting to wallet...');
      
      let lastError = null;
      const maxAttempts = 5;
      
      for (let attempt = 0; attempt < maxAttempts; attempt++) {
        try {
          const { chainId: walletChainId } = await ensureWalletConnection();
          setWalletReady(true);
          setCurrentWalletChain(walletChainId);
          setSignerValidated(true);
          setLoading(false);
          setStatusMessage('');
          if (walletChainId && chainOptions.find(c => c.id === walletChainId) && chainId !== walletChainId) {
            setChainId(walletChainId);
          }
          console.log('[SWAP] Wallet initialized, chain:', walletChainId);
          return;
        } catch (err) {
          lastError = err;
          console.log(`[SWAP] Wallet init attempt ${attempt + 1}/${maxAttempts} failed:`, err.message);
          if (attempt < maxAttempts - 1) {
            await new Promise(resolve => setTimeout(resolve, 800 * (attempt + 1)));
          }
        }
      }
      
      throw lastError || new Error('Failed to initialize wallet');
    } catch (err) {
      console.error('[SWAP] Wallet initialization failed:', err);
      setWalletReady(false);
      setSignerValidated(false);
      setLoading(false);
      setStatusMessage('');
      
      if (err.message?.includes('rejected') || err.message?.includes('denied')) {
        setError('Wallet authorization was rejected. Please try again.');
      } else if (err.message?.includes('connect')) {
        setError('Please connect your wallet first.');
      } else {
        setError('Unable to connect wallet for signing. Try disconnecting and reconnecting.');
      }
    }
  };
  
  const isWrongNetwork = walletReady && currentWalletChain !== null && currentWalletChain !== chainId;

  const resolveToken = (initial, tokens, fallbackIndex) => {
    if (!initial) return tokens[fallbackIndex] || null;
    if (typeof initial === 'object' && initial.address) {
      const existing = tokens.find(t => t.address.toLowerCase() === initial.address.toLowerCase());
      if (existing) return existing;
      // Use token list decimals as source of truth; fallback to 18 (never 0)
      const decimals = initial.decimals > 0 ? initial.decimals : 18;
      return { symbol: initial.symbol, address: initial.address, decimals, name: initial.name || initial.symbol };
    }
    const found = tokens.find(t => t.symbol === initial);
    if (found) return found;
    return tokens[fallbackIndex] || null;
  };

  useEffect(() => {
    if (isOpen && initialAmount) {
      setAmount(initialAmount);
    }
  }, [isOpen, initialAmount]);

  const getQuote = useCallback(async () => {
    if (!fromToken || !toToken || !amount || parseFloat(amount) <= 0) {
      setQuote(null);
      setQuoteError('');
      return;
    }

    if (fromToken.address === toToken.address) {
      setQuoteError('Cannot swap a token for itself');
      setQuote(null);
      return;
    }

    setQuoteLoading(true);
    setQuoteError('');
    setError('');

    try {
      const amountWei = dexService.toWei(amount, fromToken.decimals);
      console.log('[SWAP] toWei:', { amount, decimals: fromToken.decimals, amountWei });
      if (amountWei === "0") {
        setQuoteError('Amount is too small');
        setQuoteLoading(false);
        return;
      }
      
      console.log('[SWAP] Fetching quote:', { from: fromToken.symbol, to: toToken.symbol, amount, amountWei, chainId });
      
      const result = await dexService.getQuote(
        fromToken.address,
        toToken.address,
        amountWei,
        chainId
      );
      
      if (result.success) {
        setQuote(result);
        setQuoteError('');
        console.log('[SWAP] Quote received:', { dstAmount: result.dstAmount, gas: result.gas });
        
        if (fromToken.address !== NATIVE_TOKEN && walletReady) {
          try {
            const allowance = await dexService.checkAllowance(fromToken.address, chainId);
            if (allowance.success) {
              const allowanceValue = BigInt(allowance.allowance || '0');
              const amountValue = BigInt(amountWei);
              setNeedsApproval(allowanceValue < amountValue);
              console.log('[SWAP] Allowance check:', { allowance: allowance.allowance, needed: amountWei, needsApproval: allowanceValue < amountValue });
            } else {
              console.warn('[SWAP] Allowance check failed:', allowance.error);
              setNeedsApproval(false);
            }
          } catch (allowErr) {
            console.warn('[SWAP] Allowance check error:', allowErr.message);
            setNeedsApproval(false);
          }
        } else {
          setNeedsApproval(false);
        }
      } else {
        console.error('[SWAP] Quote failed:', result.error);
        const errStr = typeof result.error === 'string'
          ? result.error
          : (result.error?.message || result.error?.detail || JSON.stringify(result.error) || 'Failed to get quote');
        // User-friendly liquidity message
        const friendlyErr = /insufficient liquidity|502/i.test(errStr)
          ? 'Insufficient liquidity for this amount. Try a larger amount (min ~$1) or a different token pair.'
          : errStr;
        setQuoteError(friendlyErr);
        setQuote(null);
      }
    } catch (err) {
      console.error('[SWAP] Quote error:', err);
      const rawMsg = err.response?.data?.detail || err.response?.data?.error || err.response?.data?.message || err.message || 'Failed to get quote';
      const errorMsg = typeof rawMsg === 'string' ? rawMsg : (rawMsg?.message || rawMsg?.detail || JSON.stringify(rawMsg));
      setQuoteError(errorMsg);
      setQuote(null);
    } finally {
      setQuoteLoading(false);
    }
  }, [fromToken, toToken, amount, chainId, walletReady]);

  useEffect(() => {
    if (quoteTimerRef.current) {
      clearTimeout(quoteTimerRef.current);
    }
    
    if (amount && fromToken && toToken && parseFloat(amount) > 0) {
      quoteTimerRef.current = setTimeout(() => {
        getQuote();
      }, 600);
    } else {
      setQuote(null);
      setQuoteError('');
    }
    
    return () => {
      if (quoteTimerRef.current) {
        clearTimeout(quoteTimerRef.current);
      }
    };
  }, [amount, fromToken, toToken, getQuote]);

  const handleApprove = async () => {
    if (!walletProvider) {
      setError('Please connect your wallet first');
      return;
    }
    
    if (!walletReady || !signerValidated) {
      setError('Wallet not ready. Please try reconnecting.');
      return;
    }
    
    if (!fromToken) {
      setError('Please select a token');
      return;
    }
    
    if (isWrongNetwork) {
      try {
        setStatusMessage('Switching network...');
        await switchNetwork(chainId);
        setCurrentWalletChain(chainId);
        setStatusMessage('');
      } catch (err) {
        setError(`Please switch to ${chainOptions.find(c => c.id === chainId)?.name || 'the correct network'} in your wallet`);
        setStatusMessage('');
        return;
      }
    }
    
    setApproving(true);
    setError('');
    setStatusMessage('Requesting approval...');
    
    try {
      const approveData = await dexService.getApproveTransaction(
        fromToken.address,
        null,
        chainId
      );
      
      if (!approveData.success) {
        throw new Error(approveData.error || 'Failed to get approval data');
      }
      
      setStatusMessage('Please confirm in your wallet...');
      
      const tx = approveData.tx;
      const hash = await sendTransaction({
        to: tx.to,
        data: tx.data,
        value: tx.value || '0x0',
      }, chainId);
      
      setTxHash(hash);
      setSuccess('Token approved! Waiting for confirmation...');
      setStatusMessage('Waiting for confirmation...');
      
      await new Promise(resolve => setTimeout(resolve, 8000));
      
      const amountWei = dexService.toWei(amount, fromToken.decimals);
      const allowance = await dexService.checkAllowance(fromToken.address, chainId);
      if (allowance.success) {
        const allowanceValue = BigInt(allowance.allowance || '0');
        const amountValue = BigInt(amountWei);
        setNeedsApproval(allowanceValue < amountValue);
        if (allowanceValue >= amountValue) {
          setSuccess('Token approved successfully! You can now swap.');
        }
      }
      setStatusMessage('');
    } catch (err) {
      console.error('[SWAP] Approval failed:', err);
      setStatusMessage('');
      setError(formatSwapError(err));
    } finally {
      setApproving(false);
    }
  };

  const handleSwap = async () => {
    if (!fromToken || !toToken || !amount) {
      setError('Please fill in all swap details');
      return;
    }
    
    if (parseFloat(amount) <= 0) {
      setError('Amount must be greater than 0');
      return;
    }
    
    if (!walletProvider) {
      setError('Please connect your wallet first');
      return;
    }
    
    if (!walletReady || !signerValidated) {
      setError('Wallet not ready. Click "Authorize Wallet" first.');
      return;
    }
    
    if (isWrongNetwork) {
      try {
        setStatusMessage('Switching network...');
        await switchNetwork(chainId);
        setCurrentWalletChain(chainId);
        setStatusMessage('');
        
        const { chainId: verifiedChain } = await ensureWalletConnection();
        if (verifiedChain !== chainId) {
          setError(`Please switch to ${chainOptions.find(c => c.id === chainId)?.name} in your wallet`);
          setStatusMessage('');
          return;
        }
      } catch (err) {
        setError(`Please switch to ${chainOptions.find(c => c.id === chainId)?.name || 'the correct network'} in your wallet`);
        setStatusMessage('');
        return;
      }
    }
    
    if (needsApproval) {
      setError('Please approve the token first before swapping.');
      return;
    }
    
    setSwapping(true);
    setError('');
    setSuccess('');
    setStatusMessage('Preparing swap...');
    
    try {
      const amountWei = dexService.toWei(amount, fromToken.decimals);
      if (amountWei === "0") {
        throw new Error('Amount is too small to swap');
      }
      
      console.log('[SWAP] Executing swap:', { from: fromToken.symbol, to: toToken.symbol, amount, amountWei, slippage, chainId });
      
      setStatusMessage('Getting swap route...');
      const swapData = await dexService.getSwapTransaction(
        fromToken.address,
        toToken.address,
        amountWei,
        slippage,
        chainId
      );
      
      if (!swapData.success) {
        if (swapData.code === 'SWAP_PLAN_REQUIRED') {
          throw new Error('Swap execution requires an upgraded 1inch API plan. Quotes work but swap transactions need a premium key.');
        }
        if (swapData.code === 'NEEDS_APPROVAL') {
          setNeedsApproval(true);
          throw new Error('Token approval required. Please approve first.');
        }
        throw new Error(swapData.error || 'Failed to get swap data from 1inch');
      }
      
      if (!swapData.tx || !swapData.tx.to || !swapData.tx.data) {
        throw new Error('Invalid swap transaction data received');
      }
      
      setStatusMessage('Please confirm the transaction in your wallet...');
      
      const tx = swapData.tx;
      const hash = await sendTransaction({
        to: tx.to,
        data: tx.data,
        value: tx.value || '0x0',
        gas: tx.gas,
      }, chainId);
      
      setTxHash(hash);
      setSuccess('Swap executed successfully!');
      setStatusMessage('');
      console.log('[SWAP] Transaction sent:', hash);
      
      const toAmount = quote ? dexService.fromWei(quote.dstAmount, toToken.decimals) : 0;
      const isFromStablecoin = ['USDT', 'USDC', 'DAI', 'BUSD'].includes(fromToken.symbol);
      const isToStablecoin = ['USDT', 'USDC', 'DAI', 'BUSD'].includes(toToken.symbol);
      
      // Record transaction to history (all swaps)
      try {
        await dexService.recordTransaction({
          txHash: hash,
          fromToken: fromToken.symbol,
          toToken: toToken.symbol,
          fromAmount: parseFloat(amount),
          toAmount: toAmount,
          chainId: chainId,
        });
        console.log('[SWAP] Transaction recorded to history');
      } catch (recordErr) {
        console.warn('[SWAP] Failed to record transaction:', recordErr.message);
      }

      // Record to portfolio (only stablecoin → token buys)
      try {
        const authToken = localStorage.getItem('auth_token');
        if (authToken && isFromStablecoin && !isToStablecoin && toAmount > 0) {
          const usdtAmount = parseFloat(amount);
          const entryPrice = usdtAmount / toAmount;
          
          await dexService.recordDexSwap({
            symbol: toToken.symbol,
            usdtAmount: usdtAmount,
            quantity: toAmount,
            entryPrice: entryPrice,
            txHash: hash,
            chainId: chainId,
            strategy: 'manual',
            triggerReason: `Bought ${toToken.symbol} with ${amount} ${fromToken.symbol}`
          });
          console.log('[SWAP] DEX swap recorded to portfolio');
        }
      } catch (recordErr) {
        console.warn('[SWAP] Failed to record swap to portfolio:', recordErr.message);
      }
      
      if (onSwapComplete) {
        onSwapComplete(hash);
      }
      
      setTimeout(() => {
        onClose();
      }, 3000);
    } catch (err) {
      console.error('[SWAP] Swap failed:', err);
      setStatusMessage('');
      
      setError(formatSwapError(err));
    } finally {
      setSwapping(false);
    }
  };

  const handleSwitchNetwork = async () => {
    try {
      setStatusMessage('Switching network...');
      setError('');
      await switchNetwork(chainId);
      setCurrentWalletChain(chainId);
      setStatusMessage('');
      setSuccess(`Switched to ${chainOptions.find(c => c.id === chainId)?.name}`);
      setTimeout(() => setSuccess(''), 2000);
    } catch (err) {
      setStatusMessage('');
      setError(`Failed to switch network. Please switch to ${chainOptions.find(c => c.id === chainId)?.name} in your wallet.`);
    }
  };

  const switchTokens = () => {
    const temp = fromToken;
    setFromToken(toToken);
    setToToken(temp);
    setQuote(null);
    setQuoteError('');
  };

  // Build token list from dynamic 1inch data + any currently selected tokens
  const [tokenSearch, setTokenSearch] = useState('');
  const tokens = (() => {
    const list = [...dynamicTokens];
    [fromToken, toToken].forEach(t => {
      if (t && t.address && !list.find(lt => lt.address.toLowerCase() === t.address.toLowerCase())) {
        list.push(t);
      }
    });
    return list;
  })();
  const filteredTokens = tokenSearch
    ? tokens.filter(t => t.symbol.toLowerCase().includes(tokenSearch.toLowerCase()) || t.name?.toLowerCase().includes(tokenSearch.toLowerCase()))
    : tokens;
  
  const canSwap = chainId && walletReady && signerValidated && !swapping && !approving && quote && !needsApproval;

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm overflow-y-auto"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className="bg-gray-900 rounded-xl sm:rounded-2xl p-4 sm:p-6 w-full max-w-md border border-gray-700 shadow-2xl my-4"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between mb-4 sm:mb-6">
            <h2 className="text-lg sm:text-xl font-bold text-white">Swap Tokens</h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-400" />
            </button>
          </div>

          <div className="mb-3 sm:mb-4">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs sm:text-sm text-gray-400">Network</label>
              {contextChainId && chainOptions.find(c => c.id === contextChainId) && chainId !== contextChainId && (
                <button
                  onClick={() => {
                    setChainId(contextChainId);
                    setCurrentWalletChain(contextChainId);
                    setQuote(null);
                    setQuoteError('');
                    setFromToken(null);
                    setToToken(null);
                    setNeedsApproval(false);
                  }}
                  className="text-xs text-[#00FFD1] hover:underline flex items-center gap-1"
                >
                  <RefreshCw className="w-3 h-3" />
                  Use wallet network ({chainOptions.find(c => c.id === contextChainId)?.name})
                </button>
              )}
            </div>
            <select
              value={chainId}
              onChange={async (e) => {
                const newChainId = parseInt(e.target.value);
                setChainId(newChainId);
                setFromToken(null);
                setToToken(null);
                setQuote(null);
                setQuoteError('');
                setError('');
                setNeedsApproval(false);
                setTokenSearch('');

                if (walletProvider && switchNetwork && newChainId !== currentWalletChain) {
                  try {
                    setStatusMessage('Switching network...');
                    await switchNetwork(newChainId);
                    setCurrentWalletChain(newChainId);
                    setStatusMessage('');
                    setSuccess(`Switched to ${chainOptions.find(c => c.id === newChainId)?.name || 'network'}`);
                    setTimeout(() => setSuccess(''), 2000);
                  } catch (err) {
                    setStatusMessage('');
                    setError(`Please switch your wallet to ${chainOptions.find(c => c.id === newChainId)?.name || 'the selected network'}`);
                  }
                }
              }}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 sm:px-4 py-2.5 sm:py-3 text-sm sm:text-base text-white cursor-pointer hover:bg-gray-750"
            >
              {chainsLoading ? (
                <option>Loading chains...</option>
              ) : (
                chainOptions.map((chain) => (
                  <option key={chain.id} value={chain.id}>
                    {chain.name} {contextChainId === chain.id ? '✓ (wallet)' : ''}
                  </option>
                ))
              )}
            </select>
            {chainId && chainOptions.find(c => c.id === chainId) && (
              <p className="text-xs text-gray-500 mt-1">
                ⛽ Gas fee paid in {chainOptions.find(c => c.id === chainId)?.symbol} — make sure you have some in your wallet
              </p>
            )}
          </div>

          <div className="space-y-2 mb-3 sm:mb-4">
            <label className="text-xs sm:text-sm text-gray-400">From</label>
            <div className="bg-gray-800 rounded-xl p-3 sm:p-4 border border-gray-700">
              <div className="flex gap-2 sm:gap-4">
                <input
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0.0"
                  min="0"
                  step="any"
                  className="flex-1 bg-transparent text-xl sm:text-2xl text-white outline-none min-w-0 [&::-webkit-inner-spin-button]:appearance-none"
                />
                <select
                  value={fromToken?.address || ''}
                  onChange={(e) => {
                    const token = tokens.find(t => t.address === e.target.value);
                    setFromToken(token);
                    setQuote(null);
                    setQuoteError('');
                    setNeedsApproval(false);
                  }}
                  className="bg-gray-700 rounded-lg px-2 sm:px-3 py-2 text-sm sm:text-base text-white flex-shrink-0 max-w-[140px]"
                >
                  <option value="">{tokensLoading ? 'Loading...' : 'Select'}</option>
                  {filteredTokens.map((t) => (
                    <option key={t.address} value={t.address}>
                      {t.symbol}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="flex justify-center -my-2 z-10 relative">
            <button
              onClick={switchTokens}
              className="p-2 bg-gray-700 hover:bg-gray-600 rounded-full border-4 border-gray-900 transition-colors"
            >
              <ArrowDown className="w-5 h-5 text-white" />
            </button>
          </div>

          <div className="space-y-2 mb-3 sm:mb-4">
            <label className="text-xs sm:text-sm text-gray-400">To</label>
            <div className="bg-gray-800 rounded-xl p-3 sm:p-4 border border-gray-700">
              <div className="flex gap-2 sm:gap-4">
                <div className="flex-1 text-xl sm:text-2xl text-white min-w-0 truncate">
                  {quoteLoading ? (
                    <span className="text-gray-500 flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Loading...
                    </span>
                  ) : quote ? (
                    dexService.formatTokenAmount(quote.dstAmount, toToken?.decimals || 18, 6)
                  ) : (
                    <span className="text-gray-500">0.0</span>
                  )}
                </div>
                <select
                  value={toToken?.address || ''}
                  onChange={(e) => {
                    const token = tokens.find(t => t.address === e.target.value);
                    setToToken(token);
                    setQuote(null);
                    setQuoteError('');
                  }}
                  className="bg-gray-700 rounded-lg px-2 sm:px-3 py-2 text-sm sm:text-base text-white flex-shrink-0 max-w-[140px]"
                >
                  <option value="">{tokensLoading ? 'Loading...' : 'Select'}</option>
                  {filteredTokens.map((t) => (
                    <option key={t.address} value={t.address}>
                      {t.symbol}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="mb-3 sm:mb-4">
            <label className="text-xs sm:text-sm text-gray-400 mb-2 block">Slippage Tolerance</label>
            <div className="flex flex-wrap gap-2">
              {[0.5, 1.0, 2.0, 3.0].map((val) => (
                <button
                  key={val}
                  onClick={() => { setSlippage(val); setSlippageInput(String(val)); }}
                  className={`px-2.5 sm:px-3 py-1.5 sm:py-1 rounded-lg text-xs sm:text-sm ${
                    slippage === val
                      ? 'bg-[#00FFD1] text-black'
                      : 'bg-gray-700 text-white hover:bg-gray-600'
                  }`}
                >
                  {val}%
                </button>
              ))}
              <input
                type="number"
                value={slippageInput}
                onChange={(e) => {
                  const raw = e.target.value;
                  setSlippageInput(raw);
                  const parsed = parseFloat(raw);
                  if (!isNaN(parsed) && parsed >= 0.1 && parsed <= 50) {
                    setSlippage(parsed);
                  }
                }}
                onBlur={() => {
                  const parsed = parseFloat(slippageInput);
                  if (isNaN(parsed) || parsed < 0.1) {
                    setSlippage(0.5);
                    setSlippageInput('0.5');
                  } else if (parsed > 50) {
                    setSlippage(50);
                    setSlippageInput('50');
                  }
                }}
                className="w-14 sm:w-16 bg-gray-700 rounded-lg px-2 text-sm sm:text-base text-white text-center"
                step="0.1"
                min="0.1"
                max="50"
              />
            </div>
          </div>

          {slippage > 5 && (
            <div className="flex items-center gap-2 p-2 bg-yellow-900/30 border border-yellow-600 rounded-lg mb-3 text-yellow-400 text-xs">
              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
              <span>High slippage ({slippage}%). You may receive significantly fewer tokens.</span>
            </div>
          )}

          {quote && (
            <div className="bg-gray-800/50 rounded-lg p-2.5 sm:p-3 mb-3 sm:mb-4 text-xs sm:text-sm">
              <div className="flex justify-between text-gray-400">
                <span>Rate</span>
                <span className="text-right">
                  1 {fromToken?.symbol} = {(
                    dexService.fromWei(quote.dstAmount, toToken?.decimals || 18) /
                    parseFloat(amount || 1)
                  ).toFixed(6)} {toToken?.symbol}
                </span>
              </div>
              <div className="flex justify-between text-gray-400 mt-1">
                <span>Min. Received</span>
                <span className="text-right">
                  {(
                    dexService.fromWei(quote.dstAmount, toToken?.decimals || 18) *
                    (1 - slippage / 100)
                  ).toFixed(6)} {toToken?.symbol}
                </span>
              </div>
              <div className="flex justify-between text-gray-400 mt-1">
                <span>Slippage</span>
                <span>{slippage}%</span>
              </div>
              {quote.gas && (
                <div className="flex justify-between text-gray-400 mt-1">
                  <span>Est. Gas</span>
                  <span>{parseInt(quote.gas).toLocaleString()}</span>
                </div>
              )}
            </div>
          )}

          {quoteError && (
            <div className="flex items-start gap-2 p-2.5 sm:p-3 bg-orange-900/30 border border-orange-600 rounded-lg mb-3 sm:mb-4 text-orange-400">
              <Info className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <div className="text-xs sm:text-sm break-words overflow-hidden max-w-full">
                <span>{quoteError.length > 120 ? 'Failed to get quote. Please try again.' : quoteError}</span>
                <button 
                  onClick={getQuote} 
                  className="ml-2 underline hover:text-orange-300"
                >
                  Retry
                </button>
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-start gap-2 p-2.5 sm:p-3 bg-red-900/30 border border-red-600 rounded-lg mb-3 sm:mb-4 text-red-400">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span className="text-xs sm:text-sm break-words overflow-hidden max-w-full">{error}</span>
            </div>
          )}

          {success && (
            <div className="flex items-center gap-2 p-2.5 sm:p-3 bg-green-900/30 border border-green-600 rounded-lg mb-3 sm:mb-4 text-green-400">
              <Check className="w-4 h-4 flex-shrink-0" />
              <span className="text-xs sm:text-sm flex-1">{success}</span>
              {txHash && (
                <a
                  href={dexService.getExplorerUrl(chainId, txHash)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-shrink-0"
                >
                  <ExternalLink className="w-4 h-4" />
                </a>
              )}
            </div>
          )}

          {statusMessage && (
            <div className="flex items-center gap-2 p-2.5 sm:p-3 bg-blue-900/20 border border-blue-700/50 rounded-lg mb-3 sm:mb-4 text-blue-400">
              <Loader2 className="w-4 h-4 animate-spin flex-shrink-0" />
              <span className="text-xs sm:text-sm">{statusMessage}</span>
            </div>
          )}

          <div className="space-y-2 sm:space-y-3">
            {!walletProvider ? (
              <button
                onClick={connectWallet}
                className="w-full py-3 bg-gradient-to-r from-[#00FFD1] to-[#00D4A8] hover:from-[#00D4A8] hover:to-[#00FFD1] text-black font-semibold rounded-xl transition-all flex items-center justify-center gap-2"
              >
                <Wallet className="w-5 h-5" />
                Connect Wallet to Swap
              </button>
            ) : !walletReady || !signerValidated ? (
              <button
                onClick={initializeWallet}
                disabled={loading}
                className="w-full py-3 bg-gradient-to-r from-yellow-500 to-yellow-400 hover:from-yellow-400 hover:to-yellow-500 text-black font-semibold rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Authorizing Wallet...
                  </>
                ) : (
                  <>
                    <Wallet className="w-5 h-5" />
                    Authorize Wallet
                  </>
                )}
              </button>
            ) : isWrongNetwork ? (
              <button
                onClick={handleSwitchNetwork}
                className="w-full py-3 bg-gradient-to-r from-orange-500 to-orange-400 hover:from-orange-400 hover:to-orange-500 text-black font-semibold rounded-xl transition-all flex items-center justify-center gap-2"
              >
                <RefreshCw className="w-5 h-5" />
                Switch to {chainOptions.find(c => c.id === chainId)?.name}
              </button>
            ) : needsApproval ? (
              <button
                onClick={handleApprove}
                disabled={approving || !quote}
                className="w-full py-3 bg-gradient-to-r from-yellow-500 to-yellow-400 hover:from-yellow-400 hover:to-yellow-500 text-black font-semibold rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {approving ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Approving {fromToken?.symbol}...
                  </>
                ) : (
                  <>
                    <Check className="w-5 h-5" />
                    Approve {fromToken?.symbol} for Swap
                  </>
                )}
              </button>
            ) : (
              <button
                onClick={handleSwap}
                disabled={!canSwap}
                className="w-full py-3 bg-gradient-to-r from-[#00FFD1] to-[#00D4A8] hover:from-[#00D4A8] hover:to-[#00FFD1] text-black font-semibold rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {swapping ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Swapping...
                  </>
                ) : !fromToken || !toToken ? (
                  <>
                    <RefreshCw className="w-5 h-5" />
                    Select Tokens
                  </>
                ) : !amount || parseFloat(amount) <= 0 ? (
                  <>
                    <RefreshCw className="w-5 h-5" />
                    Enter Amount
                  </>
                ) : quoteLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Getting Quote...
                  </>
                ) : quoteError ? (
                  <>
                    <RefreshCw className="w-5 h-5" />
                    Retry Quote
                  </>
                ) : !quote ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Getting Quote...
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-5 h-5" />
                    Swap {fromToken?.symbol} → {toToken?.symbol}
                  </>
                )}
              </button>
            )}
          </div>

          <p className="text-xs text-gray-500 text-center mt-4">
            Powered by 1inch DEX Aggregator
          </p>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

export default SwapModal;
