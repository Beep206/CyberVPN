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
      http.get(`${API_BASE}/orders/`, () => {
        return HttpResponse.json([]);
      })
    );

    render(<PaymentsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('title')).toBeInTheDocument();
    });
  });

  it('test_displays_payment_list', async () => {
    server.use(
      http.get(`${API_BASE}/orders/`, () => {
        return HttpResponse.json([
          {
            id: 'order-1',
            displayed_price: 9.99,
            currency_code: 'USD',
            order_status: 'committed',
            settlement_status: 'paid',
            created_at: '2026-02-11T10:00:00Z',
            items: [{ display_name: 'Premium Plan' }],
          },
          {
            id: 'order-2',
            displayed_price: 4.99,
            currency_code: 'USD',
            order_status: 'awaiting_payment',
            settlement_status: 'pending',
            created_at: '2026-02-10T15:00:00Z',
            items: [{ display_name: 'Basic Plan' }],
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
      http.get(`${API_BASE}/orders/`, () => {
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
      http.get(`${API_BASE}/orders/`, () => {
        return HttpResponse.json([
          {
            id: 'order-1',
            displayed_price: 10,
            currency_code: 'USD',
            order_status: 'committed',
            settlement_status: 'paid',
            created_at: '2026-02-11T10:00:00Z',
            items: [{ display_name: 'Plan' }],
          },
        ]);
      })
    );

    render(<PaymentsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('status_completed')).toBeInTheDocument();
    });
  });
});
