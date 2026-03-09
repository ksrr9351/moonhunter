"""
Backtesting Engine for Moon Hunters
Simulates trading strategies on REAL historical data from CoinGecko
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import math

logger = logging.getLogger("backtesting")


class BacktestingEngine:
    def __init__(self, market_provider, historical_provider=None):
        self.market_provider = market_provider
        self.historical_provider = historical_provider
        logger.info("Backtesting Engine initialized with real historical data support")
    
    def set_historical_provider(self, provider):
        """Set the historical data provider"""
        self.historical_provider = provider
    
    async def run_backtest(
        self,
        strategy: str,
        initial_capital: float,
        start_date: str,
        end_date: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run a backtest simulation using REAL historical data"""
        
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            start_dt = datetime.now(timezone.utc) - timedelta(days=90)
            end_dt = datetime.now(timezone.utc)
        
        days = (end_dt - start_dt).days
        if days < 7:
            days = 30
            start_dt = end_dt - timedelta(days=days)
        
        if days > 365:
            days = 365
            start_dt = end_dt - timedelta(days=days)
        
        if strategy == "dump_buy":
            return await self._backtest_dump_buy(initial_capital, start_dt, end_dt, days, params)
        elif strategy == "trend_follow":
            return await self._backtest_trend_follow(initial_capital, start_dt, end_dt, days, params)
        elif strategy == "dca":
            return await self._backtest_dca(initial_capital, start_dt, end_dt, days, params)
        elif strategy == "momentum":
            return await self._backtest_momentum(initial_capital, start_dt, end_dt, days, params)
        else:
            return await self._backtest_dump_buy(initial_capital, start_dt, end_dt, days, params)
    
    async def _get_historical_prices(self, symbols: List[str], days: int) -> Dict[str, List[Dict]]:
        """Fetch real historical prices for multiple coins"""
        if not self.historical_provider:
            logger.warning("No historical provider available, cannot run backtest")
            return {}
        
        return await self.historical_provider.get_multiple_coins_history(symbols, days)
    
    def _calculate_daily_returns(self, candles: List[Dict]) -> List[float]:
        """Calculate daily percentage returns from OHLC data"""
        returns = []
        for i in range(1, len(candles)):
            prev_close = candles[i-1]["close"]
            curr_close = candles[i]["close"]
            if prev_close > 0:
                daily_return = ((curr_close - prev_close) / prev_close) * 100
                returns.append(daily_return)
        return returns
    
    def _find_dumps(self, candles: List[Dict], threshold: float) -> List[Dict]:
        """Find price dumps exceeding threshold percentage"""
        dumps = []
        for i in range(1, len(candles)):
            prev_close = candles[i-1]["close"]
            curr_close = candles[i]["close"]
            if prev_close > 0:
                change = ((curr_close - prev_close) / prev_close) * 100
                if change <= -threshold:
                    dumps.append({
                        "index": i,
                        "date": candles[i]["date"],
                        "price": curr_close,
                        "drop_pct": abs(change)
                    })
        return dumps
    
    async def _backtest_dump_buy(
        self,
        initial_capital: float,
        start_dt: datetime,
        end_dt: datetime,
        days: int,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Backtest dump buy strategy using REAL historical data"""
        
        dump_threshold = params.get("dump_threshold", 5.0)
        take_profit = params.get("take_profit", 10.0)
        stop_loss = params.get("stop_loss", 8.0)
        max_positions = params.get("max_positions", 5)
        
        # Use fewer coins to avoid CoinGecko rate limits (free tier: 30 req/min)
        symbols = ["BTC", "ETH", "SOL", "XRP", "DOGE"]
        
        historical_data = await self._get_historical_prices(symbols, days + 30)
        
        if not historical_data:
            return self._empty_result("dump_buy", initial_capital, days, "No historical data available")
        
        capital = initial_capital
        peak_capital = initial_capital
        max_drawdown = 0
        trades = []
        open_positions = []
        daily_equity = []
        
        all_dates = set()
        for symbol, candles in historical_data.items():
            for candle in candles:
                all_dates.add(candle["date"])
        
        sorted_dates = sorted(list(all_dates))
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")
        trading_dates = [d for d in sorted_dates if start_str <= d <= end_str]
        
        if not trading_dates:
            return self._empty_result("dump_buy", initial_capital, days, "No trading dates in range")
        
        price_lookup = {}
        for symbol, candles in historical_data.items():
            price_lookup[symbol] = {c["date"]: c for c in candles}
        
        for date in trading_dates:
            closed_today = []
            for pos in open_positions[:]:
                symbol = pos["symbol"]
                if symbol in price_lookup and date in price_lookup[symbol]:
                    current_price = price_lookup[symbol][date]["close"]
                    entry_price = pos["entry_price"]
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    
                    if pnl_pct >= take_profit:
                        pnl = pos["size"] * (pnl_pct / 100)
                        capital += pos["size"] + pnl
                        trades.append({
                            "coin": symbol,
                            "entry_date": pos["entry_date"],
                            "exit_date": date,
                            "entry_price": round(entry_price, 4),
                            "exit_price": round(current_price, 4),
                            "position_size": round(pos["size"], 2),
                            "pnl": round(pnl, 2),
                            "pnl_percent": round(pnl_pct, 2),
                            "status": "closed",
                            "exit_reason": "take_profit"
                        })
                        open_positions.remove(pos)
                        closed_today.append(symbol)
                    
                    elif pnl_pct <= -stop_loss:
                        pnl = pos["size"] * (pnl_pct / 100)
                        capital += pos["size"] + pnl
                        trades.append({
                            "coin": symbol,
                            "entry_date": pos["entry_date"],
                            "exit_date": date,
                            "entry_price": round(entry_price, 4),
                            "exit_price": round(current_price, 4),
                            "position_size": round(pos["size"], 2),
                            "pnl": round(pnl, 2),
                            "pnl_percent": round(pnl_pct, 2),
                            "status": "closed",
                            "exit_reason": "stop_loss"
                        })
                        open_positions.remove(pos)
                        closed_today.append(symbol)
            
            if len(open_positions) < max_positions:
                for symbol, candles_dict in price_lookup.items():
                    if symbol in closed_today:
                        continue
                    if symbol in [p["symbol"] for p in open_positions]:
                        continue
                    if len(open_positions) >= max_positions:
                        break
                    
                    if date in candles_dict:
                        candle = candles_dict[date]
                        prev_dates = [d for d in sorted_dates if d < date]
                        if prev_dates:
                            prev_date = prev_dates[-1]
                            if prev_date in candles_dict:
                                prev_price = candles_dict[prev_date]["close"]
                                curr_price = candle["close"]
                                change = ((curr_price - prev_price) / prev_price) * 100
                                
                                if change <= -dump_threshold:
                                    position_size = min(capital * 0.2, initial_capital * 0.2)
                                    if position_size >= 10 and capital >= position_size:
                                        capital -= position_size
                                        open_positions.append({
                                            "symbol": symbol,
                                            "entry_date": date,
                                            "entry_price": curr_price,
                                            "size": position_size
                                        })
            
            portfolio_value = capital
            for pos in open_positions:
                symbol = pos["symbol"]
                if symbol in price_lookup and date in price_lookup[symbol]:
                    current_price = price_lookup[symbol][date]["close"]
                    entry_price = pos["entry_price"]
                    units = pos["size"] / entry_price
                    portfolio_value += units * current_price
            
            daily_equity.append({
                "date": date,
                "equity": round(portfolio_value, 2)
            })
            
            peak_capital = max(peak_capital, portfolio_value)
            if peak_capital > 0:
                drawdown = (peak_capital - portfolio_value) / peak_capital * 100
                max_drawdown = max(max_drawdown, drawdown)
        
        final_capital = capital
        for pos in open_positions:
            symbol = pos["symbol"]
            if trading_dates and symbol in price_lookup:
                last_date = trading_dates[-1]
                if last_date in price_lookup[symbol]:
                    current_price = price_lookup[symbol][last_date]["close"]
                    entry_price = pos["entry_price"]
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    pnl = pos["size"] * (pnl_pct / 100)
                    final_capital += pos["size"] + pnl
                    trades.append({
                        "coin": symbol,
                        "entry_date": pos["entry_date"],
                        "exit_date": trading_dates[-1],
                        "entry_price": round(entry_price, 4),
                        "exit_price": round(current_price, 4),
                        "position_size": round(pos["size"], 2),
                        "pnl": round(pnl, 2),
                        "pnl_percent": round(pnl_pct, 2),
                        "status": "closed",
                        "exit_reason": "end_of_backtest"
                    })
        
        return self._calculate_metrics(
            strategy="dump_buy",
            initial_capital=initial_capital,
            final_capital=final_capital,
            trades=trades,
            daily_equity=daily_equity,
            max_drawdown=max_drawdown,
            days=days,
            data_source="Real Historical Data"
        )
    
    async def _backtest_trend_follow(
        self,
        initial_capital: float,
        start_dt: datetime,
        end_dt: datetime,
        days: int,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Backtest trend following strategy using REAL historical data"""
        
        trend_period = params.get("trend_period", 20)
        take_profit = params.get("take_profit", 15.0)
        stop_loss = params.get("stop_loss", 5.0)
        
        # Use fewer coins to avoid CoinGecko rate limits (free tier: 30 req/min)
        symbols = ["BTC", "ETH", "SOL", "AVAX", "LINK"]
        
        historical_data = await self._get_historical_prices(symbols, days + trend_period + 30)
        
        if not historical_data:
            return self._empty_result("trend_follow", initial_capital, days, "No historical data available")
        
        capital = initial_capital
        peak_capital = initial_capital
        max_drawdown = 0
        trades = []
        open_positions = []
        daily_equity = []
        
        all_dates = set()
        for symbol, candles in historical_data.items():
            for candle in candles:
                all_dates.add(candle["date"])
        
        sorted_dates = sorted(list(all_dates))
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")
        trading_dates = [d for d in sorted_dates if start_str <= d <= end_str]
        
        if not trading_dates:
            return self._empty_result("trend_follow", initial_capital, days, "No trading dates in range")
        
        price_lookup = {}
        for symbol, candles in historical_data.items():
            price_lookup[symbol] = {c["date"]: c for c in candles}
        
        for i, date in enumerate(trading_dates):
            closed_today = []
            for pos in open_positions[:]:
                symbol = pos["symbol"]
                if symbol in price_lookup and date in price_lookup[symbol]:
                    current_price = price_lookup[symbol][date]["close"]
                    entry_price = pos["entry_price"]
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    
                    if pnl_pct >= take_profit or pnl_pct <= -stop_loss:
                        pnl = pos["size"] * (pnl_pct / 100)
                        capital += pos["size"] + pnl
                        trades.append({
                            "coin": symbol,
                            "entry_date": pos["entry_date"],
                            "exit_date": date,
                            "entry_price": round(entry_price, 4),
                            "exit_price": round(current_price, 4),
                            "position_size": round(pos["size"], 2),
                            "pnl": round(pnl, 2),
                            "pnl_percent": round(pnl_pct, 2),
                            "status": "closed",
                            "exit_reason": "take_profit" if pnl_pct > 0 else "stop_loss"
                        })
                        open_positions.remove(pos)
                        closed_today.append(symbol)
            
            if i % 7 == 0 and len(open_positions) < 3:
                for symbol in symbols:
                    if symbol in closed_today:
                        continue
                    if symbol in [p["symbol"] for p in open_positions]:
                        continue
                    if len(open_positions) >= 3:
                        break
                    
                    if symbol not in price_lookup:
                        continue
                    
                    candles_dict = price_lookup[symbol]
                    if date not in candles_dict:
                        continue
                    
                    lookback_dates = [d for d in sorted_dates if d < date][-trend_period:]
                    if len(lookback_dates) < trend_period // 2:
                        continue
                    
                    lookback_prices = []
                    for d in lookback_dates:
                        if d in candles_dict:
                            lookback_prices.append(candles_dict[d]["close"])
                    
                    if len(lookback_prices) < 5:
                        continue
                    
                    start_price = lookback_prices[0]
                    end_price = lookback_prices[-1]
                    trend_strength = ((end_price - start_price) / start_price) * 100
                    
                    if trend_strength >= 5.0:
                        position_size = min(capital * 0.15, initial_capital * 0.15)
                        if position_size >= 10 and capital >= position_size:
                            current_price = candles_dict[date]["close"]
                            capital -= position_size
                            open_positions.append({
                                "symbol": symbol,
                                "entry_date": date,
                                "entry_price": current_price,
                                "size": position_size
                            })
            
            portfolio_value = capital
            for pos in open_positions:
                symbol = pos["symbol"]
                if symbol in price_lookup and date in price_lookup[symbol]:
                    current_price = price_lookup[symbol][date]["close"]
                    entry_price = pos["entry_price"]
                    units = pos["size"] / entry_price
                    portfolio_value += units * current_price
            
            daily_equity.append({
                "date": date,
                "equity": round(portfolio_value, 2)
            })
            
            peak_capital = max(peak_capital, portfolio_value)
            if peak_capital > 0:
                drawdown = (peak_capital - portfolio_value) / peak_capital * 100
                max_drawdown = max(max_drawdown, drawdown)
        
        final_capital = capital
        for pos in open_positions:
            symbol = pos["symbol"]
            if trading_dates and symbol in price_lookup:
                last_date = trading_dates[-1]
                if last_date in price_lookup[symbol]:
                    current_price = price_lookup[symbol][last_date]["close"]
                    entry_price = pos["entry_price"]
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    pnl = pos["size"] * (pnl_pct / 100)
                    final_capital += pos["size"] + pnl
                    trades.append({
                        "coin": symbol,
                        "entry_date": pos["entry_date"],
                        "exit_date": trading_dates[-1],
                        "entry_price": round(entry_price, 4),
                        "exit_price": round(current_price, 4),
                        "position_size": round(pos["size"], 2),
                        "pnl": round(pnl, 2),
                        "pnl_percent": round(pnl_pct, 2),
                        "status": "closed",
                        "exit_reason": "end_of_backtest"
                    })
        
        return self._calculate_metrics(
            strategy="trend_follow",
            initial_capital=initial_capital,
            final_capital=final_capital,
            trades=trades,
            daily_equity=daily_equity,
            max_drawdown=max_drawdown,
            days=days,
            data_source="Real Historical Data"
        )
    
    async def _backtest_dca(
        self,
        initial_capital: float,
        start_dt: datetime,
        end_dt: datetime,
        days: int,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Backtest DCA strategy using REAL historical data"""
        
        interval_days = params.get("interval_days", 7)
        coins = params.get("coins", ["BTC", "ETH"])
        
        if isinstance(coins, str):
            coins = [coins]
        
        historical_data = await self._get_historical_prices(coins, days + 30)
        
        if not historical_data:
            return self._empty_result("dca", initial_capital, days, "No historical data available")
        
        remaining_capital = initial_capital
        trades = []
        daily_equity = []
        holdings = {coin: {"units": 0, "cost": 0} for coin in coins}
        
        all_dates = set()
        for symbol, candles in historical_data.items():
            for candle in candles:
                all_dates.add(candle["date"])
        
        sorted_dates = sorted(list(all_dates))
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")
        trading_dates = [d for d in sorted_dates if start_str <= d <= end_str]
        
        if not trading_dates:
            return self._empty_result("dca", initial_capital, days, "No trading dates in range")
        
        price_lookup = {}
        for symbol, candles in historical_data.items():
            price_lookup[symbol] = {c["date"]: c for c in candles}
        
        num_buys = len(trading_dates) // interval_days
        if num_buys == 0:
            num_buys = 1
        investment_per_buy = initial_capital / num_buys / len(coins)
        
        for i, date in enumerate(trading_dates):
            if i % interval_days == 0 and remaining_capital >= investment_per_buy * len(coins):
                for coin in coins:
                    if coin in price_lookup and date in price_lookup[coin]:
                        price = price_lookup[coin][date]["close"]
                        if remaining_capital >= investment_per_buy:
                            units = investment_per_buy / price
                            holdings[coin]["units"] += units
                            holdings[coin]["cost"] += investment_per_buy
                            remaining_capital -= investment_per_buy
                            
                            trades.append({
                                "coin": coin,
                                "entry_date": date,
                                "exit_date": None,
                                "entry_price": round(price, 4),
                                "exit_price": None,
                                "position_size": round(investment_per_buy, 2),
                                "units": round(units, 6),
                                "pnl": 0,
                                "pnl_percent": 0,
                                "status": "open"
                            })
            
            portfolio_value = remaining_capital
            for coin in coins:
                if coin in price_lookup and date in price_lookup[coin]:
                    current_price = price_lookup[coin][date]["close"]
                    portfolio_value += holdings[coin]["units"] * current_price
            
            daily_equity.append({
                "date": date,
                "equity": round(portfolio_value, 2)
            })
        
        final_capital = remaining_capital
        for coin in coins:
            if trading_dates and coin in price_lookup:
                last_date = trading_dates[-1]
                if last_date in price_lookup[coin]:
                    current_price = price_lookup[coin][last_date]["close"]
                    value = holdings[coin]["units"] * current_price
                    final_capital += value
        
        peak = max([e["equity"] for e in daily_equity]) if daily_equity else initial_capital
        trough = min([e["equity"] for e in daily_equity]) if daily_equity else initial_capital
        max_drawdown = (peak - trough) / peak * 100 if peak > 0 else 0
        
        return self._calculate_metrics(
            strategy="dca",
            initial_capital=initial_capital,
            final_capital=final_capital,
            trades=trades,
            daily_equity=daily_equity,
            max_drawdown=max_drawdown,
            days=days,
            data_source="Real Historical Data"
        )
    
    async def _backtest_momentum(
        self,
        initial_capital: float,
        start_dt: datetime,
        end_dt: datetime,
        days: int,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Backtest momentum strategy using REAL historical data"""
        
        holding_period = params.get("holding_period", 7)
        top_n = params.get("top_n", 3)
        
        symbols = ["SOL", "AVAX", "MATIC", "DOT", "ATOM", "NEAR", "LINK", "UNI", "AAVE", "INJ"]
        
        historical_data = await self._get_historical_prices(symbols, days + 30)
        
        if not historical_data:
            return self._empty_result("momentum", initial_capital, days, "No historical data available")
        
        capital = initial_capital
        peak_capital = initial_capital
        max_drawdown = 0
        trades = []
        open_positions = []
        daily_equity = []
        
        all_dates = set()
        for symbol, candles in historical_data.items():
            for candle in candles:
                all_dates.add(candle["date"])
        
        sorted_dates = sorted(list(all_dates))
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")
        trading_dates = [d for d in sorted_dates if start_str <= d <= end_str]
        
        if not trading_dates:
            return self._empty_result("momentum", initial_capital, days, "No trading dates in range")
        
        price_lookup = {}
        for symbol, candles in historical_data.items():
            price_lookup[symbol] = {c["date"]: c for c in candles}
        
        for i, date in enumerate(trading_dates):
            for pos in open_positions[:]:
                symbol = pos["symbol"]
                days_held = (datetime.strptime(date, "%Y-%m-%d") - 
                            datetime.strptime(pos["entry_date"], "%Y-%m-%d")).days
                
                if days_held >= holding_period:
                    if symbol in price_lookup and date in price_lookup[symbol]:
                        current_price = price_lookup[symbol][date]["close"]
                        entry_price = pos["entry_price"]
                        pnl_pct = ((current_price - entry_price) / entry_price) * 100
                        pnl = pos["size"] * (pnl_pct / 100)
                        capital += pos["size"] + pnl
                        
                        trades.append({
                            "coin": symbol,
                            "entry_date": pos["entry_date"],
                            "exit_date": date,
                            "entry_price": round(entry_price, 4),
                            "exit_price": round(current_price, 4),
                            "position_size": round(pos["size"], 2),
                            "pnl": round(pnl, 2),
                            "pnl_percent": round(pnl_pct, 2),
                            "status": "closed"
                        })
                        open_positions.remove(pos)
            
            if i % holding_period == 0 and len(open_positions) == 0:
                momentum_scores = []
                lookback_dates = [d for d in sorted_dates if d < date][-7:]
                
                for symbol in symbols:
                    if symbol not in price_lookup:
                        continue
                    
                    candles_dict = price_lookup[symbol]
                    if date not in candles_dict or not lookback_dates:
                        continue
                    
                    start_date_lb = lookback_dates[0]
                    if start_date_lb not in candles_dict:
                        continue
                    
                    start_price = candles_dict[start_date_lb]["close"]
                    end_price = candles_dict[date]["close"]
                    momentum = ((end_price - start_price) / start_price) * 100
                    
                    momentum_scores.append({
                        "symbol": symbol,
                        "momentum": momentum,
                        "price": end_price
                    })
                
                momentum_scores.sort(key=lambda x: x["momentum"], reverse=True)
                top_coins = momentum_scores[:top_n]
                
                if top_coins and capital > 10:
                    position_size = capital / len(top_coins)
                    for coin_data in top_coins:
                        if position_size >= 10:
                            capital -= position_size
                            open_positions.append({
                                "symbol": coin_data["symbol"],
                                "entry_date": date,
                                "entry_price": coin_data["price"],
                                "size": position_size
                            })
            
            portfolio_value = capital
            for pos in open_positions:
                symbol = pos["symbol"]
                if symbol in price_lookup and date in price_lookup[symbol]:
                    current_price = price_lookup[symbol][date]["close"]
                    entry_price = pos["entry_price"]
                    units = pos["size"] / entry_price
                    portfolio_value += units * current_price
            
            daily_equity.append({
                "date": date,
                "equity": round(portfolio_value, 2)
            })
            
            peak_capital = max(peak_capital, portfolio_value)
            if peak_capital > 0:
                drawdown = (peak_capital - portfolio_value) / peak_capital * 100
                max_drawdown = max(max_drawdown, drawdown)
        
        final_capital = capital
        for pos in open_positions:
            symbol = pos["symbol"]
            if trading_dates and symbol in price_lookup:
                last_date = trading_dates[-1]
                if last_date in price_lookup[symbol]:
                    current_price = price_lookup[symbol][last_date]["close"]
                    entry_price = pos["entry_price"]
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    pnl = pos["size"] * (pnl_pct / 100)
                    final_capital += pos["size"] + pnl
                    trades.append({
                        "coin": symbol,
                        "entry_date": pos["entry_date"],
                        "exit_date": trading_dates[-1],
                        "entry_price": round(entry_price, 4),
                        "exit_price": round(current_price, 4),
                        "position_size": round(pos["size"], 2),
                        "pnl": round(pnl, 2),
                        "pnl_percent": round(pnl_pct, 2),
                        "status": "closed",
                        "exit_reason": "end_of_backtest"
                    })
        
        return self._calculate_metrics(
            strategy="momentum",
            initial_capital=initial_capital,
            final_capital=final_capital,
            trades=trades,
            daily_equity=daily_equity,
            max_drawdown=max_drawdown,
            days=days,
            data_source="Real Historical Data"
        )
    
    def _empty_result(self, strategy: str, initial_capital: float, days: int, reason: str) -> Dict[str, Any]:
        """Return empty result when backtest cannot be performed"""
        return {
            "strategy": strategy,
            "initial_capital": initial_capital,
            "final_capital": initial_capital,
            "total_return": 0,
            "annualized_return": 0,
            "max_drawdown": 0,
            "sharpe_ratio": 0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "trades": [],
            "daily_equity": [],
            "period_days": days,
            "data_source": "None",
            "error": reason
        }
    
    def _calculate_metrics(
        self,
        strategy: str,
        initial_capital: float,
        final_capital: float,
        trades: List[Dict],
        daily_equity: List[Dict],
        max_drawdown: float,
        days: int,
        data_source: str = "Historical Data"
    ) -> Dict[str, Any]:
        """Calculate performance metrics from backtest results"""
        
        total_return = ((final_capital - initial_capital) / initial_capital) * 100
        
        closed_trades = [t for t in trades if t.get("status") == "closed"]
        winning_trades = [t for t in closed_trades if t.get("pnl", 0) > 0]
        losing_trades = [t for t in closed_trades if t.get("pnl", 0) < 0]
        
        win_rate = (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0
        
        avg_win = sum(t["pnl"] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = abs(sum(t["pnl"] for t in losing_trades) / len(losing_trades)) if losing_trades else 0
        profit_factor = (avg_win * len(winning_trades)) / (avg_loss * len(losing_trades)) if losing_trades and avg_loss > 0 else 0
        
        if len(daily_equity) > 1:
            returns = []
            for i in range(1, len(daily_equity)):
                prev = daily_equity[i-1]["equity"]
                curr = daily_equity[i]["equity"]
                if prev > 0:
                    returns.append((curr - prev) / prev)
            
            if returns:
                avg_return = sum(returns) / len(returns)
                std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
                sharpe_ratio = (avg_return / std_return) * (252 ** 0.5) if std_return > 0 else 0
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        annualized_return = ((final_capital / initial_capital) ** (365 / days) - 1) * 100 if days > 0 else 0
        
        return {
            "strategy": strategy,
            "initial_capital": initial_capital,
            "final_capital": round(final_capital, 2),
            "total_return": round(total_return, 2),
            "annualized_return": round(annualized_return, 2),
            "max_drawdown": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "total_trades": len(closed_trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "trades": trades[-50:],
            "daily_equity": daily_equity,
            "period_days": days,
            "data_source": data_source
        }
    
    def get_available_strategies(self) -> List[Dict[str, Any]]:
        """Get list of available strategies with their parameters"""
        return [
            {
                "id": "dump_buy",
                "name": "Dump Buy",
                "description": "Buy coins that dropped 5%+ and sell on recovery (uses real historical data)",
                "params": [
                    {"name": "dump_threshold", "type": "number", "default": 5, "min": 3, "max": 20, "label": "Dump Threshold (%)"},
                    {"name": "take_profit", "type": "number", "default": 10, "min": 5, "max": 50, "label": "Take Profit (%)"},
                    {"name": "stop_loss", "type": "number", "default": 8, "min": 3, "max": 20, "label": "Stop Loss (%)"},
                    {"name": "max_positions", "type": "number", "default": 5, "min": 1, "max": 10, "label": "Max Positions"}
                ]
            },
            {
                "id": "trend_follow",
                "name": "Trend Following",
                "description": "Follow established trends using momentum indicators (uses real historical data)",
                "params": [
                    {"name": "trend_period", "type": "number", "default": 20, "min": 5, "max": 50, "label": "Trend Period (days)"},
                    {"name": "take_profit", "type": "number", "default": 15, "min": 5, "max": 50, "label": "Take Profit (%)"},
                    {"name": "stop_loss", "type": "number", "default": 5, "min": 3, "max": 15, "label": "Stop Loss (%)"}
                ]
            },
            {
                "id": "dca",
                "name": "Dollar Cost Averaging",
                "description": "Invest fixed amounts at regular intervals (uses real historical data)",
                "params": [
                    {"name": "interval_days", "type": "number", "default": 7, "min": 1, "max": 30, "label": "Interval (days)"},
                    {"name": "coins", "type": "coins", "default": ["BTC", "ETH"], "label": "Coins to DCA"}
                ]
            },
            {
                "id": "momentum",
                "name": "Momentum",
                "description": "Buy top performing coins based on recent gains (uses real historical data)",
                "params": [
                    {"name": "holding_period", "type": "number", "default": 7, "min": 1, "max": 30, "label": "Holding Period (days)"},
                    {"name": "top_n", "type": "number", "default": 3, "min": 1, "max": 10, "label": "Top N Coins"}
                ]
            }
        ]


backtesting_engine: Optional[BacktestingEngine] = None


def init_backtesting_engine(market_provider, historical_provider=None) -> BacktestingEngine:
    global backtesting_engine
    backtesting_engine = BacktestingEngine(market_provider, historical_provider)
    return backtesting_engine


def get_backtesting_engine() -> Optional[BacktestingEngine]:
    return backtesting_engine
