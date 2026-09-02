'use client';

import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { KeyRound, Plus, RefreshCw, ShieldAlert, Trash2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  adminRemnawaveStatusApi,
  REMNAWAVE_PARTNER_PERMISSION_KEYS,
  REMNAWAVE_RESOURCE_TYPES,
  type RemnawavePartnerPermissionKey,
  type RemnawaveResourceGrantCreate,
} from '@/lib/api/remnawave-status';
import { useAuthStore } from '@/stores/auth-store';
import { hasAdminPermission } from '@/shared/lib/admin-rbac';
import { InfrastructureEmptyState } from './empty-state';
import { InfrastructureStatusChip } from './infrastructure-status-chip';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

interface GrantFormState {
  workspaceId: string;
  resourceType: RemnawaveResourceGrantCreate['resource_type'];
  resourceUuid: string;
  permissionKeys: RemnawavePartnerPermissionKey[];
  reason: string;
}

const EMPTY_FORM: GrantFormState = {
  workspaceId: '',
  resourceType: 'node',
  resourceUuid: '',
  permissionKeys: [],
  reason: '',
};

function getHttpStatus(error: unknown): number | null {
  if (typeof error !== 'object' || error === null || !('response' in error)) return null;
  const response = (error as { response?: { status?: unknown } }).response;
  return typeof response?.status === 'number' ? response.status : null;
}

function shortId(value: string): string {
  return value.length > 18 ? `${value.slice(0, 8)}…${value.slice(-6)}` : value;
}

function formatDateTime(value: string): string {
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) return '—';
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(timestamp);
}

