import React, { useState, useEffect } from 'react';
import { useWalletAuth } from '../contexts/WalletAuthContext';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Zap, Settings, TrendingUp, AlertCircle, CheckCircle, Sparkles, DollarSign, Calendar, Target } from 'lucide-react';
import PremiumNavbar from './PremiumNavbar';
import InfoTooltip from './InfoTooltip';
import { formatUSD } from '../utils/formatters';
const API_URL = import.meta.env.VITE_BACKEND_URL || '';

const AIAutoInvestPage = () => {
  const { token } = useWalletAuth();
  
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      if (!token) {
        setConfig({
          enabled: false,
          amount: 100,
          frequency: 'weekly',
          risk_tolerance: 'moderate'
        });
        return;
      }
      
      const response = await axios.get(`${API_URL}/api/auto-invest/config`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setConfig(response.data);
    } catch (error) {
      console.error('Error fetching config:', error);
      setError('Failed to load configuration');
      setConfig({
        enabled: false,
        amount: 100,
        frequency: 'weekly',
        risk_tolerance: 'moderate'
      });
    }
  };

  const updateConfig = async (updates) => {
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      const response = await axios.put(
        `${API_URL}/api/auto-invest/config`,
        updates,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      
      setConfig(response.data);
      setSuccess('Configuration updated successfully!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to update configuration');
    } finally {
      setLoading(false);
    }
  };

  const toggleAutoInvest = () => {
    if (config) {
      updateConfig({ enabled: !config.enabled });
    }
  };

  if (!config) {
    return (
      <div className="premium-bg min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 sm:w-16 sm:h-16 border-4 border-[#00FFD1]/30 border-t-[#00FFD1] rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-400 text-sm sm:text-base">Loading...</p>
        </div>
      </div>
    );
  }

  const monthlyEstimate = 
    config.frequency === 'daily' ? config.investment_amount * 30 :
    config.frequency === 'weekly' ? config.investment_amount * 4 :
    config.investment_amount;

  return (
    <div className="premium-bg min-h-screen overflow-x-hidden">
      <PremiumNavbar />

      <div className="container mx-auto px-3 sm:px-4 lg:px-6 py-4 sm:py-6 lg:py-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6 sm:mb-8">
          <div className="flex items-center gap-3 sm:gap-4">
            <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-xl sm:rounded-2xl bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center flex-shrink-0">
              <Zap className="w-6 h-6 sm:w-8 sm:h-8 text-white" />
            </div>
            <div className="min-w-0">
              <h1 className="text-2xl sm:text-3xl font-bold text-white truncate">AI Auto-Invest</h1>
              <p className="text-gray-400 text-sm sm:text-base">Set it and forget it — AI invests for you on a schedule you choose</p>
            </div>
          </div>
        </div>

        <div className={`premium-glass-card p-5 sm:p-8 mb-6 sm:mb-8 ${
          config.enabled
            ? 'bg-gradient-to-r from-green-500/10 to-emerald-500/10 border-green-500/30'
            : 'bg-gradient-to-r from-gray-500/10 to-slate-500/10 border-gray-500/30'
        }`}>
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 sm:gap-6">
            <div className="flex items-center gap-3 sm:gap-4">
              <div className={`w-12 h-12 sm:w-16 sm:h-16 rounded-xl sm:rounded-2xl flex items-center justify-center flex-shrink-0 ${
                config.enabled 
                  ? 'bg-gradient-to-br from-[#00FFD1] to-[#00D4A8]' 
                  : 'bg-gradient-to-br from-gray-500 to-slate-500'
              }`}>
                {config.enabled ? (
                  <CheckCircle className="w-6 h-6 sm:w-8 sm:h-8 text-white" />
                ) : (
                  <AlertCircle className="w-6 h-6 sm:w-8 sm:h-8 text-white" />
                )}
              </div>
              <div className="min-w-0">
                <h3 className="text-xl sm:text-2xl font-bold text-white mb-1">
                  {config.enabled ? 'Auto-Invest is Active 🚀' : 'Auto-Invest is Inactive'}
                </h3>
                <p className="text-gray-400 text-sm sm:text-base">
                  {config.enabled
                    ? `Investing ${formatUSD(config.investment_amount)} ${config.frequency}`
                    : 'Enable to start automated investing'}
                </p>
              </div>
            </div>
            <button
              onClick={toggleAutoInvest}
              disabled={loading}
              className={`px-6 sm:px-8 py-3 sm:py-4 rounded-xl sm:rounded-2xl font-semibold transition-all disabled:opacity-50 whitespace-nowrap text-sm sm:text-base w-full md:w-auto ${
                config.enabled
                  ? 'bg-gradient-to-r from-red-500 to-pink-500 text-white hover:shadow-lg'
                  : 'premium-btn premium-btn-primary'
              }`}
            >
              {config.enabled ? 'Disable' : 'Enable Auto-Invest'}
            </button>
          </div>
        </div>

        {success && (
          <div className="p-3 sm:p-4 rounded-xl sm:rounded-2xl bg-green-500/10 border border-green-500/20 text-[#00FFD1] text-xs sm:text-sm mb-6 sm:mb-8 text-center font-semibold">
            ✓ {success}
          </div>
        )}

        {error && (
          <div className="p-3 sm:p-4 rounded-xl sm:rounded-2xl bg-red-500/10 border border-red-500/20 flex items-start gap-2 sm:gap-3 mb-6 sm:mb-8">
            <AlertCircle className="w-4 h-4 sm:w-5 sm:h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <span className="text-red-400 text-xs sm:text-sm">{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 sm:gap-8">
          <div className="premium-glass-card p-6 sm:p-8">
            <h2 className="text-xl sm:text-2xl font-bold text-white mb-4 sm:mb-6 flex items-center gap-2">
              <Settings className="w-5 h-5 sm:w-6 sm:h-6" />
              Configuration
            </h2>
            
            <div className="space-y-4 sm:space-y-6">
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-300 mb-2">
                  Investment Amount per Cycle
                  <InfoTooltip text="How much to invest each time. For example, $100 weekly means $100 is automatically invested every week." />
                </label>
                <div className="relative">
                  <DollarSign className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 sm:w-5 sm:h-5 text-gray-400" />
                  <input
                    type="number"
                    value={config.investment_amount}
                    onChange={(e) => setConfig({ ...config, investment_amount: parseFloat(e.target.value) })}
                    className="premium-input pl-10 sm:pl-12 text-sm sm:text-base"
                  />
                </div>
              </div>

              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-300 mb-2">
                  Frequency
                  <InfoTooltip text="How often to invest. Daily spreads risk most, monthly invests in larger chunks." />
                </label>
                <div className="relative">
                  <Calendar className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 sm:w-5 sm:h-5 text-gray-400" />
                  <select
                    value={config.frequency}
                    onChange={(e) => setConfig({ ...config, frequency: e.target.value })}
                    className="premium-input pl-10 sm:pl-12 text-sm sm:text-base"
                  >
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-300 mb-2">
                  Risk Tolerance
                  <InfoTooltip text="Controls which cryptocurrencies AI picks. Conservative sticks to top coins like Bitcoin and Ethereum. Aggressive includes smaller, higher-potential coins." />
                </label>
                <div className="relative">
                  <Target className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 sm:w-5 sm:h-5 text-gray-400" />
                  <select
                    value={config.risk_tolerance}
                    onChange={(e) => setConfig({ ...config, risk_tolerance: e.target.value })}
                    className="premium-input pl-10 sm:pl-12 text-sm sm:text-base"
                  >
                    <option value="conservative">Conservative — Stick to top coins (safest)</option>
                    <option value="moderate">Moderate — Mix of stable and growth coins</option>
                    <option value="aggressive">Aggressive — Include emerging coins (riskiest)</option>
                  </select>
                </div>
              </div>

              <div className="p-4 sm:p-6 rounded-xl sm:rounded-2xl bg-white/5 border border-white/10">
                <div className="flex items-center justify-between">
                  <div className="min-w-0 mr-4">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="font-semibold text-white text-sm sm:text-base">Auto-Rebalance</p>
                      <InfoTooltip text="Automatically adjusts your portfolio to stay balanced. If one coin grows too large, it sells some and buys others." />
                    </div>
                    <p className="text-xs sm:text-sm text-gray-400">Automatically rebalance portfolio</p>
                  </div>
                  <button
                    onClick={() => setConfig({ ...config, auto_rebalance: !config.auto_rebalance })}
                    className={`premium-toggle flex-shrink-0 ${config.auto_rebalance ? 'active' : ''}`}
                  >
                    <div className="premium-toggle-handle"></div>
                  </button>
                </div>
              </div>

              <button
                onClick={() => updateConfig({
                  investment_amount: config.investment_amount,
                  frequency: config.frequency,
                  risk_tolerance: config.risk_tolerance,
                  auto_rebalance: config.auto_rebalance
                })}
                disabled={loading}
                className="premium-btn premium-btn-primary w-full disabled:opacity-50 text-sm sm:text-base py-3 sm:py-4"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="w-4 h-4 sm:w-5 sm:h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Saving...
                  </span>
                ) : (
                  'Save Configuration'
                )}
              </button>
            </div>
          </div>

          <div className="space-y-4 sm:space-y-8">
            <div className="premium-glass-card p-6 sm:p-8 bg-gradient-to-br from-[#00FFD1]/5 to-gray-800/5 border-[#00FFD1]/30">
              <h2 className="text-xl sm:text-2xl font-bold text-white mb-4 sm:mb-6 flex items-center gap-2">
                <Sparkles className="w-5 h-5 sm:w-6 sm:h-6 text-[#00FFD1]" />
                How It Works
              </h2>
              <ul className="space-y-3 sm:space-y-4">
                <li className="flex items-start gap-2 sm:gap-3">
                  <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-gradient-to-br from-[#00FFD1] to-gray-800 flex items-center justify-center flex-shrink-0">
                    <span className="text-white text-xs sm:text-sm font-bold">1</span>
                  </div>
                  <p className="text-gray-300 text-xs sm:text-sm pt-1">Our AI studies the crypto market and matches picks to your comfort level</p>
                </li>
                <li className="flex items-start gap-2 sm:gap-3">
                  <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-gradient-to-br from-[#00FFD1] to-gray-800 flex items-center justify-center flex-shrink-0">
                    <span className="text-white text-xs sm:text-sm font-bold">2</span>
                  </div>
                  <p className="text-gray-300 text-xs sm:text-sm pt-1">Your money is invested automatically based on the schedule you set</p>
                </li>
                <li className="flex items-start gap-2 sm:gap-3">
                  <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-gradient-to-br from-[#00FFD1] to-gray-800 flex items-center justify-center flex-shrink-0">
                    <span className="text-white text-xs sm:text-sm font-bold">3</span>
                  </div>
                  <p className="text-gray-300 text-xs sm:text-sm pt-1">If the market shifts, AI adjusts your holdings to keep things balanced</p>
                </li>
                <li className="flex items-start gap-2 sm:gap-3">
                  <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-gradient-to-br from-[#00FFD1] to-gray-800 flex items-center justify-center flex-shrink-0">
                    <span className="text-white text-xs sm:text-sm font-bold">4</span>
                  </div>
                  <p className="text-gray-300 text-xs sm:text-sm pt-1">By investing regularly, you smooth out price swings over time (dollar-cost averaging)</p>
                </li>
              </ul>
            </div>

            <div className="premium-glass-card p-6 sm:p-8">
              <h2 className="text-xl sm:text-2xl font-bold text-white mb-4 sm:mb-6">Projected Investment</h2>
              <div className="space-y-3 sm:space-y-4">
                <div className="flex justify-between items-center p-3 sm:p-4 rounded-xl sm:rounded-2xl bg-white/5">
                  <span className="text-gray-400 text-sm sm:text-base">Per Cycle</span>
                  <span className="text-lg sm:text-xl font-bold text-white">{formatUSD(config.investment_amount)}</span>
                </div>
                <div className="flex justify-between items-center p-3 sm:p-4 rounded-xl sm:rounded-2xl bg-white/5">
                  <span className="text-gray-400 text-sm sm:text-base">Frequency</span>
                  <span className="text-lg sm:text-xl font-bold text-white capitalize">{config.frequency}</span>
                </div>
                <div className="flex justify-between items-center p-3 sm:p-4 rounded-xl sm:rounded-2xl bg-gradient-to-r from-[#00FFD1]/10 to-gray-800/10 border border-[#00FFD1]/30">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-300 font-semibold text-sm sm:text-base">Monthly Estimate</span>
                    <InfoTooltip text="The estimated total amount that will be invested per month based on your settings." />
                  </div>
                  <span className="text-xl sm:text-2xl font-bold gradient-text">
                    ${monthlyEstimate.toFixed(2)}
                  </span>
                </div>
              </div>
            </div>

            <div className="premium-glass-card p-4 sm:p-6 bg-[#00FFD1]/5 border-[#00FFD1]/30">
              <p className="text-[#00FFD1] text-xs sm:text-sm flex items-start gap-2">
                <AlertCircle className="w-4 h-4 sm:w-5 sm:h-5 flex-shrink-0 mt-0.5" />
                <span>
                  <strong>Note:</strong> Auto-invest requires sufficient wallet balance. Make sure to maintain adequate funds for scheduled investments.
                </span>
              </p>
            </div>

            <Link
              to="/wallet"
              className="block premium-btn premium-btn-primary w-full text-center text-sm sm:text-base py-3 sm:py-4"
            >
              Manage Wallet Funds
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIAutoInvestPage;
