"""
Redis cache client — async singleton with graceful fallback.
All operations silently return None / False if Redis is unavailable,
so the app never crashes due to Redis being down.
"""
import os
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_redis = None


async def init_redis():
    """Connect to Redis. Call once at startup."""
    global _redis
    url = os.environ.get("REDIS_URL")
    if not url:
        logger.warning("REDIS_URL not set — caching disabled")
        return

    try:
        import redis.asyncio as aioredis
        _redis = aioredis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=3,
            retry_on_timeout=True,
        )
        await _redis.ping()
        info = await _redis.info("server")
        host = info.get("tcp_port", "unknown")
        logger.info(f"Redis connected: {url.split('@')[-1].split('/')[0]}")
    except Exception as e:
        logger.warning(f"Redis connection failed ({e}) — caching disabled")
        _redis = None


async def close_redis():
    """Gracefully close Redis connection. Call at shutdown."""
    global _redis
    if _redis:
        try:
            await _redis.aclose()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.warning(f"Redis close error: {e}")
        _redis = None


async def cache_get(key: str) -> Optional[Any]:
    """Get a cached value by key. Returns parsed JSON or None."""
    if not _redis:
        return None
    try:
        raw = await _redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.debug(f"Redis GET {key} failed: {e}")
        return None


async def cache_set(key: str, data: Any, ttl_seconds: int = 60) -> bool:
    """Set a cached value with TTL. Returns True on success."""
    if not _redis:
        return False
    try:
        await _redis.set(key, json.dumps(data, default=str), ex=ttl_seconds)
        return True
    except Exception as e:
        logger.debug(f"Redis SET {key} failed: {e}")
        return False


async def cache_delete(key: str) -> bool:
    """Delete a single key."""
    if not _redis:
        return False
    try:
        await _redis.delete(key)
        return True
    except Exception as e:
        logger.debug(f"Redis DEL {key} failed: {e}")
        return False


async def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern (e.g. 'cmc:*'). Returns count deleted."""
    if not _redis:
        return 0
    try:
        count = 0
        async for key in _redis.scan_iter(match=pattern, count=100):
            await _redis.delete(key)
            count += 1
        return count
    except Exception as e:
        logger.debug(f"Redis DEL pattern {pattern} failed: {e}")
        return 0
