# Moon Hunters - AI-Powered Crypto Investment Platform

## Overview
Moon Hunters is an AI-driven cryptocurrency investment platform designed to provide users with real-time market insights, automated trading capabilities, and portfolio management. Its core purpose is to empower crypto investors with intelligent tools for informed decision-making and efficient strategy execution, featuring wallet-based authentication, a dynamic dashboard, AI-powered recommendations, and automated trading bots.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### High-Level Overview
Moon Hunters employs a decoupled client-server architecture. The frontend is a React 19 single-page application, and the backend is a FastAPI Python server. MongoDB serves as the primary database. Real-time data is handled via WebSockets for price streaming and Server-Sent Events for notifications. Blockchain interactions are managed client-side using ethers.js and Reown AppKit, with swap routing through the 1inch DEX Aggregator API.

### Frontend Architecture
The frontend is built with React 19 and Vite 6, utilizing Tailwind CSS 3 and shadcn/ui for styling. The Inter font (loaded via Google Fonts) is used globally as the primary typeface, including in the Reown AppKit Connect Wallet modal via the `--w3m-font-family` theme variable. State management uses React hooks and the Context API. Authentication is handled by Reown AppKit and ethers.js v6 for Web3 wallet connections. Data visualization is powered by Recharts and TradingView lightweight-charts, with animations by Framer Motion. Key features include lazy-loaded components, a 3D animated landing page, and dedicated pages for Dashboard, AI Engine, Invest, Auto-Invest, Wallet, Leaderboard, Backtest, and Top Gainers, all designed with responsive navigation and accessibility.

### Backend Architecture
The backend is a FastAPI 0.110 server running with Uvicorn, organized into modular router files. It uses MongoDB via Motor for asynchronous data access. Authentication is JWT-based with eth-account signature verification. Rate limiting is implemented with SlowAPI. AI functionalities leverage a custom Perplexity client, and server-side Ethereum interactions are managed with web3.py. The backend includes core engines for market data, DEX integration, dump detection, analysis, recommendation, portfolio management, trading bots, backtesting, and social trading. A production-grade AI system provides market analysis, anomaly detection, pump/dump detection, and signal generation.

### Real-time Features
The platform provides live price updates via WebSocket, real-time event streams via Server-Sent Events, and browser-based push notifications for price movements and trading events, including AI-driven dump alerts.

### Authentication Flow
Users connect their wallet, request a nonce from the backend, sign it, and the backend verifies the signature to issue a JWT token for authenticated API access. In production, only SIWE signature-based authentication is allowed.

### DEX Swap Flow
Users select swap details, the frontend requests a quote from the backend (1inch API), manages token allowances, and initiates the swap transaction for user signature.

### Invest Section
The Invest section acts as a "Dump Opportunities" marketplace where AI-detected dumped coins are presented with limited buying windows. Users can buy/sell via a Fee Proxy Smart Contract architecture that routes through 1inch DEX for best prices, or directly via 1inch swaps if the SC is not deployed. Dump detection is unified, utilizing a dual-engine approach to identify opportunities across multiple chains.

### Smart Contract
The `MoonHuntersFeeProxy.sol` Solidity 0.8.20 contract is a Fee Proxy Smart Contract designed to collect a small fee on buy/sell transactions and route swaps through the 1inch Aggregation Router v6. It incorporates security features like ReentrancyGuard, slippage protection, max fee cap, token whitelisting, and emergency recovery. The contract is configured for multi-chain deployment (Ethereum, Polygon, Arbitrum, BSC) with a Sepolia testnet deployment verified on Etherscan. The frontend dynamically adjusts its swap mechanism based on contract deployment status on the selected chain.

## External Dependencies

### APIs and Services
- **CoinMarketCap API**: Live cryptocurrency market data.
- **CoinGecko API**: Historical OHLC data.
- **Perplexity AI API**: AI-driven investment recommendations and analysis.
- **1inch DEX API v6.0**: Real-time swap quotes and transaction generation.
- **Multi-Chain Public RPCs**: For ETH and ERC-20 wallet balance lookups across Ethereum, Base, Polygon, and Arbitrum (multi-provider with failover per chain).
- **SMTP (Gmail)**: For email-based alerts.
- **Web Push (VAPID)**: For browser push notifications.

### Database
- **MongoDB**: Primary data store for user data, positions, bots, alerts, and analytics. Includes centralized index management with TTL indexes for ephemeral data (dump opportunities, nonces, crypto prices).

