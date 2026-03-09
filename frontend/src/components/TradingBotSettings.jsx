import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { useWalletAuth } from '../contexts/WalletAuthContext';


const API_BASE = import.meta.env.VITE_BACKEND_URL || '';

export default function TradingBotSettings({ onClose }) {
  const { token } = useWalletAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState(null);
  const [message, setMessage] = useState(null);
  const [settings, setSettings] = useState({
    enabled: false,
    execution_mode: 'dex',
    chain_id: 1,
    max_daily_investment: 100,
    max_per_trade: 50,
    min_dump_threshold: 5,
    max_risk_score: 0.6,
    cooldown_minutes: 30,
    stop_loss_percent: 10,
    take_profit_percent: 15,
    auto_stop_loss: true,
    auto_take_profit: true,
    pause_on_loss: true,
    max_daily_loss: 50,
    slippage_tolerance: 1.0,
    coin_blacklist: [],
    coin_whitelist: []
  });
  
  const showMessage = (type, text) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 5000);
  };

  useEffect(() => {
    if (token) {
      fetchBotStatus();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchBotStatus = async () => {
    if (!token) {
      setLoading(false);
      return;
    }
    
    try {
      setLoading(true);
      setMessage(null);
      
      const response = await fetch(`${API_BASE}/api/trading-bot/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setStatus(data);
        if (data.settings) {
          setSettings(prev => ({ ...prev, ...data.settings }));
        }
      } else if (response.status === 401 || response.status === 403) {
        console.log('Bot settings: waiting for authentication...');
      } else if (response.status === 429) {
        console.log('Rate limited, will retry later');
      } else {
        const errorData = await response.json().catch(() => ({}));
        console.error('Error fetching bot status:', errorData);
      }
    } catch (error) {
      console.error('Error fetching bot status:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    if (!token) {
      showMessage('error', 'Please connect your wallet first');
      return;
    }
    
    try {
      setSaving(true);
      const response = await fetch(`${API_BASE}/api/trading-bot/settings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(settings)
      });
      
      if (response.ok) {
        const savedSettings = await response.json();
        showMessage('success', 'Settings saved (DEX Real mode)');
        fetchBotStatus();
      } else if (response.status === 401 || response.status === 403) {
        showMessage('error', 'Please reconnect your wallet to save settings');
      } else {
        const error = await response.json().catch(() => ({}));
        showMessage('error', error.detail || 'Failed to save settings');
      }
    } catch (error) {
      showMessage('error', 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const toggleBot = async (enabled) => {
    if (!token) {
      showMessage('error', 'Please connect your wallet first');
      return;
    }
    
    try {
      const endpoint = enabled ? 'enable' : 'disable';
      const response = await fetch(`${API_BASE}/api/trading-bot/${endpoint}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        setSettings(prev => ({ ...prev, enabled }));
        showMessage('success', enabled ? 'Bot enabled - now monitoring markets' : 'Bot disabled');
        fetchBotStatus();
      } else if (response.status === 401 || response.status === 403) {
        showMessage('error', 'Please reconnect your wallet');
      } else {
        showMessage('error', 'Failed to toggle bot');
      }
    } catch (error) {
      showMessage('error', 'Failed to toggle bot');
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
            <span className="text-xl sm:text-2xl">🤖</span> Trading Bot Settings
          </h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>
        
        <div className="space-y-6">
      {message && (
        <div className={`p-4 rounded-lg ${
          message.type === 'error' 
            ? 'bg-red-500/20 border border-red-500/50 text-red-400' 
            : message.type === 'warning'
              ? 'bg-yellow-500/20 border border-yellow-500/50 text-yellow-400'
              : 'bg-green-500/20 border border-green-500/50 text-green-400'
        }`}>
          {message.text}
        </div>
      )}

      <div className="p-4 sm:p-6 rounded-xl bg-gray-800/50 border border-gray-700">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4 sm:mb-6">
          <div className="min-w-0">
            <h2 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
              <span className="text-xl sm:text-2xl">🤖</span> Automated Trading Bot
            </h2>
            <p className="text-xs sm:text-sm text-gray-400 mt-1">Let the AI invest for you based on market opportunities</p>
          </div>
          <div className="flex items-center gap-3 self-start sm:self-auto">
            <span className={`px-2 sm:px-3 py-1 rounded-full text-xs sm:text-sm ${settings.enabled ? 'bg-green-500/20 text-green-400' : 'bg-gray-600/50 text-gray-400'}`}>
              {settings.enabled ? 'Active' : 'Inactive'}
            </span>
            <button
              onClick={() => toggleBot(!settings.enabled)}
              className={`relative w-12 sm:w-14 h-6 sm:h-7 rounded-full transition-colors flex-shrink-0 ${settings.enabled ? 'bg-green-500' : 'bg-gray-600'}`}
            >
              <div className={`absolute top-0.5 sm:top-1 w-4 sm:w-5 h-4 sm:h-5 rounded-full bg-white transition-all ${settings.enabled ? 'left-6 sm:left-8' : 'left-1'}`}></div>
            </button>
          </div>
        </div>

        {status?.daily_stats && (
          <div className="grid grid-cols-3 gap-2 sm:gap-4 p-3 sm:p-4 rounded-lg bg-gray-900/50 mb-4 sm:mb-6">
            <div className="text-center">
              <p className="text-xs sm:text-sm text-gray-400">Trades Today</p>
              <p className="text-lg sm:text-2xl font-bold text-white">{status.daily_stats.trades_today || 0}</p>
            </div>
            <div className="text-center">
              <p className="text-xs sm:text-sm text-gray-400">Invested</p>
              <p className="text-lg sm:text-2xl font-bold text-blue-400">${(status.daily_stats.invested_today || 0).toFixed(0)}</p>
            </div>
            <div className="text-center">
              <p className="text-xs sm:text-sm text-gray-400">PnL</p>
              <p className={`text-lg sm:text-2xl font-bold ${(status.daily_stats.pnl_today || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {(status.daily_stats.pnl_today || 0) >= 0 ? '+' : ''}${(status.daily_stats.pnl_today || 0).toFixed(0)}
              </p>
            </div>
          </div>
        )}

        <div className="border-t border-gray-700 my-4 sm:my-6"></div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
          <div className="space-y-3 sm:space-y-4">
            <h3 className="text-base sm:text-lg font-semibold text-white">Investment Limits</h3>
            
            <div className="space-y-2">
              <label className="block text-xs sm:text-sm text-gray-300">Max Daily Investment (USDT)</label>
              <input
                type="number"
                value={settings.max_daily_investment}
                onChange={(e) => setSettings(prev => ({ ...prev, max_daily_investment: parseFloat(e.target.value) || 0 }))}
                className="w-full px-3 sm:px-4 py-2 rounded-lg bg-gray-900 border border-gray-700 text-sm sm:text-base text-white focus:border-blue-500 focus:outline-none"
                min={10}
                max={10000}
              />
              <p className="text-xs text-gray-500">Maximum amount the bot can invest per day</p>
            </div>

            <div className="space-y-2">
              <label className="block text-xs sm:text-sm text-gray-300">Max Per Trade (USDT)</label>
              <input
                type="number"
                value={settings.max_per_trade}
                onChange={(e) => setSettings(prev => ({ ...prev, max_per_trade: parseFloat(e.target.value) || 0 }))}
                className="w-full px-3 sm:px-4 py-2 rounded-lg bg-gray-900 border border-gray-700 text-sm sm:text-base text-white focus:border-blue-500 focus:outline-none"
                min={10}
                max={1000}
              />
              <p className="text-xs text-gray-500">Maximum amount per individual trade</p>
            </div>

            <div className="space-y-2">
              <label className="block text-xs sm:text-sm text-gray-300">Cooldown Between Trades (min)</label>
              <input
                type="number"
                value={settings.cooldown_minutes}
                onChange={(e) => setSettings(prev => ({ ...prev, cooldown_minutes: parseInt(e.target.value) || 30 }))}
                className="w-full px-3 sm:px-4 py-2 rounded-lg bg-gray-900 border border-gray-700 text-sm sm:text-base text-white focus:border-blue-500 focus:outline-none"
                min={5}
                max={1440}
              />
            </div>
          </div>

          <div className="space-y-3 sm:space-y-4">
            <h3 className="text-base sm:text-lg font-semibold text-white">Risk Management</h3>
            
            <div className="space-y-2">
              <label className="block text-xs sm:text-sm text-gray-300">Min Dump Threshold (%)</label>
              <div className="flex items-center gap-2 sm:gap-4">
                <input
                  type="range"
                  value={settings.min_dump_threshold}
                  onChange={(e) => setSettings(prev => ({ ...prev, min_dump_threshold: parseFloat(e.target.value) }))}
                  min={3}
                  max={20}
                  step={0.5}
                  className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                />
                <span className="text-white text-sm w-12 sm:w-16 text-right">{settings.min_dump_threshold}%</span>
              </div>
              <p className="text-xs text-gray-500">Only invest when price drops by this much</p>
            </div>

            <div className="space-y-2">
              <label className="block text-xs sm:text-sm text-gray-300">Max Risk Score</label>
              <div className="flex items-center gap-2 sm:gap-4">
                <input
                  type="range"
                  value={settings.max_risk_score * 100}
                  onChange={(e) => setSettings(prev => ({ ...prev, max_risk_score: parseFloat(e.target.value) / 100 }))}
                  min={10}
                  max={100}
                  step={5}
                  className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                />
                <span className="text-white text-sm w-12 sm:w-16 text-right">{(settings.max_risk_score * 100).toFixed(0)}%</span>
              </div>
              <p className="text-xs text-gray-500">Maximum risk tolerance (lower = safer)</p>
            </div>

            <div className="flex items-center justify-between p-2.5 sm:p-3 rounded-lg bg-gray-900/50">
              <div className="min-w-0 mr-3">
                <label className="text-xs sm:text-sm text-gray-300">Pause on Loss</label>
                <p className="text-xs text-gray-500 hidden sm:block">Stop trading if daily loss exceeds limit</p>
              </div>
              <button
                onClick={() => setSettings(prev => ({ ...prev, pause_on_loss: !prev.pause_on_loss }))}
                className={`relative w-10 sm:w-12 h-5 sm:h-6 rounded-full transition-colors flex-shrink-0 ${settings.pause_on_loss ? 'bg-blue-500' : 'bg-gray-600'}`}
              >
                <div className={`absolute top-0.5 w-4 sm:w-5 h-4 sm:h-5 rounded-full bg-white transition-all ${settings.pause_on_loss ? 'left-5 sm:left-6' : 'left-0.5'}`}></div>
              </button>
            </div>

            {settings.pause_on_loss && (
              <div className="space-y-2">
                <label className="block text-xs sm:text-sm text-gray-300">Max Daily Loss (USDT)</label>
                <input
                  type="number"
                  value={settings.max_daily_loss}
                  onChange={(e) => setSettings(prev => ({ ...prev, max_daily_loss: parseFloat(e.target.value) || 0 }))}
                  className="w-full px-3 sm:px-4 py-2 rounded-lg bg-gray-900 border border-gray-700 text-sm sm:text-base text-white focus:border-blue-500 focus:outline-none"
                  min={10}
                  max={1000}
                />
              </div>
            )}
          </div>
        </div>

        <div className="border-t border-gray-700 my-4 sm:my-6"></div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
          <div className="space-y-3 sm:space-y-4">
            <h3 className="text-base sm:text-lg font-semibold text-white">Stop-Loss & Take-Profit</h3>
            
            <div className="flex items-center justify-between p-2.5 sm:p-3 rounded-lg bg-gray-900/50">
              <div className="min-w-0 mr-3">
                <label className="text-xs sm:text-sm text-gray-300">Auto Stop-Loss</label>
                <p className="text-xs text-gray-500 hidden sm:block">Automatically close losing positions</p>
              </div>
              <button
                onClick={() => setSettings(prev => ({ ...prev, auto_stop_loss: !prev.auto_stop_loss }))}
                className={`relative w-10 sm:w-12 h-5 sm:h-6 rounded-full transition-colors flex-shrink-0 ${settings.auto_stop_loss ? 'bg-red-500' : 'bg-gray-600'}`}
              >
                <div className={`absolute top-0.5 w-4 sm:w-5 h-4 sm:h-5 rounded-full bg-white transition-all ${settings.auto_stop_loss ? 'left-5 sm:left-6' : 'left-0.5'}`}></div>
              </button>
            </div>

            {settings.auto_stop_loss && (
              <div className="space-y-2">
                <label className="block text-xs sm:text-sm text-gray-300">Stop-Loss (%)</label>
                <div className="flex items-center gap-2 sm:gap-4">
                  <input
                    type="range"
                    value={settings.stop_loss_percent}
                    onChange={(e) => setSettings(prev => ({ ...prev, stop_loss_percent: parseFloat(e.target.value) }))}
                    min={1}
                    max={50}
                    step={1}
                    className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-red-500"
                  />
                  <span className="text-red-400 text-sm w-12 sm:w-16 text-right">-{settings.stop_loss_percent}%</span>
                </div>
              </div>
            )}

            <div className="flex items-center justify-between p-2.5 sm:p-3 rounded-lg bg-gray-900/50">
              <div className="min-w-0 mr-3">
                <label className="text-xs sm:text-sm text-gray-300">Auto Take-Profit</label>
                <p className="text-xs text-gray-500 hidden sm:block">Automatically lock in profits</p>
              </div>
              <button
                onClick={() => setSettings(prev => ({ ...prev, auto_take_profit: !prev.auto_take_profit }))}
                className={`relative w-10 sm:w-12 h-5 sm:h-6 rounded-full transition-colors flex-shrink-0 ${settings.auto_take_profit ? 'bg-green-500' : 'bg-gray-600'}`}
              >
                <div className={`absolute top-0.5 w-4 sm:w-5 h-4 sm:h-5 rounded-full bg-white transition-all ${settings.auto_take_profit ? 'left-5 sm:left-6' : 'left-0.5'}`}></div>
              </button>
            </div>

            {settings.auto_take_profit && (
              <div className="space-y-2">
                <label className="block text-xs sm:text-sm text-gray-300">Take-Profit (%)</label>
                <div className="flex items-center gap-2 sm:gap-4">
                  <input
                    type="range"
                    value={settings.take_profit_percent}
                    onChange={(e) => setSettings(prev => ({ ...prev, take_profit_percent: parseFloat(e.target.value) }))}
                    min={1}
                    max={100}
                    step={1}
                    className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-green-500"
                  />
                  <span className="text-green-400 text-sm w-12 sm:w-16 text-right">+{settings.take_profit_percent}%</span>
                </div>
              </div>
            )}
          </div>

          <div className="space-y-3 sm:space-y-4">
            <h3 className="text-base sm:text-lg font-semibold text-white">Status</h3>
            {status?.active_triggers > 0 ? (
              <div className="p-4 rounded-lg bg-gray-900/50">
                <p className="text-gray-300">
                  <span className="text-2xl font-bold text-blue-400">{status.active_triggers}</span> active position triggers
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Stop-loss and take-profit orders are being monitored
                </p>
              </div>
            ) : (
              <div className="p-4 rounded-lg bg-gray-900/50">
                <p className="text-gray-400">No active triggers</p>
                <p className="text-xs text-gray-500">Triggers will be set automatically for new bot trades</p>
              </div>
            )}

            {status?.last_trade_time && (
              <div className="p-4 rounded-lg bg-gray-900/50">
                <p className="text-sm text-gray-400">Last Trade</p>
                <p className="text-white">
                  {new Date(status.last_trade_time).toLocaleString()}
                </p>
              </div>
            )}

            <div className="space-y-3">
              <h3 className="text-base sm:text-lg font-semibold text-white">Execution Mode</h3>
              <div className="flex gap-2">
                <div className="flex-1 px-3 py-2 rounded-lg text-xs sm:text-sm font-medium bg-green-600 text-white text-center">
                  DEX (Real Trading)
                </div>
              </div>
              
              <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/30">
                <p className="text-xs text-gray-300">
                  DEX Mode: Bot executes real trades via 1inch DEX aggregator. Requires wallet confirmation for each trade.
                </p>
              </div>
              
              <div className="space-y-2">
                <label className="block text-xs sm:text-sm text-gray-300">Slippage Tolerance (%)</label>
                <div className="flex items-center gap-2 sm:gap-4">
                  <input
                    type="range"
                    value={settings.slippage_tolerance}
                    onChange={(e) => setSettings(prev => ({ ...prev, slippage_tolerance: parseFloat(e.target.value) }))}
                    min={0.1}
                    max={5}
                    step={0.1}
                    className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-green-500"
                  />
                  <span className="text-green-400 text-sm w-12 sm:w-16 text-right">{settings.slippage_tolerance}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row justify-end gap-2 sm:gap-4 pt-4 sm:pt-6 mt-4 sm:mt-6 border-t border-gray-700">
          <button
            onClick={fetchBotStatus}
            className="px-4 sm:px-6 py-2 rounded-lg border border-gray-600 text-gray-300 hover:bg-gray-800 transition-colors text-sm sm:text-base"
          >
            Refresh
          </button>
          <button
            onClick={saveSettings}
            disabled={saving}
            className="px-4 sm:px-6 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium transition-colors disabled:opacity-50 text-sm sm:text-base"
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>

      {status?.recent_trades && status.recent_trades.length > 0 && (
        <div className="p-6 rounded-xl bg-gray-800/50 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Recent Bot Trades</h3>
          <div className="space-y-2">
            {status.recent_trades.map((trade, index) => (
              <div key={trade.id || index} className="flex items-center justify-between p-3 rounded-lg bg-gray-900/50">
                <div className="flex items-center gap-3">
                  <span className="px-2 py-1 rounded text-xs bg-green-500/20 text-green-400 border border-green-500/30">
                    {trade.action?.toUpperCase() || 'BUY'}
                  </span>
                  <span className="font-medium text-white">{trade.symbol}</span>
                </div>
                <div className="text-right">
                  <p className="text-gray-300">${(trade.amount || 0).toFixed(2)}</p>
                  <p className="text-xs text-gray-500">
                    {new Date(trade.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
        </div>
      </motion.div>
    </div>
  );
}
