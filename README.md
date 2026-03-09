# Moon Hunters - AI-Powered Crypto Investment Platform

## Overview

Moon Hunters is a full-stack cryptocurrency investment platform designed to empower users with AI-driven insights and real-time market awareness. It features wallet-based authentication via Reown AppKit with support for MetaMask, WalletConnect, Coinbase, and social logins, a dynamic dashboard for portfolio tracking, rapid detection of significant market movements, automated trading bots, and smart alerts for price movements. The platform supports both simulated and real DEX execution through the 1inch aggregator.

## Project Structure

```
/
├── backend/                        # Python FastAPI backend
│   ├── server.py                   # Main FastAPI application (all endpoints)
│   ├── market_provider.py          # CoinMarketCap API integration with caching
│   ├── historical_data_provider.py # CoinGecko API for real historical OHLC data
│   ├── wallet_auth.py              # SIWE signature verification, nonce management
│   ├── auth_utils.py               # JWT creation, validation, refresh
│   ├── wallet_service.py           # On-chain ETH/ERC-20 balance fetching via RPC
│   ├── trading_bot.py              # Automated trading engine with stop-loss/take-profit
│   ├── portfolio_engine.py         # Position tracking and management
│   ├── recommendation_engine.py    # AI-powered investment recommendations
│   ├── analysis_engine.py          # Trend, momentum, volatility analysis
│   ├── dump_detection_engine.py    # 5%+ price dump detection
│   ├── fast_movers_detector.py     # Real-time ±1.5% movement detection
│   ├── dex_service.py              # 1inch DEX API v6.0 swap integration
│   ├── analytics_engine.py         # Performance metrics and ROI tracking
│   ├── social_trading_engine.py    # Leaderboard, following, copy trading
│   ├── backtesting_engine.py       # Historical strategy simulation with real data
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
│   └── tests/                      # Test files
│       ├── test_authenticated_endpoints.py
│       ├── test_ai_dump_alerts.py
│       └── test_trading_intelligence.py
├── frontend/                       # React Vite frontend
│   ├── src/
│   │   ├── components/             # 24 React components
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
│   │   │   ├── InfoTooltip.jsx
│   │   │   └── ui/                 # shadcn/ui primitives (25+ Radix components)
│   │   ├── contexts/               # 3 React contexts
│   │   │   ├── WalletAuthContext.jsx
│   │   │   ├── PriceStreamContext.jsx
│   │   │   └── EventContext.jsx
│   │   ├── services/               # 7 API service modules
│   │   │   ├── apiClient.js
│   │   │   ├── cryptoService.js
│   │   │   ├── dexService.js
│   │   │   ├── eventService.js
│   │   │   ├── pushNotificationService.js
│   │   │   ├── socialTradingService.js
│   │   │   └── backtestingService.js
│   │   ├── config/                 # App configuration
│   │   │   └── reown.js            # Reown AppKit config
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
├── generate_architecture_pdf.py    # PDF documentation generator
├── ARCHITECTURE.md                 # This file
├── MOON_HUNTERS_ALGORITHM_REPORT.md # Detailed algorithm documentation
├── replit.md                       # Project memory and quick reference
└── .system_config/                 # Project configuration
```

## System Architecture

### High-Level Overview

Moon Hunters employs a decoupled client-server architecture. The React frontend communicates with the FastAPI backend through three channels: REST API for data requests, WebSocket for live price streaming, and Server-Sent Events (SSE) for trade/balance notifications. The backend orchestrates 8 core engines, a Trading Intelligence module, and runs 6 always-on background tasks. All persistent data is stored in MongoDB.

