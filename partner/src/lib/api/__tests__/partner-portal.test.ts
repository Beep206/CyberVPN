import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { createSafePartnerBusinessFlowFixture } from '@/features/partner-portal-state/lib/safe-partner-fixtures';
import { server } from '@/test/mocks/server';
import { FRESH_AUTH_GRANT_ID_HEADER } from '../fresh-auth';
import { partnerPortalApi } from '../partner-portal';

const API_BASE = '*/api/v1';
const ORIGINAL_SEND_BEACON = navigator.sendBeacon;
const sendBeacon = vi.fn();

beforeEach(() => {
  sendBeacon.mockClear();
  Object.defineProperty(window.navigator, 'sendBeacon', {
    configurable: true,
    value: sendBeacon,
  });
  window.location.href = 'http://portal.localhost:3002/en-EN/dashboard';
});

afterEach(() => {
  Object.defineProperty(window.navigator, 'sendBeacon', {
    configurable: true,
    value: ORIGINAL_SEND_BEACON,
  });
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

  it('lists workspace campaign assets and reseller voucher batches from canonical workspace subresources', async () => {
    server.use(
      http.get(`${API_BASE}/partner-workspaces/workspace_001/campaign-assets`, () =>
        HttpResponse.json([
          {
            id: 'asset_001',
            name: 'Spring creative bundle',
            channel: 'telegram',
            status: 'approved',
            approval_owner: 'Partner Ops',
            updated_at: '2026-04-18T09:15:00Z',
            promo_reference: 'SPRING-TELEGRAM-2026',
            disclosure_text: '#ad · CyberVPN seasonal launch copy only',
            allowed_claims: ['Seasonal onboarding bonus'],
            banned_claims: ['Guaranteed earnings'],
            allowed_geographies: ['DE', 'PL'],
            destination_urls: ['https://offers.cybervpn.example/spring'],
            valid_from: '2026-04-18T00:00:00Z',
            valid_until: '2026-05-01T00:00:00Z',
            notes: ['Creative ref: tg-pack-2026'],
          },
        ]),
      ),
      http.get(`${API_BASE}/partner-workspaces/workspace_001/reseller-voucher-batches`, () =>
        HttpResponse.json([
          {
            batch_id: 'batch_001',
            gift_type: 'subscription_entitlement',
            plan_family: 'max',
            duration_days: 365,
            status: 'active',
            issued_count: 5,
            redeemed_count: 1,
            available_count: 4,
            expires_at: '2027-04-18T09:00:00Z',
            created_at: '2026-04-18T09:00:00Z',
            updated_at: '2026-04-19T10:20:00Z',
            notes: ['Plan: Max 365'],
          },
        ]),
      ),
    );

    const [assetsResponse, voucherBatchesResponse] = await Promise.all([
      partnerPortalApi.listWorkspaceCampaignAssets('workspace_001'),
      partnerPortalApi.listWorkspaceResellerVoucherBatches('workspace_001'),
    ]);

    expect(assetsResponse.status).toBe(200);
    expect(assetsResponse.data[0]?.promo_reference).toBe('SPRING-TELEGRAM-2026');
    expect(assetsResponse.data[0]?.allowed_geographies).toEqual(['DE', 'PL']);
    expect(voucherBatchesResponse.status).toBe(200);
    expect(voucherBatchesResponse.data[0]?.batch_id).toBe('batch_001');
    expect(voucherBatchesResponse.data[0]?.available_count).toBe(4);
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

  it('walks the safe partner business-flow fixture through canonical workspace subresources', async () => {
    const fixture = createSafePartnerBusinessFlowFixture();
    let statementQuery = '';
    let payoutHistoryQuery = '';

    server.use(
      http.get(`${API_BASE}/partner-workspaces/${fixture.workspace.id}/codes`, () =>
        HttpResponse.json(fixture.workspaceCodes),
      ),
      http.get(`${API_BASE}/partner-workspaces/${fixture.workspace.id}/conversion-records`, () =>
        HttpResponse.json(fixture.workspaceConversionRecords),
      ),
      http.get(`${API_BASE}/partner-workspaces/${fixture.workspace.id}/statements`, ({ request }) => {
        statementQuery = new URL(request.url).search;
        return HttpResponse.json(fixture.workspaceStatements);
      }),
      http.get(`${API_BASE}/partner-workspaces/${fixture.workspace.id}/payout-accounts`, () =>
        HttpResponse.json(fixture.workspacePayoutAccounts),
      ),
      http.get(`${API_BASE}/partner-workspaces/${fixture.workspace.id}/payout-history`, ({ request }) => {
        payoutHistoryQuery = new URL(request.url).search;
        return HttpResponse.json(fixture.workspacePayoutHistory);
      }),
    );

    const [codes, conversions, statements, payoutAccounts, payoutHistory] = await Promise.all([
      partnerPortalApi.listWorkspaceCodes(fixture.workspace.id),
      partnerPortalApi.listWorkspaceConversionRecords(fixture.workspace.id),
      partnerPortalApi.listWorkspaceStatements(fixture.workspace.id, {
        limit: 20,
        offset: 0,
        statement_status: 'closed',
      }),
      partnerPortalApi.listWorkspacePayoutAccounts(fixture.workspace.id),
      partnerPortalApi.listWorkspacePayoutHistory(fixture.workspace.id, {
        limit: 10,
        offset: 0,
      }),
    ]);

    expect(codes.status).toBe(200);
    expect(codes.data).toEqual(expect.arrayContaining([
      expect.objectContaining({ code: 'CYBA-SAFE-42', markup_pct: 12.5 }),
      expect.objectContaining({ code: 'CYBA-PAUSED-07', is_active: false }),
    ]));
    expect(conversions.data).toEqual(expect.arrayContaining([
      expect.objectContaining({
        code_label: 'CYBA-SAFE-42',
        customer_label: 'masked-customer-001',
        status: 'commissionable',
      }),
    ]));
    expect(statements.data[0]).toEqual(expect.objectContaining({
      available_amount: 280,
      statement_key: 'fixture_closed',
    }));
    expect(payoutAccounts.data).toEqual(expect.arrayContaining([
      expect.objectContaining({
        display_label: 'Safe fixture settlement account',
        masked_destination: 'Bank **** 4242',
      }),
    ]));
    expect(payoutHistory.data.map((item) => item.instruction_status)).toEqual([
      'draft',
      'approved',
      'rejected',
    ]);
    expect(statementQuery).toContain('statement_status=closed');
    expect(payoutHistoryQuery).toContain('limit=10');
    expect(payoutHistoryQuery).toContain('offset=0');
  });

  it('attaches fresh auth grants to partner security-sensitive workspace mutations', async () => {
    const capturedHeaders: Record<string, string | null> = {};

    server.use(
      http.patch(`${API_BASE}/partner-workspaces/workspace_001/settings`, async ({ request }) => {
        capturedHeaders.settings = request.headers.get(FRESH_AUTH_GRANT_ID_HEADER);
        return HttpResponse.json({
          is_email_verified: true,
          operator_email: 'operator@partner.example',
          operator_role: 'owner',
          payout_status_emails: true,
          prefer_passkeys: true,
          preferred_currency: 'USD',
          preferred_language: 'en-EN',
          product_announcements: false,
          require_mfa_for_workspace: true,
          reviewed_active_sessions: true,
          updated_at: '2026-06-03T12:30:00Z',
          workspace_security_alerts: true,
        });
      }),
      http.post(`${API_BASE}/partner-workspaces/workspace_001/payout-accounts`, async ({ request }) => {
        capturedHeaders.payoutCreate = request.headers.get(FRESH_AUTH_GRANT_ID_HEADER);
        return HttpResponse.json({
          account_status: 'pending_review',
          approval_status: 'pending_review',
          created_at: '2026-06-03T12:30:00Z',
          display_label: 'Primary US bank',
          id: 'payout_001',
          is_default: true,
          masked_destination: 'Bank **** 4242',
          payout_rail: 'bank_wire',
          updated_at: '2026-06-03T12:30:00Z',
          verification_status: 'pending',
        }, { status: 201 });
      }),
      http.post(`${API_BASE}/partner-workspaces/workspace_001/payout-accounts/payout_001/make-default`, async ({ request }) => {
        capturedHeaders.payoutDefault = request.headers.get(FRESH_AUTH_GRANT_ID_HEADER);
        return HttpResponse.json({
          account_status: 'ready',
          approval_status: 'approved',
          created_at: '2026-06-03T12:30:00Z',
          display_label: 'Primary US bank',
          id: 'payout_001',
          is_default: true,
          masked_destination: 'Bank **** 4242',
          payout_rail: 'bank_wire',
          updated_at: '2026-06-03T12:35:00Z',
          verification_status: 'verified',
        });
      }),
      http.post(`${API_BASE}/partner-workspaces/workspace_001/members`, async ({ request }) => {
        capturedHeaders.memberCreate = request.headers.get(FRESH_AUTH_GRANT_ID_HEADER);
        return HttpResponse.json({
          admin_user_id: 'admin_001',
          id: 'member_001',
          membership_status: 'active',
          operator_display_name: 'Finance Operator',
          operator_email: 'finance@partner.example',
          operator_login: 'finance',
          permission_keys: ['workspace_read'],
          role_display_name: 'Finance',
          role_key: 'finance',
        }, { status: 201 });
      }),
      http.patch(`${API_BASE}/partner-workspaces/workspace_001/members/member_001`, async ({ request }) => {
        capturedHeaders.memberUpdate = request.headers.get(FRESH_AUTH_GRANT_ID_HEADER);
        return HttpResponse.json({
          admin_user_id: 'admin_001',
          id: 'member_001',
          membership_status: 'limited',
          operator_display_name: 'Finance Operator',
          operator_email: 'finance@partner.example',
          operator_login: 'finance',
          permission_keys: ['workspace_read'],
          role_display_name: 'Analyst',
          role_key: 'analyst',
        });
      }),
    );

    await partnerPortalApi.updateWorkspaceSettings(
      'workspace_001',
      {
        payout_status_emails: true,
        prefer_passkeys: true,
        preferred_currency: 'USD',
        preferred_language: 'en-EN',
        product_announcements: false,
        require_mfa_for_workspace: true,
        reviewed_active_sessions: true,
        workspace_security_alerts: true,
      },
      { freshAuthGrantId: 'fresh-settings-grant' },
    );
    await partnerPortalApi.createWorkspacePayoutAccount(
      'workspace_001',
      {
        destination_reference: 'bank-account-token',
        display_label: 'Primary US bank',
        make_default: true,
        payout_rail: 'bank_wire',
      },
      { freshAuthGrantId: 'fresh-payout-create-grant' },
    );
    await partnerPortalApi.makeWorkspacePayoutAccountDefault(
      'workspace_001',
      'payout_001',
      { freshAuthGrantId: 'fresh-payout-default-grant' },
    );
    await partnerPortalApi.createWorkspaceMember(
      'workspace_001',
      {
        operator_lookup: 'finance@partner.example',
        role_key: 'finance',
      },
      { freshAuthGrantId: 'fresh-member-create-grant' },
    );
    await partnerPortalApi.updateWorkspaceMember(
      'workspace_001',
      'member_001',
      {
        membership_status: 'limited',
        role_key: 'analyst',
      },
      { freshAuthGrantId: 'fresh-member-update-grant' },
    );

    expect(capturedHeaders).toEqual({
      memberCreate: 'fresh-member-create-grant',
      memberUpdate: 'fresh-member-update-grant',
      payoutCreate: 'fresh-payout-create-grant',
      payoutDefault: 'fresh-payout-default-grant',
      settings: 'fresh-settings-grant',
    });
  });

  it('lists partner bots from the canonical partner-bots family with workspace params', async () => {
    let capturedQuery: string | null = null;
    server.use(
      http.get(`${API_BASE}/partner-bots`, ({ request }) => {
        const url = new URL(request.url);
        capturedQuery = url.search;
        return HttpResponse.json([
          {
            id: 'bot_001',
            partner_account_id: 'workspace_001',
            storefront_id: null,
            bot_key: 'alpha-bot',
            display_name: 'Alpha Bot',
            short_description: 'Partner launch bot',
            long_description: null,
            telegram_bot_id: null,
            telegram_username: null,
            managed_by_bot_id: null,
            default_locale: 'en-EN',
            primary_color: '#00ffaa',
            provisioning_path: 'managed_bot',
            token_status: 'missing',
            status: 'draft',
            release_channel: 'stable',
            provisioning_last_error: null,
            provisioning_requested_at: null,
            provisioned_at: null,
            suspended_at: null,
            suspension_reason_code: null,
            created_by_admin_user_id: null,
            updated_by_admin_user_id: null,
            created_at: '2026-04-22T10:00:00Z',
            updated_at: '2026-04-22T10:00:00Z',
            latest_provisioning_job: null,
          },
        ]);
      }),
    );

    const response = await partnerPortalApi.listPartnerBots({
      partner_account_id: 'workspace_001',
      limit: 20,
      offset: 0,
    });

    expect(response.status).toBe(200);
    expect(response.data[0]?.bot_key).toBe('alpha-bot');
    expect(capturedQuery).toContain('partner_account_id=workspace_001');
  });

  it('creates and mutates partner bots through the canonical partner-bots family', async () => {
    const captured: {
      createBody?: unknown;
      provisionBody?: unknown;
      rotateBody?: unknown;
      rotateFreshAuthGrantId?: string | null;
      suspendBody?: unknown;
      restorePath?: string;
    } = {};

    server.use(
      http.post(`${API_BASE}/partner-bots`, async ({ request }) => {
        captured.createBody = await request.json();
        return HttpResponse.json(
          {
            id: 'bot_001',
            partner_account_id: 'workspace_001',
            storefront_id: null,
            bot_key: 'alpha-bot',
            display_name: 'Alpha Bot',
            short_description: 'Partner launch bot',
            long_description: null,
            telegram_bot_id: null,
            telegram_username: null,
            managed_by_bot_id: null,
            default_locale: 'en-EN',
            primary_color: null,
            provisioning_path: 'manual_token',
            token_status: 'missing',
            status: 'draft',
            release_channel: 'stable',
            provisioning_last_error: null,
            provisioning_requested_at: null,
            provisioned_at: null,
            suspended_at: null,
            suspension_reason_code: null,
            created_by_admin_user_id: null,
            updated_by_admin_user_id: null,
            created_at: '2026-04-22T10:00:00Z',
            updated_at: '2026-04-22T10:00:00Z',
            latest_provisioning_job: null,
          },
          { status: 201 },
        );
      }),
      http.post(`${API_BASE}/partner-bots/bot_001/provision`, async ({ request }) => {
        captured.provisionBody = await request.json();
        return HttpResponse.json({
          id: 'bot_001',
          partner_account_id: 'workspace_001',
          storefront_id: null,
          bot_key: 'alpha-bot',
          display_name: 'Alpha Bot',
          short_description: 'Partner launch bot',
          long_description: null,
          telegram_bot_id: null,
          telegram_username: null,
          managed_by_bot_id: null,
          default_locale: 'en-EN',
          primary_color: null,
          provisioning_path: 'manual_token',
          token_status: 'missing',
          status: 'provisioning_requested',
          release_channel: 'stable',
          provisioning_last_error: null,
          provisioning_requested_at: '2026-04-22T10:10:00Z',
          provisioned_at: null,
          suspended_at: null,
          suspension_reason_code: null,
          created_by_admin_user_id: null,
          updated_by_admin_user_id: null,
          created_at: '2026-04-22T10:00:00Z',
          updated_at: '2026-04-22T10:10:00Z',
          latest_provisioning_job: {
            id: 'job_001',
            partner_bot_id: 'bot_001',
            partner_account_id: 'workspace_001',
            requested_by_admin_user_id: null,
            provisioning_path: 'manual_token',
            job_status: 'queued',
            attempt_count: 0,
            request_payload: {},
            result_payload: {},
            last_error: null,
            queued_at: '2026-04-22T10:10:00Z',
            started_at: null,
            completed_at: null,
            created_at: '2026-04-22T10:10:00Z',
            updated_at: '2026-04-22T10:10:00Z',
          },
        });
      }),
      http.post(`${API_BASE}/partner-bots/bot_001/rotate-token`, async ({ request }) => {
        captured.rotateBody = await request.json();
        captured.rotateFreshAuthGrantId = request.headers.get(FRESH_AUTH_GRANT_ID_HEADER);
        return HttpResponse.json({ status: 'provisioning_requested', token_status: 'rotating' });
      }),
      http.post(`${API_BASE}/partner-bots/bot_001/suspend`, async ({ request }) => {
        captured.suspendBody = await request.json();
        return HttpResponse.json({ status: 'suspended', suspension_reason_code: 'policy_hold' });
      }),
      http.post(`${API_BASE}/partner-bots/bot_001/restore`, ({ request }) => {
        captured.restorePath = new URL(request.url).pathname;
        return HttpResponse.json({ status: 'active' });
      }),
    );

    const createResponse = await partnerPortalApi.createPartnerBot({
      partner_account_id: 'workspace_001',
      bot_key: 'alpha-bot',
      display_name: 'Alpha Bot',
      provisioning_path: 'manual_token',
    });
    const provisionResponse = await partnerPortalApi.requestPartnerBotProvisioning('bot_001', {
      provisioning_path: 'manual_token',
      request_payload: { handoff_reference: 'bf-001' },
    });
    const rotateResponse = await partnerPortalApi.rotatePartnerBotToken('bot_001', {
      request_payload: { handoff_reference: 'bf-rotate-001' },
    }, {
      freshAuthGrantId: 'fresh-bot-token-rotate-grant',
    });
    const suspendResponse = await partnerPortalApi.suspendPartnerBot('bot_001', {
      reason_code: 'policy_hold',
    });
    const restoreResponse = await partnerPortalApi.restorePartnerBot('bot_001');

    expect(createResponse.status).toBe(201);
    expect(provisionResponse.status).toBe(200);
    expect(rotateResponse.status).toBe(200);
    expect(suspendResponse.status).toBe(200);
    expect(restoreResponse.status).toBe(200);
    expect(captured.createBody).toMatchObject({ bot_key: 'alpha-bot', provisioning_path: 'manual_token' });
    expect(captured.provisionBody).toMatchObject({ request_payload: { handoff_reference: 'bf-001' } });
    expect(captured.rotateBody).toMatchObject({ request_payload: { handoff_reference: 'bf-rotate-001' } });
    expect(captured.rotateFreshAuthGrantId).toBe('fresh-bot-token-rotate-grant');
    expect(captured.suspendBody).toMatchObject({ reason_code: 'policy_hold' });
    expect(captured.restorePath).toBe('/api/v1/partner-bots/bot_001/restore');
  });

  it('rotates workspace integration credentials with fresh-auth headers', async () => {
    let capturedFreshAuthGrantId: string | null = null;
    let capturedBody: unknown = null;

    server.use(
      http.post(
        `${API_BASE}/partner-workspaces/workspace_001/integration-credentials/reporting_api_token/rotate`,
        async ({ request }) => {
          capturedFreshAuthGrantId = request.headers.get(FRESH_AUTH_GRANT_ID_HEADER);
          capturedBody = await request.json();
          return HttpResponse.json({
            credential: {
              blocking_reason_codes: [],
              created_at: '2026-04-22T10:10:00Z',
              destination_ref: null,
              id: 'credential_001',
              kind: 'reporting_api_token',
              label: 'Reporting API token',
              last_rotated_at: '2026-04-22T10:10:00Z',
              metadata: { surface: 'partner_portal' },
              status: 'ready',
              updated_at: '2026-04-22T10:10:00Z',
              workspace_id: 'workspace_001',
            },
            issued_at: '2026-04-22T10:10:00Z',
            issued_secret: 'rpt_test_secret',
          });
        },
      ),
    );

    const response = await partnerPortalApi.rotateWorkspaceIntegrationCredential(
      'workspace_001',
      'reporting_api_token',
      { credential_metadata: { surface: 'partner_portal' } },
      { freshAuthGrantId: 'fresh-reporting-token-rotate-grant' },
    );

    expect(response.status).toBe(200);
    expect(capturedBody).toMatchObject({ credential_metadata: { surface: 'partner_portal' } });
    expect(capturedFreshAuthGrantId).toBe('fresh-reporting-token-rotate-grant');
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

  it('uses workspace-scoped partner support ticket routes', async () => {
    const captured: {
      listQuery?: string;
      createBody?: unknown;
      replyBody?: unknown;
      closePath?: string;
      reopenPath?: string;
    } = {};

    const ticketDetail = {
      public_id: 'SUP-2026-001',
      status: 'open',
      category: 'setup',
      priority: 'normal',
      subject: 'Partner workspace setup',
      last_message_preview: 'Synthetic setup question.',
      created_at: '2026-05-29T10:00:00Z',
      updated_at: '2026-05-29T10:00:00Z',
      last_customer_message_at: null,
      last_support_message_at: null,
      resolved_at: null,
      closed_at: null,
      messages: [
        {
          author_label: 'partner',
          body: 'Synthetic setup question.',
          created_at: '2026-05-29T10:00:00Z',
        },
      ],
      events: [
        {
          actor_label: 'partner',
          event_type: 'ticket_created',
          from_value: null,
          to_value: 'open',
          audit_summary: 'Partner ticket created.',
          created_at: '2026-05-29T10:00:00Z',
        },
      ],
    };

    server.use(
      http.get(`${API_BASE}/partner-workspaces/workspace_001/support/tickets`, ({ request }) => {
        captured.listQuery = new URL(request.url).search;
        return HttpResponse.json({
          tickets: [ticketDetail],
          nextCursor: null,
        });
      }),
      http.post(`${API_BASE}/partner-workspaces/workspace_001/support/tickets`, async ({ request }) => {
        captured.createBody = await request.json();
        return HttpResponse.json(ticketDetail, { status: 201 });
      }),
      http.get(`${API_BASE}/partner-workspaces/workspace_001/support/tickets/SUP-2026-001`, () =>
        HttpResponse.json(ticketDetail),
      ),
      http.post(`${API_BASE}/partner-workspaces/workspace_001/support/tickets/SUP-2026-001/replies`, async ({ request }) => {
        captured.replyBody = await request.json();
        return HttpResponse.json({
          ...ticketDetail,
          status: 'pending_support',
        });
      }),
      http.post(`${API_BASE}/partner-workspaces/workspace_001/support/tickets/SUP-2026-001/close`, ({ request }) => {
        captured.closePath = new URL(request.url).pathname;
        return HttpResponse.json({
          ...ticketDetail,
          status: 'closed',
        });
      }),
      http.post(`${API_BASE}/partner-workspaces/workspace_001/support/tickets/SUP-2026-001/reopen`, ({ request }) => {
        captured.reopenPath = new URL(request.url).pathname;
        return HttpResponse.json({
          ...ticketDetail,
          status: 'pending_support',
        });
      }),
    );

    const listResponse = await partnerPortalApi.listWorkspaceSupportTickets(
      'workspace_001',
      {
        category: 'setup',
        limit: 50,
        status: 'open',
      },
    );
    const createResponse = await partnerPortalApi.createWorkspaceSupportTicket(
      'workspace_001',
      {
        category: 'setup',
        message: 'Synthetic setup question.',
        priority: 'normal',
        subject: 'Partner workspace setup',
      },
    );
    const detailResponse = await partnerPortalApi.getWorkspaceSupportTicket(
      'workspace_001',
      'SUP-2026-001',
    );
    const replyResponse = await partnerPortalApi.replyToWorkspaceSupportTicket(
      'workspace_001',
      'SUP-2026-001',
      { message: 'Adding a partner-side reply.' },
    );
    const closeResponse = await partnerPortalApi.closeWorkspaceSupportTicket(
      'workspace_001',
      'SUP-2026-001',
    );
    const reopenResponse = await partnerPortalApi.reopenWorkspaceSupportTicket(
      'workspace_001',
      'SUP-2026-001',
    );

    expect(listResponse.status).toBe(200);
    expect(listResponse.data.tickets[0]?.public_id).toBe('SUP-2026-001');
    expect(captured.listQuery).toContain('status=open');
    expect(captured.listQuery).toContain('category=setup');
    expect(createResponse.status).toBe(201);
    expect(captured.createBody).toMatchObject({
      category: 'setup',
      message: 'Synthetic setup question.',
      priority: 'normal',
      subject: 'Partner workspace setup',
    });
    expect(captured.createBody).not.toHaveProperty('metadata');
    expect(captured.createBody).not.toHaveProperty('source');
    expect(detailResponse.data.public_id).toBe('SUP-2026-001');
    expect(detailResponse.data.messages[0]?.author_label).toBe('partner');
    expect(detailResponse.data).not.toHaveProperty('partner_workspace_id');
    expect(replyResponse.data.status).toBe('pending_support');
    expect(captured.replyBody).toEqual({ message: 'Adding a partner-side reply.' });
    expect(closeResponse.data.status).toBe('closed');
    expect(reopenResponse.data.status).toBe('pending_support');
    expect(captured.closePath).toBe('/api/v1/partner-workspaces/workspace_001/support/tickets/SUP-2026-001/close');
    expect(captured.reopenPath).toBe('/api/v1/partner-workspaces/workspace_001/support/tickets/SUP-2026-001/reopen');
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

  it('requests reseller voucher batches through canonical workspace subresources', async () => {
    let voucherBody: Record<string, unknown> | null = null;

    server.use(
      http.post(
        `${API_BASE}/partner-workspaces/workspace_001/reseller-voucher-batches/request`,
        async ({ request }) => {
          voucherBody = await request.json();
          return HttpResponse.json(
            {
              batch: {
                batch_id: 'batch_001',
                gift_type: 'subscription_entitlement',
                plan_family: 'max',
                duration_days: 365,
                status: 'active',
                issued_count: 3,
                redeemed_count: 0,
                available_count: 3,
                expires_at: '2027-04-18T09:00:00Z',
                created_at: '2026-04-18T09:00:00Z',
                updated_at: '2026-04-18T09:00:00Z',
                notes: ['Plan: Max 365'],
              },
              issued_codes: ['GFTMAX001', 'GFTMAX002', 'GFTMAX003'],
            },
            { status: 201 },
          );
        },
      ),
    );

    const response = await partnerPortalApi.requestWorkspaceResellerVoucherBatch(
      'workspace_001',
      {
        plan_id: 'plan_001',
        count: 3,
        recipient_hint: 'Spring reseller pack',
        gift_message: 'Priority storefront batch',
      },
    );

    expect(response.status).toBe(201);
    expect(voucherBody).toEqual({
      plan_id: 'plan_001',
      count: 3,
      recipient_hint: 'Spring reseller pack',
      gift_message: 'Priority storefront batch',
    });
    expect(response.data.batch.issued_count).toBe(3);
    expect(response.data.issued_codes).toEqual(['GFTMAX001', 'GFTMAX002', 'GFTMAX003']);
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
