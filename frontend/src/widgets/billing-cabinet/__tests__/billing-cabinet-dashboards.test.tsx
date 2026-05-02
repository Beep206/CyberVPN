import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const {
  createPaymentAttemptMock,
  getBalanceMock,
  getHistoryMock,
  getOrdersMock,
  getTransactionsMock,
  getWithdrawalsMock,
  markPerformanceMock,
  measurePerformanceMock,
  openMock,
  requestWithdrawalMock,
} = vi.hoisted(() => ({
  createPaymentAttemptMock: vi.fn(),
  getBalanceMock: vi.fn(),
  getHistoryMock: vi.fn(),
  getOrdersMock: vi.fn(),
  getTransactionsMock: vi.fn(),
  getWithdrawalsMock: vi.fn(),
  markPerformanceMock: vi.fn(),
  measurePerformanceMock: vi.fn(),
  openMock: vi.fn(),
  requestWithdrawalMock: vi.fn(),
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations:
    () =>
    (key: string, values?: Record<string, string | number>) => {
      if (!values) {
        return key;
      }

      return `${key} ${Object.values(values).join(' ')}`;
    },
}));

vi.mock('@/i18n/navigation', () => ({
  Link: ({
    children,
    href,
    ...rest
  }: {
    children: ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock('@/shared/lib/web-vitals', () => ({
  PerformanceMarks: {
    PURCHASE_FLOW_COMPLETE: 'purchase-flow-complete',
    PURCHASE_FLOW_START: 'purchase-flow-start',
    WITHDRAWAL_FLOW_COMPLETE: 'withdrawal-flow-complete',
    WITHDRAWAL_FLOW_START: 'withdrawal-flow-start',
  },
  markPerformance: markPerformanceMock,
  measurePerformance: measurePerformanceMock,
}));

vi.mock('@/lib/api', () => ({
  commerceApi: {
    createPaymentAttempt: createPaymentAttemptMock,
    listOrders: getOrdersMock,
  },
  paymentsApi: {
    getHistory: getHistoryMock,
  },
  walletApi: {
    getBalance: getBalanceMock,
    getTransactions: getTransactionsMock,
    getWithdrawals: getWithdrawalsMock,
    requestWithdrawal: requestWithdrawalMock,
  },
}));

vi.mock('@/lib/api/commerce', () => ({
  createClientIdempotencyKey: () => 'payment-retry-test-key',
}));

import { PaymentHistoryDashboard } from '../payment-history-dashboard';
import { WalletCabinetDashboard } from '../wallet-cabinet-dashboard';

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

const wallet = {
  balance: 50,
  currency: 'USD',
  frozen: 5,
  id: 'wallet-1',
};

const transaction = {
  amount: 15,
  balance_after: 50,
  created_at: '2026-04-24T10:00:00Z',
  description: 'Referral reward',
  id: 'transaction-1',
  reason: 'referral_commission',
  type: 'credit',
};

const order = {
  addon_amount: 0,
  auth_realm_id: 'realm-1',
  base_price: 29,
  checkout_session_id: 'checkout-1',
  commission_base_amount: 29,
  created_at: '2026-04-24T11:00:00Z',
  currency_code: 'USD',
  discount_amount: 0,
  displayed_price: 29,
  entitlements_snapshot: {},
  gateway_amount: 29,
  id: 'order-pending-1',
  items: [
    {
      created_at: '2026-04-24T11:00:00Z',
      currency_code: 'USD',
      display_name: 'Pro Plan',
      id: 'item-1',
      item_snapshot: {},
      item_type: 'plan',
      order_id: 'order-pending-1',
      quantity: 1,
      total_price: 29,
      unit_price: 29,
      updated_at: '2026-04-24T11:00:00Z',
    },
  ],
  merchant_snapshot: {},
  order_status: 'committed',
  partner_markup: 0,
  policy_snapshot: {},
  pricing_snapshot: {},
  sale_channel: 'web',
  settlement_status: 'pending',
  storefront_id: 'storefront-1',
  updated_at: '2026-04-24T11:00:00Z',
  user_id: 'user-1',
  wallet_amount: 0,
};

beforeEach(() => {
  vi.clearAllMocks();
  Object.defineProperty(window, 'open', {
    configurable: true,
    value: openMock,
  });
  getBalanceMock.mockResolvedValue({ data: wallet });
  getTransactionsMock.mockResolvedValue({ data: [transaction] });
  getWithdrawalsMock.mockResolvedValue({
    data: [
      {
        amount: 20,
        created_at: '2026-04-24T12:00:00Z',
        currency: 'USD',
        id: 'withdrawal-1',
        method: 'cryptobot',
        status: 'pending',
      },
    ],
  });
  requestWithdrawalMock.mockResolvedValue({
    data: {
      amount: 25,
      created_at: '2026-04-24T12:30:00Z',
      currency: 'USD',
      id: 'withdrawal-2',
      method: 'cryptobot',
      status: 'pending',
    },
  });
  getHistoryMock.mockResolvedValue({
    data: {
      payments: [
        {
          amount: 29,
          created_at: '2026-04-24T10:00:00Z',
          currency: 'USD',
          id: 'payment-1',
          provider: 'cryptobot',
          status: 'completed',
        },
      ],
    },
  });
  getOrdersMock.mockResolvedValue({ data: [order] });
  createPaymentAttemptMock.mockResolvedValue({
    data: {
      attempt_number: 2,
      created_at: '2026-04-24T12:00:00Z',
      currency_code: 'USD',
      displayed_amount: 29,
      external_reference: 'invoice-2',
      gateway_amount: 29,
      id: 'attempt-2',
      idempotency_key: 'payment-retry-test-key',
      invoice: {
        amount: 29,
        currency: 'USD',
        expires_at: '2026-04-24T13:00:00Z',
        invoice_id: 'invoice-2',
        payment_url: 'https://pay.example/invoice-2',
        status: 'pending',
      },
      order_id: 'order-pending-1',
      payment_id: null,
      provider: 'cryptobot',
      sale_channel: 'web',
      status: 'pending',
      supersedes_attempt_id: null,
      terminal_at: null,
      updated_at: '2026-04-24T12:00:00Z',
      wallet_amount: 0,
    },
  });
});

describe('WalletCabinetDashboard', () => {
  it('renders wallet balance, ledger and creates withdrawal request', async () => {
    renderWithQueryClient(<WalletCabinetDashboard />);

    expect(await screen.findAllByText('$50')).not.toHaveLength(0);
    expect(screen.getByText('Referral reward')).toBeInTheDocument();
    expect(screen.getByText('withdrawals.title')).toBeInTheDocument();

    const amountInput = screen.getByLabelText('withdrawForm.amount');
    fireEvent.change(amountInput, {
      target: { value: '25' },
    });

    const form = amountInput.closest('form');
    expect(form).not.toBeNull();
    fireEvent.submit(form!);

    await waitFor(() => {
      expect(requestWithdrawalMock).toHaveBeenCalledWith({
        amount: 25,
        method: 'cryptobot',
      });
    });
  });

  it('keeps available wallet sections usable when one backend source fails', async () => {
    getWithdrawalsMock.mockRejectedValueOnce(new Error('withdrawals unavailable'));

    renderWithQueryClient(<WalletCabinetDashboard />);

    expect(await screen.findAllByText('$50')).not.toHaveLength(0);
    expect(screen.getByText('Referral reward')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('errors.partialTitle');
    expect(screen.getByText('errors.partialDescription')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'actions.refresh' })).toBeEnabled();
  });

  it('validates withdrawal amount before calling the wallet API', async () => {
    renderWithQueryClient(<WalletCabinetDashboard />);

    const amountInput = await screen.findByLabelText('withdrawForm.amount');
    const form = amountInput.closest('form');
    expect(form).not.toBeNull();

    fireEvent.submit(form!);

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'withdrawForm.errors.amount',
    );
    expect(requestWithdrawalMock).not.toHaveBeenCalled();

    expect(await screen.findAllByText('$50')).not.toHaveLength(0);

    fireEvent.change(amountInput, {
      target: { value: '75' },
    });
    fireEvent.submit(form!);

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'withdrawForm.errors.balance',
    );
    expect(requestWithdrawalMock).not.toHaveBeenCalled();
  });

  it('records withdrawal telemetry and clears the form after a successful payout request', async () => {
    renderWithQueryClient(<WalletCabinetDashboard />);

    const amountInput = await screen.findByLabelText('withdrawForm.amount');
    expect(await screen.findAllByText('$50')).not.toHaveLength(0);

    fireEvent.change(amountInput, {
      target: { value: '25' },
    });
    fireEvent.change(screen.getByLabelText('withdrawForm.method'), {
      target: { value: 'manual' },
    });

    const form = amountInput.closest('form');
    expect(form).not.toBeNull();
    fireEvent.submit(form!);

    await waitFor(() => {
      expect(requestWithdrawalMock).toHaveBeenCalledWith({
        amount: 25,
        method: 'manual',
      });
    });

    expect(markPerformanceMock).toHaveBeenCalledWith('withdrawal-flow-start', {
      method: 'manual',
    });
    expect(markPerformanceMock).toHaveBeenCalledWith('withdrawal-flow-complete', {
      method: 'manual',
    });
    expect(measurePerformanceMock).toHaveBeenCalledWith(
      'wallet-withdrawal-flow-duration',
      'withdrawal-flow-start',
      'withdrawal-flow-complete',
    );
    expect(await screen.findByText('withdrawForm.success')).toBeInTheDocument();
    await waitFor(() => {
      expect((amountInput as HTMLInputElement).value).toBe('');
    });
  });

  it('shows a withdrawal submission error when the wallet API rejects the request', async () => {
    requestWithdrawalMock.mockRejectedValueOnce(new Error('withdrawal failed'));

    renderWithQueryClient(<WalletCabinetDashboard />);

    const amountInput = await screen.findByLabelText('withdrawForm.amount');
    expect(await screen.findAllByText('$50')).not.toHaveLength(0);

    fireEvent.change(amountInput, {
      target: { value: '25' },
    });

    const form = amountInput.closest('form');
    expect(form).not.toBeNull();
    fireEvent.submit(form!);

    await waitFor(() => {
      expect(requestWithdrawalMock).toHaveBeenCalledWith({
        amount: 25,
        method: 'cryptobot',
      });
    });
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'withdrawForm.errors.submit',
    );
  });

  it('filters wallet transactions by credit and debit direction', async () => {
    getTransactionsMock.mockResolvedValueOnce({
      data: [
        transaction,
        {
          ...transaction,
          amount: -7,
          balance_after: 43,
          created_at: '2026-04-24T11:00:00Z',
          description: 'Subscription debit',
          id: 'transaction-debit',
          reason: 'subscription_payment',
          type: 'debit',
        },
      ],
    });

    renderWithQueryClient(<WalletCabinetDashboard />);

    expect(await screen.findByText('Subscription debit')).toBeInTheDocument();
    expect(screen.getByText('Referral reward')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'transactions.filters.credit' }));

    expect(screen.getByText('Referral reward')).toBeInTheDocument();
    expect(screen.queryByText('Subscription debit')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'transactions.filters.debit' }));

    expect(screen.getByText('Subscription debit')).toBeInTheDocument();
    expect(screen.queryByText('Referral reward')).not.toBeInTheDocument();
  });

  it('loads the next transaction page and returns to the cached first page', async () => {
    const firstPageTransactions = Array.from({ length: 12 }, (_, index) => ({
      ...transaction,
      amount: index + 1,
      balance_after: 50 + index,
      created_at: `2026-04-24T10:${String(index).padStart(2, '0')}:00Z`,
      description: `Ledger ${index}`,
      id: `transaction-page-1-${index}`,
    }));
    getTransactionsMock
      .mockResolvedValueOnce({ data: firstPageTransactions })
      .mockResolvedValueOnce({
        data: [
          {
            ...transaction,
            created_at: '2026-04-24T12:00:00Z',
            description: 'Second page ledger',
            id: 'transaction-page-2',
          },
        ],
      });

    renderWithQueryClient(<WalletCabinetDashboard />);

    expect(await screen.findByText('Ledger 0')).toBeInTheDocument();
    expect(screen.getByText('transactions.page 1')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'actions.next' }));

    await waitFor(() => {
      expect(getTransactionsMock).toHaveBeenCalledWith({
        limit: 12,
        offset: 12,
      });
    });
    expect(await screen.findByText('Second page ledger')).toBeInTheDocument();
    expect(screen.getByText('transactions.page 2')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'actions.previous' }));

    expect(await screen.findByText('Ledger 0')).toBeInTheDocument();
    expect(screen.getByText('transactions.page 1')).toBeInTheDocument();
  });
});

