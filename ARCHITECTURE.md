# Moon Hunters - AI-Powered Crypto Investment Platform

## Overview

Moon Hunters is a full-stack cryptocurrency investment platform designed to empower users with AI-driven insights and real-time market awareness. It features wallet-based authentication via Reown AppKit with support for MetaMask, WalletConnect, Coinbase, and social logins, a dynamic dashboard for portfolio tracking, rapid detection of significant market movements, automated trading bots, and smart alerts for price movements. The platform supports both simulated and real DEX execution through the 1inch aggregator, with a Fee Proxy Smart Contract for transparent fee collection.

## Project Structure

```
/
├── backend/                        # Python FastAPI backend
│   ├── server.py                   # Main FastAPI app (middleware, startup, router registration)
│   ├── core/                       # Shared core modules
│   │   ├── config.py               # Environment config, logging setup
│   │   ├── deps.py                 # Dependency injection (DB, engines, services)
│   │   ├── schemas.py              # Pydantic validation models (30+ schemas)
│   │   ├── indexes.py              # MongoDB index management with TTL indexes
│   │   └── error_handlers.py       # Global error/validation handlers
│   ├── routers/                    # Modular API route handlers
│   │   ├── ai.py                   # AI engine endpoints (17 routes)
│   │   ├── alerts.py               # Alert settings & test alerts (6 routes)
│   │   ├── analytics.py            # Performance analytics (5 routes)
│   │   ├── auth.py                 # Authentication (10 routes)
│   │   ├── backtest.py             # Backtesting (2 routes)
│   │   ├── crypto.py               # Market data (5 routes)
│   │   ├── dex.py                  # DEX swap integration (9 routes)
│   │   ├── events.py               # SSE event streaming (3 routes)
│   │   ├── intelligence.py         # Trading Intelligence signals (6 routes)
│   │   ├── invest.py               # Dump opportunities marketplace (9 routes)
│   │   ├── portfolio.py            # Portfolio management (7 routes)
│   │   ├── positions.py            # Position tracking & triggers (12 routes)
│   │   └── social.py               # Social trading & leaderboard (10 routes)
│   ├── market_provider.py          # CoinMarketCap API integration with 30s cache
│   ├── historical_data_provider.py # CoinGecko API for real historical OHLC data
│   ├── wallet_auth.py              # SIWE signature verification, nonce management
│   ├── auth_utils.py               # JWT creation, validation, refresh
│   ├── wallet_service.py           # On-chain ETH/ERC-20 balance fetching via RPC
│   ├── trading_bot.py              # Automated trading engine with stop-loss/take-profit
│   ├── portfolio_engine.py         # Position tracking and management
│   ├── recommendation_engine.py    # AI-powered investment recommendations
│   ├── analysis_engine.py          # Trend, momentum, volatility analysis
│   ├── dump_detection_engine.py    # 3%+ price dump detection with health filters
│   ├── fast_movers_detector.py     # Real-time movement detection (DUMP ≥0.5%, PUMP ≥1.5%)
│   ├── dex_service.py              # 1inch DEX API v6.0 swap integration
│   ├── analytics_engine.py         # Performance metrics and ROI tracking
│   ├── social_trading_engine.py    # Leaderboard, following, copy trading
│   ├── backtesting_engine.py       # Historical strategy simulation with real data
│   ├── report_generator.py         # CSV and PDF P&L report generation
│   ├── email_service.py            # SMTP email notifications
│   ├── ai_dump_alert_service.py    # AI-powered dump opportunity alerts
│   ├── push_notification_service.py # VAPID web push notifications
│   ├── event_service.py            # Server-Sent Events broadcasting
│   ├── price_streaming.py          # WebSocket price updates (30s interval)
│   ├── perplexity_client.py        # Perplexity AI API client
│   ├── nonce_store.py              # MongoDB nonce storage with TTL
│   ├── auto_invest_scheduler.py    # Scheduled investment automation (DCA)
│   ├── requirements.txt            # Python dependencies
│   ├── trading_intelligence/       # AI-Powered Trading Intelligence Engine
│   │   ├── __init__.py
│   │   ├── data_manager.py         # OHLCV candle builder, MongoDB storage
│   │   ├── indicators.py           # NumPy-based technical indicators (10 indicators)
│   │   ├── anomaly_detector.py     # IsolationForest + z-score anomaly detection
│   │   ├── pump_dump_detector.py   # Multi-factor pump/dump risk analysis
│   │   ├── signal_engine.py        # Rule-based + GradientBoosting signal generation
│   │   ├── ml_seed_data.py         # 291 labeled training samples for ML bootstrap
│   │   ├── schemas.py              # Pydantic schemas for TI data models
│   │   └── service.py              # Service orchestrator (60s background task)
│   └── tests/                      # Test files (73 tests)
│       ├── conftest.py             # Shared test fixtures and configuration
│       ├── test_api.py             # Core API endpoint tests
│       ├── test_authenticated_endpoints.py
│       ├── test_ai_dump_alerts.py
│       └── test_trading_intelligence.py
├── frontend/                       # React Vite frontend
│   ├── src/
│   │   ├── components/             # 25 React components
│   │   │   ├── HomePage.jsx
│   │   │   ├── DynamicDashboard.jsx
│   │   │   ├── WalletPage.jsx
│   │   │   ├── AIEnginePage.jsx
│   │   │   ├── AIAutoInvestPage.jsx
│   │   │   ├── InvestPage.jsx
│   │   │   ├── TradingBotSettings.jsx
│   │   │   ├── AnalyticsDashboard.jsx
│   │   │   ├── BacktestPage.jsx
│   │   │   ├── LeaderboardPage.jsx
│   │   │   ├── FastMarketMovements.jsx
│   │   │   ├── SmartAlerts.jsx
│   │   │   ├── SwapModal.jsx
│   │   │   ├── TradingViewChart.jsx
│   │   │   ├── TopGainersPage.jsx
│   │   │   ├── PremiumNavbar.jsx
│   │   │   ├── ConnectWalletBtn.jsx
│   │   │   ├── LivePriceIndicator.jsx
│   │   │   ├── RecentTransactions.jsx
│   │   │   ├── DisclaimerDialog.jsx
│   │   │   ├── ProtectedRoute.jsx
│   │   │   ├── SplineWithFallback.jsx
│   │   │   ├── ErrorBoundary.jsx
│   │   │   ├── InfoTooltip.jsx
│   │   │   └── ui/                 # shadcn/ui primitives (46 Radix components)
│   │   ├── contexts/               # 3 React contexts
│   │   │   ├── WalletAuthContext.jsx
│   │   │   ├── PriceStreamContext.jsx
│   │   │   └── EventContext.jsx
│   │   ├── services/               # 9 API service modules
│   │   │   ├── apiClient.js
│   │   │   ├── cryptoService.js
│   │   │   ├── dexService.js
│   │   │   ├── investService.js
│   │   │   ├── contractService.js
│   │   │   ├── eventService.js
│   │   │   ├── pushNotificationService.js
│   │   │   ├── socialTradingService.js
│   │   │   └── backtestingService.js
│   │   ├── config/                 # App configuration
│   │   │   ├── reown.js            # Reown AppKit config
│   │   │   └── contractConfig.js   # Multi-chain SC addresses, ABIs, fee settings
│   │   ├── hooks/                  # Custom React hooks
│   │   │   └── use-toast.js
│   │   ├── lib/                    # Utility libraries
│   │   │   └── utils.js
│   │   ├── data/                   # Static data & formatters
│   │   ├── styles/                 # CSS themes
│   │   │   └── premiumTheme.css
│   │   └── utils/                  # Helper utilities
│   │       ├── formatHelpers.js
│   │       └── formatters.js
│   ├── public/                     # Static assets (sw.js, PDF)
│   └── build/                      # Production build output
├── contracts/
│   └── MoonHuntersFeeProxy.sol     # Solidity 0.8.20 Fee Proxy Smart Contract
├── generate_architecture_pdf.py    # PDF documentation generator
├── ARCHITECTURE.md                 # This file
├── MOON_HUNTERS_ALGORITHM_REPORT.md # Detailed algorithm documentation
├── replit.md                       # Project memory and quick reference
└── .system_config/                 # Project configuration
```

