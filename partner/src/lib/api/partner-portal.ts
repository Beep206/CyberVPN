import { apiClient } from './client';
import type { operations } from './generated/types';

type ListMyPartnerWorkspacesResponse =
  operations['list_my_partner_workspaces_api_v1_partner_workspaces_me_get']['responses'][200]['content']['application/json'];
type ListPartnerNotificationsResponse =
  operations['list_partner_notifications_api_v1_partner_notifications_get']['responses'][200]['content']['application/json'];
type ListPartnerNotificationsParams =
  operations['list_partner_notifications_api_v1_partner_notifications_get']['parameters']['query'];
type GetPartnerNotificationCountersResponse =
  operations['get_partner_notification_counters_api_v1_partner_notifications_counters_get']['responses'][200]['content']['application/json'];
type GetPartnerNotificationCountersParams =
  operations['get_partner_notification_counters_api_v1_partner_notifications_counters_get']['parameters']['query'];
type MarkPartnerNotificationReadResponse =
  operations['mark_partner_notification_read_api_v1_partner_notifications__notification_id__read_post']['responses'][200]['content']['application/json'];
type MarkPartnerNotificationReadParams =
  operations['mark_partner_notification_read_api_v1_partner_notifications__notification_id__read_post']['parameters']['query'];
type ArchivePartnerNotificationResponse =
  operations['archive_partner_notification_api_v1_partner_notifications__notification_id__archive_post']['responses'][200]['content']['application/json'];
type ArchivePartnerNotificationParams =
  operations['archive_partner_notification_api_v1_partner_notifications__notification_id__archive_post']['parameters']['query'];
type GetPartnerNotificationPreferencesResponse =
  operations['get_partner_notification_preferences_api_v1_partner_notifications_preferences_get']['responses'][200]['content']['application/json'];
type UpdatePartnerNotificationPreferencesPayload =
  operations['update_partner_notification_preferences_api_v1_partner_notifications_preferences_patch']['requestBody']['content']['application/json'];
type UpdatePartnerNotificationPreferencesResponse =
  operations['update_partner_notification_preferences_api_v1_partner_notifications_preferences_patch']['responses'][200]['content']['application/json'];
type GetPartnerSessionBootstrapResponse =
  operations['get_partner_session_bootstrap_api_v1_partner_session_bootstrap_get']['responses'][200]['content']['application/json'];
type GetPartnerSessionBootstrapParams =
  operations['get_partner_session_bootstrap_api_v1_partner_session_bootstrap_get']['parameters']['query'];
type GetCurrentPartnerApplicationDraftResponse =
  operations['get_current_partner_application_draft_api_v1_partner_application_drafts_current_get']['responses'][200]['content']['application/json'];
type CreatePartnerApplicationDraftPayload =
  operations['create_partner_application_draft_api_v1_partner_application_drafts_post']['requestBody']['content']['application/json'];
type CreatePartnerApplicationDraftResponse =
  operations['create_partner_application_draft_api_v1_partner_application_drafts_post']['responses'][201]['content']['application/json'];
type UpdatePartnerApplicationDraftPayload =
  operations['update_partner_application_draft_api_v1_partner_application_drafts__draft_id__patch']['requestBody']['content']['application/json'];
type UpdatePartnerApplicationDraftResponse =
  operations['update_partner_application_draft_api_v1_partner_application_drafts__draft_id__patch']['responses'][200]['content']['application/json'];
type CreatePartnerApplicationAttachmentPayload =
  operations['create_partner_application_attachment_api_v1_partner_application_drafts__draft_id__attachments_post']['requestBody']['content']['application/json'];
type CreatePartnerApplicationAttachmentResponse =
  operations['create_partner_application_attachment_api_v1_partner_application_drafts__draft_id__attachments_post']['responses'][201]['content']['application/json'];
type SubmitPartnerApplicationDraftResponse =
  operations['submit_partner_application_draft_api_v1_partner_application_drafts__draft_id__submit_post']['responses'][200]['content']['application/json'];
type WithdrawPartnerApplicationDraftResponse =
  operations['withdraw_partner_application_draft_api_v1_partner_application_drafts__draft_id__withdraw_post']['responses'][200]['content']['application/json'];
type ResubmitPartnerApplicationDraftResponse =
  operations['resubmit_partner_application_draft_api_v1_partner_application_drafts__draft_id__resubmit_post']['responses'][200]['content']['application/json'];
type GetPartnerWorkspaceResponse =
  operations['get_partner_workspace_api_v1_partner_workspaces__workspace_id__get']['responses'][200]['content']['application/json'];
