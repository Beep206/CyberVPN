import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { User } from '@/lib/api/auth';
import { useAuthStore } from './auth-store';

const mocks = vi.hoisted(() => ({
  authLogout: vi.fn(),
  authLogin: vi.fn(),
  authSession: vi.fn(),
  authAnalyticsLoginError: vi.fn(),
  authAnalyticsLoginStarted: vi.fn(),
  authAnalyticsLoginSuccess: vi.fn(),
  authAnalyticsLogout: vi.fn(),
  authAnalyticsRateLimited: vi.fn(),
  authAnalyticsSessionRestored: vi.fn(),
  clearTokens: vi.fn(),
  passkeyCreateAuthenticationOptions: vi.fn(),
  passkeyVerifyAuthentication: vi.fn(),
  startPasskeyAuthentication: vi.fn(),
  stagePendingTwoFactorSession: vi.fn(),
}));

vi.mock('@/lib/api/auth', () => ({
  authApi: {
    login: mocks.authLogin,
    logout: mocks.authLogout,
    session: mocks.authSession,
  },
}));

vi.mock('@/lib/api/client', () => ({
  RateLimitError: class RateLimitError extends Error {
    retryAfter: number;

    constructor(retryAfter: number) {
      super(`Rate limited. Try again in ${retryAfter} seconds`);
      this.name = 'RateLimitError';
      this.retryAfter = retryAfter;
    }
  },
  tokenStorage: {
    clearTokens: mocks.clearTokens,
  },
}));

vi.mock('@/lib/api/passkeys', () => ({
  passkeysApi: {
    createAuthenticationOptions: mocks.passkeyCreateAuthenticationOptions,
    verifyAuthentication: mocks.passkeyVerifyAuthentication,
  },
}));

vi.mock('@/lib/analytics', () => ({
  authAnalytics: {
    loginError: mocks.authAnalyticsLoginError,
    loginStarted: mocks.authAnalyticsLoginStarted,
    loginSuccess: mocks.authAnalyticsLoginSuccess,
    logout: mocks.authAnalyticsLogout,
    rateLimited: mocks.authAnalyticsRateLimited,
    sessionRestored: mocks.authAnalyticsSessionRestored,
  },
}));

vi.mock('@/features/auth/lib/passkey-webauthn', () => ({
  isPasskeyWebAuthnError: () => false,
  startPasskeyAuthentication: mocks.startPasskeyAuthentication,
}));

vi.mock('@/features/auth/lib/pending-twofa-client', () => ({
  stagePendingTwoFactorSession: mocks.stagePendingTwoFactorSession,
}));

const AUTHENTICATED_ADMIN: User = {
  id: 'admin-1',
  email: 'admin@example.test',
  login: 'admin',
  role: 'super_admin',
  is_active: true,
  is_email_verified: true,
  created_at: '2026-06-04T00:00:00.000Z',
};

function resetAuthState(): void {
  useAuthStore.setState({
    error: null,
    isAuthenticated: false,
    isLoading: false,
    isMiniApp: false,
    isNewTelegramUser: false,
    rateLimitUntil: null,
    user: null,
  });
}

describe('useAuthStore.logout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAuthState();
  });

  it('clears client auth state only after server logout succeeds', async () => {
    mocks.authLogout.mockResolvedValueOnce({ status: 204 });
    useAuthStore.setState({
      isAuthenticated: true,
      user: AUTHENTICATED_ADMIN,
    });

    await useAuthStore.getState().logout();

    expect(mocks.authLogout).toHaveBeenCalledTimes(1);
    expect(mocks.clearTokens).toHaveBeenCalledTimes(1);
    expect(mocks.authAnalyticsLogout).toHaveBeenCalledTimes(1);
    expect(useAuthStore.getState()).toMatchObject({
      error: null,
      isAuthenticated: false,
      isLoading: false,
      user: null,
    });
  });

  it('keeps the admin authenticated in client state when server logout is rejected', async () => {
    const csrfError = {
      response: {
        status: 403,
        data: {
          detail: 'CSRF origin validation failed',
        },
      },
    };
    mocks.authLogout.mockRejectedValueOnce(csrfError);
    useAuthStore.setState({
      isAuthenticated: true,
      user: AUTHENTICATED_ADMIN,
    });

    await expect(useAuthStore.getState().logout()).rejects.toBe(csrfError);

    expect(mocks.clearTokens).not.toHaveBeenCalled();
    expect(mocks.authAnalyticsLogout).not.toHaveBeenCalled();
    expect(useAuthStore.getState()).toMatchObject({
      error: 'CSRF origin validation failed',
      isAuthenticated: true,
      isLoading: false,
      user: AUTHENTICATED_ADMIN,
    });
  });
});
