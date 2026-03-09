"""
Dump Detection Engine - Detects 3%+ price dumps for buy opportunities
Core strategy: Buy the dip when quality coins dump ≥3%
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

DUMP_THRESHOLD = -3.0
PUMP_THRESHOLD = 5.0
MIN_VOLUME_24H = 1_000_000
MIN_MARKET_CAP = 10_000_000
MAX_RANK = 100


@dataclass
class DumpSignal:
    """Represents a detected dump opportunity"""
    symbol: str
    name: str
    price_usdt: float
    change_1h: float
    change_24h: float
    change_7d: float
    volume_24h: float
    market_cap: float
    rank: int
    dump_magnitude: float
    dump_window: str
    volume_health: str
    risk_score: float
    recommendation: str
    reason: str
    detected_at: str


class DumpDetectionEngine:
    """
    Engine for detecting dump opportunities in the market.
    Implements the 5% dump buy strategy with volume validation.
    """
    
    def __init__(self, db, market_provider):
        self.db = db
        self.market_provider = market_provider
        self.price_history: Dict[str, List[Dict]] = {}
        logger.info("Dump Detection Engine initialized")
    
    async def analyze_market(self, coins: List[Dict]) -> Dict[str, Any]:
        """
        Analyze top 100 coins for dump opportunities.
        Returns categorized signals: dump_opportunities, pump_risks, neutral
        """
        dump_opportunities = []
        pump_risks = []
        neutral = []
        avoid_list = []
        
        for coin in coins[:MAX_RANK]:
            analysis = self._analyze_coin(coin)
            
            if analysis["category"] == "dump_opportunity":
                dump_opportunities.append(analysis)
            elif analysis["category"] == "pump_risk":
                pump_risks.append(analysis)
            elif analysis["category"] == "avoid":
                avoid_list.append(analysis)
            else:
                neutral.append(analysis)
        
        dump_opportunities.sort(key=lambda x: x["dump_magnitude"], reverse=True)
        
        return {
            "dump_opportunities": dump_opportunities[:10],
            "pump_risks": pump_risks[:10],
            "neutral": neutral,
            "avoid_list": avoid_list,
            "analysis_time": datetime.now(timezone.utc).isoformat(),
            "total_analyzed": len(coins[:MAX_RANK])
        }
    
    def _analyze_coin(self, coin: Dict) -> Dict[str, Any]:
        """Analyze a single coin for dump/pump signals"""
        symbol = coin.get("symbol", "")
        name = coin.get("name", "")
        price = coin.get("price", 0)
        change_1h = coin.get("change1h", 0) or 0
        change_24h = coin.get("change24h", 0) or 0
        change_7d = coin.get("change7d", 0) or 0
        volume_24h = coin.get("volume24h", 0) or 0
        market_cap = coin.get("marketCap", 0) or 0
        rank = coin.get("rank", 999)
        
        category = "neutral"
        dump_magnitude = 0
        dump_window = "none"
        recommendation = "hold"
        reason = ""
        risk_score = 0.5
        
        volume_health = self._assess_volume_health(volume_24h, market_cap, price)
        
        if change_1h <= DUMP_THRESHOLD:
            dump_magnitude = abs(change_1h)
            dump_window = "1h"
        elif change_24h <= DUMP_THRESHOLD:
            dump_magnitude = abs(change_24h)
            dump_window = "24h"
        
        if dump_magnitude > 0:
            if volume_health == "healthy" and market_cap >= MIN_MARKET_CAP:
                if change_7d > -30:
                    category = "dump_opportunity"
                    recommendation = "buy"
                    risk_score = self._calculate_risk_score(
                        dump_magnitude, volume_health, change_7d, market_cap
                    )
                    reason = f"5% dump detected ({dump_window}). Volume healthy. Not in long-term decline."
                else:
                    category = "avoid"
                    recommendation = "avoid"
                    reason = f"Dump detected but coin in long-term decline (-{abs(change_7d):.1f}% 7d). Possible breakdown."
            else:
                category = "avoid"
                recommendation = "avoid"
                reason = f"Dump detected but volume unhealthy or market cap too low."
        
        elif change_1h >= PUMP_THRESHOLD or change_24h >= PUMP_THRESHOLD:
            category = "pump_risk"
            recommendation = "avoid"
            pump_window = "1h" if change_1h >= PUMP_THRESHOLD else "24h"
            pump_pct = change_1h if change_1h >= PUMP_THRESHOLD else change_24h
            reason = f"Coin pumped +{pump_pct:.1f}% in {pump_window}. Overheated - do not chase."
            risk_score = 0.8
        
        else:
            category = "neutral"
            recommendation = "hold"
            reason = "No significant dump or pump detected."
            risk_score = 0.5
        
        result = {
            "symbol": symbol,
            "name": name,
            "price_usdt": price,
            "change_1h": change_1h,
            "change_24h": change_24h,
            "change_7d": change_7d,
            "volume_24h": volume_24h,
            "market_cap": market_cap,
            "rank": rank,
            "category": category,
            "dump_magnitude": dump_magnitude,
            "dump_window": dump_window,
            "volume_health": volume_health,
            "risk_score": risk_score,
            "recommendation": recommendation,
            "reason": reason,
            "logo": coin.get("logo", "")
        }
        
        if coin.get("contract_address"):
            result["contract_address"] = coin["contract_address"]
            result["platform"] = coin.get("platform", "")
        
        return result
    
    def _assess_volume_health(self, volume_24h: float, market_cap: float, price: float) -> str:
        """Assess if trading volume is healthy"""
        if volume_24h < MIN_VOLUME_24H:
            return "low"
        
        if market_cap > 0:
            volume_to_mcap = volume_24h / market_cap
            if volume_to_mcap < 0.01:
                return "low"
            elif volume_to_mcap > 0.5:
                return "high"
            else:
                return "healthy"
        
        return "unknown"
    
    def _calculate_risk_score(
        self, 
        dump_magnitude: float, 
        volume_health: str, 
        change_7d: float,
        market_cap: float
    ) -> float:
        """
        Calculate risk score for a dump opportunity.
        Lower score = less risky = better opportunity.
        Range: 0.0 (best) to 1.0 (worst)
        """
        score = 0.5
        
        if dump_magnitude >= 10:
            score -= 0.1
        elif dump_magnitude >= 7:
            score -= 0.05
        
        if volume_health == "healthy":
            score -= 0.1
        elif volume_health == "high":
            score -= 0.05
        elif volume_health == "low":
            score += 0.15
        
        if change_7d > 0:
            score -= 0.1
        elif change_7d > -10:
            score -= 0.05
        elif change_7d < -20:
            score += 0.15
        
        if market_cap > 10_000_000_000:
            score -= 0.1
        elif market_cap > 1_000_000_000:
            score -= 0.05
        elif market_cap < 100_000_000:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    async def get_dump_opportunities(self) -> List[Dict]:
        """Get current dump opportunities from the market"""
        coins = await self.market_provider.get_coins_list(100)
        analysis = await self.analyze_market(coins)
        return analysis["dump_opportunities"]
    
    async def store_price_snapshot(self, coins: List[Dict]):
        """Store price snapshot for historical tracking"""
        timestamp = datetime.now(timezone.utc)
        
        for coin in coins[:100]:
            symbol = coin.get("symbol", "")
            if symbol not in self.price_history:
                self.price_history[symbol] = []
            
            self.price_history[symbol].append({
                "price": coin.get("price", 0),
                "timestamp": timestamp.isoformat(),
                "change_1h": coin.get("change1h", 0),
                "change_24h": coin.get("change24h", 0)
            })
            
            if len(self.price_history[symbol]) > 288:
                self.price_history[symbol] = self.price_history[symbol][-288:]


dump_detection_engine = None

def init_dump_detection_engine(db, market_provider):
    global dump_detection_engine
    dump_detection_engine = DumpDetectionEngine(db, market_provider)
    return dump_detection_engine
