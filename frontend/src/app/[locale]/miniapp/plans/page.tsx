'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocale, useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import {
  AlertCircle,
  Check,
  ChevronRight,
  Gift,
  Loader2,
  Minus,
  Orbit,
  ShieldCheck,
  Sparkles,
  Tag,
  Users,
  Zap,
} from 'lucide-react';
import { codesApi, invitesApi, miniappApi } from '@/lib/api';
import type { MiniAppCheckoutFlow } from '@/lib/api/miniapp';
import type { CheckoutCommitResponse, CheckoutQuoteResponse } from '@/lib/api/payments';
import type { PlanRecord } from '@/lib/api/plans';
import type { CurrentEntitlementsResponse } from '@/lib/api/subscriptions';
import {
  getGrowthCodeResolutionMessage,
  getUnsupportedCheckoutCodeMessage,
} from '@/features/customer-growth/lib/checkout-code-resolution';
import { formatMoney, getPricePresentation } from '@/widgets/pricing/utils';
import { STAGE1_CHECKOUT_CODES_UI_ENABLED } from '@/shared/lib/stage1-growth-flags';
import type { PricingTierCode } from '@/widgets/pricing/types';
import { useTelegramWebApp } from '../hooks/useTelegramWebApp';
import { emitMiniAppRuntimeEvent } from '@/features/miniapp-runtime/lib/runtime-analytics';

type PlanFamily = {
  code: PricingTierCode;
  displayName: string;
  devicesIncluded: number;
  connectionModes: string[];
  serverPool: string[];
  supportSla: string;
  dedicatedIpIncluded: number;
  dedicatedIpEligible: boolean;
  periods: PlanRecord[];
  sortOrder: number;
};

type QuoteFlow = 'checkout' | 'upgrade' | 'addons' | 'current' | 'none';
type CheckoutAddonLine = {
  code: string;
  qty: number;
  location_code?: string;
};
type CommitCheckoutPayload = {
  flow: MiniAppCheckoutFlow;
  selectedSku: PlanRecord;
  addonLines: CheckoutAddonLine[];
  effectivePromoCode: string | null;
  effectiveCheckoutCodeInput: string | null;
  telegramStarsAmount: number;
  invoiceSupported: boolean;
};

const PUBLIC_PLAN_ORDER: PricingTierCode[] = ['basic', 'plus', 'pro', 'max'];
const PLAN_ICON_MAP = {
  basic: Orbit,
  plus: Sparkles,
  pro: ShieldCheck,
  max: Zap,
} satisfies Record<PricingTierCode, typeof Orbit>;
const PLAN_ACCENT_MAP = {
  basic: 'text-neon-cyan border-neon-cyan/30',
  plus: 'text-matrix-green border-matrix-green/30',
  pro: 'text-neon-pink border-neon-pink/30',
  max: 'text-neon-purple border-neon-purple/30',
} satisfies Record<PricingTierCode, string>;
const PLAN_NAME_KEY_MAP = {
  basic: 'planNames.basic',
  plus: 'planNames.plus',
  pro: 'planNames.pro',
  max: 'planNames.max',
} satisfies Record<PricingTierCode, string>;
const CONNECTION_MODE_KEY_MAP: Record<string, string> = {
  standard: 'connectionModes.standard',
  stealth: 'connectionModes.stealth',
  manual_config: 'connectionModes.manualConfig',
  dedicated_ip: 'connectionModes.dedicatedIp',
  experimental: 'connectionModes.experimental',
};
const SERVER_POOL_KEY_MAP: Record<string, string> = {
  shared: 'serverPools.shared',
  shared_plus: 'serverPools.sharedPlus',
  premium_shared: 'serverPools.premiumShared',
  premium: 'serverPools.premium',
  exclusive: 'serverPools.exclusive',
};

function groupPlanFamilies(plans: PlanRecord[]): PlanFamily[] {
  const grouped = new Map<PricingTierCode, PlanFamily>();

  for (const plan of plans) {
    if (!PUBLIC_PLAN_ORDER.includes(plan.plan_code as PricingTierCode)) {
      continue;
    }

    if (!plan.is_active) {
      continue;
    }

    const code = plan.plan_code as PricingTierCode;
    const existing = grouped.get(code);

    if (!existing) {
      grouped.set(code, {
        code,
        displayName: plan.display_name,
        devicesIncluded: plan.devices_included,
        connectionModes: plan.connection_modes,
        serverPool: plan.server_pool,
        supportSla: plan.support_sla,
        dedicatedIpIncluded: plan.dedicated_ip.included,
        dedicatedIpEligible: plan.dedicated_ip.eligible,
        periods: [plan],
        sortOrder: plan.sort_order,
      });
      continue;
    }

    existing.periods.push(plan);
    existing.sortOrder = Math.min(existing.sortOrder, plan.sort_order);
  }

  return PUBLIC_PLAN_ORDER
    .map((code) => grouped.get(code))
    .filter((plan): plan is PlanFamily => Boolean(plan))
    .map((plan) => ({
      ...plan,
      periods: [...plan.periods].sort((left, right) => left.duration_days - right.duration_days),
    }));
}

function findPlanByUuid(
  planFamilies: PlanFamily[],
  uuid: string | null | undefined,
): { family: PlanFamily; period: PlanRecord } | null {
  if (!uuid) {
    return null;
  }

  for (const family of planFamilies) {
    const period = family.periods.find((candidate) => candidate.uuid === uuid);
    if (period) {
      return { family, period };
    }
  }

  return null;
}

function formatPeriodLabel(t: ReturnType<typeof useTranslations>, durationDays: number) {
  if (durationDays === 30) return t('periods.monthly');
  if (durationDays === 90) return t('periods.quarterly');
  if (durationDays === 180) return t('periods.semiAnnual');
  if (durationDays === 365) return t('periods.annual');
  return t('periods.custom', { days: durationDays });
}

function translateOrFallback(t: ReturnType<typeof useTranslations>, key: string, fallback: string) {
  const translated = t(key);
  return translated === key ? fallback : translated;
}

