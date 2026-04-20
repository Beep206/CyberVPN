import { apiClient } from './client';
import type { operations } from './generated/types';

// Extract types from OpenAPI operations
type ValidatePromoRequest = operations['validate_promo_api_v1_promo_validate_post']['requestBody']['content']['application/json'];
type ValidatePromoResponse = operations['validate_promo_api_v1_promo_validate_post']['responses'][200]['content']['application/json'];

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
};
