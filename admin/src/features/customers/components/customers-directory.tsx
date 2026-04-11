'use client';

import { useDeferredValue, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Users } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { buttonVariants } from '@/components/ui/button';
import { customersApi } from '@/lib/api/customers';
import { CustomersPageShell } from '@/features/customers/components/customers-page-shell';
import { CustomerStatusChip } from '@/features/customers/components/customer-status-chip';
import {
  formatDateTime,
  getErrorMessage,
  shortId,
} from '@/features/customers/lib/formatting';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';

export function CustomersDirectory() {
  const t = useTranslations('Customers');
  const locale = useLocale();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [activityFilter, setActivityFilter] = useState<'all' | 'active' | 'inactive'>('all');
  const [partnerFilter, setPartnerFilter] = useState<'all' | 'partner' | 'non_partner'>('all');
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const deferredSearch = useDeferredValue(search);

  const customersQuery = useQuery({
    queryKey: [
      'customers',
      'directory',
      deferredSearch,
      statusFilter,
      activityFilter,
      partnerFilter,
    ],
    queryFn: async () => {
      const response = await customersApi.listMobileUsers({
        search: deferredSearch.trim() || undefined,
        status: statusFilter === 'all' ? undefined : statusFilter,
        is_active:
          activityFilter === 'all' ? undefined : activityFilter === 'active',
        is_partner:
          partnerFilter === 'all' ? undefined : partnerFilter === 'partner',
        offset: 0,
        limit: 100,
      });

      return response.data;
    },
    staleTime: 15_000,
  });

  const items = customersQuery.data?.items ?? [];
  const selectedCustomer =
    items.find((item) => item.id === selectedUserId) ?? items[0] ?? null;

  return (
    <CustomersPageShell
      eyebrow={t('directory.eyebrow')}
      title={t('directory.title')}
      description={t('directory.description')}
      icon={Users}
      actions={
        <>
          <div className="relative min-w-[18rem]">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={t('directory.searchPlaceholder')}
              className="h-10 w-full rounded-md border border-input bg-transparent pl-10 pr-3 text-sm text-foreground"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            className="h-10 rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground"
          >
            <option value="all">{t('directory.statusPlaceholder')}</option>
            {['active', 'pending', 'blocked', 'suspended'].map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
          <select
            value={activityFilter}
            onChange={(event) =>
              setActivityFilter(event.target.value as 'all' | 'active' | 'inactive')
            }
            className="h-10 rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground"
          >
            <option value="all">{t('directory.activityPlaceholder')}</option>
            <option value="active">{t('directory.activeOnly')}</option>
            <option value="inactive">{t('directory.inactiveOnly')}</option>
          </select>
          <select
            value={partnerFilter}
            onChange={(event) =>
              setPartnerFilter(event.target.value as 'all' | 'partner' | 'non_partner')
            }
            className="h-10 rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground"
          >
            <option value="all">{t('directory.partnerPlaceholder')}</option>
            <option value="partner">{t('directory.partnerOnly')}</option>
            <option value="non_partner">{t('directory.nonPartnersOnly')}</option>
          </select>
        </>
      }
      metrics={[
        {
          label: t('directory.metrics.total'),
          value: String(customersQuery.data?.total ?? 0),
          hint: t('directory.metrics.totalHint'),
          tone: 'info',
        },
        {
          label: t('directory.metrics.active'),
          value: String(items.filter((item) => item.is_active).length),
          hint: t('directory.metrics.activeHint'),
          tone: 'success',
        },
        {
          label: t('directory.metrics.partners'),
          value: String(items.filter((item) => item.is_partner).length),
          hint: t('directory.metrics.partnersHint'),
          tone: 'warning',
        },
        {
          label: t('directory.metrics.telegram'),
          value: String(items.filter((item) => item.telegram_id).length),
          hint: t('directory.metrics.telegramHint'),
          tone: 'neutral',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-8">
          {customersQuery.isError ? (
            <div className="rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
              {getErrorMessage(customersQuery.error, t('common.actionFailed'))}
            </div>
          ) : null}

          <div className="mt-2">
            {customersQuery.isLoading ? (
              <div className="grid gap-3">
                {Array.from({ length: 6 }).map((_, index) => (
                  <div
                    key={index}
                    className="h-16 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                  />
                ))}
              </div>
            ) : items.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
                {t('directory.empty')}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('directory.table.customer')}</TableHead>
                    <TableHead>{t('directory.table.status')}</TableHead>
                    <TableHead>{t('directory.table.partner')}</TableHead>
                    <TableHead>{t('directory.table.telegram')}</TableHead>
                    <TableHead>{t('directory.table.lastLogin')}</TableHead>
                    <TableHead>{t('common.actions')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((item) => {
                    const isSelected = selectedCustomer?.id === item.id;
                    return (
                      <TableRow
                        key={item.id}
                        className={isSelected ? 'border-l-2 border-l-neon-cyan bg-neon-cyan/5' : undefined}
                        onClick={() => setSelectedUserId(item.id)}
                      >
                        <TableCell>
                          <div className="space-y-1">
                            <p className="font-display uppercase tracking-[0.14em] text-white">
                              {item.email}
                            </p>
                            <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                              @{item.username ?? shortId(item.id)} / #{shortId(item.id)}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <CustomerStatusChip
                            label={item.status}
                            tone={item.is_active ? 'success' : 'warning'}
                          />
                        </TableCell>
                        <TableCell>
                          <CustomerStatusChip
                            label={item.is_partner ? t('common.partner') : t('common.none')}
                            tone={item.is_partner ? 'warning' : 'neutral'}
                          />
                        </TableCell>
                        <TableCell>
                          {item.telegram_username
                            ? `@${item.telegram_username}`
                            : item.telegram_id ?? '--'}
                        </TableCell>
                        <TableCell>{formatDateTime(item.last_login_at, locale)}</TableCell>
                        <TableCell>
                          <Link
                            href={`/customers/${item.id}`}
                            className={buttonVariants({ size: 'sm', variant: 'ghost' })}
                          >
                            {t('directory.openCard')}
                          </Link>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </div>
        </section>

        <aside className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-4">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('directory.previewTitle')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('directory.previewDescription')}
          </p>

          {selectedCustomer ? (
            <div className="mt-5 space-y-3">
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <p className="text-sm font-display uppercase tracking-[0.14em] text-white">
                  {selectedCustomer.email}
                </p>
                <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  #{selectedCustomer.id}
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <CustomerStatusChip
                    label={selectedCustomer.status}
                    tone={selectedCustomer.is_active ? 'success' : 'warning'}
                  />
                  <CustomerStatusChip
                    label={selectedCustomer.is_partner ? t('common.partner') : t('common.none')}
                    tone={selectedCustomer.is_partner ? 'warning' : 'neutral'}
                  />
                </div>
              </div>

              {[
                [t('common.lastLogin'), formatDateTime(selectedCustomer.last_login_at, locale)],
                [t('common.telegram'), selectedCustomer.telegram_username ? `@${selectedCustomer.telegram_username}` : selectedCustomer.telegram_id ?? '--'],
                [t('common.referralCode'), selectedCustomer.referral_code ?? '--'],
                [t('common.remnawaveUuid'), selectedCustomer.remnawave_uuid ?? '--'],
              ].map(([label, value]) => (
                <div
                  key={String(label)}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {label}
                  </p>
                  <p className="mt-2 break-all text-sm font-mono text-white">{value}</p>
                </div>
              ))}

              <Link
                href={`/customers/${selectedCustomer.id}`}
                className={buttonVariants({ variant: 'default' })}
              >
                {t('directory.openCard')}
              </Link>
            </div>
          ) : (
            <div className="mt-5 rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
              {t('directory.empty')}
            </div>
          )}
        </aside>
      </div>
    </CustomersPageShell>
  );
}
