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
export type CabinetStateTone = 'amber' | 'cyan' | 'green' | 'pink' | 'purple';

export type Stage1DashboardAccessState =
  | 'active'
  | 'checking'
  | 'expired'
  | 'grace'
  | 'no_access'
  | 'payment_pending'
  | 'provisioning_pending'
  | 'trial_active';
export type Stage1DashboardPaymentState =
  | 'checking'
  | 'expired'
  | 'failed'
  | 'not_started'
  | 'paid'
  | 'pending'
  | 'processing'
  | 'reconciliation_required'
  | 'refunded';
export type Stage1DashboardProvisioningState =
  | 'checking'
  | 'failed'
  | 'not_required'
  | 'pending'
  | 'ready'
  | 'reconciliation_required'
  | 'remnawave_unavailable'
  | 'retrying';
export type Stage1DashboardStateId = 'access' | 'payment' | 'provisioning';
export type Stage1DashboardStateCard = {
  actionId: CabinetActionId | null;
  id: Stage1DashboardStateId;
  state:
    | Stage1DashboardAccessState
    | Stage1DashboardPaymentState
    | Stage1DashboardProvisioningState;
  tone: CabinetStateTone;
};

const BYTE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'] as const;
const INACTIVE_ENTITLEMENT_STATUSES = [
  'blocked',
  'disabled',
  'expired',
  'inactive',
  'suspended',
] as const;
const GRACE_ENTITLEMENT_STATUSES = new Set([
  'grace',
  'grace_period',
  'in_grace',
]);
const TRIAL_ENTITLEMENT_STATUSES = new Set([
  'trial',
  'trial_active',
  'trialing',
]);
const PAYMENT_PENDING_ENTITLEMENT_STATUSES = new Set([
  'awaiting_payment',
  'payment_pending',
  'pending_payment',
]);
const PROVISIONING_PENDING_ENTITLEMENT_STATUSES = new Set([
  'awaiting_provisioning',
  'pending_provisioning',
  'provisioning',
  'provisioning_pending',
]);
const PAYMENT_STATE_ALIASES: Record<string, Stage1DashboardPaymentState> = {
  action_required: 'reconciliation_required',
  cancelled: 'expired',
  captured: 'paid',
  chargeback: 'reconciliation_required',
  completed: 'paid',
  confirmed: 'paid',
  done: 'paid',
  expired: 'expired',
  failed: 'failed',
  manual_review: 'reconciliation_required',
  new: 'not_started',
  paid: 'paid',
  partially_refunded: 'refunded',
  pending: 'pending',
  processing: 'processing',
  reconciled: 'paid',
  reconciliation_required: 'reconciliation_required',
  refunded: 'refunded',
  rejected: 'failed',
  requires_action: 'reconciliation_required',
  started: 'pending',
  succeeded: 'paid',
  timeout: 'expired',
};
const PROVISIONING_STATE_ALIASES: Record<
  string,
  Stage1DashboardProvisioningState
> = {
  action_required: 'reconciliation_required',
  available: 'ready',
  complete: 'ready',
  completed: 'ready',
  failed: 'failed',
  manual_review: 'reconciliation_required',
  missing: 'pending',
  pending: 'pending',
  provisioned: 'ready',
  provisioning: 'pending',
  ready: 'ready',
  reconciliation_required: 'reconciliation_required',
  remnawave_down: 'remnawave_unavailable',
  remnawave_unavailable: 'remnawave_unavailable',
  retry: 'retrying',
  retrying: 'retrying',
  unavailable: 'remnawave_unavailable',
};

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

function normalizeStateValue(value: string | null | undefined): string | null {
  const normalized = value?.trim().toLowerCase().replace(/[\s-]+/g, '_');
  return normalized && normalized.length > 0 ? normalized : null;
}

