import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { TelegramMiniAppAuthProvider } from '../TelegramMiniAppAuthProvider';

const {
  mockPush,
  mockStagePendingTwoFactorSession,
  mockTelegramMiniAppAuth,
} = vi.hoisted(() => ({
  mockPush: vi.fn(),
  mockStagePendingTwoFactorSession: vi.fn(),
  mockTelegramMiniAppAuth: vi.fn(),
}));

let currentLocale = 'ru-RU';
let currentAuthState = {
  telegramMiniAppAuth: mockTelegramMiniAppAuth,
  isAuthenticated: false,
  isMiniApp: true,
};

vi.mock('@/i18n/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock('next-intl', () => ({
  useLocale: () => currentLocale,
  useTranslations: () => ((key: string) => key),
}));

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: () => currentAuthState,
}));

vi.mock('@/features/auth/lib/pending-twofa-client', () => ({
  stagePendingTwoFactorSession: (...args: unknown[]) => mockStagePendingTwoFactorSession(...args),
}));

vi.mock('lucide-react', () => ({
  Loader2: (props: Record<string, unknown>) => <div data-testid="loader" {...props} />,
  AlertCircle: (props: Record<string, unknown>) => <div data-testid="alert" {...props} />,
  Shield: (props: Record<string, unknown>) => <div data-testid="shield" {...props} />,
}));

vi.mock('motion/react', () => ({
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => <div {...props}>{children}</div>,
  },
}));

describe('TelegramMiniAppAuthProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    currentLocale = 'ru-RU';
    currentAuthState = {
      telegramMiniAppAuth: mockTelegramMiniAppAuth,
      isAuthenticated: false,
      isMiniApp: true,
    };
  });

  it('keeps successful mini app auth inside the mini app namespace', async () => {
    mockTelegramMiniAppAuth.mockResolvedValue({
      requires_2fa: false,
      is_new_user: false,
    });

    render(
      <TelegramMiniAppAuthProvider>
        <div>Mini App Child</div>
      </TelegramMiniAppAuthProvider>,
    );

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/miniapp/home');
    });
  });

  it('stages two-factor flow with a mini app return path', async () => {
    mockTelegramMiniAppAuth.mockResolvedValue({
      requires_2fa: true,
      tfa_token: 'pending_2fa_token',
      is_new_user: true,
    });

    render(
      <TelegramMiniAppAuthProvider>
        <div>Mini App Child</div>
      </TelegramMiniAppAuthProvider>,
    );

    await waitFor(() => {
      expect(mockStagePendingTwoFactorSession).toHaveBeenCalledWith({
        token: 'pending_2fa_token',
        locale: 'ru-RU',
        returnTo: '/ru-RU/miniapp/home',
        isNewUser: true,
      });
    });

    expect(mockPush).toHaveBeenCalledWith('/login?2fa=true&redirect=%2Fru-RU%2Fminiapp%2Fhome');
  });

  it('renders children when mini app auto-auth is not active', () => {
    currentAuthState = {
      telegramMiniAppAuth: mockTelegramMiniAppAuth,
      isAuthenticated: false,
      isMiniApp: false,
    };

    render(
      <TelegramMiniAppAuthProvider>
        <div>Standard Flow Child</div>
      </TelegramMiniAppAuthProvider>,
    );

    expect(screen.getByText('Standard Flow Child')).toBeInTheDocument();
    expect(mockTelegramMiniAppAuth).not.toHaveBeenCalled();
  });
});