```
CoinMarketCap API (every 30s)
        │
        ▼
  MarketProvider (centralized cache + asyncio.Lock)
        │
        ├──► Fast Movers Detector (±1.5% movements)
        ├──► Dump Detection Engine (5%+ drops)
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
- **Styling**: Tailwind CSS 3 with shadcn/ui component library (25+ Radix UI primitives)
- **State Management**: React hooks and Context API
- **Authentication**: Reown AppKit v1.8.14 (MetaMask, WalletConnect, Coinbase, social logins)
- **Charts**: Recharts v3.4.1 (general), TradingView lightweight-charts (candlestick/OHLC)
- **Animations**: Framer Motion v12.23.26
- **3D Visual**: Spline with ErrorBoundary fallback
- **Real-time Updates**: WebSocket for prices, SSE for events
- **Forms**: React Hook Form v7.56.2 + Zod v3.24.4

### Frontend Components (24)
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
| FastMarketMovements | Real-time ±1.5% price movement alerts |
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

### Frontend Contexts (3)
| Context | Purpose |
|---------|---------|
| WalletAuthContext | Authentication state, wallet connection, JWT management |
| PriceStreamContext | WebSocket price streaming with auto-reconnect and throttling |
| EventContext | SSE event subscriptions with exponential backoff reconnection |

### Frontend Services (7)
| Service | Purpose |
|---------|---------|
| apiClient | Base axios client with auth headers and 401 interceptor |
| cryptoService | Market data API calls (latest, overview, fast movers, OHLC) |
| dexService | DEX swap operations (quote, swap, allowance, approve) |
| eventService | SSE connection management |
| pushNotificationService | Web push subscriptions and VAPID key management |
| socialTradingService | Social/copy trading (leaderboard, follow, copy settings) |
| backtestingService | Backtesting API (strategies, run simulation) |

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

### Backend Services (25 modules)
| Module | Purpose |
|--------|---------|
| server.py | Main FastAPI application with all endpoints (70+ endpoints) |
| market_provider.py | CoinMarketCap Pro API integration with 30s in-memory cache |
| historical_data_provider.py | CoinGecko API for real historical OHLC data (backtesting) |
| wallet_auth.py | SIWE signature verification, nonce management |
| auth_utils.py | JWT creation, validation, refresh |
| wallet_service.py | On-chain ETH/ERC-20 balance fetching via public RPC |
| trading_bot.py | Automated trading with stop-loss/take-profit, 3 execution modes |
| portfolio_engine.py | Position tracking, PnL calculation, 3 execution modes |
| recommendation_engine.py | AI-powered investment recommendations via Perplexity AI |
| analysis_engine.py | Trend, momentum, volatility analysis for top 100 coins |
| dump_detection_engine.py | 5%+ price dump detection with volume validation |
| fast_movers_detector.py | Real-time ±1.5% movement detection with 15-min cooldowns |
| dex_service.py | 1inch API v6.0 swap integration (quote, swap, approve) |
| analytics_engine.py | Performance metrics, ROI tracking, strategy breakdown |
| social_trading_engine.py | Leaderboard, following, copy trading functionality |
| backtesting_engine.py | Historical strategy simulation (4 strategies, real OHLC data) |
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
  "timestamp": "ISO-8601",
  "indicators": { "rsi": 45.2, "macd": 0.003, ... },
  "anomaly": { "score": 0.3, "is_anomaly": false },
  "pump_dump": { "risk_percent": 15, "classification": "Normal" },
  "reasons": ["RSI oversold at 28.5", "MACD bullish crossover"]
}
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

## API Endpoints

### Market Data
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/crypto/latest` | GET | Top coins with prices, changes, sparklines |
| `/api/crypto/market-overview` | GET | Global market stats, top gainers/losers |
| `/api/crypto/fast-movers` | GET | Recent ±1.5%+ movements |
| `/api/crypto/market-health` | GET | Market health score |
| `/api/crypto/ohlc/{symbol}` | GET | OHLC candlestick data |
| `/health` | GET | API health check |

### AI Engine
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ai-engine/wallet-status` | GET | Wallet USDT balance |
| `/api/ai-engine/dump-opportunities` | GET | 5%+ dump opportunities |
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

### Trading Intelligence
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/intelligence/signal/{symbol}` | GET | Signal for a specific coin |
| `/api/intelligence/signals` | GET | Signals for all tracked coins |
| `/api/intelligence/top-signals` | GET | Top BUY/SELL signals by confidence |
| `/api/intelligence/anomalies` | GET | Detected anomalies |
| `/api/intelligence/pump-dump-alerts` | GET | Active pump/dump alerts |
| `/api/intelligence/stats` | GET | System statistics |

### Trading Bot
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

### DEX Integration (1inch API v6.0)
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

