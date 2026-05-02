import type { components } from '@/lib/api/generated/types';
import type { GrowthNotificationCounters } from '@/lib/api/growth-notifications';

export type CurrentEntitlementState =
  components['schemas']['CurrentEntitlementStateResponse'];
export type CurrentServiceState =
  components['schemas']['CurrentServiceStateResponse'];
export type ProfileResponse = components['schemas']['ProfileResponse'];
export type ReferralStatsResponse =
  components['schemas']['ReferralStatsResponse'];
export type TrialStatusResponse = components['schemas']['TrialStatusResponse'];
export type UsageResponse = components['schemas']['UsageResponse'];
export type WalletResponse = components['schemas']['WalletResponse'];

export type CabinetActionId =
  | 'finishProvisioning'
  | 'getConfig'
  | 'inviteFriends'
  | 'managePlan'
  | 'reviewNotifications'
  | 'secureAccount'
  | 'startTrial'
  | 'watchTraffic';
export type CabinetHealth = 'critical' | 'attention' | 'healthy';

const BYTE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'] as const;
const INACTIVE_ENTITLEMENT_STATUSES = [
  'blocked',
  'disabled',
  'expired',
  'inactive',
  'suspended',
] as const;

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function parseNumericString(value: string): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function getEntitlementValue(
  entitlement: CurrentEntitlementState | null | undefined,
  key: string,
): unknown {
  return entitlement?.effective_entitlements[key];
}

export function readEntitlementNumber(
  entitlement: CurrentEntitlementState | null | undefined,
  key: string,
): number | null {
  const value = getEntitlementValue(entitlement, key);

  if (isFiniteNumber(value)) {
    return value;
  }

  if (typeof value === 'string') {
    return parseNumericString(value);
  }

  return null;
}

export function readEntitlementString(
  entitlement: CurrentEntitlementState | null | undefined,
  key: string,
): string | null {
  const value = getEntitlementValue(entitlement, key);

  if (typeof value === 'string' && value.trim().length > 0) {
    return value;
  }

  return null;
}

export function readEntitlementStringArray(
  entitlement: CurrentEntitlementState | null | undefined,
  key: string,
): string[] {
  const value = getEntitlementValue(entitlement, key);

  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter(
    (item): item is string => typeof item === 'string' && item.length > 0,
  );
}

export function formatBytes(
  bytes: number | null | undefined,
  locale = 'en-EN',
): string {
  if (!isFiniteNumber(bytes) || bytes <= 0) {
    return `0 ${BYTE_UNITS[0]}`;
  }

  const exponent = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    BYTE_UNITS.length - 1,
  );
  const value = bytes / 1024 ** exponent;

  try {
    const formatted = new Intl.NumberFormat(locale, {
      maximumFractionDigits: value >= 10 ? 0 : 1,
    }).format(value);

    return `${formatted} ${BYTE_UNITS[exponent]}`;
  } catch {
    return `${value.toFixed(value >= 10 ? 0 : 1)} ${BYTE_UNITS[exponent]}`;
  }
}

export function formatDate(
  value: string | null | undefined,
  locale = 'en-EN',
): string | null {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  try {
    return new Intl.DateTimeFormat(locale, {
      dateStyle: 'medium',
    }).format(date);
  } catch {
    return date.toISOString().slice(0, 10);
  }
}

