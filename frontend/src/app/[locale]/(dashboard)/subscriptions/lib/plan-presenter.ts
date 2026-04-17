import type { components } from '@/lib/api/generated/types';

export type SubscriptionPlan = components['schemas']['PlanResponse'];
export type SubscriptionQuote = components['schemas']['CheckoutQuoteResponse'];

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

export function formatMoney(locale: string, amount: number, currency: string) {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    maximumFractionDigits: amount % 1 === 0 ? 0 : 2,
  }).format(amount);
}

export function getPlanPrice(plan: SubscriptionPlan, locale: string) {
  if (locale.startsWith('ru') && typeof plan.price_rub === 'number' && plan.price_rub > 0) {
    return {
      amount: plan.price_rub,
      currency: 'RUB',
      formatted: formatMoney(locale, plan.price_rub, 'RUB'),
    };
  }

  return {
    amount: plan.price_usd,
    currency: 'USD',
    formatted: formatMoney(locale, plan.price_usd, 'USD'),
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
