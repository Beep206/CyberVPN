/**
 * Subscriptions API Client Unit Tests
 *
 * Tests the subscriptionsApi methods from src/lib/api/subscriptions.ts
 * Covers subscription plan listing, retrieval, and VPN configuration
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { subscriptionsApi } from '../subscriptions';
import { tokenStorage } from '../client';
import { AxiosError } from 'axios';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const API_BASE = 'http://localhost:8000/api/v1';

/** Type guard for AxiosError */
function isAxiosError(error: unknown): error is AxiosError<{ detail: string }> {
  return (
    typeof error === 'object' &&
    error !== null &&
    'isAxiosError' in error &&
    (error as Record<string, unknown>).isAxiosError === true
  );
}

/** Mock subscription plan */
const MOCK_PLAN = {
  uuid: 'plan_monthly',
  name: 'Monthly Premium',
  templateType: 'subscription',
  hostUuid: 'host_001',
  inboundTag: 'inbound_monthly',
  flow: 'xtls-rprx-vision',
  configData: {},
};

/** Mock subscription template */
const MOCK_SUBSCRIPTION = {
  uuid: 'sub_template_001',
  name: 'Monthly Premium',
  templateType: 'subscription',
  hostUuid: 'host_001',
  inboundTag: 'inbound_001',
  flow: 'xtls-rprx-vision',
  configData: { someKey: 'someValue' },
};

/** Mock VPN config */
const MOCK_VPN_CONFIG = {
  config: 'vmess://base64encodedconfig...',
  subscriptionUrl: 'https://api.example.com/sub/user_001',
};

// ---------------------------------------------------------------------------
// Global setup / teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  localStorage.clear();
  window.location.href = 'http://localhost:3000';
});

afterEach(() => {
  window.location.href = 'http://localhost:3000';
});

// ===========================================================================
// subscriptionsApi.list
// ===========================================================================

