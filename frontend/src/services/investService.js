const API_URL = import.meta.env.VITE_BACKEND_URL || '';

const getHeaders = (token) => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${token}`,
});

export const investService = {
  async getOpportunities(token, chainId = null) {
    const params = new URLSearchParams();
    if (chainId) params.append('chain_id', chainId);
    const url = `${API_URL}/api/invest/opportunities${params.toString() ? '?' + params : ''}`;
    const res = await fetch(url, { headers: getHeaders(token) });
    if (!res.ok) throw new Error('Failed to fetch opportunities');
    return res.json();
  },

  async getPositions(token, status = 'active') {
    const res = await fetch(`${API_URL}/api/invest/positions?status=${status}`, {
      headers: getHeaders(token),
    });
    if (!res.ok) throw new Error('Failed to fetch positions');
    return res.json();
  },

  async getSummary(token) {
    const res = await fetch(`${API_URL}/api/invest/summary`, {
      headers: getHeaders(token),
    });
    if (!res.ok) throw new Error('Failed to fetch summary');
    return res.json();
  },

  async recordBuy(token, data) {
    const res = await fetch(`${API_URL}/api/invest/record-buy`, {
      method: 'POST',
      headers: getHeaders(token),
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to record buy');
    return res.json();
  },

  async recordSell(token, data) {
    const res = await fetch(`${API_URL}/api/invest/record-sell`, {
      method: 'POST',
      headers: getHeaders(token),
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to record sell');
    return res.json();
  },

  async setTriggers(token, positionId, data) {
    const res = await fetch(`${API_URL}/api/invest/positions/${positionId}/triggers`, {
      method: 'POST',
      headers: getHeaders(token),
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to set triggers');
    return res.json();
  },

  async cancelTriggers(token, positionId) {
    const res = await fetch(`${API_URL}/api/invest/positions/${positionId}/triggers`, {
      method: 'DELETE',
      headers: getHeaders(token),
    });
    if (!res.ok) throw new Error('Failed to cancel triggers');
    return res.json();
  },

  async getReportSummary(token, period = 'all') {
    const res = await fetch(`${API_URL}/api/invest/reports/summary?period=${period}`, {
      headers: getHeaders(token),
    });
    if (!res.ok) throw new Error('Failed to fetch report');
    return res.json();
  },

  async exportReport(token, format = 'csv', period = 'all') {
    const res = await fetch(`${API_URL}/api/invest/reports/export?format=${format}&period=${period}`, {
      headers: getHeaders(token),
    });
    if (!res.ok) throw new Error('Failed to export report');
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `moonhunters_report_${period}.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  },
};
