import { render, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ReferralAttributionProvider } from '../provider';
import {
  normalizeReferralCode,
  readReferralAttribution,
  REFERRAL_ATTRIBUTION_STORAGE_KEY,
  saveReferralAttribution,
} from '../storage';

const referralApiMock = vi.hoisted(() => ({
  captureAttribution: vi.fn(),
  claimAttribution: vi.fn(),
}));

const authMock = vi.hoisted(() => ({
  pathname: '/en-EN/register',
  state: {
    isAuthenticated: false,
    user: null as { id: string } | null,
  },
}));

vi.mock('@/lib/api/referral', () => ({
  referralApi: referralApiMock,
}));

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: <T,>(selector: (state: typeof authMock.state) => T): T =>
    selector(authMock.state),
}));

vi.mock('next/navigation', () => ({
  usePathname: () => authMock.pathname,
}));

function applyBrowserPath(path: string) {
  const url = new URL(path, window.location.origin || 'http://localhost:3000');
  Object.assign(window.location, {
    hash: url.hash,
    host: url.host,
    hostname: url.hostname,
    href: url.href,
    origin: url.origin,
    pathname: url.pathname,
    port: url.port,
    protocol: url.protocol,
    search: url.search,
  });
}

function setBrowserPath(path: string) {
  applyBrowserPath(path);
}

