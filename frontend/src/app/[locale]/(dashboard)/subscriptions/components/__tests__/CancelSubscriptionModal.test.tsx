/**
 * CancelSubscriptionModal Component Tests
 *
 * Tests the three-step subscription cancellation flow:
 * 1. Confirm - Warning and action buttons
 * 2. Processing - Loading state
 * 3. Success - Confirmation message with auto-close
 *
 * Also tests error handling for API failures (404, 400)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CancelSubscriptionModal } from '../CancelSubscriptionModal';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

// Mock Modal component to render children directly
vi.mock('@/shared/ui/modal', () => ({
  Modal: ({ isOpen, children }: { isOpen: boolean; children: React.ReactNode }) =>
    isOpen ? <div data-testid="modal">{children}</div> : null,
}));

const API_BASE = 'http://localhost:8000/api/v1';

describe('CancelSubscriptionModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  describe('Confirm Step', () => {
    it('test_renders_confirm_step_with_warning_message', () => {
      const onClose = vi.fn();
      const onSuccess = vi.fn();

      render(
        <CancelSubscriptionModal
          isOpen={true}
          onClose={onClose}
          onSuccess={onSuccess}
          subscriptionName="Premium Plan"
        />
      );

      expect(screen.getByText(/You're about to cancel your/i)).toBeInTheDocument();
      expect(screen.getByText(/Premium Plan/i)).toBeInTheDocument();
      expect(screen.getByText(/Keep Subscription/i)).toBeInTheDocument();
      expect(screen.getByText(/Cancel Subscription/i)).toBeInTheDocument();
    });

    it('test_displays_expiry_date_when_provided', () => {
      const onClose = vi.fn();
      const onSuccess = vi.fn();
      const expiresAt = '2026-03-15T00:00:00Z';

      render(
        <CancelSubscriptionModal
          isOpen={true}
          onClose={onClose}
          onSuccess={onSuccess}
          expiresAt={expiresAt}
        />
      );

      expect(screen.getByText(/Your subscription will remain active until/i)).toBeInTheDocument();
      expect(screen.getByText(/3\/15\/2026/i)).toBeInTheDocument();
    });

    it('test_close_button_calls_onClose', async () => {
      const user = userEvent.setup({ delay: null });
      const onClose = vi.fn();
      const onSuccess = vi.fn();

      render(
        <CancelSubscriptionModal
          isOpen={true}
          onClose={onClose}
          onSuccess={onSuccess}
        />
      );

      const keepButton = screen.getByText(/Keep Subscription/i);
      await user.click(keepButton);

      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('Cancellation Flow', () => {
    it('test_successful_cancellation_shows_success_step', async () => {
      const user = userEvent.setup({ delay: null });
      const onClose = vi.fn();
      const onSuccess = vi.fn();

      // Mock successful cancellation
      server.use(
        http.post(`${API_BASE}/subscriptions/cancel`, () => {
          return HttpResponse.json({
            message: 'Subscription cancelled',
            cancelled_at: '2026-02-11T12:00:00Z',
          });
        })
      );

      render(
        <CancelSubscriptionModal
          isOpen={true}
          onClose={onClose}
          onSuccess={onSuccess}
        />
      );

      // Click cancel button
      const cancelButton = screen.getByText(/Cancel Subscription/i);
      await user.click(cancelButton);

      // Should show processing step
      await waitFor(() => {
        expect(screen.getByText(/Processing cancellation.../i)).toBeInTheDocument();
      });

      // Should show success step
      await waitFor(() => {
        expect(screen.getByText(/Subscription Cancelled/i)).toBeInTheDocument();
        expect(screen.getByText(/Your subscription has been cancelled successfully/i)).toBeInTheDocument();
      });

      // Auto-close after 2 seconds
      vi.advanceTimersByTime(2000);

      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalledTimes(1);
        expect(onClose).toHaveBeenCalledTimes(1);
      });
    });

    it('test_404_error_shows_no_active_subscription_message', async () => {
      const user = userEvent.setup({ delay: null });
      const onClose = vi.fn();
      const onSuccess = vi.fn();

      server.use(
        http.post(`${API_BASE}/subscriptions/cancel`, () => {
          return HttpResponse.json(
            { detail: 'No subscription found' },
            { status: 404 }
          );
        })
      );

      render(
        <CancelSubscriptionModal
          isOpen={true}
          onClose={onClose}
          onSuccess={onSuccess}
        />
      );

      const cancelButton = screen.getByText(/Cancel Subscription/i);
      await user.click(cancelButton);

      await waitFor(() => {
        expect(screen.getByText(/No active subscription found/i)).toBeInTheDocument();
      });

      // Should stay on confirm step
      expect(screen.getByText(/Keep Subscription/i)).toBeInTheDocument();
    });

    it('test_400_error_shows_already_cancelled_message', async () => {
      const user = userEvent.setup({ delay: null });
      const onClose = vi.fn();
      const onSuccess = vi.fn();

      server.use(
        http.post(`${API_BASE}/subscriptions/cancel`, () => {
          return HttpResponse.json(
            { detail: 'Subscription already cancelled' },
            { status: 400 }
          );
        })
      );

      render(
        <CancelSubscriptionModal
          isOpen={true}
          onClose={onClose}
          onSuccess={onSuccess}
        />
      );

      const cancelButton = screen.getByText(/Cancel Subscription/i);
      await user.click(cancelButton);

      await waitFor(() => {
        expect(screen.getByText(/Subscription already cancelled/i)).toBeInTheDocument();
      });
    });

    it('test_generic_error_shows_fallback_message', async () => {
      const user = userEvent.setup({ delay: null });
      const onClose = vi.fn();
      const onSuccess = vi.fn();

      server.use(
        http.post(`${API_BASE}/subscriptions/cancel`, () => {
          return HttpResponse.json(
            { detail: 'Internal server error' },
            { status: 500 }
          );
        })
      );

      render(
        <CancelSubscriptionModal
          isOpen={true}
          onClose={onClose}
          onSuccess={onSuccess}
        />
      );

      const cancelButton = screen.getByText(/Cancel Subscription/i);
      await user.click(cancelButton);

      await waitFor(() => {
        expect(screen.getByText(/Internal server error/i)).toBeInTheDocument();
      });
    });
  });

  describe('State Reset', () => {
    it('test_state_resets_on_modal_close', async () => {
      const user = userEvent.setup({ delay: null });
      const onClose = vi.fn();
      const onSuccess = vi.fn();

      server.use(
        http.post(`${API_BASE}/subscriptions/cancel`, () => {
          return HttpResponse.json(
            { detail: 'Error occurred' },
            { status: 500 }
          );
        })
      );

      const { rerender } = render(
        <CancelSubscriptionModal
          isOpen={true}
          onClose={onClose}
          onSuccess={onSuccess}
        />
      );

      // Trigger error
      const cancelButton = screen.getByText(/Cancel Subscription/i);
      await user.click(cancelButton);

      await waitFor(() => {
        expect(screen.getByText(/Error occurred/i)).toBeInTheDocument();
      });

      // Close modal
      const keepButton = screen.getByText(/Keep Subscription/i);
      await user.click(keepButton);

      // Re-open modal
      rerender(
        <CancelSubscriptionModal
          isOpen={true}
          onClose={onClose}
          onSuccess={onSuccess}
        />
      );

      // Error should be cleared
      expect(screen.queryByText(/Error occurred/i)).not.toBeInTheDocument();
    });
  });

  describe('Modal Visibility', () => {
    it('test_modal_not_rendered_when_closed', () => {
      const onClose = vi.fn();
      const onSuccess = vi.fn();

      render(
        <CancelSubscriptionModal
          isOpen={false}
          onClose={onClose}
          onSuccess={onSuccess}
        />
      );

      expect(screen.queryByTestId('modal')).not.toBeInTheDocument();
    });

    it('test_modal_rendered_when_open', () => {
      const onClose = vi.fn();
      const onSuccess = vi.fn();

      render(
        <CancelSubscriptionModal
          isOpen={true}
          onClose={onClose}
          onSuccess={onSuccess}
        />
      );

      expect(screen.getByTestId('modal')).toBeInTheDocument();
    });
  });
});
