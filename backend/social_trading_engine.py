"""
Social Trading Engine for Moon Hunters
Provides copy trading and leaderboard functionality
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from bson import ObjectId

logger = logging.getLogger("social_trading")


class SocialTradingEngine:
    def __init__(self, db):
        self.db = db
        logger.info("Social Trading Engine initialized")
    
    async def get_trader_stats(self, user_id: str) -> Dict[str, Any]:
        """Calculate trading statistics for a user"""
        positions = await self.db.ai_portfolio.find({
            "user_id": user_id,
            "status": "closed"
        }).to_list(length=500)
        
        if not positions:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_return": 0,
                "best_trade": 0,
                "worst_trade": 0
            }
        
        total_trades = len(positions)
        winning_trades = sum(1 for p in positions if p.get("pnl", 0) > 0)
        total_pnl = sum(p.get("pnl", 0) for p in positions)
        returns = [p.get("pnl_percent", 0) for p in positions]
        
        return {
            "total_trades": total_trades,
            "win_rate": round((winning_trades / total_trades) * 100, 1) if total_trades > 0 else 0,
            "total_pnl": round(total_pnl, 2),
            "avg_return": round(sum(returns) / len(returns), 2) if returns else 0,
            "best_trade": round(max(returns), 2) if returns else 0,
            "worst_trade": round(min(returns), 2) if returns else 0
        }
    
    async def get_leaderboard(self, period: str = "all", limit: int = 20) -> List[Dict[str, Any]]:
        """Get top traders by performance"""
        date_filter = {}
        if period == "week":
            date_filter = {"closed_at": {"$gte": datetime.now(timezone.utc) - timedelta(days=7)}}
        elif period == "month":
            date_filter = {"closed_at": {"$gte": datetime.now(timezone.utc) - timedelta(days=30)}}
        
        pipeline = [
            {"$match": {"status": "closed", **date_filter}},
            {"$group": {
                "_id": "$user_id",
                "total_trades": {"$sum": 1},
                "total_pnl": {"$sum": "$pnl"},
                "wins": {"$sum": {"$cond": [{"$gt": ["$pnl", 0]}, 1, 0]}},
                "total_invested": {"$sum": "$invested_usd"},
                "last_trade": {"$max": "$closed_at"}
            }},
            {"$match": {"total_trades": {"$gte": 3}}},
            {"$addFields": {
                "win_rate": {"$multiply": [{"$divide": ["$wins", "$total_trades"]}, 100]},
                "roi": {"$multiply": [{"$divide": ["$total_pnl", {"$max": ["$total_invested", 1]}]}, 100]}
            }},
            {"$sort": {"total_pnl": -1}},
            {"$limit": limit}
        ]
        
        results = await self.db.ai_portfolio.aggregate(pipeline).to_list(length=limit)
        
        trader_ids = [t["_id"] for t in results]
        oid_ids = [ObjectId(tid) for tid in trader_ids if ObjectId.is_valid(tid)]
        wallet_ids = [tid for tid in trader_ids if not ObjectId.is_valid(tid)]
        
        users_by_id = {}
        if oid_ids:
            oid_users = await self.db.users.find({"_id": {"$in": oid_ids}}).to_list(length=len(oid_ids))
            for u in oid_users:
                users_by_id[str(u["_id"])] = u
        if wallet_ids:
            wallet_users = await self.db.users.find({"wallet_address": {"$in": wallet_ids}}).to_list(length=len(wallet_ids))
            for u in wallet_users:
                users_by_id[u["wallet_address"]] = u
        
        leaderboard = []
        for rank, trader in enumerate(results, 1):
            user = users_by_id.get(trader["_id"])
            display_name = self._get_display_name(user, trader["_id"])
            
            leaderboard.append({
                "rank": rank,
                "user_id": trader["_id"],
                "display_name": display_name,
                "total_trades": trader["total_trades"],
                "win_rate": round(trader["win_rate"], 1),
                "total_pnl": round(trader["total_pnl"], 2),
                "roi": round(trader["roi"], 2),
                "last_trade": trader["last_trade"].isoformat() if trader.get("last_trade") else None
            })
        
        return leaderboard
    
    def _get_display_name(self, user: Optional[Dict], user_id: str) -> str:
        """Generate anonymous display name for leaderboard"""
        if user and user.get("display_name"):
            return user["display_name"]
        
        if len(user_id) > 10:
            return f"Trader_{user_id[:6]}...{user_id[-4:]}"
        return f"Trader_{user_id[:8]}"
    
    async def get_public_portfolio(self, user_id: str) -> Dict[str, Any]:
        """Get a trader's public portfolio for copy trading"""
        settings = await self.db.social_settings.find_one({"user_id": user_id})
        
        if not settings or not settings.get("public_portfolio", False):
            return {"error": "This trader's portfolio is not public"}
        
        open_positions = await self.db.ai_portfolio.find({
            "user_id": user_id,
            "status": "open"
        }).to_list(length=50)
        
        stats = await self.get_trader_stats(user_id)
        
        positions = []
        for pos in open_positions:
            positions.append({
                "symbol": pos["symbol"],
                "invested_usd": round(pos["invested_usd"], 2),
                "entry_price": pos["entry_price"],
                "current_pnl_percent": round(pos.get("current_pnl_percent", 0), 2),
                "opened_at": pos["created_at"].isoformat() if pos.get("created_at") else None
            })
        
        return {
            "user_id": user_id,
            "stats": stats,
            "open_positions": positions,
            "position_count": len(positions)
        }
    
    async def toggle_public_portfolio(self, user_id: str, is_public: bool) -> bool:
        """Toggle whether a user's portfolio is publicly visible"""
        await self.db.social_settings.update_one(
            {"user_id": user_id},
            {"$set": {
                "public_portfolio": is_public,
                "updated_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )
        return True
    
    async def follow_trader(self, follower_id: str, trader_id: str) -> Dict[str, Any]:
        """Follow a trader to receive their trade notifications"""
        if follower_id == trader_id:
            return {"success": False, "message": "Cannot follow yourself"}
        
        settings = await self.db.social_settings.find_one({"user_id": trader_id})
        if not settings or not settings.get("public_portfolio", False):
            return {"success": False, "message": "Trader's portfolio is not public"}
        
        existing = await self.db.follows.find_one({
            "follower_id": follower_id,
            "trader_id": trader_id
        })
        
        if existing:
            return {"success": False, "message": "Already following this trader"}
        
        await self.db.follows.insert_one({
            "follower_id": follower_id,
            "trader_id": trader_id,
            "copy_enabled": False,
            "copy_percentage": 100,
            "max_per_trade": 100,
            "followed_at": datetime.now(timezone.utc)
        })
        
        return {"success": True, "message": "Now following trader"}
    
    async def unfollow_trader(self, follower_id: str, trader_id: str) -> bool:
        """Stop following a trader"""
        result = await self.db.follows.delete_one({
            "follower_id": follower_id,
            "trader_id": trader_id
        })
        return result.deleted_count > 0
    
    async def get_following(self, user_id: str) -> List[Dict[str, Any]]:
        """Get list of traders a user is following"""
        follows = await self.db.follows.find({
            "follower_id": user_id
        }).to_list(length=100)
        
        result = []
        for follow in follows:
            stats = await self.get_trader_stats(follow["trader_id"])
            user = await self.db.users.find_one({"wallet_address": follow["trader_id"]})
            
            result.append({
                "trader_id": follow["trader_id"],
                "display_name": self._get_display_name(user, follow["trader_id"]),
                "copy_enabled": follow.get("copy_enabled", False),
                "copy_percentage": follow.get("copy_percentage", 100),
                "max_per_trade": follow.get("max_per_trade", 100),
                "followed_at": follow["followed_at"].isoformat(),
                "stats": stats
            })
        
        return result
    
    async def get_followers(self, user_id: str) -> int:
        """Get follower count for a trader"""
        return await self.db.follows.count_documents({"trader_id": user_id})
    
    async def update_copy_settings(
        self,
        follower_id: str,
        trader_id: str,
        copy_enabled: bool,
        copy_percentage: int = 100,
        max_per_trade: float = 100
    ) -> bool:
        """Update copy trading settings for a followed trader"""
        result = await self.db.follows.update_one(
            {"follower_id": follower_id, "trader_id": trader_id},
            {"$set": {
                "copy_enabled": copy_enabled,
                "copy_percentage": min(100, max(10, copy_percentage)),
                "max_per_trade": max(10, max_per_trade),
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        return result.modified_count > 0
    
    async def get_copy_traders(self, user_id: str) -> List[Dict[str, Any]]:
        """Get followers who have copy trading enabled for a trader"""
        return await self.db.follows.find({
            "trader_id": user_id,
            "copy_enabled": True
        }).to_list(length=100)
    
    async def get_activity_feed(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get activity feed of trades from followed traders"""
        follows = await self.db.follows.find({
            "follower_id": user_id
        }).to_list(length=100)
        
        if not follows:
            return []
        
        trader_ids = [f["trader_id"] for f in follows]
        
        trades = await self.db.ai_portfolio.find({
            "user_id": {"$in": trader_ids}
        }).sort("created_at", -1).limit(limit).to_list(length=limit)
        
        activity = []
        for trade in trades:
            user = await self.db.users.find_one({"wallet_address": trade["user_id"]})
            
            activity.append({
                "type": "trade",
                "trader_id": trade["user_id"],
                "trader_name": self._get_display_name(user, trade["user_id"]),
                "symbol": trade["symbol"],
                "action": "buy" if trade["status"] == "open" else "sell",
                "amount_usd": round(trade["invested_usd"], 2),
                "price": trade.get("entry_price", 0),
                "pnl": round(trade.get("pnl", 0), 2) if trade["status"] == "closed" else None,
                "pnl_percent": round(trade.get("pnl_percent", 0), 2) if trade["status"] == "closed" else None,
                "timestamp": trade.get("created_at", trade.get("closed_at")).isoformat() if trade.get("created_at") or trade.get("closed_at") else None
            })
        
        return activity
    
    async def get_social_settings(self, user_id: str) -> Dict[str, Any]:
        """Get user's social trading settings"""
        settings = await self.db.social_settings.find_one({"user_id": user_id})
        
        if not settings:
            return {
                "public_portfolio": False,
                "allow_copy": False,
                "display_name": None
            }
        
        return {
            "public_portfolio": settings.get("public_portfolio", False),
            "allow_copy": settings.get("allow_copy", False),
            "display_name": settings.get("display_name")
        }
    
    async def update_social_settings(
        self,
        user_id: str,
        public_portfolio: Optional[bool] = None,
        allow_copy: Optional[bool] = None,
        display_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update user's social trading settings"""
        update: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
        
        if public_portfolio is not None:
            update["public_portfolio"] = public_portfolio
        if allow_copy is not None:
            update["allow_copy"] = allow_copy
        if display_name is not None:
            update["display_name"] = display_name[:20] if display_name else None
        
        await self.db.social_settings.update_one(
            {"user_id": user_id},
            {"$set": update},
            upsert=True
        )
        
        return await self.get_social_settings(user_id)


social_trading_engine: Optional[SocialTradingEngine] = None


def init_social_trading_engine(db) -> SocialTradingEngine:
    global social_trading_engine
    social_trading_engine = SocialTradingEngine(db)
    return social_trading_engine


def get_social_trading_engine() -> Optional[SocialTradingEngine]:
    return social_trading_engine