describe('ReferralAttributionProvider', () => {
  beforeEach(() => {
    window.localStorage.clear();
    authMock.pathname = '/en-EN/register';
    authMock.state = {
      isAuthenticated: false,
      user: null,
    };
    referralApiMock.captureAttribution.mockResolvedValue({
      data: {
        attribution_id: 'attr-1',
        captured_at: '2026-06-22T10:00:00.000Z',
        expires_at: '2099-06-22T10:00:00.000Z',
        masked_code: 'CYBE****',
      },
    });
    referralApiMock.claimAttribution.mockResolvedValue({
      data: { status: 'no_pending' },
    });
    vi.spyOn(window.history, 'replaceState').mockImplementation((_state, _title, url) => {
      if (typeof url === 'string') {
        applyBrowserPath(url);
      }
    });
    setBrowserPath('/en-EN/register');
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  it('captures a referral query into backend attribution and local pending state', async () => {
    const longClickId = 'x'.repeat(220);
    setBrowserPath(
      `/en-EN/register?ref=cyber42&utm_source=affiliate&utm_campaign=summer&gclid=${longClickId}`,
    );
    expect(window.location.search).toContain('ref=cyber42');
    expect(normalizeReferralCode(new URLSearchParams(window.location.search).get('ref'))).toBe('CYBER42');
    expect(readReferralAttribution()).toBeNull();

    render(<ReferralAttributionProvider />);

    await waitFor(() => {
      expect(referralApiMock.captureAttribution).toHaveBeenCalledTimes(1);
    });
    expect(referralApiMock.captureAttribution).toHaveBeenCalledWith({
      referral_code: 'CYBER42',
      source_host: 'localhost:3000',
      source_path: '/en-EN/register',
      campaign_params: {
        gclid: longClickId.slice(0, 160),
        utm_campaign: 'summer',
        utm_source: 'affiliate',
      },
    });

    await waitFor(() => {
      expect(readReferralAttribution()).toMatchObject({
        attributionId: 'attr-1',
        code: 'CYBER42',
        maskedCode: 'CYBE****',
        sourceHost: 'localhost:3000',
        sourcePath: '/en-EN/register',
      });
    });
    expect(new URL(window.location.href).searchParams.has('ref')).toBe(false);
    expect(new URL(window.location.href).searchParams.get('utm_source')).toBe('affiliate');
    expect(referralApiMock.claimAttribution).not.toHaveBeenCalled();
  });

  it('does not replace an existing pending referral and strips only referral query keys', async () => {
    saveReferralAttribution({
      attributionId: 'attr-existing',
      capturedAt: '2026-06-20T10:00:00.000Z',
      code: 'KEEP42',
      expiresAt: '2099-06-20T10:00:00.000Z',
      maskedCode: 'KEEP****',
      sourceHost: 'localhost:3000',
      sourcePath: '/en-EN/pricing',
      version: 2,
    });
    setBrowserPath('/en-EN/pricing?ref=new42&code=other42&utm_source=affiliate');

    render(<ReferralAttributionProvider />);

    await waitFor(() => {
      expect(new URL(window.location.href).searchParams.has('ref')).toBe(false);
    });
    expect(new URL(window.location.href).searchParams.get('code')).toBe('other42');
    expect(referralApiMock.captureAttribution).not.toHaveBeenCalled();
    expect(readReferralAttribution()).toMatchObject({
      attributionId: 'attr-existing',
      code: 'KEEP42',
    });
  });

  it('does not treat generic growth code query values as referral attribution', async () => {
    setBrowserPath('/en-EN/register?code=promo42&utm_source=campaign');

    render(<ReferralAttributionProvider />);

    await waitFor(() => {
      expect(referralApiMock.captureAttribution).not.toHaveBeenCalled();
    });
    expect(new URL(window.location.href).searchParams.get('code')).toBe('promo42');
    expect(readReferralAttribution()).toBeNull();
  });

  it('claims a pending referral after login and clears local state on terminal success', async () => {
    saveReferralAttribution({
      attributionId: 'attr-claim',
      capturedAt: '2026-06-21T10:00:00.000Z',
      code: 'CLAIM42',
      expiresAt: '2099-06-21T10:00:00.000Z',
      maskedCode: 'CLAI****',
      sourceHost: 'localhost:3000',
      sourcePath: '/en-EN/register',
      version: 2,
    });
    authMock.pathname = '/en-EN/dashboard';
    authMock.state = {
      isAuthenticated: true,
      user: { id: 'user-1' },
    };
    referralApiMock.claimAttribution.mockResolvedValue({
      data: { status: 'claimed' },
    });
    setBrowserPath('/en-EN/dashboard');

    render(<ReferralAttributionProvider />);

    await waitFor(() => {
      expect(referralApiMock.claimAttribution).toHaveBeenCalledWith({
        fallback_referral_code: 'CLAIM42',
      });
    });
    await waitFor(() => {
      expect(window.localStorage.getItem(REFERRAL_ATTRIBUTION_STORAGE_KEY)).toBeNull();
    });
  });

  it('does not claim after login when no pending referral exists locally', async () => {
    authMock.pathname = '/en-EN/dashboard';
    authMock.state = {
      isAuthenticated: true,
      user: { id: 'user-1' },
    };
    setBrowserPath('/en-EN/dashboard');

    render(<ReferralAttributionProvider />);

    await Promise.resolve();
    expect(referralApiMock.claimAttribution).not.toHaveBeenCalled();
  });

  it('claims a cookie-backed referral capture after login when local storage is blocked', async () => {
    const localStorageSpy = vi.spyOn(window, 'localStorage', 'get').mockImplementation(() => {
      throw new Error('local storage blocked');
    });
    authMock.pathname = '/en-EN/register';
    authMock.state = {
      isAuthenticated: true,
      user: { id: 'user-1' },
    };
    referralApiMock.claimAttribution.mockResolvedValue({
      data: { status: 'claimed' },
    });
    setBrowserPath('/en-EN/register?ref=cyber42&utm_source=affiliate');

    render(<ReferralAttributionProvider />);

    await waitFor(() => {
      expect(referralApiMock.captureAttribution).toHaveBeenCalledWith({
        referral_code: 'CYBER42',
        source_host: 'localhost:3000',
        source_path: '/en-EN/register',
        campaign_params: {
          utm_source: 'affiliate',
        },
      });
    });
    await waitFor(() => {
      expect(referralApiMock.claimAttribution).toHaveBeenCalledWith({
        fallback_referral_code: 'CYBER42',
      });
    });
    expect(localStorageSpy).toHaveBeenCalled();
  });
});
