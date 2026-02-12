import { apiClient } from './client';
import type { operations } from './generated/types';

// Extract types from OpenAPI operations
type CreateInvoiceRequest = operations['create_crypto_invoice_api_v1_payments_crypto_invoice_post']['requestBody']['content']['application/json'];
type CreateInvoiceResponse = operations['create_crypto_invoice_api_v1_payments_crypto_invoice_post']['responses'][201]['content']['application/json'];
type InvoiceStatusResponse = operations['get_crypto_invoice_api_v1_payments_crypto_invoice__invoice_id__get']['responses'][200]['content']['application/json'];
type PaymentHistoryResponse = operations['get_payment_history_api_v1_payments_history_get']['responses'][200]['content']['application/json'];

/**
 * Payments API client
 * Manages cryptocurrency payments, invoices, and payment history
 */
export const paymentsApi = {
  /**
   * Create a new cryptocurrency payment invoice
   * POST /api/v1/payments/crypto/invoice
   *
   * Creates a new payment invoice for subscription purchase or wallet topup.
   * Generates a unique payment address and QR code for the transaction.
   *
   * @param data - Payment details (amount, currency, plan_id, etc.)
   * @returns Invoice with payment address, QR code, and tracking ID
   */
  createInvoice: (data: CreateInvoiceRequest) =>
    apiClient.post<CreateInvoiceResponse>('/payments/crypto/invoice', data),

  /**
   * Get payment invoice status
   * GET /api/v1/payments/crypto/invoice/{invoice_id}
   *
   * Returns current status of a payment invoice:
   * - pending: awaiting payment
   * - paid: payment received and confirmed
   * - expired: invoice expired before payment
   * - failed: payment failed or rejected
   *
   * @param invoiceId - Invoice UUID
   * @throws 404 - Invoice not found
   */
  getInvoiceStatus: (invoiceId: string) =>
    apiClient.get<InvoiceStatusResponse>(`/payments/crypto/invoice/${invoiceId}`),

  /**
   * Get authenticated user's payment history
   * GET /api/v1/payments/history
   *
   * Returns paginated list of all payment transactions including:
   * - Cryptocurrency payments
   * - Wallet deposits
   * - Subscription purchases
   * - Refunds
   *
   * Ordered by most recent first.
   */
  getHistory: (params?: { offset?: number; limit?: number }) =>
    apiClient.get<PaymentHistoryResponse>('/payments/history', { params }),
};
