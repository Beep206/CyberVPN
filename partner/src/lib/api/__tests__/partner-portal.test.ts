import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { partnerPortalApi } from '../partner-portal';

const API_BASE = 'http://portal.localhost:3002/api/v1';

beforeEach(() => {
  window.location.href = 'http://portal.localhost:3002/en-EN/dashboard';
});

afterEach(() => {
  window.location.href = 'http://portal.localhost:3002/en-EN/dashboard';
});

describe('partnerPortalApi', () => {
  it('lists my workspaces from the canonical partner portal endpoint', async () => {
    server.use(
      http.get(`${API_BASE}/partner-workspaces/me`, () =>
        HttpResponse.json([
          {
            id: 'workspace_001',
            account_key: 'nebula',
            display_name: 'Nebula',
            status: 'active',
            legacy_owner_user_id: null,
            created_by_admin_user_id: null,
            code_count: 2,
            active_code_count: 1,
            total_clients: 4,
            total_earned: 125.5,
            last_activity_at: null,
            current_role_key: 'owner',
            current_permission_keys: ['workspace_read', 'codes_read'],
            members: [],
          },
        ]),
      ),
    );

    const response = await partnerPortalApi.listMyWorkspaces();

    expect(response.status).toBe(200);
    expect(response.data[0]?.account_key).toBe('nebula');
  });

  it('lists partner notifications and marks them read through canonical inbox routes', async () => {
    let readPath: string | null = null;
    let readQuery: string | null = null;

    server.use(
      http.get(`${API_BASE}/partner-notifications`, ({ request }) => {
        const url = new URL(request.url);
        return HttpResponse.json([
          {
            id: 'review-request:request_001:open',
            kind: 'review_request_opened',
            tone: 'warning',
            route_slug: '/cases',
            message: 'Updated finance evidence is required for probation approval.',
            notes: ['Due date: 2026-04-24T12:00:00Z'],
            action_required: true,
            unread: true,
            created_at: '2026-04-20T10:00:00Z',
            source_kind: 'review_request',
            source_id: 'request_001',
            source_event_id: null,
            source_event_kind: 'review_request_open',
            workspace_id: url.searchParams.get('workspace_id'),
          },
        ]);
      }),
      http.post(/\/api\/v1\/partner-notifications\/review-request:request_001:open\/read/, ({ request }) => {
        const url = new URL(request.url);
        readPath = url.pathname;
        readQuery = url.search;
        return HttpResponse.json({
          notification_id: 'review-request:request_001:open',
          unread: false,
          archived: false,
          read_at: '2026-04-20T10:05:00Z',
          archived_at: null,
        });
      }),
    );

    const listResponse = await partnerPortalApi.listNotifications({
      workspace_id: 'workspace_001',
      include_archived: false,
    });
    const readResponse = await partnerPortalApi.markNotificationRead(
      'review-request:request_001:open',
      { workspace_id: 'workspace_001' },
    );

    expect(listResponse.status).toBe(200);
    expect(listResponse.data[0]?.kind).toBe('review_request_opened');
    expect(readResponse.status).toBe(200);
    expect(readPath).toBe('/api/v1/partner-notifications/review-request:request_001:open/read');
    expect(readQuery).toContain('workspace_id=workspace_001');
  });

  it('lists workspace codes from the workspace subresource', async () => {
    server.use(
      http.get(`${API_BASE}/partner-workspaces/workspace_001/codes`, () =>
        HttpResponse.json([
          {
            id: 'code_001',
            partner_account_id: 'workspace_001',
            partner_user_id: 'user_001',
            code: 'NEBULA42',
            markup_pct: 15,
            is_active: true,
            created_at: '2026-04-18T00:00:00Z',
            updated_at: '2026-04-18T00:00:00Z',
          },
        ]),
      ),
    );

    const response = await partnerPortalApi.listWorkspaceCodes('workspace_001');

    expect(response.status).toBe(200);
    expect(response.data[0]?.code).toBe('NEBULA42');
  });

  it('loads canonical workspace programs from the dedicated programs subresource', async () => {
    server.use(
      http.get(`${API_BASE}/partner-workspaces/workspace_001/programs`, () =>
        HttpResponse.json({
          canonical_source: 'pilot_cohorts',
          primary_lane_key: 'creator_affiliate',
          lane_memberships: [
            {
              lane_key: 'creator_affiliate',
              membership_status: 'approved_active',
              owner_context_label: 'Partner Ops',
              pilot_cohort_id: 'cohort_001',
              pilot_cohort_status: 'active',
              runbook_gate_status: 'green',
              blocking_reason_codes: [],
              warning_reason_codes: [],
              restriction_notes: ['Lane has an explicit canonical cohort and readiness trail.'],
              readiness_notes: ['Runbook gate: green.'],
              updated_at: '2026-04-19T09:00:00Z',
            },
          ],
          readiness_items: [
            {
              key: 'finance',
              status: 'ready',
              blocking_reason_codes: [],
              notes: ['At least one verified and approved payout account is available.'],
            },
          ],
          updated_at: '2026-04-19T09:00:00Z',
        }),
      ),
    );

    const response = await partnerPortalApi.getWorkspacePrograms('workspace_001');

    expect(response.status).toBe(200);
    expect(response.data.primary_lane_key).toBe('creator_affiliate');
    expect(response.data.lane_memberships[0]?.pilot_cohort_status).toBe('active');
  });

  it('lists workspace payout accounts from the workspace-scoped finance route', async () => {
    let capturedUrl: string | null = null;
    server.use(
      http.get(`${API_BASE}/partner-workspaces/workspace_001/payout-accounts`, ({ request }) => {
        capturedUrl = new URL(request.url).pathname;
        return HttpResponse.json([]);
      }),
    );

    const response = await partnerPortalApi.listWorkspacePayoutAccounts('workspace_001');

    expect(response.status).toBe(200);
    expect(capturedUrl).toBe('/api/v1/partner-workspaces/workspace_001/payout-accounts');
  });

  it('loads payout history from the workspace-scoped finance history route', async () => {
    server.use(
      http.get(`${API_BASE}/partner-workspaces/workspace_001/payout-history`, () =>
        HttpResponse.json([
          {
            id: 'execution:exec_001',
            instruction_id: 'instruction_001',
            execution_id: 'exec_001',
            partner_statement_id: 'statement_001',
            partner_payout_account_id: 'account_001',
            statement_key: '2026-04',
            payout_account_label: 'Primary USD wire',
            amount: 125.5,
            currency_code: 'USD',
            lifecycle_status: 'paid',
            instruction_status: 'approved',
            execution_status: 'succeeded',
            execution_mode: 'live',
            external_reference: 'payout_123',
            created_at: '2026-04-20T10:00:00Z',
            updated_at: '2026-04-20T11:00:00Z',
            notes: ['Execution completed successfully.'],
          },
        ]),
      ),
    );

    const response = await partnerPortalApi.listWorkspacePayoutHistory('workspace_001');

    expect(response.status).toBe(200);
    expect(response.data[0]?.lifecycle_status).toBe('paid');
    expect(response.data[0]?.payout_account_label).toBe('Primary USD wire');
  });

  it('lists workspace reporting and case overlays from canonical subresources', async () => {
    server.use(
      http.get(`${API_BASE}/partner-workspaces/workspace_001/conversion-records`, () =>
        HttpResponse.json([
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
            updated_at: '2026-04-18T10:00:00Z',
            notes: ['1 dispute record(s)'],
          },
        ]),
      ),
      http.get(`${API_BASE}/partner-workspaces/workspace_001/analytics-metrics`, () =>
        HttpResponse.json([
          {
            id: 'first_paid',
            key: 'first_paid',
            value: '1',
            trend: 'steady',
            notes: ['Attributed paid orders linked to the active workspace.'],
          },
        ]),
      ),
      http.get(`${API_BASE}/partner-workspaces/workspace_001/report-exports`, () =>
        HttpResponse.json([
          {
            id: 'statement-export',
            kind: 'statement_export',
            status: 'available',
            cadence: 'per_statement_close',
            notes: ['Frozen statement snapshots only.'],
            available_actions: ['schedule_export'],
            thread_events: [],
            last_requested_at: null,
          },
        ]),
      ),
      http.get(`${API_BASE}/partner-workspaces/workspace_001/review-requests`, () =>
        HttpResponse.json([
          {
            id: 'finance-profile:workspace_001',
            kind: 'finance_profile',
            due_date: '2026-04-25T10:00:00Z',
            status: 'open',
            available_actions: ['submit_response'],
            thread_events: [],
          },
        ]),
      ),
      http.get(`${API_BASE}/partner-workspaces/workspace_001/traffic-declarations`, () =>
        HttpResponse.json([
          {
            id: 'approved-sources:workspace_001',
            kind: 'approved_sources',
            status: 'complete',
            scope_label: 'Workspace-owned traffic sources',
            updated_at: '2026-04-25T10:00:00Z',
            notes: ['Declared sources are clear for the current workspace state.'],
          },
        ]),
      ),
      http.get(`${API_BASE}/partner-workspaces/workspace_001/cases`, () =>
        HttpResponse.json([
          {
            id: 'case:finance-profile:workspace_001',
            kind: 'finance_onboarding',
            status: 'waiting_on_partner',
            updated_at: '2026-04-25T10:00:00Z',
            notes: ['Review request kind: finance_profile'],
            available_actions: ['reply', 'mark_ready_for_ops'],
            thread_events: [],
          },
        ]),
      ),
    );

    const [
      conversionsResponse,
      analyticsResponse,
      exportsResponse,
      reviewRequestsResponse,
      trafficDeclarationsResponse,
      casesResponse,
    ] = await Promise.all([
      partnerPortalApi.listWorkspaceConversionRecords('workspace_001', {
        limit: 50,
        offset: 0,
      }),
      partnerPortalApi.listWorkspaceAnalyticsMetrics('workspace_001'),
      partnerPortalApi.listWorkspaceReportExports('workspace_001'),
      partnerPortalApi.listWorkspaceReviewRequests('workspace_001'),
      partnerPortalApi.listWorkspaceTrafficDeclarations('workspace_001'),
      partnerPortalApi.listWorkspaceCases('workspace_001'),
    ]);

    expect(conversionsResponse.status).toBe(200);
    expect(conversionsResponse.data[0]?.code_label).toBe('NEBULA42');
    expect(analyticsResponse.data[0]?.key).toBe('first_paid');
    expect(exportsResponse.data[0]?.kind).toBe('statement_export');
    expect(reviewRequestsResponse.data[0]?.kind).toBe('finance_profile');
    expect(trafficDeclarationsResponse.data[0]?.kind).toBe('approved_sources');
    expect(casesResponse.data[0]?.kind).toBe('finance_onboarding');
    expect(exportsResponse.data[0]?.available_actions).toEqual(['schedule_export']);
  });

  it('schedules workspace report exports through the canonical reporting workflow route', async () => {
    let scheduleBody: Record<string, unknown> | null = null;

    server.use(
      http.post(
        `${API_BASE}/partner-workspaces/workspace_001/report-exports/statement-export/schedule`,
        async ({ request }) => {
          scheduleBody = await request.json();
          return HttpResponse.json(
            {
              id: 'statement-export',
              kind: 'statement_export',
              status: 'scheduled',
              cadence: 'per_statement_close',
              notes: ['Frozen statement snapshots only.'],
              available_actions: ['schedule_export'],
              thread_events: [
                {
                  id: 'event_101',
                  action_kind: 'partner_export_requested',
                  message: 'Please prepare the next statement export snapshot.',
                  created_by_admin_user_id: 'admin_001',
                  created_at: '2026-04-19T12:40:00Z',
                },
              ],
              last_requested_at: '2026-04-19T12:40:00Z',
            },
            { status: 201 },
          );
        },
      ),
    );

    const response = await partnerPortalApi.scheduleWorkspaceReportExport(
      'workspace_001',
      'statement-export',
      {
        message: 'Please prepare the next statement export snapshot.',
        request_payload: {
          request_origin: 'partner_portal_reporting_surface',
        },
      },
    );

    expect(response.status).toBe(201);
    expect(response.data.last_requested_at).toBe('2026-04-19T12:40:00Z');
    expect(response.data.thread_events[0]?.action_kind).toBe('partner_export_requested');
    expect(scheduleBody).toEqual({
      message: 'Please prepare the next statement export snapshot.',
      request_payload: {
        request_origin: 'partner_portal_reporting_surface',
      },
    });
  });

  it('submits review-request and case workflow actions through canonical workspace inbox routes', async () => {
    let reviewRequestBody: Record<string, unknown> | null = null;
    let caseReplyBody: Record<string, unknown> | null = null;
    let readyForOpsBody: Record<string, unknown> | null = null;

    server.use(
      http.post(
        `${API_BASE}/partner-workspaces/workspace_001/review-requests/finance-profile:workspace_001/responses`,
        async ({ request }) => {
          reviewRequestBody = await request.json();
          return HttpResponse.json(
            {
              id: 'event_001',
              action_kind: 'partner_response_submitted',
              message: 'Uploaded payout profile evidence.',
              created_by_admin_user_id: 'admin_001',
              created_at: '2026-04-19T12:00:00Z',
            },
            { status: 201 },
          );
        },
      ),
      http.post(
        `${API_BASE}/partner-workspaces/workspace_001/cases/case:finance-profile:workspace_001/responses`,
        async ({ request }) => {
          caseReplyBody = await request.json();
          return HttpResponse.json(
            {
              id: 'event_002',
              action_kind: 'partner_reply',
              message: 'Added a finance follow-up note.',
              created_by_admin_user_id: 'admin_001',
              created_at: '2026-04-19T12:05:00Z',
            },
            { status: 201 },
          );
        },
      ),
      http.post(
        `${API_BASE}/partner-workspaces/workspace_001/cases/case:finance-profile:workspace_001/ready-for-ops`,
        async ({ request }) => {
          readyForOpsBody = await request.json();
          return HttpResponse.json(
            {
              id: 'event_003',
              action_kind: 'partner_ready_for_ops',
              message: 'Finance package is ready for ops review.',
              created_by_admin_user_id: 'admin_001',
              created_at: '2026-04-19T12:10:00Z',
            },
            { status: 201 },
          );
        },
      ),
    );

    const [reviewResponse, caseReplyResponse, readyForOpsResponse] = await Promise.all([
      partnerPortalApi.respondToWorkspaceReviewRequest(
        'workspace_001',
        'finance-profile:workspace_001',
        {
          message: 'Uploaded payout profile evidence.',
          response_payload: {
            response_origin: 'partner_portal_cases_surface',
          },
        },
      ),
      partnerPortalApi.respondToWorkspaceCase(
        'workspace_001',
        'case:finance-profile:workspace_001',
        {
          message: 'Added a finance follow-up note.',
          response_payload: {
            workflow_action: 'reply',
          },
        },
      ),
      partnerPortalApi.markWorkspaceCaseReadyForOps(
        'workspace_001',
        'case:finance-profile:workspace_001',
        {
          message: 'Finance package is ready for ops review.',
          response_payload: {
            workflow_action: 'mark_ready_for_ops',
          },
        },
      ),
    ]);

    expect(reviewResponse.status).toBe(201);
    expect(caseReplyResponse.status).toBe(201);
    expect(readyForOpsResponse.status).toBe(201);
    expect(reviewRequestBody).toEqual({
      message: 'Uploaded payout profile evidence.',
      response_payload: {
        response_origin: 'partner_portal_cases_surface',
      },
    });
    expect(caseReplyBody).toEqual({
      message: 'Added a finance follow-up note.',
      response_payload: {
        workflow_action: 'reply',
      },
    });
    expect(readyForOpsBody).toEqual({
      message: 'Finance package is ready for ops review.',
      response_payload: {
        workflow_action: 'mark_ready_for_ops',
      },
    });
  });

  it('submits workspace traffic declarations and creative approvals through canonical workspace subresources', async () => {
    let trafficBody: Record<string, unknown> | null = null;
    let creativeBody: Record<string, unknown> | null = null;

    server.use(
      http.post(
        `${API_BASE}/partner-workspaces/workspace_001/traffic-declarations`,
        async ({ request }) => {
          trafficBody = await request.json();
          return HttpResponse.json(
            {
              id: 'decl_001',
              partner_account_id: 'workspace_001',
              declaration_kind: 'postback_readiness',
              declaration_status: 'submitted',
              scope_label: 'Tracking and postback handoff',
              declaration_payload: { summary: 'Webhook destination prepared for review.' },
              notes: ['Webhook destination prepared for review.'],
              submitted_by_admin_user_id: 'admin_001',
              reviewed_by_admin_user_id: null,
              reviewed_at: null,
              created_at: '2026-04-19T10:00:00Z',
              updated_at: '2026-04-19T10:00:00Z',
            },
            { status: 201 },
          );
        },
      ),
      http.post(
        `${API_BASE}/partner-workspaces/workspace_001/creative-approvals`,
        async ({ request }) => {
          creativeBody = await request.json();
          return HttpResponse.json(
            {
              id: 'creative_001',
              partner_account_id: 'workspace_001',
              approval_kind: 'creative_approval',
              approval_status: 'under_review',
              scope_label: 'Creative and claims posture',
              creative_ref: 'banner-001',
              approval_payload: { summary: 'Creative requires claims validation.' },
              notes: ['Creative requires claims validation.'],
              submitted_by_admin_user_id: 'admin_001',
              reviewed_by_admin_user_id: null,
              reviewed_at: null,
              expires_at: null,
              created_at: '2026-04-19T10:00:00Z',
              updated_at: '2026-04-19T10:00:00Z',
            },
            { status: 201 },
          );
        },
      ),
    );

    const [trafficResponse, creativeResponse] = await Promise.all([
      partnerPortalApi.submitWorkspaceTrafficDeclaration('workspace_001', {
        declaration_kind: 'postback_readiness',
        scope_label: 'Tracking and postback handoff',
        declaration_payload: { summary: 'Webhook destination prepared for review.' },
        notes: ['Webhook destination prepared for review.'],
      }),
      partnerPortalApi.submitWorkspaceCreativeApproval('workspace_001', {
        scope_label: 'Creative and claims posture',
        creative_ref: 'banner-001',
        approval_payload: { summary: 'Creative requires claims validation.' },
        notes: ['Creative requires claims validation.'],
      }),
    ]);

    expect(trafficResponse.status).toBe(201);
    expect(creativeResponse.status).toBe(201);
    expect(trafficBody).toEqual({
      declaration_kind: 'postback_readiness',
      scope_label: 'Tracking and postback handoff',
      declaration_payload: { summary: 'Webhook destination prepared for review.' },
      notes: ['Webhook destination prepared for review.'],
    });
    expect(creativeBody).toEqual({
      scope_label: 'Creative and claims posture',
      creative_ref: 'banner-001',
      approval_payload: { summary: 'Creative requires claims validation.' },
      notes: ['Creative requires claims validation.'],
    });
  });

  it('loads workspace-scoped conversion explainability from the canonical drilldown endpoint', async () => {
    server.use(
      http.get(
        `${API_BASE}/partner-workspaces/workspace_001/conversion-records/order_001/explainability`,
        () =>
          HttpResponse.json({
            order: {
              id: 'order_001',
              settlement_status: 'paid',
              sale_channel: 'web',
              currency_code: 'USD',
              displayed_price: 125,
              commission_base_amount: 100,
              partner_code_id: 'code_001',
              program_eligibility_policy_id: 'policy_001',
              created_at: '2026-04-18T10:00:00Z',
              updated_at: '2026-04-18T10:05:00Z',
            },
            commissionability_evaluation: {
              id: 'eval_001',
              order_id: 'order_001',
              commissionability_status: 'eligible',
              reason_codes: ['qualifying_first_payment'],
              partner_context_present: true,
              program_allows_commissionability: true,
              positive_commission_base: true,
              paid_status: true,
              fully_refunded: false,
              open_payment_dispute_present: false,
              risk_allowed: true,
              evaluation_snapshot: {},
              explainability_snapshot: {},
              evaluated_at: '2026-04-18T10:05:00Z',
              created_at: '2026-04-18T10:05:00Z',
              updated_at: '2026-04-18T10:05:00Z',
            },
            explainability: {
              commercial_resolution_summary: {
                resolved_owner_type: 'reseller',
                resolved_owner_source: 'persistent_reseller_binding',
              },
            },
          }),
      ),
    );

    const response = await partnerPortalApi.getWorkspaceConversionExplainability(
      'workspace_001',
      'order_001',
    );

    expect(response.status).toBe(200);
    expect(response.data.order.id).toBe('order_001');
    expect(response.data.commissionability_evaluation.commissionability_status).toBe(
      'eligible',
    );
    expect(
      response.data.explainability.commercial_resolution_summary.resolved_owner_source,
    ).toBe('persistent_reseller_binding');
  });

  it('loads workspace integration overlays from canonical subresources', async () => {
    server.use(
      http.get(`${API_BASE}/partner-workspaces/workspace_001/integration-credentials`, () =>
        HttpResponse.json([
          {
            id: 'cred_001',
            kind: 'reporting_api_token',
            status: 'ready',
            scope_key: 'reporting:partner:read',
            token_hint: 'rpt_***ABC123',
            destination_ref: 'reporting://partner-workspace/workspace_001',
            last_rotated_at: '2026-04-19T09:00:00Z',
            notes: ['Workspace-scoped reporting token for canonical marts and export reads.'],
          },
        ]),
      ),
      http.get(`${API_BASE}/partner-workspaces/workspace_001/integration-delivery-logs`, () =>
        HttpResponse.json([
          {
            id: 'delivery_001',
            channel: 'reporting_export',
            status: 'delivered',
            destination: 'reporting://partner-workspace/workspace_001',
            last_attempt_at: '2026-04-19T09:05:00Z',
            notes: ['Canonical analytical and replay consumers are green for this workspace.'],
          },
        ]),
      ),
      http.get(`${API_BASE}/partner-workspaces/workspace_001/postback-readiness`, () =>
        HttpResponse.json({
          status: 'complete',
          delivery_status: 'paused',
          scope_label: 'Tracking and postback handoff',
          credential_id: 'cred_002',
          credential_status: 'ready',
          notes: ['Postback credential is present and workspace-scoped delivery can be promoted when the consumer is enabled.'],
        }),
      ),
    );

    const [credentialsResponse, deliveryLogsResponse, readinessResponse] = await Promise.all([
      partnerPortalApi.listWorkspaceIntegrationCredentials('workspace_001'),
      partnerPortalApi.listWorkspaceIntegrationDeliveryLogs('workspace_001'),
      partnerPortalApi.getWorkspacePostbackReadiness('workspace_001'),
    ]);

    expect(credentialsResponse.status).toBe(200);
    expect(credentialsResponse.data[0]?.kind).toBe('reporting_api_token');
    expect(deliveryLogsResponse.data[0]?.channel).toBe('reporting_export');
    expect(readinessResponse.data.status).toBe('complete');
    expect(readinessResponse.data.delivery_status).toBe('paused');
  });
});
