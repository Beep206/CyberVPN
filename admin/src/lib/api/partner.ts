import { apiClient } from './client';
import type { operations } from './generated/types';

// Extract types from OpenAPI operations
type PartnerDashboardResponse = operations['get_partner_dashboard_api_v1_partner_dashboard_get']['responses'][200]['content']['application/json'];
type BindPartnerCodeRequest = operations['bind_to_partner_api_v1_partner_bind_post']['requestBody']['content']['application/json'];
type BindPartnerCodeResponse = operations['bind_to_partner_api_v1_partner_bind_post']['responses'][200]['content']['application/json'];
type PartnerCodeResponse = operations['list_partner_codes_api_v1_partner_codes_get']['responses'][200]['content']['application/json'];
type CreatePartnerCodeRequest = operations['create_partner_code_api_v1_partner_codes_post']['requestBody']['content']['application/json'];
type PartnerEarningResponse = operations['list_partner_earnings_api_v1_partner_earnings_get']['responses'][200]['content']['application/json'];

/**
 * Partner API client
 * Manages partner program features: dashboard, codes, and earnings
 */
export const partnerApi = {
  /**
   * Get partner dashboard data
   * GET /api/v1/partner/dashboard
   *
   * Returns partner status, tier, clients, earnings, and codes list.
   */
  getDashboard: () =>
    apiClient.get<PartnerDashboardResponse>('/partner/dashboard'),

  /**
   * Bind partner code to user account
   * POST /api/v1/partner/bind
   *
   * Associates the user with a partner program by binding a partner code.
   *
   * @param data - Partner code to bind
   *
   * @throws 404 - Partner code not found
   * @throws 400 - User is already a partner
   */
  bindToPartner: (data: BindPartnerCodeRequest) =>
    apiClient.post<BindPartnerCodeResponse>('/partner/bind', data),

  /**
   * List partner codes
   * GET /api/v1/partner/codes
   *
   * Returns all partner codes owned by the authenticated user.
   */
  listCodes: () =>
    apiClient.get<PartnerCodeResponse>('/partner/codes'),

  /**
   * Create a new partner code
   * POST /api/v1/partner/codes
   *
   * Creates a new partner referral code with an optional markup percentage.
   *
   * @param data - Code name and markup percentage
   */
  createCode: (data: CreatePartnerCodeRequest) =>
    apiClient.post<PartnerCodeResponse>('/partner/codes', data),

  /**
   * List partner earnings
   * GET /api/v1/partner/earnings
   *
   * Returns all earnings from the partner's referrals.
   */
  listEarnings: () =>
    apiClient.get<PartnerEarningResponse>('/partner/earnings'),
};
