import { afterEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { commercialCatalogApi } from '../commercial-catalog';
import { server } from '@/test/mocks/server';

const API_BASE = '*/api/v1';

afterEach(() => {
  server.resetHandlers();
});

describe('commercialCatalogApi', () => {
  it('resolves public catalog context with separated locale country and currency signals', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(`${API_BASE}/catalog/context`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          uiLocale: 'ru-RU',
          displayCountry: 'DE',
          pricingCountry: 'DE',
          paymentCountry: 'DE',
          currency: 'EUR',
          confidence: 'explicit',
          selectableCountries: ['DE', 'US'],
          selectableCurrencies: ['EUR', 'USD'],
          paymentMethods: {
            availableMethods: ['crypto'],
            webCheckout: true,
            cryptobot: true,
            telegramStars: false,
            manualInvoice: false,
            autorenewal: false,
          },
          cacheKey: 'ctx-de-eur',
          resolutionTrace: ['explicit_country'],
        });
      }),
    );

    const response = await commercialCatalogApi.resolveContext({
      urlLocale: 'ru-RU',
      explicitCountryCode: 'DE',
      explicitCurrencyCode: 'EUR',
      channelKey: 'web',
    });

    expect(response.data).toMatchObject({
      uiLocale: 'ru-RU',
      pricingCountry: 'DE',
      currency: 'EUR',
    });
    expect(capturedBody).toMatchObject({
      urlLocale: 'ru-RU',
      explicitCountryCode: 'DE',
      explicitCurrencyCode: 'EUR',
      channelKey: 'web',
    });
  });

  it('requests the backend-owned catalog without client price input', async () => {
    let requestUrl: string | null = null;

    server.use(
      http.get(`${API_BASE}/catalog/`, ({ request }) => {
        requestUrl = request.url;
        return HttpResponse.json({
          catalogVersion: 'v1',
          cacheKey: 'catalog-de-eur',
          context: {
            uiLocale: 'de-DE',
            displayCountry: 'DE',
            pricingCountry: 'DE',
            paymentCountry: 'DE',
            currency: 'EUR',
            confidence: 'explicit',
            selectableCountries: ['DE'],
            selectableCurrencies: ['EUR'],
            paymentMethods: {
              availableMethods: ['crypto'],
              webCheckout: true,
              cryptobot: true,
              telegramStars: false,
              manualInvoice: false,
              autorenewal: false,
            },
            cacheKey: 'ctx-de-eur',
            resolutionTrace: [],
          },
          plans: [],
          addons: [],
          trialEligible: false,
          promoEligible: true,
          metadata: {
            policyIds: [],
            source: 'effective_catalog',
            channel: 'web',
            storefrontKey: 'cybervpn-web',
            addonsEnabled: false,
            promoCodesEnabled: true,
            checkoutCodeDiscountsEnabled: true,
            invalidationEvents: [],
          },
        });
      }),
    );

    const response = await commercialCatalogApi.getCatalog({
      channel: 'web',
      country: 'DE',
      currency: 'EUR',
      uiLocale: 'de-DE',
    });

    expect(response.data.cacheKey).toBe('catalog-de-eur');
    expect(requestUrl).toContain('country=DE');
    expect(requestUrl).toContain('currency=EUR');
    expect(requestUrl).not.toContain('amount=');
    expect(requestUrl).not.toContain('price=');
  });
});
