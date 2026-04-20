'use client';

import { BellRing, Bot, RadioTower, Webhook } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { authApi } from '@/lib/api/auth';
import { governanceApi } from '@/lib/api/governance';
import { integrationsApi } from '@/lib/api/integrations';
import { monitoringApi } from '@/lib/api/monitoring';
import { IntegrationsEmptyState } from '@/features/integrations/components/integrations-empty-state';
import { IntegrationsPageShell } from '@/features/integrations/components/integrations-page-shell';
import { IntegrationsStatusChip } from '@/features/integrations/components/integrations-status-chip';
import {
  countEnabledChannels,
  formatCompactNumber,
  humanizeToken,
  statusTone,
} from '@/features/integrations/lib/formatting';

export function IntegrationsOverview() {
  const t = useTranslations('Integrations');

  const sessionQuery = useQuery({
    queryKey: ['integrations', 'session'],
    queryFn: async () => {
      const response = await authApi.session();
      return response.data;
    },
    staleTime: 60_000,
  });

  const healthQuery = useQuery({
    queryKey: ['integrations', 'health'],
    queryFn: async () => {
      const response = await monitoringApi.health();
      return response.data;
    },
    staleTime: 10_000,
  });

  const webhookQuery = useQuery({
    queryKey: ['integrations', 'webhooks'],
    queryFn: async () => {
      const response = await governanceApi.getWebhookLogs({
        page: 1,
        page_size: 8,
      });
      return response.data;
    },
    staleTime: 30_000,
  });

  const prefsQuery = useQuery({
    queryKey: ['integrations', 'notification-preferences'],
    queryFn: async () => {
      const response = await integrationsApi.getNotificationPreferences();
      return response.data;
    },
    staleTime: 30_000,
  });

  const botAccessQuery = useQuery({
    queryKey: ['integrations', 'telegram-bot-access'],
    queryFn: async () => {
      const response = await integrationsApi.getTelegramBotAccessSettings();
      return response.data;
    },
    staleTime: 60_000,
    retry: false,
  });

  const invalidWebhooks = (webhookQuery.data ?? []).filter(
    (entry) => entry.is_valid === false,
  );
  const enabledChannels = countEnabledChannels(prefsQuery.data);
  const session = sessionQuery.data;
  const health = healthQuery.data;

  return (
    <IntegrationsPageShell
      eyebrow={t('overview.eyebrow')}
      title={t('overview.title')}
      description={t('overview.description')}
      icon={Bot}
      metrics={[
        {
          label: t('overview.metrics.health'),
          value: health?.status ? humanizeToken(health.status) : '--',
          hint: t('overview.metrics.healthHint'),
          tone: statusTone(health?.status),
        },
        {
          label: t('overview.metrics.webhooks'),
          value: formatCompactNumber(invalidWebhooks.length),
          hint: t('overview.metrics.webhooksHint'),
          tone: invalidWebhooks.length > 0 ? 'danger' : 'success',
        },
        {
          label: t('overview.metrics.channels'),
          value: `${enabledChannels}/5`,
          hint: t('overview.metrics.channelsHint'),
          tone: enabledChannels >= 3 ? 'success' : 'warning',
        },
        {
          label: t('overview.metrics.telegram'),
          value: session?.telegram_id ? t('common.linked') : t('common.unlinked'),
          hint: t('overview.metrics.telegramHint'),
          tone: session?.telegram_id ? 'info' : 'neutral',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('overview.routesTitle')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('overview.routesDescription')}
          </p>
          <div className="mt-5 grid gap-3">
            {[
              {
                href: '/integrations/telegram',
                title: t('nav.telegram'),
                description: t('overview.routes.telegram'),
              },
              {
                href: '/integrations/push',
                title: t('nav.push'),
                description: t('overview.routes.push'),
              },
              {
                href: '/integrations/realtime',
                title: t('nav.realtime'),
                description: t('overview.routes.realtime'),
              },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4 transition-colors hover:border-neon-cyan/35 hover:bg-terminal-bg/60"
              >
                <p className="text-sm font-display uppercase tracking-[0.18em] text-white">
                  {item.title}
                </p>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {item.description}
                </p>
              </Link>
            ))}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
              <Webhook className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('overview.healthTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('overview.healthDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-3">
            {health?.components ? (
              Object.entries(health.components).map(([key, component]) => (
                <div
                  key={key}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                      {humanizeToken(key)}
                    </p>
                    <IntegrationsStatusChip
                      label={humanizeToken(component.status)}
                      tone={statusTone(component.status)}
                    />
                  </div>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {component.message}
                  </p>
                </div>
              ))
            ) : (
              <IntegrationsEmptyState label={t('common.empty')} />
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
              <BellRing className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('overview.channelsTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('overview.channelsDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-3">
            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                  {t('overview.channelCards.telegram')}
                </p>
                <IntegrationsStatusChip
                  label={session?.telegram_id ? t('common.linked') : t('common.unlinked')}
                  tone={session?.telegram_id ? 'info' : 'neutral'}
                />
              </div>
              <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                {session?.telegram_id
                  ? t('overview.channelCards.telegramLinked', { telegramId: String(session.telegram_id) })
                  : t('overview.channelCards.telegramUnlinked')}
              </p>
            </div>

            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                  {t('overview.channelCards.push')}
                </p>
                <IntegrationsStatusChip
                  label={`${enabledChannels}/5`}
                  tone={enabledChannels >= 3 ? 'success' : 'warning'}
                />
              </div>
              <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                {t('overview.channelCards.pushSummary', {
                  enabled: String(enabledChannels),
                })}
              </p>
            </div>

            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                  {t('overview.channelCards.botAccess')}
                </p>
                <IntegrationsStatusChip
                  label={
                    botAccessQuery.data?.access_mode
                      ? humanizeToken(botAccessQuery.data.access_mode)
                      : t('common.unavailable')
                  }
                  tone={botAccessQuery.data?.access_mode ? 'success' : 'warning'}
                />
              </div>
              <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                {botAccessQuery.data?.rules_url
                  ? t('overview.channelCards.botRulesUrl', {
                    url: botAccessQuery.data.rules_url,
                  })
                  : t('overview.channelCards.botSecretNote')}
              </p>
            </div>
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
              <RadioTower className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('overview.incidentsTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('overview.incidentsDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            {invalidWebhooks.length ? (
              invalidWebhooks.slice(0, 4).map((entry) => (
                <div
                  key={entry.id}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                      {humanizeToken(entry.source)}
                    </p>
                    <IntegrationsStatusChip
                      label={t('common.invalid')}
                      tone="danger"
                    />
                  </div>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {entry.error_message || humanizeToken(entry.event_type)}
                  </p>
                </div>
              ))
            ) : (
              <IntegrationsEmptyState label={t('common.noIncidents')} />
            )}
          </div>
        </article>
      </div>
    </IntegrationsPageShell>
  );
}
