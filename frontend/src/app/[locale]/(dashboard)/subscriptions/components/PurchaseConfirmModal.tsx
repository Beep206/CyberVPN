'use client';

import { useEffect, useState } from 'react';
import { Modal } from '@/shared/ui/modal';
import { paymentsApi } from '@/lib/api/payments';
import { motion } from 'motion/react';
import { useLocale } from 'next-intl';
import { AlertTriangle, CheckCircle, CreditCard, Percent, ShieldCheck, Tag, Zap } from 'lucide-react';
import { AxiosError } from 'axios';
import { CyberInput } from '@/features/auth/components/CyberInput';
import { markPerformance, measurePerformance, PerformanceMarks } from '@/shared/lib/web-vitals';
import {
  formatConnectionModes,
  formatDurationLabel,
  formatMoney,
  formatSupportLabel,
  formatTrafficLabel,
  getPlanPrice,
  type SubscriptionPlan,
  type SubscriptionQuote,
} from '../lib/plan-presenter';

interface PurchaseConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  plan: SubscriptionPlan | null;
}

type ModalStep = 'confirm' | 'processing' | 'success' | 'error';

function buildCheckoutRequest(plan: SubscriptionPlan, promo?: string) {
  return {
    plan_id: plan.uuid,
    addons: [],
    promo_code: promo || undefined,
    use_wallet: 0,
    currency: 'USD',
    channel: 'web',
  };
}

