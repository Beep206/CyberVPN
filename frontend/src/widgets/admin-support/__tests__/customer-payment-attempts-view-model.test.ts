import { describe, expect, it } from 'vitest';

import {
  buildCustomerPaymentAttemptsEndpoint,
  buildFinancePaymentAttemptsEndpoint,
  canViewFinancePaymentAttempts,
  canViewSupportPaymentAttempts,
  summarizePaymentAttemptForAdmin,
  type AdminPaymentAttemptRecord,
  type Stage1PaymentAttemptViewRole,
} from '../customer-payment-attempts-view-model';

const supportAllowedRoles: Stage1PaymentAttemptViewRole[] = [
  'admin',
  'finance',
  'owner',
  'owner/super_admin',
  'owner_super_admin',
  'super_admin',
  'support',
];
const financeAllowedRoles: Stage1PaymentAttemptViewRole[] = [
  'admin',
  'finance',
  'owner',
  'owner/super_admin',
  'owner_super_admin',
  'super_admin',
];
const deniedRoles: Stage1PaymentAttemptViewRole[] = ['operator', 'viewer'];

const baseAttempt: AdminPaymentAttemptRecord = {
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
  provider: 'telegram_stars',
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

describe('customer payment attempts view model', () => {
  it('matches S1 backend role gates for support and finance views', () => {
    for (const role of supportAllowedRoles) {
      expect(canViewSupportPaymentAttempts(role)).toBe(true);
    }
    for (const role of financeAllowedRoles) {
      expect(canViewFinancePaymentAttempts(role)).toBe(true);
    }
    expect(canViewFinancePaymentAttempts('support')).toBe(false);

    for (const role of deniedRoles) {
      expect(canViewSupportPaymentAttempts(role)).toBe(false);
      expect(canViewFinancePaymentAttempts(role)).toBe(false);
    }
  });

  it('builds admin endpoints without leaking raw provider references', () => {
    expect(buildCustomerPaymentAttemptsEndpoint('customer 1')).toBe(
      '/admin/mobile-users/customer%201/payment-attempts',
    );
    expect(
      buildFinancePaymentAttemptsEndpoint({
        orderId: 'order-1',
        provider: 'cryptobot',
        status: 'pending',
        userId: 'user-1',
      }),
    ).toBe('/admin/payment-attempts?user_id=user-1&order_id=order-1&status=pending&provider=cryptobot');
  });

  it('summarizes support view with review state but without raw provider data', () => {
    const rawAttempt = {
      ...baseAttempt,
      external_reference: 'raw-provider-secret',
      idempotency_key: 'raw-idempotency-secret',
      provider_snapshot: {
        payment_url: 'https://pay.example.test/raw-token',
      },
    };

    const summary = summarizePaymentAttemptForAdmin(rawAttempt);
    const serialized = JSON.stringify(summary);

    expect(summary.requiresSupport).toBe(true);
    expect(summary.tone).toBe('warning');
    expect(summary.providerLabel).toBe('Telegram Stars');
    expect(summary.referenceLabel).toBe('ref aabbccddeeff0011');
    expect(summary.financeBreakdownLabel).toBeNull();
    expect(serialized).not.toContain('raw-provider-secret');
    expect(serialized).not.toContain('raw-idempotency-secret');
    expect(serialized).not.toContain('raw-token');
  });

  it('shows finance breakdown only when backend visibility permits it', () => {
    const financeAttempt: AdminPaymentAttemptRecord = {
      ...baseAttempt,
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

    const summary = summarizePaymentAttemptForAdmin(financeAttempt);

    expect(summary.canShowFinanceBreakdown).toBe(true);
    expect(summary.financeBreakdownLabel).toBe('wallet 2.00 USD · gateway 8.00 USD');
    expect(summary.tone).toBe('success');
  });
});