export function formatDateTime(
  value: string | null | undefined,
  locale = 'en-EN',
): string | null {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  try {
    return new Intl.DateTimeFormat(locale, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(date);
  } catch {
    return date.toISOString();
  }
}

export function formatMoney(
  amount: number | null | undefined,
  currency = 'USD',
  locale = 'en-EN',
): string {
  const safeAmount = isFiniteNumber(amount) ? amount : 0;
  const safeCurrency = currency.trim().length === 3 ? currency : 'USD';

  try {
    return new Intl.NumberFormat(locale, {
      currency: safeCurrency.toUpperCase(),
      style: 'currency',
    }).format(safeAmount);
  } catch {
    return `${safeAmount.toFixed(2)} ${safeCurrency.toUpperCase()}`;
  }
}

export function getUsagePercentage(
  usage: UsageResponse | null | undefined,
): number | null {
  if (!usage || usage.bandwidth_limit_bytes <= 0) {
    return null;
  }

  const rawPercentage =
    (usage.bandwidth_used_bytes / usage.bandwidth_limit_bytes) * 100;

  return Math.min(100, Math.max(0, Math.round(rawPercentage)));
}

export function getDaysUntilExpiry(
  entitlement: CurrentEntitlementState | null | undefined,
  now = new Date(),
): number | null {
  if (!entitlement?.expires_at) {
    return null;
  }

  const expiresAt = new Date(entitlement.expires_at);
  if (Number.isNaN(expiresAt.getTime())) {
    return null;
  }

  return Math.ceil(
    (expiresAt.getTime() - now.getTime()) / (1000 * 60 * 60 * 24),
  );
}

export function isInactiveEntitlement(
  entitlement: CurrentEntitlementState | null | undefined,
): boolean {
  if (entitlement === null) {
    return true;
  }

  const status = entitlement?.status.toLowerCase();
  return Boolean(
    status &&
      INACTIVE_ENTITLEMENT_STATUSES.includes(
        status as (typeof INACTIVE_ENTITLEMENT_STATUSES)[number],
      ),
  );
}

export function isServiceProvisioned(
  serviceState: CurrentServiceState | null | undefined,
): boolean {
  return Boolean(
    serviceState?.device_credential &&
      serviceState.provisioning_profile &&
      serviceState.access_delivery_channel,
  );
}

export function getServiceAccessLabel(
  channelType: string | null | undefined,
  fallback: string,
): string {
  if (!channelType || channelType.trim().length === 0) {
    return fallback;
  }

  return channelType
    .replace(/[_-]+/g, ' ')
    .trim()
    .split(' ')
    .filter(Boolean)
    .map((part) => `${part[0]?.toUpperCase() ?? ''}${part.slice(1)}`)
    .join(' ');
}

export function getCabinetHealth({
  entitlement,
  notifications,
  serviceState,
  usage,
  now = new Date(),
}: {
  entitlement?: CurrentEntitlementState | null;
  notifications?: GrowthNotificationCounters | null;
  serviceState?: CurrentServiceState | null;
  usage?: UsageResponse | null;
  now?: Date;
}): CabinetHealth {
  if (isInactiveEntitlement(entitlement)) {
    return 'critical';
  }

  const daysUntilExpiry = getDaysUntilExpiry(entitlement, now);
  if (daysUntilExpiry !== null && daysUntilExpiry <= 0) {
    return 'critical';
  }
  if (daysUntilExpiry !== null && daysUntilExpiry <= 3) {
    return 'attention';
  }

  const usagePercentage = getUsagePercentage(usage);
  if (usagePercentage !== null && usagePercentage >= 95) {
    return 'critical';
  }

  if ((notifications?.action_required_notifications ?? 0) > 0) {
    return 'attention';
  }

  if (serviceState === null || (serviceState && !isServiceProvisioned(serviceState))) {
    return 'attention';
  }

  if (usagePercentage !== null && usagePercentage >= 80) {
    return 'attention';
  }

  return 'healthy';
}

export function getCabinetActionIds({
  entitlement,
  notifications,
  serviceState,
  trial,
  usage,
  now = new Date(),
}: {
  entitlement?: CurrentEntitlementState | null;
  notifications?: GrowthNotificationCounters | null;
  serviceState?: CurrentServiceState | null;
  trial?: TrialStatusResponse | null;
  usage?: UsageResponse | null;
  now?: Date;
}): CabinetActionId[] {
  const actions: CabinetActionId[] = [];
  const addAction = (action: CabinetActionId) => {
    if (!actions.includes(action)) {
      actions.push(action);
    }
  };

  const entitlementInactive = isInactiveEntitlement(entitlement);
  if (entitlementInactive) {
    addAction(trial?.is_eligible ? 'startTrial' : 'managePlan');
  }

  const daysUntilExpiry = getDaysUntilExpiry(entitlement, now);
  if (!entitlementInactive && daysUntilExpiry !== null && daysUntilExpiry <= 7) {
    addAction('managePlan');
  }

  if (serviceState === null || (serviceState && !isServiceProvisioned(serviceState))) {
    addAction('finishProvisioning');
  }

  const usagePercentage = getUsagePercentage(usage);
  if (usagePercentage !== null && usagePercentage >= 80) {
    addAction('watchTraffic');
  }

  if ((notifications?.action_required_notifications ?? 0) > 0) {
    addAction('reviewNotifications');
  }

  addAction('getConfig');
  addAction('secureAccount');
  addAction('inviteFriends');
  addAction('managePlan');

  return actions.slice(0, 4);
}
