import type { ResolveGrowthCodeResponse } from '@/lib/api/codes';

export type CheckoutCodeFlow = 'checkout' | 'upgrade' | 'addons';
export type GrowthCodeResolutionMessageKey =
  | 'conflictPartnerCodeReferral'
  | 'conflictPartnerCode'
  | 'conflictPartnerBindingReferral'
  | 'conflictPartnerBinding'
  | 'conflictPromoPresent'
  | 'wrongContextInvite'
  | 'wrongContextGift'
  | 'wrongContextPartner'
  | 'wrongContextCheckout'
  | 'wrongContextRedeem'
  | 'notFound'
  | 'expired'
  | 'inactive'
  | 'exhausted'
  | 'alreadyUsed'
  | 'inviteSelfRedemption'
  | 'notEligibleForSku'
  | 'notEligibleForSurface'
  | 'blockedByRisk'
  | 'requiresAuth'
  | 'generic';

export type UnsupportedCheckoutCodeMessageKey =
  | 'partnerUnavailable'
  | 'upgradePromoOnly'
  | 'addonsPromoOnly';

export function getGrowthCodeResolutionMessageKey(
  resolution: Pick<
    ResolveGrowthCodeResponse,
    'code_type' | 'reject_reason' | 'conflict_code' | 'wrong_context_target' | 'result'
  >,
): GrowthCodeResolutionMessageKey {
  if (resolution.result === 'conflicted') {
    if (resolution.conflict_code === 'partner_code_present') {
      return resolution.code_type === 'referral'
        ? 'conflictPartnerCodeReferral'
        : 'conflictPartnerCode';
    }
    if (resolution.conflict_code === 'partner_binding_present') {
      return resolution.code_type === 'referral'
        ? 'conflictPartnerBindingReferral'
        : 'conflictPartnerBinding';
    }
    if (resolution.conflict_code === 'promo_present') {
      return 'conflictPromoPresent';
    }
  }

  if (resolution.reject_reason === 'code_wrong_context') {
    if (resolution.code_type === 'invite') {
      return 'wrongContextInvite';
    }
    if (resolution.code_type === 'gift') {
      return 'wrongContextGift';
    }
    if (resolution.code_type === 'partner') {
      return 'wrongContextPartner';
    }
    if (resolution.wrong_context_target === 'checkout') {
      return 'wrongContextCheckout';
    }
    return 'wrongContextRedeem';
  }

  if (resolution.reject_reason === 'code_not_found') {
    return 'notFound';
  }
  if (resolution.reject_reason === 'code_expired') {
    return 'expired';
  }
  if (resolution.reject_reason === 'code_not_active') {
    return 'inactive';
  }
  if (resolution.reject_reason === 'code_exhausted') {
    return 'exhausted';
  }
  if (
    resolution.reject_reason === 'code_already_redeemed'
    || resolution.reject_reason === 'gift_already_redeemed'
  ) {
    return 'alreadyUsed';
  }
  if (resolution.reject_reason === 'invite_self_redemption_blocked') {
    return 'inviteSelfRedemption';
  }
  if (resolution.reject_reason === 'code_not_eligible_for_sku') {
    return 'notEligibleForSku';
  }
  if (resolution.reject_reason === 'code_not_eligible_for_surface') {
    return 'notEligibleForSurface';
  }
  if (resolution.reject_reason === 'code_blocked_by_risk') {
    return 'blockedByRisk';
  }
  if (resolution.reject_reason === 'code_requires_auth') {
    return 'requiresAuth';
  }

  return 'generic';
}

export function getUnsupportedCheckoutCodeMessageKey({
  codeType,
  flow,
  partnerCodeEntryAllowed,
}: {
  codeType: ResolveGrowthCodeResponse['code_type'];
  flow: CheckoutCodeFlow;
  partnerCodeEntryAllowed: boolean;
}): UnsupportedCheckoutCodeMessageKey | null {
  if (codeType === 'partner' && !partnerCodeEntryAllowed) {
    return 'partnerUnavailable';
  }

  if (flow !== 'checkout' && codeType && codeType !== 'promo') {
    return flow === 'upgrade' ? 'upgradePromoOnly' : 'addonsPromoOnly';
  }

  return null;
}
