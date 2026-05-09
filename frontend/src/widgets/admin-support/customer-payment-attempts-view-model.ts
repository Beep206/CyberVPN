export type Stage1PaymentAttemptViewRole =
  | 'admin'
  | 'finance'
  | 'operator'
  | 'owner'
  | 'owner/super_admin'
  | 'owner_super_admin'
  | 'super_admin'
  | 'support'
  | 'viewer';

export type AdminPaymentAttemptVisibility = 'finance' | 'support';

export type AdminPaymentAttemptReviewState =
  | 'alert_15m'
  | 'manual_review'
  | 'ok'
  | 'p0_blocker'
  | 'p1_escalation';

export type AdminPaymentAttemptRecord = {
  age_minutes: number;
  attempt_number: number;
  created_at: string;
  currency_code: string;
  displayed_amount: number;
  external_reference_fingerprint: string | null;
  gateway_amount: number | null;
  id: string;
  idempotency_key_present: boolean;
  invoice_expires_at: string | null;
  invoice_present: boolean;
  launch_blocker: boolean;
  manual_review_required: boolean;
  order_id: string;
  order_status: string;
  payment_id: string | null;
  payment_record_present: boolean;
  provider: string;
  provider_status: string | null;
  redacted_fields: string[];
  review_reason: string | null;
  review_state: AdminPaymentAttemptReviewState;
  sale_channel: string;
  settlement_status: string;
  stage1_payment_state: string;
  status: string;
  support_escalation: boolean;
  terminal_at: string | null;
  updated_at: string;
  user_id: string;
  visibility: AdminPaymentAttemptVisibility;
  wallet_amount: number | null;
};

export type SafePaymentAttemptSummary = {
  amountLabel: string;
  canShowFinanceBreakdown: boolean;
  financeBreakdownLabel: string | null;
  providerLabel: string;
  referenceLabel: string;
  requiresSupport: boolean;
  reviewLabel: string;
  statusLabel: string;
  tone: 'danger' | 'muted' | 'success' | 'warning';
};

const SUPPORT_PAYMENT_ATTEMPT_VIEW_ROLES = new Set<Stage1PaymentAttemptViewRole>([
  'admin',
  'finance',
  'owner',
  'owner/super_admin',
  'owner_super_admin',
  'super_admin',
  'support',
]);

const FINANCE_PAYMENT_ATTEMPT_VIEW_ROLES = new Set<Stage1PaymentAttemptViewRole>([
  'admin',
  'finance',
  'owner',
  'owner/super_admin',
  'owner_super_admin',
  'super_admin',
]);

const SUCCESS_STATES = new Set(['paid', 'succeeded', 'completed']);
const ACTIVE_STATES = new Set(['pending', 'processing']);
const FAILURE_STATES = new Set(['failed', 'cancelled', 'canceled', 'expired']);
const PROVIDER_LABELS: Record<string, string> = {
  cryptobot: 'CryptoBot',
  digiseller: 'Digiseller',
  nowpayments: 'NOWPayments',
  payram: 'PayRam',
  telegram_stars: 'Telegram Stars',
  yookassa: 'YooKassa',
};

export function canViewSupportPaymentAttempts(role: Stage1PaymentAttemptViewRole): boolean {
  return SUPPORT_PAYMENT_ATTEMPT_VIEW_ROLES.has(role);
}

export function canViewFinancePaymentAttempts(role: Stage1PaymentAttemptViewRole): boolean {
  return FINANCE_PAYMENT_ATTEMPT_VIEW_ROLES.has(role);
}

export function buildCustomerPaymentAttemptsEndpoint(userId: string): string {
  return `/admin/mobile-users/${encodeURIComponent(userId)}/payment-attempts`;
}

export function buildFinancePaymentAttemptsEndpoint({
  orderId,
  provider,
  status,
  userId,
}: {
  orderId?: string;
  provider?: string;
  status?: string;
  userId?: string;
} = {}): string {
  const params = new URLSearchParams();
  if (userId) {
    params.set('user_id', userId);
  }
  if (orderId) {
    params.set('order_id', orderId);
  }
  if (status) {
    params.set('status', status);
  }
  if (provider) {
    params.set('provider', provider);
  }
  const query = params.toString();
  return query ? `/admin/payment-attempts?${query}` : '/admin/payment-attempts';
}

function formatProvider(provider: string): string {
  const normalized = provider.toLowerCase();
  if (PROVIDER_LABELS[normalized]) {
    return PROVIDER_LABELS[normalized];
  }

  return provider
    .split(/[_-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function formatCurrency(amount: number, currency: string): string {
  return `${amount.toFixed(2)} ${currency.toUpperCase()}`;
}

function reviewLabel(record: AdminPaymentAttemptRecord): string {
  if (!record.manual_review_required) {
    return 'No review required';
  }

  const reason = record.review_reason?.replaceAll('_', ' ') ?? 'manual review';
  return `${record.review_state.replaceAll('_', ' ')} · ${reason}`;
}

function toneFor(record: AdminPaymentAttemptRecord): SafePaymentAttemptSummary['tone'] {
  if (record.launch_blocker || record.review_state === 'p0_blocker') {
    return 'danger';
  }
  if (record.manual_review_required || record.support_escalation) {
    return 'warning';
  }
  const normalizedState = record.stage1_payment_state.toLowerCase();
  const normalizedStatus = record.status.toLowerCase();
  if (SUCCESS_STATES.has(normalizedState) || SUCCESS_STATES.has(normalizedStatus)) {
    return 'success';
  }
  if (ACTIVE_STATES.has(normalizedState) || ACTIVE_STATES.has(normalizedStatus)) {
    return 'warning';
  }
  if (FAILURE_STATES.has(normalizedState) || FAILURE_STATES.has(normalizedStatus)) {
    return 'danger';
  }
  return 'muted';
}

export function summarizePaymentAttemptForAdmin(
  record: AdminPaymentAttemptRecord,
): SafePaymentAttemptSummary {
  const canShowFinanceBreakdown =
    record.visibility === 'finance' &&
    typeof record.wallet_amount === 'number' &&
    typeof record.gateway_amount === 'number';

  return {
    amountLabel: formatCurrency(record.displayed_amount, record.currency_code),
    canShowFinanceBreakdown,
    financeBreakdownLabel: canShowFinanceBreakdown
      ? `wallet ${formatCurrency(record.wallet_amount ?? 0, record.currency_code)} · gateway ${formatCurrency(
          record.gateway_amount ?? 0,
          record.currency_code,
        )}`
      : null,
    providerLabel: formatProvider(record.provider),
    referenceLabel: record.external_reference_fingerprint
      ? `ref ${record.external_reference_fingerprint}`
      : 'no provider reference',
    requiresSupport: record.manual_review_required || record.support_escalation,
    reviewLabel: reviewLabel(record),
    statusLabel: record.stage1_payment_state.replaceAll('_', ' '),
    tone: toneFor(record),
  };
}
