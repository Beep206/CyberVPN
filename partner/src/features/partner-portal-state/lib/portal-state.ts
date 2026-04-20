import { useSyncExternalStore } from 'react';
import {
  isPartnerReleaseRing,
  type PartnerReleaseRing,
} from '@/features/partner-shell/config/section-registry';
import {
  loadPartnerApplicationDraft,
  type PartnerApplicationDraft,
  type PartnerPrimaryLane,
} from '@/features/partner-onboarding/lib/application-draft-storage';

export type PartnerWorkspaceStatus =
  | 'draft'
  | 'email_verified'
  | 'submitted'
  | 'needs_info'
  | 'under_review'
  | 'waitlisted'
  | 'approved_probation'
  | 'active'
  | 'restricted'
  | 'suspended'
  | 'rejected'
  | 'terminated';

export type PartnerFinanceReadiness =
  | 'not_started'
  | 'in_progress'
  | 'ready'
  | 'blocked';

export type PartnerComplianceReadiness =
  | 'not_started'
  | 'declarations_complete'
  | 'evidence_requested'
  | 'approved'
  | 'blocked';

export type PartnerTechnicalReadiness =
  | 'not_required'
  | 'in_progress'
  | 'ready'
  | 'blocked';

export type PartnerGovernanceState =
  | 'clear'
  | 'watch'
  | 'warning'
  | 'limited'
  | 'frozen';

export type PartnerPortalScenario =
  | 'draft'
  | 'needs_info'
  | 'under_review'
  | 'waitlisted'
  | 'approved_probation'
  | 'active'
  | 'restricted';

export type PartnerWorkspaceRole =
  | 'workspace_owner'
  | 'workspace_admin'
  | 'finance_manager'
  | 'analyst'
  | 'traffic_manager'
  | 'support_manager'
  | 'technical_manager'
  | 'legal_compliance_manager';

export type PartnerTeamMemberStatus =
  | 'active'
  | 'invited'
  | 'limited';

export type PartnerLaneMembershipStatus =
  | 'not_applied'
  | 'pending'
  | 'approved_probation'
  | 'approved_active'
  | 'declined'
  | 'paused'
  | 'suspended'
  | 'terminated';

export type PartnerLegalDocumentKind =
  | 'program_terms'
  | 'payout_terms'
  | 'traffic_policy'
  | 'disclosure_guidelines'
  | 'reseller_annex';

export type PartnerLegalDocumentStatus =
  | 'read_only'
  | 'pending_acceptance'
  | 'accepted';

export type PartnerCodeKind =
  | 'starter_code'
  | 'vanity_link'
  | 'qr_bundle'
  | 'sub_id_template';

export type PartnerCodeStatus =
  | 'draft'
  | 'pending_approval'
  | 'active'
  | 'paused'
  | 'revoked'
  | 'expired';

export type PartnerCampaignChannel =
  | 'content'
  | 'telegram'
  | 'paid_social'
  | 'search'
  | 'storefront';

export type PartnerCampaignStatus =
  | 'available'
  | 'approval_required'
  | 'in_review'
  | 'approved'
  | 'restricted';

export type PartnerComplianceTaskKind =
  | 'disclosure_attestation'
  | 'approved_sources'
  | 'creative_approval'
  | 'evidence_upload'
  | 'postback_readiness'
  | 'support_ownership';

export type PartnerComplianceTaskStatus =
  | 'complete'
  | 'action_required'
  | 'under_review'
  | 'blocked';

export type PartnerAnalyticsMetricKey =
  | 'clicks'
  | 'registrations'
  | 'first_paid'
  | 'repeat_paid'
  | 'refund_rate'
  | 'chargeback_rate'
  | 'earnings_available';

export type PartnerAnalyticsMetricTrend =
  | 'up'
  | 'steady'
  | 'down';

export type PartnerReportExportKind =
  | 'code_report'
  | 'geo_report'
  | 'statement_export'
  | 'payout_status_export'
  | 'explainability_report';

export type PartnerReportExportStatus =
  | 'available'
  | 'scheduled'
  | 'blocked';

export type PartnerFinanceStatementStatus =
  | 'draft'
  | 'on_hold'
  | 'ready'
  | 'paid'
  | 'blocked';

export type PartnerPayoutAccountKind =
  | 'bank_account'
  | 'crypto_wallet'
  | 'invoice_profile';

export type PartnerPayoutAccountStatus =
  | 'missing'
  | 'pending_review'
  | 'ready'
  | 'blocked';

export type PartnerConversionKind =
  | 'registration'
  | 'first_paid'
  | 'repeat_paid'
  | 'refund'
  | 'chargeback';

export type PartnerConversionStatus =
  | 'commissionable'
  | 'on_hold'
  | 'rejected'
  | 'reversed';

export type PartnerCustomerScope =
  | 'masked'
  | 'workspace_scoped'
  | 'storefront_scoped';

export type PartnerIntegrationCredentialKind =
  | 'reporting_api_token'
  | 'postback_secret'
  | 'webhook_secret'
  | 'storefront_api_key';

export type PartnerIntegrationCredentialStatus =
  | 'ready'
  | 'pending_rotation'
  | 'blocked';

export type PartnerIntegrationDeliveryChannel =
  | 'webhook'
  | 'postback'
  | 'reporting_export';

export type PartnerIntegrationDeliveryStatus =
  | 'delivered'
  | 'failed'
  | 'paused';

export type PartnerResellerStorefrontStatus =
  | 'in_review'
  | 'ready'
  | 'restricted';

export type PartnerReviewRequestKind =
  | 'business_profile'
  | 'owned_channels'
  | 'traffic_methods'
  | 'support_ownership'
  | 'finance_profile';

export type PartnerCaseKind =
  | 'application_review'
  | 'requested_info'
  | 'finance_onboarding'
  | 'compliance_followup'
  | 'restriction_notice'
  | 'attribution_dispute'
  | 'payout_dispute'
  | 'technical_support'
  | 'statement_question';

export type PartnerCaseStatus =
  | 'open'
  | 'waiting_on_partner'
  | 'waiting_on_ops'
  | 'resolved';

export type PartnerNotificationKind =
  | 'workspace_draft'
  | 'application_submitted'
  | 'application_needs_info'
  | 'application_approved_probation'
  | 'application_waitlisted'
  | 'application_rejected'
  | 'needs_info'
  | 'review_in_progress'
  | 'waitlisted'
  | 'probation_started'
  | 'lane_membership_changed'
  | 'review_request_opened'
  | 'case_created'
  | 'case_reply_received'
  | 'legal_acceptance_required'
  | 'statement_ready'
  | 'payout_blocked'
  | 'integration_delivery_failed'
  | 'governance_action_applied'
  | 'finance_blocked'
  | 'payout_profile_needed'
  | 'workspace_restricted'
  | 'workspace_active';

export type PartnerNotificationTone =
  | 'info'
  | 'success'
  | 'warning'
  | 'critical';

export interface PartnerReviewRequest {
  id: string;
  kind: PartnerReviewRequestKind;
  dueDate: string;
  status: 'open' | 'submitted';
  availableActions?: string[];
  threadEvents?: PartnerPortalThreadEvent[];
}

export interface PartnerPortalCase {
  id: string;
  kind: PartnerCaseKind;
  status: PartnerCaseStatus;
  updatedAt: string;
  notes?: string[];
  availableActions?: string[];
  threadEvents?: PartnerPortalThreadEvent[];
}

export interface PartnerPortalThreadEvent {
  id: string;
  actionKind: string;
  message: string;
  createdAt: string;
  createdByAdminUserId?: string | null;
}

export interface PartnerPortalNotification {
  id: string;
  kind: PartnerNotificationKind;
  tone: PartnerNotificationTone;
  createdAt: string;
  unread: boolean;
  routeSlug?: string | null;
  message?: string | null;
  notes?: string[];
  actionRequired?: boolean;
}

export interface PartnerTeamMember {
  id: string;
  name: string;
  email: string;
  role: PartnerWorkspaceRole;
  status: PartnerTeamMemberStatus;
}

export interface PartnerLaneMembership {
  lane: PartnerPrimaryLane;
  status: PartnerLaneMembershipStatus;
  assignedManager: string;
  restrictions: string[];
}

export interface PartnerLegalDocument {
  id: string;
  kind: PartnerLegalDocumentKind;
  version: string;
  status: PartnerLegalDocumentStatus;
  acceptedAt: string | null;
  acceptedByRole: PartnerWorkspaceRole | null;
}

export interface PartnerCode {
  id: string;
  label: string;
  kind: PartnerCodeKind;
  status: PartnerCodeStatus;
  destination: string;
  notes: string[];
}

export interface PartnerCampaignAsset {
  id: string;
  name: string;
  channel: PartnerCampaignChannel;
  status: PartnerCampaignStatus;
  approvalOwner: string;
  notes: string[];
}

export interface PartnerComplianceTask {
  id: string;
  kind: PartnerComplianceTaskKind;
  status: PartnerComplianceTaskStatus;
  ownerRole: PartnerWorkspaceRole;
  notes: string[];
}

export interface PartnerAnalyticsMetric {
  key: PartnerAnalyticsMetricKey;
  value: string;
  trend: PartnerAnalyticsMetricTrend;
  notes: string[];
}

export interface PartnerReportExport {
  id: string;
  kind: PartnerReportExportKind;
  status: PartnerReportExportStatus;
  cadence: string;
  notes: string[];
  availableActions?: string[];
  threadEvents?: PartnerPortalThreadEvent[];
  lastRequestedAt?: string | null;
}

export interface PartnerFinanceStatement {
  id: string;
  periodLabel: string;
  status: PartnerFinanceStatementStatus;
  gross: string;
  net: string;
  available: string;
  onHold: string;
  currency: string;
  notes: string[];
}

export interface PartnerPayoutAccount {
  id: string;
  label: string;
  kind: PartnerPayoutAccountKind;
  status: PartnerPayoutAccountStatus;
  currency: string;
  isDefault: boolean;
  notes: string[];
}

export interface PartnerFinanceSnapshot {
  availableEarnings: string;
  onHoldEarnings: string;
  reserves: string;
  nextPayoutForecast: string;
  currency: string;
}

export interface PartnerConversionRecord {
  id: string;
  kind: PartnerConversionKind;
  status: PartnerConversionStatus;
  orderLabel: string;
  customerLabel: string;
  codeLabel: string;
  geo: string;
  amount: string;
  customerScope: PartnerCustomerScope;
  updatedAt: string;
  notes: string[];
}

export interface PartnerIntegrationCredential {
  id: string;
  label: string;
  kind: PartnerIntegrationCredentialKind;
  status: PartnerIntegrationCredentialStatus;
  lastRotatedAt: string | null;
  notes: string[];
}

export interface PartnerIntegrationDeliveryLog {
  id: string;
  channel: PartnerIntegrationDeliveryChannel;
  status: PartnerIntegrationDeliveryStatus;
  destination: string;
  lastAttemptAt: string;
  notes: string[];
}

export interface PartnerResellerStorefront {
  id: string;
  label: string;
  domain: string;
  status: PartnerResellerStorefrontStatus;
  currency: string;
  supportOwner: string;
  notes: string[];
}

export interface PartnerResellerConsoleSnapshot {
  pricebookLabel: string;
  supportOwnership: string;
  customerScope: string;
  technicalHealth: string;
}

export interface PartnerPortalState {
  scenario: PartnerPortalScenario;
  workspaceRole: PartnerWorkspaceRole;
  releaseRing: PartnerReleaseRing;
  primaryLane: PartnerPrimaryLane | '';
  workspaceStatus: PartnerWorkspaceStatus;
  financeReadiness: PartnerFinanceReadiness;
  complianceReadiness: PartnerComplianceReadiness;
  technicalReadiness: PartnerTechnicalReadiness;
  governanceState: PartnerGovernanceState;
  teamMembers: PartnerTeamMember[];
  laneMemberships: PartnerLaneMembership[];
  legalDocuments: PartnerLegalDocument[];
  codes: PartnerCode[];
  campaignAssets: PartnerCampaignAsset[];
  complianceTasks: PartnerComplianceTask[];
  analyticsMetrics: PartnerAnalyticsMetric[];
  reportExports: PartnerReportExport[];
  financeStatements: PartnerFinanceStatement[];
  payoutAccounts: PartnerPayoutAccount[];
  financeSnapshot: PartnerFinanceSnapshot;
  conversionRecords: PartnerConversionRecord[];
  integrationCredentials: PartnerIntegrationCredential[];
  integrationDeliveryLogs: PartnerIntegrationDeliveryLog[];
  resellerStorefronts: PartnerResellerStorefront[];
  resellerSnapshot: PartnerResellerConsoleSnapshot;
  reviewRequests: PartnerReviewRequest[];
  cases: PartnerPortalCase[];
  notifications: PartnerPortalNotification[];
  updatedAt: string | null;
}

export const PARTNER_PORTAL_STATE_STORAGE_KEY =
  'ozoxy-partner-portal-state:v1';

const DEFAULT_DATE = '2026-04-18T12:00:00.000Z';
const DEFAULT_DUE_DATE = '2026-04-24T12:00:00.000Z';

const DEFAULT_PORTAL_STATE: PartnerPortalState = {
  scenario: 'draft',
  workspaceRole: 'workspace_owner',
  releaseRing: 'R1',
  primaryLane: '',
  workspaceStatus: 'draft',
  financeReadiness: 'not_started',
  complianceReadiness: 'not_started',
  technicalReadiness: 'not_required',
  governanceState: 'clear',
  teamMembers: [],
  laneMemberships: [],
  legalDocuments: [],
  codes: [],
  campaignAssets: [],
  complianceTasks: [],
  analyticsMetrics: [],
  reportExports: [],
  financeStatements: [],
  payoutAccounts: [],
  financeSnapshot: {
    availableEarnings: '0',
    onHoldEarnings: '0',
    reserves: '0',
    nextPayoutForecast: '0',
    currency: 'USD',
  },
  conversionRecords: [],
  integrationCredentials: [],
  integrationDeliveryLogs: [],
  resellerStorefronts: [],
  resellerSnapshot: {
    pricebookLabel: '',
    supportOwnership: '',
    customerScope: '',
    technicalHealth: '',
  },
  reviewRequests: [],
  cases: [],
  notifications: [],
  updatedAt: null,
};

const listeners = new Set<() => void>();

let currentPartnerPortalState = DEFAULT_PORTAL_STATE;
let hasInitializedStore = false;

