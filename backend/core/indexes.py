import logging

logger = logging.getLogger("server")


async def ensure_database_indexes(db):
    try:
        await db.users.create_index("id", unique=True)
        await db.users.create_index("email", unique=True, sparse=True)
        await db.users.create_index("wallet_address", unique=True, sparse=True)
        logger.info("Users collection indexes created")
    except Exception as e:
        logger.debug(f"Users indexes: {e}")

    try:
        await db.portfolios.create_index("user_id")
        await db.portfolios.create_index([("user_id", 1), ("created_at", -1)])
        logger.info("Portfolios collection indexes created")
    except Exception as e:
        logger.debug(f"Portfolios indexes: {e}")

    try:
        await db.transactions.create_index("user_id")
        await db.transactions.create_index([("user_id", 1), ("created_at", -1)])
        await db.transactions.create_index("portfolio_id")
        logger.info("Transactions collection indexes created")
    except Exception as e:
        logger.debug(f"Transactions indexes: {e}")

    try:
        await db.positions.create_index("user_id")
        await db.positions.create_index([("user_id", 1), ("status", 1)])
        await db.positions.create_index("status")
        logger.info("Positions collection indexes created")
    except Exception as e:
        logger.debug(f"Positions indexes: {e}")

    try:
        await db.ai_positions.create_index("user_id")
        await db.ai_positions.create_index("status")
        await db.ai_positions.create_index([("user_id", 1), ("status", 1)])
        await db.ai_positions.create_index([("user_id", 1), ("created_at", -1)])
        logger.info("AI positions collection indexes created")
    except Exception as e:
        logger.debug(f"AI positions indexes: {e}")

    try:
        await db.bot_settings.create_index("user_id", unique=True)
        logger.info("Bot settings collection indexes created")
    except Exception as e:
        logger.debug(f"Bot settings indexes: {e}")

    try:
        await db.alert_settings.create_index("user_id", unique=True)
        logger.info("Alert settings collection indexes created")
    except Exception as e:
        logger.debug(f"Alert settings indexes: {e}")

    try:
        await db.push_subscriptions.create_index("user_id")
        await db.push_subscriptions.create_index("endpoint", unique=True)
        logger.info("Push subscriptions collection indexes created")
    except Exception as e:
        logger.debug(f"Push subscriptions indexes: {e}")

    try:
        await db.social_profiles.create_index("user_id", unique=True)
        await db.social_profiles.create_index("is_public")
        logger.info("Social profiles collection indexes created")
    except Exception as e:
        logger.debug(f"Social profiles indexes: {e}")

    try:
        await db.auto_invest_executions.create_index("user_id")
        await db.auto_invest_executions.create_index([("user_id", 1), ("created_at", -1)])
        logger.info("Auto invest executions collection indexes created")
    except Exception as e:
        logger.debug(f"Auto invest indexes: {e}")

    try:
        await db.dex_transactions.create_index("user_id")
        await db.dex_transactions.create_index([("user_id", 1), ("created_at", -1)])
        logger.info("DEX transactions collection indexes created")
    except Exception as e:
        logger.debug(f"DEX transactions indexes: {e}")

    try:
        await db.auth_nonces.create_index(
            "created_at",
            expireAfterSeconds=600
        )
        await db.auth_nonces.create_index("wallet_address", unique=True)
        logger.info("Auth nonces collection indexes created")
    except Exception as e:
        logger.debug(f"Auth nonces indexes: {e}")

    try:
        await db.dump_opportunities.create_index(
            "expires_at",
            expireAfterSeconds=0
        )
        await db.dump_opportunities.create_index("symbol")
        await db.dump_opportunities.create_index("supported_chains")
        await db.dump_opportunities.create_index([("dump_percentage", 1)])
        logger.info("Dump opportunities collection indexes created (TTL on expires_at)")
    except Exception as e:
        logger.debug(f"Dump opportunities indexes: {e}")

    try:
        await db.position_triggers.create_index("position_id")
        await db.position_triggers.create_index([("user_id", 1), ("status", 1)])
        logger.info("Position triggers collection indexes created")
    except Exception as e:
        logger.debug(f"Position triggers indexes: {e}")

    try:
        await db.follows.create_index("user_id")
        await db.follows.create_index("followed_user_id")
        await db.follows.create_index([("user_id", 1), ("followed_user_id", 1)], unique=True)
        logger.info("Follows collection indexes created")
    except Exception as e:
        logger.debug(f"Follows indexes: {e}")

    try:
        await db.social_settings.create_index("user_id", unique=True)
        logger.info("Social settings collection indexes created")
    except Exception as e:
        logger.debug(f"Social settings indexes: {e}")

    try:
        await db.bot_trade_logs.create_index("user_id")
        await db.bot_trade_logs.create_index([("user_id", 1), ("timestamp", -1)])
        logger.info("Bot trade logs collection indexes created")
    except Exception as e:
        logger.debug(f"Bot trade logs indexes: {e}")

    try:
        await db.alert_history.create_index("user_id")
        await db.alert_history.create_index([("user_id", 1), ("created_at", -1)])
        logger.info("Alert history collection indexes created")
    except Exception as e:
        logger.debug(f"Alert history indexes: {e}")

    try:
        await db.crypto_prices.create_index(
            "timestamp",
            expireAfterSeconds=86400
        )
        await db.crypto_prices.create_index([("symbol", 1), ("timestamp", -1)])
        logger.info("Crypto prices collection indexes created (TTL 24h)")
    except Exception as e:
        logger.debug(f"Crypto prices indexes: {e}")

    try:
        await db.fast_movers.create_index(
            "timestamp",
            expireAfterSeconds=86400
        )
        await db.fast_movers.create_index("symbol")
        logger.info("Fast movers collection indexes created (TTL 24h)")
    except Exception as e:
        logger.debug(f"Fast movers indexes: {e}")

    logger.info("Database index creation complete")
