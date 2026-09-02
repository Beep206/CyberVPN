'use client';

import { useRef, useState, type FormEvent } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  CircleAlert,
  Network,
  RefreshCw,
  ServerCog,
  ShieldAlert,
  UserRoundSearch,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import {
  adminRemnawaveConnectionsApi,
  type AdminRemnawaveConnectionIp,
  type AdminRemnawaveConnectionDropRequest,
  type AdminRemnawaveNodeConnectionUser,
  type AdminRemnawaveNodeConnectionsStatus,
  type AdminRemnawaveUserConnectionNode,
  type AdminRemnawaveUserConnectionsStatus,
  type RemnawaveConnectionReadRequest,
  type RemnawaveConnectionsCapabilities,
} from '@/lib/api/remnawave-connections';
import { InfrastructurePageShell } from './infrastructure-page-shell';
import { RemnawaveConnectionReconciliationQueue } from './remnawave-connection-reconciliation-queue';

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const MAX_DROP_TARGETS = 1_000;

type ActiveUserLookup = {
  userId: number;
  request: RemnawaveConnectionReadRequest;
};

type ActiveNodeLookup = {
  nodeUuid: string;
  request: RemnawaveConnectionReadRequest;
};

type DropByMode = 'userIds' | 'ipAddresses';
type DropTargetMode = 'allNodes' | 'specificNodes';

function getErrorStatus(error: unknown): number | null {
  if (typeof error !== 'object' || error === null) return null;
  const response = (error as { response?: { status?: unknown } }).response;
  return typeof response?.status === 'number' ? response.status : null;
}

function errorMessageKey(error: unknown): string {
  const status = getErrorStatus(error);
  if (status === 403) return 'errors.forbidden';
  if (status === 404) return 'errors.expired';
  if (status === 409) return 'errors.conflict';
  if (status === 422) return 'errors.validation';
  if (status === 502) return 'errors.invalidProviderResponse';
  if (status === 503) return 'errors.unavailable';
  return 'errors.generic';
}

