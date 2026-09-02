'use client';

import { useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  CheckCircle2,
  Clipboard,
  Copy,
  Download,
  Eye,
  EyeOff,
  ExternalLink,
  Gauge,
  KeyRound,
  QrCode,
  RefreshCw,
  Settings,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import dynamic from 'next/dynamic';
import { useLocale, useTranslations } from 'next-intl';
import { useState } from 'react';
import { Link } from '@/i18n/navigation';
import { useCustomerSubscriptions } from '@/features/customer-subscriptions/customer-subscription-context';
import {
  profileApi,
  publicNetworkApi,
  customerSubscriptionsApi,
  DEFAULT_SERVICE_STATE_REQUEST,
  serviceAccessApi,
} from '@/lib/api';
import {
  extractConfigLinks,
  formatDateTime,
  formatServiceStatus,
  getConfigDeliveryBundle,
  getConfigAvailability,
  isServiceStateActive,
  maskConfigValue,
  type ConfigAvailability,
  type ConfigLink,
} from './server-access-model';

const LIVE_STALE_MS = 30_000;
const PROFILE_STALE_MS = 60_000;
const DPI_STALE_MS = 120_000;
const LIVE_REFETCH_MS = 45_000;

const QRCodeComponent = dynamic(() => import('react-qr-code'), { ssr: false });

type CopyState = 'config' | 'download' | 'subscription' | 'unavailable' | 'error' | null;
type Tone = 'amber' | 'cyan' | 'green' | 'pink' | 'purple';

const toneClasses: Record<
  Tone,
  {
    border: string;
    fill: string;
    icon: string;
    text: string;
  }
> = {
  amber: {
    border: 'border-amber-400/30',
    fill: 'bg-amber-400/10',
    icon: 'text-amber-300',
    text: 'text-amber-300',
  },
  cyan: {
    border: 'border-neon-cyan/30',
    fill: 'bg-neon-cyan/10',
    icon: 'text-neon-cyan',
    text: 'text-neon-cyan',
  },
  green: {
    border: 'border-matrix-green/30',
    fill: 'bg-matrix-green/10',
    icon: 'text-matrix-green',
    text: 'text-matrix-green',
  },
  pink: {
    border: 'border-neon-pink/30',
    fill: 'bg-neon-pink/10',
    icon: 'text-neon-pink',
    text: 'text-neon-pink',
  },
  purple: {
    border: 'border-neon-purple/30',
    fill: 'bg-neon-purple/10',
    icon: 'text-neon-purple',
    text: 'text-neon-purple',
  },
};

function visiblePolling(intervalMs: number) {
  return (query: { state: { error: unknown } }) => {
    if (query.state.error) {
      return false;
    }

    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
      return false;
    }

    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      return false;
    }

    return intervalMs;
  };
}

function LoadingBlock({ className = 'min-h-36' }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`${className} animate-pulse rounded-3xl border border-grid-line/30 bg-terminal-surface/40`}
    />
  );
}

function StatusPill({
  label,
  tone,
}: {
  label: string;
  tone: Tone;
}) {
  const classes = toneClasses[tone];

  return (
    <span
      className={`inline-flex min-h-8 items-center rounded-full border px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] ${classes.border} ${classes.fill} ${classes.text}`}
    >
      {label}
    </span>
  );
}

function ActionButton({
  children,
  disabled,
  onClick,
}: {
  children: React.ReactNode;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-neon-cyan/40 bg-neon-cyan/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-neon-cyan transition hover:bg-neon-cyan/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg disabled:cursor-not-allowed disabled:opacity-50"
    >
      {children}
    </button>
  );
}

function RouteLink({
  children,
  href,
}: {
  children: React.ReactNode;
  href: '/settings' | '/subscriptions';
}) {
  return (
    <Link
      href={href}
      className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-grid-line/40 bg-white/[0.03] px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-foreground transition hover:border-neon-cyan/40 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
    >
      {children}
    </Link>
  );
}

function availabilityTone(availability: ConfigAvailability): Tone {
  if (availability === 'ready') {
    return 'green';
  }

  if (availability === 'missing_config') {
    return 'amber';
  }

  return 'pink';
}

function getCopyText(state: CopyState, t: ReturnType<typeof useTranslations>) {
  if (!state) {
    return null;
  }

  return t(`copy.${state}`);
}

function fingerprintDeliveryValue(value: string): string {
  let hash = 0x811c9dc5;

  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193);
  }

  return (hash >>> 0).toString(36);
}

