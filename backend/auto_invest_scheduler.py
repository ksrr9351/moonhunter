"""
Auto-Invest Scheduler - Scheduled investment execution with wallet approval
Executes AI-recommended portfolio investments on user-defined schedules
"""
import os
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import uuid

logger = logging.getLogger(__name__)

class AutoInvestScheduler:
    """
    Scheduler for automated cryptocurrency investments
    Supports daily, weekly, and monthly schedules
    Requires wallet approval for each execution
    """
    
    def __init__(self, db, perplexity_client):
        self.db = db
        self.perplexity_client = perplexity_client
        self.pending_executions: Dict[str, Dict] = {}
    
    async def get_user_config(self, user_id: str) -> Optional[Dict]:
        """Get user's auto-invest configuration"""
        config = await self.db.auto_invest_configs.find_one(
            {"user_id": user_id},
            {"_id": 0}
        )
        return config
    
    async def check_due_investments(self) -> List[Dict]:
        """Check for investments that are due to be executed"""
        now = datetime.now(timezone.utc)
        
        configs = await self.db.auto_invest_configs.find(
            {"enabled": True},
            {"_id": 0}
        ).to_list(1000)
        
        due_investments = []
        
        for config in configs:
            last_executed = config.get("last_executed")
            frequency = config.get("frequency", "weekly")
            
            if last_executed:
                if isinstance(last_executed, str):
                    last_executed = datetime.fromisoformat(last_executed.replace('Z', '+00:00'))
                
                days_since = (now - last_executed).days
                
                if frequency == "daily" and days_since < 1:
                    continue
                elif frequency == "weekly" and days_since < 7:
                    continue
                elif frequency == "monthly" and days_since < 30:
                    continue
            
            due_investments.append(config)
        
        return due_investments
    
    async def prepare_investment(self, user_id: str) -> Dict[str, Any]:
        """
        Prepare an auto-invest execution
        Returns investment plan that requires wallet approval
        """
        config = await self.get_user_config(user_id)
        
        if not config:
            return {"success": False, "error": "Auto-invest not configured"}
        
        if not config.get("enabled"):
            return {"success": False, "error": "Auto-invest is disabled"}
        
        try:
            recommendations = await self.perplexity_client.get_ai_recommendations(
                risk_tolerance=config.get("risk_tolerance", "moderate"),
                investment_amount=config.get("investment_amount", 100),
                investment_horizon="medium-term"
            )
            
            allocations = self._parse_allocations(
                recommendations.get("recommendation", ""),
                config.get("investment_amount", 100)
            )
            
            if not allocations:
                allocations = self._get_default_allocations(
                    config.get("risk_tolerance", "moderate"),
                    config.get("investment_amount", 100)
                )
            
            execution_id = str(uuid.uuid4())
            
            execution_plan = {
                "execution_id": execution_id,
                "user_id": user_id,
                "total_amount": config.get("investment_amount", 100),
                "risk_tolerance": config.get("risk_tolerance", "moderate"),
                "allocations": allocations,
                "status": "pending_approval",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
            }
            
            self.pending_executions[execution_id] = execution_plan
            
            await self.db.auto_invest_executions.insert_one(execution_plan.copy())
            
            return {
                "success": True,
                "execution_plan": execution_plan
            }
            
        except Exception as e:
            logger.error(f"Error preparing auto-invest: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _parse_allocations(self, recommendation: str, total_amount: float) -> List[Dict]:
        """Parse portfolio allocations from AI recommendation"""
        allocations = []
        lines = recommendation.split('\n')
        
        for line in lines:
            import re
            match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*[-–:]\s*([A-Z]{2,10})', line, re.IGNORECASE)
            if match:
                percentage = float(match.group(1))
                symbol = match.group(2).upper()
                amount = (total_amount * percentage) / 100
                
                if amount >= 1:
                    allocations.append({
                        "symbol": symbol,
                        "percentage": percentage,
                        "amount": amount
                    })
        
        return allocations
    
    def _get_default_allocations(self, risk_tolerance: str, total_amount: float) -> List[Dict]:
        """Get default allocations based on risk tolerance"""
        if risk_tolerance == "conservative":
            return [
                {"symbol": "BTC", "percentage": 50, "amount": total_amount * 0.5},
                {"symbol": "ETH", "percentage": 30, "amount": total_amount * 0.3},
                {"symbol": "USDT", "percentage": 20, "amount": total_amount * 0.2}
            ]
        elif risk_tolerance == "aggressive":
            return [
                {"symbol": "ETH", "percentage": 40, "amount": total_amount * 0.4},
                {"symbol": "SOL", "percentage": 30, "amount": total_amount * 0.3},
                {"symbol": "LINK", "percentage": 30, "amount": total_amount * 0.3}
            ]
        else:
            return [
                {"symbol": "BTC", "percentage": 40, "amount": total_amount * 0.4},
                {"symbol": "ETH", "percentage": 40, "amount": total_amount * 0.4},
                {"symbol": "SOL", "percentage": 20, "amount": total_amount * 0.2}
            ]
    
    async def approve_execution(self, execution_id: str, wallet_address: str, user_id: str) -> Dict[str, Any]:
        """
        Approve a pending auto-invest execution
        Returns the execution plan (DEX swap functionality removed)
        Requires user_id to verify ownership
        """
        execution = self.pending_executions.get(execution_id)
        
        if not execution:
            execution = await self.db.auto_invest_executions.find_one(
                {"execution_id": execution_id},
                {"_id": 0}
            )
        
        if not execution:
            return {"success": False, "error": "Execution not found"}
        
        if execution.get("user_id") != user_id:
            return {"success": False, "error": "Unauthorized: execution belongs to another user"}
        
        if execution.get("status") != "pending_approval":
            return {"success": False, "error": "Execution already processed"}
        
        expires_at = datetime.fromisoformat(execution["expires_at"].replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > expires_at:
            return {"success": False, "error": "Execution has expired"}
        
        await self.db.auto_invest_executions.update_one(
            {"execution_id": execution_id},
            {"$set": {
                "status": "approved",
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "wallet_address": wallet_address
            }}
        )
        
        return {
            "success": True,
            "execution_id": execution_id,
            "allocations": execution.get("allocations", []),
            "message": "Execution approved. Use external wallet to execute trades."
        }
    
    async def mark_execution_complete(self, execution_id: str, completed_swaps: List[Dict], user_id: str) -> Dict[str, Any]:
        """Mark auto-invest execution as complete with user verification"""
        execution = await self.db.auto_invest_executions.find_one(
            {"execution_id": execution_id},
            {"_id": 0}
        )
        
        if not execution:
            return {"success": False, "error": "Execution not found"}
        
        if execution.get("user_id") != user_id:
            return {"success": False, "error": "Unauthorized: execution belongs to another user"}
        
        await self.db.auto_invest_executions.update_one(
            {"execution_id": execution_id},
            {"$set": {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "completed_swaps": completed_swaps
            }}
        )
        
        execution = await self.db.auto_invest_executions.find_one(
            {"execution_id": execution_id},
            {"_id": 0}
        )
        
        if execution:
            await self.db.auto_invest_configs.update_one(
                {"user_id": execution["user_id"]},
                {"$set": {"last_executed": datetime.now(timezone.utc).isoformat()}}
            )
        
        if execution_id in self.pending_executions:
            del self.pending_executions[execution_id]
        
        return {"success": True}
    
    async def get_execution_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get user's auto-invest execution history"""
        executions = await self.db.auto_invest_executions.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(limit)
        
        return executions