function splitCsv(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function isIpAddress(value: string): boolean {
  const octets = value.split('.');
  const isIpv4 = octets.length === 4 && octets.every((octet) => {
    if (!/^\d{1,3}$/.test(octet)) return false;
    const parsed = Number(octet);
    return parsed >= 0 && parsed <= 255;
  });
  if (isIpv4) return true;
  if (value.length > 45 || !/^[0-9a-f:]+$/i.test(value)) return false;

  const compressedParts = value.split('::');
  if (compressedParts.length > 2) return false;
  const groups = value.split(':').filter(Boolean);
  if (groups.some((group) => group.length > 4 || !/^[0-9a-f]+$/i.test(group))) {
    return false;
  }
  return compressedParts.length === 2 ? groups.length < 8 : groups.length === 8;
}

function parseDropPayload(
  dropByMode: DropByMode,
  dropValuesInput: string,
  targetMode: DropTargetMode,
  nodeUuidsInput: string,
): AdminRemnawaveConnectionDropRequest | null {
  const values = splitCsv(dropValuesInput);
  if (values.length === 0 || values.length > MAX_DROP_TARGETS) return null;

  let dropBy: AdminRemnawaveConnectionDropRequest['dropBy'];
  if (dropByMode === 'userIds') {
    const userIds = values.map(Number);
    if (userIds.some((value) => !Number.isSafeInteger(value) || value < 1)) return null;
    dropBy = { by: 'userIds', userIds };
  } else {
    if (values.some((value) => !isIpAddress(value))) return null;
    dropBy = { by: 'ipAddresses', ipAddresses: values };
  }

  if (targetMode === 'allNodes') {
    return { dropBy, targetNodes: { target: 'allNodes' } };
  }

  const nodeUuids = splitCsv(nodeUuidsInput);
  if (
    nodeUuids.length === 0
    || nodeUuids.length > 128
    || nodeUuids.some((value) => !UUID_PATTERN.test(value))
  ) {
    return null;
  }
  return {
    dropBy,
    targetNodes: {
      target: 'specificNodes',
      nodeUuids: nodeUuids.map((value) => value.toLowerCase()),
    },
  };
}

function StatusError({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry: () => void;
}) {
  const t = useTranslations('Infrastructure.remnawaveConnections');
  const forbidden = getErrorStatus(error) === 403;
  return (
    <div
      role="alert"
      className="rounded-xl border border-neon-pink/30 bg-neon-pink/5 p-4 font-mono text-sm text-neon-pink"
    >
      <p>{t(errorMessageKey(error))}</p>
      <button
        type="button"
        onClick={onRetry}
        disabled={forbidden}
        className="mt-3 inline-flex min-h-11 items-center rounded-lg border border-neon-pink/35 px-3 py-2 text-xs uppercase tracking-[0.12em] disabled:cursor-not-allowed disabled:opacity-45"
      >
        <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
        {t('actions.retryRead')}
      </button>
    </div>
  );
}

function formatConnectionTimestamp(value: string, locale: string): string {
  try {
    return new Intl.DateTimeFormat(locale, {
      dateStyle: 'medium',
      timeStyle: 'medium',
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function UserConnectionsResult({
  status,
}: {
  status: AdminRemnawaveUserConnectionsStatus;
}) {
  const t = useTranslations('Infrastructure.remnawaveConnections');
  const locale = useLocale();
  const rows: Array<{
    node: AdminRemnawaveUserConnectionNode;
    ip: AdminRemnawaveConnectionIp | null;
  }> = [];
  for (const node of status.result?.nodes ?? []) {
    if (node.ips.length === 0) rows.push({ node, ip: null });
    else for (const ip of node.ips) rows.push({ node, ip });
  }

  if (status.is_failed) {
    return <p role="alert" className="text-sm font-mono text-neon-pink">{t('states.jobFailed')}</p>;
  }
  if (!status.is_completed || status.result === null) {
    return (
      <p role="status" className="text-sm font-mono text-neon-cyan">
        {t('states.pollingProgress', { percent: Math.round(status.progress.percent) })}
      </p>
    );
  }
  if (rows.length === 0 || rows.every((row) => row.ip === null)) {
    return <p role="status" className="text-sm font-mono text-muted-foreground">{t('states.noUserConnections')}</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] border-separate border-spacing-y-2 text-left font-mono text-xs">
        <caption className="sr-only">{t('tables.userCaption')}</caption>
        <thead className="text-muted-foreground">
          <tr>
            <th scope="col" className="px-3 py-2">{t('tables.node')}</th>
            <th scope="col" className="px-3 py-2">{t('tables.country')}</th>
            <th scope="col" className="px-3 py-2">{t('tables.ip')}</th>
            <th scope="col" className="px-3 py-2">{t('tables.lastSeen')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ node, ip }, index) => (
            <tr key={`${node.node_uuid}:${ip?.ip ?? 'none'}:${index}`} className="bg-terminal-bg/45 text-foreground">
              <td className="rounded-l-xl px-3 py-3">
                <span className="block text-white">{node.node_name}</span>
                <span className="mt-1 block text-[10px] text-muted-foreground">{node.node_uuid}</span>
              </td>
              <td className="px-3 py-3">{node.country_code || '—'}</td>
              <td className="px-3 py-3 text-neon-cyan">{ip?.ip ?? '—'}</td>
              <td className="rounded-r-xl px-3 py-3">
                {ip ? formatConnectionTimestamp(ip.last_seen, locale) : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function NodeConnectionsResult({
  status,
}: {
  status: AdminRemnawaveNodeConnectionsStatus;
}) {
  const t = useTranslations('Infrastructure.remnawaveConnections');
  const locale = useLocale();
  const rows: Array<{
    user: AdminRemnawaveNodeConnectionUser;
    ip: AdminRemnawaveConnectionIp | null;
  }> = [];
  for (const user of status.result?.users ?? []) {
    if (user.ips.length === 0) rows.push({ user, ip: null });
    else for (const ip of user.ips) rows.push({ user, ip });
  }

  if (status.is_failed) {
    return <p role="alert" className="text-sm font-mono text-neon-pink">{t('states.jobFailed')}</p>;
  }
  if (!status.is_completed || status.result === null) {
    return <p role="status" className="text-sm font-mono text-neon-cyan">{t('states.polling')}</p>;
  }
  if (rows.length === 0 || rows.every((row) => row.ip === null)) {
    return <p role="status" className="text-sm font-mono text-muted-foreground">{t('states.noNodeConnections')}</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] border-separate border-spacing-y-2 text-left font-mono text-xs">
        <caption className="sr-only">{t('tables.nodeCaption')}</caption>
        <thead className="text-muted-foreground">
          <tr>
            <th scope="col" className="px-3 py-2">{t('tables.userId')}</th>
            <th scope="col" className="px-3 py-2">{t('tables.ip')}</th>
            <th scope="col" className="px-3 py-2">{t('tables.lastSeen')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ user, ip }, index) => (
            <tr key={`${user.user_id}:${ip?.ip ?? 'none'}:${index}`} className="bg-terminal-bg/45 text-foreground">
              <td className="rounded-l-xl px-3 py-3 text-white">{user.user_id}</td>
              <td className="px-3 py-3 text-neon-cyan">{ip?.ip ?? '—'}</td>
              <td className="rounded-r-xl px-3 py-3">
                {ip ? formatConnectionTimestamp(ip.last_seen, locale) : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function RemnawaveConnectionsConsole() {
  const t = useTranslations('Infrastructure.remnawaveConnections');
  const [userIdInput, setUserIdInput] = useState('');
  const [nodeUuidInput, setNodeUuidInput] = useState('');
  const [userValidationError, setUserValidationError] = useState(false);
  const [nodeValidationError, setNodeValidationError] = useState(false);
  const [activeUserLookup, setActiveUserLookup] = useState<ActiveUserLookup | null>(null);
  const [activeNodeLookup, setActiveNodeLookup] = useState<ActiveNodeLookup | null>(null);
  const [verifiedCapabilities, setVerifiedCapabilities] = useState<RemnawaveConnectionsCapabilities | null>(null);

  const userRequest = useMutation({
    mutationFn: (userId: number) => adminRemnawaveConnectionsApi.requestUserConnections(userId),
    onSuccess: (request, userId) => {
      setActiveUserLookup({ request, userId });
      setVerifiedCapabilities(request.capabilities);
    },
  });
  const nodeRequest = useMutation({
    mutationFn: (nodeUuid: string) => adminRemnawaveConnectionsApi.requestNodeConnections(nodeUuid),
    onSuccess: (request, nodeUuid) => {
      setActiveNodeLookup({ request, nodeUuid });
      setVerifiedCapabilities(request.capabilities);
    },
  });

  const userStatus = useQuery({
    queryKey: [
      'infrastructure',
      'remnawave',
      'connections',
      'user',
      activeUserLookup?.userId,
      activeUserLookup?.request.request_id,
    ],
    queryFn: () => {
      if (!activeUserLookup) throw new Error('User connection lookup is not active');
      return adminRemnawaveConnectionsApi.getUserConnections(
        activeUserLookup.userId,
        activeUserLookup.request.request_id,
      );
    },
    enabled: activeUserLookup !== null,
    retry: false,
    refetchInterval: (query) => {
      if (query.state.status === 'error') return false;
      const status = query.state.data;
      if (status?.is_completed || status?.is_failed) return false;
      return (activeUserLookup?.request.poll_after_seconds ?? 1) * 1_000;
    },
  });

  const nodeStatus = useQuery({
    queryKey: [
      'infrastructure',
      'remnawave',
      'connections',
      'node',
      activeNodeLookup?.nodeUuid,
      activeNodeLookup?.request.request_id,
    ],
    queryFn: () => {
      if (!activeNodeLookup) throw new Error('Node connection lookup is not active');
      return adminRemnawaveConnectionsApi.getNodeConnections(
        activeNodeLookup.nodeUuid,
        activeNodeLookup.request.request_id,
      );
    },
    enabled: activeNodeLookup !== null,
    retry: false,
    refetchInterval: (query) => {
      if (query.state.status === 'error') return false;
      const status = query.state.data;
      if (status?.is_completed || status?.is_failed) return false;
      return (activeNodeLookup?.request.poll_after_seconds ?? 1) * 1_000;
    },
  });

  function runUserLookup() {
    const userId = Number(userIdInput.trim());
    const valid = Number.isSafeInteger(userId) && userId > 0;
    setUserValidationError(!valid);
    if (!valid) return;
    setActiveUserLookup(null);
    userRequest.mutate(userId);
  }

  function submitUserLookup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    runUserLookup();
  }

  function runNodeLookup() {
    const nodeUuid = nodeUuidInput.trim().toLowerCase();
    const valid = UUID_PATTERN.test(nodeUuid);
    setNodeValidationError(!valid);
    if (!valid) return;
    setActiveNodeLookup(null);
    nodeRequest.mutate(nodeUuid);
  }

  function submitNodeLookup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    runNodeLookup();
  }

  const [dropByMode, setDropByMode] = useState<DropByMode>('userIds');
  const [dropValuesInput, setDropValuesInput] = useState('');
  const [dropTargetMode, setDropTargetMode] = useState<DropTargetMode>('allNodes');
  const [dropNodeUuidsInput, setDropNodeUuidsInput] = useState('');
  const [dropConfirmed, setDropConfirmed] = useState(false);
  const [dropValidationError, setDropValidationError] = useState(false);
  const [dropAlreadyAttempted, setDropAlreadyAttempted] = useState(false);
  const idempotencyKeysRef = useRef(new Map<string, string>());
  const attemptedDropSignaturesRef = useRef(new Set<string>());

  const dropMutation = useMutation({
    mutationFn: ({
      payload,
      idempotencyKey,
    }: {
      payload: AdminRemnawaveConnectionDropRequest;
      idempotencyKey: string;
    }) => adminRemnawaveConnectionsApi.dropConnections(payload, idempotencyKey),
    retry: false,
  });

  const dropAvailable = Boolean(
    verifiedCapabilities?.drop_connections
    && verifiedCapabilities.drop_requires_idempotency_key,
  );

  function resetDropOutcome() {
    dropMutation.reset();
    setDropConfirmed(false);
    setDropValidationError(false);
    setDropAlreadyAttempted(false);
  }

  function submitDrop(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = parseDropPayload(
      dropByMode,
      dropValuesInput,
      dropTargetMode,
      dropNodeUuidsInput,
    );
    if (!dropAvailable || !dropConfirmed || payload === null) {
      setDropValidationError(true);
      return;
    }

    const signature = JSON.stringify(payload);
    if (attemptedDropSignaturesRef.current.has(signature)) {
      setDropAlreadyAttempted(true);
      return;
    }
    let idempotencyKey = idempotencyKeysRef.current.get(signature);
    if (!idempotencyKey) {
      idempotencyKey = `connections-drop:${globalThis.crypto.randomUUID()}`;
      idempotencyKeysRef.current.set(signature, idempotencyKey);
    }
    attemptedDropSignaturesRef.current.add(signature);
    setDropValidationError(false);
    setDropAlreadyAttempted(false);
    dropMutation.mutate({
      payload,
      idempotencyKey,
    });
  }

  const canRetryDropWithSameKey = Boolean(
    dropMutation.error
    && dropMutation.variables
    && (getErrorStatus(dropMutation.error) === 503 || getErrorStatus(dropMutation.error) === null),
  );

  function retryDropWithSameKey() {
    if (!dropMutation.variables || !canRetryDropWithSameKey) return;
    dropMutation.mutate(dropMutation.variables);
  }

  const sectionClass = 'rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/70 p-5 md:p-6';
  const inputClass = 'mt-2 min-h-11 w-full rounded-xl border border-grid-line/30 bg-terminal-surface/70 px-3 py-2 font-mono text-sm text-white outline-none focus:border-neon-cyan focus-visible:ring-2 focus-visible:ring-neon-cyan/30';
  const actionClass = 'inline-flex min-h-11 items-center justify-center rounded-xl border border-neon-cyan/40 bg-neon-cyan/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.12em] text-neon-cyan transition-colors hover:bg-neon-cyan/15 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-neon-cyan disabled:cursor-not-allowed disabled:opacity-45';

  return (
    <InfrastructurePageShell
      eyebrow={t('eyebrow')}
      title={t('title')}
      description={t('description')}
      icon={Network}
    >
      <div className="grid gap-6 xl:grid-cols-2">
        <section className={sectionClass} aria-labelledby="remnawave-user-connections-title">
          <div className="flex items-start gap-3">
            <UserRoundSearch className="mt-1 h-5 w-5 text-neon-cyan" aria-hidden="true" />
            <div>
              <h2 id="remnawave-user-connections-title" className="font-display text-xl text-white">{t('user.title')}</h2>
              <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">{t('user.description')}</p>
            </div>
          </div>
          <form className="mt-5" onSubmit={submitUserLookup} noValidate>
            <label htmlFor="remnawave-user-id" className="font-mono text-xs uppercase tracking-[0.12em] text-muted-foreground">
              {t('user.label')}
            </label>
            <input
              id="remnawave-user-id"
              inputMode="numeric"
              autoComplete="off"
              value={userIdInput}
              onChange={(event) => {
                setUserIdInput(event.target.value);
                setUserValidationError(false);
              }}
              aria-invalid={userValidationError}
              aria-describedby={userValidationError ? 'remnawave-user-id-error' : undefined}
              className={inputClass}
              placeholder={t('user.placeholder')}
            />
            {userValidationError ? <p id="remnawave-user-id-error" role="alert" className="mt-2 font-mono text-xs text-neon-pink">{t('user.validation')}</p> : null}
            <button type="submit" disabled={userRequest.isPending} className={`${actionClass} mt-4`}>
              {userRequest.isPending ? t('states.requesting') : t('actions.inspectUser')}
            </button>
          </form>
          <div className="mt-5" aria-live="polite">
            {userRequest.error ? <StatusError error={userRequest.error} onRetry={runUserLookup} /> : activeUserLookup === null ? <p role="status" className="font-mono text-sm text-muted-foreground">{t('states.userEmpty')}</p> : userStatus.error ? <StatusError error={userStatus.error} onRetry={() => void userStatus.refetch()} /> : userStatus.data ? <UserConnectionsResult status={userStatus.data} /> : <p role="status" className="font-mono text-sm text-neon-cyan">{t('states.polling')}</p>}
          </div>
        </section>

        <section className={sectionClass} aria-labelledby="remnawave-node-connections-title">
          <div className="flex items-start gap-3">
            <ServerCog className="mt-1 h-5 w-5 text-neon-cyan" aria-hidden="true" />
            <div>
              <h2 id="remnawave-node-connections-title" className="font-display text-xl text-white">{t('node.title')}</h2>
              <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">{t('node.description')}</p>
            </div>
          </div>
          <form className="mt-5" onSubmit={submitNodeLookup} noValidate>
            <label htmlFor="remnawave-node-uuid" className="font-mono text-xs uppercase tracking-[0.12em] text-muted-foreground">
              {t('node.label')}
            </label>
            <input
              id="remnawave-node-uuid"
              autoComplete="off"
              value={nodeUuidInput}
              onChange={(event) => {
                setNodeUuidInput(event.target.value);
                setNodeValidationError(false);
              }}
              aria-invalid={nodeValidationError}
              aria-describedby={nodeValidationError ? 'remnawave-node-uuid-error' : undefined}
              className={inputClass}
              placeholder={t('node.placeholder')}
            />
            {nodeValidationError ? <p id="remnawave-node-uuid-error" role="alert" className="mt-2 font-mono text-xs text-neon-pink">{t('node.validation')}</p> : null}
            <button type="submit" disabled={nodeRequest.isPending} className={`${actionClass} mt-4`}>
              {nodeRequest.isPending ? t('states.requesting') : t('actions.inspectNode')}
            </button>
          </form>
          <div className="mt-5" aria-live="polite">
            {nodeRequest.error ? <StatusError error={nodeRequest.error} onRetry={runNodeLookup} /> : activeNodeLookup === null ? <p role="status" className="font-mono text-sm text-muted-foreground">{t('states.nodeEmpty')}</p> : nodeStatus.error ? <StatusError error={nodeStatus.error} onRetry={() => void nodeStatus.refetch()} /> : nodeStatus.data ? <NodeConnectionsResult status={nodeStatus.data} /> : <p role="status" className="font-mono text-sm text-neon-cyan">{t('states.polling')}</p>}
          </div>
        </section>
      </div>

      <section className={sectionClass} aria-labelledby="remnawave-drop-connections-title">
        <div className="flex items-start gap-3">
          <ShieldAlert className="mt-1 h-5 w-5 text-amber-300" aria-hidden="true" />
          <div>
            <h2 id="remnawave-drop-connections-title" className="font-display text-xl text-white">{t('drop.title')}</h2>
            <p className="mt-2 max-w-4xl font-mono text-sm leading-6 text-muted-foreground">{t('drop.description')}</p>
          </div>
        </div>

        {!dropAvailable ? (
          <div role="status" className="mt-5 flex items-start gap-3 rounded-xl border border-amber-300/25 bg-amber-300/5 p-4 font-mono text-sm text-amber-200">
            <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <p>{verifiedCapabilities === null ? t('drop.capabilityUnverified') : t('drop.capabilityUnavailable')}</p>
          </div>
        ) : (
          <form className="mt-5 space-y-5" onSubmit={submitDrop} noValidate>
            <div className="grid gap-4 lg:grid-cols-2">
              <label className="font-mono text-xs uppercase tracking-[0.12em] text-muted-foreground">
                {t('drop.byLabel')}
                <select
                  value={dropByMode}
                  onChange={(event) => {
                    setDropByMode(event.target.value as DropByMode);
                    resetDropOutcome();
                  }}
                  className={inputClass}
                >
                  <option value="userIds">{t('drop.byUserIds')}</option>
                  <option value="ipAddresses">{t('drop.byIpAddresses')}</option>
                </select>
              </label>
              <div>
                <label htmlFor="remnawave-drop-values" className="font-mono text-xs uppercase tracking-[0.12em] text-muted-foreground">
                  {dropByMode === 'userIds' ? t('drop.userIdsLabel') : t('drop.ipAddressesLabel')}
                </label>
                <input
                  id="remnawave-drop-values"
                  value={dropValuesInput}
                  onChange={(event) => {
                    setDropValuesInput(event.target.value);
                    resetDropOutcome();
                  }}
                  className={inputClass}
                  autoComplete="off"
                  aria-invalid={dropValidationError}
                  aria-describedby={
                    dropValidationError
                      ? 'remnawave-drop-values-help remnawave-drop-error'
                      : 'remnawave-drop-values-help'
                  }
                />
                <p id="remnawave-drop-values-help" className="mt-2 font-mono text-xs text-muted-foreground">{t('drop.commaSeparated')}</p>
              </div>
              <label className="font-mono text-xs uppercase tracking-[0.12em] text-muted-foreground">
                {t('drop.targetLabel')}
                <select
                  value={dropTargetMode}
                  onChange={(event) => {
                    setDropTargetMode(event.target.value as DropTargetMode);
                    resetDropOutcome();
                  }}
                  className={inputClass}
                >
                  <option value="allNodes">{t('drop.allNodes')}</option>
                  <option value="specificNodes">{t('drop.specificNodes')}</option>
                </select>
              </label>
              {dropTargetMode === 'specificNodes' ? (
                <label className="font-mono text-xs uppercase tracking-[0.12em] text-muted-foreground">
                  {t('drop.nodeUuidsLabel')}
                  <input
                    value={dropNodeUuidsInput}
                    onChange={(event) => {
                      setDropNodeUuidsInput(event.target.value);
                      resetDropOutcome();
                    }}
                    className={inputClass}
                    autoComplete="off"
                    aria-invalid={dropValidationError}
                    aria-describedby={dropValidationError ? 'remnawave-drop-error' : undefined}
                  />
                </label>
              ) : null}
            </div>

            <label className="flex items-start gap-3 rounded-xl border border-amber-300/25 bg-amber-300/5 p-4 font-mono text-sm text-amber-100">
              <input
                type="checkbox"
                checked={dropConfirmed}
                onChange={(event) => setDropConfirmed(event.target.checked)}
                className="mt-1 h-4 w-4 accent-cyan-400"
                aria-describedby={dropValidationError ? 'remnawave-drop-error' : undefined}
              />
              <span>{t('drop.confirm')}</span>
            </label>

            {dropValidationError ? <p id="remnawave-drop-error" role="alert" className="font-mono text-sm text-neon-pink">{t('drop.validation')}</p> : null}
            {dropAlreadyAttempted ? <p role="alert" className="font-mono text-sm text-neon-pink">{t('drop.alreadyAttempted')}</p> : null}
            {dropMutation.error ? (
              <div role="alert" className="space-y-3 font-mono text-sm text-neon-pink">
                <p>{t(errorMessageKey(dropMutation.error))} {t('drop.noBlindRetry')}</p>
                {canRetryDropWithSameKey ? (
                  <button
                    type="button"
                    onClick={retryDropWithSameKey}
                    disabled={dropMutation.isPending}
                    className="inline-flex min-h-11 items-center rounded-xl border border-amber-300/35 bg-amber-300/5 px-4 py-2 text-xs uppercase tracking-[0.12em] text-amber-100 transition-colors hover:bg-amber-300/10 disabled:cursor-not-allowed disabled:opacity-45"
                  >
                    <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
                    {t('drop.retrySameKey')}
                  </button>
                ) : null}
              </div>
            ) : null}
            {dropMutation.data ? (
              <div role="status" className="rounded-xl border border-matrix-green/30 bg-matrix-green/5 p-4 font-mono text-sm text-matrix-green">
                <p>{t(`drop.receipt.${dropMutation.data.state}`)}</p>
                <p className="mt-2 break-all text-xs text-muted-foreground">{t('drop.receiptId', { receiptId: dropMutation.data.receipt_id })}</p>
                <p className="mt-2 text-xs text-amber-100">{t('drop.noBlindRetry')}</p>
              </div>
            ) : null}

            {verifiedCapabilities?.drop_outcome_may_be_unknown ? <p className="font-mono text-xs text-amber-200">{t('drop.outcomeWarning')}</p> : null}
            <button type="submit" disabled={dropMutation.isPending || Boolean(dropMutation.data) || Boolean(dropMutation.error)} className={actionClass}>
              {dropMutation.isPending ? t('drop.pending') : t('drop.action')}
            </button>
          </form>
        )}
      </section>
      <RemnawaveConnectionReconciliationQueue />
    </InfrastructurePageShell>
  );
}
