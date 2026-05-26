'use client';

import { useState } from 'react';
import { ArrowUpRight, KeyRound, Waypoints } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocale, useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { partnerPortalApi } from '@/lib/api/partner-portal';
import { publicNetworkApi } from '@/lib/api/public-network';
import { PartnerRouteGuard } from '@/features/partner-portal-state/components/partner-route-guard';
import { usePartnerPortalRuntimeState } from '@/features/partner-portal-state/lib/use-partner-portal-runtime-state';
import {
  getPartnerIntegrationsCapabilities,
  getPartnerIntegrationsSurfaceMode,
} from '@/features/partner-operations/lib/advanced-operational-capabilities';
import { buildPartnerBotProvisioningReadiness } from '@/features/partner-integrations/lib/partner-bot-readiness';
import { DocsCodeBlock } from '@/widgets/docs-code-block';

const READINESS_BADGE_STYLES = {
  blocked: 'text-neon-pink',
  conditional: 'text-neon-cyan',
  enabled: 'text-matrix-green',
} as const;

function formatDateTime(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function formatCompactNumber(value: number, locale: string): string {
  return new Intl.NumberFormat(locale, {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value);
}

function formatTraffic(bytes: number, locale: string): string {
  if (bytes <= 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }

  return `${new Intl.NumberFormat(locale, {
    maximumFractionDigits: size >= 100 ? 0 : size >= 10 ? 1 : 2,
  }).format(size)} ${units[unitIndex]}`;
}

function resolveCybervpnPublicSiteUrl(): string {
  const configured = process.env.NEXT_PUBLIC_CYBERVPN_PUBLIC_SITE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, '');
  }

  if (process.env.NODE_ENV === 'development') {
    return 'http://localhost:3000';
  }

  return 'https://vpn.ozoxy.ru';
}

function shouldRenderLiveWidgetPreview(): boolean {
  return process.env.NODE_ENV !== 'test';
}

type CreateBotDraft = {
  bot_key: string;
  display_name: string;
  default_locale: string;
  short_description: string;
  provisioning_path: 'managed_bot' | 'manual_token';
};

type BotActionDraft = {
  action_reference: string;
  suspend_reason: string;
};

const INITIAL_CREATE_BOT_DRAFT: CreateBotDraft = {
  bot_key: '',
  display_name: '',
  default_locale: 'en-EN',
  short_description: '',
  provisioning_path: 'managed_bot',
};

function getBotActionDraft(
  drafts: Record<string, BotActionDraft>,
  botId: string,
): BotActionDraft {
  return drafts[botId] ?? {
    action_reference: '',
    suspend_reason: '',
  };
}

