import { beforeEach, describe, expect, it, vi } from 'vitest';

const apiClientMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock('../client', () => ({
  apiClient: apiClientMock,
}));

import { miniappApi } from '../miniapp';

describe('miniappApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('requests bootstrap with optional locale and start param', async () => {
    const response = {
      status: 200,
      data: {
        session: { authenticated: true, userId: 'user-1', telegramUserId: '123', authRealm: 'customer' },
      },
    };
    apiClientMock.get.mockResolvedValue(response);

    const result = await miniappApi.getBootstrap({ locale: 'en-EN', startParam: 'ref_abc' });

    expect(apiClientMock.get).toHaveBeenCalledWith('/miniapp/bootstrap', {
      params: { locale: 'en-EN', startParam: 'ref_abc' },
    });
    expect(result).toBe(response);
  });

  it('requests offers from the dedicated mini app namespace', async () => {
    const response = {
      status: 200,
      data: {
        plans: [],
        addons: [],
        trial: {
          is_trial_active: false,
          is_eligible: true,
          days_remaining: 0,
        },
        currentEntitlements: {
          status: 'none',
          effective_entitlements: {},
          invite_bundle: {},
          is_trial: false,
          addons: [],
        },
      },
    };
    apiClientMock.get.mockResolvedValue(response);

    const result = await miniappApi.getOffers();

    expect(apiClientMock.get).toHaveBeenCalledWith('/miniapp/offers');
    expect(result).toBe(response);
  });

  it('requests config from the dedicated mini app namespace', async () => {
    const response = {
      status: 200,
      data: {
        config: 'vless://generated',
        configString: 'vless://generated',
        clientType: 'vless',
        isFound: true,
        links: ['vless://generated'],
        ssConfLinks: {},
        subscriptionUrl: 'https://example.com/sub',
        generatedAt: '2026-04-22T12:00:00Z',
      },
    };
    apiClientMock.get.mockResolvedValue(response);

    const result = await miniappApi.getConfig();

    expect(apiClientMock.get).toHaveBeenCalledWith('/miniapp/config');
    expect(result).toBe(response);
  });

  it('activates trial from the dedicated mini app namespace', async () => {
    const response = {
      status: 200,
      data: {
        activated: true,
        trial_end: '2026-04-29T00:00:00Z',
        message: 'Trial activated successfully.',
      },
    };
    apiClientMock.post.mockResolvedValue(response);

    const result = await miniappApi.activateTrial();

    expect(apiClientMock.post).toHaveBeenCalledWith('/miniapp/trial/activate', {});
    expect(result).toBe(response);
  });

  it('quotes checkout via the mini app namespace', async () => {
    const payload = {
      flow: 'checkout' as const,
      plan_id: '550e8400-e29b-41d4-a716-446655440000' as never,
      addons: [],
      code_input: 'SAVE20',
      promo_code: undefined,
      partner_code: undefined,
      use_wallet: 0,
      currency: 'USD',
    };
    const response = { status: 200, data: { displayed_price: 79 } };
    apiClientMock.post.mockResolvedValue(response);

    const result = await miniappApi.quoteCheckout(payload);

    expect(apiClientMock.post).toHaveBeenCalledWith('/miniapp/checkout/quote', payload);
    expect(result).toBe(response);
  });

  it('commits checkout via the mini app namespace', async () => {
    const payload = {
      flow: 'checkout' as const,
      plan_id: '550e8400-e29b-41d4-a716-446655440000' as never,
      addons: [],
      code_input: undefined,
      promo_code: undefined,
      partner_code: undefined,
      use_wallet: 0,
      currency: 'XTR',
    };
    const response = { status: 200, data: { payment_id: 'payment-stars-1', status: 'pending' } };
    apiClientMock.post.mockResolvedValue(response);

    const result = await miniappApi.commitCheckout(payload);

    expect(apiClientMock.post).toHaveBeenCalledWith('/miniapp/checkout/commit', payload);
    expect(result).toBe(response);
  });

  it('gets payment status from the mini app namespace', async () => {
    const response = {
      status: 200,
      data: {
        payment_id: 'payment-stars-1',
        status: 'completed',
      },
    };
    apiClientMock.get.mockResolvedValue(response);

    const result = await miniappApi.getPayment('payment-stars-1');

    expect(apiClientMock.get).toHaveBeenCalledWith('/miniapp/payments/payment-stars-1');
    expect(result).toBe(response);
  });
});
