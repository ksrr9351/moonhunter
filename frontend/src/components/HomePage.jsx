import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useWalletAuth } from '../contexts/WalletAuthContext';
import ConnectWalletBtn from './ConnectWalletBtn';
import axios from 'axios';
import SplineWithFallback from './SplineWithFallback';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { DisclaimerDialog } from './DisclaimerDialog';
import { formatPrice, formatMarketCap, formatPercent } from '../utils/formatHelpers';
import { TrendingUp, Bell, Brain, Activity, Zap, ChevronRight, Target, MessageSquare, PieChart, Shield, Clock, Sparkles, ArrowUpRight, ArrowDownRight, Menu, X } from 'lucide-react';

const MiniSparkline = ({ data }) => {
  if (!data || data.length === 0) return null;
  
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  
  // Add padding to prevent clipping
  const padding = 5;
  const width = 100;
  const height = 40;
  const graphHeight = height - (padding * 2);
  const graphWidth = width - (padding * 2);
  
  const points = data.map((value, index) => {
    const x = padding + (index / (data.length - 1)) * graphWidth;
    const y = padding + (1 - (value - min) / range) * graphHeight;
    return `${x},${y}`;
  }).join(' ');
  
  // Original Moon Hunters theme: Sparklines are always neon red/pink
  const strokeColor = '#FF4500';
  
  // Create gradient area under the line
  const gradientId = `gradient-${Math.random().toString(36).substr(2, 9)}`;
  const areaPoints = `${padding},${height - padding} ${points} ${width - padding},${height - padding}`;
  
  return (
    <svg 
      width={width} 
      height={height} 
      className="sparkline-svg"
      style={{ display: 'block' }}
    >
      <defs>
        <linearGradient id={gradientId} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor={strokeColor} stopOpacity="0.3" />
          <stop offset="100%" stopColor={strokeColor} stopOpacity="0.05" />
        </linearGradient>
      </defs>
      
      {/* Filled area under the line */}
      <polygon
        points={areaPoints}
        fill={`url(#${gradientId})`}
        className="sparkline-area"
      />
      
      {/* Main line with neon glow */}
      <polyline
        points={points}
        fill="none"
        stroke={strokeColor}
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
        className="sparkline-path"
        style={{
          filter: 'drop-shadow(0 0 4px rgba(255, 69, 0, 0.8))'
        }}
      />
      
      {/* End point circle */}
      <circle
        cx={padding + graphWidth}
        cy={padding + (1 - (data[data.length - 1] - min) / range) * graphHeight}
        r="2.5"
        fill={strokeColor}
        className="sparkline-dot"
      />
    </svg>
  );
};

const FloatingParticles = () => {
  return (
    <div className="floating-particles">
      {[...Array(15)].map((_, i) => (
        <div
          key={i}
          className="particle"
          style={{
            left: `${Math.random() * 100}%`,
            animationDelay: `${Math.random() * 5}s`,
            animationDuration: `${15 + Math.random() * 10}s`
          }}
        />
      ))}
    </div>
  );
};

const FloatingOrb = ({ isDesktop }) => {
  if (!isDesktop) {
    return (
      <div className="static-orb-background">
        <div className="static-gradient-circle"></div>
      </div>
    );
  }
  
  return (
    <div className="floating-orb-container">
      <div className="floating-orb">
        <div className="orb-inner"></div>
      </div>
    </div>
  );
};

