import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { TelegramLinkClient } from '../telegram-link-client';

const {
  clearTelegramMagicLinkSession,
  pollTelegramMagicLinkStatus,
  readTelegramMagicLinkSession,
  routerPush,
  setAuthStoreState,
} = vi.hoisted(() => ({
  clearTelegramMagicLinkSession: vi.fn(),
  pollTelegramMagicLinkStatus: vi.fn(),
  readTelegramMagicLinkSession: vi.fn(),
  routerPush: vi.fn(),
  setAuthStoreState: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams('magic=magic_link_token_123'),
}));

vi.mock('@/i18n/navigation', () => ({
  useRouter: () => ({
    push: routerPush,
    replace: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

vi.mock('@/lib/api/auth', () => ({
  authApi: {
    pollTelegramMagicLinkStatus,
  },
}));

vi.mock('@/features/auth/lib/telegram-magic-link-session', () => ({
  clearTelegramMagicLinkSession,
  readTelegramMagicLinkSession,
}));

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: Object.assign(
    (selector: (state: { loginWithBotLink: () => Promise<void>; telegramMagicLinkAuth: () => Promise<void> }) => unknown) =>
      selector({
        loginWithBotLink: vi.fn(),
        telegramMagicLinkAuth: vi.fn(),
      }),
    {
      setState: setAuthStoreState,
    },
  ),
}));

vi.mock('@/features/auth/lib/pending-twofa-client', () => ({
  stagePendingTwoFactorSession: vi.fn(),
}));

describe('TelegramLinkClient', () => {
  beforeEach(() => {
    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      value: 'visible',
    });
    readTelegramMagicLinkSession.mockReturnValue({
      token: 'magic_link_token_123',
      botUrl: 'https://t.me/CyberVPNBot?start=auth_magic_link_token_123',
      deepLinkUrl: 'tg://resolve?domain=CyberVPNBot&start=auth_magic_link_token_123',
      requestedAt: Date.now(),
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('polls immediately when the user confirms Telegram in the browser', async () => {
    pollTelegramMagicLinkStatus.mockResolvedValue({ data: { status: 'pending' } });

    render(<TelegramLinkClient />);

    await waitFor(() => {
      expect(pollTelegramMagicLinkStatus).toHaveBeenCalled();
    });
    await Promise.all(pollTelegramMagicLinkStatus.mock.results.map((result) => result.value));
    await new Promise((resolve) => setTimeout(resolve, 0));

    const callsBeforeClick = pollTelegramMagicLinkStatus.mock.calls.length;
    pollTelegramMagicLinkStatus.mockResolvedValueOnce({
      data: {
        status: 'completed',
        login_result: {
          access_token: 'access_token',
          refresh_token: 'refresh_token',
          token_type: 'bearer',
          expires_in: 900,
          is_new_user: false,
          requires_2fa: false,
          tfa_token: null,
          user: {
            id: 'user-123',
            login: 'alice',
            email: null,
            is_active: true,
            is_email_verified: true,
            created_at: '2026-06-10T08:00:00Z',
          },
        },
      },
    });

    await userEvent.click(await screen.findByRole('button', { name: 'checkStatusButton' }));

    await waitFor(() => {
      expect(pollTelegramMagicLinkStatus.mock.calls.length).toBeGreaterThan(callsBeforeClick);
    });
    expect(pollTelegramMagicLinkStatus).toHaveBeenLastCalledWith('magic_link_token_123');
    expect(clearTelegramMagicLinkSession).toHaveBeenCalled();
    expect(setAuthStoreState).toHaveBeenCalledWith(
      expect.objectContaining({
        isAuthenticated: true,
        isLoading: false,
        isNewTelegramUser: false,
      }),
    );
    expect(routerPush).toHaveBeenCalledWith('/dashboard');
  });
});
