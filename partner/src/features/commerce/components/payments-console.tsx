'use client';

import { useDeferredValue, useState, type FormEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import { CreditCard, Search, X } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { paymentsApi } from '@/lib/api/payments';
import { CommercePageShell } from '@/features/commerce/components/commerce-page-shell';
import { StatusChip } from '@/features/commerce/components/status-chip';
import {
  formatCompactNumber,
  formatCurrencyAmount,
  formatDateTime,
  humanizeToken,
  shortId,
} from '@/features/commerce/lib/formatting';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';

export function PaymentsConsole() {
  const t = useTranslations('Commerce');
  const [lookupInput, setLookupInput] = useState('');
  const [appliedUserUuid, setAppliedUserUuid] = useState('');
  const [providerFilter, setProviderFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [idSearch, setIdSearch] = useState('');
  const deferredSearch = useDeferredValue(idSearch.trim().toLowerCase());

  const paymentsQuery = useQuery({
    queryKey: ['commerce', 'payments', { userUuid: appliedUserUuid || null }],
    queryFn: async () => {
      const response = await paymentsApi.getHistory({
        offset: 0,
        limit: 100,
        user_uuid: appliedUserUuid || undefined,
      });
      return response.data.payments;
    },
    staleTime: 30_000,
  });

  const payments = paymentsQuery.data ?? [];
  const filteredPayments = payments.filter((payment) => {
    if (providerFilter !== 'all' && payment.provider !== providerFilter) {
      return false;
    }
    if (statusFilter !== 'all' && payment.status !== statusFilter) {
      return false;
    }
    if (deferredSearch && !payment.id.toLowerCase().includes(deferredSearch)) {
      return false;
    }
    return true;
  });

  const providers = Array.from(new Set(payments.map((payment) => payment.provider)));
  const statuses = Array.from(new Set(payments.map((payment) => payment.status)));
  const totalVolume = filteredPayments.reduce((sum, payment) => sum + payment.amount, 0);
  const completedPayments = filteredPayments.filter((payment) => payment.status === 'completed').length;

  function handleLookupSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAppliedUserUuid(lookupInput.trim());
  }

  function statusTone(status: string) {
    if (status === 'completed') return 'success' as const;
    if (status === 'failed' || status === 'refunded') return 'danger' as const;
    return 'info' as const;
  }

  return (
    <CommercePageShell
      eyebrow={t('payments.eyebrow')}
      title={t('payments.title')}
      description={t('payments.description')}
      icon={CreditCard}
      metrics={[
        {
          label: t('payments.metrics.records'),
          value: formatCompactNumber(payments.length),
          hint: t('payments.metrics.recordsHint'),
          tone: 'info',
        },
        {
          label: t('payments.metrics.filtered'),
          value: formatCompactNumber(filteredPayments.length),
          hint: t('payments.metrics.filteredHint'),
          tone: 'neutral',
        },
        {
          label: t('payments.metrics.completed'),
          value: formatCompactNumber(completedPayments),
          hint: t('payments.metrics.completedHint'),
          tone: 'success',
        },
        {
          label: t('payments.metrics.volume'),
          value: formatCurrencyAmount(totalVolume, filteredPayments[0]?.currency ?? 'USD'),
          hint: t('payments.metrics.volumeHint'),
          tone: 'warning',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-4">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('payments.filtersTitle')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('payments.filtersDescription')}
          </p>

          <form className="mt-5 space-y-4" onSubmit={handleLookupSubmit}>
            <label className="block space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('common.userUuid')}
              </span>
              <Input
                value={lookupInput}
                onChange={(event) => setLookupInput(event.target.value)}
                placeholder={t('payments.userUuidPlaceholder')}
              />
            </label>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-1">
              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.provider')}
                </span>
                <select
                  value={providerFilter}
                  onChange={(event) => setProviderFilter(event.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                >
                  <option value="all">{t('payments.allProviders')}</option>
                  {providers.map((provider) => (
                    <option key={provider} value={provider}>
                      {provider}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.status')}
                </span>
                <select
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                >
                  <option value="all">{t('payments.allStatuses')}</option>
                  {statuses.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <label className="block space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('common.id')}
              </span>
              <Input
                value={idSearch}
                onChange={(event) => setIdSearch(event.target.value)}
                placeholder={t('payments.idSearchPlaceholder')}
              />
            </label>

            <div className="flex flex-wrap gap-3">
              <Button type="submit" magnetic={false}>
                <Search className="mr-2 h-4 w-4" />
                {t('common.apply')}
              </Button>
              <Button
                type="button"
                variant="ghost"
                magnetic={false}
                onClick={() => {
                  setLookupInput('');
                  setAppliedUserUuid('');
                  setProviderFilter('all');
                  setStatusFilter('all');
                  setIdSearch('');
                }}
              >
                <X className="mr-2 h-4 w-4" />
                {t('common.reset')}
              </Button>
            </div>
          </form>

          <div className="mt-5 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4 text-sm font-mono leading-6 text-muted-foreground">
            {t('payments.serverFilterHint')}
          </div>
        </section>

        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-8">
          {paymentsQuery.isLoading ? (
            <div className="grid gap-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <div
                  key={index}
                  className="h-16 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))}
            </div>
          ) : filteredPayments.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-10 text-center text-sm font-mono text-muted-foreground">
              {t('payments.empty')}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('common.id')}</TableHead>
                  <TableHead>{t('common.amount')}</TableHead>
                  <TableHead>{t('common.provider')}</TableHead>
                  <TableHead>{t('common.status')}</TableHead>
                  <TableHead>{t('common.createdAt')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredPayments.map((payment) => (
                  <TableRow key={payment.id}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-display uppercase tracking-[0.14em] text-white">
                          #{shortId(payment.id)}
                        </p>
                        <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          {payment.id}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>{formatCurrencyAmount(payment.amount, payment.currency)}</TableCell>
                    <TableCell>{humanizeToken(payment.provider)}</TableCell>
                    <TableCell>
                      <StatusChip
                        label={humanizeToken(payment.status)}
                        tone={statusTone(payment.status)}
                      />
                    </TableCell>
                    <TableCell>{formatDateTime(payment.created_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </section>
      </div>
    </CommercePageShell>
  );
}