export function IntegrationsConsolePage() {
  const locale = useLocale();
  const t = useTranslations('Partner.integrations');
  const portalT = useTranslations('Partner.portalState');
  const queryClient = useQueryClient();
  const { state } = usePartnerPortalRuntimeState();
  const mode = getPartnerIntegrationsSurfaceMode(state);
  const capabilities = getPartnerIntegrationsCapabilities(state);
  const [createBotDraft, setCreateBotDraft] = useState<CreateBotDraft>(INITIAL_CREATE_BOT_DRAFT);
  const [botActionDrafts, setBotActionDrafts] = useState<Record<string, BotActionDraft>>({});
  const [botFeedback, setBotFeedback] = useState<{
    tone: 'success' | 'error';
    message: string;
  } | null>(null);
  const partnerBotsQueryKey = ['partner-portal', 'partner-bots', state.activeWorkspaceId ?? null];

  async function refreshPartnerBots() {
    await queryClient.invalidateQueries({ queryKey: partnerBotsQueryKey });
  }

  function updateBotActionDraft(botId: string, patch: Partial<BotActionDraft>) {
    setBotActionDrafts((current) => ({
      ...current,
      [botId]: {
        ...getBotActionDraft(current, botId),
        ...patch,
      },
    }));
  }

  const partnerBotsQuery = useQuery({
    queryKey: partnerBotsQueryKey,
    queryFn: async () => {
      if (!state.activeWorkspaceId) {
        return null;
      }
      const response = await partnerPortalApi.listPartnerBots({
        partner_account_id: state.activeWorkspaceId,
        limit: 20,
        offset: 0,
      });
      return response.data;
    },
    enabled: Boolean(state.activeWorkspaceId),
    staleTime: 30_000,
    retry: false,
  });
  const partnerBots = partnerBotsQuery.data ?? [];
  const postbackReadinessQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-postback-readiness', state.activeWorkspaceId ?? null],
    queryFn: async () => {
      if (!state.activeWorkspaceId) {
        return null;
      }
      const response = await partnerPortalApi.getWorkspacePostbackReadiness(state.activeWorkspaceId);
      return response.data;
    },
    enabled: Boolean(state.activeWorkspaceId),
    staleTime: 30_000,
    retry: false,
  });
  const provisioningReadiness = buildPartnerBotProvisioningReadiness({
    bots: partnerBots,
    technicalReadiness: state.technicalReadiness,
    postbackReadiness: postbackReadinessQuery.data ?? null,
  });
  const widgetPreviewQuery = useQuery({
    queryKey: ['partner-portal', 'public-network-widget', locale],
    queryFn: async () => {
      const response = await publicNetworkApi.getWidget({
        locale,
        themeVariant: 'cyber',
        widgetType: 'network_card',
      });
      return response.data;
    },
    staleTime: 30_000,
    retry: false,
  });
  const publicWidgetBaseUrl = resolveCybervpnPublicSiteUrl();
  const widgetPreviewUrl = new URL(`/${locale}/widgets/network`, publicWidgetBaseUrl);
  widgetPreviewUrl.searchParams.set('widgetType', 'network_card');
  widgetPreviewUrl.searchParams.set('themeVariant', 'cyber');
  const iframeSnippet = `<iframe\n  src=\"${widgetPreviewUrl.toString()}\"\n  width=\"100%\"\n  height=\"${widgetPreviewQuery.data?.recommendedHeight ?? 420}\"\n  loading=\"lazy\"\n  style=\"border:0;border-radius:24px;overflow:hidden\"\n></iframe>`;

  const createPartnerBotMutation = useMutation({
    mutationFn: async (draft: CreateBotDraft) => {
      if (!state.activeWorkspaceId) {
        throw new Error(t('bots.workspaceRequired'));
      }
      return partnerPortalApi.createPartnerBot({
        partner_account_id: state.activeWorkspaceId,
        bot_key: draft.bot_key.trim(),
        display_name: draft.display_name.trim(),
        default_locale: draft.default_locale.trim() || 'en-EN',
        short_description: draft.short_description.trim() || null,
        provisioning_path: draft.provisioning_path,
      });
    },
    onSuccess: async () => {
      setBotFeedback({
        tone: 'success',
        message: t('bots.createSuccess'),
      });
      setCreateBotDraft(INITIAL_CREATE_BOT_DRAFT);
      await refreshPartnerBots();
    },
    onError: () => {
      setBotFeedback({
        tone: 'error',
        message: t('bots.createError'),
      });
    },
  });

  const provisionPartnerBotMutation = useMutation({
    mutationFn: async ({
      botId,
      provisioningPath,
      actionReference,
    }: {
      botId: string;
      provisioningPath: string;
      actionReference: string;
    }) =>
      partnerPortalApi.requestPartnerBotProvisioning(botId, {
        provisioning_path: provisioningPath as 'managed_bot' | 'manual_token',
        request_payload:
          actionReference.trim().length > 0
            ? provisioningPath === 'manual_token'
              ? { handoff_reference: actionReference.trim() }
              : { operator_note: actionReference.trim() }
            : {},
      }),
    onSuccess: async () => {
      setBotFeedback({
        tone: 'success',
        message: t('bots.provisionSuccess'),
      });
      await refreshPartnerBots();
    },
    onError: () => {
      setBotFeedback({
        tone: 'error',
        message: t('bots.provisionError'),
      });
    },
  });

  const rotateTokenMutation = useMutation({
    mutationFn: async ({
      botId,
      provisioningPath,
      actionReference,
    }: {
      botId: string;
      provisioningPath: string;
      actionReference: string;
    }) =>
      partnerPortalApi.rotatePartnerBotToken(botId, {
        request_payload:
          actionReference.trim().length > 0
            ? provisioningPath === 'manual_token'
              ? { handoff_reference: actionReference.trim() }
              : { operator_note: actionReference.trim() }
            : {},
      }),
    onSuccess: async () => {
      setBotFeedback({
        tone: 'success',
        message: t('bots.rotateSuccess'),
      });
      await refreshPartnerBots();
    },
    onError: () => {
      setBotFeedback({
        tone: 'error',
        message: t('bots.rotateError'),
      });
    },
  });

  const suspendPartnerBotMutation = useMutation({
    mutationFn: async ({ botId, reasonCode }: { botId: string; reasonCode: string }) =>
      partnerPortalApi.suspendPartnerBot(botId, {
        reason_code: reasonCode.trim() || null,
      }),
    onSuccess: async () => {
      setBotFeedback({
        tone: 'success',
        message: t('bots.suspendSuccess'),
      });
      await refreshPartnerBots();
    },
    onError: () => {
      setBotFeedback({
        tone: 'error',
        message: t('bots.suspendError'),
      });
    },
  });

  const restorePartnerBotMutation = useMutation({
    mutationFn: async (botId: string) => partnerPortalApi.restorePartnerBot(botId),
    onSuccess: async () => {
      setBotFeedback({
        tone: 'success',
        message: t('bots.restoreSuccess'),
      });
      await refreshPartnerBots();
    },
    onError: () => {
      setBotFeedback({
        tone: 'error',
        message: t('bots.restoreError'),
      });
    },
  });

  return (
    <PartnerRouteGuard route="integrations" title={t('title')}>
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
                  <span>{t('summary.routeAccess')}</span>
                  <span className="text-neon-cyan">
                    {portalT(`routeAccess.${access}`)}
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <span>{t('summary.technicalReadiness')}</span>
                  <span className="text-foreground">
                    {portalT(`technicalStates.${state.technicalReadiness}`)}
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <span>{t('summary.surfaceMode')}</span>
                  <span className="text-foreground">
                    {portalT(`integrationsModes.${mode}`)}
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <span>{t('summary.credentials')}</span>
                  <span className="text-foreground">{state.integrationCredentials.length}</span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <span>{t('summary.bots')}</span>
                  <span className="text-foreground">{partnerBots.length}</span>
                </div>
              </div>
            </div>
          </header>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
            <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
              <div className="flex items-center gap-3 border-b border-grid-line/20 pb-4">
                <KeyRound className="h-5 w-5 text-neon-cyan" />
                <div>
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('credentials.title')}
                  </h2>
                  <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                    {t('credentials.description')}
                  </p>
                </div>
              </div>

              <div className="mt-5 space-y-3">
                {state.integrationCredentials.map((credential) => (
                  <article
                    key={credential.id}
                    className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4"
                  >
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                          {credential.label}
                        </h3>
                        <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                          {portalT(`integrationCredentialKinds.${credential.kind}`)}
                        </p>
                        <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                          {credential.notes[0]}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                          {portalT(`integrationCredentialStatuses.${credential.status}`)}
                        </p>
                        <p className="mt-2 text-xs font-mono text-muted-foreground">
                          {credential.lastRotatedAt
                            ? t('credentials.rotatedAt', { value: formatDateTime(credential.lastRotatedAt, locale) })
                            : t('credentials.notRotated')}
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
                  <Waypoints className="h-5 w-5 text-neon-cyan" />
                  <div>
                    <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                      {t('readiness.title')}
                    </h2>
                    <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                      {t('readiness.description')}
                    </p>
                  </div>
                </div>

                {postbackReadinessQuery.isPending ? (
                  <div className="mt-4 rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4 text-sm font-mono leading-6 text-muted-foreground">
                    {t('readiness.loading')}
                  </div>
                ) : null}
                {postbackReadinessQuery.isError ? (
                  <div className="mt-4 rounded-xl border border-neon-pink/20 bg-neon-pink/5 p-4 text-sm font-mono leading-6 text-neon-pink">
                    {t('readiness.error')}
                  </div>
                ) : null}

                <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3">
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                      {t('readiness.cards.managedPath')}
                    </p>
                    <p className={`mt-2 text-sm font-display uppercase tracking-[0.16em] ${READINESS_BADGE_STYLES[provisioningReadiness.managedPathAvailability]}`}>
                      {portalT(`operationalCapabilityAvailability.${provisioningReadiness.managedPathAvailability}`)}
                    </p>
                    <p className="mt-2 text-xs font-mono text-muted-foreground">
                      {t('readiness.cards.managedPathCount', {
                        value: String(provisioningReadiness.managedPathBots),
                      })}
                    </p>
                  </div>
                  <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3">
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                      {t('readiness.cards.manualFallback')}
                    </p>
                    <p className={`mt-2 text-sm font-display uppercase tracking-[0.16em] ${READINESS_BADGE_STYLES[provisioningReadiness.manualFallbackAvailability]}`}>
                      {portalT(`operationalCapabilityAvailability.${provisioningReadiness.manualFallbackAvailability}`)}
                    </p>
                    <p className="mt-2 text-xs font-mono text-muted-foreground">
                      {t('readiness.cards.manualFallbackCount', {
                        value: String(provisioningReadiness.manualPathBots),
                      })}
                    </p>
                  </div>
                  <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3">
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                      {t('readiness.cards.postback')}
                    </p>
                    <p className={`mt-2 text-sm font-display uppercase tracking-[0.16em] ${READINESS_BADGE_STYLES[provisioningReadiness.postbackAvailability]}`}>
                      {postbackReadinessQuery.data?.status ?? t('readiness.cards.notAvailable')}
                    </p>
                    <p className="mt-2 text-xs font-mono text-muted-foreground">
                      {t('readiness.cards.deliveryStatus', {
                        value: postbackReadinessQuery.data?.delivery_status ?? '—',
                      })}
                    </p>
                  </div>
                  <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3">
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                      {t('readiness.cards.intervention')}
                    </p>
                    <p className="mt-2 text-sm font-display uppercase tracking-[0.16em] text-white">
                      {formatCompactNumber(provisioningReadiness.interventionBots, locale)}
                    </p>
                    <p className="mt-2 text-xs font-mono text-muted-foreground">
                      {t('readiness.cards.pendingCount', {
                        value: String(provisioningReadiness.pendingBots),
                      })}
                    </p>
                  </div>
                </div>

                <dl className="mt-4 grid gap-3 text-sm font-mono text-muted-foreground md:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3">
                    <dt>{t('readiness.snapshot.activeBots')}</dt>
                    <dd className="mt-2 text-foreground">
                      {formatCompactNumber(provisioningReadiness.activeBots, locale)}
                    </dd>
                  </div>
                  <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3">
                    <dt>{t('readiness.snapshot.readyManagedBindings')}</dt>
                    <dd className="mt-2 text-foreground">
                      {formatCompactNumber(provisioningReadiness.readyManagedBindings, locale)}
                    </dd>
                  </div>
                  <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3">
                    <dt>{t('readiness.snapshot.suspendedBots')}</dt>
                    <dd className="mt-2 text-foreground">
                      {formatCompactNumber(provisioningReadiness.suspendedBots, locale)}
                    </dd>
                  </div>
                  <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3">
                    <dt>{t('readiness.snapshot.scope')}</dt>
                    <dd className="mt-2 text-foreground">
                      {postbackReadinessQuery.data?.scope_label ?? '—'}
                    </dd>
                  </div>
                </dl>

                <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,0.95fr)]">
                  <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4">
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                      {t('readiness.notesTitle')}
                    </p>
                    <ul className="mt-3 space-y-2 text-sm font-mono leading-6 text-muted-foreground">
                      {provisioningReadiness.notes.length > 0 ? provisioningReadiness.notes.map((note) => (
                        <li key={note}>{t(`readiness.notes.${note}`)}</li>
                      )) : (
                        <li>{t('readiness.noNotes')}</li>
                      )}
                    </ul>
                  </div>

                  <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4">
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                      {t('readiness.postbackTitle')}
                    </p>
                    <dl className="mt-3 space-y-3 text-sm font-mono text-muted-foreground">
                      <div>
                        <dt>{t('readiness.postbackStatus')}</dt>
                        <dd className="mt-1 text-foreground">
                          {postbackReadinessQuery.data?.status ?? '—'}
                        </dd>
                      </div>
                      <div>
                        <dt>{t('readiness.postbackCredential')}</dt>
                        <dd className="mt-1 text-foreground">
                          {postbackReadinessQuery.data?.credential_status ?? '—'}
                        </dd>
                      </div>
                      <div>
                        <dt>{t('readiness.postbackDelivery')}</dt>
                        <dd className="mt-1 text-foreground">
                          {postbackReadinessQuery.data?.delivery_status ?? '—'}
                        </dd>
                      </div>
                    </dl>
                    {postbackReadinessQuery.data?.notes?.length ? (
                      <ul className="mt-4 space-y-2 text-sm font-mono text-muted-foreground">
                        {postbackReadinessQuery.data.notes.map((note) => (
                          <li key={note}>{note}</li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                </div>
              </article>

              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                <div className="flex items-center gap-3">
                  <KeyRound className="h-5 w-5 text-matrix-green" />
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('bots.title')}
                  </h2>
                </div>
                <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                  {t('bots.description')}
                </p>
                {botFeedback ? (
                  <div
                    className={[
                      'mt-4 rounded-xl border px-4 py-3 text-sm font-mono leading-6',
                      botFeedback.tone === 'success'
                        ? 'border-matrix-green/30 bg-matrix-green/10 text-matrix-green'
                        : 'border-neon-pink/30 bg-neon-pink/10 text-neon-pink',
                    ].join(' ')}
                  >
                    {botFeedback.message}
                  </div>
                ) : null}
                {(access === 'write' || access === 'admin') ? (
                  <div className="mt-4 rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {t('bots.createTitle')}
                      </h3>
                      <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan">
                        {t('bots.createRuntimeHint')}
                      </span>
                    </div>
                    <div className="mt-4 grid gap-3 md:grid-cols-2">
                      <input
                        value={createBotDraft.bot_key}
                        onChange={(event) => setCreateBotDraft((current) => ({
                          ...current,
                          bot_key: event.target.value,
                        }))}
                        placeholder={t('bots.createBotKeyPlaceholder')}
                        className="rounded-xl border border-grid-line/20 bg-terminal-bg/85 px-3 py-2 text-sm font-mono text-white outline-none transition-colors focus:border-neon-cyan/50"
                      />
                      <input
                        value={createBotDraft.display_name}
                        onChange={(event) => setCreateBotDraft((current) => ({
                          ...current,
                          display_name: event.target.value,
                        }))}
                        placeholder={t('bots.createDisplayNamePlaceholder')}
                        className="rounded-xl border border-grid-line/20 bg-terminal-bg/85 px-3 py-2 text-sm font-mono text-white outline-none transition-colors focus:border-neon-cyan/50"
                      />
                      <input
                        value={createBotDraft.default_locale}
                        onChange={(event) => setCreateBotDraft((current) => ({
                          ...current,
                          default_locale: event.target.value,
                        }))}
                        placeholder={t('bots.createLocalePlaceholder')}
                        className="rounded-xl border border-grid-line/20 bg-terminal-bg/85 px-3 py-2 text-sm font-mono text-white outline-none transition-colors focus:border-neon-cyan/50"
                      />
                      <select
                        value={createBotDraft.provisioning_path}
                        onChange={(event) => setCreateBotDraft((current) => ({
                          ...current,
                          provisioning_path: event.target.value as 'managed_bot' | 'manual_token',
                        }))}
                        className="rounded-xl border border-grid-line/20 bg-terminal-bg/85 px-3 py-2 text-sm font-mono text-white outline-none transition-colors focus:border-neon-cyan/50"
                      >
                        <option value="managed_bot">{t('bots.createProvisioningPathManaged')}</option>
                        <option value="manual_token">{t('bots.createProvisioningPathManual')}</option>
                      </select>
                      <textarea
                        value={createBotDraft.short_description}
                        onChange={(event) => setCreateBotDraft((current) => ({
                          ...current,
                          short_description: event.target.value,
                        }))}
                        placeholder={t('bots.createDescriptionPlaceholder')}
                        rows={3}
                        className="rounded-xl border border-grid-line/20 bg-terminal-bg/85 px-3 py-2 text-sm font-mono text-white outline-none transition-colors focus:border-neon-cyan/50 md:col-span-2"
                      />
                    </div>
                    <div className="mt-4 flex flex-wrap items-center gap-3">
                      <button
                        type="button"
                        onClick={() => {
                          void createPartnerBotMutation.mutateAsync(createBotDraft);
                        }}
                        disabled={
                          createPartnerBotMutation.isPending
                          || !state.activeWorkspaceId
                          || createBotDraft.bot_key.trim().length < 3
                          || createBotDraft.display_name.trim().length < 1
                        }
                        className="rounded-full border border-neon-cyan/40 bg-terminal-bg/80 px-4 py-2 text-xs font-mono uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:border-neon-cyan hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {createPartnerBotMutation.isPending
                          ? t('bots.createSubmitting')
                          : t('bots.createSubmit')}
                      </button>
                      <span className="text-xs font-mono text-muted-foreground">
                        {t('bots.createHelp')}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="mt-4 rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4 text-sm font-mono leading-6 text-muted-foreground">
                    {t('bots.readOnlyMode')}
                  </div>
                )}
                <div className="mt-4 space-y-3">
                  {partnerBotsQuery.isLoading ? (
                    <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4 text-sm font-mono leading-6 text-muted-foreground">
                      {t('bots.loading')}
                    </div>
                  ) : partnerBots.length === 0 ? (
                    <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4 text-sm font-mono leading-6 text-muted-foreground">
                      {t('bots.empty')}
                    </div>
                  ) : (
                    partnerBots.map((bot) => (
                      <article
                        key={bot.id}
                        className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                              {bot.display_name}
                            </h3>
                            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                              {bot.short_description ?? t('bots.routeHint')}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan">
                              {bot.status}
                            </p>
                            <p className="mt-2 text-xs font-mono text-muted-foreground">
                              {t('bots.tokenStatus', { value: bot.token_status })}
                            </p>
                          </div>
                        </div>
                        <div className="mt-3 grid gap-2 text-xs font-mono text-muted-foreground md:grid-cols-2">
                          <p>{t('bots.provisioningPath', { value: bot.provisioning_path })}</p>
                          <p>{t('bots.releaseChannel', { value: bot.release_channel })}</p>
                          <p>{t('bots.defaultLocale', { value: bot.default_locale })}</p>
                          <p>
                            {t('bots.binding', {
                              value: bot.telegram_username
                                ? `@${bot.telegram_username}`
                                : bot.telegram_bot_id
                                  ?? bot.managed_by_bot_id
                                  ?? t('bots.bindingPending'),
                            })}
                          </p>
                          <p>
                            {bot.latest_provisioning_job
                              ? t('bots.latestJob', {
                                  value: bot.latest_provisioning_job.job_status,
                                })
                              : t('bots.noJobs')}
                          </p>
                          <p className="md:col-span-2">
                            {t('bots.updatedAt', { value: formatDateTime(bot.updated_at, locale) })}
                          </p>
                        </div>
                        {bot.provisioning_last_error ? (
                          <p className="mt-3 rounded-lg border border-neon-pink/20 bg-neon-pink/5 px-3 py-2 text-xs font-mono leading-5 text-neon-pink">
                            {t('bots.lastError', { value: bot.provisioning_last_error })}
                          </p>
                        ) : null}
                        {bot.latest_provisioning_job?.result_payload?.reason_code ? (
                          <p className="mt-3 rounded-lg border border-grid-line/20 bg-terminal-surface/35 px-3 py-2 text-xs font-mono leading-5 text-muted-foreground">
                            {t('bots.lastReasonCode', {
                              value: String(bot.latest_provisioning_job.result_payload.reason_code),
                            })}
                          </p>
                        ) : null}
                        {(access === 'write' || access === 'admin') ? (
                          <div className="mt-4 rounded-lg border border-grid-line/20 bg-terminal-surface/35 p-3">
                            <div className="grid gap-3 md:grid-cols-2">
                              <input
                                value={getBotActionDraft(botActionDrafts, bot.id).action_reference}
                                onChange={(event) => updateBotActionDraft(bot.id, {
                                  action_reference: event.target.value,
                                })}
                                placeholder={
                                  bot.provisioning_path === 'manual_token'
                                    ? t('bots.actionReferenceManualPlaceholder')
                                    : t('bots.actionReferenceManagedPlaceholder')
                                }
                                className="rounded-lg border border-grid-line/20 bg-terminal-bg/85 px-3 py-2 text-xs font-mono text-white outline-none transition-colors focus:border-neon-cyan/50"
                              />
                              <input
                                value={getBotActionDraft(botActionDrafts, bot.id).suspend_reason}
                                onChange={(event) => updateBotActionDraft(bot.id, {
                                  suspend_reason: event.target.value,
                                })}
                                placeholder={t('bots.suspendReasonPlaceholder')}
                                className="rounded-lg border border-grid-line/20 bg-terminal-bg/85 px-3 py-2 text-xs font-mono text-white outline-none transition-colors focus:border-neon-cyan/50"
                              />
                            </div>
                            <div className="mt-3 flex flex-wrap gap-2">
                              <button
                                type="button"
                                onClick={() => {
                                  void provisionPartnerBotMutation.mutateAsync({
                                    botId: bot.id,
                                    provisioningPath: bot.provisioning_path,
                                    actionReference: getBotActionDraft(botActionDrafts, bot.id).action_reference,
                                  });
                                }}
                                disabled={
                                  provisionPartnerBotMutation.isPending
                                  || bot.status === 'suspended'
                                  || bot.status === 'revoked'
                                  || bot.status === 'provisioning_requested'
                                  || bot.status === 'provisioning_running'
                                }
                                className="rounded-full border border-neon-cyan/35 bg-terminal-bg/80 px-3 py-2 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:border-neon-cyan hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                {t('bots.actions.provision')}
                              </button>
                              <button
                                type="button"
                                onClick={() => {
                                  void rotateTokenMutation.mutateAsync({
                                    botId: bot.id,
                                    provisioningPath: bot.provisioning_path,
                                    actionReference: getBotActionDraft(botActionDrafts, bot.id).action_reference,
                                  });
                                }}
                                disabled={
                                  rotateTokenMutation.isPending
                                  || bot.status === 'suspended'
                                  || bot.status === 'revoked'
                                  || bot.status === 'provisioning_requested'
                                  || bot.status === 'provisioning_running'
                                }
                                className="rounded-full border border-neon-purple/35 bg-terminal-bg/80 px-3 py-2 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-purple transition-colors hover:border-neon-purple hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                {t('bots.actions.rotateToken')}
                              </button>
                              {bot.status === 'suspended' ? (
                                <button
                                  type="button"
                                  onClick={() => {
                                    void restorePartnerBotMutation.mutateAsync(bot.id);
                                  }}
                                  disabled={restorePartnerBotMutation.isPending}
                                  className="rounded-full border border-matrix-green/35 bg-terminal-bg/80 px-3 py-2 text-[11px] font-mono uppercase tracking-[0.18em] text-matrix-green transition-colors hover:border-matrix-green hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                  {t('bots.actions.restore')}
                                </button>
                              ) : (
                                <button
                                  type="button"
                                  onClick={() => {
                                    void suspendPartnerBotMutation.mutateAsync({
                                      botId: bot.id,
                                      reasonCode: getBotActionDraft(botActionDrafts, bot.id).suspend_reason,
                                    });
                                  }}
                                  disabled={suspendPartnerBotMutation.isPending}
                                  className="rounded-full border border-neon-pink/35 bg-terminal-bg/80 px-3 py-2 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-pink transition-colors hover:border-neon-pink hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                  {t('bots.actions.suspend')}
                                </button>
                              )}
                            </div>
                          </div>
                        ) : null}
                      </article>
                    ))
                  )}
                </div>
              </article>

              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                <div className="flex items-center gap-3">
                  <Waypoints className="h-5 w-5 text-neon-purple" />
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('delivery.title')}
                  </h2>
                </div>
                <div className="mt-4 space-y-3">
                  {state.integrationDeliveryLogs.map((item) => (
                    <article
                      key={item.id}
                      className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                          {portalT(`integrationDeliveryChannels.${item.channel}`)}
                        </p>
                        <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan">
                          {portalT(`integrationDeliveryStatuses.${item.status}`)}
                        </span>
                      </div>
                      <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                        {item.destination}
                      </p>
                      <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                        {item.notes[0]}
                      </p>
                    </article>
                  ))}
                </div>
              </article>

              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                      {t('widgets.title')}
                    </h2>
                    <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                      {t('widgets.description')}
                    </p>
                  </div>
                  <span className="rounded-full border border-neon-cyan/25 bg-neon-cyan/10 px-3 py-1 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan">
                    {t('widgets.runtimeHint')}
                  </span>
                </div>

                {widgetPreviewQuery.isLoading ? (
                  <div className="mt-4 rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4 text-sm font-mono leading-6 text-muted-foreground">
                    {t('widgets.loading')}
                  </div>
                ) : widgetPreviewQuery.isError || !widgetPreviewQuery.data ? (
                  <div className="mt-4 rounded-xl border border-neon-pink/20 bg-neon-pink/5 p-4 text-sm font-mono leading-6 text-neon-pink">
                    {t('widgets.error')}
                  </div>
                ) : (
                  <>
                    <div className="mt-4 grid gap-3 md:grid-cols-4">
                      <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3">
                        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                          {t('widgets.snapshot.status')}
                        </p>
                        <p className="mt-2 text-sm font-display uppercase tracking-[0.16em] text-white">
                          {widgetPreviewQuery.data.summary.status}
                        </p>
                      </div>
                      <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3">
                        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                          {t('widgets.snapshot.availability')}
                        </p>
                        <p className="mt-2 text-sm font-display uppercase tracking-[0.16em] text-white">
                          {widgetPreviewQuery.data.summary.currentAvailabilityPct.toFixed(2)}%
                        </p>
                      </div>
                      <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3">
                        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                          {t('widgets.snapshot.onlineServers')}
                        </p>
                        <p className="mt-2 text-sm font-display uppercase tracking-[0.16em] text-white">
                          {formatCompactNumber(widgetPreviewQuery.data.summary.onlineServers, locale)}
                        </p>
                      </div>
                      <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3">
                        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                          {t('widgets.snapshot.monthlyTraffic')}
                        </p>
                        <p className="mt-2 text-sm font-display uppercase tracking-[0.16em] text-white">
                          {formatTraffic(widgetPreviewQuery.data.summary.monthlyTrafficBytes, locale)}
                        </p>
                      </div>
                    </div>

                    <div className="mt-4 rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                            {t('widgets.previewTitle')}
                          </p>
                          <p className="mt-2 text-sm font-mono text-muted-foreground">
                            {t('widgets.snapshot.updatedAt', {
                              value: formatDateTime(widgetPreviewQuery.data.generatedAt, locale),
                            })}
                          </p>
                        </div>
                        <a
                          href={widgetPreviewUrl.toString()}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-2 text-sm font-mono text-neon-cyan underline underline-offset-4"
                        >
                          <span>{t('widgets.openLivePreview')}</span>
                          <ArrowUpRight className="h-3.5 w-3.5" />
                        </a>
                      </div>
                      <div className="mt-4 overflow-hidden rounded-[1.25rem] border border-grid-line/20 bg-black">
                        {shouldRenderLiveWidgetPreview() ? (
                          <iframe
                            title={t('widgets.previewTitle')}
                            src={widgetPreviewUrl.toString()}
                            loading="lazy"
                            className="w-full border-0"
                            style={{ height: `${widgetPreviewQuery.data.recommendedHeight}px` }}
                          />
                        ) : (
                          <div
                            aria-label={t('widgets.previewTitle')}
                            data-testid="partner-widget-preview-placeholder"
                            className="flex w-full items-center justify-center text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground"
                            style={{ height: `${widgetPreviewQuery.data.recommendedHeight}px` }}
                          >
                            {t('widgets.previewTitle')}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="mt-4">
                      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                        {t('widgets.embedCodeTitle')}
                      </p>
                      <DocsCodeBlock code={iframeSnippet} language="html" />
                    </div>
                  </>
                )}
              </article>

              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                  {t('capabilities.title')}
                </h2>
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
                  <Link href="/conversions" className="inline-flex items-center gap-2 text-sm font-mono text-neon-cyan underline underline-offset-4">
                    <span>{t('links.conversions')}</span>
                    <ArrowUpRight className="h-3.5 w-3.5" />
                  </Link>
                  <Link href="/cases" className="inline-flex items-center gap-2 text-sm font-mono text-neon-purple underline underline-offset-4">
                    <span>{t('links.cases')}</span>
                    <ArrowUpRight className="h-3.5 w-3.5" />
                  </Link>
                  <Link href="/reseller" className="inline-flex items-center gap-2 text-sm font-mono text-matrix-green underline underline-offset-4">
                    <span>{t('links.reseller')}</span>
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
