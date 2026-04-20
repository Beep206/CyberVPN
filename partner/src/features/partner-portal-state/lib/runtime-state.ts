import type {
  GetPartnerSessionBootstrapResponse,
  ListPartnerNotificationsResponse,
  GetPartnerWorkspaceProgramsResponse,
  ListPartnerWorkspaceAnalyticsMetricsResponse,
  ListPartnerWorkspaceCasesResponse,
  ListPartnerWorkspaceCampaignAssetsResponse,
  ListPartnerWorkspaceIntegrationCredentialsResponse,
  ListPartnerWorkspaceIntegrationDeliveryLogsResponse,
  GetPartnerWorkspaceResponse,
  ListMyPartnerWorkspacesResponse,
  ListPartnerWorkspaceConversionRecordsResponse,
  ListPartnerWorkspaceCodesResponse,
  ListPartnerWorkspacePayoutAccountsResponse,
  ListPartnerWorkspaceReportExportsResponse,
  ListPartnerWorkspaceReviewRequestsResponse,
  ListPartnerWorkspaceTrafficDeclarationsResponse,
  ListPartnerWorkspaceStatementsResponse,
} from '@/lib/api/partner-portal';
import type {
  PartnerAnalyticsMetric,
  PartnerCampaignAsset,
  PartnerPortalCase,
  PartnerPortalThreadEvent,
  PartnerCode,
  PartnerComplianceTask,
  PartnerComplianceReadiness,
  PartnerConversionRecord,
  PartnerFinanceReadiness,
  PartnerFinanceSnapshot,
  PartnerFinanceStatement,
  PartnerFinanceStatementStatus,
  PartnerGovernanceState,
  PartnerIntegrationCredential,
  PartnerIntegrationDeliveryLog,
  PartnerLaneMembership,
  PartnerPayoutAccount,
  PartnerPayoutAccountKind,
  PartnerPayoutAccountStatus,
  PartnerPortalNotification,
  PartnerPortalState,
  PartnerReportExport,
  PartnerReviewRequest,
  PartnerTeamMember,
  PartnerTechnicalReadiness,
  PartnerWorkspaceRole,
  PartnerWorkspaceStatus,
} from '@/features/partner-portal-state/lib/portal-state';
import type { PartnerPrimaryLane } from '@/features/partner-onboarding/lib/application-draft-storage';
import { deriveCanonicalComplianceTasks } from '@/features/partner-compliance/lib/compliance-runtime';
import { isPartnerReleaseRing } from '@/features/partner-shell/config/section-registry';

export type PartnerPortalRuntimeState = PartnerPortalState & {
  activeWorkspaceDisplayName?: string | null;
  activeWorkspaceId?: string | null;
  activeWorkspaceKey?: string | null;
  currentPermissionKeys?: readonly string[];
  trafficDeclarations: PartnerPortalTrafficDeclaration[];
  workspaceDataSource?: 'canonical' | 'local';
};

export interface PartnerPortalProgramLane {
  laneKey: string;
  membershipStatus: string;
  ownerContextLabel: string;
  pilotCohortId: string | null;
  pilotCohortStatus: string | null;
  runbookGateStatus: string | null;
  blockingReasonCodes: string[];
  warningReasonCodes: string[];
  restrictionNotes: string[];
  readinessNotes: string[];
  updatedAt: string;
}

export interface PartnerPortalProgramReadinessItem {
  key: string;
  status: string;
  blockingReasonCodes: string[];
  notes: string[];
}

export interface PartnerPortalProgramsSnapshot {
  canonicalSource: string;
  primaryLaneKey: string | null;
  laneMemberships: PartnerPortalProgramLane[];
  readinessItems: PartnerPortalProgramReadinessItem[];
  updatedAt: string;
}

export interface PartnerPortalTrafficDeclaration {
  id: string;
  kind: string;
  status: string;
  scopeLabel: string;
  updatedAt: string;
  notes: string[];
}