## System Architecture

### High-Level Overview

Moon Hunters employs a decoupled client-server architecture. The React frontend communicates with the FastAPI backend through three channels: REST API for data requests, WebSocket for live price streaming, and Server-Sent Events (SSE) for trade/balance notifications. The backend is organized into a modular router architecture with 13 route modules, orchestrates 9 core engines, a Trading Intelligence module, and runs 6 always-on background tasks. All persistent data is stored in MongoDB.

```
CoinMarketCap API (every 30s)
        │
        ▼
  MarketProvider (centralized cache + asyncio.Lock)
        │
        ├──► Fast Movers Detector (DUMP ≥0.5%, PUMP ≥1.5%, top 100 coins)
        ├──► Dump Detection Engine (≥3% drops, health-filtered)
        ├──► Price Streaming (WebSocket broadcast)
        │
        ▼
  DataManager (OHLCV candle builder, MongoDB storage)
        │
        ├──► Technical Indicators (NumPy, 10 indicators)
        ├──► Anomaly Detector (IsolationForest + z-scores)
        ├──► Pump/Dump Detector (multi-factor scoring)
        │
        ▼
  Signal Engine (rule-based scoring + GradientBoosting ML adjustment)
        │
        ▼
  Service Orchestrator (caching, batching, API delivery)
```

