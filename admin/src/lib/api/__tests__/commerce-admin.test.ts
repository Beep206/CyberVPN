import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { addonsApi } from '../addons';
import { publicCatalogApi } from '../catalog';
import { adminWalletApi } from '../wallet';
import { offersApi } from '../offers';
import { plansApi } from '../plans';
import { pricebooksApi } from '../pricebooks';
import { subscriptionsApi } from '../subscriptions';

const MATCH_ANY_API_ORIGIN = {
  plans: /https?:\/\/localhost(?::\d+)?\/api\/v1\/plans$/,
  planById: /https?:\/\/localhost(?::\d+)?\/api\/v1\/plans\/[^/]+$/,
  addons: /https?:\/\/localhost(?::\d+)?\/api\/v1\/addons$/,
  addonById: /https?:\/\/localhost(?::\d+)?\/api\/v1\/addons\/[^/]+$/,
  pricebooksAdmin: /https?:\/\/localhost(?::\d+)?\/api\/v1\/pricebooks\/admin(?:\?.*)?$/,
  pricebooksCommercialAdmin: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/pricebooks(?:\?.*)?$/,
  pricebooksCommercialById: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/pricebooks\/[^/]+$/,
  pricebooksCommercialPublish: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/pricebooks\/[^/]+\/publish$/,
  pricebooksCommercialSchedule: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/pricebooks\/[^/]+\/schedule$/,
  pricebooksCommercialRollback: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/pricebooks\/[^/]+\/rollback$/,
  pricebooksCommercialHistory: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/pricebooks\/[^/]+\/history$/,
  pricebooksCommercialAudit: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/pricebooks\/[^/]+\/audit(?:\?.*)?$/,
  pricebooksCommercialValidate: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/pricebooks\/[^/]+\/validate$/,
  commercialContextOptions: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/commercial-context\/options$/,
  pricebooksCreate: /https?:\/\/localhost(?::\d+)?\/api\/v1\/pricebooks\/?(?:\?.*)?$/,
  pricebooksResolve: /https?:\/\/localhost(?::\d+)?\/api\/v1\/pricebooks\/resolve(?:\?.*)?$/,
  offersAdmin: /https?:\/\/localhost(?::\d+)?\/api\/v1\/offers\/admin(?:\?.*)?$/,
  catalog: /https?:\/\/localhost(?::\d+)?\/api\/v1\/catalog\/?(?:\?.*)?$/,
  catalogContext: /https?:\/\/localhost(?::\d+)?\/api\/v1\/catalog\/context$/,
  storefrontPreview: /https?:\/\/localhost(?::\d+)?\/api\/v1\/storefronts\/[^/]+\/preview(?:\?.*)?$/,
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

function pricebookFixture(overrides: Record<string, unknown> = {}) {
  return {
    id: '550e8400-e29b-41d4-a716-446655440001',
    pricebook_key: 'web_usd_v1',
    display_name: 'Web USD V1',
    storefront_id: '550e8400-e29b-41d4-a716-446655440010',
    merchant_profile_id: null,
    currency_code: 'USD',
    region_code: 'US',
    discount_rules: {},
    renewal_pricing_policy: {},
    version_status: 'active',
    effective_from: '2026-05-01T00:00:00Z',
    effective_to: null,
    is_active: true,
    entries: [],
    lifecycle_status: 'active',
    ...overrides,
  };
}

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

describe('pricebooksApi admin operations', () => {
  it('lists lifecycle-aware admin pricebooks with inactive records included', async () => {
    let includeInactive = '';

    server.use(
      http.get(MATCH_ANY_API_ORIGIN.pricebooksCommercialAdmin, ({ request }) => {
        includeInactive = new URL(request.url).searchParams.get('include_inactive') ?? '';

        return HttpResponse.json([pricebookFixture()]);
      }),
    );

    const response = await pricebooksApi.listCommercialAdmin({ include_inactive: true });

    expect(response.status).toBe(200);
    expect(includeInactive).toBe('true');
    expect(response.data[0]?.pricebook_key).toBe('web_usd_v1');
    expect(response.data[0]?.lifecycle_status).toBe('active');
  });

  it('creates a pricebook with offer entry payloads', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.pricebooksCreate, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json(
          {
            id: '550e8400-e29b-41d4-a716-446655440001',
            pricebook_key: 'web_usd_v2',
            display_name: 'Web USD V2',
            storefront_id: '550e8400-e29b-41d4-a716-446655440010',
            merchant_profile_id: null,
            currency_code: 'USD',
            region_code: 'US',
            discount_rules: { loyalty: true },
            renewal_pricing_policy: {},
            version_status: 'draft',
            effective_from: '2026-06-01T00:00:00Z',
            effective_to: null,
            is_active: true,
            entries: [
              {
                id: '550e8400-e29b-41d4-a716-446655440020',
                offer_id: '550e8400-e29b-41d4-a716-446655440030',
                visible_price: 79,
                compare_at_price: null,
                included_addon_codes: ['extra_device'],
                display_order: 10,
              },
            ],
          },
          { status: 201 },
        );
      }),
    );

    const response = await pricebooksApi.create({
      pricebook_key: 'web_usd_v2',
      display_name: 'Web USD V2',
      storefront_id: '550e8400-e29b-41d4-a716-446655440010',
      merchant_profile_id: null,
      currency_code: 'USD',
      region_code: 'US',
      discount_rules: { loyalty: true },
      renewal_pricing_policy: {},
      version_status: 'draft',
      effective_from: '2026-06-01T00:00:00Z',
      effective_to: null,
      is_active: true,
      entries: [
        {
          offer_id: '550e8400-e29b-41d4-a716-446655440030',
          visible_price: 79,
          compare_at_price: null,
          included_addon_codes: ['extra_device'],
          display_order: 10,
        },
      ],
    });

    expect(response.status).toBe(201);
    expect(response.data.entries[0]?.visible_price).toBe(79);
    expect(capturedBody).toMatchObject({
      pricebook_key: 'web_usd_v2',
      currency_code: 'USD',
    });
  });

  it('updates a lifecycle pricebook with a change reason', async () => {
    let requestedPath = '';
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.patch(MATCH_ANY_API_ORIGIN.pricebooksCommercialById, async ({ request }) => {
        requestedPath = new URL(request.url).pathname.split('/').at(-1) ?? '';
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          pricebook: pricebookFixture({
            id: requestedPath,
            display_name: capturedBody.display_name,
            version_status: 'draft',
            lifecycle_status: 'draft',
          }),
          lifecycle_status: 'draft',
          audit_action: 'pricebook.updated',
        });
      }),
    );

    const response = await pricebooksApi.updateCommercialAdmin(
      '550e8400-e29b-41d4-a716-446655440001',
      {
        display_name: 'Web USD V2',
        change_reason: 'Align web checkout copy',
      },
    );

    expect(response.status).toBe(200);
    expect(requestedPath).toBe('550e8400-e29b-41d4-a716-446655440001');
    expect(response.data.pricebook.display_name).toBe('Web USD V2');
    expect(capturedBody).toMatchObject({
      display_name: 'Web USD V2',
      change_reason: 'Align web checkout copy',
    });
  });

  it('publishes a lifecycle pricebook with an audit reason', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.pricebooksCommercialPublish, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          pricebook: pricebookFixture({
            version_status: 'active',
            lifecycle_status: 'active',
          }),
          lifecycle_status: 'active',
          audit_action: 'pricebook.published',
        });
      }),
    );

    const response = await pricebooksApi.publishCommercialAdmin(
      '550e8400-e29b-41d4-a716-446655440001',
      {
        effective_from: '2026-06-01T00:00:00Z',
        change_reason: 'June pricing launch',
      },
    );

    expect(response.status).toBe(200);
    expect(response.data.lifecycle_status).toBe('active');
    expect(capturedBody).toMatchObject({
      effective_from: '2026-06-01T00:00:00Z',
      change_reason: 'June pricing launch',
    });
  });

  it('schedules a lifecycle pricebook for future activation', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.pricebooksCommercialSchedule, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          pricebook: pricebookFixture({
            version_status: 'scheduled',
            lifecycle_status: 'scheduled',
          }),
          lifecycle_status: 'scheduled',
          audit_action: 'pricebook.scheduled',
        });
      }),
    );

    const response = await pricebooksApi.scheduleCommercialAdmin(
      '550e8400-e29b-41d4-a716-446655440001',
      {
        scheduled_for: '2026-06-15T00:00:00Z',
        change_reason: 'Mid-month rollout',
      },
    );

    expect(response.status).toBe(200);
    expect(response.data.lifecycle_status).toBe('scheduled');
    expect(capturedBody).toMatchObject({
      scheduled_for: '2026-06-15T00:00:00Z',
      change_reason: 'Mid-month rollout',
    });
  });

  it('rolls back a lifecycle pricebook to a target version', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.pricebooksCommercialRollback, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          pricebook: pricebookFixture({
            id: '550e8400-e29b-41d4-a716-446655440099',
            version_status: 'active',
            lifecycle_status: 'active',
          }),
          lifecycle_status: 'active',
          audit_action: 'pricebook.rolled_back',
        });
      }),
    );

    const response = await pricebooksApi.rollbackCommercialAdmin(
      '550e8400-e29b-41d4-a716-446655440001',
      {
        target_pricebook_id: '550e8400-e29b-41d4-a716-446655440099',
        change_reason: 'Rollback failed promo price',
      },
    );

    expect(response.status).toBe(200);
    expect(response.data.audit_action).toBe('pricebook.rolled_back');
    expect(capturedBody).toMatchObject({
      target_pricebook_id: '550e8400-e29b-41d4-a716-446655440099',
      change_reason: 'Rollback failed promo price',
    });
  });

  it('loads lifecycle history and audit entries', async () => {
    let auditLimit = '';

    server.use(
      http.get(MATCH_ANY_API_ORIGIN.pricebooksCommercialHistory, () =>
        HttpResponse.json({
          pricebook_key: 'web_usd_v1',
          versions: [
            pricebookFixture({ lifecycle_status: 'active' }),
            pricebookFixture({
              id: '550e8400-e29b-41d4-a716-446655440099',
              version_status: 'archived',
              lifecycle_status: 'archived',
            }),
          ],
        }),
      ),
      http.get(MATCH_ANY_API_ORIGIN.pricebooksCommercialAudit, ({ request }) => {
        auditLimit = new URL(request.url).searchParams.get('limit') ?? '';

        return HttpResponse.json([
          {
            id: '550e8400-e29b-41d4-a716-446655440070',
            admin_id: '550e8400-e29b-41d4-a716-446655440071',
            action: 'pricebook.published',
            entity_type: 'commercial_pricebook',
            entity_id: '550e8400-e29b-41d4-a716-446655440001',
            old_value: {},
            new_value: {},
            ip_address: '127.0.0.1',
            user_agent: 'vitest',
            created_at: '2026-05-30T10:00:00Z',
          },
        ]);
      }),
    );

    const historyResponse = await pricebooksApi.getCommercialHistory('web_usd_v1');
    const auditResponse = await pricebooksApi.getCommercialAudit(
      '550e8400-e29b-41d4-a716-446655440001',
      { limit: 10 },
    );

    expect(historyResponse.status).toBe(200);
    expect(historyResponse.data.versions).toHaveLength(2);
    expect(auditResponse.status).toBe(200);
    expect(auditLimit).toBe('10');
    expect(auditResponse.data[0]?.action).toBe('pricebook.published');
  });

  it('validates lifecycle pricebook readiness issues', async () => {
    server.use(
      http.post(MATCH_ANY_API_ORIGIN.pricebooksCommercialValidate, () =>
        HttpResponse.json({
          pricebook_id: '550e8400-e29b-41d4-a716-446655440001',
          valid: false,
          checked_at: '2026-05-30T10:00:00Z',
          issues: [
            {
              code: 'missing_price',
              severity: 'error',
              message: 'Offer has no visible price',
              field: 'entries[0].visible_price',
              entry_id: null,
              offer_id: '550e8400-e29b-41d4-a716-446655440030',
              remediation: 'Add a visible price before publishing',
            },
          ],
        }),
      ),
    );

    const response = await pricebooksApi.validateCommercialAdmin(
      '550e8400-e29b-41d4-a716-446655440001',
    );

    expect(response.status).toBe(200);
    expect(response.data.valid).toBe(false);
    expect(response.data.issues[0]?.code).toBe('missing_price');
  });

  it('loads and updates commercial context country and currency options', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.get(MATCH_ANY_API_ORIGIN.commercialContextOptions, () =>
        HttpResponse.json({
          countries: [
            {
              country_code: 'US',
              default_currency_code: 'USD',
              supported_currency_codes: ['USD'],
              payment_country_code: 'US',
              is_enabled: true,
            },
          ],
          currencies: [
            {
              currency_code: 'USD',
              minor_units: 2,
              is_enabled: true,
            },
          ],
          source: 'default',
        }),
      ),
      http.put(MATCH_ANY_API_ORIGIN.commercialContextOptions, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          countries: capturedBody.countries,
          currencies: capturedBody.currencies,
          source: 'system_config',
        });
      }),
    );

    const readResponse = await pricebooksApi.getCommercialContextOptions();
    const updateResponse = await pricebooksApi.updateCommercialContextOptions({
      countries: [
        {
          country_code: 'US',
          default_currency_code: 'USD',
          supported_currency_codes: ['USD'],
          payment_country_code: 'US',
          is_enabled: true,
        },
      ],
      currencies: [
        {
          currency_code: 'USD',
          minor_units: 2,
          is_enabled: true,
        },
      ],
      change_reason: 'Align commercial context defaults',
    });

    expect(readResponse.status).toBe(200);
    expect(readResponse.data.source).toBe('default');
    expect(updateResponse.data.source).toBe('system_config');
    expect(capturedBody).toMatchObject({
      change_reason: 'Align commercial context defaults',
    });
  });
});

