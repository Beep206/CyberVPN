'use client';

import { useDeferredValue, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  FileText,
  LockKeyhole,
  RefreshCw,
  Search,
  ShieldCheck,
  Trash2,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Link, useRouter } from '@/i18n/navigation';
import { authApi } from '@/lib/api/auth';
import {
  adminPrivacyRequestsApi,
  PRIVACY_REQUEST_STATUSES,
  PRIVACY_REQUEST_TYPES,
  type AdminPrivacyRequestDetail,
  type AdminPrivacyRequestListParams,
  type AdminPrivacyRequestSummary,
  type PrivacyRequestStatus,
  type PrivacyRequestType,
} from '@/lib/api/privacy-requests';
import { cn } from '@/lib/utils';
import { hasAdminPermission } from '@/shared/lib/admin-rbac';

type PrivacyRequestsTranslate = (key: string, values?: Record<string, string | number>) => string;
type StatusFilter = 'all' | PrivacyRequestStatus;
type TypeFilter = 'all' | PrivacyRequestType;
type AssignmentFilter = 'all' | 'mine' | 'unassigned';
type SearchParams = Record<string, string | string[] | undefined>;

const STATUS_FILTERS = ['all', ...PRIVACY_REQUEST_STATUSES] as const;
const TYPE_FILTERS = ['all', ...PRIVACY_REQUEST_TYPES] as const;
const ASSIGNMENT_FILTERS = ['all', 'mine', 'unassigned'] as const;
const LIST_LIMIT = 50;
const CONTROL_FOCUS_CLASS =
  'outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg';

