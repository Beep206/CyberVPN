import axios, { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import {
  buildLocalizedLoginRedirect,
  isPublicAuthRoute,
} from '@/features/auth/lib/session';
import {
  normalizeFrontendApiEndpointTemplate,
  reportFrontendApiCall,
  sanitizeFrontendObservabilityToken,
} from '@/shared/lib/frontend-observability';

const ABSOLUTE_URL_RE = /^[a-zA-Z][a-zA-Z\d+.-]*:\/\//;

export const CANONICAL_API_BASE_PATH = '/api/v1';
export const CANONICAL_REQUEST_ID_HEADER = 'X-Request-ID';
export const CANONICAL_IDEMPOTENCY_HEADER = 'Idempotency-Key';

/**
 * Web auth relies on same-origin httpOnly cookies and Next.js rewrites.
 *
 * In the browser we intentionally use a relative `/api/v1` base path so the
 * app never reaches out to loopback/private backend origins like
 * `http://localhost:8000` from a public site origin.
 *
 * Server-only code should use `API_URL` directly (see route handlers), not this
 * browser client.
 */
export function resolveApiBaseUrl(): string {
  if (process.env.NODE_ENV === 'test') {
    const configuredBaseUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
    if (configuredBaseUrl) {
      return `${configuredBaseUrl.replace(/\/$/, '')}${CANONICAL_API_BASE_PATH}`;
    }
  }

  if (typeof window !== 'undefined') {
    return CANONICAL_API_BASE_PATH;
  }

  const configuredBaseUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (!configuredBaseUrl) {
    return CANONICAL_API_BASE_PATH;
  }

  return `${configuredBaseUrl.replace(/\/$/, '')}${CANONICAL_API_BASE_PATH}`;
}

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

export const apiClient = axios.create({
  baseURL: resolveApiBaseUrl(),
  adapter: process.env.NODE_ENV === 'test' ? 'http' : undefined,
  timeout: 10000,
  withCredentials: true, // Required for httpOnly cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

let requestSequence = 0;

type ObservabilityMetadata = {
  endpointTemplate?: string;
  requestId?: string;
  startedAt?: number;
  telemetrySkipped?: boolean;
};

type ApiClientRequestConfig = InternalAxiosRequestConfig & {
  metadata?: ObservabilityMetadata;
};

function getRequestId(): string {
  requestSequence += 1;
  return `req-${requestSequence}`;
}

function reportApiResponseTelemetry(
  config: ApiClientRequestConfig,
  input: {
    errorCode?: string;
    requestId?: string;
    result: 'success' | 'failure';
  },
): void {
  if (
    typeof window === 'undefined'
    || config.metadata?.startedAt == null
    || config.metadata.telemetrySkipped
  ) {
    return;
  }

  reportFrontendApiCall('admin_portal', {
    durationMs: performance.now() - config.metadata.startedAt,
    endpointTemplate: config.metadata.endpointTemplate ?? config.url ?? '/',
    errorCode: input.errorCode,
    method: config.method?.toUpperCase() ?? 'GET',
    path: window.location.pathname,
    requestId: input.requestId ?? config.metadata.requestId,
    result: input.result,
  });
}

// Request interceptor - X-Request-ID + queue during refresh
apiClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    const requestConfig = config as ApiClientRequestConfig;

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
      const requestId = getRequestId();
      config.headers[CANONICAL_REQUEST_ID_HEADER] = requestId;
      requestConfig.metadata = {
        endpointTemplate: normalizeFrontendApiEndpointTemplate(config.url ?? '/'),
        requestId,
        startedAt: typeof window !== 'undefined' ? performance.now() : undefined,
        telemetrySkipped: config.url?.includes('/analytics/') ?? false,
      };
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

function normalizeBlobResponse(response: AxiosResponse): AxiosResponse {
  if (
    response.config.responseType !== 'blob' ||
    typeof Blob === 'undefined' ||
    response.data instanceof Blob
  ) {
    return response;
  }

  const contentType = response.headers['content-type'];
  const blobOptions =
    typeof contentType === 'string' ? { type: contentType } : undefined;

  if (typeof response.data === 'string' || response.data instanceof ArrayBuffer) {
    response.data = new Blob([response.data], blobOptions);
  } else {
    response.data = new Blob([JSON.stringify(response.data)], blobOptions);
  }

  return response;
}

apiClient.interceptors.response.use(
  (response) => {
    const normalizedResponse = normalizeBlobResponse(response);
    const requestConfig = response.config as ApiClientRequestConfig;
    const requestIdHeader = response.headers[CANONICAL_REQUEST_ID_HEADER.toLowerCase()];

    reportApiResponseTelemetry(requestConfig, {
      requestId: typeof requestIdHeader === 'string' ? requestIdHeader : undefined,
      result: 'success',
    });

    return normalizedResponse;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as ApiClientRequestConfig & { _retry?: boolean };

    // 429 Rate Limit handling
    if (error.response?.status === 429) {
      const retryAfter = parseRetryAfter(error.response.headers['retry-after'] as string | null);
      reportApiResponseTelemetry(originalRequest, {
        errorCode: 'rate_limited',
        result: 'failure',
      });
      return Promise.reject(new RateLimitError(retryAfter));
    }

    // 401 handling
    if (error.response?.status === 401 && !originalRequest._retry) {
      const requestUrl = originalRequest.url || '';

      // Never retry refresh endpoint itself to avoid interceptor loops
      if (requestUrl.includes('/auth/refresh')) {
        reportApiResponseTelemetry(originalRequest, {
          errorCode: 'refresh_unauthorized',
          result: 'failure',
        });
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
        if (
          typeof window !== 'undefined'
          && !isNonBlockingAuthRequest
          && !isPublicAuthRoute(window.location.pathname)
        ) {
          const currentLocation = `${window.location.pathname}${window.location.search}${window.location.hash}`;
          window.location.href = buildLocalizedLoginRedirect(currentLocation);
        }
        reportApiResponseTelemetry(originalRequest, {
          errorCode: sanitizeFrontendObservabilityToken(
            String(
              (refreshError as AxiosError).response?.status
              ?? error.response?.status
              ?? error.code
              ?? 'request_failed',
            ),
          ),
          result: 'failure',
        });
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    reportApiResponseTelemetry(originalRequest, {
      errorCode: sanitizeFrontendObservabilityToken(
        String(error.response?.status ?? error.code ?? 'request_failed'),
      ),
      result: 'failure',
    });

    return Promise.reject(error);
  }
);

export type { AxiosError, InternalAxiosRequestConfig };
