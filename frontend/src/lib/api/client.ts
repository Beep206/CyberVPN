import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Token storage keys
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

// Token management functions
export const tokenStorage = {
  getAccessToken: (): string | null => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  },
  getRefreshToken: (): string | null => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },
  setTokens: (accessToken: string, refreshToken: string): void => {
    if (typeof window === 'undefined') return;
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  },
  clearTokens: (): void => {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
  hasTokens: (): boolean => {
    return !!tokenStorage.getAccessToken();
  },
};

// Rate limit error class for 429 responses
export class RateLimitError extends Error {
  retryAfter: number; // seconds until retry allowed

  constructor(retryAfter: number) {
    const message = retryAfter >= 60
      ? `Rate limited. Try again in ${Math.ceil(retryAfter / 60)} minutes`
      : `Rate limited. Try again in ${retryAfter} seconds`;
    super(message);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }
}

// Parse Retry-After header (can be seconds or HTTP date)
function parseRetryAfter(header: string | null): number {
  if (!header) return 60; // Default 60 seconds if header missing

  // Try parsing as integer (seconds)
  const seconds = parseInt(header, 10);
  if (!isNaN(seconds)) return seconds;

  // Try parsing as HTTP date
  const date = new Date(header);
  if (!isNaN(date.getTime())) {
    const diff = Math.ceil((date.getTime() - Date.now()) / 1000);
    return Math.max(diff, 1);
  }

  return 60; // Fallback
}

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 10000,
  withCredentials: true, // Required for httpOnly cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add Authorization header and X-Request-ID
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = tokenStorage.getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // Add X-Request-ID for request correlation (DX-02)
    if (config.headers) {
      config.headers['X-Request-ID'] = crypto.randomUUID();
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error)
);

// Response interceptor - shell for 401 handling (to be implemented in Phase 2)
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: AxiosError | null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve();
    }
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // 429 Rate Limit handling
    if (error.response?.status === 429) {
      const retryAfter = parseRetryAfter(error.response.headers['retry-after'] as string | null);
      return Promise.reject(new RateLimitError(retryAfter));
    }

    // 401 handling
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Don't redirect/refresh if checking session status fails
      if (originalRequest.url?.includes('/auth/me')) {
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(() => apiClient(originalRequest));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshToken = tokenStorage.getRefreshToken();
        if (!refreshToken) {
          throw new Error('No refresh token');
        }

        const response = await apiClient.post('/auth/refresh', {
          refresh_token: refreshToken,
        });

        // Store new tokens
        const { access_token, refresh_token } = response.data;
        tokenStorage.setTokens(access_token, refresh_token);

        processQueue(null);
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError as AxiosError);
        // Clear tokens and redirect to login
        tokenStorage.clearTokens();
        if (typeof window !== 'undefined') {
          window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`;
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export type { AxiosError, InternalAxiosRequestConfig };
