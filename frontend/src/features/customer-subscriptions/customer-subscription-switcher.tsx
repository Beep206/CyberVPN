'use client';

import { AlertTriangle, Layers3, RefreshCw } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import { useCustomerSubscriptions } from './customer-subscription-context';
import type { CustomerSubscriptionSummary } from '@/lib/api/customer-subscriptions';

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
  const t = useTranslations('Subscriptions');
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
  const isAccountScoped =
    selectedSubscription?.management_scope === 'account_vpn_identity' ||
    selectedSubscription?.can_manage === false ||
    limitations.length > 0;

  if (isLoading) {
    return (
      <div className="border-b border-grid-line/40 bg-terminal-bg/80 px-4 py-3 md:px-6">
        <div className="flex min-h-11 items-center gap-3 rounded-2xl border border-grid-line/30 bg-terminal-surface/55 px-4 font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
          <RefreshCw className="h-4 w-4 animate-spin text-neon-cyan" aria-hidden="true" />
          {t('switcher.loading')}
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
            {t('switcher.empty')}
          </div>
          <button
            type="button"
            onClick={refetch}
            aria-label={t('switcher.refresh')}
            className="inline-flex min-h-9 items-center gap-2 rounded-xl border border-amber-400/30 px-3 py-1 font-mono text-xs uppercase tracking-[0.14em] transition hover:bg-amber-400/10 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-amber-300 focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
          >
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            {t('switcher.refresh')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <section className="border-b border-grid-line/40 bg-terminal-bg/80 px-4 py-3 md:px-6" aria-label={t('switcher.label')}>
      <div
        className={cn(
          'flex flex-col gap-3 rounded-2xl border px-4 py-3 backdrop-blur transition-colors lg:flex-row lg:items-center lg:justify-between',
          isAccountScoped
            ? 'border-amber-400/25 bg-terminal-surface/35 text-muted-foreground'
            : 'border-neon-cyan/20 bg-terminal-surface/55',
        )}
      >
        <div className="flex min-w-0 items-center gap-3">
          <div
            className={cn(
              'flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border',
              isAccountScoped
                ? 'border-amber-400/25 bg-amber-400/10 text-amber-200'
                : 'border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan',
            )}
          >
            <Layers3 className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              {t('switcher.selected')}
            </p>
            <p className="max-w-full whitespace-normal break-normal font-display text-base leading-6 text-white">
              {selectedSubscription ? formatSubscriptionLabel(selectedSubscription) : t('switcher.empty')}
            </p>
          </div>
        </div>

        <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center">
          <label className="sr-only" htmlFor="customer-subscription-switcher">
            {t('switcher.label')}
          </label>
          <select
            id="customer-subscription-switcher"
            value={selectedSubscriptionKey ?? ''}
            onChange={(event) => setSelectedSubscriptionKey(event.target.value)}
            className="min-h-11 min-w-0 rounded-xl border border-grid-line/40 bg-black/30 px-3 py-2 font-mono text-sm text-foreground outline-hidden transition focus:border-neon-cyan focus:ring-2 focus:ring-neon-cyan/40 sm:max-w-sm"
          >
            {subscriptions.map((subscription) => (
              <option key={subscription.subscription_key} value={subscription.subscription_key}>
                {formatSubscriptionLabel(subscription)}
              </option>
            ))}
          </select>

          {selectedSubscription ? (
            <span
              className={cn(
                'inline-flex min-h-9 max-w-full items-center rounded-full border px-3 py-1 font-mono text-xs uppercase tracking-[0.14em] whitespace-normal break-normal',
                isAccountScoped
                  ? 'border-amber-400/25 bg-amber-400/10 text-amber-200'
                  : 'border-matrix-green/25 bg-matrix-green/10 text-matrix-green',
              )}
            >
              {t('switcher.status')}: {selectedSubscription.status}
            </span>
          ) : null}
        </div>
      </div>

      {isAccountScoped ? (
        <p className="mt-2 font-mono text-[11px] leading-5 text-muted-foreground">
          {t('switcher.accountScoped')}
        </p>
      ) : null}
    </section>
  );
}
