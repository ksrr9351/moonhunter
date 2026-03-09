# MoonHuntersFeeProxy Smart Contract

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Contract Details](#contract-details)
- [Functions Reference](#functions-reference)
- [Events](#events)
- [Security Features](#security-features)
- [Fee Math](#fee-math)
- [Current Deployment Status](#current-deployment-status)
- [Supported Chains](#supported-chains)
- [Whitelisted Tokens Per Chain](#whitelisted-tokens-per-chain)
- [Step-by-Step Deploy Guide](#step-by-step-deploy-guide)
- [Frontend Integration](#frontend-integration)
- [Gas Cost Estimates](#gas-cost-estimates)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)
- [npm Scripts](#npm-scripts)

---

## Overview

**MoonHuntersFeeProxy** is the core smart contract of the Moon Hunters platform. It acts as a middleman between users and the 1inch DEX aggregator, collecting a small platform fee (1-2%) on every buy and sell transaction while still giving users the best available swap price from 1inch.

**What it does:**
- User wants to buy a token (e.g., LINK) using USDT
- Instead of swapping directly on a DEX, the user sends USDT to this contract
- The contract takes a 2% fee and sends the remaining 98% through 1inch to get the best swap price
- The purchased tokens are sent back to the user
- The collected fees accumulate in the contract until the owner withdraws them to the treasury wallet

**Why it exists:**
- Generates revenue for the Moon Hunters platform
- Ensures transparent, on-chain fee collection (anyone can verify fees on the blockchain)
- Provides slippage protection — if the swap result is worse than expected, the transaction reverts
- Uses 1inch aggregation for optimal pricing across multiple DEX pools

---

## How It Works

### Architecture

```
                         MoonHuntersFeeProxy Contract
                        ┌─────────────────────────────┐
                        │                             │
  User ──── USDT ────►  │  1. Receive USDT            │
                        │  2. Deduct fee (2%)         │
                        │  3. Send 98% to 1inch       │ ──► 1inch Router ──► DEX Pools
                        │  4. Receive tokens from swap│                      (Uniswap,
  User ◄── Tokens ────  │  5. Send tokens to user     │                       SushiSwap,
                        │                             │                       Curve, etc.)
                        │  Fee stored in contract     │
                        │         │                   │
                        └─────────┼───────────────────┘
                                  │
                                  ▼
                          Treasury Wallet
                     (owner calls withdrawFees)
```

### Buy Flow (User buys a token with USDT)

1. User approves the contract to spend their USDT (standard ERC-20 approval)
2. User calls `buyToken()` with the token address, USDT amount, minimum expected tokens, and 1inch swap data
3. Contract pulls USDT from the user's wallet
4. Contract calculates and deducts the fee (e.g., 2% of 100 USDT = 2 USDT fee)
5. Contract sends the remaining USDT (98 USDT) to the 1inch router for swapping
6. Contract checks that the tokens received meet the minimum output (slippage protection)
7. Contract sends the received tokens to the user
8. `BuyExecuted` event is emitted on-chain

### Sell Flow (User sells a token for USDT)

1. User approves the contract to spend their tokens
2. User calls `sellToken()` with the token address, token amount, minimum expected USDT, and 1inch swap data
3. Contract pulls tokens from the user's wallet
4. Contract sends tokens to the 1inch router for swapping to USDT
5. Contract calculates and deducts the fee from the USDT received
6. Contract checks that the USDT after fee meets the minimum output (slippage protection)
7. Contract sends the remaining USDT to the user
8. `SellExecuted` event is emitted on-chain

---

## Contract Details

| Property | Value |
| :--- | :--- |
| **Contract Name** | MoonHuntersFeeProxy |
| **Solidity Version** | ^0.8.20 |
| **License** | MIT |
| **Source File** | `contracts/src/MoonHuntersFeeProxy.sol` |
| **Inherits From** | OpenZeppelin `Ownable`, `ReentrancyGuard` |
| **Uses** | OpenZeppelin `SafeERC20`, `IERC20` |
| **OpenZeppelin Version** | v5.1.0 |

### Constructor Parameters

The contract is initialized with these 4 values at deployment:

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `_treasury` | `address` | Wallet address that receives collected fees. Cannot be zero address. |
| `_usdtAddress` | `address` | USDT token contract address on the deployed chain. Stored as immutable (cannot change after deployment). |
| `_oneInchRouter` | `address` | 1inch Aggregation Router v6 address. Stored as immutable. |
| `_feePercent` | `uint256` | Fee in basis points (200 = 2%). Must be ≤ 500 (5% max). |

### State Variables

| Variable | Type | Mutability | Description |
| :--- | :--- | :--- | :--- |
| `treasury` | `address` | Set once in constructor | Wallet that receives withdrawn fees (no setter function — cannot be changed after deployment) |
| `usdt` | `address` | **Immutable** | USDT token address on this chain |
| `oneInchRouter` | `address` | **Immutable** | 1inch Aggregation Router address |
| `feePercent` | `uint256` | Mutable (by owner) | Current fee in basis points |
| `paused` | `bool` | Mutable (by owner) | Whether trading is paused |
| `_whitelistedTokens` | `mapping(address => bool)` | Mutable (by owner) | Which tokens are allowed for trading |
| `accumulatedFees` | `mapping(address => uint256)` | Auto-updated | Total fees collected (in practice, only USDT fees are accumulated since both buy and sell flows collect fees in USDT) |
| `MAX_FEE` | `uint256` | **Constant** | 500 (= 5% maximum fee cap) |
| `FEE_DENOMINATOR` | `uint256` | **Constant** | 10000 (basis points denominator) |

---

## Functions Reference

### User Functions (anyone can call)

#### `buyToken(token, usdtAmount, minOutput, swapData)`

Buy a token using USDT. The contract deducts a fee and routes the swap through 1inch.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `token` | `address` | The token to buy (must be whitelisted) |
| `usdtAmount` | `uint256` | Amount of USDT to spend (including fee) |
| `minOutput` | `uint256` | Minimum tokens to receive (slippage protection) |
| `swapData` | `bytes` | Encoded 1inch swap calldata (obtained from 1inch API) |

**Requirements:** Token must be whitelisted, contract not paused, amount > 0, user must have approved USDT spending.

**Modifiers:** `nonReentrant`, `whenNotPaused`, `onlyWhitelisted(token)`

---

#### `sellToken(token, tokenAmount, minUsdtOutput, swapData)`

Sell a token for USDT. The contract swaps via 1inch and deducts a fee from the USDT received.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `token` | `address` | The token to sell (must be whitelisted) |
| `tokenAmount` | `uint256` | Amount of tokens to sell |
| `minUsdtOutput` | `uint256` | Minimum USDT to receive after fee (slippage protection) |
| `swapData` | `bytes` | Encoded 1inch swap calldata |

**Requirements:** Token must be whitelisted, contract not paused, amount > 0, user must have approved token spending.

**Modifiers:** `nonReentrant`, `whenNotPaused`, `onlyWhitelisted(token)`

---

### Owner-Only Functions (admin)

These functions can only be called by the contract owner (the wallet that deployed the contract).

#### `setFeePercent(fee)`

Change the platform fee percentage.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `fee` | `uint256` | New fee in basis points (e.g., 200 = 2%). Must be ≤ 500 (5%). |

**Emits:** `FeeUpdated(oldFee, newFee)`

---

#### `withdrawFees()`

Withdraw all accumulated USDT fees to the treasury wallet. No parameters needed.

**Requirements:** There must be fees to withdraw (accumulated fees > 0).

---

#### `pause()`

Emergency pause — stops all buy/sell trading. No parameters needed.

**Emits:** `Paused(msg.sender)`

---

#### `unpause()`

Resume trading after a pause. No parameters needed.

**Emits:** `Unpaused(msg.sender)`

---

#### `recoverTokens(token, amount)`

Recover any ERC-20 tokens accidentally sent to the contract. Sends them to the treasury wallet.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `token` | `address` | Token contract address to recover |
| `amount` | `uint256` | Amount to recover. Must be > 0. |

---

#### `addWhitelistedToken(token)`

Add a token to the whitelist so users can buy/sell it through the contract.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `token` | `address` | Token contract address to whitelist. Cannot be zero address. |

---

#### `removeWhitelistedToken(token)`

Remove a token from the whitelist, preventing future buy/sell of that token.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `token` | `address` | Token contract address to remove |

---

### View Functions (read-only, no gas cost)

| Function | Returns | Description |
| :--- | :--- | :--- |
| `isWhitelisted(token)` | `bool` | Check if a token address is whitelisted for trading |
| `feePercent()` | `uint256` | Current fee in basis points (e.g., 200 = 2%) |
| `treasury()` | `address` | Current treasury wallet address |
| `paused()` | `bool` | Whether trading is currently paused |
| `accumulatedFees(token)` | `uint256` | Total unclaimed fees for a given token (in practice, only `usdt` address is used) |
| `usdt()` | `address` | USDT token address (immutable, set at deployment) |
| `oneInchRouter()` | `address` | 1inch Router address (immutable, set at deployment) |
| `owner()` | `address` | Contract owner address (inherited from Ownable) |
| `MAX_FEE()` | `uint256` | Maximum allowed fee: 500 (= 5%) |
| `FEE_DENOMINATOR()` | `uint256` | Basis points denominator: 10000 |

---

## Events

Events are emitted on-chain and can be listened to by the frontend or any blockchain indexer.

### BuyExecuted

Emitted when a user successfully buys a token.

| Parameter | Type | Indexed | Description |
| :--- | :--- | :--- | :--- |
| `user` | `address` | Yes | Buyer's wallet address |
| `token` | `address` | Yes | Token that was purchased |
| `amountIn` | `uint256` | No | Total USDT spent (including fee) |
| `amountOut` | `uint256` | No | Tokens received by the user |
| `fee` | `uint256` | No | Fee amount in USDT |

### SellExecuted

Emitted when a user successfully sells a token.

| Parameter | Type | Indexed | Description |
| :--- | :--- | :--- | :--- |
| `user` | `address` | Yes | Seller's wallet address |
| `token` | `address` | Yes | Token that was sold |
| `amountIn` | `uint256` | No | Tokens sold by the user |
| `amountOut` | `uint256` | No | USDT received by the user (after fee) |
| `fee` | `uint256` | No | Fee amount in USDT |

### FeeCollected

Emitted when a fee is deducted from a transaction.

| Parameter | Type | Indexed | Description |
| :--- | :--- | :--- | :--- |
| `token` | `address` | Yes | Token in which the fee was collected (always USDT) |
| `amount` | `uint256` | No | Fee amount |

### FeeUpdated

Emitted when the owner changes the fee percentage.

| Parameter | Type | Indexed | Description |
| :--- | :--- | :--- | :--- |
| `oldFee` | `uint256` | No | Previous fee in basis points |
| `newFee` | `uint256` | No | New fee in basis points |

### Paused / Unpaused

Emitted when trading is paused or resumed.

| Parameter | Type | Indexed | Description |
| :--- | :--- | :--- | :--- |
| `by` | `address` | Yes | Address of the owner who triggered the action |

---

## Security Features

| Feature | Protection Against | How It Works |
| :--- | :--- | :--- |
| **ReentrancyGuard** | Re-entrancy attacks | `buyToken` and `sellToken` use the `nonReentrant` modifier — prevents the contract from being called again before the first call finishes |
| **Ownable** | Unauthorized admin access | Only the contract owner can change fees, pause trading, whitelist tokens, withdraw fees, or recover tokens |
| **Slippage Protection** | Unfavorable swap execution | `minOutput` parameter on `buyToken` and `minUsdtOutput` on `sellToken` — if the swap returns less than the specified minimum, the entire transaction reverts. This limits losses from price movement but does not fully prevent MEV-based front-running. |
| **Max Fee Cap** | Fee abuse | Fee can never exceed 500 basis points (5%), enforced by `MAX_FEE` constant and checked in `setFeePercent` |
| **Token Whitelist** | Trading of malicious tokens | Only owner-approved tokens can be traded through the contract |
| **Emergency Pause** | Active exploits / market emergencies | Owner can instantly pause all buy/sell operations with `pause()` |
| **Token Recovery** | Accidentally sent tokens | Owner can recover any ERC-20 tokens stuck in the contract via `recoverTokens()` |
| **SafeERC20** | Non-standard token implementations | Uses OpenZeppelin's `SafeERC20` for all token transfers — handles tokens that don't return a boolean on transfer |

---

## Fee Math

The contract uses a **basis points** system for fee calculation:

- **1 basis point = 0.01%**
- **FEE_DENOMINATOR = 10,000** (represents 100%)
- **Current fee = 200 basis points = 2%**
- **MAX_FEE = 500 basis points = 5%** (hardcoded maximum, cannot be changed)

### Calculation Example

**Buy:** User sends 100 USDT to buy LINK
```
Fee = (100 USDT * 200) / 10000 = 2 USDT
Swap amount = 100 - 2 = 98 USDT sent to 1inch for swapping
User receives LINK worth 98 USDT (at market price)
Platform keeps 2 USDT as fee
```

**Sell:** User sells LINK and receives 100 USDT from 1inch swap
```
Fee = (100 USDT * 200) / 10000 = 2 USDT
User receives = 100 - 2 = 98 USDT
Platform keeps 2 USDT as fee
```

### Fee Range

| Fee (basis points) | Fee (%) | On $100 trade |
| :--- | :--- | :--- |
| 100 | 1% | $1.00 fee |
| 150 | 1.5% | $1.50 fee |
| **200** | **2%** | **$2.00 fee** (current) |
| 300 | 3% | $3.00 fee |
| 500 | 5% | $5.00 fee (maximum allowed) |

---

## Current Deployment Status

| Chain | Chain ID | Status | Contract Address | Fee | Treasury |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Sepolia Testnet** | 11155111 | **Deployed** | `0x36A816374554D1D53e77Db7EC1f50541d117172c` | 2% | `0x6426173D34f490641d4b70797dB57C3DB6cEF71d` |
| Ethereum Mainnet | 1 | Not deployed | — | — | — |
| Polygon | 137 | Not deployed | — | — | — |
| Arbitrum | 42161 | Not deployed | — | — | — |
| BSC | 56 | Not deployed | — | — | — |

**Sepolia Explorer:** [View Contract on Etherscan](https://sepolia.etherscan.io/address/0x36A816374554D1D53e77Db7EC1f50541d117172c)

---

## Supported Chains

The contract can be deployed to any of these chains. Each chain has its own USDT address and 1inch router.

| Chain | Chain ID | USDT Address | 1inch Router v6 | Default RPC |
| :--- | :--- | :--- | :--- | :--- |
| Ethereum | 1 | `0xdAC17F958D2ee523a2206206994597C13D831ec7` | `0x111111125421cA6dc452d289314280a0f8842A65` | `https://ethereum.publicnode.com` |
| Polygon | 137 | `0xc2132D05D31c914a87C6611C10748AEb04B58e8F` | `0x111111125421cA6dc452d289314280a0f8842A65` | `https://polygon-rpc.com` |
| Arbitrum | 42161 | `0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9` | `0x111111125421cA6dc452d289314280a0f8842A65` | `https://arb1.arbitrum.io/rpc` |
| BSC | 56 | `0x55d398326f99059fF775485246999027B3197955` | `0x111111125421cA6dc452d289314280a0f8842A65` | `https://bsc-dataseed.binance.org` |
| Sepolia (testnet) | 11155111 | `0x7169D38820dfd117C3FA1f22a697dBA58d90BA06` | `0x111111125421cA6dc452d289314280a0f8842A65` | `https://ethereum-sepolia-rpc.publicnode.com` |

> Note: The 1inch Aggregation Router v6 address is the same (`0x111111125421cA6dc452d289314280a0f8842A65`) across all supported chains.

---

## Whitelisted Tokens Per Chain

After deployment, the `setup.js` script whitelists these tokens for each chain:

### Ethereum (Chain ID: 1)

| Token | Address |
| :--- | :--- |
| WETH | `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` |
| WBTC | `0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599` |
| LINK | `0x514910771AF9Ca656af840dff83E8264EcF986CA` |
| UNI | `0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984` |
| AAVE | `0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9` |
| MKR | `0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2` |

### Polygon (Chain ID: 137)

| Token | Address |
| :--- | :--- |
| WMATIC | `0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270` |
| AAVE | `0xD6DF932A45C0f255f85145f286eA0b292B21C90B` |
| LINK | `0x53E0bca35eC356BD5ddDFebbD1Fc0fD03FaBad39` |

### Arbitrum (Chain ID: 42161)

| Token | Address |
| :--- | :--- |
| WETH | `0x82aF49447D8a07e3bd95BD0d56f35241523fBab1` |
| ARB | `0x912CE59144191C1204E64559FE8253a0e49E6548` |
| GMX | `0xfc5A1A6EB076a2C7aD06eD22C90d7E710E35ad0a` |

### BSC (Chain ID: 56)

| Token | Address |
| :--- | :--- |
| WBNB | `0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c` |
| CAKE | `0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82` |
| XVS | `0xcF6BB5389c92Bdda8a3747Ddb454cB7a64626C63` |

### Sepolia Testnet (Chain ID: 11155111)

| Token | Address |
| :--- | :--- |
| WETH | `0x7b79995e5f793A07Bc00c21412e50Ecae098E7f9` |
| USDT | `0x7169D38820dfd117C3FA1f22a697dBA58d90BA06` |
| LINK | `0x779877A7B0D9E8603169DdbD7836e478b4624789` |
| UNI | `0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984` |

> You can whitelist additional tokens at any time by calling `addWhitelistedToken(tokenAddress)` from the owner wallet, or by adding them to the `TOP_TOKENS` list in `scripts/setup.js` and re-running the setup script.

---

## Step-by-Step Deploy Guide

### Prerequisites

- Node.js 18+
- A wallet with native tokens for gas (ETH for Ethereum/Sepolia, MATIC for Polygon, etc.)
- The deployer wallet's private key
- (Optional) Block explorer API key for contract verification

### Step 1: Install Dependencies

```bash
cd contracts
npm install
```

### Step 2: Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your values:
- `DEPLOYER_PRIVATE_KEY` — Your wallet's private key (without the `0x` prefix)
- `TREASURY_ADDRESS` — Wallet address that will receive collected fees
- `FEE_PERCENT` — Fee in basis points (default: `200` = 2%)

### Step 3: Compile the Contract

```bash
npm run compile
```

This compiles `src/MoonHuntersFeeProxy.sol` using Solidity 0.8.20 with the optimizer enabled (200 runs). Artifacts are saved to `contracts/artifacts/`.

### Step 4: Deploy to Testnet First

Always test on Sepolia before deploying to mainnet:

```bash
npm run deploy:sepolia
```

The deploy script will output:
- The deployed contract address
- Constructor arguments used
- The exact `npx hardhat verify` command for block explorer verification
- Instructions to update the frontend config

### Step 5: Whitelist Tokens (Post-Deployment Setup)

After deployment, whitelist the tokens users can trade:

```bash
CONTRACT_ADDRESS=0xYourContractAddress npx hardhat run scripts/setup.js --network sepolia
```

The setup script reads the token list from `TOP_TOKENS` in `scripts/setup.js` and whitelists each one. It skips tokens that are already whitelisted.

### Step 6: Verify on Block Explorer (Optional but Recommended)

The deploy script prints the exact verification command. Example:

```bash
npx hardhat verify --network sepolia 0xContractAddress "0xTreasury" "0xUSDT" "0x1inchRouter" 200
```

### Step 7: Deploy to Mainnet

Once tested on Sepolia, deploy to your chosen mainnet:

```bash
npm run deploy:polygon     # Recommended — lowest gas costs
npm run deploy:ethereum    # Highest gas costs
npm run deploy:arbitrum    # Low gas costs (L2)
npm run deploy:bsc         # Low gas costs
```

Then run the setup script for the mainnet:

```bash
CONTRACT_ADDRESS=0x... npx hardhat run scripts/setup.js --network polygon
```

### Step 8: Update Frontend Configuration

After deployment, update `frontend/src/config/contractConfig.js`:

```javascript
export const CONTRACT_ADDRESSES = {
  1: "",                                                    // Ethereum (add address after deploying)
  56: "",                                                   // BSC
  137: "0xYourPolygonContractAddress",                      // Polygon (example)
  42161: "",                                                // Arbitrum
  11155111: "0x36A816374554D1D53e77Db7EC1f50541d117172c",   // Sepolia (already deployed)
};
```

---

## Frontend Integration

The smart contract connects to the Moon Hunters frontend through two key files:

### `frontend/src/config/contractConfig.js`

This file stores all contract configuration:
- `CONTRACT_ADDRESSES` — Maps chain ID to deployed contract address (empty string = not deployed)
- `TREASURY_ADDRESS` — Treasury wallet address
- `CHAIN_NAMES` — Maps chain ID to human-readable name
- `CHAIN_EXPLORERS` — Maps chain ID to block explorer URL
- `USDT_ADDRESSES` — Maps chain ID to USDT token address on that chain
- `FEE_PROXY_ABI` — ABI for the MoonHuntersFeeProxy contract (includes `buyToken`, `sellToken`, admin functions, key view functions like `feePercent`/`treasury`/`paused`/`isWhitelisted`, and all events. Does not include auto-generated getters for `usdt`, `oneInchRouter`, `accumulatedFees`, `MAX_FEE`, `FEE_DENOMINATOR`, or `owner` — these can be queried directly via ethers.js if needed.)
- `ERC20_ABI` — Minimal ABI for ERC-20 token interactions (approve, allowance, balanceOf, decimals)
- `FEE_PERCENT` — Current fee percentage (2)
- `MAX_FEE_PERCENT` — Maximum allowed fee (5)

### `frontend/src/services/contractService.js`

This file handles all smart contract interactions:

#### `isContractDeployed(chainId)`

Returns `true` if a valid contract address exists for the given chain ID. Used to decide the swap routing path.

#### Routing Logic

```
Is SC deployed on this chain?
├── YES → Route through Smart Contract (buyViaSC / sellViaSC)
│         - Uses the Fee Proxy contract
│         - Fee collected on-chain
│         - Events emitted for tracking
│
└── NO  → Route through 1inch directly (buyVia1inch / sellVia1inch)
          - Direct wallet-to-DEX swap
          - No on-chain fee collection
          - Fallback until SC is deployed on that chain
```

#### Buy Flow

- `buyToken(tokenAddress, usdtAmount, minOutputOrSlippage, chainId)` — Checks `isContractDeployed(chainId)`:
  - **If deployed:** Calls `buyViaSC()` — approves USDT to the contract, then calls the contract's `buyToken()` function
  - **If not deployed:** Calls `buyVia1inch()` — performs a direct swap through 1inch from the user's wallet

#### Sell Flow

- `sellToken(tokenAddress, tokenAmount, minUsdtOrSlippage, chainId)` — Same routing logic:
  - **If deployed:** Calls `sellViaSC()` — approves tokens to the contract, then calls `sellToken()`
  - **If not deployed:** Calls `sellVia1inch()` — direct 1inch swap

#### Event Listeners

- `listenForBuyEvents(chainId, callback)` — Listens for `BuyExecuted` events (only works when SC is deployed)
- `listenForSellEvents(chainId, callback)` — Listens for `SellExecuted` events (only works when SC is deployed)
- Returns `null` if SC is not deployed on the given chain

---

## Gas Cost Estimates

| Chain | Deployment Cost | Buy/Sell Transaction |
| :--- | :--- | :--- |
| Ethereum | $50 – $200 | $5 – $30 |
| Polygon | $0.01 – $0.10 | $0.001 – $0.01 |
| Arbitrum | $0.50 – $5 | $0.05 – $0.50 |
| BSC | $0.50 – $2 | $0.05 – $0.20 |
| Sepolia (testnet) | Free (testnet ETH) | Free (testnet ETH) |

> Recommendation: Start with **Polygon** or **BSC** for the lowest deployment and transaction costs. Deploy to Ethereum only if your user base primarily trades on Ethereum mainnet.

---

## Environment Variables

All environment variables are defined in `.env` (see `.env.example` for a template).

| Variable | Required | Description | Example |
| :--- | :--- | :--- | :--- |
| `DEPLOYER_PRIVATE_KEY` | Yes | Private key of the deployer wallet (without `0x` prefix). This wallet becomes the contract owner. | `abc123def456...` |
| `TREASURY_ADDRESS` | No | Wallet that receives collected fees. Defaults to deployer wallet if not set. | `0x6426...F71d` |
| `FEE_PERCENT` | No | Fee in basis points. Defaults to `200` (2%). | `200` |
| `RPC_URL_SEPOLIA` | No | Custom Sepolia RPC URL. Defaults to public RPC. | `https://rpc.sepolia.org` |
| `RPC_URL_ETH` | No | Custom Ethereum RPC URL. | `https://ethereum.publicnode.com` |
| `RPC_URL_POLYGON` | No | Custom Polygon RPC URL. | `https://polygon-rpc.com` |
| `RPC_URL_ARBITRUM` | No | Custom Arbitrum RPC URL. | `https://arb1.arbitrum.io/rpc` |
| `RPC_URL_BSC` | No | Custom BSC RPC URL. | `https://bsc-dataseed.binance.org` |
| `ETHERSCAN_API_KEY` | No | API key for Etherscan contract verification. | `ABCDEF123456` |
| `POLYGONSCAN_API_KEY` | No | API key for Polygonscan verification. | `ABCDEF123456` |
| `ARBISCAN_API_KEY` | No | API key for Arbiscan verification. | `ABCDEF123456` |
| `BSCSCAN_API_KEY` | No | API key for BSCscan verification. | `ABCDEF123456` |
| `CONTRACT_ADDRESS` | For setup | Address of the deployed contract (used by `setup.js` only). | `0x36A8...172c` |

---

## Project Structure

```
contracts/
├── src/
│   └── MoonHuntersFeeProxy.sol    # Main smart contract source code
├── scripts/
│   ├── deploy.js                  # Deployment script (handles all chains)
│   └── setup.js                   # Post-deployment setup (token whitelisting)
├── artifacts/                     # Compiled contract artifacts (auto-generated)
├── cache/                         # Hardhat compilation cache (auto-generated)
├── hardhat.config.js              # Hardhat configuration (networks, compiler, etherscan)
├── package.json                   # Dependencies and npm scripts
├── .env.example                   # Environment variable template
└── README.md                      # This file
```

### Related Frontend Files

```
frontend/src/
├── config/
│   └── contractConfig.js          # Contract addresses, ABI, chain configs
└── services/
    └── contractService.js         # SC interaction logic (buy/sell routing, events)
```

---

## npm Scripts

| Script | Command | Description |
| :--- | :--- | :--- |
| `npm run compile` | `npx hardhat compile` | Compile the Solidity contract |
| `npm run deploy:sepolia` | `npx hardhat run scripts/deploy.js --network sepolia` | Deploy to Sepolia testnet |
| `npm run deploy:ethereum` | `npx hardhat run scripts/deploy.js --network ethereum` | Deploy to Ethereum mainnet |
| `npm run deploy:polygon` | `npx hardhat run scripts/deploy.js --network polygon` | Deploy to Polygon mainnet |
| `npm run deploy:arbitrum` | `npx hardhat run scripts/deploy.js --network arbitrum` | Deploy to Arbitrum mainnet |
| `npm run deploy:bsc` | `npx hardhat run scripts/deploy.js --network bsc` | Deploy to BSC mainnet |
| `npm run setup` | `npx hardhat run scripts/setup.js` | Run post-deployment token whitelisting |
| `npm test` | `npx hardhat test` | Run contract tests |
