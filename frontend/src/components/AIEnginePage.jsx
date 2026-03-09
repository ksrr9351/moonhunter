import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWalletAuth } from '../contexts/WalletAuthContext';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain,
  TrendingDown,
  TrendingUp,
  AlertTriangle,
  Wallet,
  RefreshCw,
  Target,
  Zap,
  ArrowUpRight,
  ArrowDownRight,
  DollarSign,
  Activity,
  PieChart,
  X,
  Check,
  ChevronDown,
  ChevronUp,
  Bot,
  Settings,
  Radio,
  Shield,
  Info,
  Sparkles,
  Coins
} from 'lucide-react';
import PremiumNavbar from './PremiumNavbar';
import InfoTooltip from './InfoTooltip';
import TradingBotSettings from './TradingBotSettings';
import AnalyticsDashboard from './AnalyticsDashboard';
import { LiveConnectionStatus } from './LivePriceIndicator';
import { usePriceStream } from '../contexts/PriceStreamContext';
import { SwapModal } from './SwapModal';
import { formatUSD, formatPercent } from '../utils/formatters';


const API_URL = import.meta.env.VITE_BACKEND_URL || '';

const getRiskLabel = (score) => {
  if (score <= 0.3) return { text: 'Low', color: 'text-green-400', bg: 'bg-green-500/20', border: 'border-green-500/30' };
  if (score <= 0.6) return { text: 'Medium', color: 'text-yellow-400', bg: 'bg-yellow-500/20', border: 'border-yellow-500/30' };
  return { text: 'High', color: 'text-red-400', bg: 'bg-red-500/20', border: 'border-red-500/30' };
};

const RecommendationCard = ({ alloc, idx, type, onExecute }) => {
  const risk = getRiskLabel(alloc.risk_score || 0.5);
  const isDump = type === 'dump';
  const change24h = alloc.change_24h || 0;
  const change1h = alloc.change_1h || 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.06 }}
      className={`group relative rounded-2xl border transition-all duration-200 hover:shadow-lg hover:shadow-black/20 ${
        isDump
          ? 'bg-gradient-to-br from-gray-800/80 to-orange-950/20 border-orange-500/20 hover:border-orange-500/40'
          : 'bg-gradient-to-br from-gray-800/80 to-emerald-950/20 border-emerald-500/20 hover:border-emerald-500/40'
      }`}
    >
      <div className="p-4 sm:p-5">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="relative flex-shrink-0">
              {alloc.logo ? (
                <img src={alloc.logo} alt={alloc.symbol} className="w-10 h-10 sm:w-12 sm:h-12 rounded-full ring-2 ring-gray-700/50" onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }} />
              ) : null}
              <div className={`w-10 h-10 sm:w-12 sm:h-12 rounded-full ${isDump ? 'bg-orange-500/20' : 'bg-emerald-500/20'} flex items-center justify-center ${alloc.logo ? 'hidden' : ''}`}>
                <span className={`text-sm sm:text-base font-bold ${isDump ? 'text-orange-400' : 'text-emerald-400'}`}>{alloc.symbol?.charAt(0)}</span>
              </div>
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-white font-bold text-base sm:text-lg">{alloc.symbol}</h3>
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] sm:text-xs font-medium ${
                  isDump ? 'bg-orange-500/15 text-orange-300' : 'bg-emerald-500/15 text-emerald-300'
                }`}>
                  {isDump ? <><TrendingDown className="w-3 h-3" /> Dip Buy</> : <><TrendingUp className="w-3 h-3" /> Trending</>}
                </span>
              </div>
              {alloc.name && <p className="text-xs text-gray-500 truncate">{alloc.name}</p>}
            </div>
          </div>
          <div className="text-right flex-shrink-0">
            <p className="text-white font-bold text-base sm:text-lg">{formatUSD(alloc.price_usdt)}</p>
            <div className="flex items-center justify-end gap-1">
              {change24h >= 0 ? (
                <ArrowUpRight className="w-3 h-3 text-green-400" />
              ) : (
                <ArrowDownRight className="w-3 h-3 text-red-400" />
              )}
              <span className={`text-xs font-medium ${change24h >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {change24h >= 0 ? '+' : ''}{change24h.toFixed(1)}%
              </span>
              <span className="text-gray-600 text-xs">24h</span>
            </div>
          </div>
        </div>

        <p className="text-xs sm:text-sm text-gray-400 mb-3 leading-relaxed">{alloc.reason}</p>

        <div className="flex flex-wrap items-center gap-2 mb-4">
          <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs ${risk.bg} ${risk.color} ${risk.border} border`}>
            <Shield className="w-3 h-3" />
            {risk.text} Risk
          </div>
          {change1h !== 0 && (
            <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs ${change1h >= 0 ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'} border`}>
              {change1h >= 0 ? '+' : ''}{change1h.toFixed(1)}% 1h
            </div>
          )}
          <div className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs bg-gray-700/50 text-gray-400 border border-gray-600/30">
            <PieChart className="w-3 h-3" />
            {alloc.allocation_percent?.toFixed(0)}% of portfolio
          </div>
        </div>

        <button
          onClick={() => onExecute(alloc)}
          className={`w-full flex items-center justify-center gap-2 py-2.5 sm:py-3 rounded-xl font-semibold text-sm transition-all duration-200 ${
            isDump
              ? 'bg-gradient-to-r from-orange-500 to-amber-500 text-white hover:from-orange-400 hover:to-amber-400 shadow-lg shadow-orange-500/20 hover:shadow-orange-500/30'
              : 'bg-gradient-to-r from-emerald-500 to-teal-500 text-white hover:from-emerald-400 hover:to-teal-400 shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30'
          }`}
        >
          <Zap className="w-4 h-4" />
          Invest {formatUSD(alloc.allocation_usdt)}
        </button>
      </div>
    </motion.div>
  );
};

