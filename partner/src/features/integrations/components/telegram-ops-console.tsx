'use client';

import { useState } from 'react';
import { Bot, KeyRound, Send, ShieldPlus } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocale, useTranslations } from 'next-intl';
import { authApi } from '@/lib/api/auth';
import { integrationsApi } from '@/lib/api/integrations';
import { plansApi } from '@/lib/api/plans';
import { IntegrationsEmptyState } from '@/features/integrations/components/integrations-empty-state';
import { IntegrationsPageShell } from '@/features/integrations/components/integrations-page-shell';
import { IntegrationsStatusChip } from '@/features/integrations/components/integrations-status-chip';
import {
  formatBytes,
  formatDateTime,
  getErrorMessage,
  humanizeToken,
  statusTone,
  stringifyJson,
  summarizeBotUser,
} from '@/features/integrations/lib/formatting';

function parseTelegramId(value: string) {
  const normalized = value.trim();
  if (!/^\d+$/.test(normalized)) {
    return null;
  }

  return Number(normalized);
}

export function TelegramOpsConsole() {
  const t = useTranslations('Integrations');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const [telegramIdInput, setTelegramIdInput] = useState('');
  const [inspectedTelegramId, setInspectedTelegramId] = useState<number | null>(null);
  const [selectedPlan, setSelectedPlan] = useState('');
  const [durationDays, setDurationDays] = useState('30');
  const [bootstrapUsername, setBootstrapUsername] = useState('');
  const [bootstrapFirstName, setBootstrapFirstName] = useState('');
  const [bootstrapLanguage, setBootstrapLanguage] = useState('en');
  const [bootstrapReferrerId, setBootstrapReferrerId] = useState('');
  const [telegramIdTouched, setTelegramIdTouched] = useState(false);

  const sessionQuery = useQuery({
    queryKey: ['integrations', 'telegram', 'session'],
    queryFn: async () => {
      const response = await authApi.session();
      return response.data;
    },
    staleTime: 60_000,
  });

  const plansQuery = useQuery({
    queryKey: ['integrations', 'telegram', 'plans'],
    queryFn: async () => {
      const response = await plansApi.list();
      return response.data;
    },
    staleTime: 60_000,
  });

  const botAccessQuery = useQuery({
    queryKey: ['integrations', 'telegram', 'bot-access'],
    queryFn: async () => {
      const response = await integrationsApi.getTelegramBotAccessSettings();
      return response.data;
    },
    staleTime: 60_000,
    retry: false,
  });

  const botPlansQuery = useQuery({
    queryKey: ['integrations', 'telegram', 'bot-plans'],
    queryFn: async () => {
      const response = await integrationsApi.getTelegramBotPlans();
      return response.data;
    },
    staleTime: 60_000,
    retry: false,
  });

  const telegramUserQuery = useQuery({
    queryKey: ['integrations', 'telegram', 'user', inspectedTelegramId],
    queryFn: async () => {
      const response = await integrationsApi.getTelegramUser(inspectedTelegramId!);
      return response.data;
    },
    enabled: inspectedTelegramId !== null,
    retry: false,
  });

  const telegramConfigQuery = useQuery({
    queryKey: ['integrations', 'telegram', 'config', inspectedTelegramId],
    queryFn: async () => {
      const response = await integrationsApi.getTelegramConfig(inspectedTelegramId!);
      return response.data;
    },
    enabled: inspectedTelegramId !== null,
    retry: false,
  });

  const botUserQuery = useQuery({
    queryKey: ['integrations', 'telegram', 'bot-user', inspectedTelegramId],
    queryFn: async () => {
      const response = await integrationsApi.getTelegramBotUser(inspectedTelegramId!);
      return response.data;
    },
    enabled: inspectedTelegramId !== null,
    retry: false,
  });

  const botSubscriptionsQuery = useQuery({
    queryKey: ['integrations', 'telegram', 'bot-subscriptions', inspectedTelegramId],
    queryFn: async () => {
      const response = await integrationsApi.getTelegramBotSubscriptions(inspectedTelegramId!);
      return response.data;
    },
    enabled: inspectedTelegramId !== null,
    retry: false,
  });

  const botTrialQuery = useQuery({
    queryKey: ['integrations', 'telegram', 'bot-trial', inspectedTelegramId],
    queryFn: async () => {
      const response = await integrationsApi.getTelegramBotTrialStatus(inspectedTelegramId!);
      return response.data;
    },
    enabled: inspectedTelegramId !== null,
    retry: false,
  });

  const botReferralQuery = useQuery({
    queryKey: ['integrations', 'telegram', 'bot-referrals', inspectedTelegramId],
    queryFn: async () => {
      const response = await integrationsApi.getTelegramBotReferralStats(inspectedTelegramId!);
      return response.data;
    },
    enabled: inspectedTelegramId !== null,
    retry: false,
  });

  const botConfigQuery = useQuery({
    queryKey: ['integrations', 'telegram', 'bot-config', inspectedTelegramId],
    queryFn: async () => {
      const response = await integrationsApi.getTelegramBotConfig(inspectedTelegramId!);
      return response.data;
    },
    enabled: inspectedTelegramId !== null,
    retry: false,
  });

  const linkMutation = useMutation({
    mutationFn: async (telegramId: number) => {
      const response = await integrationsApi.generateTelegramLoginLink({
        telegram_id: telegramId,
      });
      return response.data;
    },
  });

  const subscriptionMutation = useMutation({
    mutationFn: async (telegramId: number) => {
      const response = await integrationsApi.createTelegramSubscription(
        telegramId,
        {
          plan_name: effectiveSelectedPlan,
          duration_days: Number(durationDays),
        },
      );
      return response.data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ['integrations', 'telegram', 'user', inspectedTelegramId],
        }),
        queryClient.invalidateQueries({
          queryKey: ['integrations', 'telegram', 'bot-subscriptions', inspectedTelegramId],
        }),
      ]);
    },
  });

  const bootstrapMutation = useMutation({
    mutationFn: async (telegramId: number) => {
      const response = await integrationsApi.bootstrapTelegramBotUser({
        telegram_id: telegramId,
        username: bootstrapUsername || undefined,
        first_name: bootstrapFirstName || undefined,
        language_code: bootstrapLanguage,
        referrer_id: bootstrapReferrerId ? Number(bootstrapReferrerId) : undefined,
      });
      return response.data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ['integrations', 'telegram', 'bot-user', inspectedTelegramId],
        }),
        queryClient.invalidateQueries({
          queryKey: ['integrations', 'telegram', 'bot-trial', inspectedTelegramId],
        }),
        queryClient.invalidateQueries({
          queryKey: ['integrations', 'telegram', 'bot-referrals', inspectedTelegramId],
        }),
      ]);
    },
  });

  const activateTrialMutation = useMutation({
    mutationFn: async (telegramId: number) => {
      const response = await integrationsApi.activateTelegramBotTrial(telegramId);
      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ['integrations', 'telegram', 'bot-trial', inspectedTelegramId],
      });
    },
  });

  const activePlans = (plansQuery.data ?? []).filter((plan) => plan.is_active);
  const effectiveTelegramIdInput = telegramIdTouched
    ? telegramIdInput
    : sessionQuery.data?.telegram_id
      ? String(sessionQuery.data.telegram_id)
      : telegramIdInput;
  const effectiveSelectedPlan = selectedPlan || activePlans[0]?.name || '';
  const inspected = inspectedTelegramId !== null;

  return (
    <IntegrationsPageShell
      eyebrow={t('telegram.eyebrow')}
      title={t('telegram.title')}
      description={t('telegram.description')}
      icon={Bot}
      metrics={[
        {
          label: t('telegram.metrics.accessMode'),
          value: botAccessQuery.data?.access_mode
            ? humanizeToken(botAccessQuery.data.access_mode)
            : '--',
          hint: t('telegram.metrics.accessModeHint'),
          tone: statusTone(botAccessQuery.data?.access_mode),
        },
        {
          label: t('telegram.metrics.catalog'),
          value: String(activePlans.length),
          hint: t('telegram.metrics.catalogHint'),
          tone: 'info',
        },
        {
          label: t('telegram.metrics.operatorTelegram'),
          value: sessionQuery.data?.telegram_id
            ? String(sessionQuery.data.telegram_id)
            : '--',
          hint: t('telegram.metrics.operatorTelegramHint'),
          tone: sessionQuery.data?.telegram_id ? 'success' : 'neutral',
        },
        {
          label: t('telegram.metrics.botPlans'),
          value: String(botPlansQuery.data?.length ?? 0),
          hint: t('telegram.metrics.botPlansHint'),
          tone: botPlansQuery.data?.length ? 'success' : 'warning',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
              <ShieldPlus className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('telegram.accessTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('telegram.accessDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                  {t('telegram.accessCards.botSettings')}
                </p>
                <IntegrationsStatusChip
                  label={
                    botAccessQuery.data?.access_mode
                      ? humanizeToken(botAccessQuery.data.access_mode)
                      : t('common.unavailable')
                  }
                  tone={statusTone(botAccessQuery.data?.access_mode)}
                />
              </div>
              <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                {botAccessQuery.data
                  ? t('telegram.accessCards.botSettingsSummary', {
                    channelId: botAccessQuery.data.channel_id || '--',
                  })
                  : getErrorMessage(botAccessQuery.error)}
              </p>
            </div>

            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                  {t('telegram.accessCards.botCatalog')}
                </p>
                <IntegrationsStatusChip
                  label={String(botPlansQuery.data?.length ?? 0)}
                  tone={botPlansQuery.data?.length ? 'success' : 'warning'}
                />
              </div>
              <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                {botPlansQuery.data?.length
                  ? t('telegram.accessCards.botCatalogSummary')
                  : getErrorMessage(botPlansQuery.error)}
              </p>
            </div>
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
              <KeyRound className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('telegram.lookupTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('telegram.lookupDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-4 md:grid-cols-[minmax(0,1fr)_auto]">
            <label className="space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('telegram.fields.telegramId')}
              </span>
              <input
                value={effectiveTelegramIdInput}
                onChange={(event) => {
                  setTelegramIdTouched(true);
                  setTelegramIdInput(event.target.value);
                }}
                placeholder={t('telegram.placeholders.telegramId')}
                className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-sm font-mono text-white outline-none transition-colors placeholder:text-muted-foreground focus:border-neon-cyan/40"
              />
            </label>

            <button
              type="button"
              onClick={() =>
                setInspectedTelegramId(parseTelegramId(effectiveTelegramIdInput))}
              className="self-end rounded-xl border border-neon-cyan/35 bg-neon-cyan/10 px-4 py-3 text-sm font-mono uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:bg-neon-cyan/15"
            >
              {t('telegram.actions.inspect')}
            </button>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <button
              type="button"
              disabled={!inspectedTelegramId || linkMutation.isPending}
              onClick={() => inspectedTelegramId && linkMutation.mutate(inspectedTelegramId)}
              className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-xs font-mono uppercase tracking-[0.18em] text-white transition-colors hover:border-neon-cyan/35"
            >
              {linkMutation.isPending
                ? t('telegram.actions.generatingLink')
                : t('telegram.actions.generateLink')}
            </button>

            <button
              type="button"
              disabled={!inspectedTelegramId || bootstrapMutation.isPending}
              onClick={() => inspectedTelegramId && bootstrapMutation.mutate(inspectedTelegramId)}
              className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-xs font-mono uppercase tracking-[0.18em] text-white transition-colors hover:border-neon-cyan/35"
            >
              {bootstrapMutation.isPending
                ? t('telegram.actions.bootstrapping')
                : t('telegram.actions.bootstrap')}
            </button>

            <button
              type="button"
              disabled={!inspectedTelegramId || activateTrialMutation.isPending}
              onClick={() => inspectedTelegramId && activateTrialMutation.mutate(inspectedTelegramId)}
              className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-xs font-mono uppercase tracking-[0.18em] text-white transition-colors hover:border-neon-cyan/35"
            >
              {activateTrialMutation.isPending
                ? t('telegram.actions.activatingTrial')
                : t('telegram.actions.activateTrial')}
            </button>
          </div>

          {linkMutation.data ? (
            <div className="mt-4 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('telegram.loginLinkLabel')}
              </p>
              <p className="mt-2 break-all text-sm font-mono text-neon-cyan">
                {linkMutation.data.url}
              </p>
              <p className="mt-2 text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                {t('telegram.expiresAtLabel')}: {formatDateTime(linkMutation.data.expires_at, locale)}
              </p>
            </div>
          ) : null}

          {(linkMutation.error || bootstrapMutation.error || activateTrialMutation.error) ? (
            <div className="mt-4 rounded-2xl border border-neon-pink/30 bg-neon-pink/10 p-4 text-sm font-mono text-neon-pink">
              {getErrorMessage(
                linkMutation.error
                || bootstrapMutation.error
                || activateTrialMutation.error,
              )}
            </div>
          ) : null}
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
              <Send className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('telegram.subscriptionTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('telegram.subscriptionDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-4">
            <label className="space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('telegram.fields.plan')}
              </span>
              <select
                value={effectiveSelectedPlan}
                onChange={(event) => setSelectedPlan(event.target.value)}
                className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-sm font-mono text-white outline-none transition-colors focus:border-neon-cyan/40"
              >
                {activePlans.map((plan) => (
                  <option key={plan.uuid} value={plan.name}>
                    {plan.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('telegram.fields.durationDays')}
              </span>
              <input
                value={durationDays}
                onChange={(event) => setDurationDays(event.target.value)}
                className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-sm font-mono text-white outline-none transition-colors placeholder:text-muted-foreground focus:border-neon-cyan/40"
              />
            </label>

            <button
              type="button"
              disabled={!inspectedTelegramId || !effectiveSelectedPlan || subscriptionMutation.isPending}
              onClick={() => inspectedTelegramId && subscriptionMutation.mutate(inspectedTelegramId)}
              className="rounded-xl border border-neon-cyan/35 bg-neon-cyan/10 px-4 py-3 text-sm font-mono uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:bg-neon-cyan/15"
            >
              {subscriptionMutation.isPending
                ? t('telegram.actions.creatingSubscription')
                : t('telegram.actions.createSubscription')}
            </button>
          </div>

          {subscriptionMutation.data ? (
            <pre className="mt-4 overflow-x-auto rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4 text-xs font-mono text-muted-foreground">
              {stringifyJson(subscriptionMutation.data)}
            </pre>
          ) : null}
          {subscriptionMutation.error ? (
            <div className="mt-4 rounded-2xl border border-neon-pink/30 bg-neon-pink/10 p-4 text-sm font-mono text-neon-pink">
              {getErrorMessage(subscriptionMutation.error)}
            </div>
          ) : null}
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('telegram.bootstrapTitle')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('telegram.bootstrapDescription')}
          </p>

          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <label className="space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('telegram.fields.username')}
              </span>
              <input
                value={bootstrapUsername}
                onChange={(event) => setBootstrapUsername(event.target.value)}
                className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-sm font-mono text-white outline-none transition-colors focus:border-neon-cyan/40"
              />
            </label>

            <label className="space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('telegram.fields.firstName')}
              </span>
              <input
                value={bootstrapFirstName}
                onChange={(event) => setBootstrapFirstName(event.target.value)}
                className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-sm font-mono text-white outline-none transition-colors focus:border-neon-cyan/40"
              />
            </label>

            <label className="space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('telegram.fields.language')}
              </span>
              <input
                value={bootstrapLanguage}
                onChange={(event) => setBootstrapLanguage(event.target.value)}
                className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-sm font-mono text-white outline-none transition-colors focus:border-neon-cyan/40"
              />
            </label>

            <label className="space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('telegram.fields.referrerId')}
              </span>
              <input
                value={bootstrapReferrerId}
                onChange={(event) => setBootstrapReferrerId(event.target.value)}
                className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-sm font-mono text-white outline-none transition-colors focus:border-neon-cyan/40"
              />
            </label>
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-4">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('telegram.userTitle')}
          </h2>
          <div className="mt-5 space-y-3">
            {telegramUserQuery.data ? (
              <>
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                      {telegramUserQuery.data.username}
                    </p>
                    <IntegrationsStatusChip
                      label={humanizeToken(telegramUserQuery.data.status)}
                      tone={statusTone(telegramUserQuery.data.status)}
                    />
                  </div>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    UUID: {telegramUserQuery.data.uuid}
                  </p>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                    <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('telegram.labels.dataUsage')}
                    </p>
                    <p className="mt-2 text-lg font-display tracking-[0.1em] text-white">
                      {formatBytes(telegramUserQuery.data.data_usage)}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                    <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('telegram.labels.dataLimit')}
                    </p>
                    <p className="mt-2 text-lg font-display tracking-[0.1em] text-white">
                      {formatBytes(telegramUserQuery.data.data_limit)}
                    </p>
                  </div>
                </div>
              </>
            ) : inspected ? (
              <IntegrationsEmptyState
                label={getErrorMessage(telegramUserQuery.error) || t('common.empty')}
              />
            ) : (
              <IntegrationsEmptyState label={t('telegram.emptyLookup')} />
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-4">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('telegram.botUserTitle')}
          </h2>
          <div className="mt-5 space-y-3">
            {botUserQuery.data ? (
              <>
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                      {summarizeBotUser(botUserQuery.data)}
                    </p>
                    <IntegrationsStatusChip
                      label={humanizeToken(botUserQuery.data.status)}
                      tone={statusTone(botUserQuery.data.status)}
                    />
                  </div>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {t('telegram.labels.languageCode')}: {botUserQuery.data.language_code}
                  </p>
                </div>

                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('telegram.labels.trialStatus')}
                    </p>
                    <IntegrationsStatusChip
                      label={
                        botTrialQuery.data?.is_trial_active
                          ? t('common.active')
                          : botTrialQuery.data?.eligible
                            ? t('common.eligible')
                            : t('common.inactive')
                      }
                      tone={
                        botTrialQuery.data?.is_trial_active
                          ? 'success'
                          : botTrialQuery.data?.eligible
                            ? 'info'
                            : 'warning'
                      }
                    />
                  </div>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {botTrialQuery.data
                      ? t('telegram.trialSummary', {
                        days: String(botTrialQuery.data.days_remaining),
                      })
                      : getErrorMessage(botTrialQuery.error)}
                  </p>
                </div>
              </>
            ) : inspected ? (
              <IntegrationsEmptyState label={getErrorMessage(botUserQuery.error)} />
            ) : (
              <IntegrationsEmptyState label={t('telegram.emptyLookup')} />
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-4">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('telegram.referralTitle')}
          </h2>
          <div className="mt-5 space-y-3">
            {botReferralQuery.data ? (
              <>
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('telegram.labels.totalReferrals')}
                  </p>
                  <p className="mt-2 text-lg font-display tracking-[0.1em] text-white">
                    {botReferralQuery.data.total_referrals}
                  </p>
                </div>
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('telegram.labels.referralLink')}
                  </p>
                  <p className="mt-2 break-all text-sm font-mono text-muted-foreground">
                    {botReferralQuery.data.referral_link || '--'}
                  </p>
                </div>
              </>
            ) : inspected ? (
              <IntegrationsEmptyState label={getErrorMessage(botReferralQuery.error)} />
            ) : (
              <IntegrationsEmptyState label={t('telegram.emptyLookup')} />
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('telegram.subscriptionsTitle')}
          </h2>
          <div className="mt-5 space-y-3">
            {botSubscriptionsQuery.data?.length ? (
              botSubscriptionsQuery.data.map((subscription, index) => (
                <div
                  key={`${subscription.status}-${index}`}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                      {subscription.plan_name || t('common.none')}
                    </p>
                    <IntegrationsStatusChip
                      label={humanizeToken(subscription.status)}
                      tone={statusTone(subscription.status)}
                    />
                  </div>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {t('telegram.subscriptionSummary', {
                      expiresAt: formatDateTime(subscription.expires_at, locale),
                    })}
                  </p>
                </div>
              ))
            ) : inspected ? (
              <IntegrationsEmptyState
                label={getErrorMessage(botSubscriptionsQuery.error) || t('common.empty')}
              />
            ) : (
              <IntegrationsEmptyState label={t('telegram.emptyLookup')} />
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('telegram.configTitle')}
          </h2>
          <div className="mt-5 grid gap-4">
            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('telegram.labels.adminConfig')}
              </p>
              <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap break-all text-xs font-mono leading-5 text-muted-foreground">
                {telegramConfigQuery.data?.config_string
                  ? telegramConfigQuery.data.config_string
                  : inspected
                    ? getErrorMessage(telegramConfigQuery.error)
                    : t('telegram.emptyLookup')}
              </pre>
            </div>

            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('telegram.labels.botConfig')}
              </p>
              <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap break-all text-xs font-mono leading-5 text-muted-foreground">
                {botConfigQuery.data?.config_string
                  ? botConfigQuery.data.config_string
                  : inspected
                    ? getErrorMessage(botConfigQuery.error)
                    : t('telegram.emptyLookup')}
              </pre>
            </div>
          </div>
        </article>
      </div>
    </IntegrationsPageShell>
  );
}
