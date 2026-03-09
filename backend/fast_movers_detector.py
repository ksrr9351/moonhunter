"""
Fast Market Movements Detection System
Monitors crypto prices and detects significant pump/dump movements
"""
import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List
from motor.motor_asyncio import AsyncIOMotorClient
from market_provider import MarketProvider
from email_service import email_service
from dump_detection_engine import DumpDetectionEngine

logger = logging.getLogger(__name__)

class FastMoversDetector:
    """Detects fast market movements (pumps and dumps) in cryptocurrency prices"""
    
    # Movement thresholds
    PUMP_THRESHOLD = 1.5  # +1.5% or more
    DUMP_THRESHOLD = -0.5  # -0.5% or more
    
    def __init__(self, db_client: AsyncIOMotorClient, db_name: str, market_provider=None):
        self.db = db_client[db_name]
        self.market_provider = market_provider if market_provider else MarketProvider()
        self.collection_prices = self.db.crypto_prices
        self.collection_movers = self.db.fast_movers
        self.collection_cooldowns = self.db.coin_alert_cooldowns
        self.dump_engine = DumpDetectionEngine(self.db, self.market_provider)
        
    async def initialize(self):
        """Initialize database indexes"""
        await self.collection_prices.create_index([("symbol", 1), ("timestamp", -1)])
        await self.collection_movers.create_index([("timestamp", -1)])
        await self.collection_movers.create_index([("symbol", 1)])
        await self.collection_cooldowns.create_index([("user_id", 1), ("symbol", 1)], unique=True)
        await self.collection_cooldowns.create_index([("last_alert", 1)])
        logger.info(f"Fast movers detector initialized with thresholds: pump={self.PUMP_THRESHOLD:+.1f}%, dump={self.DUMP_THRESHOLD:.1f}%, per-coin cooldowns enabled")
        
    async def fetch_and_store_prices(self) -> List[Dict]:
        """Fetch current crypto prices and store in database"""
        try:
            coins_data = await self.market_provider.get_coins_list(limit=100)
            
            if not coins_data:
                logger.warning("No coin data received from market provider")
                return []
            
            current_time = datetime.now(timezone.utc)
            stored_prices = []
            
            for coin in coins_data:
                price = coin.get('price', 0)
                
                if not price or price == 0:
                    continue
                
                price_doc = {
                    "symbol": coin['symbol'],
                    "name": coin['name'],
                    "price": price,
                    "timestamp": current_time.isoformat(),
                    "market_cap": coin.get('marketCap', 0),
                    "volume_24h": coin.get('volume24h', 0),
                    "logo": coin.get('logo', ''),
                    "change1h": coin.get('change1h', 0),
                    "change24h": coin.get('change24h', 0)
                }
                
                if coin.get('contract_address'):
                    price_doc["contract_address"] = coin['contract_address']
                    price_doc["platform"] = coin.get('platform', '')
                
                result = await self.collection_prices.insert_one(price_doc)
                if result.inserted_id:
                    stored_prices.append(price_doc)
            
            logger.info(f"Stored prices for {len(stored_prices)} coins")
            return stored_prices
            
        except Exception as e:
            logger.error(f"Error fetching/storing prices: {str(e)}")
            return []
    
    async def detect_movements(self) -> List[Dict]:
        """Detect fast market movements using stored price snapshots with real 1h change data from CMC"""
        try:
            movements = []
            current_time = datetime.now(timezone.utc)
            
            recent_prices = await self.collection_prices.find(
                {"timestamp": {"$gte": (current_time - timedelta(minutes=2)).isoformat()}}
            ).sort("timestamp", -1).to_list(500)
            
            if not recent_prices:
                logger.debug("No recent prices to analyze")
                return []
            
            latest_by_symbol = {}
            for price_doc in recent_prices:
                symbol = price_doc.get('symbol')
                if symbol and symbol not in latest_by_symbol:
                    latest_by_symbol[symbol] = price_doc
            
            logger.debug(f"Analyzing {len(latest_by_symbol)} coins for fast movements")
            
            for symbol, coin in latest_by_symbol.items():
                change1h = coin.get('change1h')
                price = coin.get('price', 0)
                
                if not price or price == 0 or change1h is None:
                    continue
                
                if change1h >= self.PUMP_THRESHOLD:
                    movement_type = "pump"
                elif change1h <= self.DUMP_THRESHOLD:
                    movement_type = "dump"
                else:
                    continue
                
                existing = await self.collection_movers.find_one({
                    "symbol": symbol,
                    "timestamp": {"$gte": (current_time - timedelta(minutes=15)).isoformat()}
                })
                
                if existing:
                    existing_change = abs(existing.get('price_change_percent', 0))
                    current_change = abs(change1h)
                    if current_change <= existing_change * 1.2:
                        logger.debug(f"Skipping {symbol}: already detected with similar magnitude")
                        continue
                
                one_hour_ago = current_time - timedelta(hours=1)
                historical = await self.collection_prices.find_one(
                    {"symbol": symbol, "timestamp": {"$lte": one_hour_ago.isoformat()}},
                    sort=[("timestamp", -1)]
                )
                
                movement = {
                    "symbol": symbol,
                    "name": coin.get('name', symbol),
                    "current_price": price,
                    "price_change_percent": round(change1h, 2),
                    "change_24h": round(coin.get('change24h', 0) if coin.get('change24h') else 0, 2),
                    "movement_type": movement_type,
                    "timestamp": current_time.isoformat(),
                    "market_cap": coin.get('market_cap', 0),
                    "volume_24h": coin.get('volume_24h', 0),
                    "logo": coin.get('logo', ''),
                    "detected_at": current_time.isoformat(),
                    "source": "cmc_1h_change"
                }
                
                if coin.get('contract_address'):
                    movement["contract_address"] = coin['contract_address']
                    movement["platform"] = coin.get('platform', '')
                
                if historical and historical.get('price', 0) > 0:
                    movement["previous_price"] = round(historical['price'], 8)
                    movement["previous_price_source"] = "stored_historical"
                
                await self.collection_movers.insert_one(movement.copy())
                movements.append(movement)
                
                if movement_type == "dump":
                    await self._create_dump_opportunity(movement, coin)
                
                logger.info(f"{movement_type.upper()} detected: {symbol} {change1h:+.2f}% (1h)")
            
            if movements:
                logger.info(f"Detected {len(movements)} fast movers this cycle")
            
            return movements
            
        except Exception as e:
            logger.error(f"Error detecting movements: {str(e)}")
            return []
    
    async def _create_dump_opportunity(self, movement: Dict, coin: Dict):
        """Create a dump opportunity with 1-hour active window"""
        try:
            symbol = movement.get("symbol")
            now = datetime.utcnow()
            expires_at = now + timedelta(hours=1)

            existing = await self.db.dump_opportunities.find_one({
                "symbol": symbol,
                "expires_at": {"$gt": now}
            })

            if existing:
                if abs(movement.get("price_change_percent", 0)) > abs(existing.get("dump_percentage", 0)) * 1.2:
                    await self.db.dump_opportunities.update_one(
                        {"symbol": symbol, "expires_at": {"$gt": now}},
                        {"$set": {
                            "current_price": movement.get("current_price", 0),
                            "dump_percentage": movement.get("price_change_percent", 0),
                            "detected_at": now,
                            "expires_at": expires_at,
                            "market_cap": coin.get("market_cap", coin.get("marketCap", 0)),
                            "volume_24h": coin.get("volume_24h", coin.get("volume24h", 0)),
                        }}
                    )
                    logger.info(f"Updated dump opportunity: {symbol} {movement.get('price_change_percent', 0):+.2f}%")
                else:
                    logger.info(f"Dump opportunity exists for {symbol}, skipping (existing: {existing.get('dump_percentage')}%, new: {movement.get('price_change_percent')}%)")
                return

            volume = coin.get("volume_24h", coin.get("volume24h", 0))
            market_cap = coin.get("market_cap", coin.get("marketCap", 0))
            dump_pct = abs(movement.get("price_change_percent", 0))

            if dump_pct >= 10:
                risk_score = 0.8
                risk_level = "High"
            elif dump_pct >= 5:
                risk_score = 0.5
                risk_level = "Moderate"
            else:
                risk_score = 0.3
                risk_level = "Low"

            if dump_pct >= 5:
                recommendation = "Strong buy signal — significant dump detected on quality coin"
            elif dump_pct >= 3:
                recommendation = "Moderate buy signal — notable price drop, watch for support"
            else:
                recommendation = "Minor dip — small buying opportunity"

            from chain_registry import get_all_chain_ids
            supported_chains = get_all_chain_ids()

            opportunity = {
                "symbol": symbol,
                "name": movement.get("name", symbol),
                "current_price": movement.get("current_price", 0),
                "dump_percentage": movement.get("price_change_percent", 0),
                "detected_at": now,
                "expires_at": expires_at,
                "market_cap": market_cap,
                "volume_24h": volume,
                "logo": movement.get("logo", ""),
                "risk_score": risk_score,
                "risk_level": risk_level,
                "ai_recommendation": recommendation,
                "reason": f"{symbol} dumped {dump_pct:.1f}% in {movement.get('source', 'cmc_1h_change').replace('cmc_1h_change', '1 hour').replace('dump_engine_1h', '1 hour').replace('dump_engine_24h', '24 hours')}",
                "supported_chains": supported_chains,
                "change_24h": movement.get("change_24h", 0),
                "source": movement.get("source", "cmc_1h_change")
            }
            
            contract_addr = movement.get("contract_address") or coin.get("contract_address", "")
            if contract_addr:
                opportunity["contract_address"] = contract_addr
                opportunity["platform"] = movement.get("platform") or coin.get("platform", "")

            await self.db.dump_opportunities.insert_one(opportunity)
            logger.info(f"Created dump opportunity: {symbol} {movement.get('price_change_percent', 0):+.2f}% (expires in 1h)")

        except Exception as e:
            logger.error(f"Error creating dump opportunity: {e}")

    async def get_recent_movers(self, limit: int = 20) -> List[Dict]:
        """Get recent fast movers from database, deduplicated by symbol (most recent per coin)"""
        try:
            # Get movers from last 24 hours
            one_day_ago = datetime.now(timezone.utc) - timedelta(hours=24)
            
            # Use aggregation to get only the most recent movement per symbol
            pipeline = [
                {"$match": {"timestamp": {"$gte": one_day_ago.isoformat()}}},
                {"$sort": {"timestamp": -1}},
                {"$group": {
                    "_id": "$symbol",
                    "symbol": {"$first": "$symbol"},
                    "name": {"$first": "$name"},
                    "price": {"$first": "$current_price"},
                    "current_price": {"$first": "$current_price"},
                    "previous_price": {"$first": "$previous_price"},
                    "price_change_percent": {"$first": "$price_change_percent"},
                    "change_24h": {"$first": "$change_24h"},
                    "movement_type": {"$first": "$movement_type"},
                    "timestamp": {"$first": "$timestamp"},
                    "volume_24h": {"$first": "$volume_24h"},
                    "market_cap": {"$first": "$market_cap"},
                    "logo": {"$first": "$logo"},
                    "contract_address": {"$first": "$contract_address"},
                    "platform": {"$first": "$platform"}
                }},
                {"$project": {"_id": 0}},
                {"$sort": {"timestamp": -1}},
                {"$limit": limit}
            ]
            
            movers = await self.collection_movers.aggregate(pipeline).to_list(limit)
            
            return movers
            
        except Exception as e:
            logger.error(f"Error fetching recent movers: {str(e)}")
            return []
    
    async def trigger_alerts_for_movement(self, movement: Dict):
        """Trigger email alerts for users who have configured alerts.
        Uses per-coin cooldowns so multiple coins can trigger alerts simultaneously.
        """
        try:
            symbol = movement.get('symbol')
            change_percent = abs(movement.get('price_change_percent', 0))
            current_time = datetime.now(timezone.utc)
            cooldown_seconds = 15 * 60  # 15 minutes per coin
            
            # Get all users with email alerts enabled
            alert_settings = await self.db.alert_settings.find({
                "email_alerts": True,
                "email": {"$nin": [None, ""]}
            }).to_list(None)
            
            logger.info(f"Checking alerts for {symbol} {change_percent:+.2f}% movement")
            logger.info(f"   Found {len(alert_settings)} users with alerts enabled")
            
            alerts_sent = 0
            skipped_threshold = 0
            skipped_cooldown = 0
            
            for settings in alert_settings:
                try:
                    user_id = settings.get('user_id')
                    user_email = settings.get('email')
                    user_threshold = settings.get('threshold', 5)
                    
                    # Check if movement meets user's threshold
                    if change_percent < user_threshold:
                        skipped_threshold += 1
                        logger.debug(f"   Skipping {user_email} for {symbol}: {change_percent:.2f}% < {user_threshold}% threshold")
                        continue
                    
                    # Per-coin cooldown check: 15 minutes per user per coin
                    coin_cooldown = await self.collection_cooldowns.find_one({
                        "user_id": user_id,
                        "symbol": symbol
                    })
                    
                    if coin_cooldown:
                        last_alert = coin_cooldown.get('last_alert')
                        if last_alert:
                            try:
                                last_alert_time = datetime.fromisoformat(last_alert.replace('Z', '+00:00'))
                                time_since_last = (current_time - last_alert_time).total_seconds()
                                
                                if time_since_last < cooldown_seconds:
                                    remaining = int((cooldown_seconds - time_since_last) / 60)
                                    skipped_cooldown += 1
                                    logger.debug(f"   Skipping {user_email} for {symbol}: per-coin cooldown active ({remaining}m remaining)")
                                    continue
                            except (ValueError, AttributeError) as e:
                                logger.warning(f"Failed to parse last_alert timestamp for {symbol}: {e}")
                    
                    # Send email alert
                    logger.info(f"   📤 Sending alert to {user_email} for {symbol}...")
                    success = email_service.send_alert_email(
                        to_email=user_email,
                        movement=movement,
                        user_threshold=user_threshold
                    )
                    
                    if success:
                        alerts_sent += 1
                        
                        # Update per-coin cooldown (upsert)
                        await self.collection_cooldowns.update_one(
                            {"user_id": user_id, "symbol": symbol},
                            {"$set": {
                                "last_alert": current_time.isoformat(),
                                "coin_name": movement.get('name', symbol),
                                "last_change_percent": change_percent
                            }},
                            upsert=True
                        )
                        
                        # Also update alert_settings.last_alert for UI compatibility
                        await self.db.alert_settings.update_one(
                            {"user_id": user_id},
                            {"$set": {"last_alert": current_time.isoformat()}}
                        )
                        
                        # Store in alert history
                        alert_history = {
                            "user_id": user_id,
                            "email": user_email,
                            "coin": symbol,
                            "change_percent": movement.get('price_change_percent'),
                            "movement_type": movement.get('movement_type'),
                            "current_price": movement.get('current_price'),
                            "threshold": user_threshold,
                            "timestamp": current_time.isoformat(),
                            "email_sent": True
                        }
                        await self.db.alert_history.insert_one(alert_history)
                        
                        logger.info(f"   [OK] Alert sent to {user_email} for {symbol}")
                    else:
                        logger.error(f"   [FAIL] Failed to send alert to {user_email} for {symbol}")
                        
                except Exception as e:
                    logger.error(f"   Error sending alert to user for {symbol}: {str(e)}")
                    continue
            
            additional_emails_str = os.environ.get('ADDITIONAL_ALERT_EMAILS', '')
            additional_emails = [e.strip() for e in additional_emails_str.split(',') if e.strip()]
            for extra_email in additional_emails:
                try:
                    extra_cooldown = await self.collection_cooldowns.find_one({
                        "user_id": f"additional_{extra_email}",
                        "symbol": symbol
                    })
                    if extra_cooldown:
                        last_alert = extra_cooldown.get('last_alert')
                        if last_alert:
                            last_alert_time = datetime.fromisoformat(last_alert.replace('Z', '+00:00'))
                            if (current_time - last_alert_time).total_seconds() < cooldown_seconds:
                                continue
                    success = email_service.send_alert_email(
                        to_email=extra_email,
                        movement=movement,
                        user_threshold=0
                    )
                    if success:
                        alerts_sent += 1
                        await self.collection_cooldowns.update_one(
                            {"user_id": f"additional_{extra_email}", "symbol": symbol},
                            {"$set": {"last_alert": current_time.isoformat()}},
                            upsert=True
                        )
                        logger.info(f"   [OK] Alert sent to additional recipient {extra_email} for {symbol}")
                except Exception as e:
                    logger.error(f"   Error sending to additional recipient {extra_email}: {str(e)}")

            if alerts_sent > 0:
                logger.info(f"Successfully sent {alerts_sent} alert(s) for {symbol}")
            else:
                reason_parts = []
                if skipped_threshold > 0:
                    reason_parts.append(f"{skipped_threshold} below threshold")
                if skipped_cooldown > 0:
                    reason_parts.append(f"{skipped_cooldown} in cooldown")
                reason = ", ".join(reason_parts) if reason_parts else "no eligible users"
                logger.info(f"No alerts sent for {symbol} ({reason})")
            
            return alerts_sent
            
        except Exception as e:
            logger.error(f"Error triggering alerts for {movement.get('symbol', 'unknown')}: {str(e)}")
            return 0

    async def cleanup_old_data(self):
        """Clean up old price, movement, and cooldown data (keep last 24 hours)"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            price_result = await self.collection_prices.delete_many(
                {"timestamp": {"$lt": cutoff_time.isoformat()}}
            )
            
            mover_result = await self.collection_movers.delete_many(
                {"timestamp": {"$lt": cutoff_time.isoformat()}}
            )
            
            cooldown_result = await self.collection_cooldowns.delete_many(
                {"last_alert": {"$lt": cutoff_time.isoformat()}}
            )
            
            total_deleted = price_result.deleted_count + mover_result.deleted_count + cooldown_result.deleted_count
            if total_deleted > 0:
                logger.info(f"🧹 Cleaned up {price_result.deleted_count} old prices, "
                           f"{mover_result.deleted_count} old movements, "
                           f"{cooldown_result.deleted_count} old cooldowns")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {str(e)}")
    
    async def detect_dump_engine_opportunities(self):
        """Run the DumpDetectionEngine to find opportunities from 1h AND 24h windows (≥5% dumps)"""
        try:
            coins = await self.market_provider.get_coins_list(100)
            if not coins:
                return 0

            analysis = await self.dump_engine.analyze_market(coins)
            dump_opps = analysis.get("dump_opportunities", [])

            if not dump_opps:
                return 0

            created = 0
            for opp in dump_opps:
                symbol = opp.get("symbol", "")
                dump_magnitude = opp.get("dump_magnitude", 0)
                dump_window = opp.get("dump_window", "24h")
                change_key = "change_1h" if dump_window == "1h" else "change_24h"
                change_value = opp.get(change_key, 0)

                movement = {
                    "symbol": symbol,
                    "name": opp.get("name", symbol),
                    "current_price": opp.get("price_usdt", 0),
                    "price_change_percent": round(change_value, 2) if change_value else round(-dump_magnitude, 2),
                    "change_24h": round(opp.get("change_24h", 0), 2),
                    "market_cap": opp.get("market_cap", 0),
                    "volume_24h": opp.get("volume_24h", 0),
                    "logo": opp.get("logo", ""),
                    "source": f"dump_engine_{dump_window}",
                }
                
                if opp.get("contract_address"):
                    movement["contract_address"] = opp["contract_address"]
                    movement["platform"] = opp.get("platform", "")

                coin_data = {
                    "marketCap": opp.get("market_cap", 0),
                    "volume24h": opp.get("volume_24h", 0),
                    "market_cap": opp.get("market_cap", 0),
                    "volume_24h": opp.get("volume_24h", 0),
                }

                await self._create_dump_opportunity(movement, coin_data)
                created += 1

            if created > 0:
                logger.info(f"DumpDetectionEngine: processed {created} dump opportunities (from {len(dump_opps)} signals)")

            return created

        except Exception as e:
            logger.error(f"Error in dump engine integration: {e}")
            return 0

    async def run_detection_cycle(self):
        """Run one complete detection cycle"""
        logger.info("Starting fast movers detection cycle...")
        
        await self.fetch_and_store_prices()
        
        movements = await self.detect_movements()
        
        if movements:
            logger.info(f"Detected {len(movements)} fast movements!")
            
            for movement in movements:
                await self.trigger_alerts_for_movement(movement)
        else:
            logger.debug("No significant movements detected this cycle")
        
        engine_count = await self.detect_dump_engine_opportunities()
        if engine_count > 0:
            logger.info(f"DumpDetectionEngine added {engine_count} opportunities this cycle")
        
        return movements


# Background task runner
async def run_fast_movers_background_task(detector: FastMoversDetector):
    """Background task that runs every 60 seconds"""
    logger.info("Fast movers background task started")
    
    # Initialize detector with retry logic for MongoDB connection issues
    initialized = False
    for attempt in range(3):
        try:
            await detector.initialize()
            initialized = True
            break
        except Exception as e:
            logger.warning(f"Fast movers initialization attempt {attempt + 1}/3 failed: {str(e)[:100]}")
            await asyncio.sleep(5)
    
    if not initialized:
        logger.error("Fast movers detector failed to initialize after 3 attempts. Background task disabled.")
        logger.error("   This is usually caused by MongoDB connection issues. The app will continue without fast movers detection.")
        return
    
    # Run cleanup once at start
    try:
        await detector.cleanup_old_data()
    except Exception as e:
        logger.warning(f"Initial cleanup failed: {str(e)[:100]}")
    
    cycle_count = 0
    while True:
        try:
            cycle_count += 1
            
            # Run detection cycle
            await detector.run_detection_cycle()
            
            # Run cleanup every 60 cycles (1 hour)
            if cycle_count % 60 == 0:
                await detector.cleanup_old_data()
            
            # Wait 60 seconds before next cycle
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Error in background task: {str(e)}")
            await asyncio.sleep(60)
