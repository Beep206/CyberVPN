import type { components } from '@/lib/api/generated/types';

export type AddonRecord = components['schemas']['AddonResponse'];
export type CurrentEntitlement = components['schemas']['CurrentEntitlementStateResponse'];
export type CurrentServiceState = components['schemas']['CurrentServiceStateResponse'];
export type OrderRecord = components['schemas']['OrderResponse'];
export type PlanRecord = components['schemas']['PlanResponse'];
export type TrialStatus = components['schemas']['TrialStatusResponse'];

export type SubscriptionHealth = 'attention' | 'critical' | 'healthy';
export type PlanAction = 'current' | 'downgrade' | 'purchase' | 'upgrade';
export type StatusTone = 'amber' | 'cyan' | 'green' | 'pink' | 'purple';

const BYTE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'] as const;
const INACTIVE_ENTITLEMENT_STATUSES = new Set([
  'blocked',
  'cancelled',
  'disabled',
  'expired',
  'inactive',
  'none',
  'suspended',
]);
const PAID_ORDER_STATUSES = new Set(['paid', 'settled', 'completed']);
const PENDING_ORDER_STATUSES = new Set(['pending', 'pending_payment', 'awaiting_payment']);

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function readEntitlementValue(
  entitlement: CurrentEntitlement | null | undefined,
  key: string,
): unknown {
  return entitlement?.effective_entitlements[key];
}

function normalizeText(value: string | null | undefined): string | null {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}

export function readEntitlementNumber(
  entitlement: CurrentEntitlement | null | undefined,
  key: string,
): number | null {
  const value = readEntitlementValue(entitlement, key);

  if (isFiniteNumber(value)) {
    return value;
  }

  if (typeof value === 'string') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  return null;
}

export function readEntitlementString(
  entitlement: CurrentEntitlement | null | undefined,
  key: string,
): string | null {
  const value = readEntitlementValue(entitlement, key);
  return typeof value === 'string' ? normalizeText(value) : null;
}

export function readEntitlementStringArray(
  entitlement: CurrentEntitlement | null | undefined,
  key: string,
): string[] {
  const value = readEntitlementValue(entitlement, key);

  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter(
    (item): item is string => typeof item === 'string' && item.trim().length > 0,
  );
}

export function formatMoney(locale: string, amount: number, currency: string): string {
  const safeAmount = isFiniteNumber(amount) ? amount : 0;
  const safeCurrency = currency.trim().length === 3 ? currency.toUpperCase() : 'USD';

  try {
    return new Intl.NumberFormat(locale, {
      currency: safeCurrency,
      maximumFractionDigits: safeAmount % 1 === 0 ? 0 : 2,
      style: 'currency',
    }).format(safeAmount);
  } catch {
    return `${safeAmount.toFixed(2)} ${safeCurrency}`;
  }
}

export function formatBytes(bytes: number | null | undefined, locale = 'en-EN'): string {
  if (!isFiniteNumber(bytes) || bytes <= 0) {
    return `0 ${BYTE_UNITS[0]}`;
  }

  const exponent = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    BYTE_UNITS.length - 1,
  );
  const value = bytes / 1024 ** exponent;

  try {
    return `${new Intl.NumberFormat(locale, {
      maximumFractionDigits: value >= 10 ? 0 : 1,
    }).format(value)} ${BYTE_UNITS[exponent]}`;
  } catch {
    return `${value.toFixed(value >= 10 ? 0 : 1)} ${BYTE_UNITS[exponent]}`;
  }
}

export function formatDate(value: string | null | undefined, locale = 'en-EN'): string | null {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  try {
    return new Intl.DateTimeFormat(locale, { dateStyle: 'medium' }).format(date);
  } catch {
    return date.toISOString().slice(0, 10);
  }
}

