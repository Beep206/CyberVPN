import { render, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PartnerAttributionProvider } from '../provider';
import {
  PARTNER_ATTRIBUTION_STORAGE_KEY,
  savePartnerAttribution,
} from '../storage';

const partnerAttributionApiMock = vi.hoisted(() => ({
  claim: vi.fn(),
  consumeTransfer: vi.fn(),
}));

const authMock = vi.hoisted(() => ({
  pathname: '/en-EN/dashboard',
  state: {
    isAuthenticated: false,
    user: null as { id: string } | null,
  },
}));

vi.mock('@/lib/api/partner-attribution', () => ({
  partnerAttributionApi: partnerAttributionApiMock,
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

describe('PartnerAttributionProvider', () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    authMock.pathname = '/en-EN/dashboard';
    authMock.state = {
      isAuthenticated: false,
      user: null,
    };
    partnerAttributionApiMock.claim.mockResolvedValue({
      data: { status: 'no_pending' },
    });
    partnerAttributionApiMock.consumeTransfer.mockResolvedValue({
      data: {
        attribution_id: 'partner-attr-1',
        captured_at: '2026-06-22T10:00:00.000Z',
        expires_at: '2099-06-22T10:00:00.000Z',
        masked_code: 'PART****',
      },
    });
    vi.spyOn(window.history, 'replaceState').mockImplementation((_state, _title, url) => {
      if (typeof url === 'string') {
        applyBrowserPath(url);
      }
    });
    setBrowserPath('/en-EN/dashboard');
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it('does not claim after login when no pending partner attribution exists locally', async () => {
    authMock.state = {
      isAuthenticated: true,
      user: { id: 'user-1' },
    };

    render(<PartnerAttributionProvider />);

    await Promise.resolve();
    expect(partnerAttributionApiMock.claim).not.toHaveBeenCalled();
  });

  it('claims a pending partner attribution after login and clears local state on terminal success', async () => {
    savePartnerAttribution({
      attributionId: 'partner-attr-claim',
      capturedAt: '2026-06-22T10:00:00.000Z',
      expiresAt: '2099-06-22T10:00:00.000Z',
      maskedCode: 'PART****',
      sourceHost: 'localhost:3000',
      sourcePath: '/en-EN/register',
      version: 1,
    });
    authMock.state = {
      isAuthenticated: true,
      user: { id: 'user-1' },
    };
    partnerAttributionApiMock.claim.mockResolvedValue({
      data: { status: 'claimed' },
    });

    render(<PartnerAttributionProvider />);

    await waitFor(() => {
      expect(partnerAttributionApiMock.claim).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(window.localStorage.getItem(PARTNER_ATTRIBUTION_STORAGE_KEY)).toBeNull();
    });
  });

  it('claims a cookie-backed transfer after login when local storage is blocked', async () => {
    const localStorageSpy = vi.spyOn(window, 'localStorage', 'get').mockImplementation(() => {
      throw new Error('local storage blocked');
    });
    authMock.state = {
      isAuthenticated: true,
      user: { id: 'user-1' },
    };
    partnerAttributionApiMock.claim.mockResolvedValue({
      data: { status: 'claimed' },
    });
    setBrowserPath('/en-EN/register?pat=transfer-token-1');

    render(<PartnerAttributionProvider />);

    await waitFor(() => {
      expect(partnerAttributionApiMock.consumeTransfer).toHaveBeenCalledWith({
        transfer_token: 'transfer-token-1',
      });
    });
    await waitFor(() => {
      expect(partnerAttributionApiMock.claim).toHaveBeenCalledTimes(1);
    });
    expect(localStorageSpy).toHaveBeenCalled();
  });
});
