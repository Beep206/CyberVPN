import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import {
  commerceApi,
  createClientIdempotencyKey,
} from '../commerce';

const API_BASE = 'http://storefront.localhost:3002/api/v1';

beforeEach(() => {
  window.location.href = 'http://storefront.localhost:3002/en-EN/checkout';
});

afterEach(() => {
  window.location.href = 'http://storefront.localhost:3002/en-EN/checkout';
});

describe('commerceApi', () => {
  it('creates quote sessions through the canonical /quotes endpoint', async () => {
    server.use(
      http.post(`${API_BASE}/quotes/`, async ({ request }) => {
        const body = await request.json() as Record<string, unknown>;
        return HttpResponse.json(
          {
            id: 'quote_001',
            storefront_key: body.storefront_key ?? 'ozoxy-storefront',
            plan_id: body.plan_id,
          },
          { status: 201 },
        );
      }),
    );

    const response = await commerceApi.createQuoteSession({
      storefront_key: 'ozoxy-storefront',
      plan_id: 'plan_001',
      currency: 'USD',
      channel: 'partner_storefront',
      use_wallet: 0,
    });

    expect(response.status).toBe(201);
    expect(response.data.id).toBe('quote_001');
  });

  it('sends Idempotency-Key when creating checkout sessions', async () => {
    let capturedIdempotencyKey: string | null = null;
    server.use(
      http.post(`${API_BASE}/checkout-sessions/`, ({ request }) => {
        capturedIdempotencyKey = request.headers.get('Idempotency-Key');
        return HttpResponse.json(
          { id: 'checkout_001', quote_session_id: 'quote_001' },
          { status: 201 },
        );
      }),
    );

    const idempotencyKey = createClientIdempotencyKey('storefront-checkout');
    const response = await commerceApi.createCheckoutSession(
      { quote_session_id: 'quote_001' },
      idempotencyKey,
    );

    expect(response.status).toBe(201);
    expect(capturedIdempotencyKey).toBe(idempotencyKey);
  });
});