### Frontend Stack
- **Framework**: React 19 with Vite 6
- **Styling**: Tailwind CSS 3 with shadcn/ui component library (46 Radix UI primitives)
- **State Management**: React hooks and Context API
- **Authentication**: Reown AppKit v1.8.14 (MetaMask, WalletConnect, Coinbase, social logins)
- **Charts**: Recharts v3.4.1 (general), TradingView lightweight-charts (candlestick/OHLC)
- **Animations**: Framer Motion v12.23.26
- **3D Visual**: Spline with ErrorBoundary fallback
- **Real-time Updates**: WebSocket for prices, SSE for events
- **Forms**: React Hook Form v7.56.2 + Zod v3.24.4
- **Blockchain**: ethers.js v6 for wallet interactions and smart contract calls

### Frontend Components (25)
| Component | Description |
|-----------|-------------|
| HomePage | Landing page with 3D Spline hero section and live market preview |
| DynamicDashboard | Main dashboard with portfolio overview, 5 parallel API calls |
| WalletPage | Wallet management, balances, and token swap interface |
| AIEnginePage | AI recommendations interface with 4 parallel API calls |
| AIAutoInvestPage | Automated DCA investment setup and management |
| InvestPage | Dump opportunities marketplace with real-time P&L tracking |
| TradingBotSettings | Bot configuration panel (modes, limits, strategies) |
| AnalyticsDashboard | Performance analytics (win rate, ROI, daily returns) |
| BacktestPage | Strategy backtesting with real CoinGecko historical data |
| LeaderboardPage | Social trading leaderboard with follow/copy features |
| FastMarketMovements | Real-time price movement alerts (public, no auth) |
| SmartAlerts | Alert configuration (pump/dump thresholds, email, push) |
| SwapModal | DEX swap interface via 1inch API v6.0 |
| TradingViewChart | OHLC candlestick charts with TradingView library |
| TopGainersPage | Top performing coins with 5-second auto-refresh |
| PremiumNavbar | Navigation component with wallet status |
| ConnectWalletBtn | Wallet connection button (Reown AppKit trigger) |
| LivePriceIndicator | Real-time price display via WebSocket |
| InfoTooltip | Informational tooltip component |
| RecentTransactions | Transaction history list |
| DisclaimerDialog | Legal disclaimer modal |
| ProtectedRoute | Auth route guard (redirects unauthenticated users) |
| SplineWithFallback | 3D graphics with ErrorBoundary CSS gradient fallback |
| ErrorBoundary | React error boundary for graceful component failure handling |

### Frontend Contexts (3)
| Context | Purpose |
|---------|---------|
| WalletAuthContext | Authentication state, wallet connection, JWT management |
| PriceStreamContext | WebSocket price streaming with auto-reconnect and throttling |
| EventContext | SSE event subscriptions with exponential backoff reconnection |

### Frontend Services (9)
| Service | Purpose |
|---------|---------|
| apiClient | Base axios client with auth headers and 401 interceptor |
| cryptoService | Market data API calls (latest, overview, fast movers, OHLC) |
| dexService | DEX swap operations (quote, swap, allowance, approve) |
| investService | Invest page API (opportunities, positions, summary, trades, reports) |
| contractService | Fee Proxy Smart Contract interactions (buy/sell via SC, allowance) |
| eventService | SSE connection management |
| pushNotificationService | Web push subscriptions and VAPID key management |
| socialTradingService | Social/copy trading (leaderboard, follow, copy settings) |
| backtestingService | Backtesting API (strategies, run simulation) with auth tokens |

### Frontend Configuration
| Config | Purpose |
|--------|---------|
| reown.js | Reown AppKit project ID, supported chains, wallet options |
| contractConfig.js | Multi-chain SC addresses, ABI definitions, fee %, treasury address, USDT addresses, chain explorers |

### Backend Stack
- **Framework**: FastAPI 0.110.1 (Python) with async support
- **Server**: Uvicorn 0.25.0 (ASGI)
- **Database**: MongoDB with Motor 3.3.1 (async driver) / PyMongo 4.5.0
- **Authentication**: JWT (PyJWT 2.10.1) with wallet address verification
- **Ethereum**: eth-account 0.13.7, eth-utils 5.3.1, web3.py 7.14.0
- **Rate Limiting**: SlowAPI 0.1.9
- **HTTP Client**: httpx 0.28.1 (async)
- **Validation**: Pydantic 2.12.4 (30+ schemas)
- **ML/Data**: scikit-learn (IsolationForest, GradientBoosting), NumPy 2.3.4, Pandas 2.3.3
- **Background Tasks**: AsyncIO for real-time monitoring
- **Reports**: CSV/PDF generation via reportlab