type GetPartnerWorkspaceProgramsResponse =
  operations['get_partner_workspace_programs_api_v1_partner_workspaces__workspace_id__programs_get']['responses'][200]['content']['application/json'];
type GetPartnerWorkspaceOrganizationProfileResponse =
  operations['get_partner_workspace_organization_profile_api_v1_partner_workspaces__workspace_id__organization_profile_get']['responses'][200]['content']['application/json'];
type UpdatePartnerWorkspaceOrganizationProfilePayload =
  operations['update_partner_workspace_organization_profile_api_v1_partner_workspaces__workspace_id__organization_profile_patch']['requestBody']['content']['application/json'];
type UpdatePartnerWorkspaceOrganizationProfileResponse =
  operations['update_partner_workspace_organization_profile_api_v1_partner_workspaces__workspace_id__organization_profile_patch']['responses'][200]['content']['application/json'];
type ListPartnerWorkspaceMembersResponse =
  operations['list_partner_workspace_members_api_v1_partner_workspaces__workspace_id__members_get']['responses'][200]['content']['application/json'];
type CreatePartnerWorkspaceMemberPayload =
  operations['add_partner_workspace_member_api_v1_partner_workspaces__workspace_id__members_post']['requestBody']['content']['application/json'];
type CreatePartnerWorkspaceMemberResponse =
  operations['add_partner_workspace_member_api_v1_partner_workspaces__workspace_id__members_post']['responses'][201]['content']['application/json'];
type ListPartnerWorkspaceRolesResponse =
  operations['list_partner_workspace_roles_api_v1_partner_workspaces__workspace_id__roles_get']['responses'][200]['content']['application/json'];
type UpdatePartnerWorkspaceMemberPayload =
  operations['update_partner_workspace_member_api_v1_partner_workspaces__workspace_id__members__member_id__patch']['requestBody']['content']['application/json'];
type UpdatePartnerWorkspaceMemberResponse =
  operations['update_partner_workspace_member_api_v1_partner_workspaces__workspace_id__members__member_id__patch']['responses'][200]['content']['application/json'];
type ListPartnerWorkspaceLegalDocumentsResponse =
  operations['list_partner_workspace_legal_documents_api_v1_partner_workspaces__workspace_id__legal_documents_get']['responses'][200]['content']['application/json'];
type AcceptPartnerWorkspaceLegalDocumentResponse =
  operations['accept_partner_workspace_legal_document_api_v1_partner_workspaces__workspace_id__legal_documents__document_kind__accept_post']['responses'][200]['content']['application/json'];
type GetPartnerWorkspaceSettingsResponse =
  operations['get_partner_workspace_settings_api_v1_partner_workspaces__workspace_id__settings_get']['responses'][200]['content']['application/json'];
type UpdatePartnerWorkspaceSettingsPayload =
  operations['update_partner_workspace_settings_api_v1_partner_workspaces__workspace_id__settings_patch']['requestBody']['content']['application/json'];
type UpdatePartnerWorkspaceSettingsResponse =
  operations['update_partner_workspace_settings_api_v1_partner_workspaces__workspace_id__settings_patch']['responses'][200]['content']['application/json'];
type ListPartnerWorkspaceCodesResponse =
  operations['list_partner_workspace_codes_api_v1_partner_workspaces__workspace_id__codes_get']['responses'][200]['content']['application/json'];
type ListPartnerWorkspaceCampaignAssetsResponse =
  operations['list_partner_workspace_campaign_assets_api_v1_partner_workspaces__workspace_id__campaign_assets_get']['responses'][200]['content']['application/json'];
type ListPartnerWorkspaceLaneApplicationsResponse =
  operations['list_partner_workspace_lane_applications_api_v1_partner_workspaces__workspace_id__lane_applications_get']['responses'][200]['content']['application/json'];
type CreatePartnerWorkspaceLaneApplicationPayload =
  operations['create_partner_workspace_lane_application_api_v1_partner_workspaces__workspace_id__lane_applications_post']['requestBody']['content']['application/json'];
type CreatePartnerWorkspaceLaneApplicationResponse =
  operations['create_partner_workspace_lane_application_api_v1_partner_workspaces__workspace_id__lane_applications_post']['responses'][201]['content']['application/json'];
type UpdatePartnerWorkspaceLaneApplicationPayload =
  operations['update_partner_workspace_lane_application_api_v1_partner_workspaces__workspace_id__lane_applications__lane_application_id__patch']['requestBody']['content']['application/json'];
