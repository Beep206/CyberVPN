export type PricingTierCode = 'basic' | 'plus' | 'pro' | 'max';

export type PricingInviteBundle = {
  count: number;
  friend_days: number;
  expiry_days: number;
};

export type PricingDedicatedIp = {
  included: number;
  eligible: boolean;
};

export type PricingTrafficPolicy = {
  mode: string;
  display_label: string;
  enforcement_profile?: string | null;
};

export type PricingCatalogMoney = {
  amount: string;
  currency: string;
  minorUnits: number;
};

export type PricingQuoteHandoff = {
  planId: string;
  planCode: string;
  billingPeriodDays: number;
  currency: string;
  catalogItemKey: string;
  contextCacheKey: string;
};

export type PricingPlanPeriod = {
  uuid: string;
  name: string;
  duration_days: number;
  display_price: PricingCatalogMoney;
  quote: PricingQuoteHandoff;
  included_addon_codes: string[];
  availability: string[];
  version: string;
  metadata: Record<string, unknown>;
  invite_bundle: PricingInviteBundle;
  trial_eligible: boolean;
  sort_order: number;
};

export type PricingPlanFamily = {
  code: PricingTierCode;
  display_name: string;
  devices_included: number;
  traffic_policy: PricingTrafficPolicy;
  connection_modes: string[];
  server_pool: string[];
  support_sla: string;
  dedicated_ip: PricingDedicatedIp;
  features: Record<string, unknown>;
  traffic_limit_bytes: number | null;
  version: string;
  promo_eligible: boolean;
  periods: PricingPlanPeriod[];
  sort_order: number;
  is_active: boolean;
};

export type PricingAddon = {
  uuid: string;
  code: string;
  display_name: string;
  duration_mode: string;
  is_stackable: boolean;
  quantity_step: number;
  display_price: PricingCatalogMoney;
  max_quantity_by_plan: Record<string, number>;
  delta_entitlements: Record<string, unknown>;
  requires_location: boolean;
  sale_channels: string[];
  is_active: boolean;
  metadata: Record<string, unknown>;
};

export type PricingPaymentMethods = {
  availableMethods: string[];
  webCheckout: boolean;
  cryptobot: boolean;
  telegramStars: boolean;
  manualInvoice: boolean;
  autorenewal: boolean;
};

export type PricingCatalogContext = {
  uiLocale: string;
  displayCountry: string;
  pricingCountry: string;
  paymentCountry: string;
  currency: string;
  confidence: string;
  selectableCountries: string[];
  selectableCurrencies: string[];
  paymentMethods: PricingPaymentMethods;
  cacheKey: string;
  resolutionTrace: string[];
};

export type PricingCatalogData = {
  plans: PricingPlanFamily[];
  addons: PricingAddon[];
  periods: number[];
  context: PricingCatalogContext;
  catalogVersion: string;
  cacheKey: string;
  metadata: {
    source: string;
    channel: string;
    storefrontKey: string | null;
    addonsEnabled: boolean;
    promoCodesEnabled: boolean;
    checkoutCodeDiscountsEnabled: boolean;
    invalidationEvents: string[];
    policyIds: string[];
  };
  source: 'api' | 'unavailable';
};