### Analytics
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analytics/performance` | GET | Win rate, ROI |
| `/api/analytics/daily-returns` | GET | Daily PnL |
| `/api/analytics/strategy-breakdown` | GET | By strategy |
| `/api/analytics/coin-performance` | GET | By coin |
| `/api/analytics/bot-analytics` | GET | Bot metrics |

### Social Trading
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

### Backtesting
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/backtest/strategies` | GET | Available strategies |
| `/api/backtest/run` | POST | Run backtest |

### Push Notifications
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/push/vapid-key` | GET | VAPID public key |
| `/api/push/subscribe` | POST | Register subscription |
| `/api/push/unsubscribe` | POST | Remove subscription |
| `/api/push/test` | POST | Test notification |

### Alerts
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/alerts/settings` | GET/POST | Alert configuration |
| `/api/alerts/ai-dump/settings` | GET/POST | AI dump alert settings |

### WebSocket
| Endpoint | Description |
|----------|-------------|
| `WS /ws/prices` | Real-time price streaming (30s updates, ping/pong heartbeat) |
| `GET /api/ws/status` | WebSocket connection status |

## Database Schema (MongoDB)

| Collection | Purpose | Key Fields | Indexes |
|------------|---------|------------|---------|
| users | User accounts | wallet_address, email, username, created_at, settings | wallet_address (unique), email (unique) |
| ai_positions | Investment positions | user_id, symbol, status, entry_price, quantity, invested_usdt, pnl, execution_mode | user_id, status, created_at |
| alert_settings | User alert prefs | user_id, pump_threshold, dump_threshold, email_enabled, push_enabled | user_id (unique) |
| auth_nonces | Login nonces | wallet_address, nonce, created_at | wallet_address (unique), created_at (TTL: 5min) |
| crypto_prices | Price snapshots | symbol, name, price, timestamp, market_cap, volume_24h | symbol + timestamp (compound) |
| fast_movers | Detected movements | symbol, price_change_percent, movement_type, timestamp | timestamp, symbol |
| bot_settings | Bot configuration | user_id, enabled, execution_mode, max_daily_investment, strategies | user_id (unique) |
| transactions | Trade records | user_id, type, symbol, amount, status, tx_hash, timestamp | user_id, timestamp |
| auto_invest_configs | DCA schedules | user_id, frequency, amount, target_coins, next_execution | user_id (unique) |
| push_subscriptions | Push endpoints | user_id, endpoint, keys, created_at | user_id, endpoint |

## Environment Variables

### Required Secrets
| Variable | Description |
|----------|-------------|
| `MONGO_URL` | MongoDB connection string |
| `DB_NAME` | MongoDB database name |
| `JWT_SECRET_KEY` | JWT signing secret (HS256) |
| `CMC_API_KEY` | CoinMarketCap Pro API key |
| `PERPLEXITY_API_KEY` | Perplexity AI API key |
| `ONEINCH_API_KEY` | 1inch DEX API key |
| `SMTP_USERNAME` | Email username |
| `SMTP_PASSWORD` | Email password |
| `SMTP_SERVER` | SMTP server (default: smtp.gmail.com) |
| `SMTP_PORT` | SMTP port (default: 587) |
| `SMTP_FROM_EMAIL` | Sender email address |
| `VAPID_PRIVATE_KEY` | Web push private key |
| `VAPID_PUBLIC_KEY` | Web push public key |
| `REOWN_SECRET` | Reown project secret |

### Frontend Environment Variables
| Variable | Description |
|----------|-------------|
| `VITE_REOWN_PROJECT_ID` | Reown project ID (required) |
| `VITE_BACKEND_URL` | Backend API URL (optional, uses proxy in dev) |

### Production Environment Variables
| Variable | Description |
|----------|-------------|
| `CORS_ORIGINS` | Allowed CORS origins |

## Key Features

### AI-Powered Investment
- **5% Dump Detection**: Scans top 100 coins for significant price dumps with volume validation
- **Trend Analysis**: Momentum, volatility, and trend strength calculations
- **Risk Scoring**: 0.0 (best) to 1.0 (worst) based on multiple factors
- **Auto-Allocation**: AI-driven portfolio allocation with limits (40% dump-buy, 60% trend-follow)
- **Perplexity AI Integration**: Natural language market analysis and recommendations

