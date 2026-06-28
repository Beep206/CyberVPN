'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Modal } from '@/shared/ui/modal';
import {
  commerceApi,
  createClientIdempotencyKey,
  OFFICIAL_WEB_SALE_CHANNEL,
  OFFICIAL_WEB_STOREFRONT_KEY,
  type CreateQuoteSessionRequest,
  type QuoteSessionResponse,
} from '@/lib/api/commerce';
import { motion } from 'motion/react';
import { useLocale, useTranslations } from 'next-intl';
import {
  AlertTriangle,
  CheckCircle,
  CreditCard,
  Percent,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import { AxiosError } from 'axios';
import {
  buildPrivateOfferUnlockCopy,
  PrivateOfferUnlock,
  type PrivateOfferSelection,
} from '@/features/customer-growth/components/PrivateOfferUnlock';
import {
  GrowthCodeBasket,
  createEmptyGrowthCodeBasketSummary,
  type GrowthCodeBasketHandle,
  type GrowthCodeBasketPrimarySelection,
  type GrowthCodeBasketSummary,
} from '@/features/customer-growth-code-basket/components/GrowthCodeBasket';
import { extractCheckoutCodeSetRejection } from '@/features/customer-growth-code-basket/lib/code-set-rejection';
import { buildGrowthCodeBasketCopy } from '@/features/customer-growth-code-basket/lib/copy';
import {
  areCheckoutCodeDiscountsEnabled,
  arePromoCodesEnabled,
  useClientCapabilities,
} from '@/features/client-capabilities/useClientCapabilities';
import {
  markPerformance,
  measurePerformance,
  PerformanceMarks,
} from '@/shared/lib/web-vitals';
import {
  canOfficialWebSurfaceAccess,
  shouldRenderOfficialQuoteAdjustmentBanner,
} from '@/shared/lib/surface-policy';
import {
  formatConnectionModes,
  formatDurationLabel,
  formatMoney,
  formatSupportLabel,
  formatTrafficLabel,
  getPlanPrice,
  type SubscriptionPlan,
} from '../lib/plan-presenter';

interface PurchaseConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  plan: SubscriptionPlan | null;
}

type ModalStep = 'confirm' | 'processing' | 'success' | 'error';
const MAX_QUOTE_EXPIRY_TIMER_MS = 2_147_483_647;

function buildQuoteRequest(
  plan: SubscriptionPlan,
  codeInputs?: string[],
  privateOffer?: PrivateOfferSelection | null,
): CreateQuoteSessionRequest {
  const quoteHandoff = plan.public_catalog_quote;
  const catalogPrice = plan.public_catalog_price;
  const acceptedCodes = (codeInputs ?? []).filter((code) => code.trim().length > 0);

  const request: CreateQuoteSessionRequest = {
    storefront_key: OFFICIAL_WEB_STOREFRONT_KEY,
    plan_id: privateOffer?.planId ?? quoteHandoff?.planId ?? plan.uuid,
    addons: [],
    private_catalog_grant_id: privateOffer?.privateCatalogGrantId ?? undefined,
    use_wallet: 0,
    currency: quoteHandoff?.currency ?? catalogPrice?.currency ?? 'USD',
    channel: OFFICIAL_WEB_SALE_CHANNEL,
  };

  if (acceptedCodes.length === 1) {
    request.code_input = acceptedCodes[0];
  } else if (acceptedCodes.length > 1) {
    request.codes = acceptedCodes.map((code, index) => ({
      code,
      client_slot_id: `web-growth-code-${index + 1}`,
    }));
  }

  return request;
}

function getPublicCatalogAmount(plan: SubscriptionPlan): number {
  if (!plan.public_catalog_price) {
    return plan.price_usd;
  }

  const amount = Number(plan.public_catalog_price.amount);
  return Number.isFinite(amount) ? amount : plan.price_usd;
}

function getQuoteErrorMessage(err: unknown, fallback: string, codeSetRejectedFallback: string) {
  if (extractCheckoutCodeSetRejection(err)) {
    return codeSetRejectedFallback;
  }

  if (err instanceof AxiosError) {
    const detail = err.response?.data?.detail;
    return detail || fallback;
  }

  return fallback;
}

