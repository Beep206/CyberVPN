'use client';

import { AlertTriangle, Layers3, RefreshCw } from 'lucide-react';
import { useLocale } from 'next-intl';
import { useCustomerSubscriptions } from './customer-subscription-context';
import type { CustomerSubscriptionSummary } from '@/lib/api/customer-subscriptions';

type SwitcherCopy = {
  accountScoped: string;
  empty: string;
  label: string;
  loading: string;
  refresh: string;
  selected: string;
  status: string;
};

function getCopy(locale: string): SwitcherCopy {
  if (locale.startsWith('ru')) {
    return {
      accountScoped: 'VPN-конфигурация пока общая для аккаунта, коммерческий контекст выбранной подписки применяется отдельно.',
      empty: 'Подписки пока не найдены',
      label: 'Выбор подписки',
      loading: 'Загрузка подписок',
      refresh: 'Обновить',
      selected: 'Выбрана',
      status: 'Статус',
    };
  }

  return {
    accountScoped: 'VPN config is account-scoped for now; the selected subscription controls the commercial context.',
    empty: 'No subscriptions found yet',
    label: 'Subscription selector',
    loading: 'Loading subscriptions',
    refresh: 'Refresh',
    selected: 'Selected',
    status: 'Status',
  };
}

function formatSubscriptionLabel(subscription: CustomerSubscriptionSummary): string {
  const trafficLabel =
    typeof subscription.effective_entitlements.display_traffic_label === 'string'
      ? subscription.effective_entitlements.display_traffic_label
      : null;

  return [
    subscription.display_name ?? subscription.plan_code ?? subscription.kind,
    trafficLabel,
    subscription.expires_at ? subscription.expires_at.slice(0, 10) : null,
  ]
    .filter(Boolean)
    .join(' / ');
}

export function CustomerSubscriptionSwitcher() {
  const locale = useLocale();
  const copy = getCopy(locale);
  const {
    isError,
    isLoading,
    limitations,
    refetch,
    selectedSubscription,
    selectedSubscriptionKey,
    setSelectedSubscriptionKey,
    subscriptions,
  } = useCustomerSubscriptions();

  if (isLoading) {
    return (
      <div className="border-b border-grid-line/40 bg-terminal-bg/80 px-4 py-3 md:px-6">
        <div className="flex min-h-11 items-center gap-3 rounded-2xl border border-grid-line/30 bg-terminal-surface/55 px-4 font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
          <RefreshCw className="h-4 w-4 animate-spin text-neon-cyan" aria-hidden="true" />
          {copy.loading}
        </div>
      </div>
    );
  }

  if (isError || subscriptions.length === 0) {
    return (
      <div className="border-b border-grid-line/40 bg-terminal-bg/80 px-4 py-3 md:px-6">
        <div className="flex min-h-11 flex-wrap items-center justify-between gap-3 rounded-2xl border border-amber-400/30 bg-amber-400/10 px-4 text-amber-200">
          <div className="flex items-center gap-3 font-mono text-xs uppercase tracking-[0.16em]">
            <AlertTriangle className="h-4 w-4" aria-hidden="true" />
            {copy.empty}
          </div>
          <button
            type="button"
            onClick={refetch}
            className="inline-flex min-h-9 items-center gap-2 rounded-xl border border-amber-400/30 px-3 py-1 font-mono text-xs uppercase tracking-[0.14em] transition hover:bg-amber-400/10 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-amber-300 focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
          >
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            {copy.refresh}
          </button>
        </div>
      </div>
    );
  }

  return (
    <section className="border-b border-grid-line/40 bg-terminal-bg/80 px-4 py-3 md:px-6" aria-label={copy.label}>
      <div className="flex flex-col gap-3 rounded-2xl border border-neon-cyan/20 bg-terminal-surface/55 px-4 py-3 backdrop-blur lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan">
            <Layers3 className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              {copy.selected}
            </p>
            <p className="truncate font-display text-base text-white">
              {selectedSubscription ? formatSubscriptionLabel(selectedSubscription) : copy.empty}
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <label className="sr-only" htmlFor="customer-subscription-switcher">
            {copy.label}
          </label>
          <select
            id="customer-subscription-switcher"
            value={selectedSubscriptionKey ?? ''}
            onChange={(event) => setSelectedSubscriptionKey(event.target.value)}
            className="min-h-11 rounded-xl border border-grid-line/40 bg-black/30 px-3 py-2 font-mono text-sm text-foreground outline-hidden transition focus:border-neon-cyan focus:ring-2 focus:ring-neon-cyan/40"
          >
            {subscriptions.map((subscription) => (
              <option key={subscription.subscription_key} value={subscription.subscription_key}>
                {formatSubscriptionLabel(subscription)}
              </option>
            ))}
          </select>

          {selectedSubscription ? (
            <span className="inline-flex min-h-9 items-center rounded-full border border-matrix-green/25 bg-matrix-green/10 px-3 py-1 font-mono text-xs uppercase tracking-[0.14em] text-matrix-green">
              {copy.status}: {selectedSubscription.status}
            </span>
          ) : null}
        </div>
      </div>

      {limitations.length > 0 ? (
        <p className="mt-2 font-mono text-[11px] leading-5 text-muted-foreground">
          {copy.accountScoped}
        </p>
      ) : null}
    </section>
  );
}
