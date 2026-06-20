'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import {
  Archive,
  Ban,
  Copy,
  LinkIcon,
  Pause,
  Play,
  Plus,
  QrCode,
  Ticket,
  Waypoints,
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { partnerPortalApi } from '@/lib/api/partner-portal';
import { PartnerRouteGuard } from '@/features/partner-portal-state/components/partner-route-guard';
import type { PartnerRouteAccessLevel } from '@/features/partner-portal-state/lib/portal-access';
import {
  getPartnerCodeCapabilities,
  getPartnerCommercialSurfaceMode,
} from '@/features/partner-commercial/lib/commercial-capabilities';
import type { PartnerCode } from '@/features/partner-portal-state/lib/portal-state';
import { usePartnerPortalRuntimeState } from '@/features/partner-portal-state/lib/use-partner-portal-runtime-state';

function isWriteAccess(access: PartnerRouteAccessLevel) {
  return access === 'write' || access === 'admin';
}

function useWorkspaceInvalidation(workspaceId: string | null | undefined) {
  const queryClient = useQueryClient();
  return () => {
    if (!workspaceId) return;
    void queryClient.invalidateQueries({ queryKey: ['partner-portal', 'workspace-codes', workspaceId] });
    void queryClient.invalidateQueries({
      queryKey: ['partner-portal', 'workspace-commercial-capabilities', workspaceId],
    });
  };
}

function buildMutationReason(action: string) {
  return `partner_portal_${action}`;
}