### Blockchain Infrastructure
- **Reown AppKit**: Manages Web3 wallet connections (frontend). No `defaultNetwork` set — AppKit uses first network in array. Networks: `[mainnet, base, polygon, arbitrum, sepolia]`. The `useAppKitNetwork` hook provides reactive chain ID.
- **ethers.js v6**: Frontend Ethereum interactions.
- **eth-account / eth-utils**: Backend signature verification.
- **web3.py**: Server-side Ethereum interactions.

### Multi-Chain Wallet Balance Detection
- Backend `wallet_service.py` has multi-chain auto-detection: if balance is 0 on the requested chain, it scans ALL supported chains (Ethereum, Base, Polygon, Arbitrum) in parallel and returns the one with the highest balance.
- Frontend `WalletPage.jsx` uses `detectedChainId` from backend response to display correct chain name, explorer links, and USDC/USDT labels.
- `WalletAuthContext.jsx` syncs chain ID from Reown's `useAppKitNetwork` hook and listens for `chainChanged` events on the wallet provider.
- Known limitation: Reown AppKit may report chain 1 (Ethereum) even when the wallet is on Base, because WalletConnect v2 session defaults to the AppKit's selected network. The backend fallback handles this gracefully.

## Detection Thresholds (Current)

### Fast Movers Detector (`backend/fast_movers_detector.py`)
- **PUMP_THRESHOLD**: +1.5% (1h change)
- **DUMP_THRESHOLD**: -0.5% (1h change)
- **Coin Coverage**: Top 100 by market cap (from CoinMarketCap)
- **Cycle Interval**: 60 seconds
- **Dedup**: 15-minute per-coin cooldown to prevent alert flooding
- **Creates dump opportunities** in MongoDB with 1-hour TTL

### Dump Detection Engine (`backend/dump_detection_engine.py`)
- **DUMP_THRESHOLD**: -3.0% (1h or 24h)
- **PUMP_THRESHOLD**: +5.0%
- **Health Filters**: Volume >= $1M, Market Cap >= $10M, Rank <= 100, 7-day trend check
- **Serves as live fallback** when stored opportunities < 5

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
- Frontend falls back to direct 1inch swaps on those chains

## Frontend Auth Requirements
All pages except the landing page require wallet authentication (ProtectedRoute wrapper).

### Services with Auth Headers
- `investService.js` — sends `Bearer ${token}` on all calls
- `backtestingService.js` — sends `Bearer ${token}` on all calls (fixed: was missing auth)
- `AIEnginePage.jsx` — sends `Bearer ${token}` on all API calls including signals and dump-opportunities (fixed: signals/dump-opportunities were missing auth)

### Public API Endpoints (no auth required)
- `GET /api/crypto/latest` — top coins list
- `GET /api/crypto/market-overview` — topGainers, topLosers, trending, globalStats
- `GET /api/crypto/fast-movers` — pump/dump movement cards (used by FastMarketMovements component)
- `GET /api/crypto/market-health` — market health scores

## Deployment Configuration
- **Target**: `vm` (always-on) — required for WebSockets, SSE, and 6 background tasks
- **Build**: `cd frontend && npm install && npm run build` (outputs to `frontend/build/`)
- **Run**: `cd backend && python -m uvicorn server:app --host 0.0.0.0 --port 5000`
- **Health check**: `/health` returns JSON with status `healthy`/`starting`/`degraded`; uses 2s timeout on DB ping to avoid blocking
- **MongoDB `serverSelectionTimeoutMS`**: 5000ms (reduced from 10000ms for faster startup)
- **Database index creation**: Runs as background task with 15s timeout to avoid blocking server startup
- **Deferred startup**: All background task initialization (market data, trading bot, price streaming, AI dump alerts, trading intelligence) runs in a deferred `asyncio.create_task` so the `@app.on_event("startup")` handler returns instantly, allowing FastAPI to accept requests and pass health checks immediately
- **Lazy-loaded modules**: `trading_intelligence` and `wallet_auth` are lazy-imported (deferred from module-level to startup/request time) to keep server import time under 5s for deployment health checks
- **Intelligence router**: Uses `core_deps.ti_service` via `_get_ti_service()` helper (returns 503 if service still initializing)

## Timestamp Handling (Important)
- All backend datetime serialization uses `.isoformat() + "Z"` to ensure UTC timestamps
- Frontend parses timestamps with UTC awareness (appends "Z" if missing)
- Invest page `activeOpportunities` filter uses server-computed `remaining_seconds` as primary check (avoids timezone issues)
- Dump opportunity dedup: existing active opportunities log skip reason in fast_movers_detector