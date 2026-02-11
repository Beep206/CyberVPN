import { apiClient } from './client';

// Type definitions for partner API responses
type PartnerDashboardResponse = {
  is_partner: boolean;
  tier?: string | null;
  total_clients?: number;
  total_earned?: number;
  codes?: Array<{
    partner_code: string;
    markup_pct: number;
    created_at: string;
  }>;
};

type BindPartnerCodeRequest = {
  partner_code: string;
};

type BindPartnerCodeResponse = {
  message: string;
  is_partner: boolean;
};

/**
 * Partner API client
 * Manages partner program features: dashboard and code binding
 */
export const partnerApi = {
  /**
   * Get partner dashboard data
   * GET /api/v1/partner/dashboard
   *
   * Returns partner status, tier, clients, earnings, and codes list.
   * If user is not a partner, returns { is_partner: false }.
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
  bindCode: (data: BindPartnerCodeRequest) =>
    apiClient.post<BindPartnerCodeResponse>('/partner/bind', data),
};
