import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  extractReferralCode,
  normalizeReferralCode,
  REFERRAL_ATTRIBUTION_STORAGE_KEY,
  REFERRAL_ATTRIBUTION_TTL_MS,
} from './constants';
import {
  clearReferralAttribution,
  persistReferralAttribution,
  readReferralAttribution,
  replaceReferralAttribution,
} from './storage';

const NOW = Date.UTC(2026, 5, 19, 12, 0, 0);

function params(value: string): URLSearchParams {
  return new URLSearchParams(value);
}

describe('referral attribution query parsing', () => {
  it('normalizes public referral query aliases', () => {
    expect(normalizeReferralCode(' xsk2saqe ')).toBe('XSK2SAQE');
    expect(extractReferralCode('/en-EN/register', params('ref=xsk2saqe')))
      .toBe('XSK2SAQE');
    expect(extractReferralCode('/en-EN/register', params('referral_code=XSK2SAQE')))
      .toBe('XSK2SAQE');
  });

  it('accepts legacy code only on the referral landing', () => {
    expect(extractReferralCode('/en-EN/referral', params('code=XSK2SAQE')))
      .toBe('XSK2SAQE');
    expect(extractReferralCode('/en-EN/oauth/callback', params('code=XSK2SAQE')))
      .toBeNull();
  });

  it('rejects malformed codes', () => {
    expect(normalizeReferralCode('bad code')).toBeNull();
    expect(normalizeReferralCode('abc')).toBeNull();
  });
});

describe('referral attribution storage', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('stores the first touch with a 30-day TTL', () => {
    const stored = persistReferralAttribution({
      code: 'xsk2saqe',
      landingPath: '/en-EN/register',
      now: NOW,
      storage: localStorage,
    });

    expect(stored).toEqual({
      capturedAt: NOW,
      code: 'XSK2SAQE',
      expiresAt: NOW + REFERRAL_ATTRIBUTION_TTL_MS,
      landingPath: '/en-EN/register',
      version: 1,
    });
    expect(readReferralAttribution(localStorage, NOW + 1)).toEqual(stored);
  });

  it('does not overwrite an unexpired first touch', () => {
    const first = persistReferralAttribution({
      code: 'FIRST123',
      landingPath: '/en-EN/register',
      now: NOW,
      storage: localStorage,
    });
    const second = persistReferralAttribution({
      code: 'SECOND45',
      landingPath: '/en-EN/register',
      now: NOW + 1000,
      storage: localStorage,
    });

    expect(second).toEqual(first);
    expect(readReferralAttribution(localStorage, NOW + 1000)?.code).toBe('FIRST123');
  });

  it('replaces an expired touch', () => {
    persistReferralAttribution({
      code: 'FIRST123',
      landingPath: '/en-EN/register',
      now: NOW,
      storage: localStorage,
    });

    const replacement = persistReferralAttribution({
      code: 'SECOND45',
      landingPath: '/en-EN/register',
      now: NOW + REFERRAL_ATTRIBUTION_TTL_MS + 1,
      storage: localStorage,
    });

    expect(replacement?.code).toBe('SECOND45');
  });

  it('can converge localStorage to the server-side first touch', () => {
    persistReferralAttribution({
      code: 'SECOND45',
      landingPath: '/en-EN/register',
      now: NOW,
      storage: localStorage,
    });

    replaceReferralAttribution({
      code: 'FIRST123',
      landingPath: '/en-EN/register',
      now: NOW + 1000,
      storage: localStorage,
    });

    expect(readReferralAttribution(localStorage, NOW + 1000)?.code).toBe('FIRST123');
  });

  it('removes corrupt and consumed values', () => {
    localStorage.setItem(REFERRAL_ATTRIBUTION_STORAGE_KEY, '{not-json');
    const warning = vi.spyOn(console, 'warn').mockImplementation(() => undefined);

    expect(readReferralAttribution(localStorage, NOW)).toBeNull();
    expect(localStorage.getItem(REFERRAL_ATTRIBUTION_STORAGE_KEY)).toBeNull();
    expect(warning).toHaveBeenCalled();

    persistReferralAttribution({
      code: 'XSK2SAQE',
      landingPath: '/en-EN/register',
      now: NOW,
      storage: localStorage,
    });
    clearReferralAttribution(localStorage);
    expect(readReferralAttribution(localStorage, NOW)).toBeNull();
  });
});
