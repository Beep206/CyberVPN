'use client';

import { useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  ArrowRight,
  BadgePercent,
  Bell,
  CheckCircle2,
  Clock,
  CreditCard,
  Gauge,
  Gift,
  KeyRound,
  RefreshCw,
  Server,
  Settings,
  ShieldCheck,
  Wallet,
  Wifi,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import {
  STAGE1_CHECKOUT_CODES_UI_ENABLED,
  STAGE1_GIFT_CODES_UI_ENABLED,
  STAGE1_GROWTH_HUB_UI_ENABLED,
  STAGE1_PROMO_CODES_UI_ENABLED,
  STAGE1_REFERRAL_UI_ENABLED,
} from '@/shared/lib/stage1-growth-flags';
import {
  entitlementsApi,
  growthNotificationsApi,
  profileApi,
  referralApi,
  serviceAccessApi,
  trialApi,
  vpnApi,
  walletApi,
} from '@/lib/api';
import {
  formatBytes,
  formatDate,
  formatDateTime,
  formatMoney,
  getCabinetActionIds,
  getCabinetHealth,
  getServiceAccessLabel,
  getStage1DashboardStates,
  getUsagePercentage,
  isUsageAvailable,
  readEntitlementNumber,
  readEntitlementString,
  readEntitlementStringArray,
  type CabinetActionId,
  type CabinetHealth,
  type CabinetStateTone,
  type Stage1DashboardStateCard,
} from './customer-cabinet-model';

const PROFILE_STALE_MS = 60_000;
const STATIC_STALE_MS = 120_000;
const LIVE_REFETCH_MS = 45_000;
const NOTIFICATION_REFETCH_MS = 30_000;

type Tone = CabinetStateTone;

const toneClasses: Record<
  Tone,
  {
    border: string;
    glow: string;
    icon: string;
    text: string;
  }
> = {
  amber: {
    border: 'border-amber-400/30',
    glow: 'shadow-[0_0_24px_rgba(251,191,36,0.08)]',
    icon: 'bg-amber-400/10 text-amber-300',
    text: 'text-amber-300',
  },
  cyan: {
    border: 'border-neon-cyan/30',
    glow: 'shadow-[0_0_24px_rgba(0,255,255,0.08)]',
    icon: 'bg-neon-cyan/10 text-neon-cyan',
    text: 'text-neon-cyan',
  },
  green: {
    border: 'border-matrix-green/30',
    glow: 'shadow-[0_0_24px_rgba(0,255,136,0.08)]',
    icon: 'bg-matrix-green/10 text-matrix-green',
    text: 'text-matrix-green',
  },
  pink: {
    border: 'border-neon-pink/30',
    glow: 'shadow-[0_0_24px_rgba(255,0,255,0.08)]',
    icon: 'bg-neon-pink/10 text-neon-pink',
    text: 'text-neon-pink',
  },
  purple: {
    border: 'border-neon-purple/30',
    glow: 'shadow-[0_0_24px_rgba(139,92,246,0.08)]',
    icon: 'bg-neon-purple/10 text-neon-purple',
    text: 'text-neon-purple',
  },
};

const stage1StateIcons: Record<Stage1DashboardStateCard['id'], LucideIcon> = {
  access: ShieldCheck,
  payment: CreditCard,
  provisioning: Server,
};

type CabinetResourceSnapshot = {
  dataUpdatedAt: number;
  id: string;
  isError: boolean;
  isFetching: boolean;
  isPending: boolean;
  label: string;
  retry: () => void;
};

function visiblePolling(intervalMs: number) {
  return () => {
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
      return false;
    }

    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      return false;
    }

    return intervalMs;
  };
}

function formatStatus(value: string | null | undefined, fallback: string): string {
  if (!value || value.trim().length === 0) {
    return fallback;
  }

  return value.replace(/[_-]+/g, ' ').trim().toUpperCase();
}

function healthTone(health: CabinetHealth): Tone {
  if (health === 'critical') {
    return 'pink';
  }

  if (health === 'attention') {
    return 'amber';
  }

  return 'green';
}

function SkeletonCard() {
  return (
    <div
      aria-hidden="true"
      className="min-h-36 animate-pulse rounded-2xl border border-grid-line/30 bg-terminal-surface/40"
    />
  );
}

function MetricCard({
  errorLabel,
  icon: Icon,
  loading,
  meta,
  onRetry,
  retryLabel,
  retrying,
  title,
  tone,
  value,
}: {
  errorLabel?: string;
  icon: LucideIcon;
  loading: boolean;
  meta: string;
  onRetry?: () => void;
  retryLabel?: string;
  retrying?: boolean;
  title: string;
  tone: Tone;
  value: string;
}) {
  if (loading) {
    return <SkeletonCard />;
  }

  const classes = toneClasses[tone];

  return (
    <article
      className={`rounded-2xl border ${classes.border} ${classes.glow} bg-terminal-surface/55 p-5 backdrop-blur`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="font-mono text-xs uppercase tracking-[0.28em] text-muted-foreground">
            {title}
          </p>
          <p className="mt-3 break-words text-2xl font-display text-white">
            {value}
          </p>
        </div>
        <div
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border ${classes.border} ${classes.icon}`}
        >
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <p className="font-mono text-xs text-muted-foreground">
          {errorLabel ?? meta}
        </p>
        {errorLabel && onRetry && retryLabel && (
          <button
            type="button"
            onClick={onRetry}
            className={`inline-flex min-h-8 items-center gap-2 rounded-full border ${classes.border} px-3 py-1 font-mono text-xs ${classes.text} transition hover:bg-white/5 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg`}
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${retrying ? 'animate-spin' : ''}`}
              aria-hidden="true"
            />
            {retryLabel}
          </button>
        )}
      </div>
    </article>
  );
}

