import { apiClient } from './client';
import type { operations } from './generated/types';

// Extract types from OpenAPI operations
type WalletResponse = operations['get_wallet_api_v1_wallet_get']['responses'][200]['content']['application/json'];
type WalletTransactionResponse = operations['list_wallet_transactions_api_v1_wallet_transactions_get']['responses'][200]['content']['application/json'];
type WithdrawRequest = operations['request_withdrawal_api_v1_wallet_withdraw_post']['requestBody']['content']['application/json'];
type WithdrawalResponse = operations['request_withdrawal_api_v1_wallet_withdraw_post']['responses'][201]['content']['application/json'];
type WithdrawalsResponse = operations['list_withdrawals_api_v1_wallet_withdrawals_get']['responses'][200]['content']['application/json'];
type AdminPendingWithdrawalsResponse =
  operations['admin_list_pending_withdrawals_api_v1_admin_withdrawals_get']['responses'][200]['content']['application/json'];
type AdminProcessWithdrawalRequest =
  operations['admin_approve_withdrawal_api_v1_admin_withdrawals__withdrawal_id__approve_put']['requestBody']['content']['application/json'];
type AdminProcessWithdrawalResponse =
  operations['admin_approve_withdrawal_api_v1_admin_withdrawals__withdrawal_id__approve_put']['responses'][200]['content']['application/json'];
type AdminWalletResponse =
  operations['admin_get_wallet_api_v1_admin_wallets__user_id__get']['responses'][200]['content']['application/json'];
type AdminWalletTopupRequest =
  operations['admin_topup_wallet_api_v1_admin_wallets__user_id__topup_post']['requestBody']['content']['application/json'];
type AdminWalletTopupResponse =
  operations['admin_topup_wallet_api_v1_admin_wallets__user_id__topup_post']['responses'][200]['content']['application/json'];

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

/**
 * Admin wallet operations
 * Manages moderation flows around pending withdrawal requests.
 */
export const adminWalletApi = {
  /**
   * Get wallet state for a specific user UUID.
   * GET /api/v1/admin/wallets/{user_id}
   */
  getWallet: (userId: string) =>
    apiClient.get<AdminWalletResponse>(`/admin/wallets/${userId}`),

  /**
   * Credit funds to a specific user's wallet.
   * POST /api/v1/admin/wallets/{user_id}/topup
   */
  topupWallet: (userId: string, data: AdminWalletTopupRequest) =>
    apiClient.post<AdminWalletTopupResponse>(`/admin/wallets/${userId}/topup`, data),

  /**
   * Get all pending withdrawal requests awaiting admin action.
   * GET /api/v1/admin/withdrawals
   */
  getPendingWithdrawals: () =>
    apiClient.get<AdminPendingWithdrawalsResponse>('/admin/withdrawals'),

  /**
   * Approve a pending withdrawal request.
   * PUT /api/v1/admin/withdrawals/{withdrawal_id}/approve
   */
  approveWithdrawal: (withdrawalId: string, data: AdminProcessWithdrawalRequest = {}) =>
    apiClient.put<AdminProcessWithdrawalResponse>(
      `/admin/withdrawals/${withdrawalId}/approve`,
      data,
    ),

  /**
   * Reject a pending withdrawal request.
   * PUT /api/v1/admin/withdrawals/{withdrawal_id}/reject
   */
  rejectWithdrawal: (withdrawalId: string, data: AdminProcessWithdrawalRequest = {}) =>
    apiClient.put<AdminProcessWithdrawalResponse>(
      `/admin/withdrawals/${withdrawalId}/reject`,
      data,
    ),
};
