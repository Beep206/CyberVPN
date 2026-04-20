'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { useLocale, useTranslations } from 'next-intl';
import {
  AlertCircle,
  CheckCircle2,
  Circle,
  RotateCcw,
  Save,
  ShieldCheck,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/utils';
import { partnerPortalApi } from '@/lib/api/partner-portal';
import { useUser } from '@/stores/auth-store';
import { getPartnerRoleRouteAccess } from '@/features/partner-portal-state/lib/portal-access';
import { usePartnerPortalRuntimeState } from '@/features/partner-portal-state/lib/use-partner-portal-runtime-state';
import {
  buildPartnerApplicationDraftPayload,
  canResubmitPartnerApplication,
  canWithdrawPartnerApplication,
  getPartnerApplicationWorkspaceStatus,
  isPartnerApplicationSubmittedStatus,
  mapApplicationDraftResponseToLocalDraft,
} from '@/features/partner-onboarding/lib/application-contract';
import {
  EMPTY_PARTNER_APPLICATION_DRAFT,
  clearPartnerApplicationDraft,
  loadPartnerApplicationDraft,
  savePartnerApplicationDraft,
  type PartnerApplicationDraft,
  type PartnerPrimaryLane,
} from '@/features/partner-onboarding/lib/application-draft-storage';

const STAGE_KEYS = ['workspace', 'profile', 'compliance', 'review'] as const;
type StageKey = (typeof STAGE_KEYS)[number];

const FIELD_CLASS_NAME = 'w-full rounded-xl border border-grid-line/25 bg-terminal-bg/70 px-4 py-3 text-sm font-mono text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-neon-cyan/50 focus:ring-2 focus:ring-neon-cyan/20';
const TEXTAREA_CLASS_NAME = `${FIELD_CLASS_NAME} min-h-[140px] resize-y`;

function formatSavedAt(value: string | null, locale: string): string | null {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function getNextIncompleteStage(
  stageProgress: Record<StageKey, boolean>,
): StageKey {
  return STAGE_KEYS.find((stageKey) => !stageProgress[stageKey]) ?? 'review';
}

function isNotFoundError(error: unknown): boolean {
  return error instanceof AxiosError && error.response?.status === 404;
}

async function invalidatePartnerApplicationQueries(queryClient: ReturnType<typeof useQueryClient>) {
  await queryClient.invalidateQueries({
    queryKey: ['partner-portal', 'application-draft', 'current'],
  });
  await queryClient.invalidateQueries({
    queryKey: ['partner-portal', 'workspace-notifications'],
  });
  await queryClient.invalidateQueries({
    queryKey: ['partner-portal', 'session-bootstrap'],
  });
  await queryClient.invalidateQueries({
    queryKey: ['partner-portal', 'workspaces'],
  });
}

export function ApplicationFoundationPage() {
  const locale = useLocale();
  const t = useTranslations('Partner.application');
  const user = useUser();
  const queryClient = useQueryClient();
  const { state: portalState } = usePartnerPortalRuntimeState();

  const [activeStage, setActiveStage] = useState<StageKey>('workspace');
  const [localDraft, setLocalDraft] = useState<PartnerApplicationDraft>(
    () => loadPartnerApplicationDraft() ?? EMPTY_PARTNER_APPLICATION_DRAFT,
  );
  const [hasLocalEdits, setHasLocalEdits] = useState(false);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [actionFeedback, setActionFeedback] = useState<{
    tone: 'success' | 'error';
    message: string;
  } | null>(null);
  const autoCreateTriggeredRef = useRef(false);

  const applicationDraftQuery = useQuery({
    queryKey: ['partner-portal', 'application-draft', 'current'],
    queryFn: async () => {
      const response = await partnerPortalApi.getCurrentApplicationDraft();
      return response.data;
    },
    staleTime: 30_000,
    retry: false,
  });

  const currentDraftResponse = applicationDraftQuery.data ?? null;
  const currentWorkspaceStatus = getPartnerApplicationWorkspaceStatus(currentDraftResponse);
  const isSubmitted = isPartnerApplicationSubmittedStatus(currentWorkspaceStatus);
  const canResubmit = canResubmitPartnerApplication(currentWorkspaceStatus);
  const canWithdraw = canWithdrawPartnerApplication(currentWorkspaceStatus);
  const currentDraftId = currentDraftResponse?.draft.id ?? null;

  const routeAccess = getPartnerRoleRouteAccess('application', portalState);
  const isReadOnly = routeAccess === 'read';

  const canonicalDraft = useMemo(
    () => (
      currentDraftResponse
        ? mapApplicationDraftResponseToLocalDraft(currentDraftResponse, user?.email)
        : null
    ),
    [currentDraftResponse, user?.email],
  );

  const effectiveDraft = useMemo<PartnerApplicationDraft>(() => ({
    ...(!hasLocalEdits && canonicalDraft ? canonicalDraft : localDraft),
    contactEmail: (
      (!hasLocalEdits && canonicalDraft ? canonicalDraft : localDraft).contactEmail
      || user?.email
      || ''
    ),
  }), [canonicalDraft, hasLocalEdits, localDraft, user?.email]);

  useEffect(() => {
    if (!canonicalDraft || hasLocalEdits) {
      return;
    }

    savePartnerApplicationDraft(canonicalDraft);
  }, [canonicalDraft, hasLocalEdits]);

  const createDraftMutation = useMutation({
    mutationFn: async (nextDraft: PartnerApplicationDraft) => {
      const response = await partnerPortalApi.createApplicationDraft(
        buildPartnerApplicationDraftPayload({
          ...nextDraft,
          reviewReady: false,
        }),
      );
      return response.data;
    },
    onSuccess: async (response) => {
      const nextDraft = mapApplicationDraftResponseToLocalDraft(response, user?.email);
      setLocalDraft(nextDraft);
      savePartnerApplicationDraft(nextDraft);
      setHasLocalEdits(false);
      setValidationMessage(null);
      queryClient.setQueryData(['partner-portal', 'application-draft', 'current'], response);
      await invalidatePartnerApplicationQueries(queryClient);
    },
    onError: (error) => {
      setActionFeedback({
        tone: 'error',
        message: error instanceof Error ? error.message : t('submitFeedback.error'),
      });
    },
  });

  useEffect(() => {
    if (autoCreateTriggeredRef.current || !user?.id || !isNotFoundError(applicationDraftQuery.error)) {
      return;
    }

    autoCreateTriggeredRef.current = true;
    createDraftMutation.mutate(effectiveDraft);
  }, [
    applicationDraftQuery.error,
    createDraftMutation,
    effectiveDraft,
    user?.id,
  ]);

  const saveDraftMutation = useMutation({
    mutationFn: async (nextDraft: PartnerApplicationDraft) => {
      const payload = buildPartnerApplicationDraftPayload({
        ...nextDraft,
        reviewReady: false,
      });
      if (currentDraftId) {
        const response = await partnerPortalApi.updateApplicationDraft(currentDraftId, payload);
        return response.data;
      }
      const response = await partnerPortalApi.createApplicationDraft(payload);
      return response.data;
    },
    onSuccess: async (response) => {
      const nextDraft = mapApplicationDraftResponseToLocalDraft(response, user?.email);
      setLocalDraft(nextDraft);
      savePartnerApplicationDraft(nextDraft);
      setHasLocalEdits(false);
      setValidationMessage(null);
      setActionFeedback({
        tone: 'success',
        message: t('saveFeedback.saved'),
      });
      queryClient.setQueryData(['partner-portal', 'application-draft', 'current'], response);
      await invalidatePartnerApplicationQueries(queryClient);
    },
    onError: (error) => {
      setActionFeedback({
        tone: 'error',
        message: error instanceof Error ? error.message : t('saveFeedback.error'),
      });
    },
  });

  const submitDraftMutation = useMutation({
    mutationFn: async (nextDraft: PartnerApplicationDraft) => {
      const payload = buildPartnerApplicationDraftPayload({
        ...nextDraft,
        reviewReady: true,
      });
      const savedDraftResponse = currentDraftId
        ? await partnerPortalApi.updateApplicationDraft(currentDraftId, payload)
        : await partnerPortalApi.createApplicationDraft(payload);
      const savedDraft = savedDraftResponse.data;
      const savedStatus = getPartnerApplicationWorkspaceStatus(savedDraft);
      const response = canResubmitPartnerApplication(savedStatus)
        ? await partnerPortalApi.resubmitApplicationDraft(savedDraft.draft.id)
        : await partnerPortalApi.submitApplicationDraft(savedDraft.draft.id);
      return {
        response: response.data,
        wasResubmission: canResubmitPartnerApplication(savedStatus),
      };
    },
    onSuccess: async ({ response, wasResubmission }) => {
      const nextDraft = mapApplicationDraftResponseToLocalDraft(response, user?.email);
      setLocalDraft(nextDraft);
      savePartnerApplicationDraft(nextDraft);
      setHasLocalEdits(false);
      setValidationMessage(null);
      setActiveStage('review');
      setActionFeedback({
        tone: 'success',
        message: wasResubmission
          ? t('submitFeedback.resubmitted')
          : t('submitFeedback.submitted'),
      });
      queryClient.setQueryData(['partner-portal', 'application-draft', 'current'], response);
      await invalidatePartnerApplicationQueries(queryClient);
    },
    onError: (error) => {
      setActionFeedback({
        tone: 'error',
        message: error instanceof Error ? error.message : t('submitFeedback.error'),
      });
    },
  });

  const withdrawDraftMutation = useMutation({
    mutationFn: async () => {
      if (!currentDraftId) {
        throw new Error(t('submitFeedback.workspaceRequired'));
      }
      const response = await partnerPortalApi.withdrawApplicationDraft(currentDraftId);
      return response.data;
    },
    onSuccess: async (response) => {
      const nextDraft = mapApplicationDraftResponseToLocalDraft(response, user?.email);
      setLocalDraft(nextDraft);
      savePartnerApplicationDraft(nextDraft);
      setHasLocalEdits(false);
      setValidationMessage(null);
      setActionFeedback({
        tone: 'success',
        message: t('submitFeedback.withdrawn'),
      });
      queryClient.setQueryData(['partner-portal', 'application-draft', 'current'], response);
      await invalidatePartnerApplicationQueries(queryClient);
    },
    onError: (error) => {
      setActionFeedback({
        tone: 'error',
        message: error instanceof Error ? error.message : t('submitFeedback.error'),
      });
    },
  });

  const stageProgress = useMemo<Record<StageKey, boolean>>(() => ({
    workspace: Boolean(effectiveDraft.workspaceName && effectiveDraft.country && effectiveDraft.primaryLane),
    profile: Boolean(
      effectiveDraft.contactName
      && effectiveDraft.contactEmail
      && effectiveDraft.website
      && effectiveDraft.businessDescription
      && effectiveDraft.acquisitionChannels,
    ),
    compliance: effectiveDraft.complianceAccepted,
    review: isSubmitted || effectiveDraft.reviewReady,
  }), [effectiveDraft, isSubmitted]);

  const profileCompletionCount = Object.values(stageProgress).filter(Boolean).length;
  const allFoundationStagesComplete =
    stageProgress.workspace && stageProgress.profile && stageProgress.compliance;
  const savedAt = formatSavedAt(effectiveDraft.updatedAt, locale);
  const openReviewRequests = currentDraftResponse?.review_requests ?? [];

  const primaryLaneOptions: Array<{
    value: PartnerPrimaryLane;
    label: string;
    description: string;
  }> = [
    {
      value: 'creator_affiliate',
      label: t('laneOptions.creatorAffiliate.label'),
      description: t('laneOptions.creatorAffiliate.description'),
    },
    {
      value: 'performance_media',
      label: t('laneOptions.performanceMedia.label'),
      description: t('laneOptions.performanceMedia.description'),
    },
    {
      value: 'reseller_api',
      label: t('laneOptions.resellerApi.label'),
      description: t('laneOptions.resellerApi.description'),
    },
  ];

  const isMutationPending =
    createDraftMutation.isPending
    || saveDraftMutation.isPending
    || submitDraftMutation.isPending
    || withdrawDraftMutation.isPending;

  const statusToneClass = currentWorkspaceStatus === 'needs_info'
    ? 'border-neon-pink/30 bg-neon-pink/10 text-neon-pink'
    : isSubmitted
      ? 'border-matrix-green/30 bg-matrix-green/10 text-matrix-green'
      : 'border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan';

  const statusLabel = currentWorkspaceStatus === 'needs_info'
    ? t('status.actionRequired')
    : isSubmitted
      ? t('status.submitted')
      : t('status.draft');

  const handleFieldChange = <
    Key extends keyof PartnerApplicationDraft,
  >(
    key: Key,
    value: PartnerApplicationDraft[Key],
  ) => {
    const nextDraft = {
      ...effectiveDraft,
      [key]: value,
      reviewReady: false,
      updatedAt: new Date().toISOString(),
    };
    setLocalDraft(nextDraft);
    savePartnerApplicationDraft(nextDraft);
    setHasLocalEdits(true);
    setActionFeedback(null);
    setValidationMessage(null);
  };

  const handleSaveDraft = () => {
    saveDraftMutation.mutate(effectiveDraft);
  };

  const handleResetDraft = () => {
    if (currentDraftResponse) {
      const nextDraft = mapApplicationDraftResponseToLocalDraft(currentDraftResponse, user?.email);
      setLocalDraft(nextDraft);
      savePartnerApplicationDraft(nextDraft);
    } else {
      clearPartnerApplicationDraft();
      setLocalDraft({
        ...EMPTY_PARTNER_APPLICATION_DRAFT,
        contactEmail: user?.email || '',
      });
    }
    setHasLocalEdits(false);
    setActionFeedback(null);
    setValidationMessage(null);
    setActiveStage('workspace');
  };

  const handleAdvanceStage = () => {
    const currentIndex = STAGE_KEYS.indexOf(activeStage);
    if (currentIndex < STAGE_KEYS.length - 1) {
      setActiveStage(STAGE_KEYS[currentIndex + 1]);
    }
  };

  const handleSubmit = () => {
    if (!allFoundationStagesComplete) {
      setValidationMessage(t('review.validation'));
      setActiveStage(getNextIncompleteStage(stageProgress));
      return;
    }
    submitDraftMutation.mutate(effectiveDraft);
  };

  const handleWithdraw = () => {
    withdrawDraftMutation.mutate();
  };

  return (
    <section className="space-y-6">
      <header className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <span className={cn('inline-flex rounded-full border px-3 py-1 text-[11px] font-mono uppercase tracking-[0.2em]', statusToneClass)}>
                {statusLabel}
              </span>
              <span className="inline-flex rounded-full border border-grid-line/25 bg-terminal-surface/40 px-3 py-1 text-[11px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
                {t('status.backendLinked')}
              </span>
            </div>
            <div>
              <p className="text-[11px] font-mono uppercase tracking-[0.24em] text-neon-cyan/80">
                {t('eyebrow')}
              </p>
              <h1 className="mt-2 text-2xl font-display tracking-[0.16em] text-white md:text-3xl">
                {t('title')}
              </h1>
              <p className="mt-3 max-w-3xl text-sm font-mono leading-6 text-muted-foreground">
                {t('subtitle')}
              </p>
            </div>
          </div>

          <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4 text-sm font-mono text-muted-foreground lg:w-[320px]">
            <div className="flex items-center justify-between gap-3">
              <span>{t('summary.progressLabel')}</span>
              <span className="text-neon-cyan">{profileCompletionCount}/4</span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-terminal-bg/80">
              <div
                className="h-full rounded-full bg-gradient-to-r from-neon-cyan to-matrix-green transition-[width]"
                style={{ width: `${(profileCompletionCount / 4) * 100}%` }}
              />
            </div>
            <p className="mt-3 text-xs leading-5">
              {savedAt
                ? t('summary.savedAt', { value: savedAt })
                : t('summary.notSaved')}
            </p>
          </div>
        </div>
      </header>

      <div className="grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-4 shadow-[0_0_24px_rgba(0,255,255,0.04)]">
          <div className="mb-4 border-b border-grid-line/20 pb-3">
            <h2 className="text-sm font-display uppercase tracking-[0.18em] text-white">
              {t('stages.title')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('stages.description')}
            </p>
          </div>

          <div className="space-y-2">
            {STAGE_KEYS.map((stageKey, index) => {
              const isComplete = stageProgress[stageKey];
              const isActive = activeStage === stageKey;

              return (
                <button
                  key={stageKey}
                  type="button"
                  onClick={() => setActiveStage(stageKey)}
                  className={cn(
                    'flex w-full items-start gap-3 rounded-2xl border px-4 py-3 text-left transition-colors',
                    isActive
                      ? 'border-neon-cyan/40 bg-neon-cyan/10'
                      : 'border-grid-line/20 bg-terminal-bg/50 hover:border-neon-cyan/25 hover:bg-terminal-bg/70',
                  )}
                >
                  <span className="mt-0.5 text-neon-cyan">
                    {isComplete ? (
                      <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                    ) : (
                      <Circle className="h-4 w-4" aria-hidden="true" />
                    )}
                  </span>
                  <span className="space-y-1">
                    <span className="block text-[11px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
                      {t('stages.stageNumber', { value: index + 1 })}
                    </span>
                    <span className="block text-sm font-display uppercase tracking-[0.16em] text-white">
                      {t(`stages.items.${stageKey}.label`)}
                    </span>
                    <span className="block text-xs font-mono leading-5 text-muted-foreground">
                      {t(`stages.items.${stageKey}.description`)}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        </aside>

        <div className="space-y-6">
          <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
            {isReadOnly ? (
              <div className="mb-5 rounded-xl border border-grid-line/20 bg-terminal-surface/35 px-4 py-3 text-sm font-mono text-muted-foreground">
                {t('readOnlyMode')}
              </div>
            ) : null}
            <div className="mb-6 border-b border-grid-line/20 pb-4">
              <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                {t(`stages.items.${activeStage}.label`)}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t(`panels.${activeStage}.intro`)}
              </p>
            </div>

            <fieldset disabled={isReadOnly || isMutationPending} className="space-y-5">
              {activeStage === 'workspace' ? (
                <>
                  <div className="grid gap-5 md:grid-cols-2">
                    <label className="space-y-2">
                      <span className="text-sm font-mono text-muted-foreground">{t('fields.workspaceName')}</span>
                      <input
                        className={FIELD_CLASS_NAME}
                        value={effectiveDraft.workspaceName}
                        onChange={(event) => handleFieldChange('workspaceName', event.target.value)}
                        placeholder={t('placeholders.workspaceName')}
                      />
                    </label>
                    <label className="space-y-2">
                      <span className="text-sm font-mono text-muted-foreground">{t('fields.country')}</span>
                      <input
                        className={FIELD_CLASS_NAME}
                        value={effectiveDraft.country}
                        onChange={(event) => handleFieldChange('country', event.target.value)}
                        placeholder={t('placeholders.country')}
                      />
                    </label>
                  </div>

                  <div className="space-y-3">
                    <span className="block text-sm font-mono text-muted-foreground">{t('fields.primaryLane')}</span>
                    <div className="grid gap-3 md:grid-cols-3">
                      {primaryLaneOptions.map((option) => (
                        <button
                          key={option.value}
                          type="button"
                          onClick={() => handleFieldChange('primaryLane', option.value)}
                          className={cn(
                            'rounded-2xl border p-4 text-left transition-colors',
                            effectiveDraft.primaryLane === option.value
                              ? 'border-neon-cyan/40 bg-neon-cyan/10'
                              : 'border-grid-line/20 bg-terminal-surface/30 hover:border-neon-cyan/25',
                          )}
                        >
                          <span className="block text-sm font-display uppercase tracking-[0.16em] text-white">
                            {option.label}
                          </span>
                          <span className="mt-2 block text-xs font-mono leading-5 text-muted-foreground">
                            {option.description}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              ) : null}

              {activeStage === 'profile' ? (
                <>
                  <div className="grid gap-5 md:grid-cols-2">
                    <label className="space-y-2">
                      <span className="text-sm font-mono text-muted-foreground">{t('fields.contactName')}</span>
                      <input
                        className={FIELD_CLASS_NAME}
                        value={effectiveDraft.contactName}
                        onChange={(event) => handleFieldChange('contactName', event.target.value)}
                        placeholder={t('placeholders.contactName')}
                      />
                    </label>
                    <label className="space-y-2">
                      <span className="text-sm font-mono text-muted-foreground">{t('fields.contactEmail')}</span>
                      <input
                        className={FIELD_CLASS_NAME}
                        type="email"
                        value={effectiveDraft.contactEmail}
                        onChange={(event) => handleFieldChange('contactEmail', event.target.value)}
                        placeholder={t('placeholders.contactEmail')}
                      />
                    </label>
                  </div>

                  <label className="space-y-2">
                    <span className="text-sm font-mono text-muted-foreground">{t('fields.website')}</span>
                    <input
                      className={FIELD_CLASS_NAME}
                      value={effectiveDraft.website}
                      onChange={(event) => handleFieldChange('website', event.target.value)}
                      placeholder={t('placeholders.website')}
                    />
                  </label>

                  <label className="space-y-2">
                    <span className="text-sm font-mono text-muted-foreground">{t('fields.businessDescription')}</span>
                    <textarea
                      className={TEXTAREA_CLASS_NAME}
                      value={effectiveDraft.businessDescription}
                      onChange={(event) => handleFieldChange('businessDescription', event.target.value)}
                      placeholder={t('placeholders.businessDescription')}
                    />
                  </label>

                  <label className="space-y-2">
                    <span className="text-sm font-mono text-muted-foreground">{t('fields.acquisitionChannels')}</span>
                    <textarea
                      className={TEXTAREA_CLASS_NAME}
                      value={effectiveDraft.acquisitionChannels}
                      onChange={(event) => handleFieldChange('acquisitionChannels', event.target.value)}
                      placeholder={t('placeholders.acquisitionChannels')}
                    />
                  </label>
                </>
              ) : null}

              {activeStage === 'compliance' ? (
                <div className="space-y-4">
                  <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                    <p className="text-sm font-mono leading-6 text-muted-foreground">
                      {t('panels.compliance.notice')}
                    </p>
                    <ul className="mt-4 space-y-2 text-sm font-mono text-muted-foreground">
                      <li>{t('panels.compliance.items.disclosure')}</li>
                      <li>{t('panels.compliance.items.fakeReviews')}</li>
                      <li>{t('panels.compliance.items.brandBidding')}</li>
                      <li>{t('panels.compliance.items.audit')}</li>
                    </ul>
                  </div>

                  <label className="flex items-start gap-3 rounded-2xl border border-grid-line/20 bg-terminal-surface/30 p-4">
                    <input
                      type="checkbox"
                      checked={effectiveDraft.complianceAccepted}
                      onChange={(event) => handleFieldChange('complianceAccepted', event.target.checked)}
                      className="mt-1 h-4 w-4 rounded border-grid-line bg-terminal-bg text-neon-cyan focus:ring-neon-cyan/50"
                    />
                    <span className="text-sm font-mono leading-6 text-muted-foreground">
                      {t('fields.complianceAccepted')}
                    </span>
                  </label>
                </div>
              ) : null}

              {activeStage === 'review' ? (
                <div className="space-y-5">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                      <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {t('review.workspaceSummary')}
                      </h3>
                      <dl className="mt-3 space-y-2 text-sm font-mono text-muted-foreground">
                        <div className="flex items-center justify-between gap-3">
                          <dt>{t('fields.workspaceName')}</dt>
                          <dd className="text-right text-foreground">{effectiveDraft.workspaceName || '—'}</dd>
                        </div>
                        <div className="flex items-center justify-between gap-3">
                          <dt>{t('fields.country')}</dt>
                          <dd className="text-right text-foreground">{effectiveDraft.country || '—'}</dd>
                        </div>
                        <div className="flex items-center justify-between gap-3">
                          <dt>{t('fields.primaryLane')}</dt>
                          <dd className="text-right text-foreground">
                            {effectiveDraft.primaryLane ? t(`laneSummary.${effectiveDraft.primaryLane}`) : '—'}
                          </dd>
                        </div>
                      </dl>
                    </div>

                    <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                      <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {t('review.readinessSummary')}
                      </h3>
                      <ul className="mt-3 space-y-2 text-sm font-mono text-muted-foreground">
                        {STAGE_KEYS.slice(0, 3).map((stageKey) => (
                          <li key={stageKey} className="flex items-center justify-between gap-3">
                            <span>{t(`stages.items.${stageKey}.label`)}</span>
                            <span className={stageProgress[stageKey] ? 'text-matrix-green' : 'text-neon-pink'}>
                              {stageProgress[stageKey] ? t('review.complete') : t('review.missing')}
                            </span>
                          </li>
                        ))}
                        <li className="flex items-center justify-between gap-3">
                          <span>{t('review.currentStatus')}</span>
                          <span className="text-foreground">{statusLabel}</span>
                        </li>
                      </ul>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-neon-cyan/20 bg-neon-cyan/5 p-4 text-sm font-mono leading-6 text-muted-foreground">
                    {t('review.backendNote')}
                  </div>

                  {openReviewRequests.length > 0 ? (
                    <div className="rounded-2xl border border-neon-pink/20 bg-neon-pink/5 p-4">
                      <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {t('review.requestedInfoTitle')}
                      </h3>
                      <ul className="mt-3 space-y-3 text-sm font-mono text-muted-foreground">
                        {openReviewRequests.map((request) => {
                          const requiredFields = request.required_fields ?? [];

                          return (
                            <li key={request.id} className="rounded-xl border border-grid-line/20 bg-terminal-surface/30 p-3">
                              <p className="text-foreground">{request.message}</p>
                              {requiredFields.length > 0 ? (
                                <p className="mt-2">
                                  {t('review.requiredFields', {
                                    value: requiredFields.join(', '),
                                  })}
                                </p>
                              ) : null}
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </fieldset>

            {validationMessage ? (
              <div className="mt-5 flex items-start gap-2 rounded-xl border border-neon-pink/25 bg-neon-pink/10 p-3 text-sm font-mono text-neon-pink">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                <span>{validationMessage}</span>
              </div>
            ) : null}

            <div className="mt-6 flex flex-col gap-3 border-t border-grid-line/20 pt-5 md:flex-row md:items-center md:justify-between">
              <div className="flex flex-wrap gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleSaveDraft}
                  disabled={isReadOnly || isMutationPending}
                  className="border-grid-line/30 bg-terminal-surface/35 font-mono text-xs uppercase tracking-[0.18em] hover:border-neon-cyan/50"
                >
                  <Save className="mr-2 h-4 w-4" aria-hidden="true" />
                  {t('actions.saveDraft')}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleResetDraft}
                  disabled={isMutationPending}
                  className="border-grid-line/30 bg-terminal-surface/35 font-mono text-xs uppercase tracking-[0.18em] hover:border-neon-pink/50"
                >
                  <RotateCcw className="mr-2 h-4 w-4" aria-hidden="true" />
                  {t('actions.resetDraft')}
                </Button>
                {canWithdraw && isSubmitted ? (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleWithdraw}
                    disabled={isReadOnly || isMutationPending}
                    className="border-grid-line/30 bg-terminal-surface/35 font-mono text-xs uppercase tracking-[0.18em] hover:border-neon-pink/50"
                  >
                    {t('actions.withdraw')}
                  </Button>
                ) : null}
              </div>

              <div className="flex flex-wrap gap-3">
                {activeStage !== 'workspace' ? (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setActiveStage(STAGE_KEYS[Math.max(0, STAGE_KEYS.indexOf(activeStage) - 1)])}
                    className="border-grid-line/30 bg-terminal-surface/35 font-mono text-xs uppercase tracking-[0.18em]"
                  >
                    {t('actions.back')}
                  </Button>
                ) : null}

                {activeStage !== 'review' ? (
                  <Button
                    type="button"
                    onClick={handleAdvanceStage}
                    disabled={isReadOnly || isMutationPending}
                    className="bg-neon-cyan text-black hover:bg-neon-cyan/90 font-mono text-xs uppercase tracking-[0.18em]"
                  >
                    {t('actions.next')}
                  </Button>
                ) : (
                  <Button
                    type="button"
                    onClick={handleSubmit}
                    disabled={isReadOnly || isMutationPending}
                    className="bg-matrix-green text-black hover:bg-matrix-green/90 font-mono text-xs uppercase tracking-[0.18em]"
                  >
                    {canResubmit ? (
                      <RotateCcw className="mr-2 h-4 w-4" aria-hidden="true" />
                    ) : (
                      <ShieldCheck className="mr-2 h-4 w-4" aria-hidden="true" />
                    )}
                    {canResubmit ? t('actions.resubmit') : t('actions.markReady')}
                  </Button>
                )}
              </div>
            </div>

            {actionFeedback ? (
              <p className={cn(
                'mt-4 text-sm font-mono',
                actionFeedback.tone === 'success' ? 'text-matrix-green' : 'text-neon-pink',
              )}>
                {actionFeedback.message}
              </p>
            ) : null}
          </article>

          <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
            <h2 className="text-sm font-display uppercase tracking-[0.18em] text-white">
              {t('linkedWorkspaces.title')}
            </h2>
            <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
              {t('linkedWorkspaces.description')}
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Link
                href="/organization"
                className="inline-flex items-center text-sm font-mono text-neon-cyan underline underline-offset-4"
              >
                {t('linkedWorkspaces.organizationLink')}
              </Link>
              <Link
                href="/settings"
                className="inline-flex items-center text-sm font-mono text-neon-purple underline underline-offset-4"
              >
                {t('linkedWorkspaces.settingsLink')}
              </Link>
            </div>
          </article>
        </div>
      </div>
    </section>
  );
}
