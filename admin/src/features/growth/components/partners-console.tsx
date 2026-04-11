'use client';

import { useDeferredValue, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { UserRoundPlus } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { Button } from '@/components/ui/button';
import { growthApi } from '@/lib/api/growth';
import { GrowthEmptyState } from '@/features/growth/components/growth-empty-state';
import { GrowthPageShell } from '@/features/growth/components/growth-page-shell';
import { GrowthStatusChip } from '@/features/growth/components/growth-status-chip';
import {
  formatCurrencyAmount,
  formatDateTime,
  getErrorMessage,
  shortId,
} from '@/features/growth/lib/formatting';

interface PartnerPromotionResult {
  userId: string;
  status: string;
}

export function PartnersConsole() {
  const t = useTranslations('Growth');
  const locale = useLocale();
  const [userId, setUserId] = useState('');
  const [search, setSearch] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [promotionHistory, setPromotionHistory] = useState<PartnerPromotionResult[]>([]);
  const deferredSearch = useDeferredValue(search);

  const partnersQuery = useQuery({
    queryKey: ['growth', 'partners', deferredSearch],
    queryFn: async () => {
      const response = await growthApi.listPartners({
        search: deferredSearch.trim() || undefined,
        offset: 0,
        limit: 50,
      });

      return response.data;
    },
    staleTime: 15_000,
  });

  const promoteMutation = useMutation({
    mutationFn: growthApi.promotePartner,
    onSuccess: (response, variables) => {
      setPromotionHistory((current) => [
        {
          userId: variables.user_id,
          status:
            typeof response.data.status === 'string'
              ? response.data.status
              : 'promoted',
        },
        ...current,
      ].slice(0, 6));
      setUserId('');
      setErrorMessage(null);
      void partnersQuery.refetch();
    },
    onError: (error) => {
      setErrorMessage(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await promoteMutation.mutateAsync({ user_id: userId.trim() });
  }

  const partners = partnersQuery.data?.items ?? [];
  const activeCodes = partners.reduce((sum, item) => sum + item.active_code_count, 0);
  const totalEarned = partners.reduce((sum, item) => sum + item.total_earned, 0);

  return (
    <GrowthPageShell
      eyebrow={t('partners.eyebrow')}
      title={t('partners.title')}
      description={t('partners.description')}
      icon={UserRoundPlus}
      metrics={[
        {
          label: t('partners.metrics.directory'),
          value: String(partnersQuery.data?.total ?? 0),
          hint: t('partners.metrics.directoryHint'),
          tone: partners.length > 0 ? 'success' : 'neutral',
        },
        {
          label: t('partners.metrics.activeCodes'),
          value: String(activeCodes),
          hint: t('partners.metrics.activeCodesHint'),
          tone: activeCodes > 0 ? 'warning' : 'neutral',
        },
        {
          label: t('partners.metrics.totalEarned'),
          value: formatCurrencyAmount(totalEarned, 'USD', locale),
          hint: t('partners.metrics.totalEarnedHint'),
          tone: totalEarned > 0 ? 'info' : 'neutral',
        },
        {
          label: t('partners.metrics.lastUser'),
          value: promotionHistory[0]?.userId ? shortId(promotionHistory[0].userId) : '--',
          hint: t('partners.metrics.lastUserHint'),
          tone: 'info',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5"
        >
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('partners.formTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('partners.formDescription')}
              </p>
            </div>
            <GrowthStatusChip label={t('partners.liveDirectory')} tone="success" />
          </div>

          {errorMessage ? (
            <div className="mt-5 rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
              {errorMessage}
            </div>
          ) : null}

          <label className="mt-5 block space-y-2">
            <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
              {t('partners.fields.userId')}
            </span>
            <input
              required
              value={userId}
              onChange={(event) => setUserId(event.target.value)}
              className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
            />
          </label>

          <label className="mt-5 block space-y-2">
            <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
              {t('partners.fields.search')}
            </span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
            />
          </label>

          <div className="mt-5 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
            <p className="text-sm font-mono leading-6 text-muted-foreground">
              {t('partners.backendNote')}
            </p>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <Button
              type="submit"
              magnetic={false}
              disabled={promoteMutation.isPending}
            >
              {t('partners.promoteAction')}
            </Button>
            <Button
              type="button"
              variant="ghost"
              magnetic={false}
              onClick={() => {
                setUserId('');
                setErrorMessage(null);
                setSearch('');
              }}
            >
              {t('common.clear')}
            </Button>
          </div>
        </form>

        <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('partners.directoryTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('partners.directoryDescription')}
              </p>
            </div>
            {partners.length ? (
              <GrowthStatusChip
                label={t('partners.directoryCount', { count: partnersQuery.data?.total ?? partners.length })}
                tone="success"
              />
            ) : null}
          </div>

          <div className="mt-5 space-y-3">
            {partnersQuery.isLoading ? (
              Array.from({ length: 4 }).map((_, index) => (
                <div
                  key={index}
                  className="h-20 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))
            ) : partners.length ? (
              partners.map((item) => (
                <div
                  key={item.user.id}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {item.user.email}
                      </p>
                      <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        @{item.user.username ?? shortId(item.user.id, 12)} / #{shortId(item.user.id, 12)}
                      </p>
                    </div>
                    <GrowthStatusChip
                      label={formatCurrencyAmount(item.total_earned, 'USD', locale)}
                      tone={item.total_earned > 0 ? 'warning' : 'info'}
                    />
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    <GrowthStatusChip
                      label={t('partners.badges.codes', { count: item.code_count })}
                      tone="info"
                    />
                    <GrowthStatusChip
                      label={t('partners.badges.activeCodes', { count: item.active_code_count })}
                      tone={item.active_code_count > 0 ? 'success' : 'neutral'}
                    />
                    <GrowthStatusChip
                      label={t('partners.badges.clients', { count: item.total_clients })}
                      tone="warning"
                    />
                    <GrowthStatusChip
                      label={formatDateTime(item.last_activity_at, locale)}
                      tone="neutral"
                    />
                  </div>

                  <div className="mt-4">
                    <Link
                      href={`/customers/${item.user.id}`}
                      className="text-xs font-mono uppercase tracking-[0.18em] text-neon-cyan transition-opacity hover:opacity-80"
                    >
                      {t('partners.openCustomer')}
                    </Link>
                  </div>
                </div>
              ))
            ) : (
              <GrowthEmptyState label={t('partners.directoryEmpty')} />
            )}
          </div>
        </div>
      </div>
    </GrowthPageShell>
  );
}
