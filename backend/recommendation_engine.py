"""
AI Recommendation Engine - Combines all signals into actionable recommendations
Provides explainable AI-driven investment advice based on dump detection and trend analysis
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Combines signals from dump detection, analysis engine, and market data
    to produce actionable investment recommendations.
    All recommendations are explainable and deterministic.
    """
    
    def __init__(self, db, dump_detection_engine, analysis_engine, market_provider):
        self.db = db
        self.dump_engine = dump_detection_engine
        self.analysis_engine = analysis_engine
        self.market_provider = market_provider
        logger.info("AI Recommendation Engine initialized")
    
    async def get_recommendations(self, user_id: str, investment_amount: float) -> Dict[str, Any]:
        """
        Generate comprehensive investment recommendations.
        Returns dump-buy candidates, trend-follow candidates, and avoid list.
        """
        coins = await self.market_provider.get_coins_list(100)
        
        dump_analysis = await self.dump_engine.analyze_market(coins)
        market_analysis = await self.analysis_engine.get_full_analysis(coins)
        
        dump_opportunities = dump_analysis.get("dump_opportunities", [])
        pump_risks = dump_analysis.get("pump_risks", [])
        avoid_list = dump_analysis.get("avoid_list", [])
        
        trend_candidates = self._identify_trend_candidates(
            market_analysis.get("all_coins", []),
            pump_risks
        )
        
        dump_allocation = min(investment_amount * 0.4, investment_amount)
        trend_allocation = investment_amount - dump_allocation if dump_opportunities else investment_amount
        
        dump_recommendations = self._create_recommendations(
            dump_opportunities[:5],
            dump_allocation,
            "dump_buy"
        )
        
        trend_recommendations = self._create_recommendations(
            trend_candidates[:5],
            trend_allocation,
            "trend_follow"
        )
        
        all_recommendations = dump_recommendations + trend_recommendations
        
        explanations = self._generate_explanations(
            dump_opportunities,
            trend_candidates,
            market_analysis.get("market_conditions", {}),
            investment_amount
        )
        
        await self._store_recommendations(user_id, all_recommendations, explanations)
        
        return {
            "success": True,
            "investment_amount_usdt": investment_amount,
            "market_conditions": market_analysis.get("market_conditions", {}),
            "dump_opportunities": dump_recommendations,
            "trend_candidates": trend_recommendations,
            "avoid_list": [
                {
                    "symbol": c.get("symbol"),
                    "reason": c.get("reason"),
                    "price_usdt": c.get("price_usdt")
                }
                for c in (avoid_list + pump_risks)[:10]
            ],
            "total_recommendations": len(all_recommendations),
            "explanations": explanations,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _identify_trend_candidates(
        self,
        analyzed_coins: List[Dict],
        pump_risks: List[Dict]
    ) -> List[Dict]:
        """Identify coins with strong positive trends that aren't overheated"""
        pump_symbols = {c.get("symbol") for c in pump_risks}
        
        candidates = []
        for coin in analyzed_coins:
            symbol = coin.get("symbol")
            
            if symbol in pump_symbols:
                continue
            
            trend = coin.get("trend", {})
            momentum = coin.get("momentum_score", 0)
            volatility = coin.get("volatility_score", 0)
            
            if (
                trend.get("direction") in ["uptrend", "recovering"] and
                momentum > 0 and
                momentum < 20 and
                volatility < 50
            ):
                risk_score = 0.3 + (volatility / 200) + (abs(momentum) / 200)
                risk_score = min(0.7, risk_score)
                
                candidates.append({
                    "symbol": symbol,
                    "name": coin.get("name"),
                    "price_usdt": coin.get("price_usdt"),
                    "change_1h": coin.get("change_1h"),
                    "change_24h": coin.get("change_24h"),
                    "momentum_score": momentum,
                    "trend_direction": trend.get("direction"),
                    "trend_strength": trend.get("strength"),
                    "risk_score": round(risk_score, 2),
                    "reason": f"Positive momentum ({momentum:.1f}), {trend.get('direction')} trend",
                    "logo": coin.get("logo", "")
                })
        
        candidates.sort(key=lambda x: x["momentum_score"], reverse=True)
        return candidates
    
    def _create_recommendations(
        self,
        candidates: List[Dict],
        total_allocation: float,
        strategy: str
    ) -> List[Dict]:
        """Create allocation recommendations from candidates"""
        if not candidates or total_allocation <= 0:
            return []
        
        total_inverse_risk = sum(1 - c.get("risk_score", 0.5) for c in candidates)
        
        recommendations = []
        max_per_coin = total_allocation * 0.25
        remaining = total_allocation
        
        for candidate in candidates:
            if remaining < 10:
                break
            
            risk_score = candidate.get("risk_score", 0.5)
            inverse_risk = 1 - risk_score
            
            weight = inverse_risk / total_inverse_risk if total_inverse_risk > 0 else 1 / len(candidates)
            allocation = min(total_allocation * weight, max_per_coin, remaining)
            
            if allocation >= 10:
                recommendations.append({
                    "symbol": candidate.get("symbol"),
                    "name": candidate.get("name"),
                    "strategy": strategy,
                    "allocation_usdt": round(allocation, 2),
                    "allocation_percent": round(allocation / total_allocation * 100, 1),
                    "price_usdt": candidate.get("price_usdt"),
                    "risk_score": risk_score,
                    "reason": candidate.get("reason"),
                    "change_1h": candidate.get("change_1h"),
                    "change_24h": candidate.get("change_24h"),
                    "logo": candidate.get("logo", "")
                })
                remaining -= allocation
        
        return recommendations
    
    def _generate_explanations(
        self,
        dump_opportunities: List[Dict],
        trend_candidates: List[Dict],
        market_conditions: Dict,
        investment_amount: float
    ) -> List[str]:
        """Generate human-readable explanations for the recommendations"""
        explanations = []
        
        sentiment = market_conditions.get("sentiment", "neutral")
        volatility_level = market_conditions.get("volatility_level", "moderate")
        
        explanations.append(
            f"Market sentiment: {sentiment.replace('_', ' ').title()}. "
            f"Volatility: {volatility_level}."
        )
        
        if dump_opportunities:
            symbols = ", ".join([d.get("symbol", "") for d in dump_opportunities[:3]])
            explanations.append(
                f"5% dump detected in: {symbols}. "
                f"Volume confirmation passed. These are potential buy opportunities."
            )
            
            for opp in dump_opportunities[:2]:
                explanations.append(
                    f"{opp.get('symbol')}: {opp.get('dump_magnitude', 0):.1f}% dump in {opp.get('dump_window', '24h')}. "
                    f"Risk score: {opp.get('risk_score', 0.5):.2f}."
                )
        else:
            explanations.append(
                "No significant dump opportunities detected in top 100 coins at this time."
            )
        
        if trend_candidates:
            trend_symbols = ", ".join([t.get("symbol", "") for t in trend_candidates[:3]])
            explanations.append(
                f"Strong trend candidates: {trend_symbols}. "
                f"These show positive momentum without being overheated."
            )
        
        dump_allocation = min(investment_amount * 0.4, investment_amount) if dump_opportunities else 0
        trend_allocation = investment_amount - dump_allocation
        
        if dump_allocation > 0 and trend_allocation > 0:
            explanations.append(
                f"Allocation strategy: {dump_allocation:.0f} USDT (40%) for dump-buy opportunities, "
                f"{trend_allocation:.0f} USDT (60%) for trend-following positions."
            )
        
        return explanations
    
    async def _store_recommendations(
        self,
        user_id: str,
        recommendations: List[Dict],
        explanations: List[str]
    ):
        """Store recommendations in database for tracking"""
        record = {
            "user_id": user_id,
            "recommendations": recommendations,
            "explanations": explanations,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.ai_recommendations.insert_one(record)
    
    async def get_quick_signals(self) -> Dict[str, Any]:
        """Get quick market signals for dashboard display"""
        coins = await self.market_provider.get_coins_list(100)
        dump_analysis = await self.dump_engine.analyze_market(coins)
        
        dump_count = len(dump_analysis.get("dump_opportunities", []))
        pump_count = len(dump_analysis.get("pump_risks", []))
        
        if dump_count >= 3:
            signal = "dump_opportunity"
            message = f"{dump_count} coins showing 5%+ dumps - buy opportunities available"
        elif pump_count >= 5:
            signal = "pump_risk"
            message = f"{pump_count} coins overheated - avoid chasing pumps"
        else:
            signal = "neutral"
            message = "Market stable - no significant opportunities detected"
        
        return {
            "signal": signal,
            "message": message,
            "dump_count": dump_count,
            "pump_count": pump_count,
            "top_dump": dump_analysis.get("dump_opportunities", [{}])[0] if dump_count > 0 else None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }


recommendation_engine = None

def init_recommendation_engine(db, dump_engine, analysis_engine, market_provider):
    global recommendation_engine
    recommendation_engine = RecommendationEngine(db, dump_engine, analysis_engine, market_provider)
    return recommendation_engine
