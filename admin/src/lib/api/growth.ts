import { apiClient, apiV3Client } from './client';
import type { operations } from './generated/types';

type AdminListPromosResponse =
  operations['admin_list_promos_api_v1_admin_promo_codes_get']['responses'][200]['content']['application/json'];
type AdminCreatePromoRequest =
  operations['admin_create_promo_api_v1_admin_promo_codes_post']['requestBody']['content']['application/json'];
type AdminCreatePromoResponse =
  operations['admin_create_promo_api_v1_admin_promo_codes_post']['responses'][201]['content']['application/json'];
type AdminGetPromoResponse =
  operations['admin_get_promo_api_v1_admin_promo_codes__promo_id__get']['responses'][200]['content']['application/json'];
type AdminUpdatePromoRequest =
  operations['admin_update_promo_api_v1_admin_promo_codes__promo_id__put']['requestBody']['content']['application/json'];
type AdminUpdatePromoResponse =
  operations['admin_update_promo_api_v1_admin_promo_codes__promo_id__put']['responses'][200]['content']['application/json'];
type AdminDeactivatePromoResponse =
  operations['admin_deactivate_promo_api_v1_admin_promo_codes__promo_id__delete']['responses'][200]['content']['application/json'];
type AdminCreateInviteCodesRequest =
  operations['admin_create_invites_api_v1_admin_invite_codes_post']['requestBody']['content']['application/json'];
type AdminCreateInviteCodesPayload =
  Omit<AdminCreateInviteCodesRequest, 'legacy_acknowledgement'> & {
    legacy_acknowledgement?: boolean;
  };
type AdminCreateInviteCodesResponse =
  operations['admin_create_invites_api_v1_admin_invite_codes_post']['responses'][201]['content']['application/json'];
type AdminListInviteBatchesParams =
  operations['admin_list_invite_batches_api_v1_admin_invite_batches_get']['parameters']['query'];
type AdminPromotePartnerRequest =
  operations['admin_promote_partner_api_v1_admin_partners_promote_post']['requestBody']['content']['application/json'];
type AdminPromotePartnerResponse =
  operations['admin_promote_partner_api_v1_admin_partners_promote_post']['responses'][200]['content']['application/json'];
type AdminReferralOverviewResponse =
  operations['get_referral_overview_api_v1_admin_referrals_overview_get']['responses'][200]['content']['application/json'];
type AdminReferralUserDetailResponse =
  operations['get_referral_user_detail_api_v1_admin_referrals_users__user_id__get']['responses'][200]['content']['application/json'];
type AdminPartnersListResponse =
  operations['list_partners_api_v1_admin_partners_get']['responses'][200]['content']['application/json'];
type AdminPartnersListParams =
  operations['list_partners_api_v1_admin_partners_get']['parameters']['query'];
type AdminPartnerDetailResponse =
  operations['get_partner_detail_api_v1_admin_partners__user_id__get']['responses'][200]['content']['application/json'];
type AdminGrowthSignalsOverviewResponse =
  operations['get_growth_signals_overview_api_v1_admin_growth_signals_overview_get']['responses'][200]['content']['application/json'];
type AdminGrowthAbuseSignalsResponse =
  operations['list_growth_abuse_signals_api_v1_admin_growth_signals_abuse_queue_get']['responses'][200]['content']['application/json'];
type AdminGrowthRuleCatalogResponse =
  operations['get_v3_growth_rule_catalog_api_v3_admin_growth_rule_catalog_get']['responses'][200]['content']['application/json'];
type AdminGrowthRuleCompileRequest =
  operations['compile_v3_growth_policy_api_v3_admin_growth_policies_compile_post']['requestBody']['content']['application/json'];
type AdminGrowthRuleCompileResponse =
  operations['compile_v3_growth_policy_api_v3_admin_growth_policies_compile_post']['responses'][200]['content']['application/json'];
type AdminGrowthRuleSimulateRequest =
  operations['preview_v3_growth_policy_impact_api_v3_admin_growth_policies_impact_preview_post']['requestBody']['content']['application/json'];
type AdminGrowthRuleSimulateResponse =
  operations['preview_v3_growth_policy_impact_api_v3_admin_growth_policies_impact_preview_post']['responses'][200]['content']['application/json'];
type AdminGrowthRulePolicyListParams =
  operations['list_growth_rule_policies_api_v1_admin_growth_policy_versions_get']['parameters']['query'];
type AdminGrowthRulePolicyListResponse =
  operations['list_growth_rule_policies_api_v1_admin_growth_policy_versions_get']['responses'][200]['content']['application/json'];
type AdminGrowthRulePolicyCreateRequest =
  operations['create_growth_rule_policy_api_v1_admin_growth_policy_versions_post']['requestBody']['content']['application/json'];
type AdminGrowthRulePolicyVersionResponse =
  operations['create_growth_rule_policy_api_v1_admin_growth_policy_versions_post']['responses'][201]['content']['application/json'];
type AdminGrowthRulePolicyActionRequest =
  operations['submit_growth_rule_policy_api_v1_admin_growth_policy_versions__policy_version_id__submit_post']['requestBody']['content']['application/json'];
type AdminGrowthRulePolicyRollbackRequest =
  operations['rollback_growth_rule_policy_api_v1_admin_growth_policy_versions__policy_version_id__rollback_post']['requestBody']['content']['application/json'];
type AdminGrowthRulePolicyDiffResponse =
  operations['diff_growth_rule_policy_api_v1_admin_growth_policy_versions__policy_version_id__diff_get']['responses'][200]['content']['application/json'];
type AdminGrowthCampaignListParams =
  operations['list_admin_growth_campaigns_api_v1_admin_growth_campaigns_get']['parameters']['query'];
type AdminGrowthCampaignListResponse =
  operations['list_admin_growth_campaigns_api_v1_admin_growth_campaigns_get']['responses'][200]['content']['application/json'];
type AdminGrowthCampaignCreateRequest =
  operations['create_admin_growth_campaign_api_v1_admin_growth_campaigns_post']['requestBody']['content']['application/json'];
type AdminGrowthCampaignResponse =
  operations['create_admin_growth_campaign_api_v1_admin_growth_campaigns_post']['responses'][201]['content']['application/json'];
type AdminGrowthCampaignPatchRequest =
  operations['update_admin_growth_campaign_api_v1_admin_growth_campaigns__campaign_id__patch']['requestBody']['content']['application/json'];
type AdminGrowthCampaignActionRequest =
  operations['publish_admin_growth_campaign_api_v1_admin_growth_campaigns__campaign_id__publish_post']['requestBody']['content']['application/json'];
type ClientCapabilityResponse =
  operations['get_client_capabilities_api_v1_client_capabilities_get']['responses'][200]['content']['application/json'];
type AdminCustomerSiteRuntimeConfigResponse =
  operations['get_admin_customer_site_runtime_config_api_v1_admin_system_config_customer_site_runtime_get']['responses'][200]['content']['application/json'];
type AdminCustomerSiteRuntime = AdminCustomerSiteRuntimeConfigResponse['site'];
type UpdateAdminCustomerSiteRuntimeConfigRequest =
  operations['update_admin_customer_site_runtime_config_api_v1_admin_system_config_customer_site_runtime_put']['requestBody']['content']['application/json'];
type ExecuteAdminCustomerSiteRuntimeActionRequest =
  operations['execute_admin_customer_site_runtime_action_api_v1_admin_system_config_customer_site_runtime_actions_post']['requestBody']['content']['application/json'];
type AdminCustomerSiteRuntimeTimelineParams =
  operations['get_admin_customer_site_runtime_timeline_api_v1_admin_system_config_customer_site_runtime_timeline_get']['parameters']['query'];
type AdminCustomerSiteRuntimeTimelineResponse =
  operations['get_admin_customer_site_runtime_timeline_api_v1_admin_system_config_customer_site_runtime_timeline_get']['responses'][200]['content']['application/json'];
type AdminGrowthCodeSetInspectParams =
  operations['inspect_growth_code_sets_api_v3_admin_growth_code_sets_inspect_get']['parameters']['query'];
type AdminGrowthCodeSetInspectResponse =
  operations['inspect_growth_code_sets_api_v3_admin_growth_code_sets_inspect_get']['responses'][200]['content']['application/json'];
type AdminGrowthFxStatusResponse =
  operations['get_growth_fx_status_api_v3_admin_growth_fx_status_get']['responses'][200]['content']['application/json'];
type AdminGrowthFxRateListParams =
  operations['list_growth_fx_rates_api_v3_admin_growth_fx_rates_get']['parameters']['query'];
type AdminGrowthFxRateListResponse =
  operations['list_growth_fx_rates_api_v3_admin_growth_fx_rates_get']['responses'][200]['content']['application/json'];
type AdminGrowthFxConfiguredRateRequest =
  operations['create_configured_growth_fx_rate_api_v3_admin_growth_fx_configured_rates_post']['requestBody']['content']['application/json'];
