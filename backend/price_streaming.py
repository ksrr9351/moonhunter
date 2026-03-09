"""
Price Streaming Service - Real-time price updates via WebSocket
Broadcasts cryptocurrency price updates to all connected clients
"""
import logging
import asyncio
from typing import Set, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class PriceStreamingService:
    """
    Manages WebSocket connections and broadcasts real-time price updates
    """
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.last_prices: Dict[str, Any] = {}
        self.is_streaming = False
        self._stream_task: Optional[asyncio.Task] = None
        logger.info("Price Streaming Service initialized")
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")
        
        if self.last_prices:
            try:
                await websocket.send_json({
                    "type": "initial_prices",
                    "data": self.last_prices,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                logger.error(f"Failed to send initial prices: {e}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Remaining: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Send a message to all connected clients"""
        if not self.active_connections:
            return
        
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to client: {e}")
                disconnected.add(connection)
        
        for conn in disconnected:
            self.active_connections.discard(conn)
    
    async def broadcast_prices(self, prices: Dict[str, Any]):
        """Broadcast price updates to all clients"""
        self.last_prices = prices
        await self.broadcast({
            "type": "price_update",
            "data": prices,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def broadcast_fast_mover(self, coin: Dict[str, Any]):
        """Broadcast a fast mover alert"""
        await self.broadcast({
            "type": "fast_mover",
            "data": coin,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def broadcast_dump_opportunity(self, opportunity: Dict[str, Any]):
        """Broadcast a dump opportunity alert"""
        await self.broadcast({
            "type": "dump_opportunity",
            "data": opportunity,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def broadcast_position_update(self, position: Dict[str, Any]):
        """Broadcast a position update (for portfolio tracking)"""
        await self.broadcast({
            "type": "position_update",
            "data": position,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def broadcast_bot_trade(self, trade: Dict[str, Any]):
        """Broadcast when trading bot executes a trade"""
        await self.broadcast({
            "type": "bot_trade",
            "data": trade,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def broadcast_trigger_executed(self, trigger: Dict[str, Any]):
        """Broadcast when a stop-loss or take-profit triggers"""
        await self.broadcast({
            "type": "trigger_executed",
            "data": trigger,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    def get_connection_count(self) -> int:
        """Get the number of active WebSocket connections"""
        return len(self.active_connections)


price_streaming_service = PriceStreamingService()


async def run_price_streaming_task(market_provider, interval_seconds: int = 30):
    """
    Background task that fetches prices and broadcasts to WebSocket clients
    """
    logger.info(f"Starting price streaming task (interval: {interval_seconds}s)")
    price_streaming_service.is_streaming = True
    
    while price_streaming_service.is_streaming:
        try:
            if price_streaming_service.active_connections:
                coins = await market_provider.get_coins_list(limit=50)
                
                if coins:
                    price_data = {}
                    for coin in coins:
                        symbol = coin.get("symbol", "")
                        price_data[symbol] = {
                            "symbol": symbol,
                            "name": coin.get("name", ""),
                            "price": coin.get("price", 0),
                            "percent_change_1h": coin.get("change1h", 0),
                            "percent_change_24h": coin.get("change24h", 0),
                            "market_cap": coin.get("marketCap", 0),
                            "volume_24h": coin.get("volume24h", 0),
                            "logo": coin.get("logo", "")
                        }
                    
                    await price_streaming_service.broadcast_prices(price_data)
                    logger.debug(f"Broadcasted prices for {len(price_data)} coins to {len(price_streaming_service.active_connections)} clients")
            
        except Exception as e:
            logger.error(f"Price streaming error: {e}")
        
        await asyncio.sleep(interval_seconds)
    
    logger.info("Price streaming task stopped")


def stop_price_streaming():
    """Stop the price streaming background task"""
    price_streaming_service.is_streaming = False
