import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useWalletAuth } from '../contexts/WalletAuthContext';
import {
  TrendingDown, Clock, Shield, AlertTriangle, ChevronDown, ChevronUp,
  ExternalLink, Download, Target, DollarSign, Wallet, RefreshCw,
  Zap, X, Check, Loader2, TrendingUp, BarChart2, Layers,
  FileText, FileSpreadsheet, Activity, ArrowDownCircle
} from 'lucide-react';
import PremiumNavbar from './PremiumNavbar';
import { SwapModal } from './SwapModal';
import { investService } from '../services/investService';
import { isContractDeployed, estimateFee, buyToken as scBuyToken, sellToken as scSellToken } from '../services/contractService';
import { useChains } from '../hooks/useChains';

const API_URL = import.meta.env.VITE_BACKEND_URL || '';

const formatUSD = (val) => {
  if (val === null || val === undefined) return '$0.00';
  const num = Number(val);
  if (num === 0 || isNaN(num)) return '$0.00';
  if (Math.abs(num) >= 1) return `$${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  if (Math.abs(num) >= 0.01) return `$${num.toFixed(4)}`;
  return `$${num.toFixed(6)}`;
};

const formatCompact = (val) => {
  const num = Number(val || 0);
  if (num === 0) return '—';
  if (num >= 1e9) return `$${(num / 1e9).toFixed(1)}B`;
  if (num >= 1e6) return `$${(num / 1e6).toFixed(1)}M`;
  if (num >= 1e3) return `$${(num / 1e3).toFixed(0)}K`;
  return `$${num.toFixed(0)}`;
};

const formatPct = (val) => {
  const num = Number(val || 0);
  const sign = num >= 0 ? '+' : '';
  return `${sign}${num.toFixed(2)}%`;
};

function CountdownTimer({ expiresAt, remainingSeconds: initialRemaining, onExpire }) {
  const [remaining, setRemaining] = useState(initialRemaining || 0);
  const firedRef = useRef(false);

  useEffect(() => {
    firedRef.current = false;
    if (expiresAt) {
      const expiry = new Date(expiresAt).getTime();
      const calc = () => Math.max(0, Math.floor((expiry - Date.now()) / 1000));
      setRemaining(calc());
      const interval = setInterval(() => {
        const val = calc();
        setRemaining(val);
        if (val <= 0) {
          clearInterval(interval);
          if (onExpire && !firedRef.current) {
            firedRef.current = true;
            onExpire();
          }
        }
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [expiresAt, onExpire]);

  if (remaining <= 0) return null;

  const mins = Math.floor(remaining / 60);
  const secs = remaining % 60;
  const isUrgent = remaining < 600;

  return (
    <span className={`text-xs font-mono font-medium ${isUrgent ? 'text-red-400 animate-pulse' : 'text-yellow-400'}`}>
      <Clock className="inline w-3 h-3 mr-1" />
      {mins}m {secs.toString().padStart(2, '0')}s
    </span>
  );
}

function RiskBadge({ level }) {
  const colors = {
    Low: 'bg-green-500/20 text-green-400 border-green-500/30',
    Moderate: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    High: 'bg-red-500/20 text-red-400 border-red-500/30',
  };
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded border ${colors[level] || colors.Moderate}`}>
      {level}
    </span>
  );
}

function ChainBadge({ chainId, chains }) {
  const chain = chains.find(c => c.id === chainId);
  if (!chain) return null;
  return (
    <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 border border-white/10 inline-flex items-center gap-1" style={{ color: chain.color }}>
      <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ backgroundColor: chain.color }}></span>
      {chain.symbol || chain.name}
    </span>
  );
}

