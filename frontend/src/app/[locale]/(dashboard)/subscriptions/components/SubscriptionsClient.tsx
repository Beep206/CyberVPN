'use client';

import { useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import type { OrderResponse } from '@/lib/api/commerce';
import type { CurrentEntitlementStateResponse } from '@/lib/api/service-access';
import { useCurrentEntitlements } from '../hooks/useCurrentEntitlements';
import { useCurrentServiceState } from '../hooks/useCurrentServiceState';
import { useOrders } from '../hooks/useOrders';
import { useSubscriptionPlans } from '../hooks/useSubscriptionPlans';
import { CancelSubscriptionModal } from './CancelSubscriptionModal';
import { PurchaseConfirmModal } from './PurchaseConfirmModal';
import { PlanCard } from './PlanCard';
import { TrialSection } from './TrialSection';
import { CodesSection } from './CodesSection';
import {
  formatConnectionModes,
  formatDurationLabel,
  formatMoney,
  formatSupportLabel,
  type SubscriptionPlan,
} from '../lib/plan-presenter';

type EffectiveEntitlementsView = {
  deviceLimit?: number;
  displayTrafficLabel?: string;
  connectionModes: string[];
  supportSla?: string;
};

function toStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : [];
}

function getEffectiveEntitlements(
  entitlement?: CurrentEntitlementStateResponse,
): EffectiveEntitlementsView {
  const source = entitlement?.effective_entitlements as Record<string, unknown> | undefined;

  return {
    deviceLimit: typeof source?.device_limit === 'number' ? source.device_limit : undefined,
    displayTrafficLabel:
      typeof source?.display_traffic_label === 'string'
        ? source.display_traffic_label
        : undefined,
    connectionModes: toStringArray(source?.connection_modes),
    supportSla: typeof source?.support_sla === 'string' ? source.support_sla : undefined,
  };
}

function formatDate(value?: string | null) {
  return value ? new Date(value).toLocaleDateString() : 'N/A';
}

function getOrderDisplayName(
  order: OrderResponse,
  plans: SubscriptionPlan[] | undefined,
): string {
  const firstItem = order.items[0];
  if (firstItem?.display_name) {
    return firstItem.display_name;
  }

  const matchingPlan = plans?.find((plan) => plan.uuid === order.subscription_plan_id);
  if (matchingPlan?.display_name) {
    return matchingPlan.display_name;
  }

  return `Order ${order.id.slice(0, 8)}`;
}

function getOrderStatusLabel(order: OrderResponse): string {
  if (order.settlement_status === 'paid') {
    return 'paid';
  }

  if (order.settlement_status === 'pending_payment') {
    return 'awaiting payment';
  }

  if (order.settlement_status === 'refunded') {
    return 'refunded';
  }

  return order.settlement_status || order.order_status;
}

function getOrderPeriodDays(order: OrderResponse, fallback?: number | null): number {
  const snapshot = order.entitlements_snapshot as Record<string, unknown>;
  return typeof snapshot.period_days === 'number' ? snapshot.period_days : (fallback ?? 30);
}

function hasCurrentSubscription(entitlement?: CurrentEntitlementStateResponse): boolean {
  if (!entitlement) {
    return false;
  }

  if (entitlement.status === 'inactive' || entitlement.status === 'none') {
    return false;
  }

  return Boolean(entitlement.plan_uuid || entitlement.display_name);
}

