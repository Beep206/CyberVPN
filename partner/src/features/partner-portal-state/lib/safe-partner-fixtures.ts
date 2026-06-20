import type {
  GetPartnerWorkspaceResponse,
  ListPartnerNotificationsResponse,
  ListPartnerWorkspaceAnalyticsMetricsResponse,
  ListPartnerWorkspaceCasesResponse,
  ListPartnerWorkspaceCodesResponse,
  ListPartnerWorkspaceConversionRecordsResponse,
  ListPartnerWorkspacePayoutAccountsResponse,
  ListPartnerWorkspacePayoutHistoryResponse,
  ListPartnerWorkspaceReportExportsResponse,
  ListPartnerWorkspaceReviewRequestsResponse,
  ListPartnerWorkspaceStatementsResponse,
  ListPartnerWorkspaceTrafficDeclarationsResponse,
} from '@/lib/api/partner-portal';

export const SAFE_PARTNER_FIXTURE_IDS = {
  adminOperatorId: '10000000-0000-4000-8000-000000000101',
  analystOperatorId: '10000000-0000-4000-8000-000000000104',
  approvedInstructionId: '10000000-0000-4000-8000-000000000303',
  financeOperatorId: '10000000-0000-4000-8000-000000000102',
  ownerMemberId: '10000000-0000-4000-8000-000000000201',
  partnerUserId: '10000000-0000-4000-8000-000000000202',
  payoutAccountId: '10000000-0000-4000-8000-000000000301',
  pendingInstructionId: '10000000-0000-4000-8000-000000000302',
  rejectedInstructionId: '10000000-0000-4000-8000-000000000304',
  statementId: '10000000-0000-4000-8000-000000000401',
  statementOnHoldId: '10000000-0000-4000-8000-000000000402',
  settlementPeriodId: '10000000-0000-4000-8000-000000000403',
  trafficOperatorId: '10000000-0000-4000-8000-000000000103',
  workspaceId: '10000000-0000-4000-8000-000000000001',
} as const;

export const SAFE_PARTNER_FIXTURE_TIME = '2026-04-20T10:00:00Z';

export const SAFE_PARTNER_ROLE_PERMISSION_FIXTURES = {
  analyst: ['workspace_read', 'earnings_read'],
  finance: ['workspace_read', 'earnings_read', 'payouts_read', 'payouts_write'],
  owner: [
    'workspace_read',
    'codes_read',
    'earnings_read',
    'payouts_read',
    'traffic_read',
    'integrations_read',
    'membership_read',
  ],
  restricted: ['workspace_read'],
  traffic: ['workspace_read', 'codes_read', 'traffic_read', 'traffic_write'],
} as const;

export interface SafePartnerBusinessFlowFixture {
  workspace: GetPartnerWorkspaceResponse;
  workspaceAnalyticsMetrics: ListPartnerWorkspaceAnalyticsMetricsResponse;
  workspaceCases: ListPartnerWorkspaceCasesResponse;
  workspaceCodes: ListPartnerWorkspaceCodesResponse;
  workspaceConversionRecords: ListPartnerWorkspaceConversionRecordsResponse;
  workspaceNotifications: ListPartnerNotificationsResponse;
  workspacePayoutAccounts: ListPartnerWorkspacePayoutAccountsResponse;
  workspacePayoutHistory: ListPartnerWorkspacePayoutHistoryResponse;
  workspaceReportExports: ListPartnerWorkspaceReportExportsResponse;
  workspaceReviewRequests: ListPartnerWorkspaceReviewRequestsResponse;
  workspaceStatements: ListPartnerWorkspaceStatementsResponse;
  workspaceTrafficDeclarations: ListPartnerWorkspaceTrafficDeclarationsResponse;
}

