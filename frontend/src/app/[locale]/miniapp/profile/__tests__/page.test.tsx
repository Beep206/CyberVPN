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
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
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
  useAuthStore: (selector: (state: Record<string, unknown>) => unknown) => {
    const mockUser = {
      id: 'user-123',
      login: 'testuser',
      email: 'test@example.com',
    };
    const mockLogout = vi.fn();
    return selector ? selector({ user: mockUser, logout: mockLogout }) : { user: mockUser, logout: mockLogout };
  },
}));

const API_BASE = '*/api/v1';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
};

describe('MiniAppProfilePage', () => {
  beforeEach(() => {
    setupTelegramWebAppMock();
    vi.clearAllMocks();

    server.use(
      http.get(`${API_BASE}/referral/code`, () => {
        return HttpResponse.json({ referral_code: 'REF2024' });
      }),
      http.get(`${API_BASE}/referral/stats`, () => {
        return HttpResponse.json({ total_referrals: 5 });
      }),
      http.get(`${API_BASE}/2fa/status`, () => {
        return HttpResponse.json({ status: 'disabled' });
      }),
      http.get(`${API_BASE}/orders/`, () => {
        return HttpResponse.json([]);
      }),
      http.get(`${API_BASE}/security/antiphishing`, () => {
        return HttpResponse.json({ code: null });
      }),
      http.get(`${API_BASE}/partner/dashboard`, () => {
        return HttpResponse.json({ is_partner: false, codes: [] });
      })
    );
  });

  afterEach(() => {
    cleanupTelegramWebAppMock();
  });

  it('test_displays_user_info_section', async () => {
    render(<ProfilePage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('testuser')).toBeInTheDocument();
      expect(screen.getByText('test@example.com')).toBeInTheDocument();
    });
  });

  it('test_displays_referral_section', async () => {
    render(<ProfilePage />, { wrapper: createWrapper() });

    const referralSection = await screen.findByRole('button', { name: /referral/i });

    fireEvent.click(referralSection);

    await waitFor(() => {
      expect(screen.getByText('REF2024')).toBeInTheDocument();
      expect(screen.getByText('yourReferralCode')).toBeInTheDocument();
    });
  });

  it('test_expands_and_collapses_sections', async () => {
    render(<ProfilePage />, { wrapper: createWrapper() });

    const securitySection = await screen.findByRole('button', { name: /security/i });
    fireEvent.click(securitySection);

    await waitFor(() => {
      expect(screen.getByText('twoFactorAuth')).toBeInTheDocument();
      expect(screen.getByText('changePassword')).toBeInTheDocument();
    });
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
