'use client';

import { useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock3,
  CreditCard,
  Gift,
  History,
  KeyRound,
  PackagePlus,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  TicketPercent,
  Wallet,
  Zap,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { useState, type ReactNode } from 'react';
import { Link } from '@/i18n/navigation';
import { useCustomerSubscriptions } from '@/features/customer-subscriptions/customer-subscription-context';
import {
  addonsApi,
  commerceApi,
  customerSubscriptionsApi,
  DEFAULT_SERVICE_STATE_REQUEST,
  entitlementsApi,
  plansApi,
  serviceAccessApi,
  trialApi,
} from '@/lib/api';
import { CancelSubscriptionModal } from '@/app/[locale]/(dashboard)/subscriptions/components/CancelSubscriptionModal';
import { PurchaseConfirmModal } from '@/app/[locale]/(dashboard)/subscriptions/components/PurchaseConfirmModal';
import {
  formatDate,
  formatDuration,
  formatLabel,
  formatMoney,
  getAddonPrice,
  getCurrentPlan,
  getDaysUntilExpiry,
  getOrderDisplayName,
  getOrderStatus,
  getOrderTone,
  getPlanAction,
  getPlanPrice,
  getPublicPlans,
  getSortedOrders,
  getSubscriptionHealth,
  getTrafficLabel,
  getVisibleAddons,
  isInactiveEntitlement,
  isServiceProvisioned,
  readEntitlementNumber,
  readEntitlementString,
  readEntitlementStringArray,
  type AddonRecord,
  type PlanAction,
  type PlanRecord,
  type StatusTone,
  type SubscriptionHealth,
} from './subscription-cabinet-model';
import type { components } from '@/lib/api/generated/types';

type CheckoutQuote = components['schemas']['CheckoutQuoteResponse'];
type CheckoutCommit = components['schemas']['CheckoutCommitResponse'];

type AsyncActionState = {
  id: string;
  message: string;
  quote?: CheckoutQuote;
  status: 'error' | 'idle' | 'loading' | 'quoted' | 'success';
};

const LIVE_STALE_MS = 30_000;
const CATALOG_STALE_MS = 5 * 60_000;
const LIVE_REFETCH_MS = 45_000;

const toneClasses: Record<
  StatusTone,
  {
    border: string;
    fill: string;
    text: string;
  }
> = {
  amber: {
    border: 'border-amber-400/30',
    fill: 'bg-amber-400/10',
    text: 'text-amber-300',
  },
  cyan: {
    border: 'border-neon-cyan/30',
    fill: 'bg-neon-cyan/10',
    text: 'text-neon-cyan',
  },
  green: {
    border: 'border-matrix-green/30',
    fill: 'bg-matrix-green/10',
    text: 'text-matrix-green',
  },
  pink: {
    border: 'border-neon-pink/30',
    fill: 'bg-neon-pink/10',
    text: 'text-neon-pink',
  },
  purple: {
    border: 'border-neon-purple/30',
    fill: 'bg-neon-purple/10',
    text: 'text-neon-purple',
  },
};

function visiblePolling(intervalMs: number) {
  return (query: { state: { error: unknown } }) => {
    if (query.state.error) {
      return false;
    }

    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
      return false;
    }

    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      return false;
    }

    return intervalMs;
  };
}

function getHealthTone(health: SubscriptionHealth): StatusTone {
  if (health === 'critical') {
    return 'pink';
  }

  if (health === 'attention') {
    return 'amber';
  }

  return 'green';
}

function getPlanActionTone(action: PlanAction): StatusTone {
  if (action === 'current') {
    return 'green';
  }

  if (action === 'upgrade') {
    return 'cyan';
  }

  if (action === 'downgrade') {
    return 'amber';
  }

  return 'purple';
}

function StatusPill({ label, tone }: { label: string; tone: StatusTone }) {
  const classes = toneClasses[tone];

  return (
    <span
      className={`inline-flex min-h-8 items-center rounded-full border px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] ${classes.border} ${classes.fill} ${classes.text}`}
    >
      {label}
    </span>
  );
}

function LoadingBlock({ className = 'min-h-36' }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`${className} animate-pulse rounded-3xl border border-grid-line/30 bg-terminal-surface/40`}
    />
  );
}

function getSafeErrorMessage(fallback: string): string {
  return fallback;
}

function buildUpgradeRequest(plan: PlanRecord, currency: string) {
  return {
    channel: 'web',
    currency,
    promo_code: null,
    target_plan_id: plan.uuid,
    use_wallet: 0,
  };
}

