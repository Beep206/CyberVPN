/**
 * Mini App Profile Page Tests
 *
 * Tests profile functionality:
 * - User info display
 * - Collapsible sections
 * - Logout and delete account
 * - Referral code sharing
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ProfilePage from '../page';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { setupTelegramWebAppMock, cleanupTelegramWebAppMock } from '@/test/mocks/telegram-webapp';

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock('@/i18n/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock('../../components/VpnConfigCard', () => ({
  VpnConfigCard: () => <div data-testid="vpn-config-card">VPN Config</div>,
}));

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: (selector: any) => {
    const mockUser = {
      id: 'user-123',
      login: 'testuser',
      email: 'test@example.com',
    };
    const mockLogout = vi.fn();
    return selector ? selector({ user: mockUser, logout: mockLogout }) : { user: mockUser, logout: mockLogout };
  },
}));

const API_BASE = 'http://localhost:8000/api/v1';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('MiniAppProfilePage', () => {
  let telegramMock: ReturnType<typeof setupTelegramWebAppMock>;

  beforeEach(() => {
    telegramMock = setupTelegramWebAppMock();
    vi.clearAllMocks();

    server.use(
      http.get(`${API_BASE}/referral/code`, () => {
        return HttpResponse.json({ code: 'REF2024' });
      }),
      http.get(`${API_BASE}/referral/stats`, () => {
        return HttpResponse.json({ total_referrals: 5 });
      }),
      http.get(`${API_BASE}/twofa/status`, () => {
        return HttpResponse.json({ enabled: false });
      }),
      http.get(`${API_BASE}/payments/history`, () => {
        return HttpResponse.json([]);
      }),
      http.get(`${API_BASE}/security/antiphishing`, () => {
        return HttpResponse.json({ code: null });
      })
    );
  });

  afterEach(() => {
    cleanupTelegramWebAppMock();
  });

  it('test_displays_user_info_section', async () => {
    render(<ProfilePage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('userInfo')).toBeInTheDocument();
    });
  });

  it('test_displays_referral_section', async () => {
    render(<ProfilePage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('referral')).toBeInTheDocument();
    });

    expect(screen.getByText('REF2024')).toBeInTheDocument();
  });

  it('test_expands_and_collapses_sections', async () => {
    const user = userEvent.setup();

    render(<ProfilePage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('security')).toBeInTheDocument();
    });

    const securitySection = screen.getByText('security');
    await user.click(securitySection);

    expect(telegramMock.HapticFeedback.selectionChanged).toHaveBeenCalled();
  });

  it('test_shows_logout_button', async () => {
    render(<ProfilePage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('logout')).toBeInTheDocument();
    });
  });

  it('test_shows_delete_account_button', async () => {
    render(<ProfilePage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('deleteAccount')).toBeInTheDocument();
    });
  });
});