export function CodesTrackingPage() {
  const t = useTranslations('Partner.codes');
  const portalT = useTranslations('Partner.portalState');
  const {
    state,
    activeWorkspace,
    queries: {
      workspaceCodesQuery,
      workspaceCommercialCapabilitiesQuery,
    },
  } = usePartnerPortalRuntimeState();
  const [newCode, setNewCode] = useState('');
  const [newDestinationPath, setNewDestinationPath] = useState('/register');
  const [deepLinkPathByCode, setDeepLinkPathByCode] = useState<Record<string, string>>({});
  const [generatedLinkByCode, setGeneratedLinkByCode] = useState<Record<string, string>>({});
  const [qrByCode, setQrByCode] = useState<Record<string, string>>({});
  const mode = getPartnerCommercialSurfaceMode('codes', state);
  const localCapabilities = getPartnerCodeCapabilities(state);
  const backendCapabilities = workspaceCommercialCapabilitiesQuery.data;
  const invalidateWorkspace = useWorkspaceInvalidation(activeWorkspace?.id);

  const canWrite = useMemo(
    () => Boolean(activeWorkspace?.id && backendCapabilities?.can_write_codes && mode !== 'read_only'),
    [activeWorkspace?.id, backendCapabilities?.can_write_codes, mode],
  );

  const createCodeMutation = useMutation({
    mutationFn: async () => {
      if (!activeWorkspace?.id) {
        throw new Error('workspace_not_selected');
      }
      return partnerPortalApi.createWorkspaceCode(
        activeWorkspace.id,
        {
          code: newCode.trim() || null,
          destination_path: newDestinationPath.trim() || null,
        },
        crypto.randomUUID(),
      );
    },
    onSuccess: () => {
      setNewCode('');
      invalidateWorkspace();
    },
  });

  const lifecycleMutation = useMutation({
    mutationFn: async ({
      code,
      action,
    }: {
      code: PartnerCode;
      action: 'activate' | 'pause' | 'revoke' | 'archive';
    }) => {
      if (!activeWorkspace?.id) {
        throw new Error('workspace_not_selected');
      }
      return partnerPortalApi.changeWorkspaceCodeLifecycle(
        activeWorkspace.id,
        code.id,
        action,
        { reason: buildMutationReason(action) },
        code.version,
      );
    },
    onSuccess: () => invalidateWorkspace(),
  });

  const linkMutation = useMutation({
    mutationFn: async (code: PartnerCode) => {
      if (!activeWorkspace?.id) {
        throw new Error('workspace_not_selected');
      }
      const destinationPath = deepLinkPathByCode[code.id]?.trim() || code.destinationPath || null;
      return partnerPortalApi.createWorkspaceCodeLink(activeWorkspace.id, code.id, {
        destination_path: destinationPath,
        campaign_params: {},
        sub_ids: {},
      });
    },
    onSuccess: (response, code) => {
      setGeneratedLinkByCode((current) => ({ ...current, [code.id]: response.data.share_url }));
      void navigator.clipboard?.writeText(response.data.share_url);
    },
  });

  const qrMutation = useMutation({
    mutationFn: async (code: PartnerCode) => {
      if (!activeWorkspace?.id) {
        throw new Error('workspace_not_selected');
      }
      return partnerPortalApi.createWorkspaceCodeQr(activeWorkspace.id, code.id, {
        destination_path: deepLinkPathByCode[code.id]?.trim() || code.destinationPath || null,
        size: 256,
      });
    },
    onSuccess: (response, code) => {
      setQrByCode((current) => ({ ...current, [code.id]: response.data.qr_svg }));
    },
  });

  const copyText = (value: string | undefined) => {
    if (!value) return;
    void navigator.clipboard?.writeText(value);
  };

  const codesErrorStatus = workspaceCodesQuery.error instanceof AxiosError
    ? workspaceCodesQuery.error.response?.status
    : null;

  return (
    <PartnerRouteGuard route="codes" title={t('title')}>
      {(access) => {
        const writeEnabled = canWrite && isWriteAccess(access);
        return (
          <section className="space-y-6">
            <header className="rounded-lg border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-[11px] font-mono uppercase tracking-[0.24em] text-neon-cyan/80">
                    {t('eyebrow')}
                  </p>
                  <h1 className="mt-2 text-2xl font-display tracking-[0.16em] text-white md:text-3xl">
                    {t('title')}
                  </h1>
                  <p className="mt-3 max-w-4xl text-sm font-mono leading-6 text-muted-foreground">
                    {t('subtitle')}
                  </p>
                </div>

                <div className="rounded-lg border border-grid-line/20 bg-terminal-surface/35 p-4 text-sm font-mono text-muted-foreground lg:w-[340px]">
                  <div className="flex items-center justify-between gap-3">
                    <span>{t('summary.currentLane')}</span>
                    <span className="text-foreground">
                      {state.primaryLane ? portalT(`laneLabels.${state.primaryLane}`) : portalT('noLane')}
                    </span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.routeAccess')}</span>
                    <span className="text-neon-cyan">{portalT(`routeAccess.${access}`)}</span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.surfaceMode')}</span>
                    <span className="text-foreground">{portalT(`commercialModes.${mode}`)}</span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.governance')}</span>
                    <span className="text-foreground">{portalT(`governanceStates.${state.governanceState}`)}</span>
                  </div>
                </div>
              </div>
            </header>

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
              <article className="rounded-lg border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
                <div className="flex items-center gap-3 border-b border-grid-line/20 pb-4">
                  <Ticket className="h-5 w-5 text-neon-cyan" />
                  <div>
                    <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                      {t('inventory.title')}
                    </h2>
                    <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                      {t('inventory.description')}
                    </p>
                  </div>
                </div>

                {workspaceCodesQuery.isLoading ? (
                  <p className="mt-5 rounded-lg border border-dashed border-grid-line/25 bg-terminal-surface/25 p-4 text-sm font-mono leading-6 text-muted-foreground">
                    {t('inventory.loading')}
                  </p>
                ) : workspaceCodesQuery.isError ? (
                  <p className="mt-5 rounded-lg border border-warning-amber/35 bg-warning-amber/10 p-4 text-sm font-mono leading-6 text-warning-amber">
                    {codesErrorStatus === 403
                      ? t('inventory.forbidden')
                      : codesErrorStatus === 404
                        ? t('inventory.notFound')
                        : t('inventory.networkError')}
                  </p>
                ) : (
                  <div className="mt-5 space-y-3">
                    {state.codes.length > 0 ? state.codes.map((code) => (
                      <article
                        key={code.id}
                        className="rounded-lg border border-grid-line/20 bg-terminal-surface/35 p-4"
                      >
                        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                          <div className="min-w-0">
                            <h3 className="break-words text-sm font-display uppercase tracking-[0.16em] text-white">
                              {code.label}
                            </h3>
                            <p className="mt-2 break-all text-sm font-mono leading-6 text-muted-foreground">
                              {t('inventory.destination', { value: code.destination })}
                            </p>
                            {generatedLinkByCode[code.id] ? (
                              <p className="mt-2 break-all text-xs font-mono leading-5 text-neon-cyan">
                                {generatedLinkByCode[code.id]}
                              </p>
                            ) : null}
                          </div>
                          <div className="shrink-0 text-left md:text-right">
                            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                              {portalT(`codeKinds.${code.kind}`)}
                            </p>
                            <p className="mt-2 text-xs font-mono text-muted-foreground">
                              {portalT(`codeStatuses.${code.status}`)}
                            </p>
                          </div>
                        </div>

                        <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
                          <label className="block">
                            <span className="text-[11px] font-mono uppercase tracking-[0.16em] text-muted-foreground">
                              {t('form.destinationPath')}
                            </span>
                            <input
                              value={deepLinkPathByCode[code.id] ?? code.destinationPath ?? '/register'}
                              onChange={(event) =>
                                setDeepLinkPathByCode((current) => ({
                                  ...current,
                                  [code.id]: event.target.value,
                                }))}
                              className="mt-2 min-h-10 w-full rounded-lg border border-grid-line/30 bg-black/30 px-3 py-2 font-mono text-sm text-foreground outline-hidden focus:border-neon-cyan"
                            />
                          </label>
                          <div className="flex flex-wrap gap-2">
                            <button
                              type="button"
                              onClick={() => copyText(code.shareUrl)}
                              className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-grid-line/30 text-neon-cyan transition hover:border-neon-cyan"
                              title={t('buttons.copy')}
                            >
                              <Copy className="h-4 w-4" />
                            </button>
                            <button
                              type="button"
                              onClick={() => linkMutation.mutate(code)}
                              disabled={!code.availableActions?.includes('create_link') || linkMutation.isPending}
                              className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-grid-line/30 text-neon-cyan transition hover:border-neon-cyan disabled:cursor-not-allowed disabled:opacity-45"
                              title={t('buttons.link')}
                            >
                              <LinkIcon className="h-4 w-4" />
                            </button>
                            <button
                              type="button"
                              onClick={() => qrMutation.mutate(code)}
                              disabled={!code.availableActions?.includes('download_qr') || qrMutation.isPending}
                              className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-grid-line/30 text-matrix-green transition hover:border-matrix-green disabled:cursor-not-allowed disabled:opacity-45"
                              title={t('buttons.qr')}
                            >
                              <QrCode className="h-4 w-4" />
                            </button>
                            {code.availableActions?.includes('activate') ? (
                              <button
                                type="button"
                                onClick={() => lifecycleMutation.mutate({ code, action: 'activate' })}
                                disabled={!writeEnabled || lifecycleMutation.isPending}
                                className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-grid-line/30 text-matrix-green transition hover:border-matrix-green disabled:cursor-not-allowed disabled:opacity-45"
                                title={t('buttons.activate')}
                              >
                                <Play className="h-4 w-4" />
                              </button>
                            ) : null}
                            {code.availableActions?.includes('pause') ? (
                              <button
                                type="button"
                                onClick={() => lifecycleMutation.mutate({ code, action: 'pause' })}
                                disabled={!writeEnabled || lifecycleMutation.isPending}
                                className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-grid-line/30 text-warning-amber transition hover:border-warning-amber disabled:cursor-not-allowed disabled:opacity-45"
                                title={t('buttons.pause')}
                              >
                                <Pause className="h-4 w-4" />
                              </button>
                            ) : null}
                            {code.availableActions?.includes('revoke') ? (
                              <button
                                type="button"
                                onClick={() => lifecycleMutation.mutate({ code, action: 'revoke' })}
                                disabled={!writeEnabled || lifecycleMutation.isPending}
                                className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-grid-line/30 text-warning-amber transition hover:border-warning-amber disabled:cursor-not-allowed disabled:opacity-45"
                                title={t('buttons.revoke')}
                              >
                                <Ban className="h-4 w-4" />
                              </button>
                            ) : null}
                            {code.availableActions?.includes('archive') ? (
                              <button
                                type="button"
                                onClick={() => lifecycleMutation.mutate({ code, action: 'archive' })}
                                disabled={!writeEnabled || lifecycleMutation.isPending}
                                className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-grid-line/30 text-muted-foreground transition hover:border-grid-line disabled:cursor-not-allowed disabled:opacity-45"
                                title={t('buttons.archive')}
                              >
                                <Archive className="h-4 w-4" />
                              </button>
                            ) : null}
                          </div>
                        </div>

                        {qrByCode[code.id] ? (
                          <div
                            className="mt-4 w-[160px] rounded-lg bg-white p-2"
                            dangerouslySetInnerHTML={{ __html: qrByCode[code.id] }}
                          />
                        ) : null}
                      </article>
                    )) : (
                      <p className="rounded-lg border border-dashed border-grid-line/25 bg-terminal-surface/25 p-4 text-sm font-mono leading-6 text-muted-foreground">
                        {t('inventory.empty')}
                      </p>
                    )}
                  </div>
                )}
              </article>

              <div className="space-y-6">
                <article className="rounded-lg border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <div className="flex items-center gap-3">
                    <Plus className="h-5 w-5 text-neon-cyan" />
                    <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                      {t('create.title')}
                    </h2>
                  </div>
                  <div className="mt-4 space-y-3">
                    <label className="block">
                      <span className="text-[11px] font-mono uppercase tracking-[0.16em] text-muted-foreground">
                        {t('form.code')}
                      </span>
                      <input
                        value={newCode}
                        onChange={(event) => setNewCode(event.target.value)}
                        placeholder={t('form.codePlaceholder')}
                        className="mt-2 min-h-10 w-full rounded-lg border border-grid-line/30 bg-black/30 px-3 py-2 font-mono text-sm text-foreground outline-hidden focus:border-neon-cyan"
                      />
                    </label>
                    <label className="block">
                      <span className="text-[11px] font-mono uppercase tracking-[0.16em] text-muted-foreground">
                        {t('form.destinationPath')}
                      </span>
                      <input
                        value={newDestinationPath}
                        onChange={(event) => setNewDestinationPath(event.target.value)}
                        className="mt-2 min-h-10 w-full rounded-lg border border-grid-line/30 bg-black/30 px-3 py-2 font-mono text-sm text-foreground outline-hidden focus:border-neon-cyan"
                      />
                    </label>
                    <button
                      type="button"
                      onClick={() => createCodeMutation.mutate()}
                      disabled={!writeEnabled || createCodeMutation.isPending}
                      className="inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-lg border border-neon-cyan/50 bg-neon-cyan/10 px-4 py-2 font-mono text-sm text-neon-cyan transition hover:bg-neon-cyan/15 disabled:cursor-not-allowed disabled:opacity-45"
                    >
                      <Plus className="h-4 w-4" />
                      {t('buttons.create')}
                    </button>
                  </div>
                </article>

                <article className="rounded-lg border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <div className="flex items-center gap-3">
                    <Waypoints className="h-5 w-5 text-neon-purple" />
                    <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                      {t('capabilities.title')}
                    </h2>
                  </div>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {t(`modes.${mode}`)}
                  </p>
                  <ul className="mt-4 space-y-3">
                    {localCapabilities.map((capability) => (
                      <li
                        key={capability.key}
                        className="flex items-center justify-between gap-3 rounded-lg border border-grid-line/20 bg-terminal-bg/55 px-4 py-3"
                      >
                        <span className="text-sm font-mono text-foreground/90">
                          {t(`capabilities.items.${capability.key}`)}
                        </span>
                        <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan">
                          {portalT(`capabilityAvailability.${capability.availability}`)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </article>

                <article className="rounded-lg border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('links.title')}
                  </h2>
                  <div className="mt-4 flex flex-col gap-3">
                    <Link href="/campaigns" className="text-sm font-mono text-neon-cyan underline underline-offset-4">
                      {t('links.campaigns')}
                    </Link>
                    <Link href="/compliance" className="text-sm font-mono text-neon-purple underline underline-offset-4">
                      {t('links.compliance')}
                    </Link>
                    <Link href="/programs" className="text-sm font-mono text-matrix-green underline underline-offset-4">
                      {t('links.programs')}
                    </Link>
                  </div>
                </article>
              </div>
            </div>
          </section>
        );
      }}
    </PartnerRouteGuard>
  );
}
