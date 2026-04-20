/**
 * VPN API Client Unit Tests
 *
 * Tests the vpnApi methods from src/lib/api/vpn.ts by exercising the real
 * axios-based apiClient against MSW mock handlers.
 *
 * Follows patterns from auth.test.ts:
 * - MSW handlers for API mocking
 * - Arrange-Act-Assert structure
 * - Test success and error scenarios
 * - Test 401 interceptor behavior
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { vpnApi } from '../vpn';
import { tokenStorage } from '../client';
import { AxiosError } from 'axios';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const API_BASE = 'http://localhost:8000/api/v1';

/** Type guard for AxiosError to safely inspect response data in catch blocks. */
function isAxiosError(error: unknown): error is AxiosError<{ detail: string }> {
  return (
    typeof error === 'object' &&
    error !== null &&
    'isAxiosError' in error &&
    (error as Record<string, unknown>).isAxiosError === true
  );
}

/** Mock usage response */
const MOCK_USAGE = {
  bandwidth_used_bytes: 1073741824, // 1 GB
  bandwidth_limit_bytes: 10737418240, // 10 GB
  connections_active: 2,
  connections_limit: 5,
  period_start: '2025-01-01T00:00:00Z',
  period_end: '2025-01-31T23:59:59Z',
  last_connection_at: '2025-01-15T10:30:00Z',
};

// ---------------------------------------------------------------------------
// Global setup / teardown for every test
// ---------------------------------------------------------------------------

beforeEach(() => {
  localStorage.clear();
  window.location.href = 'http://localhost:3000';
});

afterEach(() => {
  window.location.href = 'http://localhost:3000';
});

// ===========================================================================
// vpnApi.getUsage
// ===========================================================================

describe('vpnApi.getUsage', () => {
  it('test_get_usage_success_returns_usage_stats', async () => {
    // Arrange - add handler for /users/me/usage
    server.use(
      http.get(`${API_BASE}/users/me/usage`, () => {
        return HttpResponse.json(MOCK_USAGE);
      }),
    );

    // Act
    const response = await vpnApi.getUsage();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.bandwidth_used_bytes).toBe(1073741824);
    expect(response.data.bandwidth_limit_bytes).toBe(10737418240);
    expect(response.data.connections_active).toBe(2);
    expect(response.data.connections_limit).toBe(5);
    expect(response.data.period_start).toBe('2025-01-01T00:00:00Z');
    expect(response.data.period_end).toBe('2025-01-31T23:59:59Z');
    expect(response.data.last_connection_at).toBe('2025-01-15T10:30:00Z');
  });

  it('test_get_usage_unauthenticated_rejects_with_401', async () => {
    // Arrange - override to return 401
    server.use(
      http.get(`${API_BASE}/users/me/usage`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert - 401 interceptor tries to refresh, finds no token
    await expect(vpnApi.getUsage()).rejects.toThrow('No refresh token');
  });

  it('test_get_usage_with_refresh_token_retries_on_401', async () => {
    // Arrange - provide refresh token so interceptor can retry
    tokenStorage.setTokens('expired_access', 'valid_refresh');

    let callCount = 0;
    server.use(
      http.get(`${API_BASE}/users/me/usage`, () => {
        callCount += 1;
        if (callCount === 1) {
          // First call: 401 triggers refresh
          return HttpResponse.json(
            { detail: 'Token expired' },
            { status: 401 },
          );
        }
        // Second call (after refresh): success
        return HttpResponse.json(MOCK_USAGE);
      }),
    );

    // Act
    const response = await vpnApi.getUsage();

    // Assert
    expect(callCount).toBe(2);
    expect(response.status).toBe(200);
    expect(response.data.bandwidth_used_bytes).toBe(MOCK_USAGE.bandwidth_used_bytes);
  });

  it('test_get_usage_server_error_500_rejects', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/users/me/usage`, () => {
        return HttpResponse.json(
          { detail: 'Internal server error' },
          { status: 500 },
        );
      }),
    );

    // Act & Assert
    try {
      await vpnApi.getUsage();
      expect.fail('Expected request to reject with 500');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(500);
      }
    }
  });

  it('test_get_usage_rate_limited_rejects_with_rate_limit_error', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/users/me/usage`, () => {
        return HttpResponse.json(
          { detail: 'Too many requests' },
          { status: 429, headers: { 'Retry-After': '60' } },
        );
      }),
    );

    // Act & Assert - interceptor converts 429 to RateLimitError
    try {
      await vpnApi.getUsage();
      expect.fail('Expected RateLimitError');
    } catch (error: unknown) {
      expect((error as Error).name).toBe('RateLimitError');
      expect((error as { retryAfter: number }).retryAfter).toBe(60);
    }
  });

  it('test_get_usage_network_error_rejects', async () => {
    // Arrange - simulate network failure
    server.use(
      http.get(`${API_BASE}/users/me/usage`, () => {
        return HttpResponse.error();
      }),
    );

    // Act & Assert
    await expect(vpnApi.getUsage()).rejects.toBeDefined();
  });

  it('test_get_usage_includes_authorization_header', async () => {
    // Arrange - store token so interceptor injects it
    localStorage.setItem('access_token', 'my_jwt_token');

    let capturedAuthHeader: string | undefined;
    server.use(
      http.get(`${API_BASE}/users/me/usage`, ({ request }) => {
        capturedAuthHeader = request.headers.get('Authorization') ?? undefined;
        return HttpResponse.json(MOCK_USAGE);
      }),
    );

    // Act
    await vpnApi.getUsage();

    // Assert
    expect(capturedAuthHeader).toBe('Bearer my_jwt_token');
  });
});
