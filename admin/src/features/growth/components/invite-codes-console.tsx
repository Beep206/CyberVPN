'use client';

import { useState } from 'react';
import type { Dispatch, FormEvent, SetStateAction } from 'react';
import { Ban, Clock3, Download, MailCheck, Plus, RefreshCw, Send, TicketPlus } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { growthApi } from '@/lib/api/growth';
import type {
  AdminInviteBatchResponse,
  AdminInviteCampaignResponse,
  AdminInviteCodeSummaryResponse,
} from '@/lib/api/growth';
import { plansApi } from '@/lib/api/plans';
import { GrowthEmptyState } from '@/features/growth/components/growth-empty-state';
import { GrowthPageShell } from '@/features/growth/components/growth-page-shell';
import { GrowthStatusChip } from '@/features/growth/components/growth-status-chip';
import {
  formatCompactNumber,
  formatDateTime,
  getErrorMessage,
  humanizeToken,
  shortId,
  toIsoDateTime,
} from '@/features/growth/lib/formatting';
import { cn } from '@/lib/utils';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';

type InviteTab =
  | 'overview'
  | 'campaigns'
  | 'createBatch'
  | 'inventory'
  | 'batches'
  | 'redemptions'
  | 'inviteTree'
  | 'exportsAudit'
  | 'settings';

const INVITE_TABS: InviteTab[] = [
  'overview',
  'campaigns',
  'createBatch',
  'inventory',
  'batches',
  'redemptions',
  'inviteTree',
  'exportsAudit',
  'settings',
];

const STATUS_FILTERS = ['', 'draft', 'active', 'paused', 'archived'];
const INVENTORY_STATUSES = ['', 'issued', 'active', 'redeemed', 'revoked', 'expired'];
const REDEMPTION_STATUSES = ['', 'redeemed', 'blocked', 'reversed'];
const SURFACE_OPTIONS = ['web', 'miniapp', 'telegram_bot'];

const initialCampaignForm = {
  campaignKey: '',
  name: '',
  description: '',
  ownerMode: 'selected_user',
  allowedGeos: '',
  allowedMarkets: '',
  allowedSegments: '',
  riskPolicyKey: '',
  rawExportEnabled: true,
  requireNoActiveAccess: true,
  blockSelfRedemption: true,
  perUserRedeemCap: '1',
  globalIssueCap: '',
  maxPerBatch: '1000',
  maxPerOwner: '',
  maxDailyIssued: '',
  grantPlanId: '',
  grantPlanCode: '',
  grantDurationDays: '365',
  childGrantPlanId: '',
  childGrantPlanCode: '',
  childGrantDurationDays: '365',
  childInviteCount: '10',
  childInviteFreeDays: '365',
  childInviteExpiryDays: '30',
  maxGenerationDepth: '5',
  startsAt: '',
  expiresAt: '',
  publish: false,
  reason: '',
};

const initialBatchForm = {
  campaignId: '',
  ownerUserId: '',
  ownerUserIds: '',
  count: '10',
  expiryDays: '30',
  expiresAt: '',
  idempotencyKey: '',
  reason: '',
};

const initialInventoryFilters = {
  campaignId: '',
  campaignKey: '',
  batchId: '',
  ownerUserId: '',
  usedByUserId: '',
  rootInviteCodeId: '',
  status: '',
  used: '',
  planId: '',
  planCode: '',
  generationDepth: '',
  createdFrom: '',
  createdTo: '',
  usedFrom: '',
  usedTo: '',
  expiresFrom: '',
  expiresTo: '',
  prefix: '',
};

const initialBatchActionForm = {
  reason: '',
  extendExpiryDays: '30',
};

function statusTone(status: string | null | undefined) {
  if (status === 'active' || status === 'redeemed' || status === 'issued') return 'success' as const;
  if (status === 'blocked' || status === 'revoked' || status === 'expired' || status === 'archived') return 'danger' as const;
  if (status === 'paused' || status === 'draft') return 'warning' as const;
  return 'neutral' as const;
}

function optionalNumber(value: string) {
  if (!value.trim()) return undefined;
  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) ? undefined : parsed;
}

