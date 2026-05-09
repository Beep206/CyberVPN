import {
  getStage1GrowthUiState,
  type Stage1GrowthPublicEnv,
} from './stage1-growth-flags';

export type OfficialWebSurfaceCapability =
  | 'invite_codes'
  | 'promo_codes'
  | 'partner_markup_visibility'
  | 'partner_code_entry'
  | 'workspace_operator_modules';

export function getOfficialWebSurfacePolicy(
  env?: Stage1GrowthPublicEnv,
): Record<OfficialWebSurfaceCapability, boolean> {
  const growthState = getStage1GrowthUiState(env);

  return {
    invite_codes: true,
    promo_codes:
      growthState.checkoutCodesUiEnabled && growthState.promoCodesUiEnabled,
    partner_markup_visibility: false,
    partner_code_entry: false,
    workspace_operator_modules: false,
  };
}

export function canOfficialWebSurfaceAccess(
  capability: OfficialWebSurfaceCapability,
  env?: Stage1GrowthPublicEnv,
): boolean {
  return getOfficialWebSurfacePolicy(env)[capability];
}

export function shouldRenderOfficialQuoteAdjustmentBanner(input: {
  discountAmount: number;
  partnerMarkup: number;
}): boolean {
  return input.discountAmount > 0
    || (
      canOfficialWebSurfaceAccess('partner_markup_visibility')
      && input.partnerMarkup !== 0
    );
}
