import type {
  GrowthCodeResolutionMessageKey,
  UnsupportedCheckoutCodeMessageKey,
} from '@/features/customer-growth/lib/checkout-code-resolution';

type TranslateValues = Record<string, string | number | Date>;
type Translate = (key: string, values?: TranslateValues) => string;

export type GrowthCodeBasketCopy = {
  title: string;
  description: string;
  inputLabel: string;
  placeholder: string;
  addCta: string;
  addingCta: string;
  empty: string;
  maxCount: string;
  duplicate: string;
  inputRequired: string;
  maxReached: string;
  missingPlan: string;
  contextChanged: string;
  removeCta: string;
  retryCta: string;
  degraded: string;
  pendingCheckout: string;
  primaryApplied: string;
  acceptedQueued: string;
  networkError: string;
  status: Record<'idle' | 'checking' | 'accepted' | 'rejected' | 'warning' | 'network_error', string>;
  codeTypes: Record<'invite' | 'referral' | 'promo' | 'gift' | 'partner' | 'unknown', string>;
  resolutionErrors: Record<GrowthCodeResolutionMessageKey, string>;
  unsupportedErrors: Record<UnsupportedCheckoutCodeMessageKey, string>;
};

export function buildGrowthCodeBasketCopy(t: Translate): GrowthCodeBasketCopy {
  return {
    title: t('growthCodeBasket.title'),
    description: t('growthCodeBasket.description'),
    inputLabel: t('growthCodeBasket.inputLabel'),
    placeholder: t('growthCodeBasket.placeholder'),
    addCta: t('growthCodeBasket.addCta'),
    addingCta: t('growthCodeBasket.addingCta'),
    empty: t('growthCodeBasket.empty'),
    maxCount: t('growthCodeBasket.maxCount', { count: 5 }),
    duplicate: t('growthCodeBasket.duplicate'),
    inputRequired: t('growthCodeBasket.inputRequired'),
    maxReached: t('growthCodeBasket.maxReached', { count: 5 }),
    missingPlan: t('growthCodeBasket.missingPlan'),
    contextChanged: t('growthCodeBasket.contextChanged'),
    removeCta: t('growthCodeBasket.removeCta'),
    retryCta: t('growthCodeBasket.retryCta'),
    degraded: t('growthCodeBasket.degraded'),
    pendingCheckout: t('growthCodeBasket.pendingCheckout'),
    primaryApplied: t('growthCodeBasket.primaryApplied'),
    acceptedQueued: t('growthCodeBasket.acceptedQueued'),
    networkError: t('growthCodeBasket.networkError'),
    status: {
      idle: t('growthCodeBasket.status.idle'),
      checking: t('growthCodeBasket.status.checking'),
      accepted: t('growthCodeBasket.status.accepted'),
      rejected: t('growthCodeBasket.status.rejected'),
      warning: t('growthCodeBasket.status.warning'),
      network_error: t('growthCodeBasket.status.networkError'),
    },
    codeTypes: {
      invite: t('growthCodeBasket.codeTypes.invite'),
      referral: t('growthCodeBasket.codeTypes.referral'),
      promo: t('growthCodeBasket.codeTypes.promo'),
      gift: t('growthCodeBasket.codeTypes.gift'),
      partner: t('growthCodeBasket.codeTypes.partner'),
      unknown: t('growthCodeBasket.codeTypes.unknown'),
    },
    resolutionErrors: {
      conflictPartnerCodeReferral: t('growthCodeBasket.errors.conflictPartnerCodeReferral'),
      conflictPartnerCode: t('growthCodeBasket.errors.conflictPartnerCode'),
      conflictPartnerBindingReferral: t('growthCodeBasket.errors.conflictPartnerBindingReferral'),
      conflictPartnerBinding: t('growthCodeBasket.errors.conflictPartnerBinding'),
      conflictPromoPresent: t('growthCodeBasket.errors.conflictPromoPresent'),
      wrongContextInvite: t('growthCodeBasket.errors.wrongContextInvite'),
      wrongContextGift: t('growthCodeBasket.errors.wrongContextGift'),
      wrongContextPartner: t('growthCodeBasket.errors.wrongContextPartner'),
      wrongContextCheckout: t('growthCodeBasket.errors.wrongContextCheckout'),
      wrongContextRedeem: t('growthCodeBasket.errors.wrongContextRedeem'),
      notFound: t('growthCodeBasket.errors.notFound'),
      expired: t('growthCodeBasket.errors.expired'),
      inactive: t('growthCodeBasket.errors.inactive'),
      exhausted: t('growthCodeBasket.errors.exhausted'),
      alreadyUsed: t('growthCodeBasket.errors.alreadyUsed'),
      inviteSelfRedemption: t('growthCodeBasket.errors.inviteSelfRedemption'),
      notEligibleForSku: t('growthCodeBasket.errors.notEligibleForSku'),
      notEligibleForSurface: t('growthCodeBasket.errors.notEligibleForSurface'),
      blockedByRisk: t('growthCodeBasket.errors.blockedByRisk'),
      requiresAuth: t('growthCodeBasket.errors.requiresAuth'),
      generic: t('growthCodeBasket.errors.generic'),
    },
    unsupportedErrors: {
      partnerUnavailable: t('growthCodeBasket.unsupported.partnerUnavailable'),
      upgradePromoOnly: t('growthCodeBasket.unsupported.upgradePromoOnly'),
      addonsPromoOnly: t('growthCodeBasket.unsupported.addonsPromoOnly'),
    },
  };
}