const InfiniteMarquee = ({ items, speed = 30 }) => {
  return (
    <div className="marquee-container">
      <div className="marquee-content" style={{ animationDuration: `${speed}s` }}>
        {[...items, ...items].map((item, index) => (
          <div key={index} className="marquee-item">
            <div className="protocol-icon" style={{ borderColor: item.color || '#00FFD1' }}>
              <span style={{ color: item.color || '#00FFD1' }}>{item.icon}</span>
            </div>
            <div className="protocol-name">{item.name}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

const HomePage = () => {
  const { isAuthenticated, user } = useWalletAuth();
  const navigate = useNavigate();
  const [displayedData, setDisplayedData] = useState([]);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [highlightedRows, setHighlightedRows] = useState({});
  const [marketScore, setMarketScore] = useState(72.5);
  const [isLoading, setIsLoading] = useState(false);
  const [previousData, setPreviousData] = useState({});
  const fetchInProgress = useRef(false);
  const [marketOverview, setMarketOverview] = useState(null);
  const [marketLoading, setMarketLoading] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isDesktop, setIsDesktop] = useState(window.innerWidth >= 768);
  
  // Detect screen size for animation control - disable on mobile/tablet
  useEffect(() => {
    const handleResize = () => {
      setIsDesktop(window.innerWidth >= 768);
    };
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  
  // Handle button clicks - redirect based on auth status
  const handleCTAClick = () => {
    if (isAuthenticated) {
      navigate('/dashboard');
    } else {
      navigate('/login');
    }
  };

  // Fetch market overview data
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

  // Fetch market data on mount and every 60 seconds (reduced from 5s for performance)
  useEffect(() => {
    fetchMarketOverview();
    const interval = setInterval(fetchMarketOverview, 60000);
    return () => clearInterval(interval);
  }, []);
  
  const heroRef = useRef(null);
  const investmentHeroRef = useRef(null);
  const featuresRef = useRef(null);
  const portfolioRef = useRef(null);
  const stepsRef = useRef(null);
  const marketPreviewRef = useRef(null);
  const whyChooseRef = useRef(null);
  const protocolsRef = useRef(null);
  const walletsRef = useRef(null);
  const previewRef = useRef(null);
  const ctaRef = useRef(null);
  const footerBrandRef = useRef(null);

  // Fetch real-time data from CMC API
  const fetchCryptoData = async () => {
    if (fetchInProgress.current) return; // Prevent multiple simultaneous calls
    
    fetchInProgress.current = true;
    setIsLoading(true);
    try {
      const apiUrl = import.meta.env.VITE_BACKEND_URL || '';
      const response = await fetch(`${apiUrl}/api/crypto/latest?limit=10`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) throw new Error(`Failed to fetch: ${response.status}`);
      
      const result = await response.json();
      const newData = result.data;
      
      if (!newData || newData.length === 0) {
        throw new Error('No data received');
      }
      
      // Use sparkline data from backend (already included in API response)
      const dataWithSparklines = newData;
      
      // Detect changes for highlighting
      const newHighlights = {};
      dataWithSparklines.forEach((crypto) => {
        const prevPrice = previousData[crypto.symbol]?.price;
        if (prevPrice && crypto.price !== prevPrice) {
          newHighlights[crypto.rank] = crypto.price > prevPrice ? 'up' : 'down';
        }
      });
      
      // Store previous data for next comparison
      const dataMap = {};
      dataWithSparklines.forEach(crypto => {
        dataMap[crypto.symbol] = { price: crypto.price, marketCap: crypto.marketCap };
      });
      setPreviousData(dataMap);
      
      setDisplayedData(dataWithSparklines);
      setHighlightedRows(newHighlights);
      setLastUpdate(new Date());
      
      // Clear highlights after 1 second
      setTimeout(() => setHighlightedRows({}), 1000);
      
    } catch (error) {
      console.error('Error fetching crypto data:', error);
      // Show loading/error state or keep existing real data
    } finally {
      setIsLoading(false);
      fetchInProgress.current = false;
    }
  };

  // Initial fetch and set up interval
  useEffect(() => {
    fetchCryptoData(); // Fetch immediately on mount
    
    const interval = setInterval(() => {
      fetchCryptoData();
      setMarketScore(prev => Math.min(95, Math.max(60, prev + (Math.random() * 2 - 1))));
    }, 30000); // Update every 30 seconds (optimized from 5s)

    return () => clearInterval(interval);
  }, []); // Only run once on mount

  useEffect(() => {
    const observerOptions = {
      threshold: 0.15,
      rootMargin: '0px'
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    }, observerOptions);

    const sections = [heroRef, investmentHeroRef, featuresRef, portfolioRef, stepsRef, marketPreviewRef, whyChooseRef, protocolsRef, walletsRef, previewRef, ctaRef, footerBrandRef];
    sections.forEach((ref) => {
      if (ref.current) {
        observer.observe(ref.current);
      }
    });

    return () => {
      sections.forEach((ref) => {
        if (ref.current) {
          observer.unobserve(ref.current);
        }
      });
    };
  }, []);

  const protocols = [
    { name: 'Bitcoin', icon: '₿', color: '#F7931A' },
    { name: 'Ethereum', icon: 'Ξ', color: '#627EEA' },
    { name: 'Solana', icon: 'S', color: '#14F195' },
    { name: 'Binance', icon: 'B', color: '#F3BA2F' },
    { name: 'Cardano', icon: 'A', color: '#0033AD' },
    { name: 'Polygon', icon: 'P', color: '#8247E5' },
    { name: 'Avalanche', icon: 'A', color: '#E84142' },
    { name: 'Polkadot', icon: 'D', color: '#E6007A' }
  ];

  const wallets = [
    { name: 'MetaMask', icon: 'M', color: '#F6851B' },
    { name: 'Coinbase Wallet', icon: 'C', color: '#0052FF' },
    { name: 'Trust Wallet', icon: 'T', color: '#3375BB' },
    { name: 'Phantom Wallet', icon: 'P', color: '#AB9FF2' },
    { name: 'WalletConnect', icon: 'W', color: '#3B99FC' },
    { name: 'Binance Wallet', icon: 'B', color: '#F3BA2F' },
    { name: 'Crypto.com DeFi', icon: 'C', color: '#003D7A' },
    { name: 'Exodus Wallet', icon: 'E', color: '#0B46F9' },
    { name: 'OKX Wallet', icon: 'O', color: '#000000' },
    { name: 'Keplr Wallet', icon: 'K', color: '#7C2CFE' }
  ];

  const footerSections = [
    {
      title: 'Product',
      links: [
        { label: 'Features', href: '#features' },
        { label: 'Protocols', href: '#protocols' },
        { label: 'Live Preview', href: '#live-preview' },
        { label: 'API Access', href: '#' },
        { label: 'Documentation', href: '#' }
      ]
    },
    {
      title: 'Resources',
      links: [
        { label: 'Getting Started', href: '#' },
        { label: 'Tutorials', href: '#' },
        { label: 'API Reference', href: '#' },
        { label: 'Community', href: '#' },
        { label: 'Blog', href: '#' }
      ]
    },
    {
      title: 'Legal',
      links: [
        { label: 'Disclaimer', isButton: true, component: <DisclaimerDialog variant="link" /> },
        { label: 'Privacy Policy', href: '#' },
        { label: 'Terms of Service', href: '#' },
        { label: 'Cookie Policy', href: '#' },
        { label: 'Security', href: '#' }
      ]
    },
    {
      title: 'Company',
      links: [
        { label: 'About Us', href: '#' },
        { label: 'Careers', href: '#' },
        { label: 'Press Kit', href: '#' },
        { label: 'Contact', href: '#' },
        { label: 'Partners', href: '#' }
      ]
    }
  ];

  return (
    <div className="bg-black min-h-screen text-white relative overflow-x-hidden overflow-y-auto">
      {/* Animated Web3 Grid Background */}
      <div className="web3-grid-background"></div>
      
      {/* Header */}
      <header className="dark-header">
        <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
          <div className="w-8 h-8 sm:w-10 sm:h-10 bg-[#00FFD1] flex items-center justify-center flex-shrink-0" style={{ clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)' }}>
            <span className="text-black font-bold text-base sm:text-xl">M</span>
          </div>
          <span className="text-lg sm:text-2xl font-semibold text-white whitespace-nowrap">Moon Hunters™</span>
        </div>
        
        {/* Desktop Navigation */}
        <nav className="dark-nav hidden lg:flex">
          <a href="#features" className="dark-nav-link">Features</a>
          <a href="#protocols" className="dark-nav-link">Protocols</a>
          <a href="#live-preview" className="dark-nav-link">Live Data</a>
          {isAuthenticated && (
            <Link to="/dashboard" className="dark-nav-link">
              Dashboard
            </Link>
          )}
          <a
            href="https://blockchain-explorer.replit.app"
            target="_blank"
            rel="noopener noreferrer"
            className="dark-nav-link flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[rgba(0,255,209,0.1)] border border-[rgba(0,255,209,0.3)] text-[#00FFD1] hover:bg-[rgba(0,255,209,0.2)] transition-all font-medium text-sm whitespace-nowrap"
          >
            <span className="hidden xl:inline">Blockchain</span> Explorer
            <ArrowUpRight className="w-3.5 h-3.5 flex-shrink-0" />
          </a>
          <ConnectWalletBtn />
        </nav>
        
        {/* Mobile/Tablet Menu Button */}
        <div className="lg:hidden flex items-center gap-2">
          <div className="hidden sm:block">
            <ConnectWalletBtn />
          </div>
          <button 
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2.5 rounded-lg bg-[rgba(0,255,209,0.1)] border border-[rgba(0,255,209,0.3)] hover:bg-[rgba(0,255,209,0.2)] transition-all touch-manipulation"
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? (
              <X className="w-5 h-5 text-[#00FFD1]" />
            ) : (
              <Menu className="w-5 h-5 text-[#00FFD1]" />
            )}
          </button>
        </div>
      </header>
      
      {/* Mobile/Tablet Navigation Drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-50 bg-black/95 backdrop-blur-xl" style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}>
          <div className="flex flex-col h-full pt-20 px-6">
            {/* Close button */}
            <button 
              onClick={() => setMobileMenuOpen(false)}
              className="absolute top-5 right-5 p-2.5 rounded-lg bg-[rgba(0,255,209,0.1)] border border-[rgba(0,255,209,0.3)] touch-manipulation"
              aria-label="Close menu"
            >
              <X className="w-6 h-6 text-[#00FFD1]" />
            </button>
            
            {/* Mobile Nav Links */}
            <nav className="flex flex-col gap-4 mb-8">
              <a 
                href="#features" 
                onClick={() => setMobileMenuOpen(false)}
                className="text-xl font-medium text-white hover:text-[#00FFD1] transition-colors py-3.5 border-b border-[rgba(255,255,255,0.1)] touch-manipulation"
              >
                Features
              </a>
              <a 
                href="#protocols" 
                onClick={() => setMobileMenuOpen(false)}
                className="text-xl font-medium text-white hover:text-[#00FFD1] transition-colors py-3.5 border-b border-[rgba(255,255,255,0.1)] touch-manipulation"
              >
                Protocols
              </a>
              <a 
                href="#live-preview" 
                onClick={() => setMobileMenuOpen(false)}
                className="text-xl font-medium text-white hover:text-[#00FFD1] transition-colors py-3.5 border-b border-[rgba(255,255,255,0.1)] touch-manipulation"
              >
                Live Data
              </a>
              {isAuthenticated && (
                <Link 
                  to="/dashboard" 
                  onClick={() => setMobileMenuOpen(false)}
                  className="text-xl font-medium text-white hover:text-[#00FFD1] transition-colors py-3.5 border-b border-[rgba(255,255,255,0.1)] touch-manipulation"
                >
                  Dashboard
                </Link>
              )}
              <a
                href="https://blockchain-explorer.replit.app"
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => setMobileMenuOpen(false)}
                className="text-xl font-medium text-[#00FFD1] hover:text-white transition-colors py-3.5 border-b border-[rgba(255,255,255,0.1)] flex items-center gap-2 touch-manipulation"
              >
                Blockchain Explorer
                <ArrowUpRight className="w-5 h-5" />
              </a>
            </nav>
            
            {/* Mobile Connect Wallet Button */}
            <div className="mt-4 sm:hidden">
              <ConnectWalletBtn />
            </div>
          </div>
        </div>
      )}

      {/* Hero Section */}
      <section ref={heroRef} className="hero-section scroll-animate relative pt-24 sm:pt-32 pb-8 sm:pb-12 px-4 sm:px-[7.6923%]">
        {/* Floating particles - ONLY render on desktop */}
        {isDesktop && <FloatingParticles />}
        
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-20 items-center relative z-10">
            {/* Hero visual - animations only on desktop, static fallback on mobile */}
            <div className="relative h-[200px] sm:h-[300px] md:h-[600px] flex items-center justify-center hero-visual order-first md:order-last overflow-hidden">
              {isDesktop ? (
                <>
                  {/* Desktop: Full animated experience */}
                  <FloatingOrb isDesktop={true} />
                  <div className="absolute inset-0 hero-glow pointer-events-none"></div>
                  <SplineWithFallback 
                    scene="https://prod.spline.design/NbVmy6DPLhY-5Lvg/scene.splinecode"
                    className="w-full h-full max-w-[700px]"
                    style={{ overflow: 'hidden', position: 'relative', maxHeight: '100%' }}
                  />
                </>
              ) : (
                /* Mobile/Tablet: Static gradient background - NO animations, NO JS overhead */
                <div className="mobile-hero-static-bg">
                  <div className="mobile-gradient-orb"></div>
                </div>
              )}
            </div>
            
            <div className="space-y-4 sm:space-y-8 hero-content text-center md:text-left">
              {/* Product Badge */}
              <div className="product-badge-fixed inline-flex mx-auto md:mx-0">
                <Zap className="w-3 h-3 sm:w-4 sm:h-4" />
                <span className="text-xs sm:text-sm">Crypto Tracker of the Year</span>
              </div>
              
              <div className="space-y-4 sm:space-y-6">
                <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold leading-tight hero-headline" style={{ letterSpacing: '-0.62px' }}>
                  <span className="glow-text">Moon Hunters</span>
                  <span className="block text-[#00FFD1] mt-2 sm:mt-3 neon-text text-2xl sm:text-3xl md:text-4xl lg:text-5xl">Real-Time Crypto Tracking</span>
                </h1>
                <p className="text-sm sm:text-base md:text-lg lg:text-xl text-[rgba(255,255,255,0.85)] leading-relaxed hero-subheadline px-2 sm:px-0" style={{ lineHeight: '1.7' }}>
                  Unlock ultra-fast, real-time crypto intelligence that identifies the market's strongest plays—so you can invest ahead of the crowd, not after them.
                </p>
              </div>
              
              <div className="flex flex-col sm:flex-row flex-wrap gap-3 sm:gap-4 md:gap-6 hero-buttons justify-center md:justify-start">
                <Button className="btn-primary-hero neon-button-primary w-full sm:w-auto" onClick={handleCTAClick}>
                  Start Real-Time Analysis
                </Button>
                <Button className="btn-secondary-hero neon-button-secondary w-full sm:w-auto" onClick={handleCTAClick}>
                  Activate Moon Hunters AI
                </Button>
              </div>
              
              {/* Market Health Score */}
              <div className="market-score-container mx-auto md:mx-0 max-w-md">
                <div className="score-label">Market Health Score</div>
                <div className="score-meter">
                  <div className="score-fill" style={{ width: `${marketScore}%` }}></div>
                </div>
                <div className="score-value">{marketScore.toFixed(1)}%</div>
                <div className="score-status">Market Condition: <span className="status-good">BULLISH</span></div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Animated gradient background */}
        <div className="gradient-bg-animation"></div>
      </section>

      {/* Investment Hero Section */}
      <section ref={investmentHeroRef} className="scroll-animate pt-10 sm:pt-16 pb-10 sm:pb-16 px-4 sm:px-[7.6923%] bg-gradient-to-b from-black to-[#0a0a0a] relative z-10 overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="investment-grid-bg"></div>
        </div>
        <div className="max-w-6xl mx-auto text-center relative z-10 px-2">
          <div className="investment-hero-badge mb-4 sm:mb-6 text-xs sm:text-base">
            <Sparkles className="w-4 h-4 sm:w-5 sm:h-5" />
            <span>AI-Powered Investment Platform</span>
          </div>
          <h2 className="text-2xl sm:text-4xl md:text-5xl lg:text-6xl xl:text-7xl font-bold mb-4 sm:mb-5 investment-hero-title" style={{ letterSpacing: '-0.02em' }}>
            Invest Smarter. <span className="text-[#00FFD1] glow-text-strong block sm:inline">Grow Faster.</span>
          </h2>
          <p className="text-base sm:text-lg md:text-xl lg:text-2xl text-[rgba(255,255,255,0.85)] mb-6 sm:mb-10 leading-relaxed max-w-4xl mx-auto px-2">
            AI-powered crypto investing with real-time insights, portfolio tools, and effortless ROI tracking.
          </p>
          <Button className="btn-primary-hero text-sm sm:text-lg md:text-xl investment-cta w-full sm:w-auto" style={{ padding: '16px 32px', minHeight: '52px' }} onClick={handleCTAClick}>
            Start Investing with AI
            <ChevronRight className="w-4 h-4 sm:w-5 sm:h-5 ml-2 inline" />
          </Button>
        </div>
      </section>

      {/* Powerful Features - Investment Focused */}
      <section id="features" ref={featuresRef} className="scroll-animate pt-10 sm:pt-16 pb-10 sm:pb-16 px-4 sm:px-[7.6923%] bg-black relative z-10">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-8 sm:mb-12 fade-in-up px-2">
            <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold mb-3 sm:mb-4" style={{ letterSpacing: '-0.02em' }}>Powerful Features</h2>
            <p className="text-sm sm:text-base md:text-lg lg:text-xl text-[rgba(255,255,255,0.85)]">AI-powered crypto intelligence at your fingertips</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 lg:gap-8">
            {/* One-Click AI Investing */}
            <Card className="feature-card-animated bg-[rgba(255,255,255,0.05)] backdrop-blur-xl border border-[rgba(0,255,209,0.3)] p-8 rounded-lg group hover-lift" style={{ animationDelay: '0.1s' }}>
              <div className="feature-icon-wrapper">
                <div className="w-16 h-16 bg-gradient-to-br from-[#00FFD1] to-[#00A896] flex items-center justify-center mb-6 rounded-lg feature-icon">
                  <Target className="w-8 h-8 text-black" />
                </div>
                <div className="ai-pulse"></div>
              </div>
              <h3 className="text-2xl font-semibold mb-4 text-white">One-Click AI Investing</h3>
              <p className="text-[rgba(255,255,255,0.85)] text-base leading-relaxed">
                Select a coin and let our AI optimize entry, timing, and allocation. Invest confidently with a single click.
              </p>
            </Card>

            {/* AI Investment Agent */}
            <Card className="feature-card-animated bg-[rgba(255,255,255,0.05)] backdrop-blur-xl border border-[rgba(0,255,209,0.3)] p-8 rounded-lg group hover-lift" style={{ animationDelay: '0.2s' }}>
              <div className="feature-icon-wrapper">
                <div className="w-16 h-16 bg-gradient-to-br from-[#00FFD1] to-[#00A896] flex items-center justify-center mb-6 rounded-lg feature-icon">
                  <MessageSquare className="w-8 h-8 text-black" />
                </div>
                <div className="ai-pulse"></div>
              </div>
              <h3 className="text-2xl font-semibold mb-4 text-white">Your AI Investment Agent</h3>
              <p className="text-[rgba(255,255,255,0.85)] text-base leading-relaxed">
                Ask anything about coins, Web3, market trends, or predictions. Get real-time, actionable insights powered by advanced AI.
              </p>
            </Card>

            {/* AI-Powered Analysis */}
            <Card className="feature-card-animated bg-[rgba(255,255,255,0.05)] backdrop-blur-xl border border-[rgba(0,255,209,0.3)] p-8 rounded-lg group hover-lift" style={{ animationDelay: '0.3s' }}>
              <div className="feature-icon-wrapper">
                <div className="w-16 h-16 bg-gradient-to-br from-[#00FFD1] to-[#00A896] flex items-center justify-center mb-6 rounded-lg feature-icon">
                  <Brain className="w-8 h-8 text-black" />
                </div>
                <div className="ai-pulse"></div>
              </div>
              <h3 className="text-2xl font-semibold mb-4 text-white">AI-Powered Real-Time Analysis</h3>
              <p className="text-[rgba(255,255,255,0.85)] text-base leading-relaxed">
                Moon Hunters' AI continuously analyzes market trends, volatility shifts, and sentiment waves in real time.
              </p>
            </Card>

            {/* 10K+ Coins Monitoring */}
            <Card className="feature-card-animated bg-[rgba(255,255,255,0.05)] backdrop-blur-xl border border-[rgba(0,255,209,0.3)] p-8 rounded-lg group hover-lift" style={{ animationDelay: '0.4s' }}>
              <div className="feature-icon-wrapper">
                <div className="w-16 h-16 bg-gradient-to-br from-[#00FFD1] to-[#00A896] flex items-center justify-center mb-6 rounded-lg feature-icon">
                  <Activity className="w-8 h-8 text-black" />
                </div>
                <div className="ai-pulse"></div>
              </div>
              <h3 className="text-2xl font-semibold mb-4 text-white">10,000+ Coins Live Monitoring</h3>
              <p className="text-[rgba(255,255,255,0.85)] text-base leading-relaxed">
                Monitor live data for 10K+ cryptocurrencies with instant updates on price, market cap, volume, and volatility.
              </p>
            </Card>

            {/* Smart Detection */}
            <Card className="feature-card-animated bg-[rgba(255,255,255,0.05)] backdrop-blur-xl border border-[rgba(0,255,209,0.3)] p-8 rounded-lg group hover-lift" style={{ animationDelay: '0.5s' }}>
              <div className="feature-icon-wrapper">
                <div className="w-16 h-16 bg-gradient-to-br from-[#00FFD1] to-[#00A896] flex items-center justify-center mb-6 rounded-lg feature-icon">
                  <Bell className="w-8 h-8 text-black" />
                </div>
                <div className="ai-pulse"></div>
              </div>
              <h3 className="text-2xl font-semibold mb-4 text-white">AI Agent Smart Detection</h3>
              <p className="text-[rgba(255,255,255,0.85)] text-base leading-relaxed">
                Your personal AI companion that identifies early signals, detects trend reversals, and alerts you instantly.
              </p>
            </Card>

            {/* Advanced Portfolio Optimization */}
            <Card className="feature-card-animated bg-[rgba(255,255,255,0.05)] backdrop-blur-xl border border-[rgba(0,255,209,0.3)] p-8 rounded-lg group hover-lift" style={{ animationDelay: '0.6s' }}>
              <div className="feature-icon-wrapper">
                <div className="w-16 h-16 bg-gradient-to-br from-[#00FFD1] to-[#00A896] flex items-center justify-center mb-6 rounded-lg feature-icon">
                  <PieChart className="w-8 h-8 text-black" />
                </div>
                <div className="ai-pulse"></div>
              </div>
              <h3 className="text-2xl font-semibold mb-4 text-white">Advanced Portfolio Optimization</h3>
              <p className="text-[rgba(255,255,255,0.85)] text-base leading-relaxed">
                AI automatically analyzes risk, allocates assets efficiently, and suggests portfolio adjustments to maximize long-term growth.
              </p>
            </Card>
          </div>
        </div>
      </section>

      {/* Portfolio & ROI Section */}
      <section ref={portfolioRef} className="scroll-animate pt-16 pb-16 px-[7.6923%] bg-[#0a0a0a] relative z-10">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div className="portfolio-content">
              <div className="inline-block mb-6 px-4 py-2 bg-[rgba(0,255,209,0.1)] border border-[rgba(0,255,209,0.3)] rounded-full">
                <span className="text-[#00FFD1] text-sm font-semibold">ROI Tracking</span>
              </div>
              <h2 className="text-5xl font-bold mb-6" style={{ letterSpacing: '-0.02em' }}>
                Track Your Portfolio & ROI in Real Time
              </h2>
              <p className="text-xl text-[rgba(255,255,255,0.85)] mb-8 leading-relaxed">
                Monitor your profits, analyze growth patterns, and get automated AI suggestions to maximize returns.
              </p>
              <div className="flex gap-6 mt-8">
                <div className="flex-1 bg-[rgba(0,255,209,0.05)] backdrop-blur-xl border border-[rgba(0,255,209,0.3)] rounded-2xl p-6">
                  <div className="text-4xl font-bold text-[#00FFD1] mb-2">+127%</div>
                  <div className="text-base text-white font-medium">Avg. ROI</div>
                </div>
                <div className="flex-1 bg-[rgba(0,255,209,0.05)] backdrop-blur-xl border border-[rgba(0,255,209,0.3)] rounded-2xl p-6">
                  <div className="text-4xl font-bold text-[#00FFD1] mb-2">$2.4M</div>
                  <div className="text-base text-white font-medium">Tracked</div>
                </div>
              </div>
            </div>
            <div className="portfolio-visual">
              <Card className="bg-[rgba(255,255,255,0.05)] backdrop-blur-xl border border-[rgba(0,255,209,0.3)] p-8 rounded-xl">
                <div className="flex justify-between items-center mb-6">
                  <h3 className="text-xl font-bold text-white">Portfolio Performance</h3>
                  <span className="text-[#00FFD1] flex items-center gap-1">
                    <ArrowUpRight className="w-5 h-5" />
                    +32.5%
                  </span>
                </div>
                <div className="roi-graph-container mb-6">
                  <svg className="w-full h-32" viewBox="0 0 300 100">
                    <defs>
                      <linearGradient id="roiGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" style={{ stopColor: '#00FFD1', stopOpacity: 0.3 }} />
                        <stop offset="100%" style={{ stopColor: '#00FFD1', stopOpacity: 0 }} />
                      </linearGradient>
                    </defs>
                    <path
                      d="M 0 80 Q 50 60, 100 50 T 200 30 T 300 20"
                      fill="none"
                      stroke="#00FFD1"
                      strokeWidth="3"
                      className="roi-line"
                    />
                    <path
                      d="M 0 80 Q 50 60, 100 50 T 200 30 T 300 20 L 300 100 L 0 100 Z"
                      fill="url(#roiGradient)"
                      className="roi-area"
                    />
                  </svg>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="mini-stat">
                    <div className="text-xs text-[rgba(255,255,255,0.6)]">Total Value</div>
                    <div className="text-lg font-bold text-white">$47,250</div>
                  </div>
                  <div className="mini-stat">
                    <div className="text-xs text-[rgba(255,255,255,0.6)]">24h Change</div>
                    <div className="text-lg font-bold text-[#00FFD1]">+$1,847</div>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* 3 Steps to Invest */}
      <section ref={stepsRef} className="scroll-animate pt-16 pb-16 px-[7.6923%] bg-black relative z-10">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-5xl font-bold mb-4" style={{ letterSpacing: '-0.02em' }}>Start Investing in 3 Simple Steps</h2>
            <p className="text-xl text-[rgba(255,255,255,0.85)]">AI-guided investing made easy for everyone</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="step-card">
              <div className="step-icon-container mb-6">
                <TrendingUp className="w-12 h-12 text-[#00FFD1]" />
              </div>
              <h3 className="text-2xl font-bold mb-4">Discover Opportunities</h3>
              <p className="text-[rgba(255,255,255,0.85)]">
                AI scans the market to find top gainers, trends, and safe picks.
              </p>
            </div>
            <div className="step-card" style={{ animationDelay: '0.2s' }}>
              <div className="step-icon-container mb-6">
                <Brain className="w-12 h-12 text-[#00FFD1]" />
              </div>
              <h3 className="text-2xl font-bold mb-4">Get Smart Suggestions</h3>
              <p className="text-[rgba(255,255,255,0.85)]">
                Receive personalized investment guidance.
              </p>
            </div>
            <div className="step-card" style={{ animationDelay: '0.4s' }}>
              <div className="step-icon-container mb-6">
                <Target className="w-12 h-12 text-[#00FFD1]" />
              </div>
              <h3 className="text-2xl font-bold mb-4">Invest Instantly</h3>
              <p className="text-[rgba(255,255,255,0.85)]">
                One-click execution with AI-optimized timing.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Live Market Preview */}
      <section ref={marketPreviewRef} className="scroll-animate pt-16 pb-16 px-[7.6923%] bg-[#0a0a0a] relative z-10">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-5xl font-bold mb-4 text-white" style={{ letterSpacing: '-0.02em' }}>Live Market Preview</h2>
            <p className="text-xl text-[rgba(255,255,255,0.85)]">Real-time market insights at a glance</p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Top Gainers */}
            <Card className="market-card bg-[rgba(255,255,255,0.05)] backdrop-blur-xl border border-[rgba(0,255,209,0.3)] p-6 rounded-xl transition-all duration-500">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-white">Top Gainers</h3>
                <ArrowUpRight className="w-5 h-5 text-[#00FFD1]" />
              </div>
              {marketLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="flex justify-between items-center animate-pulse">
                      <div className="h-4 bg-gray-700 rounded w-16"></div>
                      <div className="h-4 bg-gray-700 rounded w-12"></div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-3">
                  {marketOverview?.topGainers?.map((coin) => (
                    <div key={coin.symbol} className="flex justify-between items-center">
                      <span className="text-sm text-white font-medium">{coin.symbol}</span>
                      <span className="text-[#00FFD1] font-semibold">+{coin.change24h.toFixed(2)}%</span>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {/* Top Losers */}
            <Card className="market-card bg-[rgba(255,255,255,0.05)] backdrop-blur-xl border border-[rgba(255,107,107,0.3)] p-6 rounded-xl transition-all duration-500">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-white">Top Losers</h3>
                <ArrowDownRight className="w-5 h-5 text-[#FF6B6B]" />
              </div>
              {marketLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="flex justify-between items-center animate-pulse">
                      <div className="h-4 bg-gray-700 rounded w-16"></div>
                      <div className="h-4 bg-gray-700 rounded w-12"></div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-3">
                  {marketOverview?.topLosers?.map((coin) => (
                    <div key={coin.symbol} className="flex justify-between items-center">
                      <span className="text-sm text-white font-medium">{coin.symbol}</span>
                      <span className="text-[#FF6B6B] font-semibold">{coin.change24h.toFixed(2)}%</span>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {/* Trending Coins */}
            <Card className="market-card bg-[rgba(255,255,255,0.05)] backdrop-blur-xl border border-[rgba(0,255,209,0.3)] p-6 rounded-xl transition-all duration-500">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-white">Trending</h3>
                <Zap className="w-5 h-5 text-[#00FFD1]" />
              </div>
              {marketLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="flex justify-between items-center animate-pulse">
                      <div className="h-4 bg-gray-700 rounded w-16"></div>
                      <div className="h-4 bg-gray-700 rounded w-12"></div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-3">
                  {marketOverview?.trending?.map((coin) => (
                    <div key={coin.symbol} className="flex justify-between items-center">
                      <span className="text-sm text-white font-medium">{coin.symbol}</span>
                      <span className="text-[#00FFD1] font-semibold">🔥</span>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {/* Market Overview */}
            <Card className="market-card bg-[rgba(255,255,255,0.05)] backdrop-blur-xl border border-[rgba(0,255,209,0.3)] p-6 rounded-xl transition-all duration-500">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-white">Market</h3>
                <Activity className="w-5 h-5 text-[#00FFD1]" />
              </div>
              {marketLoading ? (
                <div className="space-y-3">
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
                <div className="space-y-3">
                  <div>
                    <div className="text-xs text-white opacity-70">Total Cap</div>
                    <div className="text-lg font-bold text-white">
                      ${(marketOverview?.globalStats?.totalMarketCap / 1e12).toFixed(2)}T
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-white opacity-70">24h Volume</div>
                    <div className="text-lg font-bold text-white">
                      ${(marketOverview?.globalStats?.total24hVolume / 1e9).toFixed(1)}B
                    </div>
                  </div>
                </div>
              )}
            </Card>
          </div>
        </div>
      </section>

      {/* Why Choose Moon Hunters */}
      <section ref={whyChooseRef} className="scroll-animate pt-16 pb-16 px-[7.6923%] bg-black relative z-10">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-5xl font-bold mb-4" style={{ letterSpacing: '-0.02em' }}>Why Choose Moon Hunters</h2>
            <p className="text-xl text-[rgba(255,255,255,0.85)]">The smartest way to invest in crypto</p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card className="benefit-card-investment bg-[rgba(255,255,255,0.05)] backdrop-blur-xl border border-[rgba(0,255,209,0.3)] p-8 rounded-xl" style={{ animationDelay: '0s' }}>
              <div className="benefit-icon-wrapper mb-6">
                <Brain className="w-10 h-10 text-[#00FFD1]" />
              </div>
              <h3 className="text-xl font-bold mb-3 text-white">AI-Driven Insights</h3>
              <p className="text-[rgba(255,255,255,0.8)] leading-relaxed">
                Smarter decisions powered by real-time intelligence.
              </p>
            </Card>

            <Card className="benefit-card-investment bg-[rgba(255,255,255,0.05)] backdrop-blur-xl border border-[rgba(0,255,209,0.3)] p-8 rounded-xl" style={{ animationDelay: '0.1s' }}>
              <div className="benefit-icon-wrapper mb-6">
                <Zap className="w-10 h-10 text-[#00FFD1]" />
              </div>
              <h3 className="text-xl font-bold mb-3 text-white">Easy to Use</h3>
              <p className="text-[rgba(255,255,255,0.8)] leading-relaxed">
                Beginner-friendly interface with powerful tools.
              </p>
            </Card>

            <Card className="benefit-card-investment bg-[rgba(255,255,255,0.05)] backdrop-blur-xl border border-[rgba(0,255,209,0.3)] p-8 rounded-xl" style={{ animationDelay: '0.2s' }}>
              <div className="benefit-icon-wrapper mb-6">
                <Shield className="w-10 h-10 text-[#00FFD1]" />
              </div>
              <h3 className="text-xl font-bold mb-3 text-white">Secure & Reliable</h3>
              <p className="text-[rgba(255,255,255,0.8)] leading-relaxed">
                Enterprise-grade security for your investments.
              </p>
            </Card>

            <Card className="benefit-card-investment bg-[rgba(255,255,255,0.05)] backdrop-blur-xl border border-[rgba(0,255,209,0.3)] p-8 rounded-xl" style={{ animationDelay: '0.3s' }}>
              <div className="benefit-icon-wrapper mb-6">
                <Clock className="w-10 h-10 text-[#00FFD1]" />
              </div>
              <h3 className="text-xl font-bold mb-3 text-white">Faster ROI Tracking</h3>
              <p className="text-[rgba(255,255,255,0.8)] leading-relaxed">
                Instant performance updates with clarity.
              </p>
            </Card>
          </div>
        </div>
      </section>

      {/* Protocol Support Section - Infinite Marquee */}
      <section id="protocols" ref={protocolsRef} className="scroll-animate py-12 sm:py-20 px-4 sm:px-[7.6923%] bg-[#0a0a0a] relative z-10 overflow-hidden">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-8 sm:mb-16 fade-in-up px-2">
            <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold mb-4 sm:mb-6" style={{ letterSpacing: '-0.02em' }}>Wide Protocol Support</h2>
            <p className="text-sm sm:text-base md:text-lg lg:text-xl text-[rgba(255,255,255,0.85)]">Track assets across 50+ blockchain networks</p>
          </div>

          <InfiniteMarquee items={protocols} speed={30} />
        </div>
      </section>

      {/* Wallets Section - 10 Integrations Infinite Marquee */}
      <section ref={walletsRef} className="scroll-animate py-12 sm:py-20 px-4 sm:px-[7.6923%] bg-black relative z-10 overflow-hidden">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-8 sm:mb-16 fade-in-up px-2">
            <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold mb-4 sm:mb-6" style={{ letterSpacing: '-0.02em' }}>Seamless Integrations</h2>
            <p className="text-sm sm:text-base md:text-lg lg:text-xl text-[rgba(255,255,255,0.85)]">Connect your favorite wallets effortlessly</p>
          </div>

          <InfiniteMarquee items={wallets} speed={30} />
        </div>
      </section>

      {/* Mini Live Preview Section */}
      <section id="live-preview" ref={previewRef} className="scroll-animate slide-right py-12 sm:py-20 px-4 sm:px-[7.6923%] bg-[#0a0a0a] relative z-10">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-8 sm:mb-12 fade-in-up px-2">
            <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold mb-4 sm:mb-6" style={{ letterSpacing: '-0.02em' }}>Live Market Preview</h2>
            <p className="text-sm sm:text-base md:text-lg lg:text-xl text-[rgba(255,255,255,0.85)] mb-3 sm:mb-4">Real-time crypto data with 5-second updates</p>
            <div className="inline-flex items-center gap-2 text-[#00FFD1] text-xs sm:text-sm">
              <span className="w-2 h-2 bg-[#00FFD1] rounded-full animate-pulse"></span>
              Updating every 5s • Last update: {lastUpdate.toLocaleTimeString()}
            </div>
          </div>

          <div className="live-market-table-container" style={{ 
            overflowX: 'auto',
            WebkitOverflowScrolling: 'touch',
            background: 'rgba(255, 255, 255, 0.03)',
            backdropFilter: 'blur(10px)',
            borderRadius: '12px',
            border: '1px solid rgba(0, 255, 209, 0.15)',
            padding: '0'
          }}>
            <table className="live-market-table" style={{ 
              width: '100%', 
              minWidth: '700px',
              borderCollapse: 'collapse',
              fontSize: '14px'
            }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(0, 255, 209, 0.2)' }}>
                  <th style={{ 
                    width: '60px', 
                    padding: '16px 12px',
                    textAlign: 'left',
                    color: '#00FF99',
                    fontSize: '12px',
                    fontWeight: '700',
                    letterSpacing: '0.5px',
                    textTransform: 'uppercase'
                  }}>Rank</th>
                  <th style={{ 
                    width: '200px', 
                    padding: '16px 12px',
                    textAlign: 'left',
                    color: '#00FF99',
                    fontSize: '12px',
                    fontWeight: '700',
                    letterSpacing: '0.5px',
                    textTransform: 'uppercase'
                  }}>Name</th>
                  <th style={{ 
                    width: '140px', 
                    padding: '16px 12px',
                    textAlign: 'right',
                    color: '#00FF99',
                    fontSize: '12px',
                    fontWeight: '700',
                    letterSpacing: '0.5px',
                    textTransform: 'uppercase'
                  }}>Price</th>
                  <th style={{ 
                    width: '100px', 
                    padding: '16px 12px',
                    textAlign: 'right',
                    color: '#00FF99',
                    fontSize: '12px',
                    fontWeight: '700',
                    letterSpacing: '0.5px',
                    textTransform: 'uppercase'
                  }}>1h %</th>
                  <th style={{ 
                    width: '100px', 
                    padding: '16px 12px',
                    textAlign: 'right',
                    color: '#00FF99',
                    fontSize: '12px',
                    fontWeight: '700',
                    letterSpacing: '0.5px',
                    textTransform: 'uppercase'
                  }}>24h %</th>
                  <th style={{ 
                    width: '100px', 
                    padding: '16px 12px',
                    textAlign: 'right',
                    color: '#00FF99',
                    fontSize: '12px',
                    fontWeight: '700',
                    letterSpacing: '0.5px',
                    textTransform: 'uppercase'
                  }}>7d %</th>
                  <th style={{ 
                    width: '150px', 
                    padding: '16px 12px',
                    textAlign: 'right',
                    color: '#00FF99',
                    fontSize: '12px',
                    fontWeight: '700',
                    letterSpacing: '0.5px',
                    textTransform: 'uppercase'
                  }}>Market Cap</th>
                  <th style={{ 
                    width: '140px', 
                    padding: '16px 12px',
                    textAlign: 'center',
                    color: '#00FF99',
                    fontSize: '12px',
                    fontWeight: '700',
                    letterSpacing: '0.5px',
                    textTransform: 'uppercase'
                  }}>Last 7 Days</th>
                </tr>
              </thead>
              <tbody>
                {displayedData.map((crypto) => (
                  <tr 
                    key={crypto.rank}
                    style={{
                      transition: 'all 0.3s ease',
                      borderBottom: '1px solid rgba(255, 255, 255, 0.05)'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'rgba(0, 255, 209, 0.08)';
                      e.currentTarget.style.borderLeft = '2px solid #00FFD1';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.borderLeft = 'none';
                    }}
                  >
                    <td style={{ 
                      width: '60px',
                      padding: '16px 12px',
                      textAlign: 'left'
                    }}>
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: '28px',
                        height: '28px',
                        borderRadius: '50%',
                        background: 'rgba(0, 255, 209, 0.1)',
                        color: '#E0E0E0',
                        fontSize: '13px',
                        fontWeight: '600'
                      }}>{crypto.rank}</span>
                    </td>
                    <td style={{ 
                      width: '200px',
                      padding: '16px 12px'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{
                          width: '32px',
                          height: '32px',
                          borderRadius: '50%',
                          overflow: 'hidden',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          background: 'rgba(255, 255, 255, 0.05)',
                          fontSize: '14px',
                          fontWeight: '700',
                          color: '#00FFD1'
                        }}>
                          {crypto.logo ? (
                            <img 
                              src={crypto.logo} 
                              alt={crypto.symbol}
                              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                              onError={(e) => {
                                e.target.style.display = 'none';
                                e.target.parentElement.textContent = crypto.symbol.charAt(0);
                              }}
                            />
                          ) : (
                            crypto.symbol.charAt(0)
                          )}
                        </div>
                        <div>
                          <div style={{ 
                            color: '#FFFFFF', 
                            fontSize: '15px', 
                            fontWeight: '700',
                            marginBottom: '2px'
                          }}>{crypto.name}</div>
                          <div style={{ 
                            color: 'rgba(255, 255, 255, 0.5)', 
                            fontSize: '12px',
                            fontWeight: '400'
                          }}>{crypto.symbol}</div>
                        </div>
                      </div>
                    </td>
                    <td style={{ 
                      width: '140px',
                      padding: '16px 12px',
                      textAlign: 'right',
                      color: '#E0E0E0',
                      fontSize: '15px',
                      fontWeight: '600'
                    }}>
                      {formatPrice(crypto.price)}
                    </td>
                    <td style={{ 
                      width: '100px',
                      padding: '16px 12px',
                      textAlign: 'right'
                    }}>
                      <span style={{
                        padding: '4px 8px',
                        borderRadius: '6px',
                        fontSize: '13px',
                        fontWeight: '700',
                        backgroundColor: crypto.change1h >= 0 ? 'rgba(0, 255, 153, 0.15)' : 'rgba(255, 69, 0, 0.15)',
                        color: crypto.change1h >= 0 ? '#00FF99' : '#FF4500'
                      }}>
                        {formatPercent(crypto.change1h)}
                      </span>
                    </td>
                    <td style={{ 
                      width: '100px',
                      padding: '16px 12px',
                      textAlign: 'right'
                    }}>
                      <span style={{
                        padding: '4px 8px',
                        borderRadius: '6px',
                        fontSize: '13px',
                        fontWeight: '700',
                        backgroundColor: crypto.change24h >= 0 ? 'rgba(0, 255, 153, 0.15)' : 'rgba(255, 69, 0, 0.15)',
                        color: crypto.change24h >= 0 ? '#00FF99' : '#FF4500'
                      }}>
                        {formatPercent(crypto.change24h)}
                      </span>
                    </td>
                    <td style={{ 
                      width: '100px',
                      padding: '16px 12px',
                      textAlign: 'right'
                    }}>
                      <span style={{
                        padding: '4px 8px',
                        borderRadius: '6px',
                        fontSize: '13px',
                        fontWeight: '700',
                        backgroundColor: crypto.change7d >= 0 ? 'rgba(0, 255, 153, 0.15)' : 'rgba(255, 69, 0, 0.15)',
                        color: crypto.change7d >= 0 ? '#00FF99' : '#FF4500'
                      }}>
                        {formatPercent(crypto.change7d)}
                      </span>
                    </td>
                    <td style={{ 
                      width: '150px',
                      padding: '16px 12px',
                      textAlign: 'right',
                      color: '#E0E0E0',
                      fontSize: '14px',
                      fontWeight: '500'
                    }}>
                      {formatMarketCap(crypto.marketCap)}
                    </td>
                    <td style={{ 
                      width: '140px',
                      padding: '16px 12px',
                      textAlign: 'center'
                    }}>
                      <MiniSparkline data={crypto.sparkline} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section ref={ctaRef} className="scroll-animate py-12 sm:py-20 px-4 sm:px-[7.6923%] bg-black relative z-10">
        <div className="max-w-4xl mx-auto text-center space-y-4 sm:space-y-8 fade-in-up px-2">
          <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold" style={{ letterSpacing: '-0.02em' }}>Start Tracking Smarter Today</h2>
          <p className="text-base sm:text-lg md:text-xl lg:text-2xl text-[rgba(255,255,255,0.85)]">Join thousands of traders making data-driven decisions</p>
          <div className="flex flex-col sm:flex-row gap-3 sm:gap-6 justify-center items-center">
            <Button className="btn-primary-hero neon-button-primary text-sm sm:text-base md:text-lg lg:text-xl w-full sm:w-auto" style={{ padding: '14px 28px', minHeight: '52px' }} onClick={handleCTAClick}>
              Start Real-Time Analysis
            </Button>
            <Button className="btn-secondary-hero neon-button-secondary text-sm sm:text-base md:text-lg lg:text-xl w-full sm:w-auto" style={{ padding: '14px 28px', minHeight: '52px' }} onClick={handleCTAClick}>
              Activate Moon Hunters AI
            </Button>
          </div>
        </div>
      </section>

      {/* FIXED Web3 Footer */}
      <footer className="web3-footer-fixed bg-gradient-to-b from-[#0a0a0a] to-black border-t border-[rgba(0,255,209,0.2)] relative overflow-hidden">
        {/* Animated background pattern */}
        <div className="footer-grid-pattern"></div>
        
        <div className="max-w-7xl mx-auto px-4 sm:px-[7.6923%] py-12 sm:py-20 relative z-10">
          {/* Top Section - Brand */}
          <div ref={footerBrandRef} className="mb-8 sm:mb-16 text-center scroll-animate footer-brand-section">
            <div className="flex items-center justify-center gap-2 sm:gap-3 mb-4 sm:mb-6">
              <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-[#00FFD1] to-[#00A896] flex items-center justify-center flex-shrink-0" style={{ clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)' }}>
                <span className="text-black font-bold text-lg sm:text-2xl">M</span>
              </div>
              <span className="text-xl sm:text-2xl md:text-3xl font-bold bg-gradient-to-r from-[#00FFD1] to-[#00A896] bg-clip-text text-transparent">Moon Hunters</span>
            </div>
            <p className="footer-tagline text-sm sm:text-base md:text-lg text-[rgba(255,255,255,0.7)] max-w-2xl mx-auto leading-relaxed px-4">
              AI-powered crypto intelligence platform delivering real-time insights for serious traders
            </p>
          </div>

          {/* Dynamic Footer Links Grid - PROPERLY ALIGNED */}
          <div className="footer-links-container mb-8 sm:mb-16">
            {footerSections.map((section, index) => (
              <div key={index} className="footer-column-fixed">
                <h4 className="footer-column-title">
                  <ChevronRight className="w-4 h-4" />
                  {section.title}
                </h4>
                <ul className="footer-links-list">
                  {section.links.map((link, linkIndex) => (
                    <li key={linkIndex}>
                      {link.isButton ? (
                        link.component
                      ) : (
                        <a href={link.href} className="footer-link-fixed">
                          {link.label}
                        </a>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          {/* Social Links Section - FIXED ALIGNMENT */}
          <div className="border-t border-[rgba(0,255,209,0.2)] pt-8 sm:pt-12">
            <div className="flex flex-col md:flex-row justify-between items-center gap-6 sm:gap-8">
              <div className="flex gap-4 items-center">
                <a href="#" className="social-icon-fixed" aria-label="Discord">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515a.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0a12.64 12.64 0 0 0-.617-1.25a.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057a19.9 19.9 0 0 0 5.993 3.03a.078.078 0 0 0 .084-.028a14.09 14.09 0 0 0 1.226-1.994a.076.076 0 0 0-.041-.106a13.107 13.107 0 0 1-1.872-.892a.077.077 0 0 1-.008-.128a10.2 10.2 0 0 0 .372-.292a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127a12.299 12.299 0 0 1-1.873.892a.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028a19.839 19.839 0 0 0 6.002-3.03a.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.956-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.955-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.946 2.418-2.157 2.418z"/></svg>
                </a>
                <a href="#" className="social-icon-fixed" aria-label="Twitter">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                </a>
                <a href="#" className="social-icon-fixed" aria-label="GitHub">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg>
                </a>
                <a href="#" className="social-icon-fixed" aria-label="Telegram">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>
                </a>
                <a href="#" className="social-icon-fixed" aria-label="Medium">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M13.54 12a6.8 6.8 0 01-6.77 6.82A6.8 6.8 0 010 12a6.8 6.8 0 016.77-6.82A6.8 6.8 0 0113.54 12zM20.96 12c0 3.54-1.51 6.42-3.38 6.42-1.87 0-3.39-2.88-3.39-6.42s1.52-6.42 3.39-6.42 3.38 2.88 3.38 6.42M24 12c0 3.17-.53 5.75-1.19 5.75-.66 0-1.19-2.58-1.19-5.75s.53-5.75 1.19-5.75C23.47 6.25 24 8.83 24 12z"/></svg>
                </a>
              </div>
              
              <div className="text-[rgba(255,255,255,0.6)] text-center md:text-right">
                <p className="mb-2 text-base leading-relaxed">© {new Date().getFullYear()} Moon Hunters. All Rights Reserved.</p>
                <p className="text-sm">Built with passion for the crypto community</p>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;