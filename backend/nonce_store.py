"""
Nonce Store Service
Provides distributed nonce storage using MongoDB for multi-instance deployment.
Replaces in-memory nonce storage for scalability.
"""
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

NONCE_EXPIRY_MINUTES = 10
NONCE_COLLECTION = "auth_nonces"

_db = None


def init_nonce_store(database):
    """Initialize nonce store with shared database reference from core.deps"""
    global _db
    _db = database
    logger.info("Nonce store initialized with shared database")


def _get_db():
    """Get the database reference, raising if not initialized"""
    if _db is None:
        raise RuntimeError("Nonce store not initialized. Call init_nonce_store(db) first.")
    return _db


async def ensure_indexes():
    """Create indexes for the nonce collection. Call during startup."""
    db = _get_db()
    try:
        await db[NONCE_COLLECTION].create_index(
            "created_at",
            expireAfterSeconds=NONCE_EXPIRY_MINUTES * 60
        )
        logger.info(f"Created TTL index on {NONCE_COLLECTION}.created_at")
    except Exception as e:
        logger.debug(f"TTL index creation: {e}")

    try:
        await db[NONCE_COLLECTION].create_index(
            "wallet_address",
            unique=True
        )
        logger.info(f"Created unique index on {NONCE_COLLECTION}.wallet_address")
    except Exception as e:
        logger.debug(f"Unique index creation: {e}")


async def generate_nonce(wallet_address: str) -> str:
    """
    Generate a unique nonce for wallet authentication.
    Stores in MongoDB for multi-instance support.
    """
    db = _get_db()
    nonce = secrets.token_urlsafe(32)
    address_lower = wallet_address.lower()
    
    await db[NONCE_COLLECTION].update_one(
        {"wallet_address": address_lower},
        {
            "$set": {
                "nonce": nonce,
                "created_at": datetime.now(timezone.utc)
            }
        },
        upsert=True
    )
    
    logger.info(f"Generated nonce for {address_lower[:10]}...")
    return nonce


async def verify_nonce(wallet_address: str, nonce: str) -> bool:
    """
    Verify nonce exists and hasn't expired.
    Removes nonce after successful verification (single use).
    """
    db = _get_db()
    address_lower = wallet_address.lower()
    
    result = await db[NONCE_COLLECTION].find_one_and_delete(
        {"wallet_address": address_lower}
    )
    
    if not result:
        logger.warning(f"No nonce found for {address_lower[:10]}...")
        return False
    
    if result.get("nonce") != nonce:
        logger.warning(f"Nonce mismatch for {address_lower[:10]}...")
        return False
    
    created_at = result.get("created_at")
    if created_at:
        expiry_time = datetime.now(timezone.utc) - timedelta(minutes=NONCE_EXPIRY_MINUTES)
        # Ensure both datetimes are timezone-aware for comparison
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if created_at < expiry_time:
            logger.warning(f"Nonce expired for {address_lower[:10]}...")
            return False
    
    logger.info(f"Nonce verified for {address_lower[:10]}...")
    return True


async def cleanup_expired_nonces():
    """
    Remove expired nonces from store.
    Note: MongoDB TTL index handles this automatically, but this can be called for immediate cleanup.
    """
    db = _get_db()
    expiry_time = datetime.now(timezone.utc) - timedelta(minutes=NONCE_EXPIRY_MINUTES)
    
    result = await db[NONCE_COLLECTION].delete_many(
        {"created_at": {"$lt": expiry_time}}
    )
    
    if result.deleted_count > 0:
        logger.info(f"Cleaned up {result.deleted_count} expired nonces")
