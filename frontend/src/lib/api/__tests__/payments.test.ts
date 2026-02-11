/**
 * Payments API Client Unit Tests
 *
 * Tests the paymentsApi methods from src/lib/api/payments.ts
 * Covers cryptocurrency invoice creation, status checking, and payment history
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { paymentsApi } from '../payments';
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

/** Mock invoice response */
const MOCK_INVOICE = {
  invoice_id: 'inv_001',
  payment_url: 'https://pay.cryptobot.com/inv_001',
  amount: 9.99,
  currency: 'USD',
  status: 'pending',
  expires_at: '2025-02-10T12:00:00Z',
};

/** Mock payment history */
const MOCK_PAYMENT_HISTORY = {
  payments: [
    {
      id: 'pay_001',
      amount: 9.99,
      currency: 'USD',
      status: 'completed' as const,
      provider: 'cryptobot' as const,
      created_at: '2025-01-10T10:00:00Z',
    },
    {
      id: 'pay_002',
      amount: 14.99,
      currency: 'USD',
      status: 'pending' as const,
      provider: 'yookassa' as const,
      created_at: '2025-02-01T14:30:00Z',
    },
  ],
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
// paymentsApi.createInvoice
// ===========================================================================

describe('paymentsApi.createInvoice', () => {
  it('test_create_invoice_success_returns_payment_url', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/payments/invoice`, async () => {
        return HttpResponse.json(MOCK_INVOICE, { status: 201 });
      }),
    );

    // Act
    const response = await paymentsApi.createInvoice({
      user_uuid: 'user_001',
      plan_id: 'plan_monthly',
      currency: 'USD',
    });

    // Assert
    expect(response.status).toBe(201);
    expect(response.data.invoice_id).toBe('inv_001');
    expect(response.data.amount).toBe(9.99);
    expect(response.data.status).toBe('pending');
    expect(response.data.payment_url).toBe('https://pay.cryptobot.com/inv_001');
  });

  it('test_create_invoice_with_promo_code_applies_discount', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/payments/invoice`, async () => {
        return HttpResponse.json({
          ...MOCK_INVOICE,
          amount: 7.99,
          currency: 2.0,
        }, { status: 201 });
      }),
    );

    // Act
    const response = await paymentsApi.createInvoice({
      user_uuid: "user_001",
      plan_id: "plan_monthly",
      currency: "USD",
      
    });

    // Assert
    expect(response.status).toBe(201);
    expect(response.data.amount).toBe(7.99);
    expect(response.data.currency).toBe(2.0);
  });

  it('test_create_invoice_sends_correct_body', async () => {
    // Arrange - capture request body
    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post(`${API_BASE}/payments/invoice`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(MOCK_INVOICE, { status: 201 });
      }),
    );

    // Act
    await paymentsApi.createInvoice({
      user_uuid: 'user_001',
      plan_id: 'plan_annual',
      currency: 'USD',
    });

    // Assert
    expect(capturedBody).not.toBeNull();
    expect(capturedBody!.user_uuid).toBe('user_001');
    expect(capturedBody!.plan_id).toBe('plan_annual');
    expect(capturedBody!.currency).toBe('USD');
  });

  it('test_create_invoice_invalid_plan_rejects_with_404', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/payments/invoice`, async () => {
        return HttpResponse.json(
          { detail: 'Plan not found' },
          { status: 404 },
        );
      }),
    );

    // Act & Assert
    try {
      await paymentsApi.createInvoice({
        plan_id: 'invalid_plan',
        
      });
      expect.fail('Expected 404');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(404);
        expect(error.response?.data.detail).toContain('not found');
      }
    }
  });

  it('test_create_invoice_invalid_promo_rejects_with_422', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/payments/invoice`, async () => {
        return HttpResponse.json(
          { detail: 'Invalid promo code' },
          { status: 422 },
        );
      }),
    );

    // Act & Assert
    try {
      await paymentsApi.createInvoice({
        plan_id: 'plan_monthly',
        
      });
      expect.fail('Expected 422');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(422);
      }
    }
  });

  it('test_create_invoice_unauthenticated_rejects_with_401', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/payments/invoice`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    await expect(
      paymentsApi.createInvoice({
        plan_id: 'plan_monthly',
        
      }),
    ).rejects.toThrow('No refresh token');
  });

  it('test_create_invoice_with_refresh_token_retries_on_401', async () => {
    // Arrange
    tokenStorage.setTokens('expired_access', 'valid_refresh');

    let callCount = 0;
    server.use(
      http.post(`${API_BASE}/payments/invoice`, () => {
        callCount += 1;
        if (callCount === 1) {
          return HttpResponse.json(
            { detail: 'Token expired' },
            { status: 401 },
          );
        }
        return HttpResponse.json(MOCK_INVOICE, { status: 201 });
      }),
    );

    // Act
    const response = await paymentsApi.createInvoice({
      user_uuid: 'user_001',
      plan_id: 'plan_monthly',
      currency: 'USD',
    });

    // Assert
    expect(callCount).toBe(2);
    expect(response.status).toBe(201);
    expect(response.data.invoice_id).toBe('inv_001');
  });
});

// ===========================================================================
// paymentsApi.getInvoiceStatus
// ===========================================================================

describe('paymentsApi.getInvoiceStatus', () => {
  it('test_get_invoice_status_pending_returns_invoice_data', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/payments/invoice/:id`, () => {
        return HttpResponse.json(MOCK_INVOICE);
      }),
    );

    // Act
    const response = await paymentsApi.getInvoiceStatus('inv_001');

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.invoice_id).toBe('inv_001');
    expect(response.data.status).toBe('pending');
  });

  it('test_get_invoice_status_paid_shows_completed', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/payments/invoice/:id`, () => {
        return HttpResponse.json({
          ...MOCK_INVOICE,
          status: 'completed',
          status: '2025-02-10T10:15:00Z',
        });
      }),
    );

    // Act
    const response = await paymentsApi.getInvoiceStatus('inv_001');

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.status).toBe('completed');
    expect(response.data.status).toBe('2025-02-10T10:15:00Z');
  });

  it('test_get_invoice_status_expired_shows_expired', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/payments/invoice/:id`, () => {
        return HttpResponse.json({
          ...MOCK_INVOICE,
          status: 'expired',
        });
      }),
    );

    // Act
    const response = await paymentsApi.getInvoiceStatus('inv_001');

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.status).toBe('expired');
  });

  it('test_get_invoice_status_not_found_rejects_with_404', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/payments/invoice/:id`, () => {
        return HttpResponse.json(
          { detail: 'Invoice not found' },
          { status: 404 },
        );
      }),
    );

    // Act & Assert
    try {
      await paymentsApi.getInvoiceStatus('invalid_invoice');
      expect.fail('Expected 404');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(404);
      }
    }
  });

  it('test_get_invoice_status_unauthenticated_rejects_with_401', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/payments/invoice/:id`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    await expect(paymentsApi.getInvoiceStatus('inv_001')).rejects.toThrow(
      'No refresh token',
    );
  });

  it('test_get_invoice_status_rate_limited_rejects_with_rate_limit_error', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/payments/invoice/:id`, () => {
        return HttpResponse.json(
          { detail: 'Too many requests' },
          { status: 429, headers: { 'Retry-After': '30' } },
        );
      }),
    );

    // Act & Assert
    try {
      await paymentsApi.getInvoiceStatus('inv_001');
      expect.fail('Expected RateLimitError');
    } catch (error: unknown) {
      expect((error as Error).name).toBe('RateLimitError');
      expect((error as { retryAfter: number }).retryAfter).toBe(30);
    }
  });
});

// ===========================================================================
// paymentsApi.getHistory
// ===========================================================================

describe('paymentsApi.getHistory', () => {
  it('test_get_history_success_returns_payment_list', async () => {
    // Arrange
    const mockHistory = [
      MOCK_PAYMENT_HISTORY.payments[0],
      {
        ...MOCK_PAYMENT_HISTORY.payments[0],
        id: 'pay_002',
        status: 'pending',
        status: undefined,
      },
    ];

    server.use(
      http.get(`${API_BASE}/payments/history`, () => {
        return HttpResponse.json(mockHistory);
      }),
    );

    // Act
    const response = await paymentsApi.getHistory();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data).toHaveLength(2);
    expect(response.data[0].status).toBe('completed');
    expect(response.data[1].status).toBe('pending');
  });

  it('test_get_history_with_pagination_params', async () => {
    // Arrange - capture query params
    let capturedParams: URLSearchParams | null = null;
    server.use(
      http.get(`${API_BASE}/payments/history`, ({ request }) => {
        const url = new URL(request.url);
        capturedParams = url.searchParams;
        return HttpResponse.json([MOCK_PAYMENT_HISTORY.payments[0]]);
      }),
    );

    // Act
    await paymentsApi.getHistory({ offset: 5, limit: 10 });

    // Assert
    expect(capturedParams).not.toBeNull();
    expect(capturedParams!.get('offset')).toBe('5');
    expect(capturedParams!.get('limit')).toBe('10');
  });

  it('test_get_history_empty_list_returns_empty_array', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/payments/history`, () => {
        return HttpResponse.json([]);
      }),
    );

    // Act
    const response = await paymentsApi.getHistory();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data).toHaveLength(0);
  });

  it('test_get_history_unauthenticated_rejects_with_401', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/payments/history`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    await expect(paymentsApi.getHistory()).rejects.toThrow('No refresh token');
  });

  it('test_get_history_server_error_500_rejects', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/payments/history`, () => {
        return HttpResponse.json(
          { detail: 'Internal server error' },
          { status: 500 },
        );
      }),
    );

    // Act & Assert
    try {
      await paymentsApi.getHistory();
      expect.fail('Expected 500 error');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(500);
      }
    }
  });
});