### Trading Intelligence (ML-Powered)
- **10 Technical Indicators**: RSI, MACD, VWAP, Bollinger Bands, Momentum, Volume Delta, ATR, OBV Trend
- **Anomaly Detection**: IsolationForest (100 estimators) + statistical z-scores, per-symbol models
- **Pump/Dump Detection**: 5-factor weighted analysis (volume surge, price velocity, reversal patterns, liquidity traps, external momentum)
- **ML Signal Enhancement**: GradientBoosting classifier with 291 seed samples, 15-30% blend weight
- **Signal Output**: BUY/SELL/HOLD with 0-95% confidence per coin, updated every 60 seconds

### Real-time Monitoring
- **Fast Movers**: ±1.5% movement detection with 15-minute cooldowns
- **Price Streaming**: WebSocket-based live updates every 30 seconds with ping/pong heartbeat
- **SSE Events**: Instant notifications for trades, balance changes, auto-invest executions
- **Push Notifications**: Browser-based alerts via VAPID/Web Push

### Trading Automation
- **Trading Bot**: Automated buy/sell with configurable triggers and 3 execution modes
- **Stop-Loss/Take-Profit**: Price-based position management with auto-close
- **DEX Execution**: 1inch API v6.0 for real on-chain swaps
- **Multi-chain**: Ethereum (1), Polygon (137), Arbitrum (42161)
- **Auto-Invest (DCA)**: Scheduled daily/weekly/monthly investments with AI allocation

### Social Features
- **Leaderboard**: Ranking by performance metrics (all-time, weekly, monthly)
- **Copy Trading**: Follow and copy successful traders' settings
- **Activity Feed**: Real-time updates from followed traders

### Backtesting
- **4 Strategies**: dump_buy, trend_follow, dca, momentum
- **Real Historical Data**: CoinGecko OHLC (free, no API key needed)
- **40+ Supported Coins**: Major cryptocurrencies
- **Max Duration**: 365 days
- **Metrics**: Total return, max drawdown, Sharpe ratio, win rate, equity curve

## External APIs

| Service | Purpose | Cache | Key Required |
|---------|---------|-------|--------------|
| CoinMarketCap Pro | Live market data, prices, rankings | 30s in-memory | Yes (CMC_API_KEY) |
| CoinGecko (Free) | Historical OHLC data for backtesting | 1h cache, 1.5s rate limit | No |
| Perplexity AI | AI-powered recommendations and analysis | No (real-time) | Yes (PERPLEXITY_API_KEY) |
| 1inch API v6.0 | DEX swap routing and execution | No (real-time) | Yes (ONEINCH_API_KEY) |
| Ethereum Public RPC | On-chain balances (ETH + ERC-20) | No (live) | No |
| Reown AppKit | Web3 wallet connections (frontend) | N/A | Yes (Project ID) |
| Gmail SMTP | Email notifications and alerts | N/A (on-trigger) | Yes (app password) |

## Error Handling & Resilience

### Frontend
| Mechanism | Where Used | Description |
|-----------|-----------|-------------|
| Error Boundaries | SplineWithFallback | React ErrorBoundary wraps Spline 3D, shows CSS gradient fallback on crash |
| Promise.all with .catch() | DynamicDashboard | Each parallel API call has individual .catch() returning empty defaults |
| WebSocket Reconnection | PriceStreamContext | 3-second reconnect delay, 30s ping/pong heartbeat, 100ms message throttling |
| SSE Reconnection | EventContext | Auto-reconnect with exponential backoff, reconnects on visibility change |
| API Interceptors | apiClient.js | 401 response clears localStorage and forces re-authentication |
| Loading States | All pages | Spinner during data fetch prevents rendering with undefined data |
| Toast Notifications | use-toast hook | Non-blocking success/error notifications for user actions |

### Backend
| Mechanism | Description |
|-----------|-------------|
| HTTPException | Appropriate status codes (400, 401, 403, 404, 422, 500) with descriptive messages |
| Pydantic Validation | Request bodies validated before handler code, 422 with field-level errors |
| Background Task Try/Catch | All background tasks wrap main loop in try/except to prevent crashes |
| Graceful Degradation | Missing API key logs warning, server continues with other features |
| Request ID Tracing | Every log includes request ID for end-to-end debugging |

## Deployment

