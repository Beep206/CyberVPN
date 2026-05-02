'use client';

import { Archive, Bell, CheckCheck, Loader2 } from 'lucide-react';
import type {
  GrowthNotificationCounters,
  GrowthNotificationDetail,
  GrowthNotificationItem,
} from '@/lib/api/growth-notifications';
import type {
  GrowthNotificationActionLink,
  GrowthTroubleshootingSurface,
} from '@/features/customer-growth/lib/growth-notification-routing';
import { GrowthNotificationTroubleshootingModal } from './GrowthNotificationTroubleshootingModal';

function formatDate(locale: string, value?: string | null): string {
  if (!value) {
    return 'N/A';
  }

  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value));
}

function toneClasses(tone: string): string {
  if (tone === 'success') {
    return 'border-emerald-400/30 bg-emerald-500/10';
  }
  if (tone === 'critical') {
    return 'border-red-400/30 bg-red-500/10';
  }
  if (tone === 'warning') {
    return 'border-amber-400/30 bg-amber-500/10';
  }
  return 'border-cyan-400/30 bg-cyan-500/10';
}

type Props = {
  surface: GrowthTroubleshootingSurface;
  locale: string;
  t: (key: string, values?: Record<string, string | number>) => string;
  items: GrowthNotificationItem[];
  counters?: GrowthNotificationCounters | null;
  includeArchived: boolean;
  isLoading: boolean;
  isMarkingRead: boolean;
  isArchiving: boolean;
  isDetailLoading: boolean;
  isRecovering: boolean;
  isEscalatingSupport: boolean;
  recoveryError?: string | null;
  supportError?: string | null;
  selectedNotificationId: string | null;
  detail: GrowthNotificationDetail | null;
  onInspect: (notificationId: string) => void;
  onCloseDetail: () => void;
  onToggleArchived: () => void;
  onRequestRecovery: (notificationId: string, deliveryChannel: string) => void;
  onEscalateSupport: (notificationId: string, actionLink: GrowthNotificationActionLink) => void;
  onMarkRead: (notificationId: string) => void;
  onArchive: (notificationId: string) => void;
};

export function GrowthNotificationsPanel({
  surface,
  locale,
  t,
  items,
  counters,
  includeArchived,
  isLoading,
  isMarkingRead,
  isArchiving,
  isDetailLoading,
  isRecovering,
  isEscalatingSupport,
  recoveryError,
  supportError,
  selectedNotificationId,
  detail,
  onInspect,
  onCloseDetail,
  onToggleArchived,
  onRequestRecovery,
  onEscalateSupport,
  onMarkRead,
  onArchive,
}: Props) {
  return (
    <section className="cyber-card p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <Bell className="h-6 w-6 text-neon-cyan" />
          <div>
            <h3 className="text-lg font-display text-white">{t('notifications.title')}</h3>
            <p className="text-sm text-muted-foreground">{t('notifications.subtitle')}</p>
          </div>
        </div>
        <div className="grid gap-2 font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground sm:grid-cols-3">
          <span>{t('notifications.counters.total', { count: counters?.total_notifications ?? items.length })}</span>
          <span>{t('notifications.counters.unread', { count: counters?.unread_notifications ?? 0 })}</span>
          <span>
            {t('notifications.counters.actionRequired', {
              count: counters?.action_required_notifications ?? 0,
            })}
          </span>
        </div>
      </div>

      <div className="mt-4 flex justify-end">
        <button
          type="button"
          onClick={onToggleArchived}
          className="inline-flex items-center gap-2 rounded-lg border border-white/15 bg-white/5 px-3 py-2 font-mono text-xs uppercase tracking-[0.18em] text-white/80 transition hover:bg-white/10"
        >
          <Archive className="h-3.5 w-3.5" />
          {includeArchived ? t('notifications.showActive') : t('notifications.showArchived')}
        </button>
      </div>

      <div className="mt-5 space-y-3">
        {isLoading ? (
          <div className="flex items-center gap-3 rounded-xl border border-grid-line/40 bg-black/20 px-4 py-5 font-mono text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            {t('notifications.loading')}
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-xl border border-grid-line/40 bg-black/20 px-4 py-5 font-mono text-sm text-muted-foreground">
            {t('notifications.empty')}
          </div>
        ) : (
          items.slice(0, 8).map((item) => (
            <article
              key={item.id}
              className={`rounded-xl border px-4 py-4 ${toneClasses(item.tone)}`}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <h4 className="font-display text-base text-white">{item.title}</h4>
                    {item.unread ? (
                      <span className="rounded-full border border-neon-cyan/30 bg-neon-cyan/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.2em] text-neon-cyan">
                        {t('notifications.unread')}
                      </span>
                    ) : null}
                    {item.action_required ? (
                      <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.2em] text-amber-300">
                        {t('notifications.actionRequired')}
                      </span>
                    ) : null}
                  </div>
                  <p className="text-sm text-white/90">{item.message}</p>
                  {item.notes.length > 0 ? (
                    <ul className="space-y-1 text-xs text-muted-foreground">
                      {item.notes.map((note) => (
                        <li key={note}>• {note}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
                <div className="space-y-3 text-right">
                  <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                    {formatDate(locale, item.created_at)}
                  </p>
                  <div className="flex flex-wrap justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => onInspect(item.id)}
                      className="inline-flex items-center gap-2 rounded-lg border border-white/15 bg-white/5 px-3 py-2 font-mono text-xs uppercase tracking-[0.18em] text-white/80 transition hover:bg-white/10"
                    >
                      <Bell className="h-3.5 w-3.5" />
                      {t('notifications.detailsButton')}
                    </button>
                    {item.unread ? (
                      <button
                        type="button"
                        onClick={() => onMarkRead(item.id)}
                        disabled={isMarkingRead || isArchiving}
                        className="inline-flex items-center gap-2 rounded-lg border border-neon-cyan/30 bg-neon-cyan/10 px-3 py-2 font-mono text-xs uppercase tracking-[0.18em] text-neon-cyan transition hover:bg-neon-cyan/20 disabled:opacity-60"
                      >
                        <CheckCheck className="h-3.5 w-3.5" />
                        {t('notifications.markRead')}
                      </button>
                    ) : null}
                    <button
                      type="button"
                      onClick={() => onArchive(item.id)}
                      disabled={isArchiving || isMarkingRead}
                      className="inline-flex items-center gap-2 rounded-lg border border-white/15 bg-white/5 px-3 py-2 font-mono text-xs uppercase tracking-[0.18em] text-white/80 transition hover:bg-white/10 disabled:opacity-60"
                    >
                      <Archive className="h-3.5 w-3.5" />
                      {t('notifications.archive')}
                    </button>
                  </div>
                </div>
              </div>
            </article>
          ))
        )}
      </div>

      <GrowthNotificationTroubleshootingModal
        surface={surface}
        locale={locale}
        t={t}
        isOpen={selectedNotificationId !== null}
        onClose={onCloseDetail}
        detail={detail}
        isLoading={isDetailLoading}
        isRecovering={isRecovering}
        isEscalatingSupport={isEscalatingSupport}
        recoveryError={recoveryError}
        supportError={supportError}
        onRequestRecovery={onRequestRecovery}
        onEscalateSupport={onEscalateSupport}
      />
    </section>
  );
}