function readSearchParam(searchParams: SearchParams | undefined, key: string) {
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

function getInitialFilters(searchParams: SearchParams | undefined) {
  return {
    assignmentFilter: readAllowedValue(
      readSearchParam(searchParams, 'assignment'),
      ASSIGNMENT_FILTERS,
      'all',
    ),
    search: readSearchParam(searchParams, 'q')?.slice(0, 120) ?? '',
    statusFilter: readAllowedValue(
      readSearchParam(searchParams, 'status'),
      STATUS_FILTERS,
      'all',
    ),
    typeFilter: readAllowedValue(
      readSearchParam(searchParams, 'request_type'),
      TYPE_FILTERS,
      'all',
    ),
  };
}

function buildUrlQuery({
  assignmentFilter,
  search,
  statusFilter,
  typeFilter,
}: {
  assignmentFilter: AssignmentFilter;
  search: string;
  statusFilter: StatusFilter;
  typeFilter: TypeFilter;
}) {
  const query: Record<string, string> = {};
  const trimmed = search.trim();
  if (trimmed) query.q = trimmed;
  if (statusFilter !== 'all') query.status = statusFilter;
  if (typeFilter !== 'all') query.request_type = typeFilter;
  if (assignmentFilter !== 'all') query.assignment = assignmentFilter;
  return query;
}

function buildHref(pathname: string, query: Record<string, string>) {
  const searchParams = new URLSearchParams(query);
  const searchString = searchParams.toString();
  return searchString ? `${pathname}?${searchString}` : pathname;
}

function safePrivacyRoute(reference: string) {
  return `/privacy-requests/${encodeURIComponent(reference)}`;
}

function safeSupportRoute(reference: string) {
  return `/support/${encodeURIComponent(reference)}`;
}

function formatDateTime(value: string | null | undefined, locale: string) {
  if (!value) return 'n/a';
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function statusTone(status: PrivacyRequestStatus) {
  if (status === 'failed') return 'danger';
  if (status === 'fulfilled') return 'success';
  if (status === 'denied' || status === 'canceled') return 'muted';
  if (status === 'approved' || status === 'scheduled') return 'warning';
  return 'info';
}

function StatusChip({
  label,
  tone,
}: {
  label: string;
  tone: 'danger' | 'info' | 'muted' | 'success' | 'warning';
}) {
  return (
    <span
      className={cn(
        'inline-flex min-h-7 items-center rounded-full border px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.14em]',
        tone === 'danger' && 'border-red-400/35 bg-red-500/10 text-red-200',
        tone === 'info' && 'border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan',
        tone === 'muted' && 'border-grid-line/35 bg-terminal-bg/50 text-muted-foreground',
        tone === 'success' && 'border-matrix-green/30 bg-matrix-green/10 text-matrix-green',
        tone === 'warning' && 'border-amber-300/35 bg-amber-300/10 text-amber-200',
      )}
    >
      {label}
    </span>
  );
}

function PermissionDeniedState({ t }: { t: PrivacyRequestsTranslate }) {
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

function buildListParams({
  assignedAdminId,
  deferredSearch,
  statusFilter,
  typeFilter,
}: {
  assignedAdminId?: string;
  deferredSearch: string;
  statusFilter: StatusFilter;
  typeFilter: TypeFilter;
}): AdminPrivacyRequestListParams {
  return {
    assigned_admin_id: assignedAdminId,
    limit: LIST_LIMIT,
    query: deferredSearch.trim() || undefined,
    request_type: typeFilter === 'all' ? undefined : typeFilter,
    status: statusFilter === 'all' ? undefined : statusFilter,
  };
}

function RequestList({
  activeReference,
  locale,
  onSelect,
  query,
  requests,
  t,
}: {
  activeReference: string | null;
  locale: string;
  onSelect: (reference: string) => void;
  query: Record<string, string>;
  requests: readonly AdminPrivacyRequestSummary[];
  t: PrivacyRequestsTranslate;
}) {
  if (requests.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/45 px-4 py-10 text-center font-mono text-sm text-muted-foreground">
        {t('list.empty')}
      </div>
    );
  }

  return (
    <div className="grid gap-3">
      {requests.map((request) => {
        const isActive = request.privacy_request_reference === activeReference;
        return (
          <article
            key={request.privacy_request_reference}
            className={cn(
              'rounded-2xl border border-grid-line/20 bg-terminal-bg/55 p-4',
              isActive ? 'border-neon-cyan/50 bg-neon-cyan/10' : undefined,
            )}
          >
            <button
              type="button"
              onClick={() => onSelect(request.privacy_request_reference)}
              className={cn('block w-full rounded-xl p-1 text-left', CONTROL_FOCUS_CLASS)}
              aria-current={isActive ? 'true' : undefined}
            >
              <span className="block break-all font-display text-sm uppercase tracking-[0.16em] text-white">
                {request.privacy_request_reference}
              </span>
              <span className="mt-1 block text-xs font-mono uppercase tracking-[0.14em] text-muted-foreground">
                {t(`types.${request.request_type}`)} / {request.safe_customer_reference}
              </span>
            </button>
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusChip
                label={t(`statuses.${request.status}`)}
                tone={statusTone(request.status)}
              />
              {request.overdue ? (
                <StatusChip label={t('list.overdue')} tone="danger" />
              ) : null}
            </div>
            <div className="mt-4 grid gap-2 text-xs font-mono text-muted-foreground">
              <span>{t('list.submitted', { value: formatDateTime(request.submitted_at, locale) })}</span>
              <span>{t('list.support', { reference: request.ticket_reference ?? 'n/a' })}</span>
            </div>
            <Link
              href={buildHref(safePrivacyRoute(request.privacy_request_reference), query)}
              className={cn(
                'mt-4 inline-flex rounded-xl border border-grid-line/30 bg-terminal-bg/60 px-3 py-2 text-xs font-mono uppercase tracking-[0.16em] text-neon-cyan transition-colors hover:border-neon-cyan/40 hover:text-white',
                CONTROL_FOCUS_CLASS,
              )}
            >
              {t('list.open')}
            </Link>
          </article>
        );
      })}
    </div>
  );
}

function DetailPanel({
  detail,
  isLoading,
  locale,
  onAction,
  t,
}: {
  detail?: AdminPrivacyRequestDetail;
  isLoading: boolean;
  locale: string;
  onAction: (action: string) => void;
  t: PrivacyRequestsTranslate;
}) {
  if (isLoading) {
    return (
      <div className="grid gap-4" data-testid="privacy-detail-loading-state">
        <div className="h-32 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45" />
        <div className="h-72 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45" />
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/45 px-4 py-10 text-center font-mono text-sm text-muted-foreground">
        {t('detail.empty')}
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      <section className="rounded-2xl border border-grid-line/20 bg-terminal-bg/55 p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.22em] text-neon-cyan">
              {detail.privacy_request_reference}
            </p>
            <h2 className="mt-2 text-xl font-display uppercase tracking-[0.16em] text-white">
              {t(`types.${detail.request_type}`)}
            </h2>
            <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
              {t('detail.safeCustomer', { value: detail.safe_customer_reference })}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusChip label={t(`statuses.${detail.status}`)} tone={statusTone(detail.status)} />
            {detail.overdue ? <StatusChip label={t('list.overdue')} tone="danger" /> : null}
          </div>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-3">
          <div className="rounded-xl border border-grid-line/20 bg-terminal-surface/35 p-3">
            <p className="text-[11px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
              {t('detail.submittedAt')}
            </p>
            <p className="mt-2 text-sm font-mono text-white">
              {formatDateTime(detail.submitted_at, locale)}
            </p>
          </div>
          <div className="rounded-xl border border-grid-line/20 bg-terminal-surface/35 p-3">
            <p className="text-[11px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
              {t('detail.supportTicket')}
            </p>
            {detail.ticket_reference ? (
              <Link
                href={safeSupportRoute(detail.ticket_reference)}
                className="mt-2 inline-flex break-all text-sm font-mono text-neon-cyan hover:text-white"
              >
                {detail.ticket_reference}
              </Link>
            ) : (
              <p className="mt-2 text-sm font-mono text-muted-foreground">n/a</p>
            )}
          </div>
          <div className="rounded-xl border border-grid-line/20 bg-terminal-surface/35 p-3">
            <p className="text-[11px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
              {t('detail.version')}
            </p>
            <p className="mt-2 text-sm font-mono text-white">{detail.version}</p>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5">
        <div className="flex items-center gap-3">
          <FileText className="h-5 w-5 text-neon-cyan" />
          <h3 className="text-sm font-display uppercase tracking-[0.22em] text-white">
            {t('detail.reviewContext')}
          </h3>
        </div>
        <dl className="mt-4 grid gap-3 text-sm font-mono md:grid-cols-2">
          <div>
            <dt className="text-muted-foreground">{t('detail.reasonCode')}</dt>
            <dd className="mt-1 break-words text-white">{detail.reason_code ?? 'n/a'}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">{t('detail.decisionReason')}</dt>
            <dd className="mt-1 break-words text-white">{detail.decision_reason ?? 'n/a'}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-muted-foreground">{t('detail.notes')}</dt>
            <dd className="mt-1 whitespace-pre-wrap break-words text-white">{detail.notes_redacted ?? 'n/a'}</dd>
          </div>
          {detail.last_error_code ? (
            <div className="md:col-span-2 rounded-xl border border-red-400/30 bg-red-500/10 p-3">
              <dt className="text-red-200">{detail.last_error_code}</dt>
              <dd className="mt-1 text-red-100">{detail.last_error_redacted}</dd>
            </div>
          ) : null}
        </dl>
      </section>

      <section className="rounded-2xl border border-amber-300/25 bg-amber-300/10 p-5">
        <div className="flex items-center gap-3">
          <Trash2 className="h-5 w-5 text-amber-200" />
          <div>
            <h3 className="text-sm font-display uppercase tracking-[0.22em] text-white">
              {t('actions.title')}
            </h3>
            <p className="mt-1 text-sm font-mono text-muted-foreground">{t('actions.description')}</p>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {detail.allowed_actions.length === 0 ? (
            <span className="font-mono text-sm text-muted-foreground">{t('actions.none')}</span>
          ) : (
            detail.allowed_actions.map((action) => (
              <button
                key={action}
                type="button"
                onClick={() => onAction(action)}
                className={cn(
                  'inline-flex min-h-10 items-center rounded-xl border border-grid-line/30 bg-terminal-bg/70 px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-white transition-colors hover:border-neon-cyan/40 hover:text-neon-cyan',
                  action === 'execute' && 'border-red-400/40 bg-red-500/20 text-red-100 hover:text-white',
                  CONTROL_FOCUS_CLASS,
                )}
              >
                {t(`actions.${action}`)}
              </button>
            ))
          )}
        </div>
      </section>

      <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5">
        <div className="flex items-center gap-3">
          <Clock3 className="h-5 w-5 text-neon-cyan" />
          <h3 className="text-sm font-display uppercase tracking-[0.22em] text-white">
            {t('detail.auditTimeline')}
          </h3>
        </div>
        <div className="mt-4 grid gap-3">
          {detail.events.length === 0 ? (
            <div className="rounded-xl border border-dashed border-grid-line/30 bg-terminal-bg/45 p-4 text-sm font-mono text-muted-foreground">
              {t('detail.noEvents')}
            </div>
          ) : (
            detail.events.map((event, index) => (
              <article
                key={`${event.event_type}-${event.created_at}-${index}`}
                className="rounded-xl border border-grid-line/20 bg-terminal-bg/45 p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <StatusChip label={event.event_type} tone="info" />
                  <p className="text-xs font-mono text-muted-foreground">
                    {formatDateTime(event.created_at, locale)}
                  </p>
                </div>
                <p className="mt-3 text-sm font-mono leading-6 text-foreground/90">
                  {event.safe_summary}
                </p>
              </article>
            ))
          )}
        </div>
      </section>
    </div>
  );
}

interface PrivacyRequestConsoleProps {
  initialReference?: string;
  initialSearchParams?: SearchParams;
}

export function PrivacyRequestConsole({
  initialReference,
  initialSearchParams,
}: PrivacyRequestConsoleProps) {
  const t = useTranslations('PrivacyRequests');
  const locale = useLocale();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [initialFilters] = useState(() => getInitialFilters(initialSearchParams));
  const [search, setSearch] = useState(initialFilters.search);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>(initialFilters.statusFilter);
  const [typeFilter, setTypeFilter] = useState<TypeFilter>(initialFilters.typeFilter);
  const [assignmentFilter, setAssignmentFilter] = useState<AssignmentFilter>(
    initialFilters.assignmentFilter,
  );
  const [selectedReference, setSelectedReference] = useState<string | null>(initialReference ?? null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const deferredSearch = useDeferredValue(search);
  const privacyUrlQuery = useMemo(
    () => buildUrlQuery({
      assignmentFilter,
      search: deferredSearch,
      statusFilter,
      typeFilter,
    }),
    [assignmentFilter, deferredSearch, statusFilter, typeFilter],
  );

  useEffect(() => {
    const path = selectedReference ? safePrivacyRoute(selectedReference) : '/privacy-requests';
    router.replace(buildHref(path, privacyUrlQuery), { scroll: false });
  }, [privacyUrlQuery, router, selectedReference]);

  const sessionQuery = useQuery({
    queryKey: ['privacy-requests', 'session'],
    queryFn: async () => {
      const response = await authApi.session();
      return response.data;
    },
    staleTime: 30_000,
  });

  const role = sessionQuery.data?.role;
  const canRead = hasAdminPermission(role, 'privacy_request_read');
  const canReview = hasAdminPermission(role, 'privacy_request_review');
  const canFulfill = hasAdminPermission(role, 'privacy_request_fulfill');
  const assignedAdminId =
    assignmentFilter === 'mine' && sessionQuery.data?.id
      ? sessionQuery.data.id
      : undefined;

  const listParams = buildListParams({
    assignedAdminId,
    deferredSearch,
    statusFilter,
    typeFilter,
  });

  const listQuery = useQuery({
    queryKey: ['admin', 'privacy-requests', 'list', listParams],
    queryFn: async () => {
      const response = await adminPrivacyRequestsApi.list(listParams);
      return response.data;
    },
    enabled: canRead,
  });

  const activeReference =
    selectedReference ?? listQuery.data?.requests[0]?.privacy_request_reference ?? null;

  const detailQuery = useQuery({
    queryKey: ['admin', 'privacy-requests', 'detail', activeReference],
    queryFn: async () => {
      if (!activeReference) throw new Error('No privacy request selected');
      const response = await adminPrivacyRequestsApi.get(activeReference);
      return response.data;
    },
    enabled: canRead && Boolean(activeReference),
  });

  const invalidatePrivacyQueries = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['admin', 'privacy-requests', 'list'] }),
      queryClient.invalidateQueries({ queryKey: ['admin', 'privacy-requests', 'detail', activeReference] }),
      queryClient.invalidateQueries({ queryKey: ['admin', 'action-queues', 'privacy-requests'] }),
    ]);
  };

  const actionMutation = useMutation({
    mutationFn: async (action: string) => {
      if (!activeReference) throw new Error(t('feedback.selectRequest'));
      if (action === 'start_review') return adminPrivacyRequestsApi.startReview(activeReference);
      if (action === 'request_identity_verification') {
        const message = window.prompt(t('prompts.identityMessage'), t('prompts.identityMessageDefault'));
        if (!message) throw new Error(t('feedback.actionCanceled'));
        return adminPrivacyRequestsApi.requestIdentityVerification(activeReference, message);
      }
      if (action === 'verify_identity') {
        const method = window.prompt(t('prompts.verificationMethod'), 'support_ticket');
        if (!method) throw new Error(t('feedback.actionCanceled'));
        const note = window.prompt(t('prompts.safeNote'), '');
        return adminPrivacyRequestsApi.verifyIdentity(activeReference, method, note);
      }
      if (action === 'approve') {
        const reason = window.prompt(t('prompts.decisionReason'), t('prompts.approveDefault'));
        if (!reason || !window.confirm(t('prompts.approveConfirm'))) {
          throw new Error(t('feedback.actionCanceled'));
        }
        return adminPrivacyRequestsApi.approve(activeReference, reason);
      }
      if (action === 'deny') {
        const reason = window.prompt(t('prompts.decisionReason'), '');
        if (!reason || !window.confirm(t('prompts.denyConfirm'))) {
          throw new Error(t('feedback.actionCanceled'));
        }
        return adminPrivacyRequestsApi.deny(activeReference, reason);
      }
      if (action === 'schedule') {
        const scheduledFor = window.prompt(t('prompts.scheduleFor'), '');
        return adminPrivacyRequestsApi.schedule(activeReference, scheduledFor || null);
      }
      if (action === 'execute') {
        const confirmText = window.prompt(t('prompts.executeConfirmText'), '');
        if (confirmText !== 'DELETE' || !window.confirm(t('prompts.executeConfirm'))) {
          throw new Error(t('feedback.actionCanceled'));
        }
        return adminPrivacyRequestsApi.execute(activeReference, confirmText);
      }
      if (action === 'retry') {
        return adminPrivacyRequestsApi.retry(activeReference);
      }
      throw new Error(t('feedback.unknownAction'));
    },
    onSuccess: async (response) => {
      setFeedback(t('feedback.actionComplete'));
      setSelectedReference(response.data.privacy_request_reference);
      await invalidatePrivacyQueries();
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('feedback.actionFailed'));
    },
  });

  const detail = detailQuery.data;
  const visibleActions = detail?.allowed_actions.filter((action) => {
    if (action === 'execute') return canFulfill;
    return canReview;
  });
  const visibleDetail = detail ? { ...detail, allowed_actions: visibleActions ?? [] } : undefined;

  return (
    <div className="grid gap-6">
      <header className="rounded-2xl border border-grid-line/20 bg-terminal-surface/50 p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.24em] text-neon-cyan">
              {t('eyebrow')}
            </p>
            <h1 className="mt-2 text-3xl font-display uppercase tracking-[0.18em] text-white">
              {t('title')}
            </h1>
            <p className="mt-3 max-w-3xl text-sm font-mono leading-6 text-muted-foreground">
              {t('description')}
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              void listQuery.refetch();
              void detailQuery.refetch();
            }}
            className={cn(
              'inline-flex min-h-11 items-center gap-2 rounded-xl border border-grid-line/30 bg-terminal-bg/70 px-4 py-2 font-mono text-xs uppercase tracking-[0.14em] text-neon-cyan transition-colors hover:border-neon-cyan/40 hover:text-white',
              CONTROL_FOCUS_CLASS,
            )}
          >
            <RefreshCw className="h-4 w-4" />
            {t('common.refresh')}
          </button>
        </div>
      </header>

      {!canRead && !sessionQuery.isPending ? <PermissionDeniedState t={t} /> : null}

      {canRead ? (
        <>
          <section className="grid gap-3 rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4 lg:grid-cols-[minmax(240px,1fr)_180px_190px_190px]">
            <label className="relative block">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <span className="sr-only">{t('filters.search')}</span>
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder={t('filters.searchPlaceholder')}
                className={cn(
                  'min-h-11 w-full rounded-xl border border-grid-line/30 bg-terminal-bg/70 pl-10 pr-3 font-mono text-sm text-white outline-hidden placeholder:text-muted-foreground',
                  CONTROL_FOCUS_CLASS,
                )}
              />
            </label>
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
              className={cn(
                'min-h-11 rounded-xl border border-grid-line/30 bg-terminal-bg/70 px-3 font-mono text-sm text-white',
                CONTROL_FOCUS_CLASS,
              )}
              aria-label={t('filters.status')}
            >
              {STATUS_FILTERS.map((statusValue) => (
                <option key={statusValue} value={statusValue}>
                  {statusValue === 'all' ? t('filters.allStatuses') : t(`statuses.${statusValue}`)}
                </option>
              ))}
            </select>
            <select
              value={typeFilter}
              onChange={(event) => setTypeFilter(event.target.value as TypeFilter)}
              className={cn(
                'min-h-11 rounded-xl border border-grid-line/30 bg-terminal-bg/70 px-3 font-mono text-sm text-white',
                CONTROL_FOCUS_CLASS,
              )}
              aria-label={t('filters.requestType')}
            >
              {TYPE_FILTERS.map((typeValue) => (
                <option key={typeValue} value={typeValue}>
                  {typeValue === 'all' ? t('filters.allTypes') : t(`types.${typeValue}`)}
                </option>
              ))}
            </select>
            <select
              value={assignmentFilter}
              onChange={(event) => setAssignmentFilter(event.target.value as AssignmentFilter)}
              className={cn(
                'min-h-11 rounded-xl border border-grid-line/30 bg-terminal-bg/70 px-3 font-mono text-sm text-white',
                CONTROL_FOCUS_CLASS,
              )}
              aria-label={t('filters.assignment')}
            >
              {ASSIGNMENT_FILTERS.map((assignment) => (
                <option key={assignment} value={assignment}>
                  {t(`filters.assignmentOptions.${assignment}`)}
                </option>
              ))}
            </select>
          </section>

          {feedback ? (
            <div className="rounded-2xl border border-amber-300/30 bg-amber-300/10 p-4 font-mono text-sm text-amber-100">
              {feedback}
            </div>
          ) : null}

          <section className="grid gap-6 xl:grid-cols-[minmax(300px,420px)_minmax(0,1fr)]">
            <div className="grid gap-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/55 p-4">
                  <CheckCircle2 className="h-5 w-5 text-matrix-green" />
                  <p className="mt-3 text-2xl font-display text-white">
                    {listQuery.data?.requests.length ?? 0}
                  </p>
                  <p className="text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                    {t('metrics.visible')}
                  </p>
                </div>
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/55 p-4">
                  <AlertTriangle className="h-5 w-5 text-amber-200" />
                  <p className="mt-3 text-2xl font-display text-white">
                    {listQuery.data?.requests.filter((item) => item.overdue).length ?? 0}
                  </p>
                  <p className="text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                    {t('metrics.overdue')}
                  </p>
                </div>
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/55 p-4">
                  <ShieldCheck className="h-5 w-5 text-neon-cyan" />
                  <p className="mt-3 text-2xl font-display text-white">
                    {listQuery.data?.requests.filter((item) => item.status === 'submitted').length ?? 0}
                  </p>
                  <p className="text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                    {t('metrics.submitted')}
                  </p>
                </div>
              </div>
              {listQuery.isPending ? (
                <div className="grid gap-3">
                  {Array.from({ length: 5 }).map((_, index) => (
                    <div
                      key={index}
                      className="h-28 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                    />
                  ))}
                </div>
              ) : (
                <RequestList
                  activeReference={activeReference}
                  locale={locale}
                  onSelect={setSelectedReference}
                  query={privacyUrlQuery}
                  requests={listQuery.data?.requests ?? []}
                  t={t}
                />
              )}
            </div>
            <DetailPanel
              detail={visibleDetail}
              isLoading={detailQuery.isPending}
              locale={locale}
              onAction={(action) => actionMutation.mutate(action)}
              t={t}
            />
          </section>
        </>
      ) : null}
    </div>
  );
}
