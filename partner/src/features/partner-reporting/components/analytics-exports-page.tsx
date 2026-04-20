'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowUpRight, ChartColumnIncreasing, Download } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Link } from '@/i18n/navigation';
import { PartnerRouteGuard } from '@/features/partner-portal-state/components/partner-route-guard';
import type { PartnerRouteAccessLevel } from '@/features/partner-portal-state/lib/portal-access';
import { usePartnerPortalRuntimeState } from '@/features/partner-portal-state/lib/use-partner-portal-runtime-state';
import {
  getPartnerAnalyticsCapabilities,
  getPartnerAnalyticsSurfaceMode,
} from '@/features/partner-operations/lib/reporting-finance-capabilities';
import { partnerPortalApi } from '@/lib/api/partner-portal';

function isWriteAccess(access: PartnerRouteAccessLevel) {
  return access === 'write' || access === 'admin';
}

function formatDateTime(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export function AnalyticsExportsPage() {
  const locale = useLocale();
  const t = useTranslations('Partner.analytics');
  const portalT = useTranslations('Partner.portalState');
  const queryClient = useQueryClient();
  const { state, activeWorkspace } = usePartnerPortalRuntimeState();
  const mode = getPartnerAnalyticsSurfaceMode(state);
  const capabilities = getPartnerAnalyticsCapabilities(state);
  const activeWorkspaceId = activeWorkspace?.id ?? null;
  const [actionFeedback, setActionFeedback] = useState<{
    tone: 'success' | 'error';
    message: string;
  } | null>(null);

  const scheduleExportMutation = useMutation({
    mutationFn: async ({
      exportId,
      exportKind,
    }: {
      exportId: string;
      exportKind: string;
    }) => {
      if (!activeWorkspaceId) {
        throw new Error(t('exports.workspaceRequired'));
      }
      return partnerPortalApi.scheduleWorkspaceReportExport(
        activeWorkspaceId,
        exportId,
        {
          message: t('exports.requestMessage', {
            kind: portalT(`reportExportKinds.${exportKind}`),
          }),
          request_payload: {
            request_origin: 'partner_portal_reporting_surface',
            requested_surface_mode: mode,
          },
        },
      );
    },
    onSuccess: async (_response, variables) => {
      if (activeWorkspaceId) {
        await queryClient.invalidateQueries({
          queryKey: ['partner-portal', 'workspace-report-exports', activeWorkspaceId],
        });
      }
      setActionFeedback({
        tone: 'success',
        message: t('exports.requestSuccess', {
          kind: portalT(`reportExportKinds.${variables.exportKind}`),
        }),
      });
    },
    onError: (error) => {
      setActionFeedback({
        tone: 'error',
        message:
          error instanceof Error ? error.message : t('exports.requestErrorFallback'),
      });
    },
  });

  return (
    <PartnerRouteGuard route="analytics" title={t('title')}>
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

              <div className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-4 text-sm font-mono text-muted-foreground lg:w-[340px]">
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
                    {portalT(`analyticsModes.${mode}`)}
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <span>{t('summary.exports')}</span>
                  <span className="text-foreground">{state.reportExports.length}</span>
                </div>
              </div>
            </div>
          </header>

          {actionFeedback ? (
            <div
              className={`rounded-2xl border px-4 py-3 text-sm font-mono ${
                actionFeedback.tone === 'success'
                  ? 'border-matrix-green/35 bg-matrix-green/10 text-matrix-green'
                  : 'border-neon-pink/35 bg-neon-pink/10 text-neon-pink'
              }`}
            >
              {actionFeedback.message}
            </div>
          ) : null}

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {state.analyticsMetrics.slice(0, 4).map((metric) => (
              <article
                key={metric.key}
                className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5"
              >
                <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
                  {portalT(`analyticsMetricKeys.${metric.key}`)}
                </p>
                <p className="mt-3 text-2xl font-display tracking-[0.14em] text-white">
                  {metric.value}
                </p>
                <p className="mt-3 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {portalT(`analyticsMetricTrends.${metric.trend}`)}
                </p>
              </article>
            ))}
          </div>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
            <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
              <div className="flex items-center gap-3 border-b border-grid-line/20 pb-4">
                <ChartColumnIncreasing className="h-5 w-5 text-neon-cyan" />
                <div>
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('metrics.title')}
                  </h2>
                  <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                    {t('metrics.description')}
                  </p>
                </div>
              </div>

              <div className="mt-5 space-y-3">
                {state.analyticsMetrics.map((metric) => (
                  <article
                    key={metric.key}
                    className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4"
                  >
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                          {portalT(`analyticsMetricKeys.${metric.key}`)}
                        </h3>
                        <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                          {metric.notes[0]}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-display tracking-[0.12em] text-white">
                          {metric.value}
                        </p>
                        <p className="mt-2 text-xs font-mono text-muted-foreground">
                          {portalT(`analyticsMetricTrends.${metric.trend}`)}
                        </p>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </article>

            <div className="space-y-6">
              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                <div className="flex items-center gap-3">
                  <Download className="h-5 w-5 text-neon-purple" />
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('exports.title')}
                  </h2>
                </div>
                <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                  {t(`modes.${mode}`)}
                </p>
                <div className="mt-4 space-y-3">
                  {state.reportExports.map((item) => (
                    <article
                      key={item.id}
                      className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4"
                    >
                      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                        <div>
                          <div className="flex items-center gap-3">
                            <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                              {portalT(`reportExportKinds.${item.kind}`)}
                            </p>
                            <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan">
                              {portalT(`reportExportStatuses.${item.status}`)}
                            </span>
                          </div>
                          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                            {t('exports.cadence', { value: item.cadence })}
                          </p>
                          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                            {item.notes[0]}
                          </p>
                          {item.lastRequestedAt ? (
                            <p className="mt-2 text-xs font-mono uppercase tracking-[0.16em] text-neon-purple">
                              {t('exports.lastRequested', {
                                value: formatDateTime(item.lastRequestedAt, locale),
                              })}
                            </p>
                          ) : null}
                        </div>

                        {activeWorkspaceId &&
                        isWriteAccess(access) &&
                        item.availableActions?.includes('schedule_export') ? (
                          <Button
                            type="button"
                            variant="outline"
                            className="border-neon-cyan/40 bg-terminal-surface/50 font-mono uppercase tracking-[0.16em] text-neon-cyan hover:bg-neon-cyan/10 hover:text-neon-cyan"
                            disabled={
                              scheduleExportMutation.isPending &&
                              scheduleExportMutation.variables?.exportId === item.id
                            }
                            onClick={() => {
                              setActionFeedback(null);
                              scheduleExportMutation.mutate({
                                exportId: item.id,
                                exportKind: item.kind,
                              });
                            }}
                          >
                            {scheduleExportMutation.isPending &&
                            scheduleExportMutation.variables?.exportId === item.id
                              ? t('exports.requesting')
                              : t('exports.requestAction')}
                          </Button>
                        ) : null}
                      </div>

                      <div className="mt-4 rounded-xl border border-grid-line/20 bg-terminal-surface/35 p-3">
                        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          {t('exports.lifecycleTitle')}
                        </p>
                        {item.threadEvents && item.threadEvents.length > 0 ? (
                          <div className="mt-3 space-y-2">
                            {item.threadEvents.slice(0, 3).map((event) => (
                              <div
                                key={event.id}
                                className="rounded-lg border border-grid-line/15 bg-terminal-bg/45 px-3 py-2"
                              >
                                <p className="text-xs font-mono leading-5 text-foreground/90">
                                  {event.message}
                                </p>
                                <p className="mt-1 text-[11px] font-mono uppercase tracking-[0.14em] text-muted-foreground">
                                  {formatDateTime(event.createdAt, locale)}
                                </p>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                            {t('exports.noRequests')}
                          </p>
                        )}
                      </div>
                    </article>
                  ))}
                </div>
              </article>

              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                  {t('capabilities.title')}
                </h2>
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
                        {portalT(`operationalCapabilityAvailability.${capability.availability}`)}
                      </span>
                    </li>
                  ))}
                </ul>
              </article>

              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                  {t('links.title')}
                </h2>
                <div className="mt-4 flex flex-col gap-3">
                  <Link href="/finance" className="inline-flex items-center gap-2 text-sm font-mono text-neon-cyan underline underline-offset-4">
                    <span>{t('links.finance')}</span>
                    <ArrowUpRight className="h-3.5 w-3.5" />
                  </Link>
                  <Link href="/codes" className="inline-flex items-center gap-2 text-sm font-mono text-neon-purple underline underline-offset-4">
                    <span>{t('links.codes')}</span>
                    <ArrowUpRight className="h-3.5 w-3.5" />
                  </Link>
                  <Link href="/cases" className="inline-flex items-center gap-2 text-sm font-mono text-matrix-green underline underline-offset-4">
                    <span>{t('links.cases')}</span>
                    <ArrowUpRight className="h-3.5 w-3.5" />
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