function buildAddonRequest(addon: AddonRecord, currency: string) {
  return {
    addons: [
      {
        code: addon.code,
        qty: 1,
      },
    ],
    channel: 'web',
    currency,
    promo_code: null,
    use_wallet: 0,
  };
}

function getWriteContractGuardMessage(locale: string): string {
  if (locale.startsWith('ru')) {
    return 'Изменение плана и add-ons пока доступно только для backend current подписки. Выберите current/default подписку или дождитесь MSUB-08.';
  }

  return 'Plan changes and add-ons are available only for the backend current subscription until MSUB-08 is complete.';
}

export function SubscriptionCabinetDashboard() {
  const t = useTranslations('Subscriptions');
  const locale = useLocale();
  const { selectedSubscriptionKey } = useCustomerSubscriptions();
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [purchasePlan, setPurchasePlan] = useState<PlanRecord | null>(null);
  const [upgradeState, setUpgradeState] = useState<AsyncActionState>({
    id: '',
    message: '',
    status: 'idle',
  });
  const [addonState, setAddonState] = useState<AsyncActionState>({
    id: '',
    message: '',
    status: 'idle',
  });
  const [trialState, setTrialState] = useState<'error' | 'idle' | 'loading' | 'success'>('idle');

  const entitlementQuery = useQuery({
    queryKey: ['current-entitlements', selectedSubscriptionKey],
    queryFn: async () => {
      if (selectedSubscriptionKey) {
        const response = await customerSubscriptionsApi.getEntitlements(selectedSubscriptionKey);
        return response.data;
      }

      const response = await entitlementsApi.getCurrent();
      return response.data;
    },
    staleTime: LIVE_STALE_MS,
    refetchInterval: visiblePolling(LIVE_REFETCH_MS),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
  });

  const serviceStateQuery = useQuery({
    queryKey: ['subscription-cabinet', 'service-state', selectedSubscriptionKey],
    queryFn: async () => {
      const response = selectedSubscriptionKey
        ? await customerSubscriptionsApi.getServiceState(selectedSubscriptionKey, DEFAULT_SERVICE_STATE_REQUEST)
        : await serviceAccessApi.getCurrentServiceState();
      return response.data;
    },
    staleTime: LIVE_STALE_MS,
    refetchInterval: visiblePolling(LIVE_REFETCH_MS),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
  });

  const trialQuery = useQuery({
    queryKey: ['trial-status'],
    queryFn: async () => {
      const response = await trialApi.getStatus();
      return response.data;
    },
    staleTime: LIVE_STALE_MS,
    refetchOnWindowFocus: false,
  });

  const plansQuery = useQuery({
    queryKey: ['subscription-plans', 'web'],
    queryFn: async () => {
      const response = await plansApi.list({ channel: 'web' });
      return response.data;
    },
    staleTime: CATALOG_STALE_MS,
    refetchOnWindowFocus: false,
  });

  const addonsQuery = useQuery({
    queryKey: ['subscription-addons', 'web'],
    queryFn: async () => {
      const response = await addonsApi.listCatalog({ channel: 'web' });
      return response.data;
    },
    staleTime: CATALOG_STALE_MS,
    refetchOnWindowFocus: false,
  });

  const ordersQuery = useQuery({
    queryKey: ['orders'],
    queryFn: async () => {
      const response = await commerceApi.listOrders({ limit: 20, offset: 0 });
      return response.data;
    },
    staleTime: LIVE_STALE_MS,
    refetchInterval: visiblePolling(LIVE_REFETCH_MS),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
  });

  const entitlement = entitlementQuery.data ?? null;
  const serviceState = serviceStateQuery.data ?? null;
  const trial = trialQuery.data ?? null;
  const publicPlans = getPublicPlans(plansQuery.data ?? []);
  const currentPlan = getCurrentPlan(entitlement, publicPlans);
  const visibleAddons = getVisibleAddons(addonsQuery.data ?? [], entitlement?.plan_code).slice(0, 6);
  const sortedOrders = getSortedOrders(ordersQuery.data ?? []).slice(0, 5);
  const health = getSubscriptionHealth({ entitlement, serviceState, trial });
  const healthTone = getHealthTone(health);
  const daysUntilExpiry = getDaysUntilExpiry(entitlement);
  const deviceLimit =
    readEntitlementNumber(entitlement, 'device_limit') ?? currentPlan?.devices_included ?? null;
  const trafficLabel =
    readEntitlementString(entitlement, 'display_traffic_label') ??
    (currentPlan ? getTrafficLabel(currentPlan, locale) : t('labels.notAvailable'));
  const supportLabel = formatLabel(
    readEntitlementString(entitlement, 'support_sla') ?? currentPlan?.support_sla,
    t('labels.notAvailable'),
  );
  const connectionModes = readEntitlementStringArray(entitlement, 'connection_modes');
  const connectionModeLabel = connectionModes.length
    ? connectionModes.map((mode) => formatLabel(mode, mode)).join(' + ')
    : currentPlan?.connection_modes.map((mode) => formatLabel(mode, mode)).join(' + ') ??
      t('labels.notAvailable');
  const activeSubscription = !isInactiveEntitlement(entitlement);
  const canUseSelectedWriteContract = Boolean(selectedSubscriptionKey?.startsWith('grant:'));
  const currentPlanPrice = currentPlan ? getPlanPrice(currentPlan, locale) : null;
  const hasAnyError =
    entitlementQuery.isError ||
    serviceStateQuery.isError ||
    trialQuery.isError ||
    plansQuery.isError ||
    addonsQuery.isError ||
    ordersQuery.isError;

  const refetchCore = () =>
    Promise.all([
      entitlementQuery.refetch(),
      serviceStateQuery.refetch(),
      trialQuery.refetch(),
      ordersQuery.refetch(),
    ]);

  const handleActivateTrial = async () => {
    setTrialState('loading');

    try {
      await trialApi.activate();
      await refetchCore();
      setTrialState('success');
    } catch {
      setTrialState('error');
    }
  };

  const handleQuoteUpgrade = async (plan: PlanRecord) => {
    if (!canUseSelectedWriteContract || !selectedSubscriptionKey) {
      setUpgradeState({
        id: plan.uuid,
        message: getWriteContractGuardMessage(locale),
        status: 'error',
      });
      return;
    }

    const price = getPlanPrice(plan, locale);
    setUpgradeState({ id: plan.uuid, message: '', status: 'loading' });

    try {
      const response = await customerSubscriptionsApi.quoteUpgrade(
        selectedSubscriptionKey,
        buildUpgradeRequest(plan, price.currency),
      );
      setUpgradeState({
        id: plan.uuid,
        message: t('planActions.quoteReady', {
          amount: formatMoney(locale, response.data.gateway_amount, price.currency),
        }),
        quote: response.data,
        status: 'quoted',
      });
    } catch {
      setUpgradeState({
        id: plan.uuid,
        message: getSafeErrorMessage(t('planActions.quoteError')),
        status: 'error',
      });
    }
  };

  const handleCommitUpgrade = async (plan: PlanRecord) => {
    if (!canUseSelectedWriteContract || !selectedSubscriptionKey) {
      setUpgradeState({
        id: plan.uuid,
        message: getWriteContractGuardMessage(locale),
        status: 'error',
      });
      return;
    }

    const price = getPlanPrice(plan, locale);
    setUpgradeState((current) => ({
      ...current,
      id: plan.uuid,
      status: 'loading',
    }));

    try {
      const response = await customerSubscriptionsApi.commitUpgrade(
        selectedSubscriptionKey,
        buildUpgradeRequest(plan, price.currency),
      );
      openInvoiceIfPresent(response.data);
      await refetchCore();
      setUpgradeState({
        id: plan.uuid,
        message: t(`planActions.commit.${response.data.status === 'completed' ? 'completed' : 'pending'}`),
        status: 'success',
      });
    } catch {
      setUpgradeState({
        id: plan.uuid,
        message: getSafeErrorMessage(t('planActions.commitError')),
        status: 'error',
      });
    }
  };

  const handleQuoteAddon = async (addon: AddonRecord) => {
    if (!canUseSelectedWriteContract || !selectedSubscriptionKey) {
      setAddonState({
        id: addon.uuid,
        message: getWriteContractGuardMessage(locale),
        status: 'error',
      });
      return;
    }

    const currency = locale.startsWith('ru') && addon.price_rub ? 'RUB' : 'USD';
    setAddonState({ id: addon.uuid, message: '', status: 'loading' });

    try {
      const response = await customerSubscriptionsApi.quoteAddons(
        selectedSubscriptionKey,
        buildAddonRequest(addon, currency),
      );
      setAddonState({
        id: addon.uuid,
        message: t('addons.quoteReady', {
          amount: formatMoney(locale, response.data.gateway_amount, currency),
        }),
        quote: response.data,
        status: 'quoted',
      });
    } catch {
      setAddonState({
        id: addon.uuid,
        message: getSafeErrorMessage(t('addons.quoteError')),
        status: 'error',
      });
    }
  };

  const handlePurchaseAddon = async (addon: AddonRecord) => {
    if (!canUseSelectedWriteContract || !selectedSubscriptionKey) {
      setAddonState({
        id: addon.uuid,
        message: getWriteContractGuardMessage(locale),
        status: 'error',
      });
      return;
    }

    const currency = locale.startsWith('ru') && addon.price_rub ? 'RUB' : 'USD';
    setAddonState((current) => ({
      ...current,
      id: addon.uuid,
      status: 'loading',
    }));

    try {
      const response = await customerSubscriptionsApi.purchaseAddons(
        selectedSubscriptionKey,
        buildAddonRequest(addon, currency),
      );
      openInvoiceIfPresent(response.data);
      await refetchCore();
      setAddonState({
        id: addon.uuid,
        message: t(`addons.purchase.${response.data.status === 'completed' ? 'completed' : 'pending'}`),
        status: 'success',
      });
    } catch {
      setAddonState({
        id: addon.uuid,
        message: getSafeErrorMessage(t('addons.purchaseError')),
        status: 'error',
      });
    }
  };

  const openInvoiceIfPresent = (commit: CheckoutCommit) => {
    const paymentUrl = commit.invoice?.payment_url;

    if (paymentUrl && typeof window !== 'undefined') {
      window.open(paymentUrl, '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-[2rem] border border-neon-purple/25 bg-terminal-surface/55 p-6 shadow-[0_0_70px_rgba(157,0,255,0.08)] backdrop-blur md:p-8">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(157,0,255,0.18),transparent_34%),radial-gradient(circle_at_bottom_right,rgba(0,255,255,0.12),transparent_30%)]" />
        <div className="relative grid gap-6 lg:grid-cols-[1.25fr_0.75fr] lg:items-end">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.34em] text-neon-purple">
              {t('hero.eyebrow')}
            </p>
            <h1 className="mt-4 max-w-3xl text-4xl font-display tracking-[0.08em] text-white md:text-5xl">
              {t('title')}
            </h1>
            <p className="mt-4 max-w-2xl font-mono text-sm leading-7 text-muted-foreground">
              {t('subtitle')}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
            <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                {t('hero.health')}
              </p>
              <div className="mt-3 flex items-center gap-3">
                {health === 'healthy' ? (
                  <CheckCircle2 className="h-5 w-5 text-matrix-green" aria-hidden="true" />
                ) : (
                  <AlertTriangle className={`h-5 w-5 ${toneClasses[healthTone].text}`} aria-hidden="true" />
                )}
                <StatusPill label={t(`health.${health}`)} tone={healthTone} />
              </div>
            </div>
            <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                {t('hero.service')}
              </p>
              <div className="mt-3 flex items-center gap-3">
                <KeyRound
                  className={`h-5 w-5 ${
                    isServiceProvisioned(serviceState) ? 'text-matrix-green' : 'text-amber-300'
                  }`}
                  aria-hidden="true"
                />
                <StatusPill
                  label={t(isServiceProvisioned(serviceState) ? 'service.provisioned' : 'service.pending')}
                  tone={isServiceProvisioned(serviceState) ? 'green' : 'amber'}
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-4" aria-label={t('summary.ariaLabel')}>
        <article className="rounded-2xl border border-grid-line/30 bg-terminal-surface/45 p-5">
          <ShieldCheck className="h-5 w-5 text-neon-cyan" aria-hidden="true" />
          <p className="mt-4 font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
            {t('summary.plan')}
          </p>
          <p className="mt-2 truncate text-2xl font-display text-white">
            {entitlement?.display_name ?? currentPlan?.display_name ?? t('labels.noPlan')}
          </p>
        </article>
        <article className="rounded-2xl border border-grid-line/30 bg-terminal-surface/45 p-5">
          <Clock3 className="h-5 w-5 text-matrix-green" aria-hidden="true" />
          <p className="mt-4 font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
            {t('summary.expires')}
          </p>
          <p className="mt-2 text-2xl font-display text-white">
            {daysUntilExpiry === null ? t('labels.notAvailable') : t('summary.days', { count: daysUntilExpiry })}
          </p>
        </article>
        <article className="rounded-2xl border border-grid-line/30 bg-terminal-surface/45 p-5">
          <CreditCard className="h-5 w-5 text-neon-pink" aria-hidden="true" />
          <p className="mt-4 font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
            {t('summary.billing')}
          </p>
          <p className="mt-2 text-2xl font-display text-white">
            {currentPlanPrice?.formatted ?? t('labels.notAvailable')}
          </p>
        </article>
        <article className="rounded-2xl border border-grid-line/30 bg-terminal-surface/45 p-5">
          <PackagePlus className="h-5 w-5 text-neon-purple" aria-hidden="true" />
          <p className="mt-4 font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
            {t('summary.addons')}
          </p>
          <p className="mt-2 text-2xl font-display text-white">
            {entitlement?.addons?.length ?? 0}/{visibleAddons.length}
          </p>
        </article>
      </section>

      {trialQuery.isPending ? (
        <LoadingBlock />
      ) : trial?.is_trial_active || trial?.is_eligible ? (
        <section className="rounded-[2rem] border border-matrix-green/25 bg-terminal-surface/55 p-6 backdrop-blur">
          <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
            <div className="flex items-start gap-4">
              <div className="rounded-2xl border border-matrix-green/30 bg-matrix-green/10 p-3">
                <Zap className="h-6 w-6 text-matrix-green" aria-hidden="true" />
              </div>
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.28em] text-matrix-green">
                  {t('trial.eyebrow')}
                </p>
                <h2 className="mt-2 text-2xl font-display text-white">
                  {trial.is_trial_active ? t('trial.activeTitle') : t('trial.eligibleTitle')}
                </h2>
                <p className="mt-2 max-w-2xl font-mono text-sm leading-7 text-muted-foreground">
                  {trial.is_trial_active
                    ? t('trial.activeDescription', { count: trial.days_remaining })
                    : t('trial.eligibleDescription')}
                </p>
                {trialState === 'success' && (
                  <p className="mt-3 font-mono text-sm text-matrix-green" role="status">
                    {t('trial.success')}
                  </p>
                )}
                {trialState === 'error' && (
                  <p className="mt-3 font-mono text-sm text-amber-300" role="status">
                    {t('trial.error')}
                  </p>
                )}
              </div>
            </div>
            {trial.is_eligible && !trial.is_trial_active && (
              <button
                type="button"
                onClick={handleActivateTrial}
                disabled={trialState === 'loading'}
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-matrix-green/40 bg-matrix-green/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-matrix-green transition hover:bg-matrix-green/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Sparkles className="h-4 w-4" aria-hidden="true" />
                {trialState === 'loading' ? t('trial.activating') : t('trial.activate')}
              </button>
            )}
          </div>
        </section>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <article className="rounded-[2rem] border border-neon-cyan/25 bg-terminal-surface/55 p-6 shadow-[0_0_42px_rgba(0,255,255,0.07)] backdrop-blur">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-cyan">
                {t('current.eyebrow')}
              </p>
              <h2 className="mt-3 text-2xl font-display text-white">
                {entitlement?.display_name ?? currentPlan?.display_name ?? t('current.noPlanTitle')}
              </h2>
              <p className="mt-3 max-w-2xl font-mono text-sm leading-7 text-muted-foreground">
                {activeSubscription ? t('current.description') : t('current.noPlanDescription')}
              </p>
            </div>
            <StatusPill
              label={formatLabel(entitlement?.status, t('labels.notAvailable'))}
              tone={activeSubscription ? 'green' : 'pink'}
            />
          </div>

          {entitlementQuery.isPending ? (
            <LoadingBlock className="mt-6 min-h-56" />
          ) : (
            <div className="mt-6 space-y-5">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <Metric label={t('current.devices')} value={deviceLimit ?? t('labels.notAvailable')} />
                <Metric label={t('current.traffic')} value={trafficLabel} />
                <Metric label={t('current.support')} value={supportLabel} />
                <Metric
                  label={t('current.expiresAt')}
                  value={formatDate(entitlement?.expires_at, locale) ?? t('labels.notAvailable')}
                />
              </div>

              <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                  {t('current.connectionModes')}
                </p>
                <p className="mt-2 font-mono text-sm leading-6 text-foreground">
                  {connectionModeLabel}
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <Metric
                  label={t('service.provider')}
                  value={
                    serviceState?.service_identity?.provider_name ??
                    serviceState?.access_delivery_channel?.provider_name ??
                    t('labels.notAvailable')
                  }
                />
                <Metric
                  label={t('service.profile')}
                  value={serviceState?.provisioning_profile?.profile_key ?? t('labels.notAvailable')}
                />
                <Metric
                  label={t('service.channel')}
                  value={formatLabel(
                    serviceState?.access_delivery_channel?.channel_type,
                    t('service.pending'),
                  )}
                />
              </div>

              <div className="flex flex-wrap gap-3">
                <LinkButton href="/servers" label={t('actions.getConfig')} icon="key" />
                <LinkButton href="/payment-history" label={t('actions.paymentHistory')} icon="history" />
                <LinkButton href="/wallet" label={t('actions.wallet')} icon="wallet" />
                {activeSubscription && (
                  <button
                    type="button"
                    onClick={() => setShowCancelModal(true)}
                    className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-neon-pink/40 bg-neon-pink/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-neon-pink transition hover:bg-neon-pink/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
                  >
                    <AlertTriangle className="h-4 w-4" aria-hidden="true" />
                    {t('actions.cancel')}
                  </button>
                )}
              </div>
            </div>
          )}
        </article>

        <article className="rounded-[2rem] border border-grid-line/30 bg-terminal-surface/55 p-6 backdrop-blur">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-purple">
                {t('nextActions.eyebrow')}
              </p>
              <h2 className="mt-3 text-2xl font-display text-white">
                {t('nextActions.title')}
              </h2>
            </div>
            <ShieldCheck className="h-6 w-6 text-neon-purple" aria-hidden="true" />
          </div>

          <div className="mt-6 space-y-3">
            <ActionRow
              done={activeSubscription}
              label={activeSubscription ? t('nextActions.subscriptionReady') : t('nextActions.choosePlan')}
            />
            <ActionRow
              done={isServiceProvisioned(serviceState)}
              label={
                isServiceProvisioned(serviceState)
                  ? t('nextActions.serviceReady')
                  : t('nextActions.finishProvisioning')
              }
            />
            <ActionRow
              done={Boolean(sortedOrders.find((order) => getOrderStatus(order).toLowerCase() === 'paid'))}
              label={t('nextActions.paymentSignal')}
            />
            <ActionRow
              done={visibleAddons.length > 0}
              label={visibleAddons.length > 0 ? t('nextActions.addonsAvailable') : t('nextActions.noAddons')}
            />
          </div>
        </article>
      </section>

      <section className="rounded-[2rem] border border-grid-line/30 bg-terminal-surface/55 p-6 backdrop-blur">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-cyan">
              {t('plans.eyebrow')}
            </p>
            <h2 className="mt-3 text-2xl font-display text-white">{t('plans.title')}</h2>
            <p className="mt-3 max-w-2xl font-mono text-sm leading-7 text-muted-foreground">
              {t('plans.description')}
            </p>
          </div>
          <StatusPill label={t('plans.publicCount', { count: publicPlans.length })} tone="cyan" />
        </div>

        {plansQuery.isPending ? (
          <div className="mt-6 grid gap-4 lg:grid-cols-3">
            <LoadingBlock />
            <LoadingBlock />
            <LoadingBlock />
          </div>
        ) : publicPlans.length > 0 ? (
          <div className="mt-6 grid gap-4 lg:grid-cols-3">
            {publicPlans.map((plan) => {
              const action = getPlanAction({ currentPlan, entitlement, targetPlan: plan });
              const price = getPlanPrice(plan, locale);
              const stateForPlan = upgradeState.id === plan.uuid ? upgradeState : null;

              return (
                <article
                  key={plan.uuid}
                  className={`rounded-3xl border bg-black/20 p-5 ${
                    action === 'current' ? 'border-matrix-green/45' : 'border-grid-line/30'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                        {plan.plan_code}
                      </p>
                      <h3 className="mt-2 text-2xl font-display text-white">{plan.display_name}</h3>
                    </div>
                    <StatusPill label={t(`planActions.${action}`)} tone={getPlanActionTone(action)} />
                  </div>

                  <p className="mt-5 text-3xl font-display text-white">{price.formatted}</p>
                  <p className="mt-1 font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    {t('plans.perCycle', { duration: formatDuration(plan.duration_days) })}
                  </p>

                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    <Metric label={t('current.devices')} value={plan.devices_included} />
                    <Metric label={t('current.traffic')} value={getTrafficLabel(plan, locale)} />
                  </div>

                  <p className="mt-4 font-mono text-sm leading-6 text-muted-foreground">
                    {plan.connection_modes.map((mode) => formatLabel(mode, mode)).join(' + ')}
                  </p>

                  {stateForPlan?.message && (
                    <p
                      className={`mt-4 font-mono text-sm ${
                        stateForPlan.status === 'error' ? 'text-amber-300' : 'text-matrix-green'
                      }`}
                      role="status"
                    >
                      {stateForPlan.message}
                    </p>
                  )}

                  <PlanActionButton
                    action={action}
                    disabled={!canUseSelectedWriteContract}
                    loading={stateForPlan?.status === 'loading'}
                    quoteReady={stateForPlan?.status === 'quoted'}
                    onCommit={() => handleCommitUpgrade(plan)}
                    onPurchase={() => setPurchasePlan(plan)}
                    onQuote={() => handleQuoteUpgrade(plan)}
                    t={t}
                  />
                </article>
              );
            })}
          </div>
        ) : (
          <p className="mt-6 rounded-2xl border border-amber-400/30 bg-amber-400/10 p-5 font-mono text-sm text-amber-100">
            {t('plans.empty')}
          </p>
        )}
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <article className="rounded-[2rem] border border-neon-purple/25 bg-terminal-surface/55 p-6 backdrop-blur">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-purple">
                {t('addons.eyebrow')}
              </p>
              <h2 className="mt-3 text-2xl font-display text-white">{t('addons.title')}</h2>
              <p className="mt-3 max-w-2xl font-mono text-sm leading-7 text-muted-foreground">
                {t('addons.description')}
              </p>
            </div>
            <Gift className="h-6 w-6 text-neon-purple" aria-hidden="true" />
          </div>

          {addonsQuery.isPending ? (
            <LoadingBlock className="mt-6 min-h-56" />
          ) : visibleAddons.length > 0 ? (
            <div className="mt-6 space-y-4">
              {visibleAddons.map((addon) => {
                const stateForAddon = addonState.id === addon.uuid ? addonState : null;
                return (
                  <div key={addon.uuid} className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <h3 className="font-display text-lg text-white">{addon.display_name}</h3>
                        <p className="mt-1 font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
                          {addon.code} / {formatLabel(addon.duration_mode, addon.duration_mode)}
                        </p>
                      </div>
                      <p className="font-display text-xl text-neon-purple">
                        {getAddonPrice(addon, locale)}
                      </p>
                    </div>

                    {stateForAddon?.message && (
                      <p
                        className={`mt-3 font-mono text-sm ${
                          stateForAddon.status === 'error' ? 'text-amber-300' : 'text-matrix-green'
                        }`}
                        role="status"
                      >
                        {stateForAddon.message}
                      </p>
                    )}

                    <div className="mt-4 flex flex-wrap gap-3">
                      <button
                        type="button"
                        onClick={() => handleQuoteAddon(addon)}
                        disabled={
                          !activeSubscription ||
                          !canUseSelectedWriteContract ||
                          stateForAddon?.status === 'loading'
                        }
                        className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-neon-purple/40 bg-neon-purple/10 px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-neon-purple transition hover:bg-neon-purple/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        <TicketPercent className="h-4 w-4" aria-hidden="true" />
                        {t('addons.quote')}
                      </button>
                      <button
                        type="button"
                        onClick={() => handlePurchaseAddon(addon)}
                        disabled={
                          !activeSubscription ||
                          !canUseSelectedWriteContract ||
                          stateForAddon?.status === 'loading' ||
                          stateForAddon?.status !== 'quoted'
                        }
                        className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-matrix-green/40 bg-matrix-green/10 px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-matrix-green transition hover:bg-matrix-green/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        <PackagePlus className="h-4 w-4" aria-hidden="true" />
                        {t('addons.purchaseCta')}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="mt-6 rounded-2xl border border-amber-400/30 bg-amber-400/10 p-5 font-mono text-sm text-amber-100">
              {t('addons.empty')}
            </p>
          )}
        </article>

        <article className="rounded-[2rem] border border-grid-line/30 bg-terminal-surface/55 p-6 backdrop-blur">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-cyan">
                {t('history.eyebrow')}
              </p>
              <h2 className="mt-3 text-2xl font-display text-white">{t('history.title')}</h2>
            </div>
            <History className="h-6 w-6 text-neon-cyan" aria-hidden="true" />
          </div>

          {ordersQuery.isPending ? (
            <LoadingBlock className="mt-6 min-h-56" />
          ) : sortedOrders.length > 0 ? (
            <div className="mt-6 space-y-3">
              {sortedOrders.map((order) => {
                const tone = getOrderTone(order);
                return (
                  <div key={order.id} className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="font-mono text-sm text-white">
                          {getOrderDisplayName(order, publicPlans)}
                        </p>
                        <p className="mt-1 font-mono text-xs text-muted-foreground">
                          {formatDate(order.created_at, locale) ?? t('labels.notAvailable')}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-sm text-white/80">
                          {formatMoney(locale, order.displayed_price, order.currency_code)}
                        </span>
                        <StatusPill label={formatLabel(getOrderStatus(order), getOrderStatus(order))} tone={tone} />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="mt-6 rounded-2xl border border-grid-line/30 bg-black/20 p-5 font-mono text-sm text-muted-foreground">
              {t('history.empty')}
            </p>
          )}
        </article>
      </section>

      <section className="flex flex-col gap-3 rounded-2xl border border-grid-line/30 bg-terminal-surface/45 p-4 font-mono text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-3">
          <StatusPill label={hasAnyError ? t('sync.degraded') : t('sync.live')} tone={hasAnyError ? 'amber' : 'green'} />
          <span>{t('sync.description')}</span>
        </div>
        <button
          type="button"
          onClick={() => {
            void Promise.all([
              entitlementQuery.refetch(),
              serviceStateQuery.refetch(),
              trialQuery.refetch(),
              plansQuery.refetch(),
              addonsQuery.refetch(),
              ordersQuery.refetch(),
            ]);
          }}
          className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-grid-line/40 px-3 py-2 uppercase tracking-[0.16em] text-foreground transition hover:border-neon-cyan/40 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
        >
          <RefreshCw
            className={`h-4 w-4 ${
              entitlementQuery.isFetching ||
              serviceStateQuery.isFetching ||
              trialQuery.isFetching ||
              plansQuery.isFetching ||
              addonsQuery.isFetching ||
              ordersQuery.isFetching
                ? 'animate-spin'
                : ''
            }`}
            aria-hidden="true"
          />
          {t('sync.retry')}
        </button>
      </section>

      <CancelSubscriptionModal
        isOpen={showCancelModal}
        onClose={() => setShowCancelModal(false)}
        onSuccess={() => {
          void refetchCore();
        }}
        subscriptionName={entitlement?.display_name ?? t('current.subscriptionFallback')}
        expiresAt={entitlement?.expires_at ?? undefined}
      />

      <PurchaseConfirmModal
        isOpen={Boolean(purchasePlan)}
        onClose={() => setPurchasePlan(null)}
        plan={purchasePlan}
      />
    </div>
  );
}

function Metric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 break-words font-display text-lg text-white">{value}</p>
    </div>
  );
}

function ActionRow({ done, label }: { done: boolean; label: string }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-grid-line/30 bg-black/20 p-4">
      {done ? (
        <CheckCircle2 className="h-5 w-5 text-matrix-green" aria-hidden="true" />
      ) : (
        <AlertTriangle className="h-5 w-5 text-amber-300" aria-hidden="true" />
      )}
      <span className="font-mono text-sm text-foreground">{label}</span>
    </div>
  );
}

function LinkButton({
  href,
  icon,
  label,
}: {
  href: '/payment-history' | '/servers' | '/wallet';
  icon: 'history' | 'key' | 'wallet';
  label: string;
}) {
  const Icon = icon === 'key' ? KeyRound : icon === 'wallet' ? Wallet : History;

  return (
    <Link
      href={href}
      className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-grid-line/40 bg-white/[0.03] px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-foreground transition hover:border-neon-cyan/40 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
    >
      <Icon className="h-4 w-4" aria-hidden="true" />
      {label}
    </Link>
  );
}

function PlanActionButton({
  action,
  disabled = false,
  loading,
  onCommit,
  onPurchase,
  onQuote,
  quoteReady,
  t,
}: {
  action: PlanAction;
  disabled?: boolean;
  loading: boolean;
  onCommit: () => void;
  onPurchase: () => void;
  onQuote: () => void;
  quoteReady: boolean;
  t: ReturnType<typeof useTranslations>;
}) {
  if (action === 'current') {
    return (
      <button
        type="button"
        disabled
        className="mt-5 inline-flex min-h-11 w-full items-center justify-center rounded-xl border border-matrix-green/30 bg-matrix-green/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-matrix-green disabled:cursor-not-allowed"
      >
        {t('planActions.current')}
      </button>
    );
  }

  if (action === 'purchase') {
    return (
      <button
        type="button"
        onClick={onPurchase}
        disabled={disabled}
        className="mt-5 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-neon-purple/40 bg-neon-purple/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-neon-purple transition hover:bg-neon-purple/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg disabled:cursor-not-allowed disabled:opacity-50"
      >
        <CreditCard className="h-4 w-4" aria-hidden="true" />
        {t('planActions.purchase')}
      </button>
    );
  }

  return (
    <div className="mt-5 grid gap-3 sm:grid-cols-2">
      <button
        type="button"
        onClick={onQuote}
        disabled={disabled || loading}
        className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-neon-cyan/40 bg-neon-cyan/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-neon-cyan transition hover:bg-neon-cyan/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg disabled:cursor-not-allowed disabled:opacity-50"
      >
        <TicketPercent className="h-4 w-4" aria-hidden="true" />
        {loading ? t('planActions.loading') : t('planActions.quote')}
      </button>
      <button
        type="button"
        onClick={onCommit}
        disabled={disabled || loading || !quoteReady}
        className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-matrix-green/40 bg-matrix-green/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-matrix-green transition hover:bg-matrix-green/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg disabled:cursor-not-allowed disabled:opacity-50"
      >
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
        {t('planActions.commitCta')}
      </button>
    </div>
  );
}