describe('PaymentHistoryDashboard', () => {
  it('renders merged billing timeline and retries a pending order payment', async () => {
    renderWithQueryClient(<PaymentHistoryDashboard />);

    expect(await screen.findByText('Pro Plan')).toBeInTheDocument();
    expect(screen.getByText('Cryptobot timeline.paymentSuffix')).toBeInTheDocument();

    const orderRow = screen.getByText('Pro Plan').closest('div');
    expect(orderRow).not.toBeNull();

    fireEvent.click(screen.getByRole('button', { name: /timeline.retry/i }));

    await waitFor(() => {
      expect(createPaymentAttemptMock).toHaveBeenCalledWith(
        { order_id: 'order-pending-1' },
        'payment-retry-test-key',
      );
    });

    expect(openMock).toHaveBeenCalledWith(
      'https://pay.example/invoice-2',
      '_blank',
      'noopener,noreferrer',
    );
    expect(markPerformanceMock).toHaveBeenCalledWith('purchase-flow-start', {
      flow: 'payment_retry',
    });
    expect(markPerformanceMock).toHaveBeenCalledWith('purchase-flow-complete', {
      flow: 'payment_retry',
    });
    expect(measurePerformanceMock).toHaveBeenCalledWith(
      'payment-retry-flow-duration',
      'purchase-flow-start',
      'purchase-flow-complete',
    );

    expect(within(document.body).getByText('timeline.orderSplit $29 $0')).toBeInTheDocument();
  });

  it('keeps available billing rows usable when one backend source fails', async () => {
    getOrdersMock.mockRejectedValueOnce(new Error('orders unavailable'));

    renderWithQueryClient(<PaymentHistoryDashboard />);

    expect(await screen.findByText('Cryptobot timeline.paymentSuffix')).toBeInTheDocument();
    expect(screen.queryByText('Pro Plan')).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('errors.partialTitle');
    expect(screen.getByText('errors.partialDescription')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'actions.refresh' })).toBeEnabled();
  });

  it('filters billing events by completed, pending, failed and refunded states', async () => {
    getHistoryMock.mockResolvedValueOnce({
      data: {
        payments: [
          {
            amount: 29,
            created_at: '2026-04-24T10:00:00Z',
            currency: 'USD',
            id: 'payment-completed',
            provider: 'cryptobot',
            status: 'completed',
          },
          {
            amount: 19,
            created_at: '2026-04-24T09:00:00Z',
            currency: 'USD',
            id: 'payment-failed',
            provider: 'stripe',
            status: 'failed',
          },
          {
            amount: 5,
            created_at: '2026-04-24T08:00:00Z',
            currency: 'USD',
            id: 'payment-refunded',
            provider: 'telegram_stars',
            status: 'refunded',
          },
        ],
      },
    });

    renderWithQueryClient(<PaymentHistoryDashboard />);

    expect(await screen.findByText('Pro Plan')).toBeInTheDocument();
    expect(screen.getByText('Stripe timeline.paymentSuffix')).toBeInTheDocument();
    expect(screen.getByText('Telegram Stars timeline.paymentSuffix')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'timeline.filters.completed' }));
    expect(screen.getByText('Cryptobot timeline.paymentSuffix')).toBeInTheDocument();
    expect(screen.queryByText('Pro Plan')).not.toBeInTheDocument();
    expect(screen.queryByText('Stripe timeline.paymentSuffix')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'timeline.filters.pending' }));
    expect(screen.getByText('Pro Plan')).toBeInTheDocument();
    expect(screen.queryByText('Cryptobot timeline.paymentSuffix')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'timeline.filters.failed' }));
    expect(screen.getByText('Stripe timeline.paymentSuffix')).toBeInTheDocument();
    expect(screen.queryByText('Pro Plan')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'timeline.filters.refunded' }));
    expect(screen.getByText('Telegram Stars timeline.paymentSuffix')).toBeInTheDocument();
    expect(screen.queryByText('Stripe timeline.paymentSuffix')).not.toBeInTheDocument();
  });

  it('shows an empty state when the selected filter has no matching billing events', async () => {
    renderWithQueryClient(<PaymentHistoryDashboard />);

    expect(await screen.findByText('Pro Plan')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'timeline.filters.refunded' }));

    expect(screen.getByText('timeline.empty')).toBeInTheDocument();
  });

  it('records retry telemetry without opening a missing invoice URL', async () => {
    createPaymentAttemptMock.mockResolvedValueOnce({
      data: {
        invoice: null,
      },
    });

    renderWithQueryClient(<PaymentHistoryDashboard />);

    expect(await screen.findByText('Pro Plan')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /timeline.retry/i }));

    await waitFor(() => {
      expect(createPaymentAttemptMock).toHaveBeenCalledWith(
        { order_id: 'order-pending-1' },
        'payment-retry-test-key',
      );
    });

    expect(markPerformanceMock).toHaveBeenCalledWith('purchase-flow-start', {
      flow: 'payment_retry',
    });
    expect(markPerformanceMock).toHaveBeenCalledWith('purchase-flow-complete', {
      flow: 'payment_retry',
    });
    expect(measurePerformanceMock).toHaveBeenCalledWith(
      'payment-retry-flow-duration',
      'purchase-flow-start',
      'purchase-flow-complete',
    );
    expect(openMock).not.toHaveBeenCalled();
  });

  it('shows a retry error when the payment attempt API rejects the order', async () => {
    createPaymentAttemptMock.mockRejectedValueOnce(new Error('retry failed'));

    renderWithQueryClient(<PaymentHistoryDashboard />);

    expect(await screen.findByText('Pro Plan')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /timeline.retry/i }));

    await waitFor(() => {
      expect(createPaymentAttemptMock).toHaveBeenCalledWith(
        { order_id: 'order-pending-1' },
        'payment-retry-test-key',
      );
    });
    expect(await screen.findByRole('alert')).toHaveTextContent('timeline.retryError');
    expect(openMock).not.toHaveBeenCalled();
  });

  it('loads the next payment page and returns to the cached first page', async () => {
    const firstPagePayments = Array.from({ length: 20 }, (_, index) => ({
      amount: index + 1,
      created_at: `2026-04-24T10:${String(index).padStart(2, '0')}:00Z`,
      currency: 'USD',
      id: `payment-page-1-${index}`,
      provider: `page_${index}`,
      status: 'completed',
    }));
    getHistoryMock
      .mockResolvedValueOnce({
        data: {
          payments: firstPagePayments,
        },
      })
      .mockResolvedValueOnce({
        data: {
          payments: [
            {
              amount: 42,
              created_at: '2026-04-24T12:00:00Z',
              currency: 'USD',
              id: 'payment-page-2',
              provider: 'page_two',
              status: 'completed',
            },
          ],
        },
      });
    getOrdersMock.mockResolvedValueOnce({ data: [] });

    renderWithQueryClient(<PaymentHistoryDashboard />);

    expect(await screen.findByText('Page 0 timeline.paymentSuffix')).toBeInTheDocument();
    expect(screen.getByText('timeline.page 1')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'actions.next' }));

    await waitFor(() => {
      expect(getHistoryMock).toHaveBeenCalledWith({
        limit: 20,
        offset: 20,
      });
    });
    expect(await screen.findByText('Page Two timeline.paymentSuffix')).toBeInTheDocument();
    expect(screen.getByText('timeline.page 2')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'actions.previous' }));

    expect(await screen.findByText('Page 0 timeline.paymentSuffix')).toBeInTheDocument();
    expect(screen.getByText('timeline.page 1')).toBeInTheDocument();
  });

  it('refreshes payments and orders from the timeline action', async () => {
    renderWithQueryClient(<PaymentHistoryDashboard />);

    expect(await screen.findByText('Pro Plan')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'actions.refresh' }));

    await waitFor(() => {
      expect(getHistoryMock).toHaveBeenCalledTimes(2);
      expect(getOrdersMock).toHaveBeenCalledTimes(2);
    });
  });
});
