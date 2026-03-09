/**
 * Event Context - Provides real-time event subscription throughout the app
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { eventService } from '../services/eventService';
import { useWalletAuth } from './WalletAuthContext';

const EventContext = createContext(null);

export const useEvents = () => {
  const context = useContext(EventContext);
  if (!context) {
    throw new Error('useEvents must be used within an EventProvider');
  }
  return context;
};

export const EventProvider = ({ children }) => {
  const { token, walletConnected } = useWalletAuth();
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState(null);
  const [balanceUpdateTrigger, setBalanceUpdateTrigger] = useState(0);

  useEffect(() => {
    if (token && walletConnected) {
      eventService.connect(token);
    } else {
      eventService.disconnect();
    }

    return () => {
      eventService.disconnect();
    };
  }, [token, walletConnected]);

  useEffect(() => {
    const unsubConnection = eventService.on('connection', (data) => {
      setConnected(data.status === 'connected');
    });

    const unsubSwap = eventService.on('SWAP_EXECUTED', (data) => {
      console.log('[EventContext] Swap executed, triggering balance refresh');
      setLastEvent({ type: 'SWAP_EXECUTED', data, timestamp: Date.now() });
      setBalanceUpdateTrigger(prev => prev + 1);
    });

    const unsubAiTrade = eventService.on('AI_TRADE_EXECUTED', (data) => {
      console.log('[EventContext] AI trade executed, triggering balance refresh');
      setLastEvent({ type: 'AI_TRADE_EXECUTED', data, timestamp: Date.now() });
      setBalanceUpdateTrigger(prev => prev + 1);
    });

    const unsubAutoInvest = eventService.on('AUTO_INVEST_EXECUTED', (data) => {
      console.log('[EventContext] Auto-invest executed, triggering balance refresh');
      setLastEvent({ type: 'AUTO_INVEST_EXECUTED', data, timestamp: Date.now() });
      setBalanceUpdateTrigger(prev => prev + 1);
    });

    const unsubTxFailed = eventService.on('TX_FAILED', (data) => {
      console.log('[EventContext] Transaction failed:', data);
      setLastEvent({ type: 'TX_FAILED', data, timestamp: Date.now() });
    });

    const unsubBalanceChange = eventService.on('balanceChange', () => {
      setBalanceUpdateTrigger(prev => prev + 1);
    });

    return () => {
      unsubConnection();
      unsubSwap();
      unsubAiTrade();
      unsubAutoInvest();
      unsubTxFailed();
      unsubBalanceChange();
    };
  }, []);

  const subscribe = useCallback((eventType, callback) => {
    return eventService.on(eventType, callback);
  }, []);

  const triggerBalanceRefresh = useCallback(() => {
    setBalanceUpdateTrigger(prev => prev + 1);
  }, []);

  const value = {
    connected,
    lastEvent,
    balanceUpdateTrigger,
    subscribe,
    triggerBalanceRefresh,
    isConnected: () => eventService.isConnected()
  };

  return (
    <EventContext.Provider value={value}>
      {children}
    </EventContext.Provider>
  );
};

export default EventProvider;