function csvList(value: string) {
  return value
    .split(/[\n,]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function selectedCampaignOrFirst(
  campaigns: AdminInviteCampaignResponse[],
  selectedCampaignId: string | null,
) {
  return campaigns.find((campaign) => campaign.id === selectedCampaignId) ?? campaigns[0] ?? null;
}

export function InviteCodesConsole() {
  const t = useTranslations('Growth');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<InviteTab>('overview');
  const [campaignStatusFilter, setCampaignStatusFilter] = useState('');
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);
  const [campaignForm, setCampaignForm] = useState(initialCampaignForm);
  const [batchForm, setBatchForm] = useState(initialBatchForm);
  const [batchActionForm, setBatchActionForm] = useState(initialBatchActionForm);
  const [inventoryFilters, setInventoryFilters] = useState(initialInventoryFilters);
  const [redemptionStatusFilter, setRedemptionStatusFilter] = useState('');
  const [treeRootInput, setTreeRootInput] = useState('');
  const [treeRootId, setTreeRootId] = useState('');
  const [lastRawCodes, setLastRawCodes] = useState<string[]>([]);
  const [feedback, setFeedback] = useState<string | null>(null);

  const campaignsQuery = useQuery({
    queryKey: ['growth', 'invite-campaigns', campaignStatusFilter],
    queryFn: async () => {
      const response = await growthApi.listInviteCampaigns({
        status: campaignStatusFilter || undefined,
        offset: 0,
        limit: 50,
      });
      return response.data;
    },
    staleTime: 30_000,
  });

  const plansQuery = useQuery({
    queryKey: ['growth', 'plans', 'invite-codes', 'admin'],
    queryFn: async () => {
      const response = await plansApi.listAdmin({ include_inactive: true });
      return response.data;
    },
    staleTime: 60_000,
  });

  const inviteCodesQuery = useQuery({
    queryKey: ['growth', 'invite-codes', inventoryFilters],
    queryFn: async () => {
      const response = await growthApi.listInviteCodes({
        campaign_id: inventoryFilters.campaignId.trim() || undefined,
        campaign_key: inventoryFilters.campaignKey.trim() || undefined,
        batch_id: inventoryFilters.batchId.trim() || undefined,
        owner_user_id: inventoryFilters.ownerUserId.trim() || undefined,
        used_by_user_id: inventoryFilters.usedByUserId.trim() || undefined,
        root_invite_code_id: inventoryFilters.rootInviteCodeId.trim() || undefined,
        status: inventoryFilters.status || undefined,
        used: inventoryFilters.used ? inventoryFilters.used === 'true' : undefined,
        plan_id: inventoryFilters.planId || undefined,
        plan_code: inventoryFilters.planCode.trim() || undefined,
        generation_depth: optionalNumber(inventoryFilters.generationDepth),
        created_from: toIsoDateTime(inventoryFilters.createdFrom) ?? undefined,
        created_to: toIsoDateTime(inventoryFilters.createdTo) ?? undefined,
        used_from: toIsoDateTime(inventoryFilters.usedFrom) ?? undefined,
        used_to: toIsoDateTime(inventoryFilters.usedTo) ?? undefined,
        expires_from: toIsoDateTime(inventoryFilters.expiresFrom) ?? undefined,
        expires_to: toIsoDateTime(inventoryFilters.expiresTo) ?? undefined,
        prefix: inventoryFilters.prefix.trim() || undefined,
        offset: 0,
        limit: 100,
      });
      return response.data;
    },
    staleTime: 20_000,
  });

  const batchesQuery = useQuery({
    queryKey: ['growth', 'invite-batches'],
    queryFn: async () => {
      const response = await growthApi.listInviteBatches({
        offset: 0,
        limit: 50,
      });
      return response.data;
    },
    staleTime: 30_000,
  });

  const campaigns = campaignsQuery.data?.items ?? [];
  const selectedCampaign = selectedCampaignOrFirst(campaigns, selectedCampaignId);
  const selectedCampaignForQueriesId = selectedCampaign?.id ?? '';
  const selectedBatch =
    batchesQuery.data?.items.find((batch) => batch.id === selectedBatchId) ?? batchesQuery.data?.items[0] ?? null;
  const plans = plansQuery.data ?? [];
  const inviteCodes = inviteCodesQuery.data ?? [];
  const batches = batchesQuery.data?.items ?? [];

  const analyticsQuery = useQuery({
    queryKey: ['growth', 'invite-campaigns', selectedCampaignForQueriesId, 'analytics'],
    queryFn: async () => {
      const response = await growthApi.getInviteCampaignAnalytics(selectedCampaignForQueriesId);
      return response.data;
    },
    enabled: Boolean(selectedCampaignForQueriesId),
    staleTime: 30_000,
  });

  const redemptionsQuery = useQuery({
    queryKey: ['growth', 'invite-campaigns', selectedCampaignForQueriesId, 'redemptions', redemptionStatusFilter],
    queryFn: async () => {
      const response = await growthApi.listInviteCampaignRedemptions(selectedCampaignForQueriesId, {
        status: redemptionStatusFilter || undefined,
        offset: 0,
        limit: 50,
      });
      return response.data;
    },
    enabled: Boolean(selectedCampaignForQueriesId),
    staleTime: 20_000,
  });

  const treeQuery = useQuery({
    queryKey: ['growth', 'invite-tree', treeRootId],
    queryFn: async () => {
      const response = await growthApi.getInviteTree(treeRootId);
      return response.data;
    },
    enabled: Boolean(treeRootId),
    staleTime: 20_000,
  });

  const treeRootsQuery = useQuery({
    queryKey: ['growth', 'invite-tree-roots', selectedCampaignForQueriesId],
    queryFn: async () => {
      const response = await growthApi.listInviteTreeRoots({
        campaign_id: selectedCampaignForQueriesId || undefined,
        offset: 0,
        limit: 50,
      });
      return response.data;
    },
    staleTime: 30_000,
  });

  const createCampaignMutation = useMutation({
    mutationFn: () =>
      growthApi.createInviteCampaign({
        campaign_key: campaignForm.campaignKey.trim(),
        name: campaignForm.name.trim(),
        description: campaignForm.description.trim() || null,
        owner_mode: campaignForm.ownerMode,
        starts_at: toIsoDateTime(campaignForm.startsAt) ?? null,
        expires_at: toIsoDateTime(campaignForm.expiresAt) ?? null,
        allowed_surfaces: SURFACE_OPTIONS,
        allowed_geos: csvList(campaignForm.allowedGeos),
        allowed_markets: csvList(campaignForm.allowedMarkets),
        allowed_segments: csvList(campaignForm.allowedSegments),
        risk_policy_key: campaignForm.riskPolicyKey.trim() || null,
        grant_plan_id: campaignForm.grantPlanId || null,
        ...(campaignForm.grantPlanId
          ? { grant_plan_code: null }
          : campaignForm.grantPlanCode.trim()
            ? { grant_plan_code: campaignForm.grantPlanCode.trim() }
            : {}),
        grant_duration_days: optionalNumber(campaignForm.grantDurationDays),
        child_grant_plan_id: campaignForm.childGrantPlanId || null,
        ...(campaignForm.childGrantPlanId
          ? { child_grant_plan_code: null }
          : campaignForm.childGrantPlanCode.trim()
            ? { child_grant_plan_code: campaignForm.childGrantPlanCode.trim() }
            : {}),
        child_grant_duration_days: optionalNumber(campaignForm.childGrantDurationDays),
        child_invite_count: optionalNumber(campaignForm.childInviteCount),
        child_invite_free_days: optionalNumber(campaignForm.childInviteFreeDays),
        child_invite_expiry_days: optionalNumber(campaignForm.childInviteExpiryDays),
        max_generation_depth: optionalNumber(campaignForm.maxGenerationDepth),
        require_no_active_access: campaignForm.requireNoActiveAccess,
        block_self_redemption: campaignForm.blockSelfRedemption,
        risk_policy: {
          per_user_redeem_cap: optionalNumber(campaignForm.perUserRedeemCap) ?? 1,
        },
        export_policy: {
          raw_export_enabled: campaignForm.rawExportEnabled,
        },
        caps: {
          global_issue_cap: optionalNumber(campaignForm.globalIssueCap),
          max_per_batch: optionalNumber(campaignForm.maxPerBatch) ?? 1000,
          max_per_owner: optionalNumber(campaignForm.maxPerOwner),
          max_daily_issued: optionalNumber(campaignForm.maxDailyIssued),
        },
        publish: campaignForm.publish,
        reason: campaignForm.reason.trim() || null,
      }),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['growth', 'invite-campaigns'] });
      setSelectedCampaignId(response.data.id);
      setBatchForm((current) => ({ ...current, campaignId: response.data.id }));
      setCampaignForm(initialCampaignForm);
      setFeedback(t('inviteCodes.feedback.campaignCreated'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('inviteCodes.feedback.campaignCreateFailed')));
    },
  });

  const publishMutation = useMutation({
    mutationFn: async (campaign: AdminInviteCampaignResponse) => {
      const versionId = campaign.current_version_id ?? '';
      const validation = await growthApi.validateInviteCampaignVersion(campaign.id, versionId);
      if (!validation.data.valid) {
        throw new Error(validation.data.errors.join('; ') || 'Invite campaign version is invalid');
      }
      return growthApi.publishInviteCampaignVersion(campaign.id, versionId, {
        reason: campaignForm.reason.trim() || 'invite_campaign_publish',
      });
    },
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['growth', 'invite-campaigns'] });
      setSelectedCampaignId(response.data.id);
      setFeedback(t('inviteCodes.feedback.campaignPublished'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('inviteCodes.feedback.campaignPublishFailed')));
    },
  });

  const createBatchMutation = useMutation({
    mutationFn: () =>
      growthApi.createInviteCampaignBatch(batchForm.campaignId || selectedCampaignForQueriesId, {
        owner_user_id: batchForm.ownerUserId.trim() || null,
        owner_user_ids: csvList(batchForm.ownerUserIds),
        count: optionalNumber(batchForm.count) ?? 1,
        expiry_days: batchForm.expiresAt ? null : optionalNumber(batchForm.expiryDays),
        expires_at: toIsoDateTime(batchForm.expiresAt) ?? null,
        idempotency_key: batchForm.idempotencyKey.trim() || null,
        reason: batchForm.reason.trim(),
      }),
    onSuccess: async (response) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['growth', 'invite-campaigns'] }),
        queryClient.invalidateQueries({ queryKey: ['growth', 'invite-batches'] }),
        queryClient.invalidateQueries({ queryKey: ['growth', 'invite-codes'] }),
      ]);
      setSelectedCampaignId(response.data.campaign.id);
      setSelectedBatchId(response.data.batch.id);
      setInventoryFilters((current) => ({ ...current, batchId: response.data.batch.id }));
      setLastRawCodes(response.data.raw_codes);
      setBatchForm(initialBatchForm);
      setFeedback(t('inviteCodes.feedback.batchCreated'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('inviteCodes.feedback.batchCreateFailed')));
    },
  });

  const exportBatchMutation = useMutation({
    mutationFn: (batchId: string) => growthApi.exportInviteBatch(batchId),
    onSuccess: (response) => {
      setLastRawCodes(response.data.codes.map((code) => code.code));
      setFeedback(t('inviteCodes.feedback.exported', { count: response.data.exported_count }));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('inviteCodes.feedback.exportFailed')));
    },
  });

  const batchActionMutation = useMutation({
    mutationFn: async ({ action, batchId }: { action: 'revoke' | 'extend' | 'resend'; batchId: string }) => {
      const reason = batchActionForm.reason.trim() || `invite_batch_${action}`;
      if (action === 'revoke') {
        return growthApi.revokeInviteBatch(batchId, { reason });
      }
      if (action === 'extend') {
        return growthApi.extendInviteBatch(batchId, {
          reason,
          expiry_days: optionalNumber(batchActionForm.extendExpiryDays) ?? 30,
        });
      }
      return growthApi.resendInviteBatch(batchId, { reason });
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['growth', 'invite-batches'] }),
        queryClient.invalidateQueries({ queryKey: ['growth', 'invite-codes'] }),
      ]);
      setBatchActionForm(initialBatchActionForm);
      setFeedback(t('inviteCodes.feedback.batchActionCompleted'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('inviteCodes.feedback.batchActionFailed')));
    },
  });

  const reverseRedemptionMutation = useMutation({
    mutationFn: (redemptionId: string) =>
      growthApi.reverseInviteRedemption(redemptionId, {
        reason: batchActionForm.reason.trim() || 'invite_redemption_reverse',
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['growth', 'invite-campaigns'] }),
        queryClient.invalidateQueries({ queryKey: ['growth', 'invite-batches'] }),
        queryClient.invalidateQueries({ queryKey: ['growth', 'invite-codes'] }),
      ]);
      setFeedback(t('inviteCodes.feedback.redemptionReversed'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('inviteCodes.feedback.redemptionReverseFailed')));
    },
  });

  function handleCreateCampaign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createCampaignMutation.mutate();
  }

  function handleCreateBatch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createBatchMutation.mutate();
  }

  function handleTreeLookup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTreeRootId(treeRootInput.trim());
  }

  function selectCampaign(campaign: AdminInviteCampaignResponse) {
    setSelectedCampaignId(campaign.id);
    setBatchForm((current) => ({ ...current, campaignId: campaign.id }));
    setInventoryFilters((current) => ({ ...current, campaignId: campaign.id }));
  }

  const activeCampaigns = campaigns.filter((campaign) => campaign.status === 'active').length;
  const redeemedInventory = inviteCodes.filter((invite) => invite.is_used).length;

  return (
    <GrowthPageShell
      eyebrow={t('inviteCodes.eyebrow')}
      title={t('inviteCodes.title')}
      description={t('inviteCodes.description')}
      icon={TicketPlus}
      actions={
        <Button
          type="button"
          magnetic={false}
          variant="ghost"
          onClick={() => {
            void campaignsQuery.refetch();
            void inviteCodesQuery.refetch();
            void batchesQuery.refetch();
            void analyticsQuery.refetch();
          }}
        >
          <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
          {t('inviteCodes.actions.refresh')}
        </Button>
      }
      metrics={[
        {
          label: t('inviteCodes.metrics.campaigns'),
          value: formatCompactNumber(campaignsQuery.data?.total ?? campaigns.length, locale),
          hint: t('inviteCodes.metrics.campaignsHint'),
          tone: 'info',
        },
        {
          label: t('inviteCodes.metrics.activeCampaigns'),
          value: formatCompactNumber(activeCampaigns, locale),
          hint: t('inviteCodes.metrics.activeCampaignsHint'),
          tone: activeCampaigns > 0 ? 'success' : 'warning',
        },
        {
          label: t('inviteCodes.metrics.inventory'),
          value: formatCompactNumber(inviteCodes.length, locale),
          hint: t('inviteCodes.metrics.inventoryHint'),
          tone: 'neutral',
        },
        {
          label: t('inviteCodes.metrics.redemptions'),
          value: formatCompactNumber(analyticsQuery.data?.redeemed_count ?? redeemedInventory, locale),
          hint: t('inviteCodes.metrics.redemptionsHint'),
          tone: 'success',
        },
      ]}
    >
      <div aria-live="polite" className="sr-only">
        {feedback}
      </div>
      {feedback ? (
        <div className="rounded-lg border border-grid-line/20 bg-terminal-surface/50 p-3 text-sm font-mono text-foreground">
          {feedback}
        </div>
      ) : null}

      <div
        role="tablist"
        aria-label={t('inviteCodes.tabs.label')}
        className="flex gap-2 overflow-x-auto rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-2 backdrop-blur"
      >
        {INVITE_TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={activeTab === tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              'shrink-0 rounded-xl px-3 py-2 text-xs font-mono uppercase tracking-[0.16em] transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan',
              activeTab === tab
                ? 'border border-neon-cyan/40 bg-neon-cyan/10 text-neon-cyan'
                : 'border border-transparent text-muted-foreground hover:border-grid-line/30 hover:text-white',
            )}
          >
            {t(`inviteCodes.tabs.${tab}`)}
          </button>
        ))}
      </div>

      {activeTab === 'overview' ? (
        <OverviewTab
          campaigns={campaigns}
          batches={batches}
          inviteCodes={inviteCodes}
          selectedCampaign={selectedCampaign}
          locale={locale}
          t={t}
          onSelectCampaign={selectCampaign}
        />
      ) : null}

      {activeTab === 'campaigns' ? (
        <CampaignsTab
          campaigns={campaigns}
          campaignStatusFilter={campaignStatusFilter}
          selectedCampaignId={selectedCampaign?.id ?? null}
          campaignForm={campaignForm}
          setCampaignForm={setCampaignForm}
          setCampaignStatusFilter={setCampaignStatusFilter}
          plans={plans}
          isLoading={campaignsQuery.isLoading}
          isCreating={createCampaignMutation.isPending}
          isPublishing={publishMutation.isPending}
          locale={locale}
          t={t}
          onCreateCampaign={handleCreateCampaign}
          onPublishCampaign={(campaign) => publishMutation.mutate(campaign)}
          onSelectCampaign={selectCampaign}
        />
      ) : null}

      {activeTab === 'createBatch' ? (
        <CreateBatchTab
          campaigns={campaigns}
          selectedCampaign={selectedCampaign}
          batchForm={batchForm}
          setBatchForm={setBatchForm}
          lastRawCodes={lastRawCodes}
          isCreating={createBatchMutation.isPending}
          t={t}
          onCreateBatch={handleCreateBatch}
        />
      ) : null}

      {activeTab === 'inventory' ? (
        <InventoryTab
          inviteCodes={inviteCodes}
          inventoryFilters={inventoryFilters}
          setInventoryFilters={setInventoryFilters}
          plans={plans}
          isLoading={inviteCodesQuery.isLoading}
          isFetching={inviteCodesQuery.isFetching}
          locale={locale}
          t={t}
        />
      ) : null}

      {activeTab === 'batches' ? (
        <BatchesTab
          batches={batches}
          selectedBatchId={selectedBatch?.id ?? null}
          batchActionForm={batchActionForm}
          setBatchActionForm={setBatchActionForm}
          isLoading={batchesQuery.isLoading}
          isMutating={batchActionMutation.isPending}
          locale={locale}
          t={t}
          onSelectBatch={setSelectedBatchId}
          onBatchAction={(action, batchId) => batchActionMutation.mutate({ action, batchId })}
        />
      ) : null}

      {activeTab === 'redemptions' ? (
        <RedemptionsTab
          campaigns={campaigns}
          selectedCampaign={selectedCampaign}
          redemptionStatusFilter={redemptionStatusFilter}
          setRedemptionStatusFilter={setRedemptionStatusFilter}
          redemptions={redemptionsQuery.data?.items ?? []}
          total={redemptionsQuery.data?.total ?? 0}
          isLoading={redemptionsQuery.isLoading}
          isReversing={reverseRedemptionMutation.isPending}
          locale={locale}
          t={t}
          onSelectCampaign={selectCampaign}
          onReverseRedemption={(redemptionId) => reverseRedemptionMutation.mutate(redemptionId)}
        />
      ) : null}

      {activeTab === 'inviteTree' ? (
        <InviteTreeTab
          treeRootInput={treeRootInput}
          setTreeRootInput={setTreeRootInput}
          roots={treeRootsQuery.data?.items ?? []}
          rootsLoading={treeRootsQuery.isLoading}
          tree={treeQuery.data ?? null}
          isLoading={treeQuery.isLoading}
          errorMessage={treeQuery.error ? getErrorMessage(treeQuery.error, t('inviteCodes.feedback.treeFailed')) : null}
          locale={locale}
          t={t}
          onLookup={handleTreeLookup}
          onSelectRoot={(rootId) => {
            setTreeRootInput(rootId);
            setTreeRootId(rootId);
          }}
        />
      ) : null}

      {activeTab === 'exportsAudit' ? (
        <ExportsAuditTab
          batches={batches}
          selectedBatch={selectedBatch}
          lastRawCodes={lastRawCodes}
          isExporting={exportBatchMutation.isPending}
          locale={locale}
          t={t}
          onSelectBatch={setSelectedBatchId}
          onExport={(batchId) => exportBatchMutation.mutate(batchId)}
        />
      ) : null}

      {activeTab === 'settings' ? (
        <SettingsTab
          selectedCampaign={selectedCampaign}
          analytics={analyticsQuery.data ?? null}
          t={t}
        />
      ) : null}
    </GrowthPageShell>
  );
}

