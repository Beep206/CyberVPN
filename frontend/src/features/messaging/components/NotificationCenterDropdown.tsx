'use client';

import { useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import {
  Bell,
  Check,
  Loader2,
  MessageSquare,
  RadioTower,
  RefreshCw,
  TriangleAlert,
} from 'lucide-react';
import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/utils';
import type { SiteNotification, SiteNotificationSeverity } from '@/lib/api/messaging';
import {
  useCustomerConversationList,
  useCustomerMessagingRealtimeSession,
  useCustomerNotifications,
  useMarkCustomerNotificationsRead,
  type CustomerMessagingRealtimeStatus,
} from '../hooks/useCustomerMessaging';

const SEVERITY_CLASSES: Record<SiteNotificationSeverity, string> = {
  critical: 'border-neon-pink/40 bg-neon-pink/10 text-neon-pink',
  info: 'border-neon-cyan/35 bg-neon-cyan/10 text-neon-cyan',
  success: 'border-matrix-green/35 bg-matrix-green/10 text-matrix-green',
  warning: 'border-amber-400/35 bg-amber-400/10 text-amber-200',
};

function formatTimestamp(locale: string, value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  try {
    return new Intl.DateTimeFormat(locale, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(date);
  } catch {
    return value;
  }
}

function notificationHref(notification: SiteNotification): string | null {
  if (notification.action_url?.startsWith('/')) {
    return notification.action_url;
  }

  if (notification.conversation_id) {
    return `/messages?conversation=${encodeURIComponent(notification.conversation_id)}`;
  }

  return null;
}

function statusClass(status: CustomerMessagingRealtimeStatus): string {
  if (status === 'connected') {
    return 'border-matrix-green/30 bg-matrix-green/10 text-matrix-green';
  }

  if (status === 'offline' || status === 'reconnecting') {
    return 'border-amber-400/35 bg-amber-400/10 text-amber-200';
  }

  return 'border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan';
}

export function NotificationCenterDropdown() {
  const locale = useLocale();
  const t = useTranslations('Messaging.notifications');
  const realtimeT = useTranslations('Messaging.realtime');
  const [isOpen, setIsOpen] = useState(false);
  const notificationsQuery = useCustomerNotifications({ limit: 10 });
  const conversationsQuery = useCustomerConversationList({ limit: 50 });
  const markRead = useMarkCustomerNotificationsRead();
  const realtime = useCustomerMessagingRealtimeSession();

  const notifications = notificationsQuery.data?.notifications ?? [];
  const unreadNotifications = notifications.filter(
    (notification) => notification.status !== 'read',
  );
  const unreadConversationCount = (conversationsQuery.data?.conversations ?? [])
    .filter((conversation) => conversation.unread_count > 0).length;
  const unreadTotal = unreadNotifications.length + unreadConversationCount;
  const isBusy =
    notificationsQuery.isFetching ||
    conversationsQuery.isFetching ||
    markRead.isPending;

  const markAllRead = () => {
    if (unreadNotifications.length === 0) {
      return;
    }

    markRead.mutate(unreadNotifications.map((notification) => notification.id));
  };

  return (
    <div className="relative">
      <button
        type="button"
        aria-label={t('triggerLabel', { count: unreadTotal })}
        aria-expanded={isOpen}
        aria-haspopup="dialog"
        onClick={() => setIsOpen((current) => !current)}
        className="relative inline-flex h-10 w-10 items-center justify-center rounded-md border border-grid-line/40 bg-terminal-bg/70 text-muted-foreground transition hover:border-neon-cyan/50 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-surface"
      >
        <Bell className="h-4 w-4" aria-hidden="true" />
        {unreadTotal > 0 ? (
          <span className="absolute -right-1 -top-1 flex min-h-5 min-w-5 items-center justify-center rounded-full border border-terminal-bg bg-neon-pink px-1 font-mono text-[10px] leading-none text-white">
            {unreadTotal > 99 ? '99+' : unreadTotal}
          </span>
        ) : null}
      </button>

      {isOpen ? (
        <section
          role="dialog"
          aria-label={t('panelLabel')}
          className="absolute right-0 top-12 z-50 w-[min(92vw,24rem)] overflow-hidden rounded-lg border border-grid-line/40 bg-terminal-surface/95 shadow-[0_0_40px_rgba(0,255,255,0.14)] backdrop-blur-xl"
        >
          <header className="border-b border-grid-line/30 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.22em] text-neon-cyan">
                  {t('eyebrow')}
                </p>
                <h2 className="mt-1 font-display text-base text-white">
                  {t('title')}
                </h2>
              </div>
              <button
                type="button"
                aria-label={t('markAllRead')}
                disabled={unreadNotifications.length === 0 || markRead.isPending}
                onClick={markAllRead}
                className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-grid-line/40 text-muted-foreground transition hover:border-matrix-green/50 hover:text-matrix-green focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan disabled:cursor-not-allowed disabled:opacity-40"
              >
                {markRead.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <Check className="h-4 w-4" aria-hidden="true" />
                )}
              </button>
            </div>
            <div
              className={cn(
                'mt-3 inline-flex items-center gap-2 rounded-md border px-2.5 py-1 font-mono text-xs',
                statusClass(realtime.status),
              )}
            >
              <RadioTower className="h-3.5 w-3.5" aria-hidden="true" />
              {realtimeT(`status.${realtime.status}`)}
            </div>
          </header>

          <div className="max-h-[30rem] overflow-y-auto p-3">
            {notificationsQuery.isLoading ? (
              <div className="space-y-2" aria-busy="true">
                {[0, 1, 2].map((item) => (
                  <div
                    key={item}
                    aria-hidden="true"
                    className="h-20 animate-pulse rounded-md border border-grid-line/30 bg-white/5"
                  />
                ))}
              </div>
            ) : notificationsQuery.isError ? (
              <div className="rounded-md border border-neon-pink/30 bg-neon-pink/10 p-3 text-sm text-neon-pink" role="alert">
                <TriangleAlert className="mb-2 h-4 w-4" aria-hidden="true" />
                {t('error')}
              </div>
            ) : notifications.length === 0 ? (
              <div className="rounded-md border border-grid-line/30 bg-terminal-bg/60 p-4 text-center">
                <Bell className="mx-auto h-8 w-8 text-muted-foreground" aria-hidden="true" />
                <p className="mt-2 font-display text-sm text-white">{t('emptyTitle')}</p>
                <p className="mt-1 text-sm text-muted-foreground">{t('emptyDescription')}</p>
              </div>
            ) : (
              <div className="space-y-2">
                {notifications.map((notification) => {
                  const href = notificationHref(notification);
                  const isUnread = notification.status !== 'read';
                  const content = (
                    <article
                      className={cn(
                        'rounded-md border p-3 transition',
                        isUnread
                          ? 'border-neon-cyan/40 bg-neon-cyan/10'
                          : 'border-grid-line/30 bg-terminal-bg/60',
                      )}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span
                              className={cn(
                                'rounded-md border px-2 py-0.5 font-mono text-[10px] uppercase',
                                SEVERITY_CLASSES[notification.severity],
                              )}
                            >
                              {t(`severity.${notification.severity}`)}
                            </span>
                            {isUnread ? (
                              <span className="h-2 w-2 rounded-full bg-neon-pink shadow-[0_0_8px_var(--color-neon-pink)]" />
                            ) : null}
                          </div>
                          <h3 className="mt-2 line-clamp-2 font-display text-sm text-white">
                            {notification.title}
                          </h3>
                          {notification.body ? (
                            <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                              {notification.body}
                            </p>
                          ) : null}
                          <time
                            dateTime={notification.created_at}
                            className="mt-2 block font-mono text-[11px] text-muted-foreground"
                          >
                            {formatTimestamp(locale, notification.created_at)}
                          </time>
                        </div>
                        {notification.notification_type === 'message' ? (
                          <MessageSquare className="mt-1 h-4 w-4 shrink-0 text-neon-cyan" aria-hidden="true" />
                        ) : null}
                      </div>
                    </article>
                  );

                  return (
                    <div key={notification.id} className="group relative">
                      {href ? (
                        <Link
                          href={href}
                          onClick={() => {
                            if (isUnread) {
                              markRead.mutate([notification.id]);
                            }
                            setIsOpen(false);
                          }}
                          className="block focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan"
                        >
                          {content}
                        </Link>
                      ) : (
                        content
                      )}
                      {isUnread && !href ? (
                        <button
                          type="button"
                          aria-label={t('markOneRead')}
                          onClick={() => markRead.mutate([notification.id])}
                          className="absolute right-2 top-2 inline-flex h-7 w-7 items-center justify-center rounded-md border border-grid-line/40 bg-terminal-bg/90 text-muted-foreground opacity-0 transition hover:border-matrix-green/50 hover:text-matrix-green focus:opacity-100 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan group-hover:opacity-100"
                        >
                          <Check className="h-3.5 w-3.5" aria-hidden="true" />
                        </button>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <footer className="flex items-center justify-between gap-3 border-t border-grid-line/30 p-3">
            <Link
              href="/messages"
              onClick={() => setIsOpen(false)}
              className="inline-flex min-h-9 items-center gap-2 rounded-md border border-neon-cyan/40 bg-neon-cyan/10 px-3 py-2 font-mono text-xs text-neon-cyan transition hover:bg-neon-cyan/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan"
            >
              <MessageSquare className="h-3.5 w-3.5" aria-hidden="true" />
              {t('openMessages')}
            </Link>
            <button
              type="button"
              aria-label={t('refresh')}
              onClick={() => {
                void notificationsQuery.refetch();
                void conversationsQuery.refetch();
                void realtime.recover();
              }}
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-grid-line/40 text-muted-foreground transition hover:border-neon-cyan/50 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan"
            >
              <RefreshCw
                className={cn('h-4 w-4', isBusy ? 'animate-spin' : '')}
                aria-hidden="true"
              />
            </button>
          </footer>
        </section>
      ) : null}
    </div>
  );
}
