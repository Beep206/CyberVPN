'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, Briefcase, Waypoints } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Link } from '@/i18n/navigation';
import { partnerPortalApi } from '@/lib/api/partner-portal';
import { PartnerRouteGuard } from '@/features/partner-portal-state/components/partner-route-guard';
import type { PartnerPortalProgramsSnapshot } from '@/features/partner-portal-state/lib/runtime-state';
import { usePartnerPortalRuntimeState } from '@/features/partner-portal-state/lib/use-partner-portal-runtime-state';
import type { PartnerPrimaryLane } from '@/features/partner-onboarding/lib/application-draft-storage';

const AVAILABLE_LANE_KEYS: PartnerPrimaryLane[] = [
  'creator_affiliate',
  'performance_media',
  'reseller_api',
];

const FIELD_CLASS_NAME = 'w-full rounded-xl border border-grid-line/25 bg-terminal-bg/70 px-4 py-3 text-sm font-mono text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-neon-cyan/50 focus:ring-2 focus:ring-neon-cyan/20';
const TEXTAREA_CLASS_NAME = `${FIELD_CLASS_NAME} min-h-[120px] resize-y`;

function formatDateTime(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function buildLocalProgramsSnapshot(
  state: ReturnType<typeof usePartnerPortalRuntimeState>['state'],
): PartnerPortalProgramsSnapshot {
  return {
    canonicalSource: 'local_scenario',
    primaryLaneKey: state.primaryLane || null,
    laneMemberships: state.laneMemberships.map((membership) => ({
      laneKey: membership.lane,
      membershipStatus: membership.status,
      ownerContextLabel: membership.assignedManager,
      pilotCohortId: null,
      pilotCohortStatus: null,
      runbookGateStatus: null,
      blockingReasonCodes: [],
      warningReasonCodes: [],
      restrictionNotes: membership.restrictions,
      readinessNotes: [],
      updatedAt: state.updatedAt ?? new Date().toISOString(),
    })),
    readinessItems: [
      {
        key: 'finance',
        status: state.financeReadiness,
        blockingReasonCodes: [],
        notes: [],
      },
      {
        key: 'compliance',
        status: state.complianceReadiness,
        blockingReasonCodes: [],
        notes: [],
      },
      {
        key: 'technical',
        status: state.technicalReadiness,
        blockingReasonCodes: [],
        notes: [],
      },
    ],
    updatedAt: state.updatedAt ?? new Date().toISOString(),
  };
}

function getReadinessStatusLabel(
  key: string,
  status: string,
  portalT: ReturnType<typeof useTranslations>,
): string {
  if (key === 'finance') {
    return portalT(`financeStates.${status}`);
  }
  if (key === 'compliance') {
    return portalT(`complianceStates.${status}`);
  }
  return portalT(`technicalStates.${status}`);
}

export function ProgramsPage() {
  const locale = useLocale();
  const t = useTranslations('Partner.programs');
  const portalT = useTranslations('Partner.portalState');
  const queryClient = useQueryClient();
  const {
    state,
    programsSnapshot,
    isCanonicalWorkspace,
    activeWorkspace,
  } = usePartnerPortalRuntimeState();

  const [selectedLaneKey, setSelectedLaneKey] = useState<PartnerPrimaryLane>('performance_media');
  const [laneRequestNotes, setLaneRequestNotes] = useState('');
  const [requestFeedback, setRequestFeedback] = useState<{
    tone: 'success' | 'error';
    message: string;
  } | null>(null);

  const laneApplicationsQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-lane-applications', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return [];
      }
      const response = await partnerPortalApi.listWorkspaceLaneApplications(activeWorkspace.id);
      return response.data;
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 30_000,
    retry: false,
  });

  const requestLaneMutation = useMutation({
    mutationFn: async ({
      laneKey,
      notes,
    }: {
      laneKey: PartnerPrimaryLane;
      notes: string;
    }) => {
      if (!activeWorkspace) {
        throw new Error(t('laneApplications.workspaceRequired'));
      }

      const created = await partnerPortalApi.createWorkspaceLaneApplication(
        activeWorkspace.id,
        {
          lane_key: laneKey,
          application_payload: {
            business_case: notes,
            request_origin: 'partner_portal_programs_surface',
          },
        },
      );

      const submitted = await partnerPortalApi.submitWorkspaceLaneApplication(
        activeWorkspace.id,
        created.data.id,
      );

      return submitted.data;
    },
    onSuccess: async (application) => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ['partner-portal', 'workspace-lane-applications', activeWorkspace?.id ?? null],
        }),
        queryClient.invalidateQueries({
          queryKey: ['partner-portal', 'session-bootstrap'],
        }),
      ]);
      setLaneRequestNotes('');
      setRequestFeedback({
        tone: 'success',
        message: t('laneApplications.submitSuccess', {
          lane: portalT(`laneLabels.${application.lane_key}`),
        }),
      });
    },
    onError: (error) => {
      setRequestFeedback({
        tone: 'error',
        message:
          error instanceof Error ? error.message : t('laneApplications.submitError'),
      });
    },
  });

  const effectiveProgramsSnapshot = programsSnapshot
    ?? (isCanonicalWorkspace ? null : buildLocalProgramsSnapshot(state));
  const laneMemberships = useMemo(
    () => effectiveProgramsSnapshot?.laneMemberships ?? [],
    [effectiveProgramsSnapshot],
  );
  const readinessItems = effectiveProgramsSnapshot?.readinessItems ?? [];
  const currentLaneLabel = effectiveProgramsSnapshot?.primaryLaneKey
    ? portalT(`laneLabels.${effectiveProgramsSnapshot.primaryLaneKey}`)
    : portalT('noLane');
  const laneApplications = useMemo(
    () => laneApplicationsQuery.data ?? [],
    [laneApplicationsQuery.data],
  );

  const blockedLaneKeys = useMemo(() => new Set([
    ...laneMemberships.map((membership) => membership.laneKey),
    ...laneApplications
      .filter((application) => application.status !== 'declined')
      .map((application) => application.lane_key),
  ]), [laneApplications, laneMemberships]);

  const availableLaneOptions = AVAILABLE_LANE_KEYS.filter((laneKey) => !blockedLaneKeys.has(laneKey));
  const effectiveSelectedLaneKey = availableLaneOptions.includes(selectedLaneKey)
    ? selectedLaneKey
    : availableLaneOptions[0] ?? selectedLaneKey;

  return (
    <PartnerRouteGuard route="programs" title={t('title')}>
      {(access) => {
        const canWrite = access === 'admin' || access === 'write';

        return (
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
                    <span>{t('summary.currentRole')}</span>
                    <span className="text-foreground">
                      {portalT(`workspaceRoles.${state.workspaceRole}`)}
                    </span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.routeAccess')}</span>
                    <span className="text-neon-cyan">
                      {portalT(`routeAccess.${access}`)}
                    </span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.workspaceStatus')}</span>
                    <span className="text-foreground">
                      {portalT(`workspaceStatuses.${state.workspaceStatus}`)}
                    </span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.currentLane')}</span>
                    <span className="text-foreground">{currentLaneLabel}</span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.canonicalSource')}</span>
                    <span className="text-foreground">
                      {effectiveProgramsSnapshot?.canonicalSource ?? 'unavailable'}
                    </span>
                  </div>
                </div>
              </div>
            </header>

            {requestFeedback ? (
              <div
                className={`rounded-2xl border px-4 py-3 text-sm font-mono ${
                  requestFeedback.tone === 'success'
                    ? 'border-matrix-green/35 bg-matrix-green/10 text-matrix-green'
                    : 'border-neon-pink/35 bg-neon-pink/10 text-neon-pink'
                }`}
              >
                {requestFeedback.message}
              </div>
            ) : null}

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.08fr)_minmax(0,0.92fr)]">
              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
                <div className="flex items-center gap-3 border-b border-grid-line/20 pb-4">
                  <Waypoints className="h-5 w-5 text-neon-cyan" />
                  <div>
                    <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                      {t('lanes.title')}
                    </h2>
                    <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                      {t('lanes.description')}
                    </p>
                  </div>
                </div>

                {laneMemberships.length === 0 ? (
                  <div className="mt-5 rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                    <p className="text-sm font-mono leading-6 text-muted-foreground">
                      {t('lanes.empty')}
                    </p>
                  </div>
                ) : (
                  <div className="mt-5 space-y-3">
                    {laneMemberships.map((membership) => (
                      <article
                        key={membership.laneKey}
                        className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4"
                      >
                        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                          <div>
                            <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                              {portalT(`laneLabels.${membership.laneKey}`)}
                            </h3>
                            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                              {t('lanes.ownerContext', {
                                value: membership.ownerContextLabel,
                              })}
                            </p>
                            {membership.pilotCohortStatus ? (
                              <p className="mt-1 text-xs font-mono uppercase tracking-[0.18em] text-neon-purple/80">
                                {t('lanes.cohortStatus', {
                                  value: membership.pilotCohortStatus,
                                })}
                              </p>
                            ) : null}
                          </div>
                          <span className="inline-flex rounded-full border border-neon-cyan/30 bg-neon-cyan/10 px-3 py-1 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan">
                            {portalT(`laneStatuses.${membership.membershipStatus}`)}
                          </span>
                        </div>

                        <div className="mt-4 grid gap-4 xl:grid-cols-2">
                          <div className="space-y-3">
                            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                              {t('lanes.restrictionsTitle')}
                            </p>
                            <ul className="space-y-2">
                              {membership.restrictionNotes.map((note) => (
                                <li
                                  key={`${membership.laneKey}-restriction-${note}`}
                                  className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-3 py-2 text-sm font-mono leading-6 text-muted-foreground"
                                >
                                  {note}
                                </li>
                              ))}
                            </ul>
                          </div>

                          <div className="space-y-3">
                            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-purple/80">
                              {t('lanes.readinessTitle')}
                            </p>
                            {(membership.readinessNotes.length > 0
                              ? membership.readinessNotes
                              : [t('lanes.readinessEmpty')]).map((note) => (
                              <div
                                key={`${membership.laneKey}-readiness-${note}`}
                                className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-3 py-2 text-sm font-mono leading-6 text-muted-foreground"
                              >
                                {note}
                              </div>
                            ))}
                          </div>
                        </div>

                        {membership.blockingReasonCodes.length > 0 ? (
                          <div className="mt-4">
                            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-pink/80">
                              {t('lanes.blockingTitle')}
                            </p>
                            <div className="mt-2 flex flex-wrap gap-2">
                              {membership.blockingReasonCodes.map((code) => (
                                <span
                                  key={`${membership.laneKey}-blocking-${code}`}
                                  className="rounded-full border border-neon-pink/30 bg-neon-pink/10 px-3 py-1 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-pink"
                                >
                                  {code}
                                </span>
                              ))}
                            </div>
                          </div>
                        ) : null}

                        {membership.warningReasonCodes.length > 0 ? (
                          <div className="mt-4">
                            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-purple/80">
                              {t('lanes.warningsTitle')}
                            </p>
                            <div className="mt-2 flex flex-wrap gap-2">
                              {membership.warningReasonCodes.map((code) => (
                                <span
                                  key={`${membership.laneKey}-warning-${code}`}
                                  className="rounded-full border border-neon-purple/30 bg-neon-purple/10 px-3 py-1 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-purple"
                                >
                                  {code}
                                </span>
                              ))}
                            </div>
                          </div>
                        ) : null}
                      </article>
                    ))}
                  </div>
                )}
              </article>

              <div className="space-y-6">
                <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="h-5 w-5 text-neon-purple" />
                    <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                      {t('readiness.title')}
                    </h2>
                  </div>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {t('readiness.description')}
                  </p>
                  {effectiveProgramsSnapshot ? (
                    <p className="mt-3 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('readiness.lastUpdated', {
                        value: formatDateTime(effectiveProgramsSnapshot.updatedAt, locale),
                      })}
                    </p>
                  ) : null}

                  <div className="mt-4 space-y-3">
                    {readinessItems.map((item) => (
                      <article
                        key={item.key}
                        className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4"
                      >
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                            {portalT(`readinessLabels.${item.key}`)}
                          </p>
                          <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan">
                            {getReadinessStatusLabel(item.key, item.status, portalT)}
                          </span>
                        </div>
                        <div className="mt-3 space-y-2">
                          {item.notes.map((note) => (
                            <p
                              key={`${item.key}-${note}`}
                              className="text-sm font-mono leading-6 text-muted-foreground"
                            >
                              {note}
                            </p>
                          ))}
                        </div>
                        {item.blockingReasonCodes.length > 0 ? (
                          <div className="mt-3 flex flex-wrap gap-2">
                            {item.blockingReasonCodes.map((code) => (
                              <span
                                key={`${item.key}-${code}`}
                                className="rounded-full border border-neon-pink/30 bg-neon-pink/10 px-3 py-1 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-pink"
                              >
                                {code}
                              </span>
                            ))}
                          </div>
                        ) : null}
                      </article>
                    ))}
                  </div>
                </article>

                <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <div className="flex items-center gap-3">
                    <Briefcase className="h-5 w-5 text-neon-purple" />
                    <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                      {t('laneApplications.title')}
                    </h2>
                  </div>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {canWrite
                      ? t('laneApplications.description')
                      : t('laneApplications.readOnly')}
                  </p>

                  {laneApplications.length > 0 ? (
                    <div className="mt-4 space-y-3">
                      {laneApplications.map((application) => (
                        <article
                          key={application.id}
                          className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                              {portalT(`laneLabels.${application.lane_key}`)}
                            </p>
                            <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan">
                              {portalT(`laneStatuses.${application.status}`)}
                            </span>
                          </div>
                          <p className="mt-2 text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                            {t('laneApplications.updatedAt', {
                              value: formatDateTime(application.updated_at, locale),
                            })}
                          </p>
                          {typeof application.application_payload?.business_case === 'string' ? (
                            <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                              {String(application.application_payload.business_case)}
                            </p>
                          ) : null}
                          {application.decision_summary ? (
                            <p className="mt-3 text-sm font-mono leading-6 text-neon-purple">
                              {application.decision_summary}
                            </p>
                          ) : null}
                        </article>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-4 rounded-xl border border-dashed border-grid-line/25 bg-terminal-bg/35 px-4 py-3 text-sm font-mono leading-6 text-muted-foreground">
                      {t('laneApplications.empty')}
                    </p>
                  )}

                  {canWrite ? (
                    <div className="mt-4 space-y-3 rounded-xl border border-grid-line/20 bg-terminal-bg/35 p-4">
                      <select
                        className={FIELD_CLASS_NAME}
                        value={effectiveSelectedLaneKey}
                        onChange={(event) => {
                          setSelectedLaneKey(event.target.value as PartnerPrimaryLane);
                          setRequestFeedback(null);
                        }}
                        disabled={availableLaneOptions.length === 0}
                      >
                        {(availableLaneOptions.length > 0 ? availableLaneOptions : AVAILABLE_LANE_KEYS).map((laneKey) => (
                          <option key={laneKey} value={laneKey}>
                            {portalT(`laneLabels.${laneKey}`)}
                          </option>
                        ))}
                      </select>
                      <textarea
                        className={TEXTAREA_CLASS_NAME}
                        value={laneRequestNotes}
                        onChange={(event) => {
                          setLaneRequestNotes(event.target.value);
                          setRequestFeedback(null);
                        }}
                        placeholder={t('laneApplications.placeholder')}
                        disabled={availableLaneOptions.length === 0}
                      />
                      <Button
                        type="button"
                        className="bg-neon-cyan text-black hover:bg-neon-cyan/90 font-mono text-xs uppercase tracking-[0.18em]"
                        disabled={
                          requestLaneMutation.isPending ||
                          availableLaneOptions.length === 0 ||
                          laneRequestNotes.trim().length === 0
                        }
                        onClick={() => {
                          setRequestFeedback(null);
                          void requestLaneMutation.mutateAsync({
                            laneKey: effectiveSelectedLaneKey,
                            notes: laneRequestNotes.trim(),
                          });
                        }}
                      >
                        {requestLaneMutation.isPending
                          ? t('laneApplications.submitting')
                          : t('laneApplications.submitAction')}
                      </Button>
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
                    <Link href="/organization" className="text-sm font-mono text-neon-purple underline underline-offset-4">
                      {t('links.organization')}
                    </Link>
                    <Link href="/cases" className="text-sm font-mono text-matrix-green underline underline-offset-4">
                      {t('links.cases')}
                    </Link>
                  </div>
                  {activeWorkspace ? (
                    <p className="mt-4 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('links.workspaceContext', {
                        value: activeWorkspace.display_name,
                      })}
                    </p>
                  ) : null}
                </article>
              </div>
            </div>
          </section>
        );
      }}
    </PartnerRouteGuard>
  );
}
