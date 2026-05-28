'use client';

import { useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock3,
  Copy,
  ExternalLink,
  Gift,
  History,
  Link2,
  Loader2,
  LockKeyhole,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Ticket,
  TrendingUp,
  Users,
  WalletCards,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { useMemo, useState, type ReactNode } from 'react';
import type { GiftCodeRecord } from '@/features/customer-growth/hooks/useCustomerGrowth';
import {
  areCheckoutCodeDiscountsEnabled,
  areGiftCodesEnabled,
  areInviteCodesEnabled,
  arePromoCodesEnabled,
  isAnyGrowthSurfaceEnabled,
  isClientCapabilitiesReady,
  isReferralProgramEnabled,
  useClientCapabilities,
} from '@/features/client-capabilities/useClientCapabilities';
import type { ClientCapabilitiesResponse } from '@/lib/api/client-capabilities';
import {
  getGrowthRedeemErrorMessage,
  useGiftCatalogPlans,
  useGiftCodes,
  useGiftPurchase,
  useInviteCodes,
  useRedeemGrowthCode,
} from '@/features/customer-growth/hooks/useCustomerGrowth';
import { Link } from '@/i18n/navigation';
import { growthNotificationsApi, referralApi } from '@/lib/api';
import { markPerformance } from '@/shared/lib/web-vitals';
import {
  buildReferralLink,
  buildShareText,
  formatDate,
  formatLabel,
  formatMoney,
  formatPercent,
  formatShortId,
  getCapProgress,
  getReferralProgramHealth,
  getRewardAmountByStatus,
  getRewardTone,
  mergeRewardTimeline,
  summarizeRewardTimeline,
  type RewardLifecycleStatus,
  type StatusTone,
} from './referral-cabinet-model';

const LIVE_STALE_MS = 30_000;
const LIVE_REFETCH_MS = 45_000;
const CATALOG_STALE_MS = 5 * 60_000;
const MONTHLY_SOFT_CAP_USD = 100;
const LIFETIME_SOFT_CAP_USD = 1_000;

type InviteCode = {
  code: string;
  created_at: string;
  expires_at: string | null;
  free_days: number;
  id: string;
  is_used: boolean;
};

const toneClasses: Record<
  StatusTone,
  { border: string; fill: string; text: string }
> = {
  amber: {
    border: 'border-amber-400/30',
    fill: 'bg-amber-400/10',
    text: 'text-amber-300',
  },
  cyan: {
    border: 'border-neon-cyan/30',
    fill: 'bg-neon-cyan/10',
    text: 'text-neon-cyan',
  },
  green: {
    border: 'border-matrix-green/30',
    fill: 'bg-matrix-green/10',
    text: 'text-matrix-green',
  },
  muted: {
    border: 'border-grid-line/30',
    fill: 'bg-terminal-bg/40',
    text: 'text-muted-foreground',
  },
  pink: {
    border: 'border-neon-pink/30',
    fill: 'bg-neon-pink/10',
    text: 'text-neon-pink',
  },
  purple: {
    border: 'border-neon-purple/30',
    fill: 'bg-neon-purple/10',
    text: 'text-neon-purple',
  },
};

function visiblePolling(intervalMs: number) {
  return (query: { state: { error: unknown } }) => {
    if (query.state.error) {
      return false;
    }

    if (
      typeof document !== 'undefined' &&
      document.visibilityState === 'hidden'
    ) {
      return false;
    }

    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      return false;
    }

    return intervalMs;
  };
}

function StatusPill({
  children,
  tone,
}: {
  children: ReactNode;
  tone: StatusTone;
}) {
  const classes = toneClasses[tone];

  return (
    <span
      className={`inline-flex min-h-8 items-center rounded-full border px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] ${classes.border} ${classes.fill} ${classes.text}`}
    >
      {children}
    </span>
  );
}

function LoadingBlock({ className = 'min-h-24' }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`${className} animate-pulse rounded-3xl border border-grid-line/30 bg-terminal-surface/40`}
    />
  );
}

