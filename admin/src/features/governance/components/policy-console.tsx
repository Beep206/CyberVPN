'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { RefreshCw, Settings2, ShieldCheck } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { governanceApi } from '@/lib/api/governance';
import { GovernanceEmptyState } from '@/features/governance/components/governance-empty-state';
import { GovernanceJsonPreview } from '@/features/governance/components/governance-json-preview';
import { GovernancePageShell } from '@/features/governance/components/governance-page-shell';
import { GovernanceStatusChip } from '@/features/governance/components/governance-status-chip';
import {
  GOVERNANCE_ROLE_PERMISSION_MATRIX,
  formatDateTime,
  getErrorMessage,
  humanizeToken,
  matchesSearch,
  settingFamily,
  shortId,
  summarizeJsonValue,
} from '@/features/governance/lib/formatting';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';

function defaultSettingValue() {
  return JSON.stringify({ enabled: true }, null, 2);
}

function parseJsonInput(value: string) {
  return JSON.parse(value);
}

type MiniAppRuntimeDraft = {
  enabled: boolean;
  mode: 'live' | 'canary' | 'maintenance' | 'rollback';
  trialEnabled: boolean;
  checkoutEnabled: boolean;
  configEnabled: boolean;
  maintenanceMessage: string;
  canaryTelegramUserIds: string;
};

type MiniAppLaunchReadinessDraft = {
  observabilityAcknowledged: boolean;
  incidentRunbookAcknowledged: boolean;
  checkoutCanaryPassed: boolean;
  configDeliveryCanaryPassed: boolean;
  rollbackDrillAcknowledged: boolean;
  supportWindowConfirmed: boolean;
  customerCommsReady: boolean;
  statusPageTemplateReady: boolean;
  incidentChannel: string;
  rollbackCommander: string;
  primaryOncallContact: string;
  releaseWindowNote: string;
};

type MiniAppLaunchAction =
  | 'promote_to_live'
  | 'enter_maintenance'
  | 'start_rollback'
  | 'return_to_canary';

const DEFAULT_MINIAPP_RUNTIME_DRAFT: MiniAppRuntimeDraft = {
  enabled: true,
  mode: 'live',
  trialEnabled: true,
  checkoutEnabled: true,
  configEnabled: true,
  maintenanceMessage: '',
  canaryTelegramUserIds: '',
};

const DEFAULT_MINIAPP_LAUNCH_READINESS_DRAFT: MiniAppLaunchReadinessDraft = {
  observabilityAcknowledged: false,
  incidentRunbookAcknowledged: false,
  checkoutCanaryPassed: false,
  configDeliveryCanaryPassed: false,
  rollbackDrillAcknowledged: false,
  supportWindowConfirmed: false,
  customerCommsReady: false,
  statusPageTemplateReady: false,
  incidentChannel: '',
  rollbackCommander: '',
  primaryOncallContact: '',
  releaseWindowNote: '',
};

function buildMiniAppRuntimeDraft(input?: {
  enabled?: boolean;
  mode?: 'live' | 'canary' | 'maintenance' | 'rollback';
  trial_enabled?: boolean;
  checkout_enabled?: boolean;
  config_enabled?: boolean;
  maintenance_message?: string | null;
  canary_telegram_user_ids?: number[] | null;
} | null): MiniAppRuntimeDraft {
  return {
    enabled: input?.enabled ?? DEFAULT_MINIAPP_RUNTIME_DRAFT.enabled,
    mode: input?.mode ?? DEFAULT_MINIAPP_RUNTIME_DRAFT.mode,
    trialEnabled: input?.trial_enabled ?? DEFAULT_MINIAPP_RUNTIME_DRAFT.trialEnabled,
    checkoutEnabled: input?.checkout_enabled ?? DEFAULT_MINIAPP_RUNTIME_DRAFT.checkoutEnabled,
    configEnabled: input?.config_enabled ?? DEFAULT_MINIAPP_RUNTIME_DRAFT.configEnabled,
    maintenanceMessage: input?.maintenance_message ?? DEFAULT_MINIAPP_RUNTIME_DRAFT.maintenanceMessage,
    canaryTelegramUserIds: input?.canary_telegram_user_ids?.join(', ') ?? DEFAULT_MINIAPP_RUNTIME_DRAFT.canaryTelegramUserIds,
  };
}

function parseCanaryTelegramUserIds(value: string) {
  const entries = value
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);

  const parsed = new Set<number>();
  for (const entry of entries) {
    const numeric = Number(entry);
    if (!Number.isInteger(numeric) || numeric <= 0) {
      throw new Error(`Invalid Telegram user id: ${entry}`);
    }
    parsed.add(numeric);
  }

  return [...parsed].sort((left, right) => left - right);
}

function buildMiniAppLaunchReadinessDraft(input?: {
  observability_acknowledged?: boolean;
  incident_runbook_acknowledged?: boolean;
  checkout_canary_passed?: boolean;
  config_delivery_canary_passed?: boolean;
  rollback_drill_acknowledged?: boolean;
  support_window_confirmed?: boolean;
  customer_comms_ready?: boolean;
  status_page_template_ready?: boolean;
  incident_channel?: string | null;
  rollback_commander?: string | null;
  primary_oncall_contact?: string | null;
  release_window_note?: string | null;
} | null): MiniAppLaunchReadinessDraft {
  return {
    observabilityAcknowledged:
      input?.observability_acknowledged
      ?? DEFAULT_MINIAPP_LAUNCH_READINESS_DRAFT.observabilityAcknowledged,
    incidentRunbookAcknowledged:
      input?.incident_runbook_acknowledged
      ?? DEFAULT_MINIAPP_LAUNCH_READINESS_DRAFT.incidentRunbookAcknowledged,
    checkoutCanaryPassed:
      input?.checkout_canary_passed
      ?? DEFAULT_MINIAPP_LAUNCH_READINESS_DRAFT.checkoutCanaryPassed,
    configDeliveryCanaryPassed:
      input?.config_delivery_canary_passed
      ?? DEFAULT_MINIAPP_LAUNCH_READINESS_DRAFT.configDeliveryCanaryPassed,
    rollbackDrillAcknowledged:
      input?.rollback_drill_acknowledged
      ?? DEFAULT_MINIAPP_LAUNCH_READINESS_DRAFT.rollbackDrillAcknowledged,
    supportWindowConfirmed:
      input?.support_window_confirmed
      ?? DEFAULT_MINIAPP_LAUNCH_READINESS_DRAFT.supportWindowConfirmed,
    customerCommsReady:
      input?.customer_comms_ready
      ?? DEFAULT_MINIAPP_LAUNCH_READINESS_DRAFT.customerCommsReady,
    statusPageTemplateReady:
      input?.status_page_template_ready
      ?? DEFAULT_MINIAPP_LAUNCH_READINESS_DRAFT.statusPageTemplateReady,
    incidentChannel:
      input?.incident_channel
      ?? DEFAULT_MINIAPP_LAUNCH_READINESS_DRAFT.incidentChannel,
    rollbackCommander:
      input?.rollback_commander
      ?? DEFAULT_MINIAPP_LAUNCH_READINESS_DRAFT.rollbackCommander,
    primaryOncallContact:
      input?.primary_oncall_contact
      ?? DEFAULT_MINIAPP_LAUNCH_READINESS_DRAFT.primaryOncallContact,
    releaseWindowNote:
      input?.release_window_note
      ?? DEFAULT_MINIAPP_LAUNCH_READINESS_DRAFT.releaseWindowNote,
  };
}

