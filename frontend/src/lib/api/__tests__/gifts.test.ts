import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { giftsApi } from '../gifts';

const API_BASE = '*/api/v1';

beforeEach(() => {
  localStorage.clear();
  window.location.href = 'http://localhost:3000';
});

afterEach(() => {
  window.location.href = 'http://localhost:3000';
});

describe('giftsApi', () => {
  it('lists issued gift codes for the current user', async () => {
    server.use(
      http.get(`${API_BASE}/gifts/my`, () =>
        HttpResponse.json([
          {
            id: 'gift_001',
            masked_code: 'ABCD••••',
            raw_code: 'GIFT-AAA',
            code_type: 'gift',
            status: 'active',
            issuer_type: 'purchase',
            plan_family: 'max',
            duration_days: 365,
            created_at: '2026-04-21T10:00:00Z',
          },
        ]),
      ),
    );

    const response = await giftsApi.listMyGifts();

    expect(response.status).toBe(200);
    expect(response.data[0]?.raw_code).toBe('GIFT-AAA');
  });

  it('commits a gift purchase checkout', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(`${API_BASE}/gifts/purchase/commit`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          quote: {
            gateway_amount: 99,
          },
          payment_id: 'payment_001',
          status: 'pending',
          invoice: {
            payment_url: 'https://payments.example/gift',
          },
          gift_code: null,
        });
      }),
    );

    const response = await giftsApi.commitPurchase({
      plan_id: 'plan_001',
      recipient_hint: 'friend@example.com',
      gift_message: 'Enjoy the VPN',
      channel: 'web',
    });

    expect(response.status).toBe(200);
    expect(response.data.invoice?.payment_url).toBe('https://payments.example/gift');
    expect(capturedBody).toMatchObject({
      plan_id: 'plan_001',
      recipient_hint: 'friend@example.com',
    });
  });
});
