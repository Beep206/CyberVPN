import { apiClient, CANONICAL_IDEMPOTENCY_HEADER } from './client';
import type { components, operations } from './generated/types';

export type CreateQuoteSessionRequest =
  operations['create_quote_session_api_v1_quotes__post']['requestBody']['content']['application/json'];
export type QuoteSessionResponse = components['schemas']['QuoteSessionResponse'];
export type CreateCheckoutSessionRequest =
  operations['create_checkout_session_api_v1_checkout_sessions__post']['requestBody']['content']['application/json'];
export type CheckoutSessionResponse = components['schemas']['CheckoutSessionResponse'];
export type CreateOrderFromCheckoutRequest =
  operations['create_order_from_checkout_api_v1_orders_commit_post']['requestBody']['content']['application/json'];
export type OrderResponse = components['schemas']['OrderResponse'];
export type CreatePaymentAttemptRequest =
  operations['create_payment_attempt_api_v1_payment_attempts__post']['requestBody']['content']['application/json'];
export type PaymentAttemptResponse = components['schemas']['PaymentAttemptResponse'];

export function createClientIdempotencyKey(prefix: string): string {
  const suffix = typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

  return `${prefix}-${suffix}`;
}

export const commerceApi = {
  createQuoteSession: (data: CreateQuoteSessionRequest) =>
    apiClient.post<QuoteSessionResponse>('/quotes/', data),

  getQuoteSession: (quoteSessionId: string) =>
    apiClient.get<QuoteSessionResponse>(`/quotes/${quoteSessionId}`),

  createCheckoutSession: (data: CreateCheckoutSessionRequest, idempotencyKey: string) =>
    apiClient.post<CheckoutSessionResponse>('/checkout-sessions/', data, {
      headers: {
        [CANONICAL_IDEMPOTENCY_HEADER]: idempotencyKey,
      },
    }),

  getCheckoutSession: (checkoutSessionId: string) =>
    apiClient.get<CheckoutSessionResponse>(`/checkout-sessions/${checkoutSessionId}`),

  commitOrder: (data: CreateOrderFromCheckoutRequest) =>
    apiClient.post<OrderResponse>('/orders/commit', data),

  listOrders: (params?: { limit?: number; offset?: number }) =>
    apiClient.get<OrderResponse[]>('/orders/', { params }),

  getOrder: (orderId: string) =>
    apiClient.get<OrderResponse>(`/orders/${orderId}`),

  createPaymentAttempt: (data: CreatePaymentAttemptRequest, idempotencyKey: string) =>
    apiClient.post<PaymentAttemptResponse>('/payment-attempts/', data, {
      headers: {
        [CANONICAL_IDEMPOTENCY_HEADER]: idempotencyKey,
      },
    }),
};
