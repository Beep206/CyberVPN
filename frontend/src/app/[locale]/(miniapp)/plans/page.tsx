'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { plansApi, paymentsApi, promoApi, invitesApi, trialApi } from '@/lib/api';
import { motion } from 'motion/react';
import {
  Zap,
  Check,
  Gift,
  Tag,
  Users,
  Loader2,
  AlertCircle
} from 'lucide-react';
import { useTelegramWebApp } from '../hooks/useTelegramWebApp';

/**
 * Mini App Plans & Purchase page
 * Shows subscription plans, trial activation, promo codes, and invite redemption
 */
export default function MiniAppPlansPage() {
  const t = useTranslations('MiniApp.plans');
  const { haptic, colorScheme, webApp } = useTelegramWebApp();
  const queryClient = useQueryClient();

  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [promoCode, setPromoCode] = useState('');
  const [inviteCode, setInviteCode] = useState('');
  const [promoDiscount, setPromoDiscount] = useState<number | null>(null);

  // Fetch plans with pricing
  const { data: plansData, isLoading: plansLoading } = useQuery({
    queryKey: ['plans'],
    queryFn: async () => {
      const { data } = await plansApi.list();
      return data;
    },
  });

  // Fetch trial status
  const { data: trialData } = useQuery({
    queryKey: ['trial'],
    queryFn: async () => {
      const { data } = await trialApi.getStatus();
      return data;
    },
  });

  // Activate trial mutation
  const activateTrialMutation = useMutation({
    mutationFn: async () => {
      const { data } = await trialApi.activate();
      return data;
    },
    onSuccess: () => {
      haptic('heavy');
      queryClient.invalidateQueries({ queryKey: ['trial'] });
      queryClient.invalidateQueries({ queryKey: ['usage'] });
      webApp?.showAlert(t('trialActivated'));
    },
    onError: (error: unknown) => {
      haptic('heavy');
      const axiosError = error as { response?: { data?: { detail?: string } } };
      webApp?.showAlert(axiosError.response?.data?.detail || t('trialError'));
    },
  });

  // Validate promo code mutation
  const validatePromoMutation = useMutation({
    mutationFn: async (code: string) => {
      if (!selectedPlanId) throw new Error('No plan selected');
      const { data } = await promoApi.validate({
        code,
        plan_id: selectedPlanId,
      });
      return data;
    },
    onSuccess: (data) => {
      haptic('medium');
      setPromoDiscount(data.discount_amount || 0);
      webApp?.showAlert(t('promoValid', { discount: data.discount_amount }));
    },
    onError: (error: unknown) => {
      haptic('heavy');
      const axiosError = error as { response?: { data?: { detail?: string } } };
      webApp?.showAlert(axiosError.response?.data?.detail || t('promoInvalid'));
      setPromoDiscount(null);
    },
  });

  // Redeem invite code mutation
  const redeemInviteMutation = useMutation({
    mutationFn: async (code: string) => {
      const { data } = await invitesApi.redeem({ code });
      return data;
    },
    onSuccess: (data) => {
      haptic('heavy');
      queryClient.invalidateQueries({ queryKey: ['wallet'] });
      const reward = data.free_days ? `${data.free_days} days free` : 'bonus';
      webApp?.showAlert(t('inviteRedeemed', { reward }));
      setInviteCode('');
    },
    onError: (error: unknown) => {
      haptic('heavy');
      const axiosError = error as { response?: { data?: { detail?: string } } };
      webApp?.showAlert(axiosError.response?.data?.detail || t('inviteInvalid'));
    },
  });

  // Create payment invoice mutation
  const createInvoiceMutation = useMutation({
    mutationFn: async (planId: string) => {
      const invoiceData: {
        plan_id: string;
        currency: string;
        user_uuid: string;
        promo_code?: string;
      } = {
        plan_id: planId,
        currency: 'USDT', // Use USDT for crypto payments
        user_uuid: '', // Will be filled by backend from auth
      };

      // Add promo code if validated
      if (promoCode && promoDiscount !== null && promoDiscount > 0) {
        invoiceData.promo_code = promoCode;
      }

      const { data } = await paymentsApi.createInvoice(invoiceData);
      return data;
    },
    onSuccess: (data) => {
      haptic('medium');

      // Open payment URL in Telegram
      if (data.payment_url) {
        try {
          // Try Telegram native invoice first (for t.me/invoice/ or t.me/$)
          if (data.payment_url.includes('t.me/invoice/') || data.payment_url.includes('t.me/$')) {
            // Extract invoice slug from URL
            const match = data.payment_url.match(/t\.me\/(invoice\/|\\$)(.+)/);
            if (match && match[2] && webApp?.openInvoice) {
              webApp.openInvoice(data.payment_url, (status: 'paid' | 'cancelled' | 'failed' | 'pending') => {
                if (status === 'paid') {
                  webApp.showAlert(t('paymentSuccess'));
                  queryClient.invalidateQueries({ queryKey: ['usage'] });
                  queryClient.invalidateQueries({ queryKey: ['trial'] });
                } else if (status === 'cancelled') {
                  webApp.showAlert(t('paymentCancelled'));
                } else if (status === 'failed') {
                  webApp.showAlert(t('paymentFailed'));
                }
              });
              return;
            }
          }

          // Fallback 1: Try openTelegramLink (opens in Telegram internal browser)
          if (webApp?.openTelegramLink) {
            webApp.openTelegramLink(data.payment_url);
          } else {
            // Fallback 2: Standard window.open for external browser
            window.open(data.payment_url, '_blank');
          }
        } catch (err) {
          // Final fallback: window.open
          window.open(data.payment_url, '_blank');
        }
      }
    },
    onError: (error: unknown) => {
      haptic('heavy');
      const axiosError = error as { response?: { data?: { detail?: string } } };
      webApp?.showAlert(axiosError.response?.data?.detail || t('paymentError'));
    },
  });

  const canActivateTrial = trialData?.is_eligible && !trialData?.is_trial_active;

  // Theme colors
  const isDark = colorScheme === 'dark';
  const cardBg = isDark ? 'bg-[var(--tg-bg-color,oklch(0.06_0.015_260))]' : 'bg-[var(--tg-bg-color,oklch(0.70_0.010_250))]';
  const borderColor = isDark ? 'border-[var(--tg-hint-color,oklch(0.25_0.10_195))]' : 'border-[var(--tg-hint-color,oklch(0.45_0.03_250))]';

  const handlePurchase = (planId: string) => {
    haptic('medium');
    setSelectedPlanId(planId);
    createInvoiceMutation.mutate(planId);
  };

  return (
    <div className="max-w-screen-sm mx-auto space-y-4">
      {/* Trial Section */}
      {canActivateTrial && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className={`${cardBg} ${borderColor} border rounded-lg p-4`}
        >
          <div className="flex items-start gap-3">
            <Gift className="h-6 w-6 text-neon-pink flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-display mb-1">{t('freeTrialTitle')}</h3>
              <p className="text-sm text-muted-foreground font-mono mb-3">
                {t('freeTrialDescription')}
              </p>
              <button
                onClick={() => activateTrialMutation.mutate()}
                disabled={activateTrialMutation.isPending}
                className="w-full py-2 px-4 bg-neon-pink text-white font-mono rounded-lg hover:bg-neon-pink/90 transition-colors disabled:opacity-50 touch-manipulation"
              >
                {activateTrialMutation.isPending ? (
                  <span className="flex items-center justify-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {t('activating')}
                  </span>
                ) : (
                  t('activateTrial')
                )}
              </button>
            </div>
          </div>
        </motion.div>
      )}

      {/* Plans Grid */}
      <div>
        <h2 className="text-lg font-display mb-3">{t('availablePlans')}</h2>
        {plansLoading ? (
          <div className="flex items-center justify-center h-48">
            <Loader2 className="h-8 w-8 animate-spin text-neon-cyan" />
          </div>
        ) : plansData && plansData.length > 0 ? (
          <div className="space-y-3">
            {plansData.filter((p: any) => p.isActive).map((plan: any, index: number) => (
              <PlanCard
                key={plan.uuid}
                plan={plan}
                index={index}
                onPurchase={handlePurchase}
                isLoading={createInvoiceMutation.isPending && selectedPlanId === plan.uuid}
                colorScheme={colorScheme}
                haptic={haptic}
                t={t}
              />
            ))}
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className={`${cardBg} ${borderColor} border rounded-lg p-8 text-center`}
          >
            <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
            <p className="text-sm text-muted-foreground font-mono">{t('noPlans')}</p>
          </motion.div>
        )}
      </div>

      {/* Promo Code Input */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className={`${cardBg} ${borderColor} border rounded-lg p-4`}
      >
        <div className="flex items-center gap-2 mb-3">
          <Tag className="h-5 w-5 text-neon-cyan" />
          <h3 className="font-display text-sm">{t('havePromoCode')}</h3>
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={promoCode}
            onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
            placeholder={t('promoCodePlaceholder')}
            className="flex-1 px-3 py-2 bg-muted border border-border rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-neon-cyan uppercase"
          />
          <button
            onClick={() => {
              if (promoCode && selectedPlanId) {
                validatePromoMutation.mutate(promoCode);
              } else if (!selectedPlanId) {
                webApp?.showAlert(t('selectPlanFirst'));
              }
            }}
            disabled={!promoCode || validatePromoMutation.isPending}
            className="px-4 py-2 bg-neon-cyan text-black font-mono rounded-lg hover:bg-neon-cyan/90 transition-colors disabled:opacity-50 touch-manipulation whitespace-nowrap"
          >
            {validatePromoMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              t('apply')
            )}
          </button>
        </div>
        {promoDiscount !== null && promoDiscount > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="mt-2 text-xs font-mono text-neon-cyan flex items-center gap-1"
          >
            <Check className="h-3 w-3" />
            {t('discountApplied', { amount: promoDiscount })}
          </motion.div>
        )}
      </motion.div>

      {/* Invite Code Input */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className={`${cardBg} ${borderColor} border rounded-lg p-4`}
      >
        <div className="flex items-center gap-2 mb-3">
          <Users className="h-5 w-5 text-neon-purple" />
          <h3 className="font-display text-sm">{t('haveInviteCode')}</h3>
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={inviteCode}
            onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
            placeholder={t('inviteCodePlaceholder')}
            className="flex-1 px-3 py-2 bg-muted border border-border rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-neon-purple uppercase"
          />
          <button
            onClick={() => {
              if (inviteCode) {
                redeemInviteMutation.mutate(inviteCode);
              }
            }}
            disabled={!inviteCode || redeemInviteMutation.isPending}
            className="px-4 py-2 bg-neon-purple text-white font-mono rounded-lg hover:bg-neon-purple/90 transition-colors disabled:opacity-50 touch-manipulation whitespace-nowrap"
          >
            {redeemInviteMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              t('redeem')
            )}
          </button>
        </div>
        <p className="mt-2 text-xs text-muted-foreground font-mono">
          {t('inviteCodeNote')}
        </p>
      </motion.div>
    </div>
  );
}

// Plan Card Component
function PlanCard({
  plan,
  index,
  onPurchase,
  isLoading,
  colorScheme,
  haptic,
  t,
}: {
  plan: {
    uuid: string;
    name: string;
    price: number;
    currency: string;
    durationDays: number;
    dataLimitGb?: number | null;
    maxDevices?: number | null;
    features?: string[] | null;
    isActive: boolean;
  };
  index: number;
  onPurchase: (planId: string) => void;
  isLoading: boolean;
  colorScheme: 'light' | 'dark';
  haptic: () => void;
  t: (key: string, values?: Record<string, string | number>) => string;
}) {
  const isDark = colorScheme === 'dark';
  const cardBg = isDark ? 'bg-[var(--tg-bg-color,oklch(0.06_0.015_260))]' : 'bg-[var(--tg-bg-color,oklch(0.70_0.010_250))]';
  const borderColor = isDark ? 'border-[var(--tg-hint-color,oklch(0.25_0.10_195))]' : 'border-[var(--tg-hint-color,oklch(0.45_0.03_250))]';

  // Format duration
  const formatDuration = (days: number): string => {
    if (days === 1) return t('oneDay') || '1 day';
    if (days === 7) return t('oneWeek') || '1 week';
    if (days === 30 || days === 31) return t('oneMonth') || '1 month';
    if (days === 90) return t('threeMonths') || '3 months';
    if (days === 180) return t('sixMonths') || '6 months';
    if (days === 365 || days === 366) return t('oneYear') || '1 year';
    return `${days} ${t('days') || 'days'}`;
  };

  // Format traffic limit
  const formatTraffic = (gb: number | null | undefined): string => {
    if (!gb) return t('unlimited') || 'Unlimited';
    if (gb >= 1000) return `${(gb / 1000).toFixed(1)} TB`;
    return `${gb} GB`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.1 }}
      className={`${cardBg} ${borderColor} border rounded-lg p-4`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="text-lg font-display text-neon-cyan mb-1">{plan.name}</h3>
          <p className="text-sm text-muted-foreground font-mono">
            {formatDuration(plan.durationDays)} • {formatTraffic(plan.dataLimitGb)}
          </p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-display text-foreground">
            {plan.price}
          </div>
          <div className="text-xs text-muted-foreground font-mono">
            {plan.currency}
          </div>
        </div>
      </div>

      {/* Features */}
      {plan.features && plan.features.length > 0 && (
        <div className="space-y-1 mb-4">
          {plan.features.slice(0, 3).map((feature, idx) => (
            <div key={idx} className="flex items-start gap-2">
              <Check className="h-3 w-3 text-neon-cyan flex-shrink-0 mt-0.5" />
              <span className="text-xs text-muted-foreground">{feature}</span>
            </div>
          ))}
        </div>
      )}

      {/* Purchase Button */}
      <button
        onClick={() => {
          haptic();
          onPurchase(plan.uuid);
        }}
        disabled={isLoading}
        className="w-full py-2 px-4 bg-neon-cyan text-black font-mono rounded-lg hover:bg-neon-cyan/90 transition-colors disabled:opacity-50 touch-manipulation"
      >
        {isLoading ? (
          <span className="flex items-center justify-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            {t('processing')}
          </span>
        ) : (
          <span className="flex items-center justify-center gap-2">
            <Zap className="h-4 w-4" />
            {t('purchasePlan')}
          </span>
        )}
      </button>
    </motion.div>
  );
}
