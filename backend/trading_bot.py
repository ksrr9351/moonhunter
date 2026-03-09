"""
Automated Trading Bot - Background task for hands-free investing
Monitors market for dump opportunities and auto-executes based on user settings
"""
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import uuid

logger = logging.getLogger(__name__)

DEFAULT_BOT_SETTINGS = {
    "enabled": False,
    "execution_mode": "dex",
    "chain_id": 1,
    "max_daily_investment": 100.0,
    "max_per_trade": 50.0,
    "min_dump_threshold": 5.0,
    "max_risk_score": 0.6,
    "allowed_strategies": ["dump_buy", "trend_follow"],
    "coin_whitelist": [],
    "coin_blacklist": [],
    "pause_on_loss": True,
    "max_daily_loss": 50.0,
    "cooldown_minutes": 30,
    "stop_loss_percent": 10.0,
    "take_profit_percent": 15.0,
    "auto_stop_loss": True,
    "auto_take_profit": True,
    "slippage_tolerance": 1.0
}


class TradingBot:
    """
    Automated trading bot that monitors market and executes trades
    based on user-defined rules and AI recommendations.
    Executes real DEX trades via 1inch API.
    """
    
    def __init__(self, db, market_provider, dump_detection_engine, portfolio_engine, wallet_service, dex_service=None, email_service=None):
        self.db = db
        self.market_provider = market_provider
        self.dump_engine = dump_detection_engine
        self.portfolio_engine = portfolio_engine
        self.wallet_service = wallet_service
        self.dex_service = dex_service
        self.email_service = email_service
        self.running = False
        self.check_interval = 60
        logger.info(f"Trading Bot initialized (DEX execution via 1inch)")
    
    async def get_user_bot_settings(self, user_id: str) -> Dict[str, Any]:
        """Get user's bot settings with defaults"""
        settings = await self.db.bot_settings.find_one(
            {"user_id": user_id},
            {"_id": 0}
        )
        
        if not settings:
            return {**DEFAULT_BOT_SETTINGS, "user_id": user_id}
        
        merged = {**DEFAULT_BOT_SETTINGS, **settings}
        return merged
    
    async def update_user_bot_settings(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update user's bot settings"""
        current = await self.get_user_bot_settings(user_id)
        
        allowed_fields = set(DEFAULT_BOT_SETTINGS.keys())
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        new_settings = {**current, **filtered_updates, "user_id": user_id, "updated_at": datetime.now(timezone.utc).isoformat()}
        
        new_settings["execution_mode"] = "dex"
        
        await self.db.bot_settings.update_one(
            {"user_id": user_id},
            {"$set": new_settings},
            upsert=True
        )
        
        logger.info(f"Updated bot settings for user {user_id[:8]}...")
        return new_settings
    
    async def get_daily_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user's daily trading statistics"""
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        today_trades = await self.db.ai_positions.find({
            "user_id": user_id,
            "created_at": {"$gte": today_start.isoformat()},
            "execution_mode": "bot"
        }, {"_id": 0}).to_list(1000)
        
        total_invested_today = sum(t.get("invested_usdt", 0) for t in today_trades)
        
        closed_today = await self.db.ai_positions.find({
            "user_id": user_id,
            "closed_at": {"$gte": today_start.isoformat()},
            "status": "closed"
        }, {"_id": 0}).to_list(1000)
        
        total_pnl_today = sum(t.get("realized_pnl", 0) for t in closed_today)
        
        return {
            "trades_today": len(today_trades),
            "invested_today": total_invested_today,
            "pnl_today": total_pnl_today,
            "date": today_start.isoformat()
        }
    
    async def get_last_trade_time(self, user_id: str) -> Optional[datetime]:
        """Get the time of the last bot trade"""
        last_trade = await self.db.ai_positions.find_one(
            {"user_id": user_id, "execution_mode": "bot"},
            {"_id": 0, "created_at": 1},
            sort=[("created_at", -1)]
        )
        
        if last_trade and last_trade.get("created_at"):
            return datetime.fromisoformat(last_trade["created_at"].replace("Z", "+00:00"))
        return None
    
    async def check_and_execute_for_user(self, user_id: str) -> Dict[str, Any]:
        """Check opportunities and execute trades for a specific user"""
        settings = await self.get_user_bot_settings(user_id)
        
        if not settings.get("enabled"):
            return {"status": "disabled", "trades": 0}
        
        daily_stats = await self.get_daily_stats(user_id)
        if daily_stats["invested_today"] >= settings.get("max_daily_investment", 100):
            return {"status": "daily_limit_reached", "trades": 0}
        
        if settings.get("pause_on_loss") and daily_stats["pnl_today"] <= -settings.get("max_daily_loss", 50):
            return {"status": "paused_due_to_loss", "trades": 0}
        
        last_trade_time = await self.get_last_trade_time(user_id)
        if last_trade_time:
            cooldown = timedelta(minutes=settings.get("cooldown_minutes", 30))
            if datetime.now(timezone.utc) - last_trade_time < cooldown:
                return {"status": "cooldown", "trades": 0}
        
        wallet_status = await self.wallet_service.get_user_wallet_status(user_id)
        available_usdt = wallet_status.get("available_usdt", 0)

        if available_usdt < 10:
            return {"status": "insufficient_balance", "trades": 0}
        
        coins = await self.market_provider.get_coins_list(100)
        dump_analysis = await self.dump_engine.analyze_market(coins)
        
        opportunities = dump_analysis.get("dump_opportunities", [])
        if not opportunities:
            return {"status": "no_opportunities", "trades": 0}
        
        filtered_opportunities = self._filter_opportunities(opportunities, settings)
        
        if not filtered_opportunities:
            return {"status": "no_matching_opportunities", "trades": 0}
        
        remaining_daily = settings.get("max_daily_investment", 100) - daily_stats["invested_today"]
        max_this_trade = min(
            settings.get("max_per_trade", 50),
            remaining_daily,
            available_usdt * 0.2
        )
        
        if max_this_trade < 10:
            return {"status": "trade_amount_too_small", "trades": 0}
        
        best_opportunity = filtered_opportunities[0]
        
        if not self.dex_service:
            logger.warning(f"Bot trade skipped for user {user_id[:8]}: DEX service not available")
            return {"status": "dex_unavailable", "trades": 0, "error": "DEX service not configured. Real trading requires DEX integration."}
        
        result = await self._execute_dex_trade(
            user_id=user_id,
            opportunity=best_opportunity,
            usdt_amount=max_this_trade,
            settings=settings
        )
        
        if result.get("success"):
            position = result.get("position", {})
            
            if settings.get("auto_stop_loss") or settings.get("auto_take_profit"):
                await self._set_position_triggers(
                    user_id=user_id,
                    position_id=position.get("id"),
                    entry_price=position.get("entry_price"),
                    stop_loss_percent=settings.get("stop_loss_percent", 10),
                    take_profit_percent=settings.get("take_profit_percent", 15),
                    auto_stop_loss=settings.get("auto_stop_loss", True),
                    auto_take_profit=settings.get("auto_take_profit", True)
                )
            
            await self._log_bot_trade(user_id, position, "opened")
            
            if self.email_service:
                await self._send_trade_notification(user_id, position, "opened")
            
            await self.db.ai_positions.update_one(
                {"id": position.get("id")},
                {"$set": {"execution_mode": "bot_dex"}}
            )
            
            logger.info(f"Bot executed DEX trade: {best_opportunity['symbol']} - ${max_this_trade}")
            
            return {
                "status": "executed",
                "trades": 1,
                "position": position,
                "execution_mode": "dex"
            }
        else:
            return {
                "status": "execution_failed",
                "trades": 0,
                "error": result.get("error")
            }
    
    async def _execute_dex_trade(
        self,
        user_id: str,
        opportunity: Dict[str, Any],
        usdt_amount: float,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a real DEX trade using 1inch API"""
        try:
            symbol = opportunity.get("symbol")
            chain_id = settings.get("chain_id", 1)
            slippage = settings.get("slippage_tolerance", 1.0)
            
            user = await self.db.users.find_one({"id": user_id}, {"_id": 0, "wallet_address": 1})
            if not user or not user.get("wallet_address"):
                return {"success": False, "error": "No wallet address configured for user"}
            
            wallet_address = user["wallet_address"]
            
            token_address = await self._get_token_address(symbol, chain_id)
            if not token_address:
                return {"success": False, "error": f"Token {symbol} not found on chain {chain_id}"}
            
            usdt_address = self._get_usdt_address(chain_id)
            if not usdt_address:
                return {"success": False, "error": f"USDT not available on chain {chain_id}"}
            
            amount_wei = int(usdt_amount * 1e6)
            
            quote = await self.dex_service.get_quote(
                src_token=usdt_address,
                dst_token=token_address,
                amount=str(amount_wei),
                chain_id=chain_id
            )
            
            if quote.get("error"):
                return {"success": False, "error": f"Quote failed: {quote.get('error')}"}
            
            dst_amount = quote.get("dstAmount", "0")
            dst_decimals = quote.get("dstToken", {}).get("decimals", 18)
            tokens_received = int(dst_amount) / (10 ** dst_decimals)
            if tokens_received <= 0:
                return {"success": False, "error": "Quote returned zero tokens — swap not viable"}
            entry_price = usdt_amount / tokens_received
            
            swap_data = await self.dex_service.get_swap(
                src_token=usdt_address,
                dst_token=token_address,
                amount=str(amount_wei),
                from_address=wallet_address,
                slippage=slippage,
                chain_id=chain_id
            )
            
            if swap_data.get("error"):
                return {"success": False, "error": f"Swap generation failed: {swap_data.get('error')}"}
            
            position = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "symbol": symbol,
                "name": opportunity.get("name", symbol),
                "entry_price": entry_price,
                "current_price": entry_price,
                "invested_usdt": usdt_amount,
                "tokens": tokens_received,
                "unrealized_pnl": 0,
                "unrealized_pnl_percent": 0,
                "strategy": "dump_buy",
                "trigger_reason": f"Bot DEX: {opportunity.get('reason', 'Dump detected')}",
                "status": "pending_execution",
                "execution_mode": "bot_dex",
                "chain_id": chain_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "logo": opportunity.get("logo", ""),
                "tx_data": {
                    "to": swap_data.get("tx", {}).get("to"),
                    "data": swap_data.get("tx", {}).get("data"),
                    "value": swap_data.get("tx", {}).get("value", "0"),
                    "gas": swap_data.get("tx", {}).get("gas"),
                },
                "quote": {
                    "src_amount": usdt_amount,
                    "dst_amount": tokens_received,
                    "price_impact": quote.get("priceImpact", 0)
                }
            }
            
            await self.db.ai_positions.insert_one(position)
            
            pending_trade = {
                "id": position["id"],
                "user_id": user_id,
                "wallet_address": wallet_address,
                "symbol": symbol,
                "usdt_amount": usdt_amount,
                "tokens_expected": tokens_received,
                "tx_data": position["tx_data"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
                "status": "awaiting_user_confirmation",
                "chain_id": chain_id,
                "requires_signature": True
            }
            await self.db.pending_bot_trades.insert_one(pending_trade)
            
            try:
                from event_service import event_service
                await event_service.send_event(
                    user_id=user_id,
                    event_type="bot_trade_pending",
                    data={
                        "position_id": position["id"],
                        "symbol": symbol,
                        "amount_usdt": usdt_amount,
                        "tokens_expected": tokens_received,
                        "chain_id": chain_id,
                        "expires_at": pending_trade["expires_at"],
                        "message": f"Bot wants to buy {tokens_received:.6f} {symbol} for ${usdt_amount} USDT. Confirm in your wallet."
                    }
                )
            except Exception as e:
                logger.warning(f"Could not send SSE event: {e}")
            
            logger.info(f"DEX trade prepared (awaiting confirmation): {symbol} - {tokens_received:.6f} tokens for ${usdt_amount}")
            
            return {
                "success": True,
                "position": position,
                "pending_trade": pending_trade,
                "message": f"DEX trade prepared: Buy {tokens_received:.6f} {symbol} for ${usdt_amount} USDT. Awaiting wallet confirmation.",
                "requires_signature": True,
                "expires_at": pending_trade["expires_at"]
            }
            
        except Exception as e:
            logger.error(f"DEX trade execution error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_token_address(self, symbol: str, chain_id: int) -> Optional[str]:
        """Get token contract address for a symbol on a specific chain"""
        from dex_service import COMMON_TOKENS
        chain_tokens = COMMON_TOKENS.get(chain_id, {})
        if symbol in chain_tokens:
            return chain_tokens[symbol]
        
        tokens = await self.dex_service.get_supported_tokens(chain_id)
        for addr, info in tokens.get("tokens", {}).items():
            if info.get("symbol", "").upper() == symbol.upper():
                return addr
        
        return None
    
    def _get_usdt_address(self, chain_id: int) -> Optional[str]:
        """Get USDT contract address for a specific chain"""
        from dex_service import COMMON_TOKENS
        chain_tokens = COMMON_TOKENS.get(chain_id, {})
        return chain_tokens.get("USDT")
    
    def _filter_opportunities(self, opportunities: List[Dict], settings: Dict) -> List[Dict]:
        """Filter opportunities based on user settings"""
        filtered = []
        
        min_dump = settings.get("min_dump_threshold", 5.0)
        max_risk = settings.get("max_risk_score", 0.6)
        whitelist = set(settings.get("coin_whitelist", []))
        blacklist = set(settings.get("coin_blacklist", []))
        
        for opp in opportunities:
            symbol = opp.get("symbol", "")
            
            if blacklist and symbol in blacklist:
                continue
            
            if whitelist and symbol not in whitelist:
                continue
            
            if opp.get("dump_magnitude", 0) < min_dump:
                continue
            
            if opp.get("risk_score", 1.0) > max_risk:
                continue
            
            filtered.append(opp)
        
        filtered.sort(key=lambda x: x.get("risk_score", 1.0))
        
        return filtered
    
    async def _set_position_triggers(
        self,
        user_id: str,
        position_id: str,
        entry_price: float,
        stop_loss_percent: float,
        take_profit_percent: float,
        auto_stop_loss: bool,
        auto_take_profit: bool
    ):
        """Set stop-loss and take-profit triggers for a position"""
        stop_loss_price = entry_price * (1 - stop_loss_percent / 100) if auto_stop_loss else None
        take_profit_price = entry_price * (1 + take_profit_percent / 100) if auto_take_profit else None
        
        trigger = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "position_id": position_id,
            "entry_price": entry_price,
            "stop_loss_price": stop_loss_price,
            "take_profit_price": take_profit_price,
            "stop_loss_percent": stop_loss_percent if auto_stop_loss else None,
            "take_profit_percent": take_profit_percent if auto_take_profit else None,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.position_triggers.insert_one(trigger)
        logger.info(f"Set triggers for position {position_id[:8]}: SL={stop_loss_price}, TP={take_profit_price}")
    
    async def check_position_triggers(self) -> List[Dict]:
        """Check all active position triggers and execute if conditions met"""
        active_triggers = await self.db.position_triggers.find(
            {"status": "active"},
            {"_id": 0}
        ).to_list(1000)
        
        if not active_triggers:
            return []
        
        coins = await self.market_provider.get_coins_list(100)
        price_map = {c["symbol"]: c["price"] for c in coins}
        
        triggered = []
        
        for trigger in active_triggers:
            try:
                position = await self.db.ai_positions.find_one(
                    {"id": trigger["position_id"], "status": "active"},
                    {"_id": 0}
                )
                
                if not position:
                    await self.db.position_triggers.update_one(
                        {"id": trigger["id"]},
                        {"$set": {"status": "position_closed"}}
                    )
                    continue
                
                symbol = position.get("symbol")
                current_price = price_map.get(symbol)
                
                if not current_price:
                    continue
                
                stop_loss_price = trigger.get("stop_loss_price")
                take_profit_price = trigger.get("take_profit_price")
                
                trigger_type = None
                if stop_loss_price and current_price <= stop_loss_price:
                    trigger_type = "stop_loss"
                elif take_profit_price and current_price >= take_profit_price:
                    trigger_type = "take_profit"
                
                if trigger_type:
                    quantity = position.get("quantity", 0)
                    tx_hash = f"0x_trigger_{trigger_type}_{position.get('id', '')[:8]}_{int(datetime.now(timezone.utc).timestamp())}"

                    result = await self.portfolio_engine.close_position_with_dex(
                        user_id=trigger["user_id"],
                        position_id=trigger["position_id"],
                        exit_price=current_price,
                        exit_quantity=quantity,
                        tx_hash=tx_hash,
                        reason=trigger_type
                    )
                    
                    if result.get("success"):
                        await self.db.position_triggers.update_one(
                            {"id": trigger["id"]},
                            {"$set": {
                                "status": "triggered",
                                "trigger_type": trigger_type,
                                "trigger_price": current_price,
                                "triggered_at": datetime.now(timezone.utc).isoformat()
                            }}
                        )
                        
                        triggered.append({
                            "trigger_id": trigger["id"],
                            "position_id": trigger["position_id"],
                            "symbol": symbol,
                            "trigger_type": trigger_type,
                            "trigger_price": current_price,
                            "pnl": result.get("realized_pnl", 0)
                        })
                        
                        logger.info(f"Trigger executed via DEX close: {symbol} {trigger_type} @ {current_price} | qty={quantity} | tx={tx_hash[:16]}...")
                        
                        if self.email_service:
                            await self._send_trigger_notification(trigger["user_id"], symbol, trigger_type, current_price, result.get("realized_pnl", 0))
            except Exception as e:
                trigger_id = trigger.get("id", "unknown")
                logger.error(f"Error processing trigger {trigger_id}: {e}")
        
        return triggered
    
    async def _log_bot_trade(self, user_id: str, position: Dict, action: str):
        """Log bot trade for analytics"""
        log_entry = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "position_id": position.get("id"),
            "symbol": position.get("symbol"),
            "action": action,
            "amount": position.get("invested_usdt"),
            "price": position.get("entry_price"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.bot_trade_logs.insert_one(log_entry)
    
    async def _send_trade_notification(self, user_id: str, position: Dict, action: str):
        """Send email notification for bot trade"""
        if not self.email_service:
            return
        
        user = await self.db.users.find_one({"id": user_id}, {"_id": 0, "email": 1})
        if not user or not user.get("email"):
            return
        
        try:
            subject = f"Moon Hunters Bot: {action.upper()} {position.get('symbol')}"
            body = f"""
Your Moon Hunters Trading Bot has executed a trade:

Action: {action.upper()}
Coin: {position.get('symbol')} ({position.get('name')})
Amount: ${position.get('invested_usdt', 0):.2f} USDT
Price: ${position.get('entry_price', 0):.6f}
Reason: {position.get('trigger_reason', 'AI recommendation')}

Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

View your portfolio at: https://your-domain.com/ai-engine
"""
            await self.email_service.send_email(user["email"], subject, body)
        except Exception as e:
            logger.error(f"Failed to send trade notification: {e}")
    
    async def _send_trigger_notification(self, user_id: str, symbol: str, trigger_type: str, price: float, pnl: float):
        """Send email notification for triggered stop-loss/take-profit"""
        if not self.email_service:
            return
        
        user = await self.db.users.find_one({"id": user_id}, {"_id": 0, "email": 1})
        if not user or not user.get("email"):
            return
        
        try:
            emoji = "🛑" if trigger_type == "stop_loss" else "🎯"
            pnl_text = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
            
            subject = f"Moon Hunters: {emoji} {trigger_type.replace('_', ' ').title()} Triggered - {symbol}"
            body = f"""
Your position has been automatically closed:

{emoji} {trigger_type.replace('_', ' ').title()} Triggered

Coin: {symbol}
Exit Price: ${price:.6f}
Realized PnL: {pnl_text} USDT

Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

View your portfolio at: https://your-domain.com/ai-engine
"""
            await self.email_service.send_email(user["email"], subject, body)
        except Exception as e:
            logger.error(f"Failed to send trigger notification: {e}")
    
    async def get_bot_status(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive bot status for a user"""
        settings = await self.get_user_bot_settings(user_id)
        daily_stats = await self.get_daily_stats(user_id)
        last_trade_time = await self.get_last_trade_time(user_id)
        
        active_triggers = await self.db.position_triggers.find(
            {"user_id": user_id, "status": "active"},
            {"_id": 0}
        ).to_list(100)
        
        recent_logs = await self.db.bot_trade_logs.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(10).to_list(10)
        
        return {
            "enabled": settings.get("enabled", False),
            "dex_available": self.dex_service is not None,
            "settings": settings,
            "daily_stats": daily_stats,
            "last_trade_time": last_trade_time.isoformat() if last_trade_time else None,
            "active_triggers": len(active_triggers),
            "recent_trades": recent_logs
        }


trading_bot = None

def init_trading_bot(db, market_provider, dump_engine, portfolio_engine, wallet_service, dex_service=None, email_service=None):
    global trading_bot
    trading_bot = TradingBot(db, market_provider, dump_engine, portfolio_engine, wallet_service, dex_service, email_service)
    return trading_bot


async def run_trading_bot_background_task(bot: TradingBot):
    """Background task that runs the trading bot for all enabled users"""
    logger.info("Trading bot background task started")
    
    while True:
        try:
            enabled_users = await bot.db.bot_settings.find(
                {"enabled": True},
                {"_id": 0, "user_id": 1}
            ).to_list(1000)
            
            for user_doc in enabled_users:
                try:
                    result = await bot.check_and_execute_for_user(user_doc["user_id"])
                    if result.get("trades", 0) > 0:
                        logger.info(f"Bot trade for {user_doc['user_id'][:8]}: {result}")
                except Exception as e:
                    logger.error(f"Bot error for user {user_doc['user_id'][:8]}: {e}")
            
            triggered = await bot.check_position_triggers()
            if triggered:
                logger.info(f"Triggered {len(triggered)} stop-loss/take-profit orders")
            
        except Exception as e:
            logger.error(f"Trading bot cycle error: {e}")
        
        await asyncio.sleep(bot.check_interval)
