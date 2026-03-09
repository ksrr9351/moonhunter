import axios from 'axios';

const API_URL = import.meta.env.VITE_BACKEND_URL || '';

export const cryptoService = {
  async getTopCoins(limit = 5) {
    try {
      const response = await axios.get(`${API_URL}/api/crypto/latest?limit=${limit}`);
      return response.data.data || response.data || [];
    } catch (error) {
      console.error('Error fetching top coins:', error);
      return [];
    }
  },

  async getCoinPrice(symbol) {
    try {
      const response = await axios.get(`${API_URL}/api/crypto/price/${symbol}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching ${symbol} price:`, error);
      return null;
    }
  },

  async getMarketOverview() {
    try {
      const response = await axios.get(`${API_URL}/api/crypto/market-overview`);
      return response.data;
    } catch (error) {
      console.error('Error fetching market overview:', error);
      return null;
    }
  },

  async getFastMovers() {
    try {
      const response = await axios.get(`${API_URL}/api/crypto/fast-movers`);
      return response.data;
    } catch (error) {
      console.error('Error fetching fast movers:', error);
      return [];
    }
  }
};
