import { apiClient } from './client';
import type { operations } from './generated/types';

type ChangePasswordRequest =
  operations['change_password_api_v1_auth_change_password_post']['requestBody']['content']['application/json'];
type ChangePasswordResponse =
  operations['change_password_api_v1_auth_change_password_post']['responses'][200]['content']['application/json'];
type AntiphishingCodeResponse =
  operations['get_antiphishing_code_api_v1_security_antiphishing_get']['responses'][200]['content']['application/json'];
type SetAntiphishingCodeRequest =
  operations['set_antiphishing_code_api_v1_security_antiphishing_post']['requestBody']['content']['application/json'];
type DeleteAntiphishingCodeResponse =
  operations['delete_antiphishing_code_api_v1_security_antiphishing_delete']['responses'][200]['content']['application/json'];
type RiskReviewQueueParams =
  operations['list_risk_review_queue_api_v1_security_risk_reviews_queue_get']['parameters']['query'];
type RiskReviewQueueResponse =
  operations['list_risk_review_queue_api_v1_security_risk_reviews_queue_get']['responses'][200]['content']['application/json'];
type RiskReviewDetailResponse =
  operations['get_risk_review_api_v1_security_risk_reviews__risk_review_id__get']['responses'][200]['content']['application/json'];
type AttachRiskReviewAttachmentRequest =
  operations['attach_risk_review_attachment_api_v1_security_risk_reviews__risk_review_id__attachments_post']['requestBody']['content']['application/json'];
type AttachRiskReviewAttachmentResponse =
  operations['attach_risk_review_attachment_api_v1_security_risk_reviews__risk_review_id__attachments_post']['responses'][201]['content']['application/json'];
type ResolveRiskReviewRequest =
  operations['resolve_risk_review_api_v1_security_risk_reviews__risk_review_id__resolve_post']['requestBody']['content']['application/json'];
type ResolveRiskReviewResponse =
  operations['resolve_risk_review_api_v1_security_risk_reviews__risk_review_id__resolve_post']['responses'][200]['content']['application/json'];
type GovernanceActionsParams =
  operations['list_governance_actions_api_v1_security_governance_actions_get']['parameters']['query'];
type GovernanceActionsResponse =
  operations['list_governance_actions_api_v1_security_governance_actions_get']['responses'][200]['content']['application/json'];
type CreateGovernanceActionRequest =
  operations['create_governance_action_api_v1_security_governance_actions_post']['requestBody']['content']['application/json'];
type CreateGovernanceActionResponse =
  operations['create_governance_action_api_v1_security_governance_actions_post']['responses'][201]['content']['application/json'];

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
    apiClient.post<AntiphishingCodeResponse>('/security/antiphishing', data),

  /**
   * Delete antiphishing code
   * DELETE /api/v1/security/antiphishing
   *
   * Removes the antiphishing code. Future emails will not include it.
   */
  deleteAntiphishingCode: () =>
    apiClient.delete<DeleteAntiphishingCodeResponse>('/security/antiphishing'),

  listRiskReviewQueue: (params?: RiskReviewQueueParams) =>
    apiClient.get<RiskReviewQueueResponse>('/security/risk-reviews/queue', { params }),

  getRiskReview: (riskReviewId: string) =>
    apiClient.get<RiskReviewDetailResponse>(`/security/risk-reviews/${riskReviewId}`),

  attachRiskReviewAttachment: (riskReviewId: string, data: AttachRiskReviewAttachmentRequest) =>
    apiClient.post<AttachRiskReviewAttachmentResponse>(
      `/security/risk-reviews/${riskReviewId}/attachments`,
      data,
    ),

  resolveRiskReview: (riskReviewId: string, data: ResolveRiskReviewRequest) =>
    apiClient.post<ResolveRiskReviewResponse>(
      `/security/risk-reviews/${riskReviewId}/resolve`,
      data,
    ),

  listGovernanceActions: (params?: GovernanceActionsParams) =>
    apiClient.get<GovernanceActionsResponse>('/security/governance-actions', { params }),

  createGovernanceAction: (data: CreateGovernanceActionRequest) =>
    apiClient.post<CreateGovernanceActionResponse>('/security/governance-actions', data),
};

export type {
  AttachRiskReviewAttachmentRequest,
  AttachRiskReviewAttachmentResponse,
  CreateGovernanceActionRequest,
  CreateGovernanceActionResponse,
  GovernanceActionsParams,
  GovernanceActionsResponse,
  ResolveRiskReviewRequest,
  ResolveRiskReviewResponse,
  RiskReviewDetailResponse,
  RiskReviewQueueParams,
  RiskReviewQueueResponse,
};