export function SubscriptionsClient() {
  const t = useTranslations('Subscriptions');
  const locale = useLocale();
  const {
    data: currentEntitlement,
    isLoading: entitlementLoading,
    error: entitlementError,
    refetch: refetchEntitlements,
  } = useCurrentEntitlements();
  const {
    data: orders,
    isLoading: ordersLoading,
    error: ordersError,
    refetch: refetchOrders,
  } = useOrders();
  const {
    data: currentServiceState,
    error: serviceStateError,
    refetch: refetchServiceState,
  } = useCurrentServiceState();
  const { data: plans, isLoading: plansLoading, error: plansError } = useSubscriptionPlans();

  const [showCancelModal, setShowCancelModal] = useState(false);
  const [showPurchaseModal, setShowPurchaseModal] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<SubscriptionPlan | null>(null);

  const effectiveEntitlements = getEffectiveEntitlements(currentEntitlement);
  const currentPlanActive = hasCurrentSubscription(currentEntitlement);

  const sortedOrders = useMemo(
    () =>
      [...(orders ?? [])].sort(
        (left, right) =>
          new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
      ),
    [orders],
  );

  const activeOrder = currentEntitlement?.plan_uuid
    ? (
      sortedOrders.find((order) => order.subscription_plan_id === currentEntitlement.plan_uuid) ??
      sortedOrders[0]
    )
    : sortedOrders[0];

  const handlePurchase = (planUuid: string) => {
    const plan = plans?.find((entry: SubscriptionPlan) => entry.uuid === planUuid);
    if (plan) {
      setSelectedPlan(plan);
      setShowPurchaseModal(true);
    }
  };

  if (entitlementError) {
    return (
      <div className="cyber-card p-8 text-center">
        <p className="text-red-500 font-mono">
          {t('errorLoading') || 'Error loading subscriptions'}
        </p>
        <p className="text-sm text-muted-foreground mt-2">
          {entitlementError instanceof Error ? entitlementError.message : 'Unknown error'}
        </p>
      </div>
    );
  }

  if (entitlementLoading && !currentEntitlement) {
    return (
      <div className="space-y-6">
        <div className="cyber-card p-8 animate-pulse">
          <div className="h-6 bg-grid-line/30 rounded w-1/3 mb-4" />
          <div className="h-4 bg-grid-line/20 rounded w-2/3" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <TrialSection />

      <section>
        <h2 className="text-xl font-display text-neon-purple mb-4 pl-2 border-l-4 border-neon-purple">
          {t('currentSubscription') || 'Current Subscription'}
        </h2>

        {currentPlanActive ? (
          <div className="cyber-card p-6">
            <div className="flex justify-between items-start mb-4 gap-6">
              <div>
                <h3 className="text-2xl font-display text-neon-cyan">
                  {currentEntitlement?.display_name || 'Active Plan'}
                </h3>
                <p className="text-muted-foreground font-mono text-sm mt-1">
                  {t('status') || 'Status'}:{' '}
                  <span className="text-matrix-green">{currentEntitlement?.status || 'active'}</span>
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm text-muted-foreground">{t('expiresAt') || 'Expires'}</p>
                <p className="font-mono text-neon-pink">
                  {formatDate(currentEntitlement?.expires_at)}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-grid-line/30">
              <div>
                <p className="text-xs text-muted-foreground uppercase">{t('startedAt') || 'Started'}</p>
                <p className="font-mono text-sm mt-1">{formatDate(activeOrder?.created_at)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground uppercase">Devices</p>
                <p className="font-mono text-sm mt-1">
                  {effectiveEntitlements.deviceLimit ?? 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground uppercase">Support</p>
                <p className="font-mono text-sm mt-1">
                  {effectiveEntitlements.supportSla
                    ? formatSupportLabel(effectiveEntitlements.supportSla)
                    : 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground uppercase">Access</p>
                <p className="font-mono text-sm mt-1">
                  {currentServiceState?.access_delivery_channel?.channel_type ||
                    currentServiceState?.provisioning_profile?.target_channel ||
                    'Pending provisioning'}
                </p>
              </div>
            </div>

            <div className="mt-6 grid gap-3 md:grid-cols-2">
              <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                <p className="text-xs text-muted-foreground uppercase">Traffic Policy</p>
                <p className="mt-2 font-mono text-sm text-white/80">
                  {effectiveEntitlements.displayTrafficLabel || 'Unlimited'}
                </p>
              </div>
              <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                <p className="text-xs text-muted-foreground uppercase">Connection Modes</p>
                <p className="mt-2 font-mono text-sm text-white/80">
                  {formatConnectionModes(effectiveEntitlements.connectionModes)}
                </p>
              </div>
            </div>

            {(currentServiceState?.service_identity || currentServiceState?.provisioning_profile) && (
              <div className="mt-6 rounded-xl border border-neon-cyan/20 bg-neon-cyan/5 p-4">
                <p className="text-xs text-neon-cyan uppercase tracking-[0.18em] font-mono">
                  Purchase vs Consumption
                </p>
                <div className="mt-3 grid gap-3 md:grid-cols-3 text-sm">
                  <div>
                    <p className="text-white/45 uppercase text-[10px] font-mono">Provider</p>
                    <p className="mt-1 font-mono text-white/80">
                      {currentServiceState?.service_identity?.provider_name ||
                        currentServiceState?.access_delivery_channel?.provider_name ||
                        'N/A'}
                    </p>
                  </div>
                  <div>
                    <p className="text-white/45 uppercase text-[10px] font-mono">Profile</p>
                    <p className="mt-1 font-mono text-white/80">
                      {currentServiceState?.provisioning_profile?.profile_key || 'N/A'}
                    </p>
                  </div>
                  <div>
                    <p className="text-white/45 uppercase text-[10px] font-mono">Channel Status</p>
                    <p className="mt-1 font-mono text-white/80">
                      {currentServiceState?.access_delivery_channel?.channel_status || 'N/A'}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {serviceStateError && (
              <p className="mt-4 text-xs text-amber-400 font-mono">
                Service-state read unavailable: {serviceStateError instanceof Error ? serviceStateError.message : 'Unknown error'}
              </p>
            )}

            <button
              className="mt-6 px-6 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 text-red-400 font-mono text-sm rounded transition-colors"
              onClick={() => setShowCancelModal(true)}
            >
              {t('cancelSubscription') || 'Cancel Subscription'}
            </button>
          </div>
        ) : (
          <div className="cyber-card p-8 text-center">
            <p className="text-muted-foreground font-mono">
              {t('noActiveSubscription') || 'No active subscription'}
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              {t('choosePlanBelow') || 'Choose a plan below to get started'}
            </p>
          </div>
        )}
      </section>

      <section>
        <h2 className="text-xl font-display text-neon-purple mb-4 pl-2 border-l-4 border-neon-purple">
          {t('availablePlans') || 'Available Plans'}
        </h2>

        {plansError ? (
          <div className="cyber-card p-8 text-center">
            <p className="text-red-500 font-mono">
              {t('errorLoadingPlans') || 'Error loading plans'}
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              {plansError instanceof Error ? plansError.message : 'Unknown error'}
            </p>
          </div>
        ) : plansLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="cyber-card p-6 animate-pulse">
                <div className="h-8 bg-grid-line/30 rounded w-1/2 mx-auto mb-4" />
                <div className="h-12 bg-grid-line/30 rounded w-3/4 mx-auto mb-6" />
                <div className="space-y-2">
                  <div className="h-4 bg-grid-line/20 rounded" />
                  <div className="h-4 bg-grid-line/20 rounded" />
                  <div className="h-4 bg-grid-line/20 rounded w-3/4" />
                </div>
              </div>
            ))}
          </div>
        ) : plans && plans.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
            {plans
              .filter((plan: SubscriptionPlan) => plan.is_active && plan.catalog_visibility === 'public')
              .map((plan: SubscriptionPlan) => (
                <PlanCard
                  key={plan.uuid}
                  plan={plan}
                  isCurrentPlan={
                    currentPlanActive &&
                    (currentEntitlement?.plan_uuid === plan.uuid || currentEntitlement?.plan_code === plan.plan_code)
                  }
                  onPurchase={handlePurchase}
                />
              ))}
          </div>
        ) : (
          <div className="cyber-card p-8 text-center">
            <p className="text-muted-foreground font-mono">
              {t('noPlansAvailable') || 'No plans available at the moment'}
            </p>
          </div>
        )}
      </section>

      <section>
        <h2 className="text-xl font-display text-neon-purple mb-4 pl-2 border-l-4 border-neon-purple">
          {t('codesAndRewards') || 'Codes & Rewards'}
        </h2>
        <CodesSection />
      </section>

      <section>
        <h2 className="text-xl font-display text-neon-purple mb-4 pl-2 border-l-4 border-neon-purple">
          {t('subscriptionHistory') || 'Subscription History'}
        </h2>

        {ordersError ? (
          <div className="cyber-card p-6 text-center">
            <p className="text-amber-400 font-mono text-sm">
              Order history unavailable
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              {ordersError instanceof Error ? ordersError.message : 'Unknown error'}
            </p>
          </div>
        ) : ordersLoading ? (
          <div className="cyber-card p-6 animate-pulse">
            <div className="h-4 bg-grid-line/20 rounded w-1/2 mb-3" />
            <div className="h-4 bg-grid-line/20 rounded w-2/3" />
          </div>
        ) : sortedOrders.length > 0 ? (
          <div className="space-y-3">
            {sortedOrders.map((order) => {
              const orderStatusLabel = getOrderStatusLabel(order);

              return (
                <div key={order.id} className="cyber-card p-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="font-mono text-sm">
                      {getOrderDisplayName(order, plans)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatDate(order.created_at)} · {formatDurationLabel(getOrderPeriodDays(order, currentEntitlement?.period_days))}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-sm text-white/80">
                      {formatMoney(locale, order.displayed_price, order.currency_code)}
                    </span>
                    <span
                      className={`font-mono text-xs px-3 py-1 rounded ${
                        orderStatusLabel === 'paid'
                          ? 'bg-matrix-green/20 text-matrix-green'
                          : orderStatusLabel === 'awaiting payment'
                            ? 'bg-neon-cyan/20 text-neon-cyan'
                            : 'bg-muted/20 text-muted-foreground'
                      }`}
                    >
                      {orderStatusLabel}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="cyber-card p-8 text-center">
            <p className="text-muted-foreground font-mono">
              No canonical order history yet
            </p>
          </div>
        )}
      </section>

      {currentPlanActive && (
        <CancelSubscriptionModal
          isOpen={showCancelModal}
          onClose={() => setShowCancelModal(false)}
          onSuccess={() => {
            void Promise.all([
              refetchEntitlements(),
              refetchOrders(),
              refetchServiceState(),
            ]);
          }}
          subscriptionName={currentEntitlement?.display_name || 'subscription'}
          expiresAt={currentEntitlement?.expires_at || undefined}
        />
      )}

      <PurchaseConfirmModal
        isOpen={showPurchaseModal}
        onClose={() => {
          setShowPurchaseModal(false);
          setSelectedPlan(null);
        }}
        plan={selectedPlan}
      />
    </div>
  );
}
