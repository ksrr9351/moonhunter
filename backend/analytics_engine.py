"""
Analytics Engine - Historical performance tracking and statistics
Provides insights on trading performance, win rates, and returns
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from collections import defaultdict

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """
    Provides historical analytics and performance metrics for trading activity
    """
    
    def __init__(self, db):
        self.db = db
        logger.info("Analytics Engine initialized")
    
    async def get_performance_summary(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive performance summary for a user within specified period"""
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        all_positions = await self.db.ai_positions.find(
            {"user_id": user_id, "created_at": {"$gte": start_date}},
            {"_id": 0}
        ).to_list(10000)
        
        closed_positions = await self.db.ai_positions.find(
            {"user_id": user_id, "status": "closed", "closed_at": {"$gte": start_date}},
            {"_id": 0}
        ).to_list(10000)
        
        active_positions = await self.db.ai_positions.find(
            {"user_id": user_id, "status": "active"},
            {"_id": 0}
        ).to_list(1000)
        
        total_invested = sum(p.get("invested_usdt", 0) for p in all_positions)
        realized_pnl = sum(p.get("realized_pnl", 0) for p in closed_positions)
        unrealized_pnl = sum(p.get("unrealized_pnl", 0) for p in active_positions)
        
        winning_trades = [p for p in closed_positions if p.get("realized_pnl", 0) > 0]
        losing_trades = [p for p in closed_positions if p.get("realized_pnl", 0) < 0]
        breakeven_trades = [p for p in closed_positions if p.get("realized_pnl", 0) == 0]
        
        win_rate = (len(winning_trades) / len(closed_positions) * 100) if closed_positions else 0
        
        avg_win = sum(p.get("realized_pnl", 0) for p in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(p.get("realized_pnl", 0) for p in losing_trades) / len(losing_trades) if losing_trades else 0
        
        best_trade = max(closed_positions, key=lambda p: p.get("realized_pnl", 0)) if closed_positions else None
        worst_trade = min(closed_positions, key=lambda p: p.get("realized_pnl", 0)) if closed_positions else None
        
        roi_percent = (realized_pnl / total_invested * 100) if total_invested > 0 else 0
        
        return {
            "period_days": days,
            "total_trades": len(all_positions),
            "closed_trades": len(closed_positions),
            "active_trades": len(active_positions),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "breakeven_trades": len(breakeven_trades),
            "win_rate": round(win_rate, 2),
            "total_invested": round(total_invested, 2),
            "realized_pnl": round(realized_pnl, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_pnl": round(realized_pnl + unrealized_pnl, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "best_trade": {
                "symbol": best_trade.get("symbol"),
                "pnl": round(best_trade.get("realized_pnl", 0), 2)
            } if best_trade else None,
            "worst_trade": {
                "symbol": worst_trade.get("symbol"),
                "pnl": round(worst_trade.get("realized_pnl", 0), 2)
            } if worst_trade else None,
            "roi_percent": round(roi_percent, 2)
        }
    
    async def get_daily_returns(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily returns for charting - only includes days with actual trades"""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        start_date_iso = start_date.isoformat()
        
        closed_positions = await self.db.ai_positions.find(
            {
                "user_id": user_id,
                "status": "closed",
                "closed_at": {"$gte": start_date_iso}
            },
            {"_id": 0}
        ).to_list(10000)
        
        daily_pnl = defaultdict(float)
        daily_trades = defaultdict(int)
        
        for pos in closed_positions:
            closed_at = pos.get("closed_at", "")
            if closed_at:
                try:
                    date_str = closed_at[:10]
                    date = datetime.fromisoformat(closed_at.replace("Z", "+00:00"))
                    if date >= start_date and date <= datetime.now(timezone.utc):
                        daily_pnl[date_str] += pos.get("realized_pnl", 0)
                        daily_trades[date_str] += 1
                except (ValueError, TypeError):
                    continue
        
        sorted_dates = sorted(daily_pnl.keys())
        
        results = []
        cumulative_pnl = 0
        
        for date_str in sorted_dates:
            pnl = daily_pnl[date_str]
            trades = daily_trades[date_str]
            cumulative_pnl += pnl
            
            results.append({
                "date": date_str,
                "pnl": round(pnl, 2),
                "cumulative_pnl": round(cumulative_pnl, 2),
                "trades": trades
            })
        
        return results
    
    async def get_strategy_breakdown(self, user_id: str) -> Dict[str, Any]:
        """Get performance breakdown by strategy"""
        closed_positions = await self.db.ai_positions.find(
            {"user_id": user_id, "status": "closed"},
            {"_id": 0}
        ).to_list(10000)
        
        strategies: Dict[str, Dict[str, float]] = {}
        
        for pos in closed_positions:
            strategy = pos.get("strategy", "manual")
            pnl = pos.get("realized_pnl", 0)
            invested = pos.get("invested_usdt", 0)
            
            if strategy not in strategies:
                strategies[strategy] = {
                    "trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "breakeven": 0,
                    "total_pnl": 0.0,
                    "total_invested": 0.0
                }
            
            strategies[strategy]["trades"] += 1
            strategies[strategy]["total_pnl"] += pnl
            strategies[strategy]["total_invested"] += invested
            
            if pnl > 0:
                strategies[strategy]["wins"] += 1
            elif pnl < 0:
                strategies[strategy]["losses"] += 1
            else:
                strategies[strategy]["breakeven"] += 1
        
        result = {}
        for strategy, stats in strategies.items():
            trades = int(stats["trades"])
            win_rate = (stats["wins"] / trades * 100) if trades > 0 else 0
            roi = (stats["total_pnl"] / stats["total_invested"] * 100) if stats["total_invested"] > 0 else 0
            
            result[strategy] = {
                "trades": trades,
                "wins": int(stats["wins"]),
                "losses": int(stats["losses"]),
                "breakeven": int(stats["breakeven"]),
                "win_rate": round(win_rate, 2),
                "total_pnl": round(stats["total_pnl"], 2),
                "roi_percent": round(roi, 2)
            }
        
        return result
    
    async def get_coin_performance(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get performance breakdown by coin"""
        closed_positions = await self.db.ai_positions.find(
            {"user_id": user_id, "status": "closed"},
            {"_id": 0}
        ).to_list(10000)
        
        coins: Dict[str, Dict[str, Any]] = {}
        
        for pos in closed_positions:
            symbol = pos.get("symbol", "UNKNOWN")
            pnl = pos.get("realized_pnl", 0)
            invested = pos.get("invested_usdt", 0)
            
            if symbol not in coins:
                coins[symbol] = {
                    "trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "breakeven": 0,
                    "total_pnl": 0.0,
                    "total_invested": 0.0,
                    "logo": None
                }
            
            coins[symbol]["trades"] += 1
            coins[symbol]["total_pnl"] += pnl
            coins[symbol]["total_invested"] += invested
            coins[symbol]["logo"] = pos.get("logo")
            
            if pnl > 0:
                coins[symbol]["wins"] += 1
            elif pnl < 0:
                coins[symbol]["losses"] += 1
            else:
                coins[symbol]["breakeven"] += 1
        
        result = []
        for symbol, stats in coins.items():
            trades = int(stats["trades"])
            win_rate = (stats["wins"] / trades * 100) if trades > 0 else 0
            roi = (stats["total_pnl"] / stats["total_invested"] * 100) if stats["total_invested"] > 0 else 0
            
            result.append({
                "symbol": symbol,
                "logo": stats["logo"],
                "trades": trades,
                "wins": int(stats["wins"]),
                "losses": int(stats["losses"]),
                "breakeven": int(stats["breakeven"]),
                "win_rate": round(win_rate, 2),
                "total_pnl": round(stats["total_pnl"], 2),
                "roi_percent": round(roi, 2)
            })
        
        result.sort(key=lambda x: x["total_pnl"], reverse=True)
        return result[:limit]
    
    async def get_bot_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get analytics specifically for bot trades"""
        bot_positions = await self.db.ai_positions.find(
            {"user_id": user_id, "execution_mode": "bot"},
            {"_id": 0}
        ).to_list(10000)
        
        closed_bot = [p for p in bot_positions if p.get("status") == "closed"]
        active_bot = [p for p in bot_positions if p.get("status") == "active"]
        
        total_pnl = sum(p.get("realized_pnl", 0) for p in closed_bot)
        total_invested = sum(p.get("invested_usdt", 0) for p in bot_positions)
        
        wins = len([p for p in closed_bot if p.get("realized_pnl", 0) > 0])
        losses = len([p for p in closed_bot if p.get("realized_pnl", 0) < 0])
        breakeven = len(closed_bot) - wins - losses
        
        bot_position_ids = [p.get("id") for p in bot_positions if p.get("id")]
        
        triggered = await self.db.position_triggers.find(
            {
                "user_id": user_id,
                "status": "triggered",
                "position_id": {"$in": bot_position_ids}
            },
            {"_id": 0}
        ).to_list(10000) if bot_position_ids else []
        
        stop_losses = len([t for t in triggered if t.get("trigger_type") == "stop_loss"])
        take_profits = len([t for t in triggered if t.get("trigger_type") == "take_profit"])
        
        return {
            "total_bot_trades": len(bot_positions),
            "closed_trades": len(closed_bot),
            "active_trades": len(active_bot),
            "wins": wins,
            "losses": losses,
            "breakeven": breakeven,
            "win_rate": round((wins / len(closed_bot) * 100) if closed_bot else 0, 2),
            "total_pnl": round(total_pnl, 2),
            "total_invested": round(total_invested, 2),
            "roi_percent": round((total_pnl / total_invested * 100) if total_invested > 0 else 0, 2),
            "stop_losses_triggered": stop_losses,
            "take_profits_triggered": take_profits
        }


analytics_engine = None


def init_analytics_engine(db):
    global analytics_engine
    analytics_engine = AnalyticsEngine(db)
    return analytics_engine
