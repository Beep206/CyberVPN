'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { CheckCheck, MessageSquareText, Send, ShieldAlert } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { Button } from '@/components/ui/button';
import { partnerPortalApi } from '@/lib/api/partner-portal';
import { getCasesRestrictionReasons } from '@/features/partner-compliance/lib/compliance-runtime';
import { PartnerRouteGuard } from '@/features/partner-portal-state/components/partner-route-guard';
import {
  submitPartnerReviewRequests,
  type PartnerPortalCase,
  type PartnerReviewRequest,
} from '@/features/partner-portal-state/lib/portal-state';
import { usePartnerPortalRuntimeState } from '@/features/partner-portal-state/lib/use-partner-portal-runtime-state';
import {
  getPartnerCasesCapabilities,
  getPartnerCasesSurfaceMode,
} from '@/features/partner-operations/lib/reporting-finance-capabilities';

function formatDateTime(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function resolveMutationError(error: unknown, fallback: string): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
  }
  return fallback;
}

export function PartnerCasesPage() {
  const locale = useLocale();
  const t = useTranslations('Partner.cases');
  const portalT = useTranslations('Partner.portalState');
  const queryClient = useQueryClient();
  const {
    state,
    isCanonicalWorkspace,
    activeWorkspace,
    blockedReasons,
  } = usePartnerPortalRuntimeState();
  const mode = getPartnerCasesSurfaceMode(state);
  const capabilities = getPartnerCasesCapabilities(state);
  const workspaceId = activeWorkspace?.id ?? state.activeWorkspaceId ?? null;
  const restrictionReasons = useMemo(
    () => getCasesRestrictionReasons(blockedReasons),
    [blockedReasons],
  );

  const [reviewDrafts, setReviewDrafts] = useState<Record<string, string>>({});
  const [caseDrafts, setCaseDrafts] = useState<Record<string, string>>({});
  const [reviewFeedback, setReviewFeedback] = useState<{
    id: string;
    tone: 'success' | 'error';
    message: string;
  } | null>(null);
  const [caseFeedback, setCaseFeedback] = useState<{
    id: string;
    tone: 'success' | 'error';
    message: string;
  } | null>(null);

  const openRequests = state.reviewRequests.filter((request) => request.status === 'open');
  const operationalCases = state.cases.filter((item) => item.kind !== 'application_review');

  const invalidateWorkspaceWorkflowQueries = async (targetWorkspaceId: string) => {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: ['partner-portal', 'workspace-review-requests', targetWorkspaceId],
      }),
      queryClient.invalidateQueries({
        queryKey: ['partner-portal', 'workspace-cases', targetWorkspaceId],
      }),
      queryClient.invalidateQueries({
        queryKey: ['partner-portal', 'workspace-notifications', targetWorkspaceId],
      }),
      queryClient.invalidateQueries({
        queryKey: ['partner-portal', 'session-bootstrap'],
      }),
    ]);
  };

  const reviewResponseMutation = useMutation({
    mutationFn: async ({
      targetWorkspaceId,
      reviewRequestId,
      message,
    }: {
      targetWorkspaceId: string;
      reviewRequestId: string;
      message: string;
    }) =>
      partnerPortalApi.respondToWorkspaceReviewRequest(
        targetWorkspaceId,
        reviewRequestId,
        {
          message,
          response_payload: {
            response_origin: 'partner_portal_cases_surface',
          },
        },
      ),
    onSuccess: async (_response, variables) => {
      setReviewDrafts((current) => ({ ...current, [variables.reviewRequestId]: '' }));
      setReviewFeedback({
        id: variables.reviewRequestId,
        tone: 'success',
        message: t('requestedInfo.success'),
      });
      await invalidateWorkspaceWorkflowQueries(variables.targetWorkspaceId);
    },
    onError: (error, variables) => {
      setReviewFeedback({
        id: variables.reviewRequestId,
        tone: 'error',
        message: resolveMutationError(error, t('requestedInfo.error')),
      });
    },
  });

  const caseReplyMutation = useMutation({
    mutationFn: async ({
      targetWorkspaceId,
      caseId,
      message,
    }: {
      targetWorkspaceId: string;
      caseId: string;
      message: string;
    }) =>
      partnerPortalApi.respondToWorkspaceCase(targetWorkspaceId, caseId, {
        message,
        response_payload: {
          response_origin: 'partner_portal_cases_surface',
          workflow_action: 'reply',
        },
      }),
    onSuccess: async (_response, variables) => {
      setCaseDrafts((current) => ({ ...current, [variables.caseId]: '' }));
      setCaseFeedback({
        id: variables.caseId,
        tone: 'success',
        message: t('caseList.replySuccess'),
      });
      await invalidateWorkspaceWorkflowQueries(variables.targetWorkspaceId);
    },
    onError: (error, variables) => {
      setCaseFeedback({
        id: variables.caseId,
        tone: 'error',
        message: resolveMutationError(error, t('caseList.responseError')),
      });
    },
  });

  const caseReadyForOpsMutation = useMutation({
    mutationFn: async ({
      targetWorkspaceId,
      caseId,
      message,
    }: {
      targetWorkspaceId: string;
      caseId: string;
      message: string;
    }) =>
      partnerPortalApi.markWorkspaceCaseReadyForOps(targetWorkspaceId, caseId, {
        message,
        response_payload: {
          response_origin: 'partner_portal_cases_surface',
          workflow_action: 'mark_ready_for_ops',
        },
      }),
    onSuccess: async (_response, variables) => {
      setCaseDrafts((current) => ({ ...current, [variables.caseId]: '' }));
      setCaseFeedback({
        id: variables.caseId,
        tone: 'success',
        message: t('caseList.readySuccess'),
      });
      await invalidateWorkspaceWorkflowQueries(variables.targetWorkspaceId);
    },
    onError: (error, variables) => {
      setCaseFeedback({
        id: variables.caseId,
        tone: 'error',
        message: resolveMutationError(error, t('caseList.responseError')),
      });
    },
  });

  const renderThreadEvents = (
    item: PartnerReviewRequest | PartnerPortalCase,
    emptyLabel: string,
  ) => {
    const threadEvents = item.threadEvents ?? [];
    if (threadEvents.length === 0) {
      return (
        <p className="text-sm font-mono leading-6 text-muted-foreground">
          {emptyLabel}
        </p>
      );
    }

    return (
      <div className="space-y-2">
        {threadEvents.map((event) => (
          <article
            key={event.id}
            className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-3"
          >
            <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
              <div>
                <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                  {portalT(`workflowActionKinds.${event.actionKind}`)}
                </p>
                <p className="mt-2 text-sm font-mono leading-6 text-foreground/90">
                  {event.message}
                </p>
              </div>
              <p className="text-xs font-mono text-muted-foreground">
                {t('thread.eventAt', {
                  value: formatDateTime(event.createdAt, locale),
                })}
              </p>
            </div>
          </article>
        ))}
      </div>
    );
  };

  return (
    <PartnerRouteGuard route="cases" title={t('title')}>
      {(access) => {
        const canRespondToLocalRequests =
          !isCanonicalWorkspace
          && state.workspaceDataSource !== 'canonical'
          && state.workspaceStatus === 'needs_info'
          && openRequests.length > 0
          && (access === 'write' || access === 'admin');

        const canRespondToReviewRequest = (request: PartnerReviewRequest) =>
          Boolean(workspaceId)
          && isCanonicalWorkspace
          && (access === 'write' || access === 'admin')
          && (request.availableActions ?? []).includes('submit_response');

        const canReplyToCase = (item: PartnerPortalCase) =>
          Boolean(workspaceId)
          && isCanonicalWorkspace
          && (access === 'write' || access === 'admin')
          && (item.availableActions ?? []).includes('reply');

        const canMarkCaseReadyForOps = (item: PartnerPortalCase) =>
          Boolean(workspaceId)
          && isCanonicalWorkspace
          && (access === 'write' || access === 'admin')
          && (item.availableActions ?? []).includes('mark_ready_for_ops');

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
                    <span>{t('summary.routeAccess')}</span>
                    <span className="text-neon-cyan">
                      {portalT(`routeAccess.${access}`)}
                    </span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.surfaceMode')}</span>
                    <span className="text-foreground">
                      {portalT(`casesModes.${mode}`)}
                    </span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.openCases')}</span>
                    <span className="text-foreground">{operationalCases.length}</span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.reviewRequests')}</span>
                    <span className="text-foreground">{openRequests.length}</span>
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

            {restrictionReasons.length > 0 ? (
              <article className="rounded-[1.5rem] border border-neon-pink/25 bg-neon-pink/10 p-5 shadow-[0_0_24px_rgba(255,0,255,0.08)]">
                <div className="flex items-start gap-3">
                  <ShieldAlert className="mt-0.5 h-5 w-5 text-neon-pink" />
                  <div>
                    <h2 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                      {t('restrictions.title')}
                    </h2>
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
                  </div>
                </div>
              </article>
            ) : null}

            <section className="grid gap-4 md:grid-cols-2">
              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)]">
                <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
                  Workspace support lane
                </p>
                <h2 className="mt-3 text-lg font-display uppercase tracking-[0.16em] text-white">
                  {(activeWorkspace?.display_name ?? state.activeWorkspaceDisplayName ?? 'Current workspace')} ops and compliance routing
                </h2>
                <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                  Use portal cases, review requests, finance, and compliance surfaces for partner-operator issues. This lane owns workspace onboarding, statement questions, payout readiness, and attribution disputes.
                </p>
              </article>
              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)]">
                <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-neon-purple/80">
                  Customer support boundary
                </p>
                <h2 className="mt-3 text-lg font-display uppercase tracking-[0.16em] text-white">
                  Branded storefront support remains separate
                </h2>
                <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                  Do not answer customer checkout or access requests from workspace support threads as if they were storefront tickets. Customer messaging, legal acceptance, and branded service support stay on the storefront surface.
                </p>
              </article>
            </section>

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                <div className="flex items-center justify-between gap-3 border-b border-grid-line/20 pb-4">
                  <div>
                    <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                      {t('requestedInfo.title')}
                    </h2>
                    <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                      {t(`modes.${mode}`)}
                    </p>
                  </div>
                  {canRespondToLocalRequests ? (
                    <Button
                      type="button"
                      onClick={submitPartnerReviewRequests}
                      className="bg-neon-cyan font-mono text-xs uppercase tracking-[0.18em] text-black hover:bg-neon-cyan/90"
                    >
                      <Send className="mr-2 h-4 w-4" />
                      {t('requestedInfo.respondAction')}
                    </Button>
                  ) : null}
                </div>

                {state.reviewRequests.length === 0 ? (
                  <p className="mt-5 text-sm font-mono leading-6 text-muted-foreground">
                    {t('requestedInfo.empty')}
                  </p>
                ) : (
                  <div className="mt-5 space-y-3">
                    {state.reviewRequests.map((request) => (
                      <article
                        key={request.id}
                        className="rounded-2xl border border-neon-cyan/20 bg-terminal-bg/55 p-4"
                      >
                        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                          <div>
                            <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                              {portalT(`reviewRequestKinds.${request.kind}.title`)}
                            </h3>
                            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                              {portalT(`reviewRequestKinds.${request.kind}.description`)}
                            </p>
                          </div>
                          <div className="space-y-2 text-right">
                            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                              {portalT(`reviewRequestStatuses.${request.status}`)}
                            </p>
                            <span className="inline-flex rounded-full border border-neon-cyan/30 bg-neon-cyan/10 px-3 py-1 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan">
                              {t('requestedInfo.dueDate', {
                                value: formatDateTime(request.dueDate, locale),
                              })}
                            </span>
                          </div>
                        </div>

                        <div className="mt-4 space-y-3 border-t border-grid-line/20 pt-4">
                          <div>
                            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-purple/80">
                              {t('requestedInfo.threadTitle')}
                            </p>
                            <div className="mt-2">
                              {renderThreadEvents(request, t('requestedInfo.threadEmpty'))}
                            </div>
                          </div>

                          {canRespondToReviewRequest(request) ? (
                            <div className="space-y-3 border-t border-grid-line/20 pt-4">
                              <label
                                htmlFor={`review-request-response-${request.id}`}
                                className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80"
                              >
                                {t('requestedInfo.responseLabel')}
                              </label>
                              <textarea
                                id={`review-request-response-${request.id}`}
                                value={reviewDrafts[request.id] ?? ''}
                                onChange={(event) => {
                                  const value = event.target.value;
                                  setReviewDrafts((current) => ({
                                    ...current,
                                    [request.id]: value,
                                  }));
                                  if (reviewFeedback?.id === request.id) {
                                    setReviewFeedback(null);
                                  }
                                }}
                                placeholder={t('requestedInfo.responsePlaceholder')}
                                className="min-h-28 w-full rounded-2xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-sm font-mono text-foreground outline-none transition focus:border-neon-cyan/40"
                              />
                              <div className="flex flex-wrap items-center gap-3">
                                <Button
                                  type="button"
                                  disabled={
                                    reviewResponseMutation.isPending
                                    || !(reviewDrafts[request.id] ?? '').trim()
                                    || !workspaceId
                                  }
                                  onClick={() => {
                                    if (!workspaceId) {
                                      return;
                                    }
                                    setReviewFeedback(null);
                                    reviewResponseMutation.mutate({
                                      targetWorkspaceId: workspaceId,
                                      reviewRequestId: request.id,
                                      message: (reviewDrafts[request.id] ?? '').trim(),
                                    });
                                  }}
                                  className="bg-neon-cyan font-mono text-xs uppercase tracking-[0.18em] text-black hover:bg-neon-cyan/90"
                                >
                                  <Send className="mr-2 h-4 w-4" />
                                  {reviewResponseMutation.isPending
                                    ? t('requestedInfo.sending')
                                    : t('requestedInfo.submitCanonicalAction')}
                                </Button>
                                {reviewFeedback?.id === request.id ? (
                                  <p
                                    className={`text-xs font-mono ${
                                      reviewFeedback.tone === 'success'
                                        ? 'text-matrix-green'
                                        : 'text-neon-pink'
                                    }`}
                                  >
                                    {reviewFeedback.message}
                                  </p>
                                ) : null}
                              </div>
                            </div>
                          ) : null}
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </article>

              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                <div className="flex items-center gap-3">
                  <ShieldAlert className="h-5 w-5 text-neon-purple" />
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('capabilities.title')}
                  </h2>
                </div>
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

                <div className="mt-5 flex flex-wrap gap-3">
                  <Link href="/analytics" className="text-sm font-mono text-neon-cyan underline underline-offset-4">
                    {t('guidance.links.analytics')}
                  </Link>
                  <Link href="/finance" className="text-sm font-mono text-neon-purple underline underline-offset-4">
                    {t('guidance.links.finance')}
                  </Link>
                  <Link href="/compliance" className="text-sm font-mono text-matrix-green underline underline-offset-4">
                    {t('guidance.links.compliance')}
                  </Link>
                </div>
              </article>
            </div>

            <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
              <div className="flex items-center gap-3 border-b border-grid-line/20 pb-4">
                <MessageSquareText className="h-5 w-5 text-neon-purple" />
                <div>
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('caseList.title')}
                  </h2>
                  <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                    {t('caseList.description')}
                  </p>
                </div>
              </div>

              <div className="mt-5 space-y-3">
                {state.cases.map((item) => (
                  <article
                    key={item.id}
                    className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4"
                  >
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                          {portalT(`caseKinds.${item.kind}.title`)}
                        </h3>
                        <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                          {portalT(`caseKinds.${item.kind}.description`)}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                          {portalT(`caseStatuses.${item.status}`)}
                        </p>
                        <p className="mt-2 text-xs font-mono text-muted-foreground">
                          {t('caseList.updatedAt', {
                            value: formatDateTime(item.updatedAt, locale),
                          })}
                        </p>
                      </div>
                    </div>

                    <div className="mt-4 space-y-4 border-t border-grid-line/20 pt-4">
                      {(item.notes ?? []).length > 0 ? (
                        <div>
                          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-purple/80">
                            {t('caseList.notesTitle')}
                          </p>
                          <ul className="mt-2 space-y-2">
                            {(item.notes ?? []).map((note) => (
                              <li
                                key={`${item.id}-${note}`}
                                className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-3 py-2 text-sm font-mono leading-6 text-muted-foreground"
                              >
                                {note}
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : null}

                      <div>
                        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                          {t('caseList.threadTitle')}
                        </p>
                        <div className="mt-2">
                          {renderThreadEvents(item, t('caseList.threadEmpty'))}
                        </div>
                      </div>

                      {canReplyToCase(item) || canMarkCaseReadyForOps(item) ? (
                        <div className="space-y-3 border-t border-grid-line/20 pt-4">
                          <label
                            htmlFor={`case-response-${item.id}`}
                            className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80"
                          >
                            {t('caseList.responseLabel')}
                          </label>
                          <textarea
                            id={`case-response-${item.id}`}
                            value={caseDrafts[item.id] ?? ''}
                            onChange={(event) => {
                              const value = event.target.value;
                              setCaseDrafts((current) => ({
                                ...current,
                                [item.id]: value,
                              }));
                              if (caseFeedback?.id === item.id) {
                                setCaseFeedback(null);
                              }
                            }}
                            placeholder={t('caseList.responsePlaceholder')}
                            className="min-h-28 w-full rounded-2xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-sm font-mono text-foreground outline-none transition focus:border-neon-cyan/40"
                          />
                          <div className="flex flex-wrap items-center gap-3">
                            {canReplyToCase(item) ? (
                              <Button
                                type="button"
                                disabled={
                                  caseReplyMutation.isPending
                                  || !(caseDrafts[item.id] ?? '').trim()
                                  || !workspaceId
                                }
                                onClick={() => {
                                  if (!workspaceId) {
                                    return;
                                  }
                                  setCaseFeedback(null);
                                  caseReplyMutation.mutate({
                                    targetWorkspaceId: workspaceId,
                                    caseId: item.id,
                                    message: (caseDrafts[item.id] ?? '').trim(),
                                  });
                                }}
                                className="bg-neon-cyan font-mono text-xs uppercase tracking-[0.18em] text-black hover:bg-neon-cyan/90"
                              >
                                <Send className="mr-2 h-4 w-4" />
                                {t('caseList.replyAction')}
                              </Button>
                            ) : null}

                            {canMarkCaseReadyForOps(item) ? (
                              <Button
                                type="button"
                                variant="outline"
                                disabled={
                                  caseReadyForOpsMutation.isPending
                                  || !(caseDrafts[item.id] ?? '').trim()
                                  || !workspaceId
                                }
                                onClick={() => {
                                  if (!workspaceId) {
                                    return;
                                  }
                                  setCaseFeedback(null);
                                  caseReadyForOpsMutation.mutate({
                                    targetWorkspaceId: workspaceId,
                                    caseId: item.id,
                                    message: (caseDrafts[item.id] ?? '').trim(),
                                  });
                                }}
                                className="border-neon-purple/40 bg-neon-purple/10 font-mono text-xs uppercase tracking-[0.18em] text-neon-purple hover:bg-neon-purple/20"
                              >
                                <CheckCheck className="mr-2 h-4 w-4" />
                                {t('caseList.readyAction')}
                              </Button>
                            ) : null}

                            {caseFeedback?.id === item.id ? (
                              <p
                                className={`text-xs font-mono ${
                                  caseFeedback.tone === 'success'
                                    ? 'text-matrix-green'
                                    : 'text-neon-pink'
                                }`}
                              >
                                {caseFeedback.message}
                              </p>
                            ) : null}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  </article>
                ))}
              </div>
            </article>
          </section>
        );
      }}
    </PartnerRouteGuard>
  );
}
