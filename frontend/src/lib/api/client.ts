import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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

// Request interceptor - minimal, cookies auto-attached
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => config,
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
        await apiClient.post('/auth/refresh');
        processQueue(null);
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError as AxiosError);
        // Redirect to login - will be enhanced in Phase 2
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