function getNormalizedEntitlementStatus(
  entitlement: CurrentEntitlementState | null | undefined,
): string | null {
  return normalizeStateValue(entitlement?.status);
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

export function isUsageAvailable(
  usage: UsageResponse | null | undefined,
): usage is UsageResponse {
  return usage?.usage_available === true;
}

export function getUsagePercentage(
  usage: UsageResponse | null | undefined,
): number | null {
  if (!isUsageAvailable(usage) || usage.bandwidth_limit_bytes <= 0) {
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

  const status = getNormalizedEntitlementStatus(entitlement);
  return Boolean(
    status &&
      INACTIVE_ENTITLEMENT_STATUSES.includes(
        status as (typeof INACTIVE_ENTITLEMENT_STATUSES)[number],
      ),
  );
}

export function isGraceEntitlement(
  entitlement: CurrentEntitlementState | null | undefined,
): boolean {
  const status = getNormalizedEntitlementStatus(entitlement);
  return Boolean(status && GRACE_ENTITLEMENT_STATUSES.has(status));
}

export function isTrialEntitlement(
  entitlement: CurrentEntitlementState | null | undefined,
  trial?: TrialStatusResponse | null,
): boolean {
  const status = getNormalizedEntitlementStatus(entitlement);
  return Boolean(
    entitlement?.is_trial === true ||
      trial?.is_trial_active === true ||
      (status && TRIAL_ENTITLEMENT_STATUSES.has(status)),
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

function readExplicitPaymentState(
  entitlement: CurrentEntitlementState | null | undefined,
): Stage1DashboardPaymentState | null {
  const raw =
    readEntitlementString(entitlement, 'stage1_payment_state') ??
    readEntitlementString(entitlement, 'payment_state') ??
    readEntitlementString(entitlement, 'latest_payment_state');
  const normalized = normalizeStateValue(raw);

  return normalized ? PAYMENT_STATE_ALIASES[normalized] ?? null : null;
}

function readExplicitProvisioningState(
  entitlement: CurrentEntitlementState | null | undefined,
): Stage1DashboardProvisioningState | null {
  const raw =
    readEntitlementString(entitlement, 'stage1_provisioning_state') ??
    readEntitlementString(entitlement, 'provisioning_state') ??
    readEntitlementString(entitlement, 'vpn_provisioning_state');
  const normalized = normalizeStateValue(raw);

  return normalized ? PROVISIONING_STATE_ALIASES[normalized] ?? null : null;
}

export function getStage1DashboardAccessState({
  entitlement,
  serviceState,
  trial,
  now = new Date(),
}: {
  entitlement?: CurrentEntitlementState | null;
  serviceState?: CurrentServiceState | null;
  trial?: TrialStatusResponse | null;
  now?: Date;
}): Stage1DashboardAccessState {
  if (entitlement === undefined) {
    return 'checking';
  }

  if (entitlement === null) {
    return 'no_access';
  }

  const status = getNormalizedEntitlementStatus(entitlement);
  if (status && PAYMENT_PENDING_ENTITLEMENT_STATUSES.has(status)) {
    return 'payment_pending';
  }
  if (status && PROVISIONING_PENDING_ENTITLEMENT_STATUSES.has(status)) {
    return 'provisioning_pending';
  }
  if (isGraceEntitlement(entitlement)) {
    return 'grace';
  }
  if (isTrialEntitlement(entitlement, trial)) {
    return 'trial_active';
  }
  if (isInactiveEntitlement(entitlement)) {
    return 'expired';
  }

  const daysUntilExpiry = getDaysUntilExpiry(entitlement, now);
  if (daysUntilExpiry !== null && daysUntilExpiry <= 0) {
    return 'expired';
  }

  if (serviceState !== undefined && serviceState !== null && !isServiceProvisioned(serviceState)) {
    return 'provisioning_pending';
  }

  return 'active';
}

export function getStage1DashboardPaymentState({
  accessState,
  entitlement,
}: {
  accessState: Stage1DashboardAccessState;
  entitlement?: CurrentEntitlementState | null;
}): Stage1DashboardPaymentState {
  const explicitState = readExplicitPaymentState(entitlement);
  if (explicitState) {
    return explicitState;
  }

  if (accessState === 'payment_pending') {
    return 'pending';
  }
  if (accessState === 'checking') {
    return 'checking';
  }
  if (accessState === 'trial_active' || accessState === 'no_access') {
    return 'not_started';
  }
  if (accessState === 'expired') {
    return 'expired';
  }

  return 'paid';
}

export function getStage1DashboardProvisioningState({
  accessState,
  entitlement,
  serviceState,
  serviceStateError = false,
}: {
  accessState: Stage1DashboardAccessState;
  entitlement?: CurrentEntitlementState | null;
  serviceState?: CurrentServiceState | null;
  serviceStateError?: boolean;
}): Stage1DashboardProvisioningState {
  const explicitState = readExplicitProvisioningState(entitlement);
  if (explicitState) {
    return explicitState;
  }

  if (serviceStateError) {
    return 'remnawave_unavailable';
  }
  if (accessState === 'checking') {
    return 'checking';
  }
  if (accessState === 'no_access' || accessState === 'payment_pending') {
    return 'not_required';
  }
  if (serviceState === undefined) {
    return 'pending';
  }

  return isServiceProvisioned(serviceState) ? 'ready' : 'pending';
}

function getAccessStateTone(
  state: Stage1DashboardAccessState,
): CabinetStateTone {
  if (state === 'active' || state === 'trial_active') {
    return 'green';
  }
  if (state === 'checking') {
    return 'cyan';
  }
  if (state === 'grace' || state === 'payment_pending' || state === 'provisioning_pending') {
    return 'amber';
  }

  return 'pink';
}

function getPaymentStateTone(
  state: Stage1DashboardPaymentState,
): CabinetStateTone {
  if (state === 'paid') {
    return 'green';
  }
  if (state === 'checking' || state === 'not_started') {
    return 'cyan';
  }
  if (state === 'pending' || state === 'processing') {
    return 'amber';
  }

  return 'pink';
}

function getProvisioningStateTone(
  state: Stage1DashboardProvisioningState,
): CabinetStateTone {
  if (state === 'ready') {
    return 'green';
  }
  if (state === 'checking' || state === 'not_required') {
    return 'cyan';
  }
  if (state === 'pending' || state === 'retrying') {
    return 'amber';
  }

  return 'pink';
}

function getAccessStateAction(
  state: Stage1DashboardAccessState,
): CabinetActionId | null {
  if (state === 'active' || state === 'trial_active') {
    return 'getConfig';
  }
  if (state === 'checking') {
    return null;
  }
  if (state === 'provisioning_pending') {
    return 'finishProvisioning';
  }

  return 'managePlan';
}

function getPaymentStateAction(
  state: Stage1DashboardPaymentState,
): CabinetActionId | null {
  return state === 'checking' || state === 'paid' ? null : 'managePlan';
}

function getProvisioningStateAction(
  state: Stage1DashboardProvisioningState,
): CabinetActionId | null {
  if (state === 'ready') {
    return 'getConfig';
  }
  if (state === 'checking' || state === 'not_required') {
    return null;
  }

  return 'finishProvisioning';
}

export function getStage1DashboardStates({
  entitlement,
  serviceState,
  serviceStateError,
  trial,
  now,
}: {
  entitlement?: CurrentEntitlementState | null;
  serviceState?: CurrentServiceState | null;
  serviceStateError?: boolean;
  trial?: TrialStatusResponse | null;
  now?: Date;
}): Stage1DashboardStateCard[] {
  const accessState = getStage1DashboardAccessState({
    entitlement,
    serviceState,
    trial,
    now,
  });
  const paymentState = getStage1DashboardPaymentState({
    accessState,
    entitlement,
  });
  const provisioningState = getStage1DashboardProvisioningState({
    accessState,
    entitlement,
    serviceState,
    serviceStateError,
  });

  return [
    {
      actionId: getAccessStateAction(accessState),
      id: 'access',
      state: accessState,
      tone: getAccessStateTone(accessState),
    },
    {
      actionId: getPaymentStateAction(paymentState),
      id: 'payment',
      state: paymentState,
      tone: getPaymentStateTone(paymentState),
    },
    {
      actionId: getProvisioningStateAction(provisioningState),
      id: 'provisioning',
      state: provisioningState,
      tone: getProvisioningStateTone(provisioningState),
    },
  ];
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

  if (isGraceEntitlement(entitlement)) {
    return 'attention';
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
