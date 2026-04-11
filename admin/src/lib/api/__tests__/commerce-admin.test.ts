import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { adminWalletApi } from '../wallet';
import { plansApi } from '../plans';
import { subscriptionsApi } from '../subscriptions';

const MATCH_ANY_API_ORIGIN = {
  plans: /https?:\/\/localhost(?::\d+)?\/api\/v1\/plans$/,
  planById: /https?:\/\/localhost(?::\d+)?\/api\/v1\/plans\/[^/]+$/,
  subscriptions: /https?:\/\/localhost(?::\d+)?\/api\/v1\/subscriptions\/$/,
  subscriptionById: /https?:\/\/localhost(?::\d+)?\/api\/v1\/subscriptions\/[^/]+$/,
  walletByUser: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/wallets\/[^/]+$/,
  walletTopup: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/wallets\/[^/]+\/topup$/,
};

beforeEach(() => {
  localStorage.clear();
  window.location.href = 'http://localhost:3000';
});

afterEach(() => {
  window.location.href = 'http://localhost:3000';
});

describe('plansApi admin operations', () => {
  it('creates a plan with the expected payload', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.plans, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          uuid: 'plan_001',
          name: 'Premium Monthly',
          price: 9.99,
          currency: 'USD',
          durationDays: 30,
          dataLimitGb: 100,
          maxDevices: 5,
          features: ['Priority routing'],
          isActive: true,
        });
      }),
    );

    const response = await plansApi.create({
      name: 'Premium Monthly',
      price: 9.99,
      currency: 'USD',
      duration_days: 30,
      data_limit_gb: 100,
      max_devices: 5,
      features: ['Priority routing'],
      is_active: true,
    });

    expect(response.status).toBe(200);
    expect(response.data.uuid).toBe('plan_001');
    expect(capturedBody).toMatchObject({
      name: 'Premium Monthly',
      duration_days: 30,
      is_active: true,
    });
  });

  it('updates a plan through the UUID route', async () => {
    let requestedPath = '';

    server.use(
      http.put(MATCH_ANY_API_ORIGIN.planById, async ({ request }) => {
        requestedPath = new URL(request.url).pathname.split('/').at(-1) ?? '';
        const body = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          uuid: requestedPath,
          name: body.name,
          price: body.price,
          currency: 'USD',
          durationDays: 90,
          isActive: false,
        });
      }),
    );

    const response = await plansApi.update('plan_001', {
      name: 'Premium Quarterly',
      price: 19.99,
      is_active: false,
    });

    expect(response.status).toBe(200);
    expect(requestedPath).toBe('plan_001');
    expect(response.data.name).toBe('Premium Quarterly');
  });
});

describe('subscriptionsApi admin operations', () => {
  it('creates a subscription template with config data', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.subscriptions, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          uuid: 'sub_001',
          name: 'VLESS Vision',
          templateType: 'vless',
          hostUuid: 'host_001',
          inboundTag: 'vless-in',
          flow: 'xtls-rprx-vision',
          configData: { security: 'reality' },
        });
      }),
    );

    const response = await subscriptionsApi.create({
      name: 'VLESS Vision',
      template_type: 'vless',
      host_uuid: 'host_001',
      inbound_tag: 'vless-in',
      flow: 'xtls-rprx-vision',
      config_data: { security: 'reality' },
    });

    expect(response.status).toBe(200);
    expect(response.data.uuid).toBe('sub_001');
    expect(capturedBody).toMatchObject({
      template_type: 'vless',
      inbound_tag: 'vless-in',
    });
  });

  it('deletes a subscription template by UUID', async () => {
    let deletedUuid = '';

    server.use(
      http.delete(MATCH_ANY_API_ORIGIN.subscriptionById, ({ request }) => {
        deletedUuid = new URL(request.url).pathname.split('/').at(-1) ?? '';
        return HttpResponse.json({ ok: true });
      }),
    );

    const response = await subscriptionsApi.remove('sub_001');

    expect(response.status).toBe(200);
    expect(deletedUuid).toBe('sub_001');
  });
});

describe('adminWalletApi operations', () => {
  it('loads wallet state for a specific user UUID', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.walletByUser, ({ request }) =>
        HttpResponse.json({
          id: new URL(request.url).pathname.split('/').at(-1) ?? 'unknown',
          balance: 125.5,
          currency: 'USD',
          frozen: 20,
        }),
      ),
    );

    const response = await adminWalletApi.getWallet(
      '550e8400-e29b-41d4-a716-446655440000',
    );

    expect(response.status).toBe(200);
    expect(response.data.balance).toBe(125.5);
    expect(response.data.currency).toBe('USD');
  });

  it('tops up a wallet with amount and description', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.walletTopup, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          id: 'tx_001',
          type: 'credit',
          amount: 50,
          balance_after: 175.5,
          reason: 'admin_topup',
          description: 'Manual correction',
          created_at: '2026-04-10T10:30:00Z',
        });
      }),
    );

    const response = await adminWalletApi.topupWallet(
      '550e8400-e29b-41d4-a716-446655440000',
      {
        amount: 50,
        description: 'Manual correction',
      },
    );

    expect(response.status).toBe(200);
    expect(response.data.amount).toBe(50);
    expect(capturedBody).toMatchObject({
      amount: 50,
      description: 'Manual correction',
    });
  });
});