export function RemnawaveGrantsManager() {
  const t = useTranslations('Infrastructure.remnawave.grants');
  const queryClient = useQueryClient();
  const role = useAuthStore((state) => state.user?.role);
  const canManage = hasAdminPermission(role, 'manage_admins');
  const [includeRevoked, setIncludeRevoked] = useState(false);
  const [form, setForm] = useState<GrantFormState>(EMPTY_FORM);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [revokeGrantId, setRevokeGrantId] = useState<string | null>(null);
  const [revokeReason, setRevokeReason] = useState('');

  const grantsQuery = useQuery({
    queryKey: ['infrastructure', 'remnawave', 'resource-grants', { includeRevoked }],
    queryFn: async () =>
      (await adminRemnawaveStatusApi.listResourceGrants({
        include_revoked: includeRevoked,
      })).data,
    enabled: canManage,
    retry: false,
    staleTime: 15_000,
  });

  const invalidateGrants = async () => {
    await queryClient.invalidateQueries({
      queryKey: ['infrastructure', 'remnawave', 'resource-grants'],
    });
  };

  const createMutation = useMutation({
    mutationFn: (payload: RemnawaveResourceGrantCreate) =>
      adminRemnawaveStatusApi.createResourceGrant(payload),
    onSuccess: async () => {
      setForm(EMPTY_FORM);
      setFeedback(t('feedback.created'));
      await invalidateGrants();
    },
    onError: (error) => {
      setFeedback(getHttpStatus(error) === 409 ? t('feedback.conflict') : t('feedback.failed'));
    },
  });

  const revokeMutation = useMutation({
    mutationFn: ({ grantId, reason }: { grantId: string; reason: string }) =>
      adminRemnawaveStatusApi.revokeResourceGrant(grantId, { reason }),
    onSuccess: async () => {
      setRevokeGrantId(null);
      setRevokeReason('');
      setFeedback(t('feedback.revoked'));
      await invalidateGrants();
    },
    onError: (error) => {
      setFeedback(getHttpStatus(error) === 409 ? t('feedback.alreadyRevoked') : t('feedback.failed'));
    },
  });

  function togglePermission(permission: RemnawavePartnerPermissionKey) {
    setForm((current) => ({
      ...current,
      permissionKeys: current.permissionKeys.includes(permission)
        ? current.permissionKeys.filter((item) => item !== permission)
        : [...current.permissionKeys, permission],
    }));
  }

  function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    const workspaceId = form.workspaceId.trim();
    const resourceUuid = form.resourceUuid.trim();
    const reason = form.reason.trim();
    if (
      !UUID_PATTERN.test(workspaceId)
      || !UUID_PATTERN.test(resourceUuid)
      || form.permissionKeys.length === 0
      || reason.length < 5
    ) {
      setFeedback(t('feedback.validation'));
      return;
    }
    createMutation.mutate({
      workspace_id: workspaceId,
      resource_type: form.resourceType,
      resource_uuid: resourceUuid,
      permission_keys: form.permissionKeys,
      reason,
    });
  }

  function handleRevoke(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const reason = revokeReason.trim();
    if (!revokeGrantId || reason.length < 5) {
      setFeedback(t('feedback.validation'));
      return;
    }
    setFeedback(null);
    revokeMutation.mutate({ grantId: revokeGrantId, reason });
  }

  if (!canManage) {
    return (
      <section
        aria-labelledby="remnawave-grants-title"
        className="rounded-[1.5rem] border border-amber-400/25 bg-amber-400/5 p-5 md:p-6"
      >
        <div className="flex items-start gap-3">
          <ShieldAlert className="mt-1 h-5 w-5 text-amber-300" aria-hidden="true" />
          <div>
            <h2 id="remnawave-grants-title" className="font-display text-xl text-white">
              {t('title')}
            </h2>
            <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">
              {t('permissionDenied')}
            </p>
          </div>
        </div>
      </section>
    );
  }

  const grants = grantsQuery.data?.items ?? [];
  const isForbidden = getHttpStatus(grantsQuery.error) === 403;

  return (
    <section
      aria-labelledby="remnawave-grants-title"
      className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/70 p-5 md:p-6"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <KeyRound className="mt-1 h-5 w-5 text-neon-cyan" aria-hidden="true" />
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-neon-cyan/80">
              {t('eyebrow')}
            </p>
            <h2 id="remnawave-grants-title" className="mt-2 font-display text-xl text-white">
              {t('title')}
            </h2>
            <p className="mt-2 max-w-3xl font-mono text-sm leading-6 text-muted-foreground">
              {t('description')}
            </p>
          </div>
        </div>
        <Button
          magnetic={false}
          type="button"
          variant="outline"
          onClick={() => void grantsQuery.refetch()}
          disabled={grantsQuery.isFetching || isForbidden}
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${grantsQuery.isFetching ? 'animate-spin' : ''}`} aria-hidden="true" />
          {t('refresh')}
        </Button>
      </div>

      {feedback ? (
        <p role="status" aria-live="polite" className="mt-4 rounded-lg border border-grid-line/20 px-3 py-2 font-mono text-xs text-amber-100">
          {feedback}
        </p>
      ) : null}

      <div className="mt-6 grid gap-6 xl:grid-cols-12">
        <form onSubmit={handleCreate} className="grid gap-4 rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4 xl:col-span-4">
          <div>
            <h3 className="font-display text-lg text-white">{t('create.title')}</h3>
            <p className="mt-2 font-mono text-xs leading-5 text-muted-foreground">
              {t('create.description')}
            </p>
          </div>
          <label className="grid gap-2 font-mono text-xs text-muted-foreground">
            {t('fields.workspaceId')}
            <Input
              value={form.workspaceId}
              onChange={(event) => setForm((current) => ({ ...current, workspaceId: event.target.value }))}
              autoComplete="off"
              spellCheck={false}
              placeholder="00000000-0000-4000-8000-000000000000"
              required
            />
          </label>
          <label className="grid gap-2 font-mono text-xs text-muted-foreground">
            {t('fields.resourceType')}
            <select
              value={form.resourceType}
              onChange={(event) => setForm((current) => ({
                ...current,
                resourceType: event.target.value as RemnawaveResourceGrantCreate['resource_type'],
              }))}
              className="min-h-11 rounded-lg border border-grid-line/30 bg-terminal-bg/80 px-3 text-sm text-white outline-hidden focus:border-neon-cyan"
            >
              {REMNAWAVE_RESOURCE_TYPES.map((resourceType) => (
                <option key={resourceType} value={resourceType}>
                  {t(`resourceTypes.${resourceType}`)}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-2 font-mono text-xs text-muted-foreground">
            {t('fields.resourceUuid')}
            <Input
              value={form.resourceUuid}
              onChange={(event) => setForm((current) => ({ ...current, resourceUuid: event.target.value }))}
              autoComplete="off"
              spellCheck={false}
              placeholder="00000000-0000-4000-8000-000000000000"
              required
            />
          </label>
          <fieldset className="grid gap-2">
            <legend className="font-mono text-xs text-muted-foreground">
              {t('fields.permissions')}
            </legend>
            {REMNAWAVE_PARTNER_PERMISSION_KEYS.map((permission) => (
              <label key={permission} className="flex min-h-11 items-center gap-3 rounded-lg border border-grid-line/20 px-3 font-mono text-xs text-white">
                <input
                  type="checkbox"
                  checked={form.permissionKeys.includes(permission)}
                  onChange={() => togglePermission(permission)}
                  className="h-4 w-4 accent-cyan-400"
                />
                {t(`permissions.${permission}`)}
              </label>
            ))}
          </fieldset>
          <label className="grid gap-2 font-mono text-xs text-muted-foreground">
            {t('fields.reason')}
            <textarea
              value={form.reason}
              onChange={(event) => setForm((current) => ({ ...current, reason: event.target.value }))}
              minLength={5}
              maxLength={500}
              required
              className="min-h-24 rounded-lg border border-grid-line/30 bg-terminal-bg/80 px-3 py-2 text-sm text-white outline-hidden focus:border-neon-cyan"
            />
          </label>
          <Button magnetic={false} type="submit" disabled={createMutation.isPending}>
            <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
            {createMutation.isPending ? t('create.pending') : t('create.action')}
          </Button>
        </form>

        <div className="min-w-0 xl:col-span-8">
          <label className="mb-4 flex min-h-11 items-center gap-3 font-mono text-xs text-muted-foreground">
            <input
              type="checkbox"
              checked={includeRevoked}
              onChange={(event) => setIncludeRevoked(event.target.checked)}
              className="h-4 w-4 accent-cyan-400"
            />
            {t('includeRevoked')}
          </label>

          {grantsQuery.isPending ? (
            <div role="status" aria-live="polite" className="grid gap-3">
              <span className="sr-only">{t('loading')}</span>
              {Array.from({ length: 4 }, (_, index) => (
                <div key={index} aria-hidden="true" className="h-16 animate-pulse rounded-xl bg-terminal-surface/35" />
              ))}
            </div>
          ) : grantsQuery.isError ? (
            <div role="alert" className="rounded-xl border border-amber-400/30 bg-amber-400/5 p-4">
              <p className="font-mono text-sm text-amber-100">
                {isForbidden ? t('permissionDenied') : t('loadError')}
              </p>
              {!isForbidden ? (
                <Button magnetic={false} type="button" variant="outline" className="mt-3" onClick={() => void grantsQuery.refetch()}>
                  {t('retry')}
                </Button>
              ) : null}
            </div>
          ) : grants.length === 0 ? (
            <InfrastructureEmptyState label={t('empty')} />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <caption className="sr-only">{t('tableCaption')}</caption>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('columns.workspace')}</TableHead>
                    <TableHead>{t('columns.resource')}</TableHead>
                    <TableHead>{t('columns.permissions')}</TableHead>
                    <TableHead>{t('columns.status')}</TableHead>
                    <TableHead>{t('columns.grantedAt')}</TableHead>
                    <TableHead>{t('columns.actions')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {grants.map((grant) => (
                    <TableRow key={grant.id}>
                      <TableCell className="font-mono text-xs" title={grant.workspace_id}>
                        {shortId(grant.workspace_id)}
                      </TableCell>
                      <TableCell>
                        <p>{t(`resourceTypes.${grant.resource_type}`)}</p>
                        <p className="mt-1 font-mono text-xs text-muted-foreground" title={grant.resource_uuid}>
                          {shortId(grant.resource_uuid)}
                        </p>
                      </TableCell>
                      <TableCell>
                        <ul className="grid gap-1">
                          {grant.permission_keys.map((permission) => (
                            <li key={permission} className="font-mono text-xs">
                              {permission}
                            </li>
                          ))}
                        </ul>
                      </TableCell>
                      <TableCell>
                        <InfrastructureStatusChip
                          label={grant.revoked_at ? t('status.revoked') : t('status.active')}
                          tone={grant.revoked_at ? 'neutral' : 'success'}
                        />
                      </TableCell>
                      <TableCell>{formatDateTime(grant.granted_at)}</TableCell>
                      <TableCell>
                        {!grant.revoked_at ? (
                          <Button
                            magnetic={false}
                            type="button"
                            variant="outline"
                            onClick={() => {
                              setRevokeGrantId(grant.id);
                              setRevokeReason('');
                              setFeedback(null);
                            }}
                            disabled={revokeMutation.isPending}
                          >
                            <Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />
                            {t('revoke.selectAction')}
                          </Button>
                        ) : (
                          '—'
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {revokeGrantId ? (
            <form onSubmit={handleRevoke} className="mt-4 grid gap-3 rounded-xl border border-neon-pink/30 bg-neon-pink/5 p-4">
              <h3 className="font-display text-base text-white">{t('revoke.title')}</h3>
              <p className="font-mono text-xs text-muted-foreground">{t('revoke.description')}</p>
              <label className="grid gap-2 font-mono text-xs text-muted-foreground">
                {t('fields.reason')}
                <textarea
                  value={revokeReason}
                  onChange={(event) => setRevokeReason(event.target.value)}
                  minLength={5}
                  maxLength={500}
                  required
                  autoFocus
                  className="min-h-20 rounded-lg border border-grid-line/30 bg-terminal-bg/80 px-3 py-2 text-sm text-white outline-hidden focus:border-neon-pink"
                />
              </label>
              <div className="flex flex-wrap gap-2">
                <Button magnetic={false} type="submit" disabled={revokeMutation.isPending}>
                  {revokeMutation.isPending ? t('revoke.pending') : t('revoke.confirmAction')}
                </Button>
                <Button
                  magnetic={false}
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setRevokeGrantId(null);
                    setRevokeReason('');
                  }}
                  disabled={revokeMutation.isPending}
                >
                  {t('revoke.cancel')}
                </Button>
              </div>
            </form>
          ) : null}
        </div>
      </div>
    </section>
  );
}