export interface BuildPartnerPortalRuntimeStateOptions {
  baseState: PartnerPortalState;
  workspace: GetPartnerWorkspaceResponse | null;
  blockedReasons?: GetPartnerSessionBootstrapResponse['blocked_reasons'] | null;
  workspaceCodes?: ListPartnerWorkspaceCodesResponse | null;
  workspaceCampaignAssets?: ListPartnerWorkspaceCampaignAssetsResponse | null;
  workspaceStatements?: ListPartnerWorkspaceStatementsResponse | null;
  workspacePayoutAccounts?: ListPartnerWorkspacePayoutAccountsResponse | null;
  workspaceConversionRecords?: ListPartnerWorkspaceConversionRecordsResponse | null;
  workspaceAnalyticsMetrics?: ListPartnerWorkspaceAnalyticsMetricsResponse | null;
  workspaceReportExports?: ListPartnerWorkspaceReportExportsResponse | null;
  workspaceReviewRequests?: ListPartnerWorkspaceReviewRequestsResponse | null;
  workspaceTrafficDeclarations?: ListPartnerWorkspaceTrafficDeclarationsResponse | null;
  workspaceCases?: ListPartnerWorkspaceCasesResponse | null;
  workspaceNotifications?: ListPartnerNotificationsResponse | null;
  workspaceIntegrationCredentials?: ListPartnerWorkspaceIntegrationCredentialsResponse | null;
  workspaceIntegrationDeliveryLogs?: ListPartnerWorkspaceIntegrationDeliveryLogsResponse | null;
}

const PRIMARY_LANE_SET = new Set<PartnerPrimaryLane>([
  'creator_affiliate',
  'performance_media',
  'reseller_api',
]);

const FINANCE_READINESS_SET = new Set<PartnerFinanceReadiness>([
  'not_started',
  'in_progress',
  'ready',
  'blocked',
]);

const COMPLIANCE_READINESS_SET = new Set<PartnerComplianceReadiness>([
  'not_started',
  'declarations_complete',
  'evidence_requested',
  'approved',
  'blocked',
]);

const TECHNICAL_READINESS_SET = new Set<PartnerTechnicalReadiness>([
  'not_required',
  'in_progress',
  'ready',
  'blocked',
]);

const GOVERNANCE_STATE_SET = new Set<PartnerGovernanceState>([
  'clear',
  'watch',
  'warning',
  'limited',
  'frozen',
]);

const WORKSPACE_ROLE_MAP: Record<string, PartnerWorkspaceRole> = {
  analyst: 'analyst',
  finance: 'finance_manager',
  manager: 'workspace_admin',
  owner: 'workspace_owner',
  support_manager: 'support_manager',
  technical_manager: 'technical_manager',
  traffic_manager: 'traffic_manager',
};

const WORKSPACE_STATUS_SET = new Set<PartnerWorkspaceStatus>([
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
]);

