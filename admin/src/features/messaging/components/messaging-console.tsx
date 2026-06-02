'use client';

import { useDeferredValue, useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  Eye,
  FileText,
  Inbox,
  LockKeyhole,
  MessageCirclePlus,
  MessageSquareReply,
  Megaphone,
  NotebookPen,
  RadioTower,
  RefreshCw,
  Search,
  Send,
  UserRoundCheck,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Link, useRouter } from '@/i18n/navigation';
import { authApi } from '@/lib/api/auth';
import {
  MESSAGING_CONVERSATION_CATEGORIES,
  MESSAGING_CONVERSATION_STATUSES,
  MESSAGING_PRIORITIES,
  NOTIFICATION_BROADCAST_AUDIENCE_TYPES,
  messagingApi,
  type AdminMessagingConversationCreateRequest,
  type AdminMessagingConversationDetail,
  type AdminMessagingConversationListParams,
  type AdminMessagingConversationSummary,
  type AdminMessagingConversationUpdateRequest,
  type AdminNotificationBroadcastCampaign,
  type AdminNotificationBroadcastCreateRequest,
  type MessagingConversationCategory,
  type MessagingConversationStatus,
  type MessagingPriority,
  type NotificationBroadcastAudienceType,
} from '@/lib/api/messaging';
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
import { MessagingPageShell } from '@/features/messaging/components/messaging-page-shell';
import { MessagingStatusChip } from '@/features/messaging/components/messaging-status-chip';
import {
  formatMessagingDateTime,
  getMessagingErrorMessage,
  messagingPriorityTone,
  messagingResponseStateTone,
  messagingStatusTone,
  messagingVisibilityTone,
  shortMessagingId,
} from '@/features/messaging/lib/formatting';

type MessagingTranslate = (key: string, values?: Record<string, string | number>) => string;
type StatusFilter = 'all' | MessagingConversationStatus;
type CategoryFilter = 'all' | MessagingConversationCategory;
type PriorityFilter = 'all' | MessagingPriority;
type AssignmentFilter = 'all' | 'mine' | 'unassigned';
type RealtimeState = 'connecting' | 'connected' | 'offline';
type MessagingSearchParams = Record<string, string | string[] | undefined>;
type MessagingUrlQuery = Record<string, string>;
type MessagingInitialFilters = {
  assignmentFilter: AssignmentFilter;
  categoryFilter: CategoryFilter;
  customerFilter: string;
  priorityFilter: PriorityFilter;
  search: string;
  statusFilter: StatusFilter;
};
type UpdateMutationInput = {
  feedbackKey: string;
  payload: AdminMessagingConversationUpdateRequest;
};
type BroadcastCreateMutationInput = {
  payload: AdminNotificationBroadcastCreateRequest;
  recipientCount: number;
};
type CreateConversationField = 'customer' | 'subject' | 'initialMessage';
type CreateConversationErrors = Partial<Record<CreateConversationField, string>>;
type BroadcastFormField = 'name' | 'audience' | 'title' | 'body' | 'actionUrl' | 'scheduledAt' | 'confirmation';
type BroadcastFormErrors = Partial<Record<BroadcastFormField, string>>;
type PaginationState = {
  extraConversations: AdminMessagingConversationSummary[];
  hasLoadedExtra: boolean;
  nextCursor: string | null;
  scopeKey: string | null;
};

const MESSAGE_MAX_LENGTH = 4000;
const SUBJECT_MAX_LENGTH = 160;
const BROADCAST_NAME_MAX_LENGTH = 160;
const BROADCAST_TITLE_MAX_LENGTH = 160;
const BROADCAST_BODY_MAX_LENGTH = 4000;
const BROADCAST_ACTION_URL_MAX_LENGTH = 500;
const BROADCAST_EXPLICIT_CUSTOMER_LIMIT = 25;
const BROADCAST_CONFIRM_PHRASE = 'BROADCAST';
const BROADCAST_HISTORY_LIMIT = 6;
const MESSAGING_LIST_LIMIT = 50;
const ASSIGNMENT_FILTERS = ['all', 'mine', 'unassigned'] as const;
const STATUS_FILTERS = ['all', ...MESSAGING_CONVERSATION_STATUSES] as const;
const CATEGORY_FILTERS = ['all', ...MESSAGING_CONVERSATION_CATEGORIES] as const;
const PRIORITY_FILTERS = ['all', ...MESSAGING_PRIORITIES] as const;
const CONTROL_FOCUS_CLASS =
  'outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg';
const AMBER_FOCUS_CLASS =
  'outline-hidden focus-visible:ring-2 focus-visible:ring-amber-300 focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg';
const EMPTY_PAGINATION_STATE: PaginationState = {
  extraConversations: [],
  hasLoadedExtra: false,
  nextCursor: null,
  scopeKey: null,
};

function safeConversationRoute(publicId: string) {
  return `/messaging/${encodeURIComponent(publicId)}`;
}

function safeCustomerRoute(customerId: string) {
  return `/customers/${encodeURIComponent(customerId)}`;
}

function readSearchParam(searchParams: MessagingSearchParams | undefined, key: string) {
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

function getInitialFilters(
  searchParams: MessagingSearchParams | undefined,
): MessagingInitialFilters {
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
    customerFilter: readSearchParam(searchParams, 'customer')?.slice(0, 80) ?? '',
    priorityFilter: readAllowedValue(
      readSearchParam(searchParams, 'priority'),
      PRIORITY_FILTERS,
      'all',
    ),
    search: readSearchParam(searchParams, 'q')?.slice(0, 120) ?? '',
    statusFilter: readAllowedValue(
      readSearchParam(searchParams, 'status'),
      STATUS_FILTERS,
      'all',
    ),
  };
}

function buildMessagingUrlQuery({
  assignmentFilter,
  categoryFilter,
  customerFilter,
  priorityFilter,
  search,
  statusFilter,
}: MessagingInitialFilters): MessagingUrlQuery {
  const query: MessagingUrlQuery = {};
  const trimmedSearch = search.trim();
  const trimmedCustomer = customerFilter.trim();

  if (trimmedSearch) {
    query.q = trimmedSearch;
  }
  if (trimmedCustomer) {
    query.customer = trimmedCustomer;
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
  if (assignmentFilter !== 'all') {
    query.assignment = assignmentFilter;
  }

  return query;
}

function buildMessagingHref(pathname: string, query: MessagingUrlQuery) {
  const searchParams = new URLSearchParams(query);
  const searchString = searchParams.toString();
  return searchString ? `${pathname}?${searchString}` : pathname;
}

function buildListParams({
  assignedAdminId,
  categoryFilter,
  customerFilter,
  deferredSearch,
  priorityFilter,
  statusFilter,
}: {
  assignedAdminId: string | undefined;
  categoryFilter: CategoryFilter;
  customerFilter: string;
  deferredSearch: string;
  priorityFilter: PriorityFilter;
  statusFilter: StatusFilter;
}): AdminMessagingConversationListParams {
  return {
    assigned_admin_id: assignedAdminId,
    category: categoryFilter === 'all' ? undefined : categoryFilter,
    customer_account_id: customerFilter.trim() || undefined,
    limit: MESSAGING_LIST_LIMIT,
    priority: priorityFilter === 'all' ? undefined : priorityFilter,
    query: deferredSearch.trim() || undefined,
    status: statusFilter === 'all' ? undefined : statusFilter,
  };
}

function createClientMessageId(prefix: string) {
  const randomId =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;

  return `${prefix}-${randomId}`.slice(0, 80);
}

function parseExplicitCustomerIds(value: string) {
  return Array.from(
    new Set(
      value
        .split(/[\s,]+/)
        .map((item) => item.trim())
        .filter(Boolean),
    ),
  );
}

function parsePositiveInteger(value: string) {
  const parsed = Number.parseInt(value.trim(), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function parseAudienceFilterJson(value: string) {
  const trimmed = value.trim();
  if (!trimmed) {
    return {};
  }

  const parsed = JSON.parse(trimmed) as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('audience_filter_must_be_object');
  }

  return parsed as Record<string, unknown>;
}

function toDatetimeIso(value: string) {
  if (!value.trim()) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return undefined;
  }

  return date.toISOString();
}

function upsertBroadcastHistory(
  current: AdminNotificationBroadcastCampaign[],
  campaign: AdminNotificationBroadcastCampaign,
) {
  return [
    campaign,
    ...current.filter((item) => item.id !== campaign.id && item.public_id !== campaign.public_id),
  ].slice(0, BROADCAST_HISTORY_LIMIT);
}

function getRequiredTextError(
  value: string,
  t: MessagingTranslate,
  requiredKey: string,
  maxLength: number,
  tooLongKey: string,
) {
  const trimmed = value.trim();
  if (!trimmed) {
    return t(requiredKey);
  }
  if (trimmed.length > maxLength) {
    return t(tooLongKey, { count: maxLength });
  }

  return null;
}

function validateRequiredText(
  value: string,
  t: MessagingTranslate,
  requiredKey: string,
  maxLength: number,
  tooLongKey: string,
) {
  const error = getRequiredTextError(value, t, requiredKey, maxLength, tooLongKey);
  if (error) {
    throw new Error(error);
  }

  return value.trim();
}

function getNextCursor(
  data: { nextCursor?: string | null; next_cursor?: string | null } | undefined,
) {
  return data?.nextCursor ?? data?.next_cursor ?? null;
}

function mergeConversationPages(
  conversations: readonly AdminMessagingConversationSummary[],
) {
  const seenConversationIds = new Set<string>();

  return conversations.filter((conversation) => {
    const key = conversation.public_id || conversation.id;
    if (seenConversationIds.has(key)) {
      return false;
    }

    seenConversationIds.add(key);
    return true;
  });
}

function hasUnreadSignal(conversation: AdminMessagingConversationSummary) {
  return conversation.status === 'open' && conversation.response_state === 'waiting_admin';
}

function PermissionDeniedState({ t }: { t: MessagingTranslate }) {
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
    <div className="grid gap-3" data-testid="messaging-loading-state">
      {Array.from({ length: 6 }).map((_, index) => (
        <div
          key={index}
          className="h-20 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
        />
      ))}
    </div>
  );
}