function createWorkspaceMember({
  adminUserId,
  id,
  permissionKeys,
  roleDisplayName,
  roleKey,
}: {
  adminUserId: string;
  id: string;
  permissionKeys: readonly string[];
  roleDisplayName: string;
  roleKey: string;
}): GetPartnerWorkspaceResponse['members'][number] {
  return {
    admin_user_id: adminUserId,
    created_at: SAFE_PARTNER_FIXTURE_TIME,
    id,
    invited_by_admin_user_id: null,
    membership_status: 'active',
    operator_display_name: roleDisplayName,
    operator_email: null,
    operator_login: `${roleKey}.safe-fixture`,
    permission_keys: [...permissionKeys],
    role_display_name: roleDisplayName,
    role_id: `${id.slice(0, -3)}role`,
    role_key: roleKey,
    updated_at: SAFE_PARTNER_FIXTURE_TIME,
  };
}

function createSafePartnerWorkspace({
  permissionKeys = SAFE_PARTNER_ROLE_PERMISSION_FIXTURES.owner,
  roleKey = 'owner',
  status = 'active',
}: {
  permissionKeys?: readonly string[];
  roleKey?: string;
  status?: string;
} = {}): GetPartnerWorkspaceResponse {
  return {
    account_key: 'safe-partner-lab',
    active_code_count: status === 'suspended' ? 0 : 1,
    code_count: 2,
    created_by_admin_user_id: SAFE_PARTNER_FIXTURE_IDS.adminOperatorId,
    current_permission_keys: [...permissionKeys],
    current_role_key: roleKey,
    display_name: 'Safe Partner Lab',
    id: SAFE_PARTNER_FIXTURE_IDS.workspaceId,
    last_activity_at: SAFE_PARTNER_FIXTURE_TIME,
    legacy_owner_user_id: null,
    members: [
      createWorkspaceMember({
        adminUserId: SAFE_PARTNER_FIXTURE_IDS.adminOperatorId,
        id: SAFE_PARTNER_FIXTURE_IDS.ownerMemberId,
        permissionKeys: SAFE_PARTNER_ROLE_PERMISSION_FIXTURES.owner,
        roleDisplayName: 'Owner',
        roleKey: 'owner',
      }),
      createWorkspaceMember({
        adminUserId: SAFE_PARTNER_FIXTURE_IDS.financeOperatorId,
        id: '10000000-0000-4000-8000-000000000203',
        permissionKeys: SAFE_PARTNER_ROLE_PERMISSION_FIXTURES.finance,
        roleDisplayName: 'Finance',
        roleKey: 'finance',
      }),
      createWorkspaceMember({
        adminUserId: SAFE_PARTNER_FIXTURE_IDS.trafficOperatorId,
        id: '10000000-0000-4000-8000-000000000204',
        permissionKeys: SAFE_PARTNER_ROLE_PERMISSION_FIXTURES.traffic,
        roleDisplayName: 'Traffic Manager',
        roleKey: 'traffic_manager',
      }),
      createWorkspaceMember({
        adminUserId: SAFE_PARTNER_FIXTURE_IDS.analystOperatorId,
        id: '10000000-0000-4000-8000-000000000205',
        permissionKeys: SAFE_PARTNER_ROLE_PERMISSION_FIXTURES.analyst,
        roleDisplayName: 'Analyst',
        roleKey: 'analyst',
      }),
    ],
    status,
    total_clients: status === 'terminated' ? 0 : 12,
    total_earned: status === 'terminated' ? 0 : 280,
  };
}

