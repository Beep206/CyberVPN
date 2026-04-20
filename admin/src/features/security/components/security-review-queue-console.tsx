'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { RefreshCw, ShieldAlert } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { authApi } from '@/lib/api/auth';
import {
  securityApi,
  type CreateGovernanceActionRequest,
  type ResolveRiskReviewRequest,
} from '@/lib/api/security';
import { SecurityEmptyState } from '@/features/security/components/security-empty-state';
import { SecurityPageShell } from '@/features/security/components/security-page-shell';
import { SecurityStatusChip } from '@/features/security/components/security-status-chip';
import {
  formatDateTime,
  getErrorMessage,
  shortId,
} from '@/features/security/lib/formatting';

type SecurityTranslate = (key: string, values?: Record<string, string | number>) => string;
type RiskReviewQueueItem = Awaited<
  ReturnType<typeof securityApi.listRiskReviewQueue>
>['data'][number];
type RiskReviewDetail = Awaited<
  ReturnType<typeof securityApi.getRiskReview>
>['data'];

const GOVERNANCE_ACTION_OPTIONS = [
  'payout_freeze',
  'code_suspension',
  'reserve_extension',
  'traffic_probation',
  'creative_restriction',
  'manual_override',
] as const;

const RESOLUTION_STATUS_OPTIONS = ['resolved', 'dismissed'] as const;
const REVIEW_DECISION_OPTIONS = ['allow', 'block', 'monitor', 'hold'] as const;
const ATTACHMENT_TYPE_OPTIONS = ['document', 'screenshot', 'log_export', 'external_reference'] as const;

function humanizeToken(value: string | null | undefined) {
  if (!value) {
    return '--';
  }

  return value
    .split(/[_-]+/g)
    .filter(Boolean)
    .map((chunk) => `${chunk.slice(0, 1).toUpperCase()}${chunk.slice(1)}`)
    .join(' ');
}

function toneForRiskLevel(value: string | null | undefined) {
  if (value === 'high' || value === 'critical') return 'danger' as const;
  if (value === 'medium') return 'warning' as const;
  return 'info' as const;
}

function toneForReviewStatus(value: string | null | undefined) {
  if (value === 'resolved') return 'success' as const;
  if (value === 'dismissed') return 'neutral' as const;
  return 'warning' as const;
}

function toneForDecision(value: string | null | undefined) {
  if (value === 'allow') return 'success' as const;
  if (value === 'block' || value === 'hold') return 'danger' as const;
  if (value === 'monitor') return 'warning' as const;
  return 'neutral' as const;
}

function parseJsonInput(value: string, fallback: string): { ok: true; value: Record<string, unknown> } | { ok: false; error: string } {
  const trimmed = value.trim();
  if (!trimmed) {
    return { ok: true, value: {} };
  }

  try {
    const parsed = JSON.parse(trimmed) as unknown;
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return { ok: true, value: parsed as Record<string, unknown> };
    }
    return { ok: false, error: fallback };
  } catch {
    return { ok: false, error: fallback };
  }
}

function QueueItemCard({
  item,
  locale,
  t,
  isActive,
  onSelect,
}: {
  item: RiskReviewQueueItem;
  locale: string;
  t: SecurityTranslate;
  isActive: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-2xl border p-4 text-left transition-colors ${
        isActive
          ? 'border-neon-pink/35 bg-neon-pink/10'
          : 'border-grid-line/20 bg-terminal-bg/45 hover:border-grid-line/40 hover:bg-terminal-bg/60'
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
            {humanizeToken(item.review.review_type)}
          </p>
          <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('reviewQueue.queue.reviewRef', {
              reviewId: shortId(item.review.id),
              subjectId: shortId(item.subject.id),
            })}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <SecurityStatusChip
            label={humanizeToken(item.subject.risk_level)}
            tone={toneForRiskLevel(item.subject.risk_level)}
          />
          <SecurityStatusChip
            label={humanizeToken(item.review.status)}
            tone={toneForReviewStatus(item.review.status)}
          />
          <SecurityStatusChip
            label={humanizeToken(item.review.decision)}
            tone={toneForDecision(item.review.decision)}
          />
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('reviewQueue.queue.subject')}
          </p>
          <p className="mt-2 break-all text-sm font-mono text-white">
            {item.subject.principal_subject}
          </p>
        </div>
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('reviewQueue.queue.updatedAt')}
          </p>
          <p className="mt-2 text-sm font-mono text-white">
            {formatDateTime(item.review.updated_at, locale)}
          </p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-3 text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
        <span>{t('reviewQueue.queue.attachments', { count: item.attachment_count })}</span>
        <span>{t('reviewQueue.queue.governanceActions', { count: item.governance_action_count })}</span>
      </div>
    </button>
  );
}

