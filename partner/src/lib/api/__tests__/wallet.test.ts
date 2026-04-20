/**
 * Wallet API Client Unit Tests
 *
 * Tests the walletApi methods from src/lib/api/wallet.ts
 * Covers balance, transactions, withdrawals, and withdrawal requests
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { walletApi } from '../wallet';
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

/** Mock wallet balance response */
const MOCK_WALLET = {
  id: 'wallet_001',
  balance: 50.75,
  currency: 'USD',
  frozen: 0.0,
};

/** Mock transaction list */
const MOCK_TRANSACTIONS = [
  {
    id: 'tx_001',
    type: 'deposit',
    amount: 100.0,
    balance_after: 150.0,
    reason: 'payment',
    description: 'Payment for subscription',
    created_at: '2025-01-10T10:00:00Z',
  },
  {
    id: 'tx_002',
    type: 'withdrawal',
    amount: -50.0,
    balance_after: 100.0,
    reason: 'withdrawal_request',
    description: 'Withdrawal to bank',
    created_at: '2025-01-15T14:30:00Z',
  },
];

/** Mock withdrawal request */
const MOCK_WITHDRAWAL = {
  id: 'wd_001',
  amount: 25.0,
  currency: 'USD',
  method: 'cryptobot',
  status: 'pending',
  created_at: '2025-01-20T09:00:00Z',
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
// walletApi.getBalance
// ===========================================================================

describe('walletApi.getBalance', () => {
  it('test_get_balance_success_returns_wallet_data', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/wallet`, () => {
        return HttpResponse.json(MOCK_WALLET);
      }),
    );

    // Act
    const response = await walletApi.getBalance();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.id).toBe('wallet_001');
    expect(response.data.balance).toBe(50.75);
    expect(response.data.currency).toBe('USD');
    expect(response.data.frozen).toBe(0.0);
  });

  it('test_get_balance_wallet_not_found_autocreates_with_404', async () => {
    // Arrange - first call 404, auto-creation happens server-side
    server.use(
      http.get(`${API_BASE}/wallet`, () => {
        return HttpResponse.json(
          { detail: 'Wallet not found' },
          { status: 404 },
        );
      }),
    );

    // Act & Assert
    try {
      await walletApi.getBalance();
      expect.fail('Expected 404');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(404);
      }
    }
  });

  it('test_get_balance_unauthenticated_rejects_with_401', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/wallet`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    await expect(walletApi.getBalance()).rejects.toThrow('No refresh token');
  });

  it('test_get_balance_with_refresh_token_retries_on_401', async () => {
    // Arrange
    tokenStorage.setTokens('expired_access', 'valid_refresh');

    let callCount = 0;
    server.use(
      http.get(`${API_BASE}/wallet`, () => {
        callCount += 1;
        if (callCount === 1) {
          return HttpResponse.json(
            { detail: 'Token expired' },
            { status: 401 },
          );
        }
        return HttpResponse.json(MOCK_WALLET);
      }),
    );

    // Act
    const response = await walletApi.getBalance();

    // Assert
    expect(callCount).toBe(2);
    expect(response.status).toBe(200);
    expect(response.data.balance).toBe(50.75);
  });
});

// ===========================================================================
// walletApi.getTransactions
// ===========================================================================

