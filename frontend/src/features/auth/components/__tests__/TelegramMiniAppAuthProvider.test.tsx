import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { TelegramMiniAppAuthProvider } from '../TelegramMiniAppAuthProvider';
import { MINIAPP_AUTH_RESTORE_REQUIRED_EVENT } from '@/lib/api/client';

const {
  mockPush,
  mockReplace,
  mockUsePathname,
  mockStagePendingTwoFactorSession,
  mockTelegramMiniAppAuth,
} = vi.hoisted(() => ({
  mockPush: vi.fn(),
  mockReplace: vi.fn(),
  mockUsePathname: vi.fn(),
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
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  usePathname: () => mockUsePathname(),
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

function renderProvider(children: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <TelegramMiniAppAuthProvider>{children}</TelegramMiniAppAuthProvider>
    </QueryClientProvider>,
  );
}

describe('TelegramMiniAppAuthProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    delete (window as typeof window & { Telegram?: unknown }).Telegram;
    currentLocale = 'ru-RU';
    currentAuthState = {
      telegramMiniAppAuth: mockTelegramMiniAppAuth,
      isAuthenticated: false,
      isMiniApp: true,
    };
    mockUsePathname.mockReturnValue('/miniapp/home');
  });

  it('keeps successful mini app auth inside the current mini app namespace', async () => {
    mockTelegramMiniAppAuth.mockResolvedValue({
      requires_2fa: false,
      is_new_user: false,
    });

    renderProvider(<div>Mini App Child</div>);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/miniapp/home');
    });
  });

  it('preserves a direct VPN route after successful mini app auth', async () => {
    mockUsePathname.mockReturnValue('/miniapp/vpn');
    mockTelegramMiniAppAuth.mockResolvedValue({
      requires_2fa: false,
      is_new_user: false,
    });

    renderProvider(<div>Mini App VPN Child</div>);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/miniapp/vpn');
    });
    expect(mockReplace).not.toHaveBeenCalledWith('/miniapp/home');
  });

  it('preserves nested rewards routes after successful mini app auth', async () => {
    mockUsePathname.mockReturnValue('/miniapp/rewards/gifts');
    mockTelegramMiniAppAuth.mockResolvedValue({
      requires_2fa: false,
      is_new_user: false,
    });

    renderProvider(<div>Mini App Rewards Child</div>);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/miniapp/rewards/gifts');
    });
  });

  it('stages two-factor flow with a mini app return path', async () => {
    mockUsePathname.mockReturnValue('/miniapp/rewards/referral');
    mockTelegramMiniAppAuth.mockResolvedValue({
      requires_2fa: true,
      tfa_token: 'pending_2fa_token',
      is_new_user: true,
    });

    renderProvider(<div>Mini App Child</div>);

    await waitFor(() => {
      expect(mockStagePendingTwoFactorSession).toHaveBeenCalledWith({
        token: 'pending_2fa_token',
        locale: 'ru-RU',
        returnTo: '/ru-RU/miniapp/rewards/referral',
        isNewUser: true,
      });
    });

    expect(mockPush).toHaveBeenCalledWith('/login?2fa=true&redirect=%2Fru-RU%2Fminiapp%2Frewards%2Freferral');
  });

  it('renders children when mini app auto-auth is not active', () => {
    currentAuthState = {
      telegramMiniAppAuth: mockTelegramMiniAppAuth,
      isAuthenticated: false,
      isMiniApp: false,
    };
    mockUsePathname.mockReturnValue('/dashboard');

    renderProvider(<div>Standard Flow Child</div>);

    expect(screen.getByText('Standard Flow Child')).toBeInTheDocument();
    expect(mockTelegramMiniAppAuth).not.toHaveBeenCalled();
  });

  it('gates mini app routes instead of rendering the standard guest flow while initData is missing', () => {
    currentAuthState = {
      telegramMiniAppAuth: mockTelegramMiniAppAuth,
      isAuthenticated: false,
      isMiniApp: false,
    };
    mockUsePathname.mockReturnValue('/miniapp/profile');

    renderProvider(<div>Standard Guest Profile</div>);

    expect(screen.getByText('miniAppAutoAuth')).toBeInTheDocument();
    expect(screen.queryByText('Standard Guest Profile')).not.toBeInTheDocument();
    expect(mockTelegramMiniAppAuth).not.toHaveBeenCalled();
  });

  it('detects Telegram WebApp initData when the auth store was created too early', async () => {
    currentAuthState = {
      telegramMiniAppAuth: mockTelegramMiniAppAuth,
      isAuthenticated: false,
      isMiniApp: false,
    };
    (window as typeof window & { Telegram?: { WebApp: { initData: string } } }).Telegram = {
      WebApp: { initData: 'query_id=late&user=owner&hash=signature' },
    };
    mockTelegramMiniAppAuth.mockResolvedValue({
      requires_2fa: false,
      is_new_user: false,
    });

    renderProvider(<div>Mini App Child</div>);

    await waitFor(() => {
      expect(mockTelegramMiniAppAuth).toHaveBeenCalled();
      expect(mockReplace).toHaveBeenCalledWith('/miniapp/home');
    });
  });

  it('does not crash when mini app auth fails with structured API detail', async () => {
    mockTelegramMiniAppAuth.mockRejectedValue({
      response: {
        data: {
          detail: {
            code: 'INVALID_TOKEN',
            message: 'Invalid token',
          },
        },
      },
    });

    renderProvider(<div>Mini App Child</div>);

    await waitFor(() => {
      expect(screen.getByText('miniAppAutoAuth')).toBeInTheDocument();
    });
    expect(screen.queryByText('Mini App Child')).not.toBeInTheDocument();
  });

  it('restores Telegram Mini App auth after a protected mini app request loses its cookie session', async () => {
    currentAuthState = {
      telegramMiniAppAuth: mockTelegramMiniAppAuth,
      isAuthenticated: true,
      isMiniApp: true,
    };
    mockUsePathname.mockReturnValue('/miniapp/vpn');
    (window as typeof window & { Telegram?: { WebApp: { initData: string } } }).Telegram = {
      WebApp: { initData: 'query_id=restore&user=owner&hash=signature' },
    };
    mockTelegramMiniAppAuth.mockResolvedValue({
      requires_2fa: false,
      is_new_user: false,
    });

    renderProvider(<div>Mini App Child</div>);

    window.dispatchEvent(new CustomEvent(MINIAPP_AUTH_RESTORE_REQUIRED_EVENT));

    await waitFor(() => {
      expect(mockTelegramMiniAppAuth).toHaveBeenCalled();
      expect(mockReplace).toHaveBeenCalledWith('/miniapp/vpn');
    });
  });
});
