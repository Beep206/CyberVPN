import type { components } from '@/lib/api/generated/types';

export type BillingEventKind = 'order' | 'payment';
export type BillingFilter = 'all' | 'completed' | 'failed' | 'pending' | 'refunded';
export type StatusTone = 'amber' | 'cyan' | 'green' | 'muted' | 'pink' | 'purple';
export type TransactionDirection = 'credit' | 'debit' | 'neutral';

export type OrderRecord = components['schemas']['OrderResponse'];
export type PaymentRecord = components['schemas']['PaymentHistoryItem'];
export type WalletRecord = components['schemas']['WalletResponse'];
export type WalletTransactionRecord = components['schemas']['WalletTransactionResponse'];
export type WithdrawalRecord = components['schemas']['WithdrawalResponse'];

export type BillingEvent = {
  amount: number;
  createdAt: string;
  currency: string;
  id: string;
  kind: BillingEventKind;
  status: string;
  subtitle: string;
  title: string;
  tone: StatusTone;
};

const CREDIT_HINTS = ['credit', 'deposit', 'topup', 'commission', 'reward', 'refund', 'cashback'];
const DEBIT_HINTS = ['debit', 'withdraw', 'withdrawal', 'subscription', 'purchase', 'payment'];
const COMPLETED_STATUSES = new Set(['paid', 'settled', 'completed', 'committed', 'success']);
const FAILED_STATUSES = new Set(['cancelled', 'canceled', 'expired', 'failed', 'rejected']);
const PENDING_STATUSES = new Set(['awaiting_payment', 'created', 'open', 'pending', 'pending_payment', 'processing']);
const REFUNDED_STATUSES = new Set(['refunded', 'reversed']);

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function normalize(value: string | null | undefined): string {
  return value?.trim().toLowerCase() ?? '';
}

function normalizeCurrency(currency: string | null | undefined): string {
  const candidate = currency?.trim().toUpperCase();
  return candidate && candidate.length >= 3 ? candidate : 'USD';
}

function timestamp(value: string): number {
  const parsed = new Date(value).getTime();
  return Number.isNaN(parsed) ? 0 : parsed;
}

export function formatMoney(locale: string, amount: number, currency: string): string {
  const safeAmount = isFiniteNumber(amount) ? amount : 0;
  const safeCurrency = normalizeCurrency(currency);

  try {
    return new Intl.NumberFormat(locale, {
      currency: safeCurrency,
      maximumFractionDigits: safeAmount % 1 === 0 ? 0 : 2,
      style: 'currency',
    }).format(safeAmount);
  } catch {
    return `${safeAmount.toFixed(2)} ${safeCurrency}`;
  }
}

