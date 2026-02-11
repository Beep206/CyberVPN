/**
 * Mini App Plans Page Tests (TOB-5)
 *
 * Tests the plans/purchase page:
 * - Plans list with pricing
 * - Purchase button triggers invoice creation
 * - Trial activation
 * - Promo code validation
 * - Invite code redemption
 * - Loading states
 *
 * Depends on: MG-2, MG-4 (Plans pricing + purchase flow implementation)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MiniAppPlansPage from '../../page';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { setupTelegramWebAppMock, cleanupTelegramWebAppMock } from '@/test/mocks/telegram-webapp';

// Mock API modules
vi.mock('@/lib/api', () => ({
  plansApi: {
    list: vi.fn(),
  },
  trialApi: {
    getStatus: vi.fn(),
    activate: vi.fn(),
  },
  promoApi: {
    validate: vi.fn(),
  },
  invitesApi: {
    redeem: vi.fn(),
  },
  paymentsApi: {
    createInvoice: vi.fn(),
  },
}));

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string, values?: Record<string, any>) => {
    if (values) {
      return `${key}(${JSON.stringify(values)})`;
    }
    return key;
  },
}));

// Helper to wrap component with QueryClient
function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
}

describe('MiniApp Plans Page', () => {
  beforeEach(() => {
    setupTelegramWebAppMock();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanupTelegramWebAppMock();
  });

  describe('Loading State', () => {
    it('test_displays_loading_spinner', async () => {
      const { plansApi, trialApi } = await import('@/lib/api');

      vi.mocked(plansApi.list).mockReturnValue(new Promise(() => {}) as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: { is_eligible: false, is_trial_active: false }
      } as any);

      renderWithProviders(<MiniAppPlansPage />);

      const spinner = document.querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
    });
  });

  describe('Plans Display', () => {
    it('test_displays_plans_list', async () => {
      const { plansApi, trialApi } = await import('@/lib/api');

      vi.mocked(plansApi.list).mockResolvedValue({
        data: [
          {
            uuid: 'plan-1',
            name: 'Basic',
            price: 9.99,
            currency: 'USD',
            durationDays: 30,
            dataLimitGb: 100,
            maxDevices: 5,
            features: ['Unlimited bandwidth', 'Multiple devices'],
            isActive: true,
          },
          {
            uuid: 'plan-2',
            name: 'Premium',
            price: 19.99,
            currency: 'USD',
            durationDays: 30,
            dataLimitGb: 500,
            maxDevices: 10,
            features: ['Unlimited bandwidth', 'Priority support'],
            isActive: true,
          },
        ]
      } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: { is_eligible: false, is_trial_active: false }
      } as any);

      renderWithProviders(<MiniAppPlansPage />);

      await waitFor(() => {
        expect(screen.getByText('Basic')).toBeInTheDocument();
        expect(screen.getByText('Premium')).toBeInTheDocument();
      });
    });

    it('test_displays_plan_pricing', async () => {
      const { plansApi, trialApi } = await import('@/lib/api');

      vi.mocked(plansApi.list).mockResolvedValue({
        data: [
          {
            uuid: 'plan-1',
            name: 'Basic',
            price: 9.99,
            currency: 'USD',
            durationDays: 30,
            dataLimitGb: 100,
            isActive: true,
          },
        ]
      } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: { is_eligible: false, is_trial_active: false }
      } as any);

      renderWithProviders(<MiniAppPlansPage />);

      await waitFor(() => {
        expect(screen.getByText('9.99')).toBeInTheDocument();
        expect(screen.getByText('USD')).toBeInTheDocument();
      });
    });

    it('test_displays_no_plans_message', async () => {
      const { plansApi, trialApi } = await import('@/lib/api');

      vi.mocked(plansApi.list).mockResolvedValue({ data: [] } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: { is_eligible: false, is_trial_active: false }
      } as any);

      renderWithProviders(<MiniAppPlansPage />);

      await waitFor(() => {
        expect(screen.getByText('noPlans')).toBeInTheDocument();
      });
    });
  });

  describe('Purchase Flow', () => {
    it('test_purchase_button_triggers_invoice_creation', async () => {
      const user = userEvent.setup({ delay: null });
      const { plansApi, trialApi, paymentsApi } = await import('@/lib/api');

      vi.mocked(plansApi.list).mockResolvedValue({
        data: [
          {
            uuid: 'plan-1',
            name: 'Basic',
            price: 9.99,
            currency: 'USD',
            durationDays: 30,
            dataLimitGb: 100,
            isActive: true,
          },
        ]
      } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: { is_eligible: false, is_trial_active: false }
      } as any);
      vi.mocked(paymentsApi.createInvoice).mockResolvedValue({
        data: { payment_url: 'https://payment.url' }
      } as any);

      renderWithProviders(<MiniAppPlansPage />);

      await waitFor(() => {
        expect(screen.getByText('purchasePlan')).toBeInTheDocument();
      });

      const purchaseButton = screen.getByText('purchasePlan');
      await user.click(purchaseButton);

      await waitFor(() => {
        expect(paymentsApi.createInvoice).toHaveBeenCalledWith(
          expect.objectContaining({
            plan_id: 'plan-1',
            currency: 'USDT',
          })
        );
      });
    });
  });

  describe('Trial Section', () => {
    it('test_shows_trial_section_when_eligible', async () => {
      const { plansApi, trialApi } = await import('@/lib/api');

      vi.mocked(plansApi.list).mockResolvedValue({ data: [] } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: { is_eligible: true, is_trial_active: false }
      } as any);

      renderWithProviders(<MiniAppPlansPage />);

      await waitFor(() => {
        expect(screen.getByText('freeTrialTitle')).toBeInTheDocument();
        expect(screen.getByText('activateTrial')).toBeInTheDocument();
      });
    });

    it('test_hides_trial_section_when_not_eligible', async () => {
      const { plansApi, trialApi } = await import('@/lib/api');

      vi.mocked(plansApi.list).mockResolvedValue({ data: [] } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: { is_eligible: false, is_trial_active: false }
      } as any);

      renderWithProviders(<MiniAppPlansPage />);

      await waitFor(() => {
        expect(screen.getByText('noPlans')).toBeInTheDocument();
      });

      expect(screen.queryByText('freeTrialTitle')).not.toBeInTheDocument();
    });

    it('test_activate_trial_button_triggers_mutation', async () => {
      const user = userEvent.setup({ delay: null });
      const { plansApi, trialApi } = await import('@/lib/api');

      vi.mocked(plansApi.list).mockResolvedValue({ data: [] } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: { is_eligible: true, is_trial_active: false }
      } as any);
      vi.mocked(trialApi.activate).mockResolvedValue({ data: {} } as any);

      renderWithProviders(<MiniAppPlansPage />);

      await waitFor(() => {
        expect(screen.getByText('activateTrial')).toBeInTheDocument();
      });

      const activateButton = screen.getByText('activateTrial');
      await user.click(activateButton);

      await waitFor(() => {
        expect(trialApi.activate).toHaveBeenCalled();
      });
    });
  });

  describe('Promo Code', () => {
    it('test_displays_promo_code_input', async () => {
      const { plansApi, trialApi } = await import('@/lib/api');

      vi.mocked(plansApi.list).mockResolvedValue({ data: [] } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: { is_eligible: false, is_trial_active: false }
      } as any);

      renderWithProviders(<MiniAppPlansPage />);

      await waitFor(() => {
        expect(screen.getByText('havePromoCode')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('promoCodePlaceholder')).toBeInTheDocument();
      });
    });
  });

  describe('Invite Code', () => {
    it('test_displays_invite_code_input', async () => {
      const { plansApi, trialApi } = await import('@/lib/api');

      vi.mocked(plansApi.list).mockResolvedValue({ data: [] } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: { is_eligible: false, is_trial_active: false }
      } as any);

      renderWithProviders(<MiniAppPlansPage />);

      await waitFor(() => {
        expect(screen.getByText('haveInviteCode')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('inviteCodePlaceholder')).toBeInTheDocument();
      });
    });
  });
});
