'use client';

import { useState } from 'react';
import {
  AlertTriangle,
  Copy,
  ExternalLink,
  LifeBuoy,
  Loader2,
  RefreshCcw,
  Wrench,
} from 'lucide-react';
import { Modal } from '@/shared/ui/modal';
import type { GrowthNotificationDetail } from '@/lib/api/growth-notifications';
import {
  getGrowthNotificationHelpCenterLink,
  getGrowthNotificationRepairLink,
  getGrowthNotificationSupportActionLink,
  type GrowthNotificationActionLink,
  type GrowthTroubleshootingSurface,
} from '@/features/customer-growth/lib/growth-notification-routing';

function formatDate(locale: string, value?: string | null): string {
  if (!value) {
    return 'N/A';
  }

  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function channelLabel(
  channel: string,
  t: (key: string, values?: Record<string, string | number>) => string,
): string {
  if (channel === 'in_app') {
    return t('preferences.channels.inApp');
  }
  if (channel === 'email') {
    return t('preferences.channels.email');
  }
  if (channel === 'telegram') {
    return t('preferences.channels.telegram');
  }
  return channel;
}

type Props = {
  surface: GrowthTroubleshootingSurface;
  locale: string;
  t: (key: string, values?: Record<string, string | number>) => string;
  isOpen: boolean;
  onClose: () => void;
  detail: GrowthNotificationDetail | null;
  isLoading: boolean;
  isRecovering: boolean;
  isEscalatingSupport: boolean;
  recoveryError?: string | null;
  supportError?: string | null;
  onRequestRecovery: (notificationId: string, deliveryChannel: string) => void;
  onEscalateSupport: (notificationId: string, actionLink: GrowthNotificationActionLink) => void;
};

export function GrowthNotificationTroubleshootingModal({
  surface,
  locale,
  t,
  isOpen,
  onClose,
  detail,
  isLoading,
  isRecovering,
  isEscalatingSupport,
  recoveryError,
  supportError,
  onRequestRecovery,
  onEscalateSupport,
}: Props) {
  const [copied, setCopied] = useState(false);

  const supportActionLink = detail ? getGrowthNotificationSupportActionLink(surface, detail) : null;
  const helpCenterLink = getGrowthNotificationHelpCenterLink();
  const supportActionRequired = detail?.deliveries.some((delivery) => delivery.support_required) ?? false;

  const handleCopySupportSummary = async () => {
    if (!detail) {
      return;
    }

    try {
      await navigator.clipboard.writeText(detail.support_handoff.copy_text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={t('notifications.detailsTitle')}>
      {isLoading ? (
        <div className="flex items-center gap-3 rounded-xl border border-grid-line/40 bg-black/20 px-4 py-5 font-mono text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          {t('notifications.detailsLoading')}
        </div>
      ) : !detail ? (
        <div className="rounded-xl border border-grid-line/40 bg-black/20 px-4 py-5 font-mono text-sm text-muted-foreground">
          {t('notifications.detailsEmpty')}
        </div>
      ) : (
        <div className="space-y-6">
          <section className="rounded-2xl border border-grid-line/30 bg-terminal-surface/40 p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-lg font-display text-white">{detail.notification.title}</h3>
                  {detail.notification.archived_at ? (
                    <span className="rounded-full border border-white/15 bg-white/5 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.2em] text-white/70">
                      {t('notifications.archived')}
                    </span>
                  ) : null}
                </div>
                <p className="mt-2 text-sm text-white/85">{detail.notification.message}</p>
              </div>
              <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                {formatDate(locale, detail.notification.created_at)}
              </p>
            </div>

            {detail.notification.notes.length > 0 ? (
              <ul className="mt-4 space-y-1 text-xs text-muted-foreground">
                {detail.notification.notes.map((note) => (
                  <li key={note}>• {note}</li>
                ))}
              </ul>
            ) : null}
          </section>

          <section className="rounded-2xl border border-neon-cyan/20 bg-neon-cyan/5 p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <LifeBuoy className="h-4 w-4 text-neon-cyan" />
                  <h4 className="font-display text-base text-white">{t('notifications.supportTitle')}</h4>
                </div>
                <p className="text-sm text-white/85">{detail.support_handoff.troubleshooting_summary}</p>
                <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
                  {detail.support_handoff.reference_code}
                </p>
                {supportActionRequired && supportActionLink ? (
                  <p className="text-xs text-muted-foreground">
                    {t('notifications.supportActionHint')}
                  </p>
                ) : null}
              </div>
              <div className="flex flex-wrap justify-end gap-2">
                <button
                  type="button"
                  onClick={handleCopySupportSummary}
                  className="inline-flex items-center gap-2 rounded-lg border border-neon-cyan/30 bg-neon-cyan/10 px-3 py-2 font-mono text-xs uppercase tracking-[0.18em] text-neon-cyan transition hover:bg-neon-cyan/20"
                >
                  <Copy className="h-3.5 w-3.5" />
                  {copied ? t('notifications.copied') : t('notifications.copySupportSummary')}
                </button>
                {supportActionRequired && supportActionLink ? (
                  <button
                    type="button"
                    onClick={() =>
                      onEscalateSupport(detail.notification.id, supportActionLink)
                    }
                    disabled={isEscalatingSupport}
                    className="inline-flex items-center gap-2 rounded-lg border border-amber-400/30 bg-amber-400/10 px-3 py-2 font-mono text-xs uppercase tracking-[0.18em] text-amber-200 transition hover:bg-amber-400/20 disabled:opacity-60"
                  >
                    {isEscalatingSupport ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <LifeBuoy className="h-3.5 w-3.5" />
                    )}
                    {isEscalatingSupport
                      ? t('notifications.openingSupport')
                      : t(supportActionLink.labelKey)}
                  </button>
                ) : null}
                <a
                  href={helpCenterLink.href}
                  target={helpCenterLink.external ? '_blank' : undefined}
                  rel={helpCenterLink.external ? 'noreferrer noopener' : undefined}
                  onClick={onClose}
                  className="inline-flex items-center gap-2 rounded-lg border border-white/15 bg-white/5 px-3 py-2 font-mono text-xs uppercase tracking-[0.18em] text-white/80 transition hover:bg-white/10"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  {t(helpCenterLink.labelKey)}
                </a>
              </div>
            </div>
            {supportError ? (
              <div className="mt-4 rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                {supportError}
              </div>
            ) : null}
          </section>

          <section className="space-y-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-300" />
              <h4 className="font-display text-base text-white">{t('notifications.deliveryHistoryTitle')}</h4>
            </div>

            {recoveryError ? (
              <div className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                {recoveryError}
              </div>
            ) : null}

            {detail.deliveries.length === 0 ? (
              <div className="rounded-xl border border-grid-line/40 bg-black/20 px-4 py-5 font-mono text-sm text-muted-foreground">
                {t('notifications.noDeliveryHistory')}
              </div>
            ) : (
              detail.deliveries.map((delivery) => {
                const repairLink = getGrowthNotificationRepairLink(surface, delivery);

                return (
                  <article
                    key={delivery.delivery_id}
                    className="rounded-xl border border-grid-line/30 bg-black/20 p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <h5 className="font-display text-base text-white">
                            {channelLabel(delivery.delivery_channel, t)}
                          </h5>
                          <span className="rounded-full border border-white/15 bg-white/5 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.2em] text-white/70">
                            {delivery.troubleshooting_state}
                          </span>
                        </div>
                        <p className="text-sm text-white/85">{delivery.customer_summary}</p>
                        {delivery.repair_target ? (
                          <div className="rounded-lg border border-neon-cyan/20 bg-neon-cyan/5 px-3 py-2 text-xs text-white/75">
                            {delivery.repair_target.summary}
                          </div>
                        ) : null}
                        <div className="flex flex-wrap gap-4 font-mono text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
                          <span>
                            {t('notifications.deliveryPlannedAt', {
                              date: formatDate(locale, delivery.planned_at),
                            })}
                          </span>
                          {delivery.delivered_at ? (
                            <span>
                              {t('notifications.deliveryCompletedAt', {
                                date: formatDate(locale, delivery.delivered_at),
                              })}
                            </span>
                          ) : null}
                        </div>
                      </div>
                      <div className="flex flex-wrap justify-end gap-2">
                        {repairLink ? (
                          <a
                            href={repairLink.href}
                            target={repairLink.external ? '_blank' : undefined}
                            rel={repairLink.external ? 'noreferrer noopener' : undefined}
                            onClick={onClose}
                            className="inline-flex items-center gap-2 rounded-lg border border-white/15 bg-white/5 px-3 py-2 font-mono text-xs uppercase tracking-[0.18em] text-white/80 transition hover:bg-white/10"
                          >
                            <Wrench className="h-3.5 w-3.5" />
                            {t(repairLink.labelKey)}
                          </a>
                        ) : null}
                        {delivery.recovery_allowed ? (
                          <button
                            type="button"
                            onClick={() =>
                              onRequestRecovery(detail.notification.id, delivery.delivery_channel)
                            }
                            disabled={isRecovering}
                            className="inline-flex items-center gap-2 rounded-lg border border-neon-cyan/30 bg-neon-cyan/10 px-3 py-2 font-mono text-xs uppercase tracking-[0.18em] text-neon-cyan transition hover:bg-neon-cyan/20 disabled:opacity-60"
                          >
                            {isRecovering ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <RefreshCcw className="h-3.5 w-3.5" />
                            )}
                            {isRecovering
                              ? t('notifications.retrying')
                              : t('notifications.requestRetry')}
                          </button>
                        ) : null}
                      </div>
                    </div>

                    {delivery.events.length > 0 ? (
                      <ul className="mt-4 space-y-2 border-t border-grid-line/20 pt-4 text-xs text-muted-foreground">
                        {delivery.events.map((event) => (
                          <li
                            key={`${delivery.delivery_id}:${event.event_type}:${event.occurred_at ?? 'unknown'}`}
                          >
                            <span className="font-medium text-white/80">{event.summary}</span>
                            {event.occurred_at ? (
                              <span className="ml-2 font-mono uppercase tracking-[0.16em] text-muted-foreground">
                                {formatDate(locale, event.occurred_at)}
                              </span>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </article>
                );
              })
            )}
          </section>
        </div>
      )}
    </Modal>
  );
}
