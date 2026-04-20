'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { BellRing, CheckCheck, ExternalLink, Archive } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Link } from '@/i18n/navigation';
import {
  usePartnerPortalRuntimeState,
} from '@/features/partner-portal-state/lib/use-partner-portal-runtime-state';
import { partnerPortalApi } from '@/lib/api/partner-portal';

function normalizeRoute(routeSlug?: string | null): string {
  if (!routeSlug) {
    return '/dashboard';
  }
  return routeSlug.startsWith('/') ? routeSlug : `/${routeSlug}`;
}

function formatDateTime(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function notificationToneClass(tone: 'info' | 'success' | 'warning' | 'critical') {
  if (tone === 'success') {
    return 'border-matrix-green/25 bg-matrix-green/10';
  }
  if (tone === 'warning') {
    return 'border-neon-cyan/25 bg-neon-cyan/10';
  }
  if (tone === 'critical') {
    return 'border-neon-pink/25 bg-neon-pink/10';
  }
  return 'border-grid-line/20 bg-terminal-surface/35';
}

export function PartnerNotificationsPage() {
  const locale = useLocale();
  const queryClient = useQueryClient();
  const t = useTranslations('Partner.notifications');
  const portalT = useTranslations('Partner.portalState');
  const { state, activeWorkspace } = usePartnerPortalRuntimeState();

  const unreadCount = state.notifications.filter((notification) => notification.unread).length;
  const actionRequiredCount = state.notifications.filter((notification) => notification.actionRequired).length;

  const invalidateNotificationQueries = async () => {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: ['partner-portal', 'workspace-notifications', activeWorkspace?.id ?? null],
      }),
      queryClient.invalidateQueries({
        queryKey: ['partner-portal', 'session-bootstrap'],
      }),
    ]);
  };

  const markReadMutation = useMutation({
    mutationFn: async (notificationId: string) => {
      if (!activeWorkspace) {
        throw new Error('Active workspace is required');
      }
      const response = await partnerPortalApi.markNotificationRead(notificationId, {
        workspace_id: activeWorkspace.id,
      });
      return response.data;
    },
    onSuccess: async () => {
      await invalidateNotificationQueries();
    },
  });

  const archiveMutation = useMutation({
    mutationFn: async (notificationId: string) => {
      if (!activeWorkspace) {
        throw new Error('Active workspace is required');
      }
      const response = await partnerPortalApi.archiveNotification(notificationId, {
        workspace_id: activeWorkspace.id,
      });
      return response.data;
    },
    onSuccess: async () => {
      await invalidateNotificationQueries();
    },
  });

  return (
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

          <div className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-4 text-sm font-mono text-muted-foreground lg:w-[280px]">
            <div className="flex items-center justify-between gap-3">
              <span>{t('summary.unread')}</span>
              <span className="text-neon-cyan">{unreadCount}</span>
            </div>
            <div className="mt-3 flex items-center justify-between gap-3">
              <span>{t('summary.total')}</span>
              <span className="text-foreground">{state.notifications.length}</span>
            </div>
            <div className="mt-3 flex items-center justify-between gap-3">
              <span>{t('summary.actionRequired')}</span>
              <span className="text-neon-pink">{actionRequiredCount}</span>
            </div>
          </div>
        </div>
      </header>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
        <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
          <div className="flex items-center gap-3 border-b border-grid-line/20 pb-4">
            <BellRing className="h-5 w-5 text-neon-cyan" />
            <div>
              <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                {t('feed.title')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('feed.description')}
              </p>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            {state.notifications.length === 0 ? (
              <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4 text-sm font-mono leading-6 text-muted-foreground">
                {t('feed.empty')}
              </article>
            ) : null}
            {state.notifications.map((notification) => (
              <article
                key={notification.id}
                className={`rounded-2xl border p-4 ${notificationToneClass(notification.tone)}`}
              >
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-3">
                      <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {portalT(`notificationKinds.${notification.kind}.title`)}
                      </h3>
                      {notification.actionRequired ? (
                        <span className="inline-flex rounded-full border border-neon-pink/30 bg-neon-pink/10 px-2.5 py-1 text-[10px] font-mono uppercase tracking-[0.18em] text-neon-pink">
                          {t('feed.actionRequired')}
                        </span>
                      ) : null}
                      {notification.unread ? (
                        <span className="inline-flex rounded-full border border-neon-cyan/30 bg-neon-cyan/10 px-2.5 py-1 text-[10px] font-mono uppercase tracking-[0.18em] text-neon-cyan">
                          {t('feed.unread')}
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                      {notification.message || portalT(`notificationKinds.${notification.kind}.description`)}
                    </p>
                    {notification.notes && notification.notes.length > 0 ? (
                      <ul className="mt-3 space-y-2 text-xs font-mono leading-5 text-muted-foreground">
                        {notification.notes.map((note) => (
                          <li key={`${notification.id}:${note}`}>• {note}</li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                  <div className="flex flex-col items-start gap-3 md:items-end">
                    <p className="text-xs font-mono text-muted-foreground">
                      {formatDateTime(notification.createdAt, locale)}
                    </p>
                    <div className="flex flex-wrap items-center gap-2">
                      <Link
                        href={normalizeRoute(notification.routeSlug)}
                        className="inline-flex items-center rounded-full border border-grid-line/30 bg-terminal-surface/30 px-3 py-2 text-xs font-mono uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:border-neon-cyan/40"
                      >
                        <ExternalLink className="mr-2 h-4 w-4" />
                        {t('feed.open')}
                      </Link>
                      {notification.unread ? (
                        <Button
                          type="button"
                          variant="outline"
                          disabled={markReadMutation.isPending || !activeWorkspace}
                          onClick={() => {
                            void markReadMutation.mutateAsync(notification.id);
                          }}
                          className="border-grid-line/30 bg-terminal-surface/30 font-mono text-xs uppercase tracking-[0.18em]"
                        >
                          <CheckCheck className="mr-2 h-4 w-4" />
                          {t('feed.markRead')}
                        </Button>
                      ) : null}
                      <Button
                        type="button"
                        variant="outline"
                        disabled={archiveMutation.isPending || !activeWorkspace}
                        onClick={() => {
                          void archiveMutation.mutateAsync(notification.id);
                        }}
                        className="border-grid-line/30 bg-terminal-surface/30 font-mono text-xs uppercase tracking-[0.18em]"
                      >
                        <Archive className="mr-2 h-4 w-4" />
                        {t('feed.archive')}
                      </Button>
                    </div>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </article>

        <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
          <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
            {t('blockedStates.title')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('blockedStates.description')}
          </p>

          <div className="mt-5 space-y-3">
            <article className="rounded-2xl border border-grid-line/20 bg-terminal-bg/55 p-4">
              <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                {portalT('blockedOutcomes.finance.title')}
              </h3>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {portalT('blockedOutcomes.finance.description')}
              </p>
            </article>
            <article className="rounded-2xl border border-grid-line/20 bg-terminal-bg/55 p-4">
              <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                {portalT('blockedOutcomes.compliance.title')}
              </h3>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {portalT('blockedOutcomes.compliance.description')}
              </p>
            </article>
            <article className="rounded-2xl border border-grid-line/20 bg-terminal-bg/55 p-4">
              <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                {portalT('blockedOutcomes.technical.title')}
              </h3>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {portalT('blockedOutcomes.technical.description')}
              </p>
            </article>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <Link href="/cases" className="text-sm font-mono text-neon-cyan underline underline-offset-4">
              {t('blockedStates.links.cases')}
            </Link>
            <Link href="/application" className="text-sm font-mono text-neon-purple underline underline-offset-4">
              {t('blockedStates.links.application')}
            </Link>
          </div>
        </article>
      </div>
    </section>
  );
}
