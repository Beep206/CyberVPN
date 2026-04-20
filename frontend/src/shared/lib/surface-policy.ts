export type OfficialWebSurfaceCapability =
  | 'invite_codes'
  | 'promo_codes'
  | 'partner_markup_visibility'
  | 'partner_code_entry'
  | 'workspace_operator_modules';

const OFFICIAL_WEB_SURFACE_POLICY: Record<OfficialWebSurfaceCapability, boolean> = {
  invite_codes: true,
  promo_codes: true,
  partner_markup_visibility: false,
  partner_code_entry: false,
  workspace_operator_modules: false,
};

export function canOfficialWebSurfaceAccess(
  capability: OfficialWebSurfaceCapability,
): boolean {
  return OFFICIAL_WEB_SURFACE_POLICY[capability];
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
