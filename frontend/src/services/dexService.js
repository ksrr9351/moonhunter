import axios from 'axios';
import { getExplorerTxUrl as _getExplorerTxUrl } from './chainService';

const API_URL = import.meta.env.VITE_BACKEND_URL || '';

const getAuthHeaders = () => {
  const token = localStorage.getItem('auth_token');
  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
};

const retryRequest = async (fn, maxRetries = 2) => {
  let lastError = null;
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (err) {
      lastError = err;
      if (err.response?.status === 429) {
        const waitTime = (attempt + 1) * 2000;
        console.warn(`[DEX] Rate limited, retrying in ${waitTime}ms...`);
        await new Promise(resolve => setTimeout(resolve, waitTime));
        continue;
      }
      if (err.code === 'ERR_NETWORK' || err.code === 'ECONNABORTED') {
        const waitTime = (attempt + 1) * 1000;
        console.warn(`[DEX] Network error, retrying in ${waitTime}ms...`);
        await new Promise(resolve => setTimeout(resolve, waitTime));
        continue;
      }
      throw err;
    }
  }
  throw lastError;
};

export const dexService = {
  async getSpenderAddress(chainId) {
    const response = await retryRequest(() =>
      axios.get(`${API_URL}/api/dex/spender`, {
        headers: getAuthHeaders(),
        params: { chain_id: chainId },
        timeout: 15000,
      })
    );
    return response.data;
  },

  async getQuote(srcToken, dstToken, amount, chainId) {
    console.log(`[DEX] Getting quote: ${srcToken?.slice(0, 10)}... -> ${dstToken?.slice(0, 10)}..., amount=${amount}`);
    try {
      const response = await retryRequest(() =>
        axios.post(
          `${API_URL}/api/dex/quote`,
          {
            src_token: srcToken,
            dst_token: dstToken,
            amount: amount,
            chain_id: chainId,
          },
          { headers: getAuthHeaders(), timeout: 20000 }
        )
      );
      console.log(`[DEX] Quote response:`, response.data?.success ? 'success' : response.data?.error);
      return response.data;
    } catch (err) {
      console.error('[DEX] Quote request error:', err.response?.data || err.message);
      if (err.response?.data) {
        const data = err.response.data;
        const rawMsg = data.detail || data.error || data.message || 'Quote request failed';
        const msg = typeof rawMsg === 'string' ? rawMsg : (rawMsg?.message || rawMsg?.detail || JSON.stringify(rawMsg));
        return { success: false, error: msg };
      }
      return { success: false, error: err.message || 'Network error - please try again' };
    }
  },

  async getSwapTransaction(srcToken, dstToken, amount, slippage = 1.0, chainId) {
    try {
      console.log(`[DEX] Getting swap tx: ${srcToken?.slice(0, 10)}... -> ${dstToken?.slice(0, 10)}..., slippage=${slippage}%`);
      const response = await retryRequest(() =>
        axios.post(
          `${API_URL}/api/dex/swap`,
          {
            src_token: srcToken,
            dst_token: dstToken,
            amount: amount,
            slippage: slippage,
            chain_id: chainId,
            disable_estimate: true,
          },
          { headers: getAuthHeaders(), timeout: 30000 }
        )
      );
      console.log(`[DEX] Swap tx response:`, response.data?.success ? 'success' : response.data?.error);
      return response.data;
    } catch (err) {
      console.error('[DEX] Swap request error:', err.response?.data || err.message);
      if (err.response?.data) {
        const data = err.response.data;
        return {
          success: false,
          error: data.detail || data.error || 'Swap request failed',
          code: data.code
        };
      }
      return { success: false, error: err.message || 'Network error - please try again' };
    }
  },

  async checkAllowance(tokenAddress, chainId) {
    try {
      const response = await retryRequest(() =>
        axios.get(`${API_URL}/api/dex/allowance`, {
          headers: getAuthHeaders(),
          params: { token_address: tokenAddress, chain_id: chainId },
          timeout: 15000,
        })
      );
      return response.data;
    } catch (err) {
      console.error('[DEX] Allowance check error:', err.message);
      return { success: false, allowance: "0", error: err.message };
    }
  },

  async getApproveTransaction(tokenAddress, amount = null, chainId) {
    const response = await retryRequest(() =>
      axios.post(
        `${API_URL}/api/dex/approve`,
        {
          token_address: tokenAddress,
          amount: amount,
          chain_id: chainId,
        },
        { headers: getAuthHeaders(), timeout: 15000 }
      )
    );
    return response.data;
  },

  async getSupportedTokens(chainId) {
    const response = await retryRequest(() =>
      axios.get(`${API_URL}/api/dex/tokens`, {
        headers: getAuthHeaders(),
        params: { chain_id: chainId },
        timeout: 15000,
      })
    );
    return response.data;
  },

  async getLiquiditySources(chainId) {
    const response = await retryRequest(() =>
      axios.get(`${API_URL}/api/dex/liquidity-sources`, {
        headers: getAuthHeaders(),
        params: { chain_id: chainId },
        timeout: 15000,
      })
    );
    return response.data;
  },

  toWei(amount, decimals = 18) {
    try {
      const num = parseFloat(amount);
      if (isNaN(num) || num <= 0) return "0";
      // Guard: decimals must be a positive integer — fallback to 18 if missing/zero
      const dec = (typeof decimals === 'number' && decimals > 0) ? decimals : 18;
      const str = num.toFixed(dec);
      const [whole, fraction = ''] = str.split('.');
      const paddedFraction = fraction.padEnd(dec, '0').slice(0, dec);
      const combined = whole + paddedFraction;
      const result = BigInt(combined).toString();
      return result === "0" ? "0" : result;
    } catch (e) {
      console.error('[DEX] toWei error:', e, 'amount:', amount, 'decimals:', decimals);
      return "0";
    }
  },

  fromWei(amount, decimals = 18) {
    try {
      if (!amount || amount === "0") return 0;
      const str = String(amount).padStart(decimals + 1, '0');
      const wholeEnd = str.length - decimals;
      const whole = str.slice(0, wholeEnd) || '0';
      const fraction = str.slice(wholeEnd);
      return parseFloat(`${whole}.${fraction}`);
    } catch (e) {
      console.error('[DEX] fromWei error:', e);
      return 0;
    }
  },

  formatTokenAmount(amount, decimals = 18, displayDecimals = 6) {
    const value = this.fromWei(amount, decimals);
    if (value === 0) return '0';
    if (value < 0.000001) return '< 0.000001';
    return value.toFixed(displayDecimals);
  },

  getExplorerUrl(chainId, txHash) {
    const url = _getExplorerTxUrl(chainId, txHash);
    return url || null;
  },

  async recordDexSwap(swapDetails) {
    const response = await axios.post(
      `${API_URL}/api/ai-engine/record-dex-swap`,
      {
        symbol: swapDetails.symbol,
        usdt_amount: swapDetails.usdtAmount,
        quantity: swapDetails.quantity,
        entry_price: swapDetails.entryPrice,
        tx_hash: swapDetails.txHash,
        chain_id: swapDetails.chainId,
        strategy: swapDetails.strategy || 'manual',
        trigger_reason: swapDetails.triggerReason || 'DEX swap executed',
      },
      { headers: getAuthHeaders(), timeout: 15000 }
    );
    return response.data;
  },

  async recordTransaction({ txHash, fromToken, toToken, fromAmount, toAmount, chainId }) {
    const response = await axios.post(
      `${API_URL}/api/dex/record-transaction`,
      {
        tx_hash: txHash,
        from_token: fromToken,
        to_token: toToken,
        from_amount: fromAmount,
        to_amount: toAmount,
        chain_id: chainId,
      },
      { headers: getAuthHeaders(), timeout: 15000 }
    );
    return response.data;
  },

  async closeDexPosition(closeDetails) {
    const response = await axios.post(
      `${API_URL}/api/ai-engine/close-dex-position`,
      {
        position_id: closeDetails.positionId,
        exit_price: closeDetails.exitPrice,
        exit_quantity: closeDetails.exitQuantity,
        tx_hash: closeDetails.txHash,
        reason: closeDetails.reason || 'dex_sell',
      },
      { headers: getAuthHeaders(), timeout: 15000 }
    );
    return response.data;
  },
};

export default dexService;
