import { apiClient } from './client';

// Type definitions for security API responses
type ChangePasswordRequest = {
  current_password: string;
  new_password: string;
  new_password_confirm: string;
};

type ChangePasswordResponse = {
  message: string;
};

type AntiphishingCodeResponse = {
  code: string | null;
};

type SetAntiphishingCodeRequest = {
  code: string;
};

type SetAntiphishingCodeResponse = {
  message: string;
};

type DeleteAntiphishingCodeResponse = {
  message: string;
};

/**
 * Security API client
 * Manages account security features: password changes and antiphishing codes
 */
export const securityApi = {
  /**
   * Change user password
   * POST /api/v1/auth/change-password
   *
   * Requires current password verification. Rate limited to 3 attempts per hour.
   *
   * @param data - Current password, new password, confirmation
   *
   * @throws 401 - Invalid current password
   * @throws 422 - Password validation failed
   * @throws 429 - Rate limit exceeded (3/hr)
   */
  changePassword: (data: ChangePasswordRequest) =>
    apiClient.post<ChangePasswordResponse>('/auth/change-password', data),

  /**
   * Get antiphishing code (masked)
   * GET /api/v1/security/antiphishing
   *
   * Returns the user's antiphishing code with partial masking for security.
   */
  getAntiphishingCode: () =>
    apiClient.get<AntiphishingCodeResponse>('/security/antiphishing'),

  /**
   * Create or update antiphishing code
   * POST /api/v1/security/antiphishing
   *
   * Sets a custom antiphishing code (4-32 characters).
   * Displayed in emails to verify authenticity.
   *
   * @param data - New antiphishing code
   *
   * @throws 422 - Invalid code format
   */
  setAntiphishingCode: (data: SetAntiphishingCodeRequest) =>
    apiClient.post<SetAntiphishingCodeResponse>('/security/antiphishing', data),

  /**
   * Delete antiphishing code
   * DELETE /api/v1/security/antiphishing
   *
   * Removes the antiphishing code. Future emails will not include it.
   */
  deleteAntiphishingCode: () =>
    apiClient.delete<DeleteAntiphishingCodeResponse>('/security/antiphishing'),
};