type UpdatePartnerWorkspaceLaneApplicationResponse =
  operations['update_partner_workspace_lane_application_api_v1_partner_workspaces__workspace_id__lane_applications__lane_application_id__patch']['responses'][200]['content']['application/json'];
type SubmitPartnerWorkspaceLaneApplicationResponse =
  operations['submit_partner_workspace_lane_application_api_v1_partner_workspaces__workspace_id__lane_applications__lane_application_id__submit_post']['responses'][200]['content']['application/json'];
type ListPartnerWorkspaceStatementsResponse =
  operations['list_partner_workspace_statements_api_v1_partner_workspaces__workspace_id__statements_get']['responses'][200]['content']['application/json'];
type ListPartnerWorkspaceStatementsParams =
  operations['list_partner_workspace_statements_api_v1_partner_workspaces__workspace_id__statements_get']['parameters']['query'];
type ListPartnerWorkspaceConversionRecordsResponse =
  operations['list_partner_workspace_conversion_records_api_v1_partner_workspaces__workspace_id__conversion_records_get']['responses'][200]['content']['application/json'];
type ListPartnerWorkspaceConversionRecordsParams =
  operations['list_partner_workspace_conversion_records_api_v1_partner_workspaces__workspace_id__conversion_records_get']['parameters']['query'];
type GetPartnerWorkspaceConversionExplainabilityResponse =
  operations['get_partner_workspace_conversion_explainability_api_v1_partner_workspaces__workspace_id__conversion_records__order_id__explainability_get']['responses'][200]['content']['application/json'];
type ListPartnerWorkspaceAnalyticsMetricsResponse =
  operations['list_partner_workspace_analytics_metrics_api_v1_partner_workspaces__workspace_id__analytics_metrics_get']['responses'][200]['content']['application/json'];
type ListPartnerWorkspaceReportExportsResponse =
  operations['list_partner_workspace_report_exports_api_v1_partner_workspaces__workspace_id__report_exports_get']['responses'][200]['content']['application/json'];
type SchedulePartnerWorkspaceReportExportPayload =
  operations['schedule_partner_workspace_report_export_api_v1_partner_workspaces__workspace_id__report_exports__export_id__schedule_post']['requestBody']['content']['application/json'];
type SchedulePartnerWorkspaceReportExportResponse =
  operations['schedule_partner_workspace_report_export_api_v1_partner_workspaces__workspace_id__report_exports__export_id__schedule_post']['responses'][201]['content']['application/json'];
type ListPartnerWorkspaceReviewRequestsResponse =
  operations['list_partner_workspace_review_requests_api_v1_partner_workspaces__workspace_id__review_requests_get']['responses'][200]['content']['application/json'];
type SubmitPartnerWorkspaceReviewRequestResponsePayload =
  operations['respond_partner_workspace_review_request_api_v1_partner_workspaces__workspace_id__review_requests__review_request_id__responses_post']['requestBody']['content']['application/json'];
type SubmitPartnerWorkspaceReviewRequestResponseResponse =
  operations['respond_partner_workspace_review_request_api_v1_partner_workspaces__workspace_id__review_requests__review_request_id__responses_post']['responses'][201]['content']['application/json'];
type ListPartnerWorkspaceTrafficDeclarationsResponse =
  operations['list_partner_workspace_traffic_declarations_api_v1_partner_workspaces__workspace_id__traffic_declarations_get']['responses'][200]['content']['application/json'];
type SubmitPartnerWorkspaceTrafficDeclarationPayload =
  operations['submit_partner_workspace_traffic_declaration_api_v1_partner_workspaces__workspace_id__traffic_declarations_post']['requestBody']['content']['application/json'];
type SubmitPartnerWorkspaceTrafficDeclarationResponse =
  operations['submit_partner_workspace_traffic_declaration_api_v1_partner_workspaces__workspace_id__traffic_declarations_post']['responses'][201]['content']['application/json'];
type SubmitPartnerWorkspaceCreativeApprovalPayload =
  operations['submit_partner_workspace_creative_approval_api_v1_partner_workspaces__workspace_id__creative_approvals_post']['requestBody']['content']['application/json'];
type SubmitPartnerWorkspaceCreativeApprovalResponse =
  operations['submit_partner_workspace_creative_approval_api_v1_partner_workspaces__workspace_id__creative_approvals_post']['responses'][201]['content']['application/json'];
type ListPartnerWorkspaceCasesResponse =
  operations['list_partner_workspace_cases_api_v1_partner_workspaces__workspace_id__cases_get']['responses'][200]['content']['application/json'];
