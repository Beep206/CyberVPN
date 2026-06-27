'use client';

import { useState } from 'react';
import type { FormEvent } from 'react';
import { Flag, Send, ShieldCheck } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { growthApi } from '@/lib/api/growth';
import type {
  AdminGrowthCampaignActionRequest,
  AdminGrowthCampaignResponse,
} from '@/lib/api/growth';
import { GrowthEmptyState } from '@/features/growth/components/growth-empty-state';
import { GrowthPageShell } from '@/features/growth/components/growth-page-shell';
import { GrowthStatusChip } from '@/features/growth/components/growth-status-chip';
import {
  formatCompactNumber,
  formatDateTime,
  getErrorMessage,
  humanizeToken,
} from '@/features/growth/lib/formatting';
import { cn } from '@/lib/utils';

type CampaignAction = 'publish' | 'pause' | 'resume' | 'archive' | 'revoke';
type StackingMode = 'exclusive' | 'allow_with_same_campaign' | 'benefits_only_append' | 'max_discount';

const CAMPAIGN_ACTIONS: CampaignAction[] = ['publish', 'pause', 'resume', 'archive', 'revoke'];
const DANGEROUS_ACTIONS = new Set<CampaignAction>(['publish', 'archive', 'revoke']);
const STACKING_MODES: StackingMode[] = [
  'exclusive',
  'allow_with_same_campaign',
  'benefits_only_append',
  'max_discount',
];

function defaultCreateForm() {
  return {
    campaignKey: '',
    name: '',
    description: '',
    startsAt: '',
    expiresAt: '',
    priority: '0',
    stackingMode: 'exclusive' as StackingMode,
    stackingGroup: '',
  };
}

function actionTone(action: CampaignAction) {
  if (action === 'publish' || action === 'resume') return 'success' as const;
  if (action === 'revoke' || action === 'archive') return 'danger' as const;
  return 'warning' as const;
}

function statusTone(status: string) {
  if (status === 'active') return 'success' as const;
  if (status === 'revoked' || status === 'archived') return 'danger' as const;
  if (status === 'paused' || status === 'scheduled') return 'warning' as const;
  return 'neutral' as const;
}

function toOptionalIsoDateTime(value: string) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function campaignCountByStatus(campaigns: AdminGrowthCampaignResponse[], status: string) {
  return campaigns.filter((campaign) => campaign.status === status).length;
}

function editFormFromCampaign(campaign: AdminGrowthCampaignResponse) {
  return {
    name: campaign.name,
    description: campaign.description ?? '',
    priority: String(campaign.priority),
    stackingMode: campaign.stacking_mode as StackingMode,
    stackingGroup: campaign.stacking_group ?? '',
    reasonCode: 'campaign_version_update',
  };
}

