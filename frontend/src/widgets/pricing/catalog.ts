import 'server-only';

import { cookies } from 'next/headers';
import type {
  PublicCatalogAddonResponse,
  PublicCatalogContextResponse,
  PublicCatalogPlanResponse,
  PublicCommercialCatalogResponse,
} from '@/lib/api/commercial-catalog';
import { OFFICIAL_WEB_STOREFRONT_KEY } from '@/lib/api/commerce';
import { isSupportedCurrency } from '@/features/currency-selector/currency-config';
import type {
  PricingAddon,
  PricingCatalogContext,
  PricingCatalogData,
  PricingDedicatedIp,
  PricingInviteBundle,
  PricingPlanFamily,
  PricingTierCode,
  PricingTrafficPolicy,
} from '@/widgets/pricing/types';

const PUBLIC_PLAN_ORDER: PricingTierCode[] = ['basic', 'plus', 'pro', 'max'];
const DEFAULT_PERIODS = [30, 90, 180, 365];
const COUNTRY_COOKIE_NAMES = ['cybervpn_country', 'country_code'];
const CURRENCY_COOKIE_NAMES = ['cybervpn_currency', 'currency_code'];
const COUNTRY_CODE_RE = /^[A-Z]{2}$/;

function getApiBaseUrl(): string | null {
  const baseUrl =
    process.env.API_URL?.trim() || process.env.NEXT_PUBLIC_API_URL?.trim();
  if (!baseUrl) {
    return null;
  }

  return baseUrl.replace(/\/$/, '');
}

function normalizeCountryCode(value: string | undefined): string | null {
  if (!value) {
    return null;
  }

  const normalized = value.trim().toUpperCase();
  return COUNTRY_CODE_RE.test(normalized) ? normalized : null;
}

function normalizeCurrencyCode(value: string | undefined): string | null {
  if (!value) {
    return null;
  }

  const normalized = value.trim().toUpperCase();
  return isSupportedCurrency(normalized) ? normalized : null;
}

async function readCommercialCookies() {
  const cookieStore = await cookies();
  const country = COUNTRY_COOKIE_NAMES
    .map((name) => normalizeCountryCode(cookieStore.get(name)?.value))
    .find((value): value is string => Boolean(value));
  const currency = CURRENCY_COOKIE_NAMES
    .map((name) => normalizeCurrencyCode(cookieStore.get(name)?.value))
    .find((value): value is string => Boolean(value));

  return { country, currency };
}

