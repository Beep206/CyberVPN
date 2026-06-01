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
import {
  setupTelegramWebAppMock,
  cleanupTelegramWebAppMock,
} from '@/test/mocks/telegram-webapp';

const mocks = vi.hoisted(() => ({
  routerPush: vi.fn(),
  routerReplace: vi.fn(),
  mockLogout: vi.fn(),
  mockDeleteAccount: vi.fn(),
  capabilities: {
    data: {
      growth: {
        checkout_code_discounts: false,
        gift_codes: false,
        growth_hub: false,
        invites: true,
        promo_codes: false,
        referral: false,
      },
    },
  },
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations: () => (key: string) => key,
}));

vi.mock('@/i18n/navigation', () => ({
  Link: ({ href, onClick, children, className }: React.ComponentProps<'a'>) => (
    <a href={href} onClick={onClick} className={className}>
      {children}
    </a>
  ),
  useRouter: () => ({ push: mocks.routerPush, replace: mocks.routerReplace }),
}));

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: (selector: (state: Record<string, unknown>) => unknown) => {
    const mockUser = {
      id: 'user-123',
      login: 'testuser',
      email: 'test@example.com',
    };
    const state = {
      user: mockUser,
      logout: mocks.mockLogout,
      deleteAccount: mocks.mockDeleteAccount,
    };
    return selector ? selector(state) : state;
  },
}));

vi.mock(
  '@/features/client-capabilities/useClientCapabilities',
  async (importOriginal) => {
    const actual =
      await importOriginal<
        typeof import('@/features/client-capabilities/useClientCapabilities')
      >();
    return {
      ...actual,
      useClientCapabilities: () => mocks.capabilities,
    };
  },
);

const API_BASE = '*/api/v1';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
};

describe('MiniAppProfilePage', () => {
  beforeEach(() => {
    setupTelegramWebAppMock();
    vi.clearAllMocks();
    mocks.mockLogout.mockResolvedValue(undefined);
    mocks.mockDeleteAccount.mockResolvedValue(undefined);
    mocks.capabilities.data.growth.checkout_code_discounts = false;
    mocks.capabilities.data.growth.gift_codes = false;
    mocks.capabilities.data.growth.growth_hub = false;
    mocks.capabilities.data.growth.invites = true;
    mocks.capabilities.data.growth.promo_codes = false;
    mocks.capabilities.data.growth.referral = false;

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
      http.get(`${API_BASE}/invites/my`, () => {
        return HttpResponse.json([
          {
            id: 'invite-1',
            code: 'OWNER123',
            free_days: 7,
            is_used: false,
            expires_at: '2026-06-24T11:54:13Z',
            created_at: '2026-05-21T11:54:13Z',
          },
        ]);
      }),
      http.get(`${API_BASE}/security/antiphishing`, () => {
        return HttpResponse.json({ code: null });
      }),
      http.get(`${API_BASE}/partner/dashboard`, () => {
        return HttpResponse.json({ is_partner: false, codes: [] });
      }),
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

  it('test_renders_profile_cabinet_links_without_mixed_hub_widgets', async () => {
    render(<ProfilePage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('links.rewards')).toBeInTheDocument();
      expect(screen.getByText('links.payments')).toBeInTheDocument();
      expect(screen.getByText('links.devices')).toBeInTheDocument();
      expect(screen.getByText('links.support')).toBeInTheDocument();
    });

    expect(screen.queryByText('VPN Config')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /myInvites/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /paymentHistory/i })).not.toBeInTheDocument();
  });

  it('test_hides_partner_section_during_s3_disabled_boundary', async () => {
    render(<ProfilePage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('testuser')).toBeInTheDocument();
      expect(
        screen.queryByRole('button', { name: /partner/i }),
      ).not.toBeInTheDocument();
    });
  });

  it('test_expands_and_collapses_sections', async () => {
    render(<ProfilePage />, { wrapper: createWrapper() });

    const securitySection = await screen.findByRole('button', {
      name: /security/i,
    });
    fireEvent.click(securitySection);

    await waitFor(() => {
      expect(screen.getByText('twoFactorAuth')).toBeInTheDocument();
      expect(screen.getByText('changePassword')).toBeInTheDocument();
    });
  });

  it('test_links_active_devices_to_the_miniapp_devices_route', async () => {
    render(<ProfilePage />, { wrapper: createWrapper() });

    const securitySection = await screen.findByRole('button', {
      name: /security/i,
    });
    fireEvent.click(securitySection);
    fireEvent.click(await screen.findByRole('button', { name: /activeDevices/i }));

    await waitFor(() => {
      expect(mocks.routerPush).toHaveBeenCalledWith('/miniapp/devices');
    });
  });

  it('test_opens_official_telegram_support_from_profile_link', async () => {
    const telegramWebApp = setupTelegramWebAppMock();

    render(<ProfilePage />, { wrapper: createWrapper() });

    fireEvent.click(await screen.findByRole('button', { name: /links.support/i }));

    expect(telegramWebApp.openTelegramLink).toHaveBeenCalledWith(
      'https://t.me/C_y_b_e_r_VPN_Bot',
    );
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

  it('test_delete_account_uses_telegram_confirm_callback_and_clears_miniapp_session', async () => {
    const telegramWebApp = setupTelegramWebAppMock({
      showConfirm: vi.fn(
        (_message: string, callback?: (confirmed: boolean) => void) => {
          callback?.(true);
        },
      ),
    });

    render(<ProfilePage />, { wrapper: createWrapper() });

    fireEvent.click(
      await screen.findByRole('button', { name: /deleteAccount/i }),
    );

    await waitFor(() => {
      expect(telegramWebApp.showConfirm).toHaveBeenCalledWith(
        'deleteAccountConfirm',
        expect.any(Function),
      );
      expect(mocks.mockDeleteAccount).toHaveBeenCalledTimes(1);
      expect(telegramWebApp.showAlert).toHaveBeenCalledWith('accountDeleted');
      expect(mocks.routerReplace).toHaveBeenCalledWith('/miniapp/home');
    });
  });
});