function BuyModal({ opportunity, onClose, token, onSuccess }) {
  const { walletAddress, sendTransaction, switchNetwork, currentChainId } = useWalletAuth();
  const { chains: allChains, getChain } = useChains();
  const getExplorerTx = (cid) => {
    const c = getChain(cid);
    return c ? `${c.explorer}${c.explorer_tx_path || '/tx/'}` : '';
  };
  const [amount, setAmount] = useState('');
  const [chainId, setChainId] = useState(allChains[0]?.id || null);
  const [enableSL, setEnableSL] = useState(true);
  const [enableTP, setEnableTP] = useState(true);
  const [slPercent, setSlPercent] = useState('10');
  const [tpPercent, setTpPercent] = useState('15');
  const [status, setStatus] = useState('idle');
  const [txHash, setTxHash] = useState('');
  const [error, setError] = useState('');
  const [showSwapModal, setShowSwapModal] = useState(false);
  const pendingSlTpRef = useRef({ enableSL: true, enableTP: true, slPercent: '10', tpPercent: '15' });

  const price = opportunity?.current_price || 0;
  const numAmount = parseFloat(amount) || 0;
  const fee = estimateFee(numAmount);
  const estimatedTokens = price > 0 ? (numAmount - fee) / price : 0;
  const scDeployed = isContractDeployed(chainId);

  const recordPosition = async (hash) => {
    setTxHash(hash);
    setStatus('recording');

    await investService.recordBuy(token, {
      symbol: opportunity.symbol,
      entry_price: price,
      quantity: estimatedTokens,
      tx_hash: hash,
      chain_id: chainId,
      fee_amount: scDeployed ? fee : 0,
      strategy: 'dump_buy',
      trigger_reason: `Dump opportunity: ${opportunity.dump_percentage?.toFixed(1)}% drop`,
    });

    const { enableSL: sl, enableTP: tp, slPercent: slP, tpPercent: tpP } = pendingSlTpRef.current;
    if (sl || tp) {
      const positions = await investService.getPositions(token);
      const latest = positions.positions?.find(p => p.symbol === opportunity.symbol && p.status === 'active');
      if (latest) {
        await investService.setTriggers(token, latest.id, {
          stop_loss_percent: sl ? parseFloat(slP) : 10,
          take_profit_percent: tp ? parseFloat(tpP) : 15,
          enable_stop_loss: sl,
          enable_take_profit: tp,
        });
      }
    }

    setStatus('success');
    setTimeout(() => onSuccess?.(), 2000);
  };

  const handleSwapComplete = async (swapResult) => {
    setShowSwapModal(false);
    try {
      const hash = typeof swapResult === 'string' ? swapResult : (swapResult?.hash || swapResult?.txHash || '');
      if (!hash) {
        setError('Swap completed but no transaction hash received');
        return;
      }
      await recordPosition(hash);
    } catch (err) {
      setError(err.message || 'Failed to record position');
      setStatus('idle');
    }
  };

  const handleBuy = async () => {
    if (!numAmount || numAmount < 10) {
      setError('Minimum buy amount is 10 USDT');
      return;
    }
    setError('');
    pendingSlTpRef.current = { enableSL, enableTP, slPercent, tpPercent };

    if (scDeployed) {
      setStatus('pending');
      try {
        if (currentChainId !== chainId) {
          setStatus('switching');
          await switchNetwork(chainId);
        }
        setStatus('confirming');
        const result = await scBuyToken(opportunity.symbol, numAmount, 0, chainId, 1);
        await recordPosition(result.hash);
      } catch (err) {
        setError(err.message || 'Transaction failed');
        setStatus('idle');
      }
    } else {
      setShowSwapModal(true);
    }
  };

  const supportedChains = opportunity.supported_chains?.length > 0
    ? allChains.filter(c => c.id && opportunity.supported_chains.includes(c.id))
    : allChains.filter(c => c.id);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-[#1a1a2e] border border-white/10 rounded-2xl w-full max-w-md p-6 relative max-h-[90vh] overflow-y-auto">
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-white">
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          {opportunity.logo && <img src={opportunity.logo} alt="" className="w-10 h-10 rounded-full" />}
          <div>
            <h3 className="text-white font-bold text-lg">{opportunity.name}</h3>
            <span className="text-gray-400 text-sm">{opportunity.symbol}</span>
            <span className="ml-2 text-red-400 text-sm font-medium">{opportunity.dump_percentage?.toFixed(2)}%</span>
          </div>
        </div>

        <div className="bg-white/5 rounded-lg p-3 mb-4 flex justify-between text-sm">
          <div><span className="text-gray-400">Price</span><div className="text-white font-medium">{formatUSD(price)}</div></div>
          <div className="text-right"><span className="text-gray-400">Expires</span><div><CountdownTimer expiresAt={opportunity.expires_at} remainingSeconds={opportunity.remaining_seconds} /></div></div>
        </div>

        <div className="mb-4">
          <label className="text-gray-400 text-sm mb-1 block">Amount (USDT)</label>
          <input
            type="number" value={amount} onChange={e => setAmount(e.target.value)}
            placeholder="Enter USDT amount" min="10"
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:border-[#00FFD1]/50 transition-colors"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1.5">
            <span>Est. tokens: {estimatedTokens.toFixed(6)} {opportunity.symbol}</span>
            <span>Fee: {formatUSD(fee)} (2%)</span>
          </div>
        </div>

        <div className="mb-4">
          <label className="text-gray-400 text-sm mb-1.5 block">Chain</label>
          <div className="flex gap-2 flex-wrap">
            {supportedChains.map(c => (
              <button key={c.id} onClick={() => setChainId(c.id)}
                className={`text-xs px-3 py-1.5 rounded-lg border transition-all flex items-center gap-1.5 ${chainId === c.id ? 'border-[#00FFD1]/50 bg-[#00FFD1]/10 text-[#00FFD1]' : 'border-white/10 text-gray-400 hover:border-white/20'}`}>
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: c.color }}></span>
                {c.name}
              </button>
            ))}
          </div>
        </div>

        <div className="mb-4 bg-white/5 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-300 text-sm font-medium flex items-center gap-1.5">
              <Target className="w-3.5 h-3.5 text-yellow-400" />
              Stop-Loss / Take-Profit
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="flex items-center gap-2 text-xs text-gray-400 mb-1">
                <input type="checkbox" checked={enableSL} onChange={e => setEnableSL(e.target.checked)} className="rounded accent-red-500" />
                Stop-Loss
              </label>
              <div className="flex items-center gap-1">
                <input type="number" value={slPercent} onChange={e => setSlPercent(e.target.value)}
                  disabled={!enableSL} min="1" max="50"
                  className="w-full bg-white/5 border border-white/10 rounded px-2 py-1 text-white text-sm disabled:opacity-40 focus:outline-none focus:border-red-500/50" />
                <span className="text-gray-400 text-xs">%</span>
              </div>
              {enableSL && price > 0 && <span className="text-red-400 text-[10px]">Sells at {formatUSD(price * (1 - parseFloat(slPercent || 10) / 100))}</span>}
            </div>
            <div>
              <label className="flex items-center gap-2 text-xs text-gray-400 mb-1">
                <input type="checkbox" checked={enableTP} onChange={e => setEnableTP(e.target.checked)} className="rounded accent-green-500" />
                Take-Profit
              </label>
              <div className="flex items-center gap-1">
                <input type="number" value={tpPercent} onChange={e => setTpPercent(e.target.value)}
                  disabled={!enableTP} min="1" max="200"
                  className="w-full bg-white/5 border border-white/10 rounded px-2 py-1 text-white text-sm disabled:opacity-40 focus:outline-none focus:border-green-500/50" />
                <span className="text-gray-400 text-xs">%</span>
              </div>
              {enableTP && price > 0 && <span className="text-green-400 text-[10px]">Sells at {formatUSD(price * (1 + parseFloat(tpPercent || 15) / 100))}</span>}
            </div>
          </div>
        </div>

        <div className="bg-yellow-500/5 border border-yellow-500/20 rounded-lg p-2.5 mb-4 flex items-center gap-2 text-xs">
          <DollarSign className="w-4 h-4 text-yellow-400 flex-shrink-0" />
          <span className="text-yellow-200">Moon Hunters Fee: 2% ({formatUSD(fee)})</span>
        </div>

        {error && <div className="text-red-400 text-sm mb-3 bg-red-500/10 rounded-lg p-2.5 border border-red-500/20">{error}</div>}

        <button onClick={handleBuy} disabled={status !== 'idle' || !numAmount || !chainId}
          className="w-full py-3 rounded-xl font-bold text-sm transition-all disabled:opacity-50 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white shadow-lg shadow-green-900/20">
          {status === 'idle' && 'Confirm Buy'}
          {status === 'pending' && <><Loader2 className="inline w-4 h-4 mr-2 animate-spin" />Preparing...</>}
          {status === 'switching' && <><Loader2 className="inline w-4 h-4 mr-2 animate-spin" />Switching Network...</>}
          {status === 'confirming' && <><Loader2 className="inline w-4 h-4 mr-2 animate-spin" />Confirm in Wallet...</>}
          {status === 'recording' && <><Loader2 className="inline w-4 h-4 mr-2 animate-spin" />Recording...</>}
          {status === 'success' && <><Check className="inline w-4 h-4 mr-2" />Buy Successful!</>}
        </button>

        {txHash && (
          <a href={`${getExplorerTx(chainId)}${txHash}`} target="_blank" rel="noopener noreferrer"
            className="flex items-center justify-center gap-1 text-xs text-blue-400 mt-2 hover:text-blue-300">
            View Transaction <ExternalLink className="w-3 h-3" />
          </a>
        )}

        {!scDeployed && (
          <p className="text-gray-500 text-[10px] mt-2 text-center">
            Buy executes via 1inch DEX swap. SC fee proxy coming soon.
          </p>
        )}
      </div>

      {showSwapModal && (
        <SwapModal
          isOpen={showSwapModal}
          onClose={() => setShowSwapModal(false)}
          initialFromToken="USDT"
          initialToToken={opportunity.contract_address ? { symbol: opportunity.symbol, address: opportunity.contract_address, decimals: 18, name: opportunity.name } : opportunity.symbol}
          initialAmount={amount}
          initialChainId={currentChainId}
          onSwapComplete={handleSwapComplete}
        />
      )}
    </div>
  );
}