type SubmitPartnerWorkspaceCaseResponsePayload =
  operations['respond_partner_workspace_case_api_v1_partner_workspaces__workspace_id__cases__case_id__responses_post']['requestBody']['content']['application/json'];
type SubmitPartnerWorkspaceCaseResponseResponse =
  operations['respond_partner_workspace_case_api_v1_partner_workspaces__workspace_id__cases__case_id__responses_post']['responses'][201]['content']['application/json'];
type MarkPartnerWorkspaceCaseReadyForOpsPayload =
  operations['mark_partner_workspace_case_ready_for_ops_api_v1_partner_workspaces__workspace_id__cases__case_id__ready_for_ops_post']['requestBody']['content']['application/json'];
type MarkPartnerWorkspaceCaseReadyForOpsResponse =
  operations['mark_partner_workspace_case_ready_for_ops_api_v1_partner_workspaces__workspace_id__cases__case_id__ready_for_ops_post']['responses'][201]['content']['application/json'];
type ListPartnerWorkspaceIntegrationCredentialsResponse =
  operations['list_partner_workspace_integration_credentials_api_v1_partner_workspaces__workspace_id__integration_credentials_get']['responses'][200]['content']['application/json'];
type ListPartnerWorkspaceIntegrationDeliveryLogsResponse =
  operations['list_partner_workspace_integration_delivery_logs_api_v1_partner_workspaces__workspace_id__integration_delivery_logs_get']['responses'][200]['content']['application/json'];
type GetPartnerWorkspacePostbackReadinessResponse =
  operations['get_partner_workspace_postback_readiness_api_v1_partner_workspaces__workspace_id__postback_readiness_get']['responses'][200]['content']['application/json'];

export interface PartnerWorkspacePayoutAccountResponse {
  id: string;
  settlement_profile_id?: string | null;
  payout_rail: string;
  display_label: string;
  masked_destination: string;
  destination_metadata?: Record<string, unknown>;
  verification_status: string;
  approval_status: string;
  account_status: string;
  is_default: boolean;
  verified_at?: string | null;
  approved_at?: string | null;
  suspended_at?: string | null;
  suspension_reason_code?: string | null;
  archived_at?: string | null;
  archive_reason_code?: string | null;
  created_at: string;
  updated_at: string;
}

export type ListPartnerWorkspacePayoutAccountsResponse =
  PartnerWorkspacePayoutAccountResponse[];

export interface ListPartnerWorkspacePayoutAccountsParams {
  limit?: number;
  offset?: number;
}

export interface CreatePartnerWorkspacePayoutAccountPayload {
  payout_rail: string;
  display_label: string;
  destination_reference: string;
  destination_metadata?: Record<string, unknown>;
  settlement_profile_id?: string | null;
  make_default?: boolean;
}

export interface PartnerWorkspacePayoutAccountEligibilityResponse {
  partner_payout_account_id: string;
  partner_account_id: string;
  eligible: boolean;
  reason_codes: string[];
  blocking_risk_review_ids: string[];
  active_reserve_ids: string[];
  checked_at: string;
}

export interface PartnerWorkspacePayoutHistoryResponse {
  id: string;
  instruction_id: string;
  execution_id?: string | null;
  partner_statement_id: string;
  partner_payout_account_id?: string | null;
  statement_key: string;
  payout_account_label?: string | null;
  amount: number;
  currency_code: string;
  lifecycle_status: string;
  instruction_status: string;
  execution_status?: string | null;
  execution_mode?: string | null;
  external_reference?: string | null;
  created_at: string;
  updated_at: string;
  notes: string[];
}

export type ListPartnerWorkspacePayoutHistoryResponse =
  PartnerWorkspacePayoutHistoryResponse[];

