"""
Server-Sent Events (SSE) service for real-time updates.
Provides event streaming to authenticated frontend clients.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    WALLET_CONNECTED = "WALLET_CONNECTED"
    WALLET_DISCONNECTED = "WALLET_DISCONNECTED"
    CHAIN_CHANGED = "CHAIN_CHANGED"
    SWAP_EXECUTED = "SWAP_EXECUTED"
    AI_TRADE_EXECUTED = "AI_TRADE_EXECUTED"
    AUTO_INVEST_EXECUTED = "AUTO_INVEST_EXECUTED"
    TX_FAILED = "TX_FAILED"
    BALANCE_UPDATED = "BALANCE_UPDATED"
    HEARTBEAT = "HEARTBEAT"


@dataclass
class Event:
    event_type: EventType
    user_id: str
    payload: Dict[str, Any]
    timestamp: str = None
    event_id: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if self.event_id is None:
            self.event_id = str(uuid.uuid4())
    
    def to_sse_format(self) -> str:
        data = {
            "event_type": self.event_type.value if isinstance(self.event_type, EventType) else self.event_type,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "payload": self.payload
        }
        return f"event: {self.event_type.value if isinstance(self.event_type, EventType) else self.event_type}\ndata: {json.dumps(data)}\n\n"


class EventService:
    """
    Centralized event service for SSE broadcasting.
    Maintains per-user event queues and handles subscription/unsubscription.
    """
    
    def __init__(self):
        self._user_queues: Dict[str, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()
        self._event_log: list = []
        self._max_log_size = 1000
    
    async def subscribe(self, user_id: str) -> asyncio.Queue:
        """Subscribe a user to receive events. Returns a queue for receiving events."""
        async with self._lock:
            if user_id not in self._user_queues:
                self._user_queues[user_id] = set()
            
            queue = asyncio.Queue(maxsize=100)
            self._user_queues[user_id].add(queue)
            logger.info(f"User {user_id[:8]}... subscribed to events. Total queues: {len(self._user_queues[user_id])}")
            return queue
    
    async def unsubscribe(self, user_id: str, queue: asyncio.Queue):
        """Unsubscribe a user's queue from events."""
        async with self._lock:
            if user_id in self._user_queues:
                self._user_queues[user_id].discard(queue)
                if not self._user_queues[user_id]:
                    del self._user_queues[user_id]
                logger.info(f"User {user_id[:8]}... unsubscribed from events")
    
    async def emit(self, event: Event):
        """Emit an event to all subscribed queues for a specific user."""
        user_id = event.user_id
        
        self._log_event(event)
        
        async with self._lock:
            if user_id not in self._user_queues:
                logger.debug(f"No subscribers for user {user_id[:8]}...")
                return
            
            dead_queues = set()
            for queue in self._user_queues[user_id]:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning(f"Queue full for user {user_id[:8]}..., dropping event")
                except Exception as e:
                    logger.error(f"Error emitting event: {e}")
                    dead_queues.add(queue)
            
            for queue in dead_queues:
                self._user_queues[user_id].discard(queue)
        
        logger.info(f"Emitted {event.event_type} event to user {user_id[:8]}...")
    
    async def emit_to_all(self, event_type: EventType, payload: Dict[str, Any]):
        """Emit an event to all connected users (for system-wide events)."""
        async with self._lock:
            for user_id in list(self._user_queues.keys()):
                event = Event(event_type=event_type, user_id=user_id, payload=payload)
                for queue in self._user_queues[user_id]:
                    try:
                        queue.put_nowait(event)
                    except asyncio.QueueFull:
                        pass
    
    def _log_event(self, event: Event):
        """Log event for debugging purposes."""
        log_entry = {
            "event_id": event.event_id,
            "event_type": event.event_type.value if isinstance(event.event_type, EventType) else event.event_type,
            "user_id": event.user_id[:8] + "...",
            "timestamp": event.timestamp
        }
        self._event_log.append(log_entry)
        
        if len(self._event_log) > self._max_log_size:
            self._event_log = self._event_log[-self._max_log_size:]
        
        logger.debug(f"Event logged: {log_entry}")
    
    def get_event_log(self, limit: int = 50) -> list:
        """Get recent event log for debugging."""
        return self._event_log[-limit:]
    
    async def get_subscriber_count(self, user_id: Optional[str] = None) -> int:
        """Get count of active subscribers."""
        async with self._lock:
            if user_id:
                return len(self._user_queues.get(user_id, set()))
            return sum(len(queues) for queues in self._user_queues.values())


event_service = EventService()


async def emit_swap_executed(
    user_id: str,
    token_from: str,
    token_to: str,
    amount_from: str,
    amount_to: str,
    tx_hash: str,
    chain_id: int
):
    """Emit SWAP_EXECUTED event after successful swap."""
    await event_service.emit(Event(
        event_type=EventType.SWAP_EXECUTED,
        user_id=user_id,
        payload={
            "token_from": token_from,
            "token_to": token_to,
            "amount_from": amount_from,
            "amount_to": amount_to,
            "tx_hash": tx_hash,
            "chain_id": chain_id
        }
    ))


async def emit_ai_trade_executed(
    user_id: str,
    tokens_traded: list,
    allocations: dict,
    tx_hashes: list
):
    """Emit AI_TRADE_EXECUTED event after AI portfolio execution."""
    await event_service.emit(Event(
        event_type=EventType.AI_TRADE_EXECUTED,
        user_id=user_id,
        payload={
            "tokens_traded": tokens_traded,
            "allocations": allocations,
            "tx_hashes": tx_hashes
        }
    ))


async def emit_auto_invest_executed(
    user_id: str,
    cycle_type: str,
    trades_executed: list
):
    """Emit AUTO_INVEST_EXECUTED event after scheduled investment."""
    await event_service.emit(Event(
        event_type=EventType.AUTO_INVEST_EXECUTED,
        user_id=user_id,
        payload={
            "cycle_type": cycle_type,
            "trades_executed": trades_executed
        }
    ))


async def emit_tx_failed(user_id: str, error_message: str, tx_type: str = "swap"):
    """Emit TX_FAILED event on transaction failure."""
    await event_service.emit(Event(
        event_type=EventType.TX_FAILED,
        user_id=user_id,
        payload={
            "error": error_message,
            "tx_type": tx_type
        }
    ))


async def emit_chain_changed(user_id: str, new_chain_id: int, chain_name: str = None):
    """Emit CHAIN_CHANGED event when user switches network."""
    await event_service.emit(Event(
        event_type=EventType.CHAIN_CHANGED,
        user_id=user_id,
        payload={
            "chain_id": new_chain_id,
            "chain_name": chain_name
        }
    ))


async def emit_wallet_connected(user_id: str, wallet_address: str, chain_id: int):
    """Emit WALLET_CONNECTED event."""
    await event_service.emit(Event(
        event_type=EventType.WALLET_CONNECTED,
        user_id=user_id,
        payload={
            "wallet_address": wallet_address,
            "chain_id": chain_id
        }
    ))


async def emit_wallet_disconnected(user_id: str, reason: str = "user_action"):
    """Emit WALLET_DISCONNECTED event."""
    await event_service.emit(Event(
        event_type=EventType.WALLET_DISCONNECTED,
        user_id=user_id,
        payload={
            "reason": reason
        }
    ))


async def emit_balance_updated(user_id: str, chain_id: int, balances: dict):
    """Emit BALANCE_UPDATED event after balance change."""
    await event_service.emit(Event(
        event_type=EventType.BALANCE_UPDATED,
        user_id=user_id,
        payload={
            "chain_id": chain_id,
            "balances": balances
        }
    ))
