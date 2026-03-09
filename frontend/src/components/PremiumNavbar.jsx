import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Link, useLocation } from 'react-router-dom';
import { useWalletAuth } from '../contexts/WalletAuthContext';
import { LayoutDashboard, TrendingUp, Zap, Wallet, LogOut, Sparkles, User, Brain, Trophy, History, Menu, X, Coins, ArrowUpRight, Globe } from 'lucide-react';

const PremiumNavbar = () => {
  const { user, walletAddress, logout } = useWalletAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [mobileMenuOpen]);

  const handleLogout = () => {
    logout();
    setMobileMenuOpen(false);
  };

  const isActive = (path) => location.pathname === path;

  const navLinks = [
    { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/ai-engine', icon: Brain, label: 'AI Engine' },
    { path: '/leaderboard', icon: Trophy, label: 'Leaderboard' },
    { path: '/backtest', icon: History, label: 'Backtest' },
    { path: '/top-gainers', icon: TrendingUp, label: 'Top Gainers' },
    { path: '/invest', icon: Coins, label: 'Invest' },
    { path: '/ai-auto-invest', icon: Zap, label: 'Auto-Invest' },
    { path: '/wallet', icon: Wallet, label: 'Wallet' },
  ];

  const mobileMenuPortal = mobileMenuOpen && createPortal(
    <>
      <div 
        className="lg:hidden fixed inset-0 bg-black/80 z-[9998]"
        style={{ WebkitBackdropFilter: 'blur(4px)', backdropFilter: 'blur(4px)' }}
        onClick={() => setMobileMenuOpen(false)}
      />
      <div 
        className="lg:hidden fixed inset-x-0 top-16 bottom-0 bg-[#0a0b0d] z-[9999] overflow-y-auto"
        style={{ 
          WebkitOverflowScrolling: 'touch',
          paddingBottom: 'env(safe-area-inset-bottom, 24px)'
        }}
      >
        <div className="px-4 py-4 space-y-2 pb-24">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const active = isActive(link.path);
            
            return (
              <Link
                key={link.path}
                to={link.path}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center gap-3 px-4 py-3.5 rounded-xl font-medium transition-all touch-manipulation ${
                  active
                    ? 'bg-[#00FFD1] text-black'
                    : 'text-gray-400 hover:text-[#00FFD1] hover:bg-white/5'
                }`}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                <span className="truncate">{link.label}</span>
              </Link>
            );
          })}
          
          <a
            href="https://blockchain-explorer.replit.app"
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center gap-3 px-4 py-3.5 rounded-xl font-medium text-[#00FFD1] bg-[#00FFD1]/10 border border-[#00FFD1]/30 hover:bg-[#00FFD1]/20 transition-all touch-manipulation"
          >
            <Globe className="w-5 h-5 flex-shrink-0" />
            <span className="truncate">Blockchain Explorer</span>
            <ArrowUpRight className="w-4 h-4 flex-shrink-0 ml-auto" />
          </a>

          <div className="pt-4 mt-4 border-t border-white/10">
            <div className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="w-10 h-10 rounded-full bg-[#00FFD1] flex items-center justify-center flex-shrink-0">
                  <User className="w-5 h-5 text-black" />
                </div>
                <span className="text-white font-medium truncate">
                  {user?.username || (walletAddress ? `${walletAddress.slice(0, 6)}...${walletAddress.slice(-4)}` : 'User')}
                </span>
              </div>
              <button
                onClick={handleLogout}
                className="p-2.5 rounded-xl text-red-400 hover:bg-red-500/10 transition-all flex-shrink-0 touch-manipulation"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </>,
    document.body
  );

  return (
    <>
      <nav className="premium-navbar sticky top-0 z-[100]" style={{ paddingTop: 'env(safe-area-inset-top, 0px)' }}>
        <div className="max-w-[1920px] mx-auto px-3 sm:px-4 lg:px-6">
          <div className="flex items-center justify-between h-14 lg:h-16">
            <Link to="/" className="flex items-center gap-2 group flex-shrink-0">
              <div className="w-9 h-9 lg:w-10 lg:h-10 bg-[#00FFD1] flex items-center justify-center rounded-xl group-hover:scale-110 transition-transform">
                <Sparkles className="w-4 h-4 lg:w-5 lg:h-5 text-black" />
              </div>
              <span className="text-lg lg:text-xl font-bold text-[#00FFD1] hidden sm:block whitespace-nowrap">
                Moon Hunters
              </span>
            </Link>

            <div className="hidden lg:flex items-center gap-0.5 xl:gap-1 2xl:gap-1.5 flex-1 justify-center mx-2 xl:mx-3 2xl:mx-4 overflow-x-auto scrollbar-hide">
              {navLinks.map((link) => {
                const Icon = link.icon;
                const active = isActive(link.path);
                
                return (
                  <Link
                    key={link.path}
                    to={link.path}
                    title={link.label}
                    aria-label={link.label}
                    className={`flex items-center gap-1.5 px-2 xl:px-2.5 2xl:px-3 py-1.5 rounded-lg font-medium transition-all whitespace-nowrap text-xs 2xl:text-sm ${
                      active
                        ? 'bg-[#00FFD1] text-black shadow-lg'
                        : 'text-gray-400 hover:text-[#00FFD1] hover:bg-white/5'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5 2xl:w-4 2xl:h-4 flex-shrink-0" />
                    <span className="hidden 2xl:inline">{link.label}</span>
                  </Link>
                );
              })}

              <a
                href="https://blockchain-explorer.replit.app"
                target="_blank"
                rel="noopener noreferrer"
                title="Blockchain Explorer"
                aria-label="Blockchain Explorer"
                className="flex items-center gap-1.5 px-2 xl:px-2.5 2xl:px-3 py-1.5 rounded-lg font-medium text-xs 2xl:text-sm bg-[#00FFD1]/10 border border-[#00FFD1]/30 text-[#00FFD1] hover:bg-[#00FFD1]/20 transition-all whitespace-nowrap"
              >
                <Globe className="w-3.5 h-3.5 2xl:w-4 2xl:h-4 flex-shrink-0" />
                <span className="hidden 2xl:inline">Explorer</span>
                <ArrowUpRight className="w-3 h-3 flex-shrink-0" />
              </a>
            </div>

            <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
              <div className="hidden lg:flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-white/5 border border-[#00FFD1]/20">
                <div className="w-7 h-7 rounded-full bg-[#00FFD1] flex items-center justify-center flex-shrink-0">
                  <User className="w-3.5 h-3.5 text-black" />
                </div>
                <span className="text-xs font-medium text-white hidden 2xl:block truncate max-w-[100px]">
                  {user?.username || (walletAddress ? `${walletAddress.slice(0, 6)}...${walletAddress.slice(-4)}` : 'User')}
                </span>
              </div>

              <button
                onClick={handleLogout}
                className="hidden lg:flex p-2 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-all touch-manipulation"
                title="Logout"
              >
                <LogOut className="w-4 h-4" />
              </button>

              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="lg:hidden p-2 rounded-xl text-gray-400 hover:text-[#00FFD1] hover:bg-white/5 transition-all touch-manipulation"
              >
                {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </button>
            </div>
          </div>
        </div>
      </nav>
      {mobileMenuPortal}
    </>
  );
};

export default PremiumNavbar;
