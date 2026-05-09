import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  canOfficialWebSurfaceAccess,
  getOfficialWebSurfacePolicy,
  shouldRenderOfficialQuoteAdjustmentBanner,
} from '../surface-policy';
import {
  getStage1GrowthUiState,
  isStage1WalletWithdrawalUiEnabled,
} from '../stage1-growth-flags';

describe('official web surface policy', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('keeps S1 public growth code entry disabled while allowing invite redemption', () => {
    expect(canOfficialWebSurfaceAccess('invite_codes')).toBe(true);
    expect(canOfficialWebSurfaceAccess('promo_codes')).toBe(false);
    expect(canOfficialWebSurfaceAccess('partner_markup_visibility')).toBe(false);
    expect(canOfficialWebSurfaceAccess('workspace_operator_modules')).toBe(false);
  });

  it('requires the later evidence approval gate before any public growth UI is exposed', () => {
    expect(
      getStage1GrowthUiState({
        NEXT_PUBLIC_STAGE1_CHECKOUT_CODES_ENABLED: 'true',
        NEXT_PUBLIC_STAGE1_GIFT_CODES_ENABLED: 'true',
        NEXT_PUBLIC_STAGE1_PROMO_CODES_ENABLED: 'true',
        NEXT_PUBLIC_STAGE1_REFERRAL_ENABLED: 'true',
      }),
    ).toMatchObject({
      checkoutCodesUiEnabled: false,
      evidenceApproved: false,
      giftCodesUiEnabled: false,
      growthHubUiEnabled: false,
      promoCodesUiEnabled: false,
      referralUiEnabled: false,
    });

    expect(
      getStage1GrowthUiState({
        NEXT_PUBLIC_STAGE1_GROWTH_EVIDENCE_APPROVED: 'true',
        NEXT_PUBLIC_STAGE1_REFERRAL_ENABLED: 'true',
      }),
    ).toMatchObject({
      evidenceApproved: true,
      growthHubUiEnabled: true,
      referralUiEnabled: true,
    });
  });

  it('keeps referral and gift hub surfaces closed when only checkout codes are approved', () => {
    expect(
      getStage1GrowthUiState({
        NEXT_PUBLIC_STAGE1_CHECKOUT_CODES_ENABLED: 'true',
        NEXT_PUBLIC_STAGE1_GROWTH_EVIDENCE_APPROVED: 'true',
      }),
    ).toMatchObject({
      checkoutCodesUiEnabled: true,
      growthHubUiEnabled: false,
      referralUiEnabled: false,
    });
  });

  it('requires both checkout-code and promo evidence before official promo entry is exposed', () => {
    expect(
      getOfficialWebSurfacePolicy({
        NEXT_PUBLIC_STAGE1_CHECKOUT_CODES_ENABLED: 'true',
        NEXT_PUBLIC_STAGE1_GROWTH_EVIDENCE_APPROVED: 'true',
      }).promo_codes,
    ).toBe(false);

    expect(
      getOfficialWebSurfacePolicy({
        NEXT_PUBLIC_STAGE1_CHECKOUT_CODES_ENABLED: 'true',
        NEXT_PUBLIC_STAGE1_GROWTH_EVIDENCE_APPROVED: 'true',
        NEXT_PUBLIC_STAGE1_PROMO_CODES_ENABLED: 'true',
      }).promo_codes,
    ).toBe(true);
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

  it('keeps S1 customer wallet withdrawal UI disabled unless explicitly enabled', () => {
    vi.stubEnv('NEXT_PUBLIC_STAGE1_WALLET_WITHDRAWALS_ENABLED', '');
    expect(isStage1WalletWithdrawalUiEnabled()).toBe(false);

    vi.stubEnv('NEXT_PUBLIC_STAGE1_WALLET_WITHDRAWALS_ENABLED', 'true');
    expect(isStage1WalletWithdrawalUiEnabled()).toBe(true);
  });
});
