'use client';

import { useDeferredValue, useState } from 'react';
import { AxiosError } from 'axios';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowUpRight,
  BriefcaseBusiness,
  CheckCheck,
  CircleSlash,
  Clock3,
  FolderClock,
  RefreshCw,
  ShieldAlert,
  UserRoundPlus,
  WalletCards,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { growthApi } from '@/lib/api/growth';
import {
  partnerOperationsApi,
  type PartnerPayoutAccountResponse,
} from '@/lib/api/partner-operations';
import { GrowthEmptyState } from '@/features/growth/components/growth-empty-state';
import { GrowthPageShell } from '@/features/growth/components/growth-page-shell';
import { GrowthStatusChip } from '@/features/growth/components/growth-status-chip';
import {
  formatCurrencyAmount,
  formatDateTime,
  getErrorMessage,
  humanizeToken,
  shortId,
} from '@/features/growth/lib/formatting';

const WORKSPACE_STATUS_FILTERS = ['all', 'draft', 'submitted', 'under_review', 'approved_probation', 'active', 'restricted', 'suspended', 'rejected'] as const;

type WorkspaceStatusFilter = (typeof WORKSPACE_STATUS_FILTERS)[number];

function toneForWorkspaceStatus(value: string | null | undefined) {
  if (value === 'active' || value === 'approved_active') return 'success' as const;
  if (value === 'approved_probation' || value === 'under_review') return 'warning' as const;
  if (value === 'rejected' || value === 'suspended' || value === 'terminated') return 'danger' as const;
  return 'info' as const;
}

function toneForBoolean(value: boolean) {
  return value ? ('success' as const) : ('neutral' as const);
}

function toneForCount(value: number) {
  if (value > 0) return 'warning' as const;
  return 'neutral' as const;
}

function toneForPayoutAccount(account: PartnerPayoutAccountResponse) {
  if (account.account_status === 'archived' || account.account_status === 'suspended') {
    return 'danger' as const;
  }
  if (account.verification_status === 'verified') {
    return 'success' as const;
  }
  return 'warning' as const;
}

function isNotFoundError(error: unknown) {
  return error instanceof AxiosError && error.response?.status === 404;
}