### Backend Core Modules
| Module | Purpose |
|--------|---------|
| core/config.py | Environment variable loading, logging configuration |
| core/deps.py | Dependency injection: DB client, engine instances, service singletons |
| core/schemas.py | Pydantic validation models (30+ schemas for all API endpoints) |
| core/indexes.py | MongoDB index management with TTL indexes for ephemeral data |
| core/error_handlers.py | Global exception and validation error handlers |

### Backend Routers (13 modules, 100+ endpoints)
| Router | Prefix | Endpoints | Description |
|--------|--------|-----------|-------------|
| auth.py | /api/auth | 10 | Wallet SIWE auth, email/password auth, JWT management |
| ai.py | /api/ai-engine | 17 | AI recommendations, portfolio, invest, rebalancing |
| invest.py | /api/invest | 9 | Dump opportunities marketplace, positions, P&L reports |
| positions.py | /api (various) | 12 | Position tracking, SL/TP triggers, trade execution |
| dex.py | /api/dex | 9 | 1inch DEX integration (quote, swap, approve, tokens) |
| social.py | /api/social | 10 | Leaderboard, following, copy trading, activity feed |
| portfolio.py | /api/portfolios | 7 | Portfolio CRUD, transaction management |
| alerts.py | /api/alert-settings | 6 | Alert configuration, email/push test alerts |
| intelligence.py | /api/intelligence | 6 | Trading Intelligence signals, anomalies, pump/dump |
| crypto.py | /api/crypto | 5 | Market data (latest, overview, fast movers, OHLC) |
| analytics.py | /api/analytics | 5 | Performance metrics, daily returns, strategy breakdown |
| events.py | /api/events | 3 | SSE streaming, push notification subscriptions |
| backtest.py | /api/backtest | 2 | Strategy list, backtest execution |

### Backend Services (26 modules)
| Module | Purpose |
|--------|---------|
| server.py | Main FastAPI application: middleware pipeline, startup/shutdown, router registration |
| market_provider.py | CoinMarketCap Pro API integration with 30s in-memory cache |
| historical_data_provider.py | CoinGecko API for real historical OHLC data (backtesting) |
| wallet_auth.py | SIWE signature verification, nonce management |
| auth_utils.py | JWT creation, validation, refresh |
| wallet_service.py | On-chain ETH/ERC-20 balance fetching via public RPC |
| trading_bot.py | Automated trading with stop-loss/take-profit, 3 execution modes |
| portfolio_engine.py | Position tracking, PnL calculation, 3 execution modes |
| recommendation_engine.py | AI-powered investment recommendations via Perplexity AI |
| analysis_engine.py | Trend, momentum, volatility analysis for top 100 coins |
| dump_detection_engine.py | 3%+ price dump detection with volume/market cap validation |
| fast_movers_detector.py | Real-time movement detection with dump opportunity creation |
| dex_service.py | 1inch API v6.0 swap integration (quote, swap, approve) |
| analytics_engine.py | Performance metrics, ROI tracking, strategy breakdown |
| social_trading_engine.py | Leaderboard, following, copy trading functionality |
| backtesting_engine.py | Historical strategy simulation (4 strategies, real OHLC data) |
| report_generator.py | CSV and PDF P&L report generation for invest positions |
| email_service.py | SMTP email notifications (Gmail) |
| ai_dump_alert_service.py | AI-powered dump opportunity alerts (5-min background task) |
| push_notification_service.py | VAPID web push notifications via pywebpush |
| event_service.py | Server-Sent Events broadcasting |
| price_streaming.py | WebSocket price updates (30s interval, ping/pong heartbeat) |
| perplexity_client.py | Perplexity AI API client for recommendations |
| nonce_store.py | MongoDB nonce storage with 5-min TTL |
| auto_invest_scheduler.py | Scheduled DCA investments (daily/weekly/monthly) |

### Trading Intelligence Engine (backend/trading_intelligence/)

A production-grade AI-powered trading signal system that analyzes the top 50 coins every 60 seconds. It combines classical technical analysis, statistical anomaly detection, machine learning models, and multi-factor pump/dump analysis.

