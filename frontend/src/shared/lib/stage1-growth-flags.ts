export type Stage1GrowthPublicEnv = {
  NEXT_PUBLIC_STAGE1_CHECKOUT_CODES_ENABLED?: string;
  NEXT_PUBLIC_STAGE1_GIFT_CODES_ENABLED?: string;
  NEXT_PUBLIC_STAGE1_GROWTH_EVIDENCE_APPROVED?: string;
  NEXT_PUBLIC_STAGE1_PROMO_CODES_ENABLED?: string;
  NEXT_PUBLIC_STAGE1_REFERRAL_ENABLED?: string;
};

export type Stage1GrowthUiState = {
  checkoutCodesUiEnabled: boolean;
  evidenceApproved: boolean;
  giftCodesUiEnabled: boolean;
  growthHubUiEnabled: boolean;
  promoCodesUiEnabled: boolean;
  referralUiEnabled: boolean;
};

function isPublicFlagEnabled(value: string | undefined): boolean {
  return value === 'true';
}

export function getStage1GrowthUiState(
  env?: Stage1GrowthPublicEnv,
): Stage1GrowthUiState {
  const source = env ?? (process.env as Stage1GrowthPublicEnv);
  const evidenceApproved = isPublicFlagEnabled(
    source.NEXT_PUBLIC_STAGE1_GROWTH_EVIDENCE_APPROVED,
  );
  const referralUiEnabled =
    evidenceApproved && isPublicFlagEnabled(source.NEXT_PUBLIC_STAGE1_REFERRAL_ENABLED);
  const promoCodesUiEnabled =
    evidenceApproved && isPublicFlagEnabled(source.NEXT_PUBLIC_STAGE1_PROMO_CODES_ENABLED);
  const giftCodesUiEnabled =
    evidenceApproved && isPublicFlagEnabled(source.NEXT_PUBLIC_STAGE1_GIFT_CODES_ENABLED);
  const checkoutCodesUiEnabled =
    evidenceApproved && isPublicFlagEnabled(source.NEXT_PUBLIC_STAGE1_CHECKOUT_CODES_ENABLED);

  return {
    checkoutCodesUiEnabled,
    evidenceApproved,
    giftCodesUiEnabled,
    growthHubUiEnabled: referralUiEnabled || promoCodesUiEnabled || giftCodesUiEnabled,
    promoCodesUiEnabled,
    referralUiEnabled,
  };
}

const STAGE1_GROWTH_UI_STATE = getStage1GrowthUiState();

export const STAGE1_GROWTH_EVIDENCE_APPROVED =
  STAGE1_GROWTH_UI_STATE.evidenceApproved;

export const STAGE1_REFERRAL_UI_ENABLED =
  STAGE1_GROWTH_UI_STATE.referralUiEnabled;

export const STAGE1_PROMO_CODES_UI_ENABLED =
  STAGE1_GROWTH_UI_STATE.promoCodesUiEnabled;

export const STAGE1_GIFT_CODES_UI_ENABLED =
  STAGE1_GROWTH_UI_STATE.giftCodesUiEnabled;

export const STAGE1_CHECKOUT_CODES_UI_ENABLED =
  STAGE1_GROWTH_UI_STATE.checkoutCodesUiEnabled;

export const STAGE1_GROWTH_HUB_UI_ENABLED =
  STAGE1_GROWTH_UI_STATE.growthHubUiEnabled;

export const STAGE1_GROWTH_UI_ENABLED = STAGE1_GROWTH_HUB_UI_ENABLED;

export function isStage1WalletWithdrawalUiEnabled(): boolean {
  return process.env.NEXT_PUBLIC_STAGE1_WALLET_WITHDRAWALS_ENABLED === 'true';
}