function ProgressBar({
  fallbackLabel,
  label,
  percentage,
}: {
  fallbackLabel: string;
  label: string;
  percentage: number | null;
}) {
  if (percentage === null) {
    return (
      <div className="rounded-full border border-matrix-green/30 bg-matrix-green/10 px-3 py-1 font-mono text-xs text-matrix-green">
        {fallbackLabel}
      </div>
    );
  }

  return (
    <div className="space-y-2" aria-label={label}>
      <div
        className="h-2 overflow-hidden rounded-full bg-white/10"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percentage}
      >
        <div
          className="h-full rounded-full bg-gradient-to-r from-matrix-green via-neon-cyan to-neon-pink"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <p className="font-mono text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

function ActionLink({
  description,
  href,
  icon: Icon,
  label,
  tone,
}: {
  description: string;
  href: string;
  icon: LucideIcon;
  label: string;
  tone: Tone;
}) {
  const classes = toneClasses[tone];
  const className = `group rounded-2xl border ${classes.border} bg-terminal-surface/45 p-4 transition duration-300 hover:-translate-y-0.5 hover:bg-terminal-surface/70 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg`;
  const content = (
    <div className="flex items-center gap-3">
      <div
        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${classes.icon}`}
      >
        <Icon className="h-5 w-5" aria-hidden="true" />
      </div>
      <div className="min-w-0 flex-1">
        <p className={`font-display text-sm ${classes.text}`}>{label}</p>
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      </div>
      <ArrowRight
        className={`h-4 w-4 shrink-0 opacity-60 transition group-hover:translate-x-1 ${classes.text}`}
        aria-hidden="true"
      />
    </div>
  );

  if (href.startsWith('#')) {
    return (
      <a href={href} className={className}>
        {content}
      </a>
    );
  }

  return (
    <Link
      href={href}
      className={className}
    >
      {content}
    </Link>
  );
}

function S2ActionPanel({
  actions,
  eyebrow,
  title,
  description,
}: {
  actions: Array<{
    description: string;
    href: string;
    icon: LucideIcon;
    id: string;
    label: string;
    tone: Tone;
  }>;
  description: string;
  eyebrow: string;
  title: string;
}) {
  return (
    <section className="rounded-[1.5rem] border border-grid-line/30 bg-terminal-surface/55 p-5 backdrop-blur md:p-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.32em] text-neon-cyan">
            {eyebrow}
          </p>
          <h3 className="mt-2 text-2xl font-display text-white">{title}</h3>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            {description}
          </p>
        </div>
      </div>
      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {actions.map((action) => (
          <ActionLink
            key={action.id}
            href={action.href}
            icon={action.icon}
            label={action.label}
            description={action.description}
            tone={action.tone}
          />
        ))}
      </div>
    </section>
  );
}

function SyncStatusPanel({
  failedResources,
  issueCount,
  isSyncing,
  lastSyncedLabel,
  loadingCount,
  onRetryAll,
  retryLabel,
  statusLabel,
  subtitle,
  title,
}: {
  failedResources: CabinetResourceSnapshot[];
  issueCount: number;
  isSyncing: boolean;
  lastSyncedLabel: string;
  loadingCount: number;
  onRetryAll: () => void;
  retryLabel: string;
  statusLabel: string;
  subtitle: string;
  title: string;
}) {
  const tone: Tone =
    issueCount > 0 ? 'amber' : loadingCount > 0 ? 'cyan' : 'green';
  const classes = toneClasses[tone];

  return (
    <section
      aria-live="polite"
      className={`rounded-2xl border ${classes.border} bg-terminal-surface/45 p-4 ${classes.glow} backdrop-blur`}
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-start gap-3">
          <div
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${classes.border} ${classes.icon}`}
          >
            <RefreshCw
              className={`h-5 w-5 ${isSyncing ? 'animate-spin' : ''}`}
              aria-hidden="true"
            />
          </div>
          <div>
            <p className={`font-mono text-xs uppercase tracking-[0.28em] ${classes.text}`}>
              {statusLabel}
            </p>
            <h2 className="mt-1 font-display text-xl text-white">{title}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
            <p className="mt-2 font-mono text-xs text-muted-foreground">
              {lastSyncedLabel}
            </p>
            {failedResources.length > 0 && (
              <div className="mt-4 rounded-xl border border-amber-400/20 bg-amber-400/5 p-3">
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-amber-200">
                  {failedResources.length === 1
                    ? failedResources[0]?.label
                    : failedResources
                        .map((resource) => resource.label)
                        .join(', ')}
                </p>
                <ul className="mt-3 grid gap-2 sm:grid-cols-2">
                  {failedResources.map((resource) => (
                    <li
                      key={resource.id}
                      className="flex items-center justify-between gap-2 rounded-lg border border-grid-line/30 bg-black/20 px-3 py-2"
                    >
                      <span className="font-mono text-xs text-muted-foreground">
                        {resource.label}
                      </span>
                      <button
                        type="button"
                        onClick={resource.retry}
                        className="inline-flex min-h-8 items-center gap-1.5 rounded-full border border-amber-400/30 px-3 py-1 font-mono text-[11px] text-amber-200 transition hover:bg-amber-400/10 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-amber-300 focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
                        aria-label={`${retryLabel}: ${resource.label}`}
                      >
                        <RefreshCw
                          className={`h-3.5 w-3.5 ${
                            resource.isFetching ? 'animate-spin' : ''
                          }`}
                          aria-hidden="true"
                        />
                        {retryLabel}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
        <button
          type="button"
          onClick={onRetryAll}
          className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-full border ${classes.border} px-5 py-2 font-mono text-sm ${classes.text} transition hover:bg-white/5 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg`}
        >
          <RefreshCw
            className={`h-4 w-4 ${isSyncing ? 'animate-spin' : ''}`}
            aria-hidden="true"
          />
          {retryLabel}
        </button>
      </div>
    </section>
  );
}

export function CustomerCabinetDashboard() {
  const locale = useLocale();
  const t = useTranslations('Dashboard.cabinet');

  const profileQuery = useQuery({
    queryFn: async () => (await profileApi.getProfile()).data,
    queryKey: ['customer-cabinet', 'profile'],
    staleTime: PROFILE_STALE_MS,
  });

  const entitlementQuery = useQuery({
    queryFn: async () => (await entitlementsApi.getCurrent()).data,
    queryKey: ['customer-cabinet', 'entitlement'],
    refetchInterval: visiblePolling(LIVE_REFETCH_MS),
    staleTime: STATIC_STALE_MS,
  });

  const usageQuery = useQuery({
    queryFn: async () => (await vpnApi.getUsage()).data,
    queryKey: ['customer-cabinet', 'usage'],
    refetchInterval: visiblePolling(LIVE_REFETCH_MS),
    staleTime: LIVE_REFETCH_MS,
  });

  const walletQuery = useQuery({
    queryFn: async () => (await walletApi.getBalance()).data,
    queryKey: ['customer-cabinet', 'wallet'],
    refetchInterval: visiblePolling(LIVE_REFETCH_MS),
    staleTime: LIVE_REFETCH_MS,
  });

  const referralQuery = useQuery({
    queryFn: async () => (await referralApi.getStats()).data,
    queryKey: ['customer-cabinet', 'referral-stats'],
    enabled: STAGE1_REFERRAL_UI_ENABLED,
    staleTime: STATIC_STALE_MS,
  });

  const notificationQuery = useQuery({
    queryFn: async () => (await growthNotificationsApi.getCounters()).data,
    queryKey: ['customer-cabinet', 'growth-notification-counters'],
    refetchInterval: visiblePolling(NOTIFICATION_REFETCH_MS),
    staleTime: NOTIFICATION_REFETCH_MS,
  });

  const notificationListQuery = useQuery({
    queryFn: async () => (await growthNotificationsApi.list(false)).data,
    queryKey: ['customer-cabinet', 'growth-notifications', 'latest'],
    refetchInterval: visiblePolling(NOTIFICATION_REFETCH_MS),
    staleTime: NOTIFICATION_REFETCH_MS,
  });

  const serviceStateQuery = useQuery({
    queryFn: async () => (await serviceAccessApi.getCurrentServiceState()).data,
    queryKey: ['customer-cabinet', 'service-state'],
    refetchInterval: visiblePolling(LIVE_REFETCH_MS),
    staleTime: LIVE_REFETCH_MS,
  });

  const trialQuery = useQuery({
    queryFn: async () => (await trialApi.getStatus()).data,
    queryKey: ['customer-cabinet', 'trial-status'],
    staleTime: STATIC_STALE_MS,
  });

  const profile = profileQuery.data;
  const entitlement = entitlementQuery.data;
  const usage = usageQuery.data;
  const wallet = walletQuery.data;
  const referral = referralQuery.data;
  const notifications = notificationQuery.data;
  const latestNotifications = notificationListQuery.data ?? [];
  const serviceState = serviceStateQuery.data;
  const trial = trialQuery.data;
  const usageIsAvailable = isUsageAvailable(usage);

  const knownEntitlement =
    entitlementQuery.isFetched || entitlementQuery.isError
      ? entitlement ?? null
      : undefined;
  const knownServiceState =
    serviceStateQuery.isFetched || serviceStateQuery.isError
      ? serviceState ?? null
      : undefined;
  const knownTrial =
    trialQuery.isFetched || trialQuery.isError ? trial ?? null : undefined;
  const usagePercentage = getUsagePercentage(usage);
  const health = getCabinetHealth({
    entitlement: knownEntitlement,
    notifications,
    serviceState: knownServiceState,
    usage,
  });
  const stage1States = getStage1DashboardStates({
    entitlement: knownEntitlement,
    serviceState: knownServiceState,
    serviceStateError: serviceStateQuery.isError,
    trial: knownTrial,
  });
  const healthClasses = toneClasses[healthTone(health)];
  const deviceLimit =
    readEntitlementNumber(entitlement, 'device_limit') ??
    readEntitlementNumber(entitlement, 'devices');
  const trafficLabel = readEntitlementString(
    entitlement,
    'display_traffic_label',
  );
  const connectionModes = readEntitlementStringArray(
    entitlement,
    'connection_modes',
  );
  const supportSla = readEntitlementString(entitlement, 'support_sla');
  const displayName =
    profile?.display_name?.trim() || profile?.email || t('anonymousUser');
  const planName = entitlement?.display_name || entitlement?.plan_code;
  const expiresAt = formatDate(entitlement?.expires_at, locale);
  const lastConnectionAt = usageIsAvailable
    ? formatDate(usage.last_connection_at, locale)
    : null;
  const periodEnd = usageIsAvailable
    ? formatDate(usage.period_end, locale)
    : null;
  const walletCurrency = wallet?.currency ?? 'USD';
  const channelLabel = getServiceAccessLabel(
    serviceState?.access_delivery_channel?.channel_type ??
      serviceState?.consumption_context.channel_type,
    t('pendingProvisioning'),
  );
  const credentialStatus = formatStatus(
    serviceState?.device_credential?.credential_status,
    t('pendingProvisioning'),
  );
  const serviceStatus = formatStatus(
    serviceState?.service_identity?.identity_status,
    t('pendingProvisioning'),
  );
  const profileKey =
    serviceState?.provisioning_profile?.profile_key ?? t('pendingProvisioning');
  const healthIcon =
    health === 'healthy'
      ? CheckCircle2
      : health === 'attention'
        ? AlertTriangle
        : ShieldCheck;
  const HealthIcon = healthIcon;

  const metricErrorLabel = t('metricUnavailable');
  const priorityActions = getCabinetActionIds({
    entitlement: knownEntitlement,
    notifications,
    serviceState: knownServiceState,
    trial: knownTrial,
    usage,
  });
  const visiblePriorityActions = priorityActions.filter(
    (actionId) => actionId !== 'inviteFriends' || STAGE1_REFERRAL_UI_ENABLED,
  );
  const actionMeta: Record<
    CabinetActionId,
    {
      description: string;
      href: string;
      icon: LucideIcon;
      label: string;
      tone: Tone;
    }
  > = {
    finishProvisioning: {
      description: t('actions.finishProvisioningDescription'),
      href: '/servers',
      icon: Server,
      label: t('actions.finishProvisioning'),
      tone: 'amber',
    },
    getConfig: {
      description: t('actions.getConfigDescription'),
      href: '/servers',
      icon: Server,
      label: t('actions.getConfig'),
      tone: 'green',
    },
    inviteFriends: {
      description: t('actions.inviteDescription'),
      href: '/referral',
      icon: Gift,
      label: t('actions.invite'),
      tone: 'purple',
    },
    managePlan: {
      description: t('actions.managePlanDescription'),
      href: '/subscriptions',
      icon: CreditCard,
      label: t('actions.managePlan'),
      tone: 'cyan',
    },
    reviewNotifications: {
      description: t('actions.reviewNotificationsDescription'),
      href: '#cabinet-notifications',
      icon: Bell,
      label: t('actions.reviewNotifications'),
      tone: 'pink',
    },
    secureAccount: {
      description: t('actions.secureAccountDescription'),
      href: '/settings',
      icon: KeyRound,
      label: t('actions.secureAccount'),
      tone: 'pink',
    },
    startTrial: {
      description: t('actions.startTrialDescription'),
      href: '/subscriptions',
      icon: Zap,
      label: t('actions.startTrial'),
      tone: 'green',
    },
    watchTraffic: {
      description: t('actions.watchTrafficDescription'),
      href: '#cabinet-usage',
      icon: Gauge,
      label: t('actions.watchTraffic'),
      tone: 'amber',
    },
  };
  const s2CommerceActions = [
    {
      description: t('s2Actions.trialPlans.description'),
      href: '/subscriptions',
      icon: Zap,
      id: 'trialPlans',
      label: t('s2Actions.trialPlans.label'),
      tone: 'green' as Tone,
    },
    {
      description: t('s2Actions.paymentHistory.description'),
      href: '/payment-history',
      icon: CreditCard,
      id: 'paymentHistory',
      label: t('s2Actions.paymentHistory.label'),
      tone: 'cyan' as Tone,
    },
    ...(STAGE1_GROWTH_HUB_UI_ENABLED
      ? [
          {
            description: t('s2Actions.growthHub.description'),
            href: '/referral',
            icon: Gift,
            id: 'growthHub',
            label: t('s2Actions.growthHub.label'),
            tone: 'purple' as Tone,
          },
        ]
      : []),
    ...(STAGE1_PROMO_CODES_UI_ENABLED ||
    STAGE1_CHECKOUT_CODES_UI_ENABLED ||
    STAGE1_GIFT_CODES_UI_ENABLED
      ? [
          {
            description: t('s2Actions.codes.description'),
            href: '/referral',
            icon: BadgePercent,
            id: 'codes',
            label: t('s2Actions.codes.label'),
            tone: 'amber' as Tone,
          },
        ]
      : []),
  ];
  const querySnapshots: CabinetResourceSnapshot[] = [
    {
      dataUpdatedAt: profileQuery.dataUpdatedAt,
      id: 'profile',
      isError: profileQuery.isError,
      isFetching: profileQuery.isFetching,
      isPending: profileQuery.isPending,
      label: t('sync.resources.profile'),
      retry: () => {
        void profileQuery.refetch();
      },
    },
    {
      dataUpdatedAt: entitlementQuery.dataUpdatedAt,
      id: 'entitlement',
      isError: entitlementQuery.isError,
      isFetching: entitlementQuery.isFetching,
      isPending: entitlementQuery.isPending,
      label: t('sync.resources.entitlement'),
      retry: () => {
        void entitlementQuery.refetch();
      },
    },
    {
      dataUpdatedAt: usageQuery.dataUpdatedAt,
      id: 'usage',
      isError: usageQuery.isError,
      isFetching: usageQuery.isFetching,
      isPending: usageQuery.isPending,
      label: t('sync.resources.usage'),
      retry: () => {
        void usageQuery.refetch();
      },
    },
    {
      dataUpdatedAt: walletQuery.dataUpdatedAt,
      id: 'wallet',
      isError: walletQuery.isError,
      isFetching: walletQuery.isFetching,
      isPending: walletQuery.isPending,
      label: t('sync.resources.wallet'),
      retry: () => {
        void walletQuery.refetch();
      },
    },
    ...(STAGE1_REFERRAL_UI_ENABLED
      ? [
          {
            dataUpdatedAt: referralQuery.dataUpdatedAt,
            id: 'referral',
            isError: referralQuery.isError,
            isFetching: referralQuery.isFetching,
            isPending: referralQuery.isPending,
            label: t('sync.resources.referral'),
            retry: () => {
              void referralQuery.refetch();
            },
          },
        ]
      : []),
    {
      dataUpdatedAt: notificationQuery.dataUpdatedAt,
      id: 'notificationCounters',
      isError: notificationQuery.isError,
      isFetching: notificationQuery.isFetching,
      isPending: notificationQuery.isPending,
      label: t('sync.resources.notificationCounters'),
      retry: () => {
        void notificationQuery.refetch();
      },
    },
    {
      dataUpdatedAt: notificationListQuery.dataUpdatedAt,
      id: 'notificationList',
      isError: notificationListQuery.isError,
      isFetching: notificationListQuery.isFetching,
      isPending: notificationListQuery.isPending,
      label: t('sync.resources.notificationList'),
      retry: () => {
        void notificationListQuery.refetch();
      },
    },
    {
      dataUpdatedAt: serviceStateQuery.dataUpdatedAt,
      id: 'serviceState',
      isError: serviceStateQuery.isError,
      isFetching: serviceStateQuery.isFetching,
      isPending: serviceStateQuery.isPending,
      label: t('sync.resources.serviceState'),
      retry: () => {
        void serviceStateQuery.refetch();
      },
    },
    {
      dataUpdatedAt: trialQuery.dataUpdatedAt,
      id: 'trial',
      isError: trialQuery.isError,
      isFetching: trialQuery.isFetching,
      isPending: trialQuery.isPending,
      label: t('sync.resources.trial'),
      retry: () => {
        void trialQuery.refetch();
      },
    },
  ];
  const issueCount = querySnapshots.filter((query) => query.isError).length;
  const failedResources = querySnapshots.filter((query) => query.isError);
  const loadingCount = querySnapshots.filter((query) => query.isPending).length;
  const isSyncing = querySnapshots.some((query) => query.isFetching);
  const latestDataUpdatedAt = querySnapshots
    .map((query) => query.dataUpdatedAt)
    .filter((value) => value > 0);
  const lastSyncedAt =
    latestDataUpdatedAt.length > 0 ? Math.max(...latestDataUpdatedAt) : null;
  const lastSyncedLabel = lastSyncedAt
    ? t('sync.lastSynced', {
        value:
          formatDateTime(new Date(lastSyncedAt).toISOString(), locale) ??
          t('unknownDate'),
      })
    : t('sync.neverSynced');
  const syncStatusLabel =
    issueCount > 0
      ? t('sync.status.degraded')
      : loadingCount > 0
        ? t('sync.status.loading')
        : t('sync.status.live');
  const syncSubtitle =
    issueCount > 0
      ? t('sync.issues', { count: issueCount })
      : loadingCount > 0
        ? t('sync.loading', { count: loadingCount })
        : t('sync.clean');

  function refetchAll() {
    void profileQuery.refetch();
    void entitlementQuery.refetch();
    void usageQuery.refetch();
    void walletQuery.refetch();
    if (STAGE1_REFERRAL_UI_ENABLED) {
      void referralQuery.refetch();
    }
    void notificationQuery.refetch();
    void notificationListQuery.refetch();
    void serviceStateQuery.refetch();
    void trialQuery.refetch();
  }

  return (
    <div className="space-y-6 md:space-y-8">
      <SyncStatusPanel
        failedResources={failedResources}
        issueCount={issueCount}
        isSyncing={isSyncing}
        lastSyncedLabel={lastSyncedLabel}
        loadingCount={loadingCount}
        onRetryAll={refetchAll}
        retryLabel={t('sync.retryAll')}
        statusLabel={syncStatusLabel}
        subtitle={syncSubtitle}
        title={t('sync.title')}
      />

      <section
        className={`rounded-[1.5rem] border ${healthClasses.border} ${healthClasses.glow} bg-terminal-surface/55 p-5 backdrop-blur md:p-6`}
      >
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-4">
            <div
              className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border ${healthClasses.border} ${healthClasses.icon}`}
            >
              <HealthIcon className="h-7 w-7" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <p className="font-mono text-xs uppercase tracking-[0.32em] text-muted-foreground">
                {t('hero.eyebrow')}
              </p>
              <h2 className="mt-2 break-words text-2xl font-display text-white md:text-4xl">
                {displayName}
              </h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground md:text-base">
                {t(`health.${health}.description`)}
              </p>
            </div>
          </div>

          <div className="grid gap-3 rounded-2xl border border-grid-line/30 bg-black/20 p-4 font-mono text-xs text-muted-foreground sm:grid-cols-3 lg:min-w-[32rem]">
            <div>
              <p className="uppercase tracking-[0.24em]">{t('hero.plan')}</p>
              <p className="mt-1 text-sm text-white">
                {planName ?? t('noActivePlan')}
              </p>
            </div>
            <div>
              <p className="uppercase tracking-[0.24em]">{t('hero.renewal')}</p>
              <p className="mt-1 text-sm text-white">
                {expiresAt ?? periodEnd ?? t('unknownDate')}
              </p>
            </div>
            <div>
              <p className="uppercase tracking-[0.24em]">{t('hero.status')}</p>
              <p className={`mt-1 text-sm ${healthClasses.text}`}>
                {t(`health.${health}.title`)}
              </p>
            </div>
          </div>
        </div>

        <div className="mt-6 grid gap-3 md:grid-cols-4">
          {visiblePriorityActions.map((actionId) => {
            const action = actionMeta[actionId];

            return (
              <ActionLink
                key={actionId}
                href={action.href}
                icon={action.icon}
                label={action.label}
                description={action.description}
                tone={action.tone}
              />
            );
          })}
        </div>
      </section>

      <S2ActionPanel
        actions={s2CommerceActions}
        eyebrow={t('s2Actions.eyebrow')}
        title={t('s2Actions.title')}
        description={t('s2Actions.description')}
      />

      <section
        aria-label={t('stage1States.ariaLabel')}
        className="grid gap-4 md:grid-cols-3"
      >
        {stage1States.map((state) => {
          const classes = toneClasses[state.tone];
          const Icon = stage1StateIcons[state.id];
          const action = state.actionId ? actionMeta[state.actionId] : null;
          const actionClassName = `mt-4 inline-flex min-h-10 items-center justify-center gap-2 rounded-full border ${classes.border} px-4 py-2 font-mono text-xs ${classes.text} transition hover:bg-white/5 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg`;
          const actionContent = action ? (
            <>
              {action.label}
              <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            </>
          ) : null;

          return (
            <article
              key={state.id}
              data-testid={`stage1-state-${state.id}`}
              className={`min-h-48 rounded-[1.25rem] border ${classes.border} ${classes.glow} bg-terminal-surface/50 p-5 backdrop-blur`}
            >
              <div className="flex items-start gap-3">
                <div
                  className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border ${classes.border} ${classes.icon}`}
                >
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </div>
                <div className="min-w-0">
                  <p className="font-mono text-xs uppercase tracking-[0.26em] text-muted-foreground">
                    {t(`stage1States.${state.id}.eyebrow`)}
                  </p>
                  <h3 className={`mt-2 break-words font-display text-xl ${classes.text}`}>
                    {t(`stage1States.${state.id}.${state.state}.title`)}
                  </h3>
                </div>
              </div>
              <p className="mt-4 text-sm leading-6 text-muted-foreground">
                {t(`stage1States.${state.id}.${state.state}.description`)}
              </p>
              {action &&
                (action.href.startsWith('#') ? (
                  <a href={action.href} className={actionClassName}>
                    {actionContent}
                  </a>
                ) : (
                  <Link href={action.href} className={actionClassName}>
                    {actionContent}
                  </Link>
                ))}
            </article>
          );
        })}
      </section>

      <section
        id="cabinet-usage"
        className="grid scroll-mt-24 gap-4 md:grid-cols-2 xl:grid-cols-4"
      >
        <MetricCard
          icon={Gauge}
          loading={usageQuery.isPending}
          title={t('metrics.traffic.title')}
          value={
            usageIsAvailable
              ? formatBytes(usage.bandwidth_used_bytes, locale)
              : t('unavailable')
          }
          meta={
            usageIsAvailable
              ? t('metrics.traffic.meta', {
                  limit: usage.bandwidth_limit_bytes
                    ? formatBytes(usage.bandwidth_limit_bytes, locale)
                    : t('unlimited'),
                })
              : metricErrorLabel
          }
          errorLabel={usageQuery.isError ? metricErrorLabel : undefined}
          onRetry={() => {
            void usageQuery.refetch();
          }}
          retryLabel={t('retry')}
          retrying={usageQuery.isFetching}
          tone="cyan"
        />
        <MetricCard
          icon={Wifi}
          loading={usageQuery.isPending}
          title={t('metrics.devices.title')}
          value={
            usageIsAvailable
              ? `${usage.connections_active}/${usage.connections_limit}`
              : t('unavailable')
          }
          meta={
            deviceLimit
              ? t('metrics.devices.metaWithLimit', { limit: deviceLimit })
              : t('metrics.devices.meta')
          }
          errorLabel={usageQuery.isError ? metricErrorLabel : undefined}
          onRetry={() => {
            void usageQuery.refetch();
          }}
          retryLabel={t('retry')}
          retrying={usageQuery.isFetching}
          tone="green"
        />
        <MetricCard
          icon={Wallet}
          loading={walletQuery.isPending}
          title={t('metrics.wallet.title')}
          value={
            wallet
              ? formatMoney(wallet.balance, walletCurrency, locale)
              : t('unavailable')
          }
          meta={
            wallet
              ? t('metrics.wallet.meta', {
                  frozen: formatMoney(wallet.frozen, walletCurrency, locale),
                })
              : t('metrics.wallet.empty')
          }
          errorLabel={walletQuery.isError ? metricErrorLabel : undefined}
          onRetry={() => {
            void walletQuery.refetch();
          }}
          retryLabel={t('retry')}
          retrying={walletQuery.isFetching}
          tone="purple"
        />
        <MetricCard
          icon={Bell}
          loading={notificationQuery.isPending}
          title={t('metrics.notifications.title')}
          value={
            notifications
              ? String(notifications.unread_notifications)
              : t('unavailable')
          }
          meta={
            notifications
              ? t('metrics.notifications.meta', {
                  actionRequired:
                    notifications.action_required_notifications,
                  total: notifications.total_notifications,
                })
              : t('metrics.notifications.empty')
          }
          errorLabel={notificationQuery.isError ? metricErrorLabel : undefined}
          onRetry={() => {
            void notificationQuery.refetch();
          }}
          retryLabel={t('retry')}
          retrying={notificationQuery.isFetching}
          tone="pink"
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <article className="rounded-[1.5rem] border border-neon-cyan/25 bg-terminal-surface/55 p-5 backdrop-blur md:p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.32em] text-neon-cyan">
                {t('readiness.eyebrow')}
              </p>
              <h3 className="mt-2 text-2xl font-display text-white">
                {t('readiness.title')}
              </h3>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                {t('readiness.description')}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="rounded-full border border-matrix-green/30 bg-matrix-green/10 px-4 py-2 font-mono text-xs text-matrix-green">
                {serviceStateQuery.isError
                  ? t('readiness.degraded')
                  : serviceStatus}
              </div>
              {serviceStateQuery.isError && (
                <button
                  type="button"
                  onClick={() => {
                    void serviceStateQuery.refetch();
                  }}
                  className="inline-flex min-h-9 items-center gap-2 rounded-full border border-amber-400/35 bg-amber-400/10 px-4 py-1 font-mono text-xs text-amber-200 transition hover:bg-amber-400/20 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-amber-300 focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
                >
                  <RefreshCw
                    className={`h-3.5 w-3.5 ${
                      serviceStateQuery.isFetching ? 'animate-spin' : ''
                    }`}
                    aria-hidden="true"
                  />
                  {t('retry')}
                </button>
              )}
            </div>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
              <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted-foreground">
                {t('readiness.channel')}
              </p>
              <p className="mt-2 text-lg font-display text-white">
                {channelLabel}
              </p>
            </div>
            <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
              <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted-foreground">
                {t('readiness.profile')}
              </p>
              <p className="mt-2 text-lg font-display text-white">
                {profileKey}
              </p>
            </div>
            <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
              <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted-foreground">
                {t('readiness.credential')}
              </p>
              <p className="mt-2 text-lg font-display text-white">
                {credentialStatus}
              </p>
            </div>
            <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
              <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted-foreground">
                {t('readiness.lastConnection')}
              </p>
              <p className="mt-2 text-lg font-display text-white">
                {lastConnectionAt ?? t('readiness.noConnectionYet')}
              </p>
            </div>
          </div>

          <div className="mt-6">
            <ProgressBar
              label={
                !usageIsAvailable
                  ? metricErrorLabel
                  : usagePercentage === null
                  ? t('metrics.traffic.unmetered')
                  : t('metrics.traffic.percentage', {
                      percentage: usagePercentage,
                    })
              }
              percentage={usagePercentage}
              fallbackLabel={
                usageIsAvailable ? t('unlimited') : t('unavailable')
              }
            />
          </div>
        </article>

        <article className="rounded-[1.5rem] border border-neon-purple/25 bg-terminal-surface/55 p-5 backdrop-blur md:p-6">
          <p className="font-mono text-xs uppercase tracking-[0.32em] text-neon-purple">
            {t('plan.eyebrow')}
          </p>
          <h3 className="mt-2 text-2xl font-display text-white">
            {t('plan.title')}
          </h3>
          <div className="mt-5 space-y-4">
            <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
              <div className="flex items-center gap-3">
                <Zap className="h-5 w-5 text-neon-cyan" aria-hidden="true" />
                <div>
                  <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted-foreground">
                    {t('plan.traffic')}
                  </p>
                  <p className="mt-1 text-white">
                    {trafficLabel ?? t('unlimited')}
                  </p>
                </div>
              </div>
            </div>
            <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
              <div className="flex items-center gap-3">
                <ShieldCheck
                  className="h-5 w-5 text-matrix-green"
                  aria-hidden="true"
                />
                <div>
                  <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted-foreground">
                    {t('plan.security')}
                  </p>
                  <p className="mt-1 text-white">
                    {connectionModes.length > 0
                      ? connectionModes.join(', ')
                      : t('plan.defaultSecurity')}
                  </p>
                </div>
              </div>
            </div>
            <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
              <div className="flex items-center gap-3">
                <Clock className="h-5 w-5 text-neon-pink" aria-hidden="true" />
                <div>
                  <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted-foreground">
                    {t('plan.support')}
                  </p>
                  <p className="mt-1 text-white">
                    {supportSla ?? t('plan.standardSupport')}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {trial?.is_trial_active && (
            <div className="mt-5 rounded-2xl border border-amber-400/30 bg-amber-400/10 p-4 font-mono text-sm text-amber-200">
              {t('plan.trialActive', { days: trial.days_remaining })}
            </div>
          )}
        </article>
      </section>

      <section
        id="cabinet-notifications"
        className="scroll-mt-24 rounded-[1.5rem] border border-neon-cyan/25 bg-terminal-surface/55 p-5 backdrop-blur md:p-6"
      >
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.32em] text-neon-cyan">
              {t('notifications.eyebrow')}
            </p>
            <h3 className="mt-2 text-2xl font-display text-white">
              {t('notifications.title')}
            </h3>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
              {t('notifications.description')}
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              void notificationListQuery.refetch();
              void notificationQuery.refetch();
            }}
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-full border border-neon-cyan/35 bg-neon-cyan/10 px-5 py-2 font-mono text-sm text-neon-cyan transition hover:bg-neon-cyan/20 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
          >
            <RefreshCw
              className={`h-4 w-4 ${
                notificationListQuery.isFetching ? 'animate-spin' : ''
              }`}
              aria-hidden="true"
            />
            {t('notifications.refresh')}
          </button>
        </div>

        <div className="mt-5 grid gap-3">
          {notificationListQuery.isPending &&
            [...Array(3)].map((_, index) => <SkeletonCard key={index} />)}

          {notificationListQuery.isError && (
            <div className="rounded-2xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm text-amber-100">
              <p className="font-mono uppercase tracking-[0.18em]">
                {t('notifications.errorTitle')}
              </p>
              <p className="mt-2 text-muted-foreground">
                {t('notifications.errorDescription')}
              </p>
            </div>
          )}

          {!notificationListQuery.isPending &&
            !notificationListQuery.isError &&
            latestNotifications.length === 0 && (
              <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-5 text-sm text-muted-foreground">
                {t('notifications.empty')}
              </div>
            )}

          {!notificationListQuery.isPending &&
            !notificationListQuery.isError &&
            latestNotifications.slice(0, 3).map((notification) => (
              <article
                key={notification.id}
                className="rounded-2xl border border-grid-line/30 bg-black/20 p-4"
              >
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      {notification.action_required && (
                        <span className="rounded-full border border-neon-pink/35 bg-neon-pink/10 px-3 py-1 font-mono text-xs text-neon-pink">
                          {t('notifications.actionRequired')}
                        </span>
                      )}
                      {notification.unread && (
                        <span className="rounded-full border border-neon-cyan/35 bg-neon-cyan/10 px-3 py-1 font-mono text-xs text-neon-cyan">
                          {t('notifications.unread')}
                        </span>
                      )}
                    </div>
                    <h4 className="mt-3 break-words font-display text-lg text-white">
                      {notification.title}
                    </h4>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      {notification.message}
                    </p>
                  </div>
                  <p className="shrink-0 font-mono text-xs text-muted-foreground">
                    {formatDateTime(notification.created_at, locale) ??
                      t('unknownDate')}
                  </p>
                </div>
              </article>
            ))}
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        {STAGE1_REFERRAL_UI_ENABLED ? (
        <article className="rounded-[1.5rem] border border-matrix-green/25 bg-terminal-surface/55 p-5 backdrop-blur md:p-6">
          <p className="font-mono text-xs uppercase tracking-[0.32em] text-matrix-green">
            {t('rewards.eyebrow')}
          </p>
          <h3 className="mt-2 text-2xl font-display text-white">
            {t('rewards.title')}
          </h3>
          <div className="mt-5 grid gap-4 sm:grid-cols-3">
            <MetricCard
              icon={Gift}
              loading={referralQuery.isPending}
              title={t('rewards.referrals')}
              value={referral ? String(referral.total_referrals) : t('unavailable')}
              meta={t('rewards.totalReferrals')}
              errorLabel={referralQuery.isError ? metricErrorLabel : undefined}
              onRetry={() => {
                void referralQuery.refetch();
              }}
              retryLabel={t('retry')}
              retrying={referralQuery.isFetching}
              tone="green"
            />
            <MetricCard
              icon={Wallet}
              loading={referralQuery.isPending}
              title={t('rewards.available')}
              value={
                referral
                  ? formatMoney(referral.available_rewards_usd, 'USD', locale)
                  : t('unavailable')
              }
              meta={t('rewards.availableMeta')}
              errorLabel={referralQuery.isError ? metricErrorLabel : undefined}
              onRetry={() => {
                void referralQuery.refetch();
              }}
              retryLabel={t('retry')}
              retrying={referralQuery.isFetching}
              tone="cyan"
            />
            <MetricCard
              icon={Clock}
              loading={referralQuery.isPending}
              title={t('rewards.pending')}
              value={
                referral
                  ? formatMoney(referral.pending_rewards_usd, 'USD', locale)
                  : t('unavailable')
              }
              meta={t('rewards.pendingMeta')}
              errorLabel={referralQuery.isError ? metricErrorLabel : undefined}
              onRetry={() => {
                void referralQuery.refetch();
              }}
              retryLabel={t('retry')}
              retrying={referralQuery.isFetching}
              tone="amber"
            />
          </div>
        </article>
        ) : null}

        <article className="rounded-[1.5rem] border border-neon-pink/25 bg-terminal-surface/55 p-5 backdrop-blur md:p-6">
          <p className="font-mono text-xs uppercase tracking-[0.32em] text-neon-pink">
            {t('security.eyebrow')}
          </p>
          <h3 className="mt-2 text-2xl font-display text-white">
            {t('security.title')}
          </h3>
          <div className="mt-5 space-y-3">
            {[
              t('security.items.cookieSession'),
              t('security.items.twoFactor'),
              t('security.items.antiPhishing'),
              t('security.items.notifications'),
            ].map((item) => (
              <div
                key={item}
                className="flex items-center gap-3 rounded-2xl border border-grid-line/30 bg-black/20 p-4"
              >
                <CheckCircle2
                  className="h-5 w-5 shrink-0 text-matrix-green"
                  aria-hidden="true"
                />
                <p className="text-sm text-muted-foreground">{item}</p>
              </div>
            ))}
          </div>
          <Link
            href="/settings"
            className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-full border border-neon-pink/40 bg-neon-pink/10 px-5 py-2 font-mono text-sm text-neon-pink transition hover:bg-neon-pink/20 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-pink focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
          >
            <Settings className="h-4 w-4" aria-hidden="true" />
            {t('security.cta')}
          </Link>
        </article>
      </section>
    </div>
  );
}
