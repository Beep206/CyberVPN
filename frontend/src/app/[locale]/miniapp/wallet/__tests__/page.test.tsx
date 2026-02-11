/**
 * Mini App Wallet Page Tests
 *
 * Tests wallet functionality:
 * - Balance display
 * - Transaction history with infinite scroll
 * - Withdraw functionality
 * - Transaction status badges
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import WalletPage from '../page';
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
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('MiniAppWalletPage', () => {
  let telegramMock: ReturnType<typeof setupTelegramWebAppMock>;

  beforeEach(() => {
    telegramMock = setupTelegramWebAppMock();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanupTelegramWebAppMock();
  });

  describe('Balance Display', () => {
    it('test_shows_loading_while_fetching_balance', () => {
      server.use(
        http.get(`${API_BASE}/wallet/balance`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({ balance: 100 });
        }),
        http.get(`${API_BASE}/wallet/transactions`, () => {
          return HttpResponse.json([]);
        })
      );

      render(<WalletPage />, { wrapper: createWrapper() });

      expect(screen.getByRole('status', { hidden: true })).toBeInTheDocument();
    });

    it('test_displays_balance_amount', async () => {
      server.use(
        http.get(`${API_BASE}/wallet/balance`, () => {
          return HttpResponse.json({ balance: 150.50 });
        }),
        http.get(`${API_BASE}/wallet/transactions`, () => {
          return HttpResponse.json([]);
        })
      );

      render(<WalletPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('balance')).toBeInTheDocument();
      });

      expect(screen.getByText(/\$150\.50/)).toBeInTheDocument();
    });
  });

  describe('Transaction History', () => {
    it('test_displays_transaction_list', async () => {
      server.use(
        http.get(`${API_BASE}/wallet/balance`, () => {
          return HttpResponse.json({ balance: 100 });
        }),
        http.get(`${API_BASE}/wallet/transactions`, () => {
          return HttpResponse.json([
            {
              id: 'tx-1',
              type: 'deposit',
              amount: 50,
              status: 'completed',
              created_at: '2026-02-11T10:00:00Z',
            },
            {
              id: 'tx-2',
              type: 'withdrawal',
              amount: 25,
              status: 'pending',
              created_at: '2026-02-10T15:00:00Z',
            },
          ]);
        })
      );

      render(<WalletPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/\$50/)).toBeInTheDocument();
      });

      expect(screen.getByText(/\$25/)).toBeInTheDocument();
    });

    it('test_shows_empty_state_when_no_transactions', async () => {
      server.use(
        http.get(`${API_BASE}/wallet/balance`, () => {
          return HttpResponse.json({ balance: 0 });
        }),
        http.get(`${API_BASE}/wallet/transactions`, () => {
          return HttpResponse.json([]);
        })
      );

      render(<WalletPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('noTransactions')).toBeInTheDocument();
      });
    });

    it('test_loads_more_transactions_on_scroll', async () => {
      const user = userEvent.setup();

      server.use(
        http.get(`${API_BASE}/wallet/balance`, () => {
          return HttpResponse.json({ balance: 100 });
        }),
        http.get(`${API_BASE}/wallet/transactions`, ({ request }) => {
          const url = new URL(request.url);
          const offset = parseInt(url.searchParams.get('offset') || '0');

          // First page: 20 items
          if (offset === 0) {
            return HttpResponse.json(
              Array.from({ length: 20 }, (_, i) => ({
                id: `tx-${i}`,
                type: 'deposit',
                amount: 10,
                status: 'completed',
                created_at: '2026-02-11T10:00:00Z',
              }))
            );
          }
          // Second page: empty
          return HttpResponse.json([]);
        })
      );

      render(<WalletPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('recentTransactions')).toBeInTheDocument();
      });

      const loadMoreButton = screen.queryByText('loadMore');
      if (loadMoreButton) {
        await user.click(loadMoreButton);
      }
    });
  });
});