| Module | Purpose |
|--------|---------|
| data_manager.py | Ingests market data, builds OHLCV candles (5m/15m/1h), stores snapshots in MongoDB |
| indicators.py | NumPy-based computation of RSI(14), MACD(12/26/9), VWAP, Bollinger Bands(20/2σ), Momentum, Volume Delta, ATR, OBV Trend |
| anomaly_detector.py | Hybrid ML + statistical approach: IsolationForest (100 estimators, 5% contamination) + volume/price z-score analysis. Auto-retrains every 5 minutes per symbol |
| pump_dump_detector.py | Multi-factor analysis: volume surge(25%), price velocity(25%), reversal patterns(20%), liquidity traps(15%), external momentum(15%). Outputs 0-100% risk |
| signal_engine.py | Rule-based scoring (9 BUY conditions, 9 SELL conditions) + GradientBoosting ML confidence adjustment. Bootstrapped with 291 seed samples |
| ml_seed_data.py | 291 labeled training samples: 75 BUY (6 archetypes), 75 SELL (6 archetypes), 75 HOLD (5 patterns), 66 ambiguous samples |
| schemas.py | Pydantic schemas for TI data models |
| service.py | Orchestrator: 60s background task, cached signal retrieval, batch processing via asyncio.gather |

#### Signal Generation Flow
1. MarketProvider fetches top 100 coins from CoinMarketCap every 30s (shared cache)
2. DataManager builds OHLCV candles at 5m/15m/1h timeframes from 30s snapshots
3. Technical Indicators computed via NumPy on last 100 candles per symbol
4. Anomaly Detection: IsolationForest inference + z-score analysis
5. Pump/Dump Analysis: 5 independent scoring factors combined via weighted average
6. Signal Engine: rule-based scoring → pump/dump adjustments → anomaly adjustments → market quality scaling → ML confidence blending
7. Signals cached for 30s per symbol

#### Signal Output Format
```json
{
  "signal": "BUY|SELL|HOLD",
  "confidence": 0-95,
  "pump_dump_risk": 0-100,
  "movement_strength": 0.0-1.0,
  "volume_anomaly": true|false,
  "timestamp": "ISO-8601Z",
  "indicators": { "rsi": 45.2, "macd": 0.003, ... },
  "anomaly": { "score": 0.3, "is_anomaly": false },
  "pump_dump": { "risk_percent": 15, "classification": "Normal" },
  "reasons": ["RSI oversold at 28.5", "MACD bullish crossover"]
}
```

## Detection Thresholds

### Fast Movers Detector (`backend/fast_movers_detector.py`)
- **PUMP_THRESHOLD**: +1.5% (1h change)
- **DUMP_THRESHOLD**: -0.5% (1h change)
- **Coin Coverage**: Top 100 by market cap (from CoinMarketCap)
- **Cycle Interval**: 60 seconds
- **Dedup**: 15-minute per-coin cooldown; skips if new magnitude ≤ 1.2× existing
- **Creates dump opportunities** in MongoDB with 1-hour TTL window
- **Diagnostic logging**: Logs skip reason when existing active opportunity found

### Dump Detection Engine (`backend/dump_detection_engine.py`)
- **DUMP_THRESHOLD**: -3.0% (1h or 24h)
- **PUMP_THRESHOLD**: +5.0%
- **Health Filters**: Volume ≥ $1M, Market Cap ≥ $10M, Rank ≤ 100, 7-day trend > -30%
- **Serves as live fallback** when stored opportunities < 5

### Dual-Engine Opportunity Flow
```
Fast Movers (≥0.5% dump)  ──┐
                             ├──► _create_dump_opportunity() ──► MongoDB dump_opportunities
Dump Engine (≥3.0% dump)  ──┘           │
                                        ├── New coin: INSERT with 1h expiry
                                        ├── Existing + 20% deeper: UPDATE expiry
                                        └── Existing + similar: SKIP (logged)
                                              │
                                              ▼
                              Invest API /api/invest/opportunities
                                        ├── Query: expires_at > now
                                        ├── Fallback: Dump Engine live if < 5 stored
                                        ├── Enrich: live prices from MarketProvider
                                        └── Return: opportunities + remaining_seconds
```

## Authentication System

### Wallet Authentication Flow (Primary - SIWE)
1. User clicks "Connect Wallet" → Reown AppKit opens modal (MetaMask, WalletConnect, Coinbase, social logins)
2. Wallet connected → AppKit returns wallet address, WalletAuthContext updates state
3. Frontend sends POST `/api/auth/wallet/nonce` with `{address: '0x...'}`
4. Backend generates cryptographic nonce, stores in MongoDB `auth_nonces` with 5-min TTL
5. Frontend constructs SIWE message with nonce, wallet prompts user to sign
6. Frontend sends POST `/api/auth/wallet/verify` with `{message, signature, address}`
7. Backend uses eth-account to recover signer address, verifies match, consumes nonce atomically
8. Backend creates JWT token (HS256) containing wallet address, returns token + user data
9. JWT stored in localStorage, all API calls include `Authorization: Bearer <token>`
10. `get_current_user()` dependency decodes JWT, looks up user in MongoDB on every request

### Direct Wallet Connect (Simplified)
POST `/api/auth/wallet/connect` provides a simplified flow without SIWE signature verification, creating/retrieving a user by wallet address and issuing a JWT directly.

