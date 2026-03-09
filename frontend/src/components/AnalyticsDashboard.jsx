import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, PieChart, Pie, Cell
} from 'recharts';
import { useWalletAuth } from '../contexts/WalletAuthContext';

const API_BASE = import.meta.env.VITE_BACKEND_URL || '';

const COLORS = ['#00FFD1', '#3B82F6', '#8B5CF6', '#F59E0B', '#EF4444', '#10B981'];

export default function AnalyticsDashboard({ onClose }) {
  const { token } = useWalletAuth();
  const [loading, setLoading] = useState(true);
  const [performance, setPerformance] = useState(null);
  const [dailyReturns, setDailyReturns] = useState([]);
  const [strategyBreakdown, setStrategyBreakdown] = useState({});
  const [coinPerformance, setCoinPerformance] = useState([]);
  const [botAnalytics, setBotAnalytics] = useState(null);
  const [selectedPeriod, setSelectedPeriod] = useState(30);

  useEffect(() => {
    fetchAllData();
  }, [token, selectedPeriod]);

  const fetchAllData = async () => {
    if (!token) return;
    
    setLoading(true);
    try {
      const [perfRes, returnsRes, stratRes, coinsRes, botRes] = await Promise.all([
        fetch(`${API_BASE}/api/analytics/performance?days=${selectedPeriod}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${API_BASE}/api/analytics/daily-returns?days=${selectedPeriod}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${API_BASE}/api/analytics/strategy-breakdown`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${API_BASE}/api/analytics/coin-performance?limit=10`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${API_BASE}/api/analytics/bot-analytics`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
      ]);

      if (perfRes.ok) setPerformance(await perfRes.json());
      if (returnsRes.ok) {
        const data = await returnsRes.json();
        setDailyReturns(data.returns || []);
      }
      if (stratRes.ok) {
        const data = await stratRes.json();
        setStrategyBreakdown(data.strategies || {});
      }
      if (coinsRes.ok) {
        const data = await coinsRes.json();
        setCoinPerformance(data.coins || []);
      }
      if (botRes.ok) setBotAnalytics(await botRes.json());
    } catch (error) {
      console.error('Error fetching analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
        <div className="premium-glass-card p-6 max-w-4xl w-full">
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
          </div>
        </div>
      </div>
    );
  }

  const strategyData = Object.entries(strategyBreakdown).map(([name, stats]) => ({
    name: name.replace('_', ' ').toUpperCase(),
    value: stats.trades,
    pnl: stats.total_pnl,
    winRate: stats.win_rate
  }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className="premium-glass-card p-4 sm:p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto my-4"
      >
        <div className="flex items-center justify-between mb-4 sm:mb-6">
          <h2 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
            <span className="text-xl sm:text-2xl">📊</span> Performance Analytics
          </h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>
        
        <div className="space-y-6">
          <div className="flex gap-2">
            {[7, 30, 90].map(days => (
            <button
              key={days}
              onClick={() => setSelectedPeriod(days)}
              className={`px-3 sm:px-4 py-1.5 sm:py-2 rounded-lg text-xs sm:text-sm font-medium transition-colors ${
                selectedPeriod === days
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {days}D
            </button>
          ))}
          </div>

      {performance && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
          <div className="p-3 sm:p-4 rounded-xl bg-gray-800/50 border border-gray-700">
            <p className="text-xs sm:text-sm text-gray-400">Total Trades</p>
            <p className="text-xl sm:text-2xl font-bold text-white">{performance.total_trades}</p>
          </div>
          <div className="p-3 sm:p-4 rounded-xl bg-gray-800/50 border border-gray-700">
            <p className="text-xs sm:text-sm text-gray-400">Win Rate</p>
            <p className={`text-xl sm:text-2xl font-bold ${performance.win_rate >= 50 ? 'text-green-400' : 'text-red-400'}`}>
              {performance.win_rate}%
            </p>
          </div>
          <div className="p-3 sm:p-4 rounded-xl bg-gray-800/50 border border-gray-700">
            <p className="text-xs sm:text-sm text-gray-400">Total PnL</p>
            <p className={`text-xl sm:text-2xl font-bold ${performance.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {performance.total_pnl >= 0 ? '+' : ''}${performance.total_pnl}
            </p>
          </div>
          <div className="p-3 sm:p-4 rounded-xl bg-gray-800/50 border border-gray-700">
            <p className="text-xs sm:text-sm text-gray-400">ROI</p>
            <p className={`text-xl sm:text-2xl font-bold ${performance.roi_percent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {performance.roi_percent >= 0 ? '+' : ''}{performance.roi_percent}%
            </p>
          </div>
        </div>
      )}

      {performance && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-4">
          <div className="p-3 sm:p-4 rounded-xl bg-gray-800/50 border border-gray-700">
            <div className="flex items-center justify-between mb-1 sm:mb-2">
              <p className="text-xs sm:text-sm text-gray-400">Best Trade</p>
              <span className="text-green-400 font-bold text-sm sm:text-base">
                {performance.best_trade ? `+$${performance.best_trade.pnl}` : '-'}
              </span>
            </div>
            <p className="text-white font-medium text-sm sm:text-base">{performance.best_trade?.symbol || 'N/A'}</p>
          </div>
          <div className="p-3 sm:p-4 rounded-xl bg-gray-800/50 border border-gray-700">
            <div className="flex items-center justify-between mb-1 sm:mb-2">
              <p className="text-xs sm:text-sm text-gray-400">Worst Trade</p>
              <span className="text-red-400 font-bold text-sm sm:text-base">
                {performance.worst_trade ? `$${performance.worst_trade.pnl}` : '-'}
              </span>
            </div>
            <p className="text-white font-medium text-sm sm:text-base">{performance.worst_trade?.symbol || 'N/A'}</p>
          </div>
        </div>
      )}

      {dailyReturns.length > 0 && (
        <div className="p-4 sm:p-6 rounded-xl bg-gray-800/50 border border-gray-700">
          <h3 className="text-base sm:text-lg font-semibold text-white mb-3 sm:mb-4">Cumulative PnL</h3>
          <ResponsiveContainer width="100%" height={200} className="sm:[height:250px]">
            <LineChart data={dailyReturns}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis 
                dataKey="date" 
                stroke="#9CA3AF"
                tick={{ fontSize: 12 }}
                tickFormatter={(val) => val.slice(5)}
              />
              <YAxis stroke="#9CA3AF" tick={{ fontSize: 12 }} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }}
                labelStyle={{ color: '#9CA3AF' }}
              />
              <Line 
                type="monotone" 
                dataKey="cumulative_pnl" 
                stroke="#00FFD1" 
                strokeWidth={2}
                dot={false}
                name="Cumulative PnL"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {dailyReturns.length > 0 && (
        <div className="p-4 sm:p-6 rounded-xl bg-gray-800/50 border border-gray-700">
          <h3 className="text-base sm:text-lg font-semibold text-white mb-3 sm:mb-4">Daily PnL</h3>
          <ResponsiveContainer width="100%" height={180} className="sm:[height:200px]">
            <BarChart data={dailyReturns.slice(-14)}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis 
                dataKey="date" 
                stroke="#9CA3AF"
                tick={{ fontSize: 12 }}
                tickFormatter={(val) => val.slice(5)}
              />
              <YAxis stroke="#9CA3AF" tick={{ fontSize: 12 }} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }}
                labelStyle={{ color: '#9CA3AF' }}
              />
              <Bar 
                dataKey="pnl" 
                name="Daily PnL"
              >
                {dailyReturns.slice(-14).map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.pnl >= 0 ? '#10B981' : '#EF4444'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
        {strategyData.length > 0 && (
          <div className="p-4 sm:p-6 rounded-xl bg-gray-800/50 border border-gray-700">
            <h3 className="text-base sm:text-lg font-semibold text-white mb-3 sm:mb-4">Strategy Breakdown</h3>
            <div className="flex flex-col sm:flex-row items-center gap-4 sm:gap-6">
              <ResponsiveContainer width={120} height={120} className="sm:w-[150px] sm:h-[150px]">
                <PieChart>
                  <Pie
                    data={strategyData}
                    innerRadius={35}
                    outerRadius={50}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {strategyData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-2 w-full sm:w-auto">
                {strategyData.map((strategy, index) => (
                  <div key={strategy.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <div className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full flex-shrink-0" style={{ backgroundColor: COLORS[index % COLORS.length] }}></div>
                      <span className="text-xs sm:text-sm text-gray-300 truncate">{strategy.name}</span>
                    </div>
                    <div className="text-right flex-shrink-0 ml-2">
                      <span className={`text-xs sm:text-sm font-medium ${strategy.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        ${strategy.pnl}
                      </span>
                      <span className="text-xs text-gray-500 ml-1 sm:ml-2">({strategy.winRate}%)</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {botAnalytics && (
          <div className="p-4 sm:p-6 rounded-xl bg-gray-800/50 border border-gray-700">
            <h3 className="text-base sm:text-lg font-semibold text-white mb-3 sm:mb-4 flex items-center gap-2">
              <span>🤖</span> Bot Performance
            </h3>
            <div className="grid grid-cols-2 gap-3 sm:gap-4">
              <div>
                <p className="text-xs sm:text-sm text-gray-400">Bot Trades</p>
                <p className="text-lg sm:text-xl font-bold text-white">{botAnalytics.total_bot_trades}</p>
              </div>
              <div>
                <p className="text-xs sm:text-sm text-gray-400">Win Rate</p>
                <p className={`text-lg sm:text-xl font-bold ${botAnalytics.win_rate >= 50 ? 'text-green-400' : 'text-red-400'}`}>
                  {botAnalytics.win_rate}%
                </p>
              </div>
              <div>
                <p className="text-xs sm:text-sm text-gray-400">Bot PnL</p>
                <p className={`text-lg sm:text-xl font-bold ${botAnalytics.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  ${botAnalytics.total_pnl}
                </p>
              </div>
              <div>
                <p className="text-xs sm:text-sm text-gray-400">Bot ROI</p>
                <p className={`text-lg sm:text-xl font-bold ${botAnalytics.roi_percent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {botAnalytics.roi_percent}%
                </p>
              </div>
            </div>
            <div className="mt-3 sm:mt-4 pt-3 sm:pt-4 border-t border-gray-700">
              <div className="flex justify-between text-xs sm:text-sm">
                <span className="text-gray-400">Stop-Losses Triggered</span>
                <span className="text-red-400">{botAnalytics.stop_losses_triggered}</span>
              </div>
              <div className="flex justify-between text-xs sm:text-sm mt-2">
                <span className="text-gray-400">Take-Profits Triggered</span>
                <span className="text-green-400">{botAnalytics.take_profits_triggered}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {coinPerformance.length > 0 && (
        <div className="p-4 sm:p-6 rounded-xl bg-gray-800/50 border border-gray-700">
          <h3 className="text-base sm:text-lg font-semibold text-white mb-3 sm:mb-4">Top Performing Coins</h3>
          <div className="overflow-x-auto -mx-4 sm:mx-0 px-4 sm:px-0">
            <table className="w-full min-w-[500px]">
              <thead>
                <tr className="text-left text-xs sm:text-sm text-gray-400 border-b border-gray-700">
                  <th className="pb-2 sm:pb-3">Coin</th>
                  <th className="pb-2 sm:pb-3">Trades</th>
                  <th className="pb-2 sm:pb-3">Win</th>
                  <th className="pb-2 sm:pb-3">PnL</th>
                  <th className="pb-2 sm:pb-3">ROI</th>
                </tr>
              </thead>
              <tbody>
                {coinPerformance.map((coin, index) => (
                  <tr key={coin.symbol} className="border-b border-gray-700/50">
                    <td className="py-2 sm:py-3">
                      <div className="flex items-center gap-2">
                        {coin.logo && <img src={coin.logo} alt={coin.symbol} className="w-5 h-5 sm:w-6 sm:h-6 rounded-full" />}
                        <span className="text-white font-medium text-xs sm:text-sm">{coin.symbol}</span>
                      </div>
                    </td>
                    <td className="py-2 sm:py-3 text-gray-300 text-xs sm:text-sm">{coin.trades}</td>
                    <td className="py-2 sm:py-3">
                      <span className={`text-xs sm:text-sm ${coin.win_rate >= 50 ? 'text-green-400' : 'text-red-400'}`}>
                        {coin.win_rate}%
                      </span>
                    </td>
                    <td className="py-2 sm:py-3">
                      <span className={`text-xs sm:text-sm ${coin.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {coin.total_pnl >= 0 ? '+' : ''}${coin.total_pnl}
                      </span>
                    </td>
                    <td className="py-2 sm:py-3">
                      <span className={`text-xs sm:text-sm ${coin.roi_percent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {coin.roi_percent >= 0 ? '+' : ''}{coin.roi_percent}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {(!performance || performance.total_trades === 0) && (
        <div className="p-6 sm:p-8 rounded-xl bg-gray-800/50 border border-gray-700 text-center">
          <p className="text-lg sm:text-xl text-gray-400 mb-2">No Trading Data Yet</p>
          <p className="text-xs sm:text-sm text-gray-500">
            Start investing to see your performance analytics here
          </p>
        </div>
      )}
        </div>
      </motion.div>
    </div>
  );
}
