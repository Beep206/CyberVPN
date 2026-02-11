'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useSubscriptions } from '../hooks/useSubscriptions';
import { useSubscriptionPlans } from '../hooks/useSubscriptionPlans';
import { CancelSubscriptionModal } from './CancelSubscriptionModal';
import { PurchaseConfirmModal } from './PurchaseConfirmModal';
import { PlanCard } from './PlanCard';
import { TrialSection } from './TrialSection';
import { CodesSection } from './CodesSection';

/**
 * Subscriptions client component
 * Displays user's current subscriptions and available plans
 */
export function SubscriptionsClient() {
  const t = useTranslations('Subscriptions');
  const { data: subscriptions, isLoading, error, refetch } = useSubscriptions();
  const { data: plans, isLoading: plansLoading, error: plansError } = useSubscriptionPlans();

  const [showCancelModal, setShowCancelModal] = useState(false);
  const [showPurchaseModal, setShowPurchaseModal] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<any>(null);

  // Handle plan purchase - show confirmation modal
  const handlePurchase = (planUuid: string) => {
    const plan = plans?.find((p: any) => p.uuid === planUuid);
    if (plan) {
      setSelectedPlan(plan);
      setShowPurchaseModal(true);
    }
  };

  if (error) {
    return (
      <div className="cyber-card p-8 text-center">
        <p className="text-red-500 font-mono">
          {t('errorLoading') || 'Error loading subscriptions'}
        </p>
        <p className="text-sm text-muted-foreground mt-2">
          {error instanceof Error ? error.message : 'Unknown error'}
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="cyber-card p-8 animate-pulse">
          <div className="h-6 bg-grid-line/30 rounded w-1/3 mb-4" />
          <div className="h-4 bg-grid-line/20 rounded w-2/3" />
        </div>
      </div>
    );
  }

  // Type assertion - API currently returns templates, not user subscriptions
  const activeSubscription = subscriptions?.find((sub: any) => sub.status === 'active');

  return (
    <div className="space-y-8">
      {/* Trial Section */}
      <TrialSection />

      {/* Current Subscription Section */}
      <section>
        <h2 className="text-xl font-display text-neon-purple mb-4 pl-2 border-l-4 border-neon-purple">
          {t('currentSubscription') || 'Current Subscription'}
        </h2>

        {activeSubscription ? (
          <div className="cyber-card p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-2xl font-display text-neon-cyan">
                  {(activeSubscription as any).plan_name || activeSubscription.name || 'Active Plan'}
                </h3>
                <p className="text-muted-foreground font-mono text-sm mt-1">
                  {t('status')}: <span className="text-matrix-green">{(activeSubscription as any).status}</span>
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm text-muted-foreground">{t('expiresAt') || 'Expires'}</p>
                <p className="font-mono text-neon-pink">
                  {(activeSubscription as any).expires_at ? new Date((activeSubscription as any).expires_at).toLocaleDateString() : 'N/A'}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-grid-line/30">
              <div>
                <p className="text-xs text-muted-foreground uppercase">{t('startedAt') || 'Started'}</p>
                <p className="font-mono text-sm mt-1">
                  {(activeSubscription as any).created_at ? new Date((activeSubscription as any).created_at).toLocaleDateString() : 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground uppercase">{t('autoRenew') || 'Auto-Renew'}</p>
                <p className="font-mono text-sm mt-1">
                  {(activeSubscription as any).is_active ? t('enabled') || 'Enabled' : t('disabled') || 'Disabled'}
                </p>
              </div>
            </div>

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

      {/* Available Plans Section */}
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {plans
              .filter((plan: any) => plan.isActive)
              .map((plan: any) => (
                <PlanCard
                  key={plan.uuid}
                  plan={plan}
                  isCurrentPlan={
                    activeSubscription &&
                    (activeSubscription as any).plan_uuid === plan.uuid
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

      {/* Invite & Promo Codes Section */}
      <section>
        <h2 className="text-xl font-display text-neon-purple mb-4 pl-2 border-l-4 border-neon-purple">
          {t('codesAndRewards') || 'Codes & Rewards'}
        </h2>
        <CodesSection />
      </section>

      {/* Past Subscriptions */}
      {subscriptions && subscriptions.length > 1 && (
        <section>
          <h2 className="text-xl font-display text-neon-purple mb-4 pl-2 border-l-4 border-neon-purple">
            {t('subscriptionHistory') || 'Subscription History'}
          </h2>

          <div className="space-y-3">
            {subscriptions
              .filter((sub: any) => sub.status !== 'active')
              .map((sub: any) => (
                <div key={sub.uuid} className="cyber-card p-4 flex justify-between items-center">
                  <div>
                    <p className="font-mono text-sm">{sub.plan_name || 'Plan'}</p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(sub.created_at).toLocaleDateString()} - {new Date(sub.expires_at).toLocaleDateString()}
                    </p>
                  </div>
                  <span className={`font-mono text-xs px-3 py-1 rounded ${
                    sub.status === 'expired' ? 'bg-red-500/20 text-red-400' : 'bg-muted/20 text-muted-foreground'
                  }`}>
                    {sub.status}
                  </span>
                </div>
              ))}
          </div>
        </section>
      )}

      {/* Cancel Subscription Modal */}
      {activeSubscription && (
        <CancelSubscriptionModal
          isOpen={showCancelModal}
          onClose={() => setShowCancelModal(false)}
          onSuccess={() => {
            refetch();
          }}
          subscriptionName={(activeSubscription as any).plan_name || activeSubscription.name || 'subscription'}
          expiresAt={(activeSubscription as any).expires_at}
        />
      )}

      {/* Purchase Confirmation Modal */}
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