### Development
- Frontend: `cd frontend && npm run dev` on port 5000
- Backend: `cd backend && python -m uvicorn server:app --host localhost --port 8000 --reload`
- Vite proxy forwards `/api/*` to backend

### Production
- Frontend: Static build via `npm run build`
- Backend: Gunicorn with uvicorn workers
- Database: MongoDB Atlas with TLS/SSL connection
- CORS: Configured for production domain

## Background Tasks

| Task | Interval | Purpose |
|------|----------|---------|
| Fast Movers Detector | ~60s | Detects ±1.5% price movements |
| Trading Bot Loop | ~60s | Scans for dump-buy entries, checks stop-loss/take-profit |
| Price Broadcast | 30s | Pushes prices to all WebSocket clients |
| AI Dump Alerts | 5min | Monitors dump opportunities, sends notifications |
| TI Data Ingestion | 60s | Candle building, snapshot storage, signal generation |
| TI Model Pre-warming | 5min | Retrain IsolationForest per symbol |

## Performance Metrics

### Signal Computation Timing (Per Symbol)
| Stage | Latency |
|-------|---------|
| OHLCV data retrieval from MongoDB | ~5-15ms |
| Technical indicator computation (NumPy) | <1ms |
| Anomaly detection inference | <1ms |
| Pump/dump analysis | <1ms |
| Signal engine (rules + ML) | <2ms |
| **Total (warm cache)** | **~10-20ms** |
| **Total (cold, DB fetch)** | **~25-40ms** |

### Memory Footprint
| Component | Size |
|-----------|------|
| GradientBoosting model (50 trees, depth 3) | ~200KB |
| IsolationForest per symbol (100 trees) | ~500KB each |
| 50 anomaly models loaded | ~25MB total |
| Signal cache (50 symbols) | ~100KB |
| Price buffer (500 ticks/symbol, 50 symbols) | ~5MB |

---

## Developer Guide

### Prerequisites
- Python 3.11+
- Node.js 20+
- MongoDB instance (local or Atlas)
- Git

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd moon-hunters
   ```

2. **Set up environment variables**
   Copy the required secrets listed in the Environment Variables section above. At minimum you need:
   - `MONGO_URL` - MongoDB connection string
   - `JWT_SECRET_KEY` - Any random secret string for JWT signing
   - `CMC_API_KEY` - CoinMarketCap Pro API key (for live market data)
   - `VITE_REOWN_PROJECT_ID` - Reown project ID (for wallet connections)

3. **Install backend dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   ```

5. **Start the backend**
   ```bash
   cd backend
   python -m uvicorn server:app --host localhost --port 8000 --reload
   ```

6. **Start the frontend** (in a separate terminal)
   ```bash
   cd frontend
   npm run dev
   ```

7. **Access the application**
   - Frontend: http://localhost:5000
   - Backend API: http://localhost:8000
   - API Docs (Swagger): http://localhost:8000/docs

### Project Architecture for Developers

#### How the Frontend Communicates with the Backend

The Vite dev server proxies `/api/*` requests to the backend at port 8000. In production, CORS is configured via `CORS_ORIGINS` env var.

Three communication channels:
- **REST API** (HTTP): All CRUD operations, market data, portfolio management
- **WebSocket** (`WS /ws/prices`): Live price streaming every 30 seconds
- **SSE** (`GET /api/events/stream`): One-way push for trade events, balance updates

#### How Data Flows Through the Backend

1. **Market Data Pipeline**: CoinMarketCap → MarketProvider (30s cache) → consumed by all engines
2. **AI Pipeline**: MarketProvider → DumpDetection + Analysis → RecommendationEngine → Perplexity AI → Recommendations
3. **Trading Intelligence Pipeline**: MarketProvider → DataManager → Indicators/Anomaly/PumpDump → SignalEngine → Cached Signals
4. **Trading Bot Pipeline**: MarketProvider → DumpDetection → Bot Settings filter → Pending Trade → User Confirm → Execute
5. **Real-time Pipeline**: MarketProvider → WebSocket broadcast / FastMovers detection → SSE events

#### Adding a New Backend Endpoint

1. Define Pydantic request/response models in `server.py`
2. Add the route handler in `server.py` with appropriate auth dependency (`get_current_user` or `get_optional_user`)
3. Apply rate limiting with `@limiter.limit("X/minute")`
4. Add the endpoint to this documentation