function createSafePartnerCodes(isSuspended = false): ListPartnerWorkspaceCodesResponse {
  return [
    {
      code: 'CYBA-SAFE-42',
      code_normalized: 'CYBA-SAFE-42',
      created_at: SAFE_PARTNER_FIXTURE_TIME,
      default_destination_url: 'https://cyber-vpn.net/ru-RU/register',
      id: '10000000-0000-4000-8000-000000000501',
      is_active: !isSuspended,
      lifecycle_status: isSuspended ? 'paused' : 'active',
      approval_status: 'approved',
      owner_type: 'partner_account',
      lane_key: 'creator_affiliate',
      attribution_model: 'last_click',
      attribution_window_seconds: 2_592_000,
      masked_code: 'CYBA-SAFE-**',
      markup_pct: 12.5,
      partner_account_id: SAFE_PARTNER_FIXTURE_IDS.workspaceId,
      partner_user_id: SAFE_PARTNER_FIXTURE_IDS.partnerUserId,
      share_url: 'https://cyber-vpn.net/p/safe-42',
      updated_at: SAFE_PARTNER_FIXTURE_TIME,
      version: 1,
    },
    {
      code: 'CYBA-PAUSED-07',
      code_normalized: 'CYBA-PAUSED-07',
      created_at: SAFE_PARTNER_FIXTURE_TIME,
      default_destination_url: 'https://cyber-vpn.net/ru-RU/register',
      id: '10000000-0000-4000-8000-000000000502',
      is_active: false,
      lifecycle_status: 'paused',
      approval_status: 'approved',
      owner_type: 'partner_account',
      lane_key: 'creator_affiliate',
      attribution_model: 'last_click',
      attribution_window_seconds: 2_592_000,
      masked_code: 'CYBA-PAUSED-**',
      markup_pct: 0,
      partner_account_id: SAFE_PARTNER_FIXTURE_IDS.workspaceId,
      partner_user_id: SAFE_PARTNER_FIXTURE_IDS.partnerUserId,
      share_url: 'https://cyber-vpn.net/p/paused-07',
      updated_at: SAFE_PARTNER_FIXTURE_TIME,
      version: 1,
    },
  ];
}

function createSafePartnerStatements(): ListPartnerWorkspaceStatementsResponse {
  return [
    {
      accrual_amount: 420,
      active_reserve_count: 1,
      adjustment_count: 0,
      adjustment_net_amount: 0,
      available_amount: 280,
      closed_at: SAFE_PARTNER_FIXTURE_TIME,
      closed_by_admin_user_id: SAFE_PARTNER_FIXTURE_IDS.adminOperatorId,
      created_at: SAFE_PARTNER_FIXTURE_TIME,
      currency_code: 'USD',
      held_event_count: 1,
      id: SAFE_PARTNER_FIXTURE_IDS.statementId,
      on_hold_amount: 120,
      partner_account_id: SAFE_PARTNER_FIXTURE_IDS.workspaceId,
      reopened_from_statement_id: null,
      reserve_amount: 20,
      settlement_period_id: SAFE_PARTNER_FIXTURE_IDS.settlementPeriodId,
      source_event_count: 4,
      statement_key: 'fixture_closed',
      statement_snapshot: { source: 'safe_partner_fixture' },
      statement_status: 'closed',
      statement_version: 1,
      superseded_by_statement_id: null,
      updated_at: SAFE_PARTNER_FIXTURE_TIME,
    },
    {
      accrual_amount: 75,
      active_reserve_count: 0,
      adjustment_count: 0,
      adjustment_net_amount: 0,
      available_amount: 0,
      closed_at: null,
      closed_by_admin_user_id: null,
      created_at: SAFE_PARTNER_FIXTURE_TIME,
      currency_code: 'USD',
      held_event_count: 1,
      id: SAFE_PARTNER_FIXTURE_IDS.statementOnHoldId,
      on_hold_amount: 75,
      partner_account_id: SAFE_PARTNER_FIXTURE_IDS.workspaceId,
      reopened_from_statement_id: null,
      reserve_amount: 0,
      settlement_period_id: SAFE_PARTNER_FIXTURE_IDS.settlementPeriodId,
      source_event_count: 1,
      statement_key: 'fixture_hold',
      statement_snapshot: { source: 'safe_partner_fixture' },
      statement_status: 'open',
      statement_version: 1,
      superseded_by_statement_id: null,
      updated_at: SAFE_PARTNER_FIXTURE_TIME,
    },
  ];
}

