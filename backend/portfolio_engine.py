"""
Portfolio Engine - Manages AI-driven investment positions
Supports real DEX execution and bot-initiated trades
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)

MAX_ALLOCATION_PER_COIN = 0.20
MAX_DUMP_STRATEGY_ALLOCATION = 0.40
MIN_INVESTMENT_USDT = 10

EXECUTION_MODE_DEX = "dex"
EXECUTION_MODE_BOT = "bot"


class PortfolioEngine:
    """
    Engine for managing AI investment portfolio.
    Supports:
    - Real DEX execution via 1inch API (records actual on-chain swaps)
    - Bot-initiated positions (triggered by automated trading bot)
    """
    
    def __init__(self, db, market_provider, wallet_service):
        self.db = db
        self.market_provider = market_provider
        self.wallet_service = wallet_service
        logger.info("Portfolio Engine initialized")
    
    async def get_user_portfolio(self, user_id: str) -> Dict[str, Any]:
        """Get user's complete portfolio status"""
        try:
            positions = await self.db.ai_positions.find(
                {"user_id": user_id},
                {"_id": 0}
            ).to_list(1000)
            
            active_positions = [p for p in positions if p.get("status") == "active"]
            closed_positions = [p for p in positions if p.get("status") == "closed"]
            
            coins = await self.market_provider.get_coins_list(100)
            price_map = {c["symbol"]: c["price"] for c in coins}
            
            total_invested = 0
            total_current_value = 0
            total_unrealized_pnl = 0
            
            enriched_positions = []
            for pos in active_positions:
                symbol = pos.get("symbol")
                current_price = price_map.get(symbol, pos.get("entry_price", 0))
                invested = pos.get("invested_usdt", 0)
                quantity = pos.get("quantity", 0)
                entry_price = pos.get("entry_price", 0)
                
                current_value = quantity * current_price if quantity > 0 else invested
                unrealized_pnl = current_value - invested
                pnl_percent = (unrealized_pnl / invested * 100) if invested > 0 else 0
                
                total_invested += invested
                total_current_value += current_value
                total_unrealized_pnl += unrealized_pnl
                
                enriched_positions.append({
                    **pos,
                    "current_price": current_price,
                    "current_value": current_value,
                    "unrealized_pnl": unrealized_pnl,
                    "pnl_percent": round(pnl_percent, 2)
                })
            
            total_realized_pnl = sum(p.get("realized_pnl", 0) for p in closed_positions)
            
            return {
                "user_id": user_id,
                "active_positions": enriched_positions,
                "closed_positions": closed_positions[-10:],
                "summary": {
                    "total_invested_usdt": round(total_invested, 2),
                    "total_current_value_usdt": round(total_current_value, 2),
                    "total_unrealized_pnl_usdt": round(total_unrealized_pnl, 2),
                    "total_unrealized_pnl_percent": round((total_unrealized_pnl / total_invested * 100) if total_invested > 0 else 0, 2),
                    "total_realized_pnl_usdt": round(total_realized_pnl, 2),
                    "active_position_count": len(active_positions),
                    "closed_position_count": len(closed_positions)
                },
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching portfolio for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "active_positions": [],
                "closed_positions": [],
                "summary": {
                    "total_invested_usdt": 0,
                    "total_current_value_usdt": 0,
                    "total_unrealized_pnl_usdt": 0,
                    "total_unrealized_pnl_percent": 0,
                    "total_realized_pnl_usdt": 0,
                    "active_position_count": 0,
                    "closed_position_count": 0
                },
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "error": "Failed to fetch portfolio data"
            }
    
    async def create_investment(
        self,
        user_id: str,
        symbol: str,
        usdt_amount: float,
        strategy: str,
        trigger_reason: str,
        enforce_allocation_limits: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new investment position.
        Validates against real wallet balance and enforces allocation limits.
        
        Server-side enforcement:
        - Validates against on-chain USDT balance (source of truth)
        - Enforces 20% max allocation per coin
        - Enforces 40% max for dump_buy strategy
        - Minimum 10 USDT per investment
        """
        wallet_status = await self.wallet_service.get_user_wallet_status(user_id)
        available_usdt = wallet_status.get("available_usdt", 0)
        total_usdt = wallet_status.get("total_usdt", 0)

        if total_usdt <= 0:
            return {
                "success": False,
                "error": "No USDT balance detected. Connect a wallet with USDT."
            }
        
        if usdt_amount > available_usdt:
            return {
                "success": False,
                "error": f"Insufficient USDT. Available: {available_usdt:.2f}, Requested: {usdt_amount:.2f}"
            }
        
        if usdt_amount < MIN_INVESTMENT_USDT:
            return {
                "success": False,
                "error": f"Minimum investment is {MIN_INVESTMENT_USDT} USDT"
            }
        
        if enforce_allocation_limits:
            max_allowed_per_coin = total_usdt * MAX_ALLOCATION_PER_COIN
            if usdt_amount > max_allowed_per_coin:
                return {
                    "success": False,
                    "error": f"Max 20% per coin. Max allowed: {max_allowed_per_coin:.2f} USDT"
                }
            
            if strategy == "dump_buy":
                existing_dump_positions = await self.db.ai_positions.find(
                    {"user_id": user_id, "status": "active", "strategy": "dump_buy"},
                    {"_id": 0, "invested_usdt": 1}
                ).to_list(1000)
                
                current_dump_invested = sum(p.get("invested_usdt", 0) for p in existing_dump_positions)
                max_dump_allocation = total_usdt * MAX_DUMP_STRATEGY_ALLOCATION
                
                if current_dump_invested + usdt_amount > max_dump_allocation:
                    remaining = max(0, max_dump_allocation - current_dump_invested)
                    return {
                        "success": False,
                        "error": f"Dump strategy limit (40%) reached. Remaining: {remaining:.2f} USDT"
                    }
            
            existing_positions = await self.db.ai_positions.find(
                {"user_id": user_id, "status": "active", "symbol": symbol},
                {"_id": 0, "invested_usdt": 1}
            ).to_list(100)
            
            current_symbol_invested = sum(p.get("invested_usdt", 0) for p in existing_positions)
            if current_symbol_invested + usdt_amount > max_allowed_per_coin:
                remaining = max(0, max_allowed_per_coin - current_symbol_invested)
                return {
                    "success": False,
                    "error": f"Max 20% per coin for {symbol}. Remaining: {remaining:.2f} USDT"
                }
        
        coins = await self.market_provider.get_coins_list(100)
        coin = next((c for c in coins if c["symbol"] == symbol), None)
        
        if not coin:
            return {
                "success": False,
                "error": f"Coin {symbol} not found in top 100"
            }
        
        entry_price = coin["price"]
        quantity = usdt_amount / entry_price if entry_price > 0 else 0
        
        position_id = str(uuid.uuid4())
        position = {
            "id": position_id,
            "user_id": user_id,
            "symbol": symbol,
            "name": coin.get("name", symbol),
            "entry_price": entry_price,
            "quantity": quantity,
            "invested_usdt": usdt_amount,
            "strategy": strategy,
            "trigger_reason": trigger_reason,
            "status": "active",
            "execution_mode": "dex",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "logo": coin.get("logo", "")
        }
        
        await self.db.ai_positions.insert_one(position)
        
        logger.info(f"Created position: {symbol} - {usdt_amount} USDT @ {entry_price}")
        
        return {
            "success": True,
            "position": position,
            "message": f"Invested {usdt_amount} USDT in {symbol} @ {entry_price} USDT"
        }
    
    async def close_position(
        self,
        user_id: str,
        position_id: str,
        reason: str = "manual"
    ) -> Dict[str, Any]:
        """Close an existing position (atomic transition to prevent double-close)"""
        position = await self.db.ai_positions.find_one(
            {"id": position_id, "user_id": user_id},
            {"_id": 0}
        )
        
        if not position:
            return {"success": False, "error": "Position not found"}
        
        if position.get("status") != "active":
            return {"success": False, "error": "Position already closed"}
        
        coins = await self.market_provider.get_coins_list(100)
        price_map = {c["symbol"]: c["price"] for c in coins}
        
        symbol = position.get("symbol")
        exit_price = price_map.get(symbol, position.get("entry_price", 0))
        quantity = position.get("quantity", 0)
        invested = position.get("invested_usdt", 0)
        
        exit_value = quantity * exit_price if quantity > 0 else invested
        realized_pnl = exit_value - invested
        
        result = await self.db.ai_positions.find_one_and_update(
            {"id": position_id, "user_id": user_id, "status": "active"},
            {"$set": {
                "status": "closed",
                "exit_price": exit_price,
                "exit_value": exit_value,
                "realized_pnl": realized_pnl,
                "close_reason": reason,
                "closed_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        if not result:
            return {"success": False, "error": "Position already closed or modified by another request"}
        
        logger.info(f"Closed position: {symbol} - PnL: {realized_pnl:.2f} USDT")
        
        return {
            "success": True,
            "exit_price": exit_price,
            "exit_value": exit_value,
            "realized_pnl": realized_pnl,
            "message": f"Closed {symbol} position. PnL: {realized_pnl:+.2f} USDT"
        }
    
    async def record_dex_swap(
        self,
        user_id: str,
        symbol: str,
        usdt_amount: float,
        quantity: float,
        entry_price: float,
        tx_hash: str,
        chain_id: int,
        strategy: str = "manual",
        trigger_reason: str = "DEX swap executed"
    ) -> Dict[str, Any]:
        """
        Record a real DEX swap as a portfolio position.
        Called after user executes swap via SwapModal.
        
        Args:
            user_id: User's ID
            symbol: Token symbol (e.g., 'ETH', 'LINK')
            usdt_amount: Amount of USDT spent
            quantity: Amount of tokens received
            entry_price: Price per token at swap time
            tx_hash: Blockchain transaction hash
            chain_id: Network chain ID
            strategy: Investment strategy (dump_buy, trend_follow, manual)
            trigger_reason: Why this trade was made
        """
        coins = await self.market_provider.get_coins_list(100)
        coin = next((c for c in coins if c["symbol"] == symbol), None)
        
        position_id = str(uuid.uuid4())
        position = {
            "id": position_id,
            "user_id": user_id,
            "symbol": symbol,
            "name": coin.get("name", symbol) if coin else symbol,
            "entry_price": entry_price,
            "quantity": quantity,
            "invested_usdt": usdt_amount,
            "strategy": strategy,
            "trigger_reason": trigger_reason,
            "status": "active",
            "execution_mode": EXECUTION_MODE_DEX,
            "tx_hash": tx_hash,
            "chain_id": chain_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "logo": coin.get("logo", "") if coin else ""
        }
        
        await self.db.ai_positions.insert_one(position)
        
        logger.info(f"Recorded DEX swap: {symbol} - {usdt_amount} USDT @ {entry_price} (tx: {tx_hash[:10]}...)")
        
        return {
            "success": True,
            "position": position,
            "message": f"DEX swap recorded: {quantity:.6f} {symbol} @ {entry_price:.4f} USDT"
        }
    
    async def close_position_with_dex(
        self,
        user_id: str,
        position_id: str,
        exit_price: float,
        exit_quantity: float,
        tx_hash: str,
        reason: str = "dex_sell"
    ) -> Dict[str, Any]:
        """
        Close a position after executing a real DEX sell swap.
        
        Args:
            user_id: User's ID
            position_id: Position to close
            exit_price: Price per token at sell time
            exit_quantity: Amount of tokens sold
            tx_hash: Blockchain transaction hash
            reason: Close reason
        """
        position = await self.db.ai_positions.find_one(
            {"id": position_id, "user_id": user_id},
            {"_id": 0}
        )
        
        if not position:
            return {"success": False, "error": "Position not found"}
        
        if position.get("status") != "active":
            return {"success": False, "error": "Position already closed"}
        
        invested = position.get("invested_usdt", 0)
        exit_value = exit_quantity * exit_price
        realized_pnl = exit_value - invested
        symbol = position.get("symbol")
        
        result = await self.db.ai_positions.find_one_and_update(
            {"id": position_id, "user_id": user_id, "status": "active"},
            {"$set": {
                "status": "closed",
                "exit_price": exit_price,
                "exit_quantity": exit_quantity,
                "exit_value": exit_value,
                "realized_pnl": realized_pnl,
                "close_reason": reason,
                "close_tx_hash": tx_hash,
                "closed_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        if not result:
            return {"success": False, "error": "Position already closed or modified by another request"}
        
        logger.info(f"DEX position closed: {symbol} - PnL: {realized_pnl:.2f} USDT (tx: {tx_hash[:10]}...)")
        
        return {
            "success": True,
            "exit_price": exit_price,
            "exit_value": exit_value,
            "realized_pnl": realized_pnl,
            "tx_hash": tx_hash,
            "message": f"DEX sell executed: {symbol} PnL: {realized_pnl:+.2f} USDT"
        }
    
    async def auto_allocate(
        self,
        user_id: str,
        total_usdt: float,
        opportunities: List[Dict],
        strategy: str = "dump_buy"
    ) -> Dict[str, Any]:
        """
        Automatically allocate USDT across opportunities.
        Respects allocation limits and risk scores.
        """
        wallet_status = await self.wallet_service.get_user_wallet_status(user_id)
        available_usdt = wallet_status.get("available_usdt", 0)

        if total_usdt > available_usdt:
            return {
                "success": False,
                "error": f"Insufficient USDT. Available: {available_usdt:.2f}"
            }
        
        max_per_coin = total_usdt * MAX_ALLOCATION_PER_COIN
        
        total_risk = sum(1 - opp.get("risk_score", 0.5) for opp in opportunities)
        
        allocations = []
        allocated_total = 0
        
        for opp in opportunities:
            if allocated_total >= total_usdt:
                break
            
            risk_score = opp.get("risk_score", 0.5)
            inverse_risk = 1 - risk_score
            
            weight = inverse_risk / total_risk if total_risk > 0 else 1 / len(opportunities)
            raw_allocation = total_usdt * weight
            
            allocation = min(raw_allocation, max_per_coin, total_usdt - allocated_total)
            
            if allocation >= MIN_INVESTMENT_USDT:
                allocations.append({
                    "symbol": opp.get("symbol"),
                    "name": opp.get("name"),
                    "allocation_usdt": round(allocation, 2),
                    "risk_score": risk_score,
                    "trigger_reason": opp.get("reason", "AI recommendation"),
                    "price_usdt": opp.get("price_usdt", 0),
                    "logo": opp.get("logo", "")
                })
                allocated_total += allocation
        
        return {
            "success": True,
            "strategy": strategy,
            "total_to_invest": round(allocated_total, 2),
            "allocations": allocations,
            "allocation_count": len(allocations)
        }
    
    async def execute_allocations(
        self,
        user_id: str,
        allocations: List[Dict],
        strategy: str = "dump_buy"
    ) -> Dict[str, Any]:
        """Execute a list of allocations as investments"""
        results = []
        successful = 0
        failed = 0
        
        for alloc in allocations:
            result = await self.create_investment(
                user_id=user_id,
                symbol=alloc["symbol"],
                usdt_amount=alloc["allocation_usdt"],
                strategy=strategy,
                trigger_reason=alloc.get("trigger_reason", "AI allocation")
            )
            
            results.append({
                "symbol": alloc["symbol"],
                "amount": alloc["allocation_usdt"],
                "success": result.get("success", False),
                "message": result.get("message") or result.get("error")
            })
            
            if result.get("success"):
                successful += 1
            else:
                failed += 1
        
        return {
            "success": failed == 0,
            "total_allocations": len(allocations),
            "successful": successful,
            "failed": failed,
            "results": results
        }


    async def get_rebalancing_suggestions(
        self,
        user_id: str,
        target_allocation: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """
        Analyze portfolio and suggest rebalancing actions.
        Uses AI-driven analysis to suggest optimal allocations.
        """
        try:
            return await self._compute_rebalancing(user_id, target_allocation)
        except Exception as e:
            logger.error(f"Error computing rebalancing for user {user_id}: {e}")
            return {
                "success": False,
                "needs_rebalancing": False,
                "message": "Failed to compute rebalancing suggestions",
                "suggestions": [],
                "error": str(e)
            }

    async def _compute_rebalancing(
        self,
        user_id: str,
        target_allocation: Dict[str, float] = None
    ) -> Dict[str, Any]:
        portfolio = await self.get_user_portfolio(user_id)
        active_positions = portfolio.get("active_positions", [])
        summary = portfolio.get("summary", {})
        
        if not active_positions:
            return {
                "success": True,
                "needs_rebalancing": False,
                "message": "No active positions to rebalance",
                "suggestions": []
            }
        
        total_value = summary.get("total_current_value_usdt", 0)
        if total_value <= 0:
            return {
                "success": True,
                "needs_rebalancing": False,
                "message": "Portfolio has no value to rebalance",
                "suggestions": []
            }
        
        coins = await self.market_provider.get_coins_list(100)
        coin_analysis = {c["symbol"]: {
            "price": c["price"],
            "change_24h": c.get("percent_change_24h", 0),
            "change_7d": c.get("percent_change_7d", 0),
            "market_cap": c.get("market_cap", 0),
            "volume_24h": c.get("volume_24h", 0)
        } for c in coins}
        
        current_allocations = {}
        position_analysis = []
        
        for pos in active_positions:
            symbol = pos.get("symbol")
            current_value = pos.get("current_value", 0)
            allocation_pct = (current_value / total_value * 100) if total_value > 0 else 0
            pnl_percent = pos.get("pnl_percent", 0)
            
            current_allocations[symbol] = allocation_pct
            
            coin_data = coin_analysis.get(symbol, {})
            momentum = coin_data.get("change_24h", 0) + (coin_data.get("change_7d", 0) * 0.5)
            
            position_analysis.append({
                "symbol": symbol,
                "current_allocation_pct": round(allocation_pct, 2),
                "current_value": round(current_value, 2),
                "pnl_percent": round(pnl_percent, 2),
                "entry_price": pos.get("entry_price", 0),
                "current_price": pos.get("current_price", 0),
                "momentum_score": round(momentum, 2),
                "needs_attention": allocation_pct > 30 or pnl_percent < -10 or pnl_percent > 20
            })
        
        suggestions = []
        
        for pa in position_analysis:
            symbol = pa["symbol"]
            allocation = pa["current_allocation_pct"]
            pnl_pct = pa["pnl_percent"]
            momentum = pa["momentum_score"]
            
            if allocation > 30:
                suggestions.append({
                    "symbol": symbol,
                    "action": "reduce",
                    "reason": f"Over-concentrated ({allocation:.1f}% of portfolio)",
                    "urgency": "high",
                    "suggested_reduction_pct": round(allocation - 20, 2)
                })
            elif pnl_pct > 25:
                suggestions.append({
                    "symbol": symbol,
                    "action": "take_profit",
                    "reason": f"Strong gains (+{pnl_pct:.1f}%)",
                    "urgency": "medium",
                    "suggested_reduction_pct": round(allocation * 0.3, 2)
                })
            elif pnl_pct < -15 and momentum < -5:
                suggestions.append({
                    "symbol": symbol,
                    "action": "reduce_or_close",
                    "reason": f"Significant loss ({pnl_pct:.1f}%) with weak momentum",
                    "urgency": "high",
                    "suggested_reduction_pct": round(allocation * 0.5, 2)
                })
            elif allocation < 5 and pnl_pct > 5 and momentum > 3:
                suggestions.append({
                    "symbol": symbol,
                    "action": "increase",
                    "reason": f"Small position with positive momentum (+{momentum:.1f})",
                    "urgency": "low",
                    "suggested_increase_pct": round(min(10 - allocation, 5), 2)
                })
        
        top_performers = sorted(position_analysis, key=lambda x: x["momentum_score"], reverse=True)[:3]
        underperformers = sorted(position_analysis, key=lambda x: x["momentum_score"])[:3]
        
        for perf in top_performers:
            if perf["current_allocation_pct"] < 15 and perf["momentum_score"] > 5:
                existing = next((s for s in suggestions if s["symbol"] == perf["symbol"]), None)
                if not existing:
                    suggestions.append({
                        "symbol": perf["symbol"],
                        "action": "increase",
                        "reason": f"Top performer with +{perf['momentum_score']:.1f} momentum",
                        "urgency": "low",
                        "suggested_increase_pct": 5
                    })
        
        needs_rebalancing = len(suggestions) > 0
        
        return {
            "success": True,
            "needs_rebalancing": needs_rebalancing,
            "portfolio_summary": {
                "total_value_usdt": round(total_value, 2),
                "position_count": len(active_positions),
                "top_performers": [p["symbol"] for p in top_performers],
                "underperformers": [p["symbol"] for p in underperformers if p["momentum_score"] < 0]
            },
            "position_analysis": position_analysis,
            "suggestions": suggestions,
            "suggestion_count": len(suggestions)
        }


portfolio_engine = None

def init_portfolio_engine(db, market_provider, wallet_service):
    global portfolio_engine
    portfolio_engine = PortfolioEngine(db, market_provider, wallet_service)
    return portfolio_engine
