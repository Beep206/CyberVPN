import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { CustomerPaymentAttemptsView } from '../customer-payment-attempts-view';
import type { AdminPaymentAttemptRecord } from '../customer-payment-attempts-view-model';

const supportAttempt: AdminPaymentAttemptRecord = {
  age_minutes: 17,
  attempt_number: 1,
  created_at: '2026-05-04T09:00:00Z',
  currency_code: 'USD',
  displayed_amount: 10,
  external_reference_fingerprint: 'aabbccddeeff0011',
  gateway_amount: null,
  id: 'attempt-1',
  idempotency_key_present: true,
  invoice_expires_at: '2026-05-04T11:00:00Z',
  invoice_present: true,
  launch_blocker: false,
  manual_review_required: true,
  order_id: '11111111-2222-4333-8444-555555555555',
  order_status: 'committed',
  payment_id: null,
  payment_record_present: false,
  provider: 'cryptobot',
  provider_status: 'paid',
  redacted_fields: [
    'external_reference',
    'idempotency_key',
    'provider_snapshot',
    'request_snapshot',
    'invoice.payment_url',
  ],
  review_reason: 'paid_without_canonical_payment',
  review_state: 'alert_15m',
  sale_channel: 'telegram_bot',
  settlement_status: 'pending_payment',
  stage1_payment_state: 'paid',
  status: 'succeeded',
  support_escalation: true,
  terminal_at: '2026-05-04T09:00:00Z',
  updated_at: '2026-05-04T09:05:00Z',
  user_id: 'customer-1',
  visibility: 'support',
  wallet_amount: null,
};

function renderView(overrides: Partial<Parameters<typeof CustomerPaymentAttemptsView>[0]> = {}) {
  render(
    <CustomerPaymentAttemptsView
      actorRole="support"
      attempts={[supportAttempt]}
      customerLabel="alpha@example.com"
      userId="customer-1"
      {...overrides}
    />,
  );
}

describe('CustomerPaymentAttemptsView', () => {
  it('renders support-safe payment status and review state', () => {
    renderView();

    expect(screen.getByTestId('payment-attempts-role')).toHaveTextContent('support view');
    expect(screen.getByText('Payment attempts')).toBeInTheDocument();
    expect(screen.getAllByText('paid')).toHaveLength(2);
    expect(screen.getByText('CryptoBot')).toBeInTheDocument();
    expect(screen.getByText('10.00 USD')).toBeInTheDocument();
    expect(screen.getByText('alert 15m · paid without canonical payment')).toBeInTheDocument();
    expect(screen.getByText('ref aabbccddeeff0011')).toBeInTheDocument();
    expect(screen.getByText('no canonical payment record')).toBeInTheDocument();

    const visibleText = document.body.textContent ?? '';
    expect(visibleText).not.toContain('payment_url');
    expect(visibleText).not.toContain('provider_snapshot');
    expect(visibleText).not.toContain('idempotency_key');
    expect(visibleText).not.toContain('raw-token');
  });

  it('shows finance breakdown only to finance-capable roles', () => {
    const financeAttempt: AdminPaymentAttemptRecord = {
      ...supportAttempt,
      gateway_amount: 8,
      manual_review_required: false,
      payment_id: 'payment-1',
      payment_record_present: true,
      review_reason: null,
      review_state: 'ok',
      support_escalation: false,
      visibility: 'finance',
      wallet_amount: 2,
    };

    renderView({
      actorRole: 'finance',
      attempts: [financeAttempt],
    });

    expect(screen.getByTestId('payment-attempts-role')).toHaveTextContent('finance view');
    expect(screen.getByText('wallet 2.00 USD · gateway 8.00 USD')).toBeInTheDocument();
  });

  it('blocks operator and viewer roles before showing payment attempts', () => {
    renderView({ actorRole: 'operator' });

    expect(screen.getByRole('alert')).toHaveTextContent('restricted to support, finance');
    const table = screen.queryByRole('table');
    expect(table).not.toBeInTheDocument();
  });

  it('renders empty and loading states', () => {
    renderView({ attempts: [] });
    expect(screen.getByText('No payment attempts recorded for this customer.')).toBeInTheDocument();

    renderView({ attempts: [], isLoading: true });
    const loadingRegion = screen.getByLabelText('Loading payment attempts');
    expect(within(loadingRegion).queryByText('No payment attempts recorded')).not.toBeInTheDocument();
  });
});