function formatPlanDisplayName(t: ReturnType<typeof useTranslations>, family: PlanFamily) {
  const translationKey = PLAN_NAME_KEY_MAP[family.code];
  return translateOrFallback(t, translationKey, family.displayName);
}

function formatConnectionModes(t: ReturnType<typeof useTranslations>, modes: string[]) {
  return modes
    .map((mode) => {
      const translationKey = CONNECTION_MODE_KEY_MAP[mode];
      return translationKey ? translateOrFallback(t, translationKey, mode) : mode;
    })
    .join(' · ');
}

function formatServerPools(t: ReturnType<typeof useTranslations>, pools: string[]) {
  return pools
    .map((pool) => {
      const translationKey = SERVER_POOL_KEY_MAP[pool];
      return translationKey ? translateOrFallback(t, translationKey, pool) : pool;
    })
    .join(' · ');
}

function formatTrafficLabel(t: ReturnType<typeof useTranslations>, label: string | null | undefined) {
  if (!label || label.toLowerCase() === 'unlimited') {
    return t('trafficUnlimited');
  }

  return label;
}

function extractTelegramStarsAmount(features: Record<string, unknown> | undefined) {
  if (!features) {
    return 0;
  }

  const direct = features.telegram_stars_amount;
  const nested = typeof features.telegram_stars === 'object' && features.telegram_stars !== null
    ? features.telegram_stars as Record<string, unknown>
    : undefined;
  const prices = typeof features.prices === 'object' && features.prices !== null
    ? features.prices as Record<string, unknown>
    : undefined;

  const candidates = [direct, nested?.amount, prices?.XTR];
  for (const candidate of candidates) {
    if (candidate === null || candidate === undefined || candidate === '') continue;
    const value = Number(candidate);
    if (Number.isFinite(value) && value > 0) {
      return Math.trunc(value);
    }
  }

  return 0;
}

async function waitForPaymentCompletion(paymentId: string) {
  for (let attempt = 0; attempt < 8; attempt += 1) {
    const { data } = await miniappApi.getPayment(paymentId);
    if (data.status === 'completed') {
      return 'completed' as const;
    }
    if (['failed', 'cancelled', 'expired', 'refunded'].includes(data.status)) {
      return data.status;
    }
    await new Promise((resolve) => setTimeout(resolve, 1250));
  }

  return 'pending' as const;
}

function normalizeCurrentEntitlements(snapshot: CurrentEntitlementsResponse | undefined) {
  const effective = (snapshot?.effective_entitlements ?? {}) as {
    device_limit?: number;
    display_traffic_label?: string;
    connection_modes?: string[];
    server_pool?: string[];
    support_sla?: string;
    dedicated_ip_count?: number;
  };

  return {
    deviceLimit: effective.device_limit ?? 0,
    trafficLabel: effective.display_traffic_label ?? null,
    connectionModes: effective.connection_modes ?? [],
    serverPool: effective.server_pool ?? [],
    supportSla: effective.support_sla ?? 'standard',
    dedicatedIpCount: effective.dedicated_ip_count ?? 0,
  };
}

function openPaymentUrl(
  paymentUrl: string,
  webApp: ReturnType<typeof useTelegramWebApp>['webApp'],
  onStatus?: (status: 'paid' | 'cancelled' | 'failed' | 'pending') => void,
) {
  try {
    if (
      (paymentUrl.includes('t.me/invoice/') || paymentUrl.includes('t.me/$'))
      && webApp?.openInvoice
    ) {
      webApp.openInvoice(paymentUrl, onStatus);
      return;
    }

    if (webApp?.openTelegramLink) {
      webApp.openTelegramLink(paymentUrl);
      return;
    }

    if (webApp?.openLink) {
      webApp.openLink(paymentUrl);
      return;
    }

    window.open(paymentUrl, '_blank');
  } catch {
    window.open(paymentUrl, '_blank');
  }
}

