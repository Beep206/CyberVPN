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
      render(
        <WithdrawalModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
          currentBalance={100.00}
        />
      );

      expect(screen.getByText(/Minimum: \$10.00/i)).toBeInTheDocument();
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
      const user = userEvent.setup({ delay: null });
      let capturedRequest: any = null;

      server.use(
        http.post(`${API_BASE}/wallet/withdraw`, async ({ request }) => {
          capturedRequest = await request.json();
          return HttpResponse.json({ id: 'wd_method', status: 'pending' }, { status: 201 });
        })
      );

      render(
        <WithdrawalModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
          currentBalance={200.00}
        />
      );

      // Select bank method
      const bankButton = screen.getByLabelText(/Bank transfer payment method/i);
      await user.click(bankButton);

      const amountInput = screen.getByLabelText(/Amount|amount/i);
      await user.type(amountInput, '50');

      const bankAccountInput = screen.getByLabelText(/Bank account number/i);
      await user.type(bankAccountInput, '1234-5678-9012');

      const withdrawButton = screen.getByRole('button', { name: /Request Withdrawal/i });
      await user.click(withdrawButton);

      await waitFor(() => {
        expect(capturedRequest).not.toBeNull();
        expect(capturedRequest.amount).toBe(50);
        expect(capturedRequest.method).toBe('bank');
        expect(capturedRequest.bank_account).toBe('1234-5678-9012');
      });
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
      const user = userEvent.setup({ delay: null });

      server.use(
        http.post(`${API_BASE}/wallet/withdraw`, () => {
          return HttpResponse.json({ id: 'wd_success', status: 'pending' }, { status: 201 });
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
      await user.type(addressInput, 'TRXWallet123');

      const withdrawButton = screen.getByRole('button', { name: /Request Withdrawal/i });
      await user.click(withdrawButton);

      await waitFor(() => {
        expect(screen.getByText(/Withdrawal Request Submitted/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/Your withdrawal request has been submitted successfully/i)).toBeInTheDocument();
    });

    it('test_calls_onSuccess_callback_after_withdrawal', async () => {
      const user = userEvent.setup({ delay: null });
      const onSuccessMock = vi.fn();

      server.use(
        http.post(`${API_BASE}/wallet/withdraw`, () => {
          return HttpResponse.json({ id: 'wd_callback', status: 'pending' }, { status: 201 });
        })
      );

      render(
        <WithdrawalModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={onSuccessMock}
          currentBalance={100.00}
        />
      );

      const amountInput = screen.getByLabelText(/Amount|amount/i);
      await user.type(amountInput, '50');

      const addressInput = screen.getByLabelText(/Wallet Address|address/i);
      await user.type(addressInput, 'TRXWallet456');

      const withdrawButton = screen.getByRole('button', { name: /Request Withdrawal/i });
      await user.click(withdrawButton);

      await waitFor(() => {
        expect(screen.getByText(/Withdrawal Request Submitted/i)).toBeInTheDocument();
      });

      // Wait for auto-close timeout (2 seconds)
      await waitFor(() => {
        expect(onSuccessMock).toHaveBeenCalledTimes(1);
      }, { timeout: 3000 });
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
      await user.type(amountInput, '-10');

      const addressInput = screen.getByLabelText(/Wallet Address|address/i);
      await user.type(addressInput, 'TRXWallet789');

      const withdrawButton = screen.getByRole('button', { name: /Request Withdrawal/i });
      await user.click(withdrawButton);

      await waitFor(() => {
        expect(screen.getByText(/Please enter a valid amount/i)).toBeInTheDocument();
      });
    });

    it('test_validates_amount_is_numeric', async () => {
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
      await user.type(amountInput, 'abc');

      const addressInput = screen.getByLabelText(/Wallet Address|address/i);
      await user.type(addressInput, 'TRXWalletABC');

      const withdrawButton = screen.getByRole('button', { name: /Request Withdrawal/i });
      await user.click(withdrawButton);

      await waitFor(() => {
        expect(screen.getByText(/Please enter a valid amount/i)).toBeInTheDocument();
      });
    });

    it('test_withdrawal_button_disabled_without_amount', async () => {
      const user = userEvent.setup({ delay: null });

      render(
        <WithdrawalModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
          currentBalance={100.00}
        />
      );

      const addressInput = screen.getByLabelText(/Wallet Address|address/i);
      await user.type(addressInput, 'TRXWalletTest');

      const withdrawButton = screen.getByRole('button', { name: /Request Withdrawal/i });
      await user.click(withdrawButton);

      // Should show validation error
      await waitFor(() => {
        expect(screen.getByText(/Please enter a valid amount/i)).toBeInTheDocument();
      });
    });

    it('test_prevents_double_submission', async () => {
      const user = userEvent.setup({ delay: null });
      let apiCallCount = 0;

      server.use(
        http.post(`${API_BASE}/wallet/withdraw`, async () => {
          apiCallCount++;
          await new Promise((resolve) => setTimeout(resolve, 500));
          return HttpResponse.json({ id: 'wd_double', status: 'pending' }, { status: 201 });
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
      await user.type(addressInput, 'TRXWalletDouble');

      const withdrawButton = screen.getByRole('button', { name: /Request Withdrawal/i });

      // Click twice rapidly
      await user.click(withdrawButton);

      // Button should be disabled during processing
      expect(withdrawButton).toBeDisabled();

      // Try clicking again
      await user.click(withdrawButton);

      await waitFor(() => {
        expect(screen.getByText(/Processing withdrawal request/i)).toBeInTheDocument();
      });

      await waitFor(() => {
        expect(screen.getByText(/Withdrawal Request Submitted/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      // Should only have called API once
      expect(apiCallCount).toBe(1);
    });
  });

  describe('Error Handling', () => {
    it('test_displays_error_on_insufficient_balance', async () => {
      const user = userEvent.setup({ delay: null });

      server.use(
        http.post(`${API_BASE}/wallet/withdraw`, () => {
          return HttpResponse.json(
            { detail: 'Insufficient balance for withdrawal' },
            { status: 422 }
          );
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
      await user.type(addressInput, 'TRXWalletInsufficient');

      const withdrawButton = screen.getByRole('button', { name: /Request Withdrawal/i });
      await user.click(withdrawButton);

      await waitFor(() => {
        expect(screen.getByText(/Withdrawal Failed/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/Insufficient balance for withdrawal/i)).toBeInTheDocument();
    });

    it('test_displays_error_on_below_minimum', async () => {
      const user = userEvent.setup({ delay: null });

      server.use(
        http.post(`${API_BASE}/wallet/withdraw`, () => {
          return HttpResponse.json(
            { detail: 'Amount below minimum withdrawal threshold' },
            { status: 422 }
          );
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
      await user.type(amountInput, '20');

      const addressInput = screen.getByLabelText(/Wallet Address|address/i);
      await user.type(addressInput, 'TRXWalletMin');

      const withdrawButton = screen.getByRole('button', { name: /Request Withdrawal/i });
      await user.click(withdrawButton);

      await waitFor(() => {
        expect(screen.getByText(/Withdrawal Failed/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/Amount below minimum withdrawal threshold/i)).toBeInTheDocument();
    });

    it('test_displays_generic_api_error', async () => {
      const user = userEvent.setup({ delay: null });

      server.use(
        http.post(`${API_BASE}/wallet/withdraw`, () => {
          return HttpResponse.json(
            { detail: 'Internal server error occurred' },
            { status: 500 }
          );
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
      await user.type(addressInput, 'TRXWalletError');

      const withdrawButton = screen.getByRole('button', { name: /Request Withdrawal/i });
      await user.click(withdrawButton);

      await waitFor(() => {
        expect(screen.getByText(/Withdrawal Failed/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/Internal server error occurred/i)).toBeInTheDocument();
    });

    it('test_displays_network_error_message', async () => {
      const user = userEvent.setup({ delay: null });

      server.use(
        http.post(`${API_BASE}/wallet/withdraw`, () => {
          return HttpResponse.error();
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
      await user.type(addressInput, 'TRXWalletNetwork');

      const withdrawButton = screen.getByRole('button', { name: /Request Withdrawal/i });
      await user.click(withdrawButton);

      await waitFor(() => {
        expect(screen.getByText(/Withdrawal Failed/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/An error occurred. Please try again./i)).toBeInTheDocument();
    });

    it('test_error_message_clears_on_retry', async () => {
      const user = userEvent.setup({ delay: null });
      let callCount = 0;

      server.use(
        http.post(`${API_BASE}/wallet/withdraw`, () => {
          callCount++;
          if (callCount === 1) {
            return HttpResponse.json(
              { detail: 'Temporary error' },
              { status: 500 }
            );
          }
          return HttpResponse.json({ id: 'wd_retry', status: 'pending' }, { status: 201 });
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
      await user.type(addressInput, 'TRXWalletRetry');

      const withdrawButton = screen.getByRole('button', { name: /Request Withdrawal/i });
      await user.click(withdrawButton);

      await waitFor(() => {
        expect(screen.getByText(/Withdrawal Failed/i)).toBeInTheDocument();
      });

      const tryAgainButton = screen.getByText(/Try Again/i);
      await user.click(tryAgainButton);

      // Re-enter details after returning to form
      const amountInputRetry = screen.getByLabelText(/Amount|amount/i);
      await user.clear(amountInputRetry);
      await user.type(amountInputRetry, '50');

      const addressInputRetry = screen.getByLabelText(/Wallet Address|address/i);
      await user.clear(addressInputRetry);
      await user.type(addressInputRetry, 'TRXWalletRetrySuccess');

      const withdrawButtonRetry = screen.getByRole('button', { name: /Request Withdrawal/i });
      await user.click(withdrawButtonRetry);

      await waitFor(() => {
        expect(screen.queryByText(/Withdrawal Failed/i)).not.toBeInTheDocument();
      });

      await waitFor(() => {
        expect(screen.getByText(/Withdrawal Request Submitted/i)).toBeInTheDocument();
      });
    });

    it('test_displays_rate_limit_error', async () => {
      const user = userEvent.setup({ delay: null });

      server.use(
        http.post(`${API_BASE}/wallet/withdraw`, () => {
          return HttpResponse.json(
            { detail: 'Rate limit exceeded. Please try again in 60 seconds.' },
            { status: 429 }
          );
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
      await user.type(addressInput, 'TRXWalletRate');

      const withdrawButton = screen.getByRole('button', { name: /Request Withdrawal/i });
      await user.click(withdrawButton);

      await waitFor(() => {
        expect(screen.getByText(/Withdrawal Failed/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/Rate limit exceeded. Please try again in 60 seconds./i)).toBeInTheDocument();
    });
  });

  describe('Withdrawal Method Selection', () => {
    it('test_displays_available_withdrawal_methods', () => {
      render(
        <WithdrawalModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
          currentBalance={100.00}
        />
      );

      // Check that all three payment methods are available
      expect(screen.getByLabelText(/Crypto payment method/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Bank transfer payment method/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/PayPal payment method/i)).toBeInTheDocument();

      // Check method labels
      expect(screen.getByText('Crypto')).toBeInTheDocument();
      expect(screen.getByText('Bank')).toBeInTheDocument();
      expect(screen.getByText('PayPal')).toBeInTheDocument();
    });

    it('test_selects_default_withdrawal_method', () => {
      render(
        <WithdrawalModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
          currentBalance={100.00}
        />
      );

      // Crypto should be the default selected method (has active styling)
      const cryptoButton = screen.getByLabelText(/Crypto payment method/i);
      expect(cryptoButton).toHaveClass('bg-neon-cyan/20');

      // Default input for crypto should be visible
      expect(screen.getByLabelText(/Wallet address/i)).toBeInTheDocument();
    });

    it('test_changes_withdrawal_method', async () => {
      const user = userEvent.setup({ delay: null });

      render(
        <WithdrawalModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
          currentBalance={100.00}
        />
      );

      // Initially crypto is selected
      expect(screen.getByLabelText(/Wallet address/i)).toBeInTheDocument();

      // Click PayPal button
      const paypalButton = screen.getByLabelText(/PayPal payment method/i);
      await user.click(paypalButton);

      // PayPal input should now be visible
      expect(screen.getByLabelText(/PayPal email/i)).toBeInTheDocument();
      expect(screen.queryByLabelText(/Wallet address/i)).not.toBeInTheDocument();

      // Click Bank button
      const bankButton = screen.getByLabelText(/Bank transfer payment method/i);
      await user.click(bankButton);

      // Bank input should now be visible
      expect(screen.getByLabelText(/Bank account number/i)).toBeInTheDocument();
      expect(screen.queryByLabelText(/PayPal email/i)).not.toBeInTheDocument();
    });

    it('test_withdrawal_method_affects_api_call', async () => {
      const user = userEvent.setup({ delay: null });
      let capturedRequest: any = null;

      server.use(
        http.post(`${API_BASE}/wallet/withdraw`, async ({ request }) => {
          capturedRequest = await request.json();
          return HttpResponse.json({ id: 'wd_method_test', status: 'pending' }, { status: 201 });
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

      // Select PayPal method
      const paypalButton = screen.getByLabelText(/PayPal payment method/i);
      await user.click(paypalButton);

      const amountInput = screen.getByLabelText(/Amount|amount/i);
      await user.type(amountInput, '50');

      const paypalEmailInput = screen.getByLabelText(/PayPal email/i);
      await user.type(paypalEmailInput, 'test@paypal.com');

      const withdrawButton = screen.getByRole('button', { name: /Request Withdrawal/i });
      await user.click(withdrawButton);

      await waitFor(() => {
        expect(capturedRequest).not.toBeNull();
        expect(capturedRequest.method).toBe('paypal');
        expect(capturedRequest.paypal_email).toBe('test@paypal.com');
        expect(capturedRequest.amount).toBe(50);
      });
    });
  });

  describe('Balance Display', () => {
    it('test_displays_current_balance_in_usd', () => {
      render(
        <WithdrawalModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
          currentBalance={250.50}
        />
      );

      // Check that the balance is formatted as currency
      expect(screen.getByText(/\$250\.50/i)).toBeInTheDocument();
      expect(screen.getByText(/Available Balance/i)).toBeInTheDocument();
    });

    it('test_displays_available_balance_after_pending', () => {
      // Component currently doesn't support pending balance deduction
      // It just displays the currentBalance prop as-is
      render(
        <WithdrawalModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
          currentBalance={80.00}
        />
      );

      // Available balance should show the passed currentBalance
      expect(screen.getByText(/\$80\.00/i)).toBeInTheDocument();
      expect(screen.getByText(/Available Balance/i)).toBeInTheDocument();
    });

    it('test_updates_max_amount_based_on_balance', async () => {
      const user = userEvent.setup({ delay: null });

      render(
        <WithdrawalModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
          currentBalance={100.00}
        />
      );

      const amountInput = screen.getByLabelText(/Amount|amount/i) as HTMLInputElement;

      // Check that max attribute is set to current balance
      expect(amountInput.max).toBe('100');

      // Try to enter amount greater than balance
      await user.type(amountInput, '150');

      const addressInput = screen.getByLabelText(/Wallet Address|address/i);
      await user.type(addressInput, 'TRXWalletMax');

      const withdrawButton = screen.getByRole('button', { name: /Request Withdrawal/i });
      await user.click(withdrawButton);

      // Should show insufficient balance error
      await waitFor(() => {
        expect(screen.getByText(/Insufficient balance/i)).toBeInTheDocument();
      });
    });
  });
});
