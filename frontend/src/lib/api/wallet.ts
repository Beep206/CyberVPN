import { apiClient } from './client';
import type { operations } from './generated/types';

// Extract types from OpenAPI operations
type WalletResponse = operations['get_wallet_api_v1_wallet_get']['responses'][200]['content']['application/json'];
type WalletTransactionResponse = operations['list_wallet_transactions_api_v1_wallet_transactions_get']['responses'][200]['content']['application/json'];
type WithdrawRequest = operations['request_withdrawal_api_v1_wallet_withdraw_post']['requestBody']['content']['application/json'];
type WithdrawalResponse = operations['request_withdrawal_api_v1_wallet_withdraw_post']['responses'][201]['content']['application/json'];
type WithdrawalsResponse = operations['list_withdrawals_api_v1_wallet_withdrawals_get']['responses'][200]['content']['application/json'];

/**
 * Wallet API client
 * Manages user wallet balance, transactions, and withdrawal requests
 */
export const walletApi = {
  /**
   * Get authenticated user's wallet balance
   * GET /api/v1/wallet
   *
   * Returns current wallet balance and wallet metadata.
   *
   * @throws 404 - Wallet not found (auto-created on first access)
   */
  getBalance: () =>
    apiClient.get<WalletResponse>('/wallet'),

  /**
   * Get wallet transaction history
   * GET /api/v1/wallet/transactions
   *
   * Returns paginated list of wallet transactions (deposits, withdrawals,
   * referral commissions, etc.).
   *
   * @param params - Pagination params (offset, limit)
   * @param params.offset - Number of records to skip (default: 0)
   * @param params.limit - Max records to return (1-100, default: 50)
   */
  getTransactions: (params?: { offset?: number; limit?: number }) =>
    apiClient.get<WalletTransactionResponse>('/wallet/transactions', { params }),

  /**
   * Request withdrawal from wallet
   * POST /api/v1/wallet/withdraw
   *
   * Creates a withdrawal request that requires admin approval.
   * Validates minimum withdrawal amount and sufficient balance.
   *
   * @param data - Withdrawal amount and payment method
   * @returns Created withdrawal request with pending status
   *
   * @throws 422 - Below minimum amount or insufficient balance
   * @throws 400 - Invalid withdrawal parameters
   */
  requestWithdrawal: (data: WithdrawRequest) =>
    apiClient.post<WithdrawalResponse>('/wallet/withdraw', data),

  /**
   * Get authenticated user's withdrawal requests
   * GET /api/v1/wallet/withdrawals
   *
   * Returns all withdrawal requests for the user (pending, approved, rejected).
   */
  getWithdrawals: () =>
    apiClient.get<WithdrawalsResponse>('/wallet/withdrawals'),
};
