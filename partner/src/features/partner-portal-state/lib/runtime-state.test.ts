import { describe, expect, it } from 'vitest';
import { createPartnerPortalScenarioState } from './portal-state';
import {
  applyPartnerSessionBootstrapToState,
  buildPartnerPortalRuntimeState,
  selectActivePartnerWorkspace,
} from './runtime-state';

describe('partner portal runtime state', () => {
  it('prefers the requested workspace when present', () => {
    const selected = selectActivePartnerWorkspace(
      [
        {
          id: 'workspace_001',
          account_key: 'nebula',
          display_name: 'Nebula',
          status: 'active',
          legacy_owner_user_id: null,
          created_by_admin_user_id: null,
          code_count: 2,
          active_code_count: 2,
          total_clients: 10,
          total_earned: 120,
          last_activity_at: null,
          current_role_key: 'owner',
          current_permission_keys: ['workspace_read'],
          members: [],
        },
        {
          id: 'workspace_002',
          account_key: 'nova',
          display_name: 'Nova',
          status: 'restricted',
          legacy_owner_user_id: null,
          created_by_admin_user_id: null,
          code_count: 1,
          active_code_count: 1,
          total_clients: 4,
          total_earned: 42,
          last_activity_at: null,
          current_role_key: 'finance',
          current_permission_keys: ['workspace_read', 'earnings_read'],
          members: [],
        },
      ],
      'workspace_002',
    );

    expect(selected?.id).toBe('workspace_002');
  });

  it('falls back to the first workspace when the requested one is not visible in the canonical runtime', () => {
    const selected = selectActivePartnerWorkspace(
      [
        {
          id: 'workspace_001',
          account_key: 'nebula',
          display_name: 'Nebula',
          status: 'active',
          legacy_owner_user_id: null,
          created_by_admin_user_id: null,
          code_count: 2,
          active_code_count: 2,
          total_clients: 10,
          total_earned: 120,
          last_activity_at: null,
          current_role_key: 'owner',
          current_permission_keys: ['workspace_read'],
          members: [],
        },
      ],
      'workspace_hidden',
    );

    expect(selected?.id).toBe('workspace_001');
  });

  it('applies canonical bootstrap state to shell-critical overlays', () => {
    const baseState = createPartnerPortalScenarioState(
      'needs_info',
      'creator_affiliate',
      'workspace_owner',
      'R1',
    );

    const state = applyPartnerSessionBootstrapToState({
      baseState,
      bootstrap: {
        principal: {
          id: 'admin_001',
          login: 'partner.ops',
          email: 'partner.ops@example.com',
          role: 'admin',
          is_active: true,
          is_email_verified: true,
          auth_realm_id: 'realm_001',
          auth_realm_key: 'partner',
          audience: 'cybervpn:partner',
          principal_type: 'partner_operator',
          scope_family: 'partner',
        },
        workspaces: [],
        active_workspace_id: 'workspace_001',
        active_workspace: {
          id: 'workspace_001',
          account_key: 'nebula',
          display_name: 'Nebula Partners',
          status: 'active',
          legacy_owner_user_id: null,
          created_by_admin_user_id: null,
          code_count: 1,
          active_code_count: 1,
          total_clients: 10,
          total_earned: 120,
          last_activity_at: '2026-04-20T10:00:00Z',
          current_role_key: 'owner',
          current_permission_keys: ['workspace_read', 'earnings_read', 'integrations_read'],
          members: [
            {
              id: 'member_001',
              admin_user_id: 'admin_001',
              role_id: 'role_001',
              role_key: 'owner',
              role_display_name: 'Owner',
              membership_status: 'active',
              permission_keys: ['workspace_read'],
              invited_by_admin_user_id: null,
              created_at: '2026-04-20T09:00:00Z',
              updated_at: '2026-04-20T09:00:00Z',
            },
          ],
        },
        workspace_resolution: 'requested',
        programs: {
          canonical_source: 'pilot_cohorts',
          primary_lane_key: 'performance_media',
          lane_memberships: [
            {
              lane_key: 'performance_media',
              membership_status: 'approved_active',
              owner_context_label: 'Ops owner',
              pilot_cohort_id: null,
              pilot_cohort_status: null,
              runbook_gate_status: 'green',
              blocking_reason_codes: [],
              warning_reason_codes: [],
              restriction_notes: [],
              readiness_notes: [],
              updated_at: '2026-04-20T10:00:00Z',
            },
          ],
          readiness_items: [],
          updated_at: '2026-04-20T10:00:00Z',
        },
        release_ring: 'R3',
        finance_readiness: 'in_progress',
        compliance_readiness: 'approved',
        technical_readiness: 'ready',
        governance_state: 'watch',
        current_permission_keys: ['workspace_read', 'earnings_read', 'integrations_read'],
        counters: {
          open_review_requests: 1,
          open_cases: 2,
          unread_notifications: 0,
          pending_tasks: 2,
        },
        pending_tasks: [],
        blocked_reasons: [],
        updated_at: '2026-04-20T10:00:00Z',
      },
    });

    expect(state.workspaceStatus).toBe('active');
    expect(state.releaseRing).toBe('R3');
    expect(state.primaryLane).toBe('performance_media');
    expect(state.financeReadiness).toBe('in_progress');
    expect(state.governanceState).toBe('watch');
    expect(state.currentPermissionKeys).toEqual(['workspace_read', 'earnings_read', 'integrations_read']);
    expect(state.activeWorkspaceId).toBe('workspace_001');
    expect(state.workspaceDataSource).toBe('canonical');
  });

  it('overlays canonical workspace, finance, and code data on the local portal state', () => {
    const baseState = createPartnerPortalScenarioState(
      'approved_probation',
      'creator_affiliate',
      'workspace_owner',
      'R2',
    );
    baseState.financeReadiness = 'blocked';

    const state = buildPartnerPortalRuntimeState({
      baseState,
      workspace: {
        id: 'workspace_001',
        account_key: 'nebula',
        display_name: 'Nebula Partners',
        status: 'active',
        legacy_owner_user_id: null,
        created_by_admin_user_id: null,
        code_count: 1,
        active_code_count: 1,
        total_clients: 10,
        total_earned: 120,
        last_activity_at: '2026-04-18T10:00:00Z',
        current_role_key: 'owner',
        current_permission_keys: ['workspace_read', 'codes_read', 'earnings_read', 'payouts_read', 'traffic_read', 'integrations_read'],
        members: [
          {
            id: 'member_001',
            admin_user_id: 'admin_001',
            role_id: 'role_001',
            role_key: 'owner',
            role_display_name: 'Owner',
            membership_status: 'active',
            permission_keys: ['workspace_read', 'codes_read', 'integrations_read'],
            invited_by_admin_user_id: null,
            created_at: '2026-04-18T09:00:00Z',
            updated_at: '2026-04-18T09:00:00Z',
          },
        ],
      },
      blockedReasons: [
        {
          code: 'compliance_evidence_requested',
          severity: 'warning',
          route_slug: 'compliance',
          notes: ['Upload the requested proof of channel ownership.'],
        },
        {
          code: 'governance_state:warning',
          severity: 'warning',
          route_slug: 'compliance',
          notes: ['Governance monitoring is active. Keep declarations current.'],
        },
      ],
      workspaceCodes: [
        {
          id: 'code_001',
          partner_account_id: 'workspace_001',
          partner_user_id: 'user_001',
          code: 'NEBULA42',
          markup_pct: 15,
          is_active: true,
          created_at: '2026-04-18T09:00:00Z',
          updated_at: '2026-04-18T09:00:00Z',
        },
      ],
      workspaceCampaignAssets: [
        {
          id: 'asset_001',
          name: 'Spring creative bundle',
          channel: 'telegram',
          status: 'approved',
          approval_owner: 'Partner Ops',
          updated_at: '2026-04-18T09:15:00Z',
          notes: ['Creative ref: tg-pack-2026'],
        },
      ],
      workspaceStatements: [
        {
          id: 'statement_001',
          partner_account_id: 'workspace_001',
          settlement_period_id: 'period_001',
          statement_key: '2026-04',
          statement_version: 1,
          statement_status: 'closed',
          reopened_from_statement_id: null,
          superseded_by_statement_id: null,
          currency_code: 'USD',
          accrual_amount: 150,
          on_hold_amount: 20,
          reserve_amount: 10,
          adjustment_net_amount: 0,
          available_amount: 120,
          source_event_count: 4,
          held_event_count: 1,
          active_reserve_count: 1,
          adjustment_count: 0,
          statement_snapshot: {},
          closed_at: '2026-04-18T09:30:00Z',
          closed_by_admin_user_id: 'admin_001',
          created_at: '2026-04-18T09:00:00Z',
          updated_at: '2026-04-18T10:00:00Z',
        },
      ],
      workspacePayoutAccounts: [
        {
          id: 'payout_001',
          settlement_profile_id: null,
          payout_rail: 'crypto_wallet',
          display_label: 'Primary payout',
          masked_destination: '***1234',
          destination_metadata: { currency: 'USD' },
          verification_status: 'verified',
          approval_status: 'approved',
          account_status: 'active',
          is_default: true,
          verified_at: null,
          approved_at: null,
          suspended_at: null,
          suspension_reason_code: null,
          archived_at: null,
          archive_reason_code: null,
          created_at: '2026-04-18T09:00:00Z',
          updated_at: '2026-04-18T10:00:00Z',
        },
      ],
      workspaceConversionRecords: [
        {
          id: 'order_001',
          kind: 'chargeback',
          status: 'on_hold',
          order_label: 'ORDER-001',
          customer_label: 'CUST-001',
          code_label: 'NEBULA42',
          geo: 'masked',
          amount: '125.00 USD',
          customer_scope: 'workspace_scoped',
          updated_at: '2026-04-18T10:30:00Z',
          notes: ['1 dispute record(s)'],
        },
      ],
      workspaceAnalyticsMetrics: [
        {
          id: 'chargeback_rate',
          key: 'chargeback_rate',
          value: '50.00%',
          trend: 'steady',
          notes: ['Computed from canonical payment dispute rows over visible workspace conversions.'],
        },
      ],
      workspaceReportExports: [
        {
          id: 'statement-export',
          kind: 'statement_export',
          status: 'available',
          cadence: 'per_statement_close',
          notes: ['Frozen statement snapshots only.'],
        },
      ],
      workspaceReviewRequests: [
        {
          id: 'finance-profile:workspace_001',
          kind: 'finance_profile',
          due_date: '2026-04-19T10:45:00Z',
          status: 'open',
        },
        {
          id: 'support-ownership:workspace_001',
          kind: 'support_ownership',
          due_date: '2026-04-19T10:46:00Z',
          status: 'submitted',
        },
      ],
      workspaceTrafficDeclarations: [
        {
          id: 'approved-sources:workspace_001',
          kind: 'approved_sources',
          status: 'complete',
          scope_label: 'Workspace-owned traffic sources',
          updated_at: '2026-04-19T10:30:00Z',
          notes: ['Declared sources are clear for the current workspace state.'],
        },
      ],
      workspaceCases: [
        {
          id: 'dispute:order_001',
          kind: 'payout_dispute',
          status: 'waiting_on_ops',
          updated_at: '2026-04-18T11:00:00Z',
          notes: ['1 dispute record(s)'],
        },
      ],
      workspaceNotifications: [
        {
          id: 'review-request:finance-profile:workspace_001:open',
          kind: 'review_request_opened',
          tone: 'warning',
          route_slug: '/cases',
          message: 'Updated finance evidence is required for probation approval.',
          notes: ['Due date: 2026-04-19T10:45:00Z'],
          action_required: true,
          unread: true,
          created_at: '2026-04-19T10:46:00Z',
          source_kind: 'review_request',
          source_id: 'finance-profile:workspace_001',
          source_event_id: null,
          source_event_kind: 'review_request_open',
        },
      ],
      workspaceIntegrationCredentials: [
        {
          id: 'cred_001',
          kind: 'reporting_api_token',
          status: 'ready',
          scope_key: 'reporting:partner:read',
          token_hint: 'rpt_***ABC123',
          destination_ref: 'reporting://partner-workspace/workspace_001',
          last_rotated_at: '2026-04-19T10:40:00Z',
          notes: ['Workspace-scoped reporting token for canonical marts and export reads.'],
        },
        {
          id: 'cred_002',
          kind: 'postback_secret',
          status: 'ready',
          scope_key: 'service:postbacks:write',
          token_hint: 'pbs_***XYZ999',
          destination_ref: 'postback://workspace/workspace_001',
          last_rotated_at: '2026-04-19T10:41:00Z',
          notes: ['Scoped postback credential for signed click-tracking and postback delivery.'],
        },
      ],
      workspaceIntegrationDeliveryLogs: [
        {
          id: 'delivery_001',
          channel: 'reporting_export',
          status: 'delivered',
          destination: 'reporting://partner-workspace/nebula',
          last_attempt_at: '2026-04-19T10:42:00Z',
          notes: ['Canonical analytical and replay consumers are green for this workspace.'],
        },
        {
          id: 'delivery_002',
          channel: 'postback',
          status: 'paused',
          destination: 'postback://workspace/nebula',
          last_attempt_at: '2026-04-19T10:42:00Z',
          notes: ['Postback credential is present and workspace-scoped delivery can be promoted when the consumer is enabled.'],
        },
      ],
    });

    expect(state.workspaceDataSource).toBe('canonical');
    expect(state.activeWorkspaceKey).toBe('nebula');
    expect(state.workspaceStatus).toBe('active');
    expect(state.workspaceRole).toBe('workspace_owner');
    expect(state.currentPermissionKeys).toContain('codes_read');
    expect(state.codes[0]?.label).toBe('NEBULA42');
    expect(state.campaignAssets[0]).toEqual({
      id: 'asset_001',
      name: 'Spring creative bundle',
      channel: 'telegram',
      status: 'approved',
      approvalOwner: 'Partner Ops',
      notes: ['Creative ref: tg-pack-2026'],
    });
    expect(state.financeReadiness).toBe('blocked');
    expect(state.financeStatements[0]?.status).toBe('ready');
    expect(state.payoutAccounts[0]?.status).toBe('ready');
    expect(state.conversionRecords[0]?.kind).toBe('chargeback');
    expect(state.analyticsMetrics[0]?.key).toBe('chargeback_rate');
    expect(state.reportExports[0]?.kind).toBe('statement_export');
    expect(state.integrationCredentials[0]?.kind).toBe('reporting_api_token');
    expect(state.integrationDeliveryLogs[0]?.channel).toBe('reporting_export');
    expect(state.reviewRequests[0]?.kind).toBe('finance_profile');
    expect(state.trafficDeclarations[0]?.kind).toBe('approved_sources');
    expect(state.cases[0]?.kind).toBe('payout_dispute');
    expect(state.notifications[0]?.kind).toBe('review_request_opened');
    expect(state.notifications[0]?.message).toContain('finance evidence');
    expect(state.complianceTasks.map((item) => item.kind)).toEqual([
      'disclosure_attestation',
      'evidence_upload',
      'support_ownership',
      'approved_sources',
    ]);
    expect(state.complianceTasks[0]?.status).toBe('action_required');
    expect(state.financeSnapshot.availableEarnings).toContain('120.00');
    expect(state.updatedAt).toBe('2026-04-19T10:46:00Z');
  });
});