function readStringField(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

function readBooleanField(value: unknown, fallback = false): boolean {
  return typeof value === 'boolean' ? value : fallback;
}

function isPrimaryLane(value: string): value is PartnerPrimaryLane {
  return value === 'creator_affiliate'
    || value === 'performance_media'
    || value === 'reseller_api';
}

function isWorkspaceStatus(value: string): value is PartnerWorkspaceStatus {
  return [
    'draft',
    'email_verified',
    'submitted',
    'needs_info',
    'under_review',
    'waitlisted',
    'approved_probation',
    'active',
    'restricted',
    'suspended',
    'rejected',
    'terminated',
  ].includes(value);
}

function isFinanceReadiness(value: string): value is PartnerFinanceReadiness {
  return ['not_started', 'in_progress', 'ready', 'blocked'].includes(value);
}

function isComplianceReadiness(
  value: string,
): value is PartnerComplianceReadiness {
  return [
    'not_started',
    'declarations_complete',
    'evidence_requested',
    'approved',
    'blocked',
  ].includes(value);
}

function isTechnicalReadiness(
  value: string,
): value is PartnerTechnicalReadiness {
  return ['not_required', 'in_progress', 'ready', 'blocked'].includes(value);
}

function isGovernanceState(value: string): value is PartnerGovernanceState {
  return ['clear', 'watch', 'warning', 'limited', 'frozen'].includes(value);
}

function isPortalScenario(value: string): value is PartnerPortalScenario {
  return [
    'draft',
    'needs_info',
    'under_review',
    'waitlisted',
    'approved_probation',
    'active',
    'restricted',
  ].includes(value);
}

function isWorkspaceRole(value: string): value is PartnerWorkspaceRole {
  return [
    'workspace_owner',
    'workspace_admin',
    'finance_manager',
    'analyst',
    'traffic_manager',
    'support_manager',
    'technical_manager',
    'legal_compliance_manager',
  ].includes(value);
}

function isTeamMemberStatus(value: string): value is PartnerTeamMemberStatus {
  return ['active', 'invited', 'limited'].includes(value);
}

function isLaneMembershipStatus(value: string): value is PartnerLaneMembershipStatus {
  return [
    'not_applied',
    'pending',
    'approved_probation',
    'approved_active',
    'declined',
    'paused',
    'suspended',
    'terminated',
  ].includes(value);
}

function isLegalDocumentKind(value: string): value is PartnerLegalDocumentKind {
  return [
    'program_terms',
    'payout_terms',
    'traffic_policy',
    'disclosure_guidelines',
    'reseller_annex',
  ].includes(value);
}

function isLegalDocumentStatus(value: string): value is PartnerLegalDocumentStatus {
  return ['read_only', 'pending_acceptance', 'accepted'].includes(value);
}

function isCodeKind(value: string): value is PartnerCodeKind {
  return [
    'starter_code',
    'vanity_link',
    'qr_bundle',
    'sub_id_template',
  ].includes(value);
}

function isCodeStatus(value: string): value is PartnerCodeStatus {
  return [
    'draft',
    'pending_approval',
    'active',
    'paused',
    'revoked',
    'expired',
  ].includes(value);
}

function isCampaignChannel(value: string): value is PartnerCampaignChannel {
  return [
    'content',
    'telegram',
    'paid_social',
    'search',
    'storefront',
  ].includes(value);
}

function isCampaignStatus(value: string): value is PartnerCampaignStatus {
  return [
    'available',
    'approval_required',
    'in_review',
    'approved',
    'restricted',
  ].includes(value);
}

function isComplianceTaskKind(value: string): value is PartnerComplianceTaskKind {
  return [
    'disclosure_attestation',
    'approved_sources',
    'creative_approval',
    'evidence_upload',
    'postback_readiness',
    'support_ownership',
  ].includes(value);
}

function isComplianceTaskStatus(value: string): value is PartnerComplianceTaskStatus {
  return [
    'complete',
    'action_required',
    'under_review',
    'blocked',
  ].includes(value);
}

function isAnalyticsMetricKey(value: string): value is PartnerAnalyticsMetricKey {
  return [
    'clicks',
    'registrations',
    'first_paid',
    'repeat_paid',
    'refund_rate',
    'chargeback_rate',
    'earnings_available',
  ].includes(value);
}

function isAnalyticsMetricTrend(value: string): value is PartnerAnalyticsMetricTrend {
  return ['up', 'steady', 'down'].includes(value);
}

function isReportExportKind(value: string): value is PartnerReportExportKind {
  return [
    'code_report',
    'geo_report',
    'statement_export',
    'payout_status_export',
    'explainability_report',
  ].includes(value);
}

function isReportExportStatus(value: string): value is PartnerReportExportStatus {
  return ['available', 'scheduled', 'blocked'].includes(value);
}

function isFinanceStatementStatus(value: string): value is PartnerFinanceStatementStatus {
  return ['draft', 'on_hold', 'ready', 'paid', 'blocked'].includes(value);
}

function isPayoutAccountKind(value: string): value is PartnerPayoutAccountKind {
  return ['bank_account', 'crypto_wallet', 'invoice_profile'].includes(value);
}

function isPayoutAccountStatus(value: string): value is PartnerPayoutAccountStatus {
  return ['missing', 'pending_review', 'ready', 'blocked'].includes(value);
}

function isConversionKind(value: string): value is PartnerConversionKind {
  return [
    'registration',
    'first_paid',
    'repeat_paid',
    'refund',
    'chargeback',
  ].includes(value);
}

function isConversionStatus(value: string): value is PartnerConversionStatus {
  return ['commissionable', 'on_hold', 'rejected', 'reversed'].includes(value);
}

function isCustomerScope(value: string): value is PartnerCustomerScope {
  return ['masked', 'workspace_scoped', 'storefront_scoped'].includes(value);
}

function isIntegrationCredentialKind(
  value: string,
): value is PartnerIntegrationCredentialKind {
  return [
    'reporting_api_token',
    'postback_secret',
    'webhook_secret',
    'storefront_api_key',
  ].includes(value);
}

function isIntegrationCredentialStatus(
  value: string,
): value is PartnerIntegrationCredentialStatus {
  return ['ready', 'pending_rotation', 'blocked'].includes(value);
}

function isIntegrationDeliveryChannel(
  value: string,
): value is PartnerIntegrationDeliveryChannel {
  return ['webhook', 'postback', 'reporting_export'].includes(value);
}

function isIntegrationDeliveryStatus(
  value: string,
): value is PartnerIntegrationDeliveryStatus {
  return ['delivered', 'failed', 'paused'].includes(value);
}

function isResellerStorefrontStatus(
  value: string,
): value is PartnerResellerStorefrontStatus {
  return ['in_review', 'ready', 'restricted'].includes(value);
}

function isReviewRequestKind(value: string): value is PartnerReviewRequestKind {
  return [
    'business_profile',
    'owned_channels',
    'traffic_methods',
    'support_ownership',
    'finance_profile',
  ].includes(value);
}

function isCaseKind(value: string): value is PartnerCaseKind {
  return [
    'application_review',
    'requested_info',
    'finance_onboarding',
    'compliance_followup',
    'restriction_notice',
    'attribution_dispute',
    'payout_dispute',
    'technical_support',
    'statement_question',
  ].includes(value);
}

function isCaseStatus(value: string): value is PartnerCaseStatus {
  return ['open', 'waiting_on_partner', 'waiting_on_ops', 'resolved'].includes(value);
}

function isNotificationKind(value: string): value is PartnerNotificationKind {
  return [
    'workspace_draft',
    'application_submitted',
    'application_needs_info',
    'application_approved_probation',
    'application_waitlisted',
    'application_rejected',
    'needs_info',
    'review_in_progress',
    'waitlisted',
    'probation_started',
    'lane_membership_changed',
    'review_request_opened',
    'case_created',
    'case_reply_received',
    'legal_acceptance_required',
    'statement_ready',
    'payout_blocked',
    'integration_delivery_failed',
    'governance_action_applied',
    'finance_blocked',
    'payout_profile_needed',
    'workspace_restricted',
    'workspace_active',
  ].includes(value);
}

function isNotificationTone(value: string): value is PartnerNotificationTone {
  return ['info', 'success', 'warning', 'critical'].includes(value);
}

function getLaneTechnicalBaseline(
  primaryLane: PartnerPrimaryLane | '',
): PartnerTechnicalReadiness {
  return primaryLane === 'performance_media' || primaryLane === 'reseller_api'
    ? 'in_progress'
    : 'not_required';
}

function buildScenarioTeamMembers(
  scenario: PartnerPortalScenario,
  primaryLane: PartnerPrimaryLane | '',
): PartnerTeamMember[] {
  const technicalStatus: PartnerTeamMemberStatus =
    primaryLane === 'performance_media' || primaryLane === 'reseller_api'
      ? (scenario === 'active' || scenario === 'restricted' || scenario === 'approved_probation'
        ? 'active'
        : 'invited')
      : 'invited';

  const extendedStatus: PartnerTeamMemberStatus =
    scenario === 'active'
      ? 'active'
      : scenario === 'restricted'
        ? 'limited'
        : 'invited';

  const launchStatus: PartnerTeamMemberStatus =
    scenario === 'draft'
      ? 'invited'
      : scenario === 'restricted'
        ? 'limited'
        : 'active';

  return [
    {
      id: 'owner',
      name: 'Alex Mercer',
      email: 'alex@northstar.example',
      role: 'workspace_owner',
      status: 'active',
    },
    {
      id: 'finance',
      name: 'Maya Finch',
      email: 'finance@northstar.example',
      role: 'finance_manager',
      status: launchStatus,
    },
    {
      id: 'analyst',
      name: 'Noah Vale',
      email: 'analytics@northstar.example',
      role: 'analyst',
      status: launchStatus,
    },
    {
      id: 'traffic',
      name: 'Iris Shaw',
      email: 'traffic@northstar.example',
      role: 'traffic_manager',
      status: launchStatus,
    },
    {
      id: 'support',
      name: 'Dorian Reed',
      email: 'support@northstar.example',
      role: 'support_manager',
      status: launchStatus,
    },
    {
      id: 'workspace-admin',
      name: 'Tala Quinn',
      email: 'admin@northstar.example',
      role: 'workspace_admin',
      status: extendedStatus,
    },
    {
      id: 'technical',
      name: 'Vik Rao',
      email: 'tech@northstar.example',
      role: 'technical_manager',
      status: technicalStatus,
    },
    {
      id: 'legal',
      name: 'Rhea Cole',
      email: 'legal@northstar.example',
      role: 'legal_compliance_manager',
      status:
        scenario === 'draft'
          ? 'invited'
          : scenario === 'restricted'
            ? 'limited'
            : 'active',
    },
  ];
}

function buildScenarioLaneMemberships(
  scenario: PartnerPortalScenario,
  primaryLane: PartnerPrimaryLane | '',
): PartnerLaneMembership[] {
  const laneOrder: PartnerPrimaryLane[] = [
    'creator_affiliate',
    'performance_media',
    'reseller_api',
  ];

  const laneStatusForPrimary = (() => {
    if (!primaryLane) {
      return 'not_applied' as const;
    }

    if (
      scenario === 'needs_info'
      || scenario === 'under_review'
      || scenario === 'waitlisted'
    ) {
      return 'pending' as const;
    }
    if (scenario === 'approved_probation') {
      return 'approved_probation' as const;
    }
    if (scenario === 'active') {
      return 'approved_active' as const;
    }
    if (scenario === 'restricted') {
      return 'paused' as const;
    }

    return 'not_applied' as const;
  })();

  return laneOrder.map((lane) => {
    const isPrimary = primaryLane === lane;
    const assignedManager = lane === 'reseller_api'
      ? 'Distribution Ops'
      : lane === 'performance_media'
        ? 'Performance Review Desk'
        : 'Partner Success';

    const restrictions = !isPrimary
      ? ['Not requested yet']
      : scenario === 'approved_probation'
        ? ['Probation traffic cap', 'Expansion gated by finance readiness']
        : scenario === 'active'
          ? ['Operational scope depends on workspace role and governance state']
          : scenario === 'restricted'
            ? ['Expansion blocked until restriction is resolved']
            : scenario === 'waitlisted'
              ? ['Activation deferred by partner ops']
              : scenario === 'needs_info'
                ? ['Missing evidence and profile clarifications']
                : ['No active launch scope yet'];

    return {
      lane,
      status: isPrimary ? laneStatusForPrimary : 'not_applied',
      assignedManager,
      restrictions,
    } satisfies PartnerLaneMembership;
  });
}

function buildScenarioLegalDocuments(
  scenario: PartnerPortalScenario,
  primaryLane: PartnerPrimaryLane | '',
): PartnerLegalDocument[] {
  const acceptedAt = scenario === 'active' || scenario === 'restricted'
    ? '2026-04-18T12:00:00.000Z'
    : null;
  const baseStatus: PartnerLegalDocumentStatus =
    scenario === 'approved_probation'
      ? 'pending_acceptance'
      : scenario === 'active' || scenario === 'restricted'
        ? 'accepted'
        : 'read_only';
  const acceptedByRole: PartnerWorkspaceRole | null =
    acceptedAt ? 'workspace_owner' : null;

  const documents: PartnerLegalDocument[] = [
    {
      id: 'program-terms',
      kind: 'program_terms',
      version: 'v1.0',
      status: scenario === 'approved_probation' ? 'accepted' : baseStatus,
      acceptedAt: scenario === 'approved_probation' ? DEFAULT_DATE : acceptedAt,
      acceptedByRole: scenario === 'approved_probation'
        ? 'workspace_owner'
        : acceptedByRole,
    },
    {
      id: 'payout-terms',
      kind: 'payout_terms',
      version: 'v1.0',
      status: scenario === 'active' || scenario === 'restricted'
        ? 'accepted'
        : scenario === 'approved_probation'
          ? 'pending_acceptance'
          : 'read_only',
      acceptedAt,
      acceptedByRole,
    },
    {
      id: 'traffic-policy',
      kind: 'traffic_policy',
      version: 'v1.1',
      status: scenario === 'approved_probation'
        ? 'accepted'
        : baseStatus,
      acceptedAt: scenario === 'approved_probation' ? DEFAULT_DATE : acceptedAt,
      acceptedByRole: scenario === 'approved_probation'
        ? 'legal_compliance_manager'
        : acceptedByRole,
    },
    {
      id: 'disclosure-guidelines',
      kind: 'disclosure_guidelines',
      version: 'v1.0',
      status: baseStatus,
      acceptedAt,
      acceptedByRole,
    },
  ];

  if (primaryLane === 'reseller_api') {
    documents.push({
      id: 'reseller-annex',
      kind: 'reseller_annex',
      version: 'v1.0',
      status: scenario === 'active' || scenario === 'restricted'
        ? 'accepted'
        : scenario === 'approved_probation'
          ? 'pending_acceptance'
          : 'read_only',
      acceptedAt,
      acceptedByRole,
    });
  }

  return documents;
}

function buildScenarioCodes(
  scenario: PartnerPortalScenario,
  primaryLane: PartnerPrimaryLane | '',
): PartnerCode[] {
  if (!primaryLane || scenario === 'draft' || scenario === 'needs_info' || scenario === 'under_review' || scenario === 'waitlisted') {
    return [];
  }

  if (primaryLane === 'creator_affiliate') {
    return [
      {
        id: 'creator-starter',
        label: 'CYBER-STARTER',
        kind: 'starter_code',
        status: scenario === 'restricted' ? 'paused' : 'active',
        destination: '/vpn/privacy-bundle',
        notes: ['Starter probation code', 'Default attribution owner: workspace'],
      },
      {
        id: 'creator-vanity',
        label: 'northstar-vpn',
        kind: 'vanity_link',
        status: scenario === 'approved_probation'
          ? 'pending_approval'
          : scenario === 'restricted'
            ? 'paused'
            : 'active',
        destination: '/vpn/creator-offer',
        notes: ['Vanity route for content placements', 'Expansion subject to manager review'],
      },
      {
        id: 'creator-subid',
        label: 'creator-subid-macro',
        kind: 'sub_id_template',
        status: scenario === 'restricted' ? 'paused' : 'active',
        destination: '{base_url}?sub_id={sub_id}',
        notes: ['Supports attribution explainability', 'Use per placement or creator channel'],
      },
      {
        id: 'creator-qr',
        label: 'creator-launch-qr',
        kind: 'qr_bundle',
        status: scenario === 'approved_probation'
          ? 'pending_approval'
          : scenario === 'restricted'
            ? 'paused'
            : 'active',
        destination: '/vpn/mobile-offer',
        notes: ['Mobile and offline placements', 'Unlocks fully after active launch'],
      },
    ];
  }

  if (primaryLane === 'performance_media') {
    return [
      {
        id: 'performance-launch',
        label: 'perf-launch-01',
        kind: 'starter_code',
        status: scenario === 'approved_probation'
          ? 'pending_approval'
          : scenario === 'restricted'
            ? 'paused'
            : 'active',
        destination: '/vpn/performance-offer',
        notes: ['Limited launch scope', 'First code stays under probation traffic cap'],
      },
      {
        id: 'performance-vanity',
        label: 'perf-search-intl',
        kind: 'vanity_link',
        status: scenario === 'approved_probation'
          ? 'draft'
          : scenario === 'restricted'
            ? 'paused'
            : 'active',
        destination: '/vpn/search-prelanding',
        notes: ['Requires declared prelanding domain', 'Keyword and geo scope may be limited'],
      },
      {
        id: 'performance-subid',
        label: 'perf-click-macro',
        kind: 'sub_id_template',
        status: scenario === 'restricted' ? 'paused' : 'active',
        destination: '{base_url}?click_id={click_id}&sub_id={sub_id}',
        notes: ['Postback-ready tracking template', 'Mandatory for filtered conversion review'],
      },
      {
        id: 'performance-qr',
        label: 'perf-qr-pack',
        kind: 'qr_bundle',
        status: scenario === 'active'
          ? 'active'
          : scenario === 'restricted'
            ? 'paused'
            : 'draft',
        destination: '/vpn/performance-mobile',
        notes: ['Optional for mixed offline campaigns', 'Not part of the initial probation path'],
      },
    ];
  }

  return [
    {
      id: 'reseller-launch',
      label: 'reseller-start-01',
      kind: 'starter_code',
      status: scenario === 'approved_probation'
        ? 'pending_approval'
        : scenario === 'restricted'
          ? 'paused'
          : 'active',
      destination: '/vpn/reseller-checkout',
      notes: ['Starter code before storefront activation', 'Commerce scope stays limited on probation'],
    },
    {
      id: 'reseller-vanity',
      label: 'partner-storefront',
      kind: 'vanity_link',
      status: scenario === 'active'
        ? 'active'
        : scenario === 'restricted'
          ? 'paused'
          : 'draft',
      destination: '/vpn/reseller-storefront',
      notes: ['Storefront vanity path', 'Requires legal and finance alignment'],
    },
    {
      id: 'reseller-subid',
      label: 'reseller-scope-macro',
      kind: 'sub_id_template',
      status: scenario === 'approved_probation'
        ? 'pending_approval'
        : scenario === 'restricted'
          ? 'paused'
          : 'active',
      destination: '{base_url}?storefront_id={storefront_id}&sub_id={sub_id}',
      notes: ['Scoped to reseller properties', 'Links customer and storefront explainability later'],
    },
  ];
}

function buildScenarioCampaignAssets(
  scenario: PartnerPortalScenario,
  primaryLane: PartnerPrimaryLane | '',
): PartnerCampaignAsset[] {
  if (!primaryLane || scenario === 'draft' || scenario === 'needs_info' || scenario === 'under_review' || scenario === 'waitlisted') {
    return [];
  }

  if (primaryLane === 'creator_affiliate') {
    return [
      {
        id: 'creator-content-kit',
        name: 'Creator content starter kit',
        channel: 'content',
        status: scenario === 'restricted' ? 'restricted' : 'available',
        approvalOwner: 'Partner Success',
        notes: ['Review copy snippets and landing blocks', 'Built for owned content and community placements'],
      },
      {
        id: 'creator-telegram-pack',
        name: 'Telegram promo sequence',
        channel: 'telegram',
        status: scenario === 'approved_probation'
          ? 'approval_required'
          : scenario === 'restricted'
            ? 'restricted'
            : 'approved',
        approvalOwner: 'Creative Review',
        notes: ['Disclosure template included', 'Channel-specific claims remain governed'],
      },
      {
        id: 'creator-landing-pack',
        name: 'Coupon and landing page bundle',
        channel: 'content',
        status: scenario === 'approved_probation'
          ? 'approval_required'
          : scenario === 'restricted'
            ? 'restricted'
            : 'approved',
        approvalOwner: 'Partner Success',
        notes: ['Supports seasonal offers', 'Expansion usually follows initial quality validation'],
      },
    ];
  }

  if (primaryLane === 'performance_media') {
    return [
      {
        id: 'performance-paid-social',
        name: 'Paid social creative pack',
        channel: 'paid_social',
        status: scenario === 'restricted'
          ? 'restricted'
          : scenario === 'approved_probation'
            ? 'in_review'
            : 'approved',
        approvalOwner: 'Performance Review Desk',
        notes: ['Creative approval is mandatory', 'Launch scope tied to declared geos and traffic sources'],
      },
      {
        id: 'performance-search-kit',
        name: 'Search and prelanding toolkit',
        channel: 'search',
        status: scenario === 'approved_probation'
          ? 'approval_required'
          : scenario === 'restricted'
            ? 'restricted'
            : 'approved',
        approvalOwner: 'Performance Review Desk',
        notes: ['Brand-bidding rules are enforced', 'Prelanding domains must match declarations'],
      },
      {
        id: 'performance-disclosure',
        name: 'Disclosure and policy copy pack',
        channel: 'content',
        status: scenario === 'restricted' ? 'restricted' : 'available',
        approvalOwner: 'Compliance',
        notes: ['Required before campaign scale-out', 'Use approved earnings and privacy language only'],
      },
    ];
  }

  return [
    {
      id: 'reseller-brand-kit',
      name: 'Co-branded reseller launch pack',
      channel: 'storefront',
      status: scenario === 'active'
        ? 'approved'
        : scenario === 'restricted'
          ? 'restricted'
          : 'approval_required',
      approvalOwner: 'Distribution Ops',
      notes: ['Storefront and domain alignment required', 'Copy must match contract and support scope'],
    },
    {
      id: 'reseller-support-pack',
      name: 'Support handoff and disclosure kit',
      channel: 'content',
      status: scenario === 'restricted' ? 'restricted' : 'available',
      approvalOwner: 'Support Ops',
      notes: ['Defines support ownership boundaries', 'Use after contact and escalation setup are confirmed'],
    },
  ];
}

function buildScenarioComplianceTasks(
  scenario: PartnerPortalScenario,
  primaryLane: PartnerPrimaryLane | '',
): PartnerComplianceTask[] {
  if (!primaryLane || scenario === 'draft') {
    return [];
  }

  const evidenceStatus: PartnerComplianceTaskStatus =
    scenario === 'needs_info'
      ? 'action_required'
      : scenario === 'under_review' || scenario === 'waitlisted'
        ? 'under_review'
        : scenario === 'restricted'
          ? 'blocked'
          : 'complete';

  const baseTasks: PartnerComplianceTask[] = [
    {
      id: 'disclosure-attestation',
      kind: 'disclosure_attestation',
      status: scenario === 'needs_info'
        ? 'action_required'
        : scenario === 'under_review' || scenario === 'waitlisted'
          ? 'under_review'
          : 'complete',
      ownerRole: 'workspace_owner',
      notes: ['Material connection disclosure remains mandatory', 'Versioned policy history lives in contracts & legal'],
    },
    {
      id: 'approved-sources',
      kind: 'approved_sources',
      status: primaryLane === 'creator_affiliate' && scenario === 'approved_probation'
        ? 'under_review'
        : scenario === 'restricted'
          ? 'blocked'
          : 'complete',
      ownerRole: 'traffic_manager',
      notes: ['Declared channels and domains shape launch scope', 'Undeclared sources remain blocked'],
    },
    {
      id: 'evidence-upload',
      kind: 'evidence_upload',
      status: evidenceStatus,
      ownerRole: 'legal_compliance_manager',
      notes: ['Upload screenshots, domains, and policy evidence when requested', 'Evidence requests remain visible in restricted state'],
    },
  ];

  if (primaryLane === 'performance_media') {
    baseTasks.push(
      {
        id: 'creative-approval',
        kind: 'creative_approval',
        status: scenario === 'approved_probation'
          ? 'action_required'
          : scenario === 'restricted'
            ? 'blocked'
            : 'complete',
        ownerRole: 'traffic_manager',
        notes: ['Performance creatives require explicit approval', 'Expansion remains blocked until approved'],
      },
      {
        id: 'postback-readiness',
        kind: 'postback_readiness',
        status: scenario === 'approved_probation'
          ? 'action_required'
          : scenario === 'active' || scenario === 'restricted'
            ? 'complete'
            : 'under_review',
        ownerRole: 'technical_manager',
        notes: ['Click ID or postback capability is required', 'Diagnostic tooling arrives in later integration phases'],
      },
    );
  }

  if (primaryLane === 'reseller_api') {
    baseTasks.push({
      id: 'support-ownership',
      kind: 'support_ownership',
      status: scenario === 'approved_probation'
        ? 'action_required'
        : scenario === 'active' || scenario === 'restricted'
          ? 'complete'
          : 'under_review',
      ownerRole: 'support_manager',
      notes: ['Support ownership must be explicit before storefront launch', 'Escalation path stays visible in legal and cases surfaces'],
    });
  }

  if (primaryLane === 'creator_affiliate') {
    baseTasks.push({
      id: 'creative-approval',
      kind: 'creative_approval',
      status: scenario === 'restricted'
        ? 'blocked'
        : scenario === 'approved_probation'
          ? 'under_review'
          : 'complete',
      ownerRole: 'support_manager',
      notes: ['Creator approvals are lighter-weight but still governed', 'Templates help prevent claims drift on public channels'],
    });
  }

  return baseTasks;
}

function buildScenarioAnalyticsMetrics(
  scenario: PartnerPortalScenario,
  primaryLane: PartnerPrimaryLane | '',
): PartnerAnalyticsMetric[] {
  if (
    !primaryLane
    || scenario === 'draft'
    || scenario === 'needs_info'
    || scenario === 'under_review'
    || scenario === 'waitlisted'
  ) {
    return [];
  }

  const values = primaryLane === 'creator_affiliate'
    ? scenario === 'approved_probation'
      ? ['12.4k', '680', '72', '18', '4.1%', '0.3%', '$320']
      : scenario === 'active'
        ? ['28.7k', '1,530', '220', '96', '3.6%', '0.4%', '$1,840']
        : ['28.7k', '1,530', '214', '96', '5.9%', '0.6%', '$410']
    : primaryLane === 'performance_media'
      ? scenario === 'approved_probation'
        ? ['34.2k', '2,400', '118', '14', '2.8%', '0.7%', '$210']
        : scenario === 'active'
          ? ['128k', '8,740', '640', '188', '2.5%', '0.8%', '$6,920']
          : ['128k', '8,740', '611', '188', '4.4%', '1.1%', '$980']
      : scenario === 'approved_probation'
        ? ['640', '52', '18', '6', '1.3%', '0.1%', '$540']
        : scenario === 'active'
          ? ['3.8k', '290', '92', '44', '1.1%', '0.1%', '$4,780']
          : ['3.8k', '290', '90', '44', '1.9%', '0.1%', '$1,120'];

  const trends: PartnerAnalyticsMetricTrend[] = scenario === 'restricted'
    ? ['steady', 'steady', 'down', 'steady', 'down', 'down', 'down']
    : scenario === 'approved_probation'
      ? ['up', 'up', 'up', 'steady', 'steady', 'steady', 'up']
      : ['up', 'up', 'up', 'up', 'steady', 'steady', 'up'];

  const notes = scenario === 'restricted'
    ? ['Current metric remains visible, but the workspace is operating under restrictions.']
    : scenario === 'approved_probation'
      ? ['Probation reporting stays visible with lighter KPI depth and export scope.']
      : ['Metric definition remains canonical across partner and finance reporting.'];

  const keys: PartnerAnalyticsMetricKey[] = [
    'clicks',
    'registrations',
    'first_paid',
    'repeat_paid',
    'refund_rate',
    'chargeback_rate',
    'earnings_available',
  ];

  return keys.map((key, index) => ({
    key,
    value: values[index],
    trend: trends[index],
    notes,
  }));
}

function buildScenarioReportExports(
  scenario: PartnerPortalScenario,
  primaryLane: PartnerPrimaryLane | '',
): PartnerReportExport[] {
  if (
    !primaryLane
    || scenario === 'draft'
    || scenario === 'needs_info'
    || scenario === 'under_review'
    || scenario === 'waitlisted'
  ) {
    return [];
  }

  const baseExports: PartnerReportExport[] = [
    {
      id: 'code-report',
      kind: 'code_report',
      status: scenario === 'restricted' ? 'available' : 'available',
      cadence: 'Daily',
      notes: ['Code-level visibility stays scoped to the workspace.', 'Use this export for channel or owner-level reconciliation.'],
    },
    {
      id: 'statement-export',
      kind: 'statement_export',
      status: scenario === 'approved_probation' ? 'scheduled' : scenario === 'restricted' ? 'available' : 'available',
      cadence: 'Per settlement period',
      notes: ['Statement exports follow finance readiness and settlement windows.', 'Historical exports remain visible in constrained states.'],
    },
    {
      id: 'payout-status',
      kind: 'payout_status_export',
      status: scenario === 'approved_probation' ? 'blocked' : scenario === 'restricted' ? 'available' : 'available',
      cadence: 'On demand',
      notes: ['Payout-status exports stay blocked until finance readiness allows settlement visibility.', 'Does not grant payout execution control.'],
    },
    {
      id: 'explainability',
      kind: 'explainability_report',
      status: scenario === 'restricted' ? 'available' : 'available',
      cadence: 'On demand',
      notes: ['Explainability is partner-facing, not a raw internal moderation feed.', 'Use it to understand attribution and payout availability changes.'],
    },
  ];

  if (primaryLane !== 'reseller_api') {
    baseExports.splice(1, 0, {
      id: 'geo-report',
      kind: 'geo_report',
      status: scenario === 'approved_probation' && primaryLane === 'creator_affiliate'
        ? 'scheduled'
        : 'available',
      cadence: 'Weekly',
      notes: ['Geo/source rollups align with partner reporting definitions.', 'Available before conversions/customers surfaces arrive in PP6.'],
    });
  }

  return baseExports;
}

function buildScenarioFinanceStatements(
  scenario: PartnerPortalScenario,
  primaryLane: PartnerPrimaryLane | '',
): PartnerFinanceStatement[] {
  if (
    !primaryLane
    || scenario === 'draft'
    || scenario === 'needs_info'
    || scenario === 'under_review'
    || scenario === 'waitlisted'
  ) {
    return [];
  }

  const probationStatement: PartnerFinanceStatement = {
    id: '2026-04-probation',
    periodLabel: 'April 2026 probation period',
    status: 'on_hold',
    gross: primaryLane === 'performance_media' ? '$940' : primaryLane === 'reseller_api' ? '$1,180' : '$520',
    net: primaryLane === 'performance_media' ? '$780' : primaryLane === 'reseller_api' ? '$1,020' : '$440',
    available: '$0',
    onHold: primaryLane === 'performance_media' ? '$780' : primaryLane === 'reseller_api' ? '$1,020' : '$440',
    currency: 'USD',
    notes: ['Probation earnings remain visible.', 'Release depends on finance readiness and quality review.'],
  };

  const activeReadyStatement: PartnerFinanceStatement = {
    id: '2026-03-settlement',
    periodLabel: 'March 2026 settlement period',
    status: 'ready',
    gross: primaryLane === 'performance_media' ? '$8,920' : primaryLane === 'reseller_api' ? '$6,140' : '$2,210',
    net: primaryLane === 'performance_media' ? '$7,340' : primaryLane === 'reseller_api' ? '$5,410' : '$1,840',
    available: primaryLane === 'performance_media' ? '$6,920' : primaryLane === 'reseller_api' ? '$4,780' : '$1,840',
    onHold: primaryLane === 'performance_media' ? '$420' : primaryLane === 'reseller_api' ? '$290' : '$120',
    currency: 'USD',
    notes: ['Ready statement remains visible until payout execution occurs.', 'Adjustments and reserves stay explainable, not editable.'],
  };

  const activePaidStatement: PartnerFinanceStatement = {
    id: '2026-02-settlement',
    periodLabel: 'February 2026 settlement period',
    status: 'paid',
    gross: primaryLane === 'performance_media' ? '$7,880' : primaryLane === 'reseller_api' ? '$5,320' : '$1,740',
    net: primaryLane === 'performance_media' ? '$6,940' : primaryLane === 'reseller_api' ? '$4,860' : '$1,520',
    available: '$0',
    onHold: '$0',
    currency: 'USD',
    notes: ['Historical statement remains visible after payout.', 'Partner-side visibility never exposes internal payout execution controls.'],
  };

  if (scenario === 'approved_probation') {
    return [probationStatement];
  }

  if (scenario === 'active') {
    return [activeReadyStatement, activePaidStatement];
  }

  return [
    {
      ...activeReadyStatement,
      id: '2026-03-restricted',
      status: 'blocked',
      available: '$0',
      onHold: primaryLane === 'performance_media' ? '$1,260' : primaryLane === 'reseller_api' ? '$710' : '$480',
      notes: ['Statement remains visible in restricted state.', 'Payout-bearing actions are blocked until finance or governance issues are resolved.'],
    },
    activePaidStatement,
  ];
}

function buildScenarioPayoutAccounts(
  scenario: PartnerPortalScenario,
  primaryLane: PartnerPrimaryLane | '',
): PartnerPayoutAccount[] {
  if (
    !primaryLane
    || scenario === 'draft'
    || scenario === 'needs_info'
    || scenario === 'under_review'
    || scenario === 'waitlisted'
  ) {
    return [];
  }

  if (scenario === 'approved_probation') {
    return [
      {
        id: 'primary-payout',
        label: primaryLane === 'reseller_api' ? 'Distribution settlement account' : 'Primary settlement account',
        kind: primaryLane === 'reseller_api' ? 'invoice_profile' : 'bank_account',
        status: 'pending_review',
        currency: 'USD',
        isDefault: true,
        notes: ['Finance onboarding is still in progress.', 'Partner can see setup posture, but payout execution is not available.'],
      },
    ];
  }

  if (scenario === 'active') {
    return [
      {
        id: 'primary-payout',
        label: primaryLane === 'performance_media'
          ? 'Performance settlement account'
          : primaryLane === 'reseller_api'
            ? 'Distribution invoice profile'
            : 'Creator settlement account',
        kind: primaryLane === 'reseller_api' ? 'invoice_profile' : 'bank_account',
        status: 'ready',
        currency: 'USD',
        isDefault: true,
        notes: ['Default settlement destination is configured.', 'Changing payout ownership remains owner-sensitive.'],
      },
      {
        id: 'secondary-wallet',
        label: 'Secondary crypto wallet',
        kind: 'crypto_wallet',
        status: primaryLane === 'reseller_api' ? 'blocked' : 'pending_review',
        currency: 'USDT',
        isDefault: false,
        notes: ['Secondary payout routes remain more tightly controlled.', 'Availability depends on policy and finance validation.'],
      },
    ];
  }

  return [
    {
      id: 'primary-payout',
      label: primaryLane === 'reseller_api' ? 'Distribution invoice profile' : 'Primary settlement account',
      kind: primaryLane === 'reseller_api' ? 'invoice_profile' : 'bank_account',
      status: 'blocked',
      currency: 'USD',
      isDefault: true,
      notes: ['The payout destination remains visible.', 'Editing and payout-bearing actions stay blocked in the current state.'],
    },
  ];
}

function buildScenarioFinanceSnapshot(
  scenario: PartnerPortalScenario,
  primaryLane: PartnerPrimaryLane | '',
): PartnerFinanceSnapshot {
  if (
    !primaryLane
    || scenario === 'draft'
    || scenario === 'needs_info'
    || scenario === 'under_review'
    || scenario === 'waitlisted'
  ) {
    return {
      availableEarnings: '$0',
      onHoldEarnings: '$0',
      reserves: '$0',
      nextPayoutForecast: '$0',
      currency: 'USD',
    };
  }

  if (primaryLane === 'creator_affiliate') {
    return scenario === 'approved_probation'
      ? { availableEarnings: '$0', onHoldEarnings: '$440', reserves: '$80', nextPayoutForecast: '$320', currency: 'USD' }
      : scenario === 'active'
        ? { availableEarnings: '$1,840', onHoldEarnings: '$120', reserves: '$140', nextPayoutForecast: '$1,520', currency: 'USD' }
        : { availableEarnings: '$0', onHoldEarnings: '$480', reserves: '$220', nextPayoutForecast: '$0', currency: 'USD' };
  }

  if (primaryLane === 'performance_media') {
    return scenario === 'approved_probation'
      ? { availableEarnings: '$0', onHoldEarnings: '$780', reserves: '$160', nextPayoutForecast: '$210', currency: 'USD' }
      : scenario === 'active'
        ? { availableEarnings: '$6,920', onHoldEarnings: '$420', reserves: '$820', nextPayoutForecast: '$6,100', currency: 'USD' }
        : { availableEarnings: '$0', onHoldEarnings: '$1,260', reserves: '$1,080', nextPayoutForecast: '$0', currency: 'USD' };
  }

  return scenario === 'approved_probation'
    ? { availableEarnings: '$0', onHoldEarnings: '$1,020', reserves: '$180', nextPayoutForecast: '$540', currency: 'USD' }
    : scenario === 'active'
      ? { availableEarnings: '$4,780', onHoldEarnings: '$290', reserves: '$360', nextPayoutForecast: '$4,120', currency: 'USD' }
      : { availableEarnings: '$0', onHoldEarnings: '$710', reserves: '$480', nextPayoutForecast: '$0', currency: 'USD' };
}

function buildScenarioConversionRecords(
  scenario: PartnerPortalScenario,
  primaryLane: PartnerPrimaryLane | '',
): PartnerConversionRecord[] {
  if (
    !primaryLane
    || scenario === 'draft'
    || scenario === 'needs_info'
    || scenario === 'under_review'
    || scenario === 'waitlisted'
  ) {
    return [];
  }

  if (primaryLane === 'creator_affiliate') {
    if (scenario === 'approved_probation') {
      return [
        {
          id: 'creator-probation-registration',
          kind: 'registration',
          status: 'commissionable',
          orderLabel: 'REG-24018',
          customerLabel: 'masked-user-71',
          codeLabel: 'OZOXY-START',
          geo: 'DE',
          amount: '$0',
          customerScope: 'masked',
          updatedAt: DEFAULT_DATE,
          notes: ['Starter attribution is visible during probation.', 'Customer identity remains masked for creator lanes.'],
        },
        {
          id: 'creator-probation-first-paid',
          kind: 'first_paid',
          status: 'on_hold',
          orderLabel: 'ORD-24018',
          customerLabel: 'masked-user-71',
          codeLabel: 'OZOXY-START',
          geo: 'DE',
          amount: '$120',
          customerScope: 'masked',
          updatedAt: DEFAULT_DATE,
          notes: ['First paid conversion is visible but still on hold.', 'Release depends on probation quality checks and finance readiness.'],
        },
      ];
    }

    if (scenario === 'active') {
      return [
        {
          id: 'creator-active-registration',
          kind: 'registration',
          status: 'commissionable',
          orderLabel: 'REG-24190',
          customerLabel: 'masked-user-84',
          codeLabel: 'OZOXY-START',
          geo: 'US',
          amount: '$0',
          customerScope: 'masked',
          updatedAt: DEFAULT_DATE,
          notes: ['Registration attribution is stable.', 'Explainability remains available by code and geo.'],
        },
        {
          id: 'creator-active-first-paid',
          kind: 'first_paid',
          status: 'commissionable',
          orderLabel: 'ORD-24190',
          customerLabel: 'masked-user-84',
          codeLabel: 'OZOXY-START',
          geo: 'US',
          amount: '$180',
          customerScope: 'masked',
          updatedAt: DEFAULT_DATE,
          notes: ['First paid conversion is commissionable.', 'Customer row scope remains masked in creator lanes.'],
        },
        {
          id: 'creator-active-repeat-paid',
          kind: 'repeat_paid',
          status: 'commissionable',
          orderLabel: 'ORD-24011-R2',
          customerLabel: 'masked-user-21',
          codeLabel: 'SPRING-QR',
          geo: 'GB',
          amount: '$94',
          customerScope: 'masked',
          updatedAt: DEFAULT_DATE,
          notes: ['Renewal attribution is visible in the partner surface.', 'Use analytics and cases for explainability or disputes.'],
        },
      ];
    }

    return [
      {
        id: 'creator-restricted-first-paid',
        kind: 'first_paid',
        status: 'on_hold',
        orderLabel: 'ORD-24190',
        customerLabel: 'masked-user-84',
        codeLabel: 'OZOXY-START',
        geo: 'US',
        amount: '$180',
        customerScope: 'masked',
        updatedAt: DEFAULT_DATE,
        notes: ['This conversion remains visible while finance or governance issues are remediated.', 'Partner can inspect explainability but not expand launch scope.'],
      },
      {
        id: 'creator-restricted-refund',
        kind: 'refund',
        status: 'reversed',
        orderLabel: 'ORD-24011-R2',
        customerLabel: 'masked-user-21',
        codeLabel: 'SPRING-QR',
        geo: 'GB',
        amount: '-$94',
        customerScope: 'masked',
        updatedAt: DEFAULT_DATE,
        notes: ['Refund visibility stays partner-facing.', 'Line-item detail is visible without exposing internal override controls.'],
      },
    ];
  }

  if (primaryLane === 'performance_media') {
    if (scenario === 'approved_probation') {
      return [
        {
          id: 'performance-probation-registration',
          kind: 'registration',
          status: 'commissionable',
          orderLabel: 'CLK-8031',
          customerLabel: 'workspace-user-443',
          codeLabel: 'MEDIA-LAUNCH',
          geo: 'BR',
          amount: '$0',
          customerScope: 'workspace_scoped',
          updatedAt: DEFAULT_DATE,
          notes: ['Declared click and geo context are visible during probation.', 'Use this record to validate early funnel quality.'],
        },
        {
          id: 'performance-probation-first-paid',
          kind: 'first_paid',
          status: 'on_hold',
          orderLabel: 'ORD-8031',
          customerLabel: 'workspace-user-443',
          codeLabel: 'MEDIA-LAUNCH',
          geo: 'BR',
          amount: '$210',
          customerScope: 'workspace_scoped',
          updatedAt: DEFAULT_DATE,
          notes: ['Performance launch remains governed.', 'Click ID and commissionability context stay visible for explainability.'],
        },
      ];
    }

    if (scenario === 'active') {
      return [
        {
          id: 'performance-active-first-paid',
          kind: 'first_paid',
          status: 'commissionable',
          orderLabel: 'ORD-88014',
          customerLabel: 'workspace-user-810',
          codeLabel: 'MEDIA-LAUNCH',
          geo: 'US',
          amount: '$390',
          customerScope: 'workspace_scoped',
          updatedAt: DEFAULT_DATE,
          notes: ['Sub ID and click-path explainability remain available.', 'Commissionability is aligned with active finance posture.'],
        },
        {
          id: 'performance-active-repeat-paid',
          kind: 'repeat_paid',
          status: 'commissionable',
          orderLabel: 'ORD-88014-R2',
          customerLabel: 'workspace-user-810',
          codeLabel: 'LOOKALIKE-SET-B',
          geo: 'US',
          amount: '$160',
          customerScope: 'workspace_scoped',
          updatedAt: DEFAULT_DATE,
          notes: ['Repeat-paid visibility supports quality and retention investigation.', 'Disputes stay in cases, not inside raw ops tooling.'],
        },
        {
          id: 'performance-active-chargeback',
          kind: 'chargeback',
          status: 'rejected',
          orderLabel: 'ORD-77310',
          customerLabel: 'workspace-user-199',
          codeLabel: 'MEDIA-ALT',
          geo: 'CA',
          amount: '-$240',
          customerScope: 'workspace_scoped',
          updatedAt: DEFAULT_DATE,
          notes: ['Rejected or reversed items remain visible for investigation.', 'Use explainability and cases for follow-up.'],
        },
      ];
    }

    return [
      {
        id: 'performance-restricted-first-paid',
        kind: 'first_paid',
        status: 'on_hold',
        orderLabel: 'ORD-88014',
        customerLabel: 'workspace-user-810',
        codeLabel: 'MEDIA-LAUNCH',
        geo: 'US',
        amount: '$390',
        customerScope: 'workspace_scoped',
        updatedAt: DEFAULT_DATE,
        notes: ['The order remains visible while launch scope is constrained.', 'Partner-side row scope remains limited to the workspace.'],
      },
      {
        id: 'performance-restricted-chargeback',
        kind: 'chargeback',
        status: 'reversed',
        orderLabel: 'ORD-77310',
        customerLabel: 'workspace-user-199',
        codeLabel: 'MEDIA-ALT',
        geo: 'CA',
        amount: '-$240',
        customerScope: 'workspace_scoped',
        updatedAt: DEFAULT_DATE,
        notes: ['Chargeback and reversal context stay visible in restricted state.', 'Direct override tools remain internal-only.'],
      },
    ];
  }

  if (scenario === 'approved_probation') {
    return [
      {
        id: 'reseller-probation-first-paid',
        kind: 'first_paid',
        status: 'on_hold',
        orderLabel: 'SUB-5401',
        customerLabel: 'storefront-customer-12',
        codeLabel: 'DIST-START',
        geo: 'PL',
        amount: '$540',
        customerScope: 'storefront_scoped',
        updatedAt: DEFAULT_DATE,
        notes: ['Storefront-scoped customer visibility is available for reseller flows.', 'Settlement release remains governed during probation.'],
      },
    ];
  }

  if (scenario === 'active') {
    return [
      {
        id: 'reseller-active-first-paid',
        kind: 'first_paid',
        status: 'commissionable',
        orderLabel: 'SUB-6881',
        customerLabel: 'storefront-customer-44',
        codeLabel: 'DIST-EU',
        geo: 'DE',
        amount: '$880',
        customerScope: 'storefront_scoped',
        updatedAt: DEFAULT_DATE,
        notes: ['Reseller visibility includes storefront-scoped customer context.', 'Order ownership stays bound to storefront scope, not global platform access.'],
      },
      {
        id: 'reseller-active-repeat-paid',
        kind: 'repeat_paid',
        status: 'commissionable',
        orderLabel: 'SUB-6881-R2',
        customerLabel: 'storefront-customer-44',
        codeLabel: 'DIST-EU',
        geo: 'DE',
        amount: '$420',
        customerScope: 'storefront_scoped',
        updatedAt: DEFAULT_DATE,
        notes: ['Renewal visibility helps reseller-side support and billing context.', 'Customer scope stays limited to assigned storefronts.'],
      },
    ];
  }

  return [
    {
      id: 'reseller-restricted-first-paid',
      kind: 'first_paid',
      status: 'on_hold',
      orderLabel: 'SUB-6881',
      customerLabel: 'storefront-customer-44',
      codeLabel: 'DIST-EU',
      geo: 'DE',
      amount: '$880',
      customerScope: 'storefront_scoped',
      updatedAt: DEFAULT_DATE,
      notes: ['Storefront order history remains visible.', 'Settlement-bearing actions stay blocked until restrictions clear.'],
    },
    {
      id: 'reseller-restricted-refund',
      kind: 'refund',
      status: 'reversed',
      orderLabel: 'SUB-6881-R2',
      customerLabel: 'storefront-customer-44',
      codeLabel: 'DIST-EU',
      geo: 'DE',
      amount: '-$420',
      customerScope: 'storefront_scoped',
      updatedAt: DEFAULT_DATE,
      notes: ['Refund and support context remain visible to the reseller team.', 'Platform-wide moderation and overrides remain internal-only.'],
    },
  ];
}

function buildScenarioIntegrationCredentials(
  scenario: PartnerPortalScenario,
  primaryLane: PartnerPrimaryLane | '',
): PartnerIntegrationCredential[] {
  if (
    !primaryLane
    || scenario === 'draft'
    || scenario === 'needs_info'
    || scenario === 'under_review'
    || scenario === 'waitlisted'
    || scenario === 'approved_probation'
  ) {
    return [];
  }

  if (primaryLane === 'creator_affiliate') {
    return [
      {
        id: 'creator-reporting-token',
        label: 'Creator reporting token',
        kind: 'reporting_api_token',
        status: scenario === 'active' ? 'ready' : 'pending_rotation',
        lastRotatedAt: DEFAULT_DATE,
        notes: ['Selected creator programs can receive a reporting token.', 'This does not imply broader performance integrations.'],
      },
      {
        id: 'creator-webhook-secret',
        label: 'Creator webhook secret',
        kind: 'webhook_secret',
        status: scenario === 'active' ? 'pending_rotation' : 'blocked',
        lastRotatedAt: scenario === 'active' ? DEFAULT_DATE : null,
        notes: ['Webhook delivery remains narrower for creator lanes.', 'Activation depends on selected creator use cases.'],
      },
    ];
  }

  if (primaryLane === 'performance_media') {
    return [
      {
        id: 'performance-reporting-token',
        label: 'Performance reporting token',
        kind: 'reporting_api_token',
        status: scenario === 'active' ? 'ready' : 'pending_rotation',
        lastRotatedAt: DEFAULT_DATE,
        notes: ['Performance teams can export and reconcile reporting data.', 'Token rotation remains visible in the partner surface.'],
      },
      {
        id: 'performance-postback-secret',
        label: 'Postback credential',
        kind: 'postback_secret',
        status: scenario === 'active' ? 'ready' : 'blocked',
        lastRotatedAt: DEFAULT_DATE,
        notes: ['Postback and click diagnostics depend on technical readiness.', 'Restricted state keeps visibility but blocks rollout actions.'],
      },
      {
        id: 'performance-webhook-secret',
        label: 'Webhook secret',
        kind: 'webhook_secret',
        status: scenario === 'active' ? 'ready' : 'blocked',
        lastRotatedAt: DEFAULT_DATE,
        notes: ['Webhook delivery status is exposed without allowing unsafe internal overrides.', 'Use cases remain limited to workspace scope.'],
      },
    ];
  }

  return [
    {
      id: 'reseller-reporting-token',
      label: 'Distribution reporting token',
      kind: 'reporting_api_token',
      status: scenario === 'active' ? 'ready' : 'pending_rotation',
      lastRotatedAt: DEFAULT_DATE,
      notes: ['Reseller reporting remains storefront-scoped.', 'Cross-partner analytics visibility is never exposed.'],
    },
    {
      id: 'reseller-storefront-api',
      label: 'Storefront API key',
      kind: 'storefront_api_key',
      status: scenario === 'active' ? 'ready' : 'blocked',
      lastRotatedAt: DEFAULT_DATE,
      notes: ['Storefront API keys remain reseller-specific.', 'Availability depends on technical readiness and contract posture.'],
    },
    {
      id: 'reseller-webhook-secret',
      label: 'Reseller webhook secret',
      kind: 'webhook_secret',
      status: scenario === 'active' ? 'ready' : 'blocked',
      lastRotatedAt: DEFAULT_DATE,
      notes: ['Webhook delivery is constrained to assigned storefront scope.', 'Replay and diagnostics remain partner-facing only.'],
    },
  ];
}

function buildScenarioIntegrationDeliveryLogs(
  scenario: PartnerPortalScenario,
  primaryLane: PartnerPrimaryLane | '',
): PartnerIntegrationDeliveryLog[] {
  if (
    !primaryLane
    || scenario === 'draft'
    || scenario === 'needs_info'
    || scenario === 'under_review'
    || scenario === 'waitlisted'
    || scenario === 'approved_probation'
  ) {
    return [];
  }

  if (primaryLane === 'creator_affiliate') {
    return [
      {
        id: 'creator-reporting-export',
        channel: 'reporting_export',
        status: scenario === 'active' ? 'delivered' : 'paused',
        destination: 'analytics-export://creator-overview',
        lastAttemptAt: DEFAULT_DATE,
        notes: ['Creator export delivery remains selected-use-case only.', 'Restricted state pauses delivery expansion.'],
      },
      {
        id: 'creator-webhook',
        channel: 'webhook',
        status: scenario === 'active' ? 'failed' : 'paused',
        destination: 'https://creator.example.com/hooks/cybervpn',
        lastAttemptAt: DEFAULT_DATE,
        notes: ['Webhook diagnostics stay visible without exposing secret values.', 'Use cases remain conditional for creator lanes.'],
      },
    ];
  }

  if (primaryLane === 'performance_media') {
    return [
      {
        id: 'performance-postback',
        channel: 'postback',
        status: scenario === 'active' ? 'delivered' : 'paused',
        destination: 'https://tracker.example.com/postback',
        lastAttemptAt: DEFAULT_DATE,
        notes: ['Postback health remains a key PP6 control for performance.', 'Retries and replay are partner-visible, not internal override tools.'],
      },
      {
        id: 'performance-webhook',
        channel: 'webhook',
        status: scenario === 'active' ? 'failed' : 'paused',
        destination: 'https://ops.example.com/webhooks/cybervpn',
        lastAttemptAt: DEFAULT_DATE,
        notes: ['Failed webhook attempts remain visible for technical follow-up.', 'Lane restrictions can pause rollout while keeping logs visible.'],
      },
    ];
  }

  return [
    {
      id: 'reseller-reporting-export',
      channel: 'reporting_export',
      status: scenario === 'active' ? 'delivered' : 'paused',
      destination: 'analytics-export://reseller-storefront',
      lastAttemptAt: DEFAULT_DATE,
      notes: ['Reporting exports remain bound to reseller storefront scope.', 'No cross-storefront access is granted.'],
    },
    {
      id: 'reseller-webhook',
      channel: 'webhook',
      status: scenario === 'active' ? 'delivered' : 'failed',
      destination: 'https://reseller.example.com/hooks/storefront',
      lastAttemptAt: DEFAULT_DATE,
      notes: ['Storefront callback health is visible for partner-side diagnostics.', 'Restricted posture keeps delivery visible but constrained.'],
    },
  ];
}

function buildScenarioResellerStorefronts(
  scenario: PartnerPortalScenario,
  primaryLane: PartnerPrimaryLane | '',
): PartnerResellerStorefront[] {
  if (
    primaryLane !== 'reseller_api'
    || scenario === 'draft'
    || scenario === 'needs_info'
    || scenario === 'under_review'
    || scenario === 'waitlisted'
    || scenario === 'approved_probation'
  ) {
    return [];
  }

  if (scenario === 'active') {
    return [
      {
        id: 'reseller-eu-storefront',
        label: 'CyberVPN EU Distribution',
        domain: 'vpn.example-distribution.eu',
        status: 'ready',
        currency: 'EUR',
        supportOwner: 'Reseller L1 / CyberVPN L2',
        notes: ['Assigned storefront is active.', 'Customer and order scope remain limited to this distribution surface.'],
      },
      {
        id: 'reseller-apac-storefront',
        label: 'CyberVPN APAC Privacy Hub',
        domain: 'privacyhub.example-asia.com',
        status: 'in_review',
        currency: 'USD',
        supportOwner: 'Reseller L1 / CyberVPN L2',
        notes: ['Second storefront remains in rollout review.', 'Domain and support ownership are visible before expansion.'],
      },
    ];
  }

  return [
    {
      id: 'reseller-eu-storefront',
      label: 'CyberVPN EU Distribution',
      domain: 'vpn.example-distribution.eu',
      status: 'restricted',
      currency: 'EUR',
      supportOwner: 'Reseller L1 / CyberVPN L2',
      notes: ['Storefront remains visible during remediation.', 'Launch expansion is blocked until the restriction clears.'],
    },
  ];
}

function buildScenarioResellerSnapshot(
  scenario: PartnerPortalScenario,
  primaryLane: PartnerPrimaryLane | '',
): PartnerResellerConsoleSnapshot {
  if (primaryLane !== 'reseller_api') {
    return {
      pricebookLabel: '',
      supportOwnership: '',
      customerScope: '',
      technicalHealth: '',
    };
  }

  if (scenario === 'active') {
    return {
      pricebookLabel: 'EU + APAC reseller pricebook preview',
      supportOwnership: 'Reseller-owned L1 support with CyberVPN L2 escalation',
      customerScope: 'Storefront-scoped customer and order visibility',
      technicalHealth: 'Storefront API and callback delivery nominal',
    };
  }

  if (scenario === 'restricted') {
    return {
      pricebookLabel: 'EU reseller pricebook preview only',
      supportOwnership: 'Support ownership remains visible during remediation',
      customerScope: 'Storefront-scoped customer history remains readable',
      technicalHealth: 'One storefront remains restricted pending technical or governance follow-up',
    };
  }

  return {
    pricebookLabel: '',
    supportOwnership: '',
    customerScope: '',
    technicalHealth: '',
  };
}

function buildScenarioReviewRequests(
  scenario: PartnerPortalScenario,
  primaryLane: PartnerPrimaryLane | '',
): PartnerReviewRequest[] {
  if (scenario === 'needs_info') {
    return [
      {
        id: 'business-profile',
        kind: 'business_profile',
        dueDate: DEFAULT_DUE_DATE,
        status: 'open',
      },
      {
        id: 'owned-channels',
        kind: primaryLane === 'reseller_api' ? 'support_ownership' : 'owned_channels',
        dueDate: DEFAULT_DUE_DATE,
        status: 'open',
      },
      {
        id: 'traffic-methods',
        kind: primaryLane === 'creator_affiliate' ? 'traffic_methods' : 'finance_profile',
        dueDate: DEFAULT_DUE_DATE,
        status: 'open',
      },
    ];
  }

  if (scenario === 'under_review' || scenario === 'waitlisted') {
    return [
      {
        id: 'business-profile',
        kind: 'business_profile',
        dueDate: DEFAULT_DUE_DATE,
        status: 'submitted',
      },
    ];
  }

  if (scenario === 'approved_probation') {
    return [
      {
        id: 'finance-profile',
        kind: 'finance_profile',
        dueDate: DEFAULT_DUE_DATE,
        status: 'open',
      },
    ];
  }

  return [];
}

function buildScenarioCases(
  scenario: PartnerPortalScenario,
  primaryLane: PartnerPrimaryLane | '',
): PartnerPortalCase[] {
  if (scenario === 'draft') {
    return [
      {
        id: 'application-draft',
        kind: 'application_review',
        status: 'waiting_on_partner',
        updatedAt: DEFAULT_DATE,
      },
    ];
  }

  if (scenario === 'needs_info') {
    return [
      {
        id: 'requested-info',
        kind: 'requested_info',
        status: 'waiting_on_partner',
        updatedAt: DEFAULT_DATE,
      },
      {
        id: 'application-review',
        kind: 'application_review',
        status: 'open',
        updatedAt: DEFAULT_DATE,
      },
    ];
  }

  if (scenario === 'under_review' || scenario === 'waitlisted') {
    return [
      {
        id: 'application-review',
        kind: 'application_review',
        status: 'waiting_on_ops',
        updatedAt: DEFAULT_DATE,
      },
    ];
  }

  if (scenario === 'approved_probation') {
    return [
      {
        id: 'finance-onboarding',
        kind: 'finance_onboarding',
        status: 'waiting_on_partner',
        updatedAt: DEFAULT_DATE,
      },
      {
        id: 'compliance-followup',
        kind: 'compliance_followup',
        status: 'open',
        updatedAt: DEFAULT_DATE,
      },
      {
        id: primaryLane === 'performance_media' ? 'performance-technical' : 'probation-support',
        kind: primaryLane === 'performance_media' ? 'technical_support' : 'statement_question',
        status: primaryLane === 'performance_media' ? 'waiting_on_partner' : 'waiting_on_ops',
        updatedAt: DEFAULT_DATE,
      },
    ];
  }

  if (scenario === 'active') {
    return [
      {
        id: 'application-review',
        kind: 'application_review',
        status: 'resolved',
        updatedAt: DEFAULT_DATE,
      },
      {
        id: 'attribution-dispute',
        kind: 'attribution_dispute',
        status: primaryLane === 'creator_affiliate' ? 'waiting_on_ops' : 'open',
        updatedAt: DEFAULT_DATE,
      },
      {
        id: primaryLane === 'reseller_api' ? 'support-escalation' : 'statement-question',
        kind: primaryLane === 'reseller_api' ? 'technical_support' : 'statement_question',
        status: 'open',
        updatedAt: DEFAULT_DATE,
      },
    ];
  }

  return [
    {
      id: 'restriction-notice',
      kind: 'restriction_notice',
      status: 'waiting_on_partner',
      updatedAt: DEFAULT_DATE,
    },
    {
      id: 'finance-onboarding',
      kind: 'finance_onboarding',
      status: 'open',
      updatedAt: DEFAULT_DATE,
    },
    {
      id: 'payout-dispute',
      kind: 'payout_dispute',
      status: 'waiting_on_ops',
      updatedAt: DEFAULT_DATE,
    },
    {
      id: 'attribution-dispute',
      kind: 'attribution_dispute',
      status: 'open',
      updatedAt: DEFAULT_DATE,
    },
  ];
}

function buildScenarioNotifications(
  scenario: PartnerPortalScenario,
): PartnerPortalNotification[] {
  if (scenario === 'draft') {
    return [
      {
        id: 'workspace-draft',
        kind: 'workspace_draft',
        tone: 'info',
        createdAt: DEFAULT_DATE,
        unread: true,
      },
    ];
  }

  if (scenario === 'needs_info') {
    return [
      {
        id: 'application-submitted',
        kind: 'application_submitted',
        tone: 'info',
        createdAt: DEFAULT_DATE,
        unread: false,
      },
      {
        id: 'needs-info',
        kind: 'needs_info',
        tone: 'warning',
        createdAt: DEFAULT_DATE,
        unread: true,
      },
    ];
  }

  if (scenario === 'under_review') {
    return [
      {
        id: 'review-in-progress',
        kind: 'review_in_progress',
        tone: 'info',
        createdAt: DEFAULT_DATE,
        unread: true,
      },
    ];
  }

  if (scenario === 'waitlisted') {
    return [
      {
        id: 'waitlisted',
        kind: 'waitlisted',
        tone: 'warning',
        createdAt: DEFAULT_DATE,
        unread: true,
      },
    ];
  }

  if (scenario === 'approved_probation') {
    return [
      {
        id: 'probation-started',
        kind: 'probation_started',
        tone: 'success',
        createdAt: DEFAULT_DATE,
        unread: true,
      },
      {
        id: 'payout-profile-needed',
        kind: 'payout_profile_needed',
        tone: 'info',
        createdAt: DEFAULT_DATE,
        unread: true,
      },
    ];
  }

  if (scenario === 'active') {
    return [
      {
        id: 'workspace-active',
        kind: 'workspace_active',
        tone: 'success',
        createdAt: DEFAULT_DATE,
        unread: true,
      },
    ];
  }

  return [
    {
      id: 'workspace-restricted',
      kind: 'workspace_restricted',
      tone: 'critical',
      createdAt: DEFAULT_DATE,
      unread: true,
    },
    {
      id: 'finance-blocked',
      kind: 'finance_blocked',
      tone: 'warning',
      createdAt: DEFAULT_DATE,
      unread: true,
    },
  ];
}

export function createPartnerPortalScenarioState(
  scenario: PartnerPortalScenario,
  primaryLane: PartnerPrimaryLane | '' = '',
  workspaceRole: PartnerWorkspaceRole = 'workspace_owner',
  releaseRing: PartnerReleaseRing = derivePartnerReleaseRing(scenario, primaryLane),
): PartnerPortalState {
  if (scenario === 'draft') {
    return {
      scenario,
      workspaceRole,
      releaseRing,
      primaryLane,
      workspaceStatus: 'draft',
      financeReadiness: 'not_started',
      complianceReadiness: 'not_started',
      technicalReadiness: getLaneTechnicalBaseline(primaryLane),
      governanceState: 'clear',
      teamMembers: buildScenarioTeamMembers(scenario, primaryLane),
      laneMemberships: buildScenarioLaneMemberships(scenario, primaryLane),
      legalDocuments: buildScenarioLegalDocuments(scenario, primaryLane),
      codes: buildScenarioCodes(scenario, primaryLane),
      campaignAssets: buildScenarioCampaignAssets(scenario, primaryLane),
      complianceTasks: buildScenarioComplianceTasks(scenario, primaryLane),
      analyticsMetrics: buildScenarioAnalyticsMetrics(scenario, primaryLane),
      reportExports: buildScenarioReportExports(scenario, primaryLane),
      financeStatements: buildScenarioFinanceStatements(scenario, primaryLane),
      payoutAccounts: buildScenarioPayoutAccounts(scenario, primaryLane),
      financeSnapshot: buildScenarioFinanceSnapshot(scenario, primaryLane),
      conversionRecords: buildScenarioConversionRecords(scenario, primaryLane),
      integrationCredentials: buildScenarioIntegrationCredentials(scenario, primaryLane),
      integrationDeliveryLogs: buildScenarioIntegrationDeliveryLogs(scenario, primaryLane),
      resellerStorefronts: buildScenarioResellerStorefronts(scenario, primaryLane),
      resellerSnapshot: buildScenarioResellerSnapshot(scenario, primaryLane),
      reviewRequests: [],
      cases: buildScenarioCases(scenario, primaryLane),
      notifications: buildScenarioNotifications(scenario),
      updatedAt: DEFAULT_DATE,
    };
  }

  if (scenario === 'needs_info') {
    return {
      scenario,
      workspaceRole,
      releaseRing,
      primaryLane,
      workspaceStatus: 'needs_info',
      financeReadiness: 'not_started',
      complianceReadiness: 'evidence_requested',
      technicalReadiness: getLaneTechnicalBaseline(primaryLane),
      governanceState: 'watch',
      teamMembers: buildScenarioTeamMembers(scenario, primaryLane),
      laneMemberships: buildScenarioLaneMemberships(scenario, primaryLane),
      legalDocuments: buildScenarioLegalDocuments(scenario, primaryLane),
      codes: buildScenarioCodes(scenario, primaryLane),
      campaignAssets: buildScenarioCampaignAssets(scenario, primaryLane),
      complianceTasks: buildScenarioComplianceTasks(scenario, primaryLane),
      analyticsMetrics: buildScenarioAnalyticsMetrics(scenario, primaryLane),
      reportExports: buildScenarioReportExports(scenario, primaryLane),
      financeStatements: buildScenarioFinanceStatements(scenario, primaryLane),
      payoutAccounts: buildScenarioPayoutAccounts(scenario, primaryLane),
      financeSnapshot: buildScenarioFinanceSnapshot(scenario, primaryLane),
      conversionRecords: buildScenarioConversionRecords(scenario, primaryLane),
      integrationCredentials: buildScenarioIntegrationCredentials(scenario, primaryLane),
      integrationDeliveryLogs: buildScenarioIntegrationDeliveryLogs(scenario, primaryLane),
      resellerStorefronts: buildScenarioResellerStorefronts(scenario, primaryLane),
      resellerSnapshot: buildScenarioResellerSnapshot(scenario, primaryLane),
      reviewRequests: buildScenarioReviewRequests(scenario, primaryLane),
      cases: buildScenarioCases(scenario, primaryLane),
      notifications: buildScenarioNotifications(scenario),
      updatedAt: DEFAULT_DATE,
    };
  }

  if (scenario === 'under_review') {
    return {
      scenario,
      workspaceRole,
      releaseRing,
      primaryLane,
      workspaceStatus: 'under_review',
      financeReadiness: 'not_started',
      complianceReadiness: 'declarations_complete',
      technicalReadiness: getLaneTechnicalBaseline(primaryLane),
      governanceState: 'watch',
      teamMembers: buildScenarioTeamMembers(scenario, primaryLane),
      laneMemberships: buildScenarioLaneMemberships(scenario, primaryLane),
      legalDocuments: buildScenarioLegalDocuments(scenario, primaryLane),
      codes: buildScenarioCodes(scenario, primaryLane),
      campaignAssets: buildScenarioCampaignAssets(scenario, primaryLane),
      complianceTasks: buildScenarioComplianceTasks(scenario, primaryLane),
      analyticsMetrics: buildScenarioAnalyticsMetrics(scenario, primaryLane),
      reportExports: buildScenarioReportExports(scenario, primaryLane),
      financeStatements: buildScenarioFinanceStatements(scenario, primaryLane),
      payoutAccounts: buildScenarioPayoutAccounts(scenario, primaryLane),
      financeSnapshot: buildScenarioFinanceSnapshot(scenario, primaryLane),
      conversionRecords: buildScenarioConversionRecords(scenario, primaryLane),
      integrationCredentials: buildScenarioIntegrationCredentials(scenario, primaryLane),
      integrationDeliveryLogs: buildScenarioIntegrationDeliveryLogs(scenario, primaryLane),
      resellerStorefronts: buildScenarioResellerStorefronts(scenario, primaryLane),
      resellerSnapshot: buildScenarioResellerSnapshot(scenario, primaryLane),
      reviewRequests: buildScenarioReviewRequests(scenario, primaryLane),
      cases: buildScenarioCases(scenario, primaryLane),
      notifications: buildScenarioNotifications(scenario),
      updatedAt: DEFAULT_DATE,
    };
  }

  if (scenario === 'waitlisted') {
    return {
      scenario,
      workspaceRole,
      releaseRing,
      primaryLane,
      workspaceStatus: 'waitlisted',
      financeReadiness: 'not_started',
      complianceReadiness: 'declarations_complete',
      technicalReadiness: getLaneTechnicalBaseline(primaryLane),
      governanceState: 'warning',
      teamMembers: buildScenarioTeamMembers(scenario, primaryLane),
      laneMemberships: buildScenarioLaneMemberships(scenario, primaryLane),
      legalDocuments: buildScenarioLegalDocuments(scenario, primaryLane),
      codes: buildScenarioCodes(scenario, primaryLane),
      campaignAssets: buildScenarioCampaignAssets(scenario, primaryLane),
      complianceTasks: buildScenarioComplianceTasks(scenario, primaryLane),
      analyticsMetrics: buildScenarioAnalyticsMetrics(scenario, primaryLane),
      reportExports: buildScenarioReportExports(scenario, primaryLane),
      financeStatements: buildScenarioFinanceStatements(scenario, primaryLane),
      payoutAccounts: buildScenarioPayoutAccounts(scenario, primaryLane),
      financeSnapshot: buildScenarioFinanceSnapshot(scenario, primaryLane),
      conversionRecords: buildScenarioConversionRecords(scenario, primaryLane),
      integrationCredentials: buildScenarioIntegrationCredentials(scenario, primaryLane),
      integrationDeliveryLogs: buildScenarioIntegrationDeliveryLogs(scenario, primaryLane),
      resellerStorefronts: buildScenarioResellerStorefronts(scenario, primaryLane),
      resellerSnapshot: buildScenarioResellerSnapshot(scenario, primaryLane),
      reviewRequests: buildScenarioReviewRequests(scenario, primaryLane),
      cases: buildScenarioCases(scenario, primaryLane),
      notifications: buildScenarioNotifications(scenario),
      updatedAt: DEFAULT_DATE,
    };
  }

  if (scenario === 'approved_probation') {
    return {
      scenario,
      workspaceRole,
      releaseRing,
      primaryLane,
      workspaceStatus: 'approved_probation',
      financeReadiness: 'in_progress',
      complianceReadiness: 'approved',
      technicalReadiness: getLaneTechnicalBaseline(primaryLane),
      governanceState: 'clear',
      teamMembers: buildScenarioTeamMembers(scenario, primaryLane),
      laneMemberships: buildScenarioLaneMemberships(scenario, primaryLane),
      legalDocuments: buildScenarioLegalDocuments(scenario, primaryLane),
      codes: buildScenarioCodes(scenario, primaryLane),
      campaignAssets: buildScenarioCampaignAssets(scenario, primaryLane),
      complianceTasks: buildScenarioComplianceTasks(scenario, primaryLane),
      analyticsMetrics: buildScenarioAnalyticsMetrics(scenario, primaryLane),
      reportExports: buildScenarioReportExports(scenario, primaryLane),
      financeStatements: buildScenarioFinanceStatements(scenario, primaryLane),
      payoutAccounts: buildScenarioPayoutAccounts(scenario, primaryLane),
      financeSnapshot: buildScenarioFinanceSnapshot(scenario, primaryLane),
      conversionRecords: buildScenarioConversionRecords(scenario, primaryLane),
      integrationCredentials: buildScenarioIntegrationCredentials(scenario, primaryLane),
      integrationDeliveryLogs: buildScenarioIntegrationDeliveryLogs(scenario, primaryLane),
      resellerStorefronts: buildScenarioResellerStorefronts(scenario, primaryLane),
      resellerSnapshot: buildScenarioResellerSnapshot(scenario, primaryLane),
      reviewRequests: buildScenarioReviewRequests(scenario, primaryLane),
      cases: buildScenarioCases(scenario, primaryLane),
      notifications: buildScenarioNotifications(scenario),
      updatedAt: DEFAULT_DATE,
    };
  }

  if (scenario === 'active') {
    return {
      scenario,
      workspaceRole,
      releaseRing,
      primaryLane,
      workspaceStatus: 'active',
      financeReadiness: 'ready',
      complianceReadiness: 'approved',
      technicalReadiness:
        primaryLane === 'performance_media' || primaryLane === 'reseller_api'
          ? 'ready'
          : 'not_required',
      governanceState: 'clear',
      teamMembers: buildScenarioTeamMembers(scenario, primaryLane),
      laneMemberships: buildScenarioLaneMemberships(scenario, primaryLane),
      legalDocuments: buildScenarioLegalDocuments(scenario, primaryLane),
      codes: buildScenarioCodes(scenario, primaryLane),
      campaignAssets: buildScenarioCampaignAssets(scenario, primaryLane),
      complianceTasks: buildScenarioComplianceTasks(scenario, primaryLane),
      analyticsMetrics: buildScenarioAnalyticsMetrics(scenario, primaryLane),
      reportExports: buildScenarioReportExports(scenario, primaryLane),
      financeStatements: buildScenarioFinanceStatements(scenario, primaryLane),
      payoutAccounts: buildScenarioPayoutAccounts(scenario, primaryLane),
      financeSnapshot: buildScenarioFinanceSnapshot(scenario, primaryLane),
      conversionRecords: buildScenarioConversionRecords(scenario, primaryLane),
      integrationCredentials: buildScenarioIntegrationCredentials(scenario, primaryLane),
      integrationDeliveryLogs: buildScenarioIntegrationDeliveryLogs(scenario, primaryLane),
      resellerStorefronts: buildScenarioResellerStorefronts(scenario, primaryLane),
      resellerSnapshot: buildScenarioResellerSnapshot(scenario, primaryLane),
      reviewRequests: [],
      cases: buildScenarioCases(scenario, primaryLane),
      notifications: buildScenarioNotifications(scenario),
      updatedAt: DEFAULT_DATE,
    };
  }

  return {
    scenario,
    workspaceRole,
    releaseRing,
    primaryLane,
    workspaceStatus: 'restricted',
    financeReadiness: 'blocked',
    complianceReadiness: 'approved',
    technicalReadiness:
      primaryLane === 'performance_media' || primaryLane === 'reseller_api'
        ? 'ready'
        : 'not_required',
    governanceState: 'limited',
    teamMembers: buildScenarioTeamMembers(scenario, primaryLane),
    laneMemberships: buildScenarioLaneMemberships(scenario, primaryLane),
    legalDocuments: buildScenarioLegalDocuments(scenario, primaryLane),
    codes: buildScenarioCodes(scenario, primaryLane),
    campaignAssets: buildScenarioCampaignAssets(scenario, primaryLane),
    complianceTasks: buildScenarioComplianceTasks(scenario, primaryLane),
    analyticsMetrics: buildScenarioAnalyticsMetrics(scenario, primaryLane),
    reportExports: buildScenarioReportExports(scenario, primaryLane),
    financeStatements: buildScenarioFinanceStatements(scenario, primaryLane),
    payoutAccounts: buildScenarioPayoutAccounts(scenario, primaryLane),
    financeSnapshot: buildScenarioFinanceSnapshot(scenario, primaryLane),
    conversionRecords: buildScenarioConversionRecords(scenario, primaryLane),
    integrationCredentials: buildScenarioIntegrationCredentials(scenario, primaryLane),
    integrationDeliveryLogs: buildScenarioIntegrationDeliveryLogs(scenario, primaryLane),
    resellerStorefronts: buildScenarioResellerStorefronts(scenario, primaryLane),
    resellerSnapshot: buildScenarioResellerSnapshot(scenario, primaryLane),
    reviewRequests: [],
    cases: buildScenarioCases(scenario, primaryLane),
    notifications: buildScenarioNotifications(scenario),
    updatedAt: DEFAULT_DATE,
  };
}

export function derivePartnerPortalScenario(
  draft: PartnerApplicationDraft | null,
): PartnerPortalScenario {
  if (draft?.reviewReady) {
    return 'needs_info';
  }

  return 'draft';
}

export function derivePartnerReleaseRing(
  scenario: PartnerPortalScenario,
  primaryLane: PartnerPrimaryLane | '' = '',
): PartnerReleaseRing {
  if (primaryLane === 'reseller_api') {
    return scenario === 'active' || scenario === 'restricted' ? 'R4' : 'R1';
  }

  if (primaryLane === 'performance_media') {
    return scenario === 'active' || scenario === 'restricted' ? 'R3' : 'R1';
  }

  if (scenario === 'active' || scenario === 'restricted') {
    return 'R2';
  }

  return 'R1';
}

function readStoredPartnerPortalState(
  parsed: Record<string, unknown>,
): PartnerPortalState | null {
  const scenario = readStringField(parsed.scenario);
  const primaryLaneValue = readStringField(parsed.primaryLane);
  const workspaceRoleValue = readStringField(parsed.workspaceRole);
  const releaseRingValue = readStringField(parsed.releaseRing);
  const workspaceStatus = readStringField(parsed.workspaceStatus);
  const financeReadiness = readStringField(parsed.financeReadiness);
  const complianceReadiness = readStringField(parsed.complianceReadiness);
  const technicalReadiness = readStringField(parsed.technicalReadiness);
  const governanceState = readStringField(parsed.governanceState);

  if (
    !isPortalScenario(scenario)
    || !isWorkspaceStatus(workspaceStatus)
    || !isFinanceReadiness(financeReadiness)
    || !isComplianceReadiness(complianceReadiness)
    || !isTechnicalReadiness(technicalReadiness)
    || !isGovernanceState(governanceState)
  ) {
    return null;
  }

  const primaryLane = isPrimaryLane(primaryLaneValue) ? primaryLaneValue : '';
  const workspaceRole = isWorkspaceRole(workspaceRoleValue)
    ? workspaceRoleValue
    : 'workspace_owner';
  const releaseRing = isPartnerReleaseRing(releaseRingValue)
    ? releaseRingValue
    : derivePartnerReleaseRing(scenario, primaryLane);
  const reviewRequests = Array.isArray(parsed.reviewRequests)
    ? parsed.reviewRequests
        .map((request) => {
          if (!request || typeof request !== 'object') {
            return null;
          }

          const candidate = request as Record<string, unknown>;
          const kind = readStringField(candidate.kind);
          const status = readStringField(candidate.status);

          if (!isReviewRequestKind(kind) || (status !== 'open' && status !== 'submitted')) {
            return null;
          }

          return {
            id: readStringField(candidate.id),
            kind,
            dueDate: readStringField(candidate.dueDate, DEFAULT_DUE_DATE),
            status,
          } satisfies PartnerReviewRequest;
        })
        .filter((request): request is PartnerReviewRequest => request !== null)
    : [];

  const cases = Array.isArray(parsed.cases)
    ? parsed.cases
        .map((item) => {
          if (!item || typeof item !== 'object') {
            return null;
          }

          const candidate = item as Record<string, unknown>;
          const kind = readStringField(candidate.kind);
          const status = readStringField(candidate.status);

          if (!isCaseKind(kind) || !isCaseStatus(status)) {
            return null;
          }

          return {
            id: readStringField(candidate.id),
            kind,
            status,
            updatedAt: readStringField(candidate.updatedAt, DEFAULT_DATE),
          } satisfies PartnerPortalCase;
        })
        .filter((item): item is PartnerPortalCase => item !== null)
    : [];

  const notifications = Array.isArray(parsed.notifications)
    ? parsed.notifications
        .map((item) => {
          if (!item || typeof item !== 'object') {
            return null;
          }

          const candidate = item as Record<string, unknown>;
          const kind = readStringField(candidate.kind);
          const tone = readStringField(candidate.tone);

          if (!isNotificationKind(kind) || !isNotificationTone(tone)) {
            return null;
          }

          return {
            id: readStringField(candidate.id),
            kind,
            tone,
            createdAt: readStringField(candidate.createdAt, DEFAULT_DATE),
            unread: readBooleanField(candidate.unread, true),
            routeSlug: readStringField(candidate.routeSlug ?? candidate.route_slug, '') || undefined,
            message: readStringField(candidate.message, '') || undefined,
            notes: Array.isArray(candidate.notes)
              ? candidate.notes
                  .filter((note): note is string => typeof note === 'string')
              : undefined,
            actionRequired: readBooleanField(
              candidate.actionRequired ?? candidate.action_required,
              false,
            ),
          } satisfies PartnerPortalNotification;
        })
        .filter((item) => item !== null) as PartnerPortalNotification[]
    : [];

  const teamMembers = Array.isArray(parsed.teamMembers)
    ? parsed.teamMembers
        .map((item) => {
          if (!item || typeof item !== 'object') {
            return null;
          }

          const candidate = item as Record<string, unknown>;
          const role = readStringField(candidate.role);
          const status = readStringField(candidate.status);

          if (!isWorkspaceRole(role) || !isTeamMemberStatus(status)) {
            return null;
          }

          return {
            id: readStringField(candidate.id),
            name: readStringField(candidate.name),
            email: readStringField(candidate.email),
            role,
            status,
          } satisfies PartnerTeamMember;
        })
        .filter((item): item is PartnerTeamMember => item !== null)
    : buildScenarioTeamMembers(scenario, primaryLane);

  const laneMemberships = Array.isArray(parsed.laneMemberships)
    ? parsed.laneMemberships
        .map((item) => {
          if (!item || typeof item !== 'object') {
            return null;
          }

          const candidate = item as Record<string, unknown>;
          const lane = readStringField(candidate.lane);
          const status = readStringField(candidate.status);

          if (!isPrimaryLane(lane) || !isLaneMembershipStatus(status)) {
            return null;
          }

          return {
            lane,
            status,
            assignedManager: readStringField(candidate.assignedManager),
            restrictions: Array.isArray(candidate.restrictions)
              ? candidate.restrictions.filter(
                  (restriction): restriction is string => typeof restriction === 'string',
                )
              : [],
          } satisfies PartnerLaneMembership;
        })
        .filter((item): item is PartnerLaneMembership => item !== null)
    : buildScenarioLaneMemberships(scenario, primaryLane);

  const legalDocuments = Array.isArray(parsed.legalDocuments)
    ? parsed.legalDocuments
        .map((item) => {
          if (!item || typeof item !== 'object') {
            return null;
          }

          const candidate = item as Record<string, unknown>;
          const kind = readStringField(candidate.kind);
          const status = readStringField(candidate.status);
          const acceptedByRoleValue = readStringField(candidate.acceptedByRole);

          if (!isLegalDocumentKind(kind) || !isLegalDocumentStatus(status)) {
            return null;
          }

          return {
            id: readStringField(candidate.id),
            kind,
            version: readStringField(candidate.version),
            status,
            acceptedAt: readStringField(candidate.acceptedAt) || null,
            acceptedByRole: isWorkspaceRole(acceptedByRoleValue)
              ? acceptedByRoleValue
              : null,
          } satisfies PartnerLegalDocument;
        })
        .filter((item): item is PartnerLegalDocument => item !== null)
    : buildScenarioLegalDocuments(scenario, primaryLane);

  const codes = Array.isArray(parsed.codes)
    ? parsed.codes
        .map((item) => {
          if (!item || typeof item !== 'object') {
            return null;
          }

          const candidate = item as Record<string, unknown>;
          const kind = readStringField(candidate.kind);
          const status = readStringField(candidate.status);

          if (!isCodeKind(kind) || !isCodeStatus(status)) {
            return null;
          }

          return {
            id: readStringField(candidate.id),
            label: readStringField(candidate.label),
            kind,
            status,
            destination: readStringField(candidate.destination),
            notes: Array.isArray(candidate.notes)
              ? candidate.notes.filter(
                  (note): note is string => typeof note === 'string',
                )
              : [],
          } satisfies PartnerCode;
        })
        .filter((item): item is PartnerCode => item !== null)
    : buildScenarioCodes(scenario, primaryLane);

  const campaignAssets = Array.isArray(parsed.campaignAssets)
    ? parsed.campaignAssets
        .map((item) => {
          if (!item || typeof item !== 'object') {
            return null;
          }

          const candidate = item as Record<string, unknown>;
          const channel = readStringField(candidate.channel);
          const status = readStringField(candidate.status);

          if (!isCampaignChannel(channel) || !isCampaignStatus(status)) {
            return null;
          }

          return {
            id: readStringField(candidate.id),
            name: readStringField(candidate.name),
            channel,
            status,
            approvalOwner: readStringField(candidate.approvalOwner),
            notes: Array.isArray(candidate.notes)
              ? candidate.notes.filter(
                  (note): note is string => typeof note === 'string',
                )
              : [],
          } satisfies PartnerCampaignAsset;
        })
        .filter((item): item is PartnerCampaignAsset => item !== null)
    : buildScenarioCampaignAssets(scenario, primaryLane);

  const complianceTasks = Array.isArray(parsed.complianceTasks)
    ? parsed.complianceTasks
        .map((item) => {
          if (!item || typeof item !== 'object') {
            return null;
          }

          const candidate = item as Record<string, unknown>;
          const kind = readStringField(candidate.kind);
          const status = readStringField(candidate.status);
          const ownerRole = readStringField(candidate.ownerRole);

          if (
            !isComplianceTaskKind(kind)
            || !isComplianceTaskStatus(status)
            || !isWorkspaceRole(ownerRole)
          ) {
            return null;
          }

          return {
            id: readStringField(candidate.id),
            kind,
            status,
            ownerRole,
            notes: Array.isArray(candidate.notes)
              ? candidate.notes.filter(
                  (note): note is string => typeof note === 'string',
                )
              : [],
          } satisfies PartnerComplianceTask;
        })
        .filter((item): item is PartnerComplianceTask => item !== null)
    : buildScenarioComplianceTasks(scenario, primaryLane);

  const analyticsMetrics = Array.isArray(parsed.analyticsMetrics)
    ? parsed.analyticsMetrics
        .map((item) => {
          if (!item || typeof item !== 'object') {
            return null;
          }

          const candidate = item as Record<string, unknown>;
          const key = readStringField(candidate.key);
          const trend = readStringField(candidate.trend);

          if (!isAnalyticsMetricKey(key) || !isAnalyticsMetricTrend(trend)) {
            return null;
          }

          return {
            key,
            value: readStringField(candidate.value),
            trend,
            notes: Array.isArray(candidate.notes)
              ? candidate.notes.filter(
                  (note): note is string => typeof note === 'string',
                )
              : [],
          } satisfies PartnerAnalyticsMetric;
        })
        .filter((item): item is PartnerAnalyticsMetric => item !== null)
    : buildScenarioAnalyticsMetrics(scenario, primaryLane);

  const reportExports = Array.isArray(parsed.reportExports)
    ? parsed.reportExports
        .map((item) => {
          if (!item || typeof item !== 'object') {
            return null;
          }

          const candidate = item as Record<string, unknown>;
          const kind = readStringField(candidate.kind);
          const status = readStringField(candidate.status);

          if (!isReportExportKind(kind) || !isReportExportStatus(status)) {
            return null;
          }

          return {
            id: readStringField(candidate.id),
            kind,
            status,
            cadence: readStringField(candidate.cadence),
            notes: Array.isArray(candidate.notes)
              ? candidate.notes.filter(
                  (note): note is string => typeof note === 'string',
                )
              : [],
          } satisfies PartnerReportExport;
        })
        .filter((item): item is PartnerReportExport => item !== null)
    : buildScenarioReportExports(scenario, primaryLane);

  const financeStatements = Array.isArray(parsed.financeStatements)
    ? parsed.financeStatements
        .map((item) => {
          if (!item || typeof item !== 'object') {
            return null;
          }

          const candidate = item as Record<string, unknown>;
          const status = readStringField(candidate.status);

          if (!isFinanceStatementStatus(status)) {
            return null;
          }

          return {
            id: readStringField(candidate.id),
            periodLabel: readStringField(candidate.periodLabel),
            status,
            gross: readStringField(candidate.gross),
            net: readStringField(candidate.net),
            available: readStringField(candidate.available),
            onHold: readStringField(candidate.onHold),
            currency: readStringField(candidate.currency, 'USD'),
            notes: Array.isArray(candidate.notes)
              ? candidate.notes.filter(
                  (note): note is string => typeof note === 'string',
                )
              : [],
          } satisfies PartnerFinanceStatement;
        })
        .filter((item): item is PartnerFinanceStatement => item !== null)
    : buildScenarioFinanceStatements(scenario, primaryLane);

  const payoutAccounts = Array.isArray(parsed.payoutAccounts)
    ? parsed.payoutAccounts
        .map((item) => {
          if (!item || typeof item !== 'object') {
            return null;
          }

          const candidate = item as Record<string, unknown>;
          const kind = readStringField(candidate.kind);
          const status = readStringField(candidate.status);

          if (!isPayoutAccountKind(kind) || !isPayoutAccountStatus(status)) {
            return null;
          }

          return {
            id: readStringField(candidate.id),
            label: readStringField(candidate.label),
            kind,
            status,
            currency: readStringField(candidate.currency, 'USD'),
            isDefault: readBooleanField(candidate.isDefault, false),
            notes: Array.isArray(candidate.notes)
              ? candidate.notes.filter(
                  (note): note is string => typeof note === 'string',
                )
              : [],
          } satisfies PartnerPayoutAccount;
        })
        .filter((item): item is PartnerPayoutAccount => item !== null)
    : buildScenarioPayoutAccounts(scenario, primaryLane);

  const financeSnapshot = (
    parsed.financeSnapshot
    && typeof parsed.financeSnapshot === 'object'
  )
    ? {
        availableEarnings: readStringField(
          (parsed.financeSnapshot as Record<string, unknown>).availableEarnings,
          '$0',
        ),
        onHoldEarnings: readStringField(
          (parsed.financeSnapshot as Record<string, unknown>).onHoldEarnings,
          '$0',
        ),
        reserves: readStringField(
          (parsed.financeSnapshot as Record<string, unknown>).reserves,
          '$0',
        ),
        nextPayoutForecast: readStringField(
          (parsed.financeSnapshot as Record<string, unknown>).nextPayoutForecast,
          '$0',
        ),
        currency: readStringField(
          (parsed.financeSnapshot as Record<string, unknown>).currency,
          'USD',
        ),
      } satisfies PartnerFinanceSnapshot
    : buildScenarioFinanceSnapshot(scenario, primaryLane);

  const conversionRecords = Array.isArray(parsed.conversionRecords)
    ? parsed.conversionRecords
        .map((item) => {
          if (!item || typeof item !== 'object') {
            return null;
          }

          const candidate = item as Record<string, unknown>;
          const kind = readStringField(candidate.kind);
          const status = readStringField(candidate.status);
          const customerScope = readStringField(candidate.customerScope);

          if (
            !isConversionKind(kind)
            || !isConversionStatus(status)
            || !isCustomerScope(customerScope)
          ) {
            return null;
          }

          return {
            id: readStringField(candidate.id),
            kind,
            status,
            orderLabel: readStringField(candidate.orderLabel),
            customerLabel: readStringField(candidate.customerLabel),
            codeLabel: readStringField(candidate.codeLabel),
            geo: readStringField(candidate.geo),
            amount: readStringField(candidate.amount),
            customerScope,
            updatedAt: readStringField(candidate.updatedAt, DEFAULT_DATE),
            notes: Array.isArray(candidate.notes)
              ? candidate.notes.filter(
                  (note): note is string => typeof note === 'string',
                )
              : [],
          } satisfies PartnerConversionRecord;
        })
        .filter((item): item is PartnerConversionRecord => item !== null)
    : buildScenarioConversionRecords(scenario, primaryLane);

  const integrationCredentials = Array.isArray(parsed.integrationCredentials)
    ? parsed.integrationCredentials
        .map((item) => {
          if (!item || typeof item !== 'object') {
            return null;
          }

          const candidate = item as Record<string, unknown>;
          const kind = readStringField(candidate.kind);
          const status = readStringField(candidate.status);

          if (
            !isIntegrationCredentialKind(kind)
            || !isIntegrationCredentialStatus(status)
          ) {
            return null;
          }

          return {
            id: readStringField(candidate.id),
            label: readStringField(candidate.label),
            kind,
            status,
            lastRotatedAt: readStringField(candidate.lastRotatedAt) || null,
            notes: Array.isArray(candidate.notes)
              ? candidate.notes.filter(
                  (note): note is string => typeof note === 'string',
                )
              : [],
          } satisfies PartnerIntegrationCredential;
        })
        .filter(
          (item): item is PartnerIntegrationCredential => item !== null,
        )
    : buildScenarioIntegrationCredentials(scenario, primaryLane);

  const integrationDeliveryLogs = Array.isArray(parsed.integrationDeliveryLogs)
    ? parsed.integrationDeliveryLogs
        .map((item) => {
          if (!item || typeof item !== 'object') {
            return null;
          }

          const candidate = item as Record<string, unknown>;
          const channel = readStringField(candidate.channel);
          const status = readStringField(candidate.status);

          if (
            !isIntegrationDeliveryChannel(channel)
            || !isIntegrationDeliveryStatus(status)
          ) {
            return null;
          }

          return {
            id: readStringField(candidate.id),
            channel,
            status,
            destination: readStringField(candidate.destination),
            lastAttemptAt: readStringField(candidate.lastAttemptAt, DEFAULT_DATE),
            notes: Array.isArray(candidate.notes)
              ? candidate.notes.filter(
                  (note): note is string => typeof note === 'string',
                )
              : [],
          } satisfies PartnerIntegrationDeliveryLog;
        })
        .filter(
          (item): item is PartnerIntegrationDeliveryLog => item !== null,
        )
    : buildScenarioIntegrationDeliveryLogs(scenario, primaryLane);

  const resellerStorefronts = Array.isArray(parsed.resellerStorefronts)
    ? parsed.resellerStorefronts
        .map((item) => {
          if (!item || typeof item !== 'object') {
            return null;
          }

          const candidate = item as Record<string, unknown>;
          const status = readStringField(candidate.status);

          if (!isResellerStorefrontStatus(status)) {
            return null;
          }

          return {
            id: readStringField(candidate.id),
            label: readStringField(candidate.label),
            domain: readStringField(candidate.domain),
            status,
            currency: readStringField(candidate.currency, 'USD'),
            supportOwner: readStringField(candidate.supportOwner),
            notes: Array.isArray(candidate.notes)
              ? candidate.notes.filter(
                  (note): note is string => typeof note === 'string',
                )
              : [],
          } satisfies PartnerResellerStorefront;
        })
        .filter((item): item is PartnerResellerStorefront => item !== null)
    : buildScenarioResellerStorefronts(scenario, primaryLane);

  const resellerSnapshot = (
    parsed.resellerSnapshot
    && typeof parsed.resellerSnapshot === 'object'
  )
    ? {
        pricebookLabel: readStringField(
          (parsed.resellerSnapshot as Record<string, unknown>).pricebookLabel,
        ),
        supportOwnership: readStringField(
          (parsed.resellerSnapshot as Record<string, unknown>).supportOwnership,
        ),
        customerScope: readStringField(
          (parsed.resellerSnapshot as Record<string, unknown>).customerScope,
        ),
        technicalHealth: readStringField(
          (parsed.resellerSnapshot as Record<string, unknown>).technicalHealth,
        ),
      } satisfies PartnerResellerConsoleSnapshot
    : buildScenarioResellerSnapshot(scenario, primaryLane);

  return {
    scenario,
    workspaceRole,
    releaseRing,
    primaryLane,
    workspaceStatus,
    financeReadiness,
    complianceReadiness,
    technicalReadiness,
    governanceState,
    teamMembers,
    laneMemberships,
    legalDocuments,
    codes,
    campaignAssets,
    complianceTasks,
    analyticsMetrics,
    reportExports,
    financeStatements,
    payoutAccounts,
    financeSnapshot,
    conversionRecords,
    integrationCredentials,
    integrationDeliveryLogs,
    resellerStorefronts,
    resellerSnapshot,
    reviewRequests,
    cases,
    notifications,
    updatedAt: readStringField(parsed.updatedAt, DEFAULT_DATE),
  };
}

export function loadPartnerPortalState(): PartnerPortalState | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const rawState = window.localStorage.getItem(PARTNER_PORTAL_STATE_STORAGE_KEY);
  if (!rawState) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawState) as Record<string, unknown>;
    return readStoredPartnerPortalState(parsed);
  } catch {
    return null;
  }
}

