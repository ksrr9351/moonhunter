"""
Perplexity AI Client for crypto investment analysis and recommendations
"""
import httpx
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class PerplexityClient:
    """Client for interacting with Perplexity AI API"""
    
    BASE_URL = "https://api.perplexity.ai"
    SONAR_MODEL = "sonar"
    
    def __init__(self, api_key: str = None, timeout: int = 30):
        self.api_key = api_key or os.environ.get("PERPLEXITY_API_KEY")
        self.enabled = bool(self.api_key)
        if not self.enabled:
            logger.warning("Perplexity API key not configured - AI features will be disabled")
        
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
            "Content-Type": "application/json"
        }
    
    async def get_portfolio_recommendations(
        self,
        risk_tolerance: str,
        investment_amount: float,
        investment_horizon: str = "medium-term"
    ) -> Dict[str, Any]:
        """Get AI-powered portfolio recommendations based on user preferences"""
        if not self.enabled:
            return {
                "recommendation": "AI recommendations are not available. Please configure the Perplexity API key to enable this feature.",
                "generated_at": datetime.utcnow().isoformat(),
                "disabled": True
            }
        
        prompt = f"""As a cryptocurrency investment advisor, provide a detailed portfolio recommendation for:

Investment Amount: ${investment_amount:,.2f}
Risk Tolerance: {risk_tolerance}
Investment Horizon: {investment_horizon}

Please provide:
1. A diversified portfolio allocation with specific cryptocurrencies
2. Percentage allocation for each crypto
3. Brief rationale for each selection
4. Risk assessment
5. Expected return range

Format the response as a structured recommendation with clear allocations."""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    json={
                        "model": self.SONAR_MODEL,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert cryptocurrency investment advisor with deep knowledge of blockchain technology and market analysis."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.7,
                        "max_tokens": 2000
                    },
                    headers=self.headers
                )
                response.raise_for_status()
                
                result = response.json()
                return {
                    "recommendation": result["choices"][0]["message"]["content"],
                    "generated_at": datetime.utcnow().isoformat()
                }
        
        except httpx.HTTPError as e:
            logger.error(f"Perplexity API error: {str(e)}")
            raise PerplexityAPIException(f"Failed to get recommendations: {str(e)}")
    
    async def analyze_market_trends(
        self,
        cryptocurrencies: List[str]
    ) -> Dict[str, Any]:
        """Analyze current market trends for specific cryptocurrencies"""
        if not self.enabled:
            return {
                "analysis": "Market analysis is not available. Please configure the Perplexity API key to enable this feature.",
                "timestamp": datetime.utcnow().isoformat(),
                "disabled": True
            }
        
        crypto_list = ", ".join(cryptocurrencies)
        prompt = f"""Provide a comprehensive market analysis for the following cryptocurrencies: {crypto_list}.

For each cryptocurrency, include:
1. Current price trend (bullish/bearish/neutral)
2. Key market drivers
3. Technical indicators
4. Short-term outlook (next 7-30 days)

Keep the analysis concise and actionable."""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    json={
                        "model": self.SONAR_MODEL,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.5,
                        "max_tokens": 1500
                    },
                    headers=self.headers
                )
                response.raise_for_status()
                
                result = response.json()
                return {
                    "analysis": result["choices"][0]["message"]["content"],
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        except httpx.HTTPError as e:
            logger.error(f"Market analysis failed: {str(e)}")
            raise PerplexityAPIException(f"Failed to analyze market: {str(e)}")
    
    async def get_investment_insights(
        self,
        current_portfolio: Dict[str, float],
        market_conditions: str = "current"
    ) -> Dict[str, Any]:
        """Get AI insights for an existing portfolio"""
        if not self.enabled:
            return {
                "insights": "Portfolio insights are not available. Please configure the Perplexity API key to enable this feature.",
                "generated_at": datetime.utcnow().isoformat(),
                "disabled": True
            }
        
        portfolio_str = "\n".join([f"- {crypto}: {amount:.4f} units" 
                                   for crypto, amount in current_portfolio.items()])
        
        prompt = f"""Analyze the following cryptocurrency portfolio and provide actionable insights:

Current Holdings:
{portfolio_str}

Market Conditions: {market_conditions}

Please provide:
1. Portfolio health assessment
2. Rebalancing recommendations
3. Risk factors to watch
4. Potential opportunities
5. Suggested actions (buy/sell/hold)

Be specific and actionable."""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    json={
                        "model": self.SONAR_MODEL,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert portfolio manager specializing in cryptocurrency investments."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.6,
                        "max_tokens": 1800
                    },
                    headers=self.headers
                )
                response.raise_for_status()
                
                result = response.json()
                return {
                    "insights": result["choices"][0]["message"]["content"],
                    "generated_at": datetime.utcnow().isoformat()
                }
        
        except httpx.HTTPError as e:
            logger.error(f"Portfolio insights failed: {str(e)}")
            raise PerplexityAPIException(f"Failed to get insights: {str(e)}")


class PerplexityAPIException(Exception):
    """Custom exception for Perplexity API errors"""
    pass