export const partnerPortalApi = {
  listMyWorkspaces: () =>
    apiClient.get<ListMyPartnerWorkspacesResponse>('/partner-workspaces/me'),

  listNotifications: (params?: ListPartnerNotificationsParams) =>
    apiClient.get<ListPartnerNotificationsResponse>('/partner-notifications', {
      params,
    }),

  getNotificationCounters: (params?: GetPartnerNotificationCountersParams) =>
    apiClient.get<GetPartnerNotificationCountersResponse>('/partner-notifications/counters', {
      params,
    }),

  markNotificationRead: (
    notificationId: string,
    params?: MarkPartnerNotificationReadParams,
  ) =>
    apiClient.post<MarkPartnerNotificationReadResponse>(
      `/partner-notifications/${notificationId}/read`,
      {},
      { params },
    ),

  archiveNotification: (
    notificationId: string,
    params?: ArchivePartnerNotificationParams,
  ) =>
    apiClient.post<ArchivePartnerNotificationResponse>(
      `/partner-notifications/${notificationId}/archive`,
      {},
      { params },
    ),

  getNotificationPreferences: () =>
    apiClient.get<GetPartnerNotificationPreferencesResponse>(
      '/partner-notifications/preferences',
    ),

  updateNotificationPreferences: (
    payload: UpdatePartnerNotificationPreferencesPayload,
  ) =>
    apiClient.patch<UpdatePartnerNotificationPreferencesResponse>(
      '/partner-notifications/preferences',
      payload,
    ),

  getSessionBootstrap: (params?: GetPartnerSessionBootstrapParams) =>
    apiClient.get<GetPartnerSessionBootstrapResponse>('/partner-session/bootstrap', {
      params,
    }),

  getCurrentApplicationDraft: () =>
    apiClient.get<GetCurrentPartnerApplicationDraftResponse>(
      '/partner-application-drafts/current',
    ),

  createApplicationDraft: (payload: CreatePartnerApplicationDraftPayload) =>
    apiClient.post<CreatePartnerApplicationDraftResponse>(
      '/partner-application-drafts',
      payload,
    ),

  updateApplicationDraft: (
    draftId: string,
    payload: UpdatePartnerApplicationDraftPayload,
  ) =>
    apiClient.patch<UpdatePartnerApplicationDraftResponse>(
      `/partner-application-drafts/${draftId}`,
      payload,
    ),

  createApplicationAttachment: (
    draftId: string,
    payload: CreatePartnerApplicationAttachmentPayload,
  ) =>
    apiClient.post<CreatePartnerApplicationAttachmentResponse>(
      `/partner-application-drafts/${draftId}/attachments`,
      payload,
    ),

  submitApplicationDraft: (draftId: string) =>
    apiClient.post<SubmitPartnerApplicationDraftResponse>(
      `/partner-application-drafts/${draftId}/submit`,
      {},
    ),

  withdrawApplicationDraft: (draftId: string) =>
    apiClient.post<WithdrawPartnerApplicationDraftResponse>(
      `/partner-application-drafts/${draftId}/withdraw`,
      {},
    ),

  resubmitApplicationDraft: (draftId: string) =>
    apiClient.post<ResubmitPartnerApplicationDraftResponse>(
      `/partner-application-drafts/${draftId}/resubmit`,
      {},
    ),

  getWorkspace: (workspaceId: string) =>
    apiClient.get<GetPartnerWorkspaceResponse>(`/partner-workspaces/${workspaceId}`),

  getWorkspaceOrganizationProfile: (workspaceId: string) =>
    apiClient.get<GetPartnerWorkspaceOrganizationProfileResponse>(
      `/partner-workspaces/${workspaceId}/organization-profile`,
    ),

  updateWorkspaceOrganizationProfile: (
    workspaceId: string,
    payload: UpdatePartnerWorkspaceOrganizationProfilePayload,
  ) =>
    apiClient.patch<UpdatePartnerWorkspaceOrganizationProfileResponse>(
      `/partner-workspaces/${workspaceId}/organization-profile`,
      payload,
    ),

  listWorkspaceMembers: (workspaceId: string) =>
    apiClient.get<ListPartnerWorkspaceMembersResponse>(
      `/partner-workspaces/${workspaceId}/members`,
    ),

  createWorkspaceMember: (
    workspaceId: string,
    payload: CreatePartnerWorkspaceMemberPayload,
  ) =>
    apiClient.post<CreatePartnerWorkspaceMemberResponse>(
      `/partner-workspaces/${workspaceId}/members`,
      payload,
    ),

  listWorkspaceRoles: (workspaceId: string) =>
    apiClient.get<ListPartnerWorkspaceRolesResponse>(
      `/partner-workspaces/${workspaceId}/roles`,
    ),

  updateWorkspaceMember: (
    workspaceId: string,
    memberId: string,
    payload: UpdatePartnerWorkspaceMemberPayload,
  ) =>
    apiClient.patch<UpdatePartnerWorkspaceMemberResponse>(
      `/partner-workspaces/${workspaceId}/members/${memberId}`,
      payload,
    ),

  listWorkspaceLegalDocuments: (workspaceId: string) =>
    apiClient.get<ListPartnerWorkspaceLegalDocumentsResponse>(
      `/partner-workspaces/${workspaceId}/legal-documents`,
    ),

  acceptWorkspaceLegalDocument: (workspaceId: string, documentKind: string) =>
    apiClient.post<AcceptPartnerWorkspaceLegalDocumentResponse>(
      `/partner-workspaces/${workspaceId}/legal-documents/${documentKind}/accept`,
      {},
    ),

  getWorkspaceSettings: (workspaceId: string) =>
    apiClient.get<GetPartnerWorkspaceSettingsResponse>(
      `/partner-workspaces/${workspaceId}/settings`,
    ),

  updateWorkspaceSettings: (
    workspaceId: string,
    payload: UpdatePartnerWorkspaceSettingsPayload,
  ) =>
    apiClient.patch<UpdatePartnerWorkspaceSettingsResponse>(
      `/partner-workspaces/${workspaceId}/settings`,
      payload,
    ),

  getWorkspacePrograms: (workspaceId: string) =>
    apiClient.get<GetPartnerWorkspaceProgramsResponse>(
      `/partner-workspaces/${workspaceId}/programs`,
    ),

  listWorkspaceCodes: (workspaceId: string) =>
    apiClient.get<ListPartnerWorkspaceCodesResponse>(
      `/partner-workspaces/${workspaceId}/codes`,
    ),

  listWorkspaceCampaignAssets: (workspaceId: string) =>
    apiClient.get<ListPartnerWorkspaceCampaignAssetsResponse>(
      `/partner-workspaces/${workspaceId}/campaign-assets`,
    ),

  listWorkspaceLaneApplications: (workspaceId: string) =>
    apiClient.get<ListPartnerWorkspaceLaneApplicationsResponse>(
      `/partner-workspaces/${workspaceId}/lane-applications`,
    ),

  createWorkspaceLaneApplication: (
    workspaceId: string,
    payload: CreatePartnerWorkspaceLaneApplicationPayload,
  ) =>
    apiClient.post<CreatePartnerWorkspaceLaneApplicationResponse>(
      `/partner-workspaces/${workspaceId}/lane-applications`,
      payload,
    ),

  updateWorkspaceLaneApplication: (
    workspaceId: string,
    laneApplicationId: string,
    payload: UpdatePartnerWorkspaceLaneApplicationPayload,
  ) =>
    apiClient.patch<UpdatePartnerWorkspaceLaneApplicationResponse>(
      `/partner-workspaces/${workspaceId}/lane-applications/${laneApplicationId}`,
      payload,
    ),

  submitWorkspaceLaneApplication: (
    workspaceId: string,
    laneApplicationId: string,
  ) =>
    apiClient.post<SubmitPartnerWorkspaceLaneApplicationResponse>(
      `/partner-workspaces/${workspaceId}/lane-applications/${laneApplicationId}/submit`,
      {},
    ),

  listWorkspaceStatements: (
    workspaceId: string,
    params?: ListPartnerWorkspaceStatementsParams,
  ) =>
    apiClient.get<ListPartnerWorkspaceStatementsResponse>(
      `/partner-workspaces/${workspaceId}/statements`,
      { params },
    ),

  listWorkspaceConversionRecords: (
    workspaceId: string,
    params?: ListPartnerWorkspaceConversionRecordsParams,
  ) =>
    apiClient.get<ListPartnerWorkspaceConversionRecordsResponse>(
      `/partner-workspaces/${workspaceId}/conversion-records`,
      { params },
    ),

  getWorkspaceConversionExplainability: (workspaceId: string, orderId: string) =>
    apiClient.get<GetPartnerWorkspaceConversionExplainabilityResponse>(
      `/partner-workspaces/${workspaceId}/conversion-records/${orderId}/explainability`,
    ),

  listWorkspaceAnalyticsMetrics: (workspaceId: string) =>
    apiClient.get<ListPartnerWorkspaceAnalyticsMetricsResponse>(
      `/partner-workspaces/${workspaceId}/analytics-metrics`,
    ),

  listWorkspaceReportExports: (workspaceId: string) =>
    apiClient.get<ListPartnerWorkspaceReportExportsResponse>(
      `/partner-workspaces/${workspaceId}/report-exports`,
    ),

  scheduleWorkspaceReportExport: (
    workspaceId: string,
    exportId: string,
    payload: SchedulePartnerWorkspaceReportExportPayload,
  ) =>
    apiClient.post<SchedulePartnerWorkspaceReportExportResponse>(
      `/partner-workspaces/${workspaceId}/report-exports/${exportId}/schedule`,
      payload,
    ),

  listWorkspaceReviewRequests: (workspaceId: string) =>
    apiClient.get<ListPartnerWorkspaceReviewRequestsResponse>(
      `/partner-workspaces/${workspaceId}/review-requests`,
    ),

  respondToWorkspaceReviewRequest: (
    workspaceId: string,
    reviewRequestId: string,
    payload: SubmitPartnerWorkspaceReviewRequestResponsePayload,
  ) =>
    apiClient.post<SubmitPartnerWorkspaceReviewRequestResponseResponse>(
      `/partner-workspaces/${workspaceId}/review-requests/${reviewRequestId}/responses`,
      payload,
    ),

  listWorkspaceTrafficDeclarations: (workspaceId: string) =>
    apiClient.get<ListPartnerWorkspaceTrafficDeclarationsResponse>(
      `/partner-workspaces/${workspaceId}/traffic-declarations`,
    ),

  submitWorkspaceTrafficDeclaration: (
    workspaceId: string,
    payload: SubmitPartnerWorkspaceTrafficDeclarationPayload,
  ) =>
    apiClient.post<SubmitPartnerWorkspaceTrafficDeclarationResponse>(
      `/partner-workspaces/${workspaceId}/traffic-declarations`,
      payload,
    ),

  submitWorkspaceCreativeApproval: (
    workspaceId: string,
    payload: SubmitPartnerWorkspaceCreativeApprovalPayload,
  ) =>
    apiClient.post<SubmitPartnerWorkspaceCreativeApprovalResponse>(
      `/partner-workspaces/${workspaceId}/creative-approvals`,
      payload,
    ),

  listWorkspaceCases: (workspaceId: string) =>
    apiClient.get<ListPartnerWorkspaceCasesResponse>(
      `/partner-workspaces/${workspaceId}/cases`,
    ),

  respondToWorkspaceCase: (
    workspaceId: string,
    caseId: string,
    payload: SubmitPartnerWorkspaceCaseResponsePayload,
  ) =>
    apiClient.post<SubmitPartnerWorkspaceCaseResponseResponse>(
      `/partner-workspaces/${workspaceId}/cases/${caseId}/responses`,
      payload,
    ),

  markWorkspaceCaseReadyForOps: (
    workspaceId: string,
    caseId: string,
    payload: MarkPartnerWorkspaceCaseReadyForOpsPayload,
  ) =>
    apiClient.post<MarkPartnerWorkspaceCaseReadyForOpsResponse>(
      `/partner-workspaces/${workspaceId}/cases/${caseId}/ready-for-ops`,
      payload,
    ),

  listWorkspaceIntegrationCredentials: (workspaceId: string) =>
    apiClient.get<ListPartnerWorkspaceIntegrationCredentialsResponse>(
      `/partner-workspaces/${workspaceId}/integration-credentials`,
    ),

  listWorkspaceIntegrationDeliveryLogs: (workspaceId: string) =>
    apiClient.get<ListPartnerWorkspaceIntegrationDeliveryLogsResponse>(
      `/partner-workspaces/${workspaceId}/integration-delivery-logs`,
    ),

  getWorkspacePostbackReadiness: (workspaceId: string) =>
    apiClient.get<GetPartnerWorkspacePostbackReadinessResponse>(
      `/partner-workspaces/${workspaceId}/postback-readiness`,
    ),

  listWorkspacePayoutAccounts: (
    workspaceId: string,
    params?: ListPartnerWorkspacePayoutAccountsParams,
  ) =>
    apiClient.get<ListPartnerWorkspacePayoutAccountsResponse>(
      `/partner-workspaces/${workspaceId}/payout-accounts`,
      { params },
    ),

  createWorkspacePayoutAccount: (
    workspaceId: string,
    payload: CreatePartnerWorkspacePayoutAccountPayload,
  ) =>
    apiClient.post<PartnerWorkspacePayoutAccountResponse>(
      `/partner-workspaces/${workspaceId}/payout-accounts`,
      payload,
    ),

  getWorkspacePayoutAccountEligibility: (
    workspaceId: string,
    payoutAccountId: string,
  ) =>
    apiClient.get<PartnerWorkspacePayoutAccountEligibilityResponse>(
      `/partner-workspaces/${workspaceId}/payout-accounts/${payoutAccountId}/eligibility`,
    ),

  makeWorkspacePayoutAccountDefault: (
    workspaceId: string,
    payoutAccountId: string,
  ) =>
    apiClient.post<PartnerWorkspacePayoutAccountResponse>(
      `/partner-workspaces/${workspaceId}/payout-accounts/${payoutAccountId}/make-default`,
      {},
    ),

  listWorkspacePayoutHistory: (
    workspaceId: string,
    params?: { limit?: number; offset?: number },
  ) =>
    apiClient.get<ListPartnerWorkspacePayoutHistoryResponse>(
      `/partner-workspaces/${workspaceId}/payout-history`,
      { params },
    ),
};

