'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { RadioTower } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { inboundsApi } from '@/lib/api/infrastructure';
import { InfrastructureEmptyState } from '@/features/infrastructure/components/empty-state';
import { JsonPreview } from '@/features/infrastructure/components/json-preview';
import { InfrastructurePageShell } from '@/features/infrastructure/components/infrastructure-page-shell';
import { InfrastructureStatusChip } from '@/features/infrastructure/components/infrastructure-status-chip';
import { formatCompactNumber, humanizeToken, shortId } from '@/features/infrastructure/lib/formatting';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';

export function InboundsConsole() {
  const t = useTranslations('Infrastructure');
  const [selectedInboundId, setSelectedInboundId] = useState<string | null>(null);

  const inboundsQuery = useQuery({
    queryKey: ['infrastructure', 'inbounds'],
    queryFn: async () => {
      const response = await inboundsApi.list();
      return response.data;
    },
    staleTime: 30_000,
  });

  const inbounds = inboundsQuery.data ?? [];
  const selectedInbound =
    inbounds.find((inbound) => inbound.uuid === selectedInboundId) ?? null;

  return (
    <InfrastructurePageShell
      eyebrow={t('inbounds.eyebrow')}
      title={t('inbounds.title')}
      description={t('inbounds.description')}
      icon={RadioTower}
      metrics={[
        {
          label: t('inbounds.metrics.total'),
          value: formatCompactNumber(inbounds.length),
          hint: t('inbounds.metrics.totalHint'),
          tone: 'info',
        },
        {
          label: t('inbounds.metrics.protocols'),
          value: formatCompactNumber(new Set(inbounds.map((inbound) => inbound.protocol)).size),
          hint: t('inbounds.metrics.protocolsHint'),
          tone: 'success',
        },
        {
          label: t('inbounds.metrics.secured'),
          value: formatCompactNumber(inbounds.filter((inbound) => inbound.security).length),
          hint: t('inbounds.metrics.securedHint'),
          tone: 'warning',
        },
        {
          label: t('inbounds.metrics.nodeBound'),
          value: formatCompactNumber(inbounds.filter((inbound) => inbound.nodeUuid).length),
          hint: t('inbounds.metrics.nodeBoundHint'),
          tone: 'neutral',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          {inbounds.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('common.tag')}</TableHead>
                  <TableHead>{t('common.protocol')}</TableHead>
                  <TableHead>{t('common.port')}</TableHead>
                  <TableHead>{t('common.security')}</TableHead>
                  <TableHead>{t('common.node')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {inbounds.map((inbound) => (
                  <TableRow
                    key={inbound.uuid}
                    onClick={() => setSelectedInboundId(inbound.uuid)}
                    className="cursor-pointer"
                  >
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-display uppercase tracking-[0.14em] text-white">
                          {inbound.tag}
                        </p>
                        <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          #{shortId(inbound.uuid)}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>{inbound.protocol}</TableCell>
                    <TableCell>{inbound.port}</TableCell>
                    <TableCell>
                      <InfrastructureStatusChip
                        label={humanizeToken(inbound.security ?? t('common.none'))}
                        tone={inbound.security ? 'success' : 'neutral'}
                      />
                    </TableCell>
                    <TableCell>{inbound.nodeUuid ?? t('common.emptyShort')}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <InfrastructureEmptyState label={t('inbounds.empty')} />
          )}
        </section>

        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('inbounds.detailTitle')}
          </h2>
          <div className="mt-5">
            {selectedInbound ? (
              <JsonPreview value={selectedInbound} maxHeightClassName="max-h-[32rem]" />
            ) : (
              <InfrastructureEmptyState label={t('inbounds.detailEmpty')} />
            )}
          </div>
        </section>
      </div>
    </InfrastructurePageShell>
  );
}
