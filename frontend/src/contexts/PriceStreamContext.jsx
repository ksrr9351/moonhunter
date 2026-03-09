import React, { createContext, useContext, useState, useEffect, useCallback, useRef, useMemo } from 'react';

const WS_RECONNECT_DELAY = 3000;
const WS_PING_INTERVAL = 30000;
const MESSAGE_THROTTLE_MS = 100; // Throttle rapid WebSocket messages

const PriceStreamContext = createContext(null);

export function PriceStreamProvider({ children, enabled = true }) {
  const [prices, setPrices] = useState({});
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [fastMovers, setFastMovers] = useState([]);
  const [dumpOpportunities, setDumpOpportunities] = useState([]);
  const [botTrades, setBotTrades] = useState([]);
  
  const wsRef = useRef(null);
  const pingIntervalRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const enabledRef = useRef(enabled);
  const lastMessageTimeRef = useRef(0);
  const pendingPricesRef = useRef(null);
  const throttleTimeoutRef = useRef(null);

  useEffect(() => {
    enabledRef.current = enabled;
  }, [enabled]);

  const connect = useCallback(() => {
    if (!enabledRef.current) return;
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    // WebSocket requires auth token — skip connection if not logged in
    const token = localStorage.getItem('auth_token');
    if (!token) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const backendUrl = import.meta.env.VITE_BACKEND_URL || '';

    let wsUrl;
    if (backendUrl) {
      const url = new URL(backendUrl);
      wsUrl = `${protocol}//${url.host}/ws/prices?token=${token}`;
    } else {
      wsUrl = `${protocol}//${window.location.host}/ws/prices?token=${token}`;
    }

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected (shared)');
        setIsConnected(true);
        
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, WS_PING_INTERVAL);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          const now = Date.now();
          
          // Throttle price updates to prevent excessive re-renders
          if (message.type === 'price_update' || message.type === 'initial_prices') {
            pendingPricesRef.current = { data: message.data, timestamp: message.timestamp };
            
            if (now - lastMessageTimeRef.current >= MESSAGE_THROTTLE_MS) {
              // Immediate update if throttle window has passed
              setPrices(pendingPricesRef.current.data);
              setLastUpdate(new Date(pendingPricesRef.current.timestamp));
              lastMessageTimeRef.current = now;
              
              // Clear any pending trailing update
              if (throttleTimeoutRef.current) {
                clearTimeout(throttleTimeoutRef.current);
                throttleTimeoutRef.current = null;
              }
            } else {
              // Schedule trailing update to ensure latest data is always delivered
              if (!throttleTimeoutRef.current) {
                throttleTimeoutRef.current = setTimeout(() => {
                  if (pendingPricesRef.current) {
                    setPrices(pendingPricesRef.current.data);
                    setLastUpdate(new Date(pendingPricesRef.current.timestamp));
                    lastMessageTimeRef.current = Date.now();
                  }
                  throttleTimeoutRef.current = null;
                }, MESSAGE_THROTTLE_MS);
              }
            }
          } else {
            setLastUpdate(new Date(message.timestamp));
            switch (message.type) {
              case 'fast_mover':
                setFastMovers(prev => [message.data, ...prev.slice(0, 9)]);
                break;
              case 'dump_opportunity':
                setDumpOpportunities(prev => [message.data, ...prev.slice(0, 9)]);
                break;
              case 'bot_trade':
                setBotTrades(prev => [message.data, ...prev.slice(0, 9)]);
                break;
              default:
                break;
            }
          }
        } catch (e) {
          if (event.data !== 'pong') {
            console.error('Failed to parse WebSocket message:', e);
          }
        }
      };

      ws.onclose = (event) => {
        console.log('WebSocket disconnected', event.code);
        setIsConnected(false);

        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
        }

        // code 4001 = auth rejected — no point reconnecting without a valid token
        const authRejected = event.code === 4001;
        if (enabledRef.current && !authRejected) {
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('Attempting to reconnect...');
            connect();
          }, WS_RECONNECT_DELAY);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (e) {
      console.error('Failed to create WebSocket:', e);
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
    }
    if (throttleTimeoutRef.current) {
      clearTimeout(throttleTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  const getPrice = useCallback((symbol) => {
    return prices[symbol] || null;
  }, [prices]);

  const clearFastMovers = useCallback(() => {
    setFastMovers([]);
  }, []);

  const clearDumpOpportunities = useCallback(() => {
    setDumpOpportunities([]);
  }, []);

  // Memoize context value to prevent unnecessary re-renders
  const value = useMemo(() => ({
    prices,
    isConnected,
    lastUpdate,
    fastMovers,
    dumpOpportunities,
    botTrades,
    getPrice,
    clearFastMovers,
    clearDumpOpportunities,
    reconnect: connect
  }), [prices, isConnected, lastUpdate, fastMovers, dumpOpportunities, botTrades, getPrice, clearFastMovers, clearDumpOpportunities, connect]);

  return (
    <PriceStreamContext.Provider value={value}>
      {children}
    </PriceStreamContext.Provider>
  );
}

export function usePriceStream() {
  const context = useContext(PriceStreamContext);
  if (!context) {
    return {
      prices: {},
      isConnected: false,
      lastUpdate: null,
      fastMovers: [],
      dumpOpportunities: [],
      botTrades: [],
      getPrice: () => null,
      clearFastMovers: () => {},
      clearDumpOpportunities: () => {},
      reconnect: () => {}
    };
  }
  return context;
}

export default PriceStreamContext;
