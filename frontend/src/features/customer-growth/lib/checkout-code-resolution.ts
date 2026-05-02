import type { ResolveGrowthCodeResponse } from '@/lib/api/codes';

export type CheckoutCodeFlow = 'checkout' | 'upgrade' | 'addons';

export function getGrowthCodeResolutionMessage(
  resolution: Pick<
    ResolveGrowthCodeResponse,
    'code_type' | 'reject_reason' | 'conflict_code' | 'wrong_context_target' | 'result'
  >,
): string {
  if (resolution.result === 'conflicted') {
    if (resolution.conflict_code === 'partner_code_present') {
      return resolution.code_type === 'referral'
        ? 'Referral discounts cannot be combined with a partner code.'
        : 'This code cannot be combined with a partner code.';
    }
    if (resolution.conflict_code === 'partner_binding_present') {
      return resolution.code_type === 'referral'
        ? 'Referral discounts cannot be combined with active partner attribution.'
        : 'This code cannot be combined with active partner attribution.';
    }
    if (resolution.conflict_code === 'promo_present') {
      return 'Partner codes cannot be combined with another discount code.';
    }
  }

  if (resolution.reject_reason === 'code_wrong_context') {
    if (resolution.code_type === 'invite') {
      return 'Invite codes redeem outside checkout. Open the rewards hub instead.';
    }
    if (resolution.code_type === 'gift') {
      return 'Gift codes redeem outside checkout. Open the rewards hub instead.';
    }
    if (resolution.code_type === 'partner') {
      return 'Partner codes can only be used in partner-enabled checkout flows.';
    }
    if (resolution.wrong_context_target === 'checkout') {
      return 'This code must be applied in checkout.';
    }
    return 'This code must be redeemed outside checkout.';
  }

  if (resolution.reject_reason === 'code_not_found') {
    return 'Code not found.';
  }
  if (resolution.reject_reason === 'code_expired') {
    return 'Code expired.';
  }
  if (resolution.reject_reason === 'code_not_active') {
    return 'Code is inactive.';
  }
  if (resolution.reject_reason === 'code_exhausted') {
    return 'Code usage limit reached.';
  }
  if (
    resolution.reject_reason === 'code_already_redeemed'
    || resolution.reject_reason === 'gift_already_redeemed'
  ) {
    return 'Code has already been used.';
  }
  if (resolution.reject_reason === 'invite_self_redemption_blocked') {
    return 'You cannot redeem your own invite code.';
  }
  if (resolution.reject_reason === 'code_not_eligible_for_sku') {
    return 'This code does not apply to the selected checkout basket.';
  }
  if (resolution.reject_reason === 'code_not_eligible_for_surface') {
    return 'This code is not available on the current surface.';
  }
  if (resolution.reject_reason === 'code_blocked_by_risk') {
    return 'This code is blocked by risk policy.';
  }
  if (resolution.reject_reason === 'code_requires_auth') {
    return 'Sign in first to use this code.';
  }

  return 'Code could not be applied.';
}

export function getUnsupportedCheckoutCodeMessage({
  codeType,
  flow,
  partnerCodeEntryAllowed,
}: {
  codeType: ResolveGrowthCodeResponse['code_type'];
  flow: CheckoutCodeFlow;
  partnerCodeEntryAllowed: boolean;
}): string | null {
  if (codeType === 'partner' && !partnerCodeEntryAllowed) {
    return 'Partner codes are not available on this checkout surface.';
  }

  if (flow !== 'checkout' && codeType && codeType !== 'promo') {
    return flow === 'upgrade'
      ? 'Only promo codes can be used during subscription upgrades right now.'
      : 'Only promo codes can be used for add-ons right now.';
  }

  return null;
}
