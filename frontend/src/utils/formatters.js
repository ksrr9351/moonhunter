/**
 * Format number as USD currency
 * @param {number} value - The number to format
 * @returns {string} Formatted currency string with $ prefix, commas, and 2 decimals
 */
export const formatUSD = (value) => {
  if (value === null || value === undefined || isNaN(value)) {
    return '$0.00';
  }
  
  return parseFloat(value).toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
};

/**
 * Format number as percentage
 * @param {number} value - The number to format
 * @returns {string} Formatted percentage string with sign
 */
export const formatPercent = (value) => {
  if (value === undefined || value === null || isNaN(value)) return '0.00%';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${parseFloat(value).toFixed(2)}%`;
};

/**
 * Format large numbers with abbreviations (K, M, B, T)
 * @param {number} value - The number to format
 * @returns {string} Formatted abbreviated number
 */
export const formatCompactNumber = (value) => {
  if (value === null || value === undefined || isNaN(value)) return '0';
  
  const absValue = Math.abs(value);
  if (absValue >= 1e12) return `${(value / 1e12).toFixed(2)}T`;
  if (absValue >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (absValue >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
  if (absValue >= 1e3) return `${(value / 1e3).toFixed(2)}K`;
  return value.toFixed(2);
};

/**
 * Format wallet address with ellipsis
 * @param {string} address - The wallet address
 * @param {number} start - Characters to show at start
 * @param {number} end - Characters to show at end
 * @returns {string} Formatted address
 */
export const formatAddress = (address, start = 6, end = 4) => {
  if (!address) return '';
  return `${address.slice(0, start)}...${address.slice(-end)}`;
};
