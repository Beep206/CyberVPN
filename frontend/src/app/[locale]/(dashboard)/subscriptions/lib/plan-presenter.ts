import type { components } from '@/lib/api/generated/types';
import type {
  PublicCatalogMoneyResponse,
  PublicCatalogPlanResponse,
  PublicCatalogQuoteHandoffResponse,
  PublicCommercialCatalogResponse,
} from '@/lib/api/commercial-catalog';
import {
  formatMoney,
  getPricePresentation,
  type LocalDisplayEstimate,
} from '@/shared/lib/pricing-display';

export type SubscriptionPlan = components['schemas']['PlanResponse'] & {
  public_catalog_price?: PublicCatalogMoneyResponse;
  public_catalog_quote?: PublicCatalogQuoteHandoffResponse;
  public_catalog_context_key?: string;
};
export type SubscriptionQuote = components['schemas']['CheckoutQuoteResponse'];

export { formatMoney };

const CONNECTION_MODE_LABELS: Record<string, string> = {
  standard: 'Standard',
  stealth: 'Stealth',
  manual_config: 'Manual / Advanced',
  dedicated_ip: 'Dedicated IP',
};

const SERVER_POOL_LABELS: Record<string, string> = {
  shared: 'Shared pool',
  shared_plus: 'Shared+ pool',
  premium: 'Premium pool',
  exclusive: 'Exclusive pool',
};

const SUPPORT_LABELS: Record<string, string> = {
  standard: 'Standard support',
  priority: 'Priority support',
  vip: 'VIP support',
};

const PUBLIC_PLAN_ORDER = ['basic', 'plus', 'pro', 'max'];

