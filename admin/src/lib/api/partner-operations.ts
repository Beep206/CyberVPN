import { apiClient, CANONICAL_IDEMPOTENCY_HEADER } from './client';
import type { components } from './generated/types';

type PartnerWorkspaceResponse = components['schemas']['PartnerWorkspaceResponse'];
type PartnerApplicationAdminSummaryResponse =
  components['schemas']['PartnerApplicationAdminSummaryResponse'];
type PartnerApplicationAdminDetailResponse =
  components['schemas']['PartnerApplicationAdminDetailResponse'];
type RequestPartnerApplicationInfoRequest =
  components['schemas']['RequestPartnerApplicationInfoRequest'];
type PartnerApplicationReviewDecisionRequest =
  components['schemas']['PartnerApplicationReviewDecisionRequest'];
type PartnerApplicationReviewRequestDetailResponse =
  components['schemas']['PartnerApplicationReviewRequestDetailResponse'];
type PartnerLaneApplicationResponse = components['schemas']['PartnerLaneApplicationResponse'];
type PartnerWorkspaceProgramsResponse = components['schemas']['PartnerWorkspaceProgramsResponse'];
type PartnerCodeResponse = components['schemas']['PartnerCodeResponse'];
type PartnerWorkspaceReviewRequestResponse =
  components['schemas']['PartnerWorkspaceReviewRequestResponse'];
type PartnerWorkspaceCaseResponse = components['schemas']['PartnerWorkspaceCaseResponse'];
type TrafficDeclarationResponse = components['schemas']['TrafficDeclarationResponse'];
type CreativeApprovalResponse = components['schemas']['CreativeApprovalResponse'];
type PartnerPayoutAccountResponse = components['schemas']['PartnerPayoutAccountResponse'];
type SuspendPartnerPayoutAccountRequest =
  components['schemas']['SuspendPartnerPayoutAccountRequest'];
type ArchivePartnerPayoutAccountRequest =
  components['schemas']['ArchivePartnerPayoutAccountRequest'];
type PayoutInstructionResponse = components['schemas']['PayoutInstructionResponse'];
type RejectPayoutInstructionRequest =
  components['schemas']['RejectPayoutInstructionRequest'];
type PayoutExecutionResponse = components['schemas']['PayoutExecutionResponse'];
type GovernanceActionResponse = components['schemas']['GovernanceActionResponse'];

export interface AdminPartnerWorkspaceListParams {
  search?: string;
  workspace_status?: string;
  limit?: number;
  offset?: number;
}

export interface AdminApproveLaneParams {
  target_status?: 'approved_probation' | 'approved_active';
}

export interface AdminTrafficDeclarationsParams {
  partner_account_id: string;
  declaration_kind?: string;
  limit?: number;
  offset?: number;
}

export interface AdminCreativeApprovalsParams {
  partner_account_id?: string;
  approval_kind?: string;
  limit?: number;
  offset?: number;
}

export interface AdminPartnerPayoutAccountsParams {
  partner_account_id: string;
  payout_account_status?: string;
  verification_status?: string;
  approval_status?: string;
  limit?: number;
  offset?: number;
}

export interface AdminPayoutInstructionsParams {
  partner_account_id?: string;
  partner_statement_id?: string;
  instruction_status?: string;
  limit?: number;
  offset?: number;
}

export interface AdminPayoutExecutionsParams {
  payout_instruction_id?: string;
  partner_account_id?: string;
  partner_statement_id?: string;
  execution_status?: string;
  limit?: number;
  offset?: number;
}

export interface AdminGovernanceActionsParams {
  risk_subject_id?: string;
  risk_review_id?: string;
}

