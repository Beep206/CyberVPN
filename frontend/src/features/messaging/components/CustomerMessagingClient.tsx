'use client';

import type { FormEvent } from 'react';
import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useLocale, useTranslations } from 'next-intl';
import {
  AlertTriangle,
  CheckCircle2,
  Inbox,
  Loader2,
  MessageSquareReply,
  RefreshCw,
  Send,
  ShieldCheck,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getApiErrorMessage } from '@/lib/api/error-message';
import type {
  CustomerConversationSummary,
  MessagingConversationCategory,
  MessagingConversationStatus,
  MessagingPriority,
  MessagingResponseState,
  MessagingSenderType,
} from '@/lib/api/messaging';
import {
  useCustomerConversationDetail,
  useCustomerConversationList,
  useMarkCustomerConversationRead,
  useReplyCustomerConversation,
} from '../hooks/useCustomerMessaging';

type StatusFilter = MessagingConversationStatus | 'all';
type TranslationFn = ReturnType<typeof useTranslations>;

const STATUS_FILTERS: StatusFilter[] = [
  'all',
  'open',
  'closed',
  'archived',
  'locked',
];

const STATUS_CLASSES: Record<MessagingConversationStatus, string> = {
  archived: 'border-white/20 bg-white/10 text-white/70',
  closed: 'border-white/20 bg-white/10 text-white/70',
  locked: 'border-amber-400/35 bg-amber-400/10 text-amber-200',
  open: 'border-matrix-green/30 bg-matrix-green/10 text-matrix-green',
};

const PRIORITY_CLASSES: Record<MessagingPriority, string> = {
  high: 'border-amber-400/35 bg-amber-400/10 text-amber-200',
  low: 'border-white/20 bg-white/10 text-white/70',
  normal: 'border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan',
  urgent: 'border-neon-pink/40 bg-neon-pink/10 text-neon-pink',
};

