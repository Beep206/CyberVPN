import 'server-only';

import { cacheLife, cacheTag } from 'next/cache';
import type { AddonRecord } from '@/lib/api/addons';
import type { PlanRecord } from '@/lib/api/plans';
import type {
  PricingAddon,
  PricingCatalogData,
  PricingDedicatedIp,
  PricingInviteBundle,
  PricingPlanFamily,
  PricingTierCode,
  PricingTrafficPolicy,
} from '@/widgets/pricing/types';

const PUBLIC_PLAN_ORDER: PricingTierCode[] = ['basic', 'plus', 'pro', 'max'];
const DEFAULT_PERIODS = [30, 90, 180, 365];

type FallbackPlanSeed = {
  display_name: string;
  devices_included: number;
  traffic_policy: PricingTrafficPolicy;
  connection_modes: string[];
  server_pool: string[];
  support_sla: string;
  dedicated_ip: PricingDedicatedIp;
  features: Record<string, unknown>;
  sort_order: number;
  periods: Record<number, { price_usd: number; invite_bundle: PricingInviteBundle }>;
};

const FALLBACK_PLAN_SEEDS: Record<PricingTierCode, FallbackPlanSeed> = {
  basic: {
    display_name: 'Basic',
    devices_included: 2,
    traffic_policy: {
      mode: 'fair_use',
      display_label: 'Unlimited',
      enforcement_profile: 'consumer_entry',
    },
    connection_modes: ['standard'],
    server_pool: ['shared'],
    support_sla: 'standard',
    dedicated_ip: { included: 0, eligible: true },
    features: { marketing_badge: 'Starter', audience: 'single_user' },
    sort_order: 20,
    periods: {
      30: { price_usd: 5.99, invite_bundle: { count: 0, friend_days: 0, expiry_days: 0 } },
      90: { price_usd: 14.99, invite_bundle: { count: 0, friend_days: 0, expiry_days: 0 } },
      180: { price_usd: 27.99, invite_bundle: { count: 0, friend_days: 0, expiry_days: 0 } },
      365: { price_usd: 49.99, invite_bundle: { count: 1, friend_days: 7, expiry_days: 30 } },
    },
  },
  plus: {
    display_name: 'Plus',
    devices_included: 5,
    traffic_policy: {
      mode: 'fair_use',
      display_label: 'Unlimited',
      enforcement_profile: 'mainstream',
    },
    connection_modes: ['standard', 'stealth'],
    server_pool: ['shared_plus'],
    support_sla: 'standard',
    dedicated_ip: { included: 0, eligible: true },
    features: { marketing_badge: 'Most Popular', audience: 'mass_market' },
    sort_order: 30,
    periods: {
      30: { price_usd: 8.99, invite_bundle: { count: 0, friend_days: 0, expiry_days: 0 } },
      90: { price_usd: 22.99, invite_bundle: { count: 0, friend_days: 0, expiry_days: 0 } },
      180: { price_usd: 39.99, invite_bundle: { count: 1, friend_days: 7, expiry_days: 30 } },
      365: { price_usd: 79.0, invite_bundle: { count: 2, friend_days: 14, expiry_days: 60 } },
    },
  },
  pro: {
    display_name: 'Pro',
    devices_included: 10,
    traffic_policy: {
      mode: 'fair_use',
      display_label: 'Unlimited',
      enforcement_profile: 'power_user',
    },
    connection_modes: ['standard', 'stealth', 'manual_config'],
    server_pool: ['premium_shared'],
    support_sla: 'priority',
    dedicated_ip: { included: 0, eligible: true },
    features: { marketing_badge: 'Best Balance', audience: 'power_user' },
    sort_order: 40,
    periods: {
      30: { price_usd: 11.99, invite_bundle: { count: 0, friend_days: 0, expiry_days: 0 } },
      90: { price_usd: 29.99, invite_bundle: { count: 0, friend_days: 0, expiry_days: 0 } },
      180: { price_usd: 49.99, invite_bundle: { count: 1, friend_days: 14, expiry_days: 60 } },
      365: { price_usd: 89.0, invite_bundle: { count: 2, friend_days: 14, expiry_days: 60 } },
    },
  },
  max: {
    display_name: 'Max',
    devices_included: 15,
    traffic_policy: {
      mode: 'fair_use',
      display_label: 'Unlimited',
      enforcement_profile: 'premium_consumer',
    },
    connection_modes: ['standard', 'stealth', 'manual_config', 'dedicated_ip'],
    server_pool: ['premium', 'exclusive'],
    support_sla: 'vip',
    dedicated_ip: { included: 1, eligible: true },
    features: { marketing_badge: 'Most Complete', audience: 'family_premium' },
    sort_order: 50,
    periods: {
      30: { price_usd: 14.99, invite_bundle: { count: 0, friend_days: 0, expiry_days: 0 } },
      90: { price_usd: 36.99, invite_bundle: { count: 0, friend_days: 0, expiry_days: 0 } },
      180: { price_usd: 59.99, invite_bundle: { count: 1, friend_days: 14, expiry_days: 60 } },
      365: { price_usd: 99.0, invite_bundle: { count: 3, friend_days: 14, expiry_days: 60 } },
    },
  },
};