describe('subscriptionsApi.list', () => {
  it('test_list_subscriptions_success_returns_plan_array', async () => {
    // Arrange
    const mockPlans = [
      MOCK_PLAN,
      { ...MOCK_PLAN, uuid: 'plan_annual', name: 'Annual Premium' },
    ];

    server.use(
      http.get(`${API_BASE}/subscriptions/`, () => {
        return HttpResponse.json(mockPlans);
      }),
    );

    // Act
    const response = await subscriptionsApi.list();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data).toHaveLength(2);
    expect(response.data[0].uuid).toBe('plan_monthly');
    expect(response.data[0].name).toBe('Monthly Premium');
    expect(response.data[1].uuid).toBe('plan_annual');
  });

  it('test_list_subscriptions_returns_all_templates', async () => {
    // Arrange
    const mockPlans = [
      MOCK_PLAN,
      { ...MOCK_PLAN, uuid: 'plan_annual', name: 'Annual Plan' },
    ];

    server.use(
      http.get(`${API_BASE}/subscriptions/`, () => {
        return HttpResponse.json(mockPlans);
      }),
    );

    // Act
    const response = await subscriptionsApi.list();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data).toHaveLength(2);
  });

  it('test_list_subscriptions_empty_list_returns_empty_array', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/subscriptions/`, () => {
        return HttpResponse.json([]);
      }),
    );

    // Act
    const response = await subscriptionsApi.list();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data).toHaveLength(0);
  });

  it('test_list_subscriptions_unauthenticated_rejects_with_401', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/subscriptions/`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    await expect(subscriptionsApi.list()).rejects.toThrow('No refresh token');
  });

  it('test_list_subscriptions_server_error_500_rejects', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/subscriptions/`, () => {
        return HttpResponse.json(
          { detail: 'Internal server error' },
          { status: 500 },
        );
      }),
    );

    // Act & Assert
    try {
      await subscriptionsApi.list();
      expect.fail('Expected 500 error');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(500);
      }
    }
  });
});

// ===========================================================================
// subscriptionsApi.get
// ===========================================================================

describe('subscriptionsApi.get', () => {
  it('test_get_subscription_template_returns_subscription_data', async () => {
    // Arrange
    const uuid = 'sub_template_001';
    server.use(
      http.get(`${API_BASE}/subscriptions/${uuid}`, () => {
        return HttpResponse.json(MOCK_SUBSCRIPTION);
      }),
    );

    // Act
    const response = await subscriptionsApi.get(uuid);

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.uuid).toBe('sub_template_001');
    expect(response.data.name).toBe('Monthly Premium');
  });

  it('test_get_subscription_template_different_type', async () => {
    // Arrange
    const uuid = 'trial_template';
    server.use(
      http.get(`${API_BASE}/subscriptions/${uuid}`, () => {
        return HttpResponse.json({
          ...MOCK_SUBSCRIPTION,
          uuid: 'trial_template',
          name: 'Trial Plan',
          templateType: 'trial',
        });
      }),
    );

    // Act
    const response = await subscriptionsApi.get(uuid);

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.templateType).toBe('trial');
  });

  it('test_get_subscription_not_found_rejects_with_404', async () => {
    // Arrange
    const uuid = 'nonexistent';
    server.use(
      http.get(`${API_BASE}/subscriptions/${uuid}`, () => {
        return HttpResponse.json(
          { detail: 'Subscription template not found' },
          { status: 404 },
        );
      }),
    );

    // Act & Assert
    try {
      await subscriptionsApi.get(uuid);
      expect.fail('Expected 404');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(404);
      }
    }
  });

  it('test_get_subscription_unauthenticated_rejects_with_401', async () => {
    // Arrange
    const uuid = 'sub_001';
    server.use(
      http.get(`${API_BASE}/subscriptions/${uuid}`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    await expect(subscriptionsApi.get(uuid)).rejects.toThrow();
  });

  it('test_get_subscription_with_refresh_token_retries_on_401', async () => {
    // Arrange
    const uuid = 'sub_001';
    tokenStorage.setTokens('expired_access', 'valid_refresh');

    let callCount = 0;
    server.use(
      http.get(`${API_BASE}/subscriptions/${uuid}`, () => {
        callCount += 1;
        if (callCount === 1) {
          return HttpResponse.json(
            { detail: 'Token expired' },
            { status: 401 },
          );
        }
        return HttpResponse.json(MOCK_SUBSCRIPTION);
      }),
    );

    // Act
    const response = await subscriptionsApi.get(uuid);

    // Assert
    expect(callCount).toBe(2);
    expect(response.status).toBe(200);
    expect(response.data.uuid).toBe('sub_template_001');
  });

  it('test_get_subscription_rate_limited_rejects_with_rate_limit_error', async () => {
    // Arrange
    const uuid = 'sub_001';
    server.use(
      http.get(`${API_BASE}/subscriptions/${uuid}`, () => {
        return HttpResponse.json(
          { detail: 'Too many requests' },
          { status: 429, headers: { 'Retry-After': '45' } },
        );
      }),
    );

    // Act & Assert
    try {
      await subscriptionsApi.get(uuid);
      expect.fail('Expected RateLimitError');
    } catch (error: unknown) {
      expect((error as Error).name).toBe('RateLimitError');
      expect((error as { retryAfter: number }).retryAfter).toBe(45);
    }
  });
});

// ===========================================================================
// subscriptionsApi.getConfig
// ===========================================================================

describe('subscriptionsApi.getConfig', () => {
  it('test_get_config_success_returns_vpn_configuration', async () => {
    // Arrange
    const userUuid = 'user_001';
    server.use(
      http.get(`${API_BASE}/subscriptions/config/${userUuid}`, () => {
        return HttpResponse.json(MOCK_VPN_CONFIG);
      }),
    );

    // Act
    const response = await subscriptionsApi.getConfig(userUuid);

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.config).toBeDefined();
    expect(response.data.config).toContain('vmess://');
    expect(response.data.subscriptionUrl).toBeDefined();
  });

  it('test_get_config_without_subscription_url', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/subscriptions/config/user_001`, () => {
        return HttpResponse.json({
          config: 'vmess://config',
        });
      }),
    );

    // Act
    const response = await subscriptionsApi.getConfig('user_001');

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.config).toBeDefined();
    expect(response.data.subscriptionUrl).toBeUndefined();
  });

  it('test_get_config_no_subscription_rejects_with_404', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/subscriptions/config/user_001`, () => {
        return HttpResponse.json(
          { detail: 'No active subscription' },
          { status: 404 },
        );
      }),
    );

    // Act & Assert
    try {
      await subscriptionsApi.getConfig('user_001');
      expect.fail('Expected 404');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(404);
      }
    }
  });

  it('test_get_config_subscription_expired_rejects_with_422', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/subscriptions/config/user_001`, () => {
        return HttpResponse.json(
          { detail: 'Subscription expired' },
          { status: 422 },
        );
      }),
    );

    // Act & Assert
    try {
      await subscriptionsApi.getConfig('user_001');
      expect.fail('Expected 422');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(422);
      }
    }
  });

  it('test_get_config_unauthenticated_rejects_with_401', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/subscriptions/config/user_001`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    await expect(subscriptionsApi.getConfig('user_001')).rejects.toThrow();
  });

  it('test_get_config_server_error_500_rejects', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/subscriptions/config/user_001`, () => {
        return HttpResponse.json(
          { detail: 'Internal server error' },
          { status: 500 },
        );
      }),
    );

    // Act & Assert
    try {
      await subscriptionsApi.getConfig('user_001');
      expect.fail('Expected 500 error');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(500);
      }
    }
  });
});