function SellModal({ position, onClose, token, onSuccess }) {
  const { walletAddress, switchNetwork, currentChainId } = useWalletAuth();
  const { getChain } = useChains();
  const getExplorerTx = (cid) => {
    const c = getChain(cid);
    return c ? `${c.explorer}${c.explorer_tx_path || '/tx/'}` : '';
  };
  const [status, setStatus] = useState('idle');
  const [txHash, setTxHash] = useState('');
  const [error, setError] = useState('');
  const [showSwapModal, setShowSwapModal] = useState(false);

  const price = position?.current_price || 0;
  const pnl = position?.unrealized_pnl || 0;
  const pnlPct = position?.pnl_percent || 0;
  const isProfit = pnl >= 0;
  const chainId = position?.chain_id || null;
  const scDeployed = isContractDeployed(chainId);
  const currentValue = position?.current_value || 0;

  const recordSell = async (hash) => {
    setTxHash(hash);
    setStatus('recording');
    try {
      await investService.recordSell(token, {
        position_id: position.id,
        exit_price: price,
        exit_quantity: position.quantity || 0,
        tx_hash: hash,
        reason: 'manual_sell',
      });
      setStatus('success');
      setTimeout(() => onSuccess?.(), 2000);
    } catch (err) {
      setError(err.message || 'Failed to record sell');
      setStatus('idle');
    }
  };

  const handleSwapComplete = async (swapResult) => {
    setShowSwapModal(false);
    try {
      const hash = typeof swapResult === 'string' ? swapResult : (swapResult?.hash || swapResult?.txHash || '');
      if (!hash) {
        setError('Swap completed but no transaction hash received');
        return;
      }
      await recordSell(hash);
    } catch (err) {
      setError(err.message || 'Failed to record sell');
      setStatus('idle');
    }
  };

  const handleSell = async () => {
    setError('');
    if (scDeployed) {
      setStatus('pending');
      try {
        if (currentChainId !== chainId) {
          setStatus('switching');
          await switchNetwork(chainId);
        }
        setStatus('confirming');
        const result = await scSellToken(position.symbol, position.quantity, 0, chainId, 1);
        await recordSell(result.hash);
      } catch (err) {
        setError(err.message || 'Sell transaction failed');
        setStatus('idle');
      }
    } else {
      setShowSwapModal(true);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-[#1a1a2e] border border-white/10 rounded-2xl w-full max-w-sm p-6 relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-white">
          <X className="w-5 h-5" />
        </button>

        <h3 className="text-white font-bold text-lg mb-4 flex items-center gap-2">
          <ArrowDownCircle className="w-5 h-5 text-red-400" />
          Sell Position
        </h3>

        <div className="bg-white/5 rounded-xl p-4 mb-4">
          <div className="flex items-center gap-3 mb-3">
            {position.logo && <img src={position.logo} alt="" className="w-10 h-10 rounded-full" />}
            <div className="flex-1">
              <div className="text-white font-bold">{position.symbol}</div>
              <div className="text-gray-400 text-xs">{position.quantity?.toFixed(6)} tokens</div>
            </div>
            <ChainBadge chainId={chainId} chains={allChains} />
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <div className="text-gray-400 text-xs">Entry Price</div>
              <div className="text-white font-medium">{formatUSD(position.entry_price)}</div>
            </div>
            <div>
              <div className="text-gray-400 text-xs">Current Price</div>
              <div className="text-white font-medium">{formatUSD(price)}</div>
            </div>
            <div>
              <div className="text-gray-400 text-xs">Current Value</div>
              <div className="text-white font-medium">{formatUSD(currentValue)}</div>
            </div>
            <div>
              <div className="text-gray-400 text-xs">P&L</div>
              <div className={`font-bold ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
                {formatUSD(pnl)} ({formatPct(pnlPct)})
              </div>
            </div>
          </div>
        </div>

        {error && <div className="text-red-400 text-sm mb-3 bg-red-500/10 rounded-lg p-2.5 border border-red-500/20">{error}</div>}

        <button onClick={handleSell} disabled={status !== 'idle' || !chainId}
          className="w-full py-3 rounded-xl font-bold text-sm transition-all disabled:opacity-50 bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white shadow-lg shadow-red-900/20">
          {status === 'idle' && `Sell ${position.symbol}`}
          {status === 'pending' && <><Loader2 className="inline w-4 h-4 mr-2 animate-spin" />Preparing...</>}
          {status === 'switching' && <><Loader2 className="inline w-4 h-4 mr-2 animate-spin" />Switching Network...</>}
          {status === 'confirming' && <><Loader2 className="inline w-4 h-4 mr-2 animate-spin" />Confirm in Wallet...</>}
          {status === 'recording' && <><Loader2 className="inline w-4 h-4 mr-2 animate-spin" />Recording...</>}
          {status === 'success' && <><Check className="inline w-4 h-4 mr-2" />Sold Successfully!</>}
        </button>

        {txHash && (
          <a href={`${getExplorerTx(chainId)}${txHash}`} target="_blank" rel="noopener noreferrer"
            className="flex items-center justify-center gap-1 text-xs text-blue-400 mt-2 hover:text-blue-300">
            View Transaction <ExternalLink className="w-3 h-3" />
          </a>
        )}

        {!scDeployed && (
          <p className="text-gray-500 text-[10px] mt-2 text-center">
            Sell executes via 1inch DEX swap. SC fee proxy coming soon.
          </p>
        )}
      </div>

      {showSwapModal && (
        <SwapModal
          isOpen={showSwapModal}
          onClose={() => setShowSwapModal(false)}
          initialFromToken={position.contract_address ? { symbol: position.symbol, address: position.contract_address, decimals: 18, name: position.name || position.symbol } : position.symbol}
          initialToToken="USDT"
          initialAmount={position.quantity?.toString() || ''}
          initialChainId={currentChainId}
          onSwapComplete={handleSwapComplete}
        />
      )}
    </div>
  );
}

function SLTPModal({ position, onClose, token, onSuccess }) {
  const [slPercent, setSlPercent] = useState(position.stop_loss_percent?.toString() || '10');
  const [tpPercent, setTpPercent] = useState(position.take_profit_percent?.toString() || '15');
  const [enableSL, setEnableSL] = useState(position.has_stop_loss !== false);
  const [enableTP, setEnableTP] = useState(position.has_take_profit !== false);
  const [saving, setSaving] = useState(false);

  const entryPrice = position.entry_price || 0;

  const handleSave = async () => {
    setSaving(true);
    try {
      await investService.setTriggers(token, position.id, {
        stop_loss_percent: parseFloat(slPercent),
        take_profit_percent: parseFloat(tpPercent),
        enable_stop_loss: enableSL,
        enable_take_profit: enableTP,
      });
      onSuccess?.();
      onClose();
    } catch (err) {
      console.error('Failed to set triggers:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = async () => {
    setSaving(true);
    try {
      await investService.cancelTriggers(token, position.id);
      onSuccess?.();
      onClose();
    } catch (err) {
      console.error('Failed to cancel triggers:', err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-[#1a1a2e] border border-white/10 rounded-2xl w-full max-w-sm p-6 relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-white"><X className="w-5 h-5" /></button>
        <h3 className="text-white font-bold mb-1 flex items-center gap-2">
          <Target className="w-5 h-5 text-yellow-400" />
          Stop-Loss / Take-Profit
        </h3>
        <p className="text-gray-400 text-sm mb-4">{position.symbol} | Entry: {formatUSD(entryPrice)}</p>

        <div className="space-y-3">
          <div>
            <label className="flex items-center gap-2 text-sm text-gray-300 mb-1">
              <input type="checkbox" checked={enableSL} onChange={e => setEnableSL(e.target.checked)} className="accent-red-500" /> Stop-Loss
            </label>
            <div className="flex items-center gap-2">
              <input type="number" value={slPercent} onChange={e => setSlPercent(e.target.value)}
                disabled={!enableSL} min="1" max="50"
                className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-white text-sm disabled:opacity-40 focus:outline-none focus:border-red-500/50" />
              <span className="text-gray-400">%</span>
            </div>
            {enableSL && <span className="text-red-400 text-xs">Triggers at {formatUSD(entryPrice * (1 - parseFloat(slPercent || 10) / 100))}</span>}
          </div>
          <div>
            <label className="flex items-center gap-2 text-sm text-gray-300 mb-1">
              <input type="checkbox" checked={enableTP} onChange={e => setEnableTP(e.target.checked)} className="accent-green-500" /> Take-Profit
            </label>
            <div className="flex items-center gap-2">
              <input type="number" value={tpPercent} onChange={e => setTpPercent(e.target.value)}
                disabled={!enableTP} min="1" max="200"
                className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-white text-sm disabled:opacity-40 focus:outline-none focus:border-green-500/50" />
              <span className="text-gray-400">%</span>
            </div>
            {enableTP && <span className="text-green-400 text-xs">Triggers at {formatUSD(entryPrice * (1 + parseFloat(tpPercent || 15) / 100))}</span>}
          </div>
        </div>

        <div className="flex gap-2 mt-5">
          <button onClick={handleSave} disabled={saving}
            className="flex-1 py-2.5 rounded-lg bg-[#00FFD1]/10 text-[#00FFD1] hover:bg-[#00FFD1]/20 text-sm font-medium disabled:opacity-50 border border-[#00FFD1]/20 transition-colors">
            {saving ? 'Saving...' : 'Save'}
          </button>
          {(position.has_stop_loss || position.has_take_profit) && (
            <button onClick={handleCancel} disabled={saving}
              className="py-2.5 px-4 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 text-sm disabled:opacity-50 border border-red-500/20 transition-colors">
              Remove All
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

const SUMMARY_CARDS = [
  { key: 'total_invested', label: 'Invested', icon: DollarSign, color: 'from-blue-500/20 to-blue-600/5', borderColor: 'border-l-blue-500', iconColor: 'text-blue-400' },
  { key: 'total_current_value', label: 'Current Value', icon: TrendingUp, color: 'from-emerald-500/20 to-emerald-600/5', borderColor: 'border-l-emerald-500', iconColor: 'text-emerald-400' },
  { key: 'total_pnl', label: 'Total P&L', icon: BarChart2, color: 'from-purple-500/20 to-purple-600/5', borderColor: 'border-l-purple-500', iconColor: 'text-purple-400', isPnl: true },
  { key: 'active_positions_count', label: 'Active Positions', icon: Layers, color: 'from-yellow-500/20 to-yellow-600/5', borderColor: 'border-l-yellow-500', iconColor: 'text-yellow-400', isCount: true },
];

const InvestPage = () => {
  const { token, walletAddress, walletConnected } = useWalletAuth();
  const { chains: allChains, getChain } = useChains();
  const chainOptionsWithAll = [{ id: null, name: 'All Chains', color: '#888' }, ...allChains];
  const getExplorerTx = (cid) => {
    const c = getChain(cid);
    return c ? `${c.explorer}${c.explorer_tx_path || '/tx/'}` : '';
  };

  const [opportunities, setOpportunities] = useState([]);
  const [positions, setPositions] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [chainFilter, setChainFilter] = useState(null);
  const [buyModalOpp, setBuyModalOpp] = useState(null);
  const [sellModalPos, setSellModalPos] = useState(null);
  const [sltpPosition, setSltpPosition] = useState(null);
  const [expandedPosition, setExpandedPosition] = useState(null);
  const [exportOpen, setExportOpen] = useState(false);
  const [expireTick, setExpireTick] = useState(0);
  const refreshInterval = useRef(null);

  const handleExpire = useCallback(() => {
    setExpireTick(t => t + 1);
  }, []);

  const activeOpportunities = useMemo(() => {
    return opportunities.filter(opp => {
      if (opp.remaining_seconds !== undefined && opp.remaining_seconds !== null) {
        return opp.remaining_seconds > 0;
      }
      if (!opp.expires_at) return true;
      const ts = opp.expires_at.endsWith('Z') || opp.expires_at.includes('+') ? opp.expires_at : opp.expires_at + 'Z';
      return new Date(ts).getTime() > Date.now();
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opportunities, expireTick]);

  const fetchData = useCallback(async () => {
    if (!token) { setLoading(false); return; }
    try {
      const [oppData, posData, sumData] = await Promise.all([
        investService.getOpportunities(token, chainFilter),
        investService.getPositions(token),
        investService.getSummary(token),
      ]);
      setOpportunities(oppData.opportunities || []);
      setPositions(posData.positions || []);
      setSummary(sumData);
    } catch (err) {
      console.error('Error fetching invest data:', err);
    } finally {
      setLoading(false);
    }
  }, [token, chainFilter]);

  useEffect(() => {
    fetchData();
    refreshInterval.current = setInterval(fetchData, 30000);
    return () => clearInterval(refreshInterval.current);
  }, [fetchData]);

  const handleExport = async (format) => {
    setExportOpen(false);
    try {
      await investService.exportReport(token, format, 'all');
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  const hasActivity = summary && (summary.total_invested > 0 || summary.active_positions_count > 0);

  return (
    <div className="premium-bg min-h-screen overflow-x-hidden">
      <PremiumNavbar />
      <div className="container mx-auto px-3 sm:px-4 lg:px-6 py-4 sm:py-6">

        <div className="mb-6">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-white flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center">
                  <Zap className="w-5 h-5 text-white" />
                </div>
                Dump Opportunities
              </h1>
              <p className="text-gray-400 text-sm mt-1 ml-[46px]">AI-detected price drops — buy the dip before recovery</p>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative">
                <button onClick={() => setExportOpen(!exportOpen)}
                  className="flex items-center gap-1.5 text-sm px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-300 hover:border-white/20 hover:bg-white/[0.08] transition-all">
                  <Download className="w-4 h-4" /> Report
                </button>
                {exportOpen && (
                  <div className="absolute right-0 top-full mt-1 bg-[#1a1a2e] border border-white/10 rounded-lg overflow-hidden z-10 shadow-xl min-w-[140px]">
                    <button onClick={() => handleExport('csv')} className="flex items-center gap-2 w-full text-left px-4 py-2.5 text-sm text-gray-300 hover:bg-white/5 transition-colors">
                      <FileSpreadsheet className="w-4 h-4 text-green-400" /> CSV Export
                    </button>
                    <button onClick={() => handleExport('pdf')} className="flex items-center gap-2 w-full text-left px-4 py-2.5 text-sm text-gray-300 hover:bg-white/5 transition-colors">
                      <FileText className="w-4 h-4 text-red-400" /> PDF Report
                    </button>
                  </div>
                )}
              </div>
              <button onClick={fetchData} className="p-2 rounded-lg bg-white/5 border border-white/10 text-gray-400 hover:text-white hover:bg-white/[0.08] transition-all" title="Refresh">
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
            {SUMMARY_CARDS.map(card => {
              const Icon = card.icon;
              const val = summary?.[card.key];
              const displayVal = card.isCount
                ? (val || 0)
                : (hasActivity ? formatUSD(val) : '—');

              let pnlClass = 'text-white';
              if (card.isPnl && val !== undefined && val !== 0) {
                pnlClass = val >= 0 ? 'text-green-400' : 'text-red-400';
              }

              return (
                <div key={card.key} className={`bg-gradient-to-r ${card.color} border border-white/10 ${card.borderColor} border-l-2 rounded-xl p-3.5`}>
                  <div className="flex items-center gap-2 mb-1.5">
                    <Icon className={`w-4 h-4 ${card.iconColor}`} />
                    <span className="text-gray-400 text-xs">{card.label}</span>
                  </div>
                  <div className={`font-bold text-lg ${card.isPnl ? pnlClass : 'text-white'}`}>
                    {card.isCount ? displayVal : displayVal}
                    {card.isPnl && hasActivity && val !== undefined && (
                      <span className="text-xs font-normal ml-1">({formatPct(summary?.total_pnl_percentage)})</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {summary?.best_performer && hasActivity && (
            <div className="flex gap-3 mt-3">
              <div className="flex items-center gap-1.5 text-xs bg-green-500/10 border border-green-500/20 rounded-lg px-3 py-1.5">
                <TrendingUp className="w-3 h-3 text-green-400" />
                <span className="text-gray-400">Best:</span>
                <span className="text-green-400 font-medium">{summary.best_performer.symbol} {formatPct(summary.best_performer.pnl_percent)}</span>
              </div>
              {summary.worst_performer && (
                <div className="flex items-center gap-1.5 text-xs bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-1.5">
                  <TrendingDown className="w-3 h-3 text-red-400" />
                  <span className="text-gray-400">Worst:</span>
                  <span className="text-red-400 font-medium">{summary.worst_performer.symbol} {formatPct(summary.worst_performer.pnl_percent)}</span>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex gap-2 mb-5 overflow-x-auto pb-1">
          {chainOptionsWithAll.map(c => (
            <button key={c.id ?? 'all'} onClick={() => setChainFilter(c.id)}
              className={`text-xs px-3 py-1.5 rounded-lg border whitespace-nowrap transition-all flex items-center gap-1.5 ${chainFilter === c.id ? 'border-[#00FFD1]/50 bg-[#00FFD1]/10 text-[#00FFD1]' : 'border-white/10 text-gray-400 hover:border-white/20'}`}>
              {c.id && <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: c.color }}></span>}
              {c.name}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-[#00FFD1] animate-spin mb-3" />
            <span className="text-gray-400 text-sm">Scanning for opportunities...</span>
          </div>
        ) : activeOpportunities.length === 0 ? (
          <div className="bg-gradient-to-b from-white/5 to-transparent border border-white/10 rounded-2xl p-8 sm:p-12 text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-500/10 border border-green-500/20 flex items-center justify-center invest-float-anim">
              <Shield className="w-8 h-8 text-green-400" />
            </div>
            <h3 className="text-white font-bold text-lg mb-2">Market is Stable</h3>
            <p className="text-gray-400 text-sm max-w-md mx-auto mb-1">
              No dump opportunities right now. Our AI is continuously monitoring the market.
            </p>
            <p className="text-gray-500 text-xs max-w-md mx-auto">
              When a coin drops significantly, it will appear here as a 1-hour buying window.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            {activeOpportunities.map((opp, i) => {
              const isUrgent = (opp.remaining_seconds || 0) < 600;
              return (
                <div key={opp.symbol + i}
                  className={`bg-white/5 border rounded-xl p-4 transition-all hover:bg-white/[0.07] ${isUrgent ? 'border-red-500/40 invest-pulse-border' : 'border-white/10 hover:border-white/20'}`}>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2.5">
                      {opp.logo ? <img src={opp.logo} alt="" className="w-9 h-9 rounded-full" /> : <div className="w-9 h-9 rounded-full bg-white/10 flex items-center justify-center text-white font-bold text-sm">{opp.symbol?.charAt(0)}</div>}
                      <div>
                        <div className="text-white font-bold text-sm">{opp.name}</div>
                        <div className="text-gray-400 text-xs">{opp.symbol}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-red-400 font-bold text-lg">{opp.dump_percentage?.toFixed(1)}%</div>
                      <CountdownTimer expiresAt={opp.expires_at} remainingSeconds={opp.remaining_seconds} onExpire={handleExpire} />
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-xs mb-3 bg-white/[0.03] rounded-lg p-2">
                    <div>
                      <span className="text-gray-500 block">Price</span>
                      <span className="text-white font-medium">{formatUSD(opp.current_price)}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">MCap</span>
                      <span className="text-white font-medium">{formatCompact(opp.market_cap)}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Vol 24h</span>
                      <span className="text-white font-medium">{formatCompact(opp.volume_24h)}</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-xs mb-3">
                    <div className="flex gap-1 flex-wrap">
                      <RiskBadge level={opp.risk_level || 'Moderate'} />
                      {opp.supported_chains?.map(cid => <ChainBadge key={cid} chainId={cid} chains={allChains} />)}
                    </div>
                  </div>

                  {opp.ai_recommendation && (
                    <p className="text-gray-400 text-xs mb-3 line-clamp-2 italic">{opp.ai_recommendation}</p>
                  )}

                  <button onClick={() => setBuyModalOpp(opp)}
                    className="w-full py-2.5 rounded-lg bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white text-sm font-bold transition-all shadow-lg shadow-green-900/20">
                    Buy Now
                  </button>
                </div>
              );
            })}
          </div>
        )}

        <div className="mb-6">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center">
              <Wallet className="w-4 h-4 text-white" />
            </div>
            My Positions
            <span className="text-gray-500 text-sm font-normal ml-1">({positions.length})</span>
          </h2>

          {positions.length === 0 ? (
            <div className="bg-gradient-to-b from-white/5 to-transparent border border-white/10 rounded-xl p-8 text-center">
              <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-yellow-500/10 border border-yellow-500/20 flex items-center justify-center">
                <Activity className="w-6 h-6 text-yellow-400" />
              </div>
              <p className="text-gray-300 text-sm font-medium mb-1">No active positions</p>
              <p className="text-gray-500 text-xs max-w-sm mx-auto">
                Buy a dump opportunity above to open your first position. Your holdings with real-time P&L will appear here.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {positions.map(pos => {
                const pnl = pos.unrealized_pnl || 0;
                const pnlPct = pos.pnl_percent || 0;
                const isProfit = pnl >= 0;
                const isExpanded = expandedPosition === pos.id;

                return (
                  <div key={pos.id} className="bg-white/5 border border-white/10 rounded-xl overflow-hidden hover:border-white/15 transition-all">
                    <div className="p-3 sm:p-4 flex items-center gap-3 cursor-pointer" onClick={() => setExpandedPosition(isExpanded ? null : pos.id)}>
                      <div className="flex items-center gap-2.5 flex-1 min-w-0">
                        {pos.logo ? <img src={pos.logo} alt="" className="w-9 h-9 rounded-full flex-shrink-0" /> : <div className="w-9 h-9 rounded-full bg-white/10 flex items-center justify-center text-white font-bold text-xs flex-shrink-0">{pos.symbol?.charAt(0)}</div>}
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="text-white font-bold text-sm">{pos.symbol}</span>
                            <ChainBadge chainId={pos.chain_id} chains={allChains} />
                            {pos.has_stop_loss && <span className="text-[9px] px-1 py-0.5 rounded bg-red-500/15 text-red-400 border border-red-500/20">SL</span>}
                            {pos.has_take_profit && <span className="text-[9px] px-1 py-0.5 rounded bg-green-500/15 text-green-400 border border-green-500/20">TP</span>}
                          </div>
                          <div className="text-gray-400 text-xs mt-0.5">
                            {pos.quantity?.toFixed(4)} @ {formatUSD(pos.entry_price)}
                          </div>
                        </div>
                      </div>

                      <div className="text-right flex-shrink-0">
                        <div className="text-white font-bold text-sm">{formatUSD(pos.current_value)}</div>
                        <div className={`text-xs font-medium ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
                          {formatUSD(pnl)} ({formatPct(pnlPct)})
                        </div>
                      </div>

                      <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform flex-shrink-0 ${isExpanded ? 'rotate-180' : ''}`} />
                    </div>

                    {isExpanded && (
                      <div className="border-t border-white/5 px-3 sm:px-4 py-3 bg-white/[0.02]">
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs mb-3">
                          <div><span className="text-gray-500">Entry:</span> <span className="text-white">{formatUSD(pos.entry_price)}</span></div>
                          <div><span className="text-gray-500">Current:</span> <span className="text-white">{formatUSD(pos.current_price)}</span></div>
                          <div><span className="text-gray-500">Invested:</span> <span className="text-white">{formatUSD(pos.invested_usdt)}</span></div>
                          <div><span className="text-gray-500">Bought:</span> <span className="text-white">{pos.created_at?.split('T')[0]}</span></div>
                          {pos.stop_loss_price && <div><span className="text-gray-500">SL Price:</span> <span className="text-red-400">{formatUSD(pos.stop_loss_price)}</span></div>}
                          {pos.take_profit_price && <div><span className="text-gray-500">TP Price:</span> <span className="text-green-400">{formatUSD(pos.take_profit_price)}</span></div>}
                          {pos.fee_amount > 0 && <div><span className="text-gray-500">Fee Paid:</span> <span className="text-yellow-400">{formatUSD(pos.fee_amount)}</span></div>}
                        </div>

                        {pos.tx_hash && (
                          <a href={`${getExplorerTx(pos.chain_id)}${pos.tx_hash}`} target="_blank" rel="noopener noreferrer"
                            className="text-blue-400 text-xs hover:text-blue-300 flex items-center gap-1 mb-3">
                            TX: {pos.tx_hash.slice(0, 10)}...{pos.tx_hash.slice(-6)} <ExternalLink className="w-3 h-3" />
                          </a>
                        )}

                        <div className="flex gap-2">
                          <button onClick={(e) => { e.stopPropagation(); setSltpPosition(pos); }}
                            className="flex-1 py-2 rounded-lg bg-yellow-500/10 text-yellow-400 hover:bg-yellow-500/20 text-xs font-medium border border-yellow-500/20 transition-colors flex items-center justify-center gap-1">
                            <Target className="w-3 h-3" /> Set SL/TP
                          </button>
                          <button onClick={(e) => { e.stopPropagation(); setSellModalPos(pos); }}
                            className="flex-1 py-2 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 text-xs font-medium border border-red-500/20 transition-colors flex items-center justify-center gap-1">
                            <ArrowDownCircle className="w-3 h-3" /> Sell
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {buyModalOpp && (
        <BuyModal
          opportunity={buyModalOpp}
          onClose={() => setBuyModalOpp(null)}
          token={token}
          onSuccess={() => { setBuyModalOpp(null); fetchData(); }}
        />
      )}

      {sellModalPos && (
        <SellModal
          position={sellModalPos}
          onClose={() => setSellModalPos(null)}
          token={token}
          onSuccess={() => { setSellModalPos(null); fetchData(); }}
        />
      )}

      {sltpPosition && (
        <SLTPModal
          position={sltpPosition}
          onClose={() => setSltpPosition(null)}
          token={token}
          onSuccess={fetchData}
        />
      )}
    </div>
  );
};

export default InvestPage;
