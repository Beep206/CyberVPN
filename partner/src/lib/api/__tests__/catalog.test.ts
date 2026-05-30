import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { publicCatalogApi } from '../catalog';

const API_BASE = '*/api/v1';

beforeEach(() => {
  window.location.href = 'http://partner.localhost:3002/en-EN/reseller';
});

afterEach(() => {
  window.location.href = 'http://partner.localhost:3002/en-EN/reseller';
});

describe('publicCatalogApi', () => {
  it('loads storefront-scoped effective catalog preview', async () => {
    let storefrontKey = '';
    let requestedCurrency = '';

    server.use(
      http.get(`${API_BASE}/catalog/`, ({ request }) => {
        const url = new URL(request.url);
        storefrontKey = url.searchParams.get('storefrontKey') ?? '';
        requestedCurrency = url.searchParams.get('currency') ?? '';

        return HttpResponse.json({
          catalogVersion: 'public-commercial-v1:storefront:reseller-eu',
          cacheKey: 'commercial:catalog:web:reseller-eu',
          context: {
            uiLocale: 'en-EN',
            displayCountry: 'US',
            pricingCountry: 'US',
            paymentCountry: 'US',
            currency: requestedCurrency,
            confidence: 'explicit',
            selectableCountries: ['US'],
            selectableCurrencies: ['USD'],
            paymentMethods: {
              availableMethods: ['cryptobot'],
              webCheckout: true,
              cryptobot: true,
              telegramStars: false,
              manualInvoice: false,
              autorenewal: true,
            },
            cacheKey: 'commercial:context:web:US:USD',
            resolutionTrace: ['explicit_currency'],
          },
          plans: [],
          addons: [],
          trialEligible: false,
          promoEligible: true,
          metadata: {
            policyIds: ['stage1_paid_plan_policy'],
            source: 'subscription_plans',
            channel: 'web',
            storefrontKey,
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
      currency: 'USD',
      storefrontKey: 'reseller-eu',
      uiLocale: 'en-EN',
    });

    expect(response.status).toBe(200);
    expect(storefrontKey).toBe('reseller-eu');
    expect(requestedCurrency).toBe('USD');
    expect(response.data.metadata.storefrontKey).toBe('reseller-eu');
  });
});