### Email/Password Authentication (Fallback)
POST `/api/auth/signup` accepts email, username, password. Passwords hashed with bcrypt via passlib. POST `/api/auth/login` verifies credentials and returns JWT.

### Session Management
- JWT tokens are stateless but validated against MongoDB on each request
- POST `/api/auth/wallet/refresh` issues new tokens for long-lived sessions
- Axios interceptor catches 401 responses, clears localStorage, forces re-authentication

### Frontend Auth Requirements
All pages except the landing page require wallet authentication (ProtectedRoute wrapper).

| Service | Auth | Notes |
|---------|------|-------|
| investService.js | Bearer token on all calls | Opportunities, positions, summary, trades, reports |
| contractService.js | Wallet signing (ethers.js) | Smart contract interactions via browser wallet |
| backtestingService.js | Bearer token on all calls | Strategies and backtest execution |
| AIEnginePage.jsx | Bearer token on all calls | Signals, dump-opportunities, recommendations |
| cryptoService.js | No auth (public) | Market data, fast movers, OHLC |

### Authentication Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/wallet/connect` | POST | Direct wallet auth (primary) |
| `/api/auth/wallet/me` | GET | Validate current session |
| `/api/auth/wallet/logout` | POST | End session |
| `/api/auth/wallet/nonce` | POST | Generate SIWE nonce |
| `/api/auth/wallet/verify` | POST | Verify SIWE signature |
| `/api/auth/wallet/refresh` | POST | Refresh JWT token |
| `/api/auth/signup` | POST | Register with email/password |
| `/api/auth/login` | POST | Login with email/password |

## Invest Section Architecture

### Dump Opportunities Marketplace
The Invest page (`/invest`) is a marketplace where AI-detected dumped coins appear with 1-hour buying windows. The detection uses a dual-engine approach:

1. **Fast Movers Detector**: Scans top 100 coins every 60 seconds for ≥0.5% dumps (1h change)
2. **Dump Detection Engine**: Deeper analysis for ≥3.0% dumps with health filters (volume, market cap, rank, trend)
3. **Live Fallback**: If fewer than 5 stored opportunities exist, the invest API calls the dump engine in real-time

### Fee Proxy Smart Contract
Trades can execute through the `MoonHuntersFeeProxy.sol` contract which:
- Collects a 2% fee (200 bps) on buy/sell transactions
- Routes swaps through the 1inch Aggregation Router v6 for best prices
- Includes ReentrancyGuard, slippage protection, max fee cap, token whitelisting, emergency recovery
- Falls back to direct 1inch swaps on chains where the SC is not deployed

### Multi-Chain Support
| Chain | Chain ID | SC Deployed | Swap Method |
|-------|----------|-------------|-------------|
| Ethereum | 1 | Pending | Direct 1inch |
| Polygon | 137 | Pending | Direct 1inch |
| Arbitrum | 42161 | Pending | Direct 1inch |
| BSC | 56 | Pending | Direct 1inch |
| Sepolia | 11155111 | Active | Fee Proxy SC |

### P&L Reports
The invest section supports CSV and PDF export of position P&L data via `report_generator.py`, accessible through `/api/invest/report`.

## Smart Contract Deployment

### Sepolia Testnet (Active)
- **Contract**: `0x5e9Fb4cC805417552340Baa30FB9333A2953Cdf4`
- **Etherscan**: https://sepolia.etherscan.io/address/0x5e9Fb4cC805417552340Baa30FB9333A2953Cdf4#code
- **USDT**: `0x7169D38820dfd117C3FA1f22a697dBA58d90BA06`
- **Treasury**: `0x6426173D34f490641d4b70797dB57C3DB6cEF71d`
- **Fee**: 2% (200 bps)
- **Whitelisted tokens**: WETH, USDT, LINK, UNI

### Mainnet (Pending)
- ETH, Polygon, Arbitrum, BSC addresses are empty in `contractConfig.js`
- Frontend dynamically falls back to direct 1inch swaps on those chains

## Security & Middleware

### Middleware Pipeline (Execution Order)
| Order | Middleware | Description |
|-------|-----------|-------------|
| 1 | CORS Middleware | Validates Origin against CORS_ORIGINS env var. Allows credentials, all methods and headers |
| 2 | Request ID Middleware | Generates UUID if no X-Request-ID header. All logs include first 8 chars for traceability |
| 3 | Security Headers | Injects CSP, X-Content-Type-Options: nosniff, X-Frame-Options: SAMEORIGIN, X-XSS-Protection, Referrer-Policy, Permissions-Policy |
| 4 | Rate Limiter (SlowAPI) | Uses get_real_client_ip() extracting from X-Forwarded-For, X-Real-IP, or CF-Connecting-IP |

