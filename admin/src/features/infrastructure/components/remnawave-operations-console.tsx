'use client';

import { useQuery } from '@tanstack/react-query';
import { Activity, RefreshCw, ShieldAlert } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { InfrastructureEmptyState } from '@/features/infrastructure/components/empty-state';
import { InfrastructurePageShell } from '@/features/infrastructure/components/infrastructure-page-shell';
import { InfrastructureStatusChip } from '@/features/infrastructure/components/infrastructure-status-chip';
import {
  adminRemnawaveStatusApi,
  REMNAWAVE_CAPABILITY_KEYS,
  type RemnawaveCapabilityKey,
  type RemnawaveStreamStatus,
} from '@/lib/api/remnawave-status';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';
import { RemnawaveGrantsManager } from './remnawave-grants-manager';
import { RemnawaveNodeSshConsole } from './remnawave-node-ssh-console';
import { RemnawaveOperatorDirectory } from './remnawave-operator-directory';

function getHttpStatus(error: unknown): number | null {
  if (typeof error !== 'object' || error === null || !('response' in error)) {
    return null;
  }
  const response = (error as { response?: { status?: unknown } }).response;
  return typeof response?.status === 'number' ? response.status : null;
}

function streamTone(status: RemnawaveStreamStatus) {
  if (status === 'healthy') return 'success' as const;
  if (status === 'degraded') return 'warning' as const;
  return 'neutral' as const;
}

function formatCount(value: number | null): string {
  return value === null ? '—' : new Intl.NumberFormat().format(value);
}

function formatDateTime(value: string | null): string {
  if (!value) return '—';
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) return '—';
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(timestamp);
}

function LoadingState({ label }: { label: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="grid gap-4 md:grid-cols-2 xl:grid-cols-3"
    >
      <span className="sr-only">{label}</span>
      {Array.from({ length: 6 }, (_, index) => (
        <div
          key={index}
          aria-hidden="true"
          className="h-32 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-surface/35"
        />
      ))}
    </div>
  );
}

