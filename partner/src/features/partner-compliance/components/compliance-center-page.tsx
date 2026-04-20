'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Shield, TriangleAlert } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Link } from '@/i18n/navigation';
import { PartnerRouteGuard } from '@/features/partner-portal-state/components/partner-route-guard';
import { usePartnerPortalRuntimeState } from '@/features/partner-portal-state/lib/use-partner-portal-runtime-state';
import type { PartnerRouteAccessLevel } from '@/features/partner-portal-state/lib/portal-access';
import {
  getPartnerCommercialSurfaceMode,
  getPartnerComplianceCapabilities,
} from '@/features/partner-commercial/lib/commercial-capabilities';
import { partnerPortalApi } from '@/lib/api/partner-portal';
import { getComplianceRestrictionReasons } from '@/features/partner-compliance/lib/compliance-runtime';

function isWriteAccess(access: PartnerRouteAccessLevel) {
  return access === 'write' || access === 'admin';
}

function formatDateTime(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export function ComplianceCenterPage() {
  const locale = useLocale();
  const t = useTranslations('Partner.compliance');
  const portalT = useTranslations('Partner.portalState');
  const queryClient = useQueryClient();
  const { state, activeWorkspace, blockedReasons } = usePartnerPortalRuntimeState();
  const mode = getPartnerCommercialSurfaceMode('compliance', state);
  const capabilities = getPartnerComplianceCapabilities(state);
  const restrictionReasons = useMemo(
    () => getComplianceRestrictionReasons(blockedReasons),
    [blockedReasons],
  );
  const [trafficForm, setTrafficForm] = useState({
    declarationKind: 'approved_sources' as 'approved_sources' | 'postback_readiness',
    scopeLabel: '',
    details: '',
  });
  const [creativeForm, setCreativeForm] = useState({
    scopeLabel: '',
    creativeRef: '',
    details: '',
  });
  const [actionFeedback, setActionFeedback] = useState<{
    tone: 'success' | 'error';
    message: string;
  } | null>(null);

  const activeWorkspaceId = activeWorkspace?.id ?? null;
  const canSubmitActions = Boolean(activeWorkspaceId);

  async function invalidateComplianceQueries(workspaceId: string) {
    await queryClient.invalidateQueries({
      queryKey: ['partner-portal', 'workspace-traffic-declarations', workspaceId],
    });
    await queryClient.invalidateQueries({
      queryKey: ['partner-portal', 'workspace-campaign-assets', workspaceId],
    });
    await queryClient.invalidateQueries({
      queryKey: ['partner-portal', 'workspace-review-requests', workspaceId],
    });
    await queryClient.invalidateQueries({
      queryKey: ['partner-portal', 'workspace-cases', workspaceId],
    });
    await queryClient.invalidateQueries({
      queryKey: ['partner-portal', 'session-bootstrap'],
    });
  }

  const trafficDeclarationMutation = useMutation({
    mutationFn: async () => {
      if (!activeWorkspaceId) {
        throw new Error(t('actions.workspaceRequired'));
      }
      const details = trafficForm.details.trim();
      return partnerPortalApi.submitWorkspaceTrafficDeclaration(activeWorkspaceId, {
        declaration_kind: trafficForm.declarationKind,
        scope_label: trafficForm.scopeLabel.trim(),
        declaration_payload: { summary: details },
        notes: [details],
      });
    },
    onSuccess: async () => {
      if (activeWorkspaceId) {
        await invalidateComplianceQueries(activeWorkspaceId);
      }
      setTrafficForm({
        declarationKind: 'approved_sources',
        scopeLabel: '',
        details: '',
      });
      setActionFeedback({
        tone: 'success',
        message: t('actions.traffic.success'),
      });
    },
    onError: (error) => {
      setActionFeedback({
        tone: 'error',
        message: error instanceof Error ? error.message : t('actions.errorFallback'),
      });
    },
  });

  const creativeApprovalMutation = useMutation({
    mutationFn: async () => {
      if (!activeWorkspaceId) {
        throw new Error(t('actions.workspaceRequired'));
      }
      const details = creativeForm.details.trim();
      return partnerPortalApi.submitWorkspaceCreativeApproval(activeWorkspaceId, {
        scope_label: creativeForm.scopeLabel.trim(),
        creative_ref: creativeForm.creativeRef.trim() || null,
        approval_payload: { summary: details },
        notes: [details],
      });
    },
    onSuccess: async () => {
      if (activeWorkspaceId) {
        await invalidateComplianceQueries(activeWorkspaceId);
      }
      setCreativeForm({
        scopeLabel: '',
        creativeRef: '',
        details: '',
      });
      setActionFeedback({
        tone: 'success',
        message: t('actions.creative.success'),
      });
    },
    onError: (error) => {
      setActionFeedback({
        tone: 'error',
        message: error instanceof Error ? error.message : t('actions.errorFallback'),
      });
    },
  });

  return (
    <PartnerRouteGuard route="compliance" title={t('title')}>
      {(access) => (
        <section className="space-y-6">
          <header className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
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

              <div className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-4 text-sm font-mono text-muted-foreground lg:w-[360px]">
                <div className="flex items-center justify-between gap-3">
                  <span>{t('summary.currentLane')}</span>
                  <span className="text-foreground">
                    {state.primaryLane
                      ? portalT(`laneLabels.${state.primaryLane}`)
                      : portalT('noLane')}
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <span>{t('summary.routeAccess')}</span>
                  <span className="text-neon-cyan">
                    {portalT(`routeAccess.${access}`)}
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <span>{t('summary.surfaceMode')}</span>
                  <span className="text-foreground">
                    {portalT(`commercialModes.${mode}`)}
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <span>{t('summary.compliance')}</span>
                  <span className="text-foreground">
                    {portalT(`complianceStates.${state.complianceReadiness}`)}
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <span>{t('summary.governance')}</span>
                  <span className="text-foreground">
                    {portalT(`governanceStates.${state.governanceState}`)}
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <span>{t('summary.restrictions')}</span>
                  <span className="text-foreground">{restrictionReasons.length}</span>
                </div>
              </div>
            </div>
          </header>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
            <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
              <div className="flex items-center gap-3 border-b border-grid-line/20 pb-4">
                <Shield className="h-5 w-5 text-neon-cyan" />
                <div>
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('tasks.title')}
                  </h2>
                  <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                    {t('tasks.description')}
                  </p>
                </div>
              </div>

              {restrictionReasons.length > 0 ? (
                <article className="mt-5 rounded-2xl border border-neon-pink/25 bg-neon-pink/10 p-4 shadow-[0_0_24px_rgba(255,0,255,0.08)]">
                  <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                    {t('restrictions.title')}
                  </h3>
                  <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                    {t('restrictions.description')}
                  </p>
                  <ul className="mt-4 space-y-3">
                    {restrictionReasons.map((reason) => (
                      (() => {
                        const reasonNotes = (reason.notes?.length ?? 0) > 0
                          ? reason.notes ?? []
                          : [t('restrictions.fallbackNote')];

                        return (
                          <li
                            key={`${reason.route_slug ?? 'route'}:${reason.code}`}
                            className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-3"
                          >
                            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-pink">
                              {reason.code}
                            </p>
                            <ul className="mt-2 space-y-2 text-sm font-mono leading-6 text-muted-foreground">
                              {reasonNotes.map((note: string) => (
                                <li key={`${reason.code}:${note}`}>{note}</li>
                              ))}
                            </ul>
                          </li>
                        );
                      })()
                    ))}
                  </ul>
                </article>
              ) : null}

              <div className="mt-5 space-y-3">
                {state.complianceTasks.length > 0 ? state.complianceTasks.map((task) => (
                  <article
                    key={task.id}
                    className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4"
                  >
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                          {portalT(`complianceTaskKinds.${task.kind}`)}
                        </h3>
                        <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                          {t('tasks.ownerRole', { value: portalT(`workspaceRoles.${task.ownerRole}`) })}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs font-mono text-muted-foreground">
                          {portalT(`complianceTaskStatuses.${task.status}`)}
                        </p>
                      </div>
                    </div>
                    <ul className="mt-4 space-y-2 text-sm font-mono text-muted-foreground">
                      {task.notes.map((note) => (
                        <li key={note}>{note}</li>
                      ))}
                    </ul>
                  </article>
                )) : (
                  <p className="rounded-2xl border border-dashed border-grid-line/25 bg-terminal-surface/25 p-4 text-sm font-mono leading-6 text-muted-foreground">
                    {t('tasks.empty')}
                  </p>
                )}
              </div>
            </article>

            <div className="space-y-6">
              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                <div className="flex items-center gap-3">
                  <Shield className="h-5 w-5 text-neon-cyan" />
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('declarations.title')}
                  </h2>
                </div>
                <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                  {t('declarations.description')}
                </p>
                <div className="mt-4 space-y-3">
                  {state.trafficDeclarations.length > 0 ? state.trafficDeclarations.map((declaration) => (
                    <article
                      key={declaration.id}
                      className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                            {portalT(`complianceTaskKinds.${declaration.kind}`)}
                          </p>
                          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                            {t('declarations.scope', { value: declaration.scopeLabel })}
                          </p>
                          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                            {declaration.notes[0]}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan">
                            {portalT(`complianceTaskStatuses.${declaration.status}`)}
                          </p>
                          <p className="mt-2 text-xs font-mono text-muted-foreground">
                            {formatDateTime(declaration.updatedAt, locale)}
                          </p>
                        </div>
                      </div>
                    </article>
                  )) : (
                    <p className="rounded-xl border border-dashed border-grid-line/25 bg-terminal-bg/55 p-4 text-sm font-mono leading-6 text-muted-foreground">
                      {t('declarations.empty')}
                    </p>
                  )}
                </div>
              </article>

              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                <div className="flex items-center gap-3">
                  <TriangleAlert className="h-5 w-5 text-neon-purple" />
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('capabilities.title')}
                  </h2>
                </div>
                <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                  {t(`modes.${mode}`)}
                </p>
                <ul className="mt-4 space-y-3">
                  {capabilities.map((capability) => (
                    <li
                      key={capability.key}
                      className="flex items-center justify-between gap-3 rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3"
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

              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                  {t('actions.title')}
                </h2>
                <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                  {!isWriteAccess(access) || mode === 'read_only'
                    ? t('actions.readOnly')
                    : mode === 'review'
                      ? t('actions.review')
                      : mode === 'starter'
                        ? t('actions.starter')
                        : mode === 'controlled'
                          ? t('actions.controlled')
                          : t('actions.full')}
                </p>
                {actionFeedback ? (
                  <div
                    className={`mt-4 rounded-xl border px-4 py-3 text-sm font-mono ${
                      actionFeedback.tone === 'success'
                        ? 'border-matrix-green/30 bg-matrix-green/10 text-matrix-green'
                        : 'border-destructive/30 bg-destructive/10 text-destructive-foreground'
                    }`}
                  >
                    {actionFeedback.message}
                  </div>
                ) : null}
                {isWriteAccess(access) && mode !== 'read_only' ? (
                  <div className="mt-5 grid gap-4 xl:grid-cols-2">
                    <form
                      className="space-y-4 rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4"
                      onSubmit={(event) => {
                        event.preventDefault();
                        setActionFeedback(null);
                        trafficDeclarationMutation.mutate();
                      }}
                    >
                      <div>
                        <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                          {t('actions.traffic.title')}
                        </h3>
                        <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                          {t('actions.traffic.description')}
                        </p>
                      </div>
                      <label className="block text-sm font-mono text-foreground/90">
                        <span className="mb-2 block">{t('actions.traffic.kindLabel')}</span>
                        <select
                          className="h-10 w-full rounded-md border border-input bg-transparent px-3 text-sm text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                          value={trafficForm.declarationKind}
                          onChange={(event) =>
                            setTrafficForm((current) => ({
                              ...current,
                              declarationKind: event.target.value as 'approved_sources' | 'postback_readiness',
                            }))
                          }
                          disabled={trafficDeclarationMutation.isPending || !canSubmitActions}
                        >
                          <option value="approved_sources">
                            {t('actions.traffic.kinds.approved_sources')}
                          </option>
                          <option value="postback_readiness">
                            {t('actions.traffic.kinds.postback_readiness')}
                          </option>
                        </select>
                      </label>
                      <label className="block text-sm font-mono text-foreground/90">
                        <span className="mb-2 block">{t('actions.traffic.scopeLabel')}</span>
                        <Input
                          value={trafficForm.scopeLabel}
                          onChange={(event) =>
                            setTrafficForm((current) => ({
                              ...current,
                              scopeLabel: event.target.value,
                            }))
                          }
                          required
                          maxLength={120}
                          disabled={trafficDeclarationMutation.isPending || !canSubmitActions}
                        />
                      </label>
                      <label className="block text-sm font-mono text-foreground/90">
                        <span className="mb-2 block">{t('actions.traffic.detailsLabel')}</span>
                        <textarea
                          className="min-h-28 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                          value={trafficForm.details}
                          onChange={(event) =>
                            setTrafficForm((current) => ({
                              ...current,
                              details: event.target.value,
                            }))
                          }
                          required
                          disabled={trafficDeclarationMutation.isPending || !canSubmitActions}
                        />
                      </label>
                      <Button
                        type="submit"
                        magnetic={false}
                        disabled={trafficDeclarationMutation.isPending || !canSubmitActions}
                      >
                        {trafficDeclarationMutation.isPending
                          ? t('actions.submitting')
                          : t('actions.traffic.submit')}
                      </Button>
                    </form>

                    <form
                      className="space-y-4 rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4"
                      onSubmit={(event) => {
                        event.preventDefault();
                        setActionFeedback(null);
                        creativeApprovalMutation.mutate();
                      }}
                    >
                      <div>
                        <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                          {t('actions.creative.title')}
                        </h3>
                        <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                          {t('actions.creative.description')}
                        </p>
                      </div>
                      <label className="block text-sm font-mono text-foreground/90">
                        <span className="mb-2 block">{t('actions.creative.scopeLabel')}</span>
                        <Input
                          value={creativeForm.scopeLabel}
                          onChange={(event) =>
                            setCreativeForm((current) => ({
                              ...current,
                              scopeLabel: event.target.value,
                            }))
                          }
                          required
                          maxLength={120}
                          disabled={creativeApprovalMutation.isPending || !canSubmitActions}
                        />
                      </label>
                      <label className="block text-sm font-mono text-foreground/90">
                        <span className="mb-2 block">{t('actions.creative.referenceLabel')}</span>
                        <Input
                          value={creativeForm.creativeRef}
                          onChange={(event) =>
                            setCreativeForm((current) => ({
                              ...current,
                              creativeRef: event.target.value,
                            }))
                          }
                          maxLength={255}
                          disabled={creativeApprovalMutation.isPending || !canSubmitActions}
                        />
                      </label>
                      <label className="block text-sm font-mono text-foreground/90">
                        <span className="mb-2 block">{t('actions.creative.detailsLabel')}</span>
                        <textarea
                          className="min-h-28 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                          value={creativeForm.details}
                          onChange={(event) =>
                            setCreativeForm((current) => ({
                              ...current,
                              details: event.target.value,
                            }))
                          }
                          required
                          disabled={creativeApprovalMutation.isPending || !canSubmitActions}
                        />
                      </label>
                      <Button
                        type="submit"
                        magnetic={false}
                        disabled={creativeApprovalMutation.isPending || !canSubmitActions}
                      >
                        {creativeApprovalMutation.isPending
                          ? t('actions.submitting')
                          : t('actions.creative.submit')}
                      </Button>
                    </form>
                  </div>
                ) : null}
              </article>

              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                  {t('links.title')}
                </h2>
                <div className="mt-4 flex flex-col gap-3">
                  <Link href="/legal" className="text-sm font-mono text-neon-cyan underline underline-offset-4">
                    {t('links.legal')}
                  </Link>
                  <Link href="/cases" className="text-sm font-mono text-neon-purple underline underline-offset-4">
                    {t('links.cases')}
                  </Link>
                  <Link href="/codes" className="text-sm font-mono text-matrix-green underline underline-offset-4">
                    {t('links.codes')}
                  </Link>
                </div>
              </article>
            </div>
          </div>
        </section>
      )}
    </PartnerRouteGuard>
  );
}
