import axios from 'axios';

const API_URL = import.meta.env.VITE_BACKEND_URL || '';
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 1000;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('wallet_address');
      localStorage.removeItem('user_id');
      return Promise.reject(error);
    }

    const config = error.config;
    if (
      config &&
      config.method === 'get' &&
      !config.__retryCount &&
      (!error.response || error.response.status >= 500 || error.code === 'ECONNABORTED')
    ) {
      config.__retryCount = 0;
    }

    if (
      config &&
      config.method === 'get' &&
      config.__retryCount !== undefined &&
      config.__retryCount < MAX_RETRIES
    ) {
      config.__retryCount += 1;
      const delay = RETRY_DELAY_MS * Math.pow(2, config.__retryCount - 1);
      await sleep(delay);
      return apiClient(config);
    }

    return Promise.reject(error);
  }
);

export const api = {
  get: (url, config) => apiClient.get(url, config),
  post: (url, data, config) => apiClient.post(url, data, config),
  put: (url, data, config) => apiClient.put(url, data, config),
  delete: (url, config) => apiClient.delete(url, config),
};

export const API_BASE_URL = API_URL;

export default apiClient;