function createSafePartnerPayoutAccounts(
  isSuspended = false,
): ListPartnerWorkspacePayoutAccountsResponse {
  return [
    {
      account_status: isSuspended ? 'suspended' : 'active',
      approval_status: 'approved',
      approved_at: SAFE_PARTNER_FIXTURE_TIME,
      archive_reason_code: null,
      archived_at: null,
      created_at: SAFE_PARTNER_FIXTURE_TIME,
      destination_metadata: { currency: 'USD', fixture_scope: 'safe_partner_pack' },
      display_label: 'Safe fixture settlement account',
      id: SAFE_PARTNER_FIXTURE_IDS.payoutAccountId,
      is_default: true,
      masked_destination: 'Bank **** 4242',
      payout_rail: 'bank_wire',
      settlement_profile_id: null,
      suspended_at: isSuspended ? SAFE_PARTNER_FIXTURE_TIME : null,
      suspension_reason_code: isSuspended ? 'safe_fixture_policy_hold' : null,
      updated_at: SAFE_PARTNER_FIXTURE_TIME,
      verification_status: 'verified',
      verified_at: SAFE_PARTNER_FIXTURE_TIME,
    },
    {
      account_status: 'active',
      approval_status: 'pending',
      approved_at: null,
      archive_reason_code: null,
      archived_at: null,
      created_at: SAFE_PARTNER_FIXTURE_TIME,
      destination_metadata: { currency: 'USDT', fixture_scope: 'safe_partner_pack' },
      display_label: 'Secondary review wallet',
      id: '10000000-0000-4000-8000-000000000305',
      is_default: false,
      masked_destination: 'Wallet **** 7788',
      payout_rail: 'crypto_usdt',
      settlement_profile_id: null,
      suspended_at: null,
      suspension_reason_code: null,
      updated_at: SAFE_PARTNER_FIXTURE_TIME,
      verification_status: 'pending',
      verified_at: null,
    },
  ];
}

function createSafePartnerPayoutHistory(): ListPartnerWorkspacePayoutHistoryResponse {
  return [
    {
      amount: 75,
      created_at: SAFE_PARTNER_FIXTURE_TIME,
      currency_code: 'USD',
      execution_id: null,
      execution_mode: null,
      execution_status: null,
      external_reference: null,
      id: 'safe-payout-history-pending',
      instruction_id: SAFE_PARTNER_FIXTURE_IDS.pendingInstructionId,
      instruction_status: 'draft',
      lifecycle_status: 'pending',
      notes: ['Safe fixture pending withdrawal request.'],
      partner_payout_account_id: SAFE_PARTNER_FIXTURE_IDS.payoutAccountId,
      partner_statement_id: SAFE_PARTNER_FIXTURE_IDS.statementOnHoldId,
      payout_account_label: 'Safe fixture settlement account',
      statement_key: 'fixture_hold',
      updated_at: SAFE_PARTNER_FIXTURE_TIME,
    },
    {
      amount: 280,
      created_at: SAFE_PARTNER_FIXTURE_TIME,
      currency_code: 'USD',
      execution_id: '10000000-0000-4000-8000-000000000306',
      execution_mode: 'sandbox',
      execution_status: 'completed',
      external_reference: 'safe-fixture-approved',
      id: 'safe-payout-history-approved',
      instruction_id: SAFE_PARTNER_FIXTURE_IDS.approvedInstructionId,
      instruction_status: 'approved',
      lifecycle_status: 'approved',
      notes: ['Approved safe fixture payout history; no live payout was executed.'],
      partner_payout_account_id: SAFE_PARTNER_FIXTURE_IDS.payoutAccountId,
      partner_statement_id: SAFE_PARTNER_FIXTURE_IDS.statementId,
      payout_account_label: 'Safe fixture settlement account',
      statement_key: 'fixture_closed',
      updated_at: SAFE_PARTNER_FIXTURE_TIME,
    },
    {
      amount: 55,
      created_at: SAFE_PARTNER_FIXTURE_TIME,
      currency_code: 'USD',
      execution_id: null,
      execution_mode: null,
      execution_status: null,
      external_reference: null,
      id: 'safe-payout-history-rejected',
      instruction_id: SAFE_PARTNER_FIXTURE_IDS.rejectedInstructionId,
      instruction_status: 'rejected',
      lifecycle_status: 'rejected',
      notes: ['Rejected safe fixture payout history for moderation coverage.'],
      partner_payout_account_id: SAFE_PARTNER_FIXTURE_IDS.payoutAccountId,
      partner_statement_id: SAFE_PARTNER_FIXTURE_IDS.statementOnHoldId,
      payout_account_label: 'Safe fixture settlement account',
      statement_key: 'fixture_hold',
      updated_at: SAFE_PARTNER_FIXTURE_TIME,
    },
  ];
}