function ConversationCustomerMeta({
  conversation,
  t,
}: {
  conversation: AdminMessagingConversationSummary;
  t: MessagingTranslate;
}) {
  return (
    <div className="grid gap-2 text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
      <span>{t('list.customer')}</span>
      <span>{t('list.safeCustomerRef', { id: shortMessagingId(conversation.customer_account_id) })}</span>
    </div>
  );
}

function ConversationList({
  activeConversationRef,
  conversations,
  locale,
  onSelect,
  query,
  t,
}: {
  activeConversationRef: string | null;
  conversations: readonly AdminMessagingConversationSummary[];
  locale: string;
  onSelect: (conversationRef: string) => void;
  query: MessagingUrlQuery;
  t: MessagingTranslate;
}) {
  return (
    <>
      <ul
        aria-label={t('list.mobileListLabel')}
        className="grid gap-3 md:hidden"
        data-testid="messaging-mobile-conversation-list"
      >
        {conversations.map((conversation) => {
          const isActive =
            activeConversationRef === conversation.public_id
            || activeConversationRef === conversation.id;

          return (
            <li
              key={conversation.id}
              className={cn(
                'rounded-2xl border border-grid-line/20 bg-terminal-bg/55 p-4 [content-visibility:auto] [contain-intrinsic-size:auto_220px]',
                isActive ? 'border-neon-cyan/45 bg-neon-cyan/10' : undefined,
              )}
            >
              <button
                type="button"
                aria-current={isActive ? 'true' : undefined}
                aria-label={t('list.selectConversation', { publicId: conversation.public_id })}
                onClick={() => onSelect(conversation.public_id)}
                className={cn('block w-full rounded-xl p-1 text-left', CONTROL_FOCUS_CLASS)}
              >
                <span className="block break-words font-display uppercase tracking-[0.14em] text-white">
                  {conversation.subject}
                </span>
                <span className="mt-1 block text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {conversation.public_id}
                </span>
              </button>

              <div className="mt-4 flex flex-wrap gap-2">
                {hasUnreadSignal(conversation) ? (
                  <MessagingStatusChip label={t('states.unread')} tone="danger" />
                ) : null}
                <MessagingStatusChip
                  label={t(`statuses.${conversation.status}`)}
                  tone={messagingStatusTone(conversation.status)}
                />
                <MessagingStatusChip
                  label={t(`priorities.${conversation.priority}`)}
                  tone={messagingPriorityTone(conversation.priority)}
                />
                <MessagingStatusChip
                  label={t(`responseStates.${conversation.response_state}`)}
                  tone={messagingResponseStateTone(conversation.response_state)}
                />
              </div>

              <div className="mt-4 grid gap-3 text-sm">
                <ConversationCustomerMeta conversation={conversation} t={t} />
                <p className="font-mono text-muted-foreground">
                  {t('list.table.updated')}: {formatMessagingDateTime(conversation.updated_at, locale)}
                </p>
                <Link
                  href={buildMessagingHref(safeConversationRoute(conversation.public_id), query)}
                  aria-label={t('list.openRoute', { publicId: conversation.public_id })}
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
              <TableHead>{t('list.table.conversation')}</TableHead>
              <TableHead>{t('list.table.state')}</TableHead>
              <TableHead>{t('list.table.customer')}</TableHead>
              <TableHead>{t('list.table.updated')}</TableHead>
              <TableHead>{t('common.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {conversations.map((conversation) => {
              const isActive =
                activeConversationRef === conversation.public_id
                || activeConversationRef === conversation.id;

              return (
                <TableRow
                  key={conversation.id}
                  className={isActive ? 'border-l-2 border-l-neon-cyan bg-neon-cyan/5' : undefined}
                >
                  <TableCell>
                    <button
                      type="button"
                      aria-current={isActive ? 'true' : undefined}
                      aria-label={t('list.selectConversation', { publicId: conversation.public_id })}
                      onClick={() => onSelect(conversation.public_id)}
                      className={cn('block max-w-sm rounded-xl p-1 text-left', CONTROL_FOCUS_CLASS)}
                    >
                      <span className="block break-words font-display uppercase tracking-[0.14em] text-white">
                        {conversation.subject}
                      </span>
                      <span className="mt-1 block text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {conversation.public_id}
                      </span>
                    </button>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-2">
                      {hasUnreadSignal(conversation) ? (
                        <MessagingStatusChip label={t('states.unread')} tone="danger" />
                      ) : null}
                      <MessagingStatusChip
                        label={t(`statuses.${conversation.status}`)}
                        tone={messagingStatusTone(conversation.status)}
                      />
                      <MessagingStatusChip
                        label={t(`priorities.${conversation.priority}`)}
                        tone={messagingPriorityTone(conversation.priority)}
                      />
                      <MessagingStatusChip
                        label={t(`responseStates.${conversation.response_state}`)}
                        tone={messagingResponseStateTone(conversation.response_state)}
                      />
                    </div>
                  </TableCell>
                  <TableCell>
                    <ConversationCustomerMeta conversation={conversation} t={t} />
                  </TableCell>
                  <TableCell>{formatMessagingDateTime(conversation.updated_at, locale)}</TableCell>
                  <TableCell>
                    <Link
                      href={buildMessagingHref(safeConversationRoute(conversation.public_id), query)}
                      aria-label={t('list.openRoute', { publicId: conversation.public_id })}
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
    <div className="grid gap-4" data-testid="messaging-detail-loading-state">
      <div className="h-24 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45" />
      <div className="h-72 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45" />
      <div className="h-48 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45" />
    </div>
  );
}

function ConversationHeader({
  conversation,
  locale,
  t,
}: {
  conversation: AdminMessagingConversationDetail;
  locale: string;
  t: MessagingTranslate;
}) {
  return (
    <header className="rounded-2xl border border-grid-line/20 bg-terminal-bg/55 p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-mono uppercase tracking-[0.22em] text-neon-cyan">
            {conversation.public_id}
          </p>
          <h2 className="mt-2 break-words text-xl font-display uppercase tracking-[0.16em] text-white">
            {conversation.subject}
          </h2>
          <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
            {t('detail.updatedAt', {
              value: formatMessagingDateTime(conversation.updated_at, locale),
            })}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <MessagingStatusChip
            label={t(`statuses.${conversation.status}`)}
            tone={messagingStatusTone(conversation.status)}
          />
          <MessagingStatusChip
            label={t(`priorities.${conversation.priority}`)}
            tone={messagingPriorityTone(conversation.priority)}
          />
          <MessagingStatusChip
            label={t(`responseStates.${conversation.response_state}`)}
            tone={messagingResponseStateTone(conversation.response_state)}
          />
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-grid-line/20 bg-terminal-surface/35 p-3">
          <p className="text-[11px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
            {t('detail.customerRef')}
          </p>
          <Link
            href={safeCustomerRoute(conversation.customer_account_id)}
            className={cn(
              'mt-2 block break-all rounded-md text-sm font-mono text-neon-cyan underline-offset-4 hover:text-white hover:underline',
              CONTROL_FOCUS_CLASS,
            )}
          >
            {shortMessagingId(conversation.customer_account_id)}
          </Link>
        </div>
        <div className="rounded-xl border border-grid-line/20 bg-terminal-surface/35 p-3">
          <p className="text-[11px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
            {t('detail.assignedAdmin')}
          </p>
          <p className="mt-2 break-all text-sm font-mono text-white">
            {shortMessagingId(conversation.assigned_admin_id)}
          </p>
        </div>
        <div className="rounded-xl border border-grid-line/20 bg-terminal-surface/35 p-3">
          <p className="text-[11px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
            {t('detail.relatedSupport')}
          </p>
          <p className="mt-2 break-all text-sm font-mono text-white">
            {shortMessagingId(conversation.related_support_ticket_id)}
          </p>
        </div>
      </div>
    </header>
  );
}

function ConversationTimeline({
  conversation,
  locale,
  t,
}: {
  conversation: AdminMessagingConversationDetail;
  locale: string;
  t: MessagingTranslate;
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
        {conversation.messages.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
            {t('detail.noMessages')}
          </div>
        ) : (
          conversation.messages.map((message) => (
            <article
              key={message.id}
              data-testid={
                message.visibility === 'internal'
                  ? 'messaging-internal-message'
                  : 'messaging-public-message'
              }
              className={
                message.visibility === 'internal'
                  ? 'rounded-2xl border border-amber-300/25 bg-amber-300/10 p-4'
                  : 'rounded-2xl border border-neon-cyan/20 bg-terminal-bg/45 p-4'
              }
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap gap-2">
                  <MessagingStatusChip
                    label={t(`senders.${message.sender_type}`)}
                    tone={message.sender_type === 'admin' ? 'info' : 'neutral'}
                  />
                  <MessagingStatusChip
                    label={t(`visibilities.${message.visibility}`)}
                    tone={messagingVisibilityTone(message.visibility)}
                  />
                </div>
                <p className="text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                  {formatMessagingDateTime(message.created_at, locale)}
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
  conversation,
  t,
}: {
  conversation: AdminMessagingConversationDetail;
  t: MessagingTranslate;
}) {
  const publicMessages = conversation.messages.filter((message) => message.visibility === 'public');
  const internalCount = conversation.messages.length - publicMessages.length;

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

function ReadStatePanel({
  conversation,
  locale,
  t,
}: {
  conversation: AdminMessagingConversationDetail;
  locale: string;
  t: MessagingTranslate;
}) {
  return (
    <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <div className="flex items-center gap-3">
        <Eye className="h-5 w-5 text-muted-foreground" />
        <div>
          <h3 className="text-sm font-display uppercase tracking-[0.22em] text-white">
            {t('readStates.title')}
          </h3>
          <p className="mt-1 text-sm font-mono text-muted-foreground">
            {t('readStates.description')}
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-3">
        {conversation.read_states.length === 0 ? (
          <p className="rounded-xl border border-dashed border-grid-line/30 bg-terminal-bg/40 p-4 text-sm font-mono text-muted-foreground">
            {t('readStates.empty')}
          </p>
        ) : (
          conversation.read_states.map((readState) => (
            <article
              key={readState.id}
              className="rounded-xl border border-grid-line/20 bg-terminal-bg/45 p-4"
            >
              <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {shortMessagingId(readState.participant_id)}
              </p>
              <p className="mt-2 text-sm font-mono text-foreground">
                {t('readStates.lastReadAt', {
                  value: formatMessagingDateTime(readState.last_read_at, locale),
                })}
              </p>
              <p className="mt-1 text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                {t('readStates.lastMessage', {
                  id: shortMessagingId(readState.last_read_message_id),
                })}
              </p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}

function ConversationControlsPanel({
  canAssignMessaging,
  canCloseMessaging,
  conversation,
  isClosedReadOnly,
  isPending,
  onClose,
  onReopen,
  onSubmit,
  t,
}: {
  canAssignMessaging: boolean;
  canCloseMessaging: boolean;
  conversation: AdminMessagingConversationDetail;
  isClosedReadOnly: boolean;
  isPending: boolean;
  onClose: () => void;
  onReopen: () => void;
  onSubmit: (payload: AdminMessagingConversationUpdateRequest) => void;
  t: MessagingTranslate;
}) {
  const [categoryDraft, setCategoryDraft] = useState<MessagingConversationCategory>(
    conversation.category,
  );
  const [priorityDraft, setPriorityDraft] = useState<MessagingPriority>(conversation.priority);
  const [assignedAdminDraft, setAssignedAdminDraft] = useState(
    conversation.assigned_admin_id ?? '',
  );
  const metadataDisabled = !canAssignMessaging || isClosedReadOnly || isPending;

  function submitMetadataUpdate() {
    onSubmit({
      assigned_admin_id: assignedAdminDraft.trim() || null,
      category: categoryDraft,
      priority: priorityDraft,
    });
  }

  return (
    <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
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

      {isClosedReadOnly ? (
        <div className="mt-4 rounded-xl border border-amber-300/25 bg-amber-300/10 p-4 text-sm font-mono text-amber-100">
          {t('actions.closedReadOnly')}
        </div>
      ) : null}

      {!canAssignMessaging ? (
        <div className="mt-4 rounded-xl border border-neon-pink/25 bg-neon-pink/10 p-4 text-sm font-mono text-neon-pink">
          {t('actions.readOnly')}
        </div>
      ) : null}

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <select
          value={priorityDraft}
          onChange={(event) => setPriorityDraft(event.target.value as MessagingPriority)}
          disabled={metadataDisabled}
          aria-label={t('actions.priority')}
          className={cn(
            'h-11 rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground disabled:opacity-60',
            CONTROL_FOCUS_CLASS,
          )}
        >
          {MESSAGING_PRIORITIES.map((priority) => (
            <option key={priority} value={priority}>
              {t(`priorities.${priority}`)}
            </option>
          ))}
        </select>

        <select
          value={categoryDraft}
          onChange={(event) => setCategoryDraft(event.target.value as MessagingConversationCategory)}
          disabled={metadataDisabled}
          aria-label={t('actions.category')}
          className={cn(
            'h-11 rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground disabled:opacity-60',
            CONTROL_FOCUS_CLASS,
          )}
        >
          {MESSAGING_CONVERSATION_CATEGORIES.map((category) => (
            <option key={category} value={category}>
              {t(`categories.${category}`)}
            </option>
          ))}
        </select>

        <input
          value={assignedAdminDraft}
          onChange={(event) => setAssignedAdminDraft(event.target.value)}
          disabled={metadataDisabled}
          placeholder={t('actions.assignedAdminPlaceholder')}
          aria-label={t('actions.assignedAdmin')}
          className={cn(
            'h-11 rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground disabled:opacity-60 md:col-span-2',
            CONTROL_FOCUS_CLASS,
          )}
        />
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <button
          type="button"
          disabled={metadataDisabled}
          onClick={submitMetadataUpdate}
          className={cn(
            'rounded-xl border border-neon-cyan/35 bg-neon-cyan/10 px-4 py-3 text-xs font-mono uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:bg-neon-cyan/15 disabled:opacity-60',
            CONTROL_FOCUS_CLASS,
          )}
        >
          {isPending ? t('actions.saving') : t('actions.save')}
        </button>
        {conversation.status === 'closed' ? (
          <button
            type="button"
            disabled={!canCloseMessaging || isPending}
            onClick={onReopen}
            className={cn(
              'rounded-xl border border-amber-300/35 bg-amber-300/10 px-4 py-3 text-xs font-mono uppercase tracking-[0.18em] text-amber-300 transition-colors hover:bg-amber-300/15 disabled:opacity-60',
              AMBER_FOCUS_CLASS,
            )}
          >
            {t('actions.reopen')}
          </button>
        ) : (
          <button
            type="button"
            disabled={!canCloseMessaging || isPending}
            onClick={onClose}
            className={cn(
              'rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-xs font-mono uppercase tracking-[0.18em] text-white transition-colors hover:border-neon-pink/35 disabled:opacity-60',
              CONTROL_FOCUS_CLASS,
            )}
          >
            {t('actions.close')}
          </button>
        )}
      </div>
    </section>
  );
}

function CreateConversationPanel({
  canCreateMessaging,
  initialCustomerRef,
  isPending,
  onSubmit,
  t,
}: {
  canCreateMessaging: boolean;
  initialCustomerRef: string;
  isPending: boolean;
  onSubmit: (payload: AdminMessagingConversationCreateRequest, clientMessageId: string) => void;
  t: MessagingTranslate;
}) {
  const [customerAccountId, setCustomerAccountId] = useState(initialCustomerRef);
  const [subject, setSubject] = useState('');
  const [initialMessage, setInitialMessage] = useState('');
  const [category, setCategory] = useState<MessagingConversationCategory>('support');
  const [priority, setPriority] = useState<MessagingPriority>('normal');
  const [assignedAdminId, setAssignedAdminId] = useState('');
  const [relatedSupportTicketId, setRelatedSupportTicketId] = useState('');
  const [fieldErrors, setFieldErrors] = useState<CreateConversationErrors>({});
  const customerAccountInputRef = useRef<HTMLInputElement>(null);
  const subjectInputRef = useRef<HTMLInputElement>(null);
  const initialMessageInputRef = useRef<HTMLTextAreaElement>(null);

  function clearFieldError(field: CreateConversationField) {
    setFieldErrors((current) => ({ ...current, [field]: undefined }));
  }

  function focusCreateField(field: CreateConversationField) {
    const refs = {
      customer: customerAccountInputRef,
      initialMessage: initialMessageInputRef,
      subject: subjectInputRef,
    };

    refs[field].current?.focus();
  }

  function submitConversation() {
    const errors: CreateConversationErrors = {
      customer: getRequiredTextError(
        customerAccountId,
        t,
        'feedback.customerRequired',
        80,
        'feedback.customerTooLong',
      ) ?? undefined,
      initialMessage: getRequiredTextError(
        initialMessage,
        t,
        'feedback.messageRequired',
        MESSAGE_MAX_LENGTH,
        'feedback.messageTooLong',
      ) ?? undefined,
      subject: getRequiredTextError(
      subject,
      t,
      'feedback.subjectRequired',
      SUBJECT_MAX_LENGTH,
      'feedback.subjectTooLong',
      ) ?? undefined,
    };
    const firstInvalidField = (['customer', 'subject', 'initialMessage'] as const).find(
      (field) => Boolean(errors[field]),
    );

    setFieldErrors(errors);

    if (firstInvalidField) {
      focusCreateField(firstInvalidField);
      return;
    }

    const clientMessageId = createClientMessageId('admin-conversation');

    onSubmit({
      assigned_admin_id: assignedAdminId.trim() || null,
      category,
      customer_account_id: customerAccountId.trim(),
      initial_message: {
        body: initialMessage.trim(),
        client_message_id: clientMessageId,
      },
      priority,
      related_support_ticket_id: relatedSupportTicketId.trim() || null,
      subject: subject.trim(),
    }, clientMessageId);
  }

  return (
    <section className="rounded-2xl border border-neon-cyan/20 bg-neon-cyan/10 p-5">
      <div className="flex items-center gap-3">
        <MessageCirclePlus className="h-5 w-5 text-neon-cyan" />
        <div>
          <h3 className="text-sm font-display uppercase tracking-[0.22em] text-white">
            {t('create.title')}
          </h3>
          <p className="mt-1 text-sm font-mono text-muted-foreground">
            {t('create.description')}
          </p>
        </div>
      </div>

      {!canCreateMessaging ? (
        <div className="mt-4 rounded-xl border border-neon-pink/25 bg-neon-pink/10 p-4 text-sm font-mono text-neon-pink">
          {t('create.readOnly')}
        </div>
      ) : null}

      <form
        data-testid="messaging-create-conversation-form"
        onSubmit={(event) => {
          event.preventDefault();
          submitConversation();
        }}
        className="mt-5 grid gap-3"
      >
        <div className="grid gap-1">
          <input
            ref={customerAccountInputRef}
            value={customerAccountId}
            onChange={(event) => {
              setCustomerAccountId(event.target.value);
              clearFieldError('customer');
            }}
            disabled={!canCreateMessaging || isPending}
            placeholder={t('create.customerPlaceholder')}
            aria-describedby={
              fieldErrors.customer ? 'messaging-create-customer-error' : undefined
            }
            aria-invalid={Boolean(fieldErrors.customer)}
            aria-label={t('create.customer')}
            className={cn(
              'h-11 rounded-md border border-input bg-terminal-bg/70 px-3 py-2 text-sm text-foreground disabled:opacity-60',
              fieldErrors.customer ? 'border-neon-pink/60' : undefined,
              CONTROL_FOCUS_CLASS,
            )}
          />
          {fieldErrors.customer ? (
            <p
              id="messaging-create-customer-error"
              role="alert"
              className="text-xs font-mono leading-5 text-neon-pink"
            >
              {fieldErrors.customer}
            </p>
          ) : null}
        </div>
        <div className="grid gap-1">
          <input
            ref={subjectInputRef}
            value={subject}
            onChange={(event) => {
              setSubject(event.target.value);
              clearFieldError('subject');
            }}
            disabled={!canCreateMessaging || isPending}
            placeholder={t('create.subjectPlaceholder')}
            aria-describedby={
              fieldErrors.subject ? 'messaging-create-subject-error' : undefined
            }
            aria-invalid={Boolean(fieldErrors.subject)}
            aria-label={t('create.subject')}
            className={cn(
              'h-11 rounded-md border border-input bg-terminal-bg/70 px-3 py-2 text-sm text-foreground disabled:opacity-60',
              fieldErrors.subject ? 'border-neon-pink/60' : undefined,
              CONTROL_FOCUS_CLASS,
            )}
          />
          {fieldErrors.subject ? (
            <p
              id="messaging-create-subject-error"
              role="alert"
              className="text-xs font-mono leading-5 text-neon-pink"
            >
              {fieldErrors.subject}
            </p>
          ) : null}
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <select
            value={category}
            onChange={(event) => setCategory(event.target.value as MessagingConversationCategory)}
            disabled={!canCreateMessaging || isPending}
            aria-label={t('create.category')}
            className={cn(
              'h-11 rounded-md border border-input bg-terminal-bg/70 px-3 py-2 text-sm text-foreground disabled:opacity-60',
              CONTROL_FOCUS_CLASS,
            )}
          >
            {MESSAGING_CONVERSATION_CATEGORIES.map((item) => (
              <option key={item} value={item}>
                {t(`categories.${item}`)}
              </option>
            ))}
          </select>
          <select
            value={priority}
            onChange={(event) => setPriority(event.target.value as MessagingPriority)}
            disabled={!canCreateMessaging || isPending}
            aria-label={t('create.priority')}
            className={cn(
              'h-11 rounded-md border border-input bg-terminal-bg/70 px-3 py-2 text-sm text-foreground disabled:opacity-60',
              CONTROL_FOCUS_CLASS,
            )}
          >
            {MESSAGING_PRIORITIES.map((item) => (
              <option key={item} value={item}>
                {t(`priorities.${item}`)}
              </option>
            ))}
          </select>
        </div>
        <input
          value={assignedAdminId}
          onChange={(event) => setAssignedAdminId(event.target.value)}
          disabled={!canCreateMessaging || isPending}
          placeholder={t('create.assignedAdminPlaceholder')}
          aria-label={t('create.assignedAdmin')}
          className={cn(
            'h-11 rounded-md border border-input bg-terminal-bg/70 px-3 py-2 text-sm text-foreground disabled:opacity-60',
            CONTROL_FOCUS_CLASS,
          )}
        />
        <input
          value={relatedSupportTicketId}
          onChange={(event) => setRelatedSupportTicketId(event.target.value)}
          disabled={!canCreateMessaging || isPending}
          placeholder={t('create.relatedSupportPlaceholder')}
          aria-label={t('create.relatedSupport')}
          className={cn(
            'h-11 rounded-md border border-input bg-terminal-bg/70 px-3 py-2 text-sm text-foreground disabled:opacity-60',
            CONTROL_FOCUS_CLASS,
          )}
        />
        <div className="grid gap-1">
          <textarea
            ref={initialMessageInputRef}
            value={initialMessage}
            onChange={(event) => {
              setInitialMessage(event.target.value);
              clearFieldError('initialMessage');
            }}
            disabled={!canCreateMessaging || isPending}
            aria-describedby={
              fieldErrors.initialMessage
                ? 'messaging-create-initial-message-error'
                : undefined
            }
            aria-invalid={Boolean(fieldErrors.initialMessage)}
            aria-label={t('create.initialMessage')}
            placeholder={t('create.initialMessagePlaceholder')}
            className={cn(
              'min-h-28 rounded-xl border border-neon-cyan/25 bg-terminal-bg/70 p-3 text-sm font-mono text-foreground disabled:opacity-60',
              fieldErrors.initialMessage ? 'border-neon-pink/60' : undefined,
              CONTROL_FOCUS_CLASS,
            )}
          />
          {fieldErrors.initialMessage ? (
            <p
              id="messaging-create-initial-message-error"
              role="alert"
              className="text-xs font-mono leading-5 text-neon-pink"
            >
              {fieldErrors.initialMessage}
            </p>
          ) : null}
        </div>
        <button
          type="submit"
          disabled={!canCreateMessaging || isPending}
          className={cn(
            'inline-flex w-fit items-center gap-2 rounded-xl border border-neon-cyan/35 bg-neon-cyan/10 px-4 py-3 text-xs font-mono uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:bg-neon-cyan/15 disabled:opacity-60',
            CONTROL_FOCUS_CLASS,
          )}
        >
          <Send className="h-4 w-4" />
          {isPending ? t('create.creating') : t('create.submit')}
        </button>
      </form>
    </section>
  );
}

function canCancelBroadcastStatus(status: AdminNotificationBroadcastCampaign['status']) {
  return status === 'draft' || status === 'scheduled' || status === 'sending';
}

function BroadcastOperationsPanel({
  canCreateBroadcast,
  history,
  isCancelPending,
  isCreatePending,
  onCancel,
  onSubmit,
  t,
}: {
  canCreateBroadcast: boolean;
  history: AdminNotificationBroadcastCampaign[];
  isCancelPending: boolean;
  isCreatePending: boolean;
  onCancel: (campaignRef: string) => void;
  onSubmit: (input: BroadcastCreateMutationInput) => void;
  t: MessagingTranslate;
}) {
  const [form, setForm] = useState({
    actionUrl: '',
    audienceFilterJson: '{\n  "region": "test"\n}',
    audienceType: 'explicit_customers' as NotificationBroadcastAudienceType,
    body: '',
    confirmationText: '',
    estimatedRecipientCount: '',
    explicitCustomerIds: '',
    name: '',
    scheduledAt: '',
    title: '',
  });
  const [fieldErrors, setFieldErrors] = useState<BroadcastFormErrors>({});
  const [preview, setPreview] = useState<{
    fingerprint: string;
    payload: AdminNotificationBroadcastCreateRequest;
    recipientCount: number;
  } | null>(null);
  const fingerprint = JSON.stringify(form);
  const previewMatches = preview?.fingerprint === fingerprint;
  const isBroadAudience = form.audienceType === 'all_customers' || form.audienceType === 'admins';

  function updateForm<Key extends keyof typeof form>(key: Key, value: (typeof form)[Key]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function buildBroadcastDraft(requireCurrentPreview: boolean) {
    const errors: BroadcastFormErrors = {};
    const trimmedName = form.name.trim();
    const trimmedTitle = form.title.trim();
    const trimmedBody = form.body.trim();
    const trimmedActionUrl = form.actionUrl.trim();
    const estimatedRecipientCount = parsePositiveInteger(form.estimatedRecipientCount);
    let recipientCount = 0;
    let audienceFilter: Record<string, unknown> = {};

    if (!trimmedName) {
      errors.name = t('broadcast.feedback.nameRequired');
    } else if (trimmedName.length > BROADCAST_NAME_MAX_LENGTH) {
      errors.name = t('broadcast.feedback.nameTooLong', { count: BROADCAST_NAME_MAX_LENGTH });
    }

    if (!trimmedTitle) {
      errors.title = t('broadcast.feedback.titleRequired');
    } else if (trimmedTitle.length > BROADCAST_TITLE_MAX_LENGTH) {
      errors.title = t('broadcast.feedback.titleTooLong', { count: BROADCAST_TITLE_MAX_LENGTH });
    }

    if (!trimmedBody) {
      errors.body = t('broadcast.feedback.bodyRequired');
    } else if (trimmedBody.length > BROADCAST_BODY_MAX_LENGTH) {
      errors.body = t('broadcast.feedback.bodyTooLong', { count: BROADCAST_BODY_MAX_LENGTH });
    }

    if (trimmedActionUrl.length > BROADCAST_ACTION_URL_MAX_LENGTH) {
      errors.actionUrl = t('broadcast.feedback.actionUrlTooLong', {
        count: BROADCAST_ACTION_URL_MAX_LENGTH,
      });
    }

    if (form.audienceType === 'explicit_customers') {
      const customerIds = parseExplicitCustomerIds(form.explicitCustomerIds);
      recipientCount = customerIds.length;
      if (!customerIds.length) {
        errors.audience = t('broadcast.feedback.explicitCustomersRequired');
      } else if (customerIds.length > BROADCAST_EXPLICIT_CUSTOMER_LIMIT) {
        errors.audience = t('broadcast.feedback.explicitCustomersTooMany', {
          count: BROADCAST_EXPLICIT_CUSTOMER_LIMIT,
        });
      }
      audienceFilter = {
        customer_account_ids: customerIds,
        estimated_recipient_count: recipientCount,
      };
    } else if (form.audienceType === 'customer_segment') {
      try {
        audienceFilter = parseAudienceFilterJson(form.audienceFilterJson);
      } catch {
        errors.audience = t('broadcast.feedback.filterInvalid');
      }
      if (!Object.keys(audienceFilter).length) {
        errors.audience = t('broadcast.feedback.filterRequired');
      }
      if (estimatedRecipientCount === null) {
        errors.audience = t('broadcast.feedback.recipientEstimateRequired');
      } else {
        recipientCount = estimatedRecipientCount;
        audienceFilter = {
          ...audienceFilter,
          estimated_recipient_count: recipientCount,
        };
      }
    } else {
      if (estimatedRecipientCount === null) {
        errors.audience = t('broadcast.feedback.recipientEstimateRequired');
      } else {
        recipientCount = estimatedRecipientCount;
        audienceFilter = {
          estimated_recipient_count: recipientCount,
        };
      }
    }

    const scheduledAt = toDatetimeIso(form.scheduledAt);
    if (scheduledAt === undefined) {
      errors.scheduledAt = t('broadcast.feedback.scheduledAtInvalid');
    }

    if (isBroadAudience && form.confirmationText.trim() !== BROADCAST_CONFIRM_PHRASE) {
      errors.confirmation = t('broadcast.feedback.confirmationRequired');
    }

    if (requireCurrentPreview && !previewMatches) {
      errors.confirmation = t('broadcast.feedback.previewRequired');
    }

    setFieldErrors(errors);

    if (Object.keys(errors).length) {
      return null;
    }

    return {
      payload: {
        action_url: trimmedActionUrl || null,
        audience_filter: audienceFilter,
        audience_type: form.audienceType,
        body: trimmedBody,
        name: trimmedName,
        scheduled_at: scheduledAt,
        title: trimmedTitle,
      },
      recipientCount,
    };
  }

  function previewBroadcast() {
    const draft = buildBroadcastDraft(false);
    if (!draft) {
      setPreview(null);
      return;
    }

    setPreview({
      fingerprint,
      payload: draft.payload,
      recipientCount: draft.recipientCount,
    });
  }

  return (
    <section className="rounded-2xl border border-amber-300/30 bg-amber-300/10 p-5">
      <div className="flex items-center gap-3">
        <Megaphone className="h-5 w-5 text-amber-300" />
        <div>
          <h3 className="text-sm font-display uppercase tracking-[0.22em] text-white">
            {t('broadcast.title')}
          </h3>
          <p className="mt-1 text-sm font-mono text-muted-foreground">
            {t('broadcast.description')}
          </p>
        </div>
      </div>

      {!canCreateBroadcast ? (
        <div className="mt-4 rounded-xl border border-neon-pink/25 bg-neon-pink/10 p-4 text-sm font-mono text-neon-pink">
          {t('broadcast.readOnly')}
        </div>
      ) : null}

      <form
        data-testid="messaging-broadcast-form"
        onSubmit={(event) => {
          event.preventDefault();
          const draft = buildBroadcastDraft(true);
          if (draft) {
            onSubmit(draft);
          }
        }}
        className="mt-5 grid gap-3"
      >
        <div className="grid gap-1">
          <input
            value={form.name}
            onChange={(event) => updateForm('name', event.target.value)}
            disabled={!canCreateBroadcast || isCreatePending}
            placeholder={t('broadcast.namePlaceholder')}
            aria-describedby={fieldErrors.name ? 'messaging-broadcast-name-error' : undefined}
            aria-invalid={Boolean(fieldErrors.name)}
            aria-label={t('broadcast.name')}
            className={cn(
              'h-11 rounded-md border border-input bg-terminal-bg/70 px-3 py-2 text-sm text-foreground disabled:opacity-60',
              fieldErrors.name ? 'border-neon-pink/60' : undefined,
              AMBER_FOCUS_CLASS,
            )}
          />
          {fieldErrors.name ? (
            <p id="messaging-broadcast-name-error" role="alert" className="text-xs font-mono leading-5 text-neon-pink">
              {fieldErrors.name}
            </p>
          ) : null}
        </div>

        <select
          value={form.audienceType}
          onChange={(event) =>
            updateForm('audienceType', event.target.value as NotificationBroadcastAudienceType)}
          disabled={!canCreateBroadcast || isCreatePending}
          aria-label={t('broadcast.audience')}
          className={cn(
            'h-11 rounded-md border border-input bg-terminal-bg/70 px-3 py-2 text-sm text-foreground disabled:opacity-60',
            AMBER_FOCUS_CLASS,
          )}
        >
          {NOTIFICATION_BROADCAST_AUDIENCE_TYPES.map((item) => (
            <option key={item} value={item}>
              {t(`broadcast.audienceTypes.${item}`)}
            </option>
          ))}
        </select>

        {form.audienceType === 'explicit_customers' ? (
          <textarea
            value={form.explicitCustomerIds}
            onChange={(event) => updateForm('explicitCustomerIds', event.target.value)}
            disabled={!canCreateBroadcast || isCreatePending}
            aria-describedby={fieldErrors.audience ? 'messaging-broadcast-audience-error' : undefined}
            aria-invalid={Boolean(fieldErrors.audience)}
            aria-label={t('broadcast.explicitCustomers')}
            placeholder={t('broadcast.explicitCustomersPlaceholder')}
            className={cn(
              'min-h-24 rounded-xl border border-amber-300/25 bg-terminal-bg/70 p-3 text-sm font-mono text-foreground disabled:opacity-60',
              fieldErrors.audience ? 'border-neon-pink/60' : undefined,
              AMBER_FOCUS_CLASS,
            )}
          />
        ) : null}

        {form.audienceType !== 'explicit_customers' ? (
          <>
            {form.audienceType === 'customer_segment' ? (
              <textarea
                value={form.audienceFilterJson}
                onChange={(event) => updateForm('audienceFilterJson', event.target.value)}
                disabled={!canCreateBroadcast || isCreatePending}
                aria-describedby={fieldErrors.audience ? 'messaging-broadcast-audience-error' : undefined}
                aria-invalid={Boolean(fieldErrors.audience)}
                aria-label={t('broadcast.audienceFilter')}
                className={cn(
                  'min-h-28 rounded-xl border border-amber-300/25 bg-terminal-bg/70 p-3 text-sm font-mono text-foreground disabled:opacity-60',
                  fieldErrors.audience ? 'border-neon-pink/60' : undefined,
                  AMBER_FOCUS_CLASS,
                )}
              />
            ) : null}
            <input
              value={form.estimatedRecipientCount}
              onChange={(event) => updateForm('estimatedRecipientCount', event.target.value)}
              disabled={!canCreateBroadcast || isCreatePending}
              inputMode="numeric"
              aria-describedby={fieldErrors.audience ? 'messaging-broadcast-audience-error' : undefined}
              aria-invalid={Boolean(fieldErrors.audience)}
              aria-label={t('broadcast.recipientEstimate')}
              placeholder={t('broadcast.recipientEstimatePlaceholder')}
              className={cn(
                'h-11 rounded-md border border-input bg-terminal-bg/70 px-3 py-2 text-sm text-foreground disabled:opacity-60',
                fieldErrors.audience ? 'border-neon-pink/60' : undefined,
                AMBER_FOCUS_CLASS,
              )}
            />
          </>
        ) : null}

        {fieldErrors.audience ? (
          <p id="messaging-broadcast-audience-error" role="alert" className="text-xs font-mono leading-5 text-neon-pink">
            {fieldErrors.audience}
          </p>
        ) : null}

        <div className="grid gap-1">
          <input
            value={form.title}
            onChange={(event) => updateForm('title', event.target.value)}
            disabled={!canCreateBroadcast || isCreatePending}
            placeholder={t('broadcast.titlePlaceholder')}
            aria-describedby={fieldErrors.title ? 'messaging-broadcast-title-error' : undefined}
            aria-invalid={Boolean(fieldErrors.title)}
            aria-label={t('broadcast.messageTitle')}
            className={cn(
              'h-11 rounded-md border border-input bg-terminal-bg/70 px-3 py-2 text-sm text-foreground disabled:opacity-60',
              fieldErrors.title ? 'border-neon-pink/60' : undefined,
              AMBER_FOCUS_CLASS,
            )}
          />
          {fieldErrors.title ? (
            <p id="messaging-broadcast-title-error" role="alert" className="text-xs font-mono leading-5 text-neon-pink">
              {fieldErrors.title}
            </p>
          ) : null}
        </div>

        <div className="grid gap-1">
          <textarea
            value={form.body}
            onChange={(event) => updateForm('body', event.target.value)}
            disabled={!canCreateBroadcast || isCreatePending}
            aria-describedby={fieldErrors.body ? 'messaging-broadcast-body-error' : undefined}
            aria-invalid={Boolean(fieldErrors.body)}
            aria-label={t('broadcast.body')}
            placeholder={t('broadcast.bodyPlaceholder')}
            className={cn(
              'min-h-28 rounded-xl border border-amber-300/25 bg-terminal-bg/70 p-3 text-sm font-mono text-foreground disabled:opacity-60',
              fieldErrors.body ? 'border-neon-pink/60' : undefined,
              AMBER_FOCUS_CLASS,
            )}
          />
          {fieldErrors.body ? (
            <p id="messaging-broadcast-body-error" role="alert" className="text-xs font-mono leading-5 text-neon-pink">
              {fieldErrors.body}
            </p>
          ) : null}
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <input
            value={form.actionUrl}
            onChange={(event) => updateForm('actionUrl', event.target.value)}
            disabled={!canCreateBroadcast || isCreatePending}
            placeholder={t('broadcast.actionUrlPlaceholder')}
            aria-describedby={fieldErrors.actionUrl ? 'messaging-broadcast-action-url-error' : undefined}
            aria-invalid={Boolean(fieldErrors.actionUrl)}
            aria-label={t('broadcast.actionUrl')}
            className={cn(
              'h-11 rounded-md border border-input bg-terminal-bg/70 px-3 py-2 text-sm text-foreground disabled:opacity-60',
              fieldErrors.actionUrl ? 'border-neon-pink/60' : undefined,
              AMBER_FOCUS_CLASS,
            )}
          />
          <input
            type="datetime-local"
            value={form.scheduledAt}
            onChange={(event) => updateForm('scheduledAt', event.target.value)}
            disabled={!canCreateBroadcast || isCreatePending}
            aria-describedby={fieldErrors.scheduledAt ? 'messaging-broadcast-scheduled-error' : undefined}
            aria-invalid={Boolean(fieldErrors.scheduledAt)}
            aria-label={t('broadcast.scheduledAt')}
            className={cn(
              'h-11 rounded-md border border-input bg-terminal-bg/70 px-3 py-2 text-sm text-foreground disabled:opacity-60',
              fieldErrors.scheduledAt ? 'border-neon-pink/60' : undefined,
              AMBER_FOCUS_CLASS,
            )}
          />
        </div>
        {fieldErrors.actionUrl ? (
          <p id="messaging-broadcast-action-url-error" role="alert" className="text-xs font-mono leading-5 text-neon-pink">
            {fieldErrors.actionUrl}
          </p>
        ) : null}
        {fieldErrors.scheduledAt ? (
          <p id="messaging-broadcast-scheduled-error" role="alert" className="text-xs font-mono leading-5 text-neon-pink">
            {fieldErrors.scheduledAt}
          </p>
        ) : null}

        {isBroadAudience ? (
          <div className="grid gap-2 rounded-xl border border-neon-pink/25 bg-neon-pink/10 p-4">
            <p className="text-xs font-mono leading-5 text-neon-pink">
              {t('broadcast.broadAudienceWarning', { phrase: BROADCAST_CONFIRM_PHRASE })}
            </p>
            <input
              value={form.confirmationText}
              onChange={(event) => updateForm('confirmationText', event.target.value)}
              disabled={!canCreateBroadcast || isCreatePending}
              aria-describedby={fieldErrors.confirmation ? 'messaging-broadcast-confirmation-error' : undefined}
              aria-invalid={Boolean(fieldErrors.confirmation)}
              aria-label={t('broadcast.confirmation')}
              placeholder={BROADCAST_CONFIRM_PHRASE}
              className={cn(
                'h-11 rounded-md border border-neon-pink/30 bg-terminal-bg/70 px-3 py-2 text-sm text-foreground disabled:opacity-60',
                fieldErrors.confirmation ? 'border-neon-pink/60' : undefined,
                CONTROL_FOCUS_CLASS,
              )}
            />
          </div>
        ) : null}
        {fieldErrors.confirmation ? (
          <p id="messaging-broadcast-confirmation-error" role="alert" className="text-xs font-mono leading-5 text-neon-pink">
            {fieldErrors.confirmation}
          </p>
        ) : null}

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={previewBroadcast}
            disabled={!canCreateBroadcast || isCreatePending}
            className={cn(
              'inline-flex w-fit items-center gap-2 rounded-xl border border-amber-300/35 bg-amber-300/10 px-4 py-3 text-xs font-mono uppercase tracking-[0.18em] text-amber-300 transition-colors hover:bg-amber-300/15 disabled:opacity-60',
              AMBER_FOCUS_CLASS,
            )}
          >
            <Eye className="h-4 w-4" />
            {t('broadcast.preview')}
          </button>
          <button
            type="submit"
            disabled={!canCreateBroadcast || isCreatePending || !previewMatches}
            className={cn(
              'inline-flex w-fit items-center gap-2 rounded-xl border border-neon-cyan/35 bg-neon-cyan/10 px-4 py-3 text-xs font-mono uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:bg-neon-cyan/15 disabled:opacity-60',
              CONTROL_FOCUS_CLASS,
            )}
          >
            <Send className="h-4 w-4" />
            {isCreatePending ? t('broadcast.creating') : t('broadcast.submit')}
          </button>
        </div>
      </form>

      {preview ? (
        <div
          data-testid="messaging-broadcast-preview"
          className={cn(
            'mt-4 rounded-xl border p-4',
            previewMatches
              ? 'border-amber-300/25 bg-terminal-bg/55'
              : 'border-neon-pink/25 bg-neon-pink/10',
          )}
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs font-display uppercase tracking-[0.18em] text-white">
              {t('broadcast.previewTitle')}
            </p>
            <MessagingStatusChip
              label={previewMatches ? t('broadcast.previewReady') : t('broadcast.previewStale')}
              tone={previewMatches ? 'success' : 'warning'}
            />
          </div>
          <div className="mt-3 grid gap-3 text-sm font-mono leading-6 text-muted-foreground">
            <p className="text-white">{preview.payload.title}</p>
            <p>{preview.payload.body}</p>
            <p>
              {t('broadcast.recipientCount')}{' '}
              <span data-testid="messaging-broadcast-recipient-count" className="text-amber-200">
                {preview.recipientCount}
              </span>
            </p>
            <p>{t(`broadcast.audienceTypes.${preview.payload.audience_type}`)}</p>
            {preview.payload.action_url ? <p>{preview.payload.action_url}</p> : null}
          </div>
        </div>
      ) : null}

      <div className="mt-5">
        <h4 className="text-xs font-display uppercase tracking-[0.18em] text-white">
          {t('broadcast.historyTitle')}
        </h4>
        <div className="mt-3 grid gap-3">
          {history.length ? (
            history.map((campaign) => (
              <article
                key={campaign.id}
                className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                      {campaign.name}
                    </p>
                    <p className="mt-1 text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                      {campaign.public_id}
                    </p>
                  </div>
                  <MessagingStatusChip
                    label={t(`broadcast.statuses.${campaign.status}`)}
                    tone={campaign.status === 'cancelled' || campaign.status === 'failed' ? 'danger' : 'info'}
                  />
                </div>
                <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                  {campaign.title}
                </p>
                {canCancelBroadcastStatus(campaign.status) ? (
                  <button
                    type="button"
                    onClick={() => onCancel(campaign.public_id)}
                    disabled={!canCreateBroadcast || isCancelPending}
                    className={cn(
                      'mt-3 rounded-xl border border-neon-pink/35 bg-neon-pink/10 px-3 py-2 text-xs font-mono uppercase tracking-[0.16em] text-neon-pink transition-colors hover:bg-neon-pink/15 disabled:opacity-60',
                      CONTROL_FOCUS_CLASS,
                    )}
                  >
                    {isCancelPending ? t('broadcast.cancelling') : t('broadcast.cancel')}
                  </button>
                ) : null}
              </article>
            ))
          ) : (
            <p className="rounded-xl border border-dashed border-grid-line/25 bg-terminal-bg/35 px-4 py-5 text-sm font-mono text-muted-foreground">
              {t('broadcast.historyEmpty')}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

interface MessagingConsoleProps {
  initialConversationRef?: string;
  initialSearchParams?: MessagingSearchParams;
}

export function MessagingConsole({
  initialConversationRef,
  initialSearchParams,
}: MessagingConsoleProps) {
  const t = useTranslations('Messaging');
  const locale = useLocale();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [initialFilters] = useState(() => getInitialFilters(initialSearchParams));
  const [search, setSearch] = useState(initialFilters.search);
  const [customerFilter, setCustomerFilter] = useState(initialFilters.customerFilter);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>(initialFilters.statusFilter);
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>(
    initialFilters.categoryFilter,
  );
  const [priorityFilter, setPriorityFilter] = useState<PriorityFilter>(
    initialFilters.priorityFilter,
  );
  const [assignmentFilter, setAssignmentFilter] = useState<AssignmentFilter>(
    initialFilters.assignmentFilter,
  );
  const [selectedConversationRef, setSelectedConversationRef] = useState<string | null>(
    initialConversationRef ?? null,
  );
  const [publicReplyDraft, setPublicReplyDraft] = useState('');
  const [internalNoteDraft, setInternalNoteDraft] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);
  const [broadcastHistory, setBroadcastHistory] = useState<AdminNotificationBroadcastCampaign[]>([]);
  const [realtimeState, setRealtimeState] = useState<RealtimeState>(() =>
    typeof EventSource === 'undefined' ? 'offline' : 'connecting',
  );
  const [paginationState, setPaginationState] = useState<PaginationState>(EMPTY_PAGINATION_STATE);
  const deferredSearch = useDeferredValue(search);
  const deferredCustomerFilter = useDeferredValue(customerFilter);
  const messagingUrlQuery = buildMessagingUrlQuery({
    assignmentFilter,
    categoryFilter,
    customerFilter: deferredCustomerFilter,
    priorityFilter,
    search: deferredSearch,
    statusFilter,
  });

  useEffect(() => {
    const query = buildMessagingUrlQuery({
      assignmentFilter,
      categoryFilter,
      customerFilter: deferredCustomerFilter,
      priorityFilter,
      search: deferredSearch,
      statusFilter,
    });
    const conversationPath = selectedConversationRef
      ? safeConversationRoute(selectedConversationRef)
      : '/messaging';

    router.replace(buildMessagingHref(conversationPath, query), { scroll: false });
  }, [
    assignmentFilter,
    categoryFilter,
    deferredCustomerFilter,
    deferredSearch,
    priorityFilter,
    router,
    selectedConversationRef,
    statusFilter,
  ]);

  const sessionQuery = useQuery({
    queryKey: ['messaging', 'session'],
    queryFn: async () => {
      const response = await authApi.session();
      return response.data;
    },
    staleTime: 30_000,
  });

  const role = sessionQuery.data?.role;
  const canReadMessaging = hasAdminPermission(role, 'messaging_conversation_read');
  const canCreateMessaging = hasAdminPermission(role, 'messaging_conversation_create');
  const canWriteMessage = hasAdminPermission(role, 'messaging_message_write');
  const canWriteInternalNote = hasAdminPermission(role, 'messaging_internal_note_write');
  const canAssignMessaging = hasAdminPermission(role, 'messaging_conversation_assign');
  const canCloseMessaging = hasAdminPermission(role, 'messaging_conversation_close');
  const canCreateBroadcast = hasAdminPermission(role, 'notification_broadcast_create');
  const assignedAdminId =
    assignmentFilter === 'mine' && sessionQuery.data?.id
      ? sessionQuery.data.id
      : undefined;

  const listParams = buildListParams({
    assignedAdminId,
    categoryFilter,
    customerFilter: deferredCustomerFilter,
    deferredSearch,
    priorityFilter,
    statusFilter,
  });
  const paginationScopeKey = JSON.stringify([
    assignedAdminId ?? '',
    assignmentFilter,
    categoryFilter,
    deferredCustomerFilter,
    deferredSearch,
    priorityFilter,
    statusFilter,
  ]);

  const conversationsQuery = useQuery({
    queryKey: ['messaging', 'admin', 'conversations', listParams],
    queryFn: async () => {
      const response = await messagingApi.listAdminConversations(listParams);
      return response.data;
    },
    enabled: canReadMessaging,
    staleTime: 12_000,
  });

  const loadMoreConversationsMutation = useMutation({
    mutationFn: async (cursor: string) => {
      const response = await messagingApi.listAdminConversations({
        ...listParams,
        cursor,
      });
      return response.data;
    },
    onSuccess: (data) => {
      setPaginationState((current) => ({
        extraConversations: mergeConversationPages([
          ...(current.scopeKey === paginationScopeKey ? current.extraConversations : []),
          ...data.conversations,
        ]),
        hasLoadedExtra: true,
        nextCursor: getNextCursor(data),
        scopeKey: paginationScopeKey,
      }));
    },
    onError: (error) => {
      setFeedback(getMessagingErrorMessage(error, t('common.actionFailed')));
    },
  });

  const scopedPaginationState = paginationState.scopeKey === paginationScopeKey
    ? paginationState
    : EMPTY_PAGINATION_STATE;
  const firstPageNextCursor = getNextCursor(conversationsQuery.data);
  const activeNextCursor = scopedPaginationState.hasLoadedExtra
    ? scopedPaginationState.nextCursor
    : firstPageNextCursor;
  const serverConversations = mergeConversationPages([
    ...(conversationsQuery.data?.conversations ?? []),
    ...scopedPaginationState.extraConversations,
  ]);
  const visibleConversations = assignmentFilter === 'unassigned'
    ? serverConversations.filter((conversation) => !conversation.assigned_admin_id)
    : serverConversations;
  const effectiveConversationRef =
    selectedConversationRef
    ?? initialConversationRef
    ?? visibleConversations[0]?.public_id
    ?? null;

  const detailQuery = useQuery({
    queryKey: ['messaging', 'admin', 'conversations', effectiveConversationRef, 'detail'],
    queryFn: async () => {
      const response = await messagingApi.getAdminConversation(effectiveConversationRef!);
      return response.data;
    },
    enabled: canReadMessaging && Boolean(effectiveConversationRef),
    staleTime: 10_000,
  });

  async function refreshMessagingData(conversationRef: string | null) {
    setPaginationState(EMPTY_PAGINATION_STATE);
    await queryClient.invalidateQueries({ queryKey: ['messaging', 'admin', 'conversations'] });
    if (conversationRef) {
      await queryClient.invalidateQueries({
        queryKey: ['messaging', 'admin', 'conversations', conversationRef, 'detail'],
      });
    }
  }

  useEffect(() => {
    if (!canReadMessaging || typeof EventSource === 'undefined') {
      return undefined;
    }

    const eventSource = new EventSource('/api/v1/admin/messaging/realtime/sse', {
      withCredentials: true,
    });
    const refreshFromRealtime = () => {
      setPaginationState(EMPTY_PAGINATION_STATE);
      void queryClient.invalidateQueries({ queryKey: ['messaging', 'admin', 'conversations'] });
      if (effectiveConversationRef) {
        void queryClient.invalidateQueries({
          queryKey: ['messaging', 'admin', 'conversations', effectiveConversationRef, 'detail'],
        });
      }
    };

    eventSource.onopen = () => setRealtimeState('connected');
    eventSource.onerror = () => setRealtimeState('offline');
    eventSource.addEventListener('message', refreshFromRealtime);
    eventSource.addEventListener('sync_required', refreshFromRealtime);

    return () => {
      eventSource.close();
    };
  }, [canReadMessaging, effectiveConversationRef, queryClient]);

  const createConversationMutation = useMutation({
    mutationFn: async ({
      clientMessageId,
      payload,
    }: {
      clientMessageId: string;
      payload: AdminMessagingConversationCreateRequest;
    }) => {
      const response = await messagingApi.createAdminConversation(payload, clientMessageId);
      return response.data;
    },
    onSuccess: async (conversation) => {
      setSelectedConversationRef(conversation.public_id);
      setFeedback(t('feedback.conversationCreated'));
      await refreshMessagingData(conversation.public_id);
    },
    onError: (error) => {
      setFeedback(getMessagingErrorMessage(error, t('common.actionFailed')));
    },
  });

  const publicReplyMutation = useMutation({
    mutationFn: async () => {
      if (!effectiveConversationRef) {
        throw new Error(t('feedback.selectConversation'));
      }
      const clientMessageId = createClientMessageId('admin-message');
      const body = validateRequiredText(
        publicReplyDraft,
        t,
        'feedback.messageRequired',
        MESSAGE_MAX_LENGTH,
        'feedback.messageTooLong',
      );
      const response = await messagingApi.addAdminMessage(
        effectiveConversationRef,
        { body, client_message_id: clientMessageId },
        clientMessageId,
      );
      return response.data;
    },
    onSuccess: async (result) => {
      setPublicReplyDraft('');
      setFeedback(t('feedback.publicReplySent'));
      await refreshMessagingData(result.conversation.public_id);
    },
    onError: (error) => {
      setFeedback(getMessagingErrorMessage(error, t('common.actionFailed')));
    },
  });

  const internalNoteMutation = useMutation({
    mutationFn: async () => {
      if (!effectiveConversationRef) {
        throw new Error(t('feedback.selectConversation'));
      }
      const clientMessageId = createClientMessageId('admin-note');
      const body = validateRequiredText(
        internalNoteDraft,
        t,
        'feedback.messageRequired',
        MESSAGE_MAX_LENGTH,
        'feedback.messageTooLong',
      );
      const response = await messagingApi.addAdminInternalNote(
        effectiveConversationRef,
        { body, client_message_id: clientMessageId },
        clientMessageId,
      );
      return response.data;
    },
    onSuccess: async (result) => {
      setInternalNoteDraft('');
      setFeedback(t('feedback.internalNoteSaved'));
      await refreshMessagingData(result.conversation.public_id);
    },
    onError: (error) => {
      setFeedback(getMessagingErrorMessage(error, t('common.actionFailed')));
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ payload }: UpdateMutationInput) => {
      if (!effectiveConversationRef) {
        throw new Error(t('feedback.selectConversation'));
      }
      const response = await messagingApi.updateAdminConversation(effectiveConversationRef, payload);
      return response.data;
    },
    onSuccess: async (conversation, variables) => {
      setFeedback(t(variables.feedbackKey));
      await refreshMessagingData(conversation.public_id);
    },
    onError: (error) => {
      setFeedback(getMessagingErrorMessage(error, t('common.actionFailed')));
    },
  });

  const closeMutation = useMutation({
    mutationFn: async ({ mode }: { mode: 'close' | 'reopen' }) => {
      if (!effectiveConversationRef) {
        throw new Error(t('feedback.selectConversation'));
      }
      const response = mode === 'close'
        ? await messagingApi.closeAdminConversation(effectiveConversationRef)
        : await messagingApi.reopenAdminConversation(effectiveConversationRef);
      return response.data;
    },
    onSuccess: async (conversation) => {
      setFeedback(
        conversation.status === 'closed'
          ? t('feedback.conversationClosed')
          : t('feedback.conversationReopened'),
      );
      await refreshMessagingData(conversation.public_id);
    },
    onError: (error) => {
      setFeedback(getMessagingErrorMessage(error, t('common.actionFailed')));
    },
  });

  const createBroadcastMutation = useMutation({
    mutationFn: async ({ payload }: BroadcastCreateMutationInput) => {
      const response = await messagingApi.createAdminNotificationBroadcast(payload);
      return response.data;
    },
    onSuccess: (campaign, variables) => {
      setBroadcastHistory((current) => upsertBroadcastHistory(current, campaign));
      setFeedback(
        t('feedback.broadcastCreated', {
          count: variables.recipientCount,
          publicId: campaign.public_id,
        }),
      );
    },
    onError: (error) => {
      setFeedback(getMessagingErrorMessage(error, t('common.actionFailed')));
    },
  });

  const cancelBroadcastMutation = useMutation({
    mutationFn: async (campaignRef: string) => {
      const response = await messagingApi.cancelAdminNotificationBroadcast(campaignRef);
      return response.data;
    },
    onSuccess: (campaign) => {
      setBroadcastHistory((current) => upsertBroadcastHistory(current, campaign));
      setFeedback(t('feedback.broadcastCancelled', { publicId: campaign.public_id }));
    },
    onError: (error) => {
      setFeedback(getMessagingErrorMessage(error, t('common.actionFailed')));
    },
  });

  function submitMetadataUpdate(payload: AdminMessagingConversationUpdateRequest) {
    updateMutation.mutate({
      feedbackKey: 'feedback.conversationUpdated',
      payload,
    });
  }

  const selectedConversation = detailQuery.data ?? null;
  const isClosedReadOnly = selectedConversation?.status === 'closed';
  const internalNoteCount =
    selectedConversation?.messages.filter((message) => message.visibility === 'internal').length ?? 0;
  const waitingAdminCount = visibleConversations.filter(hasUnreadSignal).length;
  const activeCount = visibleConversations.filter(
    (conversation) => conversation.status === 'open',
  ).length;

  if (sessionQuery.isLoading) {
    return (
      <MessagingPageShell
        eyebrow={t('inbox.eyebrow')}
        title={t('inbox.title')}
        description={t('inbox.description')}
        icon={Inbox}
      >
        <LoadingRows />
      </MessagingPageShell>
    );
  }

  if (!canReadMessaging) {
    return (
      <MessagingPageShell
        eyebrow={t('inbox.eyebrow')}
        title={t('inbox.title')}
        description={t('inbox.description')}
        icon={Inbox}
      >
        <PermissionDeniedState t={t} />
      </MessagingPageShell>
    );
  }

  return (
    <MessagingPageShell
      eyebrow={t('inbox.eyebrow')}
      title={t('inbox.title')}
      description={t('inbox.description')}
      icon={Inbox}
      actions={
        <button
          type="button"
          aria-label={t('common.refresh')}
          onClick={() => void refreshMessagingData(effectiveConversationRef)}
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
          value: String(visibleConversations.length),
          hint: t('metrics.visibleHint'),
          tone: 'info',
        },
        {
          label: t('metrics.waitingAdmin'),
          value: String(waitingAdminCount),
          hint: t('metrics.waitingAdminHint'),
          tone: waitingAdminCount ? 'danger' : 'success',
        },
        {
          label: t('metrics.open'),
          value: String(activeCount),
          hint: t('metrics.openHint'),
          tone: activeCount ? 'warning' : 'neutral',
        },
        {
          label: t('metrics.presence'),
          value: t(`realtime.${realtimeState}`),
          hint: t('metrics.presenceHint'),
          tone: realtimeState === 'connected' ? 'success' : 'warning',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          <div className="grid gap-3 lg:grid-cols-[minmax(14rem,1fr)_minmax(12rem,16rem)_repeat(3,minmax(8rem,10rem))]">
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

            <input
              value={customerFilter}
              onChange={(event) => setCustomerFilter(event.target.value)}
              placeholder={t('filters.customerPlaceholder')}
              aria-label={t('filters.customer')}
              className={cn(
                'h-11 rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground',
                CONTROL_FOCUS_CLASS,
              )}
            />

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
              {MESSAGING_CONVERSATION_STATUSES.map((status) => (
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
              {MESSAGING_PRIORITIES.map((priority) => (
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
              {MESSAGING_CONVERSATION_CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {t(`categories.${category}`)}
                </option>
              ))}
            </select>
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {ASSIGNMENT_FILTERS.map((assignment) => (
              <button
                key={assignment}
                type="button"
                aria-pressed={assignmentFilter === assignment}
                onClick={() => setAssignmentFilter(assignment)}
                className={cn(
                  'rounded-xl px-3 py-2 text-xs font-mono uppercase tracking-[0.16em]',
                  assignmentFilter === assignment
                    ? 'border border-neon-cyan/35 bg-neon-cyan/10 text-neon-cyan'
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
              {t('filters.assignment.unassignedScopeHint', { count: MESSAGING_LIST_LIMIT })}
            </p>
          ) : null}

          {conversationsQuery.isError ? (
            <div className="mt-4 rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
              {getMessagingErrorMessage(conversationsQuery.error, t('list.loadError'))}
            </div>
          ) : null}

          <div className="mt-5">
            {conversationsQuery.isLoading ? (
              <LoadingRows />
            ) : visibleConversations.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-10 text-center">
                <Inbox className="mx-auto h-8 w-8 text-muted-foreground" />
                <p className="mt-3 text-sm font-mono text-muted-foreground">
                  {t('list.empty')}
                </p>
              </div>
            ) : (
              <ConversationList
                activeConversationRef={effectiveConversationRef}
                conversations={visibleConversations}
                locale={locale}
                onSelect={setSelectedConversationRef}
                query={messagingUrlQuery}
                t={t}
              />
            )}
          </div>

          {!conversationsQuery.isLoading && !conversationsQuery.isError && (
            activeNextCursor || visibleConversations.length > 0
          ) ? (
            <div
              data-testid="messaging-pagination-state"
              className="mt-4 flex flex-col gap-3 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-xs font-mono leading-5 text-muted-foreground md:flex-row md:items-center md:justify-between"
            >
              <p>
                {activeNextCursor
                  ? t('list.nextPageAvailable', { count: MESSAGING_LIST_LIMIT })
                  : t('list.endOfQueue', { count: visibleConversations.length })}
              </p>
              {activeNextCursor ? (
                <button
                  type="button"
                  data-testid="messaging-load-more"
                  disabled={loadMoreConversationsMutation.isPending}
                  onClick={() => loadMoreConversationsMutation.mutate(activeNextCursor)}
                  className={cn(
                    'inline-flex w-fit items-center gap-2 rounded-xl border border-neon-cyan/35 bg-neon-cyan/10 px-3 py-2 text-xs font-mono uppercase tracking-[0.16em] text-neon-cyan transition-colors hover:bg-neon-cyan/15 disabled:opacity-60',
                    CONTROL_FOCUS_CLASS,
                  )}
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  {loadMoreConversationsMutation.isPending
                    ? t('list.loadingMore')
                    : t('list.loadMore')}
                </button>
              ) : null}
            </div>
          ) : null}
        </section>

        <aside className="grid gap-5 xl:col-span-5">
          <CreateConversationPanel
            key={deferredCustomerFilter}
            canCreateMessaging={canCreateMessaging}
            initialCustomerRef={deferredCustomerFilter}
            isPending={createConversationMutation.isPending}
            onSubmit={(payload, clientMessageId) =>
              createConversationMutation.mutate({ clientMessageId, payload })}
            t={t}
          />

          <BroadcastOperationsPanel
            canCreateBroadcast={canCreateBroadcast}
            history={broadcastHistory}
            isCancelPending={cancelBroadcastMutation.isPending}
            isCreatePending={createBroadcastMutation.isPending}
            onCancel={(campaignRef) => cancelBroadcastMutation.mutate(campaignRef)}
            onSubmit={(input) => createBroadcastMutation.mutate(input)}
            t={t}
          />

          <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <div className="flex items-center gap-3">
              <RadioTower className="h-5 w-5 text-neon-cyan" />
              <div>
                <h3 className="text-sm font-display uppercase tracking-[0.22em] text-white">
                  {t('realtime.title')}
                </h3>
                <p className="mt-1 text-sm font-mono text-muted-foreground">
                  {t('realtime.description')}
                </p>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <MessagingStatusChip
                label={t(`realtime.${realtimeState}`)}
                tone={realtimeState === 'connected' ? 'success' : 'warning'}
              />
              <MessagingStatusChip label={t('realtime.privacy')} tone="neutral" />
            </div>
          </section>

          {detailQuery.isLoading ? (
            <DetailSkeleton />
          ) : detailQuery.isError ? (
            <div className="rounded-2xl border border-neon-pink/30 bg-neon-pink/10 p-5 text-sm font-mono text-neon-pink">
              {getMessagingErrorMessage(detailQuery.error, t('detail.loadError'))}
            </div>
          ) : !selectedConversation ? (
            <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-surface/35 p-8 text-center">
              <AlertTriangle className="mx-auto h-9 w-9 text-muted-foreground" />
              <p className="mt-3 text-sm font-mono text-muted-foreground">
                {t('detail.empty')}
              </p>
            </div>
          ) : (
            <>
              <ConversationHeader conversation={selectedConversation} locale={locale} t={t} />

              <ConversationControlsPanel
                key={selectedConversation.id}
                canAssignMessaging={canAssignMessaging}
                canCloseMessaging={canCloseMessaging}
                conversation={selectedConversation}
                isClosedReadOnly={Boolean(isClosedReadOnly)}
                isPending={updateMutation.isPending || closeMutation.isPending}
                onClose={() => closeMutation.mutate({ mode: 'close' })}
                onReopen={() => closeMutation.mutate({ mode: 'reopen' })}
                onSubmit={submitMetadataUpdate}
                t={t}
              />

              <section className="grid gap-5">
                <PublicPreviewPanel conversation={selectedConversation} t={t} />

                <form
                  data-testid="messaging-public-reply-composer"
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
                    disabled={!canWriteMessage || isClosedReadOnly}
                    aria-label={t('reply.message')}
                    placeholder={t('reply.placeholder')}
                    className={cn(
                      'mt-4 min-h-28 w-full rounded-xl border border-neon-cyan/25 bg-terminal-bg/70 p-3 text-sm font-mono text-foreground disabled:opacity-60',
                      CONTROL_FOCUS_CLASS,
                    )}
                  />
                  <button
                    type="submit"
                    disabled={!canWriteMessage || isClosedReadOnly || publicReplyMutation.isPending}
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
                  data-testid="messaging-internal-note-composer"
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
                    disabled={!canWriteInternalNote || isClosedReadOnly}
                    aria-label={t('internalNote.message')}
                    placeholder={t('internalNote.placeholder')}
                    className={cn(
                      'mt-4 min-h-28 w-full rounded-xl border border-amber-300/25 bg-terminal-bg/70 p-3 text-sm font-mono text-foreground disabled:opacity-60',
                      AMBER_FOCUS_CLASS,
                    )}
                  />
                  <button
                    type="submit"
                    disabled={
                      !canWriteInternalNote || isClosedReadOnly || internalNoteMutation.isPending
                    }
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
                data-testid="messaging-live-region"
              >
                {feedback ?? ''}
              </div>

              {feedback ? (
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/65 px-4 py-3 text-sm font-mono text-foreground">
                  {feedback}
                </div>
              ) : null}

              <ConversationTimeline conversation={selectedConversation} locale={locale} t={t} />
              <ReadStatePanel conversation={selectedConversation} locale={locale} t={t} />
              <div className="sr-only" data-testid="messaging-internal-note-count">
                {internalNoteCount}
              </div>
            </>
          )}
        </aside>
      </div>
    </MessagingPageShell>
  );
}