function QuoteBreakdown({
  t,
  locale,
  quote,
}: {
  t: ReturnType<typeof useTranslations>;
  locale: string;
  quote: CheckoutQuoteResponse;
}) {
  const entitlements = quote.entitlements_snapshot.effective_entitlements;

  return (
    <div className="space-y-4">
      <div className="grid gap-2 rounded-2xl border border-white/10 bg-black/35 p-4">
        {[
          { label: t('quote.basePrice'), value: quote.base_price },
          { label: t('quote.addonAmount'), value: quote.addon_amount },
          { label: t('quote.discount'), value: quote.discount_amount },
          { label: t('quote.walletAmount'), value: quote.wallet_amount },
          { label: t('quote.gatewayAmount'), value: quote.gateway_amount },
        ].map((row) => (
          <div key={row.label} className="flex items-center justify-between gap-4 text-sm font-mono text-white/72">
            <span>{row.label}</span>
            <span>{formatMoney(locale, row.value, 'USD')}</span>
          </div>
        ))}
        <div className="mt-2 flex items-center justify-between border-t border-white/10 pt-3 font-display text-lg uppercase tracking-[0.16em] text-white">
          <span>{t('quote.total')}</span>
          <div className="text-right">
            <span>{formatMoney(locale, quote.displayed_price, 'USD')}</span>
            <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.14em] text-white/42">
              {t('billingCurrencyNotice', { currency: 'USD' })}
            </p>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-white/45">
          {t('quote.entitlements')}
        </p>
        <div className="mt-3 grid gap-2 text-sm font-mono text-white/75">
          <div className="flex items-center justify-between gap-4">
            <span>{t('quote.devices')}</span>
            <span>{entitlements.device_limit}</span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span>{t('quote.traffic')}</span>
            <span>{formatTrafficLabel(t, entitlements.display_traffic_label)}</span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span>{t('quote.dedicatedIp')}</span>
            <span>{entitlements.dedicated_ip_count}</span>
          </div>
          <div className="flex items-start justify-between gap-4">
            <span>{t('quote.modes')}</span>
            <span className="max-w-[60%] text-right">
              {formatConnectionModes(t, entitlements.connection_modes) || t('quote.none')}
            </span>
          </div>
          <div className="flex items-start justify-between gap-4">
            <span>{t('quote.serverPool')}</span>
            <span className="max-w-[60%] text-right">
              {formatServerPools(t, entitlements.server_pool) || t('quote.none')}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function MiniAppPlansPage() {
  const t = useTranslations('MiniApp.plans');
  const locale = useLocale();
  const { haptic, hapticNotification, webApp } = useTelegramWebApp();
  const queryClient = useQueryClient();
  const startParam = webApp?.initDataUnsafe?.start_param ?? null;
  const checkoutCodesEnabled = STAGE1_CHECKOUT_CODES_UI_ENABLED;

  const [selectedPlanCodeOverride, setSelectedPlanCodeOverride] = useState<PricingTierCode | null>(null);
  const [selectedPeriodOverride, setSelectedPeriodOverride] = useState<number | null>(null);
  const [extraDeviceQty, setExtraDeviceQty] = useState(0);
  const [wantsDedicatedIp, setWantsDedicatedIp] = useState(false);
  const [dedicatedIpLocation, setDedicatedIpLocation] = useState('');
  const [codeInput, setCodeInput] = useState('');
  const [appliedCodeInput, setAppliedCodeInput] = useState<string | null>(null);
  const [appliedCodeType, setAppliedCodeType] = useState<string | null>(null);
  const [codeFeedback, setCodeFeedback] = useState<{
    tone: 'success' | 'warning' | 'error';
    message: string;
  } | null>(null);
  const [inviteCode, setInviteCode] = useState('');

  const offersQuery = useQuery({
    queryKey: ['miniapp-offers'],
    queryFn: async () => {
      const { data } = await miniappApi.getOffers();
      return data;
    },
  });
  const bootstrapQuery = useQuery({
    queryKey: ['miniapp-bootstrap', locale, startParam],
    queryFn: async () => {
      const { data } = await miniappApi.getBootstrap({
        locale,
        startParam,
      });
      return data;
    },
  });

  const plansData = offersQuery.data?.plans;
  const addonsData = offersQuery.data?.addons;
  const trialData = offersQuery.data?.trial;
  const currentEntitlements = offersQuery.data?.currentEntitlements;
  const plansLoading = offersQuery.isLoading;
  const rollout = bootstrapQuery.data?.rollout;
  const runtimeEnabled = rollout?.enabled !== false
    && rollout?.accessGranted !== false
    && rollout?.mode !== 'maintenance';
  const trialEnabled = runtimeEnabled
    && rollout?.trialEnabled !== false
    && rollout?.mode !== 'rollback';
  const checkoutEnabled = runtimeEnabled
    && rollout?.checkoutEnabled !== false
    && rollout?.mode !== 'rollback';
  const rolloutMessage = (() => {
    if (!rollout) return null;
    if (rollout.maintenanceMessage) return rollout.maintenanceMessage;
    if (rollout.mode === 'canary' && rollout.accessGranted === false) {
      return t('limitedRolloutDescription');
    }
    if (rollout.mode === 'rollback') {
      return t('rollbackDescription');
    }
    if (!runtimeEnabled) {
      return t('runtimeTemporarilyUnavailable');
    }
    if (!checkoutEnabled) {
      return t('checkoutTemporarilyUnavailable');
    }
    if (!trialEnabled) {
      return t('trialTemporarilyUnavailable');
    }
    return null;
  })();

  const groupedPlans = groupPlanFamilies(plansData ?? []);
  const currentMatch = findPlanByUuid(groupedPlans, currentEntitlements?.plan_uuid);
  const defaultFamily = currentMatch?.family ?? groupedPlans.find((plan) => plan.code === 'plus') ?? groupedPlans[0] ?? null;
  const selectedPlanCode = selectedPlanCodeOverride ?? defaultFamily?.code ?? null;
  const selectedFamily = groupedPlans.find((plan) => plan.code === selectedPlanCode) ?? null;
  const selectedPeriod =
    selectedPeriodOverride
    ?? (currentMatch?.family.code === selectedPlanCode ? currentMatch.period.duration_days : null)
    ?? selectedFamily?.periods.find((period) => period.duration_days === 365)?.duration_days
    ?? selectedFamily?.periods[0]?.duration_days
    ?? null;
  const selectedSku = selectedFamily?.periods.find((plan) => plan.duration_days === selectedPeriod) ?? null;
  const extraDeviceAddon = addonsData?.find((addon) => addon.code === 'extra_device');
  const dedicatedIpAddon = addonsData?.find((addon) => addon.code === 'dedicated_ip');
  const addonsEnabled = Boolean(extraDeviceAddon || dedicatedIpAddon);

  const isCurrentPlan = Boolean(selectedSku && currentEntitlements?.plan_uuid === selectedSku.uuid);
  const hasCurrentSubscription = currentEntitlements?.status === 'active';
  const isUpgradeFlow = Boolean(hasCurrentSubscription && selectedSku && !isCurrentPlan);
  const canAddExtraDevice = Boolean(
    selectedFamily
    && extraDeviceAddon
    && typeof extraDeviceAddon.max_quantity_by_plan[selectedFamily.code] === 'number',
  );
  const maxExtraDevices =
    (selectedFamily && extraDeviceAddon?.max_quantity_by_plan[selectedFamily.code]) || 0;

  const addonLines =
    addonsEnabled && !isUpgradeFlow
      ? [
          ...(extraDeviceQty > 0
            ? [{ code: 'extra_device', qty: extraDeviceQty }]
            : []),
          ...(wantsDedicatedIp
            ? [{
                code: 'dedicated_ip',
                qty: 1,
                location_code: dedicatedIpLocation.trim() || undefined,
              }]
            : []),
        ]
      : [];

  const flow: QuoteFlow = !selectedSku
    ? 'none'
    : isCurrentPlan
      ? addonLines.length > 0
        ? 'addons'
        : 'current'
      : hasCurrentSubscription
        ? 'upgrade'
        : 'checkout';

  const dedicatedIpReady = !addonsEnabled || !wantsDedicatedIp || dedicatedIpLocation.trim().length >= 2;
  const effectivePromoCode =
    checkoutCodesEnabled && flow !== 'checkout' && appliedCodeType === 'promo'
      ? appliedCodeInput
      : null;
  const effectiveCheckoutCodeInput =
    checkoutCodesEnabled && flow === 'checkout'
      ? appliedCodeInput
      : null;
  const unsupportedAppliedCodeMessage =
    appliedCodeInput && appliedCodeType
      ? getUnsupportedCheckoutCodeMessage({
          codeType: appliedCodeType as 'invite' | 'referral' | 'promo' | 'gift' | 'partner',
          flow: flow === 'none' || flow === 'current' ? 'checkout' : flow,
          partnerCodeEntryAllowed: false,
        })
      : null;
  const displayedCodeFeedback = unsupportedAppliedCodeMessage
    ? {
        tone: 'warning' as const,
        message: unsupportedAppliedCodeMessage,
      }
    : codeFeedback;

  const quoteQuery = useQuery({
    queryKey: [
      'miniapp-pricing-quote',
      flow,
      selectedSku?.uuid,
      extraDeviceQty,
      wantsDedicatedIp,
      dedicatedIpLocation,
      effectivePromoCode,
      effectiveCheckoutCodeInput,
    ],
    enabled: Boolean(selectedSku) && flow !== 'none' && flow !== 'current' && dedicatedIpReady && checkoutEnabled,
    queryFn: async () => {
      if (!selectedSku) {
        throw new Error('Missing selected plan');
      }
      if (flow === 'none' || flow === 'current') {
        throw new Error('Unsupported quote flow');
      }
      const { data } = await miniappApi.quoteCheckout({
        flow,
        plan_id: selectedSku.uuid,
        addons: addonLines,
        code_input: effectiveCheckoutCodeInput ?? undefined,
        promo_code: effectivePromoCode ?? undefined,
        use_wallet: 0,
        currency: 'USD',
      });
      return data;
    },
  });

  async function handleApplyCode() {
    if (!checkoutCodesEnabled) {
      setCodeFeedback({
        tone: 'warning',
        message: t('checkoutCodeDisabled'),
      });
      return;
    }

    if (!checkoutEnabled) {
      setCodeFeedback({
        tone: 'warning',
        message: rolloutMessage || t('checkoutTemporarilyUnavailable'),
      });
      return;
    }

    if (!codeInput.trim()) {
      setCodeFeedback({
        tone: 'error',
        message: t('checkoutCodeEmpty'),
      });
      return;
    }

    if (!selectedSku) {
      setCodeFeedback({
        tone: 'error',
        message: t('selectPlanToQuote'),
      });
      return;
    }

    try {
      const normalizedCode = codeInput.trim().toUpperCase();
      const resolutionResponse = await codesApi.resolve({
        code: normalizedCode,
        action_context: 'checkout',
        plan_id: selectedSku.uuid,
        amount: quoteQuery.data?.displayed_price ?? selectedSku.price_usd,
        channel: 'miniapp',
      });
      const resolution = resolutionResponse.data;

      if (!resolution.accepted) {
        setAppliedCodeInput(null);
        setAppliedCodeType(null);
        setCodeFeedback({
          tone: 'error',
          message: getGrowthCodeResolutionMessage(resolution),
        });
        return;
      }

      const unsupportedMessage = getUnsupportedCheckoutCodeMessage({
        codeType: resolution.code_type,
        flow: flow === 'none' || flow === 'current' ? 'checkout' : flow,
        partnerCodeEntryAllowed: false,
      });
      if (unsupportedMessage) {
        setAppliedCodeInput(null);
        setAppliedCodeType(null);
        setCodeFeedback({
          tone: 'warning',
          message: unsupportedMessage,
        });
        return;
      }

      setAppliedCodeInput(normalizedCode);
      setAppliedCodeType(resolution.code_type);
      setCodeInput(normalizedCode);
      setCodeFeedback({
        tone: 'success',
        message: resolution.code_type === 'referral'
          ? t('checkoutCodeAcceptedReferral')
          : t('checkoutCodeAccepted', { code: normalizedCode }),
      });
      hapticNotification('success');
      void queryClient.invalidateQueries({ queryKey: ['miniapp-pricing-quote'] });
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      setAppliedCodeInput(null);
      setAppliedCodeType(null);
      setCodeFeedback({
        tone: 'error',
        message: axiosError.response?.data?.detail || t('quoteError'),
      });
      hapticNotification('error');
    }
  }

  async function refreshMiniAppAccessState() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['miniapp-offers'] }),
      queryClient.invalidateQueries({ queryKey: ['miniapp-bootstrap'] }),
      queryClient.resetQueries({ queryKey: ['miniapp-config'], exact: true }),
      queryClient.invalidateQueries({ queryKey: ['usage'] }),
      queryClient.invalidateQueries({ queryKey: ['miniapp-profile-invites'] }),
    ]);
  }

  const activateTrialMutation = useMutation({
    mutationFn: async () => {
      const { data } = await miniappApi.activateTrial();
      return data;
    },
    onSuccess: async () => {
      hapticNotification('success');
      await refreshMiniAppAccessState();
      webApp?.showAlert(t('trialActivated'));
    },
    onError: (error: unknown) => {
      hapticNotification('error');
      const axiosError = error as { response?: { data?: { detail?: string } } };
      webApp?.showAlert(axiosError.response?.data?.detail || t('trialError'));
    },
  });

  const commitMutation = useMutation({
    mutationFn: async (payload: CommitCheckoutPayload): Promise<CheckoutCommitResponse> => {
      const canUseTelegramStarsCheckout =
        payload.flow === 'checkout'
        && payload.addonLines.length === 0
        && payload.telegramStarsAmount > 0
        && payload.invoiceSupported;

      const { data } = await miniappApi.commitCheckout({
        flow: payload.flow,
        plan_id: payload.selectedSku.uuid,
        addons: payload.addonLines,
        code_input: payload.effectiveCheckoutCodeInput ?? undefined,
        promo_code: payload.effectivePromoCode ?? undefined,
        use_wallet: 0,
        currency: canUseTelegramStarsCheckout ? 'XTR' : 'USD',
      });
      return data;
    },
    onSuccess: (data, payload) => {
      hapticNotification('success');
      queryClient.invalidateQueries({ queryKey: ['miniapp-offers'] });
      queryClient.invalidateQueries({ queryKey: ['miniapp-config'] });
      queryClient.invalidateQueries({ queryKey: ['usage'] });
      queryClient.invalidateQueries({ queryKey: ['payments-history'] });
      queryClient.invalidateQueries({ queryKey: ['miniapp-bootstrap'] });

      void emitMiniAppRuntimeEvent({
        event: 'miniapp_checkout_completed',
        page: 'plans',
        locale,
        path: `/${locale}/miniapp/plans`,
        checkoutFlow: payload.flow,
        paymentRail:
          payload.flow === 'checkout' && payload.addonLines.length === 0 && payload.telegramStarsAmount > 0 && payload.invoiceSupported
            ? 'telegram_stars_xtr'
            : 'generic_checkout',
        paymentStatus: data.status,
        subscriptionStatus: currentEntitlements?.status ?? 'none',
      });

      if (data.invoice?.payment_url) {
        openPaymentUrl(data.invoice.payment_url, webApp, async (status) => {
          if (status === 'paid') {
            if (data.invoice?.currency === 'XTR' && data.payment_id) {
              const finalStatus = await waitForPaymentCompletion(String(data.payment_id));
              await Promise.all([
                queryClient.invalidateQueries({ queryKey: ['miniapp-offers'] }),
                queryClient.invalidateQueries({ queryKey: ['miniapp-config'] }),
                queryClient.invalidateQueries({ queryKey: ['usage'] }),
                queryClient.invalidateQueries({ queryKey: ['payments-history'] }),
                queryClient.invalidateQueries({ queryKey: ['miniapp-bootstrap'] }),
              ]);

              void emitMiniAppRuntimeEvent({
                event: 'miniapp_payment_status_resolved',
                page: 'plans',
                locale,
                path: `/${locale}/miniapp/plans`,
                checkoutFlow: payload.flow,
                paymentRail: 'telegram_stars_xtr',
                paymentStatus: finalStatus,
                subscriptionStatus: currentEntitlements?.status ?? 'none',
              });

              if (finalStatus === 'completed') {
                webApp?.showAlert(t('paymentSuccess'));
              } else if (finalStatus === 'pending') {
                webApp?.showAlert(t('paymentPending'));
              } else {
                webApp?.showAlert(t('paymentFailed'));
              }
              return;
            }

            void emitMiniAppRuntimeEvent({
              event: 'miniapp_payment_status_resolved',
              page: 'plans',
              locale,
              path: `/${locale}/miniapp/plans`,
              checkoutFlow: payload.flow,
              paymentRail: data.invoice?.currency === 'XTR' ? 'telegram_stars_xtr' : 'generic_checkout',
              paymentStatus: 'paid',
              subscriptionStatus: currentEntitlements?.status ?? 'none',
            });
            webApp?.showAlert(t('paymentSuccess'));
            void refreshMiniAppAccessState();
          } else if (status === 'cancelled') {
            void emitMiniAppRuntimeEvent({
              event: 'miniapp_payment_status_resolved',
              page: 'plans',
              locale,
              path: `/${locale}/miniapp/plans`,
              checkoutFlow: payload.flow,
              paymentRail: data.invoice?.currency === 'XTR' ? 'telegram_stars_xtr' : 'generic_checkout',
              paymentStatus: 'cancelled',
              subscriptionStatus: currentEntitlements?.status ?? 'none',
            });
            webApp?.showAlert(t('paymentCancelled'));
          } else if (status === 'failed') {
            void emitMiniAppRuntimeEvent({
              event: 'miniapp_payment_status_resolved',
              page: 'plans',
              locale,
              path: `/${locale}/miniapp/plans`,
              checkoutFlow: payload.flow,
              paymentRail: data.invoice?.currency === 'XTR' ? 'telegram_stars_xtr' : 'generic_checkout',
              paymentStatus: 'failed',
              subscriptionStatus: currentEntitlements?.status ?? 'none',
            });
            webApp?.showAlert(t('paymentFailed'));
          } else {
            void emitMiniAppRuntimeEvent({
              event: 'miniapp_payment_status_resolved',
              page: 'plans',
              locale,
              path: `/${locale}/miniapp/plans`,
              checkoutFlow: payload.flow,
              paymentRail: data.invoice?.currency === 'XTR' ? 'telegram_stars_xtr' : 'generic_checkout',
              paymentStatus: 'pending',
              subscriptionStatus: currentEntitlements?.status ?? 'none',
            });
            webApp?.showAlert(t('paymentPending'));
          }
        });
        return;
      }

      webApp?.showAlert(
        data.status === 'completed' ? t('purchaseCompleted') : t('paymentPending'),
      );
    },
    onError: (error: unknown, payload) => {
      hapticNotification('error');
      const axiosError = error as { response?: { data?: { detail?: string } } };
      void emitMiniAppRuntimeEvent({
        event: 'miniapp_checkout_failed',
        page: 'plans',
        locale,
        path: `/${locale}/miniapp/plans`,
        checkoutFlow: payload.flow,
        paymentRail:
          payload.flow === 'checkout' && payload.addonLines.length === 0 && payload.telegramStarsAmount > 0 && payload.invoiceSupported
            ? 'telegram_stars_xtr'
            : 'generic_checkout',
        errorCode: axiosError.response?.data?.detail ?? 'checkout_commit_failed',
        subscriptionStatus: currentEntitlements?.status ?? 'none',
      });
      webApp?.showAlert(axiosError.response?.data?.detail || t('paymentError'));
    },
  });

  const redeemInviteMutation = useMutation({
    mutationFn: async (code: string) => {
      const { data } = await invitesApi.redeem({ code });
      return data;
    },
    onSuccess: async (data) => {
      hapticNotification('success');
      const reward = data.free_days
        ? t('inviteRewardDays', { count: data.free_days })
        : t('inviteRewardDefault');
      await refreshMiniAppAccessState();
      webApp?.showAlert(t('inviteRedeemed', { reward }));
      setInviteCode('');
    },
    onError: (error: unknown) => {
      hapticNotification('error');
      const axiosError = error as { response?: { data?: { detail?: string } } };
      webApp?.showAlert(axiosError.response?.data?.detail || t('inviteInvalid'));
    },
  });

  const trialEligible = Boolean(
    trialData?.is_eligible && currentEntitlements?.status !== 'trial',
  );
  const canActivateTrial = trialEligible && trialEnabled;
  const currentValues = normalizeCurrentEntitlements(currentEntitlements);
  const currentPlanDisplayName = currentEntitlements?.status === 'trial'
    ? t('trialLabel')
    : currentMatch
      ? formatPlanDisplayName(t, currentMatch.family)
      : currentEntitlements?.display_name || t('trialLabel');
  const cardBg = 'miniapp-card';
  const borderColor = 'border';

  const selectedPricePresentation = selectedSku ? getPricePresentation(locale, selectedSku) : null;
  const selectedPrice = selectedPricePresentation
    ? formatMoney(
        locale,
        selectedPricePresentation.billing.amount,
        selectedPricePresentation.billing.currency,
      )
    : null;
  const extraDevicePricePresentation = extraDeviceAddon
    ? getPricePresentation(locale, extraDeviceAddon)
    : null;
  const dedicatedIpPricePresentation = dedicatedIpAddon
    ? getPricePresentation(locale, dedicatedIpAddon)
    : null;
  const flowLabel = flow === 'addons'
    ? t('flow.addons')
    : flow === 'upgrade'
      ? t('flow.upgrade')
      : flow === 'checkout'
        ? t('flow.checkout')
        : flow === 'current'
          ? t('flow.current')
          : t('flow.none');
  const ctaLabel = flow === 'addons'
    ? t('actions.purchaseAddons')
    : flow === 'upgrade'
      ? t('actions.upgradeNow')
      : t('actions.openPayment');

  return (
    <div className="mx-auto max-w-screen-sm space-y-4">
      {rolloutMessage ? (
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-[1.5rem] border border-amber-500/30 bg-amber-500/10 p-4"
        >
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-200" />
            <div>
              <h3 className="font-display text-sm uppercase tracking-[0.14em] text-amber-100">
                {t('serviceMaintenanceTitle')}
              </h3>
              <p className="mt-2 text-sm font-mono text-amber-100/85">{rolloutMessage}</p>
            </div>
          </div>
        </motion.div>
      ) : null}

      {currentEntitlements?.status && currentEntitlements.status !== 'none' ? (
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          className={`${cardBg} ${borderColor} rounded-[1.5rem] border p-4`}
        >
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-white/45">
                {t('currentPlanTitle')}
              </p>
              <h2 className="mt-1 font-display text-xl uppercase tracking-[0.16em] text-neon-cyan">
                {currentPlanDisplayName}
              </h2>
              <p className="mt-1 text-sm font-mono text-white/60">
                {currentEntitlements.expires_at
                  ? t('currentPlanExpiry', { date: currentEntitlements.expires_at })
                  : t('currentPlanNoExpiry')}
              </p>
            </div>
            <div className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-white/55">
              {flowLabel}
            </div>
          </div>

          <div className="mt-4 grid gap-2 text-sm font-mono text-white/72">
            <div className="flex items-center justify-between gap-4">
              <span>{t('quote.devices')}</span>
              <span>{currentValues.deviceLimit}</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <span>{t('quote.traffic')}</span>
              <span>{formatTrafficLabel(t, currentValues.trafficLabel)}</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <span>{t('quote.dedicatedIp')}</span>
              <span>{currentValues.dedicatedIpCount}</span>
            </div>
          </div>
        </motion.div>
      ) : null}

      {trialEligible ? (
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          className={`${cardBg} ${borderColor} rounded-[1.5rem] border p-4`}
        >
          <div className="flex items-start gap-3">
            <Gift className="mt-0.5 h-6 w-6 shrink-0 text-neon-pink" />
            <div className="flex-1">
              <h3 className="font-display text-lg uppercase tracking-[0.14em]">
                {t('freeTrialTitle')}
              </h3>
              <p className="mt-2 text-sm font-mono leading-relaxed text-muted-foreground">
                {t('freeTrialDescription')}
              </p>
              <button
                type="button"
                onClick={() => activateTrialMutation.mutate()}
                disabled={activateTrialMutation.isPending || !canActivateTrial}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-neon-pink px-4 py-3 font-mono text-white transition-colors hover:bg-neon-pink/90 disabled:opacity-50"
              >
                {activateTrialMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {t('activating')}
                  </>
                ) : (
                  t('activateTrial')
                )}
              </button>
              {!canActivateTrial ? (
                <p className="mt-3 text-xs font-mono text-amber-200">
                  {rolloutMessage || t('trialTemporarilyUnavailable')}
                </p>
              ) : null}
            </div>
          </div>
        </motion.div>
      ) : null}

      <div className={`${cardBg} ${borderColor} rounded-[1.5rem] border p-4`}>
        <div className="mb-4">
          <h2 className="font-display text-lg uppercase tracking-[0.16em]">{t('availablePlans')}</h2>
          <p className="mt-1 text-sm font-mono text-muted-foreground">{t('catalogHint')}</p>
        </div>

        {plansLoading ? (
          <div className="flex h-44 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-neon-cyan" />
          </div>
        ) : groupedPlans.length > 0 ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              {groupedPlans.map((plan) => {
                const Icon = PLAN_ICON_MAP[plan.code];
                const accentClassName = PLAN_ACCENT_MAP[plan.code];
                const isSelected = selectedPlanCode === plan.code;

                return (
                  <button
                    key={plan.code}
                    type="button"
                    onClick={() => {
                      haptic('medium');
                      setSelectedPlanCodeOverride(plan.code);
                      setSelectedPeriodOverride(
                        plan.periods.find((period) => period.duration_days === 365)?.duration_days
                          ?? plan.periods[0]?.duration_days
                          ?? null,
                      );
                      setExtraDeviceQty(0);
                      setWantsDedicatedIp(false);
                      setDedicatedIpLocation('');
                    }}
                    className={`rounded-2xl border p-4 text-left transition-all ${
                      isSelected
                        ? 'border-neon-cyan bg-white/[0.06]'
                        : 'border-white/10 bg-black/25'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-display text-base uppercase tracking-[0.16em] text-white">
                          {formatPlanDisplayName(t, plan)}
                        </p>
                        <p className="mt-1 text-xs font-mono text-white/55">
                          {t('planDevices', { count: plan.devicesIncluded })}
                        </p>
                      </div>
                      <div className={`rounded-xl border p-2 ${accentClassName}`}>
                        <Icon className="h-4 w-4" />
                      </div>
                    </div>
                    <div className="mt-3 text-xs font-mono text-white/60">
                      {formatConnectionModes(t, plan.connectionModes)}
                    </div>
                  </button>
                );
              })}
            </div>

            {selectedFamily ? (
              <div className="space-y-3 rounded-2xl border border-white/10 bg-black/25 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-white/45">
                      {t('periodSelectorTitle')}
                    </p>
                    <p className="mt-1 text-sm font-mono text-white/60">
                      {formatPlanDisplayName(t, selectedFamily)} · {selectedPrice}
                    </p>
                  </div>
                  <span className="rounded-full border border-white/10 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-white/55">
                    {flowLabel}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  {selectedFamily.periods.map((period) => {
                    const isSelected = selectedPeriod === period.duration_days;
                    const periodPrice = getPricePresentation(locale, period);

                    return (
                      <button
                        key={period.uuid}
                        type="button"
                        onClick={() => {
                          haptic('light');
                          setSelectedPeriodOverride(period.duration_days);
                        }}
                        className={`rounded-xl border px-3 py-3 text-left transition-all ${
                          isSelected
                            ? 'border-neon-cyan bg-neon-cyan/10'
                            : 'border-white/10 bg-white/[0.03]'
                        }`}
                      >
                        <div className="font-display text-sm uppercase tracking-[0.14em] text-white">
                          {formatPeriodLabel(t, period.duration_days)}
                        </div>
                        <div className="mt-1 text-xs font-mono text-white/55">
                          {formatMoney(locale, periodPrice.billing.amount, periodPrice.billing.currency)}
                        </div>
                        {period.invite_bundle.count > 0 ? (
                          <div className="mt-2 text-[11px] font-mono text-matrix-green">
                            {t('periodInviteBonus', {
                              count: period.invite_bundle.count,
                              days: period.invite_bundle.friend_days,
                            })}
                          </div>
                        ) : null}
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : null}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-white/10 px-4 py-8 text-center">
            <AlertCircle className="mx-auto h-10 w-10 text-muted-foreground" />
            <p className="mt-3 text-sm font-mono text-muted-foreground">{t('noPlans')}</p>
          </div>
        )}
      </div>

      {addonsEnabled ? (
        <div className={`${cardBg} ${borderColor} rounded-[1.5rem] border p-4`}>
          <div className="mb-4">
            <h3 className="font-display text-lg uppercase tracking-[0.16em]">{t('addonsTitle')}</h3>
            <p className="mt-1 text-sm font-mono text-muted-foreground">{t('addonsDescription')}</p>
          </div>

          {isUpgradeFlow ? (
            <div className="rounded-xl border border-amber-500/25 bg-amber-500/10 px-4 py-3 text-sm font-mono text-amber-200">
              {t('addonsUpgradeLocked')}
            </div>
          ) : (
            <div className="space-y-4">
              {extraDeviceAddon ? (
                <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-display text-base uppercase tracking-[0.14em] text-white">
                        {t('extraDeviceTitle')}
                      </p>
                      <p className="mt-2 text-sm font-mono text-white/60">
                        {extraDevicePricePresentation
                          ? t('extraDevicePrice', {
                              price: formatMoney(
                                locale,
                                extraDevicePricePresentation.billing.amount,
                                extraDevicePricePresentation.billing.currency,
                              ),
                            })
                          : t('addonUnavailable')}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        disabled={extraDeviceQty <= 0}
                        onClick={() => setExtraDeviceQty((current) => Math.max(0, current - 1))}
                        className="rounded-lg border border-white/10 p-2 text-white/70 disabled:opacity-40"
                      >
                        <Minus className="h-4 w-4" />
                      </button>
                      <div className="min-w-10 text-center font-display text-lg text-white">{extraDeviceQty}</div>
                      <button
                        type="button"
                        disabled={!canAddExtraDevice || extraDeviceQty >= maxExtraDevices}
                        onClick={() => setExtraDeviceQty((current) => Math.min(maxExtraDevices, current + 1))}
                        className="rounded-lg border border-white/10 p-2 text-white/70 disabled:opacity-40"
                      >
                        <ChevronRight className="h-4 w-4 rotate-90" />
                      </button>
                    </div>
                  </div>
                  {canAddExtraDevice ? (
                    <p className="mt-3 text-xs font-mono text-white/55">
                      {t('extraDeviceLimit', { count: maxExtraDevices })}
                    </p>
                  ) : (
                    <p className="mt-3 text-xs font-mono text-white/45">{t('addonUnavailable')}</p>
                  )}
                </div>
              ) : null}

              {dedicatedIpAddon ? (
                <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
                  <label className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={wantsDedicatedIp}
                      onChange={(event) => setWantsDedicatedIp(event.target.checked)}
                      className="mt-1 h-4 w-4 rounded border-white/20 bg-black"
                    />
                    <div className="flex-1">
                      <p className="font-display text-base uppercase tracking-[0.14em] text-white">
                        {t('dedicatedIpTitle')}
                      </p>
                      <p className="mt-2 text-sm font-mono text-white/60">
                        {dedicatedIpPricePresentation
                          ? t('dedicatedIpPrice', {
                              price: formatMoney(
                                locale,
                                dedicatedIpPricePresentation.billing.amount,
                                dedicatedIpPricePresentation.billing.currency,
                              ),
                            })
                          : t('addonUnavailable')}
                      </p>
                    </div>
                  </label>

                  {wantsDedicatedIp ? (
                    <div className="mt-4 space-y-2">
                      <input
                        type="text"
                        value={dedicatedIpLocation}
                        onChange={(event) => setDedicatedIpLocation(event.target.value.toLowerCase())}
                        placeholder={t('dedicatedIpLocationPlaceholder')}
                        className="w-full rounded-xl border border-white/10 bg-black/40 px-3 py-3 font-mono text-sm text-white outline-none placeholder:text-white/35"
                      />
                      <p className="text-xs font-mono text-white/45">
                        {t('dedicatedIpLocationHint')}
                      </p>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          )}
        </div>
      ) : null}

      {checkoutCodesEnabled ? (
        <div className={`${cardBg} ${borderColor} rounded-[1.5rem] border p-4`}>
          <div className="mb-3 flex items-center gap-2">
            <Tag className="h-5 w-5 text-neon-cyan" />
            <h3 className="font-display text-sm uppercase tracking-[0.14em]">{t('havePromoCode')}</h3>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={codeInput}
              onChange={(event) => setCodeInput(event.target.value.toUpperCase())}
              placeholder={t('promoCodePlaceholder')}
              className="flex-1 rounded-xl border border-white/10 bg-black/30 px-3 py-3 font-mono text-sm text-white outline-none placeholder:text-white/35"
            />
            <button
              type="button"
              onClick={() => void handleApplyCode()}
              disabled={!checkoutEnabled}
              className="rounded-xl bg-neon-cyan px-4 py-3 font-mono text-sm text-black"
            >
              {t('apply')}
            </button>
          </div>
          {displayedCodeFeedback ? (
            <div
              className={`mt-3 flex items-center gap-2 text-xs font-mono ${
                displayedCodeFeedback.tone === 'error'
                  ? 'text-neon-pink'
                  : displayedCodeFeedback.tone === 'warning'
                    ? 'text-amber-200'
                    : 'text-neon-cyan'
              }`}
            >
              <Check className="h-3 w-3" />
              {displayedCodeFeedback.message}
            </div>
          ) : null}
        </div>
      ) : null}

      <div className={`${cardBg} ${borderColor} rounded-[1.5rem] border p-4`}>
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h3 className="font-display text-lg uppercase tracking-[0.16em]">{t('quoteTitle')}</h3>
            <p className="mt-1 text-sm font-mono text-muted-foreground">{t('quoteSubtitle')}</p>
          </div>
          <span className="rounded-full border border-white/10 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-white/55">
            {flowLabel}
          </span>
        </div>

        {!dedicatedIpReady ? (
          <div className="rounded-xl border border-amber-500/25 bg-amber-500/10 px-4 py-3 text-sm font-mono text-amber-200">
            {t('dedicatedIpLocationRequired')}
          </div>
        ) : flow === 'current' ? (
          <div className="rounded-xl border border-white/10 bg-black/25 px-4 py-4 text-sm font-mono text-white/70">
            {t('currentPlanSelected')}
          </div>
        ) : quoteQuery.isLoading ? (
          <div className="flex h-44 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-neon-cyan" />
          </div>
        ) : quoteQuery.error ? (
          <div className="rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
            {(quoteQuery.error as Error).message || t('quoteError')}
          </div>
        ) : quoteQuery.data ? (
          <QuoteBreakdown t={t} locale={locale} quote={quoteQuery.data} />
        ) : (
          <div className="rounded-xl border border-white/10 bg-black/25 px-4 py-4 text-sm font-mono text-white/55">
            {t('selectPlanToQuote')}
          </div>
        )}

        <button
          type="button"
          onClick={() => {
            if (!selectedSku || flow === 'none' || flow === 'current' || !checkoutEnabled) {
              return;
            }

            void emitMiniAppRuntimeEvent({
              event: 'miniapp_checkout_started',
              page: 'plans',
              locale,
              path: `/${locale}/miniapp/plans`,
              paymentRail: extractTelegramStarsAmount(
                selectedSku.features as Record<string, unknown> | undefined,
              )
                ? 'telegram_stars_xtr'
                : 'generic_checkout',
              subscriptionStatus: currentEntitlements?.status ?? 'none',
            });

            commitMutation.mutate({
              flow,
              selectedSku,
              addonLines,
              effectivePromoCode,
              effectiveCheckoutCodeInput,
              telegramStarsAmount: extractTelegramStarsAmount(
                selectedSku.features as Record<string, unknown> | undefined,
              ),
              invoiceSupported: Boolean(webApp?.openInvoice),
            });
          }}
          disabled={
            commitMutation.isPending
            || flow === 'none'
            || flow === 'current'
            || !selectedSku
            || !dedicatedIpReady
            || quoteQuery.isError
            || !checkoutEnabled
          }
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-neon-cyan px-4 py-3 font-mono text-black transition-colors hover:bg-neon-cyan/90 disabled:opacity-50"
        >
          {commitMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              {t('processing')}
            </>
          ) : (
            <>
              <Zap className="h-4 w-4" />
              {ctaLabel}
            </>
          )}
        </button>
        {!checkoutEnabled ? (
          <p className="mt-3 text-xs font-mono text-amber-200">
            {rolloutMessage || t('checkoutTemporarilyUnavailable')}
          </p>
        ) : null}
      </div>

      <div className={`${cardBg} ${borderColor} rounded-[1.5rem] border p-4`}>
        <div className="mb-3 flex items-center gap-2">
          <Users className="h-5 w-5 text-neon-purple" />
          <h3 className="font-display text-sm uppercase tracking-[0.14em]">{t('haveInviteCode')}</h3>
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={inviteCode}
            onChange={(event) => setInviteCode(event.target.value.toUpperCase())}
            placeholder={t('inviteCodePlaceholder')}
            className="flex-1 rounded-xl border border-white/10 bg-black/30 px-3 py-3 font-mono text-sm text-white outline-none placeholder:text-white/35"
          />
          <button
            type="button"
            onClick={() => redeemInviteMutation.mutate(inviteCode)}
            disabled={!inviteCode || redeemInviteMutation.isPending}
            className="rounded-xl bg-neon-purple px-4 py-3 font-mono text-sm text-white disabled:opacity-50"
          >
            {redeemInviteMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              t('redeem')
            )}
          </button>
        </div>
        <p className="mt-2 text-xs font-mono text-muted-foreground">{t('inviteCodeNote')}</p>
      </div>
    </div>
  );
}