function getPrimaryDeliveryRevealKey(
  selectedSubscriptionKey: string | null | undefined,
  link: ConfigLink | null,
): string | null {
  if (!link) {
    return null;
  }

  return [
    selectedSubscriptionKey ?? 'current',
    link.id,
    link.kind,
    link.value.length,
    fingerprintDeliveryValue(link.value),
  ].join(':');
}

export function ServerAccessDashboard() {
  const t = useTranslations('Servers');
  const locale = useLocale();
  const [copyState, setCopyState] = useState<CopyState>(null);
  const [revealedPrimaryDeliveryKey, setRevealedPrimaryDeliveryKey] = useState<string | null>(
    null,
  );
  const { selectedSubscriptionKey } = useCustomerSubscriptions();

  const profileQuery = useQuery({
    queryKey: ['server-access', 'profile'],
    queryFn: async () => {
      const response = await profileApi.getProfile();
      return response.data;
    },
    staleTime: PROFILE_STALE_MS,
    refetchOnWindowFocus: false,
  });

  const serviceStateQuery = useQuery({
    queryKey: ['server-access', 'service-state', selectedSubscriptionKey],
    queryFn: async () => {
      const response = selectedSubscriptionKey
        ? await customerSubscriptionsApi.getServiceState(
            selectedSubscriptionKey,
            DEFAULT_SERVICE_STATE_REQUEST,
          )
        : await serviceAccessApi.getCurrentServiceState();
      return response.data;
    },
    staleTime: LIVE_STALE_MS,
    refetchInterval: visiblePolling(LIVE_REFETCH_MS),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
  });

  const configQuery = useQuery({
    queryKey: ['server-access', 'config', selectedSubscriptionKey],
    enabled: Boolean(selectedSubscriptionKey),
    queryFn: async () => {
      if (!selectedSubscriptionKey) {
        throw new Error('Selected subscription key is required to load VPN config');
      }

      const response = await customerSubscriptionsApi.getConfig(selectedSubscriptionKey);
      return response.data;
    },
    staleTime: LIVE_STALE_MS,
    refetchInterval: visiblePolling(LIVE_REFETCH_MS),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
  });

  const dpiQuery = useQuery({
    queryKey: ['public-network-dpi-score'],
    queryFn: async () => {
      const response = await publicNetworkApi.getDpiScore();
      return response.data;
    },
    staleTime: DPI_STALE_MS,
    refetchOnWindowFocus: false,
  });

  const configLinks = extractConfigLinks(configQuery.data, serviceStateQuery.data);
  const deliveryBundle = getConfigDeliveryBundle(configLinks);
  const subscriptionLink = deliveryBundle.subscriptionLink;
  const configFileLink = deliveryBundle.configFile;
  const primaryDeliveryLink = subscriptionLink ?? deliveryBundle.configFile;
  const primaryDeliveryRevealKey = getPrimaryDeliveryRevealKey(
    selectedSubscriptionKey,
    primaryDeliveryLink,
  );
  const primaryDeliveryIsSubscription = primaryDeliveryLink?.kind === 'subscription';
  const canTogglePrimaryDeliveryValue =
    !primaryDeliveryIsSubscription && primaryDeliveryRevealKey !== null;
  const showFullPrimaryDeliveryValue =
    primaryDeliveryIsSubscription ||
    (primaryDeliveryRevealKey !== null && revealedPrimaryDeliveryKey === primaryDeliveryRevealKey);
  const rawConfigLink = deliveryBundle.rawConfigLink;
  const availability = getConfigAvailability({
    config: configQuery.data,
    profile: profileQuery.data,
    serviceState: serviceStateQuery.data,
  });
  const serviceActive = isServiceStateActive(serviceStateQuery.data);
  const latestSync = Math.max(
    serviceStateQuery.dataUpdatedAt,
    configQuery.dataUpdatedAt,
  );
  const latestSyncLabel = latestSync
    ? (formatDateTime(new Date(latestSync).toISOString(), locale) ?? t('sync.neverSynced'))
    : t('sync.neverSynced');
  const hasAnyError =
    serviceStateQuery.isError ||
    configQuery.isError ||
    dpiQuery.isError;

  const copyToClipboard = async (link: ConfigLink, state: Exclude<CopyState, null>) => {
    if (typeof navigator === 'undefined' || !navigator.clipboard?.writeText) {
      setCopyState('unavailable');
      return;
    }

    try {
      await navigator.clipboard.writeText(link.value);
      setCopyState(state);
    } catch {
      setCopyState('error');
    }
  };

  const openDeliveryLink = (link: ConfigLink) => {
    if (typeof window === 'undefined' || typeof window.open !== 'function') {
      setCopyState('unavailable');
      return;
    }

    window.open(link.value, '_blank', 'noopener,noreferrer');
  };

  const downloadConfigFile = (link: ConfigLink) => {
    if (
      typeof document === 'undefined' ||
      typeof window === 'undefined' ||
      !window.URL?.createObjectURL
    ) {
      setCopyState('unavailable');
      return;
    }

    try {
      const content = link.value.endsWith('\n') ? link.value : `${link.value}\n`;
      const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = deliveryBundle.fileName;
      anchor.rel = 'noreferrer';
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
      setCopyState('download');
    } catch {
      setCopyState('error');
    }
  };

  const retryAll = () => {
    void profileQuery.refetch();
    void serviceStateQuery.refetch();
    void configQuery.refetch();
    void dpiQuery.refetch();
  };

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-[2rem] border border-neon-cyan/20 bg-terminal-surface/55 p-6 shadow-[0_0_70px_rgba(0,255,255,0.08)] backdrop-blur md:p-8">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(0,255,255,0.18),transparent_34%),radial-gradient(circle_at_bottom_right,rgba(255,0,255,0.12),transparent_30%)]" />
        <div className="relative grid gap-6 lg:grid-cols-[1.25fr_0.75fr] lg:items-end">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.34em] text-neon-cyan">
              {t('hero.eyebrow')}
            </p>
            <h1 className="mt-4 max-w-3xl text-4xl font-display tracking-[0.08em] text-white md:text-5xl">
              {t('title')}
            </h1>
            <p className="mt-4 max-w-2xl font-mono text-sm leading-7 text-muted-foreground">
              {t('subtitle')}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
            <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                {t('hero.serviceStatus')}
              </p>
              <div className="mt-3 flex items-center gap-3">
                {serviceActive ? (
                  <CheckCircle2 className="h-5 w-5 text-matrix-green" aria-hidden="true" />
                ) : (
                  <AlertTriangle className="h-5 w-5 text-amber-300" aria-hidden="true" />
                )}
                <span className="font-display text-lg text-white">
                  {formatServiceStatus(
                    serviceStateQuery.data?.access_delivery_channel?.channel_status,
                    serviceStateQuery.isPending ? t('status.loading') : t('status.pending'),
                  )}
                </span>
              </div>
            </div>
            <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                {t('hero.configStatus')}
              </p>
              <div className="mt-3 flex items-center gap-3">
                <KeyRound
                  className={`h-5 w-5 ${toneClasses[availabilityTone(availability)].icon}`}
                  aria-hidden="true"
                />
                <StatusPill
                  label={t(`config.status.${availability}`)}
                  tone={availabilityTone(availability)}
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      <section>
        <article className="rounded-[2rem] border border-neon-cyan/25 bg-terminal-surface/55 p-6 shadow-[0_0_42px_rgba(0,255,255,0.07)] backdrop-blur">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-cyan">
                {t('config.eyebrow')}
              </p>
              <h2 className="mt-3 text-2xl font-display text-white">
                {t('config.title')}
              </h2>
              <p className="mt-3 max-w-2xl font-mono text-sm leading-7 text-muted-foreground">
                {t('config.description')}
              </p>
            </div>
            <StatusPill
              label={t(`config.status.${availability}`)}
              tone={availabilityTone(availability)}
            />
          </div>

          {profileQuery.isPending || serviceStateQuery.isPending || configQuery.isPending ? (
            <LoadingBlock className="mt-6 min-h-52" />
          ) : availability === 'ready' && primaryDeliveryLink ? (
            <div className="mt-6 space-y-5">
              <div className="grid gap-5 lg:grid-cols-[180px_1fr]">
                <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
                  <div className="flex items-center gap-2">
                    <QrCode className="h-4 w-4 text-neon-cyan" aria-hidden="true" />
                    <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                      {t('config.qrCode')}
                    </p>
                  </div>
                  <div
                    aria-label={t('config.qrCode')}
                    className="mt-4 flex justify-center rounded-2xl bg-white p-4"
                    role="img"
                  >
                    <QRCodeComponent
                      bgColor="#FFFFFF"
                      fgColor="#000000"
                      level="M"
                      size={160}
                      value={deliveryBundle.qrLink?.value ?? primaryDeliveryLink.value}
                    />
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
                    <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                      {primaryDeliveryLink.kind === 'config' ? t('config.rawConfig') : t('config.subscriptionUrl')}
                    </p>
                    <p className="mt-3 break-all rounded-xl border border-grid-line/20 bg-black/30 p-3 font-mono text-sm text-foreground">
                      {showFullPrimaryDeliveryValue
                        ? primaryDeliveryLink.value
                        : maskConfigValue(primaryDeliveryLink.value)}
                    </p>
                    <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <p className="font-mono text-xs leading-6 text-muted-foreground">
                        {primaryDeliveryIsSubscription
                          ? t('config.visibleSubscription')
                          : t('config.safeDelivery')}
                      </p>
                      {canTogglePrimaryDeliveryValue ? (
                        <button
                          type="button"
                          aria-label={t(
                            showFullPrimaryDeliveryValue
                              ? 'config.hideFullValue'
                              : 'config.showFullValue',
                          )}
                          aria-pressed={showFullPrimaryDeliveryValue}
                          onClick={() =>
                            setRevealedPrimaryDeliveryKey((current) =>
                              current === primaryDeliveryRevealKey ? null : primaryDeliveryRevealKey,
                            )
                          }
                          className="inline-flex min-h-10 shrink-0 items-center justify-center gap-2 rounded-xl border border-grid-line/40 bg-white/[0.03] px-3 py-2 font-mono text-[11px] uppercase tracking-[0.14em] text-foreground transition hover:border-neon-cyan/40 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
                        >
                          {showFullPrimaryDeliveryValue ? (
                            <EyeOff className="h-4 w-4" aria-hidden="true" />
                          ) : (
                            <Eye className="h-4 w-4" aria-hidden="true" />
                          )}
                          {t(
                            showFullPrimaryDeliveryValue
                              ? 'config.hideFullValue'
                              : 'config.showFullValue',
                          )}
                        </button>
                      ) : null}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
                    <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                      {t('config.downloadFile')}
                    </p>
                    <p className="mt-2 font-mono text-sm text-foreground">
                      {deliveryBundle.fileName}
                    </p>
                    <p className="mt-2 font-mono text-xs leading-6 text-muted-foreground">
                      {t('config.downloadNote')}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap gap-3">
                {subscriptionLink && (
                  <ActionButton
                    onClick={() => copyToClipboard(subscriptionLink, 'subscription')}
                  >
                    <Copy className="h-4 w-4" aria-hidden="true" />
                    {t('config.copySubscription')}
                  </ActionButton>
                )}
                {rawConfigLink && (
                  <ActionButton onClick={() => copyToClipboard(rawConfigLink, 'config')}>
                    <Clipboard className="h-4 w-4" aria-hidden="true" />
                    {t('config.copyConfig')}
                  </ActionButton>
                )}
                {configFileLink && (
                  <ActionButton onClick={() => downloadConfigFile(configFileLink)}>
                    <Download className="h-4 w-4" aria-hidden="true" />
                    {t('config.downloadConfig')}
                  </ActionButton>
                )}
                {subscriptionLink && (
                  <ActionButton onClick={() => openDeliveryLink(subscriptionLink)}>
                    <ExternalLink className="h-4 w-4" aria-hidden="true" />
                    {t('config.openSubscription')}
                  </ActionButton>
                )}
              </div>

              {copyState && (
                <p
                  className={`font-mono text-sm ${copyState === 'error' || copyState === 'unavailable' ? 'text-amber-300' : 'text-matrix-green'}`}
                  role="status"
                >
                  {getCopyText(copyState, t)}
                </p>
              )}
            </div>
          ) : (
            <div className="mt-6 space-y-4 rounded-2xl border border-amber-400/30 bg-amber-400/10 p-5">
              <p className="font-mono text-sm leading-7 text-amber-100">
                {t(`config.empty.${availability}`)}
              </p>
              <div className="flex flex-wrap gap-3">
                <RouteLink href="/subscriptions">
                  <Zap className="h-4 w-4" aria-hidden="true" />
                  {t('actions.managePlan')}
                </RouteLink>
                <RouteLink href="/settings">
                  <Settings className="h-4 w-4" aria-hidden="true" />
                  {t('actions.openSettings')}
                </RouteLink>
              </div>
            </div>
          )}
        </article>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <article className="rounded-[2rem] border border-grid-line/30 bg-terminal-surface/55 p-6 backdrop-blur">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <h2 className="text-2xl font-display text-white">{t('servers.title')}</h2>
              <p className="mt-3 max-w-2xl font-mono text-sm leading-7 text-muted-foreground">
                {t('servers.description')}
              </p>
            </div>
            <ShieldCheck className="h-6 w-6 text-neon-pink" aria-hidden="true" />
          </div>
          <div className="mt-6 rounded-2xl border border-neon-cyan/25 bg-neon-cyan/5 p-5 font-mono text-sm leading-7 text-muted-foreground">
            {t('recommended.customerSafeReason')}
          </div>
        </article>

        <div className="space-y-6">
          <article className="rounded-[2rem] border border-neon-purple/25 bg-terminal-surface/55 p-6 backdrop-blur">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-purple">
                  {t('dpi.eyebrow')}
                </p>
                <h2 className="mt-3 text-2xl font-display text-white">
                  {t('dpi.title')}
                </h2>
              </div>
              <ShieldCheck className="h-6 w-6 text-neon-purple" aria-hidden="true" />
            </div>

            {dpiQuery.isPending ? (
              <LoadingBlock className="mt-6 min-h-36" />
            ) : dpiQuery.data ? (
              <div className="mt-6 space-y-4">
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
                    <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                      {t('dpi.enabled')}
                    </p>
                    <p className="mt-2 font-display text-xl text-white">
                      {dpiQuery.data.enabled ? t('labels.yes') : t('labels.no')}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
                    <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                      {t('dpi.confidence')}
                    </p>
                    <p className="mt-2 font-display text-xl text-white">
                      {t(`confidence.${dpiQuery.data.confidence}`)}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
                    <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                      {t('dpi.countries')}
                    </p>
                    <p className="mt-2 font-display text-xl text-white">
                      {dpiQuery.data.countriesTracked}
                    </p>
                  </div>
                </div>
                <p className="font-mono text-sm leading-7 text-muted-foreground">
                  {t('dpi.description', {
                    version: dpiQuery.data.methodologyVersion,
                  })}
                </p>
              </div>
            ) : (
              <p className="mt-6 rounded-2xl border border-amber-400/30 bg-amber-400/10 p-5 font-mono text-sm text-amber-100">
                {t('dpi.empty')}
              </p>
            )}
          </article>

          <article className="rounded-[2rem] border border-grid-line/30 bg-terminal-surface/55 p-6 backdrop-blur">
            <div className="flex items-start gap-4">
              <Gauge className="mt-1 h-6 w-6 text-neon-cyan" aria-hidden="true" />
              <div>
                <h2 className="text-2xl font-display text-white">{t('guide.title')}</h2>
                <p className="mt-3 font-mono text-sm leading-7 text-muted-foreground">
                  {t('guide.description')}
                </p>
              </div>
            </div>
            <ol className="mt-6 space-y-4">
              {(['import', 'choose', 'verify'] as const).map((step, index) => (
                <li key={step} className="flex gap-4">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-neon-cyan/30 bg-neon-cyan/10 font-display text-sm text-neon-cyan">
                    {index + 1}
                  </span>
                  <div>
                    <p className="font-display text-lg text-white">
                      {t(`guide.steps.${step}.title`)}
                    </p>
                    <p className="mt-1 font-mono text-sm leading-6 text-muted-foreground">
                      {t(`guide.steps.${step}.body`)}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </article>
        </div>
      </section>

      <section className="flex flex-col gap-3 rounded-2xl border border-grid-line/30 bg-terminal-surface/45 p-4 font-mono text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-3">
          <StatusPill
            label={hasAnyError ? t('sync.degraded') : t('sync.live')}
            tone={hasAnyError ? 'amber' : 'green'}
          />
          <span>{t('sync.lastSynced', { value: latestSyncLabel })}</span>
        </div>
        <button
          type="button"
          onClick={retryAll}
          className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-grid-line/40 px-3 py-2 uppercase tracking-[0.16em] text-foreground transition hover:border-neon-cyan/40 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
        >
          <RefreshCw
            className={`h-4 w-4 ${
              serviceStateQuery.isFetching ||
              configQuery.isFetching ||
              dpiQuery.isFetching
                ? 'animate-spin'
                : ''
            }`}
            aria-hidden="true"
          />
          {t('sync.retry')}
        </button>
      </section>
    </div>
  );
}