#### Adding a New Frontend Page

1. Create component in `frontend/src/components/YourPage.jsx`
2. Add route in `frontend/src/App.jsx`
3. Wrap with `<ProtectedRoute>` if authentication is required
4. Use `apiClient` from `services/apiClient.js` for API calls
5. Use `PriceStreamContext` if real-time prices are needed
6. Follow existing patterns: loading states, error handling, toast notifications

#### Adding a New Trading Intelligence Indicator

1. Add computation in `backend/trading_intelligence/indicators.py` (NumPy-based)
2. Include in the feature vector returned by `compute_all()`
3. Add BUY/SELL conditions in `signal_engine.py`
4. Update the ML feature vector if used for GradientBoosting
5. Add tests in `backend/tests/test_trading_intelligence.py`

### Code Conventions

- **Backend**: Python with type hints, async/await for all I/O, Pydantic models for validation
- **Frontend**: React functional components with hooks, JSX, Tailwind CSS utility classes
- **Naming**: snake_case (Python), camelCase (JavaScript), PascalCase (React components)
- **Error Handling**: Always use try/catch in background tasks, .catch() on Promise chains
- **State Management**: React Context for global state, useState/useMemo for local state
- **API Calls**: Always through service modules in `frontend/src/services/`, never direct axios calls in components

### Testing

Run backend tests:
```bash
cd backend
python -m pytest tests/ -v
```

Test files:
- `test_authenticated_endpoints.py` - Tests for auth-protected API endpoints
- `test_ai_dump_alerts.py` - Tests for AI dump alert service
- `test_trading_intelligence.py` - Tests for the Trading Intelligence engine

### Key Dependencies

#### Backend (Python)
| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.110.1 | Async web framework with auto OpenAPI docs |
| uvicorn | 0.25.0 | ASGI server with hot reload |
| motor / pymongo | 3.3.1 / 4.5.0 | Async MongoDB driver |
| pydantic | 2.12.4 | Data validation (30+ models) |
| PyJWT / python-jose | 2.10.1 / 3.5.0 | JWT token management |
| eth-account / eth-utils / web3 | 0.13.7 / 5.3.1 / 7.14.0 | Ethereum interaction |
| httpx | 0.28.1 | Async HTTP client |
| slowapi | 0.1.9 | Rate limiting |
| numpy / pandas | 2.3.4 / 2.3.3 | Data analysis and ML features |
| pywebpush / py-vapid | 2.1.2 / 1.9.2 | Web push notifications |
| passlib + bcrypt | 1.7.4 / 4.1.3 | Password hashing |

#### Frontend (Node.js)
| Package | Version | Purpose |
|---------|---------|---------|
| react / react-dom | ^19.0.0 | Core UI framework |
| react-router-dom | 6 | Client-side routing |
| @reown/appkit + ethers | ^1.8.14 / ^6.13.4 | Web3 wallet connections |
| axios | ^1.8.4 | HTTP client |
| recharts | ^3.4.1 | Charts and data visualization |
| framer-motion | ^12.23.26 | Animations |
| @radix-ui/* (25 packages) | Various | Accessible UI primitives |
| tailwind-merge + clsx | Various | CSS class composition |
| lucide-react | ^0.507.0 | Icon library |
| zod + react-hook-form | ^3.24.4 / ^7.56.2 | Form validation |
| vite | ^6.0.7 | Build tool with HMR |

### Supported Chains (DEX)
- Ethereum (Chain ID: 1)
- Polygon (Chain ID: 137)
- Arbitrum (Chain ID: 42161)

### Rate Limits (External APIs)
| Service | Limit |
|---------|-------|
| CoinMarketCap | Per API plan |
| CoinGecko (Free) | 30 calls/minute |
| 1inch API | Per API plan |
| Backend API | SlowAPI rate limiting enabled |

## Project Statistics

| Category | Count |
|----------|-------|
| Backend Modules | 25 |
| Trading Intelligence Modules | 8 |
| Frontend Components | 24 |
| Frontend Services | 7 |
| Frontend Contexts | 3 |
| API Endpoints | 70+ |
| MongoDB Collections | 10 |
| Background Tasks | 6 |
| Backtesting Strategies | 4 |
| Technical Indicators | 10 |

