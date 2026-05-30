import { apiClient } from './client';

export type ResolveCatalogContextRequest = {
  urlLocale?: string | null;
  browserLanguage?: string | null;
  telegramLanguageCode?: string | null;
  explicitUiLocale?: string | null;
  explicitCountryCode?: string | null;
  explicitDisplayCountryCode?: string | null;
  explicitPricingCountryCode?: string | null;
  explicitCurrencyCode?: string | null;
  sessionCountryCode?: string | null;
  sessionCurrencyCode?: string | null;
  cookieCountryCode?: string | null;
  cookieCurrencyCode?: string | null;
  channelKey?: string | null;
  channelDefaultLocale?: string | null;
  fallbackCountryCode?: string;
};

export type PaymentMethodAvailabilityResponse = {
  availableMethods: string[];
  webCheckout: boolean;
  cryptobot: boolean;
  telegramStars: boolean;
  manualInvoice: boolean;
  autorenewal: boolean;
};

export type PublicCatalogContextResponse = {
  uiLocale: string;
  displayCountry: string;
  pricingCountry: string;
  paymentCountry: string;
  currency: string;
  confidence: string;
  selectableCountries: string[];
  selectableCurrencies: string[];
  paymentMethods: PaymentMethodAvailabilityResponse;
  cacheKey: string;
  resolutionTrace: string[];
};

export type PublicCatalogMoneyResponse = {
  amount: string;
  currency: string;
  minorUnits: number;
};

export type PublicCatalogQuoteHandoffResponse = {
  planId: string;
  planCode: string;
  billingPeriodDays: number;
  currency: string;
  catalogItemKey: string;
  contextCacheKey: string;
};

export type PublicCatalogBillingPeriodResponse = {
  planId: string;
  catalogItemKey: string;
  durationDays: number;
  displayPrice: PublicCatalogMoneyResponse;
  version: string;
  quote: PublicCatalogQuoteHandoffResponse;
  includedAddonCodes: string[];
  availability: string[];
  metadata: Record<string, unknown>;
};

export type PublicCatalogPlanResponse = {
  planCode: string;
  displayName: string;
  version: string;
  billingPeriods: PublicCatalogBillingPeriodResponse[];
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
};

export type PublicCatalogAddonResponse = {
  addonId: string;
  code: string;
  displayName: string;
  durationMode: string;
  isStackable: boolean;
  quantityStep: number;
  displayPrice: PublicCatalogMoneyResponse;
  maxQuantityByPlan: Record<string, number>;
  deltaEntitlements: Record<string, unknown>;
  requiresLocation: boolean;
  saleChannels: string[];
  metadata: Record<string, unknown>;
};

export type PublicCatalogMetadataResponse = {
  policyIds: string[];
  source: string;
  channel: string;
  storefrontKey: string | null;
  addonsEnabled: boolean;
  promoCodesEnabled: boolean;
  checkoutCodeDiscountsEnabled: boolean;
  invalidationEvents: string[];
};

export type PublicCommercialCatalogResponse = {
  catalogVersion: string;
  cacheKey: string;
  context: PublicCatalogContextResponse;
  plans: PublicCatalogPlanResponse[];
  addons: PublicCatalogAddonResponse[];
  trialEligible: boolean;
  promoEligible: boolean;
  metadata: PublicCatalogMetadataResponse;
};

export type PublicCatalogQueryParams = {
  channel?: string;
  country?: string;
  currency?: string;
  uiLocale?: string;
  urlLocale?: string;
  storefrontKey?: string;
};

export const commercialCatalogApi = {
  resolveContext: (data: ResolveCatalogContextRequest) =>
    apiClient.post<PublicCatalogContextResponse>('/catalog/context', data),

  getCatalog: (params?: PublicCatalogQueryParams) =>
    apiClient.get<PublicCommercialCatalogResponse>('/catalog/', { params }),
};