export type {
  ArchivePartnerNotificationResponse,
  CreatePartnerApplicationAttachmentPayload,
  CreatePartnerApplicationAttachmentResponse,
  CreatePartnerApplicationDraftPayload,
  CreatePartnerApplicationDraftResponse,
  CreatePartnerWorkspaceLaneApplicationPayload,
  CreatePartnerWorkspaceLaneApplicationResponse,
  GetCurrentPartnerApplicationDraftResponse,
  GetPartnerNotificationCountersResponse,
  GetPartnerNotificationPreferencesResponse,
  GetPartnerSessionBootstrapParams,
  GetPartnerSessionBootstrapResponse,
  GetPartnerWorkspaceResponse,
  GetPartnerWorkspaceOrganizationProfileResponse,
  GetPartnerWorkspaceProgramsResponse,
  GetPartnerWorkspaceSettingsResponse,
  ListPartnerNotificationsParams,
  ListPartnerNotificationsResponse,
  ListMyPartnerWorkspacesResponse,
  ListPartnerWorkspaceLegalDocumentsResponse,
  ListPartnerWorkspaceLaneApplicationsResponse,
  ListPartnerWorkspaceMembersResponse,
  ListPartnerWorkspaceRolesResponse,
  ListPartnerWorkspaceAnalyticsMetricsResponse,
  ListPartnerWorkspaceCasesResponse,
  ListPartnerWorkspaceCampaignAssetsResponse,
  ListPartnerWorkspaceCodesResponse,
  GetPartnerWorkspaceConversionExplainabilityResponse,
  ListPartnerWorkspaceConversionRecordsParams,
  ListPartnerWorkspaceConversionRecordsResponse,
  ListPartnerWorkspaceIntegrationCredentialsResponse,
  ListPartnerWorkspaceIntegrationDeliveryLogsResponse,
  ListPartnerWorkspaceReportExportsResponse,
  SchedulePartnerWorkspaceReportExportPayload,
  SchedulePartnerWorkspaceReportExportResponse,
  ListPartnerWorkspaceReviewRequestsResponse,
  ListPartnerWorkspaceTrafficDeclarationsResponse,
  ListPartnerWorkspaceStatementsParams,
  ListPartnerWorkspaceStatementsResponse,
  MarkPartnerNotificationReadResponse,
  MarkPartnerWorkspaceCaseReadyForOpsPayload,
  MarkPartnerWorkspaceCaseReadyForOpsResponse,
  GetPartnerWorkspacePostbackReadinessResponse,
  ResubmitPartnerApplicationDraftResponse,
  SubmitPartnerWorkspaceCaseResponsePayload,
  SubmitPartnerWorkspaceCaseResponseResponse,
  SubmitPartnerWorkspaceCreativeApprovalPayload,
  SubmitPartnerWorkspaceCreativeApprovalResponse,
  SubmitPartnerApplicationDraftResponse,
  SubmitPartnerWorkspaceLaneApplicationResponse,
  SubmitPartnerWorkspaceReviewRequestResponsePayload,
  SubmitPartnerWorkspaceReviewRequestResponseResponse,
  SubmitPartnerWorkspaceTrafficDeclarationPayload,
  SubmitPartnerWorkspaceTrafficDeclarationResponse,
  CreatePartnerWorkspaceMemberPayload,
  CreatePartnerWorkspaceMemberResponse,
  UpdatePartnerWorkspaceMemberPayload,
  UpdatePartnerWorkspaceMemberResponse,
  UpdatePartnerWorkspaceOrganizationProfilePayload,
  UpdatePartnerWorkspaceOrganizationProfileResponse,
  UpdatePartnerWorkspaceSettingsPayload,
  UpdatePartnerWorkspaceSettingsResponse,
  AcceptPartnerWorkspaceLegalDocumentResponse,
  UpdatePartnerApplicationDraftPayload,
  UpdatePartnerApplicationDraftResponse,
  UpdatePartnerNotificationPreferencesPayload,
  UpdatePartnerNotificationPreferencesResponse,
  UpdatePartnerWorkspaceLaneApplicationPayload,
  UpdatePartnerWorkspaceLaneApplicationResponse,
  WithdrawPartnerApplicationDraftResponse,
};
