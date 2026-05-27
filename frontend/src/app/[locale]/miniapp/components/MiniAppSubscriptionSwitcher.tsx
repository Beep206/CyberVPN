'use client';

import { Layers3, RefreshCw } from 'lucide-react';
import { useLocale } from 'next-intl';
import { useQueryClient } from '@tanstack/react-query';
import { useCustomerSubscriptions } from '@/features/customer-subscriptions/customer-subscription-context';
import { useTelegramWebApp } from '../hooks/useTelegramWebApp';

function getCopy(locale: string) {
  if (locale.startsWith('ru')) {
    return {
      label: 'Подписка',
      loading: 'Загрузка подписок',
      selected: 'Выбрана подписка',
    };
  }

  return {
    label: 'Subscription',
    loading: 'Loading subscriptions',
    selected: 'Selected subscription',
  };
}

function formatSubscriptionLabel(subscription: {
  display_name?: string | null;
  plan_code?: string | null;
  kind: string;
  status: string;
  expires_at?: string | null;
  effective_entitlements?: Record<string, unknown>;
}) {
  const trafficLabel =
    typeof subscription.effective_entitlements?.display_traffic_label === 'string'
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

export function MiniAppSubscriptionSwitcher() {
  const locale = useLocale();
  const copy = getCopy(locale);
  const queryClient = useQueryClient();
  const { haptic } = useTelegramWebApp();
  const {
    isLoading,
    selectedSubscription,
    selectedSubscriptionKey,
    setSelectedSubscriptionKey,
    subscriptions,
  } = useCustomerSubscriptions();

  if (isLoading && subscriptions.length === 0) {
    return (
      <div className="miniapp-card mb-4 rounded-lg border p-3">
        <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground">
          <RefreshCw className="h-4 w-4 animate-spin text-neon-cyan" aria-hidden="true" />
          {copy.loading}
        </div>
      </div>
    );
  }

  if (subscriptions.length <= 1) {
    return null;
  }

  return (
    <section className="miniapp-card mb-4 rounded-lg border p-3" aria-label={copy.label}>
      <div className="mb-2 flex items-center gap-2">
        <Layers3 className="h-4 w-4 text-neon-cyan" aria-hidden="true" />
        <div className="min-w-0">
          <p className="text-[10px] font-mono uppercase tracking-[0.16em] text-muted-foreground">
            {copy.selected}
          </p>
          <p className="truncate text-sm font-display">
            {selectedSubscription ? formatSubscriptionLabel(selectedSubscription) : copy.label}
          </p>
        </div>
      </div>

      <label className="sr-only" htmlFor="miniapp-subscription-switcher">
        {copy.label}
      </label>
      <select
        id="miniapp-subscription-switcher"
        value={selectedSubscriptionKey ?? ''}
        onChange={(event) => {
          haptic('medium');
          setSelectedSubscriptionKey(event.target.value);
          void Promise.all([
            queryClient.invalidateQueries({ queryKey: ['miniapp-bootstrap'] }),
            queryClient.invalidateQueries({ queryKey: ['miniapp-offers'] }),
            queryClient.resetQueries({ queryKey: ['miniapp-config'] }),
          ]);
        }}
        className="min-h-11 w-full rounded-lg border bg-background px-3 py-2 font-mono text-sm text-foreground outline-hidden transition focus:border-neon-cyan focus:ring-2 focus:ring-neon-cyan/35"
      >
        {subscriptions.map((subscription) => (
          <option key={subscription.subscription_key} value={subscription.subscription_key}>
            {formatSubscriptionLabel(subscription)}
          </option>
        ))}
      </select>
    </section>
  );
}
