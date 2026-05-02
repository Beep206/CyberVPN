import { describe, expect, it } from 'vitest';
import {
  buildBillingEvents,
  canRetryOrder,
  filterBillingEvents,
  formatShortId,
  getBillingFilter,
  getCompletedPaymentTotal,
  getOrderGatewayTotal,
  getOrderWalletTotal,
  getPendingWithdrawals,
  getRecentTransaction,
  getStatusTone,
  getTransactionDirection,
  getWalletLiability,
  type OrderRecord,
  type PaymentRecord,
  type WalletRecord,
  type WalletTransactionRecord,
  type WithdrawalRecord,
} from '../billing-cabinet-model';

const transaction = (
  overrides: Partial<WalletTransactionRecord>,
): WalletTransactionRecord => ({
  amount: 0,
  balance_after: 0,
  created_at: '2026-04-24T10:00:00Z',
  description: null,
  id: 'tx-1',
  reason: 'adjustment',
  type: 'adjustment',
  ...overrides,
});

const withdrawal = (overrides: Partial<WithdrawalRecord>): WithdrawalRecord => ({
  amount: 10,
  created_at: '2026-04-24T10:00:00Z',
  currency: 'USD',
  id: 'wd-1',
  method: 'cryptobot',
  status: 'pending',
  ...overrides,
});

const payment = (overrides: Partial<PaymentRecord>): PaymentRecord => ({
  amount: 29,
  created_at: '2026-04-24T10:00:00Z',
  currency: 'USD',
  id: 'pay-1',
  provider: 'cryptobot',
  status: 'completed',
  ...overrides,
});

const order = (overrides: Partial<OrderRecord>): OrderRecord => ({
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
  gateway_amount: 19,
  id: 'order-1',
  items: [
    {
      created_at: '2026-04-24T11:00:00Z',
      currency_code: 'USD',
      display_name: 'Pro Plan',
      id: 'item-1',
      item_snapshot: {},
      item_type: 'plan',
      order_id: 'order-1',
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
  settlement_status: 'paid',
  storefront_id: 'storefront-1',
  updated_at: '2026-04-24T11:00:00Z',
  user_id: 'user-1',
  wallet_amount: 10,
  ...overrides,
});

describe('billing-cabinet-model', () => {
  it('detects wallet transaction direction from amount and reason hints', () => {
    expect(getTransactionDirection(transaction({ amount: 25, type: 'credit' }))).toBe('credit');
    expect(getTransactionDirection(transaction({ amount: -10, type: 'debit' }))).toBe('debit');
    expect(getTransactionDirection(transaction({ reason: 'referral_commission' }))).toBe('credit');
    expect(getTransactionDirection(transaction({ reason: 'subscription_payment' }))).toBe('debit');
  });

  it('sorts recent transactions and pending withdrawals by created time', () => {
    expect(
      getRecentTransaction([
        transaction({ created_at: '2026-04-23T10:00:00Z', id: 'old' }),
        transaction({ created_at: '2026-04-24T10:00:00Z', id: 'new' }),
      ])?.id,
    ).toBe('new');

    expect(
      getPendingWithdrawals([
        withdrawal({ id: 'done', status: 'completed' }),
        withdrawal({ created_at: '2026-04-23T10:00:00Z', id: 'pending-old' }),
        withdrawal({ created_at: '2026-04-24T10:00:00Z', id: 'pending-new' }),
      ]).map((item) => item.id),
    ).toEqual(['pending-new', 'pending-old']);
  });

  it('maps billing statuses to filters and tones', () => {
    expect(getBillingFilter('completed')).toBe('completed');
    expect(getBillingFilter('awaiting_payment')).toBe('pending');
    expect(getBillingFilter('failed')).toBe('failed');
    expect(getBillingFilter('refunded')).toBe('refunded');
    expect(getStatusTone('unknown')).toBe('muted');
  });

  it('builds and filters a merged billing timeline', () => {
    const events = buildBillingEvents({
      orders: [order({ id: 'order-paid' })],
      payments: [payment({ created_at: '2026-04-25T10:00:00Z', id: 'pay-latest' })],
    });

    expect(events.map((event) => event.id)).toEqual(['pay-latest', 'order-paid']);
    expect(filterBillingEvents(events, 'completed')).toHaveLength(2);
    expect(filterBillingEvents(events, 'failed')).toHaveLength(0);
  });

  it('calculates totals and retry eligibility without exposing provider internals', () => {
    const wallet: WalletRecord = {
      balance: 40,
      currency: 'USD',
      frozen: 5,
      id: 'wallet-1',
    };

    expect(getWalletLiability(wallet)).toBe(45);
    expect(getCompletedPaymentTotal([payment({ amount: 29 }), payment({ amount: 5, status: 'pending' })])).toBe(29);
    expect(getOrderWalletTotal([order({ wallet_amount: 3 }), order({ wallet_amount: 7 })])).toBe(10);
    expect(getOrderGatewayTotal([order({ gateway_amount: 12 }), order({ gateway_amount: 8 })])).toBe(20);
    expect(canRetryOrder(order({ gateway_amount: 12, settlement_status: 'pending' }))).toBe(true);
    expect(canRetryOrder(order({ gateway_amount: 12, settlement_status: 'paid' }))).toBe(false);
    expect(formatShortId('1234567890abcdef')).toBe('12345678...');
  });
});