export function PurchaseConfirmModal({
  isOpen,
  onClose,
  plan,
}: PurchaseConfirmModalProps) {
  const locale = useLocale();
  const [step, setStep] = useState<ModalStep>('confirm');
  const [error, setError] = useState('');
  const [promoCode, setPromoCode] = useState('');
  const [promoError, setPromoError] = useState('');
  const [quote, setQuote] = useState<SubscriptionQuote | null>(null);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [activePromoCode, setActivePromoCode] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState('Payment page opened');

  const handleClose = () => {
    setStep('confirm');
    setError('');
    setPromoCode('');
    setPromoError('');
    setQuote(null);
    setQuoteLoading(false);
    setActivePromoCode(null);
    setSuccessMessage('Payment page opened');
    onClose();
  };

  const planPrice = plan ? getPlanPrice(plan, locale) : null;

  const handleQuoteError = (err: unknown, fallback: string) => {
    if (err instanceof AxiosError) {
      const detail = err.response?.data?.detail;
      return detail || fallback;
    }

    return fallback;
  };

  useEffect(() => {
    const activePlan = plan;

    if (!isOpen || !activePlan) {
      return;
    }

    const initialPlan: SubscriptionPlan = activePlan;

    let isCancelled = false;

    async function loadInitialQuote() {
      setQuoteLoading(true);
      setError('');
      setPromoError('');
      setQuote(null);
      setActivePromoCode(null);

      try {
        const response = await paymentsApi.quoteCheckout(buildCheckoutRequest(initialPlan));
        if (!isCancelled) {
          setQuote(response.data);
        }
      } catch (err) {
        if (!isCancelled) {
          setError(handleQuoteError(err, 'Failed to load checkout quote'));
        }
      } finally {
        if (!isCancelled) {
          setQuoteLoading(false);
        }
      }
    }

    void loadInitialQuote();

    return () => {
      isCancelled = true;
    };
  }, [isOpen, plan]);

  const handleValidatePromo = async () => {
    const activePlan = plan;
    if (!promoCode.trim()) {
      setPromoError('Please enter a promo code');
      return;
    }
    if (!activePlan) {
      return;
    }

    setQuoteLoading(true);
    setPromoError('');
    setError('');

    try {
      const normalizedPromo = promoCode.trim().toUpperCase();
      const response = await paymentsApi.quoteCheckout(buildCheckoutRequest(activePlan, normalizedPromo));
      setQuote(response.data);
      setActivePromoCode(normalizedPromo);
      setPromoCode(normalizedPromo);
    } catch (err) {
      setActivePromoCode(null);
      setPromoError(handleQuoteError(err, 'Promo code not valid'));

      try {
        const fallbackQuote = await paymentsApi.quoteCheckout(buildCheckoutRequest(activePlan));
        setQuote(fallbackQuote.data);
      } catch {
        setQuote(null);
      }
    } finally {
      setQuoteLoading(false);
    }
  };

  const handlePurchase = async () => {
    const activePlan = plan;
    if (!activePlan) return;

    markPerformance(PerformanceMarks.PURCHASE_FLOW_START, {
      planId: activePlan.uuid,
      planName: activePlan.display_name,
      hasPromoCode: !!activePromoCode,
    });

    setStep('processing');
    setError('');

    try {
      const response = await paymentsApi.commitCheckout(
        buildCheckoutRequest(activePlan, activePromoCode ?? undefined)
      );

      if (response.data.invoice?.payment_url) {
        window.open(response.data.invoice.payment_url, '_blank', 'noopener,noreferrer');
        setSuccessMessage('Payment page opened');
      } else {
        setSuccessMessage('Subscription activated');
      }

      setStep('success');
      markPerformance(PerformanceMarks.PURCHASE_FLOW_COMPLETE, {
        planId: activePlan.uuid,
        planName: activePlan.display_name,
      });
      measurePerformance(
        'purchase-flow-duration',
        PerformanceMarks.PURCHASE_FLOW_START,
        PerformanceMarks.PURCHASE_FLOW_COMPLETE
      );

      setTimeout(() => {
        handleClose();
      }, 2200);
    } catch (err) {
      setStep('error');
      if (err instanceof AxiosError) {
        const detail = err.response?.data?.detail;
        setError(detail || 'Failed to commit checkout');
      } else {
        setError('An error occurred. Please try again.');
      }
    }
  };

  if (!plan) return null;
  const quoteSnapshot = quote?.entitlements_snapshot.effective_entitlements;
  const quotedTotal = quote?.displayed_price ?? plan.price_usd;
  const quotedBase = quote?.base_price ?? plan.price_usd;
  const hasDiscount = (quote?.discount_amount ?? 0) > 0;
  const quotedGateway = quote?.gateway_amount ?? plan.price_usd;

  if (step === 'confirm') {
    return (
      <Modal isOpen={isOpen} onClose={handleClose} title="CONFIRM_PURCHASE">
        <div className="space-y-6">
          <div className="cyber-card p-6 bg-terminal-surface/50">
            <div className="flex items-start gap-4 mb-4">
              <div className="p-3 bg-neon-cyan/10 border border-neon-cyan/30 rounded-lg">
                <CreditCard className="h-6 w-6 text-neon-cyan" />
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-display text-neon-cyan mb-1">
                  {plan.display_name}
                </h3>
                <p className="text-sm text-muted-foreground font-mono">
                  {formatDurationLabel(plan.duration_days)} • {formatTrafficLabel(plan)}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 mb-4 pb-4 border-b border-grid-line/30">
              <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                <p className="text-[10px] uppercase tracking-[0.18em] text-white/40 font-mono">
                  Devices
                </p>
                <p className="mt-2 text-lg font-display text-white">
                  {quoteSnapshot?.device_limit ?? plan.devices_included}
                </p>
              </div>
              <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                <p className="text-[10px] uppercase tracking-[0.18em] text-white/40 font-mono">
                  Support
                </p>
                <p className="mt-2 text-sm font-mono text-white/75">
                  {formatSupportLabel(quoteSnapshot?.support_sla ?? plan.support_sla)}
                </p>
              </div>
            </div>

            <div className="space-y-2 text-sm text-muted-foreground">
              <div className="flex items-start justify-between gap-4">
                <span>Connection modes</span>
                <span className="max-w-[16rem] text-right font-mono text-white/75">
                  {formatConnectionModes(quoteSnapshot?.connection_modes ?? plan.connection_modes)}
                </span>
              </div>
              <div className="flex items-start justify-between gap-4">
                <span>Traffic policy</span>
                <span className="font-mono text-white/75">
                  {quoteSnapshot?.display_traffic_label ?? formatTrafficLabel(plan)}
                </span>
              </div>
              <div className="flex items-start justify-between gap-4">
                <span>Checkout total</span>
                <div className="text-right">
                  {hasDiscount && (
                    <p className="font-mono text-xs text-white/35 line-through">
                      {formatMoney(locale, quotedBase, 'USD')}
                    </p>
                  )}
                  <p className="text-2xl font-display text-matrix-green">
                    {formatMoney(locale, quotedTotal, 'USD')}
                  </p>
                </div>
              </div>
            </div>

            {planPrice && quote == null && !quoteLoading && (
              <p className="mt-3 text-xs font-mono text-white/45">
                Catalog price: {planPrice.formatted}
              </p>
            )}
          </div>

          <div className="cyber-card p-4 bg-terminal-bg">
            <div className="flex items-center gap-3 mb-3">
              <Tag className="h-5 w-5 text-neon-purple" />
              <h4 className="text-sm font-display text-neon-purple">
                Have a Promo Code?
              </h4>
            </div>

            <div className="space-y-3">
              <CyberInput
                label="Promo Code"
                type="text"
                value={promoCode}
                onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
                placeholder="SAVE20"
                prefix="promo"
                error={promoError}
                disabled={quoteLoading}
                onKeyDown={(e) => e.key === 'Enter' && handleValidatePromo()}
              />

              {activePromoCode && quote && (quote.discount_amount > 0 || quote.partner_markup !== 0) && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="flex items-start gap-2 p-3 bg-matrix-green/10 border border-matrix-green/30 rounded"
                >
                  <Percent className="h-4 w-4 text-matrix-green flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <ShieldCheck className="h-3 w-3 text-matrix-green" />
                      <span className="text-xs font-semibold text-matrix-green uppercase tracking-[0.18em]">
                        Quote Updated
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {quote.discount_amount > 0
                        ? `${activePromoCode} applied: ${formatMoney(locale, quote.discount_amount, 'USD')} off`
                        : `${activePromoCode} applied`}
                    </p>
                  </div>
                </motion.div>
              )}

              <button
                onClick={handleValidatePromo}
                disabled={quoteLoading || !promoCode.trim()}
                className="w-full px-3 py-2 bg-neon-purple/20 hover:bg-neon-purple/30 border border-neon-purple/50 text-neon-purple font-mono text-sm rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {quoteLoading ? 'Updating quote...' : 'Apply Promo'}
              </button>
            </div>
          </div>

          <div className="p-4 bg-neon-cyan/5 border border-neon-cyan/30 rounded-lg">
            <div className="flex items-start gap-3">
              <Zap className="h-5 w-5 text-neon-cyan flex-shrink-0 mt-0.5" />
              <div className="flex-1 space-y-1">
                <p className="text-sm font-semibold text-neon-cyan">
                  Secure checkout
                </p>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  The dashboard now checks the live canonical quote before payment and carries promo pricing directly into checkout.
                </p>
                <p className="text-xs font-mono text-white/55">
                  Gateway amount: {formatMoney(locale, quotedGateway, 'USD')}
                </p>
              </div>
            </div>
          </div>

          {error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={handleClose}
              className="flex-1 px-4 py-3 bg-terminal-bg hover:bg-terminal-surface border border-grid-line/50 text-muted-foreground font-mono text-sm rounded transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handlePurchase}
              disabled={quoteLoading || Boolean(error)}
              className="flex-1 px-4 py-3 bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan font-mono text-sm rounded transition-colors hover:shadow-[0_0_15px_rgba(0,255,255,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {quote?.is_zero_gateway ? 'Activate Now' : 'Pay with Crypto'}
            </button>
          </div>
        </div>
      </Modal>
    );
  }

  if (step === 'processing') {
    return (
      <Modal isOpen={isOpen} onClose={() => {}} title="PROCESSING_PAYMENT">
        <div className="text-center py-8 space-y-4">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          >
            <div className="h-12 w-12 border-4 border-neon-cyan border-t-transparent rounded-full mx-auto" />
          </motion.div>
          <p className="text-sm text-muted-foreground font-mono">
            Creating payment invoice...
          </p>
        </div>
      </Modal>
    );
  }

  if (step === 'success') {
    return (
      <Modal isOpen={isOpen} onClose={handleClose} title="PAYMENT_READY">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="text-center space-y-6 py-8"
        >
          <CheckCircle className="h-16 w-16 text-matrix-green mx-auto" />
          <div className="space-y-2">
            <h3 className="text-lg font-display text-matrix-green">
              {successMessage}
            </h3>
            <p className="text-sm text-muted-foreground">
              {successMessage === 'Subscription activated'
                ? 'Your subscription is now active and the entitlement snapshot has been committed.'
                : 'Complete your payment in the new tab to activate your subscription.'}
            </p>
          </div>
        </motion.div>
      </Modal>
    );
  }

  if (step === 'error') {
    return (
      <Modal isOpen={isOpen} onClose={handleClose} title="PAYMENT_ERROR">
        <div className="text-center space-y-6 py-8">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', bounce: 0.5 }}
          >
            <AlertTriangle className="h-16 w-16 text-red-500 mx-auto" />
          </motion.div>
          <div className="space-y-2">
            <h3 className="text-lg font-display text-red-500">
              Payment Failed
            </h3>
            <p className="text-sm text-muted-foreground">
              {error || 'Failed to create payment invoice'}
            </p>
          </div>
          <button
            onClick={() => setStep('confirm')}
            className="px-6 py-3 bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan font-mono text-sm rounded transition-colors"
          >
            Try Again
          </button>
        </div>
      </Modal>
    );
  }

  return null;
}