export function savePartnerPortalState(state: PartnerPortalState): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(
    PARTNER_PORTAL_STATE_STORAGE_KEY,
    JSON.stringify(state),
  );
}

export function clearPartnerPortalState(): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.removeItem(PARTNER_PORTAL_STATE_STORAGE_KEY);
}

function emitPartnerPortalStateChange() {
  listeners.forEach((listener) => listener());
}

function buildInitialPartnerPortalState(): PartnerPortalState {
  const applicationDraft = loadPartnerApplicationDraft();
  const storedState = loadPartnerPortalState();
  const nextScenario = derivePartnerPortalScenario(applicationDraft);
  const nextPrimaryLane = applicationDraft?.primaryLane ?? '';

  if (storedState) {
    const shouldUpgradeStoredState =
      nextScenario === 'needs_info'
      && (storedState.workspaceStatus === 'draft'
        || storedState.workspaceStatus === 'email_verified'
        || storedState.workspaceStatus === 'submitted');

    if (shouldUpgradeStoredState) {
      return createPartnerPortalScenarioState(
        nextScenario,
        nextPrimaryLane,
        storedState.workspaceRole,
        storedState.releaseRing,
      );
    }

    if (nextPrimaryLane === '' || nextPrimaryLane === storedState.primaryLane) {
      return storedState;
    }

    return {
      ...storedState,
      primaryLane: nextPrimaryLane,
      laneMemberships: buildScenarioLaneMemberships(
        storedState.scenario,
        nextPrimaryLane,
      ),
      legalDocuments: buildScenarioLegalDocuments(
        storedState.scenario,
        nextPrimaryLane,
      ),
      codes: buildScenarioCodes(
        storedState.scenario,
        nextPrimaryLane,
      ),
      campaignAssets: buildScenarioCampaignAssets(
        storedState.scenario,
        nextPrimaryLane,
      ),
      complianceTasks: buildScenarioComplianceTasks(
        storedState.scenario,
        nextPrimaryLane,
      ),
      analyticsMetrics: buildScenarioAnalyticsMetrics(
        storedState.scenario,
        nextPrimaryLane,
      ),
      reportExports: buildScenarioReportExports(
        storedState.scenario,
        nextPrimaryLane,
      ),
      financeStatements: buildScenarioFinanceStatements(
        storedState.scenario,
        nextPrimaryLane,
      ),
      payoutAccounts: buildScenarioPayoutAccounts(
        storedState.scenario,
        nextPrimaryLane,
      ),
      financeSnapshot: buildScenarioFinanceSnapshot(
        storedState.scenario,
        nextPrimaryLane,
      ),
      conversionRecords: buildScenarioConversionRecords(
        storedState.scenario,
        nextPrimaryLane,
      ),
      integrationCredentials: buildScenarioIntegrationCredentials(
        storedState.scenario,
        nextPrimaryLane,
      ),
      integrationDeliveryLogs: buildScenarioIntegrationDeliveryLogs(
        storedState.scenario,
        nextPrimaryLane,
      ),
      resellerStorefronts: buildScenarioResellerStorefronts(
        storedState.scenario,
        nextPrimaryLane,
      ),
      resellerSnapshot: buildScenarioResellerSnapshot(
        storedState.scenario,
        nextPrimaryLane,
      ),
      teamMembers: buildScenarioTeamMembers(storedState.scenario, nextPrimaryLane),
    };
  }

  return createPartnerPortalScenarioState(
    derivePartnerPortalScenario(applicationDraft),
    applicationDraft?.primaryLane ?? '',
  );
}

