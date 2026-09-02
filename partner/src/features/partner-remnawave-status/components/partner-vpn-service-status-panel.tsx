'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, CheckCircle2, Eye, LockKeyhole, RefreshCw, ShieldAlert, Wifi } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { usePartnerWorkspaceSelection } from '@/features/partner-portal-state/lib/use-partner-workspace-selection';
import { partnerRemnawaveStatusApi } from '@/lib/api/remnawave-status';
import type { PartnerRemnawaveResourceType } from '@/lib/api/remnawave-status';
import { PartnerNodeConnectionsPanel } from './partner-node-connections-panel';
import { PartnerRemnawaveSafeMutationPanel } from './partner-remnawave-safe-mutation-panel';

const REQUIRED_PERMISSION = 'remnawave_read';
const WRITE_PERMISSION = 'remnawave_write';
const EXECUTE_PERMISSION = 'remnawave_execute';

function getHttpStatus(error: unknown): number | null {
  if (typeof error !== 'object' || error === null || !('response' in error)) {
    return null;
  }
  const response = (error as { response?: { status?: unknown } }).response;
  return typeof response?.status === 'number' ? response.status : null;
}

function CapabilityItem({
  available,
  label,
  unavailableLabel,
  availableLabel,
}: {
  available: boolean;
  label: string;
  unavailableLabel: string;
  availableLabel: string;
}) {
  const Icon = available ? CheckCircle2 : AlertTriangle;
  return (
    <li className="flex items-center justify-between gap-3 rounded-xl border border-grid-line/20 bg-black/20 px-4 py-3">
      <span className="font-mono text-sm text-foreground">{label}</span>
      <span
        className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-[11px] uppercase tracking-[0.16em] ${
          available
            ? 'border-matrix-green/30 bg-matrix-green/10 text-matrix-green'
            : 'border-amber-400/30 bg-amber-400/10 text-amber-200'
        }`}
      >
        <Icon className="h-3.5 w-3.5" aria-hidden="true" />
        {available ? availableLabel : unavailableLabel}
      </span>
    </li>
  );
}

export function PartnerVpnServiceStatusPanel() {
  const t = useTranslations('Dashboard.vpnServiceStatus');
  const [inventoryPage, setInventoryPage] = useState<{ workspaceId: string; offset: number } | null>(null);
  const [selectedResource, setSelectedResource] = useState<{
    workspaceId: string;
    resourceType: PartnerRemnawaveResourceType;
    resourceUuid: string;
  } | null>(null);
  const {
    activeWorkspace,
    activeWorkspaceId,
    isSwitching,
    workspacesQuery,
  } = usePartnerWorkspaceSelection();
  const permissionKeys = activeWorkspace?.current_permission_keys ?? [];
  const canRead = permissionKeys.includes(REQUIRED_PERMISSION);
  const roleCanWrite = permissionKeys.includes(WRITE_PERMISSION);
  const roleCanExecute = permissionKeys.includes(EXECUTE_PERMISSION);
  const inventoryOffset = inventoryPage?.workspaceId === activeWorkspaceId
    ? inventoryPage.offset
    : 0;

  const statusQuery = useQuery({
    queryKey: ['partner-remnawave-status', activeWorkspaceId],
    queryFn: () => {
      if (!activeWorkspaceId) {
        throw new Error('Partner workspace is required');
      }
      return partnerRemnawaveStatusApi.getWorkspaceStatus(activeWorkspaceId);
    },
    enabled: Boolean(activeWorkspaceId) && canRead,
    retry: false,
    staleTime: 30_000,
  });

  const resourcesQuery = useQuery({
    queryKey: ['partner-remnawave-resources', activeWorkspaceId, inventoryOffset],
    queryFn: () => {
      if (!activeWorkspaceId) {
        throw new Error('Partner workspace is required');
      }
      return partnerRemnawaveStatusApi.listWorkspaceResources(activeWorkspaceId, inventoryOffset);
    },
    enabled: Boolean(activeWorkspaceId) && canRead,
    retry: false,
    staleTime: 30_000,
  });

  const selectionMatchesWorkspace = selectedResource?.workspaceId === activeWorkspaceId;
  const selectedResourceQuery = useQuery({
    queryKey: [
      'partner-remnawave-resource',
      activeWorkspaceId,
      selectionMatchesWorkspace ? selectedResource.resourceType : null,
      selectionMatchesWorkspace ? selectedResource.resourceUuid : null,
    ],
    queryFn: () => {
      if (!activeWorkspaceId || !selectedResource || !selectionMatchesWorkspace) {
        throw new Error('Partner resource selection is required');
      }
      return partnerRemnawaveStatusApi.getWorkspaceResource(
        activeWorkspaceId,
        selectedResource.resourceType,
        selectedResource.resourceUuid,
      );
    },
    enabled: Boolean(activeWorkspaceId) && canRead && selectionMatchesWorkspace,
    retry: false,
  });

  const isForbidden = getHttpStatus(statusQuery.error) === 403;
  const statusMatchesWorkspace = statusQuery.data?.workspace_id === activeWorkspaceId;
  const hasStatusMismatch = statusQuery.data !== undefined && !statusMatchesWorkspace;
  const data = statusMatchesWorkspace ? statusQuery.data : undefined;
  const isLoading = workspacesQuery.isPending
    || isSwitching
    || (Boolean(activeWorkspaceId) && canRead && statusQuery.isPending);
  const executableServiceIdentityUuids = (resourcesQuery.data?.items ?? [])
    .filter((resource) => (
      resource.resource_type === 'service_identity'
      && resource.effective_permissions.includes(EXECUTE_PERMISSION)
    ))
    .map((resource) => resource.resource_uuid);

  return (
    <section
      aria-labelledby="partner-vpn-service-status-title"
      className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 md:p-6"
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan">
            <Wifi className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-neon-cyan/80">
              {t('eyebrow')}
            </p>
            <h2 id="partner-vpn-service-status-title" className="mt-1 font-display text-xl text-white">
              {t('title')}
            </h2>
            <p className="mt-2 max-w-3xl font-mono text-sm leading-6 text-muted-foreground">
              {t('description')}
            </p>
          </div>
        </div>
        <span className="inline-flex w-fit rounded-full border border-grid-line/25 bg-terminal-bg/50 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
          {t('scopedControls')}
        </span>
      </div>

      {isLoading ? (
        <div role="status" aria-live="polite" className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <span className="sr-only">{t('loading')}</span>
          {Array.from({ length: 4 }, (_, index) => (
            <div
              key={index}
              aria-hidden="true"
              className="h-20 animate-pulse rounded-xl border border-grid-line/20 bg-terminal-bg/40"
            />
          ))}
        </div>
      ) : null}

      {!isLoading && workspacesQuery.isError ? (
        <div role="alert" className="mt-5 rounded-xl border border-amber-400/30 bg-amber-400/5 p-4">
          <p className="font-display text-base text-white">{t('workspaceError.title')}</p>
          <p className="mt-2 font-mono text-sm text-muted-foreground">{t('workspaceError.description')}</p>
          <Button
            type="button"
            variant="outline"
            className="mt-3"
            onClick={() => {
              void workspacesQuery.refetch();
            }}
          >
            <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
            {t('retry')}
          </Button>
        </div>
      ) : null}

      {!isLoading && !workspacesQuery.isError && !activeWorkspaceId ? (
        <div className="mt-5 rounded-xl border border-dashed border-grid-line/30 bg-terminal-bg/40 p-6 text-center font-mono text-sm text-muted-foreground">
          {t('empty')}
        </div>
      ) : null}

      {!isLoading && activeWorkspaceId && !canRead ? (
        <div role="note" className="mt-5 flex items-start gap-3 rounded-xl border border-grid-line/25 bg-terminal-bg/40 p-4">
          <ShieldAlert className="mt-0.5 h-5 w-5 text-muted-foreground" aria-hidden="true" />
          <div>
            <p className="font-display text-base text-white">{t('permission.title')}</p>
            <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">
              {t('permission.description')}
            </p>
          </div>
        </div>
      ) : null}

      {!isLoading && canRead && isForbidden ? (
        <div role="alert" className="mt-5 rounded-xl border border-neon-pink/30 bg-neon-pink/5 p-4">
          <p className="font-display text-base text-white">{t('forbidden.title')}</p>
          <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">
            {t('forbidden.description')}
          </p>
        </div>
      ) : null}

      {!isLoading && canRead && (statusQuery.isError || hasStatusMismatch) && !isForbidden ? (
        <div role="alert" className="mt-5 rounded-xl border border-amber-400/30 bg-amber-400/5 p-4">
          <p className="font-display text-base text-white">{t('error.title')}</p>
          <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">
            {t('error.description')}
          </p>
          <Button
            type="button"
            variant="outline"
            className="mt-3"
            onClick={() => {
              void statusQuery.refetch();
            }}
          >
            <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
            {t('retry')}
          </Button>
        </div>
      ) : null}

      {data ? (
        <div className="mt-5 space-y-4" aria-live="polite">
          {data.degraded ? (
            <div role="status" className="flex items-start gap-3 rounded-xl border border-amber-400/30 bg-amber-400/5 p-4">
              <AlertTriangle className="mt-0.5 h-5 w-5 text-amber-300" aria-hidden="true" />
              <div>
                <p className="font-display text-base text-white">{t('degraded.title')}</p>
                <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">
                  {t('degraded.description')}
                </p>
              </div>
            </div>
          ) : null}

          <div className="grid gap-4 lg:grid-cols-[0.7fr_1.3fr]">
            <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/40 p-4">
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                {t('assignedResources')}
              </p>
              <p className="mt-2 font-display text-3xl text-white">{data.assigned_resources}</p>
              <p className="mt-2 font-mono text-xs leading-5 text-muted-foreground">
                {t('assignedResourcesHint')}
              </p>
            </div>
            <ul className="grid gap-3 sm:grid-cols-3" aria-label={t('capabilitiesLabel')}>
              <CapabilityItem
                label={t('capabilities.connections')}
                available={data.capabilities.connections}
                availableLabel={t('available')}
                unavailableLabel={t('unavailable')}
              />
              <CapabilityItem
                label={t('capabilities.usage')}
                available={data.capabilities.usage}
                availableLabel={t('available')}
                unavailableLabel={t('unavailable')}
              />
              <CapabilityItem
                label={t('capabilities.devices')}
                available={data.capabilities.devices}
                availableLabel={t('available')}
                unavailableLabel={t('unavailable')}
              />
            </ul>
          </div>
        </div>
      ) : null}

      {!isLoading && activeWorkspaceId && canRead && !isForbidden ? (
        <section aria-labelledby="partner-remnawave-resources-title" className="mt-6 border-t border-grid-line/20 pt-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h3 id="partner-remnawave-resources-title" className="font-display text-lg text-white">
                {t('resources.title')}
              </h3>
              <p className="mt-2 max-w-3xl font-mono text-sm leading-6 text-muted-foreground">
                {t('resources.description')}
              </p>
            </div>
            <span className="inline-flex w-fit items-center gap-2 rounded-full border border-neon-pink/30 bg-neon-pink/5 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-neon-pink">
              <LockKeyhole className="h-3.5 w-3.5" aria-hidden="true" />
              {t('resources.sshForbidden')}
            </span>
          </div>

          {resourcesQuery.isPending ? (
            <div role="status" className="mt-4 grid gap-3 md:grid-cols-2">
              <span className="sr-only">{t('resources.loading')}</span>
              <div aria-hidden="true" className="h-28 animate-pulse rounded-xl border border-grid-line/20 bg-terminal-bg/40" />
              <div aria-hidden="true" className="h-28 animate-pulse rounded-xl border border-grid-line/20 bg-terminal-bg/40" />
            </div>
          ) : null}

          {resourcesQuery.isError ? (
            <div role="alert" className="mt-4 rounded-xl border border-amber-400/30 bg-amber-400/5 p-4">
              <p className="font-display text-base text-white">{t('resources.error.title')}</p>
              <p className="mt-2 font-mono text-sm text-muted-foreground">{t('resources.error.description')}</p>
              <Button
                type="button"
                variant="outline"
                className="mt-3"
                onClick={() => {
                  void resourcesQuery.refetch();
                }}
              >
                <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
                {t('retry')}
              </Button>
            </div>
          ) : null}

          {resourcesQuery.data?.items.length === 0 ? (
            <div className="mt-4 rounded-xl border border-dashed border-grid-line/30 bg-terminal-bg/40 p-6 text-center font-mono text-sm text-muted-foreground">
              {t('resources.empty')}
            </div>
          ) : null}

          {resourcesQuery.data && resourcesQuery.data.items.length > 0 ? (
            <div className="mt-4 space-y-4">
              <ul className="grid gap-3 md:grid-cols-2" aria-label={t('resources.listLabel')}>
                {resourcesQuery.data.items.map((resource) => (
                  <li
                    key={`${resource.resource_type}:${resource.resource_uuid}`}
                    className="rounded-xl border border-grid-line/20 bg-terminal-bg/40 p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="font-display text-base text-white">
                          {t(`resources.types.${resource.resource_type}`)}
                        </p>
                        <code className="mt-2 block break-all font-mono text-xs text-muted-foreground">
                          {resource.resource_uuid}
                        </code>
                      </div>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => {
                          setSelectedResource({
                            workspaceId: resource.workspace_id,
                            resourceType: resource.resource_type,
                            resourceUuid: resource.resource_uuid,
                          });
                        }}
                      >
                        <Eye className="mr-2 h-4 w-4" aria-hidden="true" />
                        {t('resources.inspect')}
                      </Button>
                    </div>
                    <p className="mt-3 font-mono text-xs leading-5 text-muted-foreground">
                      {resource.safe_mutations.length > 0
                        ? t('resources.safeMutationsAvailable')
                        : t('resources.mutationsUnavailable')}
                    </p>
                  </li>
                ))}
              </ul>

              <div className="flex items-center justify-between gap-3">
                <Button
                  type="button"
                  variant="outline"
                  disabled={inventoryOffset === 0 || resourcesQuery.isFetching}
                  onClick={() => {
                    if (activeWorkspaceId) {
                      setInventoryPage({
                        workspaceId: activeWorkspaceId,
                        offset: Math.max(0, inventoryOffset - 50),
                      });
                    }
                  }}
                >
                  {t('resources.previous')}
                </Button>
                <p className="font-mono text-xs text-muted-foreground">
                  {t('resources.count', { count: resourcesQuery.data.total })}
                </p>
                <Button
                  type="button"
                  variant="outline"
                  disabled={resourcesQuery.data.next_offset == null || resourcesQuery.isFetching}
                  onClick={() => {
                    const nextOffset = resourcesQuery.data.next_offset;
                    if (activeWorkspaceId && typeof nextOffset === 'number') {
                      setInventoryPage({
                        workspaceId: activeWorkspaceId,
                        offset: nextOffset,
                      });
                    }
                  }}
                >
                  {t('resources.next')}
                </Button>
              </div>
            </div>
          ) : null}

          {selectionMatchesWorkspace && selectedResourceQuery.isPending ? (
            <p role="status" className="mt-4 font-mono text-sm text-muted-foreground">
              {t('resources.detailLoading')}
            </p>
          ) : null}

          {selectionMatchesWorkspace && selectedResourceQuery.isError ? (
            <div role="alert" className="mt-4 rounded-xl border border-amber-400/30 bg-amber-400/5 p-4">
              <p className="font-display text-base text-white">{t('resources.detailError.title')}</p>
              <p className="mt-2 font-mono text-sm text-muted-foreground">{t('resources.detailError.description')}</p>
            </div>
          ) : null}

          {selectedResourceQuery.data ? (
            <div className="mt-4 rounded-xl border border-neon-cyan/25 bg-neon-cyan/5 p-4" aria-live="polite">
              <p className="font-display text-base text-white">{t('resources.detailTitle')}</p>
              <p className="mt-2 font-mono text-sm text-muted-foreground">
                {t('resources.effectivePermissions', {
                  permissions: selectedResourceQuery.data.effective_permissions.join(', '),
                })}
              </p>
              <p className="mt-2 font-mono text-xs leading-5 text-muted-foreground">
                {t('resources.providerDetailsPrivate')}
              </p>
              <PartnerRemnawaveSafeMutationPanel
                key={`mutation:${selectedResourceQuery.data.workspace_id}:${selectedResourceQuery.data.resource_uuid}`}
                resource={selectedResourceQuery.data}
                roleCanWrite={roleCanWrite}
              />
              {selectedResourceQuery.data.resource_type === 'node' ? (
                <PartnerNodeConnectionsPanel
                  key={`${selectedResourceQuery.data.workspace_id}:${selectedResourceQuery.data.resource_uuid}`}
                  workspaceId={selectedResourceQuery.data.workspace_id}
                  nodeUuid={selectedResourceQuery.data.resource_uuid}
                  connectionsAvailable={Boolean(
                    data
                    && !statusQuery.isPending
                    && !statusQuery.isError
                    && !data.degraded
                    && data.capabilities.connections,
                  )}
                  roleCanExecute={roleCanExecute}
                  exactGrantCanExecute={selectedResourceQuery.data.effective_permissions.includes(
                    EXECUTE_PERMISSION,
                  )}
                  executableServiceIdentityUuids={executableServiceIdentityUuids}
                />
              ) : null}
            </div>
          ) : null}
        </section>
      ) : null}
    </section>
  );
}
