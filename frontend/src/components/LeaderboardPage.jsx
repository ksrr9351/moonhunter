import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Trophy, TrendingUp, Users, Eye, Crown, Medal, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useWalletAuth } from '../contexts/WalletAuthContext';
import { socialTradingService } from '../services/socialTradingService';
import PremiumNavbar from './PremiumNavbar';
import InfoTooltip from './InfoTooltip';

function LeaderboardPage() {
  const { token, isAuthenticated } = useWalletAuth();
  const [leaderboard, setLeaderboard] = useState([]);
  const [period, setPeriod] = useState('all');
  const [loading, setLoading] = useState(true);
  const [selectedTrader, setSelectedTrader] = useState(null);
  const [traderDetails, setTraderDetails] = useState(null);
  const [myStats, setMyStats] = useState(null);

  useEffect(() => {
    fetchLeaderboard();
    if (token) {
      fetchMyData();
    }
  }, [period, token]);

  const fetchLeaderboard = async () => {
    try {
      setLoading(true);
      const data = await socialTradingService.getLeaderboard(period, 20);
      setLeaderboard(data.leaderboard || []);
    } catch (error) {
      console.error('Failed to fetch leaderboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchMyData = async () => {
    try {
      const statsData = await socialTradingService.getMyStats(token);
      setMyStats(statsData);
    } catch (error) {
      console.error('Failed to fetch user data:', error);
    }
  };

  const viewTrader = async (traderId) => {
    setSelectedTrader(traderId);
    try {
      const details = await socialTradingService.getTraderPortfolio(traderId);
      setTraderDetails(details);
    } catch (error) {
      console.error('Failed to fetch trader details:', error);
      setTraderDetails({ error: error.message });
    }
  };

  const getRankIcon = (rank) => {
    if (rank === 1) return <Crown className="w-6 h-6 text-yellow-400" />;
    if (rank === 2) return <Medal className="w-6 h-6 text-gray-300" />;
    if (rank === 3) return <Medal className="w-6 h-6 text-amber-600" />;
    return <span className="w-6 h-6 flex items-center justify-center text-slate-400 font-bold">{rank}</span>;
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
            <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-xl sm:rounded-2xl bg-gradient-to-br from-yellow-400 to-amber-600 flex items-center justify-center flex-shrink-0">
              <Trophy className="w-6 h-6 sm:w-8 sm:h-8 text-white" />
            </div>
            <div className="min-w-0">
              <h1 className="text-2xl sm:text-3xl font-bold text-white truncate">Trading Leaderboard</h1>
              <p className="text-gray-400 text-sm sm:text-base">See who's making the best trades. Follow top performers to learn from their strategies.</p>
            </div>
          </div>
        </motion.div>

        {myStats && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="premium-glass-card p-6 mb-6"
          >
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Users className="w-5 h-5 text-[#00FFD1]" /> Your Stats
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                <div className="text-2xl font-bold text-white">{myStats.stats?.total_trades || 0}</div>
                <div className="text-gray-400 text-sm flex items-center gap-2">
                  Total Trades
                  <InfoTooltip text="The total number of buy and sell transactions you've made." />
                </div>
              </div>
              <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                <div className="text-2xl font-bold text-[#00FFD1]">{myStats.stats?.win_rate || 0}%</div>
                <div className="text-gray-400 text-sm flex items-center gap-2">
                  Win Rate
                  <InfoTooltip text="The percentage of your trades that ended in profit." />
                </div>
              </div>
              <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                <div className={`text-2xl font-bold ${(myStats.stats?.total_pnl || 0) >= 0 ? 'text-[#00FFD1]' : 'text-red-400'}`}>
                  ${myStats.stats?.total_pnl?.toFixed(2) || '0.00'}
                </div>
                <div className="text-gray-400 text-sm flex items-center gap-2">
                  Total PnL
                  <InfoTooltip text="Profit and Loss — your total earnings minus losses across all trades." />
                </div>
              </div>
              <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                <div className="text-2xl font-bold text-[#00FFD1]">{myStats.followers || 0}</div>
                <div className="text-gray-400 text-sm flex items-center gap-2">
                  Followers
                  <InfoTooltip text="How many other users are following your trading activity." />
                </div>
              </div>
            </div>
          </motion.div>
        )}

        <div className="flex gap-2 mb-6">
          {['week', 'month', 'all'].map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`premium-chip ${period === p ? 'active' : ''}`}
            >
              {p === 'all' ? 'All Time' : p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#00FFD1]"></div>
          </div>
        ) : leaderboard.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <Trophy className="w-16 h-16 mx-auto mb-4 opacity-50 text-[#00FFD1]" />
            <p>No traders have appeared yet — be the first to start trading and claim your spot!</p>
          </div>
        ) : (
          <div className="space-y-3">
            {leaderboard.map((trader, index) => (
              <motion.div
                key={trader.user_id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className={`premium-glass-card p-4 transition-all hover:border-[#00FFD1]/50 ${
                  trader.rank <= 3 ? 'border-[#00FFD1]/30' : ''
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    {getRankIcon(trader.rank)}
                    <div>
                      <h3 className="font-semibold text-white">{trader.display_name}</h3>
                      <div className="text-sm text-gray-400">
                        {trader.total_trades} trades | {trader.win_rate}% win rate
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <div className={`font-bold ${trader.total_pnl >= 0 ? 'text-[#00FFD1]' : 'text-red-400'}`}>
                        ${trader.total_pnl.toFixed(2)}
                      </div>
                      <div className="text-sm text-gray-400">
                        Return on Investment: {trader.roi.toFixed(1)}%
                      </div>
                    </div>
                    
                    <div className="flex gap-2">
                      <button
                        onClick={() => viewTrader(trader.user_id)}
                        className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-gray-300 transition-all border border-white/10"
                        title="View Portfolio"
                      >
                        <Eye className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {selectedTrader && traderDetails && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
            onClick={() => setSelectedTrader(null)}
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              className="bg-[#0a0b0d] border border-[#00FFD1]/20 rounded-2xl p-6 max-w-lg w-full max-h-[80vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              {traderDetails.error ? (
                <div className="text-center text-red-400 py-8">
                  {traderDetails.error}
                </div>
              ) : (
                <>
                  <div className="flex justify-between items-start mb-6">
                    <div>
                      <h2 className="text-xl font-bold text-white">
                        {traderDetails.display_name || `Trader ${selectedTrader.slice(0, 8)}...`}
                      </h2>
                      <p className="text-gray-400">{traderDetails.followers || 0} followers</p>
                    </div>
                    <button
                      onClick={() => setSelectedTrader(null)}
                      className="text-gray-400 hover:text-white"
                    >
                      x
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-3 mb-6">
                    <div className="bg-white/5 rounded-xl p-3 border border-white/10">
                      <div className="text-lg font-bold text-white">{traderDetails.stats?.total_trades || 0}</div>
                      <div className="text-sm text-gray-400">Trades</div>
                    </div>
                    <div className="bg-white/5 rounded-xl p-3 border border-white/10">
                      <div className="text-lg font-bold text-[#00FFD1]">{traderDetails.stats?.win_rate || 0}%</div>
                      <div className="text-sm text-gray-400">Win Rate</div>
                    </div>
                    <div className="bg-white/5 rounded-xl p-3 border border-white/10">
                      <div className={`text-lg font-bold ${(traderDetails.stats?.total_pnl || 0) >= 0 ? 'text-[#00FFD1]' : 'text-red-400'}`}>
                        ${traderDetails.stats?.total_pnl?.toFixed(2) || '0.00'}
                      </div>
                      <div className="text-sm text-gray-400">Total PnL</div>
                    </div>
                    <div className="bg-white/5 rounded-xl p-3 border border-white/10">
                      <div className="text-lg font-bold text-[#00FFD1]">{traderDetails.stats?.avg_return?.toFixed(1) || 0}%</div>
                      <div className="text-sm text-gray-400">Avg Return</div>
                    </div>
                  </div>

                  <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-[#00FFD1]" /> Open Positions ({traderDetails.position_count || 0})
                  </h3>

                  {traderDetails.open_positions?.length > 0 ? (
                    <div className="space-y-2">
                      {traderDetails.open_positions.map((pos, idx) => (
                        <div key={idx} className="bg-white/5 rounded-xl p-3 flex justify-between border border-white/10">
                          <span className="font-medium text-white">{pos.symbol}</span>
                          <span className={pos.current_pnl_percent >= 0 ? 'text-[#00FFD1]' : 'text-red-400'}>
                            {pos.current_pnl_percent >= 0 ? '+' : ''}{pos.current_pnl_percent.toFixed(2)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-400 text-center py-4">No open positions</p>
                  )}

                  <p className="text-[10px] text-gray-600 mt-4 text-center">Past performance doesn't guarantee future results. Always do your own research.</p>

                </>
              )}
            </motion.div>
          </motion.div>
        )}
      </div>
    </div>
  );
}

export default LeaderboardPage;