function ensurePartnerPortalStateInitialized() {
  if (hasInitializedStore || typeof window === 'undefined') {
    return;
  }

  currentPartnerPortalState = buildInitialPartnerPortalState();
  hasInitializedStore = true;
  savePartnerPortalState(currentPartnerPortalState);
}

function updatePartnerPortalStateSnapshot(nextState: PartnerPortalState) {
  currentPartnerPortalState = {
    ...nextState,
    updatedAt: new Date().toISOString(),
  };
  savePartnerPortalState(currentPartnerPortalState);
  emitPartnerPortalStateChange();
}

export function getPartnerPortalStateSnapshot(): PartnerPortalState {
  ensurePartnerPortalStateInitialized();
  return currentPartnerPortalState;
}

export function getPartnerPortalServerSnapshot(): PartnerPortalState {
  return DEFAULT_PORTAL_STATE;
}

export function subscribeToPartnerPortalState(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function usePartnerPortalState() {
  return useSyncExternalStore(
    subscribeToPartnerPortalState,
    getPartnerPortalStateSnapshot,
    getPartnerPortalServerSnapshot,
  );
}

export function applyPartnerPortalScenario(
  scenario: PartnerPortalScenario,
  primaryLane?: PartnerPrimaryLane | '',
) {
  ensurePartnerPortalStateInitialized();
  updatePartnerPortalStateSnapshot(
    createPartnerPortalScenarioState(
      scenario,
      primaryLane ?? currentPartnerPortalState.primaryLane,
      currentPartnerPortalState.workspaceRole,
      currentPartnerPortalState.releaseRing,
    ),
  );
}

export function applyPartnerWorkspaceRole(role: PartnerWorkspaceRole) {
  ensurePartnerPortalStateInitialized();
  updatePartnerPortalStateSnapshot({
    ...currentPartnerPortalState,
    workspaceRole: role,
  });
}

export function applyPartnerReleaseRing(releaseRing: PartnerReleaseRing) {
  ensurePartnerPortalStateInitialized();
  updatePartnerPortalStateSnapshot({
    ...currentPartnerPortalState,
    releaseRing,
  });
}

export function syncPartnerPortalStateFromApplicationDraft(
  draft: PartnerApplicationDraft,
) {
  ensurePartnerPortalStateInitialized();

  const nextScenario = derivePartnerPortalScenario(draft);
  const shouldUpgradeFromDraft =
    draft.reviewReady
    && (currentPartnerPortalState.workspaceStatus === 'draft'
      || currentPartnerPortalState.workspaceStatus === 'email_verified'
      || currentPartnerPortalState.workspaceStatus === 'submitted');

  if (shouldUpgradeFromDraft) {
    updatePartnerPortalStateSnapshot(
      createPartnerPortalScenarioState(
        nextScenario,
        draft.primaryLane,
        currentPartnerPortalState.workspaceRole,
        currentPartnerPortalState.releaseRing,
      ),
    );
    return;
  }

  if (
    draft.primaryLane !== currentPartnerPortalState.primaryLane
    && currentPartnerPortalState.workspaceStatus === 'draft'
  ) {
    updatePartnerPortalStateSnapshot({
      ...currentPartnerPortalState,
      primaryLane: draft.primaryLane,
      technicalReadiness: getLaneTechnicalBaseline(draft.primaryLane),
      laneMemberships: buildScenarioLaneMemberships(
        currentPartnerPortalState.scenario,
        draft.primaryLane,
      ),
      legalDocuments: buildScenarioLegalDocuments(
        currentPartnerPortalState.scenario,
        draft.primaryLane,
      ),
      codes: buildScenarioCodes(
        currentPartnerPortalState.scenario,
        draft.primaryLane,
      ),
      campaignAssets: buildScenarioCampaignAssets(
        currentPartnerPortalState.scenario,
        draft.primaryLane,
      ),
      complianceTasks: buildScenarioComplianceTasks(
        currentPartnerPortalState.scenario,
        draft.primaryLane,
      ),
      analyticsMetrics: buildScenarioAnalyticsMetrics(
        currentPartnerPortalState.scenario,
        draft.primaryLane,
      ),
      reportExports: buildScenarioReportExports(
        currentPartnerPortalState.scenario,
        draft.primaryLane,
      ),
      financeStatements: buildScenarioFinanceStatements(
        currentPartnerPortalState.scenario,
        draft.primaryLane,
      ),
      payoutAccounts: buildScenarioPayoutAccounts(
        currentPartnerPortalState.scenario,
        draft.primaryLane,
      ),
      financeSnapshot: buildScenarioFinanceSnapshot(
        currentPartnerPortalState.scenario,
        draft.primaryLane,
      ),
      conversionRecords: buildScenarioConversionRecords(
        currentPartnerPortalState.scenario,
        draft.primaryLane,
      ),
      integrationCredentials: buildScenarioIntegrationCredentials(
        currentPartnerPortalState.scenario,
        draft.primaryLane,
      ),
      integrationDeliveryLogs: buildScenarioIntegrationDeliveryLogs(
        currentPartnerPortalState.scenario,
        draft.primaryLane,
      ),
      resellerStorefronts: buildScenarioResellerStorefronts(
        currentPartnerPortalState.scenario,
        draft.primaryLane,
      ),
      resellerSnapshot: buildScenarioResellerSnapshot(
        currentPartnerPortalState.scenario,
        draft.primaryLane,
      ),
      teamMembers: buildScenarioTeamMembers(
        currentPartnerPortalState.scenario,
        draft.primaryLane,
      ),
    });
  }
}

export function resetPartnerPortalStateFromApplicationDraft() {
  ensurePartnerPortalStateInitialized();
  const applicationDraft = loadPartnerApplicationDraft();
  updatePartnerPortalStateSnapshot(
    createPartnerPortalScenarioState(
      derivePartnerPortalScenario(applicationDraft),
      applicationDraft?.primaryLane ?? '',
      currentPartnerPortalState.workspaceRole,
      currentPartnerPortalState.releaseRing,
    ),
  );
}

export function submitPartnerReviewRequests() {
  ensurePartnerPortalStateInitialized();

  const nextState: PartnerPortalState = {
    ...currentPartnerPortalState,
    scenario: 'under_review',
    workspaceStatus: 'under_review',
    complianceReadiness: 'declarations_complete',
    governanceState: 'watch',
    reviewRequests: currentPartnerPortalState.reviewRequests.map((request) => ({
      ...request,
      status: 'submitted',
    })),
    cases: buildScenarioCases('under_review', currentPartnerPortalState.primaryLane),
    notifications: [
      {
        id: 'review-in-progress',
        kind: 'review_in_progress',
        tone: 'info',
        createdAt: new Date().toISOString(),
        unread: true,
      },
      ...currentPartnerPortalState.notifications.map((notification) => ({
        ...notification,
        unread: false,
      })),
    ],
  };

  updatePartnerPortalStateSnapshot(nextState);
}

export function acknowledgePartnerNotification(notificationId: string) {
  ensurePartnerPortalStateInitialized();
  updatePartnerPortalStateSnapshot({
    ...currentPartnerPortalState,
    notifications: currentPartnerPortalState.notifications.map((notification) => (
      notification.id === notificationId
        ? { ...notification, unread: false }
        : notification
    )),
  });
}