function OverviewTab({
  campaigns,
  batches,
  inviteCodes,
  selectedCampaign,
  locale,
  t,
  onSelectCampaign,
}: {
  campaigns: AdminInviteCampaignResponse[];
  batches: AdminInviteBatchResponse[];
  inviteCodes: AdminInviteCodeSummaryResponse[];
  selectedCampaign: AdminInviteCampaignResponse | null;
  locale: string;
  t: ReturnType<typeof useTranslations>;
  onSelectCampaign: (campaign: AdminInviteCampaignResponse) => void;
}) {
  const latestBatch = batches[0] ?? null;
  return (
    <div className="grid gap-6 xl:grid-cols-12">
      <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5">
        <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
          {t('inviteCodes.overview.title')}
        </h2>
        <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
          {t('inviteCodes.overview.description')}
        </p>
        <div className="mt-5 grid gap-3">
          <InfoLine
            label={t('inviteCodes.overview.selectedCampaign')}
            value={selectedCampaign?.campaign_key ?? t('common.missing')}
          />
          <InfoLine
            label={t('inviteCodes.overview.latestBatch')}
            value={latestBatch ? shortId(latestBatch.id, 12) : t('common.missing')}
          />
          <InfoLine
            label={t('inviteCodes.overview.latestIssue')}
            value={latestBatch ? formatDateTime(latestBatch.created_at, locale) : t('common.missing')}
          />
          <InfoLine
            label={t('inviteCodes.overview.inventoryWindow')}
            value={formatCompactNumber(inviteCodes.length, locale)}
          />
        </div>
      </article>

      <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
        <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
          {t('inviteCodes.overview.campaignQueueTitle')}
        </h2>
        <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
          {t('inviteCodes.overview.campaignQueueDescription')}
        </p>
        <div className="mt-5 grid gap-3">
          {campaigns.length === 0 ? (
            <GrowthEmptyState label={t('inviteCodes.campaigns.empty')} />
          ) : (
            campaigns.slice(0, 5).map((campaign) => (
              <button
                key={campaign.id}
                type="button"
                onClick={() => onSelectCampaign(campaign)}
                className="rounded-xl border border-grid-line/20 bg-terminal-bg/45 p-4 text-left transition-colors hover:border-neon-cyan/35 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate font-mono text-sm text-white">{campaign.campaign_key}</p>
                    <p className="mt-1 text-sm text-muted-foreground">{campaign.name}</p>
                  </div>
                  <GrowthStatusChip label={humanizeToken(campaign.status)} tone={statusTone(campaign.status)} />
                </div>
              </button>
            ))
          )}
        </div>
      </article>
    </div>
  );
}

