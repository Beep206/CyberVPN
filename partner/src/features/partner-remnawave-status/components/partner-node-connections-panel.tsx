'use client';

import { useState, type FormEvent } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { AlertTriangle, CheckCircle2, RefreshCw, Unplug, Wifi } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import {
  partnerRemnawaveConnectionsApi,
  type PartnerRemnawaveConnectionReadRequest,
} from '@/lib/api/remnawave-connections';

type DropAttempt = {
  idempotencyKey: string;
  serviceIdentityUuid: string;
};

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

type ConnectionErrorKind =
  | 'forbidden'
  | 'notFound'
  | 'conflict'
  | 'invalidProvider'
  | 'unavailable'
  | 'unknown';

function getHttpStatus(error: unknown): number | null {
  if (typeof error !== 'object' || error === null || !('response' in error)) {
    return null;
  }
  const response = (error as { response?: { status?: unknown } }).response;
  return typeof response?.status === 'number' ? response.status : null;
}

function getErrorKind(error: unknown): ConnectionErrorKind {
  switch (getHttpStatus(error)) {
    case 403:
      return 'forbidden';
    case 404:
      return 'notFound';
    case 409:
      return 'conflict';
    case 502:
      return 'invalidProvider';
    case 503:
      return 'unavailable';
    default:
      return 'unknown';
  }
}

function createIdempotencyKey(): string {
  const suffix = typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `partner-connection-drop-${suffix}`;
}

function parseServiceIdentityUuid(value: string): string | null {
  const normalized = value.trim();
  return UUID_PATTERN.test(normalized) ? normalized : null;
}

