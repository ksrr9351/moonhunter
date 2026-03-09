"""
Pydantic schema models for the Moon Hunters API.
This module contains all data validation and serialization models.
"""

from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator
from typing import List, Optional, Literal, Dict, Any
import uuid
from datetime import datetime, timezone
import re


# =============================================================================
# User Authentication Models
# =============================================================================

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    hashed_password: str
    wallet_address: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True


class UserSignup(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_]+$')
    password: str = Field(..., min_length=8, max_length=128)
    wallet_address: Optional[str] = Field(None, pattern=r'^0x[a-fA-F0-9]{40}$')
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    wallet_address: Optional[str] = None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# =============================================================================
# Status Check Models
# =============================================================================

class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str = Field(..., min_length=1, max_length=100)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StatusCheckCreate(BaseModel):
    client_name: str = Field(..., min_length=1, max_length=100)


# =============================================================================
# Portfolio Models
# =============================================================================

class Portfolio(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    assets: List[dict] = Field(default_factory=list)
    total_value: float = Field(default=0.0, ge=0)
    total_investment: float = Field(default=0.0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class PortfolioAsset(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10, pattern=r'^[A-Z0-9]+$')
    amount: float = Field(..., gt=0)
    purchase_price: float = Field(..., gt=0)
    purchase_date: datetime


# =============================================================================
# Transaction Models
# =============================================================================

class Transaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    portfolio_id: Optional[str] = None
    transaction_type: Literal['buy', 'sell', 'deposit', 'withdrawal']
    symbol: str = Field(..., min_length=1, max_length=10)
    amount: float = Field(..., gt=0)
    price: float = Field(..., ge=0)
    total: float = Field(..., ge=0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: Literal['completed', 'pending', 'failed'] = "completed"


class TransactionCreate(BaseModel):
    portfolio_id: Optional[str] = None
    transaction_type: Literal['buy', 'sell', 'deposit', 'withdrawal']
    symbol: str = Field(..., min_length=1, max_length=10, pattern=r'^[A-Z0-9]+$')
    amount: float = Field(..., gt=0, le=1000000000)
    price: float = Field(..., ge=0, le=1000000000)


# =============================================================================
# Wallet Models
# =============================================================================

class WalletNonceRequest(BaseModel):
    address: str = Field(..., pattern=r'^0x[a-fA-F0-9]{40}$')


class WalletVerifyRequest(BaseModel):
    address: str = Field(..., pattern=r'^0x[a-fA-F0-9]{40}$')
    signature: str = Field(..., min_length=1, max_length=500)
    nonce: str = Field(..., min_length=1, max_length=200)
    message: Optional[str] = Field(None, max_length=2000)  # Full SIWE message
    domain: Optional[str] = Field(None, max_length=200)    # Domain for SIWE
    chainId: Optional[int] = Field(None, ge=1)             # Chain ID
    issuedAt: Optional[str] = Field(None, max_length=50)   # ISO timestamp


class ReownWalletLoginRequest(BaseModel):
    walletAddress: str = Field(..., pattern=r'^0x[a-fA-F0-9]{40}$')
    reownToken: Optional[str] = Field(None, max_length=1000)


class DirectWalletConnect(BaseModel):
    address: str


# =============================================================================
# AI & Investment Models
# =============================================================================

class AIRecommendationRequest(BaseModel):
    risk_tolerance: Literal['conservative', 'moderate', 'aggressive'] = "moderate"
    investment_amount: float = Field(..., gt=0, le=1000000000)
    investment_horizon: Literal['short-term', 'medium-term', 'long-term'] = "medium-term"


class AIInvestRequest(BaseModel):
    usdt_amount: float = Field(..., gt=0, le=1000000)
    strategy: Literal['dump_buy', 'trend_follow', 'balanced'] = 'balanced'


class AIAllocateRequest(BaseModel):
    usdt_amount: float = Field(..., gt=0, le=1000000)


# =============================================================================
# Auto-Invest Models
# =============================================================================

class AutoInvestConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    enabled: bool = False
    investment_amount: float = Field(default=100.0, gt=0, le=1000000000)
    frequency: Literal['daily', 'weekly', 'monthly'] = "weekly"
    risk_tolerance: Literal['conservative', 'moderate', 'aggressive'] = "moderate"
    auto_rebalance: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AutoInvestConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    investment_amount: Optional[float] = Field(None, gt=0, le=1000000000)
    frequency: Optional[Literal['daily', 'weekly', 'monthly']] = None
    risk_tolerance: Optional[Literal['conservative', 'moderate', 'aggressive']] = None
    auto_rebalance: Optional[bool] = None


class CompletedSwapItem(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    amount: float = Field(..., ge=0)
    tx_hash: str = Field(..., pattern=r'^0x[a-fA-F0-9]{64}$')


class AutoInvestCompleteRequest(BaseModel):
    completed_swaps: List[CompletedSwapItem]


# =============================================================================
# Position & Trading Models
# =============================================================================

class CreatePositionRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    usdt_amount: float = Field(..., gt=0, le=100000)
    strategy: str = Field(default="manual", max_length=50)
    trigger_reason: str = Field(default="Manual investment", max_length=200)


class ClosePositionRequest(BaseModel):
    reason: str = Field(default="manual", max_length=200)


class SetPositionTriggerRequest(BaseModel):
    stop_loss_percent: Optional[float] = Field(None, ge=1, le=50)
    take_profit_percent: Optional[float] = Field(None, ge=1, le=100)


# =============================================================================
# DEX Trading Models
# =============================================================================

class RecordDexSwapRequest(BaseModel):
    """Record a real DEX swap as a portfolio position"""
    symbol: str = Field(..., min_length=1, max_length=10)
    usdt_amount: float = Field(..., gt=0, le=1000000)
    quantity: float = Field(..., gt=0)
    entry_price: float = Field(..., gt=0)
    tx_hash: str = Field(..., min_length=10, max_length=100)
    chain_id: int = Field(...)
    strategy: str = Field(default="manual", max_length=50)
    trigger_reason: str = Field(default="DEX swap executed", max_length=200)


class CloseDexPositionRequest(BaseModel):
    """Close a position with DEX sell transaction"""
    position_id: str = Field(..., min_length=1)
    exit_price: float = Field(..., gt=0)
    exit_quantity: float = Field(..., gt=0)
    tx_hash: str = Field(..., min_length=10, max_length=100)
    reason: str = Field(default="dex_sell", max_length=200)


# =============================================================================
# Bot Settings Models
# =============================================================================

class BotSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    max_daily_investment: Optional[float] = Field(None, ge=10, le=10000)
    max_per_trade: Optional[float] = Field(None, ge=10, le=1000)
    min_dump_threshold: Optional[float] = Field(None, ge=3, le=20)
    max_risk_score: Optional[float] = Field(None, ge=0.1, le=1.0)
    coin_whitelist: Optional[List[str]] = None
    coin_blacklist: Optional[List[str]] = None
    pause_on_loss: Optional[bool] = None
    max_daily_loss: Optional[float] = Field(None, ge=10, le=1000)
    cooldown_minutes: Optional[int] = Field(None, ge=5, le=1440)
    stop_loss_percent: Optional[float] = Field(None, ge=1, le=50)
    take_profit_percent: Optional[float] = Field(None, ge=1, le=100)
    auto_stop_loss: Optional[bool] = None
    auto_take_profit: Optional[bool] = None


# =============================================================================
# Alert Settings Models
# =============================================================================

class AlertSettings(BaseModel):
    email_alerts: bool = False
    threshold: int = Field(default=5, ge=1, le=100)
    email: Optional[str] = Field(None, max_length=255)
    last_alert: Optional[str] = None
    
    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v):
        """Allow None or empty string, validate format if provided"""
        if v is None or v == '':
            return None
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, v):
            raise ValueError('Invalid email format')
        return v


# =============================================================================
# Push Notification Models
# =============================================================================

class PushSubscription(BaseModel):
    endpoint: str
    keys: Dict[str, str]


class PushUnsubscribe(BaseModel):
    endpoint: str


# =============================================================================
# Social Trading Models
# =============================================================================

class SocialSettingsUpdate(BaseModel):
    public_portfolio: Optional[bool] = None
    allow_copy: Optional[bool] = None
    display_name: Optional[str] = None


class CopySettingsUpdate(BaseModel):
    copy_enabled: bool
    copy_percentage: int = 100
    max_per_trade: float = 100.0


# =============================================================================
# Backtesting Models
# =============================================================================

class BacktestRequest(BaseModel):
    strategy: str
    initial_capital: float = 10000.0
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    params: Dict[str, Any] = {}
