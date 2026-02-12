/**
 * Mini App Payment History Page Tests
 *
 * Tests payment history functionality:
 * - Payment list display
 * - Status badges
 * - Empty state
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import PaymentsPage from '../page';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { setupTelegramWebAppMock, cleanupTelegramWebAppMock } from '@/test/mocks/telegram-webapp';

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

const API_BASE = 'http://localhost:8000/api/v1';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
};

describe('MiniAppPaymentsPage', () => {
  beforeEach(() => {
    setupTelegramWebAppMock();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanupTelegramWebAppMock();
  });

  it('test_displays_payment_history_title', async () => {
    server.use(
      http.get(`${API_BASE}/payments/history`, () => {
        return HttpResponse.json([]);
      })
    );

    render(<PaymentsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('paymentHistory')).toBeInTheDocument();
    });
  });

  it('test_displays_payment_list', async () => {
    server.use(
      http.get(`${API_BASE}/payments/history`, () => {
        return HttpResponse.json([
          {
            id: 'pay-1',
            plan_name: 'Premium Plan',
            amount: 9.99,
            currency: 'USD',
            status: 'completed',
            created_at: '2026-02-11T10:00:00Z',
          },
          {
            id: 'pay-2',
            plan_name: 'Basic Plan',
            amount: 4.99,
            currency: 'USD',
            status: 'pending',
            created_at: '2026-02-10T15:00:00Z',
          },
        ]);
      })
    );

    render(<PaymentsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Premium Plan')).toBeInTheDocument();
    });

    expect(screen.getByText('Basic Plan')).toBeInTheDocument();
  });

  it('test_shows_empty_state_when_no_payments', async () => {
    server.use(
      http.get(`${API_BASE}/payments/history`, () => {
        return HttpResponse.json([]);
      })
    );

    render(<PaymentsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('noPayments')).toBeInTheDocument();
    });
  });

  it('test_displays_status_badges', async () => {
    server.use(
      http.get(`${API_BASE}/payments/history`, () => {
        return HttpResponse.json([
          {
            id: 'pay-1',
            plan_name: 'Plan',
            amount: 10,
            currency: 'USD',
            status: 'completed',
            created_at: '2026-02-11T10:00:00Z',
          },
        ]);
      })
    );

    render(<PaymentsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('completed')).toBeInTheDocument();
    });
  });
});
