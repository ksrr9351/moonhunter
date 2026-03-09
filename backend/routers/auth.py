from fastapi import APIRouter, HTTPException, Depends, Header, Request
from typing import Optional
import os
import uuid
import logging
from datetime import datetime, timezone

from core.deps import db, get_current_user, limiter, security
from core.schemas import (
    WalletNonceRequest, WalletVerifyRequest, ReownWalletLoginRequest,
    DirectWalletConnect, UserSignup, UserLogin, UserResponse, TokenResponse, User
)
from auth_utils import verify_password, get_password_hash, create_access_token
from wallet_auth import verify_wallet_signature, create_wallet_jwt, decode_wallet_jwt
from nonce_store import generate_nonce, verify_nonce

IS_PRODUCTION = os.environ.get('ENV', 'development').lower() == 'production'

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ==================== WALLET AUTHENTICATION ====================

@router.post("/auth/wallet/nonce")
@limiter.limit("30/minute")
async def get_wallet_nonce(request: Request, nonce_request: WalletNonceRequest):
    """Generate nonce for wallet authentication (MongoDB-backed for multi-instance)"""
    try:
        nonce = await generate_nonce(nonce_request.address)
        return {"nonce": nonce}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate nonce: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate nonce")


@router.post("/auth/wallet/verify")
@limiter.limit("10/minute")
async def verify_wallet(request: Request, verify_request: WalletVerifyRequest):
    """Verify wallet signature and create session using EIP-4361 SIWE"""
    try:
        # Get request host for server-side domain binding
        request_host = request.headers.get('host', '').split(':')[0]  # Remove port
        origin_header = request.headers.get('origin', '')
        
        # First verify the nonce using async MongoDB store
        nonce_valid = await verify_nonce(verify_request.address, verify_request.nonce)
        if not nonce_valid:
            raise HTTPException(status_code=401, detail="Invalid or expired nonce")
        
        # Pass all SIWE parameters for proper verification with server-side host binding
        # Note: Nonce already verified above, so skip_nonce_check=True
        is_valid = verify_wallet_signature(
            address=verify_request.address,
            signature=verify_request.signature,
            nonce=verify_request.nonce,
            message=verify_request.message,
            domain=verify_request.domain,
            chain_id=verify_request.chainId,
            request_host=request_host,
            request_origin=origin_header,
            skip_nonce_check=True  # Already verified above
        )
        
        if not is_valid:
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        wallet_address_lower = verify_request.address.lower()
        existing_user = await db.users.find_one(
            {"wallet_address": wallet_address_lower},
            {"_id": 0}
        )
        
        if not existing_user:
            new_user = {
                "id": str(uuid.uuid4()),
                "wallet_address": wallet_address_lower,
                "email": None,
                "username": f"user_{wallet_address_lower[:8]}",
                "hashed_password": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True
            }
            await db.users.insert_one(new_user)
            user_data = new_user
        else:
            user_data = existing_user
        
        access_token = create_wallet_jwt(wallet_address_lower)
        
        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_data["id"],
                "wallet_address": wallet_address_lower,
                "username": user_data["username"],
                "is_active": user_data.get("is_active", True)
            }
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Verification failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Verification failed")


@router.get("/auth/wallet/me")
@limiter.limit("60/minute")
async def get_wallet_user(request: Request, authorization: Optional[str] = Header(None)):
    """Get current authenticated wallet user"""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        token = authorization.replace("Bearer ", "")
        wallet_address = decode_wallet_jwt(token)
        
        if not wallet_address:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one(
            {"wallet_address": wallet_address},
            {"_id": 0}
        )
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": user["id"],
            "wallet_address": user["wallet_address"],
            "username": user["username"],
            "is_active": user.get("is_active", True)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching wallet user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch user")


@router.post("/auth/wallet/logout")
@limiter.limit("30/minute")
async def wallet_logout(request: Request):
    """Logout wallet user"""
    return {"message": "Logged out successfully"}