function buildIdempotencyKey(prefix: string) {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}`;
}

export const partnerOperationsApi = {
  listWorkspaces: (params?: AdminPartnerWorkspaceListParams) =>
    apiClient.get<PartnerWorkspaceResponse[]>('/admin/partner-workspaces', { params }),

  getWorkspace: (workspaceId: string) =>
    apiClient.get<PartnerWorkspaceResponse>(`/admin/partner-workspaces/${workspaceId}`),

  listApplications: () =>
    apiClient.get<PartnerApplicationAdminSummaryResponse[]>('/admin/partner-applications'),

  getApplication: (workspaceId: string) =>
    apiClient.get<PartnerApplicationAdminDetailResponse>(`/admin/partner-applications/${workspaceId}`),

  requestApplicationInfo: (workspaceId: string, data: RequestPartnerApplicationInfoRequest) =>
    apiClient.post<PartnerApplicationReviewRequestDetailResponse>(
      `/admin/partner-applications/${workspaceId}/request-info`,
      data,
    ),

  approveApplicationProbation: (
    workspaceId: string,
    data: PartnerApplicationReviewDecisionRequest,
  ) =>
    apiClient.post<PartnerApplicationAdminDetailResponse>(
      `/admin/partner-applications/${workspaceId}/approve-probation`,
      data,
    ),

  waitlistApplication: (workspaceId: string, data: PartnerApplicationReviewDecisionRequest) =>
    apiClient.post<PartnerApplicationAdminDetailResponse>(
      `/admin/partner-applications/${workspaceId}/waitlist`,
      data,
    ),

  rejectApplication: (workspaceId: string, data: PartnerApplicationReviewDecisionRequest) =>
    apiClient.post<PartnerApplicationAdminDetailResponse>(
      `/admin/partner-applications/${workspaceId}/reject`,
      data,
    ),

  approveLaneApplication: (
    workspaceId: string,
    laneApplicationId: string,
    data: PartnerApplicationReviewDecisionRequest,
    params?: AdminApproveLaneParams,
  ) =>
    apiClient.post<PartnerLaneApplicationResponse>(
      `/admin/partner-applications/${workspaceId}/lane-applications/${laneApplicationId}/approve`,
      data,
      { params },
    ),

  declineLaneApplication: (
    workspaceId: string,
    laneApplicationId: string,
    data: PartnerApplicationReviewDecisionRequest,
  ) =>
    apiClient.post<PartnerLaneApplicationResponse>(
      `/admin/partner-applications/${workspaceId}/lane-applications/${laneApplicationId}/decline`,
      data,
    ),

  getWorkspacePrograms: (workspaceId: string) =>
    apiClient.get<PartnerWorkspaceProgramsResponse>(`/partner-workspaces/${workspaceId}/programs`),

  listWorkspaceCodes: (workspaceId: string) =>
    apiClient.get<PartnerCodeResponse[]>(`/partner-workspaces/${workspaceId}/codes`),

  listWorkspaceReviewRequests: (workspaceId: string) =>
    apiClient.get<PartnerWorkspaceReviewRequestResponse[]>(
      `/partner-workspaces/${workspaceId}/review-requests`,
    ),

  listWorkspaceCases: (workspaceId: string) =>
    apiClient.get<PartnerWorkspaceCaseResponse[]>(`/partner-workspaces/${workspaceId}/cases`),

  listTrafficDeclarations: (params: AdminTrafficDeclarationsParams) =>
    apiClient.get<TrafficDeclarationResponse[]>('/traffic-declarations', { params }),

  listCreativeApprovals: (params?: AdminCreativeApprovalsParams) =>
    apiClient.get<CreativeApprovalResponse[]>('/creative-approvals', { params }),

  listPayoutAccounts: (params: AdminPartnerPayoutAccountsParams) =>
    apiClient.get<PartnerPayoutAccountResponse[]>('/partner-payout-accounts', { params }),

  verifyPayoutAccount: (payoutAccountId: string) =>
    apiClient.post<PartnerPayoutAccountResponse>(
      `/partner-payout-accounts/${payoutAccountId}/verify`,
    ),

  suspendPayoutAccount: (
    payoutAccountId: string,
    data: SuspendPartnerPayoutAccountRequest,
  ) =>
    apiClient.post<PartnerPayoutAccountResponse>(
      `/partner-payout-accounts/${payoutAccountId}/suspend`,
      data,
    ),

  archivePayoutAccount: (
    payoutAccountId: string,
    data: ArchivePartnerPayoutAccountRequest,
  ) =>
    apiClient.post<PartnerPayoutAccountResponse>(
      `/partner-payout-accounts/${payoutAccountId}/archive`,
      data,
    ),

  listPayoutInstructions: (params?: AdminPayoutInstructionsParams) =>
    apiClient.get<PayoutInstructionResponse[]>('/payouts/instructions', { params }),

  approvePayoutInstruction: (payoutInstructionId: string) =>
    apiClient.post<PayoutInstructionResponse>(
      `/payouts/instructions/${payoutInstructionId}/approve`,
    ),

  rejectPayoutInstruction: (
    payoutInstructionId: string,
    data: RejectPayoutInstructionRequest,
  ) =>
    apiClient.post<PayoutInstructionResponse>(
      `/payouts/instructions/${payoutInstructionId}/reject`,
      data,
    ),

  listPayoutExecutions: (params?: AdminPayoutExecutionsParams) =>
    apiClient.get<PayoutExecutionResponse[]>('/payouts/executions', { params }),

  listGovernanceActions: (params?: AdminGovernanceActionsParams) =>
    apiClient.get<GovernanceActionResponse[]>('/security/governance-actions', { params }),

  createPayoutExecutionRequestKey: () => buildIdempotencyKey('payout-execution'),

  createExecutionHeaders: () => ({
    [CANONICAL_IDEMPOTENCY_HEADER]: buildIdempotencyKey('payout-execution'),
  }),
};

export type {
  ArchivePartnerPayoutAccountRequest,
  CreativeApprovalResponse,
  GovernanceActionResponse,
  PartnerApplicationAdminDetailResponse,
  PartnerApplicationAdminSummaryResponse,
  PartnerApplicationReviewDecisionRequest,
  PartnerApplicationReviewRequestDetailResponse,
  PartnerCodeResponse,
  PartnerLaneApplicationResponse,
  PartnerPayoutAccountResponse,
  PartnerWorkspaceCaseResponse,
  PartnerWorkspaceProgramsResponse,
  PartnerWorkspaceResponse,
  PartnerWorkspaceReviewRequestResponse,
  PayoutExecutionResponse,
  PayoutInstructionResponse,
  RejectPayoutInstructionRequest,
  RequestPartnerApplicationInfoRequest,
  SuspendPartnerPayoutAccountRequest,
  TrafficDeclarationResponse,
};
