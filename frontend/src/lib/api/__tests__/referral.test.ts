/**
 * Referral Program API Client Unit Tests
 *
 * Tests the referralApi methods from src/lib/api/referral.ts
 * Covers referral status, code generation, stats, and commission tracking
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { referralApi } from '../referral';
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

/** Mock referral status */
const MOCK_REFERRAL_STATUS = {
  enabled: true,
  commission_rate: 10.0,
};

/** Mock referral code */
const MOCK_REFERRAL_CODE = {
  referral_code: 'USER123REF',
};

/** Mock referral stats */
const MOCK_REFERRAL_STATS = {
  total_referrals: 10,
  total_earned: 150.00,
  commission_rate: 10.0,
};

/** Mock recent commissions */
const MOCK_RECENT_COMMISSIONS = [
  {
    id: 'comm_001',
    referred_user_id: 'user_ref1',
    commission_amount: 10.00,
    base_amount: 100.00,
    commission_rate: 10.0,
    created_at: '2025-02-05T10:00:00Z',
  },
  {
    id: 'comm_002',
    referred_user_id: 'user_ref2',
    commission_amount: 15.00,
    base_amount: 150.00,
    commission_rate: 10.0,
    created_at: '2025-02-01T14:30:00Z',
  },
];

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
// referralApi.getStatus
// ===========================================================================

describe('referralApi.getStatus', () => {
  it('test_get_referral_status_success_returns_referral_data', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/referral/status`, () => {
        return HttpResponse.json(MOCK_REFERRAL_STATUS);
      }),
    );

    // Act
    const response = await referralApi.getStatus();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.enabled).toBe(true);
    expect(response.data.commission_rate).toBe(10.0);
  });

  it('test_get_referral_status_not_enabled_returns_disabled', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/referral/status`, () => {
        return HttpResponse.json({
          enabled: false,
          commission_rate: 10.0,
        });
      }),
    );

    // Act
    const response = await referralApi.getStatus();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.enabled).toBe(false);
  });

  it('test_get_referral_status_unauthenticated_rejects_with_401', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/referral/status`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    await expect(referralApi.getStatus()).rejects.toThrow('No refresh token');
  });

  it('test_get_referral_status_server_error_500_rejects', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/referral/status`, () => {
        return HttpResponse.json(
          { detail: 'Internal server error' },
          { status: 500 },
        );
      }),
    );

    // Act & Assert
    try {
      await referralApi.getStatus();
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
// referralApi.getCode
// ===========================================================================

describe('referralApi.getCode', () => {
  it('test_get_referral_code_success_returns_code_and_url', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/referral/code`, () => {
        return HttpResponse.json(MOCK_REFERRAL_CODE);
      }),
    );

    // Act
    const response = await referralApi.getCode();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.referral_code).toBe('USER123REF');
  });

  it('test_get_referral_code_not_created_rejects_with_404', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/referral/code`, () => {
        return HttpResponse.json(
          { detail: 'Referral code not found' },
          { status: 404 },
        );
      }),
    );

    // Act & Assert
    try {
      await referralApi.getCode();
      expect.fail('Expected 404');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(404);
      }
    }
  });

  it('test_get_referral_code_unauthenticated_rejects_with_401', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/referral/code`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    await expect(referralApi.getCode()).rejects.toThrow('No refresh token');
  });

  it('test_get_referral_code_rate_limited_rejects_with_rate_limit_error', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/referral/code`, () => {
        return HttpResponse.json(
          { detail: 'Too many requests' },
          { status: 429, headers: { 'Retry-After': '20' } },
        );
      }),
    );

    // Act & Assert
    try {
      await referralApi.getCode();
      expect.fail('Expected RateLimitError');
    } catch (error: unknown) {
      expect((error as Error).name).toBe('RateLimitError');
      expect((error as { retryAfter: number }).retryAfter).toBe(20);
    }
  });
});

// ===========================================================================
// referralApi.getStats
// ===========================================================================

describe('referralApi.getStats', () => {
  it('test_get_referral_stats_success_returns_analytics', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/referral/stats`, () => {
        return HttpResponse.json(MOCK_REFERRAL_STATS);
      }),
    );

    // Act
    const response = await referralApi.getStats();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.total_referrals).toBe(10);
    expect(response.data.total_earned).toBe(150.00);
    expect(response.data.commission_rate).toBe(10.0);
  });

  it('test_get_referral_stats_no_activity_returns_zeros', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/referral/stats`, () => {
        return HttpResponse.json({
          total_referrals: 0,
          total_earned: 0,
          commission_rate: 10.0,
        });
      }),
    );

    // Act
    const response = await referralApi.getStats();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.total_referrals).toBe(0);
    expect(response.data.total_earned).toBe(0);
  });

  it('test_get_referral_stats_unauthenticated_rejects_with_401', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/referral/stats`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    await expect(referralApi.getStats()).rejects.toThrow('No refresh token');
  });

  it('test_get_referral_stats_server_error_500_rejects', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/referral/stats`, () => {
        return HttpResponse.json(
          { detail: 'Internal server error' },
          { status: 500 },
        );
      }),
    );

    // Act & Assert
    try {
      await referralApi.getStats();
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
// referralApi.getRecentCommissions
// ===========================================================================

describe('referralApi.getRecentCommissions', () => {
  it('test_get_recent_commissions_success_returns_commission_list', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/referral/recent`, () => {
        return HttpResponse.json(MOCK_RECENT_COMMISSIONS);
      }),
    );

    // Act
    const response = await referralApi.getRecentCommissions();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data).toHaveLength(2);
    expect(response.data[0].commission_amount).toBe(10.00);
    expect(response.data[1].commission_amount).toBe(15.00);
  });

  it('test_get_recent_commissions_empty_list_returns_empty_array', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/referral/recent`, () => {
        return HttpResponse.json([]);
      }),
    );

    // Act
    const response = await referralApi.getRecentCommissions();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data).toHaveLength(0);
  });

  it('test_get_recent_commissions_returns_recent_only', async () => {
    // Arrange - only recent commissions returned (API returns 10 most recent)
    server.use(
      http.get(`${API_BASE}/referral/recent`, () => {
        return HttpResponse.json(MOCK_RECENT_COMMISSIONS);
      }),
    );

    // Act
    const response = await referralApi.getRecentCommissions();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data).toHaveLength(2);
  });

  it('test_get_recent_commissions_unauthenticated_rejects_with_401', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/referral/recent`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    await expect(referralApi.getRecentCommissions()).rejects.toThrow(
      'No refresh token',
    );
  });

  it('test_get_recent_commissions_server_error_500_rejects', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/referral/recent`, () => {
        return HttpResponse.json(
          { detail: 'Internal server error' },
          { status: 500 },
        );
      }),
    );

    // Act & Assert
    try {
      await referralApi.getRecentCommissions();
      expect.fail('Expected 500 error');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(500);
      }
    }
  });
});
