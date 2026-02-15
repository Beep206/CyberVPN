import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

const ABSOLUTE_URL_RE = /^[a-zA-Z][a-zA-Z\d+.-]*:\/\//;

/**
 * Normalizes API request URLs to avoid mixed trailing-slash variants.
 *
 * Rule: strip trailing slash only for nested API paths (2+ segments),
 * while keeping collection-root paths like `/servers/` untouched.
 */
export function normalizeApiRequestPath(rawUrl: string): string {
  if (!rawUrl) return rawUrl;

  const isAbsolute = ABSOLUTE_URL_RE.test(rawUrl);
  const parsed = new URL(rawUrl, 'http://localhost');
  const segments = parsed.pathname.split('/').filter(Boolean);

  if (parsed.pathname.endsWith('/') && segments.length > 1) {
    parsed.pathname = parsed.pathname.slice(0, -1);
  }

  if (isAbsolute) {
    return parsed.toString();
  }

  return `${parsed.pathname}${parsed.search}${parsed.hash}`;
}

// SEC-01: Token storage migrated to httpOnly cookies.
// tokenStorage is kept as a no-op shim so existing callers don't break during
// the transition.  The backend now sets/clears httpOnly cookies automatically.
export const tokenStorage = {
  getAccessToken: (): string | null => null,
  getRefreshToken: (): string | null => null,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  setTokens: (_accessToken: string, _refreshToken: string): void => {
    // No-op: tokens are now managed via httpOnly cookies set by the backend.
  },
  clearTokens: (): void => {
    // Clean up any legacy localStorage tokens from before the migration.
    if (typeof window === 'undefined') return;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
  hasTokens: (): boolean => {
    // Cannot inspect httpOnly cookies from JS — rely on /auth/me to check.
    return false;
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

// SEC-04: Extract locale prefix from current pathname for locale-aware redirects.
const LOCALE_RE = /^\/([a-z]{2,3}-[A-Z]{2})\//;
const DEFAULT_LOCALE = 'en-EN';
const AUTH_ROUTE_RE = /^\/(?:[a-z]{2,3}-[A-Z]{2}\/)?(?:login|register|magic-link|forgot-password|reset-password|verify|oauth\/callback|telegram-link)(?:\/|$)/;

function getLocaleFromPath(): string {
  if (typeof window === 'undefined') return DEFAULT_LOCALE;
  const match = window.location.pathname.match(LOCALE_RE);
  return match ? match[1] : DEFAULT_LOCALE;
}

function isAuthRoute(pathname: string): boolean {
  return AUTH_ROUTE_RE.test(pathname);
}

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 10000,
  withCredentials: true, // Required for httpOnly cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - X-Request-ID + queue during refresh
apiClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    if (config.url) {
      config.url = normalizeApiRequestPath(config.url);
    }

    // Queue requests while a token refresh is in progress
    // (except the refresh request itself and session-check requests)
    if (
      isRefreshing
      && !config.url?.includes('/auth/refresh')
      && !config.url?.includes('/auth/me')
      && !config.url?.includes('/auth/session')
    ) {
      await new Promise<void>((resolve, reject) => {
        failedQueue.push({ resolve: () => resolve(), reject: (err) => reject(err) });
      });
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
      const requestUrl = originalRequest.url || '';

      // Never retry refresh endpoint itself to avoid interceptor loops
      if (requestUrl.includes('/auth/refresh')) {
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
        // SEC-01: refresh token is sent via httpOnly cookie automatically
        const refreshResponse = await apiClient.post('/auth/refresh', {});

        // Backend sets new cookies; just check response was OK
        if (refreshResponse.status === 200) {
          processQueue(null);
          return apiClient(originalRequest);
        }
        throw new Error('Refresh failed');
      } catch (refreshError) {
        processQueue(refreshError as AxiosError);
        // Clear any legacy localStorage tokens
        tokenStorage.clearTokens();
        const isNonBlockingAuthRequest =
          requestUrl.includes('/auth/me') ||
          requestUrl.includes('/auth/session') ||
          requestUrl.includes('/auth/magic-link/verify') ||
          requestUrl.includes('/auth/magic-link/verify-otp');

        // Session probe and magic-link verification can run on public pages;
        // don't force redirect here or we can interrupt in-flight login flows.
        if (typeof window !== 'undefined' && !isNonBlockingAuthRequest && !isAuthRoute(window.location.pathname)) {
          // SEC-04: locale-aware redirect
          const locale = getLocaleFromPath();
          window.location.href = `/${locale}/login?redirect=${encodeURIComponent(window.location.pathname)}`;
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
