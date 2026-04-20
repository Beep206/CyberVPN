'use client';

import {
  ScrollText,
  Settings2,
  Shield,
  UserPlus,
  Webhook,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useLocale, useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { governanceApi } from '@/lib/api/governance';
import { GovernanceEmptyState } from '@/features/governance/components/governance-empty-state';
import { GovernancePageShell } from '@/features/governance/components/governance-page-shell';
import { GovernanceStatusChip } from '@/features/governance/components/governance-status-chip';
import {
  formatDateTime,
  formatTtl,
  humanizeToken,
  settingFamily,
  shortId,
  toneForInviteRole,
  toneForWebhookState,
} from '@/features/governance/lib/formatting';

export function GovernanceOverview() {
  const t = useTranslations('Governance');
  const locale = useLocale();

  const auditQuery = useQuery({
    queryKey: ['governance', 'audit-log', 'overview'],
    queryFn: async () => {
      const response = await governanceApi.getAuditLogs({
        page: 1,
        page_size: 6,
      });
      return response.data;
    },
    staleTime: 30_000,
  });

  const webhookQuery = useQuery({
    queryKey: ['governance', 'webhook-log', 'overview'],
    queryFn: async () => {
      const response = await governanceApi.getWebhookLogs({
        page: 1,
        page_size: 6,
      });
      return response.data;
    },
    staleTime: 30_000,
  });

  const invitesQuery = useQuery({
    queryKey: ['governance', 'admin-invites'],
    queryFn: async () => {
      const response = await governanceApi.listAdminInvites();
      return response.data;
    },
    staleTime: 15_000,
  });

  const settingsQuery = useQuery({
    queryKey: ['governance', 'settings'],
    queryFn: async () => {
      const response = await governanceApi.getSettings();
      return response.data;
    },
    staleTime: 30_000,
  });

  const auditLogs = auditQuery.data ?? [];
  const webhookLogs = webhookQuery.data ?? [];
  const invites = invitesQuery.data?.invites ?? [];
  const settings = settingsQuery.data ?? [];
  const invalidWebhookCount = webhookLogs.filter(
    (entry) => entry.is_valid === false,
  ).length;
  const publicSettingsCount = settings.filter((item) => item.isPublic).length;
  const restrictedInviteCount = invites.filter((item) => item.email_hint).length;
  const settingFamilies = new Set(settings.map((item) => settingFamily(item.key)));

  return (
    <GovernancePageShell
      eyebrow={t('overview.eyebrow')}
      title={t('overview.title')}
      description={t('overview.description')}
      icon={Shield}
      metrics={[
        {
          label: t('overview.metrics.audit'),
          value: String(auditLogs.length),
          hint: t('overview.metrics.auditHint'),
          tone: 'info',
        },
        {
          label: t('overview.metrics.webhooks'),
          value: String(invalidWebhookCount),
          hint: t('overview.metrics.webhooksHint'),
          tone: invalidWebhookCount > 0 ? 'danger' : 'success',
        },
        {
          label: t('overview.metrics.invites'),
          value: String(invites.length),
          hint: t('overview.metrics.invitesHint'),
          tone: invites.length > 0 ? 'warning' : 'neutral',
        },
        {
          label: t('overview.metrics.settings'),
          value: String(settings.length),
          hint: t('overview.metrics.settingsHint'),
          tone: 'info',
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
                href: '/governance/audit-log',
                title: t('nav.auditLog'),
                description: t('overview.routes.auditLog'),
              },
              {
                href: '/governance/webhook-log',
                title: t('nav.webhookLog'),
                description: t('overview.routes.webhookLog'),
              },
              {
                href: '/governance/admin-invites',
                title: t('nav.adminInvites'),
                description: t('overview.routes.adminInvites'),
              },
              {
                href: '/governance/policy',
                title: t('nav.policy'),
                description: t('overview.routes.policy'),
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
              <ScrollText className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('overview.auditTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('overview.auditDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            {auditLogs.length ? (
              auditLogs.slice(0, 5).map((entry) => (
                <div
                  key={entry.id}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {humanizeToken(entry.action)}
                      </p>
                      <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {entry.entity_type ? humanizeToken(entry.entity_type) : t('common.none')} / #{shortId(entry.id)}
                      </p>
                    </div>

                    <GovernanceStatusChip
                      label={entry.admin_id ? t('common.attributed') : t('common.system')}
                      tone={entry.admin_id ? 'info' : 'warning'}
                    />
                  </div>
                  <p className="mt-3 text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {formatDateTime(entry.created_at, locale)}
                  </p>
                </div>
              ))
            ) : (
              <GovernanceEmptyState label={t('common.empty')} />
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
              <Webhook className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('overview.webhookTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('overview.webhookDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            {webhookLogs.length ? (
              webhookLogs.slice(0, 4).map((entry) => (
                <div
                  key={entry.id}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {humanizeToken(entry.source)}
                      </p>
                      <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {entry.event_type ? humanizeToken(entry.event_type) : t('common.none')}
                      </p>
                    </div>
                    <GovernanceStatusChip
                      label={
                        entry.is_valid === false
                          ? t('common.invalid')
                          : entry.processed_at
                            ? t('common.processed')
                            : t('common.pending')
                      }
                      tone={toneForWebhookState(entry)}
                    />
                  </div>
                  <p className="mt-3 text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {formatDateTime(entry.created_at, locale)}
                  </p>
                </div>
              ))
            ) : (
              <GovernanceEmptyState label={t('common.empty')} />
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <div>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
                  <UserPlus className="h-4 w-4" />
                </div>
                <div>
                  <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                    {t('overview.invitesTitle')}
                  </h2>
                  <p className="mt-1 text-sm font-mono text-muted-foreground">
                    {t('overview.invitesDescription')}
                  </p>
                </div>
              </div>

              <div className="mt-5 space-y-3">
                {invites.length ? (
                  invites.slice(0, 3).map((invite) => (
                    <div
                      key={invite.token}
                      className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="font-display uppercase tracking-[0.14em] text-white">
                            #{shortId(invite.token)}
                          </p>
                          <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                            {invite.email_hint ?? t('common.none')}
                          </p>
                        </div>
                        <GovernanceStatusChip
                          label={humanizeToken(invite.role)}
                          tone={toneForInviteRole(invite.role)}
                        />
                      </div>
                      <p className="mt-3 text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {formatTtl(invite.ttl_seconds)}
                      </p>
                    </div>
                  ))
                ) : (
                  <GovernanceEmptyState label={t('common.empty')} />
                )}
              </div>
            </div>

            <div>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
                  <Settings2 className="h-4 w-4" />
                </div>
                <div>
                  <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                    {t('overview.policyTitle')}
                  </h2>
                  <p className="mt-1 text-sm font-mono text-muted-foreground">
                    {t('overview.policyDescription')}
                  </p>
                </div>
              </div>

              <div className="mt-5 grid gap-3">
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('overview.policyStats.restrictedInvites')}
                  </p>
                  <p className="mt-3 text-2xl font-display tracking-[0.12em] text-white">
                    {restrictedInviteCount}
                  </p>
                </div>
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('overview.policyStats.publicSettings')}
                  </p>
                  <p className="mt-3 text-2xl font-display tracking-[0.12em] text-white">
                    {publicSettingsCount}
                  </p>
                </div>
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('overview.policyStats.settingFamilies')}
                  </p>
                  <p className="mt-3 text-2xl font-display tracking-[0.12em] text-white">
                    {settingFamilies.size}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </article>
      </div>
    </GovernancePageShell>
  );
}
