import { beforeEach, describe, expect, it } from 'vitest';
import {
  clearReferralAttribution,
  maskReferralCode,
  normalizeReferralCode,
  readReferralAttribution,
  REFERRAL_ATTRIBUTION_STORAGE_KEY,
  saveReferralAttribution,
} from '../storage';

describe('referral attribution storage v2', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('stores and reads a pending attribution snapshot', () => {
    saveReferralAttribution({
      attributionId: 'attr-1',
      capturedAt: '2026-06-19T00:00:00.000Z',
      code: 'CYBER42',
      expiresAt: '2099-06-19T00:00:00.000Z',
      maskedCode: 'CYBE****',
      sourceHost: 'my.cyber-vpn.net',
      sourcePath: '/ru-RU/register',
      version: 2,
    });

    expect(readReferralAttribution()).toMatchObject({
      attributionId: 'attr-1',
      code: 'CYBER42',
      maskedCode: 'CYBE****',
      version: 2,
    });
  });

  it('clears expired or malformed snapshots', () => {
    window.localStorage.setItem(REFERRAL_ATTRIBUTION_STORAGE_KEY, JSON.stringify({
      attributionId: 'attr-expired',
      capturedAt: '2026-06-01T00:00:00.000Z',
      code: 'OLD42',
      expiresAt: '2026-06-02T00:00:00.000Z',
      maskedCode: 'OLD4****',
      version: 2,
    }));
    expect(readReferralAttribution()).toBeNull();
    expect(window.localStorage.getItem(REFERRAL_ATTRIBUTION_STORAGE_KEY)).toBeNull();

    window.localStorage.setItem(REFERRAL_ATTRIBUTION_STORAGE_KEY, '{"version":1}');
    expect(readReferralAttribution()).toBeNull();
  });

  it('normalizes and masks referral codes', () => {
    expect(normalizeReferralCode(' cyber42 ')).toBe('CYBER42');
    expect(normalizeReferralCode('bad code')).toBeNull();
    expect(maskReferralCode('cyber42')).toBe('CYBE****');
    clearReferralAttribution();
    expect(readReferralAttribution()).toBeNull();
  });
});
