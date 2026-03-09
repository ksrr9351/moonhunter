const API_BASE = '/api';

export const socialTradingService = {
  async getLeaderboard(period = 'all', limit = 20) {
    const response = await fetch(`${API_BASE}/social/leaderboard?period=${period}&limit=${limit}`);
    if (!response.ok) throw new Error('Failed to fetch leaderboard');
    return response.json();
  },

  async getTraderPortfolio(traderId) {
    const response = await fetch(`${API_BASE}/social/trader/${traderId}`);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch trader portfolio');
    }
    return response.json();
  },

  async getSocialSettings(token) {
    const response = await fetch(`${API_BASE}/social/settings`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch social settings');
    return response.json();
  },

  async updateSocialSettings(token, settings) {
    const response = await fetch(`${API_BASE}/social/settings`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(settings)
    });
    if (!response.ok) throw new Error('Failed to update social settings');
    return response.json();
  },

  async getFollowing(token) {
    const response = await fetch(`${API_BASE}/social/following`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch following');
    return response.json();
  },

  async followTrader(token, traderId) {
    const response = await fetch(`${API_BASE}/social/follow/${traderId}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to follow trader');
    }
    return response.json();
  },

  async unfollowTrader(token, traderId) {
    const response = await fetch(`${API_BASE}/social/follow/${traderId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to unfollow trader');
    return response.json();
  },

  async updateCopySettings(token, traderId, settings) {
    const response = await fetch(`${API_BASE}/social/copy-settings/${traderId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(settings)
    });
    if (!response.ok) throw new Error('Failed to update copy settings');
    return response.json();
  },

  async getActivityFeed(token, limit = 50) {
    const response = await fetch(`${API_BASE}/social/activity?limit=${limit}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch activity feed');
    return response.json();
  },

  async getMyStats(token) {
    const response = await fetch(`${API_BASE}/social/my-stats`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch stats');
    return response.json();
  }
};

export default socialTradingService;