const RecommendationsModal = ({ recommendations, onClose, onExecute }) => {
  const allRecs = [
    ...(recommendations.dump_opportunities || []).map(r => ({ ...r, _type: 'dump' })),
    ...(recommendations.trend_candidates || []).map(r => ({ ...r, _type: 'trend' })),
  ];
  const totalAllocation = allRecs.reduce((sum, r) => sum + (r.allocation_usdt || 0), 0);
  const avgRisk = allRecs.length > 0 ? allRecs.reduce((sum, r) => sum + (r.risk_score || 0.5), 0) / allRecs.length : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-md overflow-y-auto">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
        className="bg-gray-900 rounded-2xl sm:rounded-3xl w-full max-w-2xl max-h-[92vh] overflow-hidden border border-gray-700/50 shadow-2xl shadow-black/50 my-4 flex flex-col"
      >
        <div className="relative overflow-hidden px-5 sm:px-6 pt-5 sm:pt-6 pb-4 border-b border-gray-800/80 flex-shrink-0">
          <div className="absolute inset-0 bg-gradient-to-br from-[#00FFD1]/5 via-transparent to-purple-500/5" />
          <div className="relative">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#00FFD1]/20 to-purple-500/20 flex items-center justify-center border border-[#00FFD1]/20">
                  <Sparkles className="w-5 h-5 text-[#00FFD1]" />
                </div>
                <div>
                  <h2 className="text-lg sm:text-xl font-bold text-white">AI Picks</h2>
                  <p className="text-xs text-gray-500">Personalized for your strategy</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-xl hover:bg-white/10 transition-colors"
              >
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>

            <div className="grid grid-cols-3 gap-2 sm:gap-3">
              <div className="bg-gray-800/60 rounded-xl p-2.5 sm:p-3 text-center border border-gray-700/30">
                <p className="text-[10px] sm:text-xs text-gray-500 mb-0.5">Total Budget</p>
                <p className="text-sm sm:text-base font-bold text-white">{formatUSD(totalAllocation)}</p>
              </div>
              <div className="bg-gray-800/60 rounded-xl p-2.5 sm:p-3 text-center border border-gray-700/30">
                <p className="text-[10px] sm:text-xs text-gray-500 mb-0.5">Picks</p>
                <p className="text-sm sm:text-base font-bold text-white">{allRecs.length}</p>
              </div>
              <div className="bg-gray-800/60 rounded-xl p-2.5 sm:p-3 text-center border border-gray-700/30">
                <p className="text-[10px] sm:text-xs text-gray-500 mb-0.5">Avg Risk</p>
                <p className={`text-sm sm:text-base font-bold ${getRiskLabel(avgRisk).color}`}>{getRiskLabel(avgRisk).text}</p>
              </div>
            </div>

            {recommendations.explanations?.length > 0 && (
              <div className="mt-3 flex items-start gap-2 p-2.5 rounded-lg bg-blue-500/5 border border-blue-500/10">
                <Info className="w-3.5 h-3.5 text-blue-400 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-blue-300/80 leading-relaxed">{recommendations.explanations[0]}</p>
              </div>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-5 sm:px-6 py-4">
          <div className="space-y-3">
            {recommendations.dump_opportunities?.length > 0 && (
              <>
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-1.5 h-1.5 rounded-full bg-orange-400" />
                  <p className="text-xs font-semibold text-orange-300/80 uppercase tracking-wider">Dip Buying</p>
                  <div className="flex-1 h-px bg-gradient-to-r from-orange-500/20 to-transparent" />
                </div>
                {recommendations.dump_opportunities.map((alloc, idx) => (
                  <RecommendationCard key={`dump-${idx}`} alloc={alloc} idx={idx} type="dump" onExecute={onExecute} />
                ))}
              </>
            )}

            {recommendations.trend_candidates?.length > 0 && (
              <>
                <div className={`flex items-center gap-2 mb-1 ${recommendations.dump_opportunities?.length > 0 ? 'mt-4' : ''}`}>
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  <p className="text-xs font-semibold text-emerald-300/80 uppercase tracking-wider">Trending Up</p>
                  <div className="flex-1 h-px bg-gradient-to-r from-emerald-500/20 to-transparent" />
                </div>
                {recommendations.trend_candidates.map((alloc, idx) => (
                  <RecommendationCard key={`trend-${idx}`} alloc={alloc} idx={idx} type="trend" onExecute={onExecute} />
                ))}
              </>
            )}

            {!recommendations.dump_opportunities?.length && !recommendations.trend_candidates?.length && (
              <div className="text-center py-12">
                <div className="w-16 h-16 rounded-full bg-gray-800/50 flex items-center justify-center mx-auto mb-4">
                  <Target className="w-8 h-8 text-gray-600" />
                </div>
                <p className="text-gray-400 font-medium">No picks right now</p>
                <p className="text-sm text-gray-600 mt-1">Try a different amount or check back soon</p>
              </div>
            )}
          </div>
        </div>

        {allRecs.length > 0 && (
          <div className="px-5 sm:px-6 py-3 sm:py-4 border-t border-gray-800/80 flex-shrink-0 bg-gray-900/80">
            <p className="text-[10px] sm:text-xs text-gray-600 text-center leading-relaxed">
              Recommendations are based on market analysis and are not financial advice. Always do your own research.
            </p>
          </div>
        )}
      </motion.div>
    </div>
  );
};

const AIEnginePage = () => {
  const navigate = useNavigate();
  const { token, isAuthenticated, currentChainId } = useWalletAuth();
  
  const [walletStatus, setWalletStatus] = useState(null);
  const [dumpOpportunities, setDumpOpportunities] = useState(null);
  const [portfolio, setPortfolio] = useState(null);
  const [signals, setSignals] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  
  const [investAmount, setInvestAmount] = useState('100');
  const [strategy, setStrategy] = useState('balanced');
  const [recommendations, setRecommendations] = useState(null);
  const [showRecommendations, setShowRecommendations] = useState(false);
  const [investing, setInvesting] = useState(false);
  
  const [expandedSection, setExpandedSection] = useState('opportunities');
  const [showBotSettings, setShowBotSettings] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [showSwapModal, setShowSwapModal] = useState(false);
  const [swapFromToken, setSwapFromToken] = useState('ETH');
  const [swapToToken, setSwapToToken] = useState('USDT');
  const [swapAmount, setSwapAmount] = useState('');
  const [pendingInvestment, setPendingInvestment] = useState(null);
  const [pendingClose, setPendingClose] = useState(null);
  const [rebalancing, setRebalancing] = useState(null);
  const [showRebalancing, setShowRebalancing] = useState(false);

  const fetchData = useCallback(async () => {
    if (!token) return;
    
    try {
      const [signalsRes, dumpRes] = await Promise.all([
        axios.get(`${API_URL}/api/ai-engine/signals`, {
          headers: { Authorization: `Bearer ${token}` }
        }).catch(() => ({ data: null })),
        axios.get(`${API_URL}/api/ai-engine/dump-opportunities`, {
          headers: { Authorization: `Bearer ${token}` }
        }).catch(() => ({ data: null }))
      ]);
      
      setSignals(signalsRes.data);
      setDumpOpportunities(dumpRes.data);
      
      const [walletRes, portfolioRes] = await Promise.all([
        axios.get(`${API_URL}/api/ai-engine/wallet-status`, {
          headers: { Authorization: `Bearer ${token}` }
        }).catch(() => ({ data: null })),
        axios.get(`${API_URL}/api/ai-engine/portfolio`, {
          headers: { Authorization: `Bearer ${token}` }
        }).catch(() => ({ data: null }))
      ]);
      
      setWalletStatus(walletRes.data);
      setPortfolio(portfolioRes.data);
      
      if (portfolioRes.data?.active_positions?.length > 0) {
        const rebalanceRes = await axios.get(`${API_URL}/api/ai-engine/rebalancing`, {
          headers: { Authorization: `Bearer ${token}` }
        }).catch(() => ({ data: null }));
        setRebalancing(rebalanceRes.data);
      }
      
    } catch (err) {
      console.error('Error fetching AI Engine data:', err);
      setError('Failed to fetch data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const getRecommendations = async () => {
    if (!investAmount || parseFloat(investAmount) <= 0) {
      setError('Please enter a valid investment amount');
      return;
    }
    
    setInvesting(true);
    setError('');
    
    try {
      const response = await axios.post(
        `${API_URL}/api/ai-engine/recommendations`,
        { usdt_amount: parseFloat(investAmount) },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      setRecommendations(response.data);
      setShowRecommendations(true);
    } catch (err) {
      console.error('Error getting recommendations:', err);
      setError(err.response?.data?.detail || 'Failed to get recommendations');
    } finally {
      setInvesting(false);
    }
  };

  const executeInvestment = async (allocation) => {
    setPendingInvestment(allocation);
    setSwapFromToken('USDT');
    setSwapToToken(allocation.symbol);
    setSwapAmount(allocation.allocation_usdt.toString());
    setShowSwapModal(true);
  };
  
  const recordInvestmentAfterSwap = async (txHash) => {
    if (!pendingInvestment) return;
    
    try {
      await axios.post(
        `${API_URL}/api/ai-engine/invest`,
        {
          symbol: pendingInvestment.symbol,
          usdt_amount: pendingInvestment.allocation_usdt,
          strategy: pendingInvestment.strategy,
          trigger_reason: pendingInvestment.reason,
          tx_hash: txHash
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      fetchData();
    } catch (err) {
      console.error('Error recording investment:', err);
    } finally {
      setPendingInvestment(null);
    }
  };

  const closePosition = async (positionId, position) => {
    if (position) {
      setPendingClose({ id: positionId, position });
      setSwapFromToken(position.symbol);
      setSwapToToken('USDT');
      setSwapAmount(position.quantity?.toString() || '');
      setShowSwapModal(true);
    }
  };
  
  const recordCloseAfterSwap = async (txHash) => {
    if (!pendingClose) return;
    
    try {
      await axios.post(
        `${API_URL}/api/ai-engine/close-position/${pendingClose.id}`,
        { reason: 'manual', tx_hash: txHash },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      fetchData();
    } catch (err) {
      console.error('Error closing position:', err);
      setError(err.response?.data?.detail || 'Failed to close position');
    } finally {
      setPendingClose(null);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="premium-bg min-h-screen overflow-x-hidden">
        <PremiumNavbar />
        <div className="container mx-auto px-4 py-12 sm:py-20">
          <div className="text-center">
            <Brain className="w-16 h-16 sm:w-20 sm:h-20 text-[#00FFD1] mx-auto mb-4 sm:mb-6" />
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-white mb-3 sm:mb-4">Moon Hunters AI Engine</h1>
            <p className="text-gray-400 text-sm sm:text-base mb-6 sm:mb-8">Connect your wallet to access AI-powered investment tools</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="premium-bg min-h-screen overflow-x-hidden">
      <PremiumNavbar />
      
      <div className="container mx-auto px-3 sm:px-4 lg:px-6 py-4 sm:py-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6 sm:mb-8">
          <div className="flex items-center gap-3 sm:gap-4">
            <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-xl sm:rounded-2xl bg-gradient-to-br from-[#00FFD1] to-emerald-600 flex items-center justify-center flex-shrink-0">
              <Brain className="w-6 h-6 sm:w-8 sm:h-8 text-white" />
            </div>
            <div className="min-w-0">
              <h1 className="text-2xl sm:text-3xl font-bold text-white truncate">AI Engine</h1>
              <p className="text-gray-400 text-sm sm:text-base">AI analyzes market data and finds the best investment opportunities for you</p>
            </div>
          </div>
          
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-[#00FFD1]/10 text-[#00FFD1] hover:bg-[#00FFD1]/20 transition-all self-start sm:self-auto"
          >
            <RefreshCw className={`w-4 h-4 sm:w-5 sm:h-5 ${refreshing ? 'animate-spin' : ''}`} />
            <span className="text-sm sm:text-base">Refresh</span>
          </button>
        </div>

        {signals && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`p-3 sm:p-4 rounded-xl mb-4 sm:mb-6 flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-4 ${
              signals.signal === 'dump_opportunity'
                ? 'bg-emerald-500/10 border border-emerald-500/30'
                : signals.signal === 'pump_risk'
                ? 'bg-red-500/10 border border-red-500/30'
                : 'bg-gray-800/50 border border-gray-700'
            }`}
          >
            <div className="flex items-center gap-3 sm:gap-4">
              {signals.signal === 'dump_opportunity' ? (
                <TrendingDown className="w-5 h-5 sm:w-6 sm:h-6 text-emerald-400 flex-shrink-0" />
              ) : signals.signal === 'pump_risk' ? (
                <AlertTriangle className="w-5 h-5 sm:w-6 sm:h-6 text-red-400 flex-shrink-0" />
              ) : (
                <Activity className="w-5 h-5 sm:w-6 sm:h-6 text-gray-400 flex-shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1">
                  <p className="text-white font-medium text-sm sm:text-base">{signals.message}</p>
                  <InfoTooltip text="Real-time indicators that show whether the market is trending up, down, or staying flat." />
                </div>
                <p className="text-xs sm:text-sm text-gray-400">
                  {signals.dump_count} dump opportunities | {signals.pump_count} pump risks
                </p>
              </div>
            </div>
          </motion.div>
        )}

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6 sm:mb-8">
          <div className="premium-glass-card p-3 sm:p-5">
            <div className="flex items-center gap-2 sm:gap-3 mb-1 sm:mb-2">
              <Wallet className="w-4 h-4 sm:w-5 sm:h-5 text-[#00FFD1]" />
              <span className="text-gray-400 text-xs sm:text-sm truncate">Available USDT</span>
              <InfoTooltip text="Funds ready to invest. This is the amount you can use right now." />
            </div>
            <p className="text-lg sm:text-xl lg:text-2xl font-bold text-white truncate">
              {formatUSD(walletStatus?.available_usdt || 0)}
            </p>
          </div>
          
          <div className="premium-glass-card p-3 sm:p-5">
            <div className="flex items-center gap-2 sm:gap-3 mb-1 sm:mb-2">
              <Target className="w-4 h-4 sm:w-5 sm:h-5 text-blue-400" />
              <span className="text-gray-400 text-xs sm:text-sm truncate">Invested USDT</span>
              <InfoTooltip text="Money currently tied up in active investments." />
            </div>
            <p className="text-lg sm:text-xl lg:text-2xl font-bold text-white truncate">
              {formatUSD(portfolio?.summary?.total_invested_usdt || 0)}
            </p>
          </div>
          
          <div className="premium-glass-card p-3 sm:p-5">
            <div className="flex items-center gap-2 sm:gap-3 mb-1 sm:mb-2">
              <PieChart className="w-4 h-4 sm:w-5 sm:h-5 text-purple-400" />
              <span className="text-gray-400 text-xs sm:text-sm truncate">Current Value</span>
            </div>
            <p className="text-lg sm:text-xl lg:text-2xl font-bold text-white truncate">
              {formatUSD(portfolio?.summary?.total_current_value_usdt || 0)}
            </p>
          </div>
          
          <div className="premium-glass-card p-3 sm:p-5">
            <div className="flex items-center gap-2 sm:gap-3 mb-1 sm:mb-2">
              {(portfolio?.summary?.total_unrealized_pnl_usdt || 0) >= 0 ? (
                <ArrowUpRight className="w-4 h-4 sm:w-5 sm:h-5 text-emerald-400" />
              ) : (
                <ArrowDownRight className="w-4 h-4 sm:w-5 sm:h-5 text-red-400" />
              )}
              <span className="text-gray-400 text-xs sm:text-sm truncate">Unrealized PnL</span>
            </div>
            <p className={`text-lg sm:text-xl lg:text-2xl font-bold truncate ${
              (portfolio?.summary?.total_unrealized_pnl_usdt || 0) >= 0 
                ? 'text-emerald-400' 
                : 'text-red-400'
            }`}>
              {formatUSD(portfolio?.summary?.total_unrealized_pnl_usdt || 0)}
              <span className="text-xs sm:text-sm ml-1 sm:ml-2">
                ({formatPercent(portfolio?.summary?.total_unrealized_pnl_percent || 0)})
              </span>
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
          <div className="lg:col-span-2 space-y-4 sm:space-y-6">
            <div className="premium-glass-card p-4 sm:p-6">
              <div 
                className="flex items-center justify-between cursor-pointer"
                onClick={() => setExpandedSection(expandedSection === 'opportunities' ? '' : 'opportunities')}
              >
                <div className="flex items-center gap-2 sm:gap-3 min-w-0">
                  <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                    <TrendingDown className="w-4 h-4 sm:w-5 sm:h-5 text-emerald-400" />
                  </div>
                  <div className="min-w-0">
                    <h2 className="text-lg sm:text-xl font-bold text-white truncate">5% Dump Opportunities</h2>
                    <p className="text-xs sm:text-sm text-gray-400">
                      {dumpOpportunities?.dump_opportunities?.length || 0} opportunities detected
                    </p>
                  </div>
                </div>
                {expandedSection === 'opportunities' ? (
                  <ChevronUp className="w-4 h-4 sm:w-5 sm:h-5 text-gray-400 flex-shrink-0" />
                ) : (
                  <ChevronDown className="w-4 h-4 sm:w-5 sm:h-5 text-gray-400 flex-shrink-0" />
                )}
              </div>
              
              <AnimatePresence>
                {expandedSection === 'opportunities' && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="mt-3 sm:mt-4 space-y-2 sm:space-y-3">
                      {dumpOpportunities?.dump_opportunities?.length > 0 ? (
                        dumpOpportunities.dump_opportunities.map((opp, idx) => (
                          <div 
                            key={idx}
                            className="p-3 sm:p-4 rounded-xl bg-gray-800/50 border border-gray-700 hover:border-emerald-500/50 transition-all"
                          >
                            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                              <div className="flex items-center gap-2 sm:gap-3 min-w-0">
                                {opp.logo && (
                                  <img src={opp.logo} alt={opp.symbol} className="w-8 h-8 sm:w-10 sm:h-10 rounded-full flex-shrink-0" />
                                )}
                                <div className="min-w-0">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span className="text-white font-bold text-sm sm:text-base">{opp.symbol}</span>
                                    <span className="text-gray-400 text-xs sm:text-sm truncate">{opp.name}</span>
                                  </div>
                                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                                    <span className="text-red-400 text-xs sm:text-sm">
                                      -{opp.dump_magnitude?.toFixed(1)}% ({opp.dump_window})
                                    </span>
                                    <span className={`text-xs px-2 py-0.5 rounded ${
                                      opp.risk_score < 0.4 
                                        ? 'bg-emerald-500/20 text-emerald-400'
                                        : opp.risk_score < 0.6
                                        ? 'bg-yellow-500/20 text-yellow-400'
                                        : 'bg-red-500/20 text-red-400'
                                    }`}>
                                      Risk: {(opp.risk_score * 100).toFixed(0)}%
                                    </span>
                                  </div>
                                </div>
                              </div>
                              <div className="text-left sm:text-right flex-shrink-0">
                                <p className="text-white font-bold text-sm sm:text-base">{formatUSD(opp.price_usdt)}</p>
                                <p className="text-xs text-gray-400">{opp.volume_health} volume</p>
                              </div>
                            </div>
                            <p className="text-xs sm:text-sm text-gray-400 mt-2">{opp.reason}</p>
                          </div>
                        ))
                      ) : (
                        <div className="text-center py-6 sm:py-8 text-gray-400">
                          <TrendingDown className="w-10 h-10 sm:w-12 sm:h-12 mx-auto mb-3 opacity-50" />
                          <p className="text-sm sm:text-base">No 5% dump opportunities detected right now</p>
                          <p className="text-xs sm:text-sm">Check back when the market corrects</p>
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <div className="premium-glass-card p-4 sm:p-6">
              <div 
                className="flex items-center justify-between cursor-pointer"
                onClick={() => setExpandedSection(expandedSection === 'portfolio' ? '' : 'portfolio')}
              >
                <div className="flex items-center gap-2 sm:gap-3 min-w-0">
                  <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl bg-purple-500/20 flex items-center justify-center flex-shrink-0">
                    <PieChart className="w-4 h-4 sm:w-5 sm:h-5 text-purple-400" />
                  </div>
                  <div className="min-w-0">
                    <h2 className="text-lg sm:text-xl font-bold text-white truncate">Active Positions</h2>
                    <p className="text-xs sm:text-sm text-gray-400">
                      {portfolio?.active_positions?.length || 0} positions open
                    </p>
                  </div>
                </div>
                {expandedSection === 'portfolio' ? (
                  <ChevronUp className="w-4 h-4 sm:w-5 sm:h-5 text-gray-400 flex-shrink-0" />
                ) : (
                  <ChevronDown className="w-4 h-4 sm:w-5 sm:h-5 text-gray-400 flex-shrink-0" />
                )}
              </div>
              
              <AnimatePresence>
                {expandedSection === 'portfolio' && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="mt-3 sm:mt-4 space-y-2 sm:space-y-3">
                      {portfolio?.active_positions?.length > 0 ? (
                        portfolio.active_positions.map((pos, idx) => (
                          <div 
                            key={idx}
                            className="p-3 sm:p-4 rounded-xl bg-gray-800/50 border border-gray-700"
                          >
                            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                              <div className="flex items-center gap-2 sm:gap-3 min-w-0">
                                {pos.logo && (
                                  <img src={pos.logo} alt={pos.symbol} className="w-8 h-8 sm:w-10 sm:h-10 rounded-full flex-shrink-0" />
                                )}
                                <div className="min-w-0">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span className="text-white font-bold text-sm sm:text-base">{pos.symbol}</span>
                                    <span className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-300">
                                      {pos.strategy}
                                    </span>
                                  </div>
                                  <p className="text-xs sm:text-sm text-gray-400 truncate">
                                    Entry: {formatUSD(pos.entry_price)} | Qty: {pos.quantity?.toFixed(6)}
                                  </p>
                                </div>
                              </div>
                              <div className="text-left sm:text-right flex-shrink-0">
                                <p className={`font-bold text-sm sm:text-base ${pos.pnl_percent >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                  {formatUSD(pos.unrealized_pnl)} ({formatPercent(pos.pnl_percent)})
                                </p>
                                <p className="text-xs sm:text-sm text-gray-400">
                                  Value: {formatUSD(pos.current_value)}
                                </p>
                              </div>
                            </div>
                            <div className="mt-3 flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2">
                              <span className="text-xs text-gray-500">
                                Invested: {formatUSD(pos.invested_usdt)}
                              </span>
                              <button
                                onClick={() => closePosition(pos.id, pos)}
                                className="text-xs px-3 py-1.5 sm:py-1 rounded bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-all self-start sm:self-auto"
                              >
                                Close Position
                              </button>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="text-center py-6 sm:py-8 text-gray-400">
                          <PieChart className="w-10 h-10 sm:w-12 sm:h-12 mx-auto mb-3 opacity-50" />
                          <p className="text-sm sm:text-base">No active positions</p>
                          <p className="text-xs sm:text-sm">Start investing to build your portfolio</p>
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {rebalancing?.needs_rebalancing && rebalancing?.suggestions?.length > 0 && (
              <div className="premium-glass-card p-4 sm:p-6 border-amber-500/30">
                <div 
                  className="flex items-center justify-between cursor-pointer"
                  onClick={() => setShowRebalancing(!showRebalancing)}
                >
                  <div className="flex items-center gap-2 sm:gap-3 min-w-0">
                    <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl bg-amber-500/20 flex items-center justify-center flex-shrink-0">
                      <Target className="w-4 h-4 sm:w-5 sm:h-5 text-amber-400" />
                    </div>
                    <div className="min-w-0">
                      <h2 className="text-lg sm:text-xl font-bold text-white truncate">Rebalancing Suggestions</h2>
                      <p className="text-xs sm:text-sm text-amber-400">
                        {rebalancing.suggestion_count} actions recommended
                      </p>
                    </div>
                  </div>
                  {showRebalancing ? (
                    <ChevronUp className="w-4 h-4 sm:w-5 sm:h-5 text-gray-400 flex-shrink-0" />
                  ) : (
                    <ChevronDown className="w-4 h-4 sm:w-5 sm:h-5 text-gray-400 flex-shrink-0" />
                  )}
                </div>
                <AnimatePresence>
                  {showRebalancing && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="mt-3 sm:mt-4 space-y-2 sm:space-y-3">
                        {rebalancing.suggestions.map((sug, idx) => (
                          <div 
                            key={idx}
                            className={`p-3 sm:p-4 rounded-xl border ${
                              sug.urgency === 'high' 
                                ? 'bg-red-500/10 border-red-500/30'
                                : sug.urgency === 'medium'
                                ? 'bg-amber-500/10 border-amber-500/30'
                                : 'bg-gray-800/50 border-gray-700'
                            }`}
                          >
                            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                              <div className="flex items-center gap-2 min-w-0">
                                <span className="text-white font-bold text-sm sm:text-base">{sug.symbol}</span>
                                <span className={`text-xs px-2 py-0.5 rounded ${
                                  sug.action === 'reduce' ? 'bg-red-500/20 text-red-400' : 'bg-emerald-500/20 text-emerald-400'
                                }`}>
                                  {sug.action}
                                </span>
                              </div>
                              <span className="text-xs sm:text-sm text-gray-400">{sug.reason}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}
          </div>

          <div className="space-y-4 sm:space-y-6">
            <div className="premium-glass-card p-4 sm:p-6">
              <h2 className="text-lg sm:text-xl font-bold text-white mb-4 sm:mb-6 flex items-center gap-2">
                <Zap className="w-5 h-5 sm:w-6 sm:h-6 text-[#00FFD1]" />
                Quick Invest
              </h2>
              <p className="text-xs text-gray-500 mb-3">Enter an amount and let AI find the best crypto picks for you</p>
              
              <div className="space-y-4">
                <div>
                  <label className="flex items-center gap-1 text-xs sm:text-sm font-medium text-gray-300 mb-2">
                    Investment Amount (USDT)
                    <InfoTooltip text="How much you want to invest in total. The AI will split this across multiple cryptocurrencies." />
                  </label>
                  <input
                    type="number"
                    value={investAmount}
                    onChange={(e) => setInvestAmount(e.target.value)}
                    className="premium-input text-sm sm:text-base"
                    placeholder="100"
                  />
                </div>
                
                <div className="grid grid-cols-3 gap-2">
                  {[100, 250, 500].map((amt) => (
                    <button
                      key={amt}
                      onClick={() => setInvestAmount(amt.toString())}
                      className={`premium-chip text-xs sm:text-sm py-1.5 sm:py-2 ${investAmount === amt.toString() ? 'active' : ''}`}
                    >
                      ${amt}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-gray-400 mt-1">Minimum investment: $100</p>
                
                <button
                  onClick={getRecommendations}
                  disabled={investing}
                  className="premium-btn premium-btn-primary w-full py-3 text-sm sm:text-base disabled:opacity-50"
                >
                  {investing ? (
                    <span className="flex items-center justify-center gap-2">
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                      Analyzing...
                    </span>
                  ) : (
                    'Find Best Investments'
                  )}
                </button>
              </div>
            </div>
            
            <button
              onClick={() => navigate('/invest')}
              className="premium-glass-card p-4 sm:p-5 hover:border-[#00FFD1]/50 transition-all group w-full text-left"
            >
              <Coins className="w-6 h-6 sm:w-8 sm:h-8 text-[#00FFD1] mb-2 group-hover:scale-110 transition-transform" />
              <p className="text-white font-semibold text-sm sm:text-base">Dump Opportunities</p>
              <p className="text-gray-400 text-xs">Buy AI-detected price drops before recovery</p>
            </button>

            <div className="grid grid-cols-2 gap-3 sm:gap-4">
              <button
                onClick={() => setShowBotSettings(true)}
                className="premium-glass-card p-4 sm:p-5 hover:border-[#00FFD1]/50 transition-all group"
              >
                <Bot className="w-6 h-6 sm:w-8 sm:h-8 text-[#00FFD1] mb-2 group-hover:scale-110 transition-transform" />
                <p className="text-white font-semibold text-sm sm:text-base">Trading Bot</p>
                <p className="text-gray-400 text-xs">Automated trading based on your rules</p>
              </button>
              
              <button
                onClick={() => setShowAnalytics(true)}
                className="premium-glass-card p-4 sm:p-5 hover:border-purple-500/50 transition-all group"
              >
                <Activity className="w-6 h-6 sm:w-8 sm:h-8 text-purple-400 mb-2 group-hover:scale-110 transition-transform" />
                <p className="text-white font-semibold text-sm sm:text-base">Analytics</p>
                <p className="text-gray-400 text-xs">Track how your investments perform</p>
              </button>
            </div>
            
            {error && (
              <div className="p-3 sm:p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-2 sm:gap-3">
                <AlertTriangle className="w-4 h-4 sm:w-5 sm:h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <span className="text-red-400 text-xs sm:text-sm">{error}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {showRecommendations && recommendations && (
        <RecommendationsModal
          recommendations={recommendations}
          onClose={() => setShowRecommendations(false)}
          onExecute={executeInvestment}
        />
      )}

      {showBotSettings && (
        <TradingBotSettings onClose={() => setShowBotSettings(false)} />
      )}

      {showAnalytics && (
        <AnalyticsDashboard onClose={() => setShowAnalytics(false)} />
      )}

      <SwapModal
        isOpen={showSwapModal}
        onClose={() => {
          setShowSwapModal(false);
          setPendingInvestment(null);
          setPendingClose(null);
        }}
        initialFromToken={swapFromToken}
        initialToToken={swapToToken}
        initialAmount={swapAmount}
        initialChainId={currentChainId}
        onSwapComplete={(txHash) => {
          if (pendingInvestment) {
            recordInvestmentAfterSwap(txHash);
          } else if (pendingClose) {
            recordCloseAfterSwap(txHash);
          }
          setShowSwapModal(false);
        }}
      />
    </div>
  );
};

export default AIEnginePage;
