import type { components } from '@/lib/api/generated/types';

export type ReferralCode = components['schemas']['ReferralCodeResponse'];
export type ReferralCommission = components['schemas']['ReferralCommissionResponse'];
export type ReferralReward = components['schemas']['ReferralRewardResponse'];
export type ReferralStats = components['schemas']['ReferralStatsResponse'];
export type ReferralStatus = components['schemas']['ReferralStatusResponse'];

export type RewardLifecycleStatus =
  | 'available'
  | 'blocked_by_risk'
  | 'expired'
  | 'pending'
  | 'reversed';
export type StatusTone = 'amber' | 'cyan' | 'green' | 'muted' | 'pink' | 'purple';

export type RewardTimelineItem = {
  amount: number;
  availableAt: string | null;
  createdAt: string;
  currency: string;
  holdUntil: string | null;
  id: string;
  referredUserId: string | null;
  source: 'commission' | 'reward';
  status: RewardLifecycleStatus;
};

const STATUS_TONE: Record<RewardLifecycleStatus, StatusTone> = {
  available: 'green',
  blocked_by_risk: 'amber',
  expired: 'muted',
  pending: 'cyan',
  reversed: 'pink',
};

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function timestamp(value: string): number {
  const parsed = new Date(value).getTime();
  return Number.isNaN(parsed) ? 0 : parsed;
}

function normalizeStatus(status: string | null | undefined): RewardLifecycleStatus {
  const normalized = status?.trim().toLowerCase();

  if (
    normalized === 'available' ||
    normalized === 'blocked_by_risk' ||
    normalized === 'expired' ||
    normalized === 'pending' ||
    normalized === 'reversed'
  ) {
    return normalized;
  }

  if (normalized === 'allocated') {
    return 'pending';
  }

  return 'pending';
}

function normalizeCurrency(currency: string | null | undefined): string {
  const candidate = currency?.trim().toUpperCase();
  return candidate && candidate.length >= 3 ? candidate : 'USD';
}

export function formatMoney(locale: string, amount: number, currency = 'USD'): string {
  const safeAmount = isFiniteNumber(amount) ? amount : 0;
  const safeCurrency = normalizeCurrency(currency);

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

export function formatPercent(value: number | null | undefined, locale = 'en-EN'): string {
  const normalized = isFiniteNumber(value) ? value : 0;
  const ratio = normalized > 1 ? normalized / 100 : normalized;

  try {
    const percentValue = ratio * 100;

    return new Intl.NumberFormat(locale, {
      maximumFractionDigits: percentValue % 1 === 0 ? 0 : 1,
      style: 'percent',
    }).format(ratio);
  } catch {
    return `${Math.round(ratio * 100)}%`;
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

export function formatShortId(id: string | null | undefined): string {
  const safeId = id?.trim();
  if (!safeId) {
    return 'n/a';
  }

  return safeId.length <= 10 ? safeId : `${safeId.slice(0, 8)}...`;
}

export function formatLabel(value: string | null | undefined, fallback: string): string {
  const normalized = value?.trim();
  if (!normalized) {
    return fallback;
  }

  return normalized
    .replaceAll('_', ' ')
    .replaceAll('-', ' ')
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

export function getRewardTone(status: string | null | undefined): StatusTone {
  return STATUS_TONE[normalizeStatus(status)];
}

export function getReferralProgramHealth({
  status,
  stats,
}: {
  stats?: ReferralStats | null;
  status?: ReferralStatus | null;
}): 'active' | 'disabled' | 'earning' | 'review' {
  if (status && !status.enabled) {
    return 'disabled';
  }

  if ((stats?.pending_rewards_usd ?? 0) > 0) {
    return 'review';
  }

  if ((stats?.available_rewards_usd ?? 0) > 0 || (stats?.total_referrals ?? 0) > 0) {
    return 'earning';
  }

  return 'active';
}

export function buildReferralLink({
  code,
  fallbackOrigin = 'https://cybervpn.example',
  origin,
}: {
  code: string;
  fallbackOrigin?: string;
  origin?: string;
}): string {
  const safeCode = code.trim();
  const safeOrigin = (origin ?? fallbackOrigin).replace(/\/$/, '');
  return `${safeOrigin}/referral?code=${encodeURIComponent(safeCode)}`;
}

export function buildShareText(template: string, code: string, link: string): string {
  return template.replace('{code}', code).replace('{link}', link);
}

export function mergeRewardTimeline({
  commissions,
  rewards,
}: {
  commissions: ReferralCommission[];
  rewards: ReferralReward[];
}): RewardTimelineItem[] {
  const rewardItems = rewards.map((reward): RewardTimelineItem => ({
    amount: reward.reward_amount,
    availableAt: reward.available_at ?? null,
    createdAt: reward.created_at,
    currency: normalizeCurrency(reward.currency),
    holdUntil: reward.hold_until ?? null,
    id: reward.id,
    referredUserId: reward.referred_user_id ?? null,
    source: 'reward',
    status: normalizeStatus(reward.reward_status),
  }));

  const commissionItems = commissions.map((commission): RewardTimelineItem => ({
    amount: commission.commission_amount,
    availableAt: commission.available_at ?? null,
    createdAt: commission.created_at,
    currency: normalizeCurrency(commission.currency),
    holdUntil: commission.hold_until ?? null,
    id: commission.id,
    referredUserId: commission.referred_user_id,
    source: 'commission',
    status: normalizeStatus(commission.reward_status),
  }));

  return [...rewardItems, ...commissionItems].sort(
    (first, second) => timestamp(second.createdAt) - timestamp(first.createdAt),
  );
}

export function summarizeRewardTimeline(items: RewardTimelineItem[]) {
  return items.reduce(
    (summary, item) => {
      summary[item.status] += 1;
      return summary;
    },
    {
      available: 0,
      blocked_by_risk: 0,
      expired: 0,
      pending: 0,
      reversed: 0,
    } satisfies Record<RewardLifecycleStatus, number>,
  );
}

export function getRewardAmountByStatus(
  items: RewardTimelineItem[],
  status: RewardLifecycleStatus,
): number {
  return items
    .filter((item) => item.status === status)
    .reduce((total, item) => total + item.amount, 0);
}

export function getCapProgress(used: number | null | undefined, softCap: number): number {
  if (!isFiniteNumber(used) || used <= 0 || softCap <= 0) {
    return 0;
  }

  return Math.min(100, Math.round((used / softCap) * 100));
}