export function SecurityReviewQueueConsole() {
  const t = useTranslations('AdminSecurity');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const [selectedReviewId, setSelectedReviewId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [attachmentType, setAttachmentType] = useState<string>('document');
  const [attachmentStorageKey, setAttachmentStorageKey] = useState('');
  const [attachmentFileName, setAttachmentFileName] = useState('');
  const [attachmentMetadata, setAttachmentMetadata] = useState('{\n  "content_type": "application/pdf"\n}');
  const [actionType, setActionType] = useState<string>('payout_freeze');
  const [actionReason, setActionReason] = useState('');
  const [actionTargetType, setActionTargetType] = useState('');
  const [actionTargetRef, setActionTargetRef] = useState('');
  const [actionPayload, setActionPayload] = useState('{\n  "scope": "review"\n}');
  const [actionApplyNow, setActionApplyNow] = useState(true);
  const [resolutionDecision, setResolutionDecision] = useState<string>('monitor');
  const [resolutionStatus, setResolutionStatus] = useState<string>('resolved');
  const [resolutionReason, setResolutionReason] = useState('');
  const [resolutionEvidence, setResolutionEvidence] = useState('{\n  "source": "admin_review_queue"\n}');

  const sessionQuery = useQuery({
    queryKey: ['security', 'session'],
    queryFn: async () => {
      const response = await authApi.session();
      return response.data;
    },
    staleTime: 30_000,
  });

  const queueQuery = useQuery({
    queryKey: ['security', 'review-queue'],
    queryFn: async () => {
      const response = await securityApi.listRiskReviewQueue();
      return response.data;
    },
    staleTime: 15_000,
  });
  const effectiveSelectedReviewId = queueQuery.data?.some(
    (item) => item.review.id === selectedReviewId,
  )
    ? selectedReviewId
    : (queueQuery.data?.[0]?.review.id ?? null);

  const detailQuery = useQuery({
    queryKey: ['security', 'review-queue', effectiveSelectedReviewId, 'detail'],
    queryFn: async () => {
      const response = await securityApi.getRiskReview(effectiveSelectedReviewId!);
      return response.data;
    },
    enabled: Boolean(effectiveSelectedReviewId),
    staleTime: 15_000,
  });

  const canMutate = ['admin', 'super_admin'].includes(sessionQuery.data?.role ?? '');

  async function refreshReviewData() {
    await queryClient.invalidateQueries({ queryKey: ['security', 'review-queue'] });
    if (effectiveSelectedReviewId) {
      await queryClient.invalidateQueries({
        queryKey: ['security', 'review-queue', effectiveSelectedReviewId, 'detail'],
      });
    }
  }

  const attachmentMutation = useMutation({
    mutationFn: async () => {
      if (!effectiveSelectedReviewId) {
        throw new Error(t('reviewQueue.feedback.selectReview'));
      }
      const parsedMetadata = parseJsonInput(
        attachmentMetadata,
        t('reviewQueue.feedback.invalidAttachmentMetadata'),
      );
      if (!parsedMetadata.ok) {
        throw new Error(parsedMetadata.error);
      }

      const response = await securityApi.attachRiskReviewAttachment(effectiveSelectedReviewId, {
        attachment_type: attachmentType,
        storage_key: attachmentStorageKey.trim(),
        file_name: attachmentFileName.trim() || null,
        metadata: parsedMetadata.value,
      });
      return response.data;
    },
    onSuccess: async () => {
      await refreshReviewData();
      setAttachmentStorageKey('');
      setAttachmentFileName('');
      setFeedback(t('reviewQueue.feedback.attachmentCreated'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const governanceActionMutation = useMutation({
    mutationFn: async () => {
      const detail = detailQuery.data;
      if (!detail) {
        throw new Error(t('reviewQueue.feedback.selectReview'));
      }
      const parsedPayload = parseJsonInput(
        actionPayload,
        t('reviewQueue.feedback.invalidGovernancePayload'),
      );
      if (!parsedPayload.ok) {
        throw new Error(parsedPayload.error);
      }

      const response = await securityApi.createGovernanceAction({
        risk_subject_id: detail.subject.id,
        risk_review_id: detail.review.id,
        action_type: actionType as CreateGovernanceActionRequest['action_type'],
        reason: actionReason.trim(),
        target_type: actionTargetType.trim() || null,
        target_ref: actionTargetRef.trim() || null,
        payload: parsedPayload.value,
        apply_now: actionApplyNow,
      });
      return response.data;
    },
    onSuccess: async () => {
      await refreshReviewData();
      setActionReason('');
      setActionTargetType('');
      setActionTargetRef('');
      setFeedback(t('reviewQueue.feedback.governanceActionCreated'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const resolveMutation = useMutation({
    mutationFn: async () => {
      if (!effectiveSelectedReviewId) {
        throw new Error(t('reviewQueue.feedback.selectReview'));
      }
      const parsedEvidence = parseJsonInput(
        resolutionEvidence,
        t('reviewQueue.feedback.invalidResolutionEvidence'),
      );
      if (!parsedEvidence.ok) {
        throw new Error(parsedEvidence.error);
      }

      const response = await securityApi.resolveRiskReview(effectiveSelectedReviewId, {
        decision: resolutionDecision as ResolveRiskReviewRequest['decision'],
        resolution_status: resolutionStatus as ResolveRiskReviewRequest['resolution_status'],
        resolution_reason: resolutionReason.trim() || null,
        resolution_evidence: parsedEvidence.value,
      });
      return response.data;
    },
    onSuccess: async () => {
      await refreshReviewData();
      setResolutionReason('');
      setFeedback(t('reviewQueue.feedback.reviewResolved'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const queueItems = queueQuery.data ?? [];
  const blockingCount = queueItems.filter(
    (item) => item.review.decision === 'block' || item.review.decision === 'hold',
  ).length;
  const attachmentCount = queueItems.reduce((sum, item) => sum + item.attachment_count, 0);
  const governanceActionCount = queueItems.reduce(
    (sum, item) => sum + item.governance_action_count,
    0,
  );

  return (
    <SecurityPageShell
      eyebrow={t('reviewQueue.eyebrow')}
      title={t('reviewQueue.title')}
      description={t('reviewQueue.description')}
      icon={ShieldAlert}
      actions={(
        <Button
          magnetic={false}
          variant="ghost"
          onClick={() => {
            void refreshReviewData();
          }}
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          {t('common.refresh')}
        </Button>
      )}
      metrics={[
        {
          label: t('reviewQueue.metrics.openReviews'),
          value: String(queueItems.length),
          hint: t('reviewQueue.metrics.openReviewsHint'),
          tone: queueItems.length ? 'warning' : 'success',
        },
        {
          label: t('reviewQueue.metrics.blocking'),
          value: String(blockingCount),
          hint: t('reviewQueue.metrics.blockingHint'),
          tone: blockingCount ? 'danger' : 'success',
        },
        {
          label: t('reviewQueue.metrics.attachments'),
          value: String(attachmentCount),
          hint: t('reviewQueue.metrics.attachmentsHint'),
          tone: attachmentCount ? 'info' : 'neutral',
        },
        {
          label: t('reviewQueue.metrics.governanceActions'),
          value: String(governanceActionCount),
          hint: t('reviewQueue.metrics.governanceActionsHint'),
          tone: governanceActionCount ? 'warning' : 'neutral',
        },
      ]}
    >
      {feedback ? (
        <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-foreground">
          {feedback}
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-12">
        <section className="space-y-4 xl:col-span-5">
          <header className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('reviewQueue.queue.title')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('reviewQueue.queue.description')}
            </p>
          </header>

          {queueQuery.isLoading ? (
            <div className="grid gap-3">
              {Array.from({ length: 3 }).map((_, index) => (
                <div
                  key={index}
                  className="h-36 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))}
            </div>
          ) : queueQuery.isError ? (
            <div className="rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
              {getErrorMessage(queueQuery.error, t('reviewQueue.queue.loadError'))}
            </div>
          ) : queueItems.length ? (
            <div className="space-y-3">
              {queueItems.map((item) => (
                <QueueItemCard
                  key={item.review.id}
                  item={item}
                  locale={locale}
                  t={t}
                  isActive={item.review.id === effectiveSelectedReviewId}
                  onSelect={() => {
                    setFeedback(null);
                    setSelectedReviewId(item.review.id);
                  }}
                />
              ))}
            </div>
          ) : (
            <SecurityEmptyState label={t('reviewQueue.queue.empty')} />
          )}
        </section>

        <section className="space-y-6 xl:col-span-7">
          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('reviewQueue.detail.title')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('reviewQueue.detail.description')}
            </p>

            {detailQuery.isLoading ? (
              <div className="mt-5 h-48 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45" />
            ) : detailQuery.isError ? (
              <div className="mt-5 rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
                {getErrorMessage(detailQuery.error, t('reviewQueue.detail.loadError'))}
              </div>
            ) : detailQuery.data ? (
              <ReviewDetailPanel detail={detailQuery.data} locale={locale} t={t} />
            ) : (
              <div className="mt-5">
                <SecurityEmptyState label={t('reviewQueue.detail.empty')} />
              </div>
            )}
          </article>

          <div className="grid gap-6 xl:grid-cols-2">
            <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
              <h3 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('reviewQueue.attachments.title')}
              </h3>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('reviewQueue.attachments.description')}
              </p>

              <div className="mt-5 space-y-4">
                <label className="block space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('reviewQueue.attachments.fields.type')}
                  </span>
                  <select
                    value={attachmentType}
                    onChange={(event) => setAttachmentType(event.target.value)}
                    className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm"
                  >
                    {ATTACHMENT_TYPE_OPTIONS.map((option) => (
                      <option key={option} value={option}>
                        {humanizeToken(option)}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('reviewQueue.attachments.fields.storageKey')}
                  </span>
                  <Input
                    value={attachmentStorageKey}
                    onChange={(event) => setAttachmentStorageKey(event.target.value)}
                    placeholder={t('reviewQueue.attachments.fields.storageKeyPlaceholder')}
                  />
                </label>

                <label className="block space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('reviewQueue.attachments.fields.fileName')}
                  </span>
                  <Input
                    value={attachmentFileName}
                    onChange={(event) => setAttachmentFileName(event.target.value)}
                    placeholder={t('reviewQueue.attachments.fields.fileNamePlaceholder')}
                  />
                </label>

                <label className="block space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('reviewQueue.attachments.fields.metadata')}
                  </span>
                  <textarea
                    rows={5}
                    value={attachmentMetadata}
                    onChange={(event) => setAttachmentMetadata(event.target.value)}
                    className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm"
                  />
                </label>

                <Button
                  type="button"
                  magnetic={false}
                  disabled={!canMutate || !effectiveSelectedReviewId || attachmentMutation.isPending || !attachmentStorageKey.trim()}
                  onClick={() => {
                    setFeedback(null);
                    void attachmentMutation.mutateAsync();
                  }}
                >
                  {t('reviewQueue.attachments.submit')}
                </Button>
              </div>
            </article>

            <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
              <h3 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('reviewQueue.governance.title')}
              </h3>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('reviewQueue.governance.description')}
              </p>

              <div className="mt-5 space-y-4">
                <label className="block space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('reviewQueue.governance.fields.actionType')}
                  </span>
                  <select
                    value={actionType}
                    onChange={(event) => setActionType(event.target.value)}
                    className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm"
                  >
                    {GOVERNANCE_ACTION_OPTIONS.map((option) => (
                      <option key={option} value={option}>
                        {humanizeToken(option)}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('reviewQueue.governance.fields.reason')}
                  </span>
                  <textarea
                    rows={4}
                    value={actionReason}
                    onChange={(event) => setActionReason(event.target.value)}
                    className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm"
                    placeholder={t('reviewQueue.governance.fields.reasonPlaceholder')}
                  />
                </label>

                <div className="grid gap-4 md:grid-cols-2">
                  <label className="block space-y-2">
                    <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('reviewQueue.governance.fields.targetType')}
                    </span>
                    <Input
                      value={actionTargetType}
                      onChange={(event) => setActionTargetType(event.target.value)}
                      placeholder={t('reviewQueue.governance.fields.targetTypePlaceholder')}
                    />
                  </label>
                  <label className="block space-y-2">
                    <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('reviewQueue.governance.fields.targetRef')}
                    </span>
                    <Input
                      value={actionTargetRef}
                      onChange={(event) => setActionTargetRef(event.target.value)}
                      placeholder={t('reviewQueue.governance.fields.targetRefPlaceholder')}
                    />
                  </label>
                </div>

                <label className="block space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('reviewQueue.governance.fields.payload')}
                  </span>
                  <textarea
                    rows={5}
                    value={actionPayload}
                    onChange={(event) => setActionPayload(event.target.value)}
                    className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm"
                  />
                </label>

                <label className="flex items-center gap-3 rounded-xl border border-grid-line/20 bg-terminal-bg/40 px-3 py-2 text-sm font-mono text-white">
                  <input
                    type="checkbox"
                    checked={actionApplyNow}
                    onChange={(event) => setActionApplyNow(event.target.checked)}
                    className="h-4 w-4"
                  />
                  {t('reviewQueue.governance.fields.applyNow')}
                </label>

                <Button
                  type="button"
                  magnetic={false}
                  disabled={!canMutate || !detailQuery.data || governanceActionMutation.isPending || !actionReason.trim()}
                  onClick={() => {
                    setFeedback(null);
                    void governanceActionMutation.mutateAsync();
                  }}
                >
                  {t('reviewQueue.governance.submit')}
                </Button>
              </div>
            </article>
          </div>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h3 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('reviewQueue.resolve.title')}
            </h3>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('reviewQueue.resolve.description')}
            </p>

            <div className="mt-5 grid gap-4 xl:grid-cols-2">
              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('reviewQueue.resolve.fields.decision')}
                </span>
                <select
                  value={resolutionDecision}
                  onChange={(event) => setResolutionDecision(event.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm"
                >
                  {REVIEW_DECISION_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {humanizeToken(option)}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('reviewQueue.resolve.fields.status')}
                </span>
                <select
                  value={resolutionStatus}
                  onChange={(event) => setResolutionStatus(event.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm"
                >
                  {RESOLUTION_STATUS_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {humanizeToken(option)}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="mt-4 grid gap-4 xl:grid-cols-2">
              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('reviewQueue.resolve.fields.reason')}
                </span>
                <textarea
                  rows={4}
                  value={resolutionReason}
                  onChange={(event) => setResolutionReason(event.target.value)}
                  className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm"
                  placeholder={t('reviewQueue.resolve.fields.reasonPlaceholder')}
                />
              </label>

              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('reviewQueue.resolve.fields.evidence')}
                </span>
                <textarea
                  rows={4}
                  value={resolutionEvidence}
                  onChange={(event) => setResolutionEvidence(event.target.value)}
                  className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm"
                />
              </label>
            </div>

            <div className="mt-5 flex justify-end">
              <Button
                type="button"
                magnetic={false}
                disabled={!canMutate || !effectiveSelectedReviewId || resolveMutation.isPending}
                onClick={() => {
                  setFeedback(null);
                  void resolveMutation.mutateAsync();
                }}
              >
                {t('reviewQueue.resolve.submit')}
              </Button>
            </div>
          </article>
        </section>
      </div>
    </SecurityPageShell>
  );
}

function ReviewDetailPanel({
  detail,
  locale,
  t,
}: {
  detail: RiskReviewDetail;
  locale: string;
  t: SecurityTranslate;
}) {
  return (
    <div className="mt-5 space-y-5">
      <div className="grid gap-4 xl:grid-cols-2">
        <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('reviewQueue.detail.review')}
          </p>
          <p className="mt-3 text-sm font-display uppercase tracking-[0.14em] text-white">
            {humanizeToken(detail.review.review_type)}
          </p>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {detail.review.reason}
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <SecurityStatusChip
              label={humanizeToken(detail.review.status)}
              tone={toneForReviewStatus(detail.review.status)}
            />
            <SecurityStatusChip
              label={humanizeToken(detail.review.decision)}
              tone={toneForDecision(detail.review.decision)}
            />
          </div>
        </div>

        <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('reviewQueue.detail.subject')}
          </p>
          <p className="mt-3 break-all text-sm font-mono text-white">
            {detail.subject.principal_subject}
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <SecurityStatusChip
              label={humanizeToken(detail.subject.risk_level)}
              tone={toneForRiskLevel(detail.subject.risk_level)}
            />
            <SecurityStatusChip
              label={humanizeToken(detail.subject.status)}
              tone="info"
            />
          </div>
          <p className="mt-4 text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
            {t('reviewQueue.detail.updatedAt')}
          </p>
          <p className="mt-2 text-sm font-mono text-white">
            {formatDateTime(detail.review.updated_at, locale)}
          </p>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
          <div className="flex items-center justify-between gap-3">
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
              {t('reviewQueue.detail.attachmentsTitle')}
            </p>
            <SecurityStatusChip
              label={String(detail.attachments.length)}
              tone={detail.attachments.length ? 'info' : 'neutral'}
            />
          </div>
          <div className="mt-4 space-y-3">
            {detail.attachments.length ? detail.attachments.map((attachment) => (
              <div
                key={attachment.id}
                className="rounded-xl border border-grid-line/20 bg-terminal-surface/35 p-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm font-mono text-white">
                    {attachment.file_name ?? attachment.storage_key}
                  </p>
                  <SecurityStatusChip
                    label={humanizeToken(attachment.attachment_type)}
                    tone="info"
                  />
                </div>
                <p className="mt-2 break-all text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                  {attachment.storage_key}
                </p>
              </div>
            )) : (
              <SecurityEmptyState label={t('reviewQueue.detail.noAttachments')} />
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
          <div className="flex items-center justify-between gap-3">
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
              {t('reviewQueue.detail.governanceTitle')}
            </p>
            <SecurityStatusChip
              label={String(detail.governance_actions.length)}
              tone={detail.governance_actions.length ? 'warning' : 'neutral'}
            />
          </div>
          <div className="mt-4 space-y-3">
            {detail.governance_actions.length ? detail.governance_actions.map((action) => (
              <div
                key={action.id}
                className="rounded-xl border border-grid-line/20 bg-terminal-surface/35 p-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm font-mono text-white">
                    {humanizeToken(action.action_type)}
                  </p>
                  <SecurityStatusChip
                    label={humanizeToken(action.status)}
                    tone={action.status === 'applied' ? 'success' : 'warning'}
                  />
                </div>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {action.reason}
                </p>
              </div>
            )) : (
              <SecurityEmptyState label={t('reviewQueue.detail.noGovernanceActions')} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
