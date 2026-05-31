import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CheckoutCommitResponse, PaymentStatusResponse } from '../payments';

const apiClientMock = vi.hoisted(() => ({
  post: vi.fn(),
  get: vi.fn(),
}));

vi.mock('../client', () => ({
  apiClient: apiClientMock,
}));

import { paymentsApi } from '../payments';

describe('paymentsApi telegram stars helpers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not expose disabled legacy checkout commit helpers', () => {
    expect(paymentsApi).not.toHaveProperty('commitCheckout');
    expect(paymentsApi).not.toHaveProperty('checkout');
  });

  it('commitTelegramStarsCheckout posts to the dedicated endpoint', async () => {
    const payload = {
      plan_id: '550e8400-e29b-41d4-a716-446655440000' as never,
      addons: [],
      code_input: 'SAVE20',
      promo_code: undefined,
      partner_code: undefined,
      use_wallet: 0,
      currency: 'XTR',
      channel: 'miniapp',
    };
    const response: { status: number; data: Partial<CheckoutCommitResponse> } = {
      status: 200,
      data: {
        payment_id: 'payment-stars-1',
        status: 'pending',
      },
    };
    apiClientMock.post.mockResolvedValue(response);

    const result = await paymentsApi.commitTelegramStarsCheckout(payload);

    expect(apiClientMock.post).toHaveBeenCalledWith('/payments/checkout/telegram-stars', payload);
    expect(result).toBe(response);
  });

  it('getPayment fetches a single authenticated payment status', async () => {
    const response: { status: number; data: PaymentStatusResponse } = {
      status: 200,
      data: {
        payment_id: 'payment-stars-1',
        status: 'completed',
        provider: 'telegram_stars',
        external_id: 'charge-1',
        amount: 500,
        currency: 'XTR',
        created_at: '2026-04-21T10:00:00Z',
        updated_at: '2026-04-21T10:01:00Z',
      },
    };
    apiClientMock.get.mockResolvedValue(response);

    const result = await paymentsApi.getPayment('payment-stars-1');

    expect(apiClientMock.get).toHaveBeenCalledWith('/payments/payment-stars-1');
    expect(result).toBe(response);
  });
});