function ReferralPausedState() {
  return (
    <div className="mx-auto w-full max-w-3xl">
      <div className="cyber-card p-6">
        <div className="flex items-start gap-4">
          <div className="rounded-lg border border-neon-cyan/30 bg-neon-cyan/10 p-3">
            <LockKeyhole
              className="h-5 w-5 text-neon-cyan"
              aria-hidden="true"
            />
          </div>
          <div>
            <p className="text-xs font-mono uppercase tracking-[0.2em] text-neon-cyan">
              Growth controls
            </p>
            <h1 className="mt-2 text-xl font-display text-white">
              Rewards hub is paused
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Referral, gift, promo-code, and invite surfaces are currently
              disabled by runtime policy.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function ReferralCapabilitiesLoadingState() {
  return (
    <div className="mx-auto w-full max-w-3xl">
      <div className="cyber-card p-6">
        <div className="flex items-start gap-4">
          <div className="rounded-lg border border-neon-cyan/30 bg-neon-cyan/10 p-3">
            <Loader2
              className="h-5 w-5 animate-spin text-neon-cyan"
              aria-hidden="true"
            />
          </div>
          <div>
            <p className="text-xs font-mono uppercase tracking-[0.2em] text-neon-cyan">
              Growth controls
            </p>
            <h1 className="mt-2 text-xl font-display text-white">
              Checking rewards availability
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              CyberVPN is loading the current referral, gift, promo, and invite
              policy before opening growth actions.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function getGrowthVisibility(
  capabilities: ClientCapabilitiesResponse | undefined,
) {
  return {
    checkoutCodes: areCheckoutCodeDiscountsEnabled(capabilities),
    giftCodes: areGiftCodesEnabled(capabilities),
    invites: areInviteCodesEnabled(capabilities),
    promoCodes: arePromoCodesEnabled(capabilities),
    referral: isReferralProgramEnabled(capabilities),
    surface: isAnyGrowthSurfaceEnabled(capabilities),
  };
}

function MetricCard({
  icon,
  label,
  tone = 'cyan',
  value,
}: {
  icon: ReactNode;
  label: string;
  tone?: StatusTone;
  value: string;
}) {
  return (
    <article className="rounded-2xl border border-grid-line/30 bg-terminal-surface/45 p-5">
      <div className={toneClasses[tone].text}>{icon}</div>
      <p className="mt-4 font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 truncate text-2xl font-display text-white">{value}</p>
    </article>
  );
}

function getHealthTone(
  health: 'active' | 'disabled' | 'earning' | 'review',
): StatusTone {
  if (health === 'disabled') {
    return 'pink';
  }

  if (health === 'review') {
    return 'amber';
  }

  if (health === 'earning') {
    return 'green';
  }

  return 'cyan';
}

function getLifecycleIcon(status: RewardLifecycleStatus) {
  if (status === 'available') {
    return <CheckCircle2 className="h-5 w-5" aria-hidden="true" />;
  }

  if (status === 'blocked_by_risk') {
    return <LockKeyhole className="h-5 w-5" aria-hidden="true" />;
  }

  if (status === 'reversed') {
    return <AlertTriangle className="h-5 w-5" aria-hidden="true" />;
  }

  return <Clock3 className="h-5 w-5" aria-hidden="true" />;
}

function isInviteExpired(expiresAt?: string | null): boolean {
  return Boolean(expiresAt && new Date(expiresAt).getTime() <= Date.now());
}

function getGiftStatus(
  status: string,
): 'active' | 'expired' | 'redeemed' | 'revoked' {
  if (status === 'redeemed') {
    return 'redeemed';
  }

  if (status === 'expired') {
    return 'expired';
  }

  if (status === 'revoked') {
    return 'revoked';
  }

  return 'active';
}

export function ReferralCabinetDashboard() {
  const t = useTranslations('Referral.cabinet');
  const growthT = useTranslations('Referral');
  const locale = useLocale();
  const [copyState, setCopyState] = useState<
    'code' | 'idle' | 'link' | 'share'
  >('idle');
  const [copiedGrowthCode, setCopiedGrowthCode] = useState<string | null>(null);
  const [redeemCode, setRedeemCode] = useState('');
  const [redeemError, setRedeemError] = useState('');
  const [redeemSuccess, setRedeemSuccess] = useState('');
  const [giftPlanId, setGiftPlanId] = useState('');
  const [giftRecipientHint, setGiftRecipientHint] = useState('');
  const [giftMessage, setGiftMessage] = useState('');
  const [giftPurchaseError, setGiftPurchaseError] = useState('');
  const [giftPurchaseSuccess, setGiftPurchaseSuccess] = useState('');
  const capabilitiesQuery = useClientCapabilities();
  const capabilitiesReady = isClientCapabilitiesReady(capabilitiesQuery);
  const capabilities = capabilitiesReady ? capabilitiesQuery.data : undefined;
  const growthVisibility = getGrowthVisibility(capabilities);

  const statusQuery = useQuery({
    queryKey: ['growth', 'referral', 'status'],
    enabled: growthVisibility.referral,
    queryFn: async () => {
      const response = await referralApi.getStatus();
      return response.data;
    },
    refetchOnWindowFocus: false,
    staleTime: CATALOG_STALE_MS,
  });

  const codeQuery = useQuery({
    queryKey: ['growth', 'referral', 'code'],
    enabled: growthVisibility.referral,
    queryFn: async () => {
      const response = await referralApi.getCode();
      return response.data;
    },
    refetchOnWindowFocus: false,
    staleTime: CATALOG_STALE_MS,
  });

  const statsQuery = useQuery({
    queryKey: ['growth', 'referral', 'stats'],
    enabled: growthVisibility.referral,
    queryFn: async () => {
      const response = await referralApi.getStats();
      return response.data;
    },
    refetchInterval: visiblePolling(LIVE_REFETCH_MS),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    staleTime: LIVE_STALE_MS,
  });

  const rewardsQuery = useQuery({
    queryKey: ['growth', 'referral', 'rewards'],
    enabled: growthVisibility.referral,
    queryFn: async () => {
      const response = await referralApi.getRewards();
      return response.data;
    },
    refetchInterval: visiblePolling(LIVE_REFETCH_MS),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    staleTime: LIVE_STALE_MS,
  });

  const commissionsQuery = useQuery({
    queryKey: ['growth', 'referral', 'commissions'],
    enabled: growthVisibility.referral,
    queryFn: async () => {
      const response = await referralApi.getRecentCommissions();
      return response.data;
    },
    refetchInterval: visiblePolling(LIVE_REFETCH_MS),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    staleTime: LIVE_STALE_MS,
  });

  const notificationsQuery = useQuery({
    queryKey: ['growth', 'notifications', 'referral-cabinet'],
    enabled: growthVisibility.surface,
    queryFn: async () => {
      const response = await growthNotificationsApi.list(false);
      return response.data;
    },
    refetchInterval: visiblePolling(LIVE_REFETCH_MS),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    staleTime: LIVE_STALE_MS,
  });

  const notificationCountersQuery = useQuery({
    queryKey: ['growth', 'notifications', 'counters'],
    enabled: growthVisibility.surface,
    queryFn: async () => {
      const response = await growthNotificationsApi.getCounters();
      return response.data;
    },
    refetchInterval: visiblePolling(LIVE_REFETCH_MS),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    staleTime: LIVE_STALE_MS,
  });

  const inviteCodesQuery = useInviteCodes();
  const giftCodesQuery = useGiftCodes();
  const giftCatalogPlansQuery = useGiftCatalogPlans();
  const redeemGrowthCode = useRedeemGrowthCode();
  const giftPurchase = useGiftPurchase();

  const status = statusQuery.data ?? null;
  const stats = statsQuery.data ?? null;
  const referralCode = codeQuery.data?.referral_code ?? '';
  const rewardTimeline = mergeRewardTimeline({
    commissions: commissionsQuery.data ?? [],
    rewards: rewardsQuery.data ?? [],
  });
  const rewardSummary = summarizeRewardTimeline(rewardTimeline);
  const health = getReferralProgramHealth({ stats, status });
  const healthTone = getHealthTone(health);
  const notifications = (notificationsQuery.data ?? []).slice(0, 4);
  const inviteCodes = useMemo(
    () => (inviteCodesQuery.data ?? []) as InviteCode[],
    [inviteCodesQuery.data],
  );
  const giftCodes = useMemo(
    () => (giftCodesQuery.data ?? []) as GiftCodeRecord[],
    [giftCodesQuery.data],
  );
  const giftCatalogPlans = useMemo(
    () => giftCatalogPlansQuery.data ?? [],
    [giftCatalogPlansQuery.data],
  );
  const activeInviteCount = inviteCodes.filter(
    (invite) => !invite.is_used && !isInviteExpired(invite.expires_at),
  ).length;
  const referralLink = growthVisibility.referral
    ? buildReferralLink({
        code: referralCode,
        origin:
          typeof window !== 'undefined' ? window.location.origin : undefined,
      })
    : '';
  const shareText = buildShareText(
    t('share.message'),
    referralCode,
    referralLink,
  );
  const currency =
    rewardsQuery.data?.[0]?.currency ??
    commissionsQuery.data?.[0]?.currency ??
    'USD';
  const hasAnyError =
    (growthVisibility.referral &&
      (statusQuery.isError ||
        codeQuery.isError ||
        statsQuery.isError ||
        rewardsQuery.isError ||
        commissionsQuery.isError)) ||
    (growthVisibility.surface &&
      (notificationsQuery.isError || notificationCountersQuery.isError));

  const copyValue = async (value: string, kind: 'code' | 'link' | 'share') => {
    if (!value || typeof navigator === 'undefined' || !navigator.clipboard) {
      setCopyState('idle');
      return;
    }

    try {
      await navigator.clipboard.writeText(value);
      markPerformance('referral-share-copy', { kind });
      setCopyState(kind);
      window.setTimeout(() => setCopyState('idle'), 1600);
    } catch {
      setCopyState('idle');
    }
  };

  const refetchAll = () =>
    Promise.all([
      ...(growthVisibility.referral
        ? [
            statusQuery.refetch(),
            codeQuery.refetch(),
            statsQuery.refetch(),
            rewardsQuery.refetch(),
            commissionsQuery.refetch(),
          ]
        : []),
      ...(growthVisibility.surface
        ? [notificationsQuery.refetch(), notificationCountersQuery.refetch()]
        : []),
      ...(growthVisibility.invites ? [inviteCodesQuery.refetch()] : []),
      ...(growthVisibility.giftCodes
        ? [giftCodesQuery.refetch(), giftCatalogPlansQuery.refetch()]
        : []),
    ]);

  const copyGrowthCode = async (value: string | null | undefined) => {
    if (!value || typeof navigator === 'undefined' || !navigator.clipboard) {
      setCopiedGrowthCode(null);
      return;
    }

    try {
      await navigator.clipboard.writeText(value);
      setCopiedGrowthCode(value);
      window.setTimeout(() => setCopiedGrowthCode(null), 1600);
    } catch {
      setCopiedGrowthCode(null);
    }
  };

  const handleRedeemCode = async () => {
    const normalizedCode = redeemCode.trim().toUpperCase();
    if (!normalizedCode) {
      setRedeemError(growthT('redeemErrors.empty'));
      return;
    }

    setRedeemError('');
    setRedeemSuccess('');

    try {
      const redeemed = await redeemGrowthCode.mutateAsync(normalizedCode);
      setRedeemCode('');
      await refetchAll();

      if (redeemed.codeType === 'invite') {
        setRedeemSuccess(
          growthT('redeemSuccessInvite', {
            days: redeemed.inviteCode.free_days,
          }),
        );
        return;
      }

      setRedeemSuccess(
        growthT('redeemSuccessGift', {
          plan: redeemed.giftRedemption.gift_code.plan_family ?? 'gift plan',
          days: redeemed.giftRedemption.gift_code.duration_days ?? 0,
        }),
      );
    } catch (error) {
      setRedeemError(getGrowthRedeemErrorMessage(error));
    }
  };

  const handleGiftPurchase = async () => {
    if (!growthVisibility.giftCodes) {
      setGiftPurchaseError(growthT('giftPurchase.errors.default'));
      return;
    }

    if (!giftPlanId) {
      setGiftPurchaseError(growthT('giftPurchase.errors.planRequired'));
      return;
    }

    setGiftPurchaseError('');
    setGiftPurchaseSuccess('');

    try {
      const result = await giftPurchase.mutateAsync({
        channel: 'web',
        gift_message: giftMessage.trim() || null,
        plan_id: giftPlanId,
        recipient_hint: giftRecipientHint.trim() || null,
      });

      if (result.invoice?.payment_url) {
        window.open(
          result.invoice.payment_url,
          '_blank',
          'noopener,noreferrer',
        );
        setGiftPurchaseSuccess(growthT('giftPurchase.successPaymentPending'));
      } else if (result.gift_code?.raw_code || result.gift_code?.masked_code) {
        setGiftPurchaseSuccess(
          growthT('giftPurchase.successIssued', {
            code: result.gift_code.raw_code ?? result.gift_code.masked_code,
          }),
        );
      } else {
        setGiftPurchaseSuccess(growthT('giftPurchase.successQueued'));
      }

      setGiftRecipientHint('');
      setGiftMessage('');
      await refetchAll();
    } catch {
      setGiftPurchaseError(growthT('giftPurchase.errors.default'));
    }
  };

  if (!capabilitiesReady) {
    return <ReferralCapabilitiesLoadingState />;
  }

  if (!growthVisibility.surface) {
    return <ReferralPausedState />;
  }

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-[2rem] border border-neon-purple/25 bg-terminal-surface/55 p-6 shadow-[0_0_70px_rgba(157,0,255,0.08)] backdrop-blur md:p-8">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(157,0,255,0.18),transparent_34%),radial-gradient(circle_at_bottom_right,rgba(0,255,136,0.12),transparent_30%)]" />
        <div className="relative grid gap-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-end">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.34em] text-neon-purple">
              {t('hero.eyebrow')}
            </p>
            <h1 className="mt-4 max-w-3xl text-4xl font-display tracking-[0.08em] text-white md:text-5xl">
              {t('title')}
            </h1>
            <p className="mt-4 max-w-2xl font-mono text-sm leading-7 text-muted-foreground">
              {t('subtitle')}
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/wallet"
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-matrix-green/35 bg-matrix-green/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-matrix-green transition hover:bg-matrix-green/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
              >
                {t('hero.wallet')}
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <Link
                href="/payment-history"
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-neon-cyan/40 bg-neon-cyan/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-neon-cyan transition hover:bg-neon-cyan/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
              >
                {t('hero.payments')}
              </Link>
            </div>
          </div>

          <div className="rounded-3xl border border-grid-line/30 bg-black/25 p-5">
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
              {t('hero.health')}
            </p>
            <div className="mt-4 flex items-center gap-3">
              <Sparkles
                className={`h-6 w-6 ${toneClasses[healthTone].text}`}
                aria-hidden="true"
              />
              <StatusPill tone={healthTone}>{t(`health.${health}`)}</StatusPill>
            </div>
            <p className="mt-4 font-mono text-sm leading-7 text-muted-foreground">
              {status?.enabled === false
                ? t('hero.disabledHint')
                : t('hero.enabledHint', {
                    rate: formatPercent(
                      status?.commission_rate ?? stats?.commission_rate ?? 0,
                      locale,
                    ),
                  })}
            </p>
          </div>
        </div>
      </section>

      {hasAnyError && (
        <section
          className="rounded-2xl border border-amber-400/30 bg-amber-400/10 p-4 font-mono text-sm text-amber-200"
          role="status"
        >
          <div className="flex items-start gap-3">
            <AlertTriangle
              className="mt-0.5 h-5 w-5 shrink-0"
              aria-hidden="true"
            />
            <div>
              <p className="font-semibold">{t('errors.partialTitle')}</p>
              <p className="mt-1 text-amber-100/80">
                {t('errors.partialDescription')}
              </p>
            </div>
          </div>
        </section>
      )}

      {growthVisibility.referral && (
        <>
          <section
            className="grid gap-4 md:grid-cols-4"
            aria-label={t('summary.ariaLabel')}
          >
            <MetricCard
              icon={<Users className="h-5 w-5" aria-hidden="true" />}
              label={t('summary.referrals')}
              tone="cyan"
              value={
                statsQuery.isPending
                  ? '...'
                  : String(stats?.total_referrals ?? 0)
              }
            />
            <MetricCard
              icon={<WalletCards className="h-5 w-5" aria-hidden="true" />}
              label={t('summary.available')}
              tone="green"
              value={formatMoney(
                locale,
                stats?.available_rewards_usd ?? 0,
                'USD',
              )}
            />
            <MetricCard
              icon={<Clock3 className="h-5 w-5" aria-hidden="true" />}
              label={t('summary.pending')}
              tone={rewardSummary.pending ? 'amber' : 'muted'}
              value={formatMoney(
                locale,
                stats?.pending_rewards_usd ?? 0,
                'USD',
              )}
            />
            <MetricCard
              icon={<TrendingUp className="h-5 w-5" aria-hidden="true" />}
              label={t('summary.qualifyingOrders')}
              tone="purple"
              value={String(stats?.qualifying_orders ?? 0)}
            />
          </section>

          <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
            <article className="rounded-[2rem] border border-neon-cyan/25 bg-terminal-surface/55 p-6 shadow-[0_0_42px_rgba(0,255,255,0.07)] backdrop-blur">
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-cyan">
                    {t('share.eyebrow')}
                  </p>
                  <h2 className="mt-3 text-2xl font-display text-white">
                    {t('share.title')}
                  </h2>
                  <p className="mt-3 max-w-2xl font-mono text-sm leading-7 text-muted-foreground">
                    {t('share.description')}
                  </p>
                </div>
                <StatusPill tone={status?.enabled === false ? 'pink' : 'green'}>
                  {status?.enabled === false
                    ? t('share.paused')
                    : t('share.active')}
                </StatusPill>
              </div>

              <div className="mt-6 rounded-3xl border border-grid-line/30 bg-black/20 p-5">
                <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                  {t('share.codeLabel')}
                </p>
                {codeQuery.isPending ? (
                  <div className="mt-4 h-12 w-56 animate-pulse rounded bg-grid-line/20" />
                ) : (
                  <p className="mt-4 break-all font-mono text-4xl tracking-[0.24em] text-neon-cyan">
                    {referralCode || t('labels.notAvailable')}
                  </p>
                )}
                <p className="mt-4 break-all font-mono text-xs leading-6 text-muted-foreground">
                  {referralLink}
                </p>
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-3">
                <button
                  type="button"
                  onClick={() => void copyValue(referralCode, 'code')}
                  disabled={!referralCode}
                  className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-neon-cyan/40 bg-neon-cyan/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.14em] text-neon-cyan transition hover:bg-neon-cyan/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Copy className="h-4 w-4" aria-hidden="true" />
                  {copyState === 'code'
                    ? t('share.copied')
                    : t('share.copyCode')}
                </button>
                <button
                  type="button"
                  onClick={() => void copyValue(referralLink, 'link')}
                  disabled={!referralCode}
                  className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-neon-purple/40 bg-neon-purple/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.14em] text-neon-purple transition hover:bg-neon-purple/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Link2 className="h-4 w-4" aria-hidden="true" />
                  {copyState === 'link'
                    ? t('share.copied')
                    : t('share.copyLink')}
                </button>
                <button
                  type="button"
                  onClick={() => void copyValue(shareText, 'share')}
                  disabled={!referralCode}
                  className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-matrix-green/40 bg-matrix-green/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.14em] text-matrix-green transition hover:bg-matrix-green/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Gift className="h-4 w-4" aria-hidden="true" />
                  {copyState === 'share'
                    ? t('share.copied')
                    : t('share.copyShareText')}
                </button>
              </div>
            </article>

            <article className="rounded-[2rem] border border-grid-line/30 bg-terminal-surface/55 p-6 backdrop-blur">
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="font-mono text-xs uppercase tracking-[0.28em] text-matrix-green">
                    {t('rules.eyebrow')}
                  </p>
                  <h2 className="mt-3 text-2xl font-display text-white">
                    {t('rules.title')}
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={() => void refetchAll()}
                  className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-grid-line/40 bg-terminal-bg/60 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground transition hover:border-neon-cyan/40 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
                >
                  <RefreshCw className="h-4 w-4" aria-hidden="true" />
                  {t('actions.refresh')}
                </button>
              </div>

              <div className="mt-6 space-y-3">
                {(
                  [
                    'backendTruth',
                    'nonWithdrawable',
                    'partnerHidden',
                    'holdWindow',
                  ] as const
                ).map((item) => (
                  <div
                    key={item}
                    className="rounded-2xl border border-grid-line/30 bg-black/20 p-4"
                  >
                    <div className="flex items-start gap-3">
                      <ShieldCheck
                        className="mt-0.5 h-5 w-5 shrink-0 text-matrix-green"
                        aria-hidden="true"
                      />
                      <div>
                        <p className="font-mono text-sm text-white">
                          {t(`rules.items.${item}.title`)}
                        </p>
                        <p className="mt-1 font-mono text-xs leading-6 text-muted-foreground">
                          {item === 'holdWindow'
                            ? t(`rules.items.${item}.description`, {
                                days: status?.reward_hold_days ?? 0,
                              })
                            : t(`rules.items.${item}.description`)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </article>
          </section>
        </>
      )}

      {(growthVisibility.invites || growthVisibility.giftCodes) && (
        <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
          {(growthVisibility.invites || growthVisibility.giftCodes) && (
            <article className="rounded-[2rem] border border-neon-purple/25 bg-terminal-surface/55 p-6 backdrop-blur">
              <div className="flex items-start gap-4">
                <div className="rounded-2xl border border-neon-purple/30 bg-neon-purple/10 p-3">
                  <Ticket
                    className="h-6 w-6 text-neon-purple"
                    aria-hidden="true"
                  />
                </div>
                <div>
                  <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-purple">
                    {growthT('redeemTitle')}
                  </p>
                  <h2 className="mt-2 text-2xl font-display text-white">
                    {growthT('promoNoteTitle')}
                  </h2>
                  <p className="mt-3 max-w-2xl font-mono text-sm leading-7 text-muted-foreground">
                    {growthT('redeemSubtitle')}
                  </p>
                </div>
              </div>

              <div className="mt-6 space-y-4">
                <label className="block">
                  <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                    {growthT('redeemInputLabel')}
                  </span>
                  <input
                    value={redeemCode}
                    onChange={(event) =>
                      setRedeemCode(event.target.value.toUpperCase())
                    }
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        void handleRedeemCode();
                      }
                    }}
                    placeholder={growthT('redeemPlaceholder')}
                    disabled={redeemGrowthCode.isPending}
                    className="mt-2 w-full rounded-2xl border border-grid-line/30 bg-black/20 px-4 py-3 font-mono text-sm uppercase tracking-[0.12em] text-white outline-none transition focus:border-neon-cyan/50 focus:ring-2 focus:ring-neon-cyan/20 disabled:cursor-not-allowed disabled:opacity-60"
                  />
                </label>

                {redeemError && (
                  <p className="rounded-2xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 font-mono text-sm text-amber-200">
                    {redeemError}
                  </p>
                )}
                {redeemSuccess && (
                  <p className="rounded-2xl border border-matrix-green/30 bg-matrix-green/10 px-4 py-3 font-mono text-sm text-matrix-green">
                    {redeemSuccess}
                  </p>
                )}

                <button
                  type="button"
                  onClick={() => void handleRedeemCode()}
                  disabled={redeemGrowthCode.isPending || !redeemCode.trim()}
                  className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-neon-purple/40 bg-neon-purple/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-neon-purple transition hover:bg-neon-purple/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {redeemGrowthCode.isPending ? (
                    <>
                      <Loader2
                        className="h-4 w-4 animate-spin"
                        aria-hidden="true"
                      />
                      {growthT('redeeming')}
                    </>
                  ) : (
                    growthT('redeemButton')
                  )}
                </button>

                <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
                  <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    {growthT('promoNoteTitle')}
                  </p>
                  <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">
                    {growthT('promoNoteBody')}
                  </p>
                </div>
              </div>
            </article>
          )}

          {growthVisibility.giftCodes && (
            <article className="rounded-[2rem] border border-neon-cyan/25 bg-terminal-surface/55 p-6 backdrop-blur">
              <div className="flex items-start gap-4">
                <div className="rounded-2xl border border-neon-cyan/30 bg-neon-cyan/10 p-3">
                  <Gift className="h-6 w-6 text-neon-cyan" aria-hidden="true" />
                </div>
                <div>
                  <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-cyan">
                    {growthT('giftPurchase.title')}
                  </p>
                  <h2 className="mt-2 text-2xl font-display text-white">
                    {growthT('giftPurchase.action')}
                  </h2>
                  <p className="mt-3 max-w-2xl font-mono text-sm leading-7 text-muted-foreground">
                    {growthT('giftPurchase.subtitle')}
                  </p>
                </div>
              </div>

              <div className="mt-6 grid gap-4">
                <label className="block">
                  <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                    {growthT('giftPurchase.planLabel')}
                  </span>
                  <select
                    value={giftPlanId}
                    onChange={(event) => setGiftPlanId(event.target.value)}
                    disabled={
                      giftCatalogPlansQuery.isLoading || giftPurchase.isPending
                    }
                    className="mt-2 w-full rounded-2xl border border-grid-line/30 bg-black/20 px-4 py-3 font-mono text-sm text-white outline-none transition focus:border-neon-cyan/50 focus:ring-2 focus:ring-neon-cyan/20 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <option value="">
                      {growthT('giftPurchase.planPlaceholder')}
                    </option>
                    {giftCatalogPlans.map((plan) => (
                      <option key={plan.uuid} value={plan.uuid}>
                        {`${plan.display_name} · ${plan.duration_days}d · ${formatMoney(locale, plan.price_usd, 'USD')}`}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block">
                  <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                    {growthT('giftPurchase.recipientHintLabel')}
                  </span>
                  <input
                    value={giftRecipientHint}
                    onChange={(event) =>
                      setGiftRecipientHint(event.target.value)
                    }
                    placeholder={growthT(
                      'giftPurchase.recipientHintPlaceholder',
                    )}
                    disabled={giftPurchase.isPending}
                    className="mt-2 w-full rounded-2xl border border-grid-line/30 bg-black/20 px-4 py-3 font-mono text-sm text-white outline-none transition focus:border-neon-cyan/50 focus:ring-2 focus:ring-neon-cyan/20 disabled:cursor-not-allowed disabled:opacity-60"
                  />
                </label>

                <label className="block">
                  <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                    {growthT('giftPurchase.messageLabel')}
                  </span>
                  <textarea
                    rows={3}
                    value={giftMessage}
                    onChange={(event) => setGiftMessage(event.target.value)}
                    placeholder={growthT('giftPurchase.messagePlaceholder')}
                    disabled={giftPurchase.isPending}
                    className="mt-2 w-full rounded-2xl border border-grid-line/30 bg-black/20 px-4 py-3 font-mono text-sm text-white outline-none transition focus:border-neon-cyan/50 focus:ring-2 focus:ring-neon-cyan/20 disabled:cursor-not-allowed disabled:opacity-60"
                  />
                </label>

                {giftPurchaseError && (
                  <p className="rounded-2xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 font-mono text-sm text-amber-200">
                    {giftPurchaseError}
                  </p>
                )}
                {giftPurchaseSuccess && (
                  <p className="rounded-2xl border border-matrix-green/30 bg-matrix-green/10 px-4 py-3 font-mono text-sm text-matrix-green">
                    {giftPurchaseSuccess}
                  </p>
                )}

                <button
                  type="button"
                  onClick={() => void handleGiftPurchase()}
                  disabled={giftPurchase.isPending}
                  className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-neon-cyan/40 bg-neon-cyan/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-neon-cyan transition hover:bg-neon-cyan/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {giftPurchase.isPending ? (
                    <>
                      <Loader2
                        className="h-4 w-4 animate-spin"
                        aria-hidden="true"
                      />
                      {growthT('giftPurchase.processing')}
                    </>
                  ) : (
                    <>
                      <ExternalLink className="h-4 w-4" aria-hidden="true" />
                      {growthT('giftPurchase.action')}
                    </>
                  )}
                </button>
              </div>
            </article>
          )}
        </section>
      )}

      {(growthVisibility.invites || growthVisibility.giftCodes) && (
        <section className="grid gap-6 xl:grid-cols-2">
          {growthVisibility.invites && (
            <article className="rounded-[2rem] border border-neon-cyan/25 bg-terminal-surface/55 p-6 backdrop-blur">
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-cyan">
                    {growthT('invitesTitle')}
                  </p>
                  <h2 className="mt-3 text-2xl font-display text-white">
                    {growthT('overview.activeInvites')}
                  </h2>
                  <p className="mt-3 font-mono text-sm leading-7 text-muted-foreground">
                    {growthT('invitesSubtitle')}
                  </p>
                </div>
                <StatusPill tone={activeInviteCount > 0 ? 'green' : 'muted'}>
                  {activeInviteCount}
                </StatusPill>
              </div>

              {inviteCodesQuery.isLoading ? (
                <div className="mt-6 space-y-3">
                  {[0, 1, 2].map((item) => (
                    <LoadingBlock key={item} className="min-h-20" />
                  ))}
                </div>
              ) : inviteCodes.length === 0 ? (
                <p className="mt-6 rounded-2xl border border-grid-line/30 bg-black/20 p-5 font-mono text-sm text-muted-foreground">
                  {growthT('noInvites')}
                </p>
              ) : (
                <div className="mt-6 space-y-3">
                  {inviteCodes.map((invite) => {
                    const expired = isInviteExpired(invite.expires_at);
                    const status = invite.is_used
                      ? 'used'
                      : expired
                        ? 'expired'
                        : 'active';
                    const tone: StatusTone =
                      status === 'active'
                        ? 'green'
                        : status === 'used'
                          ? 'purple'
                          : 'amber';

                    return (
                      <div
                        key={invite.id}
                        className="rounded-2xl border border-grid-line/30 bg-black/20 p-4"
                      >
                        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                          <div>
                            <div className="flex flex-wrap items-center gap-3">
                              <code className="font-mono text-lg tracking-[0.18em] text-neon-cyan">
                                {invite.code}
                              </code>
                              <StatusPill tone={tone}>
                                {growthT(`inviteStatus.${status}`)}
                              </StatusPill>
                            </div>
                            <div className="mt-3 flex flex-wrap gap-4 font-mono text-xs text-muted-foreground">
                              <span>
                                {growthT('inviteDays', {
                                  days: invite.free_days,
                                })}
                              </span>
                              <span>
                                {growthT('inviteExpires', {
                                  date:
                                    formatDate(invite.expires_at, locale) ??
                                    t('labels.notAvailable'),
                                })}
                              </span>
                              <span>
                                {growthT('inviteCreated', {
                                  date:
                                    formatDate(invite.created_at, locale) ??
                                    t('labels.notAvailable'),
                                })}
                              </span>
                            </div>
                          </div>

                          <button
                            type="button"
                            onClick={() => void copyGrowthCode(invite.code)}
                            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-neon-cyan/40 bg-neon-cyan/10 px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-neon-cyan transition hover:bg-neon-cyan/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
                          >
                            <Copy className="h-4 w-4" aria-hidden="true" />
                            {copiedGrowthCode === invite.code
                              ? growthT('copied')
                              : growthT('copyCode')}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </article>
          )}

          {growthVisibility.giftCodes && (
            <article className="rounded-[2rem] border border-neon-pink/25 bg-terminal-surface/55 p-6 backdrop-blur">
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-pink">
                  {growthT('giftsTitle')}
                </p>
                <h2 className="mt-3 text-2xl font-display text-white">
                  {growthT('giftPurchase.title')}
                </h2>
                <p className="mt-3 font-mono text-sm leading-7 text-muted-foreground">
                  {growthT('giftsSubtitle')}
                </p>
              </div>

              {giftCodesQuery.isLoading ? (
                <div className="mt-6 space-y-3">
                  {[0, 1, 2].map((item) => (
                    <LoadingBlock key={item} className="min-h-20" />
                  ))}
                </div>
              ) : giftCodes.length === 0 ? (
                <p className="mt-6 rounded-2xl border border-grid-line/30 bg-black/20 p-5 font-mono text-sm text-muted-foreground">
                  {growthT('noGifts')}
                </p>
              ) : (
                <div className="mt-6 space-y-3">
                  {giftCodes.map((gift) => {
                    const visibleCode = gift.raw_code ?? gift.masked_code;
                    const status = getGiftStatus(gift.status);
                    const tone: StatusTone =
                      status === 'active'
                        ? 'cyan'
                        : status === 'redeemed'
                          ? 'green'
                          : status === 'revoked'
                            ? 'purple'
                            : 'amber';

                    return (
                      <div
                        key={gift.id}
                        className="rounded-2xl border border-grid-line/30 bg-black/20 p-4"
                      >
                        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                          <div>
                            <div className="flex flex-wrap items-center gap-3">
                              <code className="font-mono text-lg tracking-[0.12em] text-neon-pink">
                                {visibleCode}
                              </code>
                              <StatusPill tone={tone}>
                                {growthT(`giftStatus.${status}`)}
                              </StatusPill>
                            </div>
                            <div className="mt-3 flex flex-wrap gap-4 font-mono text-xs text-muted-foreground">
                              <span>
                                {growthT('giftPlan', {
                                  plan: gift.plan_family ?? 'N/A',
                                  days: gift.duration_days ?? 0,
                                })}
                              </span>
                              <span>
                                {growthT('giftCreated', {
                                  date:
                                    formatDate(gift.created_at, locale) ??
                                    t('labels.notAvailable'),
                                })}
                              </span>
                              <span>
                                {growthT('giftRecipient', {
                                  recipient:
                                    gift.recipient_hint ??
                                    growthT('giftRecipientFallback'),
                                })}
                              </span>
                              {gift.redeemed_at && (
                                <span>
                                  {growthT('giftRedeemed', {
                                    date:
                                      formatDate(gift.redeemed_at, locale) ??
                                      t('labels.notAvailable'),
                                  })}
                                </span>
                              )}
                            </div>
                          </div>

                          <button
                            type="button"
                            onClick={() => void copyGrowthCode(visibleCode)}
                            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-neon-pink/40 bg-neon-pink/10 px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-neon-pink transition hover:bg-neon-pink/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
                          >
                            <Copy className="h-4 w-4" aria-hidden="true" />
                            {copiedGrowthCode === visibleCode
                              ? growthT('copied')
                              : growthT('copyCode')}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </article>
          )}
        </section>
      )}

      {growthVisibility.referral && (
        <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <article className="rounded-[2rem] border border-neon-purple/25 bg-terminal-surface/55 p-6 backdrop-blur">
            <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-purple">
              {t('caps.eyebrow')}
            </p>
            <h2 className="mt-3 text-2xl font-display text-white">
              {t('caps.title')}
            </h2>
            <p className="mt-3 font-mono text-sm leading-7 text-muted-foreground">
              {t('caps.description')}
            </p>

            <div className="mt-6 space-y-5">
              {[
                {
                  label: t('caps.monthly'),
                  progress: getCapProgress(
                    stats?.monthly_cap_used_usd,
                    MONTHLY_SOFT_CAP_USD,
                  ),
                  value: formatMoney(
                    locale,
                    stats?.monthly_cap_used_usd ?? 0,
                    'USD',
                  ),
                },
                {
                  label: t('caps.lifetime'),
                  progress: getCapProgress(
                    stats?.lifetime_cap_used_usd,
                    LIFETIME_SOFT_CAP_USD,
                  ),
                  value: formatMoney(
                    locale,
                    stats?.lifetime_cap_used_usd ?? 0,
                    'USD',
                  ),
                },
              ].map((item) => (
                <div key={item.label}>
                  <div className="flex items-center justify-between gap-4 font-mono text-xs">
                    <span className="uppercase tracking-[0.18em] text-muted-foreground">
                      {item.label}
                    </span>
                    <span className="text-white">{item.value}</span>
                  </div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-grid-line/30">
                    <div
                      className="h-full rounded-full bg-neon-purple"
                      style={{ width: `${item.progress}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </article>

          <article className="rounded-[2rem] border border-grid-line/30 bg-terminal-surface/55 p-6 backdrop-blur">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-cyan">
                  {t('lifecycle.eyebrow')}
                </p>
                <h2 className="mt-3 text-2xl font-display text-white">
                  {t('lifecycle.title')}
                </h2>
                <p className="mt-3 font-mono text-sm leading-7 text-muted-foreground">
                  {t('lifecycle.description')}
                </p>
              </div>
              <StatusPill
                tone={rewardSummary.blocked_by_risk ? 'amber' : 'green'}
              >
                {t('lifecycle.blocked', {
                  count: rewardSummary.blocked_by_risk,
                })}
              </StatusPill>
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {(
                [
                  'pending',
                  'available',
                  'blocked_by_risk',
                  'reversed',
                  'expired',
                ] as const
              ).map((statusKey) => {
                const tone = getRewardTone(statusKey);

                return (
                  <div
                    key={statusKey}
                    className={`rounded-2xl border p-4 ${toneClasses[tone].border} ${toneClasses[tone].fill}`}
                  >
                    <div className={toneClasses[tone].text}>
                      {getLifecycleIcon(statusKey)}
                    </div>
                    <p className="mt-3 font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
                      {t(`lifecycle.status.${statusKey}`)}
                    </p>
                    <p className="mt-2 text-2xl font-display text-white">
                      {rewardSummary[statusKey]}
                    </p>
                    <p className="mt-1 font-mono text-xs text-muted-foreground">
                      {formatMoney(
                        locale,
                        getRewardAmountByStatus(rewardTimeline, statusKey),
                        currency,
                      )}
                    </p>
                  </div>
                );
              })}
            </div>
          </article>
        </section>
      )}

      {growthVisibility.referral && (
        <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <article className="rounded-[2rem] border border-grid-line/30 bg-terminal-surface/55 p-6 backdrop-blur">
            <p className="font-mono text-xs uppercase tracking-[0.28em] text-matrix-green">
              {t('activity.eyebrow')}
            </p>
            <h2 className="mt-3 text-2xl font-display text-white">
              {t('activity.title')}
            </h2>

            {rewardsQuery.isPending || commissionsQuery.isPending ? (
              <div className="mt-6 space-y-3">
                {[0, 1, 2].map((item) => (
                  <LoadingBlock key={item} />
                ))}
              </div>
            ) : rewardTimeline.length === 0 ? (
              <div className="mt-6 rounded-3xl border border-grid-line/30 bg-black/20 p-8 text-center">
                <History
                  className="mx-auto h-10 w-10 text-muted-foreground/60"
                  aria-hidden="true"
                />
                <p className="mt-3 font-mono text-sm text-muted-foreground">
                  {t('activity.empty')}
                </p>
              </div>
            ) : (
              <div className="mt-6 space-y-3">
                {rewardTimeline.slice(0, 6).map((item) => {
                  const tone = getRewardTone(item.status);

                  return (
                    <div
                      key={`${item.source}-${item.id}`}
                      className="rounded-2xl border border-grid-line/30 bg-black/20 p-4 transition hover:border-matrix-green/25"
                    >
                      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-mono text-sm text-white">
                              {item.source === 'reward'
                                ? t('activity.reward')
                                : t('activity.commission')}
                            </p>
                            <StatusPill tone={tone}>
                              {formatLabel(
                                item.status,
                                t('labels.notAvailable'),
                              )}
                            </StatusPill>
                          </div>
                          <p className="mt-2 font-mono text-xs leading-6 text-muted-foreground">
                            {formatDate(item.createdAt, locale)} /{' '}
                            {formatShortId(item.id)}
                          </p>
                          {item.holdUntil && (
                            <p className="mt-1 font-mono text-xs text-muted-foreground">
                              {t('activity.holdUntil', {
                                date:
                                  formatDate(item.holdUntil, locale) ??
                                  t('labels.notAvailable'),
                              })}
                            </p>
                          )}
                        </div>
                        <p
                          className={`font-display text-xl ${toneClasses[tone].text}`}
                        >
                          {formatMoney(locale, item.amount, item.currency)}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </article>

          <article className="rounded-[2rem] border border-grid-line/30 bg-terminal-surface/55 p-6 backdrop-blur">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-pink">
                  {t('notifications.eyebrow')}
                </p>
                <h2 className="mt-3 text-2xl font-display text-white">
                  {t('notifications.title')}
                </h2>
                <p className="mt-3 font-mono text-sm leading-7 text-muted-foreground">
                  {t('notifications.description')}
                </p>
              </div>
              <StatusPill
                tone={
                  (notificationCountersQuery.data
                    ?.action_required_notifications ?? 0) > 0
                    ? 'amber'
                    : 'green'
                }
              >
                {t('notifications.actionRequired', {
                  count:
                    notificationCountersQuery.data
                      ?.action_required_notifications ?? 0,
                })}
              </StatusPill>
            </div>

            {notificationsQuery.isPending ? (
              <div className="mt-6 space-y-3">
                {[0, 1].map((item) => (
                  <LoadingBlock key={item} />
                ))}
              </div>
            ) : notifications.length === 0 ? (
              <div className="mt-6 rounded-3xl border border-grid-line/30 bg-black/20 p-8 text-center">
                <History
                  className="mx-auto h-10 w-10 text-muted-foreground/60"
                  aria-hidden="true"
                />
                <p className="mt-3 font-mono text-sm text-muted-foreground">
                  {t('notifications.empty')}
                </p>
              </div>
            ) : (
              <div className="mt-6 space-y-3">
                {notifications.map((notification) => (
                  <div
                    key={notification.id}
                    className="rounded-2xl border border-grid-line/30 bg-black/20 p-4"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="font-mono text-sm text-white">
                          {notification.title}
                        </p>
                        <p className="mt-2 line-clamp-2 font-mono text-xs leading-6 text-muted-foreground">
                          {notification.message}
                        </p>
                      </div>
                      <StatusPill
                        tone={notification.action_required ? 'amber' : 'cyan'}
                      >
                        {notification.action_required
                          ? t('notifications.required')
                          : notification.unread
                            ? t('notifications.unread')
                            : t('notifications.read')}
                      </StatusPill>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </article>
        </section>
      )}
    </div>
  );
}
