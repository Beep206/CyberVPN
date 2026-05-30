'use client';

import { useDeferredValue, useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  FileText,
  Inbox,
  LockKeyhole,
  MessageSquareReply,
  NotebookPen,
  RefreshCw,
  Search,
  UserRoundCheck,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Link, useRouter } from '@/i18n/navigation';
import { authApi } from '@/lib/api/auth';
import {
  SUPPORT_TICKET_CATEGORIES,
  SUPPORT_TICKET_PRIORITIES,
  SUPPORT_TICKET_SOURCES,
  SUPPORT_TICKET_STATUSES,
  supportApi,
  type AdminSupportTicketListParams,
  type AdminSupportTicketUpdateRequest,
  type SupportTicketCategory,
  type SupportTicketDetail,
  type SupportTicketPriority,
  type SupportTicketSource,
  type SupportTicketStatus,
  type SupportTicketSummary,
} from '@/lib/api/support';
import { cn } from '@/lib/utils';
import { hasAdminPermission } from '@/shared/lib/admin-rbac';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';
import { SupportPageShell } from '@/features/support/components/support-page-shell';
import { SupportStatusChip } from '@/features/support/components/support-status-chip';
import {
  formatSupportDateTime,
  getSupportErrorMessage,
  humanizeSupportToken,
  shortSupportId,
  supportPriorityTone,
  supportStatusTone,
  supportVisibilityTone,
} from '@/features/support/lib/formatting';

type SupportTranslate = (key: string, values?: Record<string, string | number>) => string;
type StatusFilter = 'all' | SupportTicketStatus;
type CategoryFilter = 'all' | SupportTicketCategory;
type PriorityFilter = 'all' | SupportTicketPriority;
type SourceFilter = 'all' | SupportTicketSource;
type AssignmentFilter = 'all' | 'mine' | 'unassigned';
type UpdateMutationInput = {
  feedbackKey: string;
  payload: AdminSupportTicketUpdateRequest;
};
type SupportSearchParams = Record<string, string | string[] | undefined>;
type SupportUrlQuery = Record<string, string>;
type SupportInitialFilters = {
  assignmentFilter: AssignmentFilter;
  categoryFilter: CategoryFilter;
  priorityFilter: PriorityFilter;
  search: string;
  sourceFilter: SourceFilter;
  statusFilter: StatusFilter;
};

const MESSAGE_MAX_LENGTH = 4000;
const SUPPORT_LIST_LIMIT = 50;
const ASSIGNMENT_FILTERS = ['all', 'mine', 'unassigned'] as const;
const STATUS_FILTERS = ['all', ...SUPPORT_TICKET_STATUSES] as const;
const CATEGORY_FILTERS = ['all', ...SUPPORT_TICKET_CATEGORIES] as const;
const PRIORITY_FILTERS = ['all', ...SUPPORT_TICKET_PRIORITIES] as const;
const SOURCE_FILTERS = ['all', ...SUPPORT_TICKET_SOURCES] as const;
const CONTROL_FOCUS_CLASS =
  'outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg';
const AMBER_FOCUS_CLASS =
  'outline-hidden focus-visible:ring-2 focus-visible:ring-amber-300 focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg';

function safeTicketRoute(publicId: string) {
  return `/support/${encodeURIComponent(publicId)}`;
}

function readSearchParam(searchParams: SupportSearchParams | undefined, key: string) {
  const value = searchParams?.[key];
  return Array.isArray(value) ? value[0] : value;
}

function readAllowedValue<T extends string>(
  value: string | undefined,
  allowed: readonly T[],
  fallback: T,
): T {
  return value && allowed.includes(value as T) ? (value as T) : fallback;
}

function getInitialFilters(searchParams: SupportSearchParams | undefined): SupportInitialFilters {
  return {
    assignmentFilter: readAllowedValue(
      readSearchParam(searchParams, 'assignment'),
      ASSIGNMENT_FILTERS,
      'all',
    ),
    categoryFilter: readAllowedValue(
      readSearchParam(searchParams, 'category'),
      CATEGORY_FILTERS,
      'all',
    ),
    priorityFilter: readAllowedValue(
      readSearchParam(searchParams, 'priority'),
      PRIORITY_FILTERS,
      'all',
    ),
    search: readSearchParam(searchParams, 'q')?.slice(0, 120) ?? '',
    sourceFilter: readAllowedValue(
      readSearchParam(searchParams, 'source'),
      SOURCE_FILTERS,
      'all',
    ),
    statusFilter: readAllowedValue(
      readSearchParam(searchParams, 'status'),
      STATUS_FILTERS,
      'all',
    ),
  };
}

function buildSupportUrlQuery({
  assignmentFilter,
  categoryFilter,
  priorityFilter,
  search,
  sourceFilter,
  statusFilter,
}: SupportInitialFilters): SupportUrlQuery {
  const query: SupportUrlQuery = {};
  const trimmedSearch = search.trim();

  if (trimmedSearch) {
    query.q = trimmedSearch;
  }
  if (statusFilter !== 'all') {
    query.status = statusFilter;
  }
  if (categoryFilter !== 'all') {
    query.category = categoryFilter;
  }
  if (priorityFilter !== 'all') {
    query.priority = priorityFilter;
  }
  if (sourceFilter !== 'all') {
    query.source = sourceFilter;
  }
  if (assignmentFilter !== 'all') {
    query.assignment = assignmentFilter;
  }

  return query;
}

