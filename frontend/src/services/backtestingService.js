const API_BASE = `${import.meta.env.VITE_BACKEND_URL || ''}/api`;

const getHeaders = (token) => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${token}`,
});

export const backtestingService = {
  async getStrategies(token) {
    const response = await fetch(`${API_BASE}/backtest/strategies`, {
      headers: getHeaders(token),
    });
    if (!response.ok) throw new Error('Failed to fetch strategies');
    return response.json();
  },

  async runBacktest(token, strategy, initialCapital, startDate, endDate, params) {
    const response = await fetch(`${API_BASE}/backtest/run`, {
      method: 'POST',
      headers: getHeaders(token),
      body: JSON.stringify({
        strategy,
        initial_capital: initialCapital,
        start_date: startDate,
        end_date: endDate,
        params
      })
    });
    if (!response.ok) throw new Error('Failed to run backtest');
    return response.json();
  }
};

export default backtestingService;