describe('offersApi admin operations', () => {
  it('lists admin offers for pricebook entry references', async () => {
    let includeInactive = '';

    server.use(
      http.get(MATCH_ANY_API_ORIGIN.offersAdmin, ({ request }) => {
        includeInactive = new URL(request.url).searchParams.get('include_inactive') ?? '';

        return HttpResponse.json([
          {
            id: '550e8400-e29b-41d4-a716-446655440030',
            offer_key: 'plus_web_365',
            display_name: 'Plus Web Annual',
            subscription_plan_id: '550e8400-e29b-41d4-a716-446655440040',
            included_addon_codes: ['extra_device'],
            sale_channels: ['web'],
            visibility_rules: {},
            invite_bundle: {},
            trial_eligible: false,
            gift_eligible: true,
            referral_eligible: true,
            renewal_incentives: {},
            version_status: 'active',
            effective_from: '2026-05-01T00:00:00Z',
            effective_to: null,
            is_active: true,
          },
        ]);
      }),
    );

    const response = await offersApi.listAdmin({ include_inactive: true });

    expect(response.status).toBe(200);
    expect(includeInactive).toBe('true');
    expect(response.data[0]?.offer_key).toBe('plus_web_365');
  });
});

describe('publicCatalogApi operations', () => {
  it('loads an effective catalog preview with context filters', async () => {
    let requestedCurrency = '';

    server.use(
      http.get(MATCH_ANY_API_ORIGIN.catalog, ({ request }) => {
        const url = new URL(request.url);
        requestedCurrency = url.searchParams.get('currency') ?? '';

        return HttpResponse.json({
          catalogVersion: 'public-commercial-v1',
          cacheKey: 'commercial:context:web:US:USD',
          context: {
            uiLocale: 'en-EN',
            displayCountry: 'US',
            pricingCountry: 'US',
            paymentCountry: 'US',
            currency: 'USD',
            confidence: 'explicit',
            selectableCountries: ['US'],
            selectableCurrencies: ['USD'],
            paymentMethods: {
              availableMethods: ['web_checkout'],
              webCheckout: true,
              cryptobot: false,
              telegramStars: false,
              manualInvoice: false,
              autorenewal: true,
            },
            cacheKey: 'commercial:context:web:US:USD',
            resolutionTrace: ['explicit_currency'],
          },
          plans: [
            {
              planCode: 'plus',
              displayName: 'Plus',
              version: 'plus_web_365',
              billingPeriods: [
                {
                  planId: '550e8400-e29b-41d4-a716-446655440040',
                  catalogItemKey: 'plus_365',
                  durationDays: 365,
                  displayPrice: {
                    amount: '79.00',
                    currency: 'USD',
                    minorUnits: 2,
                  },
                  version: 'plus_web_365',
                  quote: {
                    planId: '550e8400-e29b-41d4-a716-446655440040',
                    planCode: 'plus',
                    billingPeriodDays: 365,
                    currency: 'USD',
                    catalogItemKey: 'plus_365',
                    contextCacheKey: 'commercial:context:web:US:USD',
                  },
                  includedAddonCodes: ['extra_device'],
                  availability: ['web'],
                  metadata: {},
                },
              ],
              devicesIncluded: 5,
              trafficLimitBytes: null,
              trafficPolicy: { mode: 'fair_use' },
              connectionModes: ['standard'],
              serverPool: ['shared_plus'],
              supportSla: 'standard',
              dedicatedIp: { included: 0, eligible: true },
              inviteBundle: {},
              trialEligible: false,
              promoEligible: true,
              metadata: {},
            },
          ],
          addons: [],
          trialEligible: false,
          promoEligible: true,
          metadata: {
            policyIds: ['stage1_paid_plan_policy'],
            source: 'subscription_plans',
            channel: 'web',
            storefrontKey: null,
            addonsEnabled: false,
            promoCodesEnabled: true,
            checkoutCodeDiscountsEnabled: false,
            invalidationEvents: ['PriceBookPublished'],
          },
        });
      }),
    );

    const response = await publicCatalogApi.getCatalog({
      channel: 'web',
      country: 'US',
      currency: 'USD',
      uiLocale: 'en-EN',
    });

    expect(response.status).toBe(200);
    expect(requestedCurrency).toBe('USD');
    expect(response.data.plans[0]?.billingPeriods[0]?.displayPrice.amount).toBe('79.00');
  });

  it('resolves commercial context through the catalog context endpoint', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.catalogContext, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          uiLocale: 'en-EN',
          displayCountry: 'US',
          pricingCountry: 'US',
          paymentCountry: 'US',
          currency: 'USD',
          confidence: 'explicit',
          selectableCountries: ['US'],
          selectableCurrencies: ['USD'],
          paymentMethods: {
            availableMethods: ['web_checkout'],
            webCheckout: true,
            cryptobot: false,
            telegramStars: false,
            manualInvoice: false,
            autorenewal: true,
          },
          cacheKey: 'commercial:context:web:US:USD',
          resolutionTrace: ['explicit_currency'],
        });
      }),
    );

    const response = await publicCatalogApi.resolveContext({
      explicitCountryCode: 'US',
      explicitCurrencyCode: 'USD',
      channelKey: 'web',
    });

    expect(response.status).toBe(200);
    expect(response.data.currency).toBe('USD');
    expect(capturedBody).toMatchObject({
      explicitCountryCode: 'US',
      explicitCurrencyCode: 'USD',
    });
  });

  it('loads a read-only storefront preview with an optional partner code', async () => {
    let requestedStorefrontKey = '';
    let requestedPartnerCode = '';

    server.use(
      http.get(MATCH_ANY_API_ORIGIN.storefrontPreview, ({ request }) => {
        const url = new URL(request.url);
        requestedStorefrontKey = url.pathname.split('/').at(-2) ?? '';
        requestedPartnerCode = url.searchParams.get('partner_code') ?? '';

        return HttpResponse.json({
          storefront_id: '550e8400-e29b-41d4-a716-446655440010',
          storefront_key: requestedStorefrontKey,
          display_name: 'Partner Storefront',
          status: 'active',
          route_contract: {
            storefront_key: requestedStorefrontKey,
            host: 'partner.example',
            preview_api_path: `/api/v1/storefronts/${requestedStorefrontKey}/preview`,
            customer_entry_path: '/storefront/partner',
            route_status: 'preview',
            public_launch_requires_stages: ['legal_acceptance'],
            checkout_side_effects: false,
          },
          branding_boundary: {
            brand_id: '550e8400-e29b-41d4-a716-446655440020',
            brand_key: 'cybervpn',
            brand_display_name: 'CyberVPN',
            brand_status: 'active',
            allowed_customizations: ['logo_lockup'],
            prohibited_claims: ['free_forever'],
            legal_copy_source: 'cybervpn',
          },
          pricing_boundary: {
            display_policy: 'storefront_pricebook',
            finance_policy: 'ledger_review_required',
            offers: [
              {
                pricebook_id: '550e8400-e29b-41d4-a716-446655440030',
                pricebook_key: 'reseller_usd',
                pricebook_display_name: 'Reseller USD',
                currency_code: 'USD',
                region_code: 'US',
                offer_id: '550e8400-e29b-41d4-a716-446655440040',
                offer_key: 'plus_reseller_365',
                offer_display_name: 'Plus reseller annual',
                plan_id: '550e8400-e29b-41d4-a716-446655440050',
                visible_price: 69,
                compare_at_price: 79,
                sale_channels: ['web'],
                pricing_source: 'storefront_pricebook',
              },
            ],
          },
          attribution_contract: {
            owner_type: 'reseller',
            owner_source: 'explicit_code',
            partner_account_id: '550e8400-e29b-41d4-a716-446655440060',
            partner_account_key: 'northstar',
            partner_account_status: 'active',
            partner_code_id: '550e8400-e29b-41d4-a716-446655440070',
            partner_code: requestedPartnerCode,
            partner_code_required_for_reseller: true,
            touchpoint_policy: 'preview_only',
          },
          analytics_contract: {
            preview_records_touchpoint: false,
            checkout_records_storefront_origin: true,
            checkout_records_explicit_code: true,
            expected_dimensions: ['storefront_key', 'partner_code'],
          },
          generated_at: '2026-05-30T12:00:00Z',
        });
      }),
    );

    const response = await publicCatalogApi.previewStorefront('reseller-us', {
      partner_code: 'PARTNER10',
    });

    expect(response.status).toBe(200);
    expect(requestedStorefrontKey).toBe('reseller-us');
    expect(requestedPartnerCode).toBe('PARTNER10');
    expect(response.data.route_contract.checkout_side_effects).toBe(false);
    expect(response.data.pricing_boundary.offers?.[0]?.pricebook_key).toBe('reseller_usd');
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
