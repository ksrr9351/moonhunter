import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  History, Play, TrendingUp, TrendingDown, DollarSign, 
  BarChart2, Percent, AlertTriangle, ArrowLeft 
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useWalletAuth } from '../contexts/WalletAuthContext';
import { backtestingService } from '../services/backtestingService';
import PremiumNavbar from './PremiumNavbar';
import InfoTooltip from './InfoTooltip';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';

function BacktestPage() {
  const { isAuthenticated, token } = useWalletAuth();
  const [strategies, setStrategies] = useState([]);
  const [selectedStrategy, setSelectedStrategy] = useState(null);
  const [params, setParams] = useState({});
  const [initialCapital, setInitialCapital] = useState(10000);
  const [periodDays, setPeriodDays] = useState(90);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchStrategies();
  }, [token]);

  const fetchStrategies = async () => {
    if (!token) return;
    try {
      const data = await backtestingService.getStrategies(token);
      setStrategies(data.strategies || []);
      if (data.strategies?.length > 0) {
        selectStrategy(data.strategies[0]);
      }
    } catch (error) {
      console.error('Failed to fetch strategies:', error);
    }
  };

  const selectStrategy = (strategy) => {
    setSelectedStrategy(strategy);
    const defaultParams = {};
    strategy.params?.forEach(p => {
      defaultParams[p.name] = p.default;
    });
    setParams(defaultParams);
    setResults(null);
  };

  const runBacktest = async () => {
    if (!selectedStrategy) return;
    
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const endDate = new Date().toISOString();
      const startDate = new Date(Date.now() - periodDays * 24 * 60 * 60 * 1000).toISOString();
      
      const result = await backtestingService.runBacktest(
        token,
        selectedStrategy.id,
        initialCapital,
        startDate,
        endDate,
        params
      );
      if (result.error) {
        setError(result.error);
      } else {
        setResults(result);
      }
    } catch (err) {
      console.error('Backtest failed:', err);
      setError(err.message || 'Failed to run backtest. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  return (
    <div className="premium-bg min-h-screen overflow-x-hidden">
      {isAuthenticated && <PremiumNavbar />}
      <div className="container mx-auto px-3 sm:px-4 lg:px-6 py-4 sm:py-6 lg:py-8">
          {!isAuthenticated && (
            <Link to="/" className="flex items-center gap-2 text-gray-400 hover:text-[#00FFD1] mb-4 transition-colors">
              <ArrowLeft className="w-4 h-4" /> Back to Home
            </Link>
          )}
          
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6 sm:mb-8"
          >
            <div className="flex items-center gap-3 sm:gap-4">
              <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-xl sm:rounded-2xl bg-gradient-to-br from-[#00FFD1] to-emerald-600 flex items-center justify-center flex-shrink-0">
                <History className="w-6 h-6 sm:w-8 sm:h-8 text-white" />
              </div>
              <div className="min-w-0">
                <h1 className="text-2xl sm:text-3xl font-bold text-white truncate">Strategy Backtesting</h1>
                <p className="text-gray-400 text-sm sm:text-base">See how a trading strategy would have performed in the past — no real money involved</p>
              </div>
            </div>
          </motion.div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1 space-y-6">
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                className="premium-glass-card p-6"
              >
                <h2 className="text-lg font-semibold text-white mb-4">Select Strategy</h2>
                <p className="text-xs text-gray-500 mt-1 mb-3">Pick a trading approach to test. Each one uses different rules to buy and sell.</p>
                
                <div className="space-y-2">
                  {strategies.map((strategy) => (
                    <button
                      key={strategy.id}
                      onClick={() => selectStrategy(strategy)}
                      className={`w-full text-left p-4 rounded-xl transition-all ${
                        selectedStrategy?.id === strategy.id
                          ? 'bg-[#00FFD1] text-black'
                          : 'bg-white/5 text-gray-300 hover:bg-white/10 border border-white/10'
                      }`}
                    >
                      <div className="font-medium">{strategy.name}</div>
                      <div className="text-sm opacity-80">{strategy.description}</div>
                    </button>
                  ))}
                </div>
              </motion.div>

              {selectedStrategy && (
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 }}
                  className="premium-glass-card p-6"
                >
                  <h2 className="text-lg font-semibold text-white mb-4">Parameters</h2>
                  <p className="text-xs text-gray-500 mt-1 mb-3">Adjust the settings below or use the defaults — they're a good starting point.</p>
                  
                  <div className="space-y-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <label className="text-sm text-gray-400">Initial Capital ($)</label>
                        <InfoTooltip text="The amount of money the simulation starts with. This is not real money." />
                      </div>
                      <input
                        type="number"
                        value={initialCapital}
                        onChange={(e) => setInitialCapital(Number(e.target.value))}
                        className="premium-input"
                        min={100}
                        max={1000000}
                      />
                    </div>
                    
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <label className="text-sm text-gray-400">Period (days)</label>
                        <InfoTooltip text="How far back in time to test. Longer periods give more reliable results." />
                      </div>
                      <select
                        value={periodDays}
                        onChange={(e) => setPeriodDays(Number(e.target.value))}
                        className="premium-input"
                      >
                        <option value={30}>30 Days</option>
                        <option value={60}>60 Days</option>
                        <option value={90}>90 Days</option>
                        <option value={180}>180 Days</option>
                        <option value={365}>1 Year</option>
                      </select>
                    </div>

                    {selectedStrategy.params?.filter(p => p.type === 'number').map((param) => (
                      <div key={param.name}>
                        <label className="text-sm text-gray-400 block mb-1">{param.label}</label>
                        <input
                          type="number"
                          value={params[param.name] ?? param.default}
                          onChange={(e) => setParams({ ...params, [param.name]: Number(e.target.value) })}
                          className="premium-input"
                          min={param.min}
                          max={param.max}
                        />
                      </div>
                    ))}
                  </div>

                  <button
                    onClick={runBacktest}
                    disabled={loading}
                    className="w-full mt-6 py-3 bg-[#00FFD1] hover:bg-[#00FFD1]/80 disabled:bg-gray-600 text-black rounded-xl font-medium transition-all flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <div className="animate-spin rounded-full h-5 w-5 border-2 border-black border-t-transparent"></div>
                        Running...
                      </>
                    ) : (
                      <>
                        <Play className="w-5 h-5" /> Run Simulation
                      </>
                    )}
                  </button>
                </motion.div>
              )}
            </div>

            <div className="lg:col-span-2">
              {results ? (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="space-y-6"
                >
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="premium-glass-card p-4">
                      <div className="flex items-center gap-2 text-gray-400 mb-2">
                        <DollarSign className="w-4 h-4 text-[#00FFD1]" />
                        <span className="text-sm">Final Capital</span>
                        <InfoTooltip text="What the initial investment would be worth at the end of the test period." />
                      </div>
                      <div className="text-xl font-bold text-white">
                        {formatCurrency(results.final_capital)}
                      </div>
                    </div>

                    <div className="premium-glass-card p-4">
                      <div className="flex items-center gap-2 text-gray-400 mb-2">
                        <Percent className="w-4 h-4 text-[#00FFD1]" />
                        <span className="text-sm">Total Return</span>
                        <InfoTooltip text="The percentage gain or loss over the entire test period." />
                      </div>
                      <div className={`text-xl font-bold ${results.total_return >= 0 ? 'text-[#00FFD1]' : 'text-red-400'}`}>
                        {results.total_return >= 0 ? '+' : ''}{results.total_return.toFixed(2)}%
                      </div>
                    </div>

                    <div className="premium-glass-card p-4">
                      <div className="flex items-center gap-2 text-gray-400 mb-2">
                        <TrendingUp className="w-4 h-4 text-[#00FFD1]" />
                        <span className="text-sm">Win Rate</span>
                        <InfoTooltip text="The percentage of trades that were profitable." />
                      </div>
                      <div className="text-xl font-bold text-white">
                        {results.win_rate.toFixed(1)}%
                      </div>
                    </div>

                    <div className="premium-glass-card p-4">
                      <div className="flex items-center gap-2 text-gray-400 mb-2">
                        <AlertTriangle className="w-4 h-4 text-red-400" />
                        <span className="text-sm">Max Drawdown</span>
                        <InfoTooltip text="The biggest drop from peak to bottom — shows worst-case risk." />
                      </div>
                      <div className="text-xl font-bold text-red-400">
                        -{results.max_drawdown.toFixed(2)}%
                      </div>
                    </div>
                  </div>

                  <div className="premium-glass-card p-6">
                    <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                      <BarChart2 className="w-5 h-5 text-[#00FFD1]" /> Equity Curve
                    </h3>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={results.daily_equity}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                          <XAxis 
                            dataKey="date" 
                            stroke="#9CA3AF"
                            tick={{ fontSize: 12 }}
                            tickFormatter={(value) => value.slice(5)}
                          />
                          <YAxis 
                            stroke="#9CA3AF"
                            tick={{ fontSize: 12 }}
                            tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                          />
                          <Tooltip 
                            contentStyle={{ backgroundColor: '#1E293B', border: '1px solid #475569', borderRadius: '8px' }}
                            labelStyle={{ color: '#94A3B8' }}
                            formatter={(value) => [formatCurrency(value), 'Equity']}
                          />
                          <ReferenceLine y={initialCapital} stroke="#6366F1" strokeDasharray="5 5" />
                          <Line 
                            type="monotone" 
                            dataKey="equity" 
                            stroke="#00FFD1" 
                            strokeWidth={2}
                            dot={false}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="premium-glass-card p-6">
                      <h3 className="text-lg font-semibold text-white mb-4">Performance Metrics</h3>
                      <div className="space-y-3">
                        <div className="flex justify-between">
                          <span className="text-gray-400">Annualized Return</span>
                          <span className={`font-medium ${results.annualized_return >= 0 ? 'text-[#00FFD1]' : 'text-red-400'}`}>
                            {results.annualized_return >= 0 ? '+' : ''}{results.annualized_return.toFixed(2)}%
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <div className="flex items-center gap-2">
                            <span className="text-gray-400">Sharpe Ratio</span>
                            <InfoTooltip text="Measures risk-adjusted returns. Higher is better. Above 1.0 is generally considered good." />
                          </div>
                          <span className="text-white font-medium">{results.sharpe_ratio.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between">
                          <div className="flex items-center gap-2">
                            <span className="text-gray-400">Profit Factor</span>
                            <InfoTooltip text="Total profits divided by total losses. Above 1.0 means the strategy is profitable." />
                          </div>
                          <span className="text-white font-medium">{results.profit_factor.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">Total Trades</span>
                          <span className="text-white font-medium">{results.total_trades}</span>
                        </div>
                      </div>
                    </div>

                    <div className="premium-glass-card p-6">
                      <h3 className="text-lg font-semibold text-white mb-4">Trade Statistics</h3>
                      <div className="space-y-3">
                        <div className="flex justify-between">
                          <span className="text-gray-400">Winning Trades</span>
                          <span className="text-[#00FFD1] font-medium">{results.winning_trades}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">Losing Trades</span>
                          <span className="text-red-400 font-medium">{results.losing_trades}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">Avg Win</span>
                          <span className="text-[#00FFD1] font-medium">{formatCurrency(results.avg_win)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">Avg Loss</span>
                          <span className="text-red-400 font-medium">{formatCurrency(results.avg_loss)}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {results.trades?.length > 0 && (
                    <div className="premium-glass-card p-6">
                      <h3 className="text-lg font-semibold text-white mb-4">Recent Trades</h3>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="text-gray-400 border-b border-white/10">
                              <th className="text-left py-2">Coin</th>
                              <th className="text-left py-2">Entry</th>
                              <th className="text-right py-2">Size</th>
                              <th className="text-right py-2">PnL</th>
                              <th className="text-right py-2">Return</th>
                            </tr>
                          </thead>
                          <tbody>
                            {results.trades.slice(0, 10).map((trade, idx) => (
                              <tr key={idx} className="border-b border-white/5">
                                <td className="py-2 text-white font-medium">{trade.coin}</td>
                                <td className="py-2 text-gray-400">{trade.entry_date?.slice(0, 10)}</td>
                                <td className="py-2 text-right text-gray-300">{formatCurrency(trade.position_size)}</td>
                                <td className={`py-2 text-right font-medium ${trade.pnl >= 0 ? 'text-[#00FFD1]' : 'text-red-400'}`}>
                                  {trade.pnl >= 0 ? '+' : ''}{formatCurrency(trade.pnl)}
                                </td>
                                <td className={`py-2 text-right ${trade.pnl_percent >= 0 ? 'text-[#00FFD1]' : 'text-red-400'}`}>
                                  {trade.pnl_percent >= 0 ? '+' : ''}{trade.pnl_percent.toFixed(1)}%
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </motion.div>
              ) : error ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="premium-glass-card p-12 flex flex-col items-center justify-center text-center h-full min-h-[400px] border border-red-500/30"
                >
                  <AlertTriangle className="w-16 h-16 text-red-400/60 mb-4" />
                  <h3 className="text-xl font-semibold text-red-400 mb-2">Backtest Failed</h3>
                  <p className="text-gray-400 max-w-md">{error}</p>
                  <p className="text-gray-500 text-sm mt-3">This usually means the data provider (CoinGecko) couldn't supply historical prices. Try again in a moment, or ask your admin to set the <span className="text-[#00FFD1] font-mono">COINGECKO_API_KEY</span> environment variable.</p>
                </motion.div>
              ) : (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="premium-glass-card p-12 flex flex-col items-center justify-center text-center h-full min-h-[400px]"
                >
                  <History className="w-16 h-16 text-[#00FFD1]/30 mb-4" />
                  <h3 className="text-xl font-semibold text-gray-400 mb-2">Ready to Test a Strategy</h3>
                  <p className="text-gray-500">Choose a strategy on the left and click Run Simulation to see how it would have performed</p>
                </motion.div>
              )}
            </div>
          </div>
      </div>
    </div>
  );
}

export default BacktestPage;
