// Reown AppKit Configuration for Moon Hunters
import { createAppKit } from '@reown/appkit'
import { EthersAdapter } from '@reown/appkit-adapter-ethers'
import { mainnet, sepolia, polygon, arbitrum, base, bsc, optimism, avalanche, gnosis } from '@reown/appkit/networks'

// Reown credentials from environment - NO FALLBACK (must be set in environment)
const REOWN_PROJECT_ID = import.meta.env.VITE_REOWN_PROJECT_ID
if (!REOWN_PROJECT_ID) {
  console.error('VITE_REOWN_PROJECT_ID environment variable is required')
}

// Get app URL - must match whitelisted domain in Reown dashboard exactly
const getAppUrl = () => {
  if (typeof window !== 'undefined') {
    return window.location.origin
  }
  return ''
}

// Supported networks — expanded to match backend chain registry
const networks = [mainnet, base, polygon, arbitrum, bsc, optimism, avalanche, gnosis, sepolia]

// Create Ethers adapter
const ethersAdapter = new EthersAdapter()

// Reown AppKit Configuration - Optimized for production
// Note: Some features (email, socials, swaps, onramp) are managed via Reown dashboard
export const modal = createAppKit({
  adapters: [ethersAdapter],
  networks,
  projectId: REOWN_PROJECT_ID,
  
  metadata: {
    name: 'Moon Hunters',
    description: 'AI-Powered Crypto Investment Platform',
    url: getAppUrl(),
    icons: [`${getAppUrl()}/favicon.ico`]
  },
  
  // Featured wallets - show these prominently
  featuredWalletIds: [
    'c57ca95b47569778a828d19178114f4db188b89b763c899ba0be274e97267d96', // MetaMask
    'fd20dc426fb37566d803205b19bbc1d4096b248ac04548e3cfb6b3a38bd033aa', // Coinbase
    '4622a2b2d6af1c9844944291e5e7351a6aa24cd7b23099efac1b2fd875da31a0', // Trust Wallet
  ],
  
  // Show all wallets including QR code option
  allWallets: 'SHOW',
  
  // Disable built-in auth features - we handle auth via direct connect
  features: {
    analytics: false,
    onramp: false,
    swaps: false,
    email: false,
    socials: false,
  },
  
  // Disable built-in email/social wallet options (we only use external wallets)
  enableWalletConnect: true,
  
  // Theme
  themeMode: 'dark',
  themeVariables: {
    '--w3m-accent': '#00FFD1',
    '--w3m-border-radius-master': '12px',
    '--w3m-z-index': '9999',
    '--w3m-font-family': "'Inter', sans-serif"
  },
})

// Export configuration
export const REOWN_CONFIG = {
  PROJECT_ID: REOWN_PROJECT_ID,
  APP_URL: getAppUrl()
}

export { ethersAdapter }