describe('walletApi.getTransactions', () => {
  it('test_get_transactions_success_returns_transaction_list', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/wallet/transactions`, () => {
        return HttpResponse.json(MOCK_TRANSACTIONS);
      }),
    );

    // Act
    const response = await walletApi.getTransactions();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data).toHaveLength(2);
    expect(response.data[0].id).toBe('tx_001');
    expect(response.data[0].type).toBe('deposit');
    expect(response.data[0].amount).toBe(100.0);
    expect(response.data[1].type).toBe('withdrawal');
  });

  it('test_get_transactions_with_pagination_params', async () => {
    // Arrange - capture query params
    let capturedParams: URLSearchParams | null = null;
    server.use(
      http.get(`${API_BASE}/wallet/transactions`, ({ request }) => {
        const url = new URL(request.url);
        capturedParams = url.searchParams;
        return HttpResponse.json(MOCK_TRANSACTIONS.slice(0, 1));
      }),
    );

    // Act
    await walletApi.getTransactions({ offset: 10, limit: 20 });

    // Assert
    expect(capturedParams).not.toBeNull();
    expect(capturedParams!.get('offset')).toBe('10');
    expect(capturedParams!.get('limit')).toBe('20');
  });

  it('test_get_transactions_empty_list_returns_empty_array', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/wallet/transactions`, () => {
        return HttpResponse.json([]);
      }),
    );

    // Act
    const response = await walletApi.getTransactions();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data).toHaveLength(0);
  });

  it('test_get_transactions_unauthenticated_rejects_with_401', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/wallet/transactions`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    await expect(walletApi.getTransactions()).rejects.toThrow('No refresh token');
  });
});

// ===========================================================================
// walletApi.requestWithdrawal
// ===========================================================================

describe('walletApi.requestWithdrawal', () => {
  it('test_request_withdrawal_success_creates_pending_request', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/wallet/withdraw`, async () => {
        return HttpResponse.json(MOCK_WITHDRAWAL, { status: 201 });
      }),
    );

    // Act
    const response = await walletApi.requestWithdrawal({
      amount: 25.0,
      method: 'cryptobot',
    });

    // Assert
    expect(response.status).toBe(201);
    expect(response.data.amount).toBe(25.0);
    expect(response.data.status).toBe('pending');
  });

  it('test_request_withdrawal_sends_correct_body', async () => {
    // Arrange - capture request body
    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post(`${API_BASE}/wallet/withdraw`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(MOCK_WITHDRAWAL, { status: 201 });
      }),
    );

    // Act
    await walletApi.requestWithdrawal({
      amount: 50.0,
      method: 'cryptobot',
    });

    // Assert
    expect(capturedBody).not.toBeNull();
    expect(capturedBody!.amount).toBe(50.0);
    expect(capturedBody!.method).toBe('cryptobot');
  });

  it('test_request_withdrawal_below_minimum_rejects_with_422', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/wallet/withdraw`, async () => {
        return HttpResponse.json(
          { detail: 'Withdrawal amount below minimum' },
          { status: 422 },
        );
      }),
    );

    // Act & Assert
    try {
      await walletApi.requestWithdrawal({
        amount: 1.0,
        method: 'cryptobot',
      });
      expect.fail('Expected 422');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(422);
        expect(error.response?.data.detail).toContain('minimum');
      }
    }
  });

  it('test_request_withdrawal_insufficient_balance_rejects_with_422', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/wallet/withdraw`, async () => {
        return HttpResponse.json(
          { detail: 'Insufficient balance' },
          { status: 422 },
        );
      }),
    );

    // Act & Assert
    try {
      await walletApi.requestWithdrawal({
        amount: 1000.0,
        method: 'cryptobot',
      });
      expect.fail('Expected 422');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(422);
        expect(error.response?.data.detail).toContain('Insufficient');
      }
    }
  });

  it('test_request_withdrawal_invalid_params_rejects_with_400', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/wallet/withdraw`, async () => {
        return HttpResponse.json(
          { detail: 'Invalid withdrawal parameters' },
          { status: 400 },
        );
      }),
    );

    // Act & Assert
    try {
      await walletApi.requestWithdrawal({
        amount: -10.0,
        method: 'invalid_method',
      });
      expect.fail('Expected 400');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(400);
      }
    }
  });

  it('test_request_withdrawal_unauthenticated_rejects_with_401', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/wallet/withdraw`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    await expect(
      walletApi.requestWithdrawal({
        amount: 25.0,
        method: 'cryptobot',
      }),
    ).rejects.toThrow('No refresh token');
  });
});

// ===========================================================================
// walletApi.getWithdrawals
// ===========================================================================

describe('walletApi.getWithdrawals', () => {
  it('test_get_withdrawals_success_returns_withdrawal_list', async () => {
    // Arrange
    const mockWithdrawals = [
      {
        ...MOCK_WITHDRAWAL,
        id: 'wd_001',
        status: 'pending',
      },
      {
        ...MOCK_WITHDRAWAL,
        id: 'wd_002',
        status: 'approved',
      },
      {
        ...MOCK_WITHDRAWAL,
        id: 'wd_003',
        status: 'rejected',
      },
    ];

    server.use(
      http.get(`${API_BASE}/wallet/withdrawals`, () => {
        return HttpResponse.json(mockWithdrawals);
      }),
    );

    // Act
    const response = await walletApi.getWithdrawals();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data).toHaveLength(3);
    expect(response.data[0].status).toBe('pending');
    expect(response.data[1].status).toBe('approved');
    expect(response.data[2].status).toBe('rejected');
  });

  it('test_get_withdrawals_empty_list_returns_empty_array', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/wallet/withdrawals`, () => {
        return HttpResponse.json([]);
      }),
    );

    // Act
    const response = await walletApi.getWithdrawals();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data).toHaveLength(0);
  });

  it('test_get_withdrawals_unauthenticated_rejects_with_401', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/wallet/withdrawals`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    await expect(walletApi.getWithdrawals()).rejects.toThrow('No refresh token');
  });

  it('test_get_withdrawals_rate_limited_rejects_with_rate_limit_error', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/wallet/withdrawals`, () => {
        return HttpResponse.json(
          { detail: 'Too many requests' },
          { status: 429, headers: { 'Retry-After': '60' } },
        );
      }),
    );

    // Act & Assert
    try {
      await walletApi.getWithdrawals();
      expect.fail('Expected RateLimitError');
    } catch (error: unknown) {
      expect((error as Error).name).toBe('RateLimitError');
      expect((error as { retryAfter: number }).retryAfter).toBe(60);
    }
  });

  it('test_get_withdrawals_server_error_500_rejects', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/wallet/withdrawals`, () => {
        return HttpResponse.json(
          { detail: 'Internal server error' },
          { status: 500 },
        );
      }),
    );

    // Act & Assert
    try {
      await walletApi.getWithdrawals();
      expect.fail('Expected 500 error');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(500);
      }
    }
  });
});