function formatConnectionTimestamp(value: string, locale: string): string {
  try {
    return new Intl.DateTimeFormat(locale, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function ConnectionErrorNotice({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry?: () => void;
}) {
  const t = useTranslations('Dashboard.vpnServiceStatus.connections');
  const kind = getErrorKind(error);
  return (
    <div role="alert" className="rounded-xl border border-amber-400/30 bg-amber-400/5 p-4">
      <p className="font-display text-base text-white">{t(`errors.${kind}.title`)}</p>
      <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">
        {t(`errors.${kind}.description`)}
      </p>
      {onRetry ? (
        <Button
          type="button"
          variant="outline"
          className="mt-3"
          onClick={onRetry}
        >
          <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
          {t('retry')}
        </Button>
      ) : null}
    </div>
  );
}

export function PartnerNodeConnectionsPanel({
  connectionsAvailable,
  exactGrantCanExecute,
  executableServiceIdentityUuids,
  nodeUuid,
  roleCanExecute,
  workspaceId,
}: {
  connectionsAvailable: boolean;
  exactGrantCanExecute: boolean;
  executableServiceIdentityUuids: readonly string[];
  nodeUuid: string;
  roleCanExecute: boolean;
  workspaceId: string;
}) {
  const t = useTranslations('Dashboard.vpnServiceStatus.connections');
  const locale = useLocale();
  const [readRequest, setReadRequest] = useState<PartnerRemnawaveConnectionReadRequest | null>(null);
  const [dropAttempt, setDropAttempt] = useState<DropAttempt | null>(null);
  const [selectedServiceIdentityUuid, setSelectedServiceIdentityUuid] = useState('');
  const [manualServiceIdentityUuid, setManualServiceIdentityUuid] = useState('');
  const [showServiceIdentityError, setShowServiceIdentityError] = useState(false);
  const canExecute = roleCanExecute && exactGrantCanExecute;

  const requestMutation = useMutation({
    mutationFn: () => partnerRemnawaveConnectionsApi.requestNodeConnections(workspaceId, nodeUuid),
    onSuccess: (request) => {
      setReadRequest(request);
    },
    retry: false,
  });

  const pollQuery = useQuery({
    queryKey: ['partner-remnawave-node-connections', workspaceId, nodeUuid, readRequest?.request_id],
    queryFn: () => {
      if (!readRequest) throw new Error('Connection request is required');
      return partnerRemnawaveConnectionsApi.getNodeConnections(
        workspaceId,
        nodeUuid,
        readRequest.request_id,
      );
    },
    enabled: connectionsAvailable && readRequest !== null,
    refetchInterval: (query) => {
      const status = query.state.data;
      if (!readRequest || status?.is_completed || status?.is_failed) return false;
      return readRequest.poll_after_seconds * 1_000;
    },
    refetchIntervalInBackground: false,
    retry: false,
  });

  const dropMutation = useMutation({
    mutationFn: (attempt: DropAttempt) => partnerRemnawaveConnectionsApi.dropNodeConnectionsByServiceIdentity(
      workspaceId,
      nodeUuid,
      attempt.serviceIdentityUuid,
      attempt.idempotencyKey,
    ),
    retry: false,
  });

  const requestSnapshot = () => {
    if (!connectionsAvailable) {
      return;
    }
    setReadRequest(null);
    requestMutation.reset();
    requestMutation.mutate();
  };

  const handleDropSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const serviceIdentityUuid = parseServiceIdentityUuid(
      manualServiceIdentityUuid || selectedServiceIdentityUuid,
    );
    if (serviceIdentityUuid === null) {
      setShowServiceIdentityError(true);
      return;
    }
    setShowServiceIdentityError(false);
    const attempt = dropAttempt?.serviceIdentityUuid === serviceIdentityUuid
      ? dropAttempt
      : { idempotencyKey: createIdempotencyKey(), serviceIdentityUuid };
    setDropAttempt(attempt);
    dropMutation.mutate(attempt);
  };

  const resetDrop = () => {
    dropMutation.reset();
    setDropAttempt(null);
    setSelectedServiceIdentityUuid('');
    setManualServiceIdentityUuid('');
    setShowServiceIdentityError(false);
  };

  const pollStatus = pollQuery.data;
  const dropCapabilityAvailable = readRequest?.capabilities.drop_connections === true;
  const canRetryDropSafely = dropMutation.isError
    && dropAttempt !== null
    && (getHttpStatus(dropMutation.error) === 503 || getHttpStatus(dropMutation.error) === null);

  if (!connectionsAvailable) {
    return (
      <section
        aria-labelledby={`partner-node-connections-${nodeUuid}`}
        className="mt-4 rounded-xl border border-grid-line/20 bg-black/20 p-4"
        data-connections-state="unavailable"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h4 id={`partner-node-connections-${nodeUuid}`} className="font-display text-base text-white">
              {t('title')}
            </h4>
            <p className="mt-2 font-mono text-xs leading-5 text-muted-foreground">
              {t('description')}
            </p>
          </div>
          <Button type="button" variant="outline" disabled>
            <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
            {t('requestSnapshot')}
          </Button>
        </div>
        <p role="status" className="mt-4 rounded-xl border border-amber-400/30 bg-amber-400/5 p-4 font-mono text-sm text-amber-100">
          {t('capabilityUnavailable')}
        </p>
      </section>
    );
  }

  return (
    <section
      aria-labelledby={`partner-node-connections-${nodeUuid}`}
      className="mt-4 rounded-xl border border-grid-line/20 bg-black/20 p-4"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h4 id={`partner-node-connections-${nodeUuid}`} className="font-display text-base text-white">
            {t('title')}
          </h4>
          <p className="mt-2 font-mono text-xs leading-5 text-muted-foreground">
            {t('description')}
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          disabled={requestMutation.isPending}
          onClick={requestSnapshot}
        >
          <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
          {requestMutation.isPending ? t('requesting') : t('requestSnapshot')}
        </Button>
      </div>

      <div className="mt-4" aria-live="polite">
        {!readRequest && !requestMutation.isPending && !requestMutation.isError ? (
          <p className="rounded-xl border border-dashed border-grid-line/30 p-4 font-mono text-sm text-muted-foreground">
            {t('empty')}
          </p>
        ) : null}

        {requestMutation.isPending ? (
          <p role="status" className="font-mono text-sm text-muted-foreground">
            {t('requestingStatus')}
          </p>
        ) : null}

        {requestMutation.isError ? (
          <ConnectionErrorNotice
            error={requestMutation.error}
            onRetry={getHttpStatus(requestMutation.error) === 403
              || getHttpStatus(requestMutation.error) === 404
              ? undefined
              : requestSnapshot}
          />
        ) : null}

        {readRequest && pollQuery.isPending ? (
          <p role="status" className="font-mono text-sm text-muted-foreground">
            {t('polling')}
          </p>
        ) : null}

        {readRequest && pollQuery.isError ? (
          <ConnectionErrorNotice
            error={pollQuery.error}
            onRetry={getHttpStatus(pollQuery.error) === 403
              ? undefined
              : getHttpStatus(pollQuery.error) === 404
                ? requestSnapshot
                : () => {
                    void pollQuery.refetch();
                  }}
          />
        ) : null}

        {pollStatus && !pollStatus.is_completed && !pollStatus.is_failed ? (
          <p role="status" className="font-mono text-sm text-muted-foreground">
            {t('polling')}
          </p>
        ) : null}

        {pollStatus?.is_failed ? (
          <div role="alert" className="rounded-xl border border-amber-400/30 bg-amber-400/5 p-4">
            <p className="font-display text-base text-white">{t('jobFailed.title')}</p>
            <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">
              {t('jobFailed.description')}
            </p>
            <Button type="button" variant="outline" className="mt-3" onClick={requestSnapshot}>
              <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
              {t('requestAgain')}
            </Button>
          </div>
        ) : null}

        {pollStatus?.is_completed && !pollStatus.is_failed && pollStatus.success === false ? (
          <div role="alert" className="rounded-xl border border-amber-400/30 bg-amber-400/5 p-4">
            <p className="font-display text-base text-white">{t('jobFailed.title')}</p>
            <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">
              {t('jobFailed.description')}
            </p>
          </div>
        ) : null}

        {pollStatus?.is_completed && !pollStatus.is_failed && pollStatus.success === true ? (
          <div className="space-y-3">
            {pollStatus.connected_user_count === 0 ? (
              <p className="rounded-xl border border-dashed border-grid-line/30 p-4 font-mono text-sm text-muted-foreground">
                {t('noActiveConnections')}
              </p>
            ) : null}
            <dl className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/40 p-3">
                <dt className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
                  {t('connectedUsers')}
                </dt>
                <dd className="mt-2 font-display text-2xl text-white">
                  {pollStatus.connected_user_count}
                </dd>
              </div>
              <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/40 p-3">
                <dt className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
                  {t('activeAddresses')}
                </dt>
                <dd className="mt-2 font-display text-2xl text-white">
                  {pollStatus.active_ip_count}
                </dd>
              </div>
              <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/40 p-3">
                <dt className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
                  {t('lastSeen')}
                </dt>
                <dd className="mt-2 font-mono text-sm text-white">
                  {pollStatus.last_seen_at ? (
                    <time dateTime={pollStatus.last_seen_at}>
                      {formatConnectionTimestamp(pollStatus.last_seen_at, locale)}
                    </time>
                  ) : t('neverSeen')}
                </dd>
              </div>
            </dl>
          </div>
        ) : null}
      </div>

      <div className="mt-5 border-t border-grid-line/20 pt-4">
        <div className="flex items-start gap-3">
          <Unplug className="mt-0.5 h-5 w-5 text-neon-pink" aria-hidden="true" />
          <div>
            <h5 className="font-display text-base text-white">{t('drop.title')}</h5>
            <p className="mt-1 font-mono text-xs leading-5 text-muted-foreground">
              {t('drop.description')}
            </p>
          </div>
        </div>

        {!canExecute ? (
          <div role="note" className="mt-3 rounded-xl border border-grid-line/25 bg-terminal-bg/40 p-3">
            <p className="font-mono text-sm text-muted-foreground">{t('drop.permissionRequired')}</p>
          </div>
        ) : null}

        {canExecute && !dropCapabilityAvailable ? (
          <div role="note" className="mt-3 rounded-xl border border-grid-line/25 bg-terminal-bg/40 p-3">
            <p className="font-mono text-sm text-muted-foreground">{t('drop.snapshotRequired')}</p>
          </div>
        ) : null}

        {canExecute && dropCapabilityAvailable ? (
          <form className="mt-3 space-y-3" onSubmit={handleDropSubmit}>
            <p className="font-mono text-xs leading-5 text-muted-foreground">
              {t('drop.serviceIdentityRequirement')}
            </p>
            {executableServiceIdentityUuids.length > 0 ? (
              <label className="block font-mono text-sm text-foreground">
                {t('drop.serviceIdentitySelectLabel')}
                <select
                  value={selectedServiceIdentityUuid}
                  disabled={dropMutation.isPending || dropMutation.isSuccess || dropMutation.isError}
                  className="mt-2 h-10 w-full rounded-md border border-grid-line/30 bg-terminal-bg px-3 font-mono text-sm text-foreground outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan"
                  onChange={(event) => {
                    setSelectedServiceIdentityUuid(event.target.value);
                    setManualServiceIdentityUuid('');
                    setShowServiceIdentityError(false);
                  }}
                >
                  <option value="">{t('drop.serviceIdentitySelectPlaceholder')}</option>
                  {executableServiceIdentityUuids.map((serviceIdentityUuid) => (
                    <option key={serviceIdentityUuid} value={serviceIdentityUuid}>
                      {serviceIdentityUuid}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            <div>
              <label htmlFor={`partner-drop-service-identity-${nodeUuid}`} className="font-mono text-sm text-foreground">
                {t('drop.serviceIdentityUuidLabel')}
              </label>
              <input
                id={`partner-drop-service-identity-${nodeUuid}`}
                inputMode="text"
                autoComplete="off"
                autoCapitalize="none"
                spellCheck={false}
                maxLength={36}
                value={manualServiceIdentityUuid}
                disabled={dropMutation.isPending || dropMutation.isSuccess || dropMutation.isError}
                aria-invalid={showServiceIdentityError}
                aria-describedby={`partner-drop-service-identity-hint-${nodeUuid}${showServiceIdentityError ? ` partner-drop-service-identity-error-${nodeUuid}` : ''}`}
                className="mt-2 h-10 w-full rounded-md border border-grid-line/30 bg-terminal-bg px-3 font-mono text-sm text-foreground outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan"
                onChange={(event) => {
                  setManualServiceIdentityUuid(event.target.value);
                  setSelectedServiceIdentityUuid('');
                  setShowServiceIdentityError(false);
                }}
              />
              <p id={`partner-drop-service-identity-hint-${nodeUuid}`} className="mt-2 font-mono text-xs leading-5 text-muted-foreground">
                {t('drop.serviceIdentityManualHint')}
              </p>
              {showServiceIdentityError ? (
                <p id={`partner-drop-service-identity-error-${nodeUuid}`} role="alert" className="mt-2 font-mono text-xs text-neon-pink">
                  {t('drop.serviceIdentityUuidError')}
                </p>
              ) : null}
            </div>
            <Button
              type="submit"
              variant="destructive"
              disabled={dropMutation.isPending || dropMutation.isSuccess || dropMutation.isError}
            >
              <Unplug className="mr-2 h-4 w-4" aria-hidden="true" />
              {dropMutation.isPending ? t('drop.submitting') : t('drop.submit')}
            </Button>
          </form>
        ) : null}

        {dropMutation.isError ? (
          <div className="mt-3">
            {getHttpStatus(dropMutation.error) === null ? (
              <div role="alert" className="rounded-xl border border-amber-400/30 bg-amber-400/5 p-4">
                <p className="font-display text-base text-white">{t('drop.clientOutcomeUnknown.title')}</p>
                <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">
                  {t('drop.clientOutcomeUnknown.description')}
                </p>
              </div>
            ) : (
              <ConnectionErrorNotice error={dropMutation.error} />
            )}
            {canRetryDropSafely ? (
              <Button
                type="button"
                variant="outline"
                className="mt-3"
                onClick={() => {
                  if (dropAttempt) dropMutation.mutate(dropAttempt);
                }}
              >
                <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
                {t('drop.retrySameKey')}
              </Button>
            ) : null}
            {!canRetryDropSafely ? (
              <Button type="button" variant="outline" className="mt-3" onClick={resetDrop}>
                {t('drop.reset')}
              </Button>
            ) : null}
          </div>
        ) : null}

        {dropMutation.data?.state === 'accepted' ? (
          <div role="status" className="mt-3 rounded-xl border border-matrix-green/30 bg-matrix-green/5 p-4">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="mt-0.5 h-5 w-5 text-matrix-green" aria-hidden="true" />
              <div>
                <p className="font-display text-base text-white">{t('drop.accepted.title')}</p>
                <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">
                  {t('drop.accepted.description')}
                </p>
              </div>
            </div>
            <Button type="button" variant="outline" className="mt-3" onClick={resetDrop}>
              {t('drop.reset')}
            </Button>
          </div>
        ) : null}

        {dropMutation.data?.state === 'outcome_unknown' ? (
          <div role="alert" className="mt-3 rounded-xl border border-amber-400/30 bg-amber-400/5 p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 text-amber-300" aria-hidden="true" />
              <div>
                <p className="font-display text-base text-white">{t('drop.outcomeUnknown.title')}</p>
                <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">
                  {t('drop.outcomeUnknown.description')}
                </p>
              </div>
            </div>
          </div>
        ) : null}
      </div>

      <p className="mt-4 flex items-center gap-2 font-mono text-[11px] leading-5 text-muted-foreground">
        <Wifi className="h-3.5 w-3.5" aria-hidden="true" />
        {t('privacy')}
      </p>
    </section>
  );
}