function buildSupportHref(pathname: string, query: SupportUrlQuery) {
  const searchParams = new URLSearchParams(query);
  const searchString = searchParams.toString();
  return searchString ? `${pathname}?${searchString}` : pathname;
}

function buildListParams({
  assignedAdminId,
  categoryFilter,
  deferredSearch,
  priorityFilter,
  sourceFilter,
  statusFilter,
}: {
  assignedAdminId: string | undefined;
  categoryFilter: CategoryFilter;
  deferredSearch: string;
  priorityFilter: PriorityFilter;
  sourceFilter: SourceFilter;
  statusFilter: StatusFilter;
}): AdminSupportTicketListParams {
  return {
    assigned_admin_id: assignedAdminId,
    category: categoryFilter === 'all' ? undefined : categoryFilter,
    limit: SUPPORT_LIST_LIMIT,
    priority: priorityFilter === 'all' ? undefined : priorityFilter,
    query: deferredSearch.trim() || undefined,
    source: sourceFilter === 'all' ? undefined : sourceFilter,
    status: statusFilter === 'all' ? undefined : statusFilter,
  };
}

function validateMessage(
  value: string,
  t: SupportTranslate,
) {
  const trimmed = value.trim();
  if (!trimmed) {
    throw new Error(t('feedback.messageRequired'));
  }
  if (trimmed.length > MESSAGE_MAX_LENGTH) {
    throw new Error(t('feedback.messageTooLong', { count: MESSAGE_MAX_LENGTH }));
  }
  return trimmed;
}

function countByStatus(tickets: readonly SupportTicketSummary[], status: SupportTicketStatus) {
  return tickets.filter((ticket) => ticket.status === status).length;
}

function PermissionDeniedState({ t }: { t: SupportTranslate }) {
  return (
    <div className="rounded-2xl border border-neon-pink/30 bg-neon-pink/10 p-6">
      <div className="flex items-start gap-4">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-neon-pink/30 bg-terminal-bg/60 text-neon-pink">
          <LockKeyhole className="h-5 w-5" />
        </div>
        <div>
          <h2 className="text-sm font-display uppercase tracking-[0.22em] text-white">
            {t('permissionDenied.title')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('permissionDenied.description')}
          </p>
        </div>
      </div>
    </div>
  );
}

function LoadingRows() {
  return (
    <div className="grid gap-3" data-testid="support-loading-state">
      {Array.from({ length: 6 }).map((_, index) => (
        <div
          key={index}
          className="h-20 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
        />
      ))}
    </div>
  );
}

function TicketOwnerMeta({
  ticket,
  t,
}: {
  t: SupportTranslate;
  ticket: SupportTicketSummary;
}) {
  const ownerId = ticket.owner_type === 'partner'
    ? ticket.partner_workspace_id
    : ticket.customer_account_id;

  return (
    <div className="grid gap-2 text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
      <span>{t(`owner.${ticket.owner_type}`)}</span>
      <span>{t('list.safeOwnerRef', { id: shortSupportId(ownerId) })}</span>
    </div>
  );
}

