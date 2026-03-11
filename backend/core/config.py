import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger("server")

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

REQUIRED_ENV_VARS = {
    'MONGO_URL': 'MongoDB connection string',
    'DB_NAME': 'MongoDB database name',
    'JWT_SECRET_KEY': 'JWT secret for token signing',
}

OPTIONAL_ENV_VARS = {
    'CMC_API_KEY': 'CoinMarketCap API key (needed for live market data)',
    'COINGECKO_API_KEY': 'CoinGecko API key (needed for backtesting historical data)',
    'PERPLEXITY_API_KEY': 'Perplexity AI API key (needed for AI recommendations)',
    'ONEINCH_API_KEY': '1inch DEX API key (needed for swaps)',
    'VAPID_PRIVATE_KEY': 'VAPID private key (needed for push notifications)',
    'VAPID_PUBLIC_KEY': 'VAPID public key (needed for push notifications)',
    'REDIS_URL': 'Redis connection URL (needed for caching)',
}

ENV = os.environ.get('ENV', 'development')
DEMO_MODE = os.environ.get('DEMO_MODE', 'false').lower() == 'true'


def validate_environment():
    if ENV == 'production' and DEMO_MODE:
        logger.error("FATAL: DEMO_MODE cannot be enabled in production!")
        sys.exit(1)

    missing_required = []
    for var, description in REQUIRED_ENV_VARS.items():
        if not os.environ.get(var):
            missing_required.append(f"  - {var}: {description}")

    if missing_required:
        logger.error("Missing required environment variables:")
        for m in missing_required:
            logger.error(m)
        sys.exit(1)

    missing_optional = []
    for var, description in OPTIONAL_ENV_VARS.items():
        if not os.environ.get(var):
            missing_optional.append(f"  - {var}: {description}")

    if missing_optional:
        logger.warning("Missing optional environment variables (some features may be limited):")
        for m in missing_optional:
            logger.warning(m)

    logger.info(f"Environment: {ENV} | Demo Mode: {DEMO_MODE}")
    logger.info("Environment validation passed")


MOONHUNTERS_CONTRACT_ADDRESS = {
    1: os.environ.get("MOONHUNTERS_CONTRACT_ETH", ""),
    56: os.environ.get("MOONHUNTERS_CONTRACT_BSC", ""),
    137: os.environ.get("MOONHUNTERS_CONTRACT_POLYGON", ""),
    42161: os.environ.get("MOONHUNTERS_CONTRACT_ARBITRUM", ""),
}

MOONHUNTERS_FEE_PERCENT = float(os.environ.get("MOONHUNTERS_FEE_PERCENT", "2"))

MOONHUNTERS_TREASURY_ADDRESS = os.environ.get(
    "MOONHUNTERS_TREASURY_ADDRESS", ""
)

MOONHUNTERS_MAX_FEE_PERCENT = 5
