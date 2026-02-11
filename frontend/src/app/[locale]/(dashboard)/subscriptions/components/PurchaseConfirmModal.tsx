'use client';

import { useState } from 'react';
import { Modal } from '@/shared/ui/modal';
import { paymentsApi } from '@/lib/api/payments';
import { promoApi } from '@/lib/api/promo';
import { motion } from 'motion/react';
import { AlertTriangle, CheckCircle, CreditCard, Tag, Percent, Check, Zap } from 'lucide-react';
import { AxiosError } from 'axios';
import { CyberInput } from '@/features/auth/components/CyberInput';
import { markPerformance, measurePerformance, PerformanceMarks } from '@/shared/lib/web-vitals';

interface Plan {
  uuid: string;
  name: string;
  price: number;
  currency: string;
  durationDays: number;
  dataLimitGb?: number | null;
  maxDevices?: number | null;
  features?: string[] | null;
}

interface PurchaseConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  plan: Plan | null;
}

type ModalStep = 'confirm' | 'processing' | 'success' | 'error';

export function PurchaseConfirmModal({
  isOpen,
  onClose,
  plan,
}: PurchaseConfirmModalProps) {
  const [step, setStep] = useState<ModalStep>('confirm');
  const [error, setError] = useState('');
  const [promoCode, setPromoCode] = useState('');
  const [validatingPromo, setValidatingPromo] = useState(false);
  const [promoError, setPromoError] = useState('');
  const [promoDiscount, setPromoDiscount] = useState<any>(null);

  // Reset state on close
  const handleClose = () => {
    setStep('confirm');
    setError('');
    setPromoCode('');
    setPromoDiscount(null);
    setPromoError('');
    onClose();
  };

  // Format duration
  const formatDuration = (days: number): string => {
    if (days === 1) return '1 day';
    if (days === 7) return '1 week';
    if (days === 30 || days === 31) return '1 month';
    if (days === 90) return '3 months';
    if (days === 180) return '6 months';
    if (days === 365 || days === 366) return '1 year';
    return `${days} days`;
  };

  // Format traffic
  const formatTraffic = (gb: number | null | undefined): string => {
    if (!gb) return 'Unlimited';
    if (gb >= 1000) return `${gb / 1000} TB`;
    return `${gb} GB`;
  };

  // Calculate final price with discount
  const calculateFinalPrice = () => {
    if (!plan) return 0;
    if (!promoDiscount) return plan.price;

    if (promoDiscount.discount_percent) {
      return plan.price * (1 - promoDiscount.discount_percent / 100);
    }
    if (promoDiscount.discount_amount) {
      return Math.max(0, plan.price - promoDiscount.discount_amount);
    }
    return plan.price;
  };

  // Validate promo code
  const handleValidatePromo = async () => {
    if (!promoCode.trim()) {
      setPromoError('Please enter a promo code');
      return;
    }

    setValidatingPromo(true);
    setPromoError('');
    setPromoDiscount(null);

    try {
      const response = await promoApi.validate({ code: promoCode });
      setPromoDiscount(response.data);
      setPromoError('');
    } catch (err) {
      if (err instanceof AxiosError) {
        const detail = err.response?.data?.detail;
        if (err.response?.status === 404) {
          setPromoError('Invalid or expired promo code');
        } else if (err.response?.status === 400) {
          setPromoError(detail || 'Promo code not valid');
        } else {
          setPromoError(detail || 'Failed to validate promo code');
        }
      } else {
        setPromoError('An error occurred. Please try again.');
      }
      setPromoDiscount(null);
    } finally {
      setValidatingPromo(false);
    }
  };

  // Handle purchase
  const handlePurchase = async () => {
    if (!plan) return;

    // Mark start of purchase flow
    markPerformance(PerformanceMarks.PURCHASE_FLOW_START, {
      planId: plan.uuid,
      planName: plan.name,
      hasPromoCode: !!promoCode,
    });

    setStep('processing');
    setError('');

    try {
      const requestData: any = {
        plan_id: plan.uuid,
        user_uuid: '',
        currency: 'USDT',
      };

      // Add promo code if validated
      if (promoCode && promoDiscount) {
        requestData.promo_code = promoCode;
      }

      const response = await paymentsApi.createInvoice(requestData);
      const invoiceUrl = response.data?.payment_url;

      if (invoiceUrl) {
        setStep('success');

        // Mark completion of purchase flow
        markPerformance(PerformanceMarks.PURCHASE_FLOW_COMPLETE, {
          planId: plan.uuid,
          planName: plan.name,
        });

        // Measure total duration
        measurePerformance(
          'purchase-flow-duration',
          PerformanceMarks.PURCHASE_FLOW_START,
          PerformanceMarks.PURCHASE_FLOW_COMPLETE
        );

        // Open payment URL in new tab
        window.open(invoiceUrl, '_blank');

        // Auto-close modal after 2 seconds
        setTimeout(() => {
          handleClose();
        }, 2000);
      } else {
        throw new Error('No payment URL received');
      }
    } catch (err) {
      setStep('error');
      if (err instanceof AxiosError) {
        const detail = err.response?.data?.detail;
        if (err.response?.status === 404) {
          setError('Plan not found');
        } else if (err.response?.status === 400) {
          setError(detail || 'Invalid purchase request');
        } else {
          setError(detail || 'Failed to create invoice');
        }
      } else {
        setError('An error occurred. Please try again.');
      }
    }
  };

  if (!plan) return null;

  // Render confirmation step
  if (step === 'confirm') {
    const finalPrice = calculateFinalPrice();
    const savings = plan.price - finalPrice;

    return (
      <Modal isOpen={isOpen} onClose={handleClose} title="CONFIRM_PURCHASE">
        <div className="space-y-6">
          {/* Plan Details */}
          <div className="cyber-card p-6 bg-terminal-surface/50">
            <div className="flex items-start gap-4 mb-4">
              <div className="p-3 bg-neon-cyan/10 border border-neon-cyan/30 rounded-lg">
                <CreditCard className="h-6 w-6 text-neon-cyan" />
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-display text-neon-cyan mb-1">
                  {plan.name}
                </h3>
                <p className="text-sm text-muted-foreground font-mono">
                  {formatDuration(plan.durationDays)} • {formatTraffic(plan.dataLimitGb)}
                </p>
              </div>
            </div>

            {/* Features */}
            {plan.features && plan.features.length > 0 && (
              <div className="space-y-2 mb-4 pb-4 border-b border-grid-line/30">
                {plan.features.map((feature, index) => (
                  <div key={index} className="flex items-start gap-2">
                    <Check className="h-4 w-4 text-matrix-green flex-shrink-0 mt-0.5" />
                    <span className="text-sm text-muted-foreground">{feature}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Price */}
            <div className="flex items-baseline justify-between">
              <span className="text-sm text-muted-foreground">Total Price:</span>
              <div className="flex items-baseline gap-2">
                {savings > 0 && (
                  <span className="text-lg text-muted-foreground line-through font-mono">
                    {plan.price} {plan.currency}
                  </span>
                )}
                <span className="text-3xl font-display text-matrix-green">
                  {finalPrice.toFixed(2)}
                </span>
                <span className="text-lg text-muted-foreground font-mono">
                  {plan.currency}
                </span>
              </div>
            </div>

            {savings > 0 && (
              <div className="mt-2 text-right">
                <span className="text-sm text-matrix-green font-mono">
                  You save {savings.toFixed(2)} {plan.currency}!
                </span>
              </div>
            )}
          </div>

          {/* Promo Code Section */}
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
                disabled={validatingPromo || !!promoDiscount}
                onKeyDown={(e) => e.key === 'Enter' && handleValidatePromo()}
              />

              {/* Discount Preview */}
              {promoDiscount && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="flex items-start gap-2 p-3 bg-matrix-green/10 border border-matrix-green/30 rounded"
                >
                  <Percent className="h-4 w-4 text-matrix-green flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Check className="h-3 w-3 text-matrix-green" />
                      <span className="text-xs font-semibold text-matrix-green">
                        Valid Promo Code
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {promoDiscount.discount_percent && `${promoDiscount.discount_percent}% discount applied`}
                      {promoDiscount.discount_amount && `$${promoDiscount.discount_amount} discount applied`}
                    </p>
                  </div>
                </motion.div>
              )}

              {!promoDiscount && (
                <button
                  onClick={handleValidatePromo}
                  disabled={validatingPromo || !promoCode.trim()}
                  className="w-full px-3 py-2 bg-neon-purple/20 hover:bg-neon-purple/30 border border-neon-purple/50 text-neon-purple font-mono text-sm rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {validatingPromo ? 'Validating...' : 'Apply Promo'}
                </button>
              )}
            </div>
          </div>

          {/* Payment Info */}
          <div className="p-4 bg-neon-cyan/5 border border-neon-cyan/30 rounded-lg">
            <div className="flex items-start gap-3">
              <Zap className="h-5 w-5 text-neon-cyan flex-shrink-0 mt-0.5" />
              <div className="flex-1 space-y-1">
                <p className="text-sm font-semibold text-neon-cyan">
                  Crypto Payment
                </p>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  You'll be redirected to a secure crypto payment page. Complete the payment to activate your subscription instantly.
                </p>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleClose}
              className="flex-1 px-4 py-3 bg-terminal-bg hover:bg-terminal-surface border border-grid-line/50 text-muted-foreground font-mono text-sm rounded transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handlePurchase}
              className="flex-1 px-4 py-3 bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan font-mono text-sm rounded transition-colors hover:shadow-[0_0_15px_rgba(0,255,255,0.3)]"
            >
              Pay with Crypto
            </button>
          </div>
        </div>
      </Modal>
    );
  }

  // Render processing step
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

  // Render success step
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
              Payment Page Opened
            </h3>
            <p className="text-sm text-muted-foreground">
              Complete your payment in the new tab to activate your subscription
            </p>
          </div>
        </motion.div>
      </Modal>
    );
  }

  // Render error step
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
