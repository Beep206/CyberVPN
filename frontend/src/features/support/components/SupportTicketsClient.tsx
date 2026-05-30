'use client';

import type { FormEvent } from 'react';
import { useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import {
  AlertTriangle,
  CheckCircle2,
  Headphones,
  LifeBuoy,
  Loader2,
  MessageSquareReply,
  RefreshCw,
  RotateCcw,
  Send,
  XCircle,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getApiErrorMessage } from '@/lib/api/error-message';
import type {
  SupportTicketCategory,
  SupportTicketStatus,
  SupportTicketSummary,
} from '@/lib/api/support-tickets';
import {
  useCloseSupportTicket,
  useCreateSupportTicket,
  useReplySupportTicket,
  useReopenSupportTicket,
  useSupportTicketDetail,
  useSupportTicketList,
} from '../hooks/useSupportTickets';

type SupportTicketsClientProps = {
  variant: 'dashboard' | 'miniapp';
};

type StatusFilter = SupportTicketStatus | 'all';
type TranslationFn = ReturnType<typeof useTranslations>;

const CATEGORY_OPTIONS: SupportTicketCategory[] = [
  'account',
  'billing',
  'setup',
  'vpn_access',
  'status',
  'privacy',
  'other',
];

const STATUS_FILTER_OPTIONS: StatusFilter[] = [
  'all',
  'open',
  'pending_support',
  'pending_customer',
  'resolved',
  'closed',
];

const STATUS_CLASSES: Record<SupportTicketStatus, string> = {
  closed: 'border-white/20 bg-white/10 text-white/70',
  open: 'border-matrix-green/30 bg-matrix-green/10 text-matrix-green',
  pending_customer: 'border-amber-400/35 bg-amber-400/10 text-amber-200',
  pending_support: 'border-neon-cyan/35 bg-neon-cyan/10 text-neon-cyan',
  resolved: 'border-neon-purple/35 bg-neon-purple/10 text-neon-purple',
};

function formatTimestamp(locale: string, value?: string | null): string {
  if (!value) {
    return '';
  }

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

function ticketSortTimestamp(ticket: SupportTicketSummary): string {
  return ticket.last_customer_message_at ?? ticket.updated_at ?? ticket.created_at;
}

function translateStatus(t: TranslationFn, status: SupportTicketStatus): string {
  return t(`status.${status}`);
}

function translateCategory(t: TranslationFn, category: SupportTicketCategory): string {
  return t(`categories.${category}`);
}

function EmptyState({
  description,
  icon: Icon,
  title,
}: {
  description: string;
  icon: LucideIcon;
  title: string;
}) {
  return (
    <div className="rounded-lg border border-grid-line/30 bg-terminal-surface/30 p-6 text-center">
      <Icon className="mx-auto h-10 w-10 text-muted-foreground" aria-hidden="true" />
      <h3 className="mt-3 font-display text-base text-white">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

export function SupportTicketsClient({ variant }: SupportTicketsClientProps) {
  const locale = useLocale();
  const t = useTranslations(variant === 'miniapp' ? 'MiniApp.support' : 'Dashboard.support');
  const isMiniApp = variant === 'miniapp';
  const [selectedTicketRefOverride, setSelectedTicketRef] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [category, setCategory] = useState<SupportTicketCategory>('vpn_access');
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [replyMessage, setReplyMessage] = useState('');
  const [createError, setCreateError] = useState('');
  const [replyError, setReplyError] = useState('');
  const [ticketActionError, setTicketActionError] = useState('');

  const listQuery = useSupportTicketList({
    limit: 50,
    status: statusFilter === 'all' ? undefined : statusFilter,
  });
  const tickets = listQuery.data?.tickets ?? [];
  const selectedTicketRef = selectedTicketRefOverride ?? tickets[0]?.public_id ?? null;
  const detailQuery = useSupportTicketDetail(selectedTicketRef);
  const createTicket = useCreateSupportTicket();
  const replyTicket = useReplySupportTicket(selectedTicketRef);
  const closeTicket = useCloseSupportTicket(selectedTicketRef);
  const reopenTicket = useReopenSupportTicket(selectedTicketRef);

  const selectedTicket = detailQuery.data;
  const isTicketClosed = selectedTicket?.status === 'closed';
  const canSubmitCreate = subject.trim().length >= 3 && message.trim().length > 0;
  const canSubmitReply = Boolean(selectedTicketRef) && replyMessage.trim().length > 0 && !isTicketClosed;
  const actionPending =
    closeTicket.isPending || createTicket.isPending || reopenTicket.isPending || replyTicket.isPending;

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!canSubmitCreate) {
      return;
    }

    setCreateError('');

    try {
      const ticket = await createTicket.mutateAsync({
        category,
        message: message.trim(),
        priority: 'normal',
        subject: subject.trim(),
      });
      setSubject('');
      setMessage('');
      setSelectedTicketRef(ticket.public_id);
    } catch (error) {
      setCreateError(getApiErrorMessage(error, t('errors.create')));
    }
  };

  const handleReply = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!canSubmitReply) {
      return;
    }

    setReplyError('');

    try {
      await replyTicket.mutateAsync({ message: replyMessage.trim() });
      setReplyMessage('');
    } catch (error) {
      setReplyError(getApiErrorMessage(error, t('errors.reply')));
    }
  };

  const handleClose = async () => {
    setTicketActionError('');

    try {
      await closeTicket.mutateAsync();
    } catch (error) {
      setTicketActionError(getApiErrorMessage(error, t('errors.close')));
    }
  };

  const handleReopen = async () => {
    setTicketActionError('');

    try {
      await reopenTicket.mutateAsync();
    } catch (error) {
      setTicketActionError(getApiErrorMessage(error, t('errors.reopen')));
    }
  };

  return (
    <div
      className={cn(
        'mx-auto w-full',
        isMiniApp ? 'max-w-screen-sm space-y-4' : 'max-w-7xl space-y-6',
      )}
    >
      <header className={cn('space-y-3', isMiniApp ? 'pt-1' : 'pt-2')}>
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-2 rounded-md border border-neon-cyan/30 bg-neon-cyan/10 px-3 py-1 font-mono text-xs uppercase tracking-[0.22em] text-neon-cyan">
            <LifeBuoy className="h-3.5 w-3.5" aria-hidden="true" />
            {t('eyebrow')}
          </span>
          <span className="rounded-md border border-grid-line/40 px-3 py-1 font-mono text-xs text-muted-foreground">
            {isMiniApp ? t('surface.miniapp') : t('surface.dashboard')}
          </span>
        </div>
        <div className={cn(isMiniApp ? 'space-y-1' : 'max-w-3xl space-y-2')}>
          <h1 className={cn('font-display text-white', isMiniApp ? 'text-2xl' : 'text-3xl md:text-4xl')}>
            {t('title')}
          </h1>
          <p className={cn('text-muted-foreground', isMiniApp ? 'text-sm' : 'text-base')}>
            {t('description')}
          </p>
        </div>
      </header>

      <section className="rounded-lg border border-amber-400/30 bg-amber-400/10 p-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-300" aria-hidden="true" />
          <div>
            <h2 className="font-display text-sm uppercase tracking-[0.14em] text-amber-100">
              {t('sensitiveWarning.title')}
            </h2>
            <p className="mt-1 text-sm text-amber-100/85">
              {t('sensitiveWarning.description')}
            </p>
          </div>
        </div>
      </section>

      <div className={cn('grid gap-4', isMiniApp ? 'grid-cols-1' : 'lg:grid-cols-[minmax(300px,380px)_1fr]')}>
        <div className="space-y-4">
          <form
            onSubmit={handleCreate}
            className="rounded-lg border border-grid-line/30 bg-terminal-surface/60 p-4 shadow-[0_0_24px_rgba(0,255,255,0.06)]"
          >
            <div className="mb-4 flex items-center gap-2">
              <Headphones className="h-5 w-5 text-neon-cyan" aria-hidden="true" />
              <h2 className="font-display text-base text-white">{t('form.title')}</h2>
            </div>

            <div className="space-y-4">
              <label className="block">
                <span className="font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
                  {t('form.categoryLabel')}
                </span>
                <select
                  aria-label={t('form.categoryLabel')}
                  value={category}
                  onChange={(event) => setCategory(event.target.value as SupportTicketCategory)}
                  className="mt-2 w-full rounded-md border border-grid-line/40 bg-terminal-bg px-3 py-3 font-mono text-sm text-white outline-hidden transition focus:border-neon-cyan focus:ring-2 focus:ring-neon-cyan/30"
                >
                  {CATEGORY_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {translateCategory(t, option)}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
                  {t('form.subjectLabel')}
                </span>
                <input
                  aria-label={t('form.subjectLabel')}
                  value={subject}
                  onChange={(event) => setSubject(event.target.value)}
                  maxLength={120}
                  placeholder={t('form.subjectPlaceholder')}
                  className="mt-2 w-full rounded-md border border-grid-line/40 bg-terminal-bg px-3 py-3 font-mono text-sm text-white outline-hidden transition placeholder:text-muted-foreground/70 focus:border-neon-cyan focus:ring-2 focus:ring-neon-cyan/30"
                />
              </label>

              <label className="block">
                <span className="font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
                  {t('form.messageLabel')}
                </span>
                <textarea
                  aria-label={t('form.messageLabel')}
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  maxLength={4000}
                  rows={isMiniApp ? 4 : 6}
                  placeholder={t('form.messagePlaceholder')}
                  className="mt-2 w-full resize-y rounded-md border border-grid-line/40 bg-terminal-bg px-3 py-3 font-mono text-sm text-white outline-hidden transition placeholder:text-muted-foreground/70 focus:border-neon-cyan focus:ring-2 focus:ring-neon-cyan/30"
                />
                <span className="mt-2 block font-mono text-xs text-muted-foreground">
                  {t('form.messageHelp', { count: message.length })}
                </span>
              </label>
            </div>

            {createError ? (
              <p className="mt-3 rounded-md border border-neon-pink/30 bg-neon-pink/10 p-3 text-sm text-neon-pink" role="alert">
                {createError}
              </p>
            ) : null}

            <button
              type="submit"
              aria-label={t('form.submit')}
              disabled={!canSubmitCreate || createTicket.isPending}
              className="mt-4 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-md border border-neon-cyan/40 bg-neon-cyan/15 px-4 py-2 font-mono text-sm text-neon-cyan transition hover:bg-neon-cyan/20 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan disabled:cursor-not-allowed disabled:opacity-50"
            >
              {createTicket.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Send className="h-4 w-4" aria-hidden="true" />
              )}
              {createTicket.isPending ? t('form.submitting') : t('form.submit')}
            </button>
          </form>

          <section className="rounded-lg border border-grid-line/30 bg-terminal-surface/45 p-4">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-display text-base text-white">{t('list.title')}</h2>
              <button
                type="button"
                aria-label={t('actions.refreshList')}
                onClick={() => void listQuery.refetch()}
                className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-grid-line/40 text-muted-foreground transition hover:border-neon-cyan/50 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan"
              >
                <RefreshCw
                  className={cn('h-4 w-4', listQuery.isFetching ? 'animate-spin' : '')}
                  aria-hidden="true"
                />
              </button>
            </div>

            <label className="mt-3 block">
              <span className="sr-only">{t('filters.statusLabel')}</span>
              <select
                aria-label={t('filters.statusLabel')}
                value={statusFilter}
                onChange={(event) => {
                  setStatusFilter(event.target.value as StatusFilter);
                  setSelectedTicketRef(null);
                }}
                className="w-full rounded-md border border-grid-line/40 bg-terminal-bg px-3 py-2 font-mono text-sm text-white outline-hidden focus:border-neon-cyan focus:ring-2 focus:ring-neon-cyan/30"
              >
                {STATUS_FILTER_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option === 'all' ? t('filters.all') : translateStatus(t, option)}
                  </option>
                ))}
              </select>
            </label>

            <div className="mt-4 space-y-3">
              {listQuery.isLoading ? (
                [0, 1, 2].map((item) => (
                  <div
                    key={item}
                    aria-hidden="true"
                    className="h-24 animate-pulse rounded-md border border-grid-line/30 bg-white/5"
                  />
                ))
              ) : listQuery.isError ? (
                <p className="rounded-md border border-neon-pink/30 bg-neon-pink/10 p-3 text-sm text-neon-pink" role="alert">
                  {t('errors.list')}
                </p>
              ) : tickets.length === 0 ? (
                <EmptyState
                  icon={MessageSquareReply}
                  title={t('list.emptyTitle')}
                  description={t('list.emptyDescription')}
                />
              ) : (
                tickets.map((ticket) => {
                  const isSelected = selectedTicketRef === ticket.public_id;

                  return (
                    <button
                      key={ticket.public_id}
                      type="button"
                      aria-label={t('list.openTicket', { id: ticket.public_id })}
                      aria-pressed={isSelected}
                      onClick={() => setSelectedTicketRef(ticket.public_id)}
                      className={cn(
                        'w-full rounded-md border p-3 text-left transition focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan',
                        isSelected
                          ? 'border-neon-cyan/60 bg-neon-cyan/10'
                          : 'border-grid-line/30 bg-terminal-bg/70 hover:border-neon-cyan/40',
                      )}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate font-mono text-xs text-muted-foreground">
                            {ticket.public_id}
                          </p>
                          <h3 className="mt-1 line-clamp-2 font-display text-sm text-white">
                            {ticket.subject}
                          </h3>
                        </div>
                        <span
                          className={cn(
                            'shrink-0 rounded-md border px-2 py-1 font-mono text-[10px] uppercase',
                            STATUS_CLASSES[ticket.status],
                          )}
                        >
                          {translateStatus(t, ticket.status)}
                        </span>
                      </div>
                      <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">
                        {ticket.last_message_preview}
                      </p>
                      <div className="mt-3 flex flex-wrap items-center gap-2 font-mono text-[11px] text-muted-foreground">
                        <span>{translateCategory(t, ticket.category)}</span>
                        <span aria-hidden="true">/</span>
                        <time dateTime={ticketSortTimestamp(ticket)}>
                          {formatTimestamp(locale, ticketSortTimestamp(ticket))}
                        </time>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </section>
        </div>

        <section className="rounded-lg border border-grid-line/30 bg-terminal-surface/55 p-4">
          {!selectedTicketRef ? (
            <EmptyState
              icon={LifeBuoy}
              title={t('detail.emptyTitle')}
              description={t('detail.emptyDescription')}
            />
          ) : detailQuery.isLoading ? (
            <div className="space-y-4" aria-busy="true">
              <div className="h-8 w-2/3 animate-pulse rounded-md bg-white/10" />
              <div className="h-24 animate-pulse rounded-md bg-white/10" />
              <div className="h-24 animate-pulse rounded-md bg-white/10" />
            </div>
          ) : detailQuery.isError || !selectedTicket ? (
            <p className="rounded-md border border-neon-pink/30 bg-neon-pink/10 p-3 text-sm text-neon-pink" role="alert">
              {t('errors.detail')}
            </p>
          ) : (
            <div className="space-y-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-mono text-xs text-muted-foreground">{selectedTicket.public_id}</p>
                  <h2 className="mt-1 break-words font-display text-xl text-white">
                    {selectedTicket.subject}
                  </h2>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <span
                      className={cn(
                        'rounded-md border px-2 py-1 font-mono text-xs uppercase',
                        STATUS_CLASSES[selectedTicket.status],
                      )}
                    >
                      {translateStatus(t, selectedTicket.status)}
                    </span>
                    <span className="rounded-md border border-grid-line/40 px-2 py-1 font-mono text-xs text-muted-foreground">
                      {translateCategory(t, selectedTicket.category)}
                    </span>
                  </div>
                </div>

                {isTicketClosed ? (
                  <button
                    type="button"
                    aria-label={t('actions.reopen')}
                    disabled={actionPending}
                    onClick={handleReopen}
                    className="inline-flex min-h-10 items-center gap-2 rounded-md border border-neon-cyan/40 bg-neon-cyan/10 px-3 py-2 font-mono text-sm text-neon-cyan transition hover:bg-neon-cyan/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan disabled:opacity-50"
                  >
                    {reopenTicket.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    ) : (
                      <RotateCcw className="h-4 w-4" aria-hidden="true" />
                    )}
                    {t('actions.reopen')}
                  </button>
                ) : (
                  <button
                    type="button"
                    aria-label={t('actions.close')}
                    disabled={actionPending}
                    onClick={handleClose}
                    className="inline-flex min-h-10 items-center gap-2 rounded-md border border-white/20 bg-white/5 px-3 py-2 font-mono text-sm text-white/80 transition hover:border-neon-pink/40 hover:text-neon-pink focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan disabled:opacity-50"
                  >
                    {closeTicket.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    ) : (
                      <XCircle className="h-4 w-4" aria-hidden="true" />
                    )}
                    {t('actions.close')}
                  </button>
                )}
              </div>

              {ticketActionError ? (
                <p className="rounded-md border border-neon-pink/30 bg-neon-pink/10 p-3 text-sm text-neon-pink" role="alert">
                  {ticketActionError}
                </p>
              ) : null}

              <div className="space-y-3">
                <h3 className="font-display text-sm uppercase tracking-[0.16em] text-muted-foreground">
                  {t('detail.conversationTitle')}
                </h3>
                {selectedTicket.messages.length === 0 ? (
                  <p className="rounded-md border border-grid-line/30 p-4 text-sm text-muted-foreground">
                    {t('detail.noMessages')}
                  </p>
                ) : (
                  selectedTicket.messages.map((ticketMessage, index) => {
                    const isCustomer = ticketMessage.author_label === 'customer';

                    return (
                      <article
                        key={`${ticketMessage.author_label}-${ticketMessage.created_at}-${index}`}
                        className={cn(
                          'rounded-md border p-4',
                          isCustomer
                            ? 'border-neon-cyan/25 bg-neon-cyan/10'
                            : 'border-matrix-green/25 bg-matrix-green/10',
                        )}
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-[0.14em] text-white">
                            {isCustomer ? t('detail.customerAuthor') : t('detail.supportAuthor')}
                          </span>
                          <time
                            dateTime={ticketMessage.created_at}
                            className="font-mono text-xs text-muted-foreground"
                          >
                            {formatTimestamp(locale, ticketMessage.created_at)}
                          </time>
                        </div>
                        <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-6 text-white/90">
                          {ticketMessage.body}
                        </p>
                      </article>
                    );
                  })
                )}
              </div>

              {isTicketClosed ? (
                <div className="rounded-md border border-white/15 bg-white/5 p-4">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-matrix-green" aria-hidden="true" />
                    <div>
                      <h3 className="font-display text-sm text-white">{t('detail.closedTitle')}</h3>
                      <p className="mt-1 text-sm text-muted-foreground">{t('detail.closedDescription')}</p>
                    </div>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleReply} className="space-y-3">
                  <label className="block">
                    <span className="font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
                      {t('reply.label')}
                    </span>
                    <textarea
                      aria-label={t('reply.label')}
                      value={replyMessage}
                      onChange={(event) => setReplyMessage(event.target.value)}
                      maxLength={4000}
                      rows={4}
                      placeholder={t('reply.placeholder')}
                      className="mt-2 w-full resize-y rounded-md border border-grid-line/40 bg-terminal-bg px-3 py-3 font-mono text-sm text-white outline-hidden transition placeholder:text-muted-foreground/70 focus:border-neon-cyan focus:ring-2 focus:ring-neon-cyan/30"
                    />
                  </label>
                  {replyError ? (
                    <p className="rounded-md border border-neon-pink/30 bg-neon-pink/10 p-3 text-sm text-neon-pink" role="alert">
                      {replyError}
                    </p>
                  ) : null}
                  <button
                    type="submit"
                    aria-label={t('reply.submit')}
                    disabled={!canSubmitReply || replyTicket.isPending}
                    className="inline-flex min-h-10 items-center gap-2 rounded-md border border-matrix-green/40 bg-matrix-green/10 px-4 py-2 font-mono text-sm text-matrix-green transition hover:bg-matrix-green/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {replyTicket.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    ) : (
                      <MessageSquareReply className="h-4 w-4" aria-hidden="true" />
                    )}
                    {replyTicket.isPending ? t('reply.submitting') : t('reply.submit')}
                  </button>
                </form>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
