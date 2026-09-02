'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  CheckCircle2,
  CircleOff,
  Clock3,
  Link2,
  Loader2,
  Network,
  RefreshCw,
  Unplug,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { toIntlLocale } from '@/i18n/intl-locale';
import {
  remnawaveStatusApi,
  type CustomerRemnawaveConnectionsStatus,
} from '@/lib/api/remnawave-status';
import { cn } from '@/lib/utils';

type CustomerConnectionsCardProps = {
  surface: 'dashboard' | 'miniapp';
};

function getHttpStatus(error: unknown): number | null {
  const status = (error as { response?: { status?: unknown } } | null)?.response?.status;
  return typeof status === 'number' ? status : null;
}

function createIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  // WebView fallback. The key is opaque and scoped by the authenticated actor
  // server-side; it never contains customer data.
  return `drop-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function formatLastSeen(value: string | null, locale: string, fallback: string): string {
  if (!value) {
    return fallback;
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return fallback;
  }

  return parsed.toLocaleString(toIntlLocale(locale));
}

export function CustomerConnectionsCard({ surface }: CustomerConnectionsCardProps) {
  const locale = useLocale();
  const t = useTranslations(
    surface === 'miniapp'
      ? 'MiniApp.liveConnections'
      : 'Dashboard.vpnServiceStatus.liveConnections',
  );
  const [requestId, setRequestId] = useState<string | null>(null);
  const [pollAfterMs, setPollAfterMs] = useState(1_000);
  const [dropAttempted, setDropAttempted] = useState(false);

  const requestMutation = useMutation({
    mutationFn: remnawaveStatusApi.requestCustomerConnections,
    retry: false,
    onSuccess: (request) => {
      setRequestId(request.request_id);
      setPollAfterMs(request.poll_after_seconds * 1_000);
    },
  });

  const statusQuery = useQuery({
    enabled: requestId !== null,
    queryFn: () => {
      if (!requestId) {
        throw new Error('Customer connection request is missing');
      }
      return remnawaveStatusApi.getCustomerConnections(requestId);
    },
    queryKey: ['customer-remnawave-connections', requestId],
    refetchInterval: (query) => {
      const status = query.state.data;
      return status?.is_completed || status?.is_failed ? false : pollAfterMs;
    },
    refetchIntervalInBackground: false,
    retry: 1,
  });

  const dropMutation = useMutation({
    mutationFn: remnawaveStatusApi.dropCustomerConnections,
    retry: false,
  });

  const status = statusQuery.data;
  const isPolling = Boolean(
    requestId
      && !statusQuery.isError
      && (!status || (!status.is_completed && !status.is_failed)),
  );
  const isRefreshing = requestMutation.isPending || isPolling;
  const canDrop = Boolean(
    status?.is_completed
      && !status.is_failed
      && status.connected
      && status.capabilities?.drop_connections
      && status.capabilities.drop_requires_idempotency_key,
  );

  const errorLabel = (error: unknown): string => {
    switch (getHttpStatus(error)) {
      case 403:
        return t('errors.forbidden');
      case 409:
        return t('errors.conflict');
      case 502:
        return t('errors.provider');
      case 503:
        return t('errors.unavailable');
      default:
        return t('errors.generic');
    }
  };

  const refresh = () => {
    setRequestId(null);
    setDropAttempted(false);
    dropMutation.reset();
    requestMutation.mutate();
  };

  const dropConnections = () => {
    setDropAttempted(true);
    dropMutation.mutate(createIdempotencyKey());
  };

  const receipt = dropMutation.data;
  const cardClassName = surface === 'miniapp'
    ? 'miniapp-card rounded-lg border p-4'
    : 'rounded-[1.5rem] border border-neon-cyan/25 bg-terminal-surface/55 p-5 backdrop-blur md:p-6';

  return (
    <section className={cardClassName} aria-labelledby={`${surface}-live-connections-title`}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-cyan">
            {t('eyebrow')}
          </p>
          <h3
            id={`${surface}-live-connections-title`}
            className={cn('mt-2 font-display text-white', surface === 'miniapp' ? 'text-lg' : 'text-2xl')}
          >
            {t('title')}
          </h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            {t('description')}
          </p>
        </div>
        <Button
          type="button"
          magnetic={false}
          variant="outline"
          touchTarget="minimum"
          onClick={refresh}
          disabled={isRefreshing || dropMutation.isPending}
          className="shrink-0 border-neon-cyan/35 bg-neon-cyan/10 font-mono text-neon-cyan hover:bg-neon-cyan/20 hover:text-neon-cyan"
        >
          <RefreshCw className={cn('mr-2 h-4 w-4', isRefreshing && 'animate-spin')} aria-hidden="true" />
          {isRefreshing ? t('refreshing') : requestId ? t('refresh') : t('load')}
        </Button>
      </div>

      <div
        className="mt-4 rounded-xl border border-grid-line/30 bg-black/20 p-4"
        role="status"
        aria-live="polite"
      >
        {!requestId && !requestMutation.isPending && !requestMutation.isError ? (
          <div className="flex items-start gap-3 text-sm text-muted-foreground">
            <Link2 className="mt-0.5 h-5 w-5 shrink-0 text-neon-cyan" aria-hidden="true" />
            <p>{t('idle')}</p>
          </div>
        ) : null}

        {isRefreshing ? (
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin text-neon-cyan" aria-hidden="true" />
            <p>
              {status
                ? t('progress', {
                    completed: status.progress.completed,
                    total: status.progress.total,
                  })
                : t('pending')}
            </p>
          </div>
        ) : null}

        {requestMutation.isError ? (
          <div className="flex items-start gap-3 text-sm text-amber-200">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
            <p>{errorLabel(requestMutation.error)}</p>
          </div>
        ) : null}

        {statusQuery.isError ? (
          <div className="flex items-start gap-3 text-sm text-amber-200">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
            <p>{errorLabel(statusQuery.error)}</p>
          </div>
        ) : null}

        {status?.is_failed ? (
          <div className="flex items-start gap-3 text-sm text-amber-200">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
            <p>{t('failed')}</p>
          </div>
        ) : null}

        {status?.is_completed && !status.is_failed ? (
          <ConnectionAggregate status={status} locale={locale} neverLabel={t('never')} t={t} />
        ) : null}
      </div>

      {status?.is_completed && !status.is_failed ? (
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs leading-5 text-muted-foreground">
            {t('privacy')}
          </p>
          {status.capabilities?.drop_connections ? (
            <Button
              type="button"
              magnetic={false}
              variant="destructive"
              touchTarget="minimum"
              onClick={dropConnections}
              disabled={!canDrop || dropAttempted || dropMutation.isPending}
              className="shrink-0 font-mono"
            >
              {dropMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Unplug className="mr-2 h-4 w-4" aria-hidden="true" />
              )}
              {dropMutation.isPending ? t('dropping') : t('drop')}
            </Button>
          ) : null}
        </div>
      ) : null}

      {receipt ? (
        <div
          className={cn(
            'mt-4 rounded-xl border p-3 text-sm',
            receipt.state === 'accepted'
              ? 'border-matrix-green/30 bg-matrix-green/10 text-matrix-green'
              : 'border-amber-400/30 bg-amber-400/10 text-amber-200',
          )}
          role="status"
          aria-live="polite"
        >
          <div className="flex items-start gap-2">
            {receipt.state === 'accepted' ? (
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            ) : (
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            )}
            <p>
              {receipt.state === 'accepted' ? t('dropAccepted') : t('dropUnknown')}{' '}
              {t('refreshRequired')}
            </p>
          </div>
        </div>
      ) : null}

      {dropAttempted && dropMutation.isError ? (
        <div
          className="mt-4 rounded-xl border border-amber-400/30 bg-amber-400/10 p-3 text-sm text-amber-200"
          role="alert"
        >
          {errorLabel(dropMutation.error)} {t('dropFailedNoRetry')}
        </div>
      ) : null}
    </section>
  );
}

function ConnectionAggregate({
  locale,
  neverLabel,
  status,
  t,
}: {
  locale: string;
  neverLabel: string;
  status: CustomerRemnawaveConnectionsStatus;
  t: ReturnType<typeof useTranslations>;
}) {
  const connected = status.connected === true;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        {connected ? (
          <Network className="h-5 w-5 text-matrix-green" aria-hidden="true" />
        ) : (
          <CircleOff className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
        )}
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
            {t('status')}
          </p>
          <p className={cn('mt-1 font-display', connected ? 'text-matrix-green' : 'text-white')}>
            {connected ? t('connected') : t('disconnected')}
          </p>
        </div>
      </div>

      <dl className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg border border-grid-line/30 bg-white/[0.03] p-3">
          <dt className="font-mono text-xs text-muted-foreground">{t('connectedNodes')}</dt>
          <dd className="mt-1 text-lg font-display text-white">{status.connected_node_count ?? 0}</dd>
        </div>
        <div className="rounded-lg border border-grid-line/30 bg-white/[0.03] p-3">
          <dt className="font-mono text-xs text-muted-foreground">{t('activeIps')}</dt>
          <dd className="mt-1 text-lg font-display text-white">{status.active_ip_count ?? 0}</dd>
        </div>
        <div className="rounded-lg border border-grid-line/30 bg-white/[0.03] p-3">
          <dt className="flex items-center gap-1.5 font-mono text-xs text-muted-foreground">
            <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
            {t('lastSeen')}
          </dt>
          <dd className="mt-1 break-words text-sm text-white">
            {formatLastSeen(status.last_seen_at, locale, neverLabel)}
          </dd>
        </div>
      </dl>
    </div>
  );
}
