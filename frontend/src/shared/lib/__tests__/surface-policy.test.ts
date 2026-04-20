import { describe, expect, it } from 'vitest';
import {
  canOfficialWebSurfaceAccess,
  shouldRenderOfficialQuoteAdjustmentBanner,
} from '../surface-policy';

describe('official web surface policy', () => {
  it('keeps promo and invite flows available while blocking partner markup visibility', () => {
    expect(canOfficialWebSurfaceAccess('invite_codes')).toBe(true);
    expect(canOfficialWebSurfaceAccess('promo_codes')).toBe(true);
    expect(canOfficialWebSurfaceAccess('partner_markup_visibility')).toBe(false);
    expect(canOfficialWebSurfaceAccess('workspace_operator_modules')).toBe(false);
  });

  it('ignores partner markup-only quote adjustments on the official surface', () => {
    expect(
      shouldRenderOfficialQuoteAdjustmentBanner({
        discountAmount: 0,
        partnerMarkup: 4.5,
      }),
    ).toBe(false);

    expect(
      shouldRenderOfficialQuoteAdjustmentBanner({
        discountAmount: 5,
        partnerMarkup: 0,
      }),
    ).toBe(true);
  });
});