type AdminGrowthFxRateResponse =
  operations['create_configured_growth_fx_rate_api_v3_admin_growth_fx_configured_rates_post']['responses'][201]['content']['application/json'];
type AdminGrowthFxXtrTableRequest =
  operations['create_growth_fx_xtr_table_api_v3_admin_growth_fx_xtr_tables_post']['requestBody']['content']['application/json'];
type AdminGrowthFxRefreshRequest =
  operations['refresh_growth_fx_rates_api_v3_admin_growth_fx_rates_refresh_post']['requestBody']['content']['application/json'];
type AdminGrowthFxRefreshResponse =
  operations['refresh_growth_fx_rates_api_v3_admin_growth_fx_rates_refresh_post']['responses'][202]['content']['application/json'];
type AdminGrowthFxSimulateRequest =
  operations['simulate_growth_fx_conversion_api_v3_admin_growth_fx_simulate_post']['requestBody']['content']['application/json'];
type AdminGrowthFxSimulationResponse =
  operations['simulate_growth_fx_conversion_api_v3_admin_growth_fx_simulate_post']['responses'][200]['content']['application/json'];
type AdminGrowthFxProviderActionRequest =
  operations['disable_growth_fx_provider_api_v3_admin_growth_fx_providers__provider_key__disable_post']['requestBody']['content']['application/json'];
type AdminGrowthPrivateTargetListParams =
  operations['list_private_catalog_targets_api_v3_admin_growth_private_catalog_targets_get']['parameters']['query'];
type AdminGrowthPrivateTargetListResponse =
  operations['list_private_catalog_targets_api_v3_admin_growth_private_catalog_targets_get']['responses'][200]['content']['application/json'];
type AdminGrowthPrivateGrantListParams =
  operations['list_private_catalog_grants_api_v3_admin_growth_private_grants_get']['parameters']['query'];
type AdminGrowthPrivateGrantListResponse =
  operations['list_private_catalog_grants_api_v3_admin_growth_private_grants_get']['responses'][200]['content']['application/json'];
type AdminGrowthPrivateGrantResponse =
  operations['get_private_catalog_grant_api_v3_admin_growth_private_grants__grant_id__get']['responses'][200]['content']['application/json'];
type AdminGrowthPrivateGrantRevokeRequest =
  operations['revoke_private_catalog_grant_api_v3_admin_growth_private_grants__grant_id__revoke_post']['requestBody']['content']['application/json'];
type AdminGrowthOnboardingRuntimeResponse =
  operations['get_growth_onboarding_settings_api_v3_admin_growth_onboarding_settings_get']['responses'][200]['content']['application/json'];
type AdminGrowthOnboardingRuntimeUpdateRequest =
  operations['update_growth_onboarding_settings_api_v3_admin_growth_onboarding_settings_put']['requestBody']['content']['application/json'];
type AdminGrowthOnboardingStateListParams =
  operations['list_growth_onboarding_states_api_v3_admin_growth_onboarding_states_get']['parameters']['query'];
type AdminGrowthOnboardingStateListResponse =
  operations['list_growth_onboarding_states_api_v3_admin_growth_onboarding_states_get']['responses'][200]['content']['application/json'];
type AdminGrowthOnboardingStateResponse =
  operations['get_growth_onboarding_state_api_v3_admin_growth_onboarding_states__state_id__get']['responses'][200]['content']['application/json'];
type AdminGrowthOnboardingApplicationListParams =
  operations['list_growth_onboarding_applications_api_v3_admin_growth_onboarding_applications_get']['parameters']['query'];
type AdminGrowthOnboardingApplicationListResponse =
  operations['list_growth_onboarding_applications_api_v3_admin_growth_onboarding_applications_get']['responses'][200]['content']['application/json'];
type AdminGrowthOnboardingStateResetRequest =
  operations['reset_growth_onboarding_state_api_v3_admin_growth_onboarding_states__state_id__reset_post']['requestBody']['content']['application/json'];
type AdminGrowthRiskModelListParams =
  operations['list_growth_risk_models_api_v3_admin_growth_risk_models_get']['parameters']['query'];
type AdminGrowthRiskModelListResponse =
  operations['list_growth_risk_models_api_v3_admin_growth_risk_models_get']['responses'][200]['content']['application/json'];
type AdminGrowthRiskDecisionListParams =
  operations['list_growth_risk_decisions_api_v3_admin_growth_risk_decisions_get']['parameters']['query'];
type AdminGrowthRiskDecisionListResponse =
  operations['list_growth_risk_decisions_api_v3_admin_growth_risk_decisions_get']['responses'][200]['content']['application/json'];
type AdminGrowthRiskReviewListParams =
  operations['list_growth_risk_reviews_api_v3_admin_growth_risk_reviews_get']['parameters']['query'];
type AdminGrowthRiskReviewListResponse =
  operations['list_growth_risk_reviews_api_v3_admin_growth_risk_reviews_get']['responses'][200]['content']['application/json'];
type AdminGrowthRiskReviewResolveRequest =
  operations['resolve_growth_risk_review_api_v3_admin_growth_risk_reviews__risk_review_id__resolve_post']['requestBody']['content']['application/json'];
type AdminGrowthRiskReviewResponse =
  operations['resolve_growth_risk_review_api_v3_admin_growth_risk_reviews__risk_review_id__resolve_post']['responses'][200]['content']['application/json'];

export interface AdminGrowthCodeLookupRequest {
  code: string;
  action_context?: 'checkout' | 'redeem' | 'signup' | 'admin_lookup';
  lookup_user_id?: string | null;
  storefront_key?: string | null;
  plan_id?: string | null;
  amount?: number | null;
  channel?: string;
  existing_partner_code_present?: boolean;
  existing_promo_present?: boolean;
}

export interface AdminGrowthCodeLookupResponse {
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
  growth_code_id?: string | null;
  promo_code_id?: string | null;
  partner_code_id?: string | null;
  user_message_key: string;
}

export interface AdminInviteCodeSummaryResponse {
  id: string;
  code_prefix?: string | null;
  code_hash?: string | null;
  owner_user_id?: string | null;
  batch_id?: string | null;
  status: string;
  is_used: boolean;
  used_by_user_id?: string | null;
  used_at?: string | null;
  revoked_at?: string | null;
  expires_at?: string | null;
  created_at: string;
  campaign_id?: string | null;
  campaign_key?: string | null;
  campaign_version_id?: string | null;
  root_invite_code_id?: string | null;
  parent_invite_code_id?: string | null;
  source_redemption_id?: string | null;
  generation_depth?: number;
  grant_mode?: string | null;
  grant_plan_id?: string | null;
  grant_plan_code?: string | null;
  grant_duration_mode?: string | null;
  grant_duration_days?: number | null;
  grant_device_limit_override?: number | null;
  root_invite_expiry_mode?: string | null;
  child_grant_plan_id?: string | null;
  child_grant_plan_code?: string | null;
  child_grant_duration_mode?: string | null;
  child_grant_duration_days?: number | null;
  child_grant_device_limit_override?: number | null;
  child_invite_count?: number;
  child_invite_expiry_mode?: string | null;
  child_policy_preview?: Record<string, unknown> | null;
}

export interface AdminInviteCodeInventoryResponse {
  items: AdminInviteCodeSummaryResponse[];
  total: number;
  offset: number;
  limit: number;
}

export interface AdminListInviteCodesParams {
  campaign_id?: string;
  campaign_key?: string;
  batch_id?: string;
  owner_user_id?: string;
  used_by_user_id?: string;
  root_invite_code_id?: string;
  parent_invite_code_id?: string;
  status?: string;
  used?: boolean;
  plan_id?: string;
  plan_code?: string;
  generation_depth?: number;
  created_from?: string;
  created_to?: string;
  used_from?: string;
  used_to?: string;
  expires_from?: string;
  expires_to?: string;
  prefix?: string;
  offset?: number;
  limit?: number;
}

export interface AdminInviteCampaignCreateRequest {
  campaign_key: string;
  name: string;
  description?: string | null;
  owner_mode?: string;
  starts_at?: string | null;
  expires_at?: string | null;
  allowed_surfaces?: string[];
  allowed_geos?: string[];
  allowed_markets?: string[];
  allowed_segments?: string[];
  risk_policy_key?: string | null;
  grant_plan_id?: string | null;
  grant_plan_code?: string | null;
  grant_duration_mode?: 'fixed_days' | 'lifetime';
  grant_duration_days?: number | null;
  grant_device_limit_override?: number | null;
  root_invite_expiry_mode?: 'relative' | 'absolute' | 'none';
  root_invite_expiry_days?: number | null;
  root_invite_expires_at?: string | null;
  child_invite_count?: number;
  child_invite_free_days?: number;
  child_invite_expiry_mode?: 'relative' | 'absolute' | 'none';
  child_invite_expiry_days?: number | null;
  child_invite_expires_at?: string | null;
  child_grant_plan_id?: string | null;
  child_grant_plan_code?: string | null;
  child_grant_duration_mode?: 'fixed_days' | 'lifetime';
  child_grant_duration_days?: number | null;
  child_grant_device_limit_override?: number | null;
  max_generation_depth?: number;
  require_no_active_access?: boolean;
  block_self_redemption?: boolean;
  risk_policy?: Record<string, unknown>;
  export_policy?: Record<string, unknown>;
  notification_policy?: Record<string, unknown>;
  caps?: Record<string, unknown>;
  lifetime_campaign_acknowledgement?: boolean;
  publish?: boolean;
  reason?: string | null;
}