### Rate Limits
| Endpoint | Limit | Reason |
|----------|-------|--------|
| /api/ (root) | 100/min | General API access |
| /api/auth/wallet/nonce | 30/min | Prevent nonce flooding |
| /api/auth/signup | 5/min | Prevent mass account creation |
| /api/auth/login | 10/min | Brute-force protection |
| /api/crypto/test-alert | 5/min | Prevent alert spam |

### Content Security Policy
| Directive | Allowed Sources |
|-----------|----------------|
| default-src | 'self' |
| script-src | 'self' 'unsafe-inline' cdn.jsdelivr.net, googletagmanager, walletconnect, reown, unpkg |
| style-src | 'self' 'unsafe-inline' fonts.googleapis.com |
| connect-src | 'self' https: wss: ws: (APIs, WebSocket, wallet connections) |
| frame-src | 'self' walletconnect.com, reown.com (wallet modals) |
| object-src | 'none' |
| img-src | 'self' data: blob: https: |

### Input Validation
All API request bodies validated using Pydantic models (30+ schemas). Invalid requests receive 422 Unprocessable Entity with field-level error messages.

## Timestamp Handling Convention

All backend datetime serialization uses `.isoformat() + "Z"` to ensure proper UTC timestamps. This prevents timezone misinterpretation by JavaScript's `new Date()` parser, which treats ISO strings without timezone indicators as local time.

- **Backend**: All `expires_at`, `detected_at`, `fetched_at` fields include "Z" suffix
- **Frontend**: Uses server-computed `remaining_seconds` as primary filter for time-sensitive data (e.g., opportunity expiration), with `expires_at` parsing as fallback
- **MongoDB**: Stores native `datetime` objects (always UTC via `datetime.utcnow()`)

## API Endpoints

### Public Endpoints (No Authentication)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/crypto/latest` | GET | Top coins with prices, changes, sparklines |
| `/api/crypto/market-overview` | GET | Global market stats, top gainers/losers |
| `/api/crypto/fast-movers` | GET | Recent movement alerts |
| `/api/crypto/market-health` | GET | Market health score |
| `/api/crypto/ohlc/{symbol}` | GET | OHLC candlestick data |
| `/health` | GET | API health check |

### AI Engine (Authenticated)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ai-engine/wallet-status` | GET | Wallet USDT balance |
| `/api/ai-engine/dump-opportunities` | GET | Dump opportunities from AI |
| `/api/ai-engine/market-analysis` | GET | Comprehensive analysis |
| `/api/ai-engine/signals` | GET | Quick market signals |
| `/api/ai-engine/recommendations` | POST | AI recommendations |
| `/api/ai-engine/portfolio` | GET | User's AI portfolio |
| `/api/ai-engine/invest` | POST | Create position |
| `/api/ai-engine/invest-auto` | POST | Auto-invest with AI |
| `/api/ai-engine/close-position/{id}` | POST | Close position |
| `/api/ai-engine/record-dex-swap` | POST | Record DEX swap |
| `/api/ai-engine/close-dex-position` | POST | Close with DEX sell |
| `/api/ai-engine/rebalancing` | GET | Rebalancing suggestions |
| `/api/ai-engine/top100` | GET | Top 100 with analysis |

### Trading Intelligence (Authenticated)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/intelligence/signal/{symbol}` | GET | Signal for a specific coin |
| `/api/intelligence/signals` | GET | Signals for all tracked coins |
| `/api/intelligence/top-signals` | GET | Top BUY/SELL signals by confidence |
| `/api/intelligence/anomalies` | GET | Detected anomalies |
| `/api/intelligence/pump-dump-alerts` | GET | Active pump/dump alerts |
| `/api/intelligence/stats` | GET | System statistics |

### Invest (Authenticated)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/invest/opportunities` | GET | Active dump opportunities (with live fallback) |
| `/api/invest/positions` | GET | User's invest positions |
| `/api/invest/summary` | GET | Portfolio summary (invested, PnL, active count) |
| `/api/invest/buy` | POST | Record buy trade |
| `/api/invest/sell` | POST | Record sell trade |
| `/api/invest/trigger` | POST | Set SL/TP trigger |
| `/api/invest/trigger/{id}` | DELETE | Remove trigger |
| `/api/invest/report` | GET | Export CSV/PDF P&L report |

### Trading Bot (Authenticated)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/trading-bot/status` | GET | Bot status and trades |
| `/api/trading-bot/settings` | GET/POST | Bot configuration |
| `/api/trading-bot/enable` | POST | Enable bot |
| `/api/trading-bot/disable` | POST | Disable bot |
| `/api/trading-bot/trigger/{id}` | POST/DELETE | Manage triggers |
| `/api/trading-bot/triggers` | GET | Active triggers |
| `/api/trading-bot/pending-trades` | GET | Pending DEX trades |
| `/api/trading-bot/confirm-trade/{id}` | POST | Confirm DEX trade |
| `/api/trading-bot/reject-trade/{id}` | POST | Reject DEX trade |
| `/api/trading-bot/daily-stats` | GET | Today's trade count, invested, PnL |