function formatMoney(amount: number, currencyCode: string): string {
  const normalizedCurrency = currencyCode || 'USD';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: normalizedCurrency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

function mapWorkspaceStatus(
  baseState: PartnerPortalState,
  workspace: GetPartnerWorkspaceResponse | null,
): PartnerWorkspaceStatus {
  const candidate = workspace?.status;
  if (candidate && WORKSPACE_STATUS_SET.has(candidate as PartnerWorkspaceStatus)) {
    return candidate as PartnerWorkspaceStatus;
  }
  return baseState.workspaceStatus;
}

function mapWorkspaceRole(
  baseState: PartnerPortalState,
  workspace: GetPartnerWorkspaceResponse | null,
): PartnerWorkspaceRole {
  return mapWorkspaceRoleKey(baseState.workspaceRole, workspace?.current_role_key ?? null);
}

function mapWorkspaceRoleKey(
  fallbackRole: PartnerWorkspaceRole,
  roleKey: string | null | undefined,
): PartnerWorkspaceRole {
  if (!roleKey) {
    return fallbackRole;
  }
  return WORKSPACE_ROLE_MAP[roleKey] ?? fallbackRole;
}

function mapWorkspaceMembers(
  workspace: GetPartnerWorkspaceResponse | null,
): PartnerTeamMember[] | null {
  if (!workspace) {
    return null;
  }

  return workspace.members.map((member) => ({
    id: member.id,
    name: member.operator_display_name || member.operator_login || member.role_display_name,
    email: member.operator_email || member.operator_login || member.admin_user_id,
    role: WORKSPACE_ROLE_MAP[member.role_key] ?? 'workspace_admin',
    status: member.membership_status === 'limited'
      ? 'limited'
      : member.membership_status === 'active'
        ? 'active'
        : 'invited',
  }));
}

function mapWorkspaceCodes(
  workspaceCodes: ListPartnerWorkspaceCodesResponse | null | undefined,
): PartnerCode[] | null {
  if (!workspaceCodes) {
    return null;
  }

  return workspaceCodes.map((code) => ({
    id: code.id,
    label: code.code,
    kind: 'starter_code',
    status: code.is_active ? 'active' : 'paused',
    destination: `/checkout?partner_code=${encodeURIComponent(code.code)}`,
    notes: [`Markup ${Number(code.markup_pct).toFixed(2)}%`],
  }));
}

function mapWorkspaceCampaignStatus(status: string): PartnerCampaignAsset['status'] {
  if (status === 'approved') {
    return 'approved';
  }
  if (status === 'in_review') {
    return 'in_review';
  }
  if (status === 'restricted') {
    return 'restricted';
  }
  if (status === 'approval_required') {
    return 'approval_required';
  }
  return 'available';
}

function mapWorkspaceCampaignChannel(channel: string): PartnerCampaignAsset['channel'] {
  if (channel === 'telegram') {
    return 'telegram';
  }
  if (channel === 'paid_social') {
    return 'paid_social';
  }
  if (channel === 'search') {
    return 'search';
  }
  if (channel === 'storefront') {
    return 'storefront';
  }
  return 'content';
}

function mapWorkspaceCampaignAssets(
  workspaceCampaignAssets: ListPartnerWorkspaceCampaignAssetsResponse | null | undefined,
): PartnerCampaignAsset[] | null {
  if (!workspaceCampaignAssets) {
    return null;
  }

  return workspaceCampaignAssets.map((asset) => ({
    id: asset.id,
    name: asset.name,
    channel: mapWorkspaceCampaignChannel(asset.channel),
    status: mapWorkspaceCampaignStatus(asset.status),
    approvalOwner: asset.approval_owner,
    notes: asset.notes ?? [],
  }));
}

function mapBootstrapLaneMemberships(
  workspacePrograms: GetPartnerWorkspaceProgramsResponse | null | undefined,
): PartnerLaneMembership[] | null {
  if (!workspacePrograms) {
    return null;
  }

  return (workspacePrograms.lane_memberships ?? [])
    .filter((item): item is typeof item & { lane_key: PartnerPrimaryLane } => (
      PRIMARY_LANE_SET.has(item.lane_key as PartnerPrimaryLane)
    ))
    .map((item) => ({
      lane: item.lane_key as PartnerPrimaryLane,
      status: item.membership_status as PartnerLaneMembership['status'],
      assignedManager: item.owner_context_label,
      restrictions: item.restriction_notes ?? [],
    }));
}

function mapBootstrapPrimaryLane(
  baseState: PartnerPortalState,
  primaryLaneKey: string | null | undefined,
): PartnerPrimaryLane | '' {
  if (!primaryLaneKey) {
    return baseState.primaryLane;
  }

  return PRIMARY_LANE_SET.has(primaryLaneKey as PartnerPrimaryLane)
    ? (primaryLaneKey as PartnerPrimaryLane)
    : baseState.primaryLane;
}

function mapBootstrapFinanceReadiness(
  baseState: PartnerPortalState,
  value: string | null | undefined,
): PartnerFinanceReadiness {
  if (!value) {
    return baseState.financeReadiness;
  }
  return FINANCE_READINESS_SET.has(value as PartnerFinanceReadiness)
    ? (value as PartnerFinanceReadiness)
    : baseState.financeReadiness;
}

function mapBootstrapComplianceReadiness(
  baseState: PartnerPortalState,
  value: string | null | undefined,
): PartnerComplianceReadiness {
  if (!value) {
    return baseState.complianceReadiness;
  }
  return COMPLIANCE_READINESS_SET.has(value as PartnerComplianceReadiness)
    ? (value as PartnerComplianceReadiness)
    : baseState.complianceReadiness;
}

function mapBootstrapTechnicalReadiness(
  baseState: PartnerPortalState,
  value: string | null | undefined,
): PartnerTechnicalReadiness {
  if (!value) {
    return baseState.technicalReadiness;
  }
  return TECHNICAL_READINESS_SET.has(value as PartnerTechnicalReadiness)
    ? (value as PartnerTechnicalReadiness)
    : baseState.technicalReadiness;
}

function mapBootstrapGovernanceState(
  baseState: PartnerPortalState,
  value: string | null | undefined,
): PartnerGovernanceState {
  if (!value) {
    return baseState.governanceState;
  }
  return GOVERNANCE_STATE_SET.has(value as PartnerGovernanceState)
    ? (value as PartnerGovernanceState)
    : baseState.governanceState;
}

export function applyPartnerSessionBootstrapToState({
  baseState,
  bootstrap,
}: {
  baseState: PartnerPortalState;
  bootstrap: GetPartnerSessionBootstrapResponse | null | undefined;
}): PartnerPortalRuntimeState {
  const activeWorkspace = bootstrap?.active_workspace ?? null;
  const workspacePrograms = bootstrap?.programs ?? null;
  if (!activeWorkspace) {
    return {
      ...baseState,
      activeWorkspaceDisplayName: null,
      activeWorkspaceId: null,
      activeWorkspaceKey: null,
      currentPermissionKeys: [],
      trafficDeclarations: [],
      workspaceDataSource: 'local',
    };
  }

  const releaseRing = bootstrap?.release_ring;
  const permissionKeys = bootstrap?.current_permission_keys
    ?? activeWorkspace.current_permission_keys
    ?? [];

  return {
    ...baseState,
    workspaceRole: mapWorkspaceRoleKey(baseState.workspaceRole, activeWorkspace.current_role_key),
    workspaceStatus: mapWorkspaceStatus(baseState, activeWorkspace),
    releaseRing: releaseRing && isPartnerReleaseRing(releaseRing)
      ? releaseRing
      : baseState.releaseRing,
    primaryLane: mapBootstrapPrimaryLane(baseState, workspacePrograms?.primary_lane_key),
    financeReadiness: mapBootstrapFinanceReadiness(baseState, bootstrap?.finance_readiness),
    complianceReadiness: mapBootstrapComplianceReadiness(baseState, bootstrap?.compliance_readiness),
    technicalReadiness: mapBootstrapTechnicalReadiness(baseState, bootstrap?.technical_readiness),
    governanceState: mapBootstrapGovernanceState(baseState, bootstrap?.governance_state),
    laneMemberships: mapBootstrapLaneMemberships(workspacePrograms) ?? baseState.laneMemberships,
    teamMembers: mapWorkspaceMembers(activeWorkspace) ?? baseState.teamMembers,
    updatedAt: bootstrap?.updated_at ?? activeWorkspace.last_activity_at ?? baseState.updatedAt,
    activeWorkspaceDisplayName: activeWorkspace.display_name,
    activeWorkspaceId: activeWorkspace.id,
    activeWorkspaceKey: activeWorkspace.account_key,
    currentPermissionKeys: permissionKeys,
    trafficDeclarations: [],
    workspaceDataSource: 'canonical',
  };
}

export function mapWorkspaceProgramsSnapshot(
  workspacePrograms: GetPartnerWorkspaceProgramsResponse | null | undefined,
): PartnerPortalProgramsSnapshot | null {
  if (!workspacePrograms) {
    return null;
  }

  const laneMemberships = workspacePrograms.lane_memberships ?? [];
  const readinessItems = workspacePrograms.readiness_items ?? [];

  return {
    canonicalSource: workspacePrograms.canonical_source,
    primaryLaneKey: workspacePrograms.primary_lane_key ?? null,
    laneMemberships: laneMemberships.map((item) => ({
      laneKey: item.lane_key,
      membershipStatus: item.membership_status,
      ownerContextLabel: item.owner_context_label,
      pilotCohortId: item.pilot_cohort_id ?? null,
      pilotCohortStatus: item.pilot_cohort_status ?? null,
      runbookGateStatus: item.runbook_gate_status ?? null,
      blockingReasonCodes: item.blocking_reason_codes ?? [],
      warningReasonCodes: item.warning_reason_codes ?? [],
      restrictionNotes: item.restriction_notes ?? [],
      readinessNotes: item.readiness_notes ?? [],
      updatedAt: item.updated_at,
    })),
    readinessItems: readinessItems.map((item) => ({
      key: item.key,
      status: item.status,
      blockingReasonCodes: item.blocking_reason_codes ?? [],
      notes: item.notes ?? [],
    })),
    updatedAt: workspacePrograms.updated_at,
  };
}

function mapFinanceStatementStatus(
  statement: ListPartnerWorkspaceStatementsResponse[number],
): PartnerFinanceStatementStatus {
  if (statement.statement_status === 'open') {
    return 'draft';
  }
  if (statement.available_amount > 0) {
    return 'ready';
  }
  if (statement.on_hold_amount > 0 || statement.reserve_amount > 0) {
    return 'on_hold';
  }
  return 'blocked';
}

function mapWorkspaceStatements(
  workspaceStatements: ListPartnerWorkspaceStatementsResponse | null | undefined,
): PartnerFinanceStatement[] | null {
  if (!workspaceStatements) {
    return null;
  }

  return workspaceStatements.map((statement) => ({
    id: statement.id,
    periodLabel: statement.statement_key,
    status: mapFinanceStatementStatus(statement),
    gross: formatMoney(statement.accrual_amount, statement.currency_code),
    net: formatMoney(
      statement.available_amount + statement.on_hold_amount + statement.reserve_amount,
      statement.currency_code,
    ),
    available: formatMoney(statement.available_amount, statement.currency_code),
    onHold: formatMoney(statement.on_hold_amount + statement.reserve_amount, statement.currency_code),
    currency: statement.currency_code,
    notes: [
      `Version ${statement.statement_version}`,
      `${statement.source_event_count} source events`,
    ],
  }));
}

function mapPayoutKind(
  account: ListPartnerWorkspacePayoutAccountsResponse[number],
): PartnerPayoutAccountKind {
  if (account.payout_rail.includes('crypto')) {
    return 'crypto_wallet';
  }
  if (account.payout_rail === 'manual') {
    return 'invoice_profile';
  }
  return 'bank_account';
}

function mapPayoutStatus(
  account: ListPartnerWorkspacePayoutAccountsResponse[number],
): PartnerPayoutAccountStatus {
  if (account.account_status === 'archived' || account.account_status === 'suspended') {
    return 'blocked';
  }
  if (account.verification_status !== 'verified' || account.approval_status !== 'approved') {
    return 'pending_review';
  }
  return 'ready';
}

function mapWorkspacePayoutAccounts(
  workspacePayoutAccounts: ListPartnerWorkspacePayoutAccountsResponse | null | undefined,
): PartnerPayoutAccount[] | null {
  if (!workspacePayoutAccounts) {
    return null;
  }

  return workspacePayoutAccounts.map((account) => ({
    id: account.id,
    label: account.display_label,
    kind: mapPayoutKind(account),
    status: mapPayoutStatus(account),
    currency: String(account.destination_metadata?.currency ?? 'USD'),
    isDefault: account.is_default,
    notes: [
      account.masked_destination,
      ...(account.verification_status !== 'verified'
        ? ['Verification pending finance review.']
        : []),
      ...(account.approval_status !== 'approved'
        ? ['Approval pending finance sign-off.']
        : []),
      ...(account.account_status === 'suspended' && account.suspension_reason_code
        ? [`Suspended: ${account.suspension_reason_code}.`]
        : []),
      ...(account.account_status === 'archived' && account.archive_reason_code
        ? [`Archived: ${account.archive_reason_code}.`]
        : []),
    ],
  }));
}

function mapWorkspaceConversionRecords(
  workspaceConversionRecords: ListPartnerWorkspaceConversionRecordsResponse | null | undefined,
): PartnerConversionRecord[] | null {
  if (!workspaceConversionRecords) {
    return null;
  }

  return workspaceConversionRecords.map((record) => ({
    id: record.id,
    kind: record.kind as PartnerConversionRecord['kind'],
    status: record.status as PartnerConversionRecord['status'],
    orderLabel: record.order_label,
    customerLabel: record.customer_label,
    codeLabel: record.code_label,
    geo: record.geo,
    amount: record.amount,
    customerScope: record.customer_scope as PartnerConversionRecord['customerScope'],
    updatedAt: record.updated_at,
    notes: record.notes ?? [],
  }));
}

function mapWorkspaceAnalyticsMetrics(
  workspaceAnalyticsMetrics: ListPartnerWorkspaceAnalyticsMetricsResponse | null | undefined,
): PartnerAnalyticsMetric[] | null {
  if (!workspaceAnalyticsMetrics) {
    return null;
  }

  return workspaceAnalyticsMetrics.map((metric) => ({
    key: metric.key as PartnerAnalyticsMetric['key'],
    value: metric.value,
    trend: metric.trend as PartnerAnalyticsMetric['trend'],
    notes: metric.notes ?? [],
  }));
}

function mapWorkspaceReportExports(
  workspaceReportExports: ListPartnerWorkspaceReportExportsResponse | null | undefined,
): PartnerReportExport[] | null {
  if (!workspaceReportExports) {
    return null;
  }

  return workspaceReportExports.map((item) => ({
    id: item.id,
    kind: item.kind as PartnerReportExport['kind'],
    status: item.status as PartnerReportExport['status'],
    cadence: item.cadence,
    notes: item.notes ?? [],
    availableActions: item.available_actions ?? [],
    threadEvents: (item.thread_events ?? []).map(
      (event): PartnerPortalThreadEvent => ({
        id: event.id,
        actionKind: event.action_kind,
        message: event.message,
        createdAt: event.created_at,
        createdByAdminUserId: event.created_by_admin_user_id,
      }),
    ),
    lastRequestedAt: item.last_requested_at ?? null,
  }));
}

function mapWorkspaceIntegrationCredentials(
  workspaceIntegrationCredentials:
    | ListPartnerWorkspaceIntegrationCredentialsResponse
    | null
    | undefined,
): PartnerIntegrationCredential[] | null {
  if (!workspaceIntegrationCredentials) {
    return null;
  }

  return workspaceIntegrationCredentials.map((item) => ({
    id: item.id,
    label: item.token_hint,
    kind: item.kind as PartnerIntegrationCredential['kind'],
    status: item.status as PartnerIntegrationCredential['status'],
    lastRotatedAt: item.last_rotated_at ?? null,
    notes: item.notes ?? [],
  }));
}

function mapWorkspaceIntegrationDeliveryLogs(
  workspaceIntegrationDeliveryLogs:
    | ListPartnerWorkspaceIntegrationDeliveryLogsResponse
    | null
    | undefined,
): PartnerIntegrationDeliveryLog[] | null {
  if (!workspaceIntegrationDeliveryLogs) {
    return null;
  }

  return workspaceIntegrationDeliveryLogs.map((item) => ({
    id: item.id,
    channel: item.channel as PartnerIntegrationDeliveryLog['channel'],
    status: item.status as PartnerIntegrationDeliveryLog['status'],
    destination: item.destination,
    lastAttemptAt: item.last_attempt_at,
    notes: item.notes ?? [],
  }));
}

function mapWorkspaceReviewRequests(
  workspaceReviewRequests: ListPartnerWorkspaceReviewRequestsResponse | null | undefined,
): PartnerReviewRequest[] | null {
  if (!workspaceReviewRequests) {
    return null;
  }

  return workspaceReviewRequests.map((request) => ({
    id: request.id,
    kind: request.kind as PartnerReviewRequest['kind'],
    dueDate: request.due_date,
    status: request.status as PartnerReviewRequest['status'],
    availableActions: request.available_actions ?? [],
    threadEvents: (request.thread_events ?? []).map(
      (event): PartnerPortalThreadEvent => ({
        id: event.id,
        actionKind: event.action_kind,
        message: event.message,
        createdAt: event.created_at,
        createdByAdminUserId: event.created_by_admin_user_id,
      }),
    ),
  }));
}

function mapWorkspaceCases(
  workspaceCases: ListPartnerWorkspaceCasesResponse | null | undefined,
): PartnerPortalCase[] | null {
  if (!workspaceCases) {
    return null;
  }

  return workspaceCases.map((item) => ({
    id: item.id,
    kind: item.kind as PartnerPortalCase['kind'],
    status: item.status as PartnerPortalCase['status'],
    updatedAt: item.updated_at,
    notes: item.notes ?? [],
    availableActions: item.available_actions ?? [],
    threadEvents: (item.thread_events ?? []).map(
      (event): PartnerPortalThreadEvent => ({
        id: event.id,
        actionKind: event.action_kind,
        message: event.message,
        createdAt: event.created_at,
        createdByAdminUserId: event.created_by_admin_user_id,
      }),
    ),
  }));
}

function mapWorkspaceNotifications(
  workspaceNotifications: ListPartnerNotificationsResponse | null | undefined,
): PartnerPortalNotification[] | null {
  if (!workspaceNotifications) {
    return null;
  }

  return workspaceNotifications.map((item) => ({
    id: item.id,
    kind: item.kind as PartnerPortalNotification['kind'],
    tone: item.tone as PartnerPortalNotification['tone'],
    createdAt: item.created_at,
    unread: item.unread,
    routeSlug: item.route_slug,
    message: item.message,
    notes: item.notes ?? [],
    actionRequired: item.action_required,
  }));
}

function mapWorkspaceTrafficDeclarations(
  workspaceTrafficDeclarations: ListPartnerWorkspaceTrafficDeclarationsResponse | null | undefined,
): PartnerPortalTrafficDeclaration[] | null {
  if (!workspaceTrafficDeclarations) {
    return null;
  }

  return workspaceTrafficDeclarations.map((item) => ({
    id: item.id,
    kind: item.kind,
    status: item.status,
    scopeLabel: item.scope_label,
    updatedAt: item.updated_at,
    notes: item.notes ?? [],
  }));
}

function mapCanonicalComplianceTasks({
  baseState,
  blockedReasons,
  reviewRequests,
  trafficDeclarations,
}: {
  baseState: PartnerPortalState;
  blockedReasons: GetPartnerSessionBootstrapResponse['blocked_reasons'] | null | undefined;
  reviewRequests: ListPartnerWorkspaceReviewRequestsResponse | null | undefined;
  trafficDeclarations: ListPartnerWorkspaceTrafficDeclarationsResponse | null | undefined;
}): PartnerComplianceTask[] {
  return deriveCanonicalComplianceTasks({
    complianceReadiness: baseState.complianceReadiness,
    governanceState: baseState.governanceState,
    primaryLane: baseState.primaryLane,
    reviewRequests: mapWorkspaceReviewRequests(reviewRequests) ?? [],
    trafficDeclarations: mapWorkspaceTrafficDeclarations(trafficDeclarations) ?? [],
    blockedReasons,
  });
}

function deriveFinanceSnapshot(
  baseState: PartnerPortalState,
  workspaceStatements: ListPartnerWorkspaceStatementsResponse | null | undefined,
): PartnerFinanceSnapshot {
  if (!workspaceStatements) {
    return baseState.financeSnapshot;
  }

  const currency = workspaceStatements[0]?.currency_code ?? baseState.financeSnapshot.currency ?? 'USD';
  const available = workspaceStatements.reduce((sum, item) => sum + Number(item.available_amount), 0);
  const onHold = workspaceStatements.reduce((sum, item) => sum + Number(item.on_hold_amount), 0);
  const reserves = workspaceStatements.reduce((sum, item) => sum + Number(item.reserve_amount), 0);
  const nextPayoutForecast = workspaceStatements
    .filter((item) => item.statement_status === 'closed')
    .reduce((sum, item) => sum + Number(item.available_amount), 0);

  return {
    availableEarnings: formatMoney(available, currency),
    onHoldEarnings: formatMoney(onHold, currency),
    reserves: formatMoney(reserves, currency),
    nextPayoutForecast: formatMoney(nextPayoutForecast, currency),
    currency,
  };
}

function deriveUpdatedAt(
  baseState: PartnerPortalState,
  workspace: GetPartnerWorkspaceResponse | null,
  statements: ListPartnerWorkspaceStatementsResponse | null | undefined,
  payoutAccounts: ListPartnerWorkspacePayoutAccountsResponse | null | undefined,
  conversionRecords: ListPartnerWorkspaceConversionRecordsResponse | null | undefined,
  reviewRequests: ListPartnerWorkspaceReviewRequestsResponse | null | undefined,
  trafficDeclarations: ListPartnerWorkspaceTrafficDeclarationsResponse | null | undefined,
  cases: ListPartnerWorkspaceCasesResponse | null | undefined,
  notifications: ListPartnerNotificationsResponse | null | undefined,
  integrationCredentials: ListPartnerWorkspaceIntegrationCredentialsResponse | null | undefined,
  integrationDeliveryLogs: ListPartnerWorkspaceIntegrationDeliveryLogsResponse | null | undefined,
): string | null {
  const candidates = [
    baseState.updatedAt,
    workspace?.last_activity_at ?? null,
    ...(statements?.map((item) => item.updated_at) ?? []),
    ...(payoutAccounts?.map((item) => item.updated_at) ?? []),
    ...(conversionRecords?.map((item) => item.updated_at) ?? []),
    ...(reviewRequests?.map((item) => item.due_date) ?? []),
    ...(trafficDeclarations?.map((item) => item.updated_at) ?? []),
    ...(cases?.map((item) => item.updated_at) ?? []),
    ...(notifications?.map((item) => item.created_at) ?? []),
    ...(integrationCredentials?.map((item) => item.last_rotated_at).filter(Boolean) ?? []),
    ...(integrationDeliveryLogs?.map((item) => item.last_attempt_at) ?? []),
  ].filter((value): value is string => Boolean(value));

  return candidates.sort().at(-1) ?? null;
}

export function selectActivePartnerWorkspace(
  workspaces: ListMyPartnerWorkspacesResponse | undefined,
  preferredWorkspaceId: string | null,
): GetPartnerWorkspaceResponse | null {
  if (!workspaces || workspaces.length === 0) {
    return null;
  }

  if (preferredWorkspaceId) {
    return workspaces.find((workspace: GetPartnerWorkspaceResponse) => workspace.id === preferredWorkspaceId) ?? workspaces[0];
  }

  return workspaces[0];
}

export function buildPartnerPortalRuntimeState({
  baseState,
  workspace,
  blockedReasons,
  workspaceCodes,
  workspaceCampaignAssets,
  workspaceStatements,
  workspacePayoutAccounts,
  workspaceConversionRecords,
  workspaceAnalyticsMetrics,
  workspaceReportExports,
  workspaceReviewRequests,
  workspaceTrafficDeclarations,
  workspaceCases,
  workspaceNotifications,
  workspaceIntegrationCredentials,
  workspaceIntegrationDeliveryLogs,
}: BuildPartnerPortalRuntimeStateOptions): PartnerPortalRuntimeState {
  if (!workspace) {
    return {
      ...baseState,
      activeWorkspaceDisplayName: null,
      activeWorkspaceId: null,
      activeWorkspaceKey: null,
      currentPermissionKeys: [],
      trafficDeclarations: [],
      workspaceDataSource: 'local',
    };
  }

  const permissionKeys = workspace.current_permission_keys ?? [];
  const hasWorkspaceRead = permissionKeys.includes('workspace_read');
  const hasCodeRead = permissionKeys.includes('codes_read');
  const hasEarningsRead = permissionKeys.includes('earnings_read');
  const hasPayoutsRead = permissionKeys.includes('payouts_read');
  const hasTrafficRead = permissionKeys.includes('traffic_read');
  const hasIntegrationsRead = permissionKeys.includes('integrations_read');

  const mappedStatements = mapWorkspaceStatements(
    hasEarningsRead ? workspaceStatements : [],
  );
  const mappedCampaignAssets = mapWorkspaceCampaignAssets(
    hasTrafficRead ? workspaceCampaignAssets : [],
  );
  const mappedPayoutAccounts = mapWorkspacePayoutAccounts(
    hasPayoutsRead ? workspacePayoutAccounts : [],
  );
  const mappedConversionRecords = mapWorkspaceConversionRecords(
    hasEarningsRead ? workspaceConversionRecords : [],
  );
  const mappedAnalyticsMetrics = mapWorkspaceAnalyticsMetrics(
    hasEarningsRead ? workspaceAnalyticsMetrics : [],
  );
  const mappedReportExports = mapWorkspaceReportExports(
    hasEarningsRead ? workspaceReportExports : [],
  );
  const mappedReviewRequests = mapWorkspaceReviewRequests(
    hasWorkspaceRead ? workspaceReviewRequests : [],
  );
  const mappedTrafficDeclarations = mapWorkspaceTrafficDeclarations(
    hasTrafficRead ? workspaceTrafficDeclarations : [],
  );
  const mappedComplianceTasks = mapCanonicalComplianceTasks({
    baseState,
    blockedReasons,
    reviewRequests: hasWorkspaceRead ? workspaceReviewRequests : [],
    trafficDeclarations: hasTrafficRead ? workspaceTrafficDeclarations : [],
  });
  const mappedCases = mapWorkspaceCases(hasWorkspaceRead ? workspaceCases : []);
  const mappedNotifications = mapWorkspaceNotifications(
    hasWorkspaceRead ? workspaceNotifications : [],
  );
  const mappedIntegrationCredentials = mapWorkspaceIntegrationCredentials(
    hasIntegrationsRead ? workspaceIntegrationCredentials : [],
  );
  const mappedIntegrationDeliveryLogs = mapWorkspaceIntegrationDeliveryLogs(
    hasIntegrationsRead ? workspaceIntegrationDeliveryLogs : [],
  );

  return {
    ...baseState,
    workspaceRole: mapWorkspaceRole(baseState, workspace),
    workspaceStatus: mapWorkspaceStatus(baseState, workspace),
    financeReadiness: baseState.financeReadiness,
    teamMembers: mapWorkspaceMembers(workspace) ?? baseState.teamMembers,
    codes: hasCodeRead ? (mapWorkspaceCodes(workspaceCodes) ?? []) : [],
    campaignAssets: mappedCampaignAssets ?? [],
    analyticsMetrics: mappedAnalyticsMetrics ?? [],
    reportExports: mappedReportExports ?? [],
    financeStatements: mappedStatements ?? [],
    payoutAccounts: mappedPayoutAccounts ?? [],
    trafficDeclarations: mappedTrafficDeclarations ?? [],
    complianceTasks: mappedComplianceTasks,
    financeSnapshot: deriveFinanceSnapshot(baseState, hasEarningsRead ? workspaceStatements : []),
    conversionRecords: mappedConversionRecords ?? [],
    integrationCredentials: mappedIntegrationCredentials ?? [],
    integrationDeliveryLogs: mappedIntegrationDeliveryLogs ?? [],
    reviewRequests: mappedReviewRequests ?? [],
    cases: mappedCases ?? [],
    notifications: mappedNotifications ?? [],
    updatedAt: deriveUpdatedAt(
      baseState,
      workspace,
      hasEarningsRead ? workspaceStatements : [],
      hasPayoutsRead ? workspacePayoutAccounts : [],
      hasEarningsRead ? workspaceConversionRecords : [],
      hasWorkspaceRead ? workspaceReviewRequests : [],
      hasTrafficRead ? workspaceTrafficDeclarations : [],
      hasWorkspaceRead ? workspaceCases : [],
      hasWorkspaceRead ? workspaceNotifications : [],
      hasIntegrationsRead ? workspaceIntegrationCredentials : [],
      hasIntegrationsRead ? workspaceIntegrationDeliveryLogs : [],
    ),
    activeWorkspaceDisplayName: workspace.display_name,
    activeWorkspaceId: workspace.id,
    activeWorkspaceKey: workspace.account_key,
    currentPermissionKeys: permissionKeys,
    workspaceDataSource: 'canonical',
  };
}