export function PurchaseConfirmModal({
  isOpen,
  onClose,
  plan,
}: PurchaseConfirmModalProps) {
  const locale = useLocale();
  const t = useTranslations('Subscriptions');
  const queryClient = useQueryClient();
  const { data: capabilities } = useClientCapabilities();
  const [step, setStep] = useState<ModalStep>('confirm');
  const [error, setError] = useState('');
  const [quoteSession, setQuoteSession] = useState<QuoteSessionResponse | null>(null);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [quoteExpired, setQuoteExpired] = useState(false);
  const [appliedCodeInput, setAppliedCodeInput] = useState<string | null>(null);
  const [appliedCodeInputs, setAppliedCodeInputs] = useState<string[]>([]);
  const [appliedCodeType, setAppliedCodeType] =
    useState<GrowthCodeBasketPrimarySelection['codeType']>(null);
  const [codeBasketSummary, setCodeBasketSummary] =
    useState<GrowthCodeBasketSummary>(() => createEmptyGrowthCodeBasketSummary());
  const [privateOfferSelection, setPrivateOfferSelection] =
    useState<PrivateOfferSelection | null>(null);
  const [successMessage, setSuccessMessage] = useState(t('checkoutQuote.paymentPageOpened'));
  const quoteRequestId = useRef(0);
  const growthCodeBasketRef = useRef<GrowthCodeBasketHandle>(null);
  const privateOfferCopy = useMemo(() => buildPrivateOfferUnlockCopy(t), [t]);
  const growthCodeBasketCopy = useMemo(() => buildGrowthCodeBasketCopy(t), [t]);
  const checkoutQuoteCodeSetRejected = t('checkoutQuote.codeSetRejected');
  const privateOfferQuoteError = t('privateOffer.quoteError');

  const handleClose = () => {
    setStep('confirm');
    setError('');
    setQuoteSession(null);
    setQuoteLoading(false);
    setQuoteExpired(false);
    setAppliedCodeInput(null);
    setAppliedCodeInputs([]);
    setAppliedCodeType(null);
    setCodeBasketSummary(createEmptyGrowthCodeBasketSummary());
    setPrivateOfferSelection(null);
    setSuccessMessage(t('checkoutQuote.paymentPageOpened'));
    onClose();
  };

  const planPrice = plan ? getPlanPrice(plan, locale) : null;
  const checkoutQuoteLoadError = t('checkoutQuote.loadError');

  const requestQuoteSession = useCallback(async ({
    codeInputs,
    privateOffer,
    fallbackError,
  }: {
    codeInputs?: string[];
    privateOffer?: PrivateOfferSelection | null;
    fallbackError: string;
  }) => {
    const activePlan = plan;
    if (!activePlan) {
      return;
    }

    const requestId = quoteRequestId.current + 1;
    quoteRequestId.current = requestId;
    setQuoteLoading(true);
    setError('');

    try {
      const response = await commerceApi.createQuoteSession(
        buildQuoteRequest(activePlan, codeInputs, privateOffer ?? null),
      );

      if (requestId === quoteRequestId.current) {
        setQuoteSession(response.data);
        setQuoteExpired(false);
      }
    } catch (err) {
      if (requestId === quoteRequestId.current) {
        const codeSetRejection = extractCheckoutCodeSetRejection(err);
        if (codeSetRejection) {
          growthCodeBasketRef.current?.applyServerApplications(codeSetRejection.applications);
        }
        setQuoteSession(null);
        setError(getQuoteErrorMessage(
          err,
          fallbackError,
          checkoutQuoteCodeSetRejected,
        ));
      }
    } finally {
      if (requestId === quoteRequestId.current) {
        setQuoteLoading(false);
      }
    }
  }, [checkoutQuoteCodeSetRejected, plan]);

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
      setQuoteSession(null);
      setQuoteExpired(false);
      setAppliedCodeInput(null);
      setAppliedCodeInputs([]);
      setAppliedCodeType(null);
      setCodeBasketSummary(createEmptyGrowthCodeBasketSummary());
      setPrivateOfferSelection(null);

      try {
        const response = await commerceApi.createQuoteSession(
          buildQuoteRequest(initialPlan),
        );
        if (!isCancelled) {
          setQuoteSession(response.data);
        }
      } catch (err) {
        if (!isCancelled) {
          setError(getQuoteErrorMessage(
            err,
            checkoutQuoteLoadError,
            checkoutQuoteCodeSetRejected,
          ));
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
  }, [checkoutQuoteCodeSetRejected, checkoutQuoteLoadError, isOpen, plan]);

  useEffect(() => {
    if (!quoteSession) {
      setQuoteExpired(false);
      return;
    }

    const expiresAt = Date.parse(quoteSession.expires_at);
    if (!Number.isFinite(expiresAt)) {
      setQuoteExpired(false);
      return;
    }

    const delay = expiresAt - Date.now();
    if (delay <= 0 || quoteSession.status !== 'open') {
      setQuoteExpired(true);
      return;
    }

    setQuoteExpired(false);
    const timeoutId = setTimeout(
      () => setQuoteExpired(true),
      Math.min(delay, MAX_QUOTE_EXPIRY_TIMER_MS),
    );

    return () => {
      clearTimeout(timeoutId);
    };
  }, [quoteSession]);

  const handleRefreshQuote = async () => {
    const activePlan = plan;
    if (!activePlan) return;

    setQuoteLoading(true);
    setError('');

    try {
      const response = await commerceApi.createQuoteSession(
        buildQuoteRequest(activePlan, appliedCodeInputs, privateOfferSelection),
      );
      setQuoteSession(response.data);
      setQuoteExpired(false);
    } catch (err) {
      const codeSetRejection = extractCheckoutCodeSetRejection(err);
      if (codeSetRejection) {
        growthCodeBasketRef.current?.applyServerApplications(codeSetRejection.applications);
      }
      setError(getQuoteErrorMessage(
        err,
        t('checkoutQuote.refreshError'),
        checkoutQuoteCodeSetRejected,
      ));
    } finally {
      setQuoteLoading(false);
    }
  };

  const handlePrivateOfferSelectionChange = useCallback(async (
    selection: PrivateOfferSelection | null,
  ) => {
    const activePlan = plan;
    const hadPrivateOffer = Boolean(privateOfferSelection);
    setPrivateOfferSelection(selection);
    setQuoteExpired(false);
    setError('');

    if (!activePlan || (!selection && !hadPrivateOffer)) {
      return;
    }

    await requestQuoteSession({
      codeInputs: appliedCodeInputs,
      privateOffer: selection,
      fallbackError: privateOfferQuoteError,
    });
  }, [appliedCodeInputs, plan, privateOfferQuoteError, privateOfferSelection, requestQuoteSession]);

  const handleGrowthCodeBasketSelectionChange = useCallback((
    primary: GrowthCodeBasketPrimarySelection | null,
    summary: GrowthCodeBasketSummary,
  ) => {
    setCodeBasketSummary(summary);

    if (summary.pendingCount > 0) {
      return;
    }

    const nextCodes = summary.acceptedCodes;
    const nextCode = nextCodes[0] ?? null;
    const nextCodeType = primary?.codeType ?? null;
    setAppliedCodeInput(nextCode);
    setAppliedCodeInputs(nextCodes);
    setAppliedCodeType(nextCodeType);

    void requestQuoteSession({
      codeInputs: nextCodes,
      privateOffer: privateOfferSelection,
      fallbackError: checkoutQuoteLoadError,
    });
  }, [checkoutQuoteLoadError, privateOfferSelection, requestQuoteSession]);

  const handlePurchase = async () => {
    const activePlan = plan;
    if (!activePlan) return;
    if (!quoteSession || quoteExpired) {
      setError(t('checkoutQuote.expiredBody'));
      setStep('confirm');
      return;
    }

    markPerformance(PerformanceMarks.PURCHASE_FLOW_START, {
      planId: privateOfferSelection?.planId ?? activePlan.uuid,
      planName: activePlan.display_name,
      hasPromoCode: appliedCodeInputs.length > 0,
    });

    setStep('processing');
    setError('');

    try {
      const freshQuote = await commerceApi.getQuoteSession(quoteSession.id);
      if (freshQuote.data.status !== 'open') {
        setQuoteSession(freshQuote.data);
        setQuoteExpired(true);
        setStep('confirm');
        setError(t('checkoutQuote.expiredBody'));
        return;
      }

      const checkoutSessionResponse = await commerceApi.createCheckoutSession(
        { quote_session_id: freshQuote.data.id },
        createClientIdempotencyKey('checkout-session'),
      );
      const orderResponse = await commerceApi.commitOrder({
        checkout_session_id: checkoutSessionResponse.data.id,
      });
      const paymentAttemptResponse = await commerceApi.createPaymentAttempt(
        { order_id: orderResponse.data.id },
        createClientIdempotencyKey('payment-attempt'),
      );

      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['orders'] }),
        queryClient.invalidateQueries({ queryKey: ['current-entitlements'] }),
        queryClient.invalidateQueries({ queryKey: ['current-service-state'] }),
        queryClient.invalidateQueries({ queryKey: ['subscriptions'] }),
        queryClient.invalidateQueries({ queryKey: ['payments', 'history'] }),
      ]);

      if (paymentAttemptResponse.data.invoice?.payment_url) {
        window.open(
          paymentAttemptResponse.data.invoice.payment_url,
          '_blank',
          'noopener,noreferrer',
        );
        setSuccessMessage(t('checkoutQuote.paymentPageOpened'));
      } else {
        setSuccessMessage(t('checkoutQuote.subscriptionActivated'));
      }

      setStep('success');
      markPerformance(PerformanceMarks.PURCHASE_FLOW_COMPLETE, {
        planId: privateOfferSelection?.planId ?? activePlan.uuid,
        planName: activePlan.display_name,
      });
      measurePerformance(
        'purchase-flow-duration',
        PerformanceMarks.PURCHASE_FLOW_START,
        PerformanceMarks.PURCHASE_FLOW_COMPLETE,
      );

      setTimeout(() => {
        handleClose();
      }, 2200);
    } catch (err) {
      const codeSetRejection = extractCheckoutCodeSetRejection(err);
      if (codeSetRejection) {
        growthCodeBasketRef.current?.applyServerApplications(codeSetRejection.applications);
        setStep('confirm');
        setError(checkoutQuoteCodeSetRejected);
        return;
      }

      setStep('error');
      if (err instanceof AxiosError) {
        const detail = err.response?.data?.detail;
        setError(detail || t('checkoutQuote.commitError'));
      } else {
        setError(t('checkoutQuote.genericError'));
      }
    }
  };

  if (!plan) return null;
  const quote = quoteSession?.quote ?? null;
  const quoteCurrency =
    quoteSession?.currency_code ??
    plan.public_catalog_price?.currency ??
    planPrice?.currency ??
    'USD';
  const quoteSnapshot = quote?.entitlements_snapshot.effective_entitlements;
  const quotedTotal = quote?.displayed_price ?? planPrice?.amount ?? plan.price_usd;
  const quotedBase = quote?.base_price ?? planPrice?.amount ?? plan.price_usd;
  const hasDiscount = (quote?.discount_amount ?? 0) > 0;
  const quotedGateway = quote?.gateway_amount ?? planPrice?.amount ?? plan.price_usd;
  const quotePlanId =
    privateOfferSelection?.planId
    ?? plan.public_catalog_quote?.planId
    ?? plan.uuid;
  const codeBasketBlocksCheckout =
    codeBasketSummary.pendingCount > 0 || codeBasketSummary.isDegraded;
  const showPromoControls =
    arePromoCodesEnabled(capabilities) &&
    areCheckoutCodeDiscountsEnabled(capabilities);
  const showQuoteAdjustmentBanner =
    appliedCodeInput && quote
      ? shouldRenderOfficialQuoteAdjustmentBanner({
          discountAmount: quote.discount_amount,
          partnerMarkup: quote.partner_markup,
        })
      : false;

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
                  {formatDurationLabel(plan.duration_days)} •{' '}
                  {formatTrafficLabel(plan)}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 mb-4 pb-4 border-b border-grid-line/30">
              <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                <p className="text-[10px] uppercase tracking-[0.18em] text-white/40 font-mono">
                  {t('checkoutQuote.devices')}
                </p>
                <p className="mt-2 text-lg font-display text-white">
                  {quoteSnapshot?.device_limit ?? plan.devices_included}
                </p>
              </div>
              <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                <p className="text-[10px] uppercase tracking-[0.18em] text-white/40 font-mono">
                  {t('checkoutQuote.support')}
                </p>
                <p className="mt-2 text-sm font-mono text-white/75">
                  {formatSupportLabel(
                    quoteSnapshot?.support_sla ?? plan.support_sla,
                  )}
                </p>
              </div>
            </div>

            <div className="space-y-2 text-sm text-muted-foreground">
              <div className="flex items-start justify-between gap-4">
                <span>{t('checkoutQuote.connectionModes')}</span>
                <span className="max-w-[16rem] text-right font-mono text-white/75">
                  {formatConnectionModes(
                    quoteSnapshot?.connection_modes ?? plan.connection_modes,
                  )}
                </span>
              </div>
              <div className="flex items-start justify-between gap-4">
                <span>{t('checkoutQuote.trafficPolicy')}</span>
                <span className="font-mono text-white/75">
                  {quoteSnapshot?.display_traffic_label ??
                    formatTrafficLabel(plan)}
                </span>
              </div>
              <div className="flex items-start justify-between gap-4">
                <span>{t('checkoutQuote.total')}</span>
                <div className="text-right">
                  {hasDiscount && (
                    <p className="font-mono text-xs text-white/35 line-through">
                      {formatMoney(locale, quotedBase, quoteCurrency)}
                    </p>
                  )}
                  <p className="text-2xl font-display text-matrix-green">
                    {formatMoney(locale, quotedTotal, quoteCurrency)}
                  </p>
                  <p className="mt-1 font-mono text-[11px] uppercase tracking-[0.16em] text-white/40">
                    {t('checkoutQuote.chargedIn', { currency: quoteCurrency })}
                  </p>
                </div>
              </div>
            </div>

            {planPrice && quote == null && !quoteLoading && (
              <p className="mt-3 text-xs font-mono text-white/45">
                {t('checkoutQuote.catalogPrice', { price: planPrice.formatted })}
              </p>
            )}

            {quoteExpired ? (
              <div className="mt-4 rounded-lg border border-amber-400/30 bg-amber-400/10 px-4 py-3">
                <p className="text-sm font-semibold text-amber-200">
                  {t('checkoutQuote.expiredTitle')}
                </p>
                <p className="mt-1 text-xs leading-relaxed text-amber-100/75">
                  {t('checkoutQuote.expiredBody')}
                </p>
                <button
                  type="button"
                  onClick={handleRefreshQuote}
                  disabled={quoteLoading}
                  className="mt-3 rounded border border-amber-300/50 px-3 py-2 font-mono text-xs uppercase tracking-[0.16em] text-amber-100 transition-colors hover:bg-amber-300/10 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {quoteLoading ? t('checkoutQuote.refreshing') : t('checkoutQuote.refreshCta')}
                </button>
              </div>
            ) : null}
          </div>

          <PrivateOfferUnlock
            storefrontKey={OFFICIAL_WEB_STOREFRONT_KEY}
            channel={OFFICIAL_WEB_SALE_CHANNEL}
            currency={quoteCurrency}
            copy={privateOfferCopy}
            selectedOffer={privateOfferSelection}
            onSelectionChange={handlePrivateOfferSelectionChange}
            variant="web"
          />

          {showPromoControls ? (
            <GrowthCodeBasket
              ref={growthCodeBasketRef}
              copy={growthCodeBasketCopy}
              context={{
                storefrontKey: OFFICIAL_WEB_STOREFRONT_KEY,
                planId: quotePlanId,
                amount: getPublicCatalogAmount(plan),
                channel: OFFICIAL_WEB_SALE_CHANNEL,
                flow: 'checkout',
                partnerCodeEntryAllowed:
                  canOfficialWebSurfaceAccess('partner_code_entry'),
              }}
              contextFingerprint={[
                OFFICIAL_WEB_STOREFRONT_KEY,
                OFFICIAL_WEB_SALE_CHANNEL,
                quotePlanId,
                quoteCurrency,
                getPublicCatalogAmount(plan),
                privateOfferSelection?.privateCatalogGrantId ?? 'public',
              ].join(':')}
              disabled={quoteLoading}
              slotIdPrefix="web-growth-code"
              onSelectionChange={handleGrowthCodeBasketSelectionChange}
              variant="web"
            />
          ) : null}

          {showQuoteAdjustmentBanner ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-start gap-2 rounded border border-matrix-green/30 bg-matrix-green/10 p-3"
            >
              <Percent className="mt-0.5 h-4 w-4 flex-shrink-0 text-matrix-green" />
              <div className="flex-1">
                <div className="mb-1 flex items-center gap-2">
                  <ShieldCheck className="h-3 w-3 text-matrix-green" />
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-matrix-green">
                    {appliedCodeType === 'referral'
                      ? t('checkoutQuote.referralCodeAccepted')
                      : t('checkoutQuote.checkoutCodeAccepted')}
                  </span>
                </div>
                {(quote?.discount_amount ?? 0) > 0 ? (
                  <p className="text-xs text-muted-foreground">
                    {t('checkoutQuote.discountApplied', {
                      amount: formatMoney(locale, quote?.discount_amount ?? 0, quoteCurrency),
                    })}
                  </p>
                ) : null}
              </div>
            </motion.div>
          ) : null}

          <div className="p-4 bg-neon-cyan/5 border border-neon-cyan/30 rounded-lg">
            <div className="flex items-start gap-3">
              <Zap className="h-5 w-5 text-neon-cyan flex-shrink-0 mt-0.5" />
              <div className="flex-1 space-y-1">
                <p className="text-sm font-semibold text-neon-cyan">
                  {t('checkoutQuote.secureTitle')}
                </p>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {t('checkoutQuote.secureDescription')}
                </p>
                <p className="text-xs font-mono text-white/55">
                  {t('checkoutQuote.gatewayAmount', {
                    amount: formatMoney(locale, quotedGateway, quoteCurrency),
                    currency: quoteCurrency,
                  })}
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
              {t('checkoutQuote.cancel')}
            </button>
            <button
              onClick={handlePurchase}
              disabled={
                quoteLoading
                || Boolean(error)
                || quoteExpired
                || !quoteSession
                || codeBasketBlocksCheckout
              }
              className="flex-1 px-4 py-3 bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan font-mono text-sm rounded transition-colors hover:shadow-[0_0_15px_rgba(0,255,255,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {quote?.is_zero_gateway ? t('checkoutQuote.activateNow') : t('checkoutQuote.payWithCrypto')}
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
            {t('checkoutQuote.processingPayment')}
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
              {successMessage === t('checkoutQuote.subscriptionActivated')
                ? t('checkoutQuote.successActivatedBody')
                : t('checkoutQuote.successPaymentBody')}
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
              {t('checkoutQuote.paymentFailed')}
            </h3>
            <p className="text-sm text-muted-foreground">
              {error || t('checkoutQuote.paymentInvoiceFailed')}
            </p>
          </div>
          <button
            onClick={() => setStep('confirm')}
            className="px-6 py-3 bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan font-mono text-sm rounded transition-colors"
          >
            {t('checkoutQuote.tryAgain')}
          </button>
        </div>
      </Modal>
    );
  }

  return null;
}
