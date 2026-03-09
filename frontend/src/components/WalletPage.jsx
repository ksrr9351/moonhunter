import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Wallet, RefreshCw, ExternalLink, Copy, Check, AlertTriangle, 
  ArrowUpRight, ArrowDownRight, Repeat, Loader2, Shield, Lock,
  CheckCircle2, Clock, TrendingUp, Sparkles
} from 'lucide-react';
import { useWalletAuth } from '../contexts/WalletAuthContext';
import { Contract, formatUnits, formatEther } from 'ethers';
import PremiumNavbar from './PremiumNavbar';
import InfoTooltip from './InfoTooltip';
import { SwapModal } from './SwapModal';
import { formatUSD } from '../utils/formatters';
import { useChains } from '../hooks/useChains';


const ERC20_ABI = [
  'function balanceOf(address) view returns (uint256)',
  'function decimals() view returns (uint8)',
  'function symbol() view returns (string)',
];

const WalletPage = () => {
  const { 
    walletAddress, 
    walletConnected, 
    signerReady, 
    currentChainId,
    getSigner,
    connectWallet,
    token
  } = useWalletAuth();

  const { chains, getChain } = useChains();
  const supportedChainIds = new Set(chains.map(c => c.id));
  const getChainName = (cid) => getChain(cid)?.name || `Chain ${cid}`;
  const getExplorer = (cid) => getChain(cid)?.explorer || null;

  const [usdtBalance, setUsdtBalance] = useState(null);
  const [stablecoinSymbol, setStablecoinSymbol] = useState(null); // actual symbol from backend (USDC or USDT)
  const [ethBalance, setEthBalance] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  const [transactions, setTransactions] = useState([]);
  const [txLoading, setTxLoading] = useState(false);
  const [dexAvailable, setDexAvailable] = useState(true);

  const [showSwapModal, setShowSwapModal] = useState(false);
  const [swapConfig, setSwapConfig] = useState({ from: 'ETH', to: 'USDT', action: 'swap' });
  const [detectedChainId, setDetectedChainId] = useState(null);

  const getStablecoin = (cid) => {
    // If backend told us the actual stablecoin (USDC/USDT), trust that over chain config
    if (stablecoinSymbol) {
      return stablecoinSymbol === 'USDC'
        ? { symbol: 'USDC', name: 'USD Coin' }
        : { symbol: 'USDT', name: 'Tether USD' };
    }
    const c = getChain(cid);
    if (!c) return { symbol: 'USDT', name: 'Tether USD' };
    if (c.usdt_address) return { symbol: 'USDT', name: 'Tether USD' };
    if (c.usdc_address) return { symbol: 'USDC', name: 'USD Coin' };
    return { symbol: 'USDT', name: 'Tether USD' };
  };
  const getUsdtConfig = (cid) => {
    const c = getChain(cid);
    if (!c || !c.usdt_address) return null;
    return { address: c.usdt_address, decimals: c.usdt_decimals || 6 };
  };

  const fetchBalances = useCallback(async (retryCount = 0) => {
    if (!walletAddress) {
      return;
    }

    setLoading(true);
    if (retryCount === 0) setError('');

    // Use detected/current chain, or fallback to 1 (Ethereum) so backend can auto-scan all chains
    const chainToQuery = detectedChainId || currentChainId || 1;
    console.log('[WALLET] fetchBalances called with chainId:', chainToQuery, '(currentChainId:', currentChainId, ', detectedChainId:', detectedChainId, ')');

    try {
      const response = await fetch(
        `${import.meta.env.VITE_BACKEND_URL || ''}/api/ai-engine/wallet-status?chain_id=${chainToQuery}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (response.ok) {
        const data = await response.json();
        console.log('[WALLET] Fetched balances from backend (chain_id=' + chainToQuery + ', detected_chain=' + data.chain_id + '):', data);
        setEthBalance(data.eth_balance?.toString() || '0');
        setUsdtBalance(data.available_usdt?.toString() || '0');
        if (data.tokens?.length > 0) {
          const stable = data.tokens[0]; // first token is always the selected stablecoin
          setStablecoinSymbol(stable.symbol);
        }
        if (data.chain_id) {
          if (data.chain_id !== currentChainId) {
            console.log('[WALLET] Backend detected balance on chain', data.chain_id, '(wallet reports:', currentChainId, ')');
          }
          setDetectedChainId(data.chain_id);
        }
        setError('');
        return;
      }
      
      if (signerReady) {
        const signer = await getSigner();
        if (signer) {
          const provider = signer.provider;
          if (provider) {
            const [ethBal, network] = await Promise.all([
              provider.getBalance(walletAddress),
              provider.getNetwork()
            ]);

            const signerChainId = Number(network.chainId);
            setEthBalance(formatEther(ethBal));
            setDetectedChainId(signerChainId);
            setError('');

            const usdtConfig = getUsdtConfig(signerChainId);
            if (usdtConfig) {
              const usdtContract = new Contract(usdtConfig.address, ERC20_ABI, provider);
              const usdtBal = await usdtContract.balanceOf(walletAddress);
              setUsdtBalance(formatUnits(usdtBal, usdtConfig.decimals));
            } else {
              setUsdtBalance('0');
            }

            if (!supportedChainIds.has(signerChainId)) {
              setError(`Unsupported network: ${getChainName(signerChainId)}. Please switch to a supported chain.`);
            }
            return;
          }
        }
      }
      
      if (retryCount < 3) {
        console.log(`[WALLET] Balance fetch failed, retrying in ${(retryCount + 1) * 500}ms... (attempt ${retryCount + 1}/3)`);
        setTimeout(() => fetchBalances(retryCount + 1), (retryCount + 1) * 500);
        return;
      }
      
      setError('Failed to fetch balances. Please try again.');
    } catch (err) {
      console.error('Error fetching balances:', err);
      const errorMsg = err.message || '';
      if (retryCount < 3) {
        console.log(`[WALLET] Retry ${retryCount + 1}/3...`);
        setTimeout(() => fetchBalances(retryCount + 1), (retryCount + 1) * 500);
        return;
      }
      if (!errorMsg.includes('connect()') && !errorMsg.includes('coalesce')) {
        setError(errorMsg || 'Failed to fetch balances. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }, [walletAddress, token, signerReady, getSigner, currentChainId, detectedChainId]);

  const fetchTransactions = useCallback(async () => {
    if (!walletAddress || !token) return;
    
    setTxLoading(true);
    try {
      const response = await fetch(
        `${import.meta.env.VITE_BACKEND_URL || ''}/api/dex/transactions?wallet=${walletAddress}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (response.ok) {
        const data = await response.json();
        setTransactions(data.transactions || []);
      }
    } catch (err) {
      console.error('Error fetching transactions:', err);
    } finally {
      setTxLoading(false);
    }
  }, [walletAddress, token]);

  const checkDexAvailability = useCallback(async () => {
    try {
      const response = await fetch(
        `${import.meta.env.VITE_BACKEND_URL || ''}/api/trading-bot/status`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (response.ok) {
        const data = await response.json();
        setDexAvailable(data.dex_available ?? true);
      }
    } catch (err) {
      console.error('Error checking DEX availability:', err);
    }
  }, [token]);

  useEffect(() => {
    if (walletConnected && walletAddress && token) {
      fetchBalances();
      fetchTransactions();
    }
  }, [walletConnected, walletAddress, token]);

  // Re-fetch when chain is detected (after wallet provider initializes)
  useEffect(() => {
    if (walletConnected && walletAddress && token && currentChainId) {
      fetchBalances();
    }
  }, [currentChainId]);

  useEffect(() => {
    if (token) {
      checkDexAvailability();
    }
  }, [token, checkDexAvailability]);

  const copyAddress = () => {
    navigator.clipboard.writeText(walletAddress);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const openSwap = (action, fromToken = 'ETH', toToken = 'USDT') => {
    if (!dexAvailable) {
      setError('DEX trading is currently unavailable. Please try again later.');
      return;
    }
    setSwapConfig({ action, from: fromToken, to: toToken });
    setShowSwapModal(true);
  };

  const handleSwapComplete = async () => {
    setShowSwapModal(false);
    await fetchBalances();
    await fetchTransactions();
  };

  const shortenAddress = (addr) => {
    if (!addr) return '';
    return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
  };

  const displayChainId = detectedChainId || currentChainId;
  const isWrongNetwork = currentChainId && supportedChainIds.size > 0 && !supportedChainIds.has(currentChainId);

  if (!walletConnected) {
    return (
      <div className="premium-bg min-h-screen">
        <PremiumNavbar />
        <div className="container mx-auto px-4 py-16 sm:py-24">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="max-w-md mx-auto text-center"
          >
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-[#00FFD1]/20 via-emerald-500/10 to-[#00FFD1]/20 blur-3xl opacity-30"></div>
              <div className="relative bg-[#0d0f12]/90 backdrop-blur-xl border border-gray-800/50 rounded-3xl p-8 sm:p-12 shadow-2xl">
                <div className="w-20 h-20 mx-auto mb-8 rounded-2xl bg-gradient-to-br from-[#00FFD1] to-emerald-600 flex items-center justify-center shadow-lg shadow-[#00FFD1]/20">
                  <Wallet className="w-10 h-10 text-black" />
                </div>
                <h2 className="text-2xl sm:text-3xl font-bold text-white mb-3">Secure Wallet Access</h2>
                <p className="text-gray-400 mb-8 leading-relaxed">
                  Connect your wallet to see your balances and start trading
                </p>
                
                <button
                  onClick={connectWallet}
                  className="w-full py-4 px-6 bg-gradient-to-r from-[#00FFD1] to-emerald-500 text-black font-semibold rounded-xl hover:shadow-lg hover:shadow-[#00FFD1]/25 transition-all duration-300 transform hover:scale-[1.02]"
                >
                  Connect Wallet
                </button>
                
                <div className="mt-8 pt-6 border-t border-gray-800/50">
                  <div className="flex items-center justify-center gap-6 text-xs text-gray-500">
                    <div className="flex items-center gap-1.5">
                      <Shield className="w-3.5 h-3.5 text-[#00FFD1]" />
                      <span>Non-custodial</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Lock className="w-3.5 h-3.5 text-[#00FFD1]" />
                      <span>Encrypted</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-[#00FFD1]" />
                      <span>Audited</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    );
  }

  return (
    <div className="premium-bg min-h-screen">
      <PremiumNavbar />

      <div className="container mx-auto px-3 sm:px-4 lg:px-6 py-4 sm:py-6 lg:py-8">
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6 sm:mb-8"
        >
          <div className="flex items-center gap-3 sm:gap-4">
            <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-xl sm:rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center flex-shrink-0">
              <Wallet className="w-6 h-6 sm:w-8 sm:h-8 text-white" />
            </div>
            <div className="min-w-0">
              <h1 className="text-2xl sm:text-3xl font-bold text-white truncate">Wallet</h1>
              <p className="text-gray-400 text-sm sm:text-base">Your crypto wallet — view balances, swap tokens, and track transactions</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#00FFD1]/10 border border-[#00FFD1]/20 rounded-full">
              <div className="w-2 h-2 rounded-full bg-[#00FFD1] animate-pulse"></div>
              <span className="text-[#00FFD1] text-xs font-medium">Live</span>
            </div>
          </div>
        </motion.div>

        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mb-6 p-4 rounded-xl bg-red-500/5 border border-red-500/20 flex items-start gap-3"
          >
            <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <span className="text-red-400 text-sm">{error}</span>
          </motion.div>
        )}

        {isWrongNetwork && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 p-4 rounded-xl bg-amber-500/5 border border-amber-500/20 flex items-start gap-3"
          >
            <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <span className="text-amber-400 text-sm">
              Unsupported network: {getChainName(displayChainId)}. Please switch to a supported chain.
            </span>
          </motion.div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="lg:col-span-2"
          >
            <div className="bg-[#0d0f12]/80 backdrop-blur-sm border border-gray-800/50 rounded-2xl p-6 sm:p-8">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-8">
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-gray-500 text-sm">Connected Address</span>
                    <div className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                      supportedChainIds.has(displayChainId)
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    }`}>
                      {getChainName(displayChainId)}
                    </div>
                    <InfoTooltip text="The blockchain network your wallet is connected to." />
                  </div>
                  <div className="flex items-center gap-3">
                    <code className="text-white font-mono text-lg sm:text-xl tracking-wide">{shortenAddress(walletAddress)}</code>
                    <button
                      onClick={copyAddress}
                      className="p-2 rounded-lg bg-gray-800/50 hover:bg-gray-700/50 transition-colors group"
                      title="Copy wallet address"
                    >
                      {copied ? (
                        <Check className="w-4 h-4 text-[#00FFD1]" />
                      ) : (
                        <Copy className="w-4 h-4 text-gray-400 group-hover:text-white transition-colors" />
                      )}
                    </button>
                    {getExplorer(displayChainId) && (
                      <a
                        href={`${getExplorer(displayChainId)}/address/${walletAddress}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2 rounded-lg bg-gray-800/50 hover:bg-gray-700/50 transition-colors group"
                        title={`View on explorer`}
                      >
                        <ExternalLink className="w-4 h-4 text-gray-400 group-hover:text-white transition-colors" />
                      </a>
                    )}
                  </div>
                </div>
                <button
                  onClick={fetchBalances}
                  disabled={loading}
                  className="flex items-center gap-2 px-4 py-2 bg-gray-800/50 hover:bg-gray-700/50 border border-gray-700/50 rounded-xl transition-all disabled:opacity-50"
                >
                  <RefreshCw className={`w-4 h-4 text-gray-400 ${loading ? 'animate-spin' : ''}`} />
                  <span className="text-gray-400 text-sm">Refresh</span>
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#00FFD1]/5 to-transparent border border-[#00FFD1]/10 p-6">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-[#00FFD1]/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2"></div>
                  <div className="relative">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-[#00FFD1]/10 flex items-center justify-center">
                          <span className="text-[#00FFD1] font-bold text-sm">$</span>
                        </div>
                        <span className="text-gray-400 font-medium">{getStablecoin(displayChainId).symbol}</span>
                        <InfoTooltip text={`${getStablecoin(displayChainId).symbol} is a stablecoin pegged to the US dollar. 1 ${getStablecoin(displayChainId).symbol} ≈ $1.`} />
                      </div>
                      <span className="text-[10px] px-2 py-1 rounded-full bg-[#00FFD1]/10 text-[#00FFD1] font-medium">Primary</span>
                    </div>
                    <div className="text-3xl sm:text-4xl font-bold text-white mb-1">
                      {loading ? (
                        <Loader2 className="w-8 h-8 animate-spin text-[#00FFD1]" />
                      ) : usdtBalance !== null ? (
                        formatUSD(parseFloat(usdtBalance))
                      ) : (
                        <span className="text-gray-600">--</span>
                      )}
                    </div>
                    <p className="text-gray-500 text-xs">{getStablecoin(displayChainId).name}</p>
                  </div>
                </div>

                <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-blue-500/5 to-transparent border border-blue-500/10 p-6">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2"></div>
                  <div className="relative">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
                          <span className="text-blue-400 font-bold text-sm">E</span>
                        </div>
                        <span className="text-gray-400 font-medium">ETH</span>
                        <InfoTooltip text="Ethereum (ETH) is the main currency on the Ethereum network. You need a small amount of ETH to pay for transaction fees (gas)." />
                      </div>
                      <span className="text-[10px] px-2 py-1 rounded-full bg-blue-500/10 text-blue-400 font-medium">Gas</span>
                    </div>
                    <div className="text-3xl sm:text-4xl font-bold text-white mb-1">
                      {loading ? (
                        <Loader2 className="w-8 h-8 animate-spin text-blue-400" />
                      ) : ethBalance !== null ? (
                        `${parseFloat(ethBalance).toFixed(4)}`
                      ) : (
                        <span className="text-gray-600">--</span>
                      )}
                    </div>
                    <p className="text-gray-500 text-xs">Ethereum</p>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <div className="bg-[#0d0f12]/80 backdrop-blur-sm border border-gray-800/50 rounded-2xl p-6 h-full">
              <div className="flex items-center gap-2 mb-4">
                <h3 className="text-white font-semibold">Quick Actions</h3>
                <InfoTooltip text="Swap lets you exchange one cryptocurrency for another directly from your wallet." />
              </div>
              <div className="space-y-3">
                <button
                  onClick={() => openSwap('buy', 'USDT', 'ETH')}
                  disabled={!dexAvailable || isWrongNetwork}
                  className="w-full p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20 hover:bg-emerald-500/10 hover:border-emerald-500/30 transition-all group disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center group-hover:scale-105 transition-transform">
                      <ArrowDownRight className="w-5 h-5 text-emerald-400" />
                    </div>
                    <div className="text-left">
                      <p className="text-white font-medium">Buy</p>
                      <p className="text-gray-500 text-xs">Purchase tokens</p>
                    </div>
                  </div>
                </button>

                <button
                  onClick={() => openSwap('sell', 'ETH', 'USDT')}
                  disabled={!dexAvailable || isWrongNetwork}
                  className="w-full p-4 rounded-xl bg-rose-500/5 border border-rose-500/20 hover:bg-rose-500/10 hover:border-rose-500/30 transition-all group disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-rose-500/10 flex items-center justify-center group-hover:scale-105 transition-transform">
                      <ArrowUpRight className="w-5 h-5 text-rose-400" />
                    </div>
                    <div className="text-left">
                      <p className="text-white font-medium">Sell</p>
                      <p className="text-gray-500 text-xs">Convert to USDT</p>
                    </div>
                  </div>
                </button>

                <button
                  onClick={() => openSwap('swap', 'ETH', 'USDT')}
                  disabled={!dexAvailable || isWrongNetwork}
                  className="w-full p-4 rounded-xl bg-[#00FFD1]/5 border border-[#00FFD1]/20 hover:bg-[#00FFD1]/10 hover:border-[#00FFD1]/30 transition-all group disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-[#00FFD1]/10 flex items-center justify-center group-hover:scale-105 transition-transform">
                      <Repeat className="w-5 h-5 text-[#00FFD1]" />
                    </div>
                    <div className="text-left">
                      <p className="text-white font-medium">Swap</p>
                      <p className="text-gray-500 text-xs">Exchange via 1inch</p>
                    </div>
                  </div>
                </button>
              </div>

              <div className="mt-6 pt-4 border-t border-gray-800/50">
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <Shield className="w-3.5 h-3.5 text-[#00FFD1]" />
                  <span>Powered by 1inch DEX Aggregator</span>
                </div>
              </div>
            </div>
          </motion.div>
        </div>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <div className="bg-[#0d0f12]/80 backdrop-blur-sm border border-gray-800/50 rounded-2xl">
            <div className="flex items-center justify-between p-6 border-b border-gray-800/50">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gray-800/50 flex items-center justify-center">
                  <Clock className="w-5 h-5 text-gray-400" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-white font-semibold">Transaction History</h3>
                    <InfoTooltip text="A record of all your crypto trades, swaps, deposits, and withdrawals." />
                  </div>
                  <p className="text-gray-500 text-xs">Your recent DEX trades</p>
                </div>
              </div>
              <button
                onClick={fetchTransactions}
                disabled={txLoading}
                className="p-2 rounded-lg hover:bg-gray-800/50 transition-colors"
              >
                <RefreshCw className={`w-4 h-4 text-gray-500 ${txLoading ? 'animate-spin' : ''}`} />
              </button>
            </div>

            <div className="p-6">
              {txLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-6 h-6 text-[#00FFD1] animate-spin" />
                </div>
              ) : transactions.length > 0 ? (
                <div className="space-y-3">
                  {transactions.map((tx, idx) => (
                    <div 
                      key={tx.hash || idx} 
                      className="flex items-center justify-between p-4 rounded-xl bg-gray-800/20 border border-gray-800/30 hover:border-gray-700/50 transition-colors"
                    >
                      <div className="flex items-center gap-4">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                          tx.action === 'buy' ? 'bg-emerald-500/10' :
                          tx.action === 'sell' ? 'bg-rose-500/10' : 'bg-[#00FFD1]/10'
                        }`}>
                          {tx.action === 'buy' ? (
                            <ArrowDownRight className="w-5 h-5 text-emerald-400" />
                          ) : tx.action === 'sell' ? (
                            <ArrowUpRight className="w-5 h-5 text-rose-400" />
                          ) : (
                            <Repeat className="w-5 h-5 text-[#00FFD1]" />
                          )}
                        </div>
                        <div>
                          <p className="text-white font-medium capitalize">{tx.action || 'Swap'}</p>
                          <p className="text-gray-500 text-xs">{tx.token_symbol || tx.symbol}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-white font-medium">{formatUSD(tx.amount_usdt || tx.amount)}</p>
                        <div className="flex items-center justify-end gap-2 mt-1">
                          <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                            tx.status === 'confirmed' ? 'bg-emerald-500/10 text-emerald-400' :
                            tx.status === 'pending' ? 'bg-amber-500/10 text-amber-400' :
                            'bg-rose-500/10 text-rose-400'
                          }`}>
                            {tx.status || 'confirmed'}
                          </span>
                          {tx.hash && getExplorer(displayChainId) && (
                            <a
                              href={`${getExplorer(displayChainId)}/tx/${tx.hash}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-gray-500 hover:text-[#00FFD1] transition-colors"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gray-800/30 flex items-center justify-center">
                    <Sparkles className="w-7 h-7 text-gray-600" />
                  </div>
                  <p className="text-gray-400 font-medium mb-1">No transactions yet</p>
                  <p className="text-gray-600 text-sm">Your DEX trades will appear here</p>
                </div>
              )}
            </div>
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="mt-8 flex flex-wrap items-center justify-center gap-6 text-xs text-gray-600"
        >
          <div className="flex items-center gap-1.5">
            <Shield className="w-3.5 h-3.5" />
            <span>Non-custodial</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5" />
            <span>Your keys, your crypto</span>
          </div>
          <div className="flex items-center gap-1.5">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Best rates via 1inch</span>
          </div>
        </motion.div>
      </div>

      <AnimatePresence>
        {showSwapModal && (
          <SwapModal
            isOpen={showSwapModal}
            onClose={() => setShowSwapModal(false)}
            initialFromToken={swapConfig.from}
            initialToToken={swapConfig.to}
            initialChainId={detectedChainId || currentChainId}
            onSwapComplete={handleSwapComplete}
          />
        )}
      </AnimatePresence>
    </div>
  );
};

export default WalletPage;