function createSafePartnerConversionRecords(): ListPartnerWorkspaceConversionRecordsResponse {
  return [
    {
      amount: '$420.00',
      code_label: 'CYBA-SAFE-42',
      customer_label: 'masked-customer-001',
      customer_scope: 'workspace_scoped',
      geo: 'DE',
      id: 'safe-conversion-first-paid',
      kind: 'first_paid',
      notes: ['Attributed through CYBA-SAFE-42 with workspace-scoped masked customer data.'],
      order_label: 'SAFE-ORDER-001',
      status: 'commissionable',
      updated_at: SAFE_PARTNER_FIXTURE_TIME,
    },
    {
      amount: '$120.00',
      code_label: 'CYBA-SAFE-42',
      customer_label: 'masked-customer-002',
      customer_scope: 'workspace_scoped',
      geo: 'PL',
      id: 'safe-conversion-on-hold',
      kind: 'repeat_paid',
      notes: ['On-hold repeat payment keeps earnings visible without payout authority.'],
      order_label: 'SAFE-ORDER-002',
      status: 'on_hold',
      updated_at: SAFE_PARTNER_FIXTURE_TIME,
    },
    {
      amount: '-$55.00',
      code_label: 'CYBA-PAUSED-07',
      customer_label: 'masked-customer-003',
      customer_scope: 'workspace_scoped',
      geo: 'US',
      id: 'safe-conversion-reversed',
      kind: 'refund',
      notes: ['Reversed fixture row for attribution dispute coverage.'],
      order_label: 'SAFE-ORDER-003',
      status: 'reversed',
      updated_at: SAFE_PARTNER_FIXTURE_TIME,
    },
  ];
}

function createSafePartnerAnalyticsMetrics(): ListPartnerWorkspaceAnalyticsMetricsResponse {
  return [
    {
      id: 'safe-first-paid',
      key: 'first_paid',
      notes: ['Synthetic first-paid count from safe fixture rows.'],
      pii_redacted: true,
      source_of_truth: 'safe_fixture_partner_reporting_mart',
      trend: 'up',
      value: '1',
      workspace_scoped: true,
    },
    {
      id: 'safe-earnings-available',
      key: 'earnings_available',
      notes: ['Synthetic available earnings only; no production payout data.'],
      pii_redacted: true,
      source_of_truth: 'safe_fixture_partner_reporting_mart',
      trend: 'steady',
      value: '$280.00',
      workspace_scoped: true,
    },
  ];
}

function createSafePartnerReportExports(): ListPartnerWorkspaceReportExportsResponse {
  return [
    {
      cadence: 'on_demand',
      id: 'safe-statement-export',
      kind: 'statement_export',
      available_actions: ['schedule_export'],
      last_requested_at: null,
      notes: ['Safe fixture statement export uses masked customer labels.'],
      pii_fields_excluded: ['customer_email', 'customer_phone', 'payment_reference'],
      redaction_policy: 'safe_fixture_redacted_partner_export',
      source_of_truth: 'safe_fixture_partner_reporting_mart',
      status: 'available',
      thread_events: [],
    },
  ];
}

function createSafePartnerReviewRequests(): ListPartnerWorkspaceReviewRequestsResponse {
  return [
    {
      available_actions: ['respond'],
      due_date: SAFE_PARTNER_FIXTURE_TIME,
      id: 'safe-finance-review',
      kind: 'finance_profile',
      status: 'open',
      thread_events: [],
    },
  ];
}

