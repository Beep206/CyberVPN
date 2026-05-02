import { apiClient } from './client';
import type { operations } from './generated/types';

// Extract types from OpenAPI operations
type ValidatePromoRequest = operations['validate_promo_api_v1_promo_validate_post']['requestBody']['content']['application/json'];
type ValidatePromoResponse = operations['validate_promo_api_v1_promo_validate_post']['responses'][200]['content']['application/json'];

export interface ResolveGrowthCodeRequest {
  code: string;
  action_context: 'checkout' | 'redeem' | 'signup' | 'admin_lookup';
  storefront_key?: string | null;
  plan_id?: string | null;
  amount?: number | null;
  channel?: string;
  existing_partner_code_present?: boolean;
  existing_promo_present?: boolean;
}

export interface ResolveGrowthCodeResponse {
  accepted: boolean;
  code_type: 'invite' | 'referral' | 'promo' | 'gift' | 'partner' | null;
  action_context: 'checkout' | 'redeem' | 'signup' | 'admin_lookup';
  result: 'accepted' | 'rejected' | 'conflicted' | 'blocked_by_risk';
  reject_reason?: string | null;
  conflict_code?: string | null;
  wrong_context_target?: 'checkout' | 'redeem' | null;
  issuer_type?: string | null;
  owner_type?: string | null;
  resolved_code_id?: string | null;
  promo_code_id?: string | null;
  partner_code_id?: string | null;
  user_message_key: string;
}

/**
 * Promo Codes API client
 * Validates promotional discount codes for purchases
 */
export const codesApi = {
  /**
   * Validate a promo code and calculate discount
   * POST /api/v1/promo/validate
   *
   * Validates a promo code against the authenticated user's purchase context:
   * - Checks code exists and is active
   * - Verifies expiration date
   * - Checks usage limits (max uses, single-use)
   * - Validates plan eligibility
   * - Calculates discount amount based on type (percentage/fixed)
   *
   * @param data - Promo code, plan ID, and purchase amount
   * @returns Validation result with calculated discount or error details
   *
   * @throws 404 - Promo code not found
   * @throws 422 - Promo code invalid or exhausted
   */
  validate: (data: ValidatePromoRequest) =>
    apiClient.post<ValidatePromoResponse>('/promo/validate', data),

  resolve: (data: ResolveGrowthCodeRequest) =>
    apiClient.post<ResolveGrowthCodeResponse>('/codes/resolve', data),
};
