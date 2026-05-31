import { apiClient } from './client';

export interface PublicPaymentMethodAvailability {
  availableMethods: string[];
  webCheckout: boolean;
  cryptobot: boolean;
  telegramStars: boolean;
  manualInvoice: boolean;
  autorenewal: boolean;
}

export interface PublicCatalogContext {
  uiLocale: string;
  displayCountry: string;
  pricingCountry: string;
  paymentCountry: string;
  currency: string;
  confidence: string;
  selectableCountries: string[];
  selectableCurrencies: string[];
  paymentMethods: PublicPaymentMethodAvailability;
  cacheKey: string;
  resolutionTrace: string[];
}

export interface PublicCatalogMoney {
  amount: string;
  currency: string;
  minorUnits: number;
}

export interface PublicCatalogQuoteHandoff {
  planId: string;
  planCode: string;
  billingPeriodDays: number;
  currency: string;
  catalogItemKey: string;
  contextCacheKey: string;
}

export interface PublicCatalogBillingPeriod {
  planId: string;
  catalogItemKey: string;
  durationDays: number;
  displayPrice: PublicCatalogMoney;
  version: string;
  quote: PublicCatalogQuoteHandoff;
  includedAddonCodes: string[];
  availability: string[];
  metadata: Record<string, unknown>;
}

export interface PublicCatalogPlan {
  planCode: string;
  displayName: string;
  version: string;
  billingPeriods: PublicCatalogBillingPeriod[];
  devicesIncluded: number;
  trafficLimitBytes: number | null;
  trafficPolicy: Record<string, unknown>;
  connectionModes: string[];
  serverPool: string[];
  supportSla: string;
  dedicatedIp: Record<string, unknown>;
  inviteBundle: Record<string, unknown>;
  trialEligible: boolean;
  promoEligible: boolean;
  metadata: Record<string, unknown>;
}

export interface PublicCatalogAddon {
  addonId: string;
  code: string;
  displayName: string;
  durationMode: string;
  isStackable: boolean;
  quantityStep: number;
  displayPrice: PublicCatalogMoney;
  maxQuantityByPlan: Record<string, number>;
  deltaEntitlements: Record<string, unknown>;
  requiresLocation: boolean;
  saleChannels: string[];
  metadata: Record<string, unknown>;
}

export interface PublicCatalogMetadata {
  policyIds: string[];
  source: string;
  channel: string;
  storefrontKey: string | null;
  addonsEnabled: boolean;
  promoCodesEnabled: boolean;
  checkoutCodeDiscountsEnabled: boolean;
  invalidationEvents: string[];
}

export interface PublicCommercialCatalog {
  catalogVersion: string;
  cacheKey: string;
  context: PublicCatalogContext;
  plans: PublicCatalogPlan[];
  addons: PublicCatalogAddon[];
  trialEligible: boolean;
  promoEligible: boolean;
  metadata: PublicCatalogMetadata;
}

export interface GetPublicCatalogParams {
  channel?: string;
  country?: string;
  currency?: string;
  uiLocale?: string;
  urlLocale?: string;
  storefrontKey?: string;
}

export const publicCatalogApi = {
  getCatalog: (params?: GetPublicCatalogParams) =>
    apiClient.get<PublicCommercialCatalog>('/catalog/', { params }),
};