export function formatDateTime(value: string | null | undefined, locale = 'en-EN'): string | null {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  try {
    return new Intl.DateTimeFormat(locale, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(date);
  } catch {
    return date.toISOString();
  }
}

export function formatShortId(id: string | null | undefined): string {
  const safeId = id?.trim();
  if (!safeId) {
    return 'n/a';
  }

  return safeId.length <= 10 ? safeId : `${safeId.slice(0, 8)}...`;
}

export function formatLabel(value: string | null | undefined, fallback: string): string {
  const normalized = value?.trim();
  if (!normalized) {
    return fallback;
  }

  return normalized
    .replaceAll('_', ' ')
    .replaceAll('-', ' ')
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

export function getTransactionDirection(
  transaction: WalletTransactionRecord,
): TransactionDirection {
  if (transaction.amount > 0) {
    return 'credit';
  }

  if (transaction.amount < 0) {
    return 'debit';
  }

  const type = normalize(transaction.type);
  const reason = normalize(transaction.reason);
  const searchable = `${type} ${reason}`;

  if (CREDIT_HINTS.some((hint) => searchable.includes(hint))) {
    return 'credit';
  }

  if (DEBIT_HINTS.some((hint) => searchable.includes(hint))) {
    return 'debit';
  }

  return 'neutral';
}

export function getTransactionTone(transaction: WalletTransactionRecord): StatusTone {
  const direction = getTransactionDirection(transaction);

  if (direction === 'credit') {
    return 'green';
  }

  if (direction === 'debit') {
    return 'pink';
  }

  return 'muted';
}

export function getStatusTone(status: string | null | undefined): StatusTone {
  const normalized = normalize(status);

  if (COMPLETED_STATUSES.has(normalized)) {
    return 'green';
  }

  if (PENDING_STATUSES.has(normalized)) {
    return 'cyan';
  }

  if (FAILED_STATUSES.has(normalized)) {
    return 'pink';
  }

  if (REFUNDED_STATUSES.has(normalized)) {
    return 'purple';
  }

  return 'muted';
}

export function getBillingFilter(status: string | null | undefined): BillingFilter {
  const normalized = normalize(status);

  if (COMPLETED_STATUSES.has(normalized)) {
    return 'completed';
  }

  if (PENDING_STATUSES.has(normalized)) {
    return 'pending';
  }

  if (FAILED_STATUSES.has(normalized)) {
    return 'failed';
  }

  if (REFUNDED_STATUSES.has(normalized)) {
    return 'refunded';
  }

  return 'all';
}

export function getOrderStatus(order: OrderRecord): string {
  if (order.settlement_status && order.settlement_status !== 'none') {
    return order.settlement_status;
  }

  return order.order_status;
}

export function getOrderDisplayName(order: OrderRecord): string {
  const itemName = order.items
    .map((item) => item.display_name?.trim())
    .find((name): name is string => Boolean(name));

  if (itemName) {
    return itemName;
  }

  return 'Order';
}

export function getSortedTransactions(
  transactions: WalletTransactionRecord[],
): WalletTransactionRecord[] {
  return [...transactions].sort((first, second) => timestamp(second.created_at) - timestamp(first.created_at));
}

export function getSortedWithdrawals(withdrawals: WithdrawalRecord[]): WithdrawalRecord[] {
  return [...withdrawals].sort((first, second) => timestamp(second.created_at) - timestamp(first.created_at));
}

export function getPendingWithdrawals(withdrawals: WithdrawalRecord[]): WithdrawalRecord[] {
  return getSortedWithdrawals(withdrawals).filter((withdrawal) =>
    ['pending', 'processing'].includes(normalize(withdrawal.status)),
  );
}

export function getWalletLiability(wallet: WalletRecord | null | undefined): number {
  if (!wallet) {
    return 0;
  }

  return Math.max(0, wallet.balance + wallet.frozen);
}

export function getRecentTransaction(
  transactions: WalletTransactionRecord[],
): WalletTransactionRecord | null {
  return getSortedTransactions(transactions)[0] ?? null;
}

export function buildBillingEvents({
  labels,
  orders,
  payments,
}: {
  labels?: {
    order: string;
    paymentSuffix: string;
  };
  orders: OrderRecord[];
  payments: PaymentRecord[];
}): BillingEvent[] {
  const safeLabels = labels ?? {
    order: 'Order',
    paymentSuffix: 'payment',
  };
  const paymentEvents = payments.map((payment): BillingEvent => ({
    amount: payment.amount,
    createdAt: payment.created_at,
    currency: normalizeCurrency(payment.currency),
    id: payment.id,
    kind: 'payment',
    status: payment.status,
    subtitle: payment.provider,
    title: `${formatLabel(payment.provider, 'Payment')} ${safeLabels.paymentSuffix}`,
    tone: getStatusTone(payment.status),
  }));

  const orderEvents = orders.map((order): BillingEvent => ({
    amount: order.displayed_price,
    createdAt: order.created_at,
    currency: normalizeCurrency(order.currency_code),
    id: order.id,
    kind: 'order',
    status: getOrderStatus(order),
    subtitle: `${formatMoney('en-EN', order.gateway_amount, order.currency_code)} gateway / ${formatMoney(
      'en-EN',
      order.wallet_amount,
      order.currency_code,
    )} wallet`,
    title: getOrderDisplayName(order) === 'Order' ? safeLabels.order : getOrderDisplayName(order),
    tone: getStatusTone(getOrderStatus(order)),
  }));

  return [...paymentEvents, ...orderEvents].sort(
    (first, second) => timestamp(second.createdAt) - timestamp(first.createdAt),
  );
}

export function filterBillingEvents(events: BillingEvent[], filter: BillingFilter): BillingEvent[] {
  if (filter === 'all') {
    return events;
  }

  return events.filter((event) => getBillingFilter(event.status) === filter);
}

export function getCompletedPaymentTotal(payments: PaymentRecord[]): number {
  return payments
    .filter((payment) => getBillingFilter(payment.status) === 'completed')
    .reduce((total, payment) => total + payment.amount, 0);
}

export function getOrderWalletTotal(orders: OrderRecord[]): number {
  return orders.reduce((total, order) => total + order.wallet_amount, 0);
}

export function getOrderGatewayTotal(orders: OrderRecord[]): number {
  return orders.reduce((total, order) => total + order.gateway_amount, 0);
}

export function canRetryOrder(order: OrderRecord): boolean {
  return order.gateway_amount > 0 && getBillingFilter(getOrderStatus(order)) !== 'completed';
}
