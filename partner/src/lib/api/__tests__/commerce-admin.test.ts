import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { addonsApi } from '../addons';
import { adminWalletApi } from '../wallet';
import { plansApi } from '../plans';
import { subscriptionsApi } from '../subscriptions';

const MATCH_ANY_API_ORIGIN = {
  plans: /https?:\/\/localhost(?::\d+)?\/api\/v1\/plans$/,
  planById: /https?:\/\/localhost(?::\d+)?\/api\/v1\/plans\/[^/]+$/,
  addons: /https?:\/\/localhost(?::\d+)?\/api\/v1\/addons$/,
  addonById: /https?:\/\/localhost(?::\d+)?\/api\/v1\/addons\/[^/]+$/,
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
          name: 'plus_365',
          plan_code: 'plus',
          display_name: 'Plus',
          catalog_visibility: 'public',
          duration_days: 365,
          devices_included: 5,
          price_usd: 79,
          price_rub: null,
          traffic_policy: { mode: 'fair_use', display_label: 'Unlimited' },
          connection_modes: ['standard', 'stealth'],
          server_pool: ['shared_plus'],
          support_sla: 'standard',
          dedicated_ip: { included: 0, eligible: true },
          sale_channels: ['web', 'miniapp'],
          invite_bundle: { count: 2, friend_days: 14, expiry_days: 60 },
          trial_eligible: false,
          features: { marketing_badge: 'Most Popular' },
          is_active: true,
          sort_order: 30,
        }, { status: 201 });
      }),
    );

    const response = await plansApi.create({
      name: 'plus_365',
      plan_code: 'plus',
      display_name: 'Plus',
      catalog_visibility: 'public',
      duration_days: 365,
      devices_included: 5,
      price_usd: 79,
      traffic_policy: { mode: 'fair_use', display_label: 'Unlimited' },
      connection_modes: ['standard', 'stealth'],
      server_pool: ['shared_plus'],
      support_sla: 'standard',
      dedicated_ip: { included: 0, eligible: true },
      sale_channels: ['web', 'miniapp'],
      invite_bundle: { count: 2, friend_days: 14, expiry_days: 60 },
      trial_eligible: false,
      features: { marketing_badge: 'Most Popular' },
      is_active: true,
      sort_order: 30,
    });

    expect(response.status).toBe(201);
    expect(response.data.uuid).toBe('plan_001');
    expect(capturedBody).toMatchObject({
      name: 'plus_365',
      plan_code: 'plus',
      duration_days: 365,
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
          plan_code: body.plan_code,
          display_name: body.display_name,
          catalog_visibility: 'hidden',
          duration_days: 90,
          devices_included: 10,
          price_usd: 29.99,
          price_rub: null,
          traffic_policy: { mode: 'fair_use', display_label: 'Unlimited' },
          connection_modes: ['standard', 'stealth', 'manual_config'],
          server_pool: ['premium_shared'],
          support_sla: 'priority',
          dedicated_ip: { included: 0, eligible: true },
          sale_channels: ['admin'],
          invite_bundle: { count: 1, friend_days: 14, expiry_days: 60 },
          trial_eligible: false,
          features: { audience: 'power_user' },
          is_active: false,
          sort_order: 40,
        });
      }),
    );

    const response = await plansApi.update('plan_001', {
      name: 'pro_90',
      plan_code: 'pro',
      display_name: 'Pro',
      is_active: false,
    });

    expect(response.status).toBe(200);
    expect(requestedPath).toBe('plan_001');
    expect(response.data.name).toBe('pro_90');
  });
});

describe('addonsApi admin operations', () => {
  it('creates an addon with the expected payload', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.addons, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          uuid: 'addon_001',
          code: 'extra_device',
          display_name: '+1 device',
          duration_mode: 'inherits_subscription',
          is_stackable: true,
          quantity_step: 1,
          price_usd: 6,
          price_rub: null,
          max_quantity_by_plan: { basic: 2, plus: 3, pro: 5, max: 10 },
          delta_entitlements: { device_limit: 1 },
          requires_location: false,
          sale_channels: ['web', 'miniapp'],
          is_active: true,
        }, { status: 201 });
      }),
    );

    const response = await addonsApi.create({
      code: 'extra_device',
      display_name: '+1 device',
      duration_mode: 'inherits_subscription',
      is_stackable: true,
      quantity_step: 1,
      price_usd: 6,
      max_quantity_by_plan: { basic: 2, plus: 3, pro: 5, max: 10 },
      delta_entitlements: { device_limit: 1 },
      requires_location: false,
      sale_channels: ['web', 'miniapp'],
      is_active: true,
    });

    expect(response.status).toBe(201);
    expect(response.data.code).toBe('extra_device');
    expect(capturedBody).toMatchObject({
      code: 'extra_device',
      quantity_step: 1,
      is_active: true,
    });
  });

  it('updates an addon through the UUID route', async () => {
    let requestedPath = '';

    server.use(
      http.put(MATCH_ANY_API_ORIGIN.addonById, async ({ request }) => {
        requestedPath = new URL(request.url).pathname.split('/').at(-1) ?? '';
        const body = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          uuid: requestedPath,
          code: 'dedicated_ip',
          display_name: body.display_name,
          duration_mode: 'inherits_subscription',
          is_stackable: true,
          quantity_step: 1,
          price_usd: 24,
          price_rub: null,
          max_quantity_by_plan: {},
          delta_entitlements: { dedicated_ip_count: 1 },
          requires_location: true,
          sale_channels: ['web', 'miniapp'],
          is_active: false,
        });
      }),
    );

    const response = await addonsApi.update('addon_001', {
      display_name: 'Dedicated IP',
      is_active: false,
    });

    expect(response.status).toBe(200);
    expect(requestedPath).toBe('addon_001');
    expect(response.data.display_name).toBe('Dedicated IP');
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
