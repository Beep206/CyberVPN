import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  PUBLIC_PRICING_CATALOG_CACHE_TAG,
  getPublicPricingCatalog,
} from '../catalog';

const headersMock = vi.hoisted(() => ({
  cookieValues: new Map<string, string>(),
}));
const nextCacheMock = vi.hoisted(() => ({
  cacheLife: vi.fn(),
  cacheTag: vi.fn(),
}));

vi.mock('next/headers', () => ({
  cookies: vi.fn(async () => ({
    get: (name: string) => {
      const value = headersMock.cookieValues.get(name);
      return value === undefined ? undefined : { name, value };
    },
  })),
}));

vi.mock('next/cache', () => ({
  cacheLife: nextCacheMock.cacheLife,
  cacheTag: nextCacheMock.cacheTag,
}));

const originalApiUrl = process.env.API_URL;
const originalPublicApiUrl = process.env.NEXT_PUBLIC_API_URL;

afterEach(() => {
  headersMock.cookieValues.clear();
  nextCacheMock.cacheLife.mockReset();
  nextCacheMock.cacheTag.mockReset();
  vi.unstubAllGlobals();
  process.env.API_URL = originalApiUrl;
  process.env.NEXT_PUBLIC_API_URL = originalPublicApiUrl;
});

describe('public pricing catalog adapter', () => {
  it('requests backend-owned catalog context and normalizes public plans by storefront rules', async () => {
    process.env.API_URL = 'https://backend.cybervpn.test/';
    headersMock.cookieValues.set('cybervpn_country', ' de ');
    headersMock.cookieValues.set('cybervpn_currency', ' eur ');

    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      void input;
      return new Response(
      JSON.stringify({
        catalogVersion: 'catalog-v2',
        cacheKey: 'catalog-de-eur',
        context: {
          uiLocale: 'de-DE',
          displayCountry: 'DE',
          pricingCountry: 'DE',
          paymentCountry: 'DE',
          currency: 'EUR',
          confidence: 'explicit',
          selectableCountries: ['DE', 'US'],
          selectableCurrencies: ['EUR', 'USD'],
          paymentMethods: {
            availableMethods: ['card', 'crypto'],
            webCheckout: true,
            cryptobot: true,
            telegramStars: false,
            manualInvoice: false,
            autorenewal: true,
          },
          cacheKey: 'ctx-de-eur',
          resolutionTrace: ['explicit_country', 'explicit_currency'],
        },
        plans: [
          {
            planCode: 'enterprise',
            displayName: 'Enterprise',
            devicesIncluded: 99,
            trafficLimitBytes: null,
            trafficPolicy: {},
            connectionModes: ['dedicated'],
            serverPool: ['dedicated'],
            supportSla: 'priority',
            dedicatedIp: { included: 1, eligible: true },
            inviteBundle: { count: 1, friendDays: 7, expiryDays: 14 },
            trialEligible: false,
            promoEligible: false,
            version: 'v1',
            metadata: {},
            billingPeriods: [
              {
                planId: 'enterprise-30',
                catalogItemKey: 'enterprise_30',
                durationDays: 30,
                displayPrice: { amount: '100000', currency: 'EUR', minorUnits: 2 },
                quote: {
                  planId: 'enterprise-30',
                  planCode: 'enterprise',
                  billingPeriodDays: 30,
                  currency: 'EUR',
                  catalogItemKey: 'enterprise_30',
                  contextCacheKey: 'ctx-de-eur',
                },
                includedAddonCodes: [],
                availability: ['web'],
                version: 'v1',
                metadata: {},
              },
            ],
          },
          {
            planCode: 'pro',
            displayName: 'Pro',
            devicesIncluded: 10,
            trafficLimitBytes: null,
            trafficPolicy: {
              mode: 'unlimited',
              displayLabel: 'Unlimited',
              enforcementProfile: 'consumer_pro',
            },
            connectionModes: ['standard', 'stealth'],
            serverPool: ['shared', 'premium'],
            supportSla: 'priority',
            dedicatedIp: { included: '1', eligible: true },
            inviteBundle: { count: '2', friendDays: '14', expiryDays: '30' },
            trialEligible: true,
            promoEligible: true,
            version: 'v2',
            metadata: { badge: 'Best value' },
            billingPeriods: [
              {
                planId: 'pro-400',
                catalogItemKey: 'pro_400',
                durationDays: 400,
                displayPrice: { amount: '10000', currency: 'EUR', minorUnits: 2 },
                quote: {
                  planId: 'pro-400',
                  planCode: 'pro',
                  billingPeriodDays: 400,
                  currency: 'EUR',
                  catalogItemKey: 'pro_400',
                  contextCacheKey: 'ctx-de-eur',
                },
                includedAddonCodes: [],
                availability: ['web'],
                version: 'v2',
                metadata: {},
              },
              {
                planId: 'pro-365',
                catalogItemKey: 'pro_365',
                durationDays: 365,
                displayPrice: { amount: '7999', currency: 'EUR', minorUnits: 2 },
                quote: {
                  planId: 'pro-365',
                  planCode: 'pro',
                  billingPeriodDays: 365,
                  currency: 'EUR',
                  catalogItemKey: 'pro_365',
                  contextCacheKey: 'ctx-de-eur',
                },
                includedAddonCodes: ['dedicated_ip'],
                availability: ['web'],
                version: 'v2',
                metadata: { campaign: 'summer' },
              },
              {
                planId: 'pro-30',
                catalogItemKey: 'pro_30',
                durationDays: 30,
                displayPrice: { amount: '999', currency: 'EUR', minorUnits: 2 },
                quote: {
                  planId: 'pro-30',
                  planCode: 'pro',
                  billingPeriodDays: 30,
                  currency: 'EUR',
                  catalogItemKey: 'pro_30',
                  contextCacheKey: 'ctx-de-eur',
                },
                includedAddonCodes: [],
                availability: ['web'],
                version: 'v2',
                metadata: {},
              },
            ],
          },
          {
            planCode: 'basic',
            displayName: 'Basic',
            devicesIncluded: 2,
            trafficLimitBytes: 1000,
            trafficPolicy: {},
            connectionModes: ['standard'],
            serverPool: ['shared'],
            supportSla: 'standard',
            dedicatedIp: { included: 0, eligible: false },
            inviteBundle: { count: 0, friend_days: 0, expiry_days: 0 },
            trialEligible: false,
            promoEligible: true,
            version: 'v1',
            metadata: {},
            billingPeriods: [
              {
                planId: 'basic-30',
                catalogItemKey: 'basic_30',
                durationDays: 30,
                displayPrice: { amount: '499', currency: 'EUR', minorUnits: 2 },
                quote: {
                  planId: 'basic-30',
                  planCode: 'basic',
                  billingPeriodDays: 30,
                  currency: 'EUR',
                  catalogItemKey: 'basic_30',
                  contextCacheKey: 'ctx-de-eur',
                },
                includedAddonCodes: [],
                availability: ['web'],
                version: 'v1',
                metadata: {},
              },
            ],
          },
        ],
        addons: [
          {
            addonId: 'addon-dedicated-ip',
            code: 'dedicated_ip',
            displayName: 'Dedicated IP',
            durationMode: 'inherits_subscription',
            isStackable: false,
            quantityStep: 1,
            displayPrice: { amount: '300', currency: 'EUR', minorUnits: 2 },
            maxQuantityByPlan: { pro: 1 },
            deltaEntitlements: { dedicated_ip: 1 },
            requiresLocation: true,
            saleChannels: ['web'],
            metadata: { regionRequired: true },
          },
        ],
        trialEligible: true,
        promoEligible: true,
        metadata: {
          source: 'effective_catalog',
          channel: 'web',
          storefrontKey: 'cybervpn-web',
          addonsEnabled: true,
          promoCodesEnabled: true,
          checkoutCodeDiscountsEnabled: true,
          invalidationEvents: ['catalog.updated'],
          policyIds: ['policy-de-eur'],
        },
      }),
      {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      },
      );
    });
    vi.stubGlobal('fetch', fetchMock);

    const catalog = await getPublicPricingCatalog({ locale: 'de-DE' });

    expect(nextCacheMock.cacheLife).toHaveBeenCalledWith({
      stale: 300,
      revalidate: 900,
      expire: 3600,
    });
    expect(nextCacheMock.cacheTag).toHaveBeenCalledWith(PUBLIC_PRICING_CATALOG_CACHE_TAG);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const requestedUrl = new URL(String(fetchMock.mock.calls[0]?.[0]));
    expect(requestedUrl.origin).toBe('https://backend.cybervpn.test');
    expect(requestedUrl.searchParams.get('channel')).toBe('web');
    expect(requestedUrl.searchParams.get('uiLocale')).toBe('de-DE');
    expect(requestedUrl.searchParams.get('urlLocale')).toBe('de-DE');
    expect(requestedUrl.searchParams.get('storefrontKey')).toBe('cybervpn-web');
    expect(requestedUrl.searchParams.get('country')).toBe('DE');
    expect(requestedUrl.searchParams.get('currency')).toBe('EUR');

    expect(catalog.source).toBe('api');
    expect(catalog.cacheKey).toBe('catalog-de-eur');
    expect(catalog.context).toMatchObject({
      displayCountry: 'DE',
      pricingCountry: 'DE',
      currency: 'EUR',
      confidence: 'explicit',
    });
    expect(catalog.plans.map((plan) => plan.code)).toEqual(['basic', 'pro']);
    expect(catalog.periods).toEqual([30, 365]);
    expect(catalog.plans[1]).toMatchObject({
      code: 'pro',
      traffic_policy: {
        mode: 'unlimited',
        display_label: 'Unlimited',
        enforcement_profile: 'consumer_pro',
      },
      dedicated_ip: { included: 1, eligible: true },
      features: { badge: 'Best value' },
      promo_eligible: true,
      periods: [
        {
          uuid: 'pro-30',
          duration_days: 30,
          invite_bundle: { count: 2, friend_days: 14, expiry_days: 30 },
          trial_eligible: true,
        },
        {
          uuid: 'pro-365',
          duration_days: 365,
          included_addon_codes: ['dedicated_ip'],
        },
      ],
    });
    expect(catalog.addons).toEqual([
      expect.objectContaining({
        uuid: 'addon-dedicated-ip',
        code: 'dedicated_ip',
        max_quantity_by_plan: { pro: 1 },
        requires_location: true,
      }),
    ]);
    expect(catalog.metadata).toMatchObject({
      source: 'effective_catalog',
      storefrontKey: 'cybervpn-web',
      addonsEnabled: true,
      policyIds: ['policy-de-eur'],
    });
  });

  it('returns a safe unavailable catalog when backend catalog cannot be reached', async () => {
    process.env.API_URL = 'https://backend.cybervpn.test';
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        void input;
        return new Response('unavailable', { status: 503 });
      }),
    );

    const catalog = await getPublicPricingCatalog({ locale: 'ru-RU' });

    expect(catalog).toMatchObject({
      source: 'unavailable',
      plans: [],
      addons: [],
      periods: [30, 90, 180, 365],
      catalogVersion: 'unavailable',
      metadata: {
        source: 'unavailable',
        channel: 'web',
        storefrontKey: 'cybervpn-web',
      },
      context: {
        uiLocale: 'ru-RU',
        confidence: 'unavailable',
        paymentMethods: {
          webCheckout: false,
          cryptobot: false,
          telegramStars: false,
          manualInvoice: false,
          autorenewal: false,
        },
      },
    });
  });
});
