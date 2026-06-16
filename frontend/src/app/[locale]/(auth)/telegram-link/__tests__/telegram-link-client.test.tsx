import type React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { TELEGRAM_MAGIC_LINK_STORAGE_KEY } from '@/features/auth/lib/telegram-magic-link-session';
import { TelegramLinkClient } from '../telegram-link-client';

type MockAuthState = {
  loginWithBotLink: (...args: unknown[]) => unknown;
  telegramMagicLinkAuth: (...args: unknown[]) => unknown;
};

const routerPush = vi.hoisted(() => vi.fn());
const routeState = vi.hoisted(() => ({
  searchParams: new URLSearchParams(),
}));
const authApiMocks = vi.hoisted(() => ({
  pollTelegramMagicLinkStatus: vi.fn(),
}));
const authStoreMocks = vi.hoisted(() => ({
  loginWithBotLink: vi.fn(),
  setState: vi.fn(),
  telegramMagicLinkAuth: vi.fn(),
}));
const analyticsMocks = vi.hoisted(() => ({
  telegramSuccess: vi.fn(),
}));
const twoFactorMocks = vi.hoisted(() => ({
  stagePendingTwoFactorSession: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useSearchParams: () => routeState.searchParams,
}));

vi.mock('@/i18n/navigation', () => ({
  useRouter: () => ({
    back: vi.fn(),
    prefetch: vi.fn(),
    push: routerPush,
    replace: vi.fn(),
  }),
}));

vi.mock('@/lib/api/auth', () => ({
  authApi: {
    pollTelegramMagicLinkStatus: authApiMocks.pollTelegramMagicLinkStatus,
  },
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations: (namespace: string) => (key: string) => `${namespace}.${key}`,
}));

vi.mock('@/lib/analytics', () => ({
  authAnalytics: {
    telegramSuccess: analyticsMocks.telegramSuccess,
  },
}));

vi.mock('@/features/auth/lib/pending-twofa-client', () => ({
  stagePendingTwoFactorSession: twoFactorMocks.stagePendingTwoFactorSession,
}));

vi.mock('@/stores/auth-store', () => {
  const state: MockAuthState = {
    loginWithBotLink: authStoreMocks.loginWithBotLink,
    telegramMagicLinkAuth: authStoreMocks.telegramMagicLinkAuth,
  };
  const useAuthStore = <T,>(selector: (state: MockAuthState) => T): T => selector(state);

  return {
    useAuthStore: Object.assign(useAuthStore, {
      setState: authStoreMocks.setState,
    }),
  };
});

vi.mock('@/components/ui/button', async () => {
  const ReactModule = await import('react');

  return {
    Button: ({
      children,
      ...props
    }: React.ButtonHTMLAttributes<HTMLButtonElement> & { children?: React.ReactNode }) =>
      ReactModule.createElement('button', props, children),
  };
});

describe('TelegramLinkClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    routeState.searchParams = new URLSearchParams();
    window.sessionStorage.clear();
    window.location.pathname = '/en-EN/telegram-link';
    window.location.search = '';
    window.location.hash = '';
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('completes Telegram magic-link polling from tokenless metadata and scrubs magic URL token', async () => {
    routeState.searchParams = new URLSearchParams('magic=magic_link_token_123');
    window.location.search = '?magic=magic_link_token_123';
    window.sessionStorage.setItem(
      TELEGRAM_MAGIC_LINK_STORAGE_KEY,
      JSON.stringify({
        token: 'magic_link_token_123',
        botUrl: 'https://t.me/CyberVPNBot?start=auth_magic_link_token_123',
        deepLinkUrl: 'tg://resolve?domain=CyberVPNBot&start=auth_magic_link_token_123',
        requestedAt: Date.now(),
      }),
    );
    const replaceStateSpy = vi.spyOn(window.history, 'replaceState').mockImplementation(() => undefined);

    authApiMocks.pollTelegramMagicLinkStatus.mockResolvedValue({
      data: {
        status: 'completed',
        login_result: {
          user: {
            id: 'user-telegram-1',
            public_uid: 14677650,
            login: 'telegram-user',
            email: null,
            is_active: true,
            is_email_verified: true,
            created_at: '2026-06-16T12:00:00Z',
          },
          is_new_user: true,
          requires_2fa: false,
          tfa_token: null,
        },
      },
    });

    render(<TelegramLinkClient />);

    await waitFor(() => {
      expect(authApiMocks.pollTelegramMagicLinkStatus).toHaveBeenCalledWith('magic_link_token_123');
      expect(authStoreMocks.setState).toHaveBeenCalledWith(
        expect.objectContaining({
          isAuthenticated: true,
          isNewTelegramUser: true,
          user: expect.objectContaining({
            email: '',
            id: 'user-telegram-1',
            login: 'telegram-user',
            role: 'viewer',
          }),
        }),
      );
      expect(routerPush).toHaveBeenCalledWith('/dashboard?welcome=true');
    });

    expect(replaceStateSpy).toHaveBeenCalledWith({}, document.title, '/en-EN/telegram-link');
    expect(window.sessionStorage.getItem(TELEGRAM_MAGIC_LINK_STORAGE_KEY)).toBeNull();
    expect(analyticsMocks.telegramSuccess).toHaveBeenCalledWith('user-telegram-1');
    expect(twoFactorMocks.stagePendingTwoFactorSession).not.toHaveBeenCalled();
  });

  it('shows expired copy for a route-only expired Telegram magic link without login side effects', async () => {
    routeState.searchParams = new URLSearchParams();
    window.location.search = '?magic=expired-magic-cyba697';

    authApiMocks.pollTelegramMagicLinkStatus.mockResolvedValue({
      data: {
        status: 'expired',
        login_result: null,
      },
    });

    render(<TelegramLinkClient />);

    expect(await screen.findByRole('alert')).toHaveTextContent('Auth.telegram.botLinkExpired');
    expect(authApiMocks.pollTelegramMagicLinkStatus).toHaveBeenCalledWith('expired-magic-cyba697');
    expect(window.sessionStorage.removeItem).toHaveBeenCalledWith(TELEGRAM_MAGIC_LINK_STORAGE_KEY);
    expect(routerPush).not.toHaveBeenCalled();
    expect(authStoreMocks.loginWithBotLink).not.toHaveBeenCalled();
    expect(authStoreMocks.telegramMagicLinkAuth).not.toHaveBeenCalled();
    expect(authStoreMocks.setState).not.toHaveBeenCalled();
    expect(analyticsMocks.telegramSuccess).not.toHaveBeenCalled();
  });

  it('shows invalid copy when no route or stored Telegram magic token is available', async () => {
    render(<TelegramLinkClient />);

    expect(await screen.findByRole('alert')).toHaveTextContent('Auth.telegram.botLinkInvalid');
    expect(authApiMocks.pollTelegramMagicLinkStatus).not.toHaveBeenCalled();
    expect(routerPush).not.toHaveBeenCalled();
    expect(authStoreMocks.loginWithBotLink).not.toHaveBeenCalled();
    expect(authStoreMocks.telegramMagicLinkAuth).not.toHaveBeenCalled();
    expect(authStoreMocks.setState).not.toHaveBeenCalled();
    expect(analyticsMocks.telegramSuccess).not.toHaveBeenCalled();
  });
});
