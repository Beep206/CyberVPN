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

  it('enables S2 public growth surfaces by default while keeping partner modules closed', () => {
    expect(canOfficialWebSurfaceAccess('invite_codes')).toBe(true);
    expect(canOfficialWebSurfaceAccess('promo_codes')).toBe(true);
    expect(canOfficialWebSurfaceAccess('partner_markup_visibility')).toBe(false);
    expect(canOfficialWebSurfaceAccess('workspace_operator_modules')).toBe(false);
  });

  it('allows runtime env flags to explicitly disable public growth UI', () => {
    expect(
      getStage1GrowthUiState({
        NEXT_PUBLIC_STAGE1_GROWTH_EVIDENCE_APPROVED: 'false',
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
      }),
    ).toMatchObject({
      evidenceApproved: true,
      checkoutCodesUiEnabled: true,
      giftCodesUiEnabled: true,
      growthHubUiEnabled: true,
      promoCodesUiEnabled: true,
      referralUiEnabled: true,
    });
  });

  it('keeps referral and gift hub surfaces closed when explicitly disabled', () => {
    expect(
      getStage1GrowthUiState({
        NEXT_PUBLIC_STAGE1_GROWTH_EVIDENCE_APPROVED: 'true',
        NEXT_PUBLIC_STAGE1_GIFT_CODES_ENABLED: 'false',
        NEXT_PUBLIC_STAGE1_PROMO_CODES_ENABLED: 'false',
        NEXT_PUBLIC_STAGE1_REFERRAL_ENABLED: 'false',
      }),
    ).toMatchObject({
      checkoutCodesUiEnabled: true,
      growthHubUiEnabled: false,
      referralUiEnabled: false,
    });
  });

  it('requires checkout-code and promo capabilities to stay enabled before official promo entry is exposed', () => {
    expect(
      getOfficialWebSurfacePolicy({
        NEXT_PUBLIC_STAGE1_GROWTH_EVIDENCE_APPROVED: 'true',
        NEXT_PUBLIC_STAGE1_CHECKOUT_CODES_ENABLED: 'false',
      }).promo_codes,
    ).toBe(false);

    expect(
      getOfficialWebSurfacePolicy({
        NEXT_PUBLIC_STAGE1_CHECKOUT_CODES_ENABLED: 'true',
        NEXT_PUBLIC_STAGE1_GROWTH_EVIDENCE_APPROVED: 'true',
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