export interface AdminInviteCampaignVersionResponse {
  id: string;
  campaign_id: string;
  version: number;
  status: string;
  grant_mode: string;
  grant_plan_id?: string | null;
  grant_duration_mode?: string;
  grant_duration_days?: number | null;
  grant_device_limit_override?: number | null;
  root_invite_expiry_mode?: string;
  root_invite_expiry_days?: number | null;
  root_invite_expires_at?: string | null;
  grant_snapshot: Record<string, unknown>;
  child_invite_count: number;
  child_invite_free_days: number;
  child_invite_expiry_days?: number | null;
  child_invite_expiry_mode?: string;
  child_invite_expires_at?: string | null;
  child_grant_plan_id?: string | null;
  child_grant_duration_mode?: string;
  child_grant_duration_days?: number | null;
  child_grant_device_limit_override?: number | null;
  child_grant_snapshot: Record<string, unknown>;
  max_generation_depth: number;
  block_self_redemption: boolean;
  require_no_active_access: boolean;
  allowed_surfaces: string[];
  risk_policy: Record<string, unknown>;
  redemption_policy: Record<string, unknown>;
  child_policy: Record<string, unknown>;
  issue_policy: Record<string, unknown>;
  export_policy: Record<string, unknown>;
  notification_policy: Record<string, unknown>;
  checksum: string;
  created_by_admin_id: string;
  published_by_admin_id?: string | null;
  published_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminInviteCampaignResponse {
  id: string;
  campaign_key: string;
  name: string;
  description?: string | null;
  status: string;
  owner_mode: string;
  current_version_id?: string | null;
  starts_at?: string | null;
  expires_at?: string | null;
  allowed_surfaces: string[];
  allowed_geos: Record<string, unknown>;
  risk_policy: Record<string, unknown>;
  export_policy: Record<string, unknown>;
  notification_policy: Record<string, unknown>;
  caps: Record<string, unknown>;
  created_by_admin_id: string;
  updated_by_admin_id?: string | null;
  published_at?: string | null;
  paused_at?: string | null;
  archived_at?: string | null;
  created_at: string;
  updated_at: string;
  current_version?: AdminInviteCampaignVersionResponse | null;
}

export interface AdminInviteCampaignListResponse {
  items: AdminInviteCampaignResponse[];
  total: number;
  offset: number;
  limit: number;
}

export interface AdminInviteCampaignActionRequest {
  reason: string;
}

export interface AdminInviteCampaignVersionCreateRequest {
  grant_plan_id?: string | null;
  grant_plan_code?: string | null;
  grant_duration_mode?: 'fixed_days' | 'lifetime';
  grant_duration_days?: number | null;
  grant_device_limit_override?: number | null;
  root_invite_expiry_mode?: 'relative' | 'absolute' | 'none';
  root_invite_expiry_days?: number | null;
  root_invite_expires_at?: string | null;
  child_invite_count?: number;
  child_invite_free_days?: number;
  child_invite_expiry_mode?: 'relative' | 'absolute' | 'none';
  child_invite_expiry_days?: number | null;
  child_invite_expires_at?: string | null;
  child_grant_plan_id?: string | null;
  child_grant_plan_code?: string | null;
  child_grant_duration_mode?: 'fixed_days' | 'lifetime';
  child_grant_duration_days?: number | null;
  child_grant_device_limit_override?: number | null;
  max_generation_depth?: number;
  require_no_active_access?: boolean;
  block_self_redemption?: boolean;
  allowed_surfaces?: string[];
  risk_policy?: Record<string, unknown>;
  export_policy?: Record<string, unknown>;
  notification_policy?: Record<string, unknown>;
  lifetime_campaign_acknowledgement?: boolean;
  reason?: string | null;
}

export interface AdminInviteCampaignVersionValidationResponse {
  version_id: string;
  checksum: string;
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface AdminInviteCampaignBatchCreateRequest {
  owner_user_id?: string | null;
  owner_user_ids?: string[];
  count: number;
  version_id?: string | null;
  idempotency_key?: string | null;
  expiry_mode?: 'campaign_default' | 'relative' | 'absolute' | 'none';
  expires_at?: string | null;
  expiry_days?: number | null;
  reason: string;
}

export interface AdminInviteBatchResponse {
  id: string;
  owner_user_id?: string | null;
  campaign_id?: string | null;
  invite_campaign_id?: string | null;
  invite_campaign_version_id?: string | null;
  root_invite_code_id?: string | null;
  parent_invite_code_id?: string | null;
  source_redemption_id?: string | null;
  root_owner_user_id?: string | null;
  generation_depth?: number;
  batch_kind?: string | null;
  source_growth_code_id?: string | null;
  source_benefit_id?: string | null;
  source_order_id?: string | null;
  source_payment_id?: string | null;
  source_type: string;
  requested_count: number;
  issued_count: number;
  friend_days: number;
  expiry_mode: string;
  expiry_days?: number | null;
  expires_at?: string | null;
  entitlement_mode: string;
  entitlement_profile_key?: string | null;
  plan_id?: string | null;
  entitlement_snapshot: Record<string, unknown>;
  grant_mode?: string | null;
  grant_plan_id?: string | null;
  grant_duration_mode?: string | null;
  grant_duration_days?: number | null;
  grant_device_limit_override?: number | null;
  grant_snapshot?: Record<string, unknown> | null;
  child_grant_plan_id?: string | null;
  child_grant_duration_mode?: string | null;
  child_grant_duration_days?: number | null;
  child_grant_device_limit_override?: number | null;
  child_invite_expiry_mode?: string | null;
  child_policy?: Record<string, unknown> | null;
  risk_policy?: Record<string, unknown> | null;
  redemption_policy?: Record<string, unknown> | null;
  issue_policy?: Record<string, unknown> | null;
  status: string;
  idempotency_key: string;
  revoked_at?: string | null;
  revoked_by_admin_id?: string | null;
  revoked_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminInviteBatchListResponse {
  items: AdminInviteBatchResponse[];
  total: number;
  offset: number;
  limit: number;
}

export interface AdminInviteCampaignBatchCreateResponse {
  campaign: AdminInviteCampaignResponse;
  batch: AdminInviteBatchResponse;
  raw_codes: string[];
}

export interface AdminInviteRedemptionResponse {
  id: string;
  invite_code_id: string;
  campaign_id?: string | null;
  campaign_version_id?: string | null;
  root_invite_code_id?: string | null;
  parent_invite_code_id?: string | null;
  inviter_user_id?: string | null;
  invitee_user_id: string;
  generation_depth: number;
  source_surface: string;
  entitlement_grant_id?: string | null;
  granted_plan_id?: string | null;
  granted_plan_code?: string | null;
  granted_duration_days?: number | null;
  child_batch_id?: string | null;
  child_issued_count?: number;
  status: string;
  blocked_reason?: string | null;
  risk_decision: Record<string, unknown>;
  grant_snapshot: Record<string, unknown>;
  redeemed_at?: string | null;
  reversed_at?: string | null;
  created_at: string;
}

export interface AdminInviteRedemptionListResponse {
  items: AdminInviteRedemptionResponse[];
  total: number;
  offset: number;
  limit: number;
}

export interface AdminInviteRedemptionReverseRequest {
  reason: string;
  cascade_mode?: 'none' | 'unused_child_invites' | 'all_descendants';
  confirm_descendant_reversal?: boolean;
}

export interface AdminInviteTreeNodeResponse {
  invite_code_id: string;
  parent_invite_code_id?: string | null;
  root_invite_code_id: string;
  owner_user_id?: string | null;
  used_by_user_id?: string | null;
  generation_depth: number;
  status: string;
  grant_mode?: string | null;
  grant_plan_id?: string | null;
  grant_duration_mode?: string | null;
  grant_device_limit_override?: number | null;
  child_batch_id?: string | null;
  granted_plan_id?: string | null;
  granted_plan_code?: string | null;
  grant_lifetime?: boolean;
  child_invite_count?: number;
  child_invite_expiry_mode?: string | null;
  child_count: number;
  created_at?: string | null;
  used_at?: string | null;
}

export interface AdminInviteTreeEdgeResponse {
  id: string;
  root_invite_code_id: string;
  parent_invite_code_id?: string | null;
  redeemed_invite_code_id: string;
  redemption_id: string;
  inviter_user_id?: string | null;
  invitee_user_id: string;
  generation_depth: number;
  status: string;
  child_batch_id?: string | null;
  granted_plan_id?: string | null;
  granted_plan_code?: string | null;
}

export interface AdminInviteTreeResponse {
  root_invite_code_id: string;
  nodes: AdminInviteTreeNodeResponse[];
  edges: AdminInviteTreeEdgeResponse[];
  stats: Record<string, unknown>;
}

export interface AdminInviteTreeRootResponse {
  root_invite_code_id: string;
  campaign_id?: string | null;
  campaign_key?: string | null;
  owner_user_id?: string | null;
  generation_depth?: number;
  status: string;
  issued_count: number;
  redeemed_count: number;
  child_invites_issued_count: number;
  max_depth_reached: number;
  created_at?: string | null;
}

export interface AdminInviteTreeRootListResponse {
  items: AdminInviteTreeRootResponse[];
  total: number;
  offset: number;
  limit: number;
}

export interface AdminInviteCampaignAnalyticsResponse {
  campaign_id: string;
  issued_count: number;
  issued_total?: number;
  redeemed_count: number;
  redeemed_total?: number;
  blocked_count: number;
  active_vpn_total?: number;
  child_invites_issued_total?: number;
  lifetime_grants?: number;
  premium_smart_ru_grants?: number;
  max_depth_reached?: number;
  depth_breakdown?: Record<string, number>;
  conversion?: {
    issued_to_redeemed_pct?: number;
    redeemed_to_connected_pct?: number;
  };
}

export interface AdminInviteBatchActionRequest {
  reason: string;
}

export interface AdminExtendInviteBatchRequest extends AdminInviteBatchActionRequest {
  expiry_days?: number | null;
  expires_at?: string | null;
}

export interface AdminInviteBatchExportCodeResponse {
  id: string;
  code: string;
  code_prefix?: string | null;
  code_hash?: string | null;
  status: string;
  is_used: boolean;
  expires_at?: string | null;
}

export interface AdminInviteBatchExportResponse {
  batch_id: string;
  exported_count: number;
  codes: AdminInviteBatchExportCodeResponse[];
}

export interface AdminGrowthSignalCount {
  key: string;
  count: number;
}

export interface AdminGrowthLifecycleEvent {
  id: string;
  event_name: string;
  event_family: string;
  aggregate_type: string;
  aggregate_id: string;
  occurred_at: string;
  event_status: string;
}

export interface AdminGrowthSignalsOverview {
  total_codes: number;
  active_codes: number;
  total_redemptions: number;
  active_reservations: number;
  blocked_reward_count: number;
  available_referral_credit_usd: number;
  code_status_breakdown: AdminGrowthSignalCount[];
  resolution_result_breakdown: AdminGrowthSignalCount[];
  rejection_reason_breakdown: AdminGrowthSignalCount[];
  redemption_breakdown: AdminGrowthSignalCount[];
  reward_status_breakdown: AdminGrowthSignalCount[];
  reward_type_breakdown: AdminGrowthSignalCount[];
  recent_lifecycle_events: AdminGrowthLifecycleEvent[];
}

export interface AdminGrowthReportingFamilySummary {
  family: string;
  issued_total: number;
  resolution_attempts_total: number;
  resolution_accepted_total: number;
  resolution_rejected_total: number;
  redemption_total: number;
  reservations_reserved_total: number;
  reservations_consumed_total: number;
  reservations_released_total: number;
  reservations_expired_total: number;
  rewards_created_total: number;
  rewards_available_total: number;
  rewards_reversed_total: number;
  reward_created_amount_usd: number;
  reward_available_amount_usd: number;
  reward_reversed_amount_usd: number;
}

export interface AdminGrowthReportingDailyPoint extends AdminGrowthReportingFamilySummary {
  report_date: string;
}

export interface AdminGrowthReportingRefreshRun {
  id: string;
  trigger_kind: string;
  refresh_status: string;
  requested_window_days: number;
  window_start: string;
  window_end: string;
  latest_rollup_date?: string | null;
  rows_written: number;
  families_updated: string[];
  error_message?: string | null;
  started_at: string;
  finished_at: string;
  refreshed_at?: string | null;
}

export interface AdminGrowthReportingHealth {
  freshness_status: 'fresh' | 'stale' | 'failed' | 'never_refreshed' | string;
  stale_reason?: string | null;
  refresh_age_seconds?: number | null;
  expected_refresh_interval_seconds: number;
  stale_after_seconds: number;
  auto_refresh_enabled: boolean;
  latest_attempt_at?: string | null;
  latest_success_at?: string | null;
  latest_failure_at?: string | null;
  latest_failure_message?: string | null;
  latest_run?: AdminGrowthReportingRefreshRun | null;
}

export interface AdminGrowthReportingExecutiveSummary {
  total_issued: number;
  total_redemptions: number;
  total_reward_available_usd: number;
  total_reward_reversed_usd: number;
  resolution_acceptance_rate_pct: number;
  dominant_family?: string | null;
  highlights: string[];
}

export interface AdminGrowthReportingRecipientPolicy {
  template_key: string;
  template_locale: string;
  email_subject_prefix?: string | null;
  title_override?: string | null;
  recipient_domain_policy: string;
  allowed_recipient_domains: string[];
  suppressed_until?: string | null;
  suppression_reason_code?: string | null;
}

export interface AdminGrowthReportingGovernanceFollowup {
  status: string;
  reason_code?: string | null;
  opened_at?: string | null;
  due_at?: string | null;
  last_notified_at?: string | null;
  resolved_at?: string | null;
  resolution_code?: string | null;
  is_overdue: boolean;
  action_required: boolean;
}

export interface AdminGrowthReportingGovernanceCoverageCount {
  coverage_state: string;
  count: number;
}

export interface AdminGrowthReportingGovernanceFollowupQueueItem {
  subscription_id: string;
  recipient_email: string;
  audience_key: string;
  health_status: string;
  followup: AdminGrowthReportingGovernanceFollowup;
  next_delivery_at: string;
  latest_delivery_status?: string | null;
  latest_delivery_reason?: string | null;
}

export interface AdminGrowthReportingGovernanceDecision {
  delivery_id: string;
  subscription_id: string;
  recipient_email: string;
  audience_key: string;
  template_key: string;
  decision_kind: string;
  status_reason: string;
  created_at: string;
  planned_at: string;
  window_start: string;
  window_end: string;
  can_export_artifact: boolean;
  summary: string;
}

export interface AdminGrowthReportingGovernanceAuditEvent {
  id: string;
  action: string;
  entity_id?: string | null;
  actor_label: string;
  reason_code?: string | null;
  changed_fields: string[];
  created_at: string;
}

export interface AdminGrowthReportingGovernanceOverview {
  generated_at: string;
  active_subscription_count: number;
  paused_subscription_count: number;
  coverage_gap_count: number;
  followup_open_count: number;
  followup_overdue_count: number;
  coverage_counts: AdminGrowthReportingGovernanceCoverageCount[];
  followup_queue: AdminGrowthReportingGovernanceFollowupQueueItem[];
  recent_decisions: AdminGrowthReportingGovernanceDecision[];
  recent_audit_events: AdminGrowthReportingGovernanceAuditEvent[];
  notes: string[];
}

export interface AdminGrowthReportingOverview {
  window_start: string;
  window_end: string;
  latest_rollup_date?: string | null;
  refreshed_at?: string | null;
  family_summaries: AdminGrowthReportingFamilySummary[];
  daily_points: AdminGrowthReportingDailyPoint[];
  totals: AdminGrowthReportingFamilySummary;
  health: AdminGrowthReportingHealth;
  executive_summary: AdminGrowthReportingExecutiveSummary;
  coverage_notes: string[];
}

export interface AdminGrowthReportingRefreshResponse {
  trigger_kind: string;
  window_start: string;
  window_end: string;
  latest_rollup_date?: string | null;
  refreshed_at: string;
  rows_written: number;
  families_updated: string[];
  coverage_notes: string[];
}

export interface AdminGrowthReportingSubscription {
  id: string;
  recipient_email: string;
  recipient_name?: string | null;
  audience_key: string;
  delivery_channel: string;
  cadence: string;
  report_window_days: number;
  subscription_status: string;
  next_delivery_at: string;
  last_delivery_attempt_at?: string | null;
  last_success_at?: string | null;
  latest_delivery_status?: string | null;
  latest_delivery_reason?: string | null;
  health_status: string;
  policy: AdminGrowthReportingRecipientPolicy;
  followup: AdminGrowthReportingGovernanceFollowup;
}

export interface AdminGrowthReportingDelivery {
  id: string;
  subscription_id: string;
  recipient_email: string;
  recipient_name?: string | null;
  audience_key: string;
  delivery_channel: string;
  cadence: string;
  report_window_days: number;
  template_key: string;
  template_locale: string;
  subject_line: string;
  title_line: string;
  delivery_status: string;
  status_reason?: string | null;
  freshness_status: string;
  artifact_checksum?: string | null;
  provider_name?: string | null;
  provider_message_id?: string | null;
  failure_message?: string | null;
  window_start: string;
  window_end: string;
  planned_at: string;
  started_at?: string | null;
  delivered_at?: string | null;
  created_at: string;
  updated_at: string;
  can_export_artifact: boolean;
  policy: AdminGrowthReportingRecipientPolicy;
}

export interface AdminGrowthReportingSubscriptionsResponse {
  items: AdminGrowthReportingSubscription[];
  total: number;
  overdue_count: number;
  active_count: number;
  retention_rollup_days: number;
  retention_refresh_run_days: number;
  retention_delivery_days: number;
}

export interface AdminGrowthReportingDeliveriesResponse {
  items: AdminGrowthReportingDelivery[];
  total: number;
  failed_count: number;
}

export interface AdminGrowthReportingGovernanceExportResponse {
  export_kind: string;
  filename: string;
  exported_at: string;
  overview: AdminGrowthReportingGovernanceOverview;
  payload: Record<string, unknown>;
}

export interface AdminCreateGrowthReportingSubscriptionRequest {
  recipient_email: string;
  recipient_name?: string | null;
  audience_key: string;
  cadence: string;
  report_window_days: number;
  policy?: AdminGrowthReportingRecipientPolicyRequest;
}

export interface AdminGrowthReportingRecipientPolicyRequest {
  template_key?: string | null;
  template_locale?: string;
  email_subject_prefix?: string | null;
  title_override?: string | null;
  recipient_domain_policy?: string;
  allowed_recipient_domains?: string[];
  suppressed_until?: string | null;
  suppression_reason_code?: string | null;
}

export interface AdminUpdateGrowthReportingSubscriptionRequest {
  recipient_email: string;
  recipient_name?: string | null;
  audience_key: string;
  cadence: string;
  report_window_days: number;
  policy?: AdminGrowthReportingRecipientPolicyRequest;
  reason_code?: string | null;
}

export interface AdminUpdateGrowthReportingSubscriptionStatusRequest {
  reason_code?: string | null;
}

export interface AdminUpdateGrowthReportingGovernanceFollowupRequest {
  reason_code?: string | null;
}

export interface AdminGrowthAbuseSignal {
  signal_key: string;
  signal_type: string;
  severity: string;
  code_type?: string | null;
  reason_code: string;
  count: number;
  unique_users: number;
  latest_event_at: string;
  review_hint: string;
  growth_code_id?: string | null;
  reward_allocation_id?: string | null;
  beneficiary_user_id?: string | null;
  source_redemption_id?: string | null;
}

export interface AdminGrowthAbuseSignals {
  items: AdminGrowthAbuseSignal[];
  total: number;
}

export interface AdminGrowthNotificationDelivery {
  id: string;
  mobile_user_id: string;
  user?: {
    id: string;
    email: string;
    username?: string | null;
    telegram_username?: string | null;
    referral_code?: string | null;
    is_partner: boolean;
  } | null;
  notification_key: string;
  notification_kind: string;
  delivery_channel: string;
  delivery_status: string;
  status_reason?: string | null;
  title: string;
  message: string;
  route_slug?: string | null;
  notes: string[];
  source_kind?: string | null;
  source_id?: string | null;
  notification_queue_id?: string | null;
  queue_status?: string | null;
  queue_error_message?: string | null;
  created_by_admin_user_id?: string | null;
  planned_at: string;
  delivered_at?: string | null;
  created_at: string;
  updated_at: string;
  can_resend: boolean;
  can_pause: boolean;
  can_revoke: boolean;
  can_resolve: boolean;
}

export interface AdminGrowthNotificationQueueSnapshot {
  id: string;
  status: string;
  attempts: number;
  scheduled_at: string;
  sent_at?: string | null;
  error_message?: string | null;
}

export interface AdminGrowthNotificationDeliveryEvent {
  id: string;
  event_type: string;
  delivery_status: string;
  reason_code?: string | null;
  event_payload: Record<string, unknown>;
  event_note?: string | null;
  notification_queue_id?: string | null;
  created_by_admin_user_id?: string | null;
  occurred_at: string;
  created_at: string;
}

export interface AdminGrowthNotificationSourceSummary {
  source_kind: string;
  source_id?: string | null;
  source_label?: string | null;
  source_status?: string | null;
  owner_user_id?: string | null;
  beneficiary_user_id?: string | null;
  metadata: Record<string, unknown>;
}

export interface AdminGrowthNotificationDeliveryDetail {
  delivery: AdminGrowthNotificationDelivery;
  sibling_deliveries: AdminGrowthNotificationDelivery[];
  event_timeline: AdminGrowthNotificationDeliveryEvent[];
  queue_snapshot?: AdminGrowthNotificationQueueSnapshot | null;
  source_summary?: AdminGrowthNotificationSourceSummary | null;
  lifecycle_events: AdminGrowthLifecycleEvent[];
  troubleshooting_state: string;
  customer_message_key: string;
  support_summary: string;
}

export interface AdminListGrowthNotificationDeliveriesResponse {
  items: AdminGrowthNotificationDelivery[];
  total: number;
  offset: number;
  limit: number;
}

export interface AdminListGrowthNotificationDeliveriesParams {
  mobile_user_id?: string;
  delivery_channel?: string;
  delivery_status?: string;
  source_kind?: string;
  offset?: number;
  limit?: number;
}

export interface AdminGrowthNotificationDeliveryActionRequest {
  reason_code?: string | null;
}

export interface AdminManualGrowthNotificationRequest {
  mobile_user_id: string;
  title: string;
  message: string;
  route_slug?: string;
  locale?: string;
  notes?: string[];
  channels?: string[];
}

export interface AdminManualGrowthNotificationResponse {
  deliveries: AdminGrowthNotificationDelivery[];
}

export interface AdminGiftCodeListItem {
  id: string;
  masked_code: string;
  raw_code?: string | null;
  batch_id?: string | null;
  status: string;
  issuer_type: string;
  source_type?: string | null;
  owner_user_id?: string | null;
  issued_by_admin_id?: string | null;
  plan_family?: string | null;
  duration_days?: number | null;
  recipient_hint?: string | null;
  gift_message?: string | null;
  expires_at?: string | null;
  created_at: string;
  redeemed_at?: string | null;
  redeemed_by_user_id?: string | null;
  source_order_id?: string | null;
  source_payment_id?: string | null;
}

export interface AdminListGiftCodesResponse {
  items: AdminGiftCodeListItem[];
  total: number;
  offset: number;
  limit: number;
}

export interface AdminListGiftCodesParams {
  owner_user_id?: string;
  offset?: number;
  limit?: number;
}

export interface AdminIssueGiftCodeRequest {
  owner_user_id: string;
  plan_id: string;
  recipient_hint?: string | null;
  gift_message?: string | null;
  reason_code?: string | null;
  admin_note?: string | null;
}

export interface AdminIssueGiftCodeResponse {
  gift_code: AdminGiftCodeListItem;
}

export interface AdminIssueGiftCodeBatchRequest {
  owner_user_id: string;
  plan_id: string;
  count: number;
  recipient_hint?: string | null;
  gift_message?: string | null;
  reason_code?: string | null;
  admin_note?: string | null;
}

export interface AdminIssueGiftCodeBatchResponse {
  batch_id: string;
  issued_count: number;
  gift_codes: AdminGiftCodeListItem[];
}

export interface AdminPartnerWorkspaceMemberResponse {
  id: string;
  admin_user_id: string;
  role_id: string;
  role_key: string;
  role_display_name: string;
  membership_status: string;
  permission_keys: string[];
  invited_by_admin_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminPartnerWorkspaceResponse {
  id: string;
  account_key: string;
  display_name: string;
  status: string;
  legacy_owner_user_id: string | null;
  created_by_admin_user_id: string | null;
  code_count: number;
  active_code_count: number;
  total_clients: number;
  total_earned: number;
  last_activity_at: string | null;
  current_role_key: string | null;
  current_permission_keys: string[];
  members: AdminPartnerWorkspaceMemberResponse[];
}

export interface AdminCreatePartnerWorkspaceRequest {
  display_name: string;
  account_key?: string | null;
  legacy_owner_user_id?: string | null;
  owner_admin_user_id?: string | null;
}

/**
 * Growth API client
 * Covers admin-ready acquisition and promotion surfaces.
 */
export const growthApi = {
  listPromos: (params?: { offset?: number; limit?: number }) =>
    apiClient.get<AdminListPromosResponse>('/admin/promo-codes', { params }),

  createPromo: (data: AdminCreatePromoRequest) =>
    apiClient.post<AdminCreatePromoResponse>('/admin/promo-codes', data),

  getPromo: (promoId: string) =>
    apiClient.get<AdminGetPromoResponse>(`/admin/promo-codes/${promoId}`),

  updatePromo: (promoId: string, data: AdminUpdatePromoRequest) =>
    apiClient.put<AdminUpdatePromoResponse>(`/admin/promo-codes/${promoId}`, data),

  deactivatePromo: (promoId: string) =>
    apiClient.delete<AdminDeactivatePromoResponse>(`/admin/promo-codes/${promoId}`),

  createInviteCodes: (data: AdminCreateInviteCodesPayload) =>
    apiClient.post<AdminCreateInviteCodesResponse>('/admin/invite-codes', data),

  listInviteCodes: (params?: AdminListInviteCodesParams) =>
    apiClient.get<AdminInviteCodeInventoryResponse>('/admin/invite-codes', { params }),

  listInviteBatches: (params?: AdminListInviteBatchesParams) =>
    apiClient.get<AdminInviteBatchListResponse>('/admin/invite-batches', { params }),

  exportInviteBatch: (batchId: string) =>
    apiClient.get<AdminInviteBatchExportResponse>(`/admin/invite-batches/${batchId}/export`),

  revokeInviteBatch: (batchId: string, data: AdminInviteBatchActionRequest) =>
    apiClient.post<AdminInviteBatchResponse>(`/admin/invite-batches/${batchId}/revoke`, data),

  extendInviteBatch: (batchId: string, data: AdminExtendInviteBatchRequest) =>
    apiClient.post<AdminInviteBatchResponse>(`/admin/invite-batches/${batchId}/extend`, data),

  resendInviteBatch: (batchId: string, data: AdminInviteBatchActionRequest) =>
    apiClient.post<AdminInviteBatchResponse>(`/admin/invite-batches/${batchId}/resend`, data),

  listInviteCampaigns: (params?: { status?: string; campaign_key?: string; offset?: number; limit?: number }) =>
    apiClient.get<AdminInviteCampaignListResponse>('/admin/invite-campaigns', { params }),

  createInviteCampaign: (data: AdminInviteCampaignCreateRequest) =>
    apiClient.post<AdminInviteCampaignResponse>('/admin/invite-campaigns', data),

  createInviteCampaignVersion: (campaignId: string, data: AdminInviteCampaignVersionCreateRequest) =>
    apiClient.post<AdminInviteCampaignVersionResponse>(`/admin/invite-campaigns/${campaignId}/versions`, data),

  validateInviteCampaignVersion: (campaignId: string, versionId: string) =>
    apiClient.post<AdminInviteCampaignVersionValidationResponse>(
      `/admin/invite-campaigns/${campaignId}/versions/${versionId}/validate`,
    ),

  publishInviteCampaignVersion: (
    campaignId: string,
    versionId: string,
    data: AdminInviteCampaignActionRequest,
  ) =>
    apiClient.post<AdminInviteCampaignResponse>(
      `/admin/invite-campaigns/${campaignId}/versions/${versionId}/publish`,
      data,
    ),

  createInviteCampaignBatch: (campaignId: string, data: AdminInviteCampaignBatchCreateRequest) =>
    apiClient.post<AdminInviteCampaignBatchCreateResponse>(
      `/admin/invite-campaigns/${campaignId}/batches`,
      data,
    ),

  listInviteCampaignRedemptions: (
    campaignId: string,
    params?: { status?: string; offset?: number; limit?: number },
  ) =>
    apiClient.get<AdminInviteRedemptionListResponse>(
      `/admin/invite-campaigns/${campaignId}/redemptions`,
      { params },
    ),

  reverseInviteRedemption: (redemptionId: string, data: AdminInviteRedemptionReverseRequest) =>
    apiClient.post<AdminInviteRedemptionResponse>(
      `/admin/invite-redemptions/${redemptionId}/reverse`,
      data,
    ),

  getInviteCampaignAnalytics: (campaignId: string) =>
    apiClient.get<AdminInviteCampaignAnalyticsResponse>(
      `/admin/invite-campaigns/${campaignId}/analytics`,
    ),

  getInviteTree: (rootInviteCodeId: string) =>
    apiClient.get<AdminInviteTreeResponse>(`/admin/invite-trees/${rootInviteCodeId}`),

  listInviteTreeRoots: (params?: { campaign_id?: string; offset?: number; limit?: number }) =>
    apiClient.get<AdminInviteTreeRootListResponse>('/admin/invite-trees', { params }),

  getInviteTreeForUser: (userId: string) =>
    apiClient.get<AdminInviteTreeResponse>(`/admin/invite-trees/users/${userId}`),

  promotePartner: (data: AdminPromotePartnerRequest) =>
    apiClient.post<AdminPromotePartnerResponse>('/admin/partners/promote', data),

  getReferralOverview: () =>
    apiClient.get<AdminReferralOverviewResponse>('/admin/referrals/overview'),

  getReferralUserDetail: (userId: string) =>
    apiClient.get<AdminReferralUserDetailResponse>(`/admin/referrals/users/${userId}`),

  listPartners: (params?: AdminPartnersListParams) =>
    apiClient.get<AdminPartnersListResponse>('/admin/partners', { params }),

  getPartnerDetail: (userId: string) =>
    apiClient.get<AdminPartnerDetailResponse>(`/admin/partners/${userId}`),

  getGrowthSignalsOverview: () =>
    apiClient.get<AdminGrowthSignalsOverviewResponse>('/admin/growth-signals/overview'),

  getGrowthReportingOverview: (params?: { window_days?: number }) =>
    apiClient.get<AdminGrowthReportingOverview>('/admin/growth-reporting/overview', { params }),

  getGrowthReportingGovernanceOverview: () =>
    apiClient.get<AdminGrowthReportingGovernanceOverview>('/admin/growth-reporting/governance'),

  refreshGrowthReporting: (params?: { window_days?: number }) =>
    apiClient.post<AdminGrowthReportingRefreshResponse>('/admin/growth-reporting/refresh', undefined, { params }),

  listGrowthReportingSubscriptions: () =>
    apiClient.get<AdminGrowthReportingSubscriptionsResponse>('/admin/growth-reporting/subscriptions'),

  createGrowthReportingSubscription: (data: AdminCreateGrowthReportingSubscriptionRequest) =>
    apiClient.post<AdminGrowthReportingSubscription>('/admin/growth-reporting/subscriptions', data),

  updateGrowthReportingSubscription: (
    subscriptionId: string,
    data: AdminUpdateGrowthReportingSubscriptionRequest,
  ) =>
    apiClient.put<AdminGrowthReportingSubscription>(
      `/admin/growth-reporting/subscriptions/${subscriptionId}`,
      data,
    ),

  pauseGrowthReportingSubscription: (
    subscriptionId: string,
    data: AdminUpdateGrowthReportingSubscriptionStatusRequest = {},
  ) =>
    apiClient.post<AdminGrowthReportingSubscription>(
      `/admin/growth-reporting/subscriptions/${subscriptionId}/pause`,
      data,
    ),

  resumeGrowthReportingSubscription: (
    subscriptionId: string,
    data: AdminUpdateGrowthReportingSubscriptionStatusRequest = {},
  ) =>
    apiClient.post<AdminGrowthReportingSubscription>(
      `/admin/growth-reporting/subscriptions/${subscriptionId}/resume`,
      data,
    ),

  updateGrowthReportingGovernanceFollowup: (
    subscriptionId: string,
    action: 'resolve' | 'dismiss',
    data: AdminUpdateGrowthReportingGovernanceFollowupRequest = {},
  ) =>
    apiClient.post<AdminGrowthReportingSubscription>(
      `/admin/growth-reporting/subscriptions/${subscriptionId}/follow-up/${action}`,
      data,
    ),

  listGrowthReportingDeliveries: (params?: { limit?: number }) =>
    apiClient.get<AdminGrowthReportingDeliveriesResponse>('/admin/growth-reporting/deliveries', { params }),

  exportGrowthReportingOverview: async (params?: { window_days?: number }) => {
    const response = await apiClient.get<Blob>('/admin/growth-reporting/export', {
      params,
      responseType: 'blob',
    });
    return response;
  },

  exportGrowthReportingGovernanceSnapshot: async () => {
    const response = await apiClient.get<Blob>('/admin/growth-reporting/governance/export', {
      responseType: 'blob',
    });
    return response;
  },

  exportGrowthReportingDeliveryArtifact: async (deliveryId: string) => {
    const response = await apiClient.get<Blob>(
      `/admin/growth-reporting/deliveries/${deliveryId}/artifact`,
      { responseType: 'blob' },
    );
    return response;
  },

  listGrowthAbuseSignals: (params?: { limit?: number }) =>
    apiClient.get<AdminGrowthAbuseSignalsResponse>('/admin/growth-signals/abuse-queue', { params }),

  listGrowthNotificationDeliveries: (params?: AdminListGrowthNotificationDeliveriesParams) =>
    apiClient.get<AdminListGrowthNotificationDeliveriesResponse>(
      '/admin/growth-notification-deliveries',
      { params },
    ),

  getGrowthNotificationDeliveryDetail: (deliveryId: string) =>
    apiClient.get<AdminGrowthNotificationDeliveryDetail>(
      `/admin/growth-notification-deliveries/${deliveryId}`,
    ),

  exportGrowthNotificationDeliveryDetail: async (deliveryId: string) => {
    const response = await apiClient.get<Blob>(
      `/admin/growth-notification-deliveries/${deliveryId}/export`,
      { responseType: 'blob' },
    );
    return response;
  },

  createManualGrowthNotification: (data: AdminManualGrowthNotificationRequest) =>
    apiClient.post<AdminManualGrowthNotificationResponse>(
      '/admin/growth-notification-deliveries/manual',
      data,
    ),

  resendGrowthNotificationDelivery: (
    deliveryId: string,
    data: AdminGrowthNotificationDeliveryActionRequest = {},
  ) =>
    apiClient.post<AdminGrowthNotificationDelivery>(
      `/admin/growth-notification-deliveries/${deliveryId}/resend`,
      data,
    ),

  pauseGrowthNotificationDelivery: (
    deliveryId: string,
    data: AdminGrowthNotificationDeliveryActionRequest = {},
  ) =>
    apiClient.post<AdminGrowthNotificationDelivery>(
      `/admin/growth-notification-deliveries/${deliveryId}/pause`,
      data,
    ),

  revokeGrowthNotificationDelivery: (
    deliveryId: string,
    data: AdminGrowthNotificationDeliveryActionRequest = {},
  ) =>
    apiClient.post<AdminGrowthNotificationDelivery>(
      `/admin/growth-notification-deliveries/${deliveryId}/revoke`,
      data,
    ),

  resolveGrowthNotificationDelivery: (
    deliveryId: string,
    data: AdminGrowthNotificationDeliveryActionRequest = {},
  ) =>
    apiClient.post<AdminGrowthNotificationDelivery>(
      `/admin/growth-notification-deliveries/${deliveryId}/resolve`,
      data,
    ),

  lookupGrowthCode: (data: AdminGrowthCodeLookupRequest) =>
    apiClient.post<AdminGrowthCodeLookupResponse>('/admin/growth-codes/lookup', data),

  getGrowthRuleCatalog: () =>
    apiV3Client.get<AdminGrowthRuleCatalogResponse>('/admin/growth/rule-catalog'),

  compileGrowthRule: (data: AdminGrowthRuleCompileRequest) =>
    apiV3Client.post<AdminGrowthRuleCompileResponse>('/admin/growth/policies/compile', data),

  simulateGrowthRule: (data: AdminGrowthRuleSimulateRequest) =>
    apiV3Client.post<AdminGrowthRuleSimulateResponse>('/admin/growth/policies/impact-preview', data),

  listGrowthRulePolicies: (params?: AdminGrowthRulePolicyListParams) =>
    apiV3Client.get<AdminGrowthRulePolicyListResponse>('/admin/growth/policy-versions', { params }),

  createGrowthRulePolicy: (data: AdminGrowthRulePolicyCreateRequest) =>
    apiV3Client.post<AdminGrowthRulePolicyVersionResponse>('/admin/growth/policy-versions', data),

  submitGrowthRulePolicy: (policyVersionId: string, data: AdminGrowthRulePolicyActionRequest) =>
    apiV3Client.post<AdminGrowthRulePolicyVersionResponse>(
      `/admin/growth/policy-versions/${policyVersionId}/submit`,
      data,
    ),

  approveGrowthRulePolicy: (policyVersionId: string, data: AdminGrowthRulePolicyActionRequest) =>
    apiV3Client.post<AdminGrowthRulePolicyVersionResponse>(
      `/admin/growth/policy-versions/${policyVersionId}/approve`,
      data,
    ),

  rejectGrowthRulePolicy: (policyVersionId: string, data: AdminGrowthRulePolicyActionRequest) =>
    apiV3Client.post<AdminGrowthRulePolicyVersionResponse>(
      `/admin/growth/policy-versions/${policyVersionId}/reject`,
      data,
    ),

  publishGrowthRulePolicy: (policyVersionId: string, data: AdminGrowthRulePolicyActionRequest) =>
    apiV3Client.post<AdminGrowthRulePolicyVersionResponse>(
      `/admin/growth/policy-versions/${policyVersionId}/publish`,
      data,
    ),

  rollbackGrowthRulePolicy: (
    policyVersionId: string,
    data: AdminGrowthRulePolicyRollbackRequest,
  ) =>
    apiV3Client.post<AdminGrowthRulePolicyVersionResponse>(
      `/admin/growth/policy-versions/${policyVersionId}/rollback`,
      data,
    ),

  diffGrowthRulePolicy: (policyVersionId: string, compareToPolicyVersionId?: string) =>
    apiV3Client.get<AdminGrowthRulePolicyDiffResponse>(
      compareToPolicyVersionId
        ? `/admin/growth/policy-versions/${policyVersionId}/diff/${compareToPolicyVersionId}`
        : `/admin/growth/policy-versions/${policyVersionId}/diff`,
    ),

  listGrowthCampaigns: (params?: AdminGrowthCampaignListParams) =>
    apiClient.get<AdminGrowthCampaignListResponse>('/admin/growth/campaigns', { params }),

  createGrowthCampaign: (data: AdminGrowthCampaignCreateRequest) =>
    apiClient.post<AdminGrowthCampaignResponse>('/admin/growth/campaigns', data),

  getGrowthCampaign: (campaignId: string) =>
    apiClient.get<AdminGrowthCampaignResponse>(`/admin/growth/campaigns/${campaignId}`),

  updateGrowthCampaign: (campaignId: string, data: AdminGrowthCampaignPatchRequest) =>
    apiClient.patch<AdminGrowthCampaignResponse>(`/admin/growth/campaigns/${campaignId}`, data),

  publishGrowthCampaign: (campaignId: string, data: AdminGrowthCampaignActionRequest) =>
    apiClient.post<AdminGrowthCampaignResponse>(
      `/admin/growth/campaigns/${campaignId}/publish`,
      data,
    ),

  pauseGrowthCampaign: (campaignId: string, data: AdminGrowthCampaignActionRequest) =>
    apiClient.post<AdminGrowthCampaignResponse>(
      `/admin/growth/campaigns/${campaignId}/pause`,
      data,
    ),

  resumeGrowthCampaign: (campaignId: string, data: AdminGrowthCampaignActionRequest) =>
    apiClient.post<AdminGrowthCampaignResponse>(
      `/admin/growth/campaigns/${campaignId}/resume`,
      data,
    ),

  archiveGrowthCampaign: (campaignId: string, data: AdminGrowthCampaignActionRequest) =>
    apiClient.post<AdminGrowthCampaignResponse>(
      `/admin/growth/campaigns/${campaignId}/archive`,
      data,
    ),

  revokeGrowthCampaign: (campaignId: string, data: AdminGrowthCampaignActionRequest) =>
    apiClient.post<AdminGrowthCampaignResponse>(
      `/admin/growth/campaigns/${campaignId}/revoke`,
      data,
    ),

  getClientCapabilities: () =>
    apiClient.get<ClientCapabilityResponse>('/client/capabilities'),

  getCustomerSiteRuntime: () =>
    apiClient.get<AdminCustomerSiteRuntimeConfigResponse>('/admin/system-config/customer-site-runtime'),

  updateCustomerSiteRuntime: (data: UpdateAdminCustomerSiteRuntimeConfigRequest) =>
    apiClient.put<AdminCustomerSiteRuntimeConfigResponse>('/admin/system-config/customer-site-runtime', data),

  executeCustomerSiteRuntimeAction: (data: ExecuteAdminCustomerSiteRuntimeActionRequest) =>
    apiClient.post<AdminCustomerSiteRuntimeConfigResponse>('/admin/system-config/customer-site-runtime/actions', data),

  getCustomerSiteRuntimeTimeline: (params?: AdminCustomerSiteRuntimeTimelineParams) =>
    apiClient.get<AdminCustomerSiteRuntimeTimelineResponse>(
      '/admin/system-config/customer-site-runtime/timeline',
      { params },
    ),

  inspectGrowthCodeSets: (params?: AdminGrowthCodeSetInspectParams) =>
    apiV3Client.get<AdminGrowthCodeSetInspectResponse>('/admin/growth/code-sets/inspect', {
      params,
    }),

  getGrowthFxStatus: () =>
    apiV3Client.get<AdminGrowthFxStatusResponse>('/admin/growth/fx/status'),

  listGrowthFxRates: (params?: AdminGrowthFxRateListParams) =>
    apiV3Client.get<AdminGrowthFxRateListResponse>('/admin/growth/fx/rates', { params }),

  createConfiguredGrowthFxRate: (data: AdminGrowthFxConfiguredRateRequest) =>
    apiV3Client.post<AdminGrowthFxRateResponse>('/admin/growth/fx/configured-rates', data),

  createGrowthFxXtrTable: (data: AdminGrowthFxXtrTableRequest) =>
    apiV3Client.post<AdminGrowthFxRateResponse>('/admin/growth/fx/xtr-tables', data),

  refreshGrowthFxRates: (data: AdminGrowthFxRefreshRequest) =>
    apiV3Client.post<AdminGrowthFxRefreshResponse>('/admin/growth/fx/rates/refresh', data),

  approveGrowthFxRate: (rateId: string, data: AdminGrowthFxProviderActionRequest) =>
    apiV3Client.post<AdminGrowthFxRateResponse>(`/admin/growth/fx/rates/${rateId}/approve`, data),

  rejectGrowthFxRate: (rateId: string, data: AdminGrowthFxProviderActionRequest) =>
    apiV3Client.post<AdminGrowthFxRateResponse>(`/admin/growth/fx/rates/${rateId}/reject`, data),

  simulateGrowthFxConversion: (data: AdminGrowthFxSimulateRequest) =>
    apiV3Client.post<AdminGrowthFxSimulationResponse>('/admin/growth/fx/simulate', data),

  disableGrowthFxProvider: (providerKey: string, data: AdminGrowthFxProviderActionRequest) =>
    apiV3Client.post<AdminGrowthFxStatusResponse>(
      `/admin/growth/fx/providers/${providerKey}/disable`,
      data,
    ),

  enableGrowthFxProvider: (providerKey: string, data: AdminGrowthFxProviderActionRequest) =>
    apiV3Client.post<AdminGrowthFxStatusResponse>(
      `/admin/growth/fx/providers/${providerKey}/enable`,
      data,
    ),

  listPrivateCatalogTargets: (params?: AdminGrowthPrivateTargetListParams) =>
    apiV3Client.get<AdminGrowthPrivateTargetListResponse>('/admin/growth/private-catalog/targets', {
      params,
    }),

  listPrivateCatalogGrants: (params?: AdminGrowthPrivateGrantListParams) =>
    apiV3Client.get<AdminGrowthPrivateGrantListResponse>('/admin/growth/private-grants', { params }),

  getPrivateCatalogGrant: (grantId: string) =>
    apiV3Client.get<AdminGrowthPrivateGrantResponse>(`/admin/growth/private-grants/${grantId}`),

  revokePrivateCatalogGrant: (grantId: string, data: AdminGrowthPrivateGrantRevokeRequest) =>
    apiV3Client.post<AdminGrowthPrivateGrantResponse>(
      `/admin/growth/private-grants/${grantId}/revoke`,
      data,
    ),

  getGrowthOnboardingSettings: () =>
    apiV3Client.get<AdminGrowthOnboardingRuntimeResponse>('/admin/growth/onboarding/settings'),

  updateGrowthOnboardingSettings: (data: AdminGrowthOnboardingRuntimeUpdateRequest) =>
    apiV3Client.put<AdminGrowthOnboardingRuntimeResponse>('/admin/growth/onboarding/settings', data),

  listGrowthOnboardingStates: (params?: AdminGrowthOnboardingStateListParams) =>
    apiV3Client.get<AdminGrowthOnboardingStateListResponse>('/admin/growth/onboarding/states', {
      params,
    }),

  getGrowthOnboardingState: (stateId: string) =>
    apiV3Client.get<AdminGrowthOnboardingStateResponse>(
      `/admin/growth/onboarding/states/${stateId}`,
    ),

  listGrowthOnboardingApplications: (params?: AdminGrowthOnboardingApplicationListParams) =>
    apiV3Client.get<AdminGrowthOnboardingApplicationListResponse>(
      '/admin/growth/onboarding/applications',
      { params },
    ),

  resetGrowthOnboardingState: (stateId: string, data: AdminGrowthOnboardingStateResetRequest) =>
    apiV3Client.post<AdminGrowthOnboardingStateResponse>(
      `/admin/growth/onboarding/states/${stateId}/reset`,
      data,
    ),

  listGrowthRiskModels: (params?: AdminGrowthRiskModelListParams) =>
    apiV3Client.get<AdminGrowthRiskModelListResponse>('/admin/growth/risk/models', { params }),

  listGrowthRiskDecisions: (params?: AdminGrowthRiskDecisionListParams) =>
    apiV3Client.get<AdminGrowthRiskDecisionListResponse>('/admin/growth/risk/decisions', { params }),

  listGrowthRiskReviews: (params?: AdminGrowthRiskReviewListParams) =>
    apiV3Client.get<AdminGrowthRiskReviewListResponse>('/admin/growth/risk/reviews', { params }),

  resolveGrowthRiskReview: (riskReviewId: string, data: AdminGrowthRiskReviewResolveRequest) =>
    apiV3Client.post<AdminGrowthRiskReviewResponse>(
      `/admin/growth/risk/reviews/${riskReviewId}/resolve`,
      data,
    ),

  listGiftCodes: (params?: AdminListGiftCodesParams) =>
    apiClient.get<AdminListGiftCodesResponse>('/admin/gift-codes', { params }),

  issueGiftCode: (data: AdminIssueGiftCodeRequest) =>
    apiClient.post<AdminIssueGiftCodeResponse>('/admin/gift-codes/issue', data),

  issueGiftCodeBatch: (data: AdminIssueGiftCodeBatchRequest) =>
    apiClient.post<AdminIssueGiftCodeBatchResponse>('/admin/gift-code-batches/issue', data),

  createPartnerWorkspace: (data: AdminCreatePartnerWorkspaceRequest) =>
    apiClient.post<AdminPartnerWorkspaceResponse>('/admin/partner-workspaces', data),

  getPartnerWorkspace: (workspaceId: string) =>
    apiClient.get<AdminPartnerWorkspaceResponse>(`/admin/partner-workspaces/${workspaceId}`),
};

export type {
  AdminGrowthAbuseSignalsResponse,
  AdminGrowthRuleCatalogResponse,
  AdminGrowthRuleCompileRequest,
  AdminGrowthRuleCompileResponse,
  AdminGrowthRuleSimulateRequest,
  AdminGrowthRuleSimulateResponse,
  AdminGrowthRulePolicyActionRequest,
  AdminGrowthRulePolicyCreateRequest,
  AdminGrowthRulePolicyDiffResponse,
  AdminGrowthRulePolicyListParams,
  AdminGrowthRulePolicyListResponse,
  AdminGrowthRulePolicyRollbackRequest,
  AdminGrowthRulePolicyVersionResponse,
  AdminGrowthCampaignActionRequest,
  AdminGrowthCampaignCreateRequest,
  AdminGrowthCampaignListParams,
  AdminGrowthCampaignListResponse,
  AdminGrowthCampaignPatchRequest,
  AdminGrowthCampaignResponse,
  AdminCustomerSiteRuntime,
  AdminCustomerSiteRuntimeConfigResponse,
  ExecuteAdminCustomerSiteRuntimeActionRequest,
  AdminCustomerSiteRuntimeTimelineParams,
  AdminCustomerSiteRuntimeTimelineResponse,
  AdminGrowthCodeSetInspectParams,
  AdminGrowthCodeSetInspectResponse,
  AdminGrowthFxConfiguredRateRequest,
  AdminGrowthFxProviderActionRequest,
  AdminGrowthFxRefreshRequest,
  AdminGrowthFxRefreshResponse,
  AdminGrowthFxRateListParams,
  AdminGrowthFxRateListResponse,
  AdminGrowthFxRateResponse,
  AdminGrowthFxSimulateRequest,
  AdminGrowthFxSimulationResponse,
  AdminGrowthFxStatusResponse,
  AdminGrowthFxXtrTableRequest,
  AdminGrowthPrivateGrantListParams,
  AdminGrowthPrivateGrantListResponse,
  AdminGrowthPrivateGrantResponse,
  AdminGrowthPrivateGrantRevokeRequest,
  AdminGrowthPrivateTargetListParams,
  AdminGrowthPrivateTargetListResponse,
  AdminGrowthOnboardingApplicationListParams,
  AdminGrowthOnboardingApplicationListResponse,
  AdminGrowthOnboardingRuntimeResponse,
  AdminGrowthOnboardingRuntimeUpdateRequest,
  AdminGrowthOnboardingStateListParams,
  AdminGrowthOnboardingStateListResponse,
  AdminGrowthOnboardingStateResetRequest,
  AdminGrowthOnboardingStateResponse,
  AdminGrowthRiskDecisionListParams,
  AdminGrowthRiskDecisionListResponse,
  AdminGrowthRiskModelListParams,
  AdminGrowthRiskModelListResponse,
  AdminGrowthRiskReviewListParams,
  AdminGrowthRiskReviewListResponse,
  AdminGrowthRiskReviewResolveRequest,
  AdminGrowthRiskReviewResponse,
  UpdateAdminCustomerSiteRuntimeConfigRequest,
  AdminGrowthSignalsOverviewResponse,
  AdminCreateInviteCodesRequest,
  AdminCreateInviteCodesResponse,
  ClientCapabilityResponse,
  AdminPartnerDetailResponse,
  AdminPartnersListParams,
  AdminPartnersListResponse,
  AdminCreatePromoRequest,
  AdminCreatePromoResponse,
  AdminDeactivatePromoResponse,
  AdminGetPromoResponse,
  AdminListPromosResponse,
  AdminPromotePartnerRequest,
  AdminPromotePartnerResponse,
  AdminReferralOverviewResponse,
  AdminReferralUserDetailResponse,
  AdminUpdatePromoRequest,
  AdminUpdatePromoResponse,
};
