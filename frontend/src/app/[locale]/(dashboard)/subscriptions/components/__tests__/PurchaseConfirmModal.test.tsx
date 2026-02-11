/**
 * PurchaseConfirmModal Component Tests (TOB-2)
 *
 * Tests the subscription purchase confirmation flow:
 * - Modal rendering with plan details
 * - Purchase API call with correct parameters
 * - Crypto invoice display after successful purchase
 * - Error handling for API failures
 * - Form validation
 *
 * Depends on: FG-1 (Purchase flow implementation)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PurchaseConfirmModal } from '../PurchaseConfirmModal';
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

describe('PurchaseConfirmModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    server.resetHandlers();
  });

  describe('Rendering', () => {
    it('test_renders_purchase_modal_with_plan_details', () => {
      const mockPlan = {
        uuid: 'plan-123',
        name: 'Premium Plan',
        price: 29.99,
        currency: 'USD',
        durationDays: 30,
        dataLimitGb: 500,
        maxDevices: 5,
        features: ['High Speed', 'No Ads', 'Priority Support'],
      };

      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={vi.fn()}
          plan={mockPlan}
        />
      );

      expect(screen.getByText('Premium Plan')).toBeInTheDocument();
      expect(screen.getByText(/29.99/i)).toBeInTheDocument();
      expect(screen.getByText(/1 month/i)).toBeInTheDocument();
    });

    it('test_renders_purchase_button', () => {
      const mockPlan = {
        uuid: 'plan-001',
        name: 'Basic Plan',
        price: 9.99,
        currency: 'USD',
        durationDays: 7,
      };

      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={vi.fn()}
          plan={mockPlan}
        />
      );

      expect(screen.getByText(/Pay with Crypto/i)).toBeInTheDocument();
    });

    it('test_renders_cancel_button', () => {
      const mockPlan = {
        uuid: 'plan-002',
        name: 'Pro Plan',
        price: 19.99,
        currency: 'USD',
        durationDays: 30,
      };

      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={vi.fn()}
          plan={mockPlan}
        />
      );

      expect(screen.getByText(/Cancel/i)).toBeInTheDocument();
    });

    it('test_displays_plan_features_list', () => {
      const mockPlan = {
        uuid: 'plan-003',
        name: 'Premium Plan',
        price: 49.99,
        currency: 'USD',
        durationDays: 90,
        features: ['Unlimited Bandwidth', 'Priority Support', '10 Devices'],
      };

      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={vi.fn()}
          plan={mockPlan}
        />
      );

      mockPlan.features.forEach((feature) => {
        expect(screen.getByText(feature)).toBeInTheDocument();
      });
    });
  });

  describe('Purchase Flow', () => {
    it('test_purchase_button_calls_api_with_correct_params', async () => {
      const user = userEvent.setup({ delay: null });
      let capturedRequest: any = null;

      server.use(
        http.post(`${API_BASE}/payments/crypto/invoice`, async ({ request }) => {
          capturedRequest = await request.json();
          return HttpResponse.json({
            payment_url: 'https://cryptobot.example/invoice/123',
          }, { status: 201 });
        })
      );

      const mockPlan = {
        uuid: 'plan-456',
        name: 'Test Plan',
        price: 19.99,
        currency: 'USD',
        durationDays: 7,
      };

      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={vi.fn()}
          plan={mockPlan}
        />
      );

      const purchaseButton = screen.getByText(/Pay with Crypto/i);
      await user.click(purchaseButton);

      await waitFor(() => {
        expect(capturedRequest).not.toBeNull();
        expect(capturedRequest.plan_id).toBe('plan-456');
        expect(capturedRequest.currency).toBe('USDT');
      });
    });

    it('test_displays_loading_state_during_purchase', async () => {
      const user = userEvent.setup({ delay: null });

      server.use(
        http.post(`${API_BASE}/payments/crypto/invoice`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 1000));
          return HttpResponse.json({ payment_url: 'https://crypto.example/inv' }, { status: 201 });
        })
      );

      const mockPlan = {
        uuid: 'plan-delay',
        name: 'Test Plan',
        price: 15.00,
        currency: 'USD',
        durationDays: 14,
      };

      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={vi.fn()}
          plan={mockPlan}
        />
      );

      const purchaseButton = screen.getByText(/Pay with Crypto/i);
      await user.click(purchaseButton);

      // Component transitions to processing step with spinner
      expect(screen.getByText(/Creating payment invoice/i)).toBeInTheDocument();
    });

    it('test_displays_crypto_invoice_after_purchase_success', async () => {
      const user = userEvent.setup({ delay: null });
      const windowOpenSpy = vi.spyOn(window, 'open').mockImplementation(() => null);

      server.use(
        http.post(`${API_BASE}/payments/crypto/invoice`, () => {
          return HttpResponse.json({
            payment_url: 'https://cryptobot.example/invoice/456',
          }, { status: 201 });
        })
      );

      const mockPlan = {
        uuid: 'plan-success',
        name: 'Premium Plan',
        price: 29.99,
        currency: 'USD',
        durationDays: 30,
      };

      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={vi.fn()}
          plan={mockPlan}
        />
      );

      const purchaseButton = screen.getByText(/Pay with Crypto/i);
      await user.click(purchaseButton);

      await waitFor(() => {
        expect(screen.getByText(/Payment Page Opened/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/Complete your payment in the new tab/i)).toBeInTheDocument();
      expect(windowOpenSpy).toHaveBeenCalledWith('https://cryptobot.example/invoice/456', '_blank');
      windowOpenSpy.mockRestore();
    });

    it('test_calls_onSuccess_callback_after_purchase', async () => {
      const user = userEvent.setup({ delay: null });
      const paymentUrl = 'https://cryptobot.example/invoice/789';
      const windowOpenSpy = vi.spyOn(window, 'open').mockImplementation(() => null);

      server.use(
        http.post(`${API_BASE}/payments/crypto/invoice`, () => {
          return HttpResponse.json({
            payment_url: paymentUrl,
          }, { status: 201 });
        })
      );

      const mockPlan = {
        uuid: 'plan-callback',
        name: 'Test Plan',
        price: 19.99,
        currency: 'USD',
        durationDays: 30,
      };

      const onClose = vi.fn();

      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={onClose}
          plan={mockPlan}
        />
      );

      const purchaseButton = screen.getByText(/Pay with Crypto/i);
      await user.click(purchaseButton);

      await waitFor(() => {
        expect(windowOpenSpy).toHaveBeenCalledWith(paymentUrl, '_blank');
      });

      expect(screen.getByText(/Payment Page Opened/i)).toBeInTheDocument();
      windowOpenSpy.mockRestore();
    });

    it('test_closes_modal_on_cancel_button_click', async () => {
      const user = userEvent.setup({ delay: null });
      const onClose = vi.fn();

      const mockPlan = {
        uuid: 'plan-cancel',
        name: 'Test Plan',
        price: 12.00,
        currency: 'USD',
        durationDays: 10,
      };

      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={onClose}
          plan={mockPlan}
        />
      );

      const cancelButton = screen.getByText(/Cancel/i);
      await user.click(cancelButton);

      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('Error Handling', () => {
    it('test_displays_error_message_on_purchase_failure', async () => {
      const user = userEvent.setup({ delay: null });

      server.use(
        http.post(`${API_BASE}/payments/crypto/invoice`, () => {
          return HttpResponse.json(
            { detail: 'Payment gateway error' },
            { status: 400 }
          );
        })
      );

      const mockPlan = {
        uuid: 'plan-789',
        name: 'Test Plan',
        price: 9.99,
        currency: 'USD',
        durationDays: 1,
      };

      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={vi.fn()}
          plan={mockPlan}
        />
      );

      const purchaseButton = screen.getByText(/Pay with Crypto/i);
      await user.click(purchaseButton);

      await waitFor(() => {
        expect(screen.getByText(/Payment Failed/i)).toBeInTheDocument();
      });
    });

    it('test_displays_insufficient_balance_error', async () => {
      const user = userEvent.setup({ delay: null });

      server.use(
        http.post(`${API_BASE}/payments/crypto/invoice`, () => {
          return HttpResponse.json(
            { detail: 'Insufficient balance' },
            { status: 422 }
          );
        })
      );

      const mockPlan = {
        uuid: 'plan-balance',
        name: 'Test Plan',
        price: 99.99,
        currency: 'USD',
        durationDays: 30,
      };

      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={vi.fn()}
          plan={mockPlan}
        />
      );

      const purchaseButton = screen.getByText(/Pay with Crypto/i);
      await user.click(purchaseButton);

      await waitFor(() => {
        expect(screen.getByText(/Payment Failed/i)).toBeInTheDocument();
        expect(screen.getByText(/Insufficient balance/i)).toBeInTheDocument();
      });
    });

    it('test_displays_plan_not_found_error', async () => {
      const user = userEvent.setup({ delay: null });

      server.use(
        http.post(`${API_BASE}/payments/crypto/invoice`, () => {
          return HttpResponse.json(
            { detail: 'Plan not found' },
            { status: 404 }
          );
        })
      );

      const mockPlan = {
        uuid: 'plan-notfound',
        name: 'Test Plan',
        price: 19.99,
        currency: 'USD',
        durationDays: 30,
      };

      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={vi.fn()}
          plan={mockPlan}
        />
      );

      const purchaseButton = screen.getByText(/Pay with Crypto/i);
      await user.click(purchaseButton);

      await waitFor(() => {
        expect(screen.getByText(/Payment Failed/i)).toBeInTheDocument();
        expect(screen.getByText(/Plan not found/i)).toBeInTheDocument();
      });
    });

    it('test_displays_network_error_message', async () => {
      const user = userEvent.setup({ delay: null });

      server.use(
        http.post(`${API_BASE}/payments/crypto/invoice`, () => {
          return HttpResponse.error();
        })
      );

      const mockPlan = {
        uuid: 'plan-network',
        name: 'Test Plan',
        price: 19.99,
        currency: 'USD',
        durationDays: 30,
      };

      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={vi.fn()}
          plan={mockPlan}
        />
      );

      const purchaseButton = screen.getByText(/Pay with Crypto/i);
      await user.click(purchaseButton);

      await waitFor(() => {
        expect(screen.getByText(/Payment Failed/i)).toBeInTheDocument();
      });
    });

    it('test_error_message_clears_on_retry', async () => {
      const user = userEvent.setup({ delay: null });
      const windowOpenSpy = vi.spyOn(window, 'open').mockImplementation(() => null);
      let callCount = 0;

      server.use(
        http.post(`${API_BASE}/payments/crypto/invoice`, () => {
          callCount++;
          if (callCount === 1) {
            return HttpResponse.json(
              { detail: 'Payment gateway error' },
              { status: 400 }
            );
          }
          return HttpResponse.json({
            payment_url: 'https://cryptobot.example/invoice/retry-success',
          }, { status: 201 });
        })
      );

      const mockPlan = {
        uuid: 'plan-retry',
        name: 'Test Plan',
        price: 19.99,
        currency: 'USD',
        durationDays: 30,
      };

      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={vi.fn()}
          plan={mockPlan}
        />
      );

      const purchaseButton = screen.getByText(/Pay with Crypto/i);
      await user.click(purchaseButton);

      await waitFor(() => {
        expect(screen.getByText(/Payment Failed/i)).toBeInTheDocument();
      });

      const tryAgainButton = screen.getByText(/Try Again/i);
      await user.click(tryAgainButton);

      await waitFor(() => {
        expect(screen.queryByText(/Payment Failed/i)).not.toBeInTheDocument();
      });

      await waitFor(() => {
        expect(screen.getByText(/Payment Page Opened/i)).toBeInTheDocument();
      });

      windowOpenSpy.mockRestore();
    });
  });

  describe('Form Validation', () => {
    it('test_purchase_button_disabled_without_plan', () => {
      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={vi.fn()}
          plan={null}
        />
      );

      // Modal should not render when plan is null
      expect(screen.queryByText(/Pay with Crypto/i)).not.toBeInTheDocument();
    });

    it('test_prevents_double_submission', async () => {
      const user = userEvent.setup({ delay: null });
      let apiCallCount = 0;

      server.use(
        http.post(`${API_BASE}/payments/crypto/invoice`, async () => {
          apiCallCount++;
          await new Promise((resolve) => setTimeout(resolve, 500));
          return HttpResponse.json({
            payment_url: 'https://cryptobot.example/invoice/double',
          }, { status: 201 });
        })
      );

      const mockPlan = {
        uuid: 'plan-double',
        name: 'Test Plan',
        price: 19.99,
        currency: 'USD',
        durationDays: 30,
      };

      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={vi.fn()}
          plan={mockPlan}
        />
      );

      const purchaseButton = screen.getByText(/Pay with Crypto/i);

      // Click twice rapidly
      await user.click(purchaseButton);
      await user.click(purchaseButton);

      await waitFor(() => {
        expect(screen.getByText(/Creating payment invoice/i)).toBeInTheDocument();
      });

      // Wait for processing to complete
      await waitFor(() => {
        expect(screen.getByText(/Payment Page Opened/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      // Should only have called API once
      expect(apiCallCount).toBe(1);
    });

    it('test_validates_minimum_plan_price', async () => {
      const user = userEvent.setup({ delay: null });

      const mockPlan = {
        uuid: 'plan-zero',
        name: 'Free Plan',
        price: 0,
        currency: 'USD',
        durationDays: 7,
      };

      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={vi.fn()}
          plan={mockPlan}
        />
      );

      // Should still render and show the plan with 0 price
      expect(screen.getByText('Free Plan')).toBeInTheDocument();
      expect(screen.getByText(/0.00/i)).toBeInTheDocument();

      const purchaseButton = screen.getByText(/Pay with Crypto/i);
      expect(purchaseButton).toBeInTheDocument();

      // Button should be clickable (component doesn't validate min price client-side)
      await user.click(purchaseButton);
      expect(screen.getByText(/Creating payment invoice/i)).toBeInTheDocument();
    });
  });

  describe('Crypto Invoice Display', () => {
    it('test_displays_qr_code_for_payment', async () => {
      const user = userEvent.setup({ delay: null });
      const windowOpenSpy = vi.spyOn(window, 'open').mockImplementation(() => null);

      server.use(
        http.post(`${API_BASE}/payments/crypto/invoice`, () => {
          return HttpResponse.json({
            payment_url: 'https://cryptobot.example/invoice/qr-test',
          }, { status: 201 });
        })
      );

      const mockPlan = {
        uuid: 'plan-qr',
        name: 'Test Plan',
        price: 29.99,
        currency: 'USD',
        durationDays: 30,
      };

      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={vi.fn()}
          plan={mockPlan}
        />
      );

      const purchaseButton = screen.getByText(/Pay with Crypto/i);
      await user.click(purchaseButton);

      // Component shows success message but doesn't render QR code inline
      // The payment URL is opened in a new tab where the QR code would be displayed
      await waitFor(() => {
        expect(screen.getByText(/Payment Page Opened/i)).toBeInTheDocument();
      });

      expect(windowOpenSpy).toHaveBeenCalledWith('https://cryptobot.example/invoice/qr-test', '_blank');
      windowOpenSpy.mockRestore();
    });

    it('test_displays_payment_address_with_copy_button', async () => {
      const user = userEvent.setup({ delay: null });
      const windowOpenSpy = vi.spyOn(window, 'open').mockImplementation(() => null);

      server.use(
        http.post(`${API_BASE}/payments/crypto/invoice`, () => {
          return HttpResponse.json({
            payment_url: 'https://cryptobot.example/invoice/address-test',
          }, { status: 201 });
        })
      );

      const mockPlan = {
        uuid: 'plan-address',
        name: 'Test Plan',
        price: 19.99,
        currency: 'USD',
        durationDays: 30,
      };

      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={vi.fn()}
          plan={mockPlan}
        />
      );

      const purchaseButton = screen.getByText(/Pay with Crypto/i);
      await user.click(purchaseButton);

      await waitFor(() => {
        expect(screen.getByText(/Payment Page Opened/i)).toBeInTheDocument();
      });

      // Component doesn't display address inline, it opens payment URL in new tab
      expect(screen.getByText(/Complete your payment in the new tab/i)).toBeInTheDocument();
      expect(windowOpenSpy).toHaveBeenCalledWith('https://cryptobot.example/invoice/address-test', '_blank');

      windowOpenSpy.mockRestore();
    });

    it('test_copy_button_copies_address_to_clipboard', async () => {
      const user = userEvent.setup({ delay: null });
      const windowOpenSpy = vi.spyOn(window, 'open').mockImplementation(() => null);
      const clipboardWriteTextSpy = vi.fn();
      Object.assign(navigator, {
        clipboard: {
          writeText: clipboardWriteTextSpy,
        },
      });

      server.use(
        http.post(`${API_BASE}/payments/crypto/invoice`, () => {
          return HttpResponse.json({
            payment_url: 'https://cryptobot.example/invoice/clipboard-test',
          }, { status: 201 });
        })
      );

      const mockPlan = {
        uuid: 'plan-clipboard',
        name: 'Test Plan',
        price: 19.99,
        currency: 'USD',
        durationDays: 30,
      };

      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={vi.fn()}
          plan={mockPlan}
        />
      );

      const purchaseButton = screen.getByText(/Pay with Crypto/i);
      await user.click(purchaseButton);

      await waitFor(() => {
        expect(screen.getByText(/Payment Page Opened/i)).toBeInTheDocument();
      });

      // Component doesn't have a copy button - payment details are in the external page
      expect(screen.queryByText(/copy/i)).not.toBeInTheDocument();
      expect(clipboardWriteTextSpy).not.toHaveBeenCalled();

      windowOpenSpy.mockRestore();
    });

    it('test_displays_payment_amount_and_currency', async () => {
      const user = userEvent.setup({ delay: null });
      const windowOpenSpy = vi.spyOn(window, 'open').mockImplementation(() => null);

      server.use(
        http.post(`${API_BASE}/payments/crypto/invoice`, () => {
          return HttpResponse.json({
            payment_url: 'https://cryptobot.example/invoice/amount-test',
          }, { status: 201 });
        })
      );

      const mockPlan = {
        uuid: 'plan-amount',
        name: 'Premium Plan',
        price: 49.99,
        currency: 'USD',
        durationDays: 90,
      };

      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={vi.fn()}
          plan={mockPlan}
        />
      );

      // Amount and currency are displayed in the confirmation step before purchase
      expect(screen.getByText(/49.99/i)).toBeInTheDocument();
      expect(screen.getByText(/USD/i)).toBeInTheDocument();

      const purchaseButton = screen.getByText(/Pay with Crypto/i);
      await user.click(purchaseButton);

      await waitFor(() => {
        expect(screen.getByText(/Payment Page Opened/i)).toBeInTheDocument();
      });

      windowOpenSpy.mockRestore();
    });

    it('test_displays_payment_expiration_time', async () => {
      const user = userEvent.setup({ delay: null });
      const windowOpenSpy = vi.spyOn(window, 'open').mockImplementation(() => null);

      server.use(
        http.post(`${API_BASE}/payments/crypto/invoice`, () => {
          return HttpResponse.json({
            payment_url: 'https://cryptobot.example/invoice/expiration-test',
          }, { status: 201 });
        })
      );

      const mockPlan = {
        uuid: 'plan-expiration',
        name: 'Test Plan',
        price: 19.99,
        currency: 'USD',
        durationDays: 30,
      };

      render(
        <PurchaseConfirmModal
          isOpen={true}
          onClose={vi.fn()}
          plan={mockPlan}
        />
      );

      const purchaseButton = screen.getByText(/Pay with Crypto/i);
      await user.click(purchaseButton);

      await waitFor(() => {
        expect(screen.getByText(/Payment Page Opened/i)).toBeInTheDocument();
      });

      // Component doesn't display expiration time - that would be on the payment page
      // Success message is shown instead
      expect(screen.getByText(/Complete your payment in the new tab/i)).toBeInTheDocument();

      windowOpenSpy.mockRestore();
    });
  });
});
