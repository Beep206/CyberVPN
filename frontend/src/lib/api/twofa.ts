import { apiClient } from './client';
import type { operations } from './generated/types';

// Extract types from OpenAPI operations
type ReauthRequest = operations['reauthenticate_api_v1_2fa_reauth_post']['requestBody']['content']['application/json'];
type ReauthResponse = operations['reauthenticate_api_v1_2fa_reauth_post']['responses'][200]['content']['application/json'];
type SetupResponse = operations['setup_2fa_api_v1_2fa_setup_post']['responses'][200]['content']['application/json'];
type VerifyRequest = operations['verify_2fa_api_v1_2fa_verify_post']['requestBody']['content']['application/json'];
type VerifyResponse = operations['verify_2fa_api_v1_2fa_verify_post']['responses'][200]['content']['application/json'];
type ValidateRequest = operations['validate_2fa_api_v1_2fa_validate_post']['requestBody']['content']['application/json'];
type ValidateResponse = operations['validate_2fa_api_v1_2fa_validate_post']['responses'][200]['content']['application/json'];
type DisableRequest = operations['disable_2fa_post_alias_api_v1_2fa_disable_post']['requestBody']['content']['application/json'];
type DisableResponse = operations['disable_2fa_post_alias_api_v1_2fa_disable_post']['responses'][200]['content']['application/json'];
type StatusResponse = operations['get_2fa_status_api_v1_2fa_status_get']['responses'][200]['content']['application/json'];

/**
 * Two-Factor Authentication (2FA) API client
 * Manages TOTP-based 2FA setup, verification, and session management
 *
 * Security features (CRIT-3):
 * - Password re-authentication required for setup and disable
 * - TOTP secret stored only after successful verification
 * - Rate limiting on verification attempts (5 attempts per 15 min)
 */
export const twofaApi = {
  /**
   * Re-authenticate with password for sensitive 2FA operations
   * POST /api/v1/2fa/reauth
   *
   * Required before setup or disable operations. Returns a temporary
   * reauth token valid for the current session.
   *
   * @param data - User's password for re-authentication
   * @returns Reauth token for subsequent 2FA operations
   *
   * @throws 401 - Invalid password
   * @throws 429 - Rate limit exceeded
   */
  reauth: (data: ReauthRequest) =>
    apiClient.post<ReauthResponse>('/2fa/reauth', data),

  /**
   * Initiate 2FA setup - generate TOTP secret
   * POST /api/v1/2fa/setup
   *
   * Requires valid reauth token. Generates a new TOTP secret and QR code URI.
   * Secret is stored temporarily - finalized only after successful verification.
   *
   * @returns TOTP secret, QR code URI, and backup codes
   *
   * @throws 401 - Missing or invalid reauth token
   * @throws 400 - 2FA already enabled
   */
  setup: () =>
    apiClient.post<SetupResponse>('/2fa/setup'),

  /**
   * Verify TOTP code during setup to finalize 2FA activation
   * POST /api/v1/2fa/verify
   *
   * Validates the TOTP code from authenticator app. On success,
   * permanently stores the TOTP secret and activates 2FA.
   *
   * @param data - 6-digit TOTP code from authenticator
   * @returns Confirmation of successful verification
   *
   * @throws 401 - Missing or invalid reauth token
   * @throws 400 - Invalid TOTP code
   * @throws 429 - Rate limit exceeded (5 attempts per 15 min)
   */
  verify: (data: VerifyRequest) =>
    apiClient.post<VerifyResponse>('/2fa/verify', data),

  /**
   * Validate TOTP code during login
   * POST /api/v1/2fa/validate
   *
   * Used after successful password login when user has 2FA enabled.
   * Validates the current TOTP code.
   *
   * @param data - 6-digit TOTP code from authenticator
   * @returns Validation result
   *
   * @throws 400 - Invalid TOTP code
   * @throws 429 - Rate limit exceeded
   */
  validate: (data: ValidateRequest) =>
    apiClient.post<ValidateResponse>('/2fa/validate', data),

  /**
   * Disable 2FA for authenticated user
   * POST /api/v1/2fa/disable (alias for DELETE, backward compatible)
   *
   * Requires both password re-authentication AND current valid TOTP code.
   * Removes TOTP secret and disables 2FA.
   *
   * @param data - Password and current TOTP code
   * @returns Confirmation of successful disable
   *
   * @throws 401 - Missing or invalid reauth token
   * @throws 400 - Invalid TOTP code or password
   * @throws 404 - 2FA not enabled
   */
  disable: (data: DisableRequest) =>
    apiClient.post<DisableResponse>('/2fa/disable', data),

  /**
   * Get 2FA status for authenticated user
   * GET /api/v1/2fa/status
   *
   * Returns whether 2FA is currently enabled for the user.
   */
  getStatus: () =>
    apiClient.get<StatusResponse>('/2fa/status'),
};