### DEX Integration (1inch API v6.0, Authenticated)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dex/spender` | GET | 1inch router address |
| `/api/dex/quote` | POST | Get swap quote |
| `/api/dex/swap` | POST | Generate swap transaction |
| `/api/dex/allowance` | GET | Check token allowance |
| `/api/dex/approve` | POST | Generate approval tx |
| `/api/dex/tokens` | GET | Supported tokens |
| `/api/dex/liquidity-sources` | GET | Available DEX protocols |
| `/api/dex/transactions` | GET | User's DEX swap history |

### Analytics (Authenticated)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analytics/performance` | GET | Win rate, ROI |
| `/api/analytics/daily-returns` | GET | Daily PnL |
| `/api/analytics/strategy-breakdown` | GET | By strategy |
| `/api/analytics/coin-performance` | GET | By coin |
| `/api/analytics/bot-analytics` | GET | Bot metrics |

### Social Trading (Authenticated)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/social/leaderboard` | GET | Trading leaderboard |
| `/api/social/trader/{id}` | GET | Trader portfolio |
| `/api/social/settings` | GET/POST | Social settings |
| `/api/social/following` | GET | Following list |
| `/api/social/follow/{id}` | POST/DELETE | Follow/unfollow |
| `/api/social/copy-settings/{id}` | POST | Copy settings |
| `/api/social/activity` | GET | Activity feed |
| `/api/social/my-stats` | GET | User stats |

### Backtesting (Authenticated)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/backtest/strategies` | GET | Available strategies |
| `/api/backtest/run` | POST | Run backtest |

### Alerts (Authenticated)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/alert-settings` | GET/POST | Get/update alert preferences |
| `/api/crypto/test-alert` | POST | Send test alert email |
| `/api/push/vapid-key` | GET | Get VAPID public key |
| `/api/push/subscribe` | POST | Subscribe to push notifications |
| `/api/push/unsubscribe` | POST | Unsubscribe from push |

### Portfolio (Authenticated)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/portfolios` | GET/POST | List/create portfolios |
| `/api/portfolios/{id}` | GET/PUT/DELETE | Portfolio CRUD |
| `/api/transactions` | GET/POST | Transaction history |

### Events (Authenticated)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/events/stream` | GET | SSE event stream |

## External Dependencies

### APIs and Services
- **CoinMarketCap API**: Live cryptocurrency market data (top 100 coins, global stats)
- **CoinGecko API**: Historical OHLC data for backtesting
- **Perplexity AI API**: AI-driven investment recommendations and analysis
- **1inch DEX API v6.0**: Real-time swap quotes and transaction generation
- **Ethereum Public RPC**: For ETH and ERC-20 wallet balance lookups (multi-provider with failover)
- **SMTP (Gmail)**: For email-based alerts (daily sending limits apply)
- **Web Push (VAPID)**: For browser push notifications

### Database
- **MongoDB**: Primary data store for user data, positions, bots, alerts, and analytics. Includes centralized index management with TTL indexes for ephemeral data (dump opportunities, nonces, crypto prices).

### Blockchain Infrastructure
- **Reown AppKit**: Manages Web3 wallet connections (frontend)
- **ethers.js v6**: Frontend Ethereum interactions and smart contract calls
- **eth-account / eth-utils**: Backend signature verification
- **web3.py**: Server-side Ethereum interactions

## Background Tasks (6 always-on)
| Task | Interval | Purpose |
|------|----------|---------|
| Fast Movers Detector | 60s | Scan top 100 coins for ≥0.5% dumps / ≥1.5% pumps, create opportunities |
| Trading Intelligence | 60s | Compute signals, anomalies, pump/dump risk for top 50 coins |
| Price Streaming | 30s | Broadcast live prices via WebSocket to connected clients |
| AI Dump Alert Service | 5min | Send email/push alerts for new dump opportunities |
| Auto-Invest Scheduler | 1min | Execute scheduled DCA investments |
| Data Cleanup | 60 cycles | Remove expired prices, movements, cooldowns |

## Testing
- **73 backend tests** across 4 test files (excluding `test_user_with_alerts_enabled`)
- Test files: `test_api.py`, `test_authenticated_endpoints.py`, `test_ai_dump_alerts.py`, `test_trading_intelligence.py`
- Shared fixtures in `conftest.py`
- Run: `cd backend && python -m pytest tests/ -x -q -k "not test_user_with_alerts_enabled"`