const MESSAGE_CLASSES: Record<MessagingSenderType, string> = {
  admin: 'border-matrix-green/25 bg-matrix-green/10',
  customer: 'border-neon-cyan/25 bg-neon-cyan/10',
  system: 'border-neon-purple/25 bg-neon-purple/10',
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

function conversationSortTimestamp(conversation: CustomerConversationSummary): string {
  return conversation.last_message_at ?? conversation.updated_at ?? conversation.created_at;
}

function translateStatus(t: TranslationFn, status: MessagingConversationStatus): string {
  return t(`status.${status}`);
}

function translateResponseState(t: TranslationFn, state: MessagingResponseState): string {
  return t(`responseState.${state}`);
}

function translateCategory(t: TranslationFn, category: MessagingConversationCategory): string {
  return t(`category.${category}`);
}

function translatePriority(t: TranslationFn, priority: MessagingPriority): string {
  return t(`priority.${priority}`);
}

function translateSender(t: TranslationFn, senderType: MessagingSenderType): string {
  return t(`sender.${senderType}`);
}

function EmptyState({
  description,
  title,
}: {
  description: string;
  title: string;
}) {
  return (
    <div className="rounded-lg border border-grid-line/30 bg-terminal-surface/30 p-6 text-center">
      <Inbox className="mx-auto h-10 w-10 text-muted-foreground" aria-hidden="true" />
      <h3 className="mt-3 font-display text-base text-white">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

export function CustomerMessagingClient() {
  const locale = useLocale();
  const t = useTranslations('Messaging');
  const searchParams = useSearchParams();
  const [selectedConversationRefOverride, setSelectedConversationRef] =
    useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [replyBody, setReplyBody] = useState('');
  const [replyError, setReplyError] = useState('');
  const markedReadRef = useRef<string | null>(null);

  const listQuery = useCustomerConversationList({
    limit: 50,
    status: statusFilter === 'all' ? undefined : statusFilter,
  });
  const conversations = listQuery.data?.conversations ?? [];
  const linkedConversationRef = searchParams.get('conversation');
  const selectedConversationRef =
    selectedConversationRefOverride ?? linkedConversationRef ?? conversations[0]?.public_id ?? null;
  const detailQuery = useCustomerConversationDetail(selectedConversationRef);
  const replyConversation = useReplyCustomerConversation(selectedConversationRef);
  const markConversationRead = useMarkCustomerConversationRead(selectedConversationRef);
  const selectedConversation = detailQuery.data;
  const isWritable = selectedConversation?.status === 'open';
  const canReply = Boolean(selectedConversationRef) && isWritable && replyBody.trim().length > 0;

  useEffect(() => {
    if (!selectedConversation || selectedConversation.unread_count <= 0) {
      return;
    }

    const lastMessage = selectedConversation.messages.at(-1);
    if (!lastMessage) {
      return;
    }

    const marker = `${selectedConversation.id}:${lastMessage.id}`;
    if (markedReadRef.current === marker || markConversationRead.isPending) {
      return;
    }

    markedReadRef.current = marker;
    markConversationRead.mutate(lastMessage.id);
  }, [markConversationRead, selectedConversation]);

  const handleReply = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!canReply) {
      return;
    }

    setReplyError('');

    try {
      await replyConversation.mutateAsync({ body: replyBody.trim() });
      setReplyBody('');
    } catch (error) {
      setReplyError(getApiErrorMessage(error, t('reply.error')));
    }
  };

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header className="space-y-3 pt-2">
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-2 rounded-md border border-neon-cyan/30 bg-neon-cyan/10 px-3 py-1 font-mono text-xs uppercase tracking-[0.22em] text-neon-cyan">
            <MessageSquareReply className="h-3.5 w-3.5" aria-hidden="true" />
            {t('eyebrow')}
          </span>
          <span className="rounded-md border border-grid-line/40 px-3 py-1 font-mono text-xs text-muted-foreground">
            {t('surface')}
          </span>
        </div>
        <div className="max-w-3xl space-y-2">
          <h1 className="font-display text-3xl text-white md:text-4xl">
            {t('title')}
          </h1>
          <p className="text-base leading-7 text-muted-foreground">
            {t('description')}
          </p>
        </div>
      </header>

      <section className="rounded-lg border border-neon-cyan/25 bg-neon-cyan/10 p-4">
        <div className="flex items-start gap-3">
          <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-neon-cyan" aria-hidden="true" />
          <div>
            <h2 className="font-display text-sm uppercase tracking-[0.14em] text-white">
              {t('privacy.title')}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {t('privacy.description')}
            </p>
          </div>
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-[minmax(300px,390px)_1fr]">
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
                setSelectedConversationRef(null);
              }}
              className="w-full rounded-md border border-grid-line/40 bg-terminal-bg px-3 py-2 font-mono text-sm text-white outline-hidden focus:border-neon-cyan focus:ring-2 focus:ring-neon-cyan/30"
            >
              {STATUS_FILTERS.map((option) => (
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
                  className="h-28 animate-pulse rounded-md border border-grid-line/30 bg-white/5"
                />
              ))
            ) : listQuery.isError ? (
              <p className="rounded-md border border-neon-pink/30 bg-neon-pink/10 p-3 text-sm text-neon-pink" role="alert">
                {t('errors.list')}
              </p>
            ) : conversations.length === 0 ? (
              <EmptyState
                title={t('list.emptyTitle')}
                description={t('list.emptyDescription')}
              />
            ) : (
              conversations.map((conversation) => {
                const isSelected =
                  selectedConversationRef === conversation.public_id ||
                  selectedConversationRef === conversation.id;

                return (
                  <button
                    key={conversation.id}
                    type="button"
                    aria-label={t('list.openConversation', {
                      subject: conversation.subject,
                    })}
                    aria-pressed={isSelected}
                    onClick={() => setSelectedConversationRef(conversation.public_id)}
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
                          {conversation.public_id}
                        </p>
                        <h3 className="mt-1 line-clamp-2 font-display text-sm text-white">
                          {conversation.subject}
                        </h3>
                      </div>
                      <div className="flex shrink-0 flex-col items-end gap-2">
                        <span
                          className={cn(
                            'rounded-md border px-2 py-1 font-mono text-[10px] uppercase',
                            STATUS_CLASSES[conversation.status],
                          )}
                        >
                          {translateStatus(t, conversation.status)}
                        </span>
                        {conversation.unread_count > 0 ? (
                          <span className="flex min-h-5 min-w-5 items-center justify-center rounded-full bg-neon-pink px-1 font-mono text-[10px] text-white">
                            {conversation.unread_count > 99 ? '99+' : conversation.unread_count}
                          </span>
                        ) : null}
                      </div>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-2 font-mono text-[11px] text-muted-foreground">
                      <span>{translateCategory(t, conversation.category)}</span>
                      <span aria-hidden="true">/</span>
                      <span>{translateResponseState(t, conversation.response_state)}</span>
                      <span aria-hidden="true">/</span>
                      <time dateTime={conversationSortTimestamp(conversation)}>
                        {formatTimestamp(locale, conversationSortTimestamp(conversation))}
                      </time>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </section>

        <section className="rounded-lg border border-grid-line/30 bg-terminal-surface/55 p-4">
          {!selectedConversationRef ? (
            <EmptyState
              title={t('detail.emptyTitle')}
              description={t('detail.emptyDescription')}
            />
          ) : detailQuery.isLoading ? (
            <div className="space-y-4" aria-busy="true">
              <div className="h-8 w-2/3 animate-pulse rounded-md bg-white/10" />
              <div className="h-24 animate-pulse rounded-md bg-white/10" />
              <div className="h-24 animate-pulse rounded-md bg-white/10" />
            </div>
          ) : detailQuery.isError || !selectedConversation ? (
            <p className="rounded-md border border-neon-pink/30 bg-neon-pink/10 p-3 text-sm text-neon-pink" role="alert">
              {t('errors.detail')}
            </p>
          ) : (
            <div className="space-y-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-mono text-xs text-muted-foreground">
                    {selectedConversation.public_id}
                  </p>
                  <h2 className="mt-1 break-words font-display text-xl text-white">
                    {selectedConversation.subject}
                  </h2>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <span
                      className={cn(
                        'rounded-md border px-2 py-1 font-mono text-xs uppercase',
                        STATUS_CLASSES[selectedConversation.status],
                      )}
                    >
                      {translateStatus(t, selectedConversation.status)}
                    </span>
                    <span
                      className={cn(
                        'rounded-md border px-2 py-1 font-mono text-xs uppercase',
                        PRIORITY_CLASSES[selectedConversation.priority],
                      )}
                    >
                      {translatePriority(t, selectedConversation.priority)}
                    </span>
                    <span className="rounded-md border border-grid-line/40 px-2 py-1 font-mono text-xs text-muted-foreground">
                      {translateCategory(t, selectedConversation.category)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <h3 className="font-display text-sm uppercase tracking-[0.16em] text-muted-foreground">
                  {t('detail.threadTitle')}
                </h3>
                {selectedConversation.messages.length === 0 ? (
                  <p className="rounded-md border border-grid-line/30 p-4 text-sm text-muted-foreground">
                    {t('detail.noMessages')}
                  </p>
                ) : (
                  selectedConversation.messages.map((message) => (
                    <article
                      key={message.id}
                      className={cn(
                        'rounded-md border p-4',
                        MESSAGE_CLASSES[message.sender_type],
                      )}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-[0.14em] text-white">
                          {translateSender(t, message.sender_type)}
                        </span>
                        <time
                          dateTime={message.created_at}
                          className="font-mono text-xs text-muted-foreground"
                        >
                          {formatTimestamp(locale, message.created_at)}
                        </time>
                      </div>
                      <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-6 text-white/90">
                        {message.body}
                      </p>
                    </article>
                  ))
                )}
              </div>

              {isWritable ? (
                <form onSubmit={handleReply} className="space-y-3">
                  <label className="block">
                    <span className="font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
                      {t('reply.label')}
                    </span>
                    <textarea
                      aria-label={t('reply.label')}
                      value={replyBody}
                      onChange={(event) => setReplyBody(event.target.value)}
                      maxLength={4000}
                      rows={4}
                      placeholder={t('reply.placeholder')}
                      className="mt-2 w-full resize-y rounded-md border border-grid-line/40 bg-terminal-bg px-3 py-3 font-mono text-sm text-white outline-hidden transition placeholder:text-muted-foreground/70 focus:border-neon-cyan focus:ring-2 focus:ring-neon-cyan/30"
                    />
                    <span className="mt-2 block font-mono text-xs text-muted-foreground">
                      {t('reply.counter', { count: replyBody.length })}
                    </span>
                  </label>
                  {replyError ? (
                    <p className="rounded-md border border-neon-pink/30 bg-neon-pink/10 p-3 text-sm text-neon-pink" role="alert">
                      {replyError}
                    </p>
                  ) : null}
                  <button
                    type="submit"
                    aria-label={t('reply.submit')}
                    disabled={!canReply || replyConversation.isPending}
                    className="inline-flex min-h-10 items-center gap-2 rounded-md border border-matrix-green/40 bg-matrix-green/10 px-4 py-2 font-mono text-sm text-matrix-green transition hover:bg-matrix-green/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {replyConversation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    ) : (
                      <Send className="h-4 w-4" aria-hidden="true" />
                    )}
                    {replyConversation.isPending ? t('reply.submitting') : t('reply.submit')}
                  </button>
                </form>
              ) : (
                <div className="rounded-md border border-white/15 bg-white/5 p-4">
                  <div className="flex items-start gap-3">
                    {selectedConversation.status === 'closed' ? (
                      <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-matrix-green" aria-hidden="true" />
                    ) : (
                      <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-300" aria-hidden="true" />
                    )}
                    <div>
                      <h3 className="font-display text-sm text-white">
                        {t(`readOnly.${selectedConversation.status}.title`)}
                      </h3>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {t(`readOnly.${selectedConversation.status}.description`)}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
