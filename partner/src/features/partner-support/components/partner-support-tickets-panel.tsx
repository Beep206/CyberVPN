'use client';

import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import {
  AlertTriangle,
  CheckCircle2,
  LockKeyhole,
  MessageSquareText,
  Plus,
  RefreshCw,
  Send,
  XCircle,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import {
  partnerPortalApi,
  type CreatePartnerSupportTicketPayload,
  type PartnerSupportTicketCategory,
  type PartnerSupportTicketEvent,
  type PartnerSupportTicketPriority,
  type PartnerSupportTicketStatus,
} from '@/lib/api/partner-portal';
import type { PartnerRouteAccessLevel } from '@/features/partner-portal-state/lib/portal-access';

const TICKET_STATUSES = [
  'open',
  'pending_support',
  'pending_customer',
  'resolved',
  'closed',
] as const satisfies readonly PartnerSupportTicketStatus[];

const TICKET_CATEGORIES = [
  'account',
  'billing',
  'setup',
  'vpn_access',
  'status',
  'privacy',
  'other',
] as const satisfies readonly PartnerSupportTicketCategory[];

const TICKET_PRIORITIES = [
  'low',
  'normal',
  'high',
  'urgent',
] as const satisfies readonly PartnerSupportTicketPriority[];

const PUBLIC_EVENT_TYPES = new Set<string>([
  'ticket_created',
  'public_reply_added',
  'status_changed',
  'priority_changed',
  'category_changed',
  'closed',
  'reopened',
]);

type TicketFilterValue = 'all' | PartnerSupportTicketStatus;
type CategoryFilterValue = 'all' | PartnerSupportTicketCategory;
type PublicActorLabelKey = 'admin' | 'customer' | 'partner' | 'support' | 'system';

const PUBLIC_ACTOR_LABEL_KEYS = new Set<string>([
  'admin',
  'customer',
  'partner',
  'support',
  'system',
]);

interface PartnerSupportTicketsPanelProps {
  access: PartnerRouteAccessLevel;
  currentPermissionKeys?: readonly string[];
  initialTicketRef?: string | null;
  isCanonicalWorkspace: boolean;
  workspaceId: string | null;
  workspaceName: string;
}

type FeedbackState = {
  message: string;
  tone: 'success' | 'error';
} | null;

function createEmptyDraft(): CreatePartnerSupportTicketPayload {
  return {
    category: 'account',
    message: '',
    priority: 'normal',
    subject: '',
  };
}

function formatDateTime(value: string | null | undefined, locale: string): string {
  if (!value) {
    return '';
  }

  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) {
    return value;
  }

  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(timestamp);
}

function resolveMutationError(error: unknown, fallback: string): string {
  if (error instanceof AxiosError) {
    const data = error.response?.data as {
      detail?: unknown;
      message?: unknown;
    } | undefined;
    const detail = data?.detail ?? data?.message;

    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
  }

  return fallback;
}

function getPublicEvents(events: PartnerSupportTicketEvent[]): PartnerSupportTicketEvent[] {
  return events.filter((event) => PUBLIC_EVENT_TYPES.has(event.event_type));
}

function translatePublicActorLabel(
  t: ReturnType<typeof useTranslations>,
  label: string,
): string {
  if (!PUBLIC_ACTOR_LABEL_KEYS.has(label)) {
    return label;
  }

  const key = label === 'support' ? 'admin' : label;
  return t(`authors.${key as PublicActorLabelKey}`);
}

