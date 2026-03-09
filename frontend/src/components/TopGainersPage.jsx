import React, { useState, useEffect } from 'react';
import PremiumNavbar from './PremiumNavbar';
import FastMarketMovements from './FastMarketMovements';
import SmartAlerts from './SmartAlerts';
import InfoTooltip from './InfoTooltip';
import { ArrowUpRight, ArrowDownRight, Zap, Activity } from 'lucide-react';
import { Card } from './ui/card';
import axios from 'axios';
import './TopGainersPage.css';

const TopGainersPage = () => {
  const [marketOverview, setMarketOverview] = useState(null);
  const [marketLoading, setMarketLoading] = useState(true);

  const fetchMarketOverview = async () => {
    try {
      const apiUrl = import.meta.env.VITE_BACKEND_URL || '';
      const response = await axios.get(`${apiUrl}/api/crypto/market-overview`);
      setMarketOverview(response.data);
      setMarketLoading(false);
    } catch (error) {
      console.error('Error fetching market overview:', error);
      setMarketLoading(false);
    }
  };

  useEffect(() => {
    fetchMarketOverview();
    const interval = setInterval(fetchMarketOverview, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="top-gainers-page">
      <PremiumNavbar />
      
      <div className="page-content">
        <div className="page-header">
          <div className="header-content">
            <h1 className="page-title">Top Gainers</h1>
            <p className="page-subtitle">
              See which cryptocurrencies are moving the most right now — and get notified about big changes
            </p>
            <div className="mt-4 p-3 rounded-xl bg-blue-500/5 border border-blue-500/10 max-w-2xl mx-auto">
              <p className="text-xs text-blue-300/80 text-center">
                Tip: Big price movements can mean opportunity — but also risk. Always research before investing.
              </p>
            </div>
          </div>
          
          <div className="header-decoration">
            <div className="glow-orb glow-orb-1"></div>
            <div className="glow-orb glow-orb-2"></div>
          </div>
        </div>

        <div className="market-overview-section">
          <div className="section-header-with-badge">
            <h2 className="section-title flex items-center gap-1">Live Market Preview <InfoTooltip text="Real-time market data updated every few seconds. Green means the price went up, red means it went down." /></h2>
            <span className="live-badge">
              <span className="pulse-dot"></span>
              LIVE
            </span>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mb-8 sm:mb-12">
            <Card className="market-card bg-[rgba(255,255,255,0.05)] backdrop-blur-xl border border-[rgba(0,255,209,0.3)] p-4 sm:p-6 rounded-xl transition-all duration-500">
              <div className="flex items-center justify-between mb-3 sm:mb-4">
                <h3 className="text-base sm:text-lg font-bold text-white flex items-center gap-1">Top Gainers <InfoTooltip text="Coins with the biggest price increases in the last 24 hours." /></h3>
                <ArrowUpRight className="w-4 h-4 sm:w-5 sm:h-5 text-[#00FFD1]" />
              </div>
              {marketLoading ? (
                <div className="space-y-2 sm:space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="flex justify-between items-center animate-pulse">
                      <div className="h-4 bg-gray-700 rounded w-16"></div>
                      <div className="h-4 bg-gray-700 rounded w-12"></div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-2 sm:space-y-3">
                  {marketOverview?.topGainers?.map((coin) => (
                    <div key={coin.symbol} className="flex justify-between items-center">
                      <span className="text-xs sm:text-sm text-white font-medium">{coin.symbol}</span>
                      <span className="text-[#00FFD1] font-semibold text-xs sm:text-sm">+{coin.change24h.toFixed(2)}%</span>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <Card className="market-card bg-[rgba(255,255,255,0.05)] backdrop-blur-xl border border-[rgba(255,107,107,0.3)] p-4 sm:p-6 rounded-xl transition-all duration-500">
              <div className="flex items-center justify-between mb-3 sm:mb-4">
                <h3 className="text-base sm:text-lg font-bold text-white flex items-center gap-1">Top Losers <InfoTooltip text="Coins with the biggest price drops in the last 24 hours. Some investors see drops as buying opportunities." /></h3>
                <ArrowDownRight className="w-4 h-4 sm:w-5 sm:h-5 text-[#FF6B6B]" />
              </div>
              {marketLoading ? (
                <div className="space-y-2 sm:space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="flex justify-between items-center animate-pulse">
                      <div className="h-4 bg-gray-700 rounded w-16"></div>
                      <div className="h-4 bg-gray-700 rounded w-12"></div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-2 sm:space-y-3">
                  {marketOverview?.topLosers?.map((coin) => (
                    <div key={coin.symbol} className="flex justify-between items-center">
                      <span className="text-xs sm:text-sm text-white font-medium">{coin.symbol}</span>
                      <span className="text-[#FF6B6B] font-semibold text-xs sm:text-sm">{coin.change24h.toFixed(2)}%</span>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <Card className="market-card bg-[rgba(255,255,255,0.05)] backdrop-blur-xl border border-[rgba(0,255,209,0.3)] p-4 sm:p-6 rounded-xl transition-all duration-500">
              <div className="flex items-center justify-between mb-3 sm:mb-4">
                <h3 className="text-base sm:text-lg font-bold text-white">Trending</h3>
                <Zap className="w-4 h-4 sm:w-5 sm:h-5 text-[#00FFD1]" />
              </div>
              {marketLoading ? (
                <div className="space-y-2 sm:space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="flex justify-between items-center animate-pulse">
                      <div className="h-4 bg-gray-700 rounded w-16"></div>
                      <div className="h-4 bg-gray-700 rounded w-12"></div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-2 sm:space-y-3">
                  {marketOverview?.trending?.map((coin) => (
                    <div key={coin.symbol} className="flex justify-between items-center">
                      <span className="text-xs sm:text-sm text-white font-medium">{coin.symbol}</span>
                      <span className="text-[#00FFD1] font-semibold text-xs sm:text-sm">🔥</span>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <Card className="market-card bg-[rgba(255,255,255,0.05)] backdrop-blur-xl border border-[rgba(0,255,209,0.3)] p-4 sm:p-6 rounded-xl transition-all duration-500">
              <div className="flex items-center justify-between mb-3 sm:mb-4">
                <h3 className="text-base sm:text-lg font-bold text-white">Market</h3>
                <Activity className="w-4 h-4 sm:w-5 sm:h-5 text-[#00FFD1]" />
              </div>
              {marketLoading ? (
                <div className="space-y-2 sm:space-y-3">
                  <div className="animate-pulse">
                    <div className="h-3 bg-gray-700 rounded w-20 mb-2"></div>
                    <div className="h-5 bg-gray-700 rounded w-24"></div>
                  </div>
                  <div className="animate-pulse">
                    <div className="h-3 bg-gray-700 rounded w-20 mb-2"></div>
                    <div className="h-5 bg-gray-700 rounded w-24"></div>
                  </div>
                </div>
              ) : (
                <div className="space-y-2 sm:space-y-3">
                  <div>
                    <div className="text-xs text-white opacity-70">Total Cap</div>
                    <div className="text-sm sm:text-base font-bold text-white">
                      ${(marketOverview?.globalStats?.totalMarketCap / 1e12).toFixed(2)}T
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-white opacity-70">24h Volume</div>
                    <div className="text-sm sm:text-base font-bold text-white">
                      ${(marketOverview?.globalStats?.total24hVolume / 1e9).toFixed(1)}B
                    </div>
                  </div>
                </div>
              )}
            </Card>
          </div>
        </div>

        <FastMarketMovements />

        <SmartAlerts />
      </div>
    </div>
  );
};

export default TopGainersPage;