function TicketList({
  activeTicketRef,
  locale,
  onSelect,
  query,
  t,
  tickets,
}: {
  activeTicketRef: string | null;
  locale: string;
  onSelect: (ticketRef: string) => void;
  query: SupportUrlQuery;
  t: SupportTranslate;
  tickets: readonly SupportTicketSummary[];
}) {
  return (
    <>
      <ul
        aria-label={t('list.mobileListLabel')}
        className="grid gap-3 md:hidden"
        data-testid="support-mobile-ticket-list"
      >
        {tickets.map((ticket) => {
          const isActive = activeTicketRef === ticket.public_id || activeTicketRef === ticket.id;

          return (
            <li
              key={ticket.id}
              className={cn(
                'rounded-2xl border border-grid-line/20 bg-terminal-bg/55 p-4 [content-visibility:auto] [contain-intrinsic-size:auto_220px]',
                isActive ? 'border-amber-300/45 bg-amber-300/10' : undefined,
              )}
            >
              <button
                type="button"
                aria-current={isActive ? 'true' : undefined}
                aria-label={t('list.selectTicket', { publicId: ticket.public_id })}
                onClick={() => onSelect(ticket.public_id)}
                className={cn(
                  'block w-full rounded-xl p-1 text-left',
                  CONTROL_FOCUS_CLASS,
                )}
              >
                <span className="block break-words font-display uppercase tracking-[0.14em] text-white">
                  {ticket.subject}
                </span>
                <span className="mt-1 block text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {ticket.public_id}
                </span>
                <span className="mt-2 block line-clamp-2 text-sm font-mono normal-case tracking-normal text-muted-foreground">
                  {ticket.last_message_preview || t('list.noPreview')}
                </span>
              </button>

              <div className="mt-4 flex flex-wrap gap-2">
                <SupportStatusChip
                  label={humanizeSupportToken(ticket.status)}
                  tone={supportStatusTone(ticket.status)}
                />
                <SupportStatusChip
                  label={humanizeSupportToken(ticket.priority)}
                  tone={supportPriorityTone(ticket.priority)}
                />
                <SupportStatusChip
                  label={humanizeSupportToken(ticket.category)}
                  tone="neutral"
                />
              </div>

              <div className="mt-4 grid gap-3 text-sm">
                <TicketOwnerMeta ticket={ticket} t={t} />
                <p className="font-mono text-muted-foreground">
                  {t('list.table.updated')}: {formatSupportDateTime(ticket.updated_at, locale)}
                </p>
                <Link
                  href={buildSupportHref(safeTicketRoute(ticket.public_id), query)}
                  aria-label={t('list.openRoute', { publicId: ticket.public_id })}
                  className={cn(
                    'inline-flex w-fit rounded-xl border border-grid-line/30 bg-terminal-bg/60 px-3 py-2 text-xs font-mono uppercase tracking-[0.16em] text-neon-cyan transition-colors hover:border-neon-cyan/40 hover:text-white',
                    CONTROL_FOCUS_CLASS,
                  )}
                >
                  {t('list.open')}
                </Link>
              </div>
            </li>
          );
        })}
      </ul>

      <div className="hidden md:block">
        <Table>
          <caption className="sr-only">{t('list.tableCaption')}</caption>
          <TableHeader>
            <TableRow>
              <TableHead>{t('list.table.ticket')}</TableHead>
              <TableHead>{t('list.table.state')}</TableHead>
              <TableHead>{t('list.table.owner')}</TableHead>
              <TableHead>{t('list.table.updated')}</TableHead>
              <TableHead>{t('common.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tickets.map((ticket) => {
              const isActive = activeTicketRef === ticket.public_id || activeTicketRef === ticket.id;

              return (
                <TableRow
                  key={ticket.id}
                  className={isActive ? 'border-l-2 border-l-amber-300 bg-amber-300/5' : undefined}
                >
                  <TableCell>
                    <button
                      type="button"
                      aria-current={isActive ? 'true' : undefined}
                      aria-label={t('list.selectTicket', { publicId: ticket.public_id })}
                      onClick={() => onSelect(ticket.public_id)}
                      className={cn(
                        'block max-w-sm rounded-xl p-1 text-left',
                        CONTROL_FOCUS_CLASS,
                      )}
                    >
                      <span className="block break-words font-display uppercase tracking-[0.14em] text-white">
                        {ticket.subject}
                      </span>
                      <span className="mt-1 block text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {ticket.public_id}
                      </span>
                      <span className="mt-2 block line-clamp-2 text-sm font-mono normal-case tracking-normal text-muted-foreground">
                        {ticket.last_message_preview || t('list.noPreview')}
                      </span>
                    </button>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-2">
                      <SupportStatusChip
                        label={humanizeSupportToken(ticket.status)}
                        tone={supportStatusTone(ticket.status)}
                      />
                      <SupportStatusChip
                        label={humanizeSupportToken(ticket.priority)}
                        tone={supportPriorityTone(ticket.priority)}
                      />
                      <SupportStatusChip
                        label={humanizeSupportToken(ticket.category)}
                        tone="neutral"
                      />
                    </div>
                  </TableCell>
                  <TableCell>
                    <TicketOwnerMeta ticket={ticket} t={t} />
                  </TableCell>
                  <TableCell>{formatSupportDateTime(ticket.updated_at, locale)}</TableCell>
                  <TableCell>
                    <Link
                      href={buildSupportHref(safeTicketRoute(ticket.public_id), query)}
                      aria-label={t('list.openRoute', { publicId: ticket.public_id })}
                      className={cn(
                        'inline-flex rounded-xl border border-grid-line/30 bg-terminal-bg/60 px-3 py-2 text-xs font-mono uppercase tracking-[0.16em] text-neon-cyan transition-colors hover:border-neon-cyan/40 hover:text-white',
                        CONTROL_FOCUS_CLASS,
                      )}
                    >
                      {t('list.open')}
                    </Link>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </>
  );
}

function DetailSkeleton() {
  return (
    <div className="grid gap-4" data-testid="support-detail-loading-state">
      <div className="h-24 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45" />
      <div className="h-72 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45" />
      <div className="h-48 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45" />
    </div>
  );
}

function ConversationHeader({
  locale,
  t,
  ticket,
}: {
  locale: string;
  t: SupportTranslate;
  ticket: SupportTicketDetail;
}) {
  return (
    <header className="rounded-2xl border border-grid-line/20 bg-terminal-bg/55 p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-mono uppercase tracking-[0.22em] text-amber-300">
            {ticket.public_id}
          </p>
          <h2 className="mt-2 break-words text-xl font-display uppercase tracking-[0.16em] text-white">
            {ticket.subject}
          </h2>
          <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
            {t('detail.updatedAt', {
              value: formatSupportDateTime(ticket.updated_at, locale),
            })}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <SupportStatusChip
            label={humanizeSupportToken(ticket.status)}
            tone={supportStatusTone(ticket.status)}
          />
          <SupportStatusChip
            label={humanizeSupportToken(ticket.priority)}
            tone={supportPriorityTone(ticket.priority)}
          />
          <SupportStatusChip
            label={humanizeSupportToken(ticket.source)}
            tone="info"
          />
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-grid-line/20 bg-terminal-surface/35 p-3">
          <p className="text-[11px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
            {t('detail.owner')}
          </p>
          <p className="mt-2 break-all text-sm font-mono text-white">
            {t(`owner.${ticket.owner_type}`)}
          </p>
        </div>
        <div className="rounded-xl border border-grid-line/20 bg-terminal-surface/35 p-3">
          <p className="text-[11px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
            {t('detail.customerRef')}
          </p>
          <p className="mt-2 break-all text-sm font-mono text-white">
            {shortSupportId(ticket.customer_account_id)}
          </p>
        </div>
        <div className="rounded-xl border border-grid-line/20 bg-terminal-surface/35 p-3">
          <p className="text-[11px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
            {t('detail.partnerRef')}
          </p>
          <p className="mt-2 break-all text-sm font-mono text-white">
            {shortSupportId(ticket.partner_workspace_id)}
          </p>
        </div>
      </div>
    </header>
  );
}

function TimelinePanel({
  locale,
  t,
  ticket,
}: {
  locale: string;
  t: SupportTranslate;
  ticket: SupportTicketDetail;
}) {
  return (
    <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
          <MessageSquareReply className="h-4 w-4" />
        </div>
        <div>
          <h3 className="text-sm font-display uppercase tracking-[0.22em] text-white">
            {t('detail.conversationTitle')}
          </h3>
          <p className="mt-1 text-sm font-mono text-muted-foreground">
            {t('detail.conversationDescription')}
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-4">
        {ticket.messages.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
            {t('detail.noMessages')}
          </div>
        ) : (
          ticket.messages.map((message) => (
            <article
              key={message.id}
              data-testid={
                message.visibility === 'internal'
                  ? 'support-internal-message'
                  : 'support-public-message'
              }
              className={
                message.visibility === 'internal'
                  ? 'rounded-2xl border border-amber-300/25 bg-amber-300/10 p-4'
                  : 'rounded-2xl border border-neon-cyan/20 bg-terminal-bg/45 p-4'
              }
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap gap-2">
                  <SupportStatusChip
                    label={humanizeSupportToken(message.author_type)}
                    tone={message.author_type === 'admin' ? 'info' : 'neutral'}
                  />
                  <SupportStatusChip
                    label={humanizeSupportToken(message.visibility)}
                    tone={supportVisibilityTone(message.visibility)}
                  />
                </div>
                <p className="text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                  {formatSupportDateTime(message.created_at, locale)}
                </p>
              </div>
              <p className="mt-3 whitespace-pre-wrap text-sm font-mono leading-6 text-foreground/90">
                {message.body}
              </p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}

function PublicPreviewPanel({
  t,
  ticket,
}: {
  t: SupportTranslate;
  ticket: SupportTicketDetail;
}) {
  const publicMessages = ticket.messages.filter((message) => message.visibility === 'public');
  const internalCount = ticket.messages.length - publicMessages.length;

  return (
    <section className="rounded-2xl border border-neon-cyan/20 bg-neon-cyan/10 p-5">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-neon-cyan/25 bg-terminal-bg/60 text-neon-cyan">
          <FileText className="h-4 w-4" />
        </div>
        <div>
          <h3 className="text-sm font-display uppercase tracking-[0.22em] text-white">
            {t('detail.publicPreviewTitle')}
          </h3>
          <p className="mt-1 text-sm font-mono text-muted-foreground">
            {t('detail.publicPreviewDescription', { count: internalCount })}
          </p>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-grid-line/20 bg-terminal-bg/45 p-4 text-sm font-mono leading-6 text-foreground/90">
        {publicMessages.at(-1)?.body ?? t('detail.publicPreviewEmpty')}
      </div>
    </section>
  );
}

function AuditTimeline({
  locale,
  t,
  ticket,
}: {
  locale: string;
  t: SupportTranslate;
  ticket: SupportTicketDetail;
}) {
  return (
    <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <h3 className="text-sm font-display uppercase tracking-[0.22em] text-white">
        {t('detail.auditTitle')}
      </h3>
      <div className="mt-4 grid gap-3">
        {ticket.events.length === 0 ? (
          <p className="rounded-xl border border-dashed border-grid-line/30 bg-terminal-bg/40 p-4 text-sm font-mono text-muted-foreground">
            {t('detail.noEvents')}
          </p>
        ) : (
          ticket.events.map((event) => (
            <article
              key={event.id}
              className="rounded-xl border border-grid-line/20 bg-terminal-bg/45 p-4"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <SupportStatusChip
                  label={humanizeSupportToken(event.event_type)}
                  tone={event.event_type === 'internal_note_added' ? 'warning' : 'neutral'}
                />
                <span className="text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                  {formatSupportDateTime(event.created_at, locale)}
                </span>
              </div>
              <p className="mt-3 text-sm font-mono leading-6 text-foreground/90">
                {event.audit_summary}
              </p>
              {event.from_value || event.to_value ? (
                <p className="mt-2 text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                  {t('detail.transition', {
                    from: event.from_value ?? '--',
                    to: event.to_value ?? '--',
                  })}
                </p>
              ) : null}
            </article>
          ))
        )}
      </div>
    </section>
  );
}

function TicketActionsPanel({
  canWriteSupport,
  isPending,
  onQuickStatus,
  onSubmit,
  t,
  ticket,
}: {
  canWriteSupport: boolean;
  isPending: boolean;
  onQuickStatus: (status: SupportTicketStatus) => void;
  onSubmit: (payload: AdminSupportTicketUpdateRequest) => void;
  t: SupportTranslate;
  ticket: SupportTicketDetail;
}) {
  const [statusDraft, setStatusDraft] = useState<SupportTicketStatus>(ticket.status);
  const [categoryDraft, setCategoryDraft] = useState<SupportTicketCategory>(ticket.category);
  const [priorityDraft, setPriorityDraft] = useState<SupportTicketPriority>(ticket.priority);
  const [assignedAdminDraft, setAssignedAdminDraft] = useState(ticket.assigned_admin_id ?? '');

  function submitMetadataUpdate() {
    onSubmit({
      assigned_admin_id: assignedAdminDraft.trim() || null,
      category: categoryDraft,
      priority: priorityDraft,
      status: statusDraft,
    });
  }

  return (
    <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-amber-300">
          <UserRoundCheck className="h-4 w-4" />
        </div>
        <div>
          <h3 className="text-sm font-display uppercase tracking-[0.22em] text-white">
            {t('actions.title')}
          </h3>
          <p className="mt-1 text-sm font-mono text-muted-foreground">
            {t('actions.description')}
          </p>
        </div>
      </div>

      {!canWriteSupport ? (
        <div className="mt-4 rounded-xl border border-neon-pink/25 bg-neon-pink/10 p-4 text-sm font-mono text-neon-pink">
          {t('actions.readOnly')}
        </div>
      ) : null}

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <select
          value={statusDraft}
          onChange={(event) => setStatusDraft(event.target.value as SupportTicketStatus)}
          disabled={!canWriteSupport}
          aria-label={t('actions.status')}
          className={cn(
            'h-11 rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground disabled:opacity-60',
            CONTROL_FOCUS_CLASS,
          )}
        >
          {SUPPORT_TICKET_STATUSES.map((status) => (
            <option key={status} value={status}>
              {t(`statuses.${status}`)}
            </option>
          ))}
        </select>

        <select
          value={priorityDraft}
          onChange={(event) => setPriorityDraft(event.target.value as SupportTicketPriority)}
          disabled={!canWriteSupport}
          aria-label={t('actions.priority')}
          className={cn(
            'h-11 rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground disabled:opacity-60',
            CONTROL_FOCUS_CLASS,
          )}
        >
          {SUPPORT_TICKET_PRIORITIES.map((priority) => (
            <option key={priority} value={priority}>
              {t(`priorities.${priority}`)}
            </option>
          ))}
        </select>

        <select
          value={categoryDraft}
          onChange={(event) => setCategoryDraft(event.target.value as SupportTicketCategory)}
          disabled={!canWriteSupport}
          aria-label={t('actions.category')}
          className={cn(
            'h-11 rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground disabled:opacity-60',
            CONTROL_FOCUS_CLASS,
          )}
        >
          {SUPPORT_TICKET_CATEGORIES.map((category) => (
            <option key={category} value={category}>
              {t(`categories.${category}`)}
            </option>
          ))}
        </select>

        <input
          value={assignedAdminDraft}
          onChange={(event) => setAssignedAdminDraft(event.target.value)}
          disabled={!canWriteSupport}
          placeholder={t('actions.assignedAdminPlaceholder')}
          aria-label={t('actions.assignedAdmin')}
          className={cn(
            'h-11 rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground disabled:opacity-60',
            CONTROL_FOCUS_CLASS,
          )}
        />
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <button
          type="button"
          disabled={!canWriteSupport || isPending}
          onClick={submitMetadataUpdate}
          className={cn(
            'rounded-xl border border-amber-300/35 bg-amber-300/10 px-4 py-3 text-xs font-mono uppercase tracking-[0.18em] text-amber-300 transition-colors hover:bg-amber-300/15 disabled:opacity-60',
            AMBER_FOCUS_CLASS,
          )}
        >
          {isPending ? t('actions.saving') : t('actions.save')}
        </button>
        {(['resolved', 'closed', 'pending_support'] as const).map((status) => (
          <button
            key={status}
            type="button"
            disabled={!canWriteSupport || isPending}
            onClick={() => onQuickStatus(status)}
            className={cn(
              'rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-xs font-mono uppercase tracking-[0.18em] text-white transition-colors hover:border-neon-cyan/35 disabled:opacity-60',
              CONTROL_FOCUS_CLASS,
            )}
          >
            {t(`actions.quick.${status}`)}
          </button>
        ))}
      </div>
    </section>
  );
}

interface SupportConsoleProps {
  initialSearchParams?: SupportSearchParams;
  initialTicketRef?: string;
}

export function SupportConsole({
  initialSearchParams,
  initialTicketRef,
}: SupportConsoleProps) {
  const t = useTranslations('Support');
  const locale = useLocale();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [initialFilters] = useState(() => getInitialFilters(initialSearchParams));
  const [search, setSearch] = useState(initialFilters.search);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>(initialFilters.statusFilter);
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>(
    initialFilters.categoryFilter,
  );
  const [priorityFilter, setPriorityFilter] = useState<PriorityFilter>(
    initialFilters.priorityFilter,
  );
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>(initialFilters.sourceFilter);
  const [assignmentFilter, setAssignmentFilter] = useState<AssignmentFilter>(
    initialFilters.assignmentFilter,
  );
  const [selectedTicketRef, setSelectedTicketRef] = useState<string | null>(
    initialTicketRef ?? null,
  );
  const [publicReplyDraft, setPublicReplyDraft] = useState('');
  const [internalNoteDraft, setInternalNoteDraft] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);
  const deferredSearch = useDeferredValue(search);
  const supportUrlQuery = buildSupportUrlQuery({
    assignmentFilter,
    categoryFilter,
    priorityFilter,
    search: deferredSearch,
    sourceFilter,
    statusFilter,
  });

  useEffect(() => {
    const query = buildSupportUrlQuery({
      assignmentFilter,
      categoryFilter,
      priorityFilter,
      search: deferredSearch,
      sourceFilter,
      statusFilter,
    });
    const ticketPath = selectedTicketRef ? safeTicketRoute(selectedTicketRef) : '/support';
    router.replace(buildSupportHref(ticketPath, query), { scroll: false });
  }, [
    assignmentFilter,
    categoryFilter,
    deferredSearch,
    priorityFilter,
    router,
    selectedTicketRef,
    sourceFilter,
    statusFilter,
  ]);

  const sessionQuery = useQuery({
    queryKey: ['support', 'session'],
    queryFn: async () => {
      const response = await authApi.session();
      return response.data;
    },
    staleTime: 30_000,
  });

  const role = sessionQuery.data?.role;
  const canReadSupport = hasAdminPermission(role, 'support_ticket_read');
  const canWriteSupport = hasAdminPermission(role, 'user_update');
  const assignedAdminId =
    assignmentFilter === 'mine' && sessionQuery.data?.id
      ? sessionQuery.data.id
      : undefined;

  const listParams = buildListParams({
    assignedAdminId,
    categoryFilter,
    deferredSearch,
    priorityFilter,
    sourceFilter,
    statusFilter,
  });

  const ticketsQuery = useQuery({
    queryKey: ['support', 'admin', 'tickets', listParams],
    queryFn: async () => {
      const response = await supportApi.listAdminTickets(listParams);
      return response.data;
    },
    enabled: canReadSupport,
    staleTime: 12_000,
  });

  const serverTickets = ticketsQuery.data?.tickets ?? [];
  const visibleTickets = assignmentFilter === 'unassigned'
    ? serverTickets.filter((ticket) => !ticket.assigned_admin_id)
    : serverTickets;
  const effectiveTicketRef =
    selectedTicketRef
    ?? initialTicketRef
    ?? visibleTickets[0]?.public_id
    ?? null;

  const detailQuery = useQuery({
    queryKey: ['support', 'admin', 'tickets', effectiveTicketRef, 'detail'],
    queryFn: async () => {
      const response = await supportApi.getAdminTicket(effectiveTicketRef!);
      return response.data;
    },
    enabled: canReadSupport && Boolean(effectiveTicketRef),
    staleTime: 10_000,
  });

  async function refreshSupportData(ticketRef: string | null) {
    await queryClient.invalidateQueries({ queryKey: ['support', 'admin', 'tickets'] });
    if (ticketRef) {
      await queryClient.invalidateQueries({
        queryKey: ['support', 'admin', 'tickets', ticketRef, 'detail'],
      });
    }
  }

  const publicReplyMutation = useMutation({
    mutationFn: async () => {
      if (!effectiveTicketRef) {
        throw new Error(t('feedback.selectTicket'));
      }
      const message = validateMessage(publicReplyDraft, t);
      const response = await supportApi.addAdminReply(effectiveTicketRef, { message });
      return response.data;
    },
    onSuccess: async (ticket) => {
      setPublicReplyDraft('');
      setFeedback(t('feedback.publicReplySent'));
      await refreshSupportData(ticket.public_id);
    },
    onError: (error) => {
      setFeedback(getSupportErrorMessage(error, t('common.actionFailed')));
    },
  });

  const internalNoteMutation = useMutation({
    mutationFn: async () => {
      if (!effectiveTicketRef) {
        throw new Error(t('feedback.selectTicket'));
      }
      const message = validateMessage(internalNoteDraft, t);
      const response = await supportApi.addAdminInternalNote(effectiveTicketRef, { message });
      return response.data;
    },
    onSuccess: async (ticket) => {
      setInternalNoteDraft('');
      setFeedback(t('feedback.internalNoteSaved'));
      await refreshSupportData(ticket.public_id);
    },
    onError: (error) => {
      setFeedback(getSupportErrorMessage(error, t('common.actionFailed')));
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ payload }: UpdateMutationInput) => {
      if (!effectiveTicketRef) {
        throw new Error(t('feedback.selectTicket'));
      }
      const response = await supportApi.updateAdminTicket(effectiveTicketRef, payload);
      return response.data;
    },
    onSuccess: async (ticket, variables) => {
      setFeedback(t(variables.feedbackKey));
      await refreshSupportData(ticket.public_id);
    },
    onError: (error) => {
      setFeedback(getSupportErrorMessage(error, t('common.actionFailed')));
    },
  });

  function submitMetadataUpdate(payload: AdminSupportTicketUpdateRequest) {
    updateMutation.mutate({
      feedbackKey: 'feedback.ticketUpdated',
      payload,
    });
  }

  function submitQuickStatus(status: SupportTicketStatus) {
    updateMutation.mutate({
      feedbackKey: 'feedback.statusUpdated',
      payload: { status },
    });
  }

  const selectedTicket = detailQuery.data ?? null;
  const internalNoteCount =
    selectedTicket?.messages.filter((message) => message.visibility === 'internal').length ?? 0;
  const activeCount =
    countByStatus(visibleTickets, 'open') + countByStatus(visibleTickets, 'pending_support');

  if (sessionQuery.isLoading) {
    return (
      <SupportPageShell
        eyebrow={t('inbox.eyebrow')}
        title={t('inbox.title')}
        description={t('inbox.description')}
        icon={Inbox}
      >
        <LoadingRows />
      </SupportPageShell>
    );
  }

  if (!canReadSupport) {
    return (
      <SupportPageShell
        eyebrow={t('inbox.eyebrow')}
        title={t('inbox.title')}
        description={t('inbox.description')}
        icon={Inbox}
      >
        <PermissionDeniedState t={t} />
      </SupportPageShell>
    );
  }

  return (
    <SupportPageShell
      eyebrow={t('inbox.eyebrow')}
      title={t('inbox.title')}
      description={t('inbox.description')}
      icon={Inbox}
      actions={
        <button
          type="button"
          aria-label={t('common.refresh')}
          onClick={() => void refreshSupportData(effectiveTicketRef)}
          className={cn(
            'inline-flex items-center gap-2 rounded-xl border border-grid-line/30 bg-terminal-bg/65 px-4 py-3 text-xs font-mono uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:border-neon-cyan/40 hover:text-white',
            CONTROL_FOCUS_CLASS,
          )}
        >
          <RefreshCw className="h-4 w-4" />
          <span>{t('common.refresh')}</span>
        </button>
      }
      metrics={[
        {
          label: t('metrics.visible'),
          value: String(visibleTickets.length),
          hint: t('metrics.visibleHint'),
          tone: 'info',
        },
        {
          label: t('metrics.active'),
          value: String(activeCount),
          hint: t('metrics.activeHint'),
          tone: activeCount ? 'danger' : 'success',
        },
        {
          label: t('metrics.urgent'),
          value: String(visibleTickets.filter((ticket) => ticket.priority === 'urgent').length),
          hint: t('metrics.urgentHint'),
          tone: 'warning',
        },
        {
          label: t('metrics.internalNotes'),
          value: String(internalNoteCount),
          hint: t('metrics.internalNotesHint'),
          tone: internalNoteCount ? 'warning' : 'neutral',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          <div className="grid gap-3 lg:grid-cols-[minmax(16rem,1fr)_repeat(4,minmax(8rem,10rem))]">
            <label className="relative block">
              <span className="sr-only">{t('filters.search')}</span>
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder={t('filters.searchPlaceholder')}
                aria-label={t('filters.search')}
                className={cn(
                  'h-11 w-full rounded-md border border-input bg-transparent pl-10 pr-3 text-sm text-foreground',
                  CONTROL_FOCUS_CLASS,
                )}
              />
            </label>

            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
              aria-label={t('filters.status')}
              className={cn(
                'h-11 rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground',
                CONTROL_FOCUS_CLASS,
              )}
            >
              <option value="all">{t('filters.allStatuses')}</option>
              {SUPPORT_TICKET_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {t(`statuses.${status}`)}
                </option>
              ))}
            </select>

            <select
              value={priorityFilter}
              onChange={(event) => setPriorityFilter(event.target.value as PriorityFilter)}
              aria-label={t('filters.priority')}
              className={cn(
                'h-11 rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground',
                CONTROL_FOCUS_CLASS,
              )}
            >
              <option value="all">{t('filters.allPriorities')}</option>
              {SUPPORT_TICKET_PRIORITIES.map((priority) => (
                <option key={priority} value={priority}>
                  {t(`priorities.${priority}`)}
                </option>
              ))}
            </select>

            <select
              value={categoryFilter}
              onChange={(event) => setCategoryFilter(event.target.value as CategoryFilter)}
              aria-label={t('filters.category')}
              className={cn(
                'h-11 rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground',
                CONTROL_FOCUS_CLASS,
              )}
            >
              <option value="all">{t('filters.allCategories')}</option>
              {SUPPORT_TICKET_CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {t(`categories.${category}`)}
                </option>
              ))}
            </select>

            <select
              value={sourceFilter}
              onChange={(event) => setSourceFilter(event.target.value as SourceFilter)}
              aria-label={t('filters.source')}
              className={cn(
                'h-11 rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground',
                CONTROL_FOCUS_CLASS,
              )}
            >
              <option value="all">{t('filters.allSources')}</option>
              {SUPPORT_TICKET_SOURCES.map((source) => (
                <option key={source} value={source}>
                  {t(`sources.${source}`)}
                </option>
              ))}
            </select>
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {(['all', 'mine', 'unassigned'] as const).map((assignment) => (
              <button
                key={assignment}
                type="button"
                aria-pressed={assignmentFilter === assignment}
                onClick={() => setAssignmentFilter(assignment)}
                className={cn(
                  'rounded-xl px-3 py-2 text-xs font-mono uppercase tracking-[0.16em]',
                  assignmentFilter === assignment
                    ? 'border border-amber-300/35 bg-amber-300/10 text-amber-300'
                    : 'border border-grid-line/20 bg-terminal-bg/50 text-muted-foreground transition-colors hover:text-white',
                  CONTROL_FOCUS_CLASS,
                )}
              >
                {t(`filters.assignment.${assignment}`)}
              </button>
            ))}
          </div>

          {assignmentFilter === 'unassigned' ? (
            <p
              role="note"
              className="mt-3 rounded-xl border border-amber-300/25 bg-amber-300/10 px-4 py-3 text-xs font-mono leading-5 text-amber-100"
            >
              {t('filters.assignment.unassignedScopeHint', { count: SUPPORT_LIST_LIMIT })}
            </p>
          ) : null}

          {ticketsQuery.isError ? (
            <div className="mt-4 rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
              {getSupportErrorMessage(ticketsQuery.error, t('list.loadError'))}
            </div>
          ) : null}

          <div className="mt-5">
            {ticketsQuery.isLoading ? (
              <LoadingRows />
            ) : visibleTickets.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-10 text-center">
                <Inbox className="mx-auto h-8 w-8 text-muted-foreground" />
                <p className="mt-3 text-sm font-mono text-muted-foreground">
                  {t('list.empty')}
                </p>
              </div>
            ) : (
              <TicketList
                activeTicketRef={effectiveTicketRef}
                locale={locale}
                onSelect={setSelectedTicketRef}
                query={supportUrlQuery}
                t={t}
                tickets={visibleTickets}
              />
            )}
          </div>
        </section>

        <aside className="grid gap-5 xl:col-span-5">
          {detailQuery.isLoading ? (
            <DetailSkeleton />
          ) : detailQuery.isError ? (
            <div className="rounded-2xl border border-neon-pink/30 bg-neon-pink/10 p-5 text-sm font-mono text-neon-pink">
              {getSupportErrorMessage(detailQuery.error, t('detail.loadError'))}
            </div>
          ) : !selectedTicket ? (
            <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-surface/35 p-8 text-center">
              <AlertTriangle className="mx-auto h-9 w-9 text-muted-foreground" />
              <p className="mt-3 text-sm font-mono text-muted-foreground">
                {t('detail.empty')}
              </p>
            </div>
          ) : (
            <>
              <ConversationHeader locale={locale} t={t} ticket={selectedTicket} />

              <TicketActionsPanel
                key={selectedTicket.id}
                canWriteSupport={canWriteSupport}
                isPending={updateMutation.isPending}
                onQuickStatus={submitQuickStatus}
                onSubmit={submitMetadataUpdate}
                t={t}
                ticket={selectedTicket}
              />

              <section className="grid gap-5">
                <form
                  data-testid="support-public-reply-composer"
                  onSubmit={(event) => {
                    event.preventDefault();
                    publicReplyMutation.mutate();
                  }}
                  className="rounded-2xl border border-neon-cyan/25 bg-neon-cyan/10 p-5"
                >
                  <div className="flex items-center gap-3">
                    <MessageSquareReply className="h-5 w-5 text-neon-cyan" />
                    <div>
                      <h3 className="text-sm font-display uppercase tracking-[0.22em] text-white">
                        {t('reply.title')}
                      </h3>
                      <p className="mt-1 text-sm font-mono text-muted-foreground">
                        {t('reply.description')}
                      </p>
                    </div>
                  </div>
                  <textarea
                    value={publicReplyDraft}
                    onChange={(event) => setPublicReplyDraft(event.target.value)}
                    disabled={!canWriteSupport || selectedTicket.status === 'closed'}
                    aria-label={t('reply.message')}
                    placeholder={t('reply.placeholder')}
                    className={cn(
                      'mt-4 min-h-28 w-full rounded-xl border border-neon-cyan/25 bg-terminal-bg/70 p-3 text-sm font-mono text-foreground disabled:opacity-60',
                      CONTROL_FOCUS_CLASS,
                    )}
                  />
                  <button
                    type="submit"
                    disabled={
                      !canWriteSupport
                      || selectedTicket.status === 'closed'
                      || publicReplyMutation.isPending
                    }
                    className={cn(
                      'mt-3 rounded-xl border border-neon-cyan/35 bg-neon-cyan/10 px-4 py-3 text-xs font-mono uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:bg-neon-cyan/15 disabled:opacity-60',
                      CONTROL_FOCUS_CLASS,
                    )}
                  >
                    {publicReplyMutation.isPending
                      ? t('reply.sending')
                      : t('reply.submit')}
                  </button>
                </form>

                <form
                  data-testid="support-internal-note-composer"
                  onSubmit={(event) => {
                    event.preventDefault();
                    internalNoteMutation.mutate();
                  }}
                  className="rounded-2xl border border-amber-300/30 bg-amber-300/10 p-5"
                >
                  <div className="flex items-center gap-3">
                    <NotebookPen className="h-5 w-5 text-amber-300" />
                    <div>
                      <h3 className="text-sm font-display uppercase tracking-[0.22em] text-white">
                        {t('internalNote.title')}
                      </h3>
                      <p className="mt-1 text-sm font-mono text-muted-foreground">
                        {t('internalNote.description')}
                      </p>
                    </div>
                  </div>
                  <textarea
                    value={internalNoteDraft}
                    onChange={(event) => setInternalNoteDraft(event.target.value)}
                    disabled={!canWriteSupport}
                    aria-label={t('internalNote.message')}
                    placeholder={t('internalNote.placeholder')}
                    className={cn(
                      'mt-4 min-h-28 w-full rounded-xl border border-amber-300/25 bg-terminal-bg/70 p-3 text-sm font-mono text-foreground disabled:opacity-60',
                      AMBER_FOCUS_CLASS,
                    )}
                  />
                  <button
                    type="submit"
                    disabled={!canWriteSupport || internalNoteMutation.isPending}
                    className={cn(
                      'mt-3 rounded-xl border border-amber-300/35 bg-amber-300/10 px-4 py-3 text-xs font-mono uppercase tracking-[0.18em] text-amber-300 transition-colors hover:bg-amber-300/15 disabled:opacity-60',
                      AMBER_FOCUS_CLASS,
                    )}
                  >
                    {internalNoteMutation.isPending
                      ? t('internalNote.saving')
                      : t('internalNote.submit')}
                  </button>
                </form>
              </section>

              <div
                className="sr-only"
                role="status"
                aria-live="polite"
                aria-atomic="true"
                data-testid="support-live-region"
              >
                {feedback ?? ''}
              </div>

              {feedback ? (
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/65 px-4 py-3 text-sm font-mono text-foreground">
                  {feedback}
                </div>
              ) : null}

              <PublicPreviewPanel t={t} ticket={selectedTicket} />
              <TimelinePanel locale={locale} t={t} ticket={selectedTicket} />
              <AuditTimeline locale={locale} t={t} ticket={selectedTicket} />
            </>
          )}
        </aside>
      </div>
    </SupportPageShell>
  );
}
