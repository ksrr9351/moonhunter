"""
Wallet Authentication Utilities
Handles signature verification and JWT management for wallet-based authentication.
Nonce generation/verification is handled by nonce_store.py (MongoDB-backed).
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from eth_account.messages import encode_defunct
from eth_account import Account
from dotenv import load_dotenv
from pathlib import Path
import os
from jose import jwt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY environment variable is required")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def parse_siwe_message(message: str) -> dict:
    """Parse EIP-4361 SIWE message into components"""
    import re
    
    parsed = {}
    lines = message.strip().split('\n')
    
    if lines and 'wants you to sign in with your Ethereum account' in lines[0]:
        domain_match = re.match(r'^(.+?) wants you to sign in', lines[0])
        if domain_match:
            parsed['domain'] = domain_match.group(1)
    
    if len(lines) > 1:
        address_match = re.match(r'^(0x[a-fA-F0-9]{40})$', lines[1].strip())
        if address_match:
            parsed['address'] = address_match.group(1)
    
    for line in lines:
        if line.startswith('URI: '):
            parsed['uri'] = line[5:].strip()
        elif line.startswith('Version: '):
            parsed['version'] = line[9:].strip()
        elif line.startswith('Chain ID: '):
            try:
                parsed['chain_id'] = int(line[10:].strip())
            except ValueError:
                pass
        elif line.startswith('Nonce: '):
            parsed['nonce'] = line[7:].strip()
        elif line.startswith('Issued At: '):
            parsed['issued_at'] = line[11:].strip()
    
    return parsed


ALLOWED_DOMAINS = os.environ.get('SIWE_ALLOWED_DOMAINS', '').split(',') if os.environ.get('SIWE_ALLOWED_DOMAINS') else []
from chain_registry import get_all_chain_ids


def verify_wallet_signature(
    address: str, 
    signature: str, 
    nonce: str,
    message: Optional[str] = None,
    domain: Optional[str] = None,
    chain_id: Optional[int] = None,
    request_host: Optional[str] = None,
    request_origin: Optional[str] = None,
    skip_nonce_check: bool = False
) -> bool:
    """
    Verify that the signature was created by the wallet address.
    Implements full EIP-4361 SIWE verification with domain and chain binding.
    Validates against request host for server-side security.
    Falls back to legacy format for backward compatibility.
    
    Args:
        skip_nonce_check: If True, skips nonce verification (already done externally with MongoDB)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"[SIWE] Verifying signature for address: {address[:10]}...")
        logger.info(f"[SIWE] Nonce provided: {nonce[:20]}...")
        
        if not skip_nonce_check:
            logger.warning(f"[SIWE] skip_nonce_check is False but in-memory nonce store removed. Nonce must be verified externally via nonce_store module.")
            return False
        else:
            logger.info(f"[SIWE] Skipping nonce check (already verified externally)")
        
        if message:
            parsed = parse_siwe_message(message)
            logger.info(f"[SIWE] Parsed message fields: {list(parsed.keys())}")
            
            if parsed.get('nonce') != nonce:
                logger.warning(f"[SIWE] Nonce mismatch: expected {nonce[:10]}..., got {parsed.get('nonce', 'None')[:10] if parsed.get('nonce') else 'None'}...")
                return False
            
            if parsed.get('address', '').lower() != address.lower():
                logger.warning(f"[SIWE] Address mismatch in SIWE message")
                return False
            
            msg_domain = parsed.get('domain')
            if not msg_domain:
                logger.warning(f"[SIWE] Missing domain in SIWE message")
                return False
            
            if request_host:
                if msg_domain != request_host and not request_host.endswith('.' + msg_domain):
                    if not msg_domain.endswith('.replit.dev') and not msg_domain.endswith('.replit.app'):
                        logger.warning(f"[SIWE] Domain {msg_domain} doesn't match request host {request_host}")
                        return False
            
            if domain and msg_domain != domain:
                logger.warning(f"[SIWE] Domain mismatch: client sent {domain}, message has {msg_domain}")
                return False
            
            if ALLOWED_DOMAINS:
                is_allowed = any(
                    msg_domain.endswith(allowed) or msg_domain == allowed 
                    for allowed in ALLOWED_DOMAINS if allowed
                )
                if not is_allowed:
                    logger.warning(f"[SIWE] Domain {msg_domain} not in allowed list")
                    return False
            
            msg_chain_id = parsed.get('chain_id')
            if not msg_chain_id:
                logger.warning(f"[SIWE] Missing Chain ID in SIWE message")
                return False
            
            if msg_chain_id not in get_all_chain_ids(include_testnet=True):
                logger.warning(f"[SIWE] Chain ID {msg_chain_id} not in allowed list {get_all_chain_ids(include_testnet=True)}")
                return False
            
            if chain_id and msg_chain_id != chain_id:
                logger.warning(f"[SIWE] Chain ID mismatch: client sent {chain_id}, message has {msg_chain_id}")
                return False
            
            issued_at = parsed.get('issued_at')
            if not issued_at:
                logger.warning(f"[SIWE] Missing Issued At timestamp in SIWE message")
                return False
            
            try:
                issued_time = datetime.fromisoformat(issued_at.replace('Z', '+00:00'))
                age_seconds = (datetime.now(timezone.utc) - issued_time).total_seconds()
                if age_seconds > 600:
                    logger.warning(f"[SIWE] Message too old: {age_seconds:.0f} seconds")
                    return False
                if age_seconds < -60:
                    logger.warning(f"[SIWE] Message timestamp in future: {age_seconds:.0f} seconds")
                    return False
            except Exception as e:
                logger.warning(f"[SIWE] Invalid issuedAt format: {e}")
                return False
            
            version = parsed.get('version')
            if version != '1':
                logger.warning(f"[SIWE] Invalid or missing version: {version}")
                return False
            
            uri = parsed.get('uri')
            if not uri:
                logger.warning(f"[SIWE] Missing URI in SIWE message")
                return False
            
            if request_origin:
                if uri != request_origin:
                    if not (uri.endswith('.replit.dev') or uri.endswith('.replit.app')):
                        logger.warning(f"[SIWE] URI {uri} doesn't match request origin {request_origin}")
                        return False
            
            logger.info(f"[SIWE] EIP-4361 message validation passed (domain={msg_domain}, chainId={msg_chain_id})")
            verification_message = message
        else:
            verification_message = f"Sign this message to authenticate with Moon Hunters\n\nNonce: {nonce}\nAddress: {address}"
            logger.info(f"[SIWE] Using legacy message format (not EIP-4361)")
        
        logger.info(f"[SIWE] Message to verify (first 100 chars): {verification_message[:100]}...")
        
        message_hash = encode_defunct(text=verification_message)
        
        recovered_address = Account.recover_message(message_hash, signature=signature)
        logger.info(f"[SIWE] Recovered address: {recovered_address[:10]}... vs claimed: {address[:10]}...")
        
        is_match = recovered_address.lower() == address.lower()
        if is_match:
            logger.info(f"[SIWE] Signature valid for address: {address[:10]}...")
        else:
            logger.warning(f"[SIWE] Address mismatch! Recovered: {recovered_address}, Claimed: {address}")
        
        return is_match
        
    except Exception as e:
        logger.error(f"[SIWE] Signature verification error: {str(e)}")
        return False


def create_wallet_jwt(wallet_address: str) -> str:
    """Create JWT token for authenticated wallet"""
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode = {
        "sub": wallet_address.lower(),
        "wallet_address": wallet_address.lower(),
        "exp": expire,
        "type": "wallet"
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_wallet_jwt(token: str) -> Optional[str]:
    """Decode JWT token and return wallet address"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        wallet_address = payload.get("wallet_address")
        
        if wallet_address is None:
            return None
            
        return str(wallet_address)
        
    except Exception:
        return None
