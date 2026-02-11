/**
 * Mini App Plans Page Tests
 *
 * Tests the plans/purchase page for Telegram Mini App:
 * - Trial activation
 * - Plan cards display and purchase
 * - Promo code validation
 * - Invite code redemption
 * - CryptoBot payment integration
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PlansPage from '../page';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { setupTelegramWebAppMock, cleanupTelegramWebAppMock } from '@/test/mocks/telegram-webapp';

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string, values?: Record<string, string | number>) => {
    if (values) {
      return `${key}:${JSON.stringify(values)}`;
    }
    return key;
  },
}));

const API_BASE = 'http://localhost:8000/api/v1';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

const mockPlans = [
  {
    uuid: 'plan-1',
    name: 'Basic Plan',
    templateType: 'vless',
    hostUuid: 'host-1',
    inboundTag: 'tag-1',
    flow: 'xtls-rprx-vision',
    configData: null,
  },
  {
    uuid: 'plan-2',
    name: 'Premium Plan',
    templateType: 'vmess',
    hostUuid: 'host-2',
    inboundTag: 'tag-2',
    flow: null,
    configData: { speed: '1000Mbps' },
  },
];

const mockTrialData = {
  is_trial_active: false,
  is_eligible: true,
  trial_end: null,
  days_remaining: 0,
};

describe('MiniAppPlansPage', () => {
  let telegramMock: ReturnType<typeof setupTelegramWebAppMock>;

  beforeEach(() => {
    telegramMock = setupTelegramWebAppMock();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanupTelegramWebAppMock();
  });

  describe('Loading State', () => {
    it('test_shows_loading_spinner_while_fetching_plans', () => {
      server.use(
        http.get(`${API_BASE}/plans`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json(mockPlans);
        }),
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json(mockTrialData);
        })
      );

      render(<PlansPage />, { wrapper: createWrapper() });

      expect(screen.getByRole('status', { hidden: true })).toBeInTheDocument();
    });
  });

  describe('Trial Activation Section', () => {
    beforeEach(() => {
      server.use(
        http.get(`${API_BASE}/plans`, () => {
          return HttpResponse.json(mockPlans);
        }),
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json(mockTrialData);
        })
      );
    });

    it('test_shows_trial_section_when_eligible', async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('freeTrialTitle')).toBeInTheDocument();
      });

      expect(screen.getByText('freeTrialDescription')).toBeInTheDocument();
      expect(screen.getByText('activateTrial')).toBeInTheDocument();
    });

    it('test_hides_trial_section_when_not_eligible', async () => {
      server.use(
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json({
            is_trial_active: false,
            is_eligible: false,
            trial_end: null,
            days_remaining: 0,
          });
        })
      );

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('availablePlans')).toBeInTheDocument();
      });

      expect(screen.queryByText('freeTrialTitle')).not.toBeInTheDocument();
    });

    it('test_hides_trial_section_when_already_active', async () => {
      server.use(
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json({
            is_trial_active: true,
            is_eligible: false,
            trial_end: '2026-02-18T23:59:59Z',
            days_remaining: 7,
          });
        })
      );

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('availablePlans')).toBeInTheDocument();
      });

      expect(screen.queryByText('freeTrialTitle')).not.toBeInTheDocument();
    });

    it('test_activates_trial_successfully', async () => {
      const user = userEvent.setup();

      server.use(
        http.post(`${API_BASE}/trial/activate`, () => {
          return HttpResponse.json({ message: 'Trial activated' });
        })
      );

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('activateTrial')).toBeInTheDocument();
      });

      const activateButton = screen.getByText('activateTrial');
      await user.click(activateButton);

      await waitFor(() => {
        expect(screen.getByText('activating')).toBeInTheDocument();
      });

      await waitFor(() => {
        expect(telegramMock.showAlert).toHaveBeenCalledWith('trialActivated');
      });

      expect(telegramMock.HapticFeedback.impactOccurred).toHaveBeenCalledWith('heavy');
    });

    it('test_shows_error_when_trial_activation_fails', async () => {
      const user = userEvent.setup();

      server.use(
        http.post(`${API_BASE}/trial/activate`, () => {
          return HttpResponse.json(
            { detail: 'Trial already used' },
            { status: 400 }
          );
        })
      );

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('activateTrial')).toBeInTheDocument();
      });

      const activateButton = screen.getByText('activateTrial');
      await user.click(activateButton);

      await waitFor(() => {
        expect(telegramMock.showAlert).toHaveBeenCalledWith('Trial already used');
      });
    });

    it('test_disables_button_while_activating', async () => {
      const user = userEvent.setup();

      server.use(
        http.post(`${API_BASE}/trial/activate`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({ message: 'Success' });
        })
      );

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('activateTrial')).toBeInTheDocument();
      });

      const activateButton = screen.getByText('activateTrial');
      await user.click(activateButton);

      await waitFor(() => {
        const button = screen.getByText('activating').closest('button');
        expect(button).toBeDisabled();
      });
    });
  });

  describe('Plans Display', () => {
    beforeEach(() => {
      server.use(
        http.get(`${API_BASE}/plans`, () => {
          return HttpResponse.json(mockPlans);
        }),
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json(mockTrialData);
        })
      );
    });

    it('test_displays_available_plans_title', async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('availablePlans')).toBeInTheDocument();
      });
    });

    it('test_displays_all_plan_cards', async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('Basic Plan')).toBeInTheDocument();
      });

      expect(screen.getByText('Premium Plan')).toBeInTheDocument();
    });

    it('test_displays_plan_template_types', async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('vless')).toBeInTheDocument();
      });

      expect(screen.getByText('vmess')).toBeInTheDocument();
    });

    it('test_displays_contact_for_price_placeholder', async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getAllByText('contactForPrice')).toHaveLength(2);
      });
    });

    it('test_displays_purchase_buttons_for_all_plans', async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getAllByText('purchasePlan')).toHaveLength(2);
      });
    });

    it('test_shows_empty_state_when_no_plans', async () => {
      server.use(
        http.get(`${API_BASE}/plans`, () => {
          return HttpResponse.json([]);
        })
      );

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('noPlans')).toBeInTheDocument();
      });
    });
  });

  describe('Plan Purchase Flow', () => {
    beforeEach(() => {
      server.use(
        http.get(`${API_BASE}/plans`, () => {
          return HttpResponse.json(mockPlans);
        }),
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json(mockTrialData);
        })
      );
    });

    it('test_creates_invoice_and_opens_payment_url', async () => {
      const user = userEvent.setup();

      server.use(
        http.post(`${API_BASE}/payments/invoices`, () => {
          return HttpResponse.json({
            payment_url: 'https://t.me/CryptoBot?start=pay_ABC123',
            invoice_id: 'inv-123',
          });
        })
      );

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getAllByText('purchasePlan')).toHaveLength(2);
      });

      const purchaseButtons = screen.getAllByText('purchasePlan');
      await user.click(purchaseButtons[0]);

      await waitFor(() => {
        expect(telegramMock.openTelegramLink).toHaveBeenCalledWith(
          'https://t.me/CryptoBot?start=pay_ABC123'
        );
      });

      expect(telegramMock.HapticFeedback.impactOccurred).toHaveBeenCalledWith('medium');
    });

    it('test_shows_processing_state_during_purchase', async () => {
      const user = userEvent.setup();

      server.use(
        http.post(`${API_BASE}/payments/invoices`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({
            payment_url: 'https://t.me/CryptoBot',
            invoice_id: 'inv-123',
          });
        })
      );

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getAllByText('purchasePlan')).toHaveLength(2);
      });

      const purchaseButtons = screen.getAllByText('purchasePlan');
      await user.click(purchaseButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('processing')).toBeInTheDocument();
      });
    });

    it('test_shows_error_when_payment_fails', async () => {
      const user = userEvent.setup();

      server.use(
        http.post(`${API_BASE}/payments/invoices`, () => {
          return HttpResponse.json(
            { detail: 'Payment service unavailable' },
            { status: 500 }
          );
        })
      );

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getAllByText('purchasePlan')).toHaveLength(2);
      });

      const purchaseButtons = screen.getAllByText('purchasePlan');
      await user.click(purchaseButtons[0]);

      await waitFor(() => {
        expect(telegramMock.showAlert).toHaveBeenCalledWith('Payment service unavailable');
      });
    });

    it('test_triggers_haptic_on_purchase_button_click', async () => {
      const user = userEvent.setup();

      server.use(
        http.post(`${API_BASE}/payments/invoices`, () => {
          return HttpResponse.json({
            payment_url: 'https://t.me/CryptoBot',
            invoice_id: 'inv-123',
          });
        })
      );

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getAllByText('purchasePlan')).toHaveLength(2);
      });

      const purchaseButtons = screen.getAllByText('purchasePlan');
      await user.click(purchaseButtons[0]);

      expect(telegramMock.HapticFeedback.impactOccurred).toHaveBeenCalled();
    });
  });

  describe('Promo Code Validation', () => {
    beforeEach(() => {
      server.use(
        http.get(`${API_BASE}/plans`, () => {
          return HttpResponse.json(mockPlans);
        }),
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json(mockTrialData);
        })
      );
    });

    it('test_displays_promo_code_input_section', async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('havePromoCode')).toBeInTheDocument();
      });

      expect(screen.getByPlaceholderText('promoCodePlaceholder')).toBeInTheDocument();
      expect(screen.getByText('apply')).toBeInTheDocument();
    });

    it('test_converts_promo_code_to_uppercase', async () => {
      const user = userEvent.setup();

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByPlaceholderText('promoCodePlaceholder')).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText('promoCodePlaceholder') as HTMLInputElement;
      await user.type(input, 'promo20');

      expect(input.value).toBe('PROMO20');
    });

    it('test_validates_promo_code_successfully', async () => {
      const user = userEvent.setup();

      server.use(
        http.post(`${API_BASE}/promo/validate`, () => {
          return HttpResponse.json({
            discount_amount: 5.99,
            valid: true,
          });
        })
      );

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getAllByText('purchasePlan')).toHaveLength(2);
      });

      // First select a plan
      const purchaseButtons = screen.getAllByText('purchasePlan');
      await user.click(purchaseButtons[0]);

      // Then apply promo code
      const promoInput = screen.getByPlaceholderText('promoCodePlaceholder');
      await user.type(promoInput, 'SAVE5');

      const applyButton = screen.getByText('apply');
      await user.click(applyButton);

      await waitFor(() => {
        expect(screen.getByText(/discountApplied/)).toBeInTheDocument();
      });

      expect(telegramMock.HapticFeedback.impactOccurred).toHaveBeenCalledWith('medium');
    });

    it('test_shows_alert_when_no_plan_selected', async () => {
      const user = userEvent.setup();

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByPlaceholderText('promoCodePlaceholder')).toBeInTheDocument();
      });

      const promoInput = screen.getByPlaceholderText('promoCodePlaceholder');
      await user.type(promoInput, 'PROMO');

      const applyButton = screen.getByText('apply');
      await user.click(applyButton);

      await waitFor(() => {
        expect(telegramMock.showAlert).toHaveBeenCalledWith('selectPlanFirst');
      });
    });

    it('test_shows_error_for_invalid_promo_code', async () => {
      const user = userEvent.setup();

      server.use(
        http.post(`${API_BASE}/promo/validate`, () => {
          return HttpResponse.json(
            { detail: 'Invalid promo code' },
            { status: 404 }
          );
        })
      );

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getAllByText('purchasePlan')).toHaveLength(2);
      });

      // Select a plan first
      const purchaseButtons = screen.getAllByText('purchasePlan');
      await user.click(purchaseButtons[0]);

      const promoInput = screen.getByPlaceholderText('promoCodePlaceholder');
      await user.type(promoInput, 'INVALID');

      const applyButton = screen.getByText('apply');
      await user.click(applyButton);

      await waitFor(() => {
        expect(telegramMock.showAlert).toHaveBeenCalledWith('Invalid promo code');
      });
    });

    it('test_disables_apply_button_without_code', async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('apply')).toBeInTheDocument();
      });

      const applyButton = screen.getByText('apply').closest('button');
      expect(applyButton).toBeDisabled();
    });

    it('test_shows_loading_spinner_while_validating', async () => {
      const user = userEvent.setup();

      server.use(
        http.post(`${API_BASE}/promo/validate`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({ discount_amount: 5, valid: true });
        })
      );

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getAllByText('purchasePlan')).toHaveLength(2);
      });

      // Select a plan
      const purchaseButtons = screen.getAllByText('purchasePlan');
      await user.click(purchaseButtons[0]);

      const promoInput = screen.getByPlaceholderText('promoCodePlaceholder');
      await user.type(promoInput, 'CODE');

      const applyButton = screen.getByText('apply');
      await user.click(applyButton);

      await waitFor(() => {
        const loadingSpinner = document.querySelector('.animate-spin');
        expect(loadingSpinner).toBeInTheDocument();
      });
    });
  });

  describe('Invite Code Redemption', () => {
    beforeEach(() => {
      server.use(
        http.get(`${API_BASE}/plans`, () => {
          return HttpResponse.json(mockPlans);
        }),
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json(mockTrialData);
        })
      );
    });

    it('test_displays_invite_code_input_section', async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('haveInviteCode')).toBeInTheDocument();
      });

      expect(screen.getByPlaceholderText('inviteCodePlaceholder')).toBeInTheDocument();
      expect(screen.getByText('redeem')).toBeInTheDocument();
      expect(screen.getByText('inviteCodeNote')).toBeInTheDocument();
    });

    it('test_converts_invite_code_to_uppercase', async () => {
      const user = userEvent.setup();

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByPlaceholderText('inviteCodePlaceholder')).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText('inviteCodePlaceholder') as HTMLInputElement;
      await user.type(input, 'invite123');

      expect(input.value).toBe('INVITE123');
    });

    it('test_redeems_invite_code_successfully', async () => {
      const user = userEvent.setup();

      server.use(
        http.post(`${API_BASE}/invites/redeem`, () => {
          return HttpResponse.json({
            message: 'Invite redeemed',
            free_days: 7,
          });
        })
      );

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByPlaceholderText('inviteCodePlaceholder')).toBeInTheDocument();
      });

      const inviteInput = screen.getByPlaceholderText('inviteCodePlaceholder');
      await user.type(inviteInput, 'FRIEND2024');

      const redeemButton = screen.getByText('redeem');
      await user.click(redeemButton);

      await waitFor(() => {
        expect(telegramMock.showAlert).toHaveBeenCalledWith(
          expect.stringContaining('inviteRedeemed')
        );
      });

      expect(telegramMock.HapticFeedback.impactOccurred).toHaveBeenCalledWith('heavy');
    });

    it('test_clears_input_after_successful_redemption', async () => {
      const user = userEvent.setup();

      server.use(
        http.post(`${API_BASE}/invites/redeem`, () => {
          return HttpResponse.json({
            message: 'Success',
            free_days: 7,
          });
        })
      );

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByPlaceholderText('inviteCodePlaceholder')).toBeInTheDocument();
      });

      const inviteInput = screen.getByPlaceholderText('inviteCodePlaceholder') as HTMLInputElement;
      await user.type(inviteInput, 'CODE');

      const redeemButton = screen.getByText('redeem');
      await user.click(redeemButton);

      await waitFor(() => {
        expect(inviteInput.value).toBe('');
      });
    });

    it('test_shows_error_for_invalid_invite_code', async () => {
      const user = userEvent.setup();

      server.use(
        http.post(`${API_BASE}/invites/redeem`, () => {
          return HttpResponse.json(
            { detail: 'Invalid invite code' },
            { status: 404 }
          );
        })
      );

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByPlaceholderText('inviteCodePlaceholder')).toBeInTheDocument();
      });

      const inviteInput = screen.getByPlaceholderText('inviteCodePlaceholder');
      await user.type(inviteInput, 'INVALID');

      const redeemButton = screen.getByText('redeem');
      await user.click(redeemButton);

      await waitFor(() => {
        expect(telegramMock.showAlert).toHaveBeenCalledWith('Invalid invite code');
      });
    });

    it('test_disables_redeem_button_without_code', async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('redeem')).toBeInTheDocument();
      });

      const redeemButton = screen.getByText('redeem').closest('button');
      expect(redeemButton).toBeDisabled();
    });

    it('test_shows_loading_spinner_while_redeeming', async () => {
      const user = userEvent.setup();

      server.use(
        http.post(`${API_BASE}/invites/redeem`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({ message: 'Success', free_days: 7 });
        })
      );

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByPlaceholderText('inviteCodePlaceholder')).toBeInTheDocument();
      });

      const inviteInput = screen.getByPlaceholderText('inviteCodePlaceholder');
      await user.type(inviteInput, 'CODE');

      const redeemButton = screen.getByText('redeem');
      await user.click(redeemButton);

      await waitFor(() => {
        const loadingSpinner = document.querySelector('.animate-spin');
        expect(loadingSpinner).toBeInTheDocument();
      });
    });
  });

  describe('Theme Integration', () => {
    beforeEach(() => {
      server.use(
        http.get(`${API_BASE}/plans`, () => {
          return HttpResponse.json(mockPlans);
        }),
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json(mockTrialData);
        })
      );
    });

    it('test_uses_dark_theme_by_default', async () => {
      const { container } = render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('availablePlans')).toBeInTheDocument();
      });

      const cards = container.querySelectorAll('[class*="bg-[var(--tg-bg-color"]');
      expect(cards.length).toBeGreaterThan(0);
    });

    it('test_uses_light_theme_when_telegram_in_light_mode', async () => {
      cleanupTelegramWebAppMock();
      setupTelegramWebAppMock({ colorScheme: 'light' });

      const { container } = render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('availablePlans')).toBeInTheDocument();
      });

      expect(container.querySelector('[class*="bg-[var(--tg-bg-color"]')).toBeInTheDocument();
    });
  });
});