const FALLBACK_ADDONS: PricingAddon[] = [
  {
    uuid: 'fallback-extra-device',
    code: 'extra_device',
    display_name: '+1 device',
    duration_mode: 'inherits_subscription',
    is_stackable: true,
    quantity_step: 1,
    price_usd: 6,
    price_rub: null,
    max_quantity_by_plan: {
      basic: 2,
      plus: 3,
      pro: 5,
      max: 10,
    },
    delta_entitlements: { device_limit: 1 },
    requires_location: false,
    sale_channels: ['web', 'miniapp', 'telegram_bot', 'admin'],
    is_active: true,
  },
  {
    uuid: 'fallback-dedicated-ip',
    code: 'dedicated_ip',
    display_name: 'Dedicated IP',
    duration_mode: 'inherits_subscription',
    is_stackable: true,
    quantity_step: 1,
    price_usd: 24,
    price_rub: null,
    max_quantity_by_plan: {},
    delta_entitlements: { dedicated_ip_count: 1 },
    requires_location: true,
    sale_channels: ['web', 'miniapp', 'telegram_bot', 'admin'],
    is_active: true,
  },
];

function getApiBaseUrl(): string | null {
  const baseUrl = process.env.API_URL?.trim() || process.env.NEXT_PUBLIC_API_URL?.trim();
  if (!baseUrl) {
    return null;
  }

  return baseUrl.replace(/\/$/, '');
}

function normalizePlanFamilies(records: PlanRecord[]): PricingPlanFamily[] {
  const buckets = new Map<PricingTierCode, PricingPlanFamily>();

  for (const record of records) {
    if (!PUBLIC_PLAN_ORDER.includes(record.plan_code as PricingTierCode)) {
      continue;
    }

    if (!record.is_active) {
      continue;
    }

    const code = record.plan_code as PricingTierCode;
    const existing = buckets.get(code);
    const period = {
      uuid: record.uuid,
      name: record.name,
      duration_days: record.duration_days,
      price_usd: record.price_usd,
      price_rub: record.price_rub ?? null,
      invite_bundle: record.invite_bundle,
      trial_eligible: record.trial_eligible,
      sort_order: record.sort_order,
    };

    if (!existing) {
      buckets.set(code, {
        code,
        display_name: record.display_name,
        devices_included: record.devices_included,
        traffic_policy: record.traffic_policy,
        connection_modes: record.connection_modes,
        server_pool: record.server_pool,
        support_sla: record.support_sla,
        dedicated_ip: record.dedicated_ip,
        features: record.features ?? {},
        periods: [period],
        sort_order: record.sort_order,
        is_active: record.is_active,
      });
      continue;
    }

    existing.periods.push(period);
    existing.sort_order = Math.min(existing.sort_order, record.sort_order);
  }

  return PUBLIC_PLAN_ORDER
    .map((code) => buckets.get(code))
    .filter((plan): plan is PricingPlanFamily => Boolean(plan))
    .map((plan) => ({
      ...plan,
      periods: [...plan.periods].sort((left, right) => left.duration_days - right.duration_days),
    }));
}

function buildFallbackCatalog(): PricingCatalogData {
  const plans = PUBLIC_PLAN_ORDER.map((code) => {
    const seed = FALLBACK_PLAN_SEEDS[code];
    return {
      code,
      display_name: seed.display_name,
      devices_included: seed.devices_included,
      traffic_policy: seed.traffic_policy,
      connection_modes: seed.connection_modes,
      server_pool: seed.server_pool,
      support_sla: seed.support_sla,
      dedicated_ip: seed.dedicated_ip,
      features: seed.features,
      sort_order: seed.sort_order,
      is_active: true,
      periods: DEFAULT_PERIODS.map((durationDays) => ({
        uuid: `${code}-${durationDays}`,
        name: `${code}_${durationDays}`,
        duration_days: durationDays,
        price_usd: seed.periods[durationDays].price_usd,
        price_rub: null,
        invite_bundle: seed.periods[durationDays].invite_bundle,
        trial_eligible: false,
        sort_order: seed.sort_order + durationDays,
      })),
    };
  });

  return {
    plans,
    addons: FALLBACK_ADDONS,
    periods: DEFAULT_PERIODS,
    source: 'fallback',
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

export async function getPublicPricingCatalog(): Promise<PricingCatalogData> {
  'use cache';
  cacheLife('hours');
  cacheTag('pricing-catalog');

  const baseUrl = getApiBaseUrl();
  if (!baseUrl) {
    return buildFallbackCatalog();
  }

  try {
    const [plans, addons] = await Promise.all([
      fetchJson<PlanRecord[]>(`${baseUrl}/api/v1/plans?channel=web`),
      fetchJson<AddonRecord[]>(`${baseUrl}/api/v1/addons/catalog?channel=web`),
    ]);
    const normalizedPlans = normalizePlanFamilies(plans);

    if (normalizedPlans.length === 0) {
      return buildFallbackCatalog();
    }

    const periods = Array.from(
      new Set(normalizedPlans.flatMap((plan) => plan.periods.map((period) => period.duration_days))),
    ).sort((left, right) => left - right);

    return {
      plans: normalizedPlans,
      addons: addons.filter((addon) => addon.is_active),
      periods: periods.length > 0 ? periods : DEFAULT_PERIODS,
      source: 'api',
    };
  } catch {
    return buildFallbackCatalog();
  }
}
