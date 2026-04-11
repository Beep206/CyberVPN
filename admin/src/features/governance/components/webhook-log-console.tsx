'use client';

import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { RefreshCw, Webhook } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { governanceApi } from '@/lib/api/governance';
import { GovernanceEmptyState } from '@/features/governance/components/governance-empty-state';
import { GovernanceJsonPreview } from '@/features/governance/components/governance-json-preview';
import { GovernancePageShell } from '@/features/governance/components/governance-page-shell';
import { GovernanceStatusChip } from '@/features/governance/components/governance-status-chip';
import {
  formatDateTime,
  humanizeToken,
  matchesSearch,
  shortId,
  toneForWebhookState,
} from '@/features/governance/lib/formatting';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';

const PAGE_SIZE = 25;

export function WebhookLogConsole() {
  const t = useTranslations('Governance');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const webhookQuery = useQuery({
    queryKey: ['governance', 'webhook-log', { page, pageSize: PAGE_SIZE }],
    queryFn: async () => {
      const response = await governanceApi.getWebhookLogs({
        page,
        page_size: PAGE_SIZE,
      });
      return response.data;
    },
    staleTime: 15_000,
  });

  const webhookLogs = webhookQuery.data ?? [];
  const availableSources = Array.from(
    new Set(webhookLogs.map((entry) => entry.source)),
  ).sort((left, right) => left.localeCompare(right));
  const filteredLogs = webhookLogs.filter((entry) => {
    if (sourceFilter !== 'all' && entry.source !== sourceFilter) {
      return false;
    }

    if (statusFilter === 'invalid' && entry.is_valid !== false) {
      return false;
    }

    if (statusFilter === 'processed' && !entry.processed_at) {
      return false;
    }

    if (statusFilter === 'pending' && entry.processed_at) {
      return false;
    }

    return matchesSearch(
      [
        entry.source,
        entry.event_type,
        entry.error_message,
        entry.payload,
        entry.id,
      ],
      search,
    );
  });
  const selectedLog =
    filteredLogs.find((entry) => entry.id === selectedId) ?? filteredLogs[0] ?? null;
  const invalidCount = webhookLogs.filter((entry) => entry.is_valid === false).length;
  const processedCount = webhookLogs.filter((entry) => Boolean(entry.processed_at)).length;

  return (
    <GovernancePageShell
      eyebrow={t('webhookLog.eyebrow')}
      title={t('webhookLog.title')}
      description={t('webhookLog.description')}
      icon={Webhook}
      actions={
        <>
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t('webhookLog.searchPlaceholder')}
            className="w-[15rem]"
          />
          <select
            value={sourceFilter}
            onChange={(event) => setSourceFilter(event.target.value)}
            className="h-10 rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground"
          >
            <option value="all">{t('webhookLog.filters.allSources')}</option>
            {availableSources.map((source) => (
              <option key={source} value={source}>
                {humanizeToken(source)}
              </option>
            ))}
          </select>
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            className="h-10 rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground"
          >
            <option value="all">{t('webhookLog.filters.allStatuses')}</option>
            <option value="invalid">{t('webhookLog.filters.invalid')}</option>
            <option value="processed">{t('webhookLog.filters.processed')}</option>
            <option value="pending">{t('webhookLog.filters.pending')}</option>
          </select>
          <Button
            type="button"
            variant="ghost"
            magnetic={false}
            onClick={() => {
              void queryClient.invalidateQueries({ queryKey: ['governance', 'webhook-log'] });
            }}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            {t('common.refresh')}
          </Button>
          <Button
            type="button"
            variant="ghost"
            magnetic={false}
            disabled={page === 1}
            onClick={() => setPage((current) => Math.max(1, current - 1))}
          >
            {t('common.previous')}
          </Button>
          <Button
            type="button"
            variant="ghost"
            magnetic={false}
            disabled={webhookLogs.length < PAGE_SIZE}
            onClick={() => setPage((current) => current + 1)}
          >
            {t('common.next')}
          </Button>
        </>
      }
      metrics={[
        {
          label: t('webhookLog.metrics.visible'),
          value: String(filteredLogs.length),
          hint: t('webhookLog.metrics.visibleHint'),
          tone: 'info',
        },
        {
          label: t('webhookLog.metrics.invalid'),
          value: String(invalidCount),
          hint: t('webhookLog.metrics.invalidHint'),
          tone: invalidCount > 0 ? 'danger' : 'success',
        },
        {
          label: t('webhookLog.metrics.processed'),
          value: String(processedCount),
          hint: t('webhookLog.metrics.processedHint'),
          tone: 'success',
        },
        {
          label: t('webhookLog.metrics.sources'),
          value: String(availableSources.length),
          hint: t('webhookLog.metrics.sourcesHint'),
          tone: 'neutral',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-8">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('webhookLog.streamTitle')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('webhookLog.streamDescription', { page })}
          </p>

          <div className="mt-5">
            {webhookQuery.isLoading ? (
              <div className="grid gap-3">
                {Array.from({ length: 6 }).map((_, index) => (
                  <div
                    key={index}
                    className="h-16 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                  />
                ))}
              </div>
            ) : filteredLogs.length === 0 ? (
              <GovernanceEmptyState label={t('webhookLog.empty')} />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('common.source')}</TableHead>
                    <TableHead>{t('common.eventType')}</TableHead>
                    <TableHead>{t('common.status')}</TableHead>
                    <TableHead>{t('common.createdAt')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredLogs.map((entry) => {
                    const isSelected = selectedLog?.id === entry.id;

                    return (
                      <TableRow
                        key={entry.id}
                        className={isSelected ? 'border-l-2 border-l-neon-cyan bg-neon-cyan/5' : undefined}
                        onClick={() => setSelectedId(entry.id)}
                      >
                        <TableCell>
                          <div className="space-y-1">
                            <p className="font-display uppercase tracking-[0.14em] text-white">
                              {humanizeToken(entry.source)}
                            </p>
                            <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                              #{shortId(entry.id)}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell>
                          {entry.event_type ? humanizeToken(entry.event_type) : t('common.none')}
                        </TableCell>
                        <TableCell>
                          <GovernanceStatusChip
                            label={
                              entry.is_valid === false
                                ? t('common.invalid')
                                : entry.processed_at
                                  ? t('common.processed')
                                  : t('common.pending')
                            }
                            tone={toneForWebhookState(entry)}
                          />
                        </TableCell>
                        <TableCell>{formatDateTime(entry.created_at, locale)}</TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </div>
        </section>

        <section className="space-y-6 xl:col-span-4">
          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('webhookLog.detailTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('webhookLog.detailDescription')}
            </p>

            {selectedLog ? (
              <div className="mt-5 space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <GovernanceStatusChip
                    label={humanizeToken(selectedLog.source)}
                    tone="info"
                  />
                  <GovernanceStatusChip
                    label={
                      selectedLog.is_valid === false
                        ? t('common.invalid')
                        : selectedLog.processed_at
                          ? t('common.processed')
                          : t('common.pending')
                    }
                    tone={toneForWebhookState(selectedLog)}
                  />
                </div>

                <div className="grid gap-3">
                  <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('common.eventType')}
                    </p>
                    <p className="mt-3 text-sm font-mono leading-6 text-white">
                      {selectedLog.event_type ? humanizeToken(selectedLog.event_type) : t('common.none')}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('common.processedAt')}
                    </p>
                    <p className="mt-3 text-sm font-mono leading-6 text-white">
                      {formatDateTime(selectedLog.processed_at, locale)}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('common.error')}
                    </p>
                    <p className="mt-3 break-words text-sm font-mono leading-6 text-white">
                      {selectedLog.error_message ?? '--'}
                    </p>
                  </div>
                </div>

                <div>
                  <p className="mb-2 text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('common.payload')}
                  </p>
                  <GovernanceJsonPreview value={selectedLog.payload} />
                </div>
              </div>
            ) : (
              <div className="mt-5">
                <GovernanceEmptyState label={t('webhookLog.empty')} />
              </div>
            )}
          </article>
        </section>
      </div>
    </GovernancePageShell>
  );
}
