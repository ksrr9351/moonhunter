/**
 * Real-time Event Service using Server-Sent Events (SSE)
 * Subscribes to backend event stream for instant updates
 * Uses fetch-based streaming for authenticated connections
 */

const API_URL = import.meta.env.VITE_BACKEND_URL || '';

class EventService {
  constructor() {
    this.abortController = null;
    this.listeners = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 3000;
    this.connected = false;
    this.token = null;
    this.reconnectTimer = null;
  }

  connect(token) {
    if (this.abortController) {
      this.disconnect();
    }

    this.token = token;
    if (!token) {
      console.warn('[EventService] No token provided, cannot connect');
      return;
    }

    this.startEventStream(token);
  }

  startEventStream(token) {
    const url = `${API_URL}/api/events/stream`;
    
    this.abortController = new AbortController();

    const fetchEvents = async () => {
      try {
        const response = await fetch(url, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache'
          },
          signal: this.abortController.signal
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        this.connected = true;
        this.reconnectAttempts = 0;
        console.log('[EventService] Connected to event stream');
        this.emit('connection', { status: 'connected' });

        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            console.log('[EventService] Stream ended');
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const chunks = buffer.split('\n\n');
          buffer = chunks.pop() || '';

          for (const chunk of chunks) {
            if (chunk.trim()) {
              this.parseSSEChunk(chunk);
            }
          }
        }

        this.connected = false;
        this.emit('connection', { status: 'disconnected' });
        this.handleReconnect();

      } catch (error) {
        if (error.name === 'AbortError') {
          console.log('[EventService] Connection aborted');
          return;
        }
        
        console.error('[EventService] Stream error:', error);
        this.connected = false;
        this.emit('connection', { status: 'error', error: error.message });
        this.handleReconnect();
      }
    };

    fetchEvents();
  }

  parseSSEChunk(chunk) {
    const lines = chunk.split('\n');
    let eventType = 'message';
    let data = null;

    for (const line of lines) {
      if (line.startsWith('event:')) {
        eventType = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        const dataStr = line.slice(5).trim();
        try {
          data = JSON.parse(dataStr);
        } catch (e) {
          data = dataStr;
        }
      }
    }

    if (data !== null) {
      this.handleEvent(eventType, data);
    }
  }

  handleEvent(eventType, data) {
    console.log(`[EventService] Received ${eventType}:`, data);
    this.emit(eventType, data);

    switch (eventType) {
      case 'SWAP_EXECUTED':
      case 'AI_TRADE_EXECUTED':
      case 'AUTO_INVEST_EXECUTED':
      case 'BALANCE_UPDATED':
        this.emit('balanceChange', data);
        break;
      case 'TX_FAILED':
        this.emit('transactionFailed', data);
        break;
      case 'heartbeat':
      case 'connected':
        break;
      default:
        break;
    }
  }

  handleReconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[EventService] Max reconnect attempts reached');
      this.emit('connection', { status: 'failed' });
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`[EventService] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    this.reconnectTimer = setTimeout(() => {
      const freshToken = localStorage.getItem('auth_token');
      if (freshToken) {
        this.token = freshToken;
        this.startEventStream(freshToken);
      } else if (this.token) {
        this.startEventStream(this.token);
      }
    }, delay);
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
    
    this.connected = false;
    this.reconnectAttempts = 0;
    this.token = null;
    console.log('[EventService] Disconnected');
  }

  updateToken(newToken) {
    if (newToken && newToken !== this.token) {
      this.token = newToken;
      if (this.connected || this.reconnectTimer) {
        this.disconnect();
        this.connect(newToken);
      }
    }
  }

  on(eventType, callback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType).add(callback);
    
    return () => this.off(eventType, callback);
  }

  off(eventType, callback) {
    if (this.listeners.has(eventType)) {
      this.listeners.get(eventType).delete(callback);
    }
  }

  emit(eventType, data) {
    if (this.listeners.has(eventType)) {
      this.listeners.get(eventType).forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`[EventService] Error in ${eventType} handler:`, error);
        }
      });
    }
  }

  isConnected() {
    return this.connected;
  }
}

export const eventService = new EventService();
export default eventService;
