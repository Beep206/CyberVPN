/**
 * WithdrawalModal Component Tests (TOB-2)
 *
 * Tests the wallet withdrawal flow:
 * - Modal rendering with current balance
 * - Withdrawal API call with amount validation
 * - Form validation (minimum amount, exceeds balance)
 * - Success and error handling
 * - Withdrawal method selection
 *
 * Depends on: FG-2 (Wallet withdrawal implementation)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WithdrawalModal } from '../WithdrawalModal';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

// Mock Modal component
vi.mock('@/shared/ui/modal', () => ({
  Modal: ({ isOpen, children }: { isOpen: boolean; children: React.ReactNode }) =>
    isOpen ? <div data-testid="modal">{children}</div> : null,
}));

const API_BASE = 'http://localhost:8000/api/v1';

describe('WithdrawalModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    server.resetHandlers();
  });

  describe('Rendering', () => {
    it('test_renders_withdrawal_form_with_balance', () => {
      render(
        <WithdrawalModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
          currentBalance={250.50}
        />
      );

      expect(screen.getByText(/Available Balance/i)).toBeInTheDocument();
      expect(screen.getByText(/250.50/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Amount|amount/i)).toBeInTheDocument();
    });

    it('test_renders_withdrawal_button', () => {
      render(
        <WithdrawalModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
          currentBalance={100.00}
        />
      );

      expect(screen.getByRole('button', { name: /Request Withdrawal/i })).toBeInTheDocument();
    });

    it('test_renders_cancel_button', () => {
      render(
        <WithdrawalModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
          currentBalance={100.00}
        />
      );

      expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
    });

    it('test_displays_withdrawal_method_selector', () => {
      render(
        <WithdrawalModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
          currentBalance={100.00}
        />
      );

      // Withdrawal method selector should be present
      expect(screen.getByText(/Withdrawal Method|Method/i)).toBeInTheDocument();
    });

    it('test_displays_minimum_withdrawal_info', () => {
      // TODO: Render modal
      // TODO: Assert minimum withdrawal amount is shown
    });
  });

  describe('Withdrawal Flow', () => {
    it('test_withdrawal_button_calls_api_with_amount', async () => {
      const user = userEvent.setup({ delay: null });
      let capturedRequest: any = null;

      server.use(
        http.post(`${API_BASE}/wallet/withdraw`, async ({ request }) => {
          capturedRequest = await request.json();
          return HttpResponse.json({ id: 'wd_123', status: 'pending' }, { status: 201 });
        })
      );

      render(
        <WithdrawalModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
          currentBalance={100.00}
        />
      );

      const amountInput = screen.getByLabelText(/Amount|amount/i);
      await user.type(amountInput, '50');

      // Fill in required wallet address for crypto method
      const addressInput = screen.getByLabelText(/Wallet Address|address/i);
      await user.type(addressInput, 'TRXWalletAddress123456789');

      const withdrawButton = screen.getByRole('button', { name: /Request Withdrawal/i });
      await user.click(withdrawButton);

      await waitFor(() => {
        expect(capturedRequest).not.toBeNull();
        expect(capturedRequest.amount).toBe(50);
        expect(capturedRequest.method).toBe('crypto');
      });
    });

    it('test_withdrawal_includes_selected_method', async () => {
      // TODO: Setup MSW handler to capture request
      // TODO: Render modal
      // TODO: Select withdrawal method (e.g., cryptobot)
      // TODO: Enter amount
      // TODO: Click withdraw button
      // TODO: Assert API request includes method
    });

    it('test_displays_loading_state_during_withdrawal', async () => {
      const user = userEvent.setup({ delay: null });

      server.use(
        http.post(`${API_BASE}/wallet/withdraw`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 1000));
          return HttpResponse.json({ id: 'wd_delay', status: 'pending' }, { status: 201 });
        })
      );

      render(
        <WithdrawalModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
          currentBalance={100.00}
        />
      );

      const amountInput = screen.getByLabelText(/Amount|amount/i);
      await user.type(amountInput, '50');

      const addressInput = screen.getByLabelText(/Wallet Address|address/i);
      await user.type(addressInput, 'TRXAddr123');

      const withdrawButton = screen.getByRole('button', { name: /Request Withdrawal/i });
      await user.click(withdrawButton);

      // Button should be disabled during submission
      expect(withdrawButton).toBeDisabled();
    });

    it('test_displays_success_message_after_withdrawal', async () => {
      // TODO: Setup MSW handler for successful withdrawal
      // TODO: Render modal
      // TODO: Submit withdrawal
      // TODO: Wait for success
      // TODO: Assert success message is displayed
    });

    it('test_calls_onSuccess_callback_after_withdrawal', async () => {
      // TODO: Setup MSW handler for success
      // TODO: Mock onSuccess callback
      // TODO: Render modal with onSuccess prop
      // TODO: Submit withdrawal
      // TODO: Assert onSuccess was called
    });

    it('test_closes_modal_on_cancel_button_click', async () => {
      const user = userEvent.setup({ delay: null });
      const onClose = vi.fn();

      render(
        <WithdrawalModal
          isOpen={true}
          onClose={onClose}
          onSuccess={vi.fn()}
          currentBalance={100.00}
        />
      );

      const cancelButton = screen.getByRole('button', { name: /Cancel/i });
      await user.click(cancelButton);

      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('Validation', () => {
    it('test_validates_withdrawal_amount_minimum', async () => {
      const user = userEvent.setup({ delay: null });

      render(
        <WithdrawalModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
          currentBalance={100.00}
        />
      );

      const amountInput = screen.getByLabelText(/Amount|amount/i);
      await user.type(amountInput, '5');

      // Fill in wallet address
      const addressInput = screen.getByLabelText(/Wallet Address|address/i);
      await user.type(addressInput, 'TRXWalletAddress123');

      const withdrawButton = screen.getByRole('button', { name: /Request Withdrawal/i });
      await user.click(withdrawButton);

      await waitFor(() => {
        expect(screen.getByText(/Minimum withdrawal amount is \$10/i)).toBeInTheDocument();
      });
    });

    it('test_validates_withdrawal_exceeds_balance', async () => {
      const user = userEvent.setup({ delay: null });

      render(
        <WithdrawalModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
          currentBalance={100.00}
        />
      );

      const amountInput = screen.getByLabelText(/Amount|amount/i);
      await user.type(amountInput, '150');

      // Fill in wallet address
      const addressInput = screen.getByLabelText(/Wallet Address|address/i);
      await user.type(addressInput, 'TRXWalletAddress456');

      const withdrawButton = screen.getByRole('button', { name: /Request Withdrawal/i });
      await user.click(withdrawButton);

      await waitFor(() => {
        expect(screen.getByText(/Insufficient balance/i)).toBeInTheDocument();
      });
    });

    it('test_validates_amount_is_positive', async () => {
      // TODO: Render modal
      // TODO: Enter negative or zero amount
      // TODO: Click withdraw button
      // TODO: Assert validation error
    });

    it('test_validates_amount_is_numeric', async () => {
      // TODO: Render modal
      // TODO: Enter non-numeric text
      // TODO: Assert input validation or conversion
    });

    it('test_withdrawal_button_disabled_without_amount', () => {
      // TODO: Render modal
      // TODO: Assert withdraw button is disabled when amount is empty
    });

    it('test_prevents_double_submission', async () => {
      // TODO: Setup MSW handler with delay
      // TODO: Render modal
      // TODO: Submit withdrawal
      // TODO: Try to submit again immediately
      // TODO: Assert only one API call was made
    });
  });

  describe('Error Handling', () => {
    it('test_displays_error_on_insufficient_balance', async () => {
      // TODO: Setup MSW handler to return 422 insufficient balance
      // TODO: Render modal
      // TODO: Submit withdrawal
      // TODO: Wait for error
      // TODO: Assert specific error message about insufficient balance
    });

    it('test_displays_error_on_below_minimum', async () => {
      // TODO: Setup MSW handler to return 422 below minimum
      // TODO: Render modal
      // TODO: Submit withdrawal with amount below server minimum
      // TODO: Assert error message about minimum amount
    });

    it('test_displays_generic_api_error', async () => {
      // TODO: Setup MSW handler to return 400 or 500
      // TODO: Render modal
      // TODO: Submit withdrawal
      // TODO: Assert generic error message is displayed
    });

    it('test_displays_network_error_message', async () => {
      // TODO: Setup MSW handler to throw network error
      // TODO: Render modal
      // TODO: Submit withdrawal
      // TODO: Assert network error message
    });

    it('test_error_message_clears_on_retry', async () => {
      // TODO: Setup MSW handler to fail first, succeed second
      // TODO: Render modal
      // TODO: Submit withdrawal (fail)
      // TODO: Assert error displayed
      // TODO: Submit again (succeed)
      // TODO: Assert error cleared
    });

    it('test_displays_rate_limit_error', async () => {
      // TODO: Setup MSW handler to return 429 rate limit
      // TODO: Render modal
      // TODO: Submit withdrawal
      // TODO: Assert rate limit error with retry time
    });
  });

  describe('Withdrawal Method Selection', () => {
    it('test_displays_available_withdrawal_methods', () => {
      // TODO: Render modal
      // TODO: Assert cryptobot method is available
      // TODO: Assert other methods (if any) are listed
    });

    it('test_selects_default_withdrawal_method', () => {
      // TODO: Render modal
      // TODO: Assert a default method is selected (e.g., cryptobot)
    });

    it('test_changes_withdrawal_method', async () => {
      // TODO: Render modal with multiple methods
      // TODO: Select different method
      // TODO: Assert selected method updates
    });

    it('test_withdrawal_method_affects_api_call', async () => {
      // TODO: Setup MSW handler to capture request
      // TODO: Render modal
      // TODO: Select specific method
      // TODO: Submit withdrawal
      // TODO: Assert API request contains selected method
    });
  });

  describe('Balance Display', () => {
    it('test_displays_current_balance_in_usd', () => {
      // TODO: Render modal with balance=250.50
      // TODO: Assert "$250.50" or "250.50 USD" is displayed
    });

    it('test_displays_available_balance_after_pending', () => {
      // TODO: Render modal with balance=100, pending=20
      // TODO: Assert available balance is shown (100 - 20 = 80)
    });

    it('test_updates_max_amount_based_on_balance', () => {
      // TODO: Render modal with balance=100
      // TODO: Assert max withdrawal amount is 100 or less
      // TODO: Try to enter amount > balance
      // TODO: Assert validation error
    });
  });
});