export function RemnawaveOperationsConsole() {
  const t = useTranslations('Infrastructure.remnawave');
  const statusQuery = useQuery({
    queryKey: ['infrastructure', 'remnawave', 'capabilities-and-streams'],
    queryFn: async () =>
      (await adminRemnawaveStatusApi.getCapabilitiesAndStreams()).data,
    retry: false,
    staleTime: 15_000,
  });

  const data = statusQuery.data;
  const enabledCount = data
    ? REMNAWAVE_CAPABILITY_KEYS.filter((key) => data.capabilities[key]).length
    : 0;
  const degradedStreams = data?.streams.filter((stream) => stream.status !== 'healthy') ?? [];
  const isDegraded = Boolean(data?.degraded_reason) || degradedStreams.length > 0;
  const isForbidden = getHttpStatus(statusQuery.error) === 403;

  const metrics = data
    ? [
        {
          label: t('metrics.panelVersion'),
          value: data.panel_version ?? t('unknown'),
          hint: t('metrics.panelTarget', { version: data.target_panel_version }),
          tone: data.panel_version === data.target_panel_version ? 'success' as const : 'warning' as const,
        },
        {
          label: t('metrics.nodeTarget'),
          value: data.target_node_version,
          hint: t('metrics.contract', { version: data.contract_version }),
          tone: 'info' as const,
        },
        {
          label: t('metrics.capabilities'),
          value: `${enabledCount}/${REMNAWAVE_CAPABILITY_KEYS.length}`,
          hint: t('metrics.capabilitiesHint'),
          tone: enabledCount === REMNAWAVE_CAPABILITY_KEYS.length ? 'success' as const : 'warning' as const,
        },
        {
          label: t('metrics.streams'),
          value: String(data.streams.length - degradedStreams.length),
          hint: t('metrics.streamsHint', { total: data.streams.length }),
          tone: isDegraded ? 'warning' as const : 'success' as const,
        },
      ]
    : [];

  return (
    <InfrastructurePageShell
      eyebrow={t('eyebrow')}
      title={t('title')}
      description={t('description')}
      icon={Activity}
      metrics={metrics}
      actions={
        <Button
          type="button"
          variant="outline"
          onClick={() => {
            void statusQuery.refetch();
          }}
          disabled={statusQuery.isFetching || isForbidden}
        >
          <RefreshCw
            className={`mr-2 h-4 w-4 ${statusQuery.isFetching ? 'animate-spin' : ''}`}
            aria-hidden="true"
          />
          {t('retry')}
        </Button>
      }
    >
      {statusQuery.isPending ? <LoadingState label={t('loading')} /> : null}

      {isForbidden ? (
        <section
          role="alert"
          className="rounded-2xl border border-neon-pink/30 bg-neon-pink/5 p-6"
        >
          <div className="flex items-start gap-3">
            <ShieldAlert className="mt-0.5 h-5 w-5 text-neon-pink" aria-hidden="true" />
            <div>
              <h2 className="font-display text-xl text-white">{t('forbidden.title')}</h2>
              <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">
                {t('forbidden.description')}
              </p>
            </div>
          </div>
        </section>
      ) : null}

      {statusQuery.isError && !isForbidden ? (
        <section
          role="alert"
          className="rounded-2xl border border-amber-400/30 bg-amber-400/5 p-6"
        >
          <h2 className="font-display text-xl text-white">{t('error.title')}</h2>
          <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">
            {t('error.description')}
          </p>
          <Button
            type="button"
            variant="outline"
            className="mt-4"
            onClick={() => {
              void statusQuery.refetch();
            }}
          >
            <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
            {t('retry')}
          </Button>
        </section>
      ) : null}

      {data ? (
        <div className="space-y-6" aria-live="polite">
          {isDegraded ? (
            <section
              role="status"
              className="rounded-2xl border border-amber-400/30 bg-amber-400/5 p-5"
            >
              <div className="flex items-start gap-3">
                <ShieldAlert className="mt-0.5 h-5 w-5 text-amber-300" aria-hidden="true" />
                <div>
                  <h2 className="font-display text-lg text-white">{t('degraded.title')}</h2>
                  <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">
                    {data.degraded_reason ?? t('degraded.streams', { count: degradedStreams.length })}
                  </p>
                </div>
              </div>
            </section>
          ) : null}

          <RemnawaveOperatorDirectory capabilities={data.capabilities} />

          <section className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/70 p-5 md:p-6">
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-neon-cyan/80">
                {t('capabilities.eyebrow')}
              </p>
              <h2 className="mt-2 font-display text-xl text-white">{t('capabilities.title')}</h2>
              <p className="mt-2 max-w-3xl font-mono text-sm leading-6 text-muted-foreground">
                {t('capabilities.description')}
              </p>
            </div>

            {enabledCount === 0 ? (
              <div className="mt-5">
                <InfrastructureEmptyState label={t('capabilities.empty')} />
              </div>
            ) : null}

            <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {REMNAWAVE_CAPABILITY_KEYS.map((key: RemnawaveCapabilityKey) => {
                const enabled = data.capabilities[key];
                return (
                  <article
                    key={key}
                    className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="font-display text-base text-white">
                          {t(`capabilities.items.${key}.title`)}
                        </h3>
                        <p className="mt-2 font-mono text-xs leading-5 text-muted-foreground">
                          {t(`capabilities.items.${key}.description`)}
                        </p>
                      </div>
                      <InfrastructureStatusChip
                        label={enabled ? t('enabled') : t('disabled')}
                        tone={enabled ? 'success' : 'neutral'}
                      />
                    </div>
                  </article>
                );
              })}
            </div>
          </section>

          <section className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/70 p-5 md:p-6">
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-neon-cyan/80">
                {t('streams.eyebrow')}
              </p>
              <h2 className="mt-2 font-display text-xl text-white">{t('streams.title')}</h2>
              <p className="mt-2 max-w-3xl font-mono text-sm leading-6 text-muted-foreground">
                {t('streams.description')}
              </p>
            </div>

            {data.streams.length === 0 ? (
              <div className="mt-5">
                <InfrastructureEmptyState label={t('streams.empty')} />
              </div>
            ) : (
              <div className="mt-5 overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('streams.columns.stream')}</TableHead>
                      <TableHead>{t('streams.columns.status')}</TableHead>
                      <TableHead>{t('streams.columns.lag')}</TableHead>
                      <TableHead>{t('streams.columns.pending')}</TableHead>
                      <TableHead>{t('streams.columns.deadLetters')}</TableHead>
                      <TableHead>{t('streams.columns.retention')}</TableHead>
                      <TableHead>{t('streams.columns.lastConsumed')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.streams.map((stream) => (
                      <TableRow key={stream.key}>
                        <TableCell>
                          <p className="font-mono text-sm text-white">
                            {t(`streams.items.${stream.key}`)}
                          </p>
                          <p className="mt-1 font-mono text-xs text-muted-foreground">
                            {stream.consumer_group}
                          </p>
                        </TableCell>
                        <TableCell>
                          <InfrastructureStatusChip
                            label={t(`streams.status.${stream.status}`)}
                            tone={streamTone(stream.status)}
                          />
                          {stream.degraded_reason ? (
                            <p className="mt-2 max-w-xs font-mono text-xs text-amber-200">
                              {stream.degraded_reason}
                            </p>
                          ) : null}
                        </TableCell>
                        <TableCell>{formatCount(stream.lag)}</TableCell>
                        <TableCell>{formatCount(stream.pending)}</TableCell>
                        <TableCell>{formatCount(stream.dead_letters)}</TableCell>
                        <TableCell>{t('streams.retentionDays', { count: stream.retention_days })}</TableCell>
                        <TableCell>{formatDateTime(stream.last_consumed_at)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </section>

          <RemnawaveGrantsManager />

          <RemnawaveNodeSshConsole enabled={data.capabilities.node_ssh} />
        </div>
      ) : null}
    </InfrastructurePageShell>
  );
}