@router.post("/auth/wallet/refresh")
@limiter.limit("30/minute")
async def refresh_wallet_session(request: Request, authorization: Optional[str] = Header(None)):
    """
    Refresh wallet session token for long-lived sessions.
    Returns a new JWT token if the current one is still valid.
    """
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        token = authorization.replace("Bearer ", "")
        wallet_address = decode_wallet_jwt(token)
        
        if not wallet_address:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        user = await db.users.find_one(
            {"wallet_address": wallet_address},
            {"_id": 0}
        )
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not user.get("is_active", True):
            raise HTTPException(status_code=403, detail="User account is disabled")
        
        new_token = create_wallet_jwt(wallet_address)
        
        logger.info(f"Session refreshed for wallet: {wallet_address[:10]}...")
        
        return {
            "success": True,
            "access_token": new_token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "wallet_address": user["wallet_address"],
                "username": user["username"],
                "is_active": user.get("is_active", True)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing wallet session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to refresh session")


# ==================== DIRECT WALLET CONNECTION ====================

@router.post("/auth/wallet/connect")
@limiter.limit("30/minute")
async def direct_wallet_connect(request: Request, connect_request: DirectWalletConnect):
    """
    Direct wallet connection - authenticates user based on wallet address.
    Creates a new user if they don't exist.
    SECURITY: Disabled in production — use SIWE signature-based auth instead.
    """
    if IS_PRODUCTION:
        raise HTTPException(
            status_code=403,
            detail="Direct wallet connect is disabled in production. Use signature-based authentication."
        )
    logger.warning(f"Direct wallet connect used (non-production): {connect_request.address[:10]}...")
    try:
        wallet_address = connect_request.address.lower()
        
        if not wallet_address or not wallet_address.startswith('0x') or len(wallet_address) != 42:
            raise HTTPException(status_code=400, detail="Invalid wallet address")
        
        # Find or create user
        existing_user = await db.users.find_one(
            {"wallet_address": wallet_address},
            {"_id": 0}
        )
        
        if not existing_user:
            new_user = {
                "id": str(uuid.uuid4()),
                "wallet_address": wallet_address,
                "email": None,
                "username": f"user_{wallet_address[:8]}",
                "hashed_password": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True
            }
            await db.users.insert_one(new_user)
            user_data = new_user
            logger.info(f"New user created via direct connect: {wallet_address[:10]}...")
        else:
            user_data = existing_user
            logger.info(f"Existing user connected: {wallet_address[:10]}...")
        
        # Create JWT token
        access_token = create_wallet_jwt(wallet_address)
        
        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_data["id"],
                "wallet_address": wallet_address,
                "username": user_data["username"],
                "is_active": user_data.get("is_active", True)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Direct wallet connect error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Connection failed")


# ==================== AUTHENTICATION ROUTES ====================

@router.post("/auth/signup", response_model=TokenResponse)
@limiter.limit("5/minute")
async def signup(request: Request, user_data: UserSignup):
    """Register a new user"""
    try:
        existing_user = await db.users.find_one({"email": user_data.email}, {"_id": 0})
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=get_password_hash(user_data.password)
        )
        
        user_dict = user.model_dump()
        user_dict['created_at'] = user_dict['created_at'].isoformat()
        await db.users.insert_one(user_dict)
        
        access_token = create_access_token(data={"sub": user.id, "email": user.email})
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user.id,
                email=user.email,
                username=user.username,
                created_at=user.created_at
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during signup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Signup failed")


@router.post("/auth/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, credentials: UserLogin):
    """Login user and return JWT token"""
    try:
        user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
        if not user or not verify_password(credentials.password, user["hashed_password"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        if isinstance(user.get('created_at'), str):
            user['created_at'] = datetime.fromisoformat(user['created_at'])
        
        access_token = create_access_token(data={"sub": user["id"], "email": user["email"]})
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user["id"],
                email=user["email"],
                username=user["username"],
                created_at=user["created_at"]
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Login failed")


@router.get("/auth/me", response_model=UserResponse)
@limiter.limit("60/minute")
async def get_me(request: Request, current_user: dict = Depends(get_current_user)):
    """Get current authenticated user information"""
    try:
        return UserResponse(
            id=current_user["id"],
            email=current_user["email"],
            username=current_user["username"],
            created_at=current_user["created_at"]
        )
    except Exception as e:
        logger.error(f"Error fetching user info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch user info")


@router.post("/auth/logout")
@limiter.limit("30/minute")
async def logout(request: Request):
    """Logout user (client-side token removal)"""
    return {"message": "Logged out successfully"}
