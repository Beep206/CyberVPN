import { describe, expect, it } from "vitest";

import {
  flattenCommercialCatalogPlans,
  formatCatalogPrice,
} from "./commercial-catalog";
import type { PublicCommercialCatalogResponse } from "../../shared/api/ipc";

const catalog: PublicCommercialCatalogResponse = {
  catalogVersion: "v1",
  cacheKey: "catalog-us-usd",
  context: {
    uiLocale: "en-EN",
    displayCountry: "US",
    pricingCountry: "US",
    paymentCountry: "US",
    currency: "USD",
    confidence: "explicit",
    selectableCountries: ["US"],
    selectableCurrencies: ["USD"],
    paymentMethods: {
      availableMethods: ["crypto"],
      webCheckout: true,
      cryptobot: true,
      telegramStars: false,
      manualInvoice: false,
      autorenewal: false,
    },
    cacheKey: "ctx-us-usd",
    resolutionTrace: [],
  },
  plans: [
    {
      planCode: "plus",
      displayName: "Plus",
      version: "2026.05",
      devicesIncluded: 5,
      trafficLimitBytes: null,
      trafficPolicy: {},
      connectionModes: ["standard", "stealth"],
      serverPool: ["shared_plus"],
      supportSla: "standard",
      dedicatedIp: {},
      inviteBundle: {},
      trialEligible: false,
      promoEligible: true,
      metadata: {},
      billingPeriods: [
        {
          planId: "plus-365",
          catalogItemKey: "plus_365",
          durationDays: 365,
          displayPrice: { amount: "79.99", currency: "USD", minorUnits: 2 },
          version: "2026.05",
          includedAddonCodes: [],
          availability: ["web"],
          metadata: { requires_quote: true },
          quote: {
            planId: "plus-365",
            planCode: "plus",
            billingPeriodDays: 365,
            currency: "USD",
            catalogItemKey: "plus_365",
            contextCacheKey: "ctx-us-usd",
          },
        },
        {
          planId: "plus-30",
          catalogItemKey: "plus_30",
          durationDays: 30,
          displayPrice: { amount: "9.99", currency: "USD", minorUnits: 2 },
          version: "2026.05",
          includedAddonCodes: [],
          availability: ["web"],
          metadata: { requires_quote: true },
          quote: {
            planId: "plus-30",
            planCode: "plus",
            billingPeriodDays: 30,
            currency: "USD",
            catalogItemKey: "plus_30",
            contextCacheKey: "ctx-us-usd",
          },
        },
      ],
    },
  ],
  addons: [],
  trialEligible: false,
  promoEligible: true,
  metadata: {
    policyIds: [],
    source: "effective_catalog",
    channel: "web",
    storefrontKey: null,
    addonsEnabled: false,
    promoCodesEnabled: true,
    checkoutCodeDiscountsEnabled: true,
    invalidationEvents: [],
  },
};

describe("desktop commercial catalog", () => {
  it("flattens backend-owned plans without introducing client price input", () => {
    const options = flattenCommercialCatalogPlans(catalog);

    expect(options).toHaveLength(2);
    expect(options[0]).toMatchObject({
      id: "plus-30",
      planCode: "plus",
      durationDays: 30,
      amount: 9.99,
      quoteCatalogItemKey: "plus_30",
      quoteContextCacheKey: "ctx-us-usd",
    });
    expect(Object.keys(options[0])).not.toContain("priceInput");
    expect(Object.keys(options[0])).not.toContain("visiblePrice");
  });

  it("formats catalog money using Intl with a plain fallback", () => {
    expect(formatCatalogPrice(9.99, "USD", "en-US")).toBe("$9.99");
    expect(formatCatalogPrice(9.99, "BAD", "en-US")).toBe("9.99 BAD");
  });
});