export function PolicyConsole() {
  const t = useTranslations('Governance');
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [selectedSettingId, setSelectedSettingId] = useState<number | null>(null);
  const [editorMode, setEditorMode] = useState<'create' | 'update'>('create');
  const [editorKey, setEditorKey] = useState('');
  const [editorValue, setEditorValue] = useState(defaultSettingValue());
  const [editorDescription, setEditorDescription] = useState('');
  const [editorIsPublic, setEditorIsPublic] = useState(false);
  const [miniAppDraft, setMiniAppDraft] = useState<MiniAppRuntimeDraft | null>(null);
  const [miniAppLaunchReadinessDraft, setMiniAppLaunchReadinessDraft] =
    useState<MiniAppLaunchReadinessDraft | null>(null);
  const [miniAppChangeReason, setMiniAppChangeReason] = useState('');
  const [miniAppLaunchReadinessChangeReason, setMiniAppLaunchReadinessChangeReason] = useState('');
  const [miniAppLaunchActionReason, setMiniAppLaunchActionReason] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);

  const settingsQuery = useQuery({
    queryKey: ['governance', 'settings'],
    queryFn: async () => {
      const response = await governanceApi.getSettings();
      return response.data;
    },
    staleTime: 30_000,
  });

  const miniAppRuntimeQuery = useQuery({
    queryKey: ['governance', 'system-config', 'miniapp-runtime'],
    queryFn: async () => {
      const response = await governanceApi.getMiniAppRuntimeConfig();
      return response.data;
    },
    staleTime: 15_000,
  });

  const miniAppLaunchReadinessQuery = useQuery({
    queryKey: ['governance', 'system-config', 'miniapp-launch-readiness'],
    queryFn: async () => {
      const response = await governanceApi.getMiniAppLaunchReadinessConfig();
      return response.data;
    },
    staleTime: 15_000,
  });

  const miniAppLaunchSummaryQuery = useQuery({
    queryKey: ['governance', 'system-config', 'miniapp-launch-summary'],
    queryFn: async () => {
      const response = await governanceApi.getMiniAppLaunchSummary();
      return response.data;
    },
    staleTime: 10_000,
  });

  const miniAppLaunchTimelineQuery = useQuery({
    queryKey: ['governance', 'system-config', 'miniapp-launch-timeline'],
    queryFn: async () => {
      const response = await governanceApi.getMiniAppLaunchTimeline({ limit: 6 });
      return response.data;
    },
    staleTime: 10_000,
  });

  const createMutation = useMutation({
    mutationFn: (payload: {
      key: string;
      value: unknown;
      description: string | null;
      is_public: boolean;
    }) => governanceApi.createSetting(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['governance', 'settings'] });
      resetEditor();
      setFeedback(t('policy.createSuccess'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const updateMutation = useMutation({
    mutationFn: (payload: {
      id: number;
      value: unknown;
      description: string | null;
      is_public: boolean;
    }) =>
      governanceApi.updateSetting(payload.id, {
        value: payload.value,
        description: payload.description,
        is_public: payload.is_public,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['governance', 'settings'] });
      setFeedback(t('policy.updateSuccess'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const miniAppRuntimeMutation = useMutation({
    mutationFn: (canaryTelegramUserIds: number[]) =>
      governanceApi.updateMiniAppRuntimeConfig({
        enabled: effectiveMiniAppRuntime.enabled,
        mode: effectiveMiniAppRuntime.mode,
        trial_enabled: effectiveMiniAppRuntime.trialEnabled,
        checkout_enabled: effectiveMiniAppRuntime.checkoutEnabled,
        config_enabled: effectiveMiniAppRuntime.configEnabled,
        maintenance_message: effectiveMiniAppRuntime.maintenanceMessage.trim() || null,
        canary_telegram_user_ids: canaryTelegramUserIds,
        change_reason: miniAppChangeReason.trim() || null,
      }),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({
        queryKey: ['governance', 'system-config', 'miniapp-runtime'],
      });
      await queryClient.invalidateQueries({
        queryKey: ['governance', 'system-config', 'miniapp-launch-summary'],
      });
      await queryClient.invalidateQueries({
        queryKey: ['governance', 'system-config', 'miniapp-launch-timeline'],
      });
      setMiniAppDraft(buildMiniAppRuntimeDraft(response.data.rollout));
      setMiniAppChangeReason('');
      setFeedback(t('policy.runtimeControl.updateSuccess'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const miniAppLaunchReadinessMutation = useMutation({
    mutationFn: () =>
      governanceApi.updateMiniAppLaunchReadinessConfig({
        observability_acknowledged: effectiveMiniAppLaunchReadiness.observabilityAcknowledged,
        incident_runbook_acknowledged: effectiveMiniAppLaunchReadiness.incidentRunbookAcknowledged,
        checkout_canary_passed: effectiveMiniAppLaunchReadiness.checkoutCanaryPassed,
        config_delivery_canary_passed: effectiveMiniAppLaunchReadiness.configDeliveryCanaryPassed,
        rollback_drill_acknowledged: effectiveMiniAppLaunchReadiness.rollbackDrillAcknowledged,
        support_window_confirmed: effectiveMiniAppLaunchReadiness.supportWindowConfirmed,
        customer_comms_ready: effectiveMiniAppLaunchReadiness.customerCommsReady,
        status_page_template_ready: effectiveMiniAppLaunchReadiness.statusPageTemplateReady,
        incident_channel: effectiveMiniAppLaunchReadiness.incidentChannel.trim() || null,
        rollback_commander: effectiveMiniAppLaunchReadiness.rollbackCommander.trim() || null,
        primary_oncall_contact: effectiveMiniAppLaunchReadiness.primaryOncallContact.trim() || null,
        release_window_note: effectiveMiniAppLaunchReadiness.releaseWindowNote.trim() || null,
        change_reason: miniAppLaunchReadinessChangeReason.trim() || null,
      }),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({
        queryKey: ['governance', 'system-config', 'miniapp-launch-readiness'],
      });
      await queryClient.invalidateQueries({
        queryKey: ['governance', 'system-config', 'miniapp-launch-summary'],
      });
      await queryClient.invalidateQueries({
        queryKey: ['governance', 'system-config', 'miniapp-launch-timeline'],
      });
      setMiniAppLaunchReadinessDraft(
        buildMiniAppLaunchReadinessDraft(response.data.readiness),
      );
      setMiniAppLaunchReadinessChangeReason('');
      setFeedback(t('policy.launchReadiness.updateSuccess'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const miniAppLaunchActionMutation = useMutation({
    mutationFn: (action: MiniAppLaunchAction) =>
      governanceApi.executeMiniAppLaunchAction({
        action,
        change_reason: miniAppLaunchActionReason.trim() || null,
      }),
    onSuccess: async (response, action) => {
      await queryClient.invalidateQueries({
        queryKey: ['governance', 'system-config', 'miniapp-runtime'],
      });
      await queryClient.invalidateQueries({
        queryKey: ['governance', 'system-config', 'miniapp-launch-summary'],
      });
      await queryClient.invalidateQueries({
        queryKey: ['governance', 'system-config', 'miniapp-launch-timeline'],
      });
      setMiniAppDraft(buildMiniAppRuntimeDraft(response.data.runtime));
      setMiniAppLaunchActionReason('');
      setFeedback(t(`policy.launchActions.success.${action}`));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const settings = settingsQuery.data ?? [];
  const filteredSettings = settings.filter((setting) =>
    matchesSearch(
      [setting.key, setting.description, setting.value, setting.isPublic],
      search,
    ),
  );
  const selectedSetting =
    filteredSettings.find((setting) => setting.id === selectedSettingId) ??
    filteredSettings[0] ??
    null;
  const miniAppRuntime = miniAppRuntimeQuery.data ?? null;
  const miniAppLaunchSummary = miniAppLaunchSummaryQuery.data ?? null;
  const miniAppLaunchTimeline = miniAppLaunchTimelineQuery.data ?? [];
  const effectiveMiniAppRuntime = miniAppDraft ?? buildMiniAppRuntimeDraft(miniAppRuntime?.rollout);
  const effectiveRuntimeStatus = effectiveMiniAppRuntime.enabled
    ? effectiveMiniAppRuntime.mode
    : 'maintenance';
  const miniAppLaunchReadiness = miniAppLaunchReadinessQuery.data ?? null;
  const effectiveMiniAppLaunchReadiness = miniAppLaunchReadinessDraft
    ?? buildMiniAppLaunchReadinessDraft(miniAppLaunchReadiness?.readiness);
  const availableMiniAppLaunchActions = miniAppLaunchSummary?.available_actions ?? [];
  const orderedMiniAppLaunchActions = [
    miniAppLaunchSummary?.primary_action ?? null,
    ...availableMiniAppLaunchActions,
  ].filter((value, index, array): value is MiniAppLaunchAction => (
    Boolean(value) && array.indexOf(value) === index
  ));
  const launchChecklistReadiness = miniAppLaunchSummary?.readiness ?? null;
  const launchChecklistItems = [
    {
      key: 'observability',
      label: t('policy.launchReadiness.items.observability'),
      complete: Boolean(launchChecklistReadiness?.observability_acknowledged),
      value: null,
    },
    {
      key: 'incidentRunbook',
      label: t('policy.launchReadiness.items.incidentRunbook'),
      complete: Boolean(launchChecklistReadiness?.incident_runbook_acknowledged),
      value: null,
    },
    {
      key: 'checkoutCanary',
      label: t('policy.launchReadiness.items.checkoutCanary'),
      complete: Boolean(launchChecklistReadiness?.checkout_canary_passed),
      value: null,
    },
    {
      key: 'configDeliveryCanary',
      label: t('policy.launchReadiness.items.configDeliveryCanary'),
      complete: Boolean(launchChecklistReadiness?.config_delivery_canary_passed),
      value: null,
    },
    {
      key: 'rollbackDrill',
      label: t('policy.launchReadiness.items.rollbackDrill'),
      complete: Boolean(launchChecklistReadiness?.rollback_drill_acknowledged),
      value: null,
    },
    {
      key: 'supportWindow',
      label: t('policy.launchReadiness.items.supportWindow'),
      complete: Boolean(launchChecklistReadiness?.support_window_confirmed),
      value: null,
    },
    {
      key: 'customerComms',
      label: t('policy.launchReadiness.items.customerComms'),
      complete: Boolean(launchChecklistReadiness?.customer_comms_ready),
      value: null,
    },
    {
      key: 'statusPageTemplate',
      label: t('policy.launchReadiness.items.statusPageTemplate'),
      complete: Boolean(launchChecklistReadiness?.status_page_template_ready),
      value: null,
    },
    {
      key: 'incidentChannel',
      label: t('policy.launchSummary.incidentChannel'),
      complete: Boolean(launchChecklistReadiness?.incident_channel),
      value: launchChecklistReadiness?.incident_channel ?? t('policy.launchChecklist.missingValue'),
    },
    {
      key: 'rollbackCommander',
      label: t('policy.launchSummary.rollbackCommander'),
      complete: Boolean(launchChecklistReadiness?.rollback_commander),
      value: launchChecklistReadiness?.rollback_commander ?? t('policy.launchChecklist.missingValue'),
    },
    {
      key: 'primaryOncall',
      label: t('policy.launchSummary.primaryOncall'),
      complete: Boolean(launchChecklistReadiness?.primary_oncall_contact),
      value: launchChecklistReadiness?.primary_oncall_contact ?? t('policy.launchChecklist.missingValue'),
    },
  ];
  const launchChecklistCompletedCount = launchChecklistItems.filter((item) => item.complete).length;
  const isMiniAppLaunchReady = Boolean(miniAppLaunchSummary?.live_switch_allowed);
  const publicCount = settings.filter((setting) => setting.isPublic).length;
  const describedCount = settings.filter((setting) => Boolean(setting.description)).length;
  const familyCount = new Set(settings.map((setting) => settingFamily(setting.key))).size;

  function resetEditor() {
    setEditorMode('create');
    setSelectedSettingId(null);
    setEditorKey('');
    setEditorValue(defaultSettingValue());
    setEditorDescription('');
    setEditorIsPublic(false);
  }

  function loadSettingIntoEditor(setting: (typeof settings)[number]) {
    setEditorMode('update');
    setSelectedSettingId(setting.id);
    setEditorKey(setting.key);
    setEditorValue(JSON.stringify(setting.value, null, 2));
    setEditorDescription(setting.description ?? '');
    setEditorIsPublic(setting.isPublic);
  }

  function submitEditor() {
    if (editorMode === 'create' && !editorKey.trim()) {
      setFeedback(t('common.validation.keyRequired'));
      return;
    }

    if (!editorValue.trim()) {
      setFeedback(t('common.validation.valueRequired'));
      return;
    }

    let parsedValue: unknown;

    try {
      parsedValue = parseJsonInput(editorValue);
    } catch {
      setFeedback(t('common.validation.jsonInvalid'));
      return;
    }

    if (editorMode === 'create') {
      createMutation.mutate({
        key: editorKey.trim(),
        value: parsedValue,
        description: editorDescription.trim() || null,
        is_public: editorIsPublic,
      });
      return;
    }

    if (!selectedSettingId) {
      setFeedback(t('policy.selectionRequired'));
      return;
    }

    updateMutation.mutate({
      id: selectedSettingId,
      value: parsedValue,
      description: editorDescription.trim() || null,
      is_public: editorIsPublic,
    });
  }

  return (
    <GovernancePageShell
      eyebrow={t('policy.eyebrow')}
      title={t('policy.title')}
      description={t('policy.description')}
      icon={Settings2}
      actions={
        <>
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t('policy.searchPlaceholder')}
            className="w-[15rem]"
          />
          <Button
            type="button"
            variant="ghost"
            magnetic={false}
            onClick={() => {
              setMiniAppDraft(null);
              setMiniAppLaunchReadinessDraft(null);
              setMiniAppLaunchActionReason('');
              void queryClient.invalidateQueries({ queryKey: ['governance', 'settings'] });
              void queryClient.invalidateQueries({
                queryKey: ['governance', 'system-config', 'miniapp-runtime'],
              });
              void queryClient.invalidateQueries({
                queryKey: ['governance', 'system-config', 'miniapp-launch-readiness'],
              });
              void queryClient.invalidateQueries({
                queryKey: ['governance', 'system-config', 'miniapp-launch-summary'],
              });
              void queryClient.invalidateQueries({
                queryKey: ['governance', 'system-config', 'miniapp-launch-timeline'],
              });
            }}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            {t('common.refresh')}
          </Button>
        </>
      }
      metrics={[
        {
          label: t('policy.metrics.total'),
          value: String(settings.length),
          hint: t('policy.metrics.totalHint'),
          tone: 'info',
        },
        {
          label: t('policy.metrics.public'),
          value: String(publicCount),
          hint: t('policy.metrics.publicHint'),
          tone: 'warning',
        },
        {
          label: t('policy.metrics.described'),
          value: String(describedCount),
          hint: t('policy.metrics.describedHint'),
          tone: 'success',
        },
        {
          label: t('policy.metrics.families'),
          value: String(familyCount),
          hint: t('policy.metrics.familiesHint'),
          tone: 'neutral',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="space-y-6 xl:col-span-7">
          {feedback ? (
            <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-foreground">
              {feedback}
            </div>
          ) : null}

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('policy.registryTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('policy.registryDescription')}
            </p>

            <div className="mt-5">
              {settingsQuery.isLoading ? (
                <div className="grid gap-3">
                  {Array.from({ length: 5 }).map((_, index) => (
                    <div
                      key={index}
                      className="h-16 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                    />
                  ))}
                </div>
              ) : filteredSettings.length === 0 ? (
                <GovernanceEmptyState label={t('policy.empty')} />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('common.key')}</TableHead>
                      <TableHead>{t('common.value')}</TableHead>
                      <TableHead>{t('common.status')}</TableHead>
                      <TableHead>{t('common.actions')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredSettings.map((setting) => {
                      const isSelected = selectedSetting?.id === setting.id;

                      return (
                        <TableRow
                          key={setting.id}
                          className={isSelected ? 'border-l-2 border-l-neon-cyan bg-neon-cyan/5' : undefined}
                          onClick={() => setSelectedSettingId(setting.id)}
                        >
                          <TableCell>
                            <div className="space-y-1">
                              <p className="font-display uppercase tracking-[0.14em] text-white">
                                {setting.key}
                              </p>
                              <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                                {setting.description ?? t('common.none')}
                              </p>
                            </div>
                          </TableCell>
                          <TableCell className="max-w-[18rem]">
                            <span className="text-xs text-muted-foreground">
                              {summarizeJsonValue(setting.value)}
                            </span>
                          </TableCell>
                          <TableCell>
                            <GovernanceStatusChip
                              label={setting.isPublic ? t('common.public') : t('common.private')}
                              tone={setting.isPublic ? 'warning' : 'info'}
                            />
                          </TableCell>
                          <TableCell>
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              magnetic={false}
                              onClick={(event) => {
                                event.stopPropagation();
                                loadSettingIntoEditor(setting);
                              }}
                            >
                              {t('common.edit')}
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </div>
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
                <ShieldCheck className="h-4 w-4" />
              </div>
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                  {t('policy.roleMatrixTitle')}
                </h2>
                <p className="mt-1 text-sm font-mono text-muted-foreground">
                  {t('policy.roleMatrixDescription')}
                </p>
              </div>
            </div>

            <div className="mt-5 grid gap-3">
              {GOVERNANCE_ROLE_PERMISSION_MATRIX.map((entry) => (
                <div
                  key={entry.role}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                      {entry.role}
                    </p>
                    <GovernanceStatusChip
                      label={String(entry.permissions.length)}
                      tone="info"
                    />
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {entry.permissions.map((permission) => (
                      <GovernanceStatusChip
                        key={`${entry.role}-${permission}`}
                        label={humanizeToken(permission)}
                        tone="neutral"
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </article>
        </section>

        <section className="space-y-6 xl:col-span-5">
          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                  {t('policy.launchSummary.title')}
                </h2>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {t('policy.launchSummary.description')}
                </p>
              </div>
              <GovernanceStatusChip
                label={t(`policy.launchSummary.states.${miniAppLaunchSummary?.launch_state ?? 'blocked'}`)}
                tone={
                  miniAppLaunchSummary?.launch_state === 'live'
                    ? 'success'
                    : miniAppLaunchSummary?.launch_state === 'ready_for_live'
                      ? 'info'
                      : miniAppLaunchSummary?.launch_state === 'canary_in_progress'
                        ? 'info'
                        : miniAppLaunchSummary?.launch_state === 'maintenance'
                          ? 'warning'
                          : 'danger'
                }
              />
            </div>

            <div className="mt-5 space-y-4">
              <div className="flex flex-wrap gap-2">
                <GovernanceStatusChip
                  label={`${t('policy.launchSummary.nextAction')}: ${t(`policy.launchSummary.actions.${miniAppLaunchSummary?.next_action ?? 'stabilize_runtime'}`)}`}
                  tone="neutral"
                />
                <GovernanceStatusChip
                  label={
                    miniAppLaunchSummary?.live_switch_allowed
                      ? t('policy.launchSummary.liveSwitchAllowed')
                      : t('policy.launchSummary.liveSwitchBlocked')
                  }
                  tone={miniAppLaunchSummary?.live_switch_allowed ? 'success' : 'warning'}
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('policy.launchSummary.incidentChannel')}
                  </p>
                  <p className="mt-2 text-sm font-mono text-foreground">
                    {miniAppLaunchSummary?.readiness.incident_channel ?? '—'}
                  </p>
                </div>
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('policy.launchSummary.rollbackCommander')}
                  </p>
                  <p className="mt-2 text-sm font-mono text-foreground">
                    {miniAppLaunchSummary?.readiness.rollback_commander ?? '—'}
                  </p>
                </div>
              </div>

              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('policy.launchSummary.primaryOncall')}
                </p>
                <p className="mt-2 text-sm font-mono text-foreground">
                  {miniAppLaunchSummary?.readiness.primary_oncall_contact ?? '—'}
                </p>
              </div>

              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('policy.launchSummary.blockers')}
                </p>
                {miniAppLaunchSummary?.blockers.length ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {miniAppLaunchSummary.blockers.map((blocker) => (
                      <GovernanceStatusChip
                        key={blocker}
                        label={t(`policy.launchSummary.blockerLabels.${blocker}`)}
                        tone="warning"
                      />
                    ))}
                  </div>
                ) : (
                  <p className="mt-2 text-sm font-mono text-matrix-green">
                    {t('policy.launchSummary.noBlockers')}
                  </p>
                )}
              </div>
            </div>
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                  {t('policy.launchActions.title')}
                </h2>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {t('policy.launchActions.description')}
                </p>
              </div>
              <GovernanceStatusChip
                label={
                  miniAppLaunchSummary?.primary_action
                    ? t(`policy.launchActions.items.${miniAppLaunchSummary.primary_action}`)
                    : t('policy.launchSummary.actions.stabilize_runtime')
                }
                tone={miniAppLaunchSummary?.primary_action ? 'info' : 'neutral'}
              />
            </div>

            <div className="mt-5 space-y-4">
              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('policy.launchActions.reason')}
                </span>
                <Input
                  value={miniAppLaunchActionReason}
                  onChange={(event) => setMiniAppLaunchActionReason(event.target.value)}
                  placeholder={t('policy.launchActions.reasonPlaceholder')}
                />
              </label>

              <div className="grid gap-3 sm:grid-cols-2">
                {orderedMiniAppLaunchActions.length ? orderedMiniAppLaunchActions.map((action) => {
                  const isPrimary = miniAppLaunchSummary?.primary_action === action;
                  return (
                    <Button
                      key={action}
                      type="button"
                      variant={isPrimary ? 'default' : 'outline'}
                      magnetic={false}
                      disabled={
                        miniAppLaunchActionMutation.isPending
                        || !availableMiniAppLaunchActions.includes(action)
                      }
                      onClick={() => miniAppLaunchActionMutation.mutate(action)}
                    >
                      {t(`policy.launchActions.items.${action}`)}
                    </Button>
                  );
                }) : (
                  <p className="text-sm font-mono text-muted-foreground">
                    {t('policy.launchActions.noActions')}
                  </p>
                )}
              </div>

              <p className="text-xs font-mono text-muted-foreground">
                {t('policy.launchActions.currentStateHint', {
                  state: t(`policy.launchSummary.states.${miniAppLaunchSummary?.launch_state ?? 'blocked'}`),
                })}
              </p>
            </div>
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                  {t('policy.launchChecklist.title')}
                </h2>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {t('policy.launchChecklist.description')}
                </p>
              </div>
              <GovernanceStatusChip
                label={`${launchChecklistCompletedCount}/${launchChecklistItems.length}`}
                tone={miniAppLaunchSummary?.readiness.is_ready ? 'success' : 'warning'}
              />
            </div>

            <div className="mt-5 space-y-4">
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('policy.launchChecklist.releaseWindow')}
                </p>
                <p className="mt-2 text-sm font-mono text-foreground">
                  {launchChecklistReadiness?.release_window_note ?? t('policy.launchChecklist.missingValue')}
                </p>
              </div>

              <div className="grid gap-3">
                {launchChecklistItems.map((item) => (
                  <div
                    key={item.key}
                    className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="space-y-2">
                        <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                          {item.label}
                        </p>
                        {item.value ? (
                          <p className="text-sm font-mono leading-6 text-muted-foreground">
                            {item.value}
                          </p>
                        ) : null}
                      </div>
                      <GovernanceStatusChip
                        label={item.complete
                          ? t('policy.launchReadiness.status.ready')
                          : t('policy.launchReadiness.status.blocked')}
                        tone={item.complete ? 'success' : 'warning'}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                  {t('policy.launchTimeline.title')}
                </h2>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {t('policy.launchTimeline.description')}
                </p>
              </div>
              <GovernanceStatusChip
                label={String(miniAppLaunchTimeline.length)}
                tone="neutral"
              />
            </div>

            <div className="mt-5 space-y-3">
              {miniAppLaunchTimelineQuery.isLoading ? (
                Array.from({ length: 3 }).map((_, index) => (
                  <div
                    key={index}
                    className="h-20 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                  />
                ))
              ) : miniAppLaunchTimeline.length ? (
                miniAppLaunchTimeline.map((entry) => (
                  <div
                    key={entry.id}
                    className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                          {entry.action_name
                            ? t(`policy.launchActions.items.${entry.action_name}`)
                            : t(`policy.launchTimeline.eventTypes.${entry.event_type}`)}
                        </p>
                        <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          {formatDateTime(entry.created_at)} / {entry.admin_id ? shortId(entry.admin_id) : t('common.system')}
                        </p>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        <GovernanceStatusChip
                          label={t(`policy.launchTimeline.eventTypes.${entry.event_type}`)}
                          tone="info"
                        />
                        {entry.resulting_launch_state ? (
                          <GovernanceStatusChip
                            label={t(`policy.launchSummary.states.${entry.resulting_launch_state}`)}
                            tone={entry.resulting_launch_state === 'live' ? 'success' : 'warning'}
                          />
                        ) : null}
                        {entry.resulting_runtime_mode ? (
                          <GovernanceStatusChip
                            label={t(`policy.runtimeControl.status.${entry.resulting_runtime_mode}`)}
                            tone={entry.resulting_runtime_mode === 'live' ? 'success' : 'neutral'}
                          />
                        ) : null}
                        {typeof entry.readiness_ready === 'boolean' ? (
                          <GovernanceStatusChip
                            label={entry.readiness_ready
                              ? t('policy.launchReadiness.status.ready')
                              : t('policy.launchReadiness.status.blocked')}
                            tone={entry.readiness_ready ? 'success' : 'warning'}
                          />
                        ) : null}
                      </div>
                    </div>

                    <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                      {entry.change_reason || t('policy.launchTimeline.noReason')}
                    </p>
                  </div>
                ))
              ) : (
                <GovernanceEmptyState label={t('policy.launchTimeline.empty')} />
              )}
            </div>
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                  {t('policy.runtimeControl.title')}
                </h2>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {t('policy.runtimeControl.description')}
                </p>
              </div>
              <GovernanceStatusChip
                label={
                  t(`policy.runtimeControl.status.${effectiveRuntimeStatus}`)
                }
                tone={
                  effectiveRuntimeStatus === 'live'
                    ? 'success'
                    : effectiveRuntimeStatus === 'canary'
                      ? 'info'
                      : effectiveRuntimeStatus === 'maintenance'
                    ? 'warning'
                    : 'danger'
                }
              />
              {!isMiniAppLaunchReady && effectiveMiniAppRuntime.enabled && effectiveMiniAppRuntime.mode === 'live' ? (
                <GovernanceStatusChip
                  label={t('policy.runtimeControl.liveGateBlocked')}
                  tone="warning"
                />
              ) : null}
            </div>

            <div className="mt-5 space-y-4">
              <label className="flex items-center gap-3 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3">
                <input
                  type="checkbox"
                  checked={effectiveMiniAppRuntime.enabled}
                  onChange={(event) =>
                    setMiniAppDraft({
                      ...effectiveMiniAppRuntime,
                      enabled: event.target.checked,
                    })}
                  className="h-4 w-4 rounded border border-input bg-transparent"
                />
                <span className="text-sm font-mono text-foreground">
                  {t('policy.runtimeControl.enabled')}
                </span>
              </label>

              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('policy.runtimeControl.mode')}
                </span>
                <select
                  value={effectiveMiniAppRuntime.mode}
                  onChange={(event) =>
                    setMiniAppDraft({
                      ...effectiveMiniAppRuntime,
                      mode: event.target.value as MiniAppRuntimeDraft['mode'],
                    })}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                >
                  <option value="live">{t('policy.runtimeControl.status.live')}</option>
                  <option value="canary">{t('policy.runtimeControl.status.canary')}</option>
                  <option value="maintenance">{t('policy.runtimeControl.status.maintenance')}</option>
                  <option value="rollback">{t('policy.runtimeControl.status.rollback')}</option>
                </select>
              </label>

              <div className="grid gap-3 sm:grid-cols-3">
                <label className="flex items-center gap-3 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={effectiveMiniAppRuntime.trialEnabled}
                    onChange={(event) =>
                      setMiniAppDraft({
                        ...effectiveMiniAppRuntime,
                        trialEnabled: event.target.checked,
                      })}
                    className="h-4 w-4 rounded border border-input bg-transparent"
                  />
                  <span className="text-sm font-mono text-foreground">
                    {t('policy.runtimeControl.trial')}
                  </span>
                </label>
                <label className="flex items-center gap-3 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={effectiveMiniAppRuntime.checkoutEnabled}
                    onChange={(event) =>
                      setMiniAppDraft({
                        ...effectiveMiniAppRuntime,
                        checkoutEnabled: event.target.checked,
                      })}
                    className="h-4 w-4 rounded border border-input bg-transparent"
                  />
                  <span className="text-sm font-mono text-foreground">
                    {t('policy.runtimeControl.checkout')}
                  </span>
                </label>
                <label className="flex items-center gap-3 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={effectiveMiniAppRuntime.configEnabled}
                    onChange={(event) =>
                      setMiniAppDraft({
                        ...effectiveMiniAppRuntime,
                        configEnabled: event.target.checked,
                      })}
                    className="h-4 w-4 rounded border border-input bg-transparent"
                  />
                  <span className="text-sm font-mono text-foreground">
                    {t('policy.runtimeControl.config')}
                  </span>
                </label>
              </div>

              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('policy.runtimeControl.maintenanceMessage')}
                </span>
                <Input
                  value={effectiveMiniAppRuntime.maintenanceMessage}
                  onChange={(event) =>
                    setMiniAppDraft({
                      ...effectiveMiniAppRuntime,
                      maintenanceMessage: event.target.value,
                    })}
                  placeholder={t('policy.runtimeControl.maintenancePlaceholder')}
                />
              </label>

              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('policy.runtimeControl.canaryAllowlist')}
                </span>
                <textarea
                  value={effectiveMiniAppRuntime.canaryTelegramUserIds}
                  onChange={(event) =>
                    setMiniAppDraft({
                      ...effectiveMiniAppRuntime,
                      canaryTelegramUserIds: event.target.value,
                    })}
                  placeholder={t('policy.runtimeControl.canaryAllowlistPlaceholder')}
                  rows={3}
                  className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                />
                <p className="text-xs font-mono text-muted-foreground">
                  {t('policy.runtimeControl.canaryAllowlistHint')}
                </p>
              </label>

              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('policy.runtimeControl.changeReason')}
                </span>
                <Input
                  value={miniAppChangeReason}
                  onChange={(event) => setMiniAppChangeReason(event.target.value)}
                  placeholder={t('policy.runtimeControl.changeReasonPlaceholder')}
                />
              </label>

              <div className="grid gap-3 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <GovernanceStatusChip
                    label={miniAppRuntime?.key ?? 'miniapp.runtime'}
                    tone="info"
                  />
                  {miniAppRuntime?.updated_by ? (
                    <GovernanceStatusChip
                      label={`${t('policy.runtimeControl.updatedBy')}: ${shortId(miniAppRuntime.updated_by)}`}
                      tone="neutral"
                    />
                  ) : null}
                </div>
                <p className="text-xs font-mono leading-6 text-muted-foreground">
                  {t('policy.runtimeControl.lastUpdated')}: {formatDateTime(miniAppRuntime?.updated_at)}
                </p>
              </div>

              <Button
                type="button"
                magnetic={false}
                disabled={
                  miniAppRuntimeQuery.isLoading
                  || miniAppRuntimeMutation.isPending
                  || (
                    effectiveMiniAppRuntime.enabled
                    && effectiveMiniAppRuntime.mode === 'live'
                    && !isMiniAppLaunchReady
                  )
                }
                onClick={() => {
                  try {
                    const canaryTelegramUserIds = parseCanaryTelegramUserIds(
                      effectiveMiniAppRuntime.canaryTelegramUserIds,
                    );
                    if (effectiveMiniAppRuntime.mode === 'canary' && canaryTelegramUserIds.length === 0) {
                      setFeedback(t('policy.runtimeControl.canaryAllowlistRequired'));
                      return;
                    }
                    miniAppRuntimeMutation.mutate(canaryTelegramUserIds);
                  } catch {
                    setFeedback(t('policy.runtimeControl.canaryAllowlistInvalid'));
                  }
                }}
              >
                {t('policy.runtimeControl.apply')}
              </Button>
              {!isMiniAppLaunchReady && effectiveMiniAppRuntime.enabled && effectiveMiniAppRuntime.mode === 'live' ? (
                <p className="text-xs font-mono text-amber-300">
                  {t('policy.runtimeControl.liveGateHint')}
                </p>
              ) : null}
            </div>
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                  {t('policy.launchReadiness.title')}
                </h2>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {t('policy.launchReadiness.description')}
                </p>
              </div>
              <GovernanceStatusChip
                label={
                  effectiveMiniAppLaunchReadiness.observabilityAcknowledged
                  && effectiveMiniAppLaunchReadiness.incidentRunbookAcknowledged
                  && effectiveMiniAppLaunchReadiness.checkoutCanaryPassed
                  && effectiveMiniAppLaunchReadiness.configDeliveryCanaryPassed
                  && effectiveMiniAppLaunchReadiness.rollbackDrillAcknowledged
                  && effectiveMiniAppLaunchReadiness.supportWindowConfirmed
                    ? t('policy.launchReadiness.status.ready')
                    : t('policy.launchReadiness.status.blocked')
                }
                tone={
                  effectiveMiniAppLaunchReadiness.observabilityAcknowledged
                  && effectiveMiniAppLaunchReadiness.incidentRunbookAcknowledged
                  && effectiveMiniAppLaunchReadiness.checkoutCanaryPassed
                  && effectiveMiniAppLaunchReadiness.configDeliveryCanaryPassed
                  && effectiveMiniAppLaunchReadiness.rollbackDrillAcknowledged
                  && effectiveMiniAppLaunchReadiness.supportWindowConfirmed
                    ? 'success'
                    : 'warning'
                }
              />
            </div>

            <div className="mt-5 space-y-4">
              <div className="grid gap-3 sm:grid-cols-2">
                {[
                  ['observabilityAcknowledged', 'observability'],
                  ['incidentRunbookAcknowledged', 'incidentRunbook'],
                  ['checkoutCanaryPassed', 'checkoutCanary'],
                  ['configDeliveryCanaryPassed', 'configDeliveryCanary'],
                  ['rollbackDrillAcknowledged', 'rollbackDrill'],
                  ['supportWindowConfirmed', 'supportWindow'],
                  ['customerCommsReady', 'customerComms'],
                  ['statusPageTemplateReady', 'statusPageTemplate'],
                ].map(([field, labelKey]) => (
                  <label
                    key={field}
                    className="flex items-center gap-3 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3"
                  >
                    <input
                      type="checkbox"
                      checked={effectiveMiniAppLaunchReadiness[field as keyof MiniAppLaunchReadinessDraft] as boolean}
                      onChange={(event) =>
                        setMiniAppLaunchReadinessDraft({
                          ...effectiveMiniAppLaunchReadiness,
                          [field]: event.target.checked,
                        })}
                      className="h-4 w-4 rounded border border-input bg-transparent"
                    />
                    <span className="text-sm font-mono text-foreground">
                      {t(`policy.launchReadiness.items.${labelKey}`)}
                    </span>
                  </label>
                ))}
              </div>

              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('policy.launchReadiness.incidentChannel')}
                </span>
                <Input
                  value={effectiveMiniAppLaunchReadiness.incidentChannel}
                  onChange={(event) =>
                    setMiniAppLaunchReadinessDraft({
                      ...effectiveMiniAppLaunchReadiness,
                      incidentChannel: event.target.value,
                    })}
                  placeholder={t('policy.launchReadiness.incidentChannelPlaceholder')}
                />
              </label>

              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('policy.launchReadiness.rollbackCommander')}
                  </span>
                  <Input
                    value={effectiveMiniAppLaunchReadiness.rollbackCommander}
                    onChange={(event) =>
                      setMiniAppLaunchReadinessDraft({
                        ...effectiveMiniAppLaunchReadiness,
                        rollbackCommander: event.target.value,
                      })}
                    placeholder={t('policy.launchReadiness.rollbackCommanderPlaceholder')}
                  />
                </label>
                <label className="block space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('policy.launchReadiness.primaryOncall')}
                  </span>
                  <Input
                    value={effectiveMiniAppLaunchReadiness.primaryOncallContact}
                    onChange={(event) =>
                      setMiniAppLaunchReadinessDraft({
                        ...effectiveMiniAppLaunchReadiness,
                        primaryOncallContact: event.target.value,
                      })}
                    placeholder={t('policy.launchReadiness.primaryOncallPlaceholder')}
                  />
                </label>
              </div>

              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('policy.launchReadiness.releaseWindowNote')}
                </span>
                <Input
                  value={effectiveMiniAppLaunchReadiness.releaseWindowNote}
                  onChange={(event) =>
                    setMiniAppLaunchReadinessDraft({
                      ...effectiveMiniAppLaunchReadiness,
                      releaseWindowNote: event.target.value,
                    })}
                  placeholder={t('policy.launchReadiness.releaseWindowNotePlaceholder')}
                />
              </label>

              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('policy.launchReadiness.changeReason')}
                </span>
                <Input
                  value={miniAppLaunchReadinessChangeReason}
                  onChange={(event) => setMiniAppLaunchReadinessChangeReason(event.target.value)}
                  placeholder={t('policy.launchReadiness.changeReasonPlaceholder')}
                />
              </label>

              <div className="grid gap-3 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <GovernanceStatusChip
                    label={miniAppLaunchReadiness?.key ?? 'miniapp.launch_readiness'}
                    tone="info"
                  />
                  {miniAppLaunchReadiness?.updated_by ? (
                    <GovernanceStatusChip
                      label={`${t('policy.launchReadiness.updatedBy')}: ${shortId(miniAppLaunchReadiness.updated_by)}`}
                      tone="neutral"
                    />
                  ) : null}
                </div>
                <p className="text-xs font-mono leading-6 text-muted-foreground">
                  {t('policy.launchReadiness.lastUpdated')}: {formatDateTime(miniAppLaunchReadiness?.updated_at)}
                </p>
              </div>

              <Button
                type="button"
                magnetic={false}
                disabled={miniAppLaunchReadinessQuery.isLoading || miniAppLaunchReadinessMutation.isPending}
                onClick={() => miniAppLaunchReadinessMutation.mutate()}
              >
                {t('policy.launchReadiness.apply')}
              </Button>
            </div>
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                  {t('policy.editorTitle')}
                </h2>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {t(`policy.editorDescription.${editorMode}`)}
                </p>
              </div>
              {editorMode === 'update' ? (
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  magnetic={false}
                  onClick={() => resetEditor()}
                >
                  {t('policy.resetEditor')}
                </Button>
              ) : null}
            </div>

            <div className="mt-5 space-y-4">
              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.key')}
                </span>
                <Input
                  value={editorKey}
                  disabled={editorMode === 'update'}
                  onChange={(event) => setEditorKey(event.target.value)}
                  placeholder={t('policy.keyPlaceholder')}
                />
              </label>

              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.description')}
                </span>
                <Input
                  value={editorDescription}
                  onChange={(event) => setEditorDescription(event.target.value)}
                  placeholder={t('policy.descriptionPlaceholder')}
                />
              </label>

              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.value')}
                </span>
                <textarea
                  value={editorValue}
                  onChange={(event) => setEditorValue(event.target.value)}
                  placeholder={t('policy.valuePlaceholder')}
                  className="min-h-48 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground outline-none"
                />
              </label>

              <label className="flex items-center gap-3 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3">
                <input
                  type="checkbox"
                  checked={editorIsPublic}
                  onChange={(event) => setEditorIsPublic(event.target.checked)}
                  className="h-4 w-4 rounded border border-input bg-transparent"
                />
                <span className="text-sm font-mono text-foreground">
                  {t('policy.publicToggle')}
                </span>
              </label>

              <Button
                type="button"
                magnetic={false}
                disabled={createMutation.isPending || updateMutation.isPending}
                onClick={() => submitEditor()}
              >
                {editorMode === 'create' ? t('common.create') : t('common.update')}
              </Button>
            </div>
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('policy.detailTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('policy.detailDescription')}
            </p>

            {selectedSetting ? (
              <div className="mt-5 space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <GovernanceStatusChip
                    label={selectedSetting.isPublic ? t('common.public') : t('common.private')}
                    tone={selectedSetting.isPublic ? 'warning' : 'info'}
                  />
                  <GovernanceStatusChip
                    label={settingFamily(selectedSetting.key)}
                    tone="neutral"
                  />
                </div>
                <GovernanceJsonPreview value={selectedSetting.value} maxHeightClassName="max-h-[20rem]" />
              </div>
            ) : (
              <div className="mt-5">
                <GovernanceEmptyState label={t('policy.empty')} />
              </div>
            )}
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('policy.gapTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('policy.gapDescription')}
            </p>
          </article>
        </section>
      </div>
    </GovernancePageShell>
  );
}
