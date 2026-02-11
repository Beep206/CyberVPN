import { apiClient } from './client';
import type { operations } from './generated/types';

// Extract types from OpenAPI operations
type ValidatePromoRequest = operations['validate_promo_api_v1_promo_validate_post']['requestBody']['content']['application/json'];
type ValidatePromoResponse = operations['validate_promo_api_v1_promo_validate_post']['responses'][200]['content']['application/json'];

/**
 * Promo Codes API client
 * Manages promo code validation and discount preview
 */
export const promoApi = {
  /**
   * Validate a promo code
   * POST /api/v1/promo/validate
   *
   * Validates a promo code and returns discount details.
   * Shows discount amount, expiry, and applicable plans.
   *
   * @param data - Promo code to validate
   * @returns Discount details and validation result
   * @throws 404 - Promo code not found or expired
   * @throws 400 - Promo code not valid for user
   */
  validate: (data: ValidatePromoRequest) =>
    apiClient.post<ValidatePromoResponse>('/promo/validate', data),
};
