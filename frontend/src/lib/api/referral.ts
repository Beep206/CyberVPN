import { apiClient } from './client';
import type { operations } from './generated/types';

// Extract types from OpenAPI operations
type ReferralStatusResponse = operations['get_referral_status_api_v1_referral_status_get']['responses'][200]['content']['application/json'];
type ReferralCodeResponse = operations['get_referral_code_api_v1_referral_code_get']['responses'][200]['content']['application/json'];
type ReferralStatsResponse = operations['get_referral_stats_api_v1_referral_stats_get']['responses'][200]['content']['application/json'];
type ReferralCommissionResponse = operations['get_recent_commissions_api_v1_referral_recent_get']['responses'][200]['content']['application/json'];

/**
 * Referral Program API client
 * Manages user referral codes, earnings, and commission tracking
 */
export const referralApi = {
  /**
   * Get referral program status
   * GET /api/v1/referral/status
   *
   * Returns whether the referral program is currently enabled
   * and the active commission rate percentage.
   */
  getStatus: () =>
    apiClient.get<ReferralStatusResponse>('/referral/status'),

  /**
   * Get or generate authenticated user's referral code
   * GET /api/v1/referral/code
   *
   * Returns the user's unique referral code.
   * If user doesn't have a code yet, generates a new one.
   */
  getCode: () =>
    apiClient.get<ReferralCodeResponse>('/referral/code'),

  /**
   * Get referral statistics for authenticated user
   * GET /api/v1/referral/stats
   *
   * Returns aggregated referral metrics:
   * - Total referrals count
   * - Total earnings (commission sum)
   * - Current commission rate
   */
  getStats: () =>
    apiClient.get<ReferralStatsResponse>('/referral/stats'),

  /**
   * Get recent referral commissions
   * GET /api/v1/referral/recent
   *
   * Returns the 10 most recent referral commissions
   * earned by the authenticated user.
   */
  getRecentCommissions: () =>
    apiClient.get<ReferralCommissionResponse>('/referral/recent'),
};