function toNumber(value: unknown, fallback = 0): number {
  const parsed = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function toRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function normalizeTrafficPolicy(raw: Record<string, unknown>): PricingTrafficPolicy {
  return {
    mode: typeof raw.mode === 'string' ? raw.mode : 'fair_use',
    display_label:
      typeof raw.display_label === 'string'
        ? raw.display_label
        : typeof raw.displayLabel === 'string'
          ? raw.displayLabel
          : 'Fair use',
    enforcement_profile:
      typeof raw.enforcement_profile === 'string'
        ? raw.enforcement_profile
        : typeof raw.enforcementProfile === 'string'
          ? raw.enforcementProfile
          : null,
  };
}

function normalizeDedicatedIp(raw: Record<string, unknown>): PricingDedicatedIp {
  return {
    included: toNumber(raw.included),
    eligible: raw.eligible === true,
  };
}

function normalizeInviteBundle(raw: Record<string, unknown>): PricingInviteBundle {
  return {
    count: toNumber(raw.count),
    friend_days: toNumber(raw.friend_days ?? raw.friendDays),
    expiry_days: toNumber(raw.expiry_days ?? raw.expiryDays),
  };
}

function normalizeContext(context: PublicCatalogContextResponse): PricingCatalogContext {
  return {
    uiLocale: context.uiLocale,
    displayCountry: context.displayCountry,
    pricingCountry: context.pricingCountry,
    paymentCountry: context.paymentCountry,
    currency: context.currency,
    confidence: context.confidence,
    selectableCountries: context.selectableCountries,
    selectableCurrencies: context.selectableCurrencies,
    paymentMethods: context.paymentMethods,
    cacheKey: context.cacheKey,
    resolutionTrace: context.resolutionTrace,
  };
}

function getPlanSortOrder(planCode: string): number {
  const index = PUBLIC_PLAN_ORDER.indexOf(planCode as PricingTierCode);
  return index === -1 ? Number.MAX_SAFE_INTEGER : index + 1;
}

function normalizePlan(plan: PublicCatalogPlanResponse): PricingPlanFamily | null {
  if (!PUBLIC_PLAN_ORDER.includes(plan.planCode as PricingTierCode)) {
    return null;
  }

  const periods = plan.billingPeriods
    .filter((period) => DEFAULT_PERIODS.includes(period.durationDays))
    .map((period) => ({
      uuid: period.planId,
      name: period.catalogItemKey,
      duration_days: period.durationDays,
      display_price: period.displayPrice,
      quote: period.quote,
      included_addon_codes: period.includedAddonCodes,
      availability: period.availability,
      version: period.version,
      metadata: period.metadata,
      invite_bundle: normalizeInviteBundle(plan.inviteBundle),
      trial_eligible: plan.trialEligible,
      sort_order: getPlanSortOrder(plan.planCode) * 1000 + period.durationDays,
    }))
    .sort((left, right) => left.duration_days - right.duration_days);

  if (periods.length === 0) {
    return null;
  }

  const metadata = toRecord(plan.metadata);

  return {
    code: plan.planCode as PricingTierCode,
    display_name: plan.displayName,
    devices_included: plan.devicesIncluded,
    traffic_limit_bytes: plan.trafficLimitBytes,
    traffic_policy: normalizeTrafficPolicy(plan.trafficPolicy),
    connection_modes: plan.connectionModes,
    server_pool: plan.serverPool,
    support_sla: plan.supportSla,
    dedicated_ip: normalizeDedicatedIp(plan.dedicatedIp),
    features: metadata,
    version: plan.version,
    promo_eligible: plan.promoEligible,
    periods,
    sort_order: getPlanSortOrder(plan.planCode),
    is_active: true,
  };
}

function normalizeAddon(addon: PublicCatalogAddonResponse): PricingAddon {
  return {
    uuid: addon.addonId,
    code: addon.code,
    display_name: addon.displayName,
    duration_mode: addon.durationMode,
    is_stackable: addon.isStackable,
    quantity_step: addon.quantityStep,
    display_price: addon.displayPrice,
    max_quantity_by_plan: addon.maxQuantityByPlan,
    delta_entitlements: addon.deltaEntitlements,
    requires_location: addon.requiresLocation,
    sale_channels: addon.saleChannels,
    is_active: true,
    metadata: addon.metadata,
  };
}

function buildUnavailableCatalog(locale: string): PricingCatalogData {
  const context: PricingCatalogContext = {
    uiLocale: locale,
    displayCountry: 'US',
    pricingCountry: 'US',
    paymentCountry: 'US',
    currency: 'USD',
    confidence: 'unavailable',
    selectableCountries: ['US'],
    selectableCurrencies: ['USD'],
    paymentMethods: {
      availableMethods: [],
      webCheckout: false,
      cryptobot: false,
      telegramStars: false,
      manualInvoice: false,
      autorenewal: false,
    },
    cacheKey: 'catalog-unavailable',
    resolutionTrace: ['frontend_catalog_unavailable'],
  };

  return {
    plans: [],
    addons: [],
    periods: DEFAULT_PERIODS,
    context,
    catalogVersion: 'unavailable',
    cacheKey: 'catalog-unavailable',
    metadata: {
      source: 'unavailable',
      channel: 'web',
      storefrontKey: OFFICIAL_WEB_STOREFRONT_KEY,
      addonsEnabled: false,
      promoCodesEnabled: false,
      checkoutCodeDiscountsEnabled: false,
      invalidationEvents: [],
      policyIds: [],
    },
    source: 'unavailable',
  };
}

function normalizeCatalog(catalog: PublicCommercialCatalogResponse): PricingCatalogData {
  const plans = catalog.plans
    .map(normalizePlan)
    .filter((plan): plan is PricingPlanFamily => Boolean(plan))
    .sort((left, right) => left.sort_order - right.sort_order);
  const periods = Array.from(
    new Set(
      plans.flatMap((plan) => plan.periods.map((period) => period.duration_days)),
    ),
  ).sort((left, right) => left - right);

  return {
    plans,
    addons: catalog.addons.map(normalizeAddon),
    periods: periods.length > 0 ? periods : DEFAULT_PERIODS,
    context: normalizeContext(catalog.context),
    catalogVersion: catalog.catalogVersion,
    cacheKey: catalog.cacheKey,
    metadata: {
      source: catalog.metadata.source,
      channel: catalog.metadata.channel,
      storefrontKey: catalog.metadata.storefrontKey,
      addonsEnabled: catalog.metadata.addonsEnabled,
      promoCodesEnabled: catalog.metadata.promoCodesEnabled,
      checkoutCodeDiscountsEnabled: catalog.metadata.checkoutCodeDiscountsEnabled,
      invalidationEvents: catalog.metadata.invalidationEvents,
      policyIds: catalog.metadata.policyIds,
    },
    source: 'api',
  };
}

async function fetchJson<T>(input: string): Promise<T> {
  const response = await fetch(input, {
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch ${input}: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function getPublicPricingCatalog({
  locale,
}: {
  locale: string;
}): Promise<PricingCatalogData> {
  const baseUrl = getApiBaseUrl();
  if (!baseUrl) {
    return buildUnavailableCatalog(locale);
  }

  const { country, currency } = await readCommercialCookies();
  const params = new URLSearchParams({
    channel: 'web',
    uiLocale: locale,
    urlLocale: locale,
    storefrontKey: OFFICIAL_WEB_STOREFRONT_KEY,
  });

  if (country) {
    params.set('country', country);
  }
  if (currency) {
    params.set('currency', currency);
  }

  try {
    const catalog = await fetchJson<PublicCommercialCatalogResponse>(
      `${baseUrl}/api/v1/catalog/?${params.toString()}`,
    );
    return normalizeCatalog(catalog);
  } catch {
    return buildUnavailableCatalog(locale);
  }
}