function toNumber(value: unknown, fallback = 0): number {
  const parsed = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function toRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function normalizeTrafficPolicy(value: Record<string, unknown>) {
  return {
    mode: typeof value.mode === 'string' ? value.mode : 'fair_use',
    display_label:
      typeof value.display_label === 'string'
        ? value.display_label
        : typeof value.displayLabel === 'string'
          ? value.displayLabel
          : 'Unlimited',
    enforcement_profile:
      typeof value.enforcement_profile === 'string'
        ? value.enforcement_profile
        : typeof value.enforcementProfile === 'string'
          ? value.enforcementProfile
          : null,
  };
}

function normalizeDedicatedIp(value: Record<string, unknown>) {
  return {
    included: toNumber(value.included),
    eligible: value.eligible === true,
  };
}

function normalizeInviteBundle(value: Record<string, unknown>) {
  return {
    count: toNumber(value.count),
    friend_days: toNumber(value.friend_days ?? value.friendDays),
    expiry_days: toNumber(value.expiry_days ?? value.expiryDays),
  };
}

function planSortOrder(plan: PublicCatalogPlanResponse, durationDays: number) {
  const planIndex = PUBLIC_PLAN_ORDER.indexOf(plan.planCode);
  const planOrder = planIndex === -1 ? PUBLIC_PLAN_ORDER.length : planIndex;
  return planOrder * 1000 + durationDays;
}

export function mapPublicCatalogToSubscriptionPlans(
  catalog: PublicCommercialCatalogResponse,
): SubscriptionPlan[] {
  return catalog.plans.flatMap((plan) => {
    const metadata = toRecord(plan.metadata);

    return plan.billingPeriods.map((period) => ({
      uuid: period.planId,
      name: period.catalogItemKey,
      plan_code: plan.planCode,
      display_name: plan.displayName,
      catalog_visibility: 'public',
      duration_days: period.durationDays,
      traffic_limit_bytes: plan.trafficLimitBytes,
      devices_included: plan.devicesIncluded,
      price_usd: toNumber(period.displayPrice.amount),
      price_rub: null,
      traffic_policy: normalizeTrafficPolicy(plan.trafficPolicy),
      connection_modes: plan.connectionModes,
      server_pool: plan.serverPool,
      support_sla: plan.supportSla,
      dedicated_ip: normalizeDedicatedIp(plan.dedicatedIp),
      sale_channels: [catalog.metadata.channel],
      invite_bundle: normalizeInviteBundle(plan.inviteBundle),
      trial_eligible: plan.trialEligible,
      features: {
        ...metadata,
        catalog_version: catalog.catalogVersion,
        pricing_country: catalog.context.pricingCountry,
        payment_country: catalog.context.paymentCountry,
      },
      is_active: true,
      sort_order: planSortOrder(plan, period.durationDays),
      public_catalog_price: period.displayPrice,
      public_catalog_quote: period.quote,
      public_catalog_context_key: catalog.context.cacheKey,
    }));
  });
}

export function getPlanPrice(plan: SubscriptionPlan, locale: string) {
  if (plan.public_catalog_price) {
    const amount = toNumber(plan.public_catalog_price.amount);
    return {
      amount,
      currency: plan.public_catalog_price.currency,
      formatted: formatMoney(locale, amount, plan.public_catalog_price.currency),
      localEstimate: null,
    };
  }

  const price = getPricePresentation(locale, plan);
  const localEstimate: (LocalDisplayEstimate & { formatted: string }) | null =
    price.localEstimate
      ? {
          ...price.localEstimate,
          formatted: formatMoney(
            locale,
            price.localEstimate.amount,
            price.localEstimate.currency,
          ),
        }
      : null;

  return {
    amount: price.billing.amount,
    currency: price.billing.currency,
    formatted: formatMoney(locale, price.billing.amount, price.billing.currency),
    localEstimate,
  };
}

export function formatDurationLabel(days: number) {
  if (days === 30) return '30 days';
  if (days === 90) return '90 days';
  if (days === 180) return '180 days';
  if (days === 365) return '365 days';
  return `${days} days`;
}

function formatBytesAsTrafficLabel(bytes: number) {
  const gb = bytes / (1024 ** 3);
  if (gb >= 1000) {
    return `${(gb / 1000).toFixed(gb % 1000 === 0 ? 0 : 1)} TB`;
  }

  return `${Math.round(gb)} GB`;
}

export function formatTrafficLabel(plan: SubscriptionPlan) {
  if (plan.traffic_policy?.display_label) {
    return plan.traffic_policy.display_label;
  }

  if (typeof plan.traffic_limit_bytes === 'number' && plan.traffic_limit_bytes > 0) {
    return formatBytesAsTrafficLabel(plan.traffic_limit_bytes);
  }

  return 'Unlimited';
}

export function formatConnectionModes(modes: string[]) {
  if (!modes.length) {
    return 'Standard';
  }

  return modes
    .map((mode) => CONNECTION_MODE_LABELS[mode] ?? mode.replaceAll('_', ' '))
    .join(' + ');
}

export function formatServerPools(pools: string[]) {
  if (!pools.length) {
    return 'Shared pool';
  }

  return pools
    .map((pool) => SERVER_POOL_LABELS[pool] ?? pool.replaceAll('_', ' '))
    .join(' · ');
}

export function formatSupportLabel(supportSla: string) {
  return SUPPORT_LABELS[supportSla] ?? supportSla.replaceAll('_', ' ');
}

export function getInviteLabel(plan: SubscriptionPlan) {
  if (!plan.invite_bundle?.count) {
    return 'No invite bundle';
  }

  const codeLabel = plan.invite_bundle.count === 1 ? 'invite' : 'invites';
  return `${plan.invite_bundle.count} ${codeLabel} for ${plan.invite_bundle.friend_days} days`;
}

export function getPlanHighlights(plan: SubscriptionPlan) {
  const highlights = [
    `${plan.devices_included} ${plan.devices_included === 1 ? 'device' : 'devices'}`,
    formatTrafficLabel(plan),
    formatConnectionModes(plan.connection_modes),
    formatServerPools(plan.server_pool),
    plan.dedicated_ip.included > 0
      ? `${plan.dedicated_ip.included} dedicated IP included`
      : plan.dedicated_ip.eligible
        ? 'Dedicated IP available as add-on'
        : null,
    formatSupportLabel(plan.support_sla),
    plan.invite_bundle.count > 0 ? getInviteLabel(plan) : null,
  ];

  return highlights.filter((item): item is string => Boolean(item));
}

export function getMarketingBadge(plan: SubscriptionPlan) {
  const rawBadge = plan.features?.marketing_badge;
  if (typeof rawBadge === 'string' && rawBadge.trim().length > 0) {
    return rawBadge;
  }

  if (plan.plan_code === 'plus') {
    return 'Most Popular';
  }

  if (plan.plan_code === 'max') {
    return 'Flagship';
  }

  return null;
}