export function PartnerOperationsConsole() {
  const t = useTranslations('Growth');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const [userId, setUserId] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<WorkspaceStatusFilter>('all');
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [decisionReasonCode, setDecisionReasonCode] = useState('manual_review');
  const [decisionReasonSummary, setDecisionReasonSummary] = useState('');
  const [requestInfoMessage, setRequestInfoMessage] = useState('');
  const [suspendReasonCode, setSuspendReasonCode] = useState('manual_finance_review');
  const [instructionRejectReasonCode, setInstructionRejectReasonCode] = useState('maker_checker_rejected');
  const deferredSearch = useDeferredValue(search);

  const applicationsQuery = useQuery({
    queryKey: ['partner-ops', 'applications'],
    queryFn: async () => {
      const response = await partnerOperationsApi.listApplications();
      return response.data;
    },
    staleTime: 15_000,
  });

  const workspacesQuery = useQuery({
    queryKey: ['partner-ops', 'workspaces', deferredSearch, statusFilter],
    queryFn: async () => {
      const response = await partnerOperationsApi.listWorkspaces({
        search: deferredSearch.trim() || undefined,
        workspace_status: statusFilter === 'all' ? undefined : statusFilter,
        limit: 50,
        offset: 0,
      });
      return response.data;
    },
    staleTime: 15_000,
  });

  const effectiveSelectedWorkspaceId = selectedWorkspaceId
    ?? applicationsQuery.data?.[0]?.workspace.id
    ?? workspacesQuery.data?.[0]?.id
    ?? null;

  const workspaceDetailQuery = useQuery({
    queryKey: ['partner-ops', 'workspace', effectiveSelectedWorkspaceId],
    queryFn: async () => {
      const response = await partnerOperationsApi.getWorkspace(effectiveSelectedWorkspaceId!);
      return response.data;
    },
    enabled: Boolean(effectiveSelectedWorkspaceId),
    staleTime: 15_000,
  });

  const applicationDetailQuery = useQuery({
    queryKey: ['partner-ops', 'application', effectiveSelectedWorkspaceId],
    queryFn: async () => {
      try {
        const response = await partnerOperationsApi.getApplication(effectiveSelectedWorkspaceId!);
        return response.data;
      } catch (error) {
        if (isNotFoundError(error)) {
          return null;
        }
        throw error;
      }
    },
    enabled: Boolean(effectiveSelectedWorkspaceId),
    staleTime: 15_000,
    retry: false,
  });

  const programsQuery = useQuery({
    queryKey: ['partner-ops', 'programs', effectiveSelectedWorkspaceId],
    queryFn: async () => {
      const response = await partnerOperationsApi.getWorkspacePrograms(effectiveSelectedWorkspaceId!);
      return response.data;
    },
    enabled: Boolean(effectiveSelectedWorkspaceId),
    staleTime: 15_000,
  });

  const codesQuery = useQuery({
    queryKey: ['partner-ops', 'codes', effectiveSelectedWorkspaceId],
    queryFn: async () => {
      const response = await partnerOperationsApi.listWorkspaceCodes(effectiveSelectedWorkspaceId!);
      return response.data;
    },
    enabled: Boolean(effectiveSelectedWorkspaceId),
    staleTime: 15_000,
  });

  const reviewRequestsQuery = useQuery({
    queryKey: ['partner-ops', 'review-requests', effectiveSelectedWorkspaceId],
    queryFn: async () => {
      const response = await partnerOperationsApi.listWorkspaceReviewRequests(effectiveSelectedWorkspaceId!);
      return response.data;
    },
    enabled: Boolean(effectiveSelectedWorkspaceId),
    staleTime: 15_000,
  });

  const casesQuery = useQuery({
    queryKey: ['partner-ops', 'cases', effectiveSelectedWorkspaceId],
    queryFn: async () => {
      const response = await partnerOperationsApi.listWorkspaceCases(effectiveSelectedWorkspaceId!);
      return response.data;
    },
    enabled: Boolean(effectiveSelectedWorkspaceId),
    staleTime: 15_000,
  });

  const trafficQuery = useQuery({
    queryKey: ['partner-ops', 'traffic', effectiveSelectedWorkspaceId],
    queryFn: async () => {
      const response = await partnerOperationsApi.listTrafficDeclarations({
        partner_account_id: effectiveSelectedWorkspaceId!,
        limit: 20,
        offset: 0,
      });
      return response.data;
    },
    enabled: Boolean(effectiveSelectedWorkspaceId),
    staleTime: 15_000,
  });

  const creativeQuery = useQuery({
    queryKey: ['partner-ops', 'creative', effectiveSelectedWorkspaceId],
    queryFn: async () => {
      const response = await partnerOperationsApi.listCreativeApprovals({
        partner_account_id: effectiveSelectedWorkspaceId!,
        limit: 20,
        offset: 0,
      });
      return response.data;
    },
    enabled: Boolean(effectiveSelectedWorkspaceId),
    staleTime: 15_000,
  });

  const payoutAccountsQuery = useQuery({
    queryKey: ['partner-ops', 'payout-accounts', effectiveSelectedWorkspaceId],
    queryFn: async () => {
      const response = await partnerOperationsApi.listPayoutAccounts({
        partner_account_id: effectiveSelectedWorkspaceId!,
        limit: 20,
        offset: 0,
      });
      return response.data;
    },
    enabled: Boolean(effectiveSelectedWorkspaceId),
    staleTime: 15_000,
  });

  const payoutInstructionsQuery = useQuery({
    queryKey: ['partner-ops', 'payout-instructions', effectiveSelectedWorkspaceId],
    queryFn: async () => {
      const response = await partnerOperationsApi.listPayoutInstructions({
        partner_account_id: effectiveSelectedWorkspaceId!,
        limit: 20,
        offset: 0,
      });
      return response.data;
    },
    enabled: Boolean(effectiveSelectedWorkspaceId),
    staleTime: 15_000,
  });

  const payoutExecutionsQuery = useQuery({
    queryKey: ['partner-ops', 'payout-executions', effectiveSelectedWorkspaceId],
    queryFn: async () => {
      const response = await partnerOperationsApi.listPayoutExecutions({
        partner_account_id: effectiveSelectedWorkspaceId!,
        limit: 20,
        offset: 0,
      });
      return response.data;
    },
    enabled: Boolean(effectiveSelectedWorkspaceId),
    staleTime: 15_000,
  });

  async function refreshWorkspaceSlice(targetWorkspaceId: string | null) {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['partner-ops', 'applications'] }),
      queryClient.invalidateQueries({ queryKey: ['partner-ops', 'workspaces'] }),
      queryClient.invalidateQueries({ queryKey: ['partner-ops', 'workspace', targetWorkspaceId] }),
      queryClient.invalidateQueries({ queryKey: ['partner-ops', 'application', targetWorkspaceId] }),
      queryClient.invalidateQueries({ queryKey: ['partner-ops', 'programs', targetWorkspaceId] }),
      queryClient.invalidateQueries({ queryKey: ['partner-ops', 'codes', targetWorkspaceId] }),
      queryClient.invalidateQueries({ queryKey: ['partner-ops', 'review-requests', targetWorkspaceId] }),
      queryClient.invalidateQueries({ queryKey: ['partner-ops', 'cases', targetWorkspaceId] }),
      queryClient.invalidateQueries({ queryKey: ['partner-ops', 'traffic', targetWorkspaceId] }),
      queryClient.invalidateQueries({ queryKey: ['partner-ops', 'creative', targetWorkspaceId] }),
      queryClient.invalidateQueries({ queryKey: ['partner-ops', 'payout-accounts', targetWorkspaceId] }),
      queryClient.invalidateQueries({ queryKey: ['partner-ops', 'payout-instructions', targetWorkspaceId] }),
      queryClient.invalidateQueries({ queryKey: ['partner-ops', 'payout-executions', targetWorkspaceId] }),
    ]);
  }

  const promoteMutation = useMutation({
    mutationFn: growthApi.promotePartner,
    onSuccess: async (response) => {
      setFeedback(t('partners.feedback.promoted', { userId: String(response.data.user_id ?? '') }));
      setUserId('');
      await refreshWorkspaceSlice(effectiveSelectedWorkspaceId);
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const applicationDecisionMutation = useMutation({
    mutationFn: async (action: 'approve_probation' | 'waitlist' | 'reject') => {
      if (!effectiveSelectedWorkspaceId) {
        throw new Error(t('partners.feedback.selectWorkspace'));
      }
      const payload = {
        reason_code: decisionReasonCode.trim() || 'manual_review',
        reason_summary: decisionReasonSummary.trim() || t('partners.defaults.reasonSummary'),
      };
      if (action === 'approve_probation') {
        return partnerOperationsApi.approveApplicationProbation(effectiveSelectedWorkspaceId, payload);
      }
      if (action === 'waitlist') {
        return partnerOperationsApi.waitlistApplication(effectiveSelectedWorkspaceId, payload);
      }
      return partnerOperationsApi.rejectApplication(effectiveSelectedWorkspaceId, payload);
    },
    onSuccess: async (_, action) => {
      await refreshWorkspaceSlice(effectiveSelectedWorkspaceId);
      const feedbackKey = action === 'approve_probation'
        ? 'applicationApproved'
        : action === 'waitlist'
          ? 'applicationWaitlisted'
          : 'applicationRejected';
      setFeedback(t(`partners.feedback.${feedbackKey}`));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const requestInfoMutation = useMutation({
    mutationFn: async () => {
      if (!effectiveSelectedWorkspaceId) {
        throw new Error(t('partners.feedback.selectWorkspace'));
      }
      return partnerOperationsApi.requestApplicationInfo(effectiveSelectedWorkspaceId, {
        request_kind: 'application_follow_up',
        message: requestInfoMessage.trim() || t('partners.defaults.requestInfoMessage'),
        required_fields: [],
        required_attachments: [],
      });
    },
    onSuccess: async () => {
      await refreshWorkspaceSlice(effectiveSelectedWorkspaceId);
      setRequestInfoMessage('');
      setFeedback(t('partners.feedback.infoRequested'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const laneDecisionMutation = useMutation({
    mutationFn: async ({
      laneApplicationId,
      action,
      targetStatus,
    }: {
      laneApplicationId: string;
      action: 'approve' | 'decline';
      targetStatus?: 'approved_probation' | 'approved_active';
    }) => {
      if (!effectiveSelectedWorkspaceId) {
        throw new Error(t('partners.feedback.selectWorkspace'));
      }
      const payload = {
        reason_code: decisionReasonCode.trim() || 'lane_review',
        reason_summary: decisionReasonSummary.trim() || t('partners.defaults.reasonSummary'),
      };
      if (action === 'approve') {
        return partnerOperationsApi.approveLaneApplication(
          effectiveSelectedWorkspaceId,
          laneApplicationId,
          payload,
          { target_status: targetStatus ?? 'approved_probation' },
        );
      }
      return partnerOperationsApi.declineLaneApplication(
        effectiveSelectedWorkspaceId,
        laneApplicationId,
        payload,
      );
    },
    onSuccess: async (_, variables) => {
      await refreshWorkspaceSlice(effectiveSelectedWorkspaceId);
      setFeedback(
        variables.action === 'approve'
          ? t('partners.feedback.laneApproved')
          : t('partners.feedback.laneDeclined'),
      );
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const payoutAccountMutation = useMutation({
    mutationFn: async ({
      payoutAccountId,
      action,
    }: {
      payoutAccountId: string;
      action: 'verify' | 'suspend' | 'archive';
    }) => {
      if (action === 'verify') {
        return partnerOperationsApi.verifyPayoutAccount(payoutAccountId);
      }
      if (action === 'suspend') {
        return partnerOperationsApi.suspendPayoutAccount(payoutAccountId, {
          reason_code: suspendReasonCode.trim() || 'manual_finance_review',
        });
      }
      return partnerOperationsApi.archivePayoutAccount(payoutAccountId, {
        reason_code: suspendReasonCode.trim() || 'manual_archive',
      });
    },
    onSuccess: async (_, variables) => {
      await refreshWorkspaceSlice(effectiveSelectedWorkspaceId);
      setFeedback(
        variables.action === 'verify'
          ? t('partners.feedback.payoutAccountVerified')
          : variables.action === 'suspend'
            ? t('partners.feedback.payoutAccountSuspended')
            : t('partners.feedback.payoutAccountArchived'),
      );
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const payoutInstructionMutation = useMutation({
    mutationFn: async ({
      payoutInstructionId,
      action,
    }: {
      payoutInstructionId: string;
      action: 'approve' | 'reject';
    }) => {
      if (action === 'approve') {
        return partnerOperationsApi.approvePayoutInstruction(payoutInstructionId);
      }
      return partnerOperationsApi.rejectPayoutInstruction(payoutInstructionId, {
        rejection_reason_code: instructionRejectReasonCode.trim() || 'maker_checker_rejected',
      });
    },
    onSuccess: async (_, variables) => {
      await refreshWorkspaceSlice(effectiveSelectedWorkspaceId);
      setFeedback(
        variables.action === 'approve'
          ? t('partners.feedback.payoutInstructionApproved')
          : t('partners.feedback.payoutInstructionRejected'),
      );
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  async function handlePromoteSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await promoteMutation.mutateAsync({ user_id: userId.trim() });
  }

  const applications = applicationsQuery.data ?? [];
  const workspaces = workspacesQuery.data ?? [];
  const selectedWorkspace = workspaceDetailQuery.data
    ?? workspaces.find((item) => item.id === effectiveSelectedWorkspaceId)
    ?? null;
  const selectedApplication = applicationDetailQuery.data;
  const selectedPrograms = programsQuery.data;
  const selectedLaneMemberships = selectedPrograms?.lane_memberships ?? [];
  const selectedCodes = codesQuery.data ?? [];
  const selectedReviewRequests = reviewRequestsQuery.data ?? [];
  const selectedCases = casesQuery.data ?? [];
  const selectedTrafficDeclarations = trafficQuery.data ?? [];
  const selectedCreativeApprovals = creativeQuery.data ?? [];
  const selectedPayoutAccounts = payoutAccountsQuery.data ?? [];
  const selectedPayoutInstructions = payoutInstructionsQuery.data ?? [];
  const selectedPayoutExecutions = payoutExecutionsQuery.data ?? [];
  const pendingLaneDecisionCount = applications.reduce(
    (sum, item) => sum + (item.lane_statuses ?? []).filter((status) => !status.startsWith('approved')).length,
    0,
  );
  const financeReviewCount = selectedPayoutAccounts.filter(
    (item) => item.verification_status !== 'verified' || item.account_status !== 'active',
  ).length + selectedPayoutInstructions.filter(
    (item) => item.instruction_status === 'pending_approval' || item.instruction_status === 'rejected',
  ).length;

  return (
    <GrowthPageShell
      eyebrow={t('partners.eyebrow')}
      title={t('partners.title')}
      description={t('partners.description')}
      icon={BriefcaseBusiness}
      actions={
        <>
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t('partners.fields.search')}
            className="w-[16rem]"
          />
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as WorkspaceStatusFilter)}
            className="h-10 rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-3 text-sm font-mono text-white outline-none"
          >
            {WORKSPACE_STATUS_FILTERS.map((value) => (
              <option key={value} value={value}>
                {value === 'all'
                  ? t('partners.fields.allStatuses')
                  : humanizeToken(value)}
              </option>
            ))}
          </select>
          <Button
            type="button"
            variant="ghost"
            magnetic={false}
            onClick={() => {
              void refreshWorkspaceSlice(effectiveSelectedWorkspaceId);
            }}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            {t('common.refresh')}
          </Button>
        </>
      }
      metrics={[
        {
          label: t('partners.metrics.applications'),
          value: String(applications.length),
          hint: t('partners.metrics.applicationsHint'),
          tone: applications.length > 0 ? 'warning' : 'neutral',
        },
        {
          label: t('partners.metrics.workspaces'),
          value: String(workspaces.length),
          hint: t('partners.metrics.workspacesHint'),
          tone: workspaces.length > 0 ? 'success' : 'neutral',
        },
        {
          label: t('partners.metrics.laneDecisions'),
          value: String(pendingLaneDecisionCount),
          hint: t('partners.metrics.laneDecisionsHint'),
          tone: toneForCount(pendingLaneDecisionCount),
        },
        {
          label: t('partners.metrics.financeReview'),
          value: String(financeReviewCount),
          hint: t('partners.metrics.financeReviewHint'),
          tone: toneForCount(financeReviewCount),
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <form
          onSubmit={handlePromoteSubmit}
          className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-3"
        >
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('partners.formTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('partners.formDescription')}
              </p>
            </div>
            <GrowthStatusChip label={t('partners.liveDirectory')} tone="success" />
          </div>

          {feedback ? (
            <div className="mt-5 rounded-xl border border-neon-cyan/20 bg-neon-cyan/10 px-4 py-3 text-sm font-mono text-neon-cyan">
              {feedback}
            </div>
          ) : null}

          <label className="mt-5 block space-y-2">
            <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
              {t('partners.fields.userId')}
            </span>
            <Input
              required
              value={userId}
              onChange={(event) => setUserId(event.target.value)}
            />
          </label>

          <div className="mt-5 flex flex-wrap gap-3">
            <Button type="submit" magnetic={false} disabled={promoteMutation.isPending}>
              <UserRoundPlus className="mr-2 h-4 w-4" />
              {t('partners.promoteAction')}
            </Button>
            <Button
              type="button"
              variant="ghost"
              magnetic={false}
              onClick={() => {
                setUserId('');
                setFeedback(null);
              }}
            >
              {t('common.clear')}
            </Button>
          </div>
        </form>

        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('partners.queueTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('partners.queueDescription')}
              </p>
            </div>
            <GrowthStatusChip label={String(applications.length)} tone={toneForCount(applications.length)} />
          </div>

          <div className="mt-5 space-y-3">
            {applicationsQuery.isLoading ? (
              Array.from({ length: 4 }).map((_, index) => (
                <div
                  key={index}
                  className="h-24 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))
            ) : applications.length ? (
              applications.map((application) => {
                const isActive = application.workspace.id === effectiveSelectedWorkspaceId;
                return (
                  <button
                    key={application.workspace.id}
                    type="button"
                    onClick={() => setSelectedWorkspaceId(application.workspace.id)}
                    className={`w-full rounded-2xl border p-4 text-left transition-colors ${
                      isActive
                        ? 'border-neon-cyan/35 bg-neon-cyan/10'
                        : 'border-grid-line/20 bg-terminal-bg/45 hover:border-grid-line/40'
                    }`}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                          {application.workspace.display_name}
                        </p>
                        <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          #{shortId(application.workspace.id)} / {application.primary_lane
                            ? humanizeToken(application.primary_lane)
                            : t('partners.labels.noPrimaryLane')}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <GrowthStatusChip
                          label={humanizeToken(application.workspace.status)}
                          tone={toneForWorkspaceStatus(application.workspace.status)}
                        />
                        <GrowthStatusChip
                          label={application.review_ready ? t('partners.labels.reviewReady') : t('partners.labels.reviewPending')}
                          tone={toneForBoolean(application.review_ready)}
                        />
                      </div>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                      <GrowthStatusChip
                        label={t('partners.badges.reviewRequests', {
                          count: application.open_review_request_count,
                        })}
                        tone={toneForCount(application.open_review_request_count)}
                      />
                      {(application.lane_statuses ?? []).map((status) => (
                        <GrowthStatusChip
                          key={`${application.workspace.id}-${status}`}
                          label={humanizeToken(status)}
                          tone={toneForWorkspaceStatus(status)}
                        />
                      ))}
                    </div>

                    <p className="mt-4 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {formatDateTime(application.submitted_at ?? application.updated_at, locale)}
                    </p>
                  </button>
                );
              })
            ) : (
              <GrowthEmptyState label={t('partners.queueEmpty')} />
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('partners.inventoryTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('partners.inventoryDescription')}
              </p>
            </div>
            <GrowthStatusChip label={String(workspaces.length)} tone={toneForCount(workspaces.length)} />
          </div>

          <div className="mt-5 space-y-3">
            {workspacesQuery.isLoading ? (
              Array.from({ length: 4 }).map((_, index) => (
                <div
                  key={index}
                  className="h-20 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))
            ) : workspaces.length ? (
              workspaces.map((workspace) => {
                const isActive = workspace.id === effectiveSelectedWorkspaceId;
                return (
                  <button
                    key={workspace.id}
                    type="button"
                    onClick={() => setSelectedWorkspaceId(workspace.id)}
                    className={`w-full rounded-2xl border p-4 text-left transition-colors ${
                      isActive
                        ? 'border-neon-pink/35 bg-neon-pink/10'
                        : 'border-grid-line/20 bg-terminal-bg/45 hover:border-grid-line/40'
                    }`}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                          {workspace.display_name}
                        </p>
                        <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          @{workspace.account_key} / #{shortId(workspace.id)}
                        </p>
                      </div>
                      <GrowthStatusChip
                        label={humanizeToken(workspace.status)}
                        tone={toneForWorkspaceStatus(workspace.status)}
                      />
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                      <GrowthStatusChip
                        label={t('partners.badges.codes', { count: workspace.code_count })}
                        tone="info"
                      />
                      <GrowthStatusChip
                        label={t('partners.badges.activeCodes', { count: workspace.active_code_count })}
                        tone={workspace.active_code_count > 0 ? 'success' : 'neutral'}
                      />
                      <GrowthStatusChip
                        label={t('partners.badges.clients', { count: workspace.total_clients })}
                        tone="warning"
                      />
                      <GrowthStatusChip
                        label={formatCurrencyAmount(workspace.total_earned, 'USD', locale)}
                        tone={workspace.total_earned > 0 ? 'warning' : 'neutral'}
                      />
                    </div>
                  </button>
                );
              })
            ) : (
              <GrowthEmptyState label={t('partners.inventoryEmpty')} />
            )}
          </div>
        </section>
      </div>

      <div className="grid gap-6 xl:grid-cols-12">
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('partners.workspaceTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('partners.workspaceDescription')}
              </p>
            </div>
            {selectedWorkspace ? (
              <GrowthStatusChip
                label={humanizeToken(selectedWorkspace.status)}
                tone={toneForWorkspaceStatus(selectedWorkspace.status)}
              />
            ) : null}
          </div>

          {!selectedWorkspace ? (
            <div className="mt-5">
              <GrowthEmptyState label={t('partners.workspaceEmpty')} />
            </div>
          ) : (
            <div className="mt-5 space-y-5">
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                  {selectedWorkspace.display_name}
                </p>
                <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  @{selectedWorkspace.account_key} / #{shortId(selectedWorkspace.id)}
                </p>

                <div className="mt-4 flex flex-wrap gap-2">
                  <GrowthStatusChip
                    label={t('partners.badges.members', { count: selectedWorkspace.members.length })}
                    tone="info"
                  />
                  <GrowthStatusChip
                    label={t('partners.badges.codes', { count: selectedWorkspace.code_count })}
                    tone="info"
                  />
                  <GrowthStatusChip
                    label={t('partners.badges.clients', { count: selectedWorkspace.total_clients })}
                    tone="warning"
                  />
                </div>
              </div>

              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('partners.programsTitle')}
                  </p>
                  {selectedPrograms?.primary_lane_key ? (
                    <GrowthStatusChip
                      label={humanizeToken(selectedPrograms.primary_lane_key)}
                      tone="success"
                    />
                  ) : null}
                </div>

                <div className="mt-4 space-y-3">
                  {selectedLaneMemberships.length ? (
                    selectedLaneMemberships.map((lane) => (
                      <div
                        key={lane.lane_key}
                        className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-3"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-display uppercase tracking-[0.14em] text-white">
                              {humanizeToken(lane.lane_key)}
                            </p>
                            <p className="mt-2 text-xs font-mono text-muted-foreground">
                              {lane.owner_context_label}
                            </p>
                          </div>
                          <GrowthStatusChip
                            label={humanizeToken(lane.membership_status)}
                            tone={toneForWorkspaceStatus(lane.membership_status)}
                          />
                        </div>
                      </div>
                    ))
                  ) : (
                    <GrowthEmptyState label={t('partners.programsEmpty')} />
                  )}
                </div>
              </div>

              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('partners.codesTitle')}
                  </p>
                  <GrowthStatusChip
                    label={String(selectedCodes.length)}
                    tone={toneForCount(selectedCodes.length)}
                  />
                </div>
                <div className="mt-4 space-y-2">
                  {selectedCodes.length ? (
                    selectedCodes.slice(0, 6).map((code) => (
                      <div
                        key={code.id}
                        className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-grid-line/20 bg-terminal-surface/35 px-3 py-2"
                      >
                        <div>
                          <p className="text-sm font-mono uppercase tracking-[0.18em] text-white">
                            {code.code}
                          </p>
                          <p className="mt-1 text-xs font-mono text-muted-foreground">
                            {formatDateTime(code.created_at, locale)}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <GrowthStatusChip
                            label={`${code.markup_pct}%`}
                            tone="info"
                          />
                          <GrowthStatusChip
                            label={code.is_active ? t('partners.labels.active') : t('partners.labels.inactive')}
                            tone={code.is_active ? 'success' : 'danger'}
                          />
                        </div>
                      </div>
                    ))
                  ) : (
                    <GrowthEmptyState label={t('partners.codesEmpty')} />
                  )}
                </div>
              </div>
            </div>
          )}
        </section>

        <section className="space-y-6 xl:col-span-8">
          <div className="grid gap-6 xl:grid-cols-2">
            <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                    {t('partners.applicationTitle')}
                  </h2>
                  <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                    {t('partners.applicationDescription')}
                  </p>
                </div>
                {selectedApplication ? (
                  <GrowthStatusChip
                    label={humanizeToken(selectedApplication.workspace.status)}
                    tone={toneForWorkspaceStatus(selectedApplication.workspace.status)}
                  />
                ) : null}
              </div>

              {!selectedApplication ? (
                <div className="mt-5">
                  <GrowthEmptyState label={t('partners.applicationEmpty')} />
                </div>
              ) : (
                <div className="mt-5 space-y-4">
                  <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                          {selectedApplication.applicant?.login ?? t('partners.labels.noApplicant')}
                        </p>
                        <p className="mt-2 text-xs font-mono text-muted-foreground">
                          {selectedApplication.applicant?.email ?? '--'}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <GrowthStatusChip
                          label={selectedApplication.draft.review_ready ? t('partners.labels.reviewReady') : t('partners.labels.reviewPending')}
                          tone={toneForBoolean(selectedApplication.draft.review_ready)}
                        />
                        <GrowthStatusChip
                          label={selectedApplication.applicant?.is_email_verified ? t('partners.labels.emailVerified') : t('partners.labels.emailPending')}
                          tone={toneForBoolean(Boolean(selectedApplication.applicant?.is_email_verified))}
                        />
                      </div>
                    </div>

                    <div className="mt-4 grid gap-3 md:grid-cols-2">
                      <div>
                        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          {t('partners.labels.contact')}
                        </p>
                        <p className="mt-2 text-sm font-mono text-white">
                          {selectedApplication.draft.draft_payload.contact_name || '--'}
                        </p>
                      </div>
                      <div>
                        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          {t('partners.labels.website')}
                        </p>
                        <p className="mt-2 break-all text-sm font-mono text-white">
                          {selectedApplication.draft.draft_payload.website || '--'}
                        </p>
                      </div>
                      <div>
                        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          {t('partners.labels.country')}
                        </p>
                        <p className="mt-2 text-sm font-mono text-white">
                          {selectedApplication.draft.draft_payload.country || '--'}
                        </p>
                      </div>
                      <div>
                        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          {t('partners.labels.primaryLane')}
                        </p>
                        <p className="mt-2 text-sm font-mono text-white">
                          {selectedApplication.draft.draft_payload.primary_lane
                            ? humanizeToken(selectedApplication.draft.draft_payload.primary_lane)
                            : '--'}
                        </p>
                      </div>
                    </div>
                  </div>

                  <label className="block space-y-2">
                    <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('partners.fields.reasonCode')}
                    </span>
                    <Input
                      value={decisionReasonCode}
                      onChange={(event) => setDecisionReasonCode(event.target.value)}
                    />
                  </label>

                  <label className="block space-y-2">
                    <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('partners.fields.reasonSummary')}
                    </span>
                    <textarea
                      value={decisionReasonSummary}
                      onChange={(event) => setDecisionReasonSummary(event.target.value)}
                      className="min-h-24 w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                    />
                  </label>

                  <label className="block space-y-2">
                    <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('partners.fields.requestInfoMessage')}
                    </span>
                    <textarea
                      value={requestInfoMessage}
                      onChange={(event) => setRequestInfoMessage(event.target.value)}
                      className="min-h-24 w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                    />
                  </label>

                  <div className="flex flex-wrap gap-3">
                    <Button
                      type="button"
                      magnetic={false}
                      disabled={requestInfoMutation.isPending}
                      onClick={() => {
                        void requestInfoMutation.mutateAsync();
                      }}
                    >
                      <FolderClock className="mr-2 h-4 w-4" />
                      {t('partners.requestInfoAction')}
                    </Button>
                    <Button
                      type="button"
                      magnetic={false}
                      disabled={applicationDecisionMutation.isPending}
                      onClick={() => {
                        void applicationDecisionMutation.mutateAsync('approve_probation');
                      }}
                    >
                      <CheckCheck className="mr-2 h-4 w-4" />
                      {t('partners.approveProbationAction')}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      magnetic={false}
                      disabled={applicationDecisionMutation.isPending}
                      onClick={() => {
                        void applicationDecisionMutation.mutateAsync('waitlist');
                      }}
                    >
                      <Clock3 className="mr-2 h-4 w-4" />
                      {t('partners.waitlistAction')}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      magnetic={false}
                      disabled={applicationDecisionMutation.isPending}
                      onClick={() => {
                        void applicationDecisionMutation.mutateAsync('reject');
                      }}
                    >
                      <CircleSlash className="mr-2 h-4 w-4" />
                      {t('partners.rejectAction')}
                    </Button>
                  </div>

                  <div className="space-y-3">
                    {(selectedApplication.lane_applications ?? []).map((lane) => (
                      <div
                        key={lane.id}
                        className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                              {humanizeToken(lane.lane_key)}
                            </p>
                            <p className="mt-2 text-xs font-mono text-muted-foreground">
                              {lane.decision_summary || t('partners.labels.noDecisionSummary')}
                            </p>
                          </div>
                          <GrowthStatusChip
                            label={humanizeToken(lane.status)}
                            tone={toneForWorkspaceStatus(lane.status)}
                          />
                        </div>

                        <div className="mt-4 flex flex-wrap gap-3">
                          <Button
                            type="button"
                            magnetic={false}
                            disabled={laneDecisionMutation.isPending}
                            onClick={() => {
                              void laneDecisionMutation.mutateAsync({
                                laneApplicationId: lane.id,
                                action: 'approve',
                                targetStatus: 'approved_probation',
                              });
                            }}
                          >
                            {t('partners.approveLaneProbationAction')}
                          </Button>
                          <Button
                            type="button"
                            magnetic={false}
                            disabled={laneDecisionMutation.isPending}
                            onClick={() => {
                              void laneDecisionMutation.mutateAsync({
                                laneApplicationId: lane.id,
                                action: 'approve',
                                targetStatus: 'approved_active',
                              });
                            }}
                          >
                            {t('partners.approveLaneActiveAction')}
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            magnetic={false}
                            disabled={laneDecisionMutation.isPending}
                            onClick={() => {
                              void laneDecisionMutation.mutateAsync({
                                laneApplicationId: lane.id,
                                action: 'decline',
                              });
                            }}
                          >
                            {t('partners.declineLaneAction')}
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </section>

            <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                    {t('partners.financeTitle')}
                  </h2>
                  <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                    {t('partners.financeDescription')}
                  </p>
                </div>
                <GrowthStatusChip
                  label={String(selectedPayoutAccounts.length)}
                  tone={toneForCount(selectedPayoutAccounts.length)}
                />
              </div>

              <div className="mt-5 space-y-4">
                <label className="block space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('partners.fields.suspendReasonCode')}
                  </span>
                  <Input
                    value={suspendReasonCode}
                    onChange={(event) => setSuspendReasonCode(event.target.value)}
                  />
                </label>

                <label className="block space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('partners.fields.rejectReasonCode')}
                  </span>
                  <Input
                    value={instructionRejectReasonCode}
                    onChange={(event) => setInstructionRejectReasonCode(event.target.value)}
                  />
                </label>

                <div className="space-y-3">
                  {selectedPayoutAccounts.length ? (
                    selectedPayoutAccounts.map((account) => (
                      <div
                        key={account.id}
                        className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                              {account.display_label}
                            </p>
                            <p className="mt-2 text-xs font-mono text-muted-foreground">
                              {account.masked_destination}
                            </p>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            <GrowthStatusChip
                              label={humanizeToken(account.verification_status)}
                              tone={toneForPayoutAccount(account)}
                            />
                            <GrowthStatusChip
                              label={humanizeToken(account.account_status)}
                              tone={toneForWorkspaceStatus(account.account_status)}
                            />
                          </div>
                        </div>

                        <div className="mt-4 flex flex-wrap gap-3">
                          <Button
                            type="button"
                            magnetic={false}
                            disabled={payoutAccountMutation.isPending}
                            onClick={() => {
                              void payoutAccountMutation.mutateAsync({
                                payoutAccountId: account.id,
                                action: 'verify',
                              });
                            }}
                          >
                            {t('partners.verifyPayoutAction')}
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            magnetic={false}
                            disabled={payoutAccountMutation.isPending}
                            onClick={() => {
                              void payoutAccountMutation.mutateAsync({
                                payoutAccountId: account.id,
                                action: 'suspend',
                              });
                            }}
                          >
                            {t('partners.suspendPayoutAction')}
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            magnetic={false}
                            disabled={payoutAccountMutation.isPending}
                            onClick={() => {
                              void payoutAccountMutation.mutateAsync({
                                payoutAccountId: account.id,
                                action: 'archive',
                              });
                            }}
                          >
                            {t('partners.archivePayoutAction')}
                          </Button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <GrowthEmptyState label={t('partners.payoutAccountsEmpty')} />
                  )}
                </div>

                <div className="space-y-3">
                  {selectedPayoutInstructions.length ? (
                    selectedPayoutInstructions.map((instruction) => (
                      <div
                        key={instruction.id}
                        className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                              {instruction.instruction_key}
                            </p>
                            <p className="mt-2 text-xs font-mono text-muted-foreground">
                              {formatCurrencyAmount(instruction.payout_amount, instruction.currency_code, locale)}
                            </p>
                          </div>
                          <GrowthStatusChip
                            label={humanizeToken(instruction.instruction_status)}
                            tone={toneForWorkspaceStatus(instruction.instruction_status)}
                          />
                        </div>

                        <div className="mt-4 flex flex-wrap gap-3">
                          <Button
                            type="button"
                            magnetic={false}
                            disabled={payoutInstructionMutation.isPending}
                            onClick={() => {
                              void payoutInstructionMutation.mutateAsync({
                                payoutInstructionId: instruction.id,
                                action: 'approve',
                              });
                            }}
                          >
                            {t('partners.approveInstructionAction')}
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            magnetic={false}
                            disabled={payoutInstructionMutation.isPending}
                            onClick={() => {
                              void payoutInstructionMutation.mutateAsync({
                                payoutInstructionId: instruction.id,
                                action: 'reject',
                              });
                            }}
                          >
                            {t('partners.rejectInstructionAction')}
                          </Button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <GrowthEmptyState label={t('partners.payoutInstructionsEmpty')} />
                  )}
                </div>

                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('partners.payoutExecutionsTitle')}
                    </p>
                    <GrowthStatusChip
                      label={String(selectedPayoutExecutions.length)}
                      tone={toneForCount(selectedPayoutExecutions.length)}
                    />
                  </div>
                  <div className="mt-4 space-y-2">
                    {selectedPayoutExecutions.length ? (
                      selectedPayoutExecutions.slice(0, 5).map((execution) => (
                        <div
                          key={execution.id}
                          className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-grid-line/20 bg-terminal-surface/35 px-3 py-2"
                        >
                          <div>
                            <p className="text-sm font-mono uppercase tracking-[0.18em] text-white">
                              {execution.execution_key}
                            </p>
                            <p className="mt-1 text-xs font-mono text-muted-foreground">
                              {formatDateTime(execution.updated_at, locale)}
                            </p>
                          </div>
                          <GrowthStatusChip
                            label={humanizeToken(execution.execution_status)}
                            tone={toneForWorkspaceStatus(execution.execution_status)}
                          />
                        </div>
                      ))
                    ) : (
                      <GrowthEmptyState label={t('partners.payoutExecutionsEmpty')} />
                    )}
                  </div>
                </div>
              </div>
            </section>
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                    {t('partners.signalsTitle')}
                  </h2>
                  <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                    {t('partners.signalsDescription')}
                  </p>
                </div>
                <ShieldAlert className="h-5 w-5 text-neon-pink" />
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-2">
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('partners.labels.reviewRequests')}
                  </p>
                  <p className="mt-2 text-2xl font-display text-white">
                    {selectedReviewRequests.length}
                  </p>
                </div>
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('partners.labels.cases')}
                  </p>
                  <p className="mt-2 text-2xl font-display text-white">
                    {selectedCases.length}
                  </p>
                </div>
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('partners.labels.trafficDeclarations')}
                  </p>
                  <p className="mt-2 text-2xl font-display text-white">
                    {selectedTrafficDeclarations.length}
                  </p>
                </div>
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('partners.labels.creativeApprovals')}
                  </p>
                  <p className="mt-2 text-2xl font-display text-white">
                    {selectedCreativeApprovals.length}
                  </p>
                </div>
              </div>

              <div className="mt-5 space-y-3">
                {selectedTrafficDeclarations.slice(0, 3).map((item) => (
                  <div
                    key={item.id}
                    className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-display uppercase tracking-[0.14em] text-white">
                          {humanizeToken(item.declaration_kind)}
                        </p>
                        <p className="mt-2 text-xs font-mono text-muted-foreground">
                          {item.scope_label}
                        </p>
                      </div>
                      <GrowthStatusChip
                        label={humanizeToken(item.declaration_status)}
                        tone={toneForWorkspaceStatus(item.declaration_status)}
                      />
                    </div>
                  </div>
                ))}
                {selectedCreativeApprovals.slice(0, 3).map((item) => (
                  <div
                    key={item.id}
                    className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-display uppercase tracking-[0.14em] text-white">
                          {humanizeToken(item.approval_kind)}
                        </p>
                        <p className="mt-2 text-xs font-mono text-muted-foreground">
                          {item.scope_label}
                        </p>
                      </div>
                      <GrowthStatusChip
                        label={humanizeToken(item.approval_status)}
                        tone={toneForWorkspaceStatus(item.approval_status)}
                      />
                    </div>
                  </div>
                ))}
                {!selectedTrafficDeclarations.length && !selectedCreativeApprovals.length ? (
                  <GrowthEmptyState label={t('partners.signalsEmpty')} />
                ) : null}
              </div>
            </section>

            <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                    {t('partners.opsLinksTitle')}
                  </h2>
                  <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                    {t('partners.opsLinksDescription')}
                  </p>
                </div>
                <WalletCards className="h-5 w-5 text-neon-cyan" />
              </div>

              <div className="mt-5 space-y-3">
                <Link
                  href="/security/review-queue"
                  className="flex items-center justify-between rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-white transition-colors hover:border-grid-line/40"
                >
                  <span>{t('partners.openReviewQueue')}</span>
                  <ArrowUpRight className="h-4 w-4 text-neon-cyan" />
                </Link>
                <Link
                  href="/governance/audit-log"
                  className="flex items-center justify-between rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-white transition-colors hover:border-grid-line/40"
                >
                  <span>{t('partners.openAuditLog')}</span>
                  <ArrowUpRight className="h-4 w-4 text-neon-cyan" />
                </Link>
                <Link
                  href="/governance/policy"
                  className="flex items-center justify-between rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-white transition-colors hover:border-grid-line/40"
                >
                  <span>{t('partners.openPolicyConsole')}</span>
                  <ArrowUpRight className="h-4 w-4 text-neon-cyan" />
                </Link>
              </div>

              <div className="mt-5 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('partners.labels.currentWorkspace')}
                </p>
                <p className="mt-2 text-sm font-display uppercase tracking-[0.14em] text-white">
                  {selectedWorkspace?.display_name ?? t('partners.workspaceEmpty')}
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <GrowthStatusChip
                    label={t('partners.badges.reviewRequests', { count: selectedReviewRequests.length })}
                    tone={toneForCount(selectedReviewRequests.length)}
                  />
                  <GrowthStatusChip
                    label={t('partners.badges.cases', { count: selectedCases.length })}
                    tone={toneForCount(selectedCases.length)}
                  />
                  <GrowthStatusChip
                    label={t('partners.badges.payoutAccounts', { count: selectedPayoutAccounts.length })}
                    tone={toneForCount(selectedPayoutAccounts.length)}
                  />
                </div>
              </div>
            </section>
          </div>
        </section>
      </div>
    </GrowthPageShell>
  );
}
