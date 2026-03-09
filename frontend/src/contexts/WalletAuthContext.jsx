import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { modal, REOWN_CONFIG } from '../config/reown';
import { useAppKitAccount, useAppKitProvider, useAppKitNetwork } from '@reown/appkit/react';
import { BrowserProvider } from 'ethers';
import { getChains, getChainById } from '../services/chainService';

const API_URL = import.meta.env.VITE_BACKEND_URL || '';

// Populated dynamically from /api/dex/chains on mount
const DEFAULT_SUPPORTED_CHAINS = {};

// ==================== WALLET AUTH CONTEXT ====================
const WalletAuthContext = createContext();

export const useWalletAuth = () => {
  const context = useContext(WalletAuthContext);
  if (!context) {
    throw new Error('useWalletAuth must be used within WalletAuthProvider');
  }
  return context;
};

export const WalletAuthProvider = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();

  // ==================== REOWN APPKIT HOOKS ====================
  const { address, isConnected, status } = useAppKitAccount();
  const { walletProvider } = useAppKitProvider('eip155');
  const { chainId: reownChainId } = useAppKitNetwork();

  // ==================== GLOBAL AUTH STATE ====================
  // FIX: Initialize from localStorage synchronously to prevent flash
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    const hasAuth = !!localStorage.getItem('auth_token') && !!localStorage.getItem('wallet_address');
    console.log('[INIT] Auth state initialized from localStorage:', hasAuth);
    return hasAuth;
  });
  const [walletConnected, setWalletConnected] = useState(() => !!localStorage.getItem('wallet_address'));
  const [walletAddress, setWalletAddress] = useState(() => localStorage.getItem('wallet_address') || '');
  const [token, setToken] = useState(() => localStorage.getItem('auth_token') || '');
  const [userId, setUserId] = useState(() => localStorage.getItem('user_id') || '');
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [currentChainId, setCurrentChainId] = useState(null);
  const [signerReady, setSignerReady] = useState(false);
  const [SUPPORTED_CHAINS, setSupportedChains] = useState(DEFAULT_SUPPORTED_CHAINS);
  
  // Load dynamic chain list from backend
  useEffect(() => {
    getChains().then(chains => {
      if (chains && chains.length > 0) {
        const map = {};
        chains.forEach(c => { map[c.id] = c.name; });
        setSupportedChains(map);
      }
    }).catch(() => {}); // fallback to defaults
  }, []);
  
  
  // Cached provider and signer refs
  const providerRef = useRef(null);
  const signerRef = useRef(null);
  const lastProviderRef = useRef(null);
  
  // Use refs for all flags to prevent stale closures
  const loginInProgress = useRef(false);
  const hasRedirected = useRef(false);
  const lastProcessedAddress = useRef(null);
  const connectionDebounceTimer = useRef(null);

  // ==================== VALIDATE AUTH ON MOUNT ====================
  // FIX: Validate the pre-loaded auth state with backend
  useEffect(() => {
    const validateAuth = async () => {
      console.log('[AUTH] Validating existing auth...');
      
      const savedToken = localStorage.getItem('auth_token');
      const savedWalletAddress = localStorage.getItem('wallet_address');
      const savedUserId = localStorage.getItem('user_id');

      console.log('[AUTH] LocalStorage check:', { 
        hasToken: !!savedToken, 
        hasAddress: !!savedWalletAddress,
        address: savedWalletAddress?.slice(0, 10) + '...'
      });

      if (savedToken && savedWalletAddress) {
        try {
          // Validate token with backend
          const response = await axios.get(`${API_URL}/api/auth/wallet/me`, {
            headers: { Authorization: `Bearer ${savedToken}` },
            timeout: 10000 // 10 second timeout
          });
          
          if (response.data && response.data.wallet_address) {
            console.log('[AUTH] Token validated successfully!');
            // Token is valid, ensure state is correct
            setIsAuthenticated(true);
            setWalletConnected(true);
            setWalletAddress(savedWalletAddress);
            setToken(savedToken);
            setUserId(savedUserId || response.data.id);
            setUser(response.data);
            console.log('[AUTH] Auth state restored from validated token');
          } else {
            throw new Error('Invalid response from server');
          }
        } catch (error) {
          console.log('[AUTH] Token validation failed:', error.message);
          // Token is invalid/expired - clear everything
          clearAuthState();
          console.log('[AUTH] Session expired. User will need to reconnect wallet.');
        }
      } else {
        // No saved auth, ensure clean state
        setIsAuthenticated(false);
        setWalletConnected(false);
      }
      
      setIsLoading(false);
    };

    validateAuth();
  }, []);

  // ==================== CLEAR AUTH STATE HELPER ====================
  const clearAuthState = () => {
    console.log('[AUTH] Clearing auth state...');
    localStorage.removeItem('auth_token');
    localStorage.removeItem('wallet_address');
    localStorage.removeItem('user_id');
    setIsAuthenticated(false);
    setWalletConnected(false);
    setWalletAddress('');
    setToken('');
    setUserId('');
    setUser(null);
  };

  // ==================== FORCE CLOSE REOWN MODAL ====================
  const forceCloseModal = useCallback(() => {
    try {
      modal.close();
    } catch (e) {
      // Ignore - modal might already be closed
    }
  }, []);

  // ==================== WATCH REOWN MODAL EVENTS ====================
  useEffect(() => {
    if (!modal || typeof modal.subscribeEvents !== 'function') return;
    
    const unsubscribe = modal.subscribeEvents((event) => {
      console.log('[REOWN EVENT]', event?.data?.event, event?.data?.properties);
      
      const eventName = event?.data?.event;
      
      if (eventName === 'CONNECT_SUCCESS') {
        console.log('[REOWN EVENT] Connection successful! Closing modal...');
        setTimeout(() => forceCloseModal(), 200);
      }
      
      if (eventName === 'CONNECT_ERROR' || eventName === 'MODAL_CLOSE') {
        const errorMsg = event?.data?.properties?.message?.toLowerCase() || '';
        if (errorMsg.includes('rejected') || errorMsg.includes('auth')) {
          console.log('[REOWN EVENT] Auth error caught:', errorMsg);
          // Check if actually connected despite the error (Trust Wallet quirk)
          setTimeout(() => {
            if (isConnected && address && !loginInProgress.current && !isAuthenticated) {
              console.log('[REOWN EVENT] Connected despite auth error! Starting direct auth...');
              lastProcessedAddress.current = address;
              handleDirectConnect(address);
            }
          }, 1000);
        }
      }
    });
    
    return () => {
      if (typeof unsubscribe === 'function') unsubscribe();
    };
  }, [isConnected, address, isAuthenticated, forceCloseModal]);

  // ==================== WATCH REOWN CONNECTION CHANGES ====================
  useEffect(() => {
    console.log('[REOWN] State changed:', { 
      address: address?.slice(0, 10) + '...', 
      isConnected, 
      status,
      isAuthenticated,
      loginInProgress: loginInProgress.current
    });
    
    // Don't process if already authenticated
    if (isAuthenticated) {
      console.log('[REOWN] Already authenticated, ignoring state change');
      forceCloseModal();
      return;
    }
    
    // Don't process if login is already in progress
    if (loginInProgress.current) {
      console.log('[REOWN] Login already in progress, ignoring state change');
      return;
    }
    
    // Don't process the same address twice
    if (address && address.toLowerCase() === lastProcessedAddress.current?.toLowerCase()) {
      console.log('[REOWN] Address already processed, ignoring');
      return;
    }
    
    // Process new connection - DIRECT CONNECT (no signature required for maximum compatibility)
    if (isConnected && address) {
      console.log('[REOWN] New connection detected:', address.slice(0, 10) + '...');
      
      // Close modal after a brief delay to let WalletConnect session stabilize
      setTimeout(() => forceCloseModal(), 300);
      
      // Clear any existing debounce timer
      if (connectionDebounceTimer.current) {
        clearTimeout(connectionDebounceTimer.current);
      }
      
      // Wait longer for mobile wallets (WalletConnect needs time to fully establish session)
      connectionDebounceTimer.current = setTimeout(() => {
        if (!loginInProgress.current && !isAuthenticated) {
          lastProcessedAddress.current = address;
          
          forceCloseModal();
          
          console.log('[DIRECT] Starting direct wallet authentication for:', address.slice(0, 10) + '...');
          handleDirectConnect(address);
        }
      }, 500);
    }
    
    return () => {
      if (connectionDebounceTimer.current) {
        clearTimeout(connectionDebounceTimer.current);
      }
    };
  }, [isConnected, address, status, isAuthenticated, forceCloseModal]);

  // ==================== AUTO-AUTHENTICATE ON WALLET RECONNECTION ====================
  // When wallet is connected after page reload, authenticate directly
  useEffect(() => {
    const autoAuthenticate = async () => {
      // Only run if connected but not authenticated
      if (!isConnected || !address || isAuthenticated || loginInProgress.current) {
        return;
      }
      
      // Check if we already have a valid token for this address
      const storedAddress = localStorage.getItem('wallet_address');
      const storedToken = localStorage.getItem('auth_token');
      
      if (storedAddress && storedToken && storedAddress.toLowerCase() === address.toLowerCase()) {
        console.log('[AUTO] Found existing auth for this wallet, validating...');
        try {
          // Validate the token
          const response = await axios.get(`${API_URL}/api/auth/wallet/me`, {
            headers: { Authorization: `Bearer ${storedToken}` },
            timeout: 5000
          });
          
          if (response.data.user) {
            console.log('[AUTO] Token is still valid, restoring session...');
            setIsAuthenticated(true);
            setWalletConnected(true);
            setWalletAddress(address.toLowerCase());
            setToken(storedToken);
            setUser(response.data.user);
            lastProcessedAddress.current = address;
            
            // Redirect to dashboard
            redirectToDashboard();
            return;
          }
        } catch (e) {
          console.log('[AUTO] Stored token is invalid, will re-authenticate');
          localStorage.removeItem('auth_token');
        }
      }
      
      // Clear any pending SIWE state (we use direct connect now)
      localStorage.removeItem('pending_siwe');
      
      // If wallet is connected but no valid token, authenticate with direct connect
      console.log('[AUTO] Wallet connected after reload, starting direct authentication...');
      handleDirectConnect(address);
    };
    
    // Delay slightly to allow wallet state to stabilize
    const timer = setTimeout(autoAuthenticate, 300);
    return () => clearTimeout(timer);
  }, [isConnected, address, isAuthenticated, forceCloseModal]);

  // ==================== REDIRECT TO DASHBOARD ====================
  const redirectToDashboard = useCallback(() => {
    if (hasRedirected.current) {
      console.log('[REDIRECT] Already redirected, skipping...');
      return;
    }
    
    hasRedirected.current = true;
    console.log('[REDIRECT] Redirecting to dashboard...');
    
    // FIX: Close modal multiple times to ensure it's closed
    forceCloseModal();
    setTimeout(forceCloseModal, 100);
    setTimeout(forceCloseModal, 300);
    
    // Use navigate for SPA routing
    try {
      navigate('/dashboard', { replace: true });
      console.log('[REDIRECT] Navigation to dashboard initiated');
    } catch (e) {
      console.log('[REDIRECT] Navigate failed, using window.location');
      window.location.href = '/dashboard';
    }
  }, [navigate, forceCloseModal]);

  // ==================== HANDLE DIRECT CONNECT (NO SIGNATURE) ====================
  // Simple wallet authentication - works with all wallets including mobile
  const handleDirectConnect = async (walletAddr) => {
    if (loginInProgress.current) {
      console.log('[DIRECT] Login already in progress, skipping...');
      return false;
    }
    
    if (isAuthenticated) {
      console.log('[DIRECT] Already authenticated, skipping...');
      return false;
    }
    
    loginInProgress.current = true;
    
    // Close the Reown modal immediately
    console.log('[DIRECT] Closing Reown modal...');
    forceCloseModal();
    
    try {
      console.log('[DIRECT] Authenticating wallet:', walletAddr.slice(0, 10) + '...');

      // Call direct connect endpoint (no signature required)
      const response = await axios.post(`${API_URL}/api/auth/wallet/connect`, {
        address: walletAddr
      }, { timeout: 10000 });

      if (response.data.success && response.data.access_token) {
        const userData = response.data.user;
        const accessToken = response.data.access_token;

        console.log('[DIRECT] Authentication successful!');

        // Clear any pending SIWE state
        localStorage.removeItem('pending_siwe');
        
        // Save to localStorage
        localStorage.setItem('auth_token', accessToken);
        localStorage.setItem('wallet_address', walletAddr.toLowerCase());
        localStorage.setItem('user_id', userData.id);
        console.log('[DIRECT] Auth data saved to localStorage');

        // Update global auth state
        setIsAuthenticated(true);
        setWalletConnected(true);
        setWalletAddress(walletAddr.toLowerCase());
        setToken(accessToken);
        setUserId(userData.id);
        setUser(userData);
        loginInProgress.current = false;

        console.log('[DIRECT] User authenticated:', userData.username);
        
        // Redirect to dashboard immediately
        redirectToDashboard();
        return true;
      } else {
        throw new Error('Authentication failed');
      }
    } catch (error) {
      console.error('[DIRECT] Authentication failed:', error.message);
      loginInProgress.current = false;
      lastProcessedAddress.current = null;
      
      if (error.code === 'ERR_NETWORK' || error.code === 'ECONNABORTED') {
        alert('Network error. Please check your connection and try again.');
      } else {
        alert('Authentication failed. Please try connecting again.');
      }
      return false;
    }
  };

  // ==================== HANDLE SIWE (SIGN-IN WITH ETHEREUM) AUTHENTICATION ====================
  // Secure authentication with cryptographic signature verification (fallback)
  const handleSIWEAuth = async (walletAddr) => {
    if (loginInProgress.current) {
      console.log('[SIWE] Login already in progress, skipping...');
      return false;
    }
    
    if (isAuthenticated) {
      console.log('[SIWE] Already authenticated, skipping...');
      return false;
    }
    
    loginInProgress.current = true;
    
    // Close the Reown modal immediately and wait for it to fully close
    console.log('[SIWE] Closing Reown modal before signing...');
    forceCloseModal();
    await new Promise(resolve => setTimeout(resolve, 500)); // Wait for modal to close
    forceCloseModal(); // Double-close to ensure it's gone
    
    try {
      console.log('[SIWE] Starting Sign-In With Ethereum for:', walletAddr.slice(0, 10) + '...');

      // Step 1: Request nonce from backend
      console.log('[SIWE] Step 1: Requesting nonce from server...');
      const nonceResponse = await axios.post(`${API_URL}/api/auth/wallet/nonce`, {
        address: walletAddr
      }, { timeout: 10000 });

      const nonce = nonceResponse.data.nonce;
      if (!nonce) {
        throw new Error('Failed to get nonce from server');
      }
      console.log('[SIWE] Nonce received:', nonce.slice(0, 20) + '...');

      // Step 2: Create proper EIP-4361 SIWE message
      const domain = window.location.host;
      const origin = window.location.origin;
      const issuedAt = new Date().toISOString();
      const chainId = currentChainId || 1; // Default to Ethereum mainnet
      
      // EIP-4361 SIWE message format
      const siweMessage = `${domain} wants you to sign in with your Ethereum account:
${walletAddr}

Sign in to Moon Hunters - AI-Powered Crypto Investment Platform

URI: ${origin}
Version: 1
Chain ID: ${chainId}
Nonce: ${nonce}
Issued At: ${issuedAt}`;
      
      console.log('[SIWE] Step 2: EIP-4361 SIWE message created');
      
      // Store pending SIWE state in case of page reload (mobile wallet redirect)
      localStorage.setItem('pending_siwe', JSON.stringify({
        address: walletAddr,
        nonce: nonce,
        message: siweMessage,
        domain: domain,
        chainId: chainId,
        issuedAt: issuedAt,
        timestamp: Date.now()
      }));
      console.log('[SIWE] Pending SIWE state saved to localStorage');

      // Step 3: Wait for signer to be ready and sign the message
      console.log('[SIWE] Step 3: Requesting signature from wallet...');
      
      // Ensure modal is closed before signing
      forceCloseModal();
      
      // Get signer - wait for provider to be ready (longer wait for mobile)
      let signer = null;
      let attempts = 0;
      const maxAttempts = 15; // Increased attempts for mobile wallets
      
      while (!signer && attempts < maxAttempts) {
        try {
          if (walletProvider) {
            console.log(`[SIWE] Getting signer (attempt ${attempts + 1}/${maxAttempts})...`);
            const provider = new BrowserProvider(walletProvider);
            signer = await provider.getSigner();
            const signerAddress = await signer.getAddress(); // Verify signer is working
            console.log(`[SIWE] Got signer for address: ${signerAddress.slice(0, 10)}...`);
          } else {
            console.log(`[SIWE] Wallet provider not ready yet (attempt ${attempts + 1}/${maxAttempts})...`);
          }
        } catch (e) {
          console.log(`[SIWE] Waiting for signer (attempt ${attempts + 1}/${maxAttempts}): ${e.message}`);
          await new Promise(resolve => setTimeout(resolve, 800)); // Longer wait between attempts
        }
        attempts++;
      }
      
      if (!signer) {
        throw new Error('Could not get wallet signer. Please close the wallet modal and try connecting again.');
      }
      
      // Ensure modal is closed right before signing request
      forceCloseModal();

      // Sign the message
      let signature;
      try {
        console.log('[SIWE] Sending sign request to wallet...');
        console.log('[SIWE] User should see signing prompt in wallet app');
        
        // The signMessage call will trigger the wallet to show a signing popup
        signature = await signer.signMessage(siweMessage);
        console.log('[SIWE] Signature obtained:', signature.slice(0, 20) + '...');
      } catch (signError) {
        console.error('[SIWE] Signing error:', signError);
        if (signError.code === 4001 || signError.code === 'ACTION_REJECTED' || 
            signError.message?.includes('rejected') || signError.message?.includes('denied') ||
            signError.message?.includes('user rejected')) {
          console.log('[SIWE] User rejected signature request');
          throw new Error('Signature request was rejected. Please sign the message to authenticate.');
        }
        // Check for mobile-specific errors
        if (signError.message?.includes('pending') || signError.message?.includes('already pending')) {
          throw new Error('A signing request is already pending. Please check your wallet app.');
        }
        throw signError;
      }

      // Step 4: Verify signature with backend (send full SIWE message for verification)
      console.log('[SIWE] Step 4: Verifying signature with server...');
      const verifyResponse = await axios.post(`${API_URL}/api/auth/wallet/verify`, {
        address: walletAddr,
        signature: signature,
        nonce: nonce,
        message: siweMessage,
        domain: domain,
        chainId: chainId,
        issuedAt: issuedAt
      }, { timeout: 15000 });

      if (verifyResponse.data.success && verifyResponse.data.access_token) {
        const userData = verifyResponse.data.user;
        const accessToken = verifyResponse.data.access_token;

        console.log('[SIWE] Signature verified! Authentication successful!');

        // Clear pending SIWE state
        localStorage.removeItem('pending_siwe');
        
        // Save to localStorage
        localStorage.setItem('auth_token', accessToken);
        localStorage.setItem('wallet_address', walletAddr.toLowerCase());
        localStorage.setItem('user_id', userData.id);
        console.log('[SIWE] Auth data saved to localStorage');

        // Update global auth state
        setIsAuthenticated(true);
        setWalletConnected(true);
        setWalletAddress(walletAddr.toLowerCase());
        setToken(accessToken);
        setUserId(userData.id);
        setUser(userData);

        console.log('[SIWE] Authentication complete! Redirecting to dashboard...');
        
        // Redirect to dashboard
        setTimeout(() => {
          redirectToDashboard();
        }, 100);

        return true;
      } else {
        throw new Error('Signature verification failed');
      }
    } catch (error) {
      console.error('[SIWE] Authentication failed:', error.message);
      loginInProgress.current = false;
      lastProcessedAddress.current = null;
      
      // Clear pending SIWE state on error
      localStorage.removeItem('pending_siwe');
      
      if (error.message?.includes('rejected') || error.message?.includes('denied')) {
        alert('Please sign the message in your wallet to authenticate.');
      } else if (error.response?.status === 401) {
        alert('Signature verification failed. Please try again.');
      } else if (error.response?.status === 500) {
        alert('Server error. Please try again in a few moments.');
      } else if (error.code === 'ERR_NETWORK' || error.code === 'ECONNABORTED') {
        alert('Network error. Please check your connection and try again.');
      } else {
        alert(error.message || 'Authentication failed. Please try again.');
      }
      return false;
    }
  };

  // ==================== SET AUTH STATE ====================
  const setAuthState = (state) => {
    if (state.isAuthenticated !== undefined) setIsAuthenticated(state.isAuthenticated);
    if (state.walletConnected !== undefined) setWalletConnected(state.walletConnected);
    if (state.walletAddress !== undefined) setWalletAddress(state.walletAddress);
    if (state.token !== undefined) setToken(state.token);
    if (state.userId !== undefined) setUserId(state.userId);
    if (state.user !== undefined) setUser(state.user);
  };

  // ==================== CLEAR AUTH ====================
  const clearAuth = () => {
    console.log('[AUTH] clearAuth called');
    setIsAuthenticated(false);
    setWalletConnected(false);
    setWalletAddress('');
    setToken('');
    setUserId('');
    setUser(null);
    
    // Reset all flags
    loginInProgress.current = false;
    hasRedirected.current = false;
    lastProcessedAddress.current = null;
    
    localStorage.removeItem('auth_token');
    localStorage.removeItem('wallet_address');
    localStorage.removeItem('user_id');
  };

  // ==================== CONNECT WALLET ====================
  const connectWallet = async () => {
    try {
      console.log('[WALLET] Opening Reown modal...');
      console.log('[WALLET] Modal instance:', modal ? 'exists' : 'undefined');
      console.log('[WALLET] Project ID:', REOWN_CONFIG?.PROJECT_ID ? 'configured' : 'missing');
      
      // Reset all flags for new login attempt
      loginInProgress.current = false;
      hasRedirected.current = false;
      lastProcessedAddress.current = null;
      
      // Try to open the modal
      if (modal && typeof modal.open === 'function') {
        await modal.open({ view: 'Connect' });
        console.log('[WALLET] Modal.open() called successfully');
      } else {
        console.error('[WALLET] Modal is not properly initialized');
        alert('Wallet connection is not available. Please refresh the page.');
      }
    } catch (error) {
      console.error('[WALLET] Error opening modal:', error);
      
      const errorMsg = error?.message?.toLowerCase() || '';
      if (errorMsg.includes('rejected') || errorMsg.includes('denied') || errorMsg.includes('user rejected') || errorMsg.includes('auth request')) {
        console.log('[WALLET] User closed modal or auth was rejected by provider — checking if wallet connected anyway...');
        // Trust Wallet sometimes throws "auth rejected" even though connection succeeded
        // Wait briefly and check if we actually got connected
        await new Promise(resolve => setTimeout(resolve, 1500));
        if (isConnected && address && !loginInProgress.current && !isAuthenticated) {
          console.log('[WALLET] Wallet IS connected despite error! Proceeding with direct auth...');
          lastProcessedAddress.current = address;
          handleDirectConnect(address);
          return;
        }
        console.log('[WALLET] Wallet not connected. User may have rejected or closed the modal.');
      } else {
        alert('Failed to open wallet connection. Please refresh and try again.');
      }
    }
  };

  // ==================== LOGOUT ====================
  const handleLogout = async () => {
    console.log('[LOGOUT] Starting logout...');
    
    try {
      // Call backend logout
      await axios.post(`${API_URL}/api/auth/wallet/logout`, {}, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 5000
      });
    } catch (error) {
      console.log('[LOGOUT] Logout API error (non-critical):', error.message);
    }

    // Disconnect Reown
    try {
      await modal.disconnect();
    } catch (e) {
      console.log('[LOGOUT] Reown already disconnected');
    }

    // Clear auth state
    clearAuth();
    
    console.log('[LOGOUT] Logout complete, redirecting to home');
    navigate('/');
  };

  // ==================== SYNC CHAIN ID FROM REOWN ====================
  useEffect(() => {
    if (reownChainId && isConnected) {
      const numericChainId = typeof reownChainId === 'number' ? reownChainId : Number(reownChainId);
      if (numericChainId && numericChainId !== currentChainId) {
        console.log('[CHAIN] Network changed via Reown hook:', numericChainId, '(was:', currentChainId, ')');
        setCurrentChainId(numericChainId);
      }
    }
  }, [reownChainId, isConnected]);

  // ==================== LISTEN FOR CHAIN CHANGES ON WALLET PROVIDER ====================
  useEffect(() => {
    if (!walletProvider || !isConnected) return;

    const handleChainChanged = (chainIdHex) => {
      const numericChainId = typeof chainIdHex === 'string' ? parseInt(chainIdHex, 16) : Number(chainIdHex);
      console.log('[CHAIN] chainChanged event from wallet provider:', numericChainId);
      setCurrentChainId(numericChainId);
      providerRef.current = null;
      signerRef.current = null;
      lastProviderRef.current = null;
      setSignerReady(false);
    };

    if (walletProvider.on) {
      walletProvider.on('chainChanged', handleChainChanged);
    }

    return () => {
      if (walletProvider.removeListener) {
        walletProvider.removeListener('chainChanged', handleChainChanged);
      }
    };
  }, [walletProvider, isConnected]);

  // ==================== INITIALIZE SIGNER WHEN PROVIDER CHANGES ====================
  useEffect(() => {
    const initializeSigner = async () => {
      if (!walletProvider || !isConnected || !address) {
        if (!isConnected) {
          setSignerReady(false);
        }
        return;
      }
      
      if (lastProviderRef.current === walletProvider && signerRef.current) {
        return;
      }
      
      try {
        console.log('[SIGNER] Bridging Reown → ethers v6...');
        
        const provider = new BrowserProvider(walletProvider);
        const signer = await provider.getSigner();
        const signerAddress = await signer.getAddress();
        
        console.log('[SIGNER] Signer obtained for:', signerAddress.slice(0, 10) + '...');
        
        const network = await provider.getNetwork();
        const chainId = Number(network.chainId);
        
        providerRef.current = provider;
        signerRef.current = signer;
        lastProviderRef.current = walletProvider;
        setCurrentChainId(chainId);
        setSignerReady(true);
        
        console.log('[SIGNER] Bridge complete, chain:', chainId);
      } catch (error) {
        console.error('[SIGNER] Bridge failed:', error.message);
        if (!error.message?.includes('connect()')) {
          setSignerReady(false);
          providerRef.current = null;
          signerRef.current = null;
        }
      }
    };
    
    const timer = setTimeout(initializeSigner, 100);
    return () => clearTimeout(timer);
  }, [walletProvider, isConnected, address]);

  // ==================== ENSURE WALLET CONNECTION ====================
  const ensureWalletConnection = useCallback(async (requiredChainId = null) => {
    if (!walletProvider || !isConnected) {
      throw new Error('Please connect your wallet first');
    }
    
    try {
      if (signerRef.current && providerRef.current && lastProviderRef.current === walletProvider) {
        try {
          const signerAddress = await signerRef.current.getAddress();
          const network = await providerRef.current.getNetwork();
          const chainId = Number(network.chainId);
          setCurrentChainId(chainId);
          
          if (requiredChainId && chainId !== requiredChainId) {
            const chainName = SUPPORTED_CHAINS[requiredChainId] || `Chain ${requiredChainId}`;
            throw new Error(`Please switch to ${chainName} in your wallet`);
          }
          
          console.log('[WALLET] Reusing cached signer for:', signerAddress.slice(0, 10) + '...');
          return { provider: providerRef.current, signer: signerRef.current, chainId };
        } catch (error) {
          if (error.message?.includes('switch to')) {
            throw error;
          }
          console.log('[WALLET] Cached signer stale, reinitializing...');
        }
      }
      
      const provider = new BrowserProvider(walletProvider);
      const signer = await provider.getSigner();
      const signerAddress = await signer.getAddress();
      
      console.log('[WALLET] Signer obtained for:', signerAddress.slice(0, 10) + '...');
      
      const network = await provider.getNetwork();
      const chainId = Number(network.chainId);
      
      if (requiredChainId && chainId !== requiredChainId) {
        const chainName = SUPPORTED_CHAINS[requiredChainId] || `Chain ${requiredChainId}`;
        throw new Error(`Please switch to ${chainName} in your wallet`);
      }
      
      providerRef.current = provider;
      signerRef.current = signer;
      lastProviderRef.current = walletProvider;
      setCurrentChainId(chainId);
      setSignerReady(true);
      
      return { provider, signer, chainId };
    } catch (error) {
      console.error('[WALLET] Connection failed:', error.message);
      throw error;
    }
  }, [walletProvider, isConnected]);

  // ==================== GET SIGNER ====================
  const getSigner = useCallback(async () => {
    if (signerRef.current && lastProviderRef.current === walletProvider) {
      try {
        await signerRef.current.getAddress();
        return signerRef.current;
      } catch (e) {
        console.log('[WALLET] Cached signer invalid, getting new one...');
      }
    }
    
    const { signer } = await ensureWalletConnection();
    return signer;
  }, [ensureWalletConnection, walletProvider]);

  // ==================== SWITCH NETWORK ====================
  const switchNetwork = useCallback(async (targetChainId) => {
    if (!walletProvider) {
      throw new Error('Please connect your wallet first');
    }
    
    const chainHex = `0x${targetChainId.toString(16)}`;
    const chainName = SUPPORTED_CHAINS[targetChainId] || `Chain ${targetChainId}`;
    
    try {
      await walletProvider.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: chainHex }],
      });
      
      console.log(`[NETWORK] Switched to ${chainName}`);
      providerRef.current = null;
      signerRef.current = null;
      setSignerReady(false);
      setCurrentChainId(targetChainId);
      return true;
    } catch (switchError) {
      if (switchError.code === 4902) {
        // Chain not added to wallet - build config dynamically from registry
        const chainData = getChainById(targetChainId);
        if (chainData && chainData.rpc_urls?.length > 0) {
          const addChainConfig = {
            chainId: chainHex,
            chainName: chainData.name,
            nativeCurrency: { name: chainData.symbol, symbol: chainData.symbol, decimals: 18 },
            rpcUrls: chainData.rpc_urls,
            blockExplorerUrls: chainData.explorer ? [chainData.explorer] : [],
          };
          try {
            await walletProvider.request({
              method: 'wallet_addEthereumChain',
              params: [addChainConfig],
            });
            providerRef.current = null;
            signerRef.current = null;
            setSignerReady(false);
            setCurrentChainId(targetChainId);
            return true;
          } catch (addError) {
            throw new Error(`Failed to add ${chainName}`);
          }
        }
      }
      throw new Error(`Failed to switch to ${chainName}`);
    }
  }, [walletProvider]);

  // ==================== SEND TRANSACTION ====================
  const sendTransaction = useCallback(async (tx, requiredChainId = null) => {
    if (!walletProvider) {
      throw new Error('Please connect your wallet first');
    }
    
    try {
      let { signer, chainId } = await ensureWalletConnection();
      
      if (requiredChainId && chainId !== requiredChainId) {
        console.log(`[TX] Switching from chain ${chainId} to ${requiredChainId}...`);
        await switchNetwork(requiredChainId);
        const result = await ensureWalletConnection();
        if (result.chainId !== requiredChainId) {
          throw new Error(`Please switch to ${SUPPORTED_CHAINS[requiredChainId] || `chain ${requiredChainId}`}`);
        }
        signer = result.signer;
        chainId = result.chainId;
      }
      
      const txParams = {
        to: tx.to,
        data: tx.data,
        value: tx.value || '0x0',
      };
      
      if (tx.gas) {
        txParams.gasLimit = tx.gas;
      }
      
      console.log('[TX] Sending transaction...');
      const txResponse = await signer.sendTransaction(txParams);
      console.log('[TX] Transaction sent:', txResponse.hash);
      
      return txResponse.hash;
    } catch (error) {
      console.error('[TX] Transaction failed:', error.message);
      
      if (error.code === 4001 || error.message?.includes('rejected') || error.message?.includes('denied')) {
        throw new Error('Transaction rejected by user');
      } else if (error.message?.includes('insufficient funds')) {
        throw new Error('Insufficient funds for this transaction');
      } else if (error.message?.includes('connect')) {
        throw new Error('Please connect your wallet first');
      } else if (error.message?.includes('switch to')) {
        throw error;
      } else if (error.message?.includes('could not coalesce') || error.message?.includes('CALL_EXCEPTION')) {
        throw new Error('Transaction failed. The swap route may have changed or the price moved beyond your slippage tolerance.');
      } else if (/code.*-32000/i.test(error.message) || /code.*-32603/i.test(error.message)) {
        throw new Error('The network rejected this transaction. Try increasing slippage or reducing the amount.');
      } else if (error.message?.includes('execution reverted')) {
        throw new Error('Transaction would fail on-chain. Please refresh the quote and try again.');
      }
      
      const cleanMsg = error.message || 'Transaction failed. Please try again.';
      throw new Error(cleanMsg.length > 150 ? 'Transaction failed. Please try again with different settings.' : cleanMsg);
    }
  }, [walletProvider, ensureWalletConnection, switchNetwork]);

  // ==================== CONTEXT VALUE ====================
  const value = {
    // State
    isAuthenticated,
    walletConnected,
    walletAddress,
    token,
    userId,
    user,
    isLoading,
    currentChainId,
    walletProvider,
    signerReady,
    SUPPORTED_CHAINS,

    // Functions
    setAuthenticated: (val) => setIsAuthenticated(val),
    setWalletConnected: (val) => setWalletConnected(val),
    setWalletAddress: (val) => setWalletAddress(val),
    setToken: (val) => setToken(val),
    setUserId: (val) => setUserId(val),
    setAuthState,
    connectWallet,
    logout: handleLogout,
    sendTransaction,
    switchNetwork,
    ensureWalletConnection,
    getSigner,
  };

  return (
    <WalletAuthContext.Provider value={value}>
      {children}
    </WalletAuthContext.Provider>
  );
};

export default WalletAuthContext;