export function getDaysUntilExpiry(
  entitlement: CurrentEntitlement | null | undefined,
  now = new Date(),
): number | null {
  if (!entitlement?.expires_at) {
    return null;
  }

  const expiresAt = new Date(entitlement.expires_at);
  if (Number.isNaN(expiresAt.getTime())) {
    return null;
  }

  return Math.ceil((expiresAt.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
}

export function isInactiveEntitlement(
  entitlement: CurrentEntitlement | null | undefined,
): boolean {
  if (!entitlement) {
    return true;
  }

  return INACTIVE_ENTITLEMENT_STATUSES.has(entitlement.status.toLowerCase());
}

export function isServiceProvisioned(
  serviceState: CurrentServiceState | null | undefined,
): boolean {
  return Boolean(
    serviceState?.service_identity &&
      serviceState.provisioning_profile &&
      serviceState.access_delivery_channel,
  );
}

export function getSubscriptionHealth({
  entitlement,
  serviceState,
  trial,
  now = new Date(),
}: {
  entitlement?: CurrentEntitlement | null;
  now?: Date;
  serviceState?: CurrentServiceState | null;
  trial?: TrialStatus | null;
}): SubscriptionHealth {
  if (isInactiveEntitlement(entitlement) && !trial?.is_trial_active) {
    return 'critical';
  }

  const daysUntilExpiry = getDaysUntilExpiry(entitlement, now);
  if (daysUntilExpiry !== null && daysUntilExpiry <= 0) {
    return 'critical';
  }

  if (daysUntilExpiry !== null && daysUntilExpiry <= 3) {
    return 'attention';
  }

  if (serviceState === null || (serviceState && !isServiceProvisioned(serviceState))) {
    return 'attention';
  }

  if (trial?.is_trial_active && trial.days_remaining <= 2) {
    return 'attention';
  }

  return 'healthy';
}

export function getPublicPlans(plans: PlanRecord[]): PlanRecord[] {
  return [...plans]
    .filter((plan) => plan.is_active && plan.catalog_visibility === 'public')
    .sort((first, second) => first.sort_order - second.sort_order);
}

export function getCurrentPlan(
  entitlement: CurrentEntitlement | null | undefined,
  plans: PlanRecord[],
): PlanRecord | null {
  if (!entitlement) {
    return null;
  }

  return (
    plans.find(
      (plan) => plan.uuid === entitlement.plan_uuid || plan.plan_code === entitlement.plan_code,
    ) ?? null
  );
}

export function getPlanAction({
  currentPlan,
  entitlement,
  targetPlan,
}: {
  currentPlan?: PlanRecord | null;
  entitlement?: CurrentEntitlement | null;
  targetPlan: PlanRecord;
}): PlanAction {
  if (
    currentPlan &&
    (targetPlan.uuid === currentPlan.uuid || targetPlan.plan_code === currentPlan.plan_code)
  ) {
    return 'current';
  }

  if (isInactiveEntitlement(entitlement)) {
    return 'purchase';
  }

  const currentRank = currentPlan?.sort_order ?? 0;
  return targetPlan.sort_order > currentRank ? 'upgrade' : 'downgrade';
}

export function getVisibleAddons(
  addons: AddonRecord[],
  currentPlanCode: string | null | undefined,
): AddonRecord[] {
  return [...addons]
    .filter((addon) => {
      if (!addon.is_active || !addon.sale_channels.includes('web')) {
        return false;
      }

      if (!currentPlanCode) {
        return true;
      }

      const maxQuantity = addon.max_quantity_by_plan[currentPlanCode];
      return maxQuantity === undefined || maxQuantity > 0;
    })
    .sort((first, second) => first.price_usd - second.price_usd);
}

export function getPlanPrice(plan: PlanRecord, locale: string) {
  if (locale.startsWith('ru') && isFiniteNumber(plan.price_rub) && plan.price_rub > 0) {
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

export function getAddonPrice(addon: AddonRecord, locale: string) {
  if (locale.startsWith('ru') && isFiniteNumber(addon.price_rub) && addon.price_rub > 0) {
    return formatMoney(locale, addon.price_rub, 'RUB');
  }

  return formatMoney(locale, addon.price_usd, 'USD');
}

export function formatDuration(days: number): string {
  if (days === 1) {
    return '1 day';
  }

  return `${days} days`;
}

export function formatLabel(value: string | null | undefined, fallback: string): string {
  const normalized = normalizeText(value);

  if (!normalized) {
    return fallback;
  }

  return normalized
    .replace(/[_-]+/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((part) => `${part[0]?.toUpperCase() ?? ''}${part.slice(1)}`)
    .join(' ');
}

export function getTrafficLabel(plan: PlanRecord, locale = 'en-EN'): string {
  if (plan.traffic_policy.display_label) {
    return plan.traffic_policy.display_label;
  }

  return plan.traffic_limit_bytes ? formatBytes(plan.traffic_limit_bytes, locale) : 'Unlimited';
}

export function getOrderDisplayName(order: OrderRecord, plans: PlanRecord[]): string {
  const firstItem = order.items?.[0];
  if (firstItem?.display_name) {
    return firstItem.display_name;
  }

  const matchingPlan = plans.find((plan) => plan.uuid === order.subscription_plan_id);
  return matchingPlan?.display_name ?? `Order ${order.id.slice(0, 8)}`;
}

export function getOrderStatus(order: OrderRecord): string {
  return order.settlement_status || order.order_status;
}

export function getOrderTone(order: OrderRecord): StatusTone {
  const status = getOrderStatus(order).toLowerCase();

  if (PAID_ORDER_STATUSES.has(status)) {
    return 'green';
  }

  if (PENDING_ORDER_STATUSES.has(status)) {
    return 'cyan';
  }

  if (status.includes('refund')) {
    return 'purple';
  }

  return 'amber';
}

export function getSortedOrders(orders: OrderRecord[]): OrderRecord[] {
  return [...orders].sort(
    (first, second) =>
      new Date(second.created_at).getTime() - new Date(first.created_at).getTime(),
  );
}
