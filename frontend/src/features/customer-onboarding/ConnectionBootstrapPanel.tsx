'use client';

import { useMemo, useRef, useState } from 'react';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import QRCode from 'react-qr-code';
import {
  CheckCircle2,
  Copy,
  ExternalLink,
  Loader2,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useRouter } from '@/i18n/navigation';
import {
  customerOnboardingApi,
  type CustomerOnboardingConnectionInstruction,
  type OnboardingConnectionPlatform,
  type OnboardingConnectionSurface,
} from './api';
import { normalizeOnboardingDestination } from './routing';

const CONNECTION_PLATFORMS = ['ios', 'android', 'windows', 'macos', 'linux'] as const;
const PENDING_REFRESH_LIMIT_MS = 30_000;
const PENDING_REFRESH_INTERVAL_MS = 4_000;

type CustomerConnectionPanelSurface = Extract<OnboardingConnectionSurface, 'web' | 'miniapp'>;
type RenderableConnectionInstruction = CustomerOnboardingConnectionInstruction & {
  steps: NonNullable<CustomerOnboardingConnectionInstruction['steps']>;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isAuthorizationError(error: unknown): boolean {
  if (!isRecord(error) || !isRecord(error.response)) {
    return false;
  }
  const status = error.response.status;
  return status === 401 || status === 403;
}

function detectPlatform(): OnboardingConnectionPlatform {
  if (typeof navigator === 'undefined') {
    return 'unknown';
  }

  const userAgent = navigator.userAgent.toLowerCase();
  if (/iphone|ipad|ipod/.test(userAgent)) {
    return 'ios';
  }
  if (userAgent.includes('android')) {
    return 'android';
  }
  if (userAgent.includes('windows')) {
    return 'windows';
  }
  if (userAgent.includes('mac os') || userAgent.includes('macintosh')) {
    return 'macos';
  }
  if (userAgent.includes('linux')) {
    return 'linux';
  }
  return 'unknown';
}

function scopedTranslationKey(key: string): string {
  return key
    .replace(/^Auth\.onboarding\./, '')
    .replace(/^onboarding\./, '');
}

function buildFallbackInstruction(
  platform: Exclude<OnboardingConnectionPlatform, 'unknown'>,
): RenderableConnectionInstruction {
  return {
    platform,
    title_key: `connection.platforms.${platform}`,
    steps: [1, 2, 3, 4].map((step) => ({
      order: step,
      title_key: `connection.instructions.${platform}.step${step}.title`,
      body_key: `connection.instructions.${platform}.step${step}.body`,
    })),
    recommended_apps: [],
  };
}

function formatTrafficLimit(bytes: number | null | undefined): string | null {
  if (!bytes || bytes <= 0) {
    return null;
  }

  const gib = bytes / 1024 / 1024 / 1024;
  return gib >= 1 ? `${Math.round(gib)} GB` : `${Math.round(bytes / 1024 / 1024)} MB`;
}

export function ConnectionBootstrapPanel({
  surface,
}: {
  surface: CustomerConnectionPanelSurface;
}) {
  const t = useTranslations('Auth.onboarding');
  const router = useRouter();
  const queryClient = useQueryClient();
  const pendingRefreshStartedAtRef = useRef<number | null>(null);
  const [selectedPlatform, setSelectedPlatform] = useState<OnboardingConnectionPlatform>(() => {
    const detected = detectPlatform();
    return detected === 'unknown' ? 'ios' : detected;
  });
  const [copyStatus, setCopyStatus] = useState<'idle' | 'copied' | 'failed'>('idle');

  const bootstrapQuery = useQuery({
    queryKey: ['customer-onboarding', 'connection-bootstrap', surface, selectedPlatform],
    queryFn: async () => {
      const { data } = await customerOnboardingApi.connectionBootstrap({
        surface,
        platform_hint: selectedPlatform,
      });
      return data;
    },
    placeholderData: keepPreviousData,
    retry: (failureCount, error) => failureCount < 1 && !isAuthorizationError(error),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status !== 'service_identity_pending') {
        pendingRefreshStartedAtRef.current = null;
        return false;
      }

      if (pendingRefreshStartedAtRef.current === null) {
        pendingRefreshStartedAtRef.current = Date.now();
      }

      return Date.now() - pendingRefreshStartedAtRef.current < PENDING_REFRESH_LIMIT_MS
        ? PENDING_REFRESH_INTERVAL_MS
        : false;
    },
  });

  const markConnectedMutation = useMutation({
    mutationFn: async () => {
      const currentBootstrap = bootstrapQuery.data;
      const connectionSessionId = currentBootstrap?.connection_session_id;
      if (!connectionSessionId) {
        throw new Error('Missing onboarding connection session id');
      }
      const { data } = await customerOnboardingApi.markConnected({
        connection_session_id: connectionSessionId,
        flow_key: currentBootstrap?.flow_key ?? null,
        platform: selectedPlatform,
        source_surface: surface,
        version: currentBootstrap?.version ?? null,
      });
      return data;
    },
    onSuccess: async (result) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['current-entitlements'] }),
        queryClient.invalidateQueries({ queryKey: ['current-service-state'] }),
        queryClient.invalidateQueries({ queryKey: ['subscriptions'] }),
        queryClient.invalidateQueries({ queryKey: ['miniapp-bootstrap'] }),
        queryClient.resetQueries({ queryKey: ['miniapp-config'], exact: true }),
      ]);
      router.replace(normalizeOnboardingDestination(result.next_destination, surface));
    },
  });

  const bootstrap = bootstrapQuery.data;
  const subscriptionUrl = bootstrap?.subscription_url ?? null;
  const qrPayload = bootstrap?.qr_payload ?? subscriptionUrl;
  const trafficLimit = formatTrafficLimit(bootstrap?.traffic_limit_bytes);
  const availableInstruction = useMemo<RenderableConnectionInstruction>(() => {
    const instruction = bootstrap?.instructions?.find((item) => item.platform === selectedPlatform);
    const fallbackPlatform = selectedPlatform === 'unknown' ? 'ios' : selectedPlatform;
    const fallback = buildFallbackInstruction(fallbackPlatform);
    if (!instruction) {
      return fallback;
    }

    return {
      ...instruction,
      steps: instruction.steps?.length ? instruction.steps : fallback.steps,
      recommended_apps: instruction.recommended_apps ?? fallback.recommended_apps,
    };
  }, [bootstrap?.instructions, selectedPlatform]);
  const dashboardDestination = surface === 'miniapp' ? '/miniapp/home' : '/dashboard';
  const isMiniApp = surface === 'miniapp';

  const handleCopy = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopyStatus('copied');
    } catch {
      setCopyStatus('failed');
    }
  };

  const handleOpen = (value: string) => {
    window.open(value, '_blank', 'noopener,noreferrer');
  };

  if (bootstrapQuery.isLoading && !bootstrap) {
    return (
      <div className="mt-6 flex items-center gap-3 rounded-lg border border-grid-line/40 p-4 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin text-neon-cyan" aria-hidden="true" />
        {t('connection.loading')}
      </div>
    );
  }

  if (bootstrapQuery.isError && !bootstrap) {
    const isAuthError = isAuthorizationError(bootstrapQuery.error);
    return (
      <div className="mt-6 rounded-lg border border-yellow-500/40 bg-yellow-500/10 p-4">
        <p className="text-sm text-yellow-100" role="alert">
          {isAuthError ? t('connection.authorizationError') : t('connection.networkError')}
        </p>
        <Button
          type="button"
          onClick={() => void bootstrapQuery.refetch()}
          className="mt-4 bg-neon-cyan text-black hover:bg-neon-cyan/90"
          magnetic={false}
        >
          <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
          {t('connection.retry')}
        </Button>
      </div>
    );
  }

  if (!bootstrap || !bootstrap.available || !subscriptionUrl || !qrPayload || !bootstrap.connection_session_id) {
    const isPending = bootstrap?.status === 'service_identity_pending';
    return (
      <div className="mt-6 rounded-lg border border-amber-400/35 bg-amber-400/10 p-4">
        <p className="font-mono text-xs uppercase tracking-[0.14em] text-amber-100">
          {isPending ? t('connection.pendingTitle') : t('connection.unavailableTitle')}
        </p>
        <p className="mt-2 text-sm leading-6 text-amber-100/80" role={isPending ? 'status' : 'alert'}>
          {isPending ? t('connection.pending') : t('connection.unavailable')}
        </p>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          <Button
            type="button"
            onClick={() => void bootstrapQuery.refetch()}
            className="min-h-11 bg-neon-cyan text-black hover:bg-neon-cyan/90"
            magnetic={false}
          >
            <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
            {t('connection.retry')}
          </Button>
          <Button
            type="button"
            variant="outline"
            className="min-h-11"
            onClick={() => router.replace(dashboardDestination)}
            magnetic={false}
          >
            {isMiniApp ? t('connection.goMiniAppHome') : t('connection.goDashboard')}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <section
      aria-labelledby="onboarding-connection-title"
      className={[
        'mt-6 rounded-lg border border-matrix-green/35 bg-matrix-green/10 p-4',
        isMiniApp ? 'pb-[calc(var(--safe-area-bottom)+1rem)]' : '',
      ].join(' ')}
    >
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-matrix-green/30 bg-matrix-green/10">
          <ShieldCheck className="h-5 w-5 text-matrix-green" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <p className="font-mono text-xs uppercase tracking-[0.14em] text-matrix-green">
            {t('connection.eyebrow')}
          </p>
          <h2 id="onboarding-connection-title" className="mt-1 font-display text-xl uppercase text-foreground">
            {t('connection.title')}
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {t('connection.description')}
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1fr)]">
        <div className="rounded-lg border border-grid-line/40 bg-black/25 p-4">
          <p className="font-mono text-xs uppercase tracking-[0.14em] text-foreground">
            {t('connection.qrCaption')}
          </p>
          <div className="mt-3 flex justify-center rounded-lg bg-white p-3">
            <QRCode value={qrPayload} className="h-auto w-full max-w-[220px]" />
          </div>
          <label
            htmlFor="onboarding-connection-url"
            className="mt-4 block font-mono text-xs uppercase tracking-[0.14em] text-white/55"
          >
            {t('connection.subscriptionUrlLabel')}
          </label>
          <input
            id="onboarding-connection-url"
            readOnly
            value={subscriptionUrl}
            className="mt-2 w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 font-mono text-xs text-white outline-none focus:border-neon-cyan/60"
            onFocus={(event) => event.currentTarget.select()}
          />
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <Button
              type="button"
              onClick={() => void handleCopy(subscriptionUrl)}
              className="min-h-11 bg-neon-cyan text-black hover:bg-neon-cyan/90"
              magnetic={false}
            >
              <Copy className="mr-2 h-4 w-4" aria-hidden="true" />
              {t('connection.copyLink')}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpen(subscriptionUrl)}
              className="min-h-11"
              magnetic={false}
            >
              <ExternalLink className="mr-2 h-4 w-4" aria-hidden="true" />
              {t('connection.openLink')}
            </Button>
          </div>
          <p className="mt-2 text-xs text-muted-foreground" role="status">
            {copyStatus === 'copied'
              ? t('connection.copySuccess')
              : copyStatus === 'failed'
                ? t('connection.copyFailed')
                : t('connection.copyHint')}
          </p>
          <div className="mt-3 grid gap-1 text-xs font-mono text-white/55">
            {bootstrap.config_profile_name ? (
              <span>{t('connection.profileName', { profile: bootstrap.config_profile_name })}</span>
            ) : null}
            {bootstrap.device_limit ? (
              <span>{t('connection.deviceLimit', { count: bootstrap.device_limit })}</span>
            ) : null}
            {trafficLimit ? (
              <span>{t('connection.trafficLimit', { limit: trafficLimit })}</span>
            ) : null}
            {bootstrap.expires_at ? (
              <span>{t('connection.expiresAt', { date: bootstrap.expires_at })}</span>
            ) : null}
          </div>
        </div>

        <div className="rounded-lg border border-grid-line/40 bg-black/20 p-4">
          <div
            role="tablist"
            aria-label={t('connection.platformTabsLabel')}
            className="flex flex-wrap gap-2"
          >
            {CONNECTION_PLATFORMS.map((platform) => (
              <button
                key={platform}
                type="button"
                role="tab"
                aria-selected={selectedPlatform === platform}
                onClick={() => setSelectedPlatform(platform)}
                className={[
                  'rounded-lg border px-3 py-2 font-mono text-xs uppercase tracking-[0.12em] transition-colors',
                  selectedPlatform === platform
                    ? 'border-neon-cyan bg-neon-cyan/15 text-neon-cyan'
                    : 'border-white/10 bg-white/[0.03] text-white/60 hover:text-white',
                ].join(' ')}
              >
                {t(`connection.platforms.${platform}`)}
              </button>
            ))}
          </div>

          <div className="mt-4">
            <h3 className="font-display text-base uppercase tracking-[0.14em] text-neon-cyan">
              {t(scopedTranslationKey(availableInstruction.title_key))}
            </h3>
            <ol className="mt-3 space-y-3">
              {availableInstruction.steps.map((step) => (
                <li key={`${availableInstruction.platform}-${step.order}`} className="flex gap-3 text-sm">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-neon-cyan/30 bg-neon-cyan/10 font-mono text-xs text-neon-cyan">
                    {step.order}
                  </span>
                  <div className="min-w-0">
                    <p className="font-semibold text-foreground">
                      {t(scopedTranslationKey(step.title_key))}
                    </p>
                    <p className="mt-1 leading-6 text-muted-foreground">
                      {t(scopedTranslationKey(step.body_key))}
                    </p>
                    {step.action_url ? (
                      <a
                        href={step.action_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-2 inline-flex items-center gap-1 text-xs font-mono text-neon-cyan underline-offset-4 hover:underline"
                      >
                        {t('connection.openRecommendedApp')}
                        <ExternalLink className="h-3 w-3" aria-hidden="true" />
                      </a>
                    ) : null}
                    {step.copy_value ? (
                      <button
                        type="button"
                        onClick={() => void handleCopy(step.copy_value ?? '')}
                        className="mt-2 inline-flex items-center gap-1 text-xs font-mono text-neon-cyan underline-offset-4 hover:underline"
                      >
                        <Copy className="h-3 w-3" aria-hidden="true" />
                        {t('connection.copyStepValue')}
                      </button>
                    ) : null}
                  </div>
                </li>
              ))}
            </ol>
            {availableInstruction.recommended_apps?.length ? (
              <div className="mt-4 rounded-lg border border-white/10 bg-white/[0.03] p-3">
                <p className="font-mono text-xs uppercase tracking-[0.14em] text-white/55">
                  {t('connection.recommendedApps')}
                </p>
                <ul className="mt-2 space-y-2">
                  {availableInstruction.recommended_apps.map((app) => (
                    <li key={`${availableInstruction.platform}-${app.name}`} className="text-sm text-muted-foreground">
                      {app.url ? (
                        <a
                          href={app.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-neon-cyan underline-offset-4 hover:underline"
                        >
                          {app.name}
                          <ExternalLink className="h-3 w-3" aria-hidden="true" />
                        </a>
                      ) : app.name}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <div
        className={[
          'mt-4 flex flex-col gap-3 sm:flex-row',
          isMiniApp ? 'sticky bottom-[calc(var(--safe-area-bottom)+0.75rem)] rounded-lg border border-black/20 bg-terminal-bg/95 p-2 backdrop-blur' : '',
        ].join(' ')}
      >
        <Button
          type="button"
          disabled={markConnectedMutation.isPending}
          onClick={() => markConnectedMutation.mutate()}
          className="min-h-11 flex-1 bg-matrix-green text-black hover:bg-matrix-green/90"
          magnetic={false}
        >
          {markConnectedMutation.isPending ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <CheckCircle2 className="mr-2 h-4 w-4" aria-hidden="true" />
          )}
          {t('connection.connected')}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => router.replace(dashboardDestination)}
          className="min-h-11 flex-1"
          magnetic={false}
        >
          {isMiniApp ? t('connection.goMiniAppHome') : t('connection.goDashboard')}
        </Button>
      </div>

      {markConnectedMutation.isError ? (
        <p className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200" role="alert">
          {isAuthorizationError(markConnectedMutation.error)
            ? t('connection.authorizationError')
            : t('connection.markConnectedFailed')}
        </p>
      ) : null}
    </section>
  );
}