function createSafePartnerTrafficDeclarations(): ListPartnerWorkspaceTrafficDeclarationsResponse {
  return [
    {
      id: 'safe-approved-sources',
      kind: 'approved_sources',
      notes: ['Declared channels use .example fixture destinations only.'],
      scope_label: 'Safe fixture sources',
      status: 'complete',
      updated_at: SAFE_PARTNER_FIXTURE_TIME,
    },
  ];
}

function createSafePartnerCases(): ListPartnerWorkspaceCasesResponse {
  return [
    {
      available_actions: ['respond'],
      id: 'safe-attribution-dispute',
      kind: 'attribution_dispute',
      notes: ['Synthetic dispute covering paused code and reversed fixture row.'],
      status: 'open',
      thread_events: [],
      updated_at: SAFE_PARTNER_FIXTURE_TIME,
    },
    {
      available_actions: ['respond'],
      id: 'safe-payout-dispute',
      kind: 'payout_dispute',
      notes: ['Synthetic payout moderation case; no live payout execution.'],
      status: 'waiting_on_ops',
      thread_events: [],
      updated_at: SAFE_PARTNER_FIXTURE_TIME,
    },
  ];
}

function createSafePartnerNotifications(status = 'active'): ListPartnerNotificationsResponse {
  const constrained = status === 'suspended' || status === 'terminated';

  return [
    {
      action_required: constrained,
      created_at: SAFE_PARTNER_FIXTURE_TIME,
      id: constrained ? 'safe-workspace-disabled' : 'safe-workspace-active',
      kind: constrained ? 'workspace_restricted' : 'workspace_active',
      message: constrained
        ? 'Safe fixture workspace is read-only for remediation checks.'
        : 'Safe fixture workspace is active.',
      notes: ['No production partner, customer, or payment data is present.'],
      route_slug: constrained ? '/cases' : '/dashboard',
      source_event_id: null,
      source_event_kind: constrained ? 'workspace_disabled_fixture' : 'workspace_active_fixture',
      source_id: SAFE_PARTNER_FIXTURE_IDS.workspaceId,
      source_kind: 'workspace',
      tone: constrained ? 'critical' : 'success',
      unread: true,
    },
  ];
}

export function createSafePartnerBusinessFlowFixture(): SafePartnerBusinessFlowFixture {
  return {
    workspace: createSafePartnerWorkspace(),
    workspaceAnalyticsMetrics: createSafePartnerAnalyticsMetrics(),
    workspaceCases: createSafePartnerCases(),
    workspaceCodes: createSafePartnerCodes(),
    workspaceConversionRecords: createSafePartnerConversionRecords(),
    workspaceNotifications: createSafePartnerNotifications(),
    workspacePayoutAccounts: createSafePartnerPayoutAccounts(),
    workspacePayoutHistory: createSafePartnerPayoutHistory(),
    workspaceReportExports: createSafePartnerReportExports(),
    workspaceReviewRequests: createSafePartnerReviewRequests(),
    workspaceStatements: createSafePartnerStatements(),
    workspaceTrafficDeclarations: createSafePartnerTrafficDeclarations(),
  };
}

export function createSafePartnerSuspendedWorkspaceFixture(): SafePartnerBusinessFlowFixture {
  return {
    ...createSafePartnerBusinessFlowFixture(),
    workspace: createSafePartnerWorkspace({ status: 'suspended' }),
    workspaceCodes: createSafePartnerCodes(true),
    workspaceNotifications: createSafePartnerNotifications('suspended'),
    workspacePayoutAccounts: createSafePartnerPayoutAccounts(true),
  };
}

export function createSafePartnerDisabledWorkspaceFixture(): SafePartnerBusinessFlowFixture {
  return {
    ...createSafePartnerBusinessFlowFixture(),
    workspace: createSafePartnerWorkspace({
      permissionKeys: SAFE_PARTNER_ROLE_PERMISSION_FIXTURES.restricted,
      roleKey: 'analyst',
      status: 'terminated',
    }),
    workspaceNotifications: createSafePartnerNotifications('terminated'),
  };
}