export function GrowthCampaignsConsole() {
  const t = useTranslations('Growth');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState(defaultCreateForm);
  const [editForm, setEditForm] = useState({
    name: '',
    description: '',
    priority: '0',
    stackingMode: 'exclusive' as StackingMode,
    stackingGroup: '',
    reasonCode: 'campaign_version_update',
  });
  const [actionForm, setActionForm] = useState({
    action: 'publish' as CampaignAction,
    reasonCode: 'growth_campaign_publish',
    confirmation: '',
  });
  const [feedback, setFeedback] = useState<string | null>(null);

  const campaignsQuery = useQuery({
    queryKey: ['growth', 'campaigns', statusFilter],
    queryFn: async () => {
      const response = await growthApi.listGrowthCampaigns({
        status: statusFilter || undefined,
        offset: 0,
        limit: 50,
        sort: '-updated_at',
      });
      return response.data;
    },
  });

  const selectedCampaignQuery = useQuery({
    queryKey: ['growth', 'campaigns', 'detail', selectedCampaignId],
    queryFn: async () => {
      if (!selectedCampaignId) {
        throw new Error('campaign_id_required');
      }
      const response = await growthApi.getGrowthCampaign(selectedCampaignId);
      return response.data;
    },
    enabled: Boolean(selectedCampaignId),
  });

  const campaigns = campaignsQuery.data?.items ?? [];
  const selectedCampaign =
    selectedCampaignQuery.data
    ?? campaigns.find((campaign) => campaign.id === selectedCampaignId)
    ?? null;
  const selectedRequiresConfirmation = DANGEROUS_ACTIONS.has(actionForm.action);
  const confirmationMatches =
    !selectedRequiresConfirmation
    || (selectedCampaign != null && actionForm.confirmation === selectedCampaign.campaign_key);

  function selectCampaign(campaign: AdminGrowthCampaignResponse) {
    setSelectedCampaignId(campaign.id);
    setEditForm(editFormFromCampaign(campaign));
    setActionForm((current) => ({
      ...current,
      confirmation: '',
    }));
  }

  const createMutation = useMutation({
    mutationFn: () =>
      growthApi.createGrowthCampaign({
        campaign_key: createForm.campaignKey.trim(),
        name: createForm.name.trim(),
        description: createForm.description.trim() || null,
        priority: Number.parseInt(createForm.priority, 10) || 0,
        schedule: {
          starts_at: toOptionalIsoDateTime(createForm.startsAt),
          expires_at: toOptionalIsoDateTime(createForm.expiresAt),
        },
        stacking: {
          mode: createForm.stackingMode,
          group: createForm.stackingGroup.trim() || null,
        },
      }),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['growth', 'campaigns'] });
      setSelectedCampaignId(response.data.id);
      setEditForm(editFormFromCampaign(response.data));
      setCreateForm(defaultCreateForm());
      setFeedback(t('campaigns.feedback.created'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('campaigns.feedback.createFailed')));
    },
  });

  const updateMutation = useMutation({
    mutationFn: (campaign: AdminGrowthCampaignResponse) =>
      growthApi.updateGrowthCampaign(campaign.id, {
        name: editForm.name.trim(),
        description: editForm.description.trim() || null,
        priority: Number.parseInt(editForm.priority, 10) || 0,
        stacking: {
          mode: editForm.stackingMode,
          group: editForm.stackingGroup.trim() || null,
        },
        expected_version: campaign.current_version,
        reason_code: editForm.reasonCode.trim(),
      }),
    onSuccess: async (response) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['growth', 'campaigns'] }),
        queryClient.invalidateQueries({ queryKey: ['growth', 'campaigns', 'detail', response.data.id] }),
      ]);
      setEditForm(editFormFromCampaign(response.data));
      setFeedback(t('campaigns.feedback.updated'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('campaigns.feedback.updateFailed')));
    },
  });

  const actionMutation = useMutation({
    mutationFn: ({
      campaign,
      action,
      payload,
    }: {
      campaign: AdminGrowthCampaignResponse;
      action: CampaignAction;
      payload: AdminGrowthCampaignActionRequest;
    }) => {
      if (action === 'publish') return growthApi.publishGrowthCampaign(campaign.id, payload);
      if (action === 'pause') return growthApi.pauseGrowthCampaign(campaign.id, payload);
      if (action === 'resume') return growthApi.resumeGrowthCampaign(campaign.id, payload);
      if (action === 'archive') return growthApi.archiveGrowthCampaign(campaign.id, payload);
      return growthApi.revokeGrowthCampaign(campaign.id, payload);
    },
    onSuccess: async (response, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['growth', 'campaigns'] }),
        queryClient.invalidateQueries({ queryKey: ['growth', 'campaigns', 'detail', response.data.id] }),
      ]);
      setActionForm((current) => ({ ...current, confirmation: '' }));
      setFeedback(t(`campaigns.feedback.${variables.action}`));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('campaigns.feedback.actionFailed')));
    },
  });

  function handleCreateSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!createForm.campaignKey.trim() || !createForm.name.trim()) {
      setFeedback(t('campaigns.feedback.required'));
      return;
    }
    createMutation.mutate();
  }

  function handleUpdateSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCampaign) return;
    if (!editForm.name.trim() || !editForm.reasonCode.trim()) {
      setFeedback(t('campaigns.feedback.required'));
      return;
    }
    updateMutation.mutate(selectedCampaign);
  }

  function handleActionSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCampaign || !actionForm.reasonCode.trim() || !confirmationMatches) {
      setFeedback(t('campaigns.feedback.actionBlocked'));
      return;
    }
    actionMutation.mutate({
      campaign: selectedCampaign,
      action: actionForm.action,
      payload: {
        expected_version: selectedCampaign.current_version,
        reason_code: actionForm.reasonCode.trim(),
      },
    });
  }

  return (
    <GrowthPageShell
      eyebrow={t('campaigns.eyebrow')}
      title={t('campaigns.title')}
      description={t('campaigns.description')}
      icon={Flag}
      metrics={[
        {
          label: t('campaigns.metrics.total'),
          value: formatCompactNumber(campaignsQuery.data?.total ?? campaigns.length, locale),
          hint: t('campaigns.metrics.totalHint'),
          tone: 'info',
        },
        {
          label: t('campaigns.metrics.active'),
          value: formatCompactNumber(campaignCountByStatus(campaigns, 'active'), locale),
          hint: t('campaigns.metrics.activeHint'),
          tone: 'success',
        },
        {
          label: t('campaigns.metrics.drafts'),
          value: formatCompactNumber(campaignCountByStatus(campaigns, 'draft'), locale),
          hint: t('campaigns.metrics.draftsHint'),
          tone: 'warning',
        },
        {
          label: t('campaigns.metrics.version'),
          value: selectedCampaign ? String(selectedCampaign.current_version) : t('common.missing'),
          hint: t('campaigns.metrics.versionHint'),
          tone: selectedCampaign ? 'neutral' : 'warning',
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

      <div className="grid gap-6 2xl:grid-cols-[minmax(18rem,0.8fr)_minmax(0,1.25fr)_minmax(20rem,1fr)]">
        <form
          onSubmit={handleCreateSubmit}
          className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur"
        >
          <h2 className="text-sm font-display uppercase tracking-[0.22em] text-white">
            {t('campaigns.createTitle')}
          </h2>
          <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
            {t('campaigns.createDescription')}
          </p>
          <div className="mt-5 grid gap-4">
            <TextField
              label={t('campaigns.fields.campaignKey')}
              value={createForm.campaignKey}
              onChange={(value) => setCreateForm((current) => ({ ...current, campaignKey: value }))}
              required
            />
            <TextField
              label={t('campaigns.fields.name')}
              value={createForm.name}
              onChange={(value) => setCreateForm((current) => ({ ...current, name: value }))}
              required
            />
            <TextField
              label={t('campaigns.fields.description')}
              value={createForm.description}
              onChange={(value) => setCreateForm((current) => ({ ...current, description: value }))}
            />
            <TextField
              label={t('campaigns.fields.priority')}
              type="number"
              value={createForm.priority}
              onChange={(value) => setCreateForm((current) => ({ ...current, priority: value }))}
            />
            <TextField
              label={t('campaigns.fields.startsAt')}
              type="datetime-local"
              value={createForm.startsAt}
              onChange={(value) => setCreateForm((current) => ({ ...current, startsAt: value }))}
            />
            <TextField
              label={t('campaigns.fields.expiresAt')}
              type="datetime-local"
              value={createForm.expiresAt}
              onChange={(value) => setCreateForm((current) => ({ ...current, expiresAt: value }))}
            />
            <SelectField
              label={t('campaigns.fields.stackingMode')}
              value={createForm.stackingMode}
              options={STACKING_MODES}
              onChange={(value) =>
                setCreateForm((current) => ({ ...current, stackingMode: value as StackingMode }))
              }
            />
            <TextField
              label={t('campaigns.fields.stackingGroup')}
              value={createForm.stackingGroup}
              onChange={(value) => setCreateForm((current) => ({ ...current, stackingGroup: value }))}
            />
          </div>
          <Button
            type="submit"
            className="mt-5 w-full"
            magnetic={false}
            disabled={createMutation.isPending}
          >
            <Send className="mr-2 h-4 w-4" aria-hidden="true" />
            {createMutation.isPending ? t('campaigns.creating') : t('campaigns.createAction')}
          </Button>
        </form>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.22em] text-white">
                {t('campaigns.inventoryTitle')}
              </h2>
              <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
                {t('campaigns.inventoryDescription')}
              </p>
            </div>
            <SelectField
              label={t('campaigns.fields.status')}
              value={statusFilter}
              options={['', 'draft', 'scheduled', 'active', 'paused', 'archived', 'revoked']}
              onChange={setStatusFilter}
              optionLabel={(value) => (value ? humanizeToken(value) : t('campaigns.fields.allStatuses'))}
              compact
            />
          </div>
          <div className="mt-5 grid gap-3">
            {campaignsQuery.isLoading ? (
              <GrowthEmptyState label={t('campaigns.loading')} />
            ) : campaigns.length === 0 ? (
              <GrowthEmptyState label={t('campaigns.empty')} />
            ) : (
              campaigns.map((campaign) => (
                <button
                  key={campaign.id}
                  type="button"
                  onClick={() => selectCampaign(campaign)}
                  className={cn(
                    'rounded-lg border p-4 text-left transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan',
                    campaign.id === selectedCampaignId
                      ? 'border-neon-cyan/45 bg-neon-cyan/10'
                      : 'border-grid-line/20 bg-terminal-bg/45 hover:border-grid-line/50',
                  )}
                  aria-pressed={campaign.id === selectedCampaignId}
                  aria-label={t('campaigns.selectCampaign', { key: campaign.campaign_key })}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate font-mono text-sm text-white">{campaign.campaign_key}</p>
                      <p className="mt-1 text-sm text-muted-foreground">{campaign.name}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <GrowthStatusChip label={humanizeToken(campaign.status)} tone={statusTone(campaign.status)} />
                      <GrowthStatusChip
                        label={t('campaigns.badges.version', { version: campaign.current_version })}
                        tone="neutral"
                      />
                    </div>
                  </div>
                  <div className="mt-3 grid gap-2 text-xs font-mono text-muted-foreground md:grid-cols-2">
                    <span>{formatDateTime(campaign.updated_at, locale)}</span>
                    <span>{campaign.published_at ? formatDateTime(campaign.published_at, locale) : t('common.missing')}</span>
                  </div>
                </button>
              ))
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
          <h2 className="text-sm font-display uppercase tracking-[0.22em] text-white">
            {t('campaigns.detailTitle')}
          </h2>
          {selectedCampaign ? (
            <div className="mt-5 space-y-6">
              <div className="space-y-3 rounded-lg border border-grid-line/20 bg-terminal-bg/45 p-4">
                <InfoLine label={t('campaigns.fields.campaignKey')} value={selectedCampaign.campaign_key} />
                <InfoLine label={t('campaigns.fields.status')} value={humanizeToken(selectedCampaign.status)} />
                <InfoLine
                  label={t('campaigns.fields.version')}
                  value={String(selectedCampaign.current_version)}
                />
                <InfoLine
                  label={t('campaigns.fields.schedule')}
                  value={[
                    selectedCampaign.starts_at ? formatDateTime(selectedCampaign.starts_at, locale) : t('common.noExpiry'),
                    selectedCampaign.expires_at ? formatDateTime(selectedCampaign.expires_at, locale) : t('common.noExpiry'),
                  ].join(' / ')}
                />
              </div>

              <form onSubmit={handleUpdateSubmit} className="space-y-4">
                <div>
                  <h3 className="text-xs font-display uppercase tracking-[0.2em] text-white">
                    {t('campaigns.updateTitle')}
                  </h3>
                  <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
                    {t('campaigns.updateDescription')}
                  </p>
                </div>
                <TextField
                  label={t('campaigns.fields.name')}
                  value={editForm.name}
                  onChange={(value) => setEditForm((current) => ({ ...current, name: value }))}
                  required
                />
                <TextField
                  label={t('campaigns.fields.description')}
                  value={editForm.description}
                  onChange={(value) => setEditForm((current) => ({ ...current, description: value }))}
                />
                <TextField
                  label={t('campaigns.fields.priority')}
                  type="number"
                  value={editForm.priority}
                  onChange={(value) => setEditForm((current) => ({ ...current, priority: value }))}
                />
                <SelectField
                  label={t('campaigns.fields.stackingMode')}
                  value={editForm.stackingMode}
                  options={STACKING_MODES}
                  onChange={(value) =>
                    setEditForm((current) => ({ ...current, stackingMode: value as StackingMode }))
                  }
                />
                <TextField
                  label={t('campaigns.fields.stackingGroup')}
                  value={editForm.stackingGroup}
                  onChange={(value) => setEditForm((current) => ({ ...current, stackingGroup: value }))}
                />
                <TextField
                  label={t('campaigns.fields.reasonCode')}
                  value={editForm.reasonCode}
                  onChange={(value) => setEditForm((current) => ({ ...current, reasonCode: value }))}
                  required
                />
                <Button type="submit" magnetic={false} disabled={updateMutation.isPending}>
                  <ShieldCheck className="mr-2 h-4 w-4" aria-hidden="true" />
                  {updateMutation.isPending ? t('campaigns.updating') : t('campaigns.updateAction')}
                </Button>
              </form>

              <form onSubmit={handleActionSubmit} className="space-y-4">
                <div>
                  <h3 className="text-xs font-display uppercase tracking-[0.2em] text-white">
                    {t('campaigns.lifecycleTitle')}
                  </h3>
                  <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
                    {t('campaigns.lifecycleDescription')}
                  </p>
                </div>
                <SelectField
                  label={t('campaigns.fields.action')}
                  value={actionForm.action}
                  options={CAMPAIGN_ACTIONS}
                  onChange={(value) =>
                    setActionForm((current) => ({
                      ...current,
                      action: value as CampaignAction,
                      confirmation: '',
                    }))
                  }
                  optionLabel={(value) => t(`campaigns.actions.${value}`)}
                />
                <TextField
                  label={t('campaigns.fields.reasonCode')}
                  value={actionForm.reasonCode}
                  onChange={(value) => setActionForm((current) => ({ ...current, reasonCode: value }))}
                  required
                />
                {selectedRequiresConfirmation ? (
                  <TextField
                    label={t('campaigns.fields.confirmation')}
                    value={actionForm.confirmation}
                    onChange={(value) => setActionForm((current) => ({ ...current, confirmation: value }))}
                    placeholder={selectedCampaign.campaign_key}
                    required
                  />
                ) : null}
                <Button
                  type="submit"
                  magnetic={false}
                  disabled={
                    actionMutation.isPending
                    || !actionForm.reasonCode.trim()
                    || !confirmationMatches
                  }
                >
                  {actionMutation.isPending
                    ? t('campaigns.applying')
                    : t(`campaigns.actions.${actionForm.action}`)}
                </Button>
                <GrowthStatusChip
                  label={selectedRequiresConfirmation ? t('campaigns.confirmationRequired') : t('campaigns.reasonRequired')}
                  tone={actionTone(actionForm.action)}
                />
              </form>
            </div>
          ) : (
            <div className="mt-5">
              <GrowthEmptyState label={t('campaigns.detailEmpty')} />
            </div>
          )}
        </article>
      </div>
    </GrowthPageShell>
  );
}

function TextField({
  label,
  value,
  onChange,
  type = 'text',
  required = false,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
  placeholder?: string;
}) {
  return (
    <label className="block text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
      {label}
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required={required}
        placeholder={placeholder}
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
    <label className={cn('block text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground', compact ? 'min-w-48' : '')}>
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-2 w-full rounded-lg border border-grid-line/25 bg-terminal-bg/70 px-3 py-2 text-sm text-foreground outline-hidden focus:border-neon-cyan/60 focus:ring-2 focus:ring-neon-cyan/25"
      >
        {options.map((option) => (
          <option key={option || 'all'} value={option}>
            {optionLabel ? optionLabel(option) : humanizeToken(option)}
          </option>
        ))}
      </select>
    </label>
  );
}

function InfoLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <p className="text-[11px] font-mono uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 break-words font-mono text-xs text-foreground">{value}</p>
    </div>
  );
}