export function PartnerSupportTicketsPanel({
  access,
  currentPermissionKeys = [],
  initialTicketRef = null,
  isCanonicalWorkspace,
  workspaceId,
  workspaceName,
}: PartnerSupportTicketsPanelProps) {
  const locale = useLocale();
  const t = useTranslations('Partner.supportTickets');
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<TicketFilterValue>('all');
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilterValue>('all');
  const [selectedTicketRef, setSelectedTicketRef] = useState<string | null>(initialTicketRef);
  const [createDraft, setCreateDraft] = useState<CreatePartnerSupportTicketPayload>(
    createEmptyDraft,
  );
  const [replyDraft, setReplyDraft] = useState('');
  const [feedback, setFeedback] = useState<FeedbackState>(null);

  useEffect(() => {
    setSelectedTicketRef(initialTicketRef);
  }, [initialTicketRef]);

  const canRead = access !== 'none' && Boolean(workspaceId) && isCanonicalWorkspace;
  const hasOperationsWrite =
    currentPermissionKeys.length === 0 || currentPermissionKeys.includes('operations_write');
  const canMutate =
    canRead && hasOperationsWrite && (access === 'write' || access === 'admin');

  const listQuery = useQuery({
    queryKey: [
      'partner-support-tickets',
      workspaceId,
      statusFilter,
      categoryFilter,
    ],
    queryFn: async () => {
      if (!workspaceId) {
        return { nextCursor: null, tickets: [] };
      }

      const response = await partnerPortalApi.listWorkspaceSupportTickets(
        workspaceId,
        {
          category: categoryFilter === 'all' ? undefined : categoryFilter,
          limit: 50,
          status: statusFilter === 'all' ? undefined : statusFilter,
        },
      );

      return response.data;
    },
    enabled: canRead,
    retry: false,
    staleTime: 15_000,
  });

  const detailQuery = useQuery({
    queryKey: ['partner-support-ticket', workspaceId, selectedTicketRef],
    queryFn: async () => {
      if (!workspaceId || !selectedTicketRef) {
        return null;
      }

      const response = await partnerPortalApi.getWorkspaceSupportTicket(
        workspaceId,
        selectedTicketRef,
      );
      return response.data;
    },
    enabled: canRead && Boolean(selectedTicketRef),
    retry: false,
  });

  const invalidateSupportTickets = async (ticketRef?: string | null) => {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: ['partner-support-tickets', workspaceId],
      }),
      ticketRef
        ? queryClient.invalidateQueries({
            queryKey: ['partner-support-ticket', workspaceId, ticketRef],
          })
        : Promise.resolve(),
      queryClient.invalidateQueries({
        queryKey: ['partner-portal', 'workspace-notifications', workspaceId],
      }),
    ]);
  };

  const createTicketMutation = useMutation({
    mutationFn: async (payload: CreatePartnerSupportTicketPayload) => {
      if (!workspaceId) {
        throw new Error(t('errors.workspaceMissing'));
      }
      const response = await partnerPortalApi.createWorkspaceSupportTicket(
        workspaceId,
        payload,
      );
      return response.data;
    },
    onSuccess: async (ticket) => {
      setCreateDraft(createEmptyDraft());
      setReplyDraft('');
      setSelectedTicketRef(ticket.public_id);
      setFeedback({ message: t('create.success'), tone: 'success' });
      await invalidateSupportTickets(ticket.public_id);
    },
    onError: (error) => {
      setFeedback({
        message: resolveMutationError(error, t('create.error')),
        tone: 'error',
      });
    },
  });

  const replyMutation = useMutation({
    mutationFn: async ({
      message,
      ticketRef,
    }: {
      message: string;
      ticketRef: string;
    }) => {
      if (!workspaceId) {
        throw new Error(t('errors.workspaceMissing'));
      }
      const response = await partnerPortalApi.replyToWorkspaceSupportTicket(
        workspaceId,
        ticketRef,
        { message },
      );
      return response.data;
    },
    onSuccess: async (ticket) => {
      setReplyDraft('');
      setSelectedTicketRef(ticket.public_id);
      setFeedback({ message: t('detail.replySuccess'), tone: 'success' });
      await invalidateSupportTickets(ticket.public_id);
    },
    onError: (error) => {
      setFeedback({
        message: resolveMutationError(error, t('detail.replyError')),
        tone: 'error',
      });
    },
  });

  const closeMutation = useMutation({
    mutationFn: async (ticketRef: string) => {
      if (!workspaceId) {
        throw new Error(t('errors.workspaceMissing'));
      }
      const response = await partnerPortalApi.closeWorkspaceSupportTicket(
        workspaceId,
        ticketRef,
      );
      return response.data;
    },
    onSuccess: async (ticket) => {
      setSelectedTicketRef(ticket.public_id);
      setFeedback({ message: t('detail.closeSuccess'), tone: 'success' });
      await invalidateSupportTickets(ticket.public_id);
    },
    onError: (error) => {
      setFeedback({
        message: resolveMutationError(error, t('detail.closeError')),
        tone: 'error',
      });
    },
  });

  const reopenMutation = useMutation({
    mutationFn: async (ticketRef: string) => {
      if (!workspaceId) {
        throw new Error(t('errors.workspaceMissing'));
      }
      const response = await partnerPortalApi.reopenWorkspaceSupportTicket(
        workspaceId,
        ticketRef,
      );
      return response.data;
    },
    onSuccess: async (ticket) => {
      setSelectedTicketRef(ticket.public_id);
      setFeedback({ message: t('detail.reopenSuccess'), tone: 'success' });
      await invalidateSupportTickets(ticket.public_id);
    },
    onError: (error) => {
      setFeedback({
        message: resolveMutationError(error, t('detail.reopenError')),
        tone: 'error',
      });
    },
  });

  const workspaceTickets = listQuery.data?.tickets ?? [];
  const selectedTicket = detailQuery.data;
  const publicMessages = selectedTicket?.messages ?? [];
  const publicEvents = getPublicEvents(selectedTicket?.events ?? []);
  const canCloseSelected =
    Boolean(selectedTicket)
    && selectedTicket?.status !== 'closed'
    && canMutate;
  const canReopenSelected =
    Boolean(selectedTicket)
    && (selectedTicket?.status === 'closed' || selectedTicket?.status === 'resolved')
    && canMutate;

  return (
    <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
      <div className="flex flex-col gap-4 border-b border-grid-line/20 pb-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
            {t('eyebrow')}
          </p>
          <h2 className="mt-2 text-lg font-display uppercase tracking-[0.18em] text-white md:text-xl">
            {t('title')}
          </h2>
          <p className="mt-3 max-w-4xl text-sm font-mono leading-6 text-muted-foreground">
            {t('subtitle', { workspace: workspaceName })}
          </p>
        </div>
        <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4 font-mono text-xs text-muted-foreground lg:w-[360px]">
          <div className="flex items-center justify-between gap-3">
            <span>{t('summary.workspace')}</span>
            <span className="truncate text-foreground">{workspaceName}</span>
          </div>
          <div className="mt-3 flex items-center justify-between gap-3">
            <span>{t('summary.visibleTickets')}</span>
            <span className="text-neon-cyan">{workspaceTickets.length}</span>
          </div>
          <div className="mt-3 flex items-center justify-between gap-3">
            <span>{t('summary.writeAccess')}</span>
            <span className={canMutate ? 'text-matrix-green' : 'text-neon-pink'}>
              {canMutate ? t('summary.writeEnabled') : t('summary.writeDisabled')}
            </span>
          </div>
        </div>
      </div>

      {!isCanonicalWorkspace || !workspaceId ? (
        <div className="mt-5 rounded-2xl border border-neon-pink/25 bg-neon-pink/10 p-4">
          <div className="flex items-start gap-3">
            <LockKeyhole className="mt-0.5 h-5 w-5 text-neon-pink" />
            <p className="text-sm font-mono leading-6 text-muted-foreground">
              {t('states.workspaceUnavailable')}
            </p>
          </div>
        </div>
      ) : null}

      {feedback ? (
        <div
          role="status"
          className={`mt-5 rounded-2xl border p-4 text-sm font-mono ${
            feedback.tone === 'success'
              ? 'border-matrix-green/25 bg-matrix-green/10 text-matrix-green'
              : 'border-neon-pink/25 bg-neon-pink/10 text-neon-pink'
          }`}
        >
          {feedback.message}
        </div>
      ) : null}

      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
        <section className="space-y-4">
          <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-end">
              <label className="grid flex-1 gap-2 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                {t('filters.statusLabel')}
                <select
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value as TicketFilterValue)}
                  className="rounded-xl border border-grid-line/20 bg-terminal-bg/70 px-3 py-2 text-sm normal-case tracking-normal text-foreground outline-none focus:border-neon-cyan/40"
                >
                  <option value="all">{t('filters.allStatuses')}</option>
                  {TICKET_STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {t(`statuses.${status}`)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="grid flex-1 gap-2 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                {t('filters.categoryLabel')}
                <select
                  value={categoryFilter}
                  onChange={(event) => setCategoryFilter(event.target.value as CategoryFilterValue)}
                  className="rounded-xl border border-grid-line/20 bg-terminal-bg/70 px-3 py-2 text-sm normal-case tracking-normal text-foreground outline-none focus:border-neon-cyan/40"
                >
                  <option value="all">{t('filters.allCategories')}</option>
                  {TICKET_CATEGORIES.map((category) => (
                    <option key={category} value={category}>
                      {t(`categories.${category}`)}
                    </option>
                  ))}
                </select>
              </label>
              <Button
                type="button"
                variant="outline"
                disabled={!canRead || listQuery.isFetching}
                onClick={() => {
                  void listQuery.refetch();
                }}
                className="border-neon-cyan/40 bg-neon-cyan/10 font-mono text-xs uppercase tracking-[0.18em] text-neon-cyan hover:bg-neon-cyan/20"
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                {listQuery.isFetching ? t('actions.refreshing') : t('actions.refresh')}
              </Button>
            </div>
          </div>

          <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
            <div className="flex items-center gap-3">
              <MessageSquareText className="h-5 w-5 text-neon-purple" />
              <h3 className="text-sm font-display uppercase tracking-[0.18em] text-white">
                {t('list.title')}
              </h3>
            </div>

            {listQuery.isLoading ? (
              <p className="mt-4 text-sm font-mono leading-6 text-muted-foreground">
                {t('states.loading')}
              </p>
            ) : listQuery.isError ? (
              <div className="mt-4 flex items-start gap-3 rounded-xl border border-neon-pink/25 bg-neon-pink/10 p-3">
                <AlertTriangle className="mt-0.5 h-4 w-4 text-neon-pink" />
                <p className="text-sm font-mono leading-6 text-muted-foreground">
                  {t('states.listError')}
                </p>
              </div>
            ) : workspaceTickets.length === 0 ? (
              <p className="mt-4 text-sm font-mono leading-6 text-muted-foreground">
                {t('states.empty')}
              </p>
            ) : (
              <div className="mt-4 space-y-3">
                {workspaceTickets.map((ticket) => {
                  const isSelected = selectedTicketRef === ticket.public_id;
                  return (
                    <button
                      key={ticket.public_id}
                      type="button"
                      onClick={() => {
                        setFeedback(null);
                        setSelectedTicketRef(ticket.public_id);
                      }}
                      className={`w-full rounded-2xl border p-4 text-left transition ${
                        isSelected
                          ? 'border-neon-cyan/45 bg-neon-cyan/10'
                          : 'border-grid-line/20 bg-terminal-bg/55 hover:border-neon-cyan/35'
                      }`}
                    >
                      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                        <div>
                          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                            {ticket.public_id}
                          </p>
                          <h4 className="mt-2 text-sm font-display uppercase tracking-[0.14em] text-white">
                            {ticket.subject}
                          </h4>
                          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                            {ticket.last_message_preview}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2 md:justify-end">
                          <span className="rounded-full border border-grid-line/25 bg-terminal-surface/55 px-3 py-1 text-[11px] font-mono uppercase tracking-[0.16em] text-neon-cyan">
                            {t(`statuses.${ticket.status}`)}
                          </span>
                          <span className="rounded-full border border-grid-line/25 bg-terminal-surface/55 px-3 py-1 text-[11px] font-mono uppercase tracking-[0.16em] text-muted-foreground">
                            {t(`priorities.${ticket.priority}`)}
                          </span>
                        </div>
                      </div>
                      <p className="mt-3 text-xs font-mono text-muted-foreground">
                        {t('list.updatedAt', {
                          value: formatDateTime(ticket.updated_at, locale),
                        })}
                      </p>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <form
            className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4"
            onSubmit={(event) => {
              event.preventDefault();
              setFeedback(null);
              createTicketMutation.mutate({
                ...createDraft,
                message: createDraft.message.trim(),
                subject: createDraft.subject.trim(),
              });
            }}
          >
            <div className="flex items-center gap-3">
              <Plus className="h-5 w-5 text-matrix-green" />
              <h3 className="text-sm font-display uppercase tracking-[0.18em] text-white">
                {t('create.title')}
              </h3>
            </div>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('create.description')}
            </p>

            <div className="mt-4 grid gap-3">
              <label className="grid gap-2 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                {t('create.subjectLabel')}
                <input
                  value={createDraft.subject}
                  onChange={(event) =>
                    setCreateDraft((current) => ({
                      ...current,
                      subject: event.target.value,
                    }))
                  }
                  disabled={!canMutate || createTicketMutation.isPending}
                  minLength={3}
                  maxLength={120}
                  className="rounded-xl border border-grid-line/20 bg-terminal-bg/70 px-3 py-2 text-sm normal-case tracking-normal text-foreground outline-none focus:border-neon-cyan/40"
                />
              </label>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="grid gap-2 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                  {t('create.categoryLabel')}
                  <select
                    value={createDraft.category}
                    onChange={(event) =>
                      setCreateDraft((current) => ({
                        ...current,
                        category: event.target.value as PartnerSupportTicketCategory,
                      }))
                    }
                    disabled={!canMutate || createTicketMutation.isPending}
                    className="rounded-xl border border-grid-line/20 bg-terminal-bg/70 px-3 py-2 text-sm normal-case tracking-normal text-foreground outline-none focus:border-neon-cyan/40"
                  >
                    {TICKET_CATEGORIES.map((category) => (
                      <option key={category} value={category}>
                        {t(`categories.${category}`)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="grid gap-2 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                  {t('create.priorityLabel')}
                  <select
                    value={createDraft.priority}
                    onChange={(event) =>
                      setCreateDraft((current) => ({
                        ...current,
                        priority: event.target.value as PartnerSupportTicketPriority,
                      }))
                    }
                    disabled={!canMutate || createTicketMutation.isPending}
                    className="rounded-xl border border-grid-line/20 bg-terminal-bg/70 px-3 py-2 text-sm normal-case tracking-normal text-foreground outline-none focus:border-neon-cyan/40"
                  >
                    {TICKET_PRIORITIES.map((priority) => (
                      <option key={priority} value={priority}>
                        {t(`priorities.${priority}`)}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <label className="grid gap-2 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                {t('create.messageLabel')}
                <textarea
                  value={createDraft.message}
                  onChange={(event) =>
                    setCreateDraft((current) => ({
                      ...current,
                      message: event.target.value,
                    }))
                  }
                  disabled={!canMutate || createTicketMutation.isPending}
                  minLength={1}
                  maxLength={4000}
                  className="min-h-28 rounded-xl border border-grid-line/20 bg-terminal-bg/70 px-3 py-2 text-sm normal-case tracking-normal text-foreground outline-none focus:border-neon-cyan/40"
                />
              </label>
              {!canMutate ? (
                <p className="text-xs font-mono leading-5 text-muted-foreground">
                  {t('states.readOnly')}
                </p>
              ) : null}
              <Button
                type="submit"
                disabled={
                  !canMutate
                  || createTicketMutation.isPending
                  || createDraft.subject.trim().length < 3
                  || createDraft.message.trim().length < 1
                }
                className="w-fit bg-matrix-green font-mono text-xs uppercase tracking-[0.18em] text-black hover:bg-matrix-green/90"
              >
                <Plus className="mr-2 h-4 w-4" />
                {createTicketMutation.isPending ? t('create.sending') : t('create.submit')}
              </Button>
            </div>
          </form>
        </section>

        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
          <div className="flex items-center gap-3 border-b border-grid-line/20 pb-4">
            <MessageSquareText className="h-5 w-5 text-neon-cyan" />
            <div>
              <h3 className="text-sm font-display uppercase tracking-[0.18em] text-white">
                {t('detail.title')}
              </h3>
              <p className="mt-1 text-sm font-mono leading-6 text-muted-foreground">
                {t('detail.description')}
              </p>
            </div>
          </div>

          {!selectedTicketRef ? (
            <p className="mt-5 text-sm font-mono leading-6 text-muted-foreground">
              {t('detail.selectPrompt')}
            </p>
          ) : detailQuery.isLoading ? (
            <p className="mt-5 text-sm font-mono leading-6 text-muted-foreground">
              {t('states.detailLoading')}
            </p>
          ) : detailQuery.isError ? (
            <div className="mt-5 flex items-start gap-3 rounded-xl border border-neon-pink/25 bg-neon-pink/10 p-3">
              <AlertTriangle className="mt-0.5 h-4 w-4 text-neon-pink" />
              <p className="text-sm font-mono leading-6 text-muted-foreground">
                {t('states.detailError')}
              </p>
            </div>
          ) : selectedTicket ? (
            <div className="mt-5 space-y-5">
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/55 p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                      {selectedTicket.public_id}
                    </p>
                    <h4 className="mt-2 text-base font-display uppercase tracking-[0.16em] text-white">
                      {selectedTicket.subject}
                    </h4>
                    <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                      {t('detail.updatedAt', {
                        value: formatDateTime(selectedTicket.updated_at, locale),
                      })}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 md:justify-end">
                    <span className="rounded-full border border-neon-cyan/30 bg-neon-cyan/10 px-3 py-1 text-[11px] font-mono uppercase tracking-[0.16em] text-neon-cyan">
                      {t(`statuses.${selectedTicket.status}`)}
                    </span>
                    <span className="rounded-full border border-grid-line/25 bg-terminal-surface/55 px-3 py-1 text-[11px] font-mono uppercase tracking-[0.16em] text-muted-foreground">
                      {t(`categories.${selectedTicket.category}`)}
                    </span>
                    <span className="rounded-full border border-grid-line/25 bg-terminal-surface/55 px-3 py-1 text-[11px] font-mono uppercase tracking-[0.16em] text-muted-foreground">
                      {t(`priorities.${selectedTicket.priority}`)}
                    </span>
                  </div>
                </div>
              </div>

              <div>
                <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-purple/80">
                  {t('detail.messagesTitle')}
                </p>
                {publicMessages.length === 0 ? (
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {t('detail.messagesEmpty')}
                  </p>
                ) : (
                  <div className="mt-3 space-y-3">
                    {publicMessages.map((message, index) => (
                      <article
                        key={`${message.author_label}-${message.created_at}-${index}`}
                        className="rounded-2xl border border-grid-line/20 bg-terminal-bg/55 p-4"
                      >
                        <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                            {translatePublicActorLabel(t, message.author_label)}
                          </p>
                          <p className="text-xs font-mono text-muted-foreground">
                            {formatDateTime(message.created_at, locale)}
                          </p>
                        </div>
                        <p className="mt-2 whitespace-pre-wrap text-sm font-mono leading-6 text-foreground/90">
                          {message.body}
                        </p>
                      </article>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-purple/80">
                  {t('detail.eventsTitle')}
                </p>
                {publicEvents.length === 0 ? (
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {t('detail.eventsEmpty')}
                  </p>
                ) : (
                  <div className="mt-3 space-y-2">
                    {publicEvents.map((event, index) => (
                      <div
                        key={`${event.event_type}-${event.created_at}-${index}`}
                        className="flex flex-col gap-2 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-3 py-2 md:flex-row md:items-center md:justify-between"
                      >
                        <div>
                          <span className="text-sm font-mono text-foreground/90">
                            {t(`events.${event.event_type}`)}
                          </span>
                          <span className="mt-1 block text-xs font-mono text-muted-foreground">
                            {translatePublicActorLabel(t, event.actor_label)}
                          </span>
                        </div>
                        <span className="text-xs font-mono text-muted-foreground">
                          {formatDateTime(event.created_at, locale)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <form
                className="space-y-3 border-t border-grid-line/20 pt-4"
                onSubmit={(event) => {
                  event.preventDefault();
                  if (!selectedTicket) {
                    return;
                  }
                  setFeedback(null);
                  replyMutation.mutate({
                    message: replyDraft.trim(),
                    ticketRef: selectedTicket.public_id,
                  });
                }}
              >
                <label className="grid gap-2 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                  {t('detail.replyLabel')}
                  <textarea
                    value={replyDraft}
                    onChange={(event) => setReplyDraft(event.target.value)}
                    disabled={!canMutate || replyMutation.isPending}
                    maxLength={4000}
                    className="min-h-28 rounded-xl border border-grid-line/20 bg-terminal-bg/70 px-3 py-2 text-sm normal-case tracking-normal text-foreground outline-none focus:border-neon-cyan/40"
                  />
                </label>
                <div className="flex flex-wrap gap-3">
                  <Button
                    type="submit"
                    disabled={!canMutate || replyMutation.isPending || !replyDraft.trim()}
                    className="bg-neon-cyan font-mono text-xs uppercase tracking-[0.18em] text-black hover:bg-neon-cyan/90"
                  >
                    <Send className="mr-2 h-4 w-4" />
                    {replyMutation.isPending ? t('detail.replySending') : t('detail.replyAction')}
                  </Button>
                  {canCloseSelected ? (
                    <Button
                      type="button"
                      variant="outline"
                      disabled={closeMutation.isPending}
                      onClick={() => closeMutation.mutate(selectedTicket.public_id)}
                      className="border-neon-pink/40 bg-neon-pink/10 font-mono text-xs uppercase tracking-[0.18em] text-neon-pink hover:bg-neon-pink/20"
                    >
                      <XCircle className="mr-2 h-4 w-4" />
                      {closeMutation.isPending ? t('detail.closeSending') : t('detail.closeAction')}
                    </Button>
                  ) : null}
                  {canReopenSelected ? (
                    <Button
                      type="button"
                      variant="outline"
                      disabled={reopenMutation.isPending}
                      onClick={() => reopenMutation.mutate(selectedTicket.public_id)}
                      className="border-matrix-green/40 bg-matrix-green/10 font-mono text-xs uppercase tracking-[0.18em] text-matrix-green hover:bg-matrix-green/20"
                    >
                      <CheckCircle2 className="mr-2 h-4 w-4" />
                      {reopenMutation.isPending ? t('detail.reopenSending') : t('detail.reopenAction')}
                    </Button>
                  ) : null}
                </div>
              </form>
            </div>
          ) : null}
        </section>
      </div>
    </article>
  );
}
