'use client';

import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { RefreshCw, ScrollText } from 'lucide-react';
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

export function AuditLogConsole() {
  const t = useTranslations('Governance');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const auditQuery = useQuery({
    queryKey: ['governance', 'audit-log', { page, pageSize: PAGE_SIZE }],
    queryFn: async () => {
      const response = await governanceApi.getAuditLogs({
        page,
        page_size: PAGE_SIZE,
      });
      return response.data;
    },
    staleTime: 15_000,
  });

  const auditLogs = auditQuery.data ?? [];
  const filteredLogs = auditLogs.filter((entry) =>
    matchesSearch(
      [
        entry.action,
        entry.entity_type,
        entry.entity_id,
        entry.admin_id,
        entry.ip_address,
        entry.user_agent,
        entry.old_value,
        entry.new_value,
      ],
      search,
    ),
  );
  const selectedLog =
    filteredLogs.find((entry) => entry.id === selectedId) ?? filteredLogs[0] ?? null;
  const entityCount = new Set(
    auditLogs.map((entry) => entry.entity_type).filter(Boolean),
  ).size;
  const unattributedCount = auditLogs.filter((entry) => !entry.admin_id).length;
  const changedCount = auditLogs.filter(
    (entry) => entry.old_value || entry.new_value,
  ).length;

  return (
    <GovernancePageShell
      eyebrow={t('auditLog.eyebrow')}
      title={t('auditLog.title')}
      description={t('auditLog.description')}
      icon={ScrollText}
      actions={
        <>
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t('auditLog.searchPlaceholder')}
            className="w-[16rem]"
          />
          <Button
            type="button"
            variant="ghost"
            magnetic={false}
            onClick={() => {
              void queryClient.invalidateQueries({ queryKey: ['governance', 'audit-log'] });
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
            disabled={auditLogs.length < PAGE_SIZE}
            onClick={() => setPage((current) => current + 1)}
          >
            {t('common.next')}
          </Button>
        </>
      }
      metrics={[
        {
          label: t('auditLog.metrics.visible'),
          value: String(filteredLogs.length),
          hint: t('auditLog.metrics.visibleHint'),
          tone: 'info',
        },
        {
          label: t('auditLog.metrics.entities'),
          value: String(entityCount),
          hint: t('auditLog.metrics.entitiesHint'),
          tone: 'neutral',
        },
        {
          label: t('auditLog.metrics.unattributed'),
          value: String(unattributedCount),
          hint: t('auditLog.metrics.unattributedHint'),
          tone: unattributedCount > 0 ? 'warning' : 'success',
        },
        {
          label: t('auditLog.metrics.changed'),
          value: String(changedCount),
          hint: t('auditLog.metrics.changedHint'),
          tone: 'warning',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-8">
          <div className="mb-5 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('auditLog.streamTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('auditLog.streamDescription', { page })}
              </p>
            </div>
          </div>

          {auditQuery.isLoading ? (
            <div className="grid gap-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <div
                  key={index}
                  className="h-16 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))}
            </div>
          ) : filteredLogs.length === 0 ? (
            <GovernanceEmptyState label={t('auditLog.empty')} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('common.action')}</TableHead>
                  <TableHead>{t('common.entity')}</TableHead>
                  <TableHead>{t('common.admin')}</TableHead>
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
                            {humanizeToken(entry.action)}
                          </p>
                          <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                            #{shortId(entry.id)}
                          </p>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1">
                          <p>{entry.entity_type ? humanizeToken(entry.entity_type) : t('common.none')}</p>
                          <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                            {entry.entity_id ?? '--'}
                          </p>
                        </div>
                      </TableCell>
                      <TableCell>
                        {entry.admin_id ? shortId(entry.admin_id) : t('common.system')}
                      </TableCell>
                      <TableCell>{formatDateTime(entry.created_at, locale)}</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </section>

        <section className="space-y-6 xl:col-span-4">
          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('auditLog.detailTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('auditLog.detailDescription')}
            </p>

            {selectedLog ? (
              <div className="mt-5 space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <GovernanceStatusChip
                    label={selectedLog.admin_id ? t('common.attributed') : t('common.system')}
                    tone={selectedLog.admin_id ? 'info' : 'warning'}
                  />
                  {selectedLog.entity_type ? (
                    <GovernanceStatusChip
                      label={humanizeToken(selectedLog.entity_type)}
                      tone="neutral"
                    />
                  ) : null}
                </div>

                <div className="grid gap-3">
                  <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('common.action')}
                    </p>
                    <p className="mt-3 text-sm font-mono leading-6 text-white">
                      {humanizeToken(selectedLog.action)}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('common.admin')}
                    </p>
                    <p className="mt-3 break-all text-sm font-mono leading-6 text-white">
                      {selectedLog.admin_id ?? t('common.system')}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('common.ipAddress')}
                    </p>
                    <p className="mt-3 text-sm font-mono leading-6 text-white">
                      {selectedLog.ip_address ?? '--'}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('common.userAgent')}
                    </p>
                    <p className="mt-3 break-words text-sm font-mono leading-6 text-white">
                      {selectedLog.user_agent ?? '--'}
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  <div>
                    <p className="mb-2 text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('auditLog.oldValue')}
                    </p>
                    <GovernanceJsonPreview value={selectedLog.old_value} />
                  </div>
                  <div>
                    <p className="mb-2 text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('auditLog.newValue')}
                    </p>
                    <GovernanceJsonPreview value={selectedLog.new_value} />
                  </div>
                </div>
              </div>
            ) : (
              <div className="mt-5">
                <GovernanceEmptyState label={t('auditLog.empty')} />
              </div>
            )}
          </article>
        </section>
      </div>
    </GovernancePageShell>
  );
}
