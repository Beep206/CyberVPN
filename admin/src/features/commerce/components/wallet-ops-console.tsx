'use client';

import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Search, WalletCards } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { adminWalletApi } from '@/lib/api/wallet';
import { CommercePageShell } from '@/features/commerce/components/commerce-page-shell';
import { formatCurrencyAmount } from '@/features/commerce/lib/formatting';

export function WalletOpsConsole() {
  const t = useTranslations('Commerce');
  const queryClient = useQueryClient();
  const [lookupInput, setLookupInput] = useState('');
  const [activeUserUuid, setActiveUserUuid] = useState('');
  const [topupAmount, setTopupAmount] = useState('');
  const [topupDescription, setTopupDescription] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);

  const walletQuery = useQuery({
    queryKey: ['commerce', 'wallet', activeUserUuid],
    queryFn: async () => {
      const response = await adminWalletApi.getWallet(activeUserUuid);
      return response.data;
    },
    enabled: Boolean(activeUserUuid),
    staleTime: 30_000,
  });

  const topupMutation = useMutation({
    mutationFn: (payload: { userUuid: string; amount: number; description?: string }) =>
      adminWalletApi.topupWallet(payload.userUuid, {
        amount: payload.amount,
        description: payload.description,
      }),
    onSuccess: async (response, payload) => {
      await queryClient.invalidateQueries({ queryKey: ['commerce', 'wallet', payload.userUuid] });
      setFeedback(
        `${t('wallets.topupSuccess')}: ${formatCurrencyAmount(
          response.data.amount,
          walletQuery.data?.currency ?? 'USD',
        )}`,
      );
      setTopupAmount('');
      setTopupDescription('');
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  function handleLookupSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    setActiveUserUuid(lookupInput.trim());
  }

  async function handleTopupSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeUserUuid) {
      setFeedback(t('wallets.lookupRequired'));
      return;
    }

    const amount = Number(topupAmount);
    if (!Number.isFinite(amount) || amount <= 0) {
      setFeedback(t('common.validation.amountInvalid'));
      return;
    }

    await topupMutation.mutateAsync({
      userUuid: activeUserUuid,
      amount,
      description: topupDescription.trim() || undefined,
    });
  }

  return (
    <CommercePageShell
      eyebrow={t('wallets.eyebrow')}
      title={t('wallets.title')}
      description={t('wallets.description')}
      icon={WalletCards}
      metrics={[
        {
          label: t('wallets.metrics.balance'),
          value: formatCurrencyAmount(walletQuery.data?.balance, walletQuery.data?.currency ?? 'USD'),
          hint: t('wallets.metrics.balanceHint'),
          tone: 'success',
        },
        {
          label: t('wallets.metrics.frozen'),
          value: formatCurrencyAmount(walletQuery.data?.frozen, walletQuery.data?.currency ?? 'USD'),
          hint: t('wallets.metrics.frozenHint'),
          tone: 'warning',
        },
        {
          label: t('wallets.metrics.currency'),
          value: walletQuery.data?.currency ?? '--',
          hint: t('wallets.metrics.currencyHint'),
          tone: 'info',
        },
        {
          label: t('wallets.metrics.lookup'),
          value: activeUserUuid ? activeUserUuid.slice(0, 8) : '--',
          hint: t('wallets.metrics.lookupHint'),
          tone: 'neutral',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('wallets.lookupTitle')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('wallets.lookupDescription')}
          </p>

          <form className="mt-5 space-y-4" onSubmit={handleLookupSubmit}>
            <label className="block space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('common.userUuid')}
              </span>
              <Input
                value={lookupInput}
                onChange={(event) => setLookupInput(event.target.value)}
                placeholder={t('wallets.lookupPlaceholder')}
              />
            </label>

            <Button type="submit" magnetic={false}>
              <Search className="mr-2 h-4 w-4" />
              {t('wallets.lookupAction')}
            </Button>
          </form>

          <div className="mt-5 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4 text-sm font-mono leading-6 text-muted-foreground">
            {activeUserUuid
              ? `${t('wallets.activeLookup')}: ${activeUserUuid}`
              : t('wallets.lookupEmpty')}
          </div>
        </section>

        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('wallets.topupTitle')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('wallets.topupDescription')}
          </p>

          {feedback ? (
            <div className="mt-5 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-foreground">
              {feedback}
            </div>
          ) : null}

          {walletQuery.isLoading ? (
            <div className="mt-5 h-40 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45" />
          ) : walletQuery.isError ? (
            <div className="mt-5 rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-6 text-sm font-mono text-neon-pink">
              {t('wallets.lookupError')}
            </div>
          ) : walletQuery.data ? (
            <form className="mt-5 space-y-4" onSubmit={handleTopupSubmit}>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="block space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('common.amount')}
                  </span>
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    value={topupAmount}
                    onChange={(event) => setTopupAmount(event.target.value)}
                    placeholder="25"
                  />
                </label>

                <label className="block space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('common.description')}
                  </span>
                  <Input
                    value={topupDescription}
                    onChange={(event) => setTopupDescription(event.target.value)}
                    placeholder={t('wallets.descriptionPlaceholder')}
                  />
                </label>
              </div>

              <Button type="submit" magnetic={false} disabled={topupMutation.isPending}>
                {topupMutation.isPending ? t('common.saving') : t('wallets.topupAction')}
              </Button>
            </form>
          ) : (
            <div className="mt-5 rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-10 text-center text-sm font-mono text-muted-foreground">
              {t('wallets.lookupEmpty')}
            </div>
          )}
        </section>
      </div>
    </CommercePageShell>
  );
}
