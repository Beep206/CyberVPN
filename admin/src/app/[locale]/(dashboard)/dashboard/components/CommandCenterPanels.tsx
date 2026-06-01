'use client';

import type { ComponentType, ReactNode } from 'react';
import {
  ArrowUpRight,
  CheckCircle2,
  Inbox,
  Landmark,
  ReceiptText,
  ScrollText,
  UserRoundCheck,
  Webhook,
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { components } from '@/lib/api/generated/types';
import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/utils';
import {
  getAdminRolePermissions,
  type AdminPermission,
} from '@/shared/lib/admin-rbac';
import { useAuthStore } from '@/stores/auth-store';
import {
  resolveAdminNavigationGroups,
  type ResolvedAdminNavItem,
} from '@/features/admin-shell/config/admin-navigation';
import {
  ADMIN_NAV_ITEMS,
  ADMIN_SECTION_OVERVIEWS,
  type AdminNavItem,
  type AdminSectionSlug,
} from '@/features/admin-shell/config/section-registry';
import {
  formatAdminQueueBadge,
  useAdminActionQueues,
  type AdminActionQueue,
} from '@/features/admin-shell/hooks/use-admin-action-queues';
import {
  usePendingWithdrawals,
  useRecentAuditLogs,
  useRecentPayments,
  useRecentWebhookLogs,
} from '../hooks/useDashboardData';

type PaymentHistoryItem = components['schemas']['PaymentHistoryItem'];
type WithdrawalResponse = components['schemas']['WithdrawalResponse'];
type AuditLogResponse = components['schemas']['AuditLogResponse'];
type WebhookLogResponse = components['schemas']['WebhookLogResponse'];

function formatCurrencyAmount(amount: number, currency: string) {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(amount);
}

function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return '--';
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function humanizeToken(value: string | null | undefined) {
  if (!value) {
    return 'Unknown';
  }

  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function shortId(value: string | null | undefined) {
  if (!value) {
    return '--';
  }

  return value.slice(0, 8);
}

function readinessToneClass(readinessTone: 'strong' | 'partial' | 'blocked') {
  if (readinessTone === 'strong') {
    return 'border-matrix-green/35 bg-matrix-green/10 text-matrix-green';
  }
  if (readinessTone === 'partial') {
    return 'border-neon-cyan/35 bg-neon-cyan/10 text-neon-cyan';
  }
  return 'border-neon-pink/35 bg-neon-pink/10 text-neon-pink';
}

const SUPPORT_SECTION_CARD_OVERVIEW = {
  availableNow: ['inbox', 'conversation', 'internalNotes'],
  nextModules: ['securityGate', 'qaEvidence', 'partnerWorkspaceSupport'],
  readinessTone: 'partial',
} as const;

const MESSAGING_SECTION_CARD_OVERVIEW = {
  availableNow: ['privateInbox', 'assignment', 'internalNotes', 'presence'],
  nextModules: ['securityReview', 'playwrightEvidence', 'notificationBadges'],
  readinessTone: 'partial',
} as const;

function getSectionCardOverview(item: AdminNavItem) {
  if (item.href === '/support') {
    return SUPPORT_SECTION_CARD_OVERVIEW;
  }
  if (item.href === '/messaging') {
    return MESSAGING_SECTION_CARD_OVERVIEW;
  }

  const slug = item.href.slice(1) as AdminSectionSlug;
  return ADMIN_SECTION_OVERVIEWS[slug];
}

function resolveSectionCards(
  role: string | null | undefined,
): { item: AdminNavItem; resolvedItem: ResolvedAdminNavItem }[] {
  const resolvedItemsByHref = new Map(
    resolveAdminNavigationGroups(role)
      .flatMap((group) => group.items)
      .map((item) => [item.href, item]),
  );

  return ADMIN_NAV_ITEMS
    .filter((item) => item.href !== '/dashboard')
    .flatMap((item) => {
      const resolvedItem = resolvedItemsByHref.get(item.href);

      return resolvedItem ? [{ item, resolvedItem }] : [];
    });
}

function statusToneClass(status: string) {
  const normalized = status.toLowerCase();

  if (normalized === 'completed' || normalized === 'approved' || normalized === 'valid') {
    return 'border-matrix-green/35 bg-matrix-green/10 text-matrix-green';
  }

  if (normalized === 'failed' || normalized === 'rejected' || normalized === 'invalid') {
    return 'border-neon-pink/35 bg-neon-pink/10 text-neon-pink';
  }

  return 'border-neon-cyan/35 bg-neon-cyan/10 text-neon-cyan';
}

function queueToneClass(queue: AdminActionQueue) {
  if (queue.tone === 'warning') {
    return 'border-amber-300/35 bg-amber-300/10 text-amber-200';
  }

  if (queue.tone === 'danger') {
    return 'border-neon-pink/35 bg-neon-pink/10 text-neon-pink';
  }

  if (queue.tone === 'success') {
    return 'border-matrix-green/35 bg-matrix-green/10 text-matrix-green';
  }

  return 'border-grid-line/25 bg-terminal-bg/60 text-muted-foreground';
}

function riskLabelKey(risk: 'danger' | 'read' | 'write') {
  if (risk === 'danger') return 'workspaceRisk.danger';
  if (risk === 'write') return 'workspaceRisk.write';
  return 'workspaceRisk.read';
}

function formatRole(role: string | null | undefined) {
  return role ? role.replace(/_/g, ' ').toUpperCase() : 'UNASSIGNED';
}

interface PanelShellProps {
  title: string;
  description: string;
  icon: ComponentType<{ className?: string }>;
  badge?: string;
  className?: string;
  children: ReactNode;
}

function PanelShell({
  title,
  description,
  icon: Icon,
  badge,
  className,
  children,
}: PanelShellProps) {
  return (
    <article
      className={cn(
        'rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] backdrop-blur',
        className,
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
              <Icon className="h-4 w-4" />
            </div>
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {title}
            </h2>
          </div>
          <p className="max-w-2xl text-sm font-mono leading-6 text-muted-foreground">
            {description}
          </p>
        </div>

        {badge ? (
          <span className="inline-flex items-center rounded-full border border-grid-line/20 bg-terminal-bg/60 px-3 py-1 text-[11px] font-mono uppercase tracking-[0.2em] text-neon-cyan">
            {badge}
          </span>
        ) : null}
      </div>

      <div className="mt-5">{children}</div>
    </article>
  );
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
      {label}
    </div>
  );
}

function ErrorState({ label }: { label: string }) {
  return (
    <div className="rounded-2xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-8 text-center text-sm font-mono text-neon-pink">
      {label}
    </div>
  );
}

function LoadingList() {
  return (
    <div className="grid gap-3">
      {Array.from({ length: 3 }).map((_, index) => (
        <div
          key={index}
          className="h-20 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/50"
        />
      ))}
    </div>
  );
}

function SectionCards() {
  const t = useTranslations('Dashboard');
  const navT = useTranslations('Navigation');
  const user = useAuthStore((state) => state.user);
  const sectionCards = resolveSectionCards(user?.role);

  return (
    <div className="grid gap-3 md:grid-cols-2">
      {sectionCards.map(({ item, resolvedItem }) => {
        const overview = getSectionCardOverview(item);
        const Icon = item.icon;
        const isEnabled = resolvedItem.accessState === 'enabled';
        const cardClassName = cn(
          'rounded-2xl border p-4 transition-colors',
          isEnabled
            ? 'group border-grid-line/20 bg-terminal-bg/45 hover:border-neon-cyan/35 hover:bg-terminal-bg/60 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan'
            : 'border-grid-line/15 bg-terminal-bg/25 opacity-70',
        );
        const content = (
          <>
            <div className="flex items-start justify-between gap-3">
              <div
                className={cn(
                  'flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-surface/70',
                  isEnabled ? 'text-neon-cyan' : 'text-muted-foreground',
                )}
              >
                <Icon className="h-4 w-4" />
              </div>
              <span
                className={cn(
                  'inline-flex rounded-full border px-2.5 py-1 text-[10px] font-mono uppercase tracking-[0.18em]',
                  readinessToneClass(overview.readinessTone),
                )}
              >
                {t(`sectionReadiness.${overview.readinessTone}`)}
              </span>
            </div>

            <div className="mt-4 space-y-2">
              <h3 className="text-sm font-display uppercase tracking-[0.2em] text-white">
                {navT(item.labelKey)}
              </h3>
              <p className="text-sm font-mono leading-6 text-muted-foreground">
                {navT(item.hintKey)}
              </p>
            </div>

            <div className="mt-4 border-t border-grid-line/20 pt-3 text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
              <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                <span>
                  {overview.availableNow.length} {t('sectionSignalsReady')}
                </span>
                <span>
                  {overview.nextModules.length} {t('sectionModulesNext')}
                </span>
                {isEnabled ? (
                  <ArrowUpRight className="h-3.5 w-3.5 text-neon-cyan transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                ) : null}
              </div>
              {!isEnabled ? (
                <span className="mt-2 block w-full max-w-full wrap-normal rounded-xl border border-grid-line/20 bg-terminal-surface/40 px-2 py-1.5 text-left text-[10px] leading-5 text-muted-foreground">
                  {navT('unavailableForRole')}
                </span>
              ) : null}
            </div>
          </>
        );

        if (!isEnabled) {
          return (
            <article
              key={item.href}
              data-access-state={resolvedItem.accessState}
              className={cardClassName}
              title={navT('unavailableForRole')}
            >
              {content}
            </article>
          );
        }

        return (
          <Link
            key={item.href}
            href={item.href}
            className={cardClassName}
          >
            {content}
          </Link>
        );
      })}
    </div>
  );
}

function ActionQueuesPanel() {
  const t = useTranslations('Dashboard');
  const { queues } = useAdminActionQueues();

  return (
    <div className="grid gap-3 md:grid-cols-2">
      {queues.map((queue) => {
        const stateLabel = t(`queueStates.${queue.state}`);
        const countLabel =
          queue.count === null ? '--' : formatAdminQueueBadge(queue.count);

        return (
          <article
            key={queue.id}
            className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="text-sm font-display uppercase tracking-[0.2em] text-white">
                  {t(queue.titleKey)}
                </h3>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {t(queue.descriptionKey)}
                </p>
              </div>

              <span
                className={cn(
                  'inline-flex rounded-full border px-2.5 py-1 text-[10px] font-mono uppercase tracking-[0.18em]',
                  queueToneClass(queue),
                )}
              >
                {stateLabel}
              </span>
            </div>

            <div className="mt-5 flex items-end justify-between gap-4">
              <div>
                <p className="text-3xl font-display tracking-[0.14em] text-white">
                  {countLabel}
                </p>
                <p className="mt-1 text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t(queue.metricKey)}
                </p>
              </div>

              {queue.state === 'unavailable' ? (
                <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('queueUnavailableForRole')}
                </span>
              ) : (
                <Link
                  href={queue.href}
                  className="inline-flex items-center gap-2 rounded-xl border border-grid-line/20 bg-terminal-surface/70 px-3 py-2 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:border-neon-cyan/35 hover:bg-neon-cyan/10 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan"
                >
                  {t('openQueue')}
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </Link>
              )}
            </div>
          </article>
        );
      })}
    </div>
  );
}

function MyWorkspacePanel() {
  const t = useTranslations('Dashboard');
  const navT = useTranslations('Navigation');
  const user = useAuthStore((state) => state.user);
  const role = user?.role;
  const groups = resolveAdminNavigationGroups(role);
  const items = groups.flatMap((group) => group.items);
  const enabledItems = items.filter((item) => item.accessState === 'enabled');
  const restrictedItems = items.filter((item) => item.accessState === 'disabled');
  const permissions = getAdminRolePermissions(role) as readonly AdminPermission[];
  const writeActionCount = enabledItems.filter(
    (item) => item.risk === 'write' || item.risk === 'danger',
  ).length;
  const readActionCount = enabledItems.length - writeActionCount;

  return (
    <div className="grid gap-4">
      <div className="grid gap-3 sm:grid-cols-2">
        {[
          {
            label: t('workspaceRoleLabel'),
            value: formatRole(role),
          },
          {
            label: t('workspaceEnabledActions'),
            value: String(enabledItems.length),
          },
          {
            label: t('workspaceRestrictedActions'),
            value: String(restrictedItems.length),
          },
          {
            label: t('workspacePermissionCount'),
            value: String(permissions.length),
          },
        ].map((stat) => (
          <div
            key={stat.label}
            className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
          >
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
              {stat.label}
            </p>
            <p className="mt-2 break-words text-lg font-display tracking-[0.14em] text-white">
              {stat.value}
            </p>
          </div>
        ))}
      </div>

      <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('workspaceAvailableNow')}
          </p>
          <div className="flex flex-wrap gap-2 text-[10px] font-mono uppercase tracking-[0.18em]">
            <span className="rounded-full border border-matrix-green/35 bg-matrix-green/10 px-2.5 py-1 text-matrix-green">
              {readActionCount} {t('workspaceReadActions')}
            </span>
            <span className="rounded-full border border-amber-300/35 bg-amber-300/10 px-2.5 py-1 text-amber-200">
              {writeActionCount} {t('workspaceWriteActions')}
            </span>
          </div>
        </div>

        {enabledItems.length ? (
          <ul className="mt-4 grid gap-2">
            {enabledItems.slice(0, 5).map((item) => {
              const Icon = item.icon;

              return (
                <li key={item.id}>
                  <Link
                    href={item.href}
                    className="group flex items-center justify-between gap-3 rounded-xl border border-grid-line/20 bg-terminal-surface/50 px-3 py-2 transition-colors hover:border-neon-cyan/35 hover:bg-neon-cyan/10 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan"
                  >
                    <span className="flex min-w-0 items-center gap-3">
                      <Icon className="h-4 w-4 shrink-0 text-neon-cyan" />
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-mono text-white">
                          {navT(item.labelKey)}
                        </span>
                        <span className="mt-0.5 block truncate text-[10px] font-mono uppercase tracking-[0.16em] text-muted-foreground">
                          {t(riskLabelKey(item.risk ?? 'read'))}
                        </span>
                      </span>
                    </span>
                    <ArrowUpRight className="h-3.5 w-3.5 shrink-0 text-neon-cyan transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                  </Link>
                </li>
              );
            })}
          </ul>
        ) : (
          <EmptyState label={t('workspaceNoActions')} />
        )}
      </div>
    </div>
  );
}

function WithdrawalQueue({
  data,
  isPending,
  isError,
}: {
  data: WithdrawalResponse[] | undefined;
  isPending: boolean;
  isError: boolean;
}) {
  const t = useTranslations('Dashboard');

  if (isPending) {
    return <LoadingList />;
  }

  if (isError) {
    return <ErrorState label={t('errors.load')} />;
  }

  if (!data || data.length === 0) {
    return <EmptyState label={t('empty.withdrawals')} />;
  }

  return (
    <ul className="grid gap-3">
      {data.slice(0, 5).map((withdrawal) => (
        <li
          key={withdrawal.id}
          className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-lg font-display tracking-[0.14em] text-white">
                {formatCurrencyAmount(withdrawal.amount, withdrawal.currency)}
              </p>
              <p className="mt-1 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('labels.method')}: {humanizeToken(withdrawal.method)}
              </p>
            </div>

            <span
              className={cn(
                'inline-flex rounded-full border px-2.5 py-1 text-[10px] font-mono uppercase tracking-[0.18em]',
                statusToneClass(withdrawal.status),
              )}
            >
              {humanizeToken(withdrawal.status)}
            </span>
          </div>

          <div className="mt-3 flex flex-wrap gap-3 text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            <span>{formatDateTime(withdrawal.created_at)}</span>
            <span>#{shortId(withdrawal.id)}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}

function PaymentsList({
  data,
  isPending,
  isError,
}: {
  data: PaymentHistoryItem[] | undefined;
  isPending: boolean;
  isError: boolean;
}) {
  const t = useTranslations('Dashboard');

  if (isPending) {
    return <LoadingList />;
  }

  if (isError) {
    return <ErrorState label={t('errors.load')} />;
  }

  if (!data || data.length === 0) {
    return <EmptyState label={t('empty.payments')} />;
  }

  return (
    <ul className="grid gap-3">
      {data.map((payment) => (
        <li
          key={payment.id}
          className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-lg font-display tracking-[0.14em] text-white">
                {formatCurrencyAmount(payment.amount, payment.currency)}
              </p>
              <p className="mt-1 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('labels.provider')}: {humanizeToken(payment.provider)}
              </p>
            </div>

            <span
              className={cn(
                'inline-flex rounded-full border px-2.5 py-1 text-[10px] font-mono uppercase tracking-[0.18em]',
                statusToneClass(payment.status),
              )}
            >
              {humanizeToken(payment.status)}
            </span>
          </div>

          <div className="mt-3 flex flex-wrap gap-3 text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            <span>{formatDateTime(payment.created_at)}</span>
            <span>#{shortId(payment.id)}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}

function AuditStream({
  data,
  isPending,
  isError,
}: {
  data: AuditLogResponse[] | undefined;
  isPending: boolean;
  isError: boolean;
}) {
  const t = useTranslations('Dashboard');

  if (isPending) {
    return <LoadingList />;
  }

  if (isError) {
    return <ErrorState label={t('errors.load')} />;
  }

  if (!data || data.length === 0) {
    return <EmptyState label={t('empty.audit')} />;
  }

  return (
    <ul className="grid gap-3">
      {data.map((entry) => (
        <li
          key={entry.id}
          className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-2">
              <p className="text-sm font-display uppercase tracking-[0.18em] text-white">
                {humanizeToken(entry.action)}
              </p>
              <p className="text-sm font-mono leading-6 text-muted-foreground">
                {entry.entity_type ? `${humanizeToken(entry.entity_type)} / ` : ''}
                {entry.entity_id ?? t('labels.unknown')}
              </p>
            </div>

            <span className="inline-flex rounded-full border border-grid-line/20 bg-terminal-surface/60 px-2.5 py-1 text-[10px] font-mono uppercase tracking-[0.18em] text-neon-cyan">
              {entry.admin_id ? `#${shortId(entry.admin_id)}` : t('labels.unassigned')}
            </span>
          </div>

          <div className="mt-3 flex flex-wrap gap-3 text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            <span>{formatDateTime(entry.created_at)}</span>
            <span>{entry.ip_address ?? t('labels.unknown')}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}

function WebhookStream({
  data,
  isPending,
  isError,
}: {
  data: WebhookLogResponse[] | undefined;
  isPending: boolean;
  isError: boolean;
}) {
  const t = useTranslations('Dashboard');

  if (isPending) {
    return <LoadingList />;
  }

  if (isError) {
    return <ErrorState label={t('errors.load')} />;
  }

  if (!data || data.length === 0) {
    return <EmptyState label={t('empty.webhooks')} />;
  }

  return (
    <ul className="grid gap-3 xl:grid-cols-2">
      {data.map((entry) => {
        const validity = entry.is_valid === false ? 'invalid' : 'valid';
        return (
          <li
            key={entry.id}
            className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-2">
                <p className="text-sm font-display uppercase tracking-[0.18em] text-white">
                  {humanizeToken(entry.source)}
                </p>
                <p className="text-sm font-mono leading-6 text-muted-foreground">
                  {entry.event_type ?? t('labels.unknown')}
                </p>
              </div>

              <span
                className={cn(
                  'inline-flex rounded-full border px-2.5 py-1 text-[10px] font-mono uppercase tracking-[0.18em]',
                  statusToneClass(validity),
                )}
              >
                {t(`labels.${validity}`)}
              </span>
            </div>

            <div className="mt-3 space-y-2 text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
              <p>{formatDateTime(entry.created_at)}</p>
              <p>
                {t('labels.processedAt')}: {formatDateTime(entry.processed_at)}
              </p>
              <p className="break-words text-foreground/80">
                {entry.error_message ?? t('labels.noError')}
              </p>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

/**
 * Detailed operational panels below the KPI strip.
 */
export function CommandCenterPanels() {
  const t = useTranslations('Dashboard');
  const pendingWithdrawals = usePendingWithdrawals();
  const recentPayments = useRecentPayments();
  const auditLogs = useRecentAuditLogs();
  const webhookLogs = useRecentWebhookLogs();

  const pendingAmount = pendingWithdrawals.data?.reduce(
    (sum, withdrawal) => sum + withdrawal.amount,
    0,
  );
  const invalidWebhookCount = webhookLogs.data?.filter((entry) => entry.is_valid === false).length ?? 0;

  return (
    <section
      aria-label={t('opsGridLabel')}
      className="grid gap-6 xl:grid-cols-12"
    >
      <PanelShell
        title={t('actionQueuesTitle')}
        description={t('actionQueuesDescription')}
        icon={Inbox}
        className="xl:col-span-7"
      >
        <ActionQueuesPanel />
      </PanelShell>

      <PanelShell
        title={t('myWorkspaceTitle')}
        description={t('myWorkspaceDescription')}
        icon={UserRoundCheck}
        badge={t('myWorkspaceBadge')}
        className="xl:col-span-5"
      >
        <MyWorkspacePanel />
      </PanelShell>

      <PanelShell
        title={t('sectionMapTitle')}
        description={t('sectionMapDescription')}
        icon={CheckCircle2}
        className="xl:col-span-5"
      >
        <SectionCards />
      </PanelShell>

      <PanelShell
        title={t('withdrawalsTitle')}
        description={t('withdrawalsDescription')}
        icon={ReceiptText}
        badge={
          pendingWithdrawals.data
            ? `${pendingWithdrawals.data.length} ${t('labels.items')} / ${formatCurrencyAmount(pendingAmount ?? 0, 'USD')}`
            : undefined
        }
        className="xl:col-span-7"
      >
        <WithdrawalQueue
          data={pendingWithdrawals.data}
          isPending={pendingWithdrawals.isPending}
          isError={pendingWithdrawals.isError}
        />
      </PanelShell>

      <PanelShell
        title={t('paymentsTitle')}
        description={t('paymentsDescription')}
        icon={Landmark}
        className="xl:col-span-6"
      >
        <PaymentsList
          data={recentPayments.data}
          isPending={recentPayments.isPending}
          isError={recentPayments.isError}
        />
      </PanelShell>

      <PanelShell
        title={t('auditTitle')}
        description={t('auditDescription')}
        icon={ScrollText}
        className="xl:col-span-6"
      >
        <AuditStream
          data={auditLogs.data}
          isPending={auditLogs.isPending}
          isError={auditLogs.isError}
        />
      </PanelShell>

      <PanelShell
        title={t('webhooksTitle')}
        description={t('webhooksDescription')}
        icon={Webhook}
        badge={`${invalidWebhookCount} ${t('labels.invalid')}`}
        className="xl:col-span-12"
      >
        <WebhookStream
          data={webhookLogs.data}
          isPending={webhookLogs.isPending}
          isError={webhookLogs.isError}
        />
      </PanelShell>
    </section>
  );
}
