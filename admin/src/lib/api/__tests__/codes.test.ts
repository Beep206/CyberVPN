/**
 * Promo Codes API Client Unit Tests
 *
 * Tests the codesApi methods from src/lib/api/codes.ts
 * Covers promo code validation for discount calculations
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { codesApi } from '../codes';
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
// codesApi.validate
// ===========================================================================

describe('codesApi.validate', () => {
  it('test_validate_promo_success_with_percentage_discount', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/promo/validate`, async () => {
        return HttpResponse.json({
          promo_code_id: 'promo_001',
          discount_type: 'percentage',
          discount_value: 20,
          discount_amount: 10.0,
          code: 'SAVE20',
        });
      }),
    );

    // Act
    const response = await codesApi.validate({
      code: 'SAVE20',
      plan_id: 'plan_monthly',
      amount: 50.0,
    });

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.promo_code_id).toBe('promo_001');
    expect(response.data.discount_type).toBe('percentage');
    expect(response.data.discount_value).toBe(20);
    expect(response.data.discount_amount).toBe(10.0);
  });

  it('test_validate_promo_success_with_fixed_discount', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/promo/validate`, async () => {
        return HttpResponse.json({
          promo_code_id: 'promo_002',
          discount_type: 'fixed',
          discount_value: 5.0,
          discount_amount: 5.0,
          code: 'FLAT5',
        });
      }),
    );

    // Act
    const response = await codesApi.validate({
      code: 'FLAT5',
      plan_id: 'plan_monthly',
      amount: 50.0,
    });

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.promo_code_id).toBe('promo_002');
    expect(response.data.discount_type).toBe('fixed');
    expect(response.data.discount_amount).toBe(5.0);
    expect(response.data.code).toBe('FLAT5');
  });

  it('test_validate_promo_code_not_found_rejects_with_404', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/promo/validate`, async () => {
        return HttpResponse.json(
          { detail: 'Promo code not found' },
          { status: 404 },
        );
      }),
    );

    // Act & Assert
    try {
      await codesApi.validate({
        code: 'INVALID123',
        plan_id: 'plan_monthly',
        amount: 50.0,
      });
      expect.fail('Expected request to reject with 404');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(404);
        expect(error.response?.data.detail).toBe('Promo code not found');
      }
    }
  });

  it('test_validate_promo_code_expired_rejects_with_422', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/promo/validate`, async () => {
        return HttpResponse.json(
          { detail: 'Promo code has expired' },
          { status: 422 },
        );
      }),
    );

    // Act & Assert
    try {
      await codesApi.validate({
        code: 'EXPIRED',
        plan_id: 'plan_monthly',
        amount: 50.0,
      });
      expect.fail('Expected request to reject with 422');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(422);
        expect(error.response?.data.detail).toContain('expired');
      }
    }
  });

  it('test_validate_promo_code_exhausted_rejects_with_422', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/promo/validate`, async () => {
        return HttpResponse.json(
          { detail: 'Promo code has reached maximum uses' },
          { status: 422 },
        );
      }),
    );

    // Act & Assert
    try {
      await codesApi.validate({
        code: 'EXHAUSTED',
        plan_id: 'plan_monthly',
        amount: 50.0,
      });
      expect.fail('Expected request to reject with 422');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(422);
        expect(error.response?.data.detail).toContain('maximum uses');
      }
    }
  });

  it('test_validate_promo_sends_correct_request_body', async () => {
    // Arrange - capture request body
    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post(`${API_BASE}/promo/validate`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          promo_code_id: 'promo_test',
          discount_type: 'percentage',
          discount_value: 10,
          discount_amount: 5.0,
          code: 'TEST10',
        });
      }),
    );

    // Act
    await codesApi.validate({
      code: 'TEST10',
      plan_id: 'plan_annual',
      amount: 50.0,
    });

    // Assert
    expect(capturedBody).not.toBeNull();
    expect(capturedBody!.code).toBe('TEST10');
    expect(capturedBody!.plan_id).toBe('plan_annual');
    expect(capturedBody!.amount).toBe(50.0);
  });

  it('test_validate_promo_unauthenticated_rejects_with_401', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/promo/validate`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert - 401 interceptor tries refresh, finds no token
    await expect(
      codesApi.validate({
        code: 'TEST',
        plan_id: 'plan_monthly',
        amount: 50.0,
      }),
    ).rejects.toThrow('No refresh token');
  });

  it('test_validate_promo_with_refresh_token_retries_on_401', async () => {
    // Arrange
    tokenStorage.setTokens('expired_access', 'valid_refresh');

    let callCount = 0;
    server.use(
      http.post(`${API_BASE}/promo/validate`, () => {
        callCount += 1;
        if (callCount === 1) {
          return HttpResponse.json(
            { detail: 'Token expired' },
            { status: 401 },
          );
        }
        return HttpResponse.json({
          promo_code_id: 'promo_retry',
          discount_type: 'percentage',
          discount_value: 15,
          discount_amount: 7.5,
          code: 'RETRY15',
        });
      }),
    );

    // Act
    const response = await codesApi.validate({
      code: 'RETRY15',
      plan_id: 'plan_monthly',
      amount: 50.0,
    });

    // Assert
    expect(callCount).toBe(2);
    expect(response.status).toBe(200);
    expect(response.data.promo_code_id).toBe('promo_retry');
    expect(response.data.discount_amount).toBe(7.5);
  });

  it('test_validate_promo_server_error_500_rejects', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/promo/validate`, () => {
        return HttpResponse.json(
          { detail: 'Internal server error' },
          { status: 500 },
        );
      }),
    );

    // Act & Assert
    try {
      await codesApi.validate({
        code: 'ERROR',
        plan_id: 'plan_monthly',
        amount: 50.0,
      });
      expect.fail('Expected request to reject with 500');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(500);
      }
    }
  });

  it('test_validate_promo_rate_limited_rejects_with_rate_limit_error', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/promo/validate`, () => {
        return HttpResponse.json(
          { detail: 'Too many requests' },
          { status: 429, headers: { 'Retry-After': '30' } },
        );
      }),
    );

    // Act & Assert
    try {
      await codesApi.validate({
        code: 'TEST',
        plan_id: 'plan_monthly',
        amount: 50.0,
      });
      expect.fail('Expected RateLimitError');
    } catch (error: unknown) {
      expect((error as Error).name).toBe('RateLimitError');
      expect((error as { retryAfter: number }).retryAfter).toBe(30);
    }
  });

  it('test_validate_promo_missing_fields_rejects_with_422', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/promo/validate`, () => {
        return HttpResponse.json(
          { detail: 'Missing required fields' },
          { status: 422 },
        );
      }),
    );

    // Act & Assert
    try {
      await codesApi.validate({
        code: '',
        plan_id: '',
        amount: 0,
      });
      expect.fail('Expected request to reject with 422');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(422);
      }
    }
  });
});