function CampaignsTab({
  campaigns,
  campaignStatusFilter,
  selectedCampaignId,
  campaignForm,
  setCampaignForm,
  setCampaignStatusFilter,
  plans,
  isLoading,
  isCreating,
  isPublishing,
  locale,
  t,
  onCreateCampaign,
  onPublishCampaign,
  onSelectCampaign,
}: {
  campaigns: AdminInviteCampaignResponse[];
  campaignStatusFilter: string;
  selectedCampaignId: string | null;
  campaignForm: typeof initialCampaignForm;
  setCampaignForm: Dispatch<SetStateAction<typeof initialCampaignForm>>;
  setCampaignStatusFilter: (value: string) => void;
  plans: Awaited<ReturnType<typeof plansApi.listAdmin>>['data'];
  isLoading: boolean;
  isCreating: boolean;
  isPublishing: boolean;
  locale: string;
  t: ReturnType<typeof useTranslations>;
  onCreateCampaign: (event: FormEvent<HTMLFormElement>) => void;
  onPublishCampaign: (campaign: AdminInviteCampaignResponse) => void;
  onSelectCampaign: (campaign: AdminInviteCampaignResponse) => void;
}) {
  return (
    <div className="grid gap-6 2xl:grid-cols-[minmax(20rem,0.95fr)_minmax(0,1.2fr)]">
      <form
        onSubmit={onCreateCampaign}
        className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur"
      >
        <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
          {t('inviteCodes.campaigns.createTitle')}
        </h2>
        <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
          {t('inviteCodes.campaigns.createDescription')}
        </p>
        <div className="mt-5 grid gap-4">
          <TextField
            label={t('inviteCodes.fields.campaignKey')}
            value={campaignForm.campaignKey}
            onChange={(value) => setCampaignForm((current) => ({ ...current, campaignKey: value }))}
            required
          />
          <TextField
            label={t('inviteCodes.fields.name')}
            value={campaignForm.name}
            onChange={(value) => setCampaignForm((current) => ({ ...current, name: value }))}
            required
          />
          <TextField
            label={t('inviteCodes.fields.description')}
            value={campaignForm.description}
            onChange={(value) => setCampaignForm((current) => ({ ...current, description: value }))}
          />
          <SelectField
            label={t('inviteCodes.fields.ownerMode')}
            value={campaignForm.ownerMode}
            onChange={(value) => setCampaignForm((current) => ({ ...current, ownerMode: value }))}
            options={['system', 'selected_user', 'uploaded_user_list']}
            optionLabel={(value) => t(`inviteCodes.ownerModes.${value}`)}
          />
          <SelectField
            label={t('inviteCodes.fields.grantPlan')}
            value={campaignForm.grantPlanId}
            onChange={(value) => setCampaignForm((current) => ({ ...current, grantPlanId: value }))}
            options={['', ...plans.map((plan) => plan.uuid)]}
            optionLabel={(value) => {
              const plan = plans.find((item) => item.uuid === value);
              return plan
                ? `${plan.display_name ?? plan.name} · ${t('inviteCodes.units.daysShort', { count: plan.duration_days })}`
                : t('inviteCodes.fields.grantPlanCodeFallback');
            }}
          />
          <TextField
            label={t('inviteCodes.fields.grantPlanCode')}
            value={campaignForm.grantPlanCode}
            onChange={(value) => setCampaignForm((current) => ({ ...current, grantPlanCode: value }))}
          />
          <SelectField
            label={t('inviteCodes.fields.childGrantPlan')}
            value={campaignForm.childGrantPlanId}
            onChange={(value) => setCampaignForm((current) => ({ ...current, childGrantPlanId: value }))}
            options={['', ...plans.map((plan) => plan.uuid)]}
            optionLabel={(value) => {
              const plan = plans.find((item) => item.uuid === value);
              return plan
                ? `${plan.display_name ?? plan.name} · ${t('inviteCodes.units.daysShort', { count: plan.duration_days })}`
                : t('inviteCodes.fields.childGrantPlanCodeFallback');
            }}
          />
          <TextField
            label={t('inviteCodes.fields.childGrantPlanCode')}
            value={campaignForm.childGrantPlanCode}
            onChange={(value) => setCampaignForm((current) => ({ ...current, childGrantPlanCode: value }))}
          />
          <div className="grid gap-4 md:grid-cols-2">
            <TextField
              label={t('inviteCodes.fields.grantDurationDays')}
              type="number"
              value={campaignForm.grantDurationDays}
              onChange={(value) => setCampaignForm((current) => ({ ...current, grantDurationDays: value }))}
            />
            <TextField
              label={t('inviteCodes.fields.childGrantDurationDays')}
              type="number"
              value={campaignForm.childGrantDurationDays}
              onChange={(value) => setCampaignForm((current) => ({ ...current, childGrantDurationDays: value }))}
            />
            <TextField
              label={t('inviteCodes.fields.childInviteCount')}
              type="number"
              value={campaignForm.childInviteCount}
              onChange={(value) => setCampaignForm((current) => ({ ...current, childInviteCount: value }))}
            />
            <TextField
              label={t('inviteCodes.fields.childInviteFreeDays')}
              type="number"
              value={campaignForm.childInviteFreeDays}
              onChange={(value) => setCampaignForm((current) => ({ ...current, childInviteFreeDays: value }))}
            />
            <TextField
              label={t('inviteCodes.fields.childInviteExpiryDays')}
              type="number"
              value={campaignForm.childInviteExpiryDays}
              onChange={(value) => setCampaignForm((current) => ({ ...current, childInviteExpiryDays: value }))}
            />
            <TextField
              label={t('inviteCodes.fields.maxGenerationDepth')}
              type="number"
              value={campaignForm.maxGenerationDepth}
              onChange={(value) => setCampaignForm((current) => ({ ...current, maxGenerationDepth: value }))}
            />
            <TextField
              label={t('inviteCodes.fields.perUserRedeemCap')}
              type="number"
              value={campaignForm.perUserRedeemCap}
              onChange={(value) => setCampaignForm((current) => ({ ...current, perUserRedeemCap: value }))}
            />
            <TextField
              label={t('inviteCodes.fields.maxPerBatch')}
              type="number"
              value={campaignForm.maxPerBatch}
              onChange={(value) => setCampaignForm((current) => ({ ...current, maxPerBatch: value }))}
            />
            <TextField
              label={t('inviteCodes.fields.globalIssueCap')}
              type="number"
              value={campaignForm.globalIssueCap}
              onChange={(value) => setCampaignForm((current) => ({ ...current, globalIssueCap: value }))}
            />
            <TextField
              label={t('inviteCodes.fields.maxPerOwner')}
              type="number"
              value={campaignForm.maxPerOwner}
              onChange={(value) => setCampaignForm((current) => ({ ...current, maxPerOwner: value }))}
            />
            <TextField
              label={t('inviteCodes.fields.maxDailyIssued')}
              type="number"
              value={campaignForm.maxDailyIssued}
              onChange={(value) => setCampaignForm((current) => ({ ...current, maxDailyIssued: value }))}
            />
            <TextField
              label={t('inviteCodes.fields.riskPolicyKey')}
              value={campaignForm.riskPolicyKey}
              onChange={(value) => setCampaignForm((current) => ({ ...current, riskPolicyKey: value }))}
            />
            <TextField
              label={t('inviteCodes.fields.reason')}
              value={campaignForm.reason}
              onChange={(value) => setCampaignForm((current) => ({ ...current, reason: value }))}
            />
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <TextField
              label={t('inviteCodes.fields.allowedGeos')}
              value={campaignForm.allowedGeos}
              onChange={(value) => setCampaignForm((current) => ({ ...current, allowedGeos: value }))}
            />
            <TextField
              label={t('inviteCodes.fields.allowedMarkets')}
              value={campaignForm.allowedMarkets}
              onChange={(value) => setCampaignForm((current) => ({ ...current, allowedMarkets: value }))}
            />
            <TextField
              label={t('inviteCodes.fields.allowedSegments')}
              value={campaignForm.allowedSegments}
              onChange={(value) => setCampaignForm((current) => ({ ...current, allowedSegments: value }))}
            />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <TextField
              label={t('inviteCodes.fields.startsAt')}
              type="datetime-local"
              value={campaignForm.startsAt}
              onChange={(value) => setCampaignForm((current) => ({ ...current, startsAt: value }))}
            />
            <TextField
              label={t('inviteCodes.fields.expiresAt')}
              type="datetime-local"
              value={campaignForm.expiresAt}
              onChange={(value) => setCampaignForm((current) => ({ ...current, expiresAt: value }))}
            />
          </div>
          <label className="flex items-center gap-3 rounded-xl border border-grid-line/20 bg-terminal-bg/45 p-3 text-sm font-mono text-muted-foreground">
            <input
              type="checkbox"
              checked={campaignForm.publish}
              onChange={(event) => setCampaignForm((current) => ({ ...current, publish: event.target.checked }))}
              className="h-4 w-4 accent-neon-cyan"
            />
            {t('inviteCodes.fields.publishNow')}
          </label>
          <div className="grid gap-3 md:grid-cols-3">
            <CheckboxRow
              label={t('inviteCodes.fields.rawExportEnabled')}
              checked={campaignForm.rawExportEnabled}
              onChange={(checked) => setCampaignForm((current) => ({ ...current, rawExportEnabled: checked }))}
            />
            <CheckboxRow
              label={t('inviteCodes.fields.requireNoActiveAccess')}
              checked={campaignForm.requireNoActiveAccess}
              onChange={(checked) => setCampaignForm((current) => ({ ...current, requireNoActiveAccess: checked }))}
            />
            <CheckboxRow
              label={t('inviteCodes.fields.blockSelfRedemption')}
              checked={campaignForm.blockSelfRedemption}
              onChange={(checked) => setCampaignForm((current) => ({ ...current, blockSelfRedemption: checked }))}
            />
          </div>
        </div>
        <Button type="submit" className="mt-5 w-full" magnetic={false} disabled={isCreating}>
          <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
          {isCreating ? t('inviteCodes.actions.creating') : t('inviteCodes.actions.createCampaign')}
        </Button>
      </form>

      <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('inviteCodes.campaigns.inventoryTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('inviteCodes.campaigns.inventoryDescription')}
            </p>
          </div>
          <SelectField
            label={t('inviteCodes.fields.status')}
            value={campaignStatusFilter}
            onChange={setCampaignStatusFilter}
            options={STATUS_FILTERS}
            optionLabel={(value) => (value ? humanizeToken(value) : t('inviteCodes.fields.allStatuses'))}
            compact
          />
        </div>
        <div className="mt-5 grid gap-3">
          {isLoading ? (
            <GrowthEmptyState label={t('inviteCodes.campaigns.loading')} />
          ) : campaigns.length === 0 ? (
            <GrowthEmptyState label={t('inviteCodes.campaigns.empty')} />
          ) : (
            campaigns.map((campaign) => (
              <div
                key={campaign.id}
                className={cn(
                  'rounded-xl border p-4 transition-colors',
                  selectedCampaignId === campaign.id
                    ? 'border-neon-cyan/45 bg-neon-cyan/10'
                    : 'border-grid-line/20 bg-terminal-bg/45 hover:border-grid-line/50',
                )}
              >
                <button
                  type="button"
                  onClick={() => onSelectCampaign(campaign)}
                  className="block w-full text-left focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan"
                  aria-pressed={selectedCampaignId === campaign.id}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate font-mono text-sm text-white">{campaign.campaign_key}</p>
                      <p className="mt-1 text-sm text-muted-foreground">{campaign.name}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <GrowthStatusChip label={humanizeToken(campaign.status)} tone={statusTone(campaign.status)} />
                      {campaign.current_version ? (
                        <GrowthStatusChip
                          label={t('inviteCodes.campaigns.versionBadge', { version: campaign.current_version.version })}
                          tone="neutral"
                        />
                      ) : null}
                    </div>
                  </div>
                  <div className="mt-3 grid gap-2 text-xs font-mono text-muted-foreground md:grid-cols-2">
                    <span>{formatDateTime(campaign.updated_at, locale)}</span>
                    <span>{campaign.published_at ? formatDateTime(campaign.published_at, locale) : t('common.missing')}</span>
                  </div>
                </button>
                {campaign.current_version_id ? (
                  <div className="mt-3">
                    <Button
                      type="button"
                      variant="ghost"
                      magnetic={false}
                      disabled={isPublishing || campaign.status === 'active'}
                      onClick={() => onPublishCampaign(campaign)}
                    >
                      {t('inviteCodes.actions.publish')}
                    </Button>
                  </div>
                ) : null}
              </div>
            ))
          )}
        </div>
      </article>
    </div>
  );
}

function CreateBatchTab({
  campaigns,
  selectedCampaign,
  batchForm,
  setBatchForm,
  lastRawCodes,
  isCreating,
  t,
  onCreateBatch,
}: {
  campaigns: AdminInviteCampaignResponse[];
  selectedCampaign: AdminInviteCampaignResponse | null;
  batchForm: typeof initialBatchForm;
  setBatchForm: Dispatch<SetStateAction<typeof initialBatchForm>>;
  lastRawCodes: string[];
  isCreating: boolean;
  t: ReturnType<typeof useTranslations>;
  onCreateBatch: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <div className="grid gap-6 xl:grid-cols-12">
      <form
        onSubmit={onCreateBatch}
        className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5"
      >
        <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
          {t('inviteCodes.createBatch.title')}
        </h2>
        <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
          {t('inviteCodes.createBatch.description')}
        </p>
        <div className="mt-5 grid gap-4">
          <SelectField
            label={t('inviteCodes.fields.campaign')}
            value={batchForm.campaignId || selectedCampaign?.id || ''}
            onChange={(value) => setBatchForm((current) => ({ ...current, campaignId: value }))}
            options={['', ...campaigns.map((campaign) => campaign.id)]}
            optionLabel={(value) => campaigns.find((campaign) => campaign.id === value)?.campaign_key ?? t('common.missing')}
          />
          <TextField
            label={t('inviteCodes.fields.ownerUserId')}
            value={batchForm.ownerUserId}
            onChange={(value) => setBatchForm((current) => ({ ...current, ownerUserId: value }))}
          />
          <TextField
            label={t('inviteCodes.fields.ownerUserIds')}
            value={batchForm.ownerUserIds}
            onChange={(value) => setBatchForm((current) => ({ ...current, ownerUserIds: value }))}
          />
          <div className="grid gap-4 md:grid-cols-2">
            <TextField
              label={t('inviteCodes.fields.count')}
              type="number"
              value={batchForm.count}
              onChange={(value) => setBatchForm((current) => ({ ...current, count: value }))}
              required
            />
            <TextField
              label={t('inviteCodes.fields.expiryDays')}
              type="number"
              value={batchForm.expiryDays}
              onChange={(value) => setBatchForm((current) => ({ ...current, expiryDays: value }))}
            />
          </div>
          <TextField
            label={t('inviteCodes.fields.expiresAt')}
            type="datetime-local"
            value={batchForm.expiresAt}
            onChange={(value) => setBatchForm((current) => ({ ...current, expiresAt: value }))}
          />
          <TextField
            label={t('inviteCodes.fields.idempotencyKey')}
            value={batchForm.idempotencyKey}
            onChange={(value) => setBatchForm((current) => ({ ...current, idempotencyKey: value }))}
          />
          <TextField
            label={t('inviteCodes.fields.reason')}
            value={batchForm.reason}
            onChange={(value) => setBatchForm((current) => ({ ...current, reason: value }))}
            required
          />
        </div>
        <Button
          type="submit"
          className="mt-5 w-full"
          magnetic={false}
          disabled={isCreating || !(batchForm.campaignId || selectedCampaign?.id)}
        >
          <Send className="mr-2 h-4 w-4" aria-hidden="true" />
          {isCreating ? t('inviteCodes.actions.creating') : t('inviteCodes.actions.createBatch')}
        </Button>
      </form>

      <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
        <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
          {t('inviteCodes.createBatch.resultTitle')}
        </h2>
        <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
          {t('inviteCodes.createBatch.resultDescription')}
        </p>
        <div className="mt-5">
          {lastRawCodes.length === 0 ? (
            <GrowthEmptyState label={t('inviteCodes.createBatch.empty')} />
          ) : (
            <div className="overflow-hidden rounded-2xl border border-grid-line/20">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('inviteCodes.table.code')}</TableHead>
                    <TableHead>{t('inviteCodes.table.created')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {lastRawCodes.map((code) => (
                    <TableRow key={code}>
                      <TableCell className="font-mono text-neon-cyan">{code}</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {t('common.missing')}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </article>
    </div>
  );
}

function InventoryTab({
  inviteCodes,
  inventoryFilters,
  setInventoryFilters,
  plans,
  isLoading,
  isFetching,
  locale,
  t,
}: {
  inviteCodes: AdminInviteCodeSummaryResponse[];
  inventoryFilters: typeof initialInventoryFilters;
  setInventoryFilters: Dispatch<SetStateAction<typeof initialInventoryFilters>>;
  plans: Awaited<ReturnType<typeof plansApi.listAdmin>>['data'];
  isLoading: boolean;
  isFetching: boolean;
  locale: string;
  t: ReturnType<typeof useTranslations>;
}) {
  return (
    <div className="grid gap-6 xl:grid-cols-12">
      <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-4">
        <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
          {t('inviteCodes.inventory.filtersTitle')}
        </h2>
        <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
          {t('inviteCodes.inventory.filtersDescription')}
        </p>
        <div className="mt-5 grid gap-4">
          <TextField
            label={t('inviteCodes.fields.campaignId')}
            value={inventoryFilters.campaignId}
            onChange={(value) => setInventoryFilters((current) => ({ ...current, campaignId: value }))}
          />
          <TextField
            label={t('inviteCodes.fields.campaignKey')}
            value={inventoryFilters.campaignKey}
            onChange={(value) => setInventoryFilters((current) => ({ ...current, campaignKey: value }))}
          />
          <TextField
            label={t('inviteCodes.fields.batchId')}
            value={inventoryFilters.batchId}
            onChange={(value) => setInventoryFilters((current) => ({ ...current, batchId: value }))}
          />
          <TextField
            label={t('inviteCodes.fields.ownerUserId')}
            value={inventoryFilters.ownerUserId}
            onChange={(value) => setInventoryFilters((current) => ({ ...current, ownerUserId: value }))}
          />
          <TextField
            label={t('inviteCodes.fields.usedByUserId')}
            value={inventoryFilters.usedByUserId}
            onChange={(value) => setInventoryFilters((current) => ({ ...current, usedByUserId: value }))}
          />
          <SelectField
            label={t('inviteCodes.fields.status')}
            value={inventoryFilters.status}
            onChange={(value) => setInventoryFilters((current) => ({ ...current, status: value }))}
            options={INVENTORY_STATUSES}
            optionLabel={(value) => (value ? humanizeToken(value) : t('inviteCodes.fields.allStatuses'))}
          />
          <SelectField
            label={t('inviteCodes.fields.used')}
            value={inventoryFilters.used}
            onChange={(value) => setInventoryFilters((current) => ({ ...current, used: value }))}
            options={['', 'true', 'false']}
            optionLabel={(value) => {
              if (value === 'true') return t('common.used');
              if (value === 'false') return t('common.unused');
              return t('inviteCodes.fields.anyUsage');
            }}
          />
          <SelectField
            label={t('inviteCodes.fields.planId')}
            value={inventoryFilters.planId}
            onChange={(value) => setInventoryFilters((current) => ({ ...current, planId: value }))}
            options={['', ...plans.map((plan) => plan.uuid)]}
            optionLabel={(value) => {
              const plan = plans.find((item) => item.uuid === value);
              return plan
                ? `${plan.display_name ?? plan.name} · ${t('inviteCodes.units.daysShort', { count: plan.duration_days })}`
                : t('inviteCodes.fields.anyPlan');
            }}
          />
          <TextField
            label={t('inviteCodes.fields.planCode')}
            value={inventoryFilters.planCode}
            onChange={(value) => setInventoryFilters((current) => ({ ...current, planCode: value }))}
          />
          <TextField
            label={t('inviteCodes.fields.generationDepth')}
            type="number"
            value={inventoryFilters.generationDepth}
            onChange={(value) => setInventoryFilters((current) => ({ ...current, generationDepth: value }))}
          />
          <TextField
            label={t('inviteCodes.fields.prefix')}
            value={inventoryFilters.prefix}
            onChange={(value) => setInventoryFilters((current) => ({ ...current, prefix: value }))}
          />
          <div className="grid gap-4 md:grid-cols-2">
            <TextField
              label={t('inviteCodes.fields.createdFrom')}
              type="datetime-local"
              value={inventoryFilters.createdFrom}
              onChange={(value) => setInventoryFilters((current) => ({ ...current, createdFrom: value }))}
            />
            <TextField
              label={t('inviteCodes.fields.createdTo')}
              type="datetime-local"
              value={inventoryFilters.createdTo}
              onChange={(value) => setInventoryFilters((current) => ({ ...current, createdTo: value }))}
            />
            <TextField
              label={t('inviteCodes.fields.usedFrom')}
              type="datetime-local"
              value={inventoryFilters.usedFrom}
              onChange={(value) => setInventoryFilters((current) => ({ ...current, usedFrom: value }))}
            />
            <TextField
              label={t('inviteCodes.fields.usedTo')}
              type="datetime-local"
              value={inventoryFilters.usedTo}
              onChange={(value) => setInventoryFilters((current) => ({ ...current, usedTo: value }))}
            />
            <TextField
              label={t('inviteCodes.fields.expiresFrom')}
              type="datetime-local"
              value={inventoryFilters.expiresFrom}
              onChange={(value) => setInventoryFilters((current) => ({ ...current, expiresFrom: value }))}
            />
            <TextField
              label={t('inviteCodes.fields.expiresTo')}
              type="datetime-local"
              value={inventoryFilters.expiresTo}
              onChange={(value) => setInventoryFilters((current) => ({ ...current, expiresTo: value }))}
            />
          </div>
          <Button
            type="button"
            variant="ghost"
            magnetic={false}
            onClick={() => setInventoryFilters(initialInventoryFilters)}
          >
            {t('common.clear')}
          </Button>
        </div>
      </article>

      <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-8">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('inviteCodes.inventory.title')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('inviteCodes.inventory.description')}
            </p>
          </div>
          <GrowthStatusChip
            label={isFetching ? t('inviteCodes.actions.syncing') : t('inviteCodes.inventory.live')}
            tone={isFetching ? 'warning' : 'success'}
          />
        </div>
        <div className="mt-5 overflow-hidden rounded-2xl border border-grid-line/20">
          <InviteCodesTable inviteCodes={inviteCodes} isLoading={isLoading} locale={locale} t={t} />
        </div>
      </article>
    </div>
  );
}

function BatchesTab({
  batches,
  selectedBatchId,
  batchActionForm,
  setBatchActionForm,
  isLoading,
  isMutating,
  locale,
  t,
  onSelectBatch,
  onBatchAction,
}: {
  batches: AdminInviteBatchResponse[];
  selectedBatchId: string | null;
  batchActionForm: typeof initialBatchActionForm;
  setBatchActionForm: Dispatch<SetStateAction<typeof initialBatchActionForm>>;
  isLoading: boolean;
  isMutating: boolean;
  locale: string;
  t: ReturnType<typeof useTranslations>;
  onSelectBatch: (batchId: string) => void;
  onBatchAction: (action: 'revoke' | 'extend' | 'resend', batchId: string) => void;
}) {
  return (
    <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
        {t('inviteCodes.batches.title')}
      </h2>
      <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
        {t('inviteCodes.batches.description')}
      </p>
      <div className="mt-5 grid gap-4 md:grid-cols-[minmax(0,1fr)_12rem]">
        <TextField
          label={t('inviteCodes.fields.reason')}
          value={batchActionForm.reason}
          onChange={(value) => setBatchActionForm((current) => ({ ...current, reason: value }))}
        />
        <TextField
          label={t('inviteCodes.fields.extendExpiryDays')}
          type="number"
          value={batchActionForm.extendExpiryDays}
          onChange={(value) => setBatchActionForm((current) => ({ ...current, extendExpiryDays: value }))}
        />
      </div>
      <div className="mt-5 overflow-hidden rounded-2xl border border-grid-line/20">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('inviteCodes.table.batch')}</TableHead>
              <TableHead>{t('inviteCodes.table.owner')}</TableHead>
              <TableHead>{t('inviteCodes.table.issued')}</TableHead>
              <TableHead>{t('inviteCodes.table.status')}</TableHead>
              <TableHead>{t('inviteCodes.table.expires')}</TableHead>
              <TableHead>{t('inviteCodes.table.created')}</TableHead>
              <TableHead>{t('inviteCodes.table.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7}>
                  <GrowthEmptyState label={t('inviteCodes.batches.loading')} />
                </TableCell>
              </TableRow>
            ) : batches.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7}>
                  <GrowthEmptyState label={t('inviteCodes.batches.empty')} />
                </TableCell>
              </TableRow>
            ) : (
              batches.map((batch) => (
                <TableRow key={batch.id}>
                  <TableCell>
                    <button
                      type="button"
                      onClick={() => onSelectBatch(batch.id)}
                      className={cn(
                        'font-mono text-sm underline-offset-4 hover:underline focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan',
                        selectedBatchId === batch.id ? 'text-neon-cyan' : 'text-white',
                      )}
                    >
                      {shortId(batch.id, 12)}
                    </button>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {shortId(batch.owner_user_id)}
                  </TableCell>
                  <TableCell>{formatCompactNumber(batch.issued_count, locale)}</TableCell>
                  <TableCell>
                    <GrowthStatusChip label={humanizeToken(batch.status)} tone={statusTone(batch.status)} />
                  </TableCell>
                  <TableCell>{formatDateTime(batch.expires_at, locale)}</TableCell>
                  <TableCell>{formatDateTime(batch.created_at, locale)}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        type="button"
                        variant="ghost"
                        magnetic={false}
                        disabled={isMutating || batch.status === 'revoked'}
                        onClick={() => onBatchAction('revoke', batch.id)}
                      >
                        <Ban className="mr-2 h-4 w-4" aria-hidden="true" />
                        {t('inviteCodes.actions.revoke')}
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        magnetic={false}
                        disabled={isMutating || batch.status === 'revoked'}
                        onClick={() => onBatchAction('extend', batch.id)}
                      >
                        <Clock3 className="mr-2 h-4 w-4" aria-hidden="true" />
                        {t('inviteCodes.actions.extend')}
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        magnetic={false}
                        disabled={isMutating}
                        onClick={() => onBatchAction('resend', batch.id)}
                      >
                        <MailCheck className="mr-2 h-4 w-4" aria-hidden="true" />
                        {t('inviteCodes.actions.resend')}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </article>
  );
}

function RedemptionsTab({
  campaigns,
  selectedCampaign,
  redemptionStatusFilter,
  setRedemptionStatusFilter,
  redemptions,
  total,
  isLoading,
  isReversing,
  locale,
  t,
  onSelectCampaign,
  onReverseRedemption,
}: {
  campaigns: AdminInviteCampaignResponse[];
  selectedCampaign: AdminInviteCampaignResponse | null;
  redemptionStatusFilter: string;
  setRedemptionStatusFilter: (value: string) => void;
  redemptions: Awaited<ReturnType<typeof growthApi.listInviteCampaignRedemptions>>['data']['items'];
  total: number;
  isLoading: boolean;
  isReversing: boolean;
  locale: string;
  t: ReturnType<typeof useTranslations>;
  onSelectCampaign: (campaign: AdminInviteCampaignResponse) => void;
  onReverseRedemption: (redemptionId: string) => void;
}) {
  return (
    <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('inviteCodes.redemptions.title')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('inviteCodes.redemptions.description', {
              campaign: selectedCampaign?.campaign_key ?? t('common.missing'),
              count: total,
            })}
          </p>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <SelectField
            label={t('inviteCodes.fields.campaign')}
            value={selectedCampaign?.id ?? ''}
            onChange={(value) => {
              const campaign = campaigns.find((item) => item.id === value);
              if (campaign) onSelectCampaign(campaign);
            }}
            options={['', ...campaigns.map((campaign) => campaign.id)]}
            optionLabel={(value) => campaigns.find((campaign) => campaign.id === value)?.campaign_key ?? t('common.missing')}
            compact
          />
          <SelectField
            label={t('inviteCodes.fields.status')}
            value={redemptionStatusFilter}
            onChange={setRedemptionStatusFilter}
            options={REDEMPTION_STATUSES}
            optionLabel={(value) => (value ? humanizeToken(value) : t('inviteCodes.fields.allStatuses'))}
            compact
          />
        </div>
      </div>
      <div className="mt-5 overflow-hidden rounded-2xl border border-grid-line/20">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('inviteCodes.table.redemption')}</TableHead>
              <TableHead>{t('inviteCodes.table.invitee')}</TableHead>
              <TableHead>{t('inviteCodes.table.depth')}</TableHead>
              <TableHead>{t('inviteCodes.table.plan')}</TableHead>
              <TableHead>{t('inviteCodes.table.childInvites')}</TableHead>
              <TableHead>{t('inviteCodes.table.surface')}</TableHead>
              <TableHead>{t('inviteCodes.table.status')}</TableHead>
              <TableHead>{t('inviteCodes.table.redeemed')}</TableHead>
              <TableHead>{t('inviteCodes.table.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={9}>
                  <GrowthEmptyState label={t('inviteCodes.redemptions.loading')} />
                </TableCell>
              </TableRow>
            ) : redemptions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9}>
                  <GrowthEmptyState label={t('inviteCodes.redemptions.empty')} />
                </TableCell>
              </TableRow>
            ) : (
              redemptions.map((redemption) => (
                <TableRow key={redemption.id}>
                  <TableCell className="font-mono text-neon-cyan">{shortId(redemption.id, 12)}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {shortId(redemption.invitee_user_id)}
                  </TableCell>
                  <TableCell>{redemption.generation_depth}</TableCell>
                  <TableCell className="font-mono text-xs text-white/85">
                    {redemption.granted_plan_code ?? shortId(redemption.granted_plan_id)}
                  </TableCell>
                  <TableCell>{redemption.child_issued_count ?? 0}</TableCell>
                  <TableCell className="font-mono text-xs text-white/85">
                    {humanizeToken(redemption.source_surface)}
                  </TableCell>
                  <TableCell>
                    <GrowthStatusChip label={humanizeToken(redemption.status)} tone={statusTone(redemption.status)} />
                  </TableCell>
                  <TableCell>{formatDateTime(redemption.redeemed_at, locale)}</TableCell>
                  <TableCell>
                    <Button
                      type="button"
                      variant="ghost"
                      magnetic={false}
                      disabled={isReversing || redemption.status === 'reversed'}
                      onClick={() => onReverseRedemption(redemption.id)}
                    >
                      <Ban className="mr-2 h-4 w-4" aria-hidden="true" />
                      {t('inviteCodes.actions.reverse')}
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </article>
  );
}

function InviteTreeTab({
  treeRootInput,
  setTreeRootInput,
  roots,
  rootsLoading,
  tree,
  isLoading,
  errorMessage,
  locale,
  t,
  onLookup,
  onSelectRoot,
}: {
  treeRootInput: string;
  setTreeRootInput: (value: string) => void;
  roots: Awaited<ReturnType<typeof growthApi.listInviteTreeRoots>>['data']['items'];
  rootsLoading: boolean;
  tree: Awaited<ReturnType<typeof growthApi.getInviteTree>>['data'] | null;
  isLoading: boolean;
  errorMessage: string | null;
  locale: string;
  t: ReturnType<typeof useTranslations>;
  onLookup: (event: FormEvent<HTMLFormElement>) => void;
  onSelectRoot: (rootId: string) => void;
}) {
  return (
    <div className="grid gap-6 xl:grid-cols-12">
      <form
        onSubmit={onLookup}
        className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-4"
      >
        <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
          {t('inviteCodes.tree.lookupTitle')}
        </h2>
        <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
          {t('inviteCodes.tree.lookupDescription')}
        </p>
        <div className="mt-5 grid gap-4">
          <TextField
            label={t('inviteCodes.fields.rootInviteCodeId')}
            value={treeRootInput}
            onChange={setTreeRootInput}
            required
          />
          <Button type="submit" magnetic={false} disabled={isLoading || !treeRootInput.trim()}>
            {isLoading ? t('inviteCodes.actions.loading') : t('inviteCodes.actions.lookupTree')}
          </Button>
        </div>
        {errorMessage ? (
          <div className="mt-5 rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
            {errorMessage}
          </div>
        ) : null}
        <div className="mt-5 space-y-2">
          <p className="text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
            {t('inviteCodes.tree.roots')}
          </p>
          {rootsLoading ? (
            <GrowthEmptyState label={t('inviteCodes.tree.rootsLoading')} />
          ) : roots.length === 0 ? (
            <GrowthEmptyState label={t('inviteCodes.tree.rootsEmpty')} />
          ) : (
            <div className="grid gap-2">
              {roots.slice(0, 8).map((root) => (
                <button
                  key={root.root_invite_code_id}
                  type="button"
                  onClick={() => onSelectRoot(root.root_invite_code_id)}
                  className="rounded-xl border border-grid-line/20 bg-terminal-bg/45 p-3 text-left text-xs font-mono text-muted-foreground transition-colors hover:border-neon-cyan/40 hover:text-white focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan"
                >
                  <span className="block text-neon-cyan">{shortId(root.root_invite_code_id, 12)}</span>
                  <span className="mt-1 block">
                    {t('inviteCodes.tree.rootStats', {
                      issued: root.issued_count,
                      redeemed: root.redeemed_count,
                      depth: root.max_depth_reached,
                    })}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </form>

      <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-8">
        <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
          {t('inviteCodes.tree.title')}
        </h2>
        <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
          {t('inviteCodes.tree.description')}
        </p>
        <div className="mt-5">
          {!tree ? (
            <GrowthEmptyState label={t('inviteCodes.tree.empty')} />
          ) : (
            <div className="space-y-5">
              <div className="grid gap-3 md:grid-cols-3">
                <InfoLine label={t('inviteCodes.tree.root')} value={shortId(tree.root_invite_code_id, 12)} />
                <InfoLine label={t('inviteCodes.tree.nodes')} value={formatCompactNumber(tree.nodes.length, locale)} />
                <InfoLine label={t('inviteCodes.tree.edges')} value={formatCompactNumber(tree.edges.length, locale)} />
              </div>
              <div className="overflow-hidden rounded-2xl border border-grid-line/20">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('inviteCodes.table.code')}</TableHead>
                      <TableHead>{t('inviteCodes.table.parent')}</TableHead>
                      <TableHead>{t('inviteCodes.table.depth')}</TableHead>
                      <TableHead>{t('inviteCodes.table.status')}</TableHead>
                      <TableHead>{t('inviteCodes.table.used')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tree.nodes.map((node) => (
                      <TableRow key={node.invite_code_id}>
                        <TableCell className="font-mono text-neon-cyan">
                          {shortId(node.invite_code_id, 12)}
                        </TableCell>
                        <TableCell className="font-mono text-xs text-muted-foreground">
                          {shortId(node.parent_invite_code_id, 12)}
                        </TableCell>
                        <TableCell>{node.generation_depth}</TableCell>
                        <TableCell>
                          <GrowthStatusChip label={humanizeToken(node.status)} tone={statusTone(node.status)} />
                        </TableCell>
                        <TableCell>{formatDateTime(node.used_at, locale)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}
        </div>
      </article>
    </div>
  );
}

function ExportsAuditTab({
  batches,
  selectedBatch,
  lastRawCodes,
  isExporting,
  locale,
  t,
  onSelectBatch,
  onExport,
}: {
  batches: AdminInviteBatchResponse[];
  selectedBatch: AdminInviteBatchResponse | null;
  lastRawCodes: string[];
  isExporting: boolean;
  locale: string;
  t: ReturnType<typeof useTranslations>;
  onSelectBatch: (batchId: string) => void;
  onExport: (batchId: string) => void;
}) {
  return (
    <div className="grid gap-6 xl:grid-cols-12">
      <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-4">
        <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
          {t('inviteCodes.exports.title')}
        </h2>
        <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
          {t('inviteCodes.exports.description')}
        </p>
        <div className="mt-5 grid gap-4">
          <SelectField
            label={t('inviteCodes.fields.batch')}
            value={selectedBatch?.id ?? ''}
            onChange={onSelectBatch}
            options={['', ...batches.map((batch) => batch.id)]}
            optionLabel={(value) => value ? shortId(value, 12) : t('common.missing')}
          />
          <Button
            type="button"
            magnetic={false}
            disabled={isExporting || !selectedBatch}
            onClick={() => {
              if (selectedBatch) onExport(selectedBatch.id);
            }}
          >
            <Download className="mr-2 h-4 w-4" aria-hidden="true" />
            {isExporting ? t('inviteCodes.actions.exporting') : t('inviteCodes.actions.exportBatch')}
          </Button>
        </div>
        {selectedBatch ? (
          <div className="mt-5 grid gap-3">
            <InfoLine label={t('inviteCodes.table.batch')} value={shortId(selectedBatch.id, 12)} />
            <InfoLine label={t('inviteCodes.table.status')} value={humanizeToken(selectedBatch.status)} />
            <InfoLine label={t('inviteCodes.table.created')} value={formatDateTime(selectedBatch.created_at, locale)} />
          </div>
        ) : null}
      </article>

      <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-8">
        <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
          {t('inviteCodes.exports.auditTitle')}
        </h2>
        <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
          {t('inviteCodes.exports.auditDescription')}
        </p>
        <div className="mt-5">
          {lastRawCodes.length === 0 ? (
            <GrowthEmptyState label={t('inviteCodes.exports.empty')} />
          ) : (
            <div className="overflow-hidden rounded-2xl border border-grid-line/20">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('inviteCodes.table.code')}</TableHead>
                    <TableHead>{t('inviteCodes.table.exported')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {lastRawCodes.map((code) => (
                    <TableRow key={code}>
                      <TableCell className="font-mono text-neon-cyan">{code}</TableCell>
                      <TableCell>{t('common.missing')}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </article>
    </div>
  );
}

function SettingsTab({
  selectedCampaign,
  analytics,
  t,
}: {
  selectedCampaign: AdminInviteCampaignResponse | null;
  analytics: Awaited<ReturnType<typeof growthApi.getInviteCampaignAnalytics>>['data'] | null;
  t: ReturnType<typeof useTranslations>;
}) {
  const version = selectedCampaign?.current_version ?? null;
  return (
    <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
        {t('inviteCodes.settings.title')}
      </h2>
      <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
        {t('inviteCodes.settings.description')}
      </p>
      {!selectedCampaign || !version ? (
        <div className="mt-5">
          <GrowthEmptyState label={t('inviteCodes.settings.empty')} />
        </div>
      ) : (
        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <InfoLine label={t('inviteCodes.fields.campaign')} value={selectedCampaign.campaign_key} />
          <InfoLine label={t('inviteCodes.fields.ownerMode')} value={humanizeToken(selectedCampaign.owner_mode)} />
          <InfoLine label={t('inviteCodes.fields.grantMode')} value={humanizeToken(version.grant_mode)} />
          <InfoLine label={t('inviteCodes.fields.grantDurationDays')} value={String(version.grant_duration_days ?? '--')} />
          <InfoLine label={t('inviteCodes.fields.childInviteCount')} value={String(version.child_invite_count)} />
          <InfoLine label={t('inviteCodes.fields.childGrantDurationDays')} value={String(version.child_grant_duration_days ?? '--')} />
          <InfoLine label={t('inviteCodes.fields.childInviteFreeDays')} value={String(version.child_invite_free_days)} />
          <InfoLine label={t('inviteCodes.fields.childInviteExpiryDays')} value={String(version.child_invite_expiry_days)} />
          <InfoLine label={t('inviteCodes.fields.maxGenerationDepth')} value={String(version.max_generation_depth)} />
          <InfoLine label={t('inviteCodes.settings.issued')} value={String(analytics?.issued_total ?? analytics?.issued_count ?? '--')} />
          <InfoLine label={t('inviteCodes.settings.blocked')} value={String(analytics?.blocked_count ?? '--')} />
          <InfoLine
            label={t('inviteCodes.settings.childIssued')}
            value={String(analytics?.child_invites_issued_total ?? '--')}
          />
          <InfoLine label={t('inviteCodes.settings.maxDepth')} value={String(analytics?.max_depth_reached ?? '--')} />
          <InfoLine label={t('inviteCodes.settings.surfaces')} value={version.allowed_surfaces.join(', ')} />
        </div>
      )}
    </article>
  );
}

function InviteCodesTable({
  inviteCodes,
  isLoading,
  locale,
  t,
}: {
  inviteCodes: AdminInviteCodeSummaryResponse[];
  isLoading: boolean;
  locale: string;
  t: ReturnType<typeof useTranslations>;
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t('inviteCodes.table.code')}</TableHead>
          <TableHead>{t('inviteCodes.table.status')}</TableHead>
          <TableHead>{t('inviteCodes.table.used')}</TableHead>
          <TableHead>{t('inviteCodes.table.depth')}</TableHead>
          <TableHead>{t('inviteCodes.table.expires')}</TableHead>
          <TableHead>{t('inviteCodes.table.created')}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {isLoading ? (
          <TableRow>
            <TableCell colSpan={6}>
              <GrowthEmptyState label={t('inviteCodes.inventory.loading')} />
            </TableCell>
          </TableRow>
        ) : inviteCodes.length === 0 ? (
          <TableRow>
            <TableCell colSpan={6}>
              <GrowthEmptyState label={t('inviteCodes.inventory.empty')} />
            </TableCell>
          </TableRow>
        ) : (
          inviteCodes.map((invite) => (
            <TableRow key={invite.id}>
              <TableCell>
                <div className="space-y-1">
                  <p className="font-display uppercase tracking-[0.14em] text-white">
                    {invite.code_prefix ?? shortId(invite.id, 12)}
                  </p>
                  <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    #{shortId(invite.id)}
                  </p>
                </div>
              </TableCell>
              <TableCell>
                <GrowthStatusChip label={humanizeToken(invite.status)} tone={statusTone(invite.status)} />
              </TableCell>
              <TableCell>
                <GrowthStatusChip
                  label={invite.is_used ? t('common.used') : t('common.unused')}
                  tone={invite.is_used ? 'warning' : 'success'}
                />
              </TableCell>
              <TableCell>{invite.generation_depth ?? 0}</TableCell>
              <TableCell>{formatDateTime(invite.expires_at, locale)}</TableCell>
              <TableCell>{formatDateTime(invite.created_at, locale)}</TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );
}

function TextField({
  label,
  value,
  onChange,
  type = 'text',
  required = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
}) {
  return (
    <label className="block text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
      {label}
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required={required}
        className="mt-2 w-full rounded-lg border border-grid-line/25 bg-terminal-bg/70 px-3 py-2 text-sm text-foreground outline-hidden focus:border-neon-cyan/60 focus:ring-2 focus:ring-neon-cyan/25"
      />
    </label>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange,
  optionLabel,
  compact = false,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
  optionLabel?: (value: string) => string;
  compact?: boolean;
}) {
  return (
    <label className="block text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={cn(
          'mt-2 w-full rounded-lg border border-grid-line/25 bg-terminal-bg/70 px-3 py-2 text-sm text-foreground outline-hidden focus:border-neon-cyan/60 focus:ring-2 focus:ring-neon-cyan/25',
          compact ? 'min-w-44' : '',
        )}
      >
        {options.map((option) => (
          <option key={option || 'empty'} value={option}>
            {optionLabel ? optionLabel(option) : option}
          </option>
        ))}
      </select>
    </label>
  );
}

function CheckboxRow({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-3 rounded-xl border border-grid-line/20 bg-terminal-bg/45 p-3 text-sm font-mono text-muted-foreground">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 accent-neon-cyan"
      />
      {label}
    </label>
  );
}

function InfoLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/45 p-3">
      <p className="text-[10px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 break-words font-mono text-sm text-white">{value}</p>
    </div>
  );
}
