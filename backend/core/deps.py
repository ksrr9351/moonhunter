import os
import certifi
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter
from datetime import datetime

from auth_utils import decode_access_token
from perplexity_client import PerplexityClient
from market_provider import market_provider
from fast_movers_detector import FastMoversDetector
from auto_invest_scheduler import AutoInvestScheduler
from event_service import event_service
from wallet_service import init_wallet_service
from dump_detection_engine import init_dump_detection_engine
from analysis_engine import init_analysis_engine
from portfolio_engine import init_portfolio_engine
from recommendation_engine import init_recommendation_engine
from trading_bot import init_trading_bot
from analytics_engine import init_analytics_engine
from price_streaming import price_streaming_service
from dex_service import init_dex_service
from push_notification_service import init_push_notification_service
from social_trading_engine import init_social_trading_engine
from backtesting_engine import init_backtesting_engine
from historical_data_provider import init_historical_data_provider
from ai_dump_alert_service import AIDumpAlertService
from email_service import email_service
from nonce_store import init_nonce_store

logger = logging.getLogger("server")


def get_real_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()
    if request.client:
        return request.client.host
    return "unknown"


limiter = Limiter(key_func=get_real_client_ip)

mongo_url = os.environ['MONGO_URL']
ENV = os.environ.get('ENV', 'development')
mongo_tls_kwargs = {
    "tls": True,
    "tlsCAFile": certifi.where(),
}
if ENV != 'production':
    mongo_tls_kwargs["tlsAllowInvalidCertificates"] = True

mongo_client = AsyncIOMotorClient(
    mongo_url,
    maxPoolSize=100,
    minPoolSize=10,
    maxIdleTimeMS=30000,
    serverSelectionTimeoutMS=5000,
    **mongo_tls_kwargs
)
db = mongo_client[os.environ['DB_NAME']]

init_nonce_store(db)

security = HTTPBearer()

perplexity_client = PerplexityClient()
fast_movers_detector = FastMoversDetector(mongo_client, os.environ['DB_NAME'], market_provider=market_provider)
auto_invest_scheduler = AutoInvestScheduler(db, perplexity_client)
wallet_service = init_wallet_service(db)
dump_detection_engine = init_dump_detection_engine(db, market_provider)
analysis_engine = init_analysis_engine(db, market_provider)
portfolio_engine = init_portfolio_engine(db, market_provider, wallet_service)
recommendation_engine = init_recommendation_engine(db, dump_detection_engine, analysis_engine, market_provider)
dex_service = init_dex_service()
analytics_engine = init_analytics_engine(db)
trading_bot = init_trading_bot(db, market_provider, dump_detection_engine, portfolio_engine, wallet_service, dex_service, email_service)
push_service = init_push_notification_service(db)
social_trading = init_social_trading_engine(db)
historical_provider = init_historical_data_provider()
backtesting = init_backtesting_engine(market_provider, historical_provider)
ti_service = None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials

    from wallet_auth import decode_wallet_jwt
    wallet_address = decode_wallet_jwt(token)
    if wallet_address:
        user = await db.users.find_one({"wallet_address": wallet_address}, {"_id": 0})
        if user:
            if isinstance(user.get('created_at'), str):
                user['created_at'] = datetime.fromisoformat(user['created_at'])
            return user

    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    if isinstance(user.get('created_at'), str):
        user['created_at'] = datetime.fromisoformat(user['created_at'])

    return user
