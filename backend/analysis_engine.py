"""
Market Analysis Engine - Mathematical analysis of crypto market trends
Provides deterministic, explainable analysis for AI recommendations
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import statistics

logger = logging.getLogger(__name__)


class AnalysisEngine:
    """
    Engine for analyzing cryptocurrency market data.
    All logic is mathematical, deterministic, and explainable.
    """
    
    def __init__(self, db, market_provider):
        self.db = db
        self.market_provider = market_provider
        logger.info("Analysis Engine initialized")
    
    async def analyze_market_conditions(self, coins: List[Dict]) -> Dict[str, Any]:
        """Analyze overall market conditions"""
        if not coins:
            return {"status": "no_data", "sentiment": "neutral"}
        
        positive_1h = sum(1 for c in coins if (c.get("change1h") or 0) > 0)
        negative_1h = sum(1 for c in coins if (c.get("change1h") or 0) < 0)
        
        positive_24h = sum(1 for c in coins if (c.get("change24h") or 0) > 0)
        negative_24h = sum(1 for c in coins if (c.get("change24h") or 0) < 0)
        
        avg_change_1h = statistics.mean([c.get("change1h") or 0 for c in coins])
        avg_change_24h = statistics.mean([c.get("change24h") or 0 for c in coins])
        
        if avg_change_24h > 3:
            sentiment = "bullish"
        elif avg_change_24h > 0:
            sentiment = "slightly_bullish"
        elif avg_change_24h > -3:
            sentiment = "slightly_bearish"
        else:
            sentiment = "bearish"
        
        volatility = statistics.stdev([c.get("change24h") or 0 for c in coins]) if len(coins) > 1 else 0
        
        if volatility > 10:
            volatility_level = "extreme"
        elif volatility > 5:
            volatility_level = "high"
        elif volatility > 2:
            volatility_level = "moderate"
        else:
            volatility_level = "low"
        
        return {
            "status": "analyzed",
            "sentiment": sentiment,
            "volatility": volatility,
            "volatility_level": volatility_level,
            "avg_change_1h": round(avg_change_1h, 2),
            "avg_change_24h": round(avg_change_24h, 2),
            "positive_1h_count": positive_1h,
            "negative_1h_count": negative_1h,
            "positive_24h_count": positive_24h,
            "negative_24h_count": negative_24h,
            "total_coins": len(coins),
            "analysis_time": datetime.now(timezone.utc).isoformat()
        }
    
    def calculate_momentum_score(self, coin: Dict) -> float:
        """
        Calculate momentum score for a coin.
        Score range: -100 (strong downward) to +100 (strong upward)
        """
        change_1h = coin.get("change1h") or 0
        change_24h = coin.get("change24h") or 0
        change_7d = coin.get("change7d") or 0
        
        weighted_momentum = (
            change_1h * 0.4 +
            change_24h * 0.35 +
            change_7d * 0.25
        )
        
        return max(-100, min(100, weighted_momentum))
    
    def calculate_volatility_score(self, coin: Dict) -> float:
        """
        Calculate volatility score for a coin.
        Score range: 0 (stable) to 100 (extremely volatile)
        """
        change_1h = abs(coin.get("change1h") or 0)
        change_24h = abs(coin.get("change24h") or 0)
        change_7d = abs(coin.get("change7d") or 0)
        
        avg_volatility = (change_1h + change_24h + change_7d) / 3
        
        score = min(100, avg_volatility * 5)
        
        return round(score, 2)
    
    def calculate_trend_strength(self, coin: Dict) -> Dict[str, Any]:
        """
        Calculate trend strength and direction.
        Returns trend direction and strength score.
        """
        change_1h = coin.get("change1h") or 0
        change_24h = coin.get("change24h") or 0
        change_7d = coin.get("change7d") or 0
        
        all_positive = change_1h > 0 and change_24h > 0 and change_7d > 0
        all_negative = change_1h < 0 and change_24h < 0 and change_7d < 0
        
        if all_positive:
            direction = "uptrend"
            strength = min(100, (abs(change_1h) + abs(change_24h) + abs(change_7d)) / 3 * 5)
        elif all_negative:
            direction = "downtrend"
            strength = min(100, (abs(change_1h) + abs(change_24h) + abs(change_7d)) / 3 * 5)
        else:
            direction = "sideways"
            strength = 0
            
            if change_1h > 0 and change_24h > 0:
                direction = "recovering"
                strength = min(100, (change_1h + change_24h) * 2.5)
            elif change_1h < 0 and change_24h < 0:
                direction = "weakening"
                strength = min(100, (abs(change_1h) + abs(change_24h)) * 2.5)
        
        return {
            "direction": direction,
            "strength": round(strength, 2),
            "consistent": all_positive or all_negative
        }
    
    def calculate_volume_vs_price(self, coin: Dict) -> Dict[str, Any]:
        """
        Analyze relationship between volume and price movement.
        High volume with price drop = potential reversal opportunity.
        """
        volume_24h = coin.get("volume24h") or 0
        market_cap = coin.get("marketCap") or 0
        change_24h = coin.get("change24h") or 0
        
        if market_cap == 0:
            return {"ratio": 0, "signal": "unknown", "explanation": "No market cap data"}
        
        volume_ratio = volume_24h / market_cap
        
        if volume_ratio > 0.3 and change_24h < -5:
            signal = "capitulation"
            explanation = "High volume selling - potential reversal if fundamentals intact"
        elif volume_ratio > 0.3 and change_24h > 5:
            signal = "euphoria"
            explanation = "High volume buying - possible top forming"
        elif volume_ratio > 0.1 and change_24h < -3:
            signal = "distribution"
            explanation = "Elevated selling pressure"
        elif volume_ratio > 0.1 and change_24h > 3:
            signal = "accumulation"
            explanation = "Elevated buying pressure"
        elif volume_ratio < 0.02:
            signal = "low_interest"
            explanation = "Low trading activity - be cautious"
        else:
            signal = "normal"
            explanation = "Normal trading activity"
        
        return {
            "ratio": round(volume_ratio, 4),
            "signal": signal,
            "explanation": explanation
        }
    
    async def get_full_analysis(self, coins: List[Dict]) -> Dict[str, Any]:
        """Get comprehensive market analysis"""
        market_conditions = await self.analyze_market_conditions(coins)
        
        analyzed_coins = []
        for coin in coins[:100]:
            momentum = self.calculate_momentum_score(coin)
            volatility = self.calculate_volatility_score(coin)
            trend = self.calculate_trend_strength(coin)
            volume_signal = self.calculate_volume_vs_price(coin)
            
            analyzed_coins.append({
                "symbol": coin.get("symbol"),
                "name": coin.get("name"),
                "price_usdt": coin.get("price"),
                "change_1h": coin.get("change1h"),
                "change_24h": coin.get("change24h"),
                "change_7d": coin.get("change7d"),
                "momentum_score": momentum,
                "volatility_score": volatility,
                "trend": trend,
                "volume_signal": volume_signal,
                "logo": coin.get("logo")
            })
        
        analyzed_coins.sort(key=lambda x: x["momentum_score"], reverse=True)
        
        return {
            "market_conditions": market_conditions,
            "top_momentum": analyzed_coins[:10],
            "worst_momentum": analyzed_coins[-10:],
            "all_coins": analyzed_coins,
            "analysis_time": datetime.now(timezone.utc).isoformat()
        }


analysis_engine = None

def init_analysis_engine(db, market_provider):
    global analysis_engine
    analysis_engine = AnalysisEngine(db, market_provider)
    return analysis_engine
