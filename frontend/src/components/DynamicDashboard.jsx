import React, { useState, useEffect, useMemo } from 'react';
import { useWalletAuth } from '../contexts/WalletAuthContext';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, Wallet, Target, Zap, DollarSign, ArrowUpRight, ArrowDownRight, Send, Download, BarChart2, Sparkles } from 'lucide-react';
import PremiumNavbar from './PremiumNavbar';
import { cryptoService } from '../services/cryptoService';
import { LiveConnectionStatus } from './LivePriceIndicator';
import { usePriceStream } from '../contexts/PriceStreamContext';
import { AnimatePresence } from 'framer-motion';
import TradingViewChart from './TradingViewChart';
import InfoTooltip from './InfoTooltip';
import { WidgetErrorBoundary } from './ErrorBoundary';

const API_URL = import.meta.env.VITE_BACKEND_URL || '';

const DynamicDashboard = () => {
  const { user, walletAddress, token } = useWalletAuth();

  const [loading, setLoading] = useState(true);
  const [portfolios, setPortfolios] = useState([]);
  const [walletStatus, setWalletStatus] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [autoInvestConfig, setAutoInvestConfig] = useState(null);
  const [topCoins, setTopCoins] = useState([]);
  const [chartPeriod, setChartPeriod] = useState('7D');
  const [chartData, setChartData] = useState([]);
  const [selectedCoin, setSelectedCoin] = useState(null);
  const [investSummary, setInvestSummary] = useState(null);

  useEffect(() => {
    if (token) {
      fetchDashboardData();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);

      const headers = { Authorization: `Bearer ${token}` };

      const [portfoliosRes, walletRes, transactionsRes, autoInvestRes, coinsData, investRes] = await Promise.all([
        axios.get(`${API_URL}/api/portfolios`, { headers }).catch(() => ({ data: [] })),
        axios.get(`${API_URL}/api/ai-engine/wallet-status`, { headers }).catch(() => ({ data: { connected: false, available_usdt: 0, invested_usdt: 0, total_usdt: 0 } })),
        axios.get(`${API_URL}/api/transactions?limit=10`, { headers }).catch(() => ({ data: [] })),
        axios.get(`${API_URL}/api/auto-invest/config`, { headers }).catch(() => ({ data: null })),
        cryptoService.getTopCoins(5),
        axios.get(`${API_URL}/api/invest/summary`, { headers }).catch(() => ({ data: null }))
      ]);

      setPortfolios(portfoliosRes.data || []);
      setWalletStatus(walletRes.data || { connected: false, available_usdt: 0, invested_usdt: 0, total_usdt: 0 });
      setTransactions(transactionsRes.data || []);
      setAutoInvestConfig(autoInvestRes.data);
      setTopCoins(coinsData || []);
      setInvestSummary(investRes.data);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const portfolioValue = useMemo(() => {
    if (investSummary?.total_current_value > 0) return investSummary.total_current_value;
    return walletStatus?.total_usdt || 0;
  }, [investSummary, walletStatus]);

  const generateChartData = (period) => {
    const days = { '7D': 7, '1M': 30, '3M': 90, '1Y': 365 }[period] || 7;
    const data = [];
    const currentValue = portfolioValue;

    for (let i = days; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);

      data.push({
        date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        value: Math.round(currentValue)
      });
    }

    setChartData(data);
  };

  useEffect(() => {
    if (!loading) {
      generateChartData(chartPeriod);
    }
  }, [portfolioValue, loading, chartPeriod]);

  const roi = useMemo(() => {
    if (investSummary && investSummary.total_invested > 0) {
      return investSummary.total_pnl_percentage?.toFixed(2) || 0;
    }
    return 0;
  }, [investSummary]);

  const isPositiveROI = roi >= 0;

  if (loading) {
    return (
      <div className="premium-bg min-h-screen overflow-x-hidden">
        <PremiumNavbar />
        <div className="container mx-auto px-4 py-8">
          <div className="flex flex-col items-center justify-center h-64">
            <div className="w-16 h-16 border-4 border-[#00FFD1]/30 border-t-[#00FFD1] rounded-full animate-spin mb-4"></div>
            <p className="text-gray-400">Loading your dashboard...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="premium-bg min-h-screen overflow-x-hidden">
      <PremiumNavbar />
      <div className="container mx-auto px-3 sm:px-4 lg:px-6 py-4 sm:py-6 lg:py-8 overflow-x-hidden">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6 sm:mb-8">
          <div className="flex items-center gap-3 sm:gap-4">
            <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-xl sm:rounded-2xl bg-gradient-to-br from-[#00FFD1] to-emerald-600 flex items-center justify-center flex-shrink-0">
              <BarChart2 className="w-6 h-6 sm:w-8 sm:h-8 text-white" />
            </div>
            <div className="min-w-0">
              <h1 className="text-2xl sm:text-3xl font-bold text-white truncate">
                Welcome back, <span className="gradient-text">{user?.username || (walletAddress ? `${walletAddress.slice(0, 6)}...${walletAddress.slice(-4)}` : 'User')}</span>!
              </h1>
              <p className="text-gray-400 text-sm sm:text-base">Here's a quick look at your investments and market activity</p>
            </div>
          </div>
          <div className="flex-shrink-0">
            <LiveConnectionStatus />
          </div>
        </div>

        {portfolios.length === 0 && !loading && (
          <div className="mb-6 sm:mb-8 premium-glass-card p-5 sm:p-6 bg-gradient-to-r from-[#00FFD1]/5 to-purple-500/5 border-[#00FFD1]/20">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#00FFD1]/20 to-purple-500/20 flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-6 h-6 text-[#00FFD1]" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-lg font-bold text-white mb-1">Getting Started</h3>
                <p className="text-sm text-gray-400 mb-4">Here's how to begin your investment journey in 3 simple steps:</p>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <Link to="/wallet" className="flex items-center gap-3 p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-all border border-white/10 group">
                    <div className="w-8 h-8 rounded-lg bg-[#00FFD1]/20 flex items-center justify-center flex-shrink-0">
                      <span className="text-[#00FFD1] font-bold text-sm">1</span>
                    </div>
                    <div className="min-w-0">
                      <p className="text-white font-medium text-sm">Fund Wallet</p>
                      <p className="text-gray-500 text-xs">Add crypto to your wallet</p>
                    </div>
                  </Link>
                  <Link to="/ai-engine" className="flex items-center gap-3 p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-all border border-white/10 group">
                    <div className="w-8 h-8 rounded-lg bg-[#00FFD1]/20 flex items-center justify-center flex-shrink-0">
                      <span className="text-[#00FFD1] font-bold text-sm">2</span>
                    </div>
                    <div className="min-w-0">
                      <p className="text-white font-medium text-sm">Get AI Picks</p>
                      <p className="text-gray-500 text-xs">Let AI find opportunities</p>
                    </div>
                  </Link>
                  <Link to="/invest" className="flex items-center gap-3 p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-all border border-white/10 group">
                    <div className="w-8 h-8 rounded-lg bg-[#00FFD1]/20 flex items-center justify-center flex-shrink-0">
                      <span className="text-[#00FFD1] font-bold text-sm">3</span>
                    </div>
                    <div className="min-w-0">
                      <p className="text-white font-medium text-sm">Start Investing</p>
                      <p className="text-gray-500 text-xs">Build your portfolio</p>
                    </div>
                  </Link>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 lg:gap-6 mb-6 sm:mb-8">
          <div className="premium-glass-card p-4 sm:p-6">
            <div className="flex items-center justify-between mb-3 sm:mb-4">
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl bg-gradient-to-br from-[#00FFD1]/20 to-[#00D4A8]/20 flex items-center justify-center flex-shrink-0">
                <Wallet className="w-5 h-5 sm:w-6 sm:h-6 text-[#00FFD1]" />
              </div>
              <span className={`px-2 sm:px-3 py-1 rounded-full text-xs sm:text-sm font-semibold ${isPositiveROI ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                {isPositiveROI ? '+' : ''}{roi}%
              </span>
            </div>
            <p className="text-gray-400 text-xs sm:text-sm mb-1 sm:mb-2 flex items-center gap-1">
              Portfolio Value
              <InfoTooltip text="The total current value of all your crypto investments combined." />
            </p>
            <h3 className="text-xl sm:text-2xl lg:text-3xl font-bold text-white truncate">${portfolioValue.toLocaleString()}</h3>
          </div>

          <div className="premium-glass-card p-4 sm:p-6">
            <div className="flex items-center justify-between mb-3 sm:mb-4">
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl bg-gradient-to-br from-[#00FFD1]/20 to-[#00D4A8]/20 flex items-center justify-center flex-shrink-0">
                <Target className="w-5 h-5 sm:w-6 sm:h-6 text-[#00FFD1]" />
              </div>
              {isPositiveROI ? (
                <TrendingUp className="w-4 h-4 sm:w-5 sm:h-5 text-green-400" />
              ) : (
                <TrendingDown className="w-4 h-4 sm:w-5 sm:h-5 text-red-400" />
              )}
            </div>
            <p className="text-gray-400 text-xs sm:text-sm mb-1 sm:mb-2 flex items-center gap-1">
              Total ROI
              <InfoTooltip text="Return on Investment — shows how much profit or loss you've made as a percentage of what you invested." />
            </p>
            <h3 className={`text-xl sm:text-2xl lg:text-3xl font-bold ${isPositiveROI ? 'text-green-400' : 'text-red-400'}`}>
              {isPositiveROI ? '+' : ''}{roi}%
            </h3>
          </div>

          <div className="premium-glass-card p-4 sm:p-6">
            <div className="flex items-center justify-between mb-3 sm:mb-4">
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl bg-gradient-to-br from-[#00FFD1]/20 to-[#00D4A8]/20 flex items-center justify-center flex-shrink-0">
                <DollarSign className="w-5 h-5 sm:w-6 sm:h-6 text-[#00FFD1]" />
              </div>
            </div>
            <p className="text-gray-400 text-xs sm:text-sm mb-1 sm:mb-2 flex items-center gap-1">
              Active Portfolios
              <InfoTooltip text="The number of different crypto coins you're currently invested in." />
            </p>
            <h3 className="text-xl sm:text-2xl lg:text-3xl font-bold text-white">{investSummary?.active_positions_count || portfolios.length}</h3>
          </div>

          <div className="premium-glass-card p-4 sm:p-6">
            <div className="flex items-center justify-between mb-3 sm:mb-4">
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl bg-gradient-to-br from-[#00FFD1]/20 to-[#00D4A8]/20 flex items-center justify-center flex-shrink-0">
                <Zap className="w-5 h-5 sm:w-6 sm:h-6 text-[#00FFD1]" />
              </div>
              <span className={`px-2 sm:px-3 py-1 rounded-full text-xs font-semibold ${
                autoInvestConfig?.enabled ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'
              }`}>
                {autoInvestConfig?.enabled ? 'Active' : 'Inactive'}
              </span>
            </div>
            <p className="text-gray-400 text-xs sm:text-sm mb-1 sm:mb-2 flex items-center gap-1">
              Auto-Invest
              <InfoTooltip text="Automatic investing puts money into crypto on a schedule you set — daily, weekly, or monthly." />
            </p>
            <h3 className="text-xl sm:text-2xl lg:text-3xl font-bold text-white">
              {autoInvestConfig?.enabled ? `$${autoInvestConfig.amount}` : 'Off'}
            </h3>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6 lg:gap-8">
          <div className="lg:col-span-2 space-y-4 sm:space-y-6 lg:space-y-8">
            <WidgetErrorBoundary name="Portfolio Performance">
            <div className="premium-glass-card p-4 sm:p-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4 sm:mb-6">
                <div>
                  <h2 className="text-lg sm:text-xl lg:text-2xl font-bold text-white">Portfolio Performance</h2>
                  <p className="text-xs text-gray-500 mt-1">Track how your total investment value changes over time</p>
                </div>
                <div className="flex gap-1 sm:gap-2 overflow-x-auto scrollbar-hide">
                  {['7D', '1M', '3M', '1Y'].map((period) => (
                    <button
                      key={period}
                      onClick={() => {
                        setChartPeriod(period);
                        generateChartData(period);
                      }}
                      className={`px-3 sm:px-4 py-1.5 sm:py-2 rounded-lg text-xs sm:text-sm font-semibold transition-all flex-shrink-0 ${
                        chartPeriod === period
                          ? 'bg-[#00FFD1] text-black'
                          : 'bg-white/5 text-gray-400 hover:bg-white/10'
                      }`}
                    >
                      {period}
                    </button>
                  ))}
                </div>
              </div>

              <div className="h-[200px] sm:h-[250px] lg:h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="date" stroke="#9CA3AF" tick={{ fontSize: 10 }} />
                    <YAxis stroke="#9CA3AF" tick={{ fontSize: 10 }} width={50} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1F2937',
                        border: '1px solid #374151',
                        borderRadius: '8px',
                        color: '#fff',
                        fontSize: '12px'
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#00FFD1"
                      strokeWidth={2}
                      dot={{ fill: '#00FFD1', r: 3 }}
                      activeDot={{ r: 5 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
            </WidgetErrorBoundary>

            <WidgetErrorBoundary name="Recent Transactions">
            <div className="premium-glass-card p-4 sm:p-6">
              <div className="flex items-center justify-between mb-4 sm:mb-6">
                <h2 className="text-lg sm:text-xl lg:text-2xl font-bold text-white">Recent Transactions</h2>
                <Link to="/wallet" className="text-[#00FFD1] hover:text-[#00D4A8] text-xs sm:text-sm font-semibold">
                  View All
                </Link>
              </div>

              <div className="space-y-3 sm:space-y-4">
                {transactions.length > 0 ? (
                  transactions.slice(0, 5).map((tx, index) => (
                    <div key={index} className="flex items-center justify-between p-3 sm:p-4 rounded-xl bg-white/5 hover:bg-white/10 transition-colors">
                      <div className="flex items-center gap-3 sm:gap-4 min-w-0">
                        <div className={`w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                          tx.type === 'buy' ? 'bg-green-500/20' : 'bg-red-500/20'
                        }`}>
                          {tx.type === 'buy' ? (
                            <ArrowDownRight className="w-4 h-4 sm:w-5 sm:h-5 text-green-400" />
                          ) : (
                            <ArrowUpRight className="w-4 h-4 sm:w-5 sm:h-5 text-red-400" />
                          )}
                        </div>
                        <div className="min-w-0">
                          <p className="text-white font-semibold text-sm sm:text-base truncate">{tx.type === 'buy' ? 'Buy' : 'Sell'} {tx.coin_symbol}</p>
                          <p className="text-gray-400 text-xs sm:text-sm">{new Date(tx.created_at).toLocaleDateString()}</p>
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0 ml-2">
                        <p className="text-white font-bold text-sm sm:text-base">${tx.amount}</p>
                        <p className="text-gray-400 text-xs sm:text-sm">{tx.quantity} {tx.coin_symbol}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-6 sm:py-8">
                    <p className="text-gray-400 text-sm sm:text-base">You haven't made any trades yet</p>
                    <Link to="/invest" className="text-[#00FFD1] hover:text-[#00D4A8] text-sm font-semibold mt-2 inline-block">
                      Make Your First Investment →
                    </Link>
                  </div>
                )}
              </div>
            </div>
            </WidgetErrorBoundary>
          </div>

          <div className="space-y-4 sm:space-y-6 lg:space-y-8">
            <WidgetErrorBoundary name="Market Top Coins">
            <div className="premium-glass-card p-4 sm:p-6">
              <h2 className="text-lg sm:text-xl lg:text-2xl font-bold text-white mb-4 sm:mb-6">Market Top Coins</h2>
              <div className="space-y-3 sm:space-y-4">
                {Array.isArray(topCoins) && topCoins.length > 0 ? topCoins.map((coin) => {
                  const price = coin.price || coin.quote?.USD?.price || 0;
                  const change24h = coin.change24h || coin.quote?.USD?.percent_change_24h || 0;
                  const isPositive = change24h >= 0;

                  return (
                    <div 
                      key={coin.id} 
                      className="flex items-center justify-between p-3 sm:p-4 rounded-xl bg-white/5 hover:bg-white/10 transition-colors cursor-pointer group"
                      onClick={() => setSelectedCoin({ ...coin, price, change24h })}
                    >
                      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
                        {coin.logo ? (
                          <img src={coin.logo} alt={coin.name} className="w-8 h-8 sm:w-10 sm:h-10 rounded-full flex-shrink-0" />
                        ) : (
                          <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-gradient-to-br from-[#00FFD1]/20 to-[#00D4A8]/20 flex items-center justify-center flex-shrink-0">
                            <span className="text-base sm:text-lg font-bold text-[#00FFD1]">{coin.symbol.charAt(0)}</span>
                          </div>
                        )}
                        <div className="min-w-0">
                          <p className="text-white font-semibold text-sm sm:text-base truncate">{coin.symbol}</p>
                          <p className="text-gray-400 text-xs sm:text-sm truncate">{coin.name}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 sm:gap-4 flex-shrink-0">
                        <div className="text-right">
                          <p className="text-white font-bold text-xs sm:text-sm">${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                          <p className={`text-xs sm:text-sm font-semibold flex items-center justify-end gap-1 ${
                            isPositive ? 'text-green-400' : 'text-red-400'
                          }`}>
                            {isPositive ? <TrendingUp className="w-3 h-3 sm:w-4 sm:h-4" /> : <TrendingDown className="w-3 h-3 sm:w-4 sm:h-4" />}
                            {isPositive ? '+' : ''}{change24h.toFixed(2)}%
                          </p>
                        </div>
                        <BarChart2 className="w-4 h-4 sm:w-5 sm:h-5 text-gray-500 group-hover:text-[#00FFD1] transition-colors hidden sm:block" />
                      </div>
                    </div>
                  );
                }) : (
                  <div className="text-center py-6 sm:py-8 text-gray-400">
                    <p className="text-sm sm:text-base">Market data is loading — check back in a moment</p>
                  </div>
                )}
              </div>
            </div>
            </WidgetErrorBoundary>

            <div className="premium-glass-card p-4 sm:p-6">
              <h2 className="text-lg sm:text-xl lg:text-2xl font-bold text-white mb-4 sm:mb-6">Quick Actions</h2>
              <div className="space-y-3 sm:space-y-4">
                <Link
                  to="/wallet"
                  className="flex items-center justify-between p-3 sm:p-4 rounded-xl bg-gradient-to-r from-[#00FFD1]/10 to-[#00D4A8]/10 hover:from-[#00FFD1]/20 hover:to-[#00D4A8]/20 transition-all group"
                >
                  <div className="flex items-center gap-2 sm:gap-3">
                    <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-[#00FFD1] flex items-center justify-center flex-shrink-0">
                      <Download className="w-4 h-4 sm:w-5 sm:h-5 text-black" />
                    </div>
                    <span className="text-white font-semibold text-sm sm:text-base">Deposit Funds</span>
                  </div>
                  <ArrowUpRight className="w-4 h-4 sm:w-5 sm:h-5 text-[#00FFD1] group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
                </Link>

                <Link
                  to="/wallet"
                  className="flex items-center justify-between p-3 sm:p-4 rounded-xl bg-gradient-to-r from-[#00FFD1]/10 to-[#00D4A8]/10 hover:from-[#00FFD1]/20 hover:to-[#00D4A8]/20 transition-all group"
                >
                  <div className="flex items-center gap-2 sm:gap-3">
                    <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-[#00FFD1] flex items-center justify-center flex-shrink-0">
                      <Send className="w-4 h-4 sm:w-5 sm:h-5 text-black" />
                    </div>
                    <span className="text-white font-semibold text-sm sm:text-base">Withdraw Funds</span>
                  </div>
                  <ArrowUpRight className="w-4 h-4 sm:w-5 sm:h-5 text-[#00FFD1] group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
                </Link>

                <Link
                  to="/invest"
                  className="flex items-center justify-between p-3 sm:p-4 rounded-xl bg-gradient-to-r from-[#00FFD1] to-[#00D4A8] hover:opacity-90 transition-all group"
                >
                  <div className="flex items-center gap-2 sm:gap-3">
                    <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-black/20 flex items-center justify-center flex-shrink-0">
                      <Zap className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                    </div>
                    <span className="text-black font-bold text-sm sm:text-base">Start Investing</span>
                  </div>
                  <ArrowUpRight className="w-4 h-4 sm:w-5 sm:h-5 text-black group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {selectedCoin && (
          <TradingViewChart
            symbol={selectedCoin.symbol}
            name={selectedCoin.name}
            currentPrice={selectedCoin.price}
            change24h={selectedCoin.change24h}
            onClose={() => setSelectedCoin(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
};

export default DynamicDashboard;
