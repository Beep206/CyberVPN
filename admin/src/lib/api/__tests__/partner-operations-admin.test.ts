import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { partnerOperationsApi } from '../partner-operations';

const MATCH_ANY_API_ORIGIN = {
  adminPartnerWorkspaces: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/partner-workspaces(?:\?.*)?$/,
  adminPartnerWorkspaceById: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/partner-workspaces\/[^/]+$/,
  adminPartnerApplications: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/partner-applications(?:\?.*)?$/,
  adminPartnerApplicationByWorkspace: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/partner-applications\/[^/]+$/,
  adminApproveProbation: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/partner-applications\/[^/]+\/approve-probation$/,
  adminLaneApprove: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/partner-applications\/[^/]+\/lane-applications\/[^/]+\/approve(?:\?.*)?$/,
  partnerPayoutAccountVerify: /https?:\/\/localhost(?::\d+)?\/api\/v1\/partner-payout-accounts\/[^/]+\/verify$/,
  payoutInstructions: /https?:\/\/localhost(?::\d+)?\/api\/v1\/payouts\/instructions(?:\?.*)?$/,
};

beforeEach(() => {
  localStorage.clear();
  window.location.href = 'http://localhost:3000';
});

afterEach(() => {
  window.location.href = 'http://localhost:3000';
});

describe('partnerOperationsApi', () => {
  it('lists admin partner workspaces with filters', async () => {
    let capturedSearch = '';
    let capturedStatus = '';

    server.use(
      http.get(MATCH_ANY_API_ORIGIN.adminPartnerWorkspaces, ({ request }) => {
        const url = new URL(request.url);
        capturedSearch = url.searchParams.get('search') ?? '';
        capturedStatus = url.searchParams.get('workspace_status') ?? '';

        return HttpResponse.json([
          {
            id: 'workspace_001',
            account_key: 'aurora-ops',
            display_name: 'Aurora Ops',
            status: 'under_review',
            legacy_owner_user_id: null,
            created_by_admin_user_id: 'admin_001',
            code_count: 3,
            active_code_count: 2,
            total_clients: 14,
            total_earned: 420.5,
            last_activity_at: '2026-04-20T09:00:00Z',
            current_role_key: null,
            current_permission_keys: [],
            members: [],
          },
        ]);
      }),
    );

    const response = await partnerOperationsApi.listWorkspaces({
      search: 'aurora',
      workspace_status: 'under_review',
      limit: 25,
      offset: 0,
    });

    expect(response.status).toBe(200);
    expect(response.data[0]?.display_name).toBe('Aurora Ops');
    expect(capturedSearch).toBe('aurora');
    expect(capturedStatus).toBe('under_review');
  });

  it('loads admin partner applications and detail', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.adminPartnerApplications, () =>
        HttpResponse.json([
          {
            workspace: {
              id: 'workspace_002',
              account_key: 'nebula-affiliates',
              display_name: 'Nebula Affiliates',
              status: 'submitted',
              current_role_key: null,
              current_permission_keys: [],
            },
            applicant: {
              id: 'admin_user_001',
              login: 'nebula.ops',
              email: 'ops@example.com',
              is_email_verified: true,
            },
            primary_lane: 'creator_affiliate',
            review_ready: true,
            submitted_at: '2026-04-19T12:00:00Z',
            updated_at: '2026-04-19T12:30:00Z',
            open_review_request_count: 1,
            lane_statuses: ['submitted'],
          },
        ]),
      ),
      http.get(MATCH_ANY_API_ORIGIN.adminPartnerApplicationByWorkspace, () =>
        HttpResponse.json({
          workspace: {
            id: 'workspace_002',
            account_key: 'nebula-affiliates',
            display_name: 'Nebula Affiliates',
            status: 'submitted',
            current_role_key: null,
            current_permission_keys: [],
          },
          applicant: {
            id: 'admin_user_001',
            login: 'nebula.ops',
            email: 'ops@example.com',
            is_email_verified: true,
          },
          draft: {
            id: 'draft_001',
            partner_account_id: 'workspace_002',
            applicant_admin_user_id: 'admin_user_001',
            workspace: {
              id: 'workspace_002',
              account_key: 'nebula-affiliates',
              display_name: 'Nebula Affiliates',
              status: 'submitted',
              current_role_key: null,
              current_permission_keys: [],
            },
            draft_payload: {
              workspace_name: 'Nebula Affiliates',
              contact_name: 'Ops',
              contact_email: 'ops@example.com',
              country: 'DE',
              website: 'https://example.com',
              primary_lane: 'creator_affiliate',
              business_description: 'Content operator',
              acquisition_channels: 'SEO, YouTube',
              operating_regions: 'EU',
              languages: 'en,de',
              support_contact: 'support@example.com',
              technical_contact: 'tech@example.com',
              finance_contact: 'finance@example.com',
              compliance_accepted: true,
            },
            review_ready: true,
            submitted_at: '2026-04-19T12:00:00Z',
            withdrawn_at: null,
            created_at: '2026-04-19T10:00:00Z',
            updated_at: '2026-04-19T12:30:00Z',
          },
          lane_applications: [],
          review_requests: [],
          attachments: [],
        }),
      ),
    );

    const listResponse = await partnerOperationsApi.listApplications();
    const detailResponse = await partnerOperationsApi.getApplication('workspace_002');

    expect(listResponse.status).toBe(200);
    expect(listResponse.data[0]?.workspace.display_name).toBe('Nebula Affiliates');
    expect(detailResponse.status).toBe(200);
    expect(detailResponse.data.draft.draft_payload.primary_lane).toBe('creator_affiliate');
  });

  it('submits admin application and lane approval actions', async () => {
    let approveBody: Record<string, unknown> | null = null;
    let approveTargetStatus = '';

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.adminApproveProbation, async ({ request }) => {
        approveBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          workspace: {
            id: 'workspace_003',
            account_key: 'aurora-affiliates',
            display_name: 'Aurora Affiliates',
            status: 'approved_probation',
            current_role_key: null,
            current_permission_keys: [],
          },
          applicant: null,
          draft: {
            id: 'draft_003',
            partner_account_id: 'workspace_003',
            applicant_admin_user_id: null,
            workspace: {
              id: 'workspace_003',
              account_key: 'aurora-affiliates',
              display_name: 'Aurora Affiliates',
              status: 'approved_probation',
              current_role_key: null,
              current_permission_keys: [],
            },
            draft_payload: {
              workspace_name: 'Aurora Affiliates',
              contact_name: '',
              contact_email: '',
              country: '',
              website: '',
              primary_lane: 'creator_affiliate',
              business_description: '',
              acquisition_channels: '',
              operating_regions: '',
              languages: '',
              support_contact: '',
              technical_contact: '',
              finance_contact: '',
              compliance_accepted: true,
            },
            review_ready: true,
            submitted_at: '2026-04-19T12:00:00Z',
            withdrawn_at: null,
            created_at: '2026-04-19T10:00:00Z',
            updated_at: '2026-04-19T12:30:00Z',
          },
          lane_applications: [],
          review_requests: [],
          attachments: [],
        });
      }),
      http.post(MATCH_ANY_API_ORIGIN.adminLaneApprove, async ({ request }) => {
        approveTargetStatus = new URL(request.url).searchParams.get('target_status') ?? '';
        await request.json();
        return HttpResponse.json({
          id: 'lane_001',
          partner_account_id: 'workspace_003',
          partner_application_draft_id: 'draft_003',
          lane_key: 'creator_affiliate',
          status: 'approved_active',
          application_payload: {},
          submitted_at: '2026-04-19T12:00:00Z',
          decided_at: '2026-04-20T10:00:00Z',
          decision_reason_code: 'manual_review',
          decision_summary: 'Ready for scale',
          created_at: '2026-04-19T10:00:00Z',
        });
      }),
    );

    const approveResponse = await partnerOperationsApi.approveApplicationProbation('workspace_003', {
      reason_code: 'manual_review',
      reason_summary: 'Ready for probation',
    });
    const laneResponse = await partnerOperationsApi.approveLaneApplication(
      'workspace_003',
      'lane_001',
      {
        reason_code: 'manual_review',
        reason_summary: 'Ready for scale',
      },
      { target_status: 'approved_active' },
    );

    expect(approveResponse.status).toBe(200);
    expect(approveBody).toMatchObject({
      reason_code: 'manual_review',
      reason_summary: 'Ready for probation',
    });
    expect(laneResponse.status).toBe(200);
    expect(approveTargetStatus).toBe('approved_active');
    expect(laneResponse.data.status).toBe('approved_active');
  });

  it('verifies payout accounts and lists payout instructions', async () => {
    let verifiedId = '';

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.partnerPayoutAccountVerify, ({ request }) => {
        verifiedId = new URL(request.url).pathname.split('/').at(-2) ?? '';
        return HttpResponse.json({
          id: verifiedId,
          partner_account_id: 'workspace_004',
          settlement_profile_id: null,
          payout_rail: 'bank_transfer',
          display_label: 'Primary EUR',
          masked_destination: 'DE89 **** 4432',
          destination_metadata: { currency: 'EUR' },
          verification_status: 'verified',
          approval_status: 'approved',
          account_status: 'active',
          is_default: true,
          created_by_admin_user_id: 'admin_001',
          verified_by_admin_user_id: 'admin_002',
          verified_at: '2026-04-20T10:00:00Z',
          approved_by_admin_user_id: 'admin_002',
          approved_at: '2026-04-20T10:05:00Z',
          suspended_by_admin_user_id: null,
          suspended_at: null,
          suspension_reason_code: null,
          archived_by_admin_user_id: null,
          archived_at: null,
          archive_reason_code: null,
          default_selected_by_admin_user_id: 'admin_002',
          default_selected_at: '2026-04-20T10:05:00Z',
          created_at: '2026-04-19T10:00:00Z',
          updated_at: '2026-04-20T10:05:00Z',
        });
      }),
      http.get(MATCH_ANY_API_ORIGIN.payoutInstructions, ({ request }) => {
        expect(new URL(request.url).searchParams.get('partner_account_id')).toBe('workspace_004');
        return HttpResponse.json([
          {
            id: 'instruction_001',
            partner_account_id: 'workspace_004',
            partner_statement_id: 'statement_001',
            partner_payout_account_id: 'payout_001',
            instruction_key: 'pi_001',
            instruction_status: 'draft',
            payout_amount: 420.5,
            currency_code: 'EUR',
            instruction_snapshot: {},
            created_by_admin_user_id: 'admin_001',
            approved_by_admin_user_id: null,
            approved_at: null,
            rejected_by_admin_user_id: null,
            rejected_at: null,
            rejection_reason_code: null,
            completed_at: null,
            created_at: '2026-04-20T09:00:00Z',
            updated_at: '2026-04-20T09:00:00Z',
          },
        ]);
      }),
    );

    const verifyResponse = await partnerOperationsApi.verifyPayoutAccount('payout_001');
    const instructionsResponse = await partnerOperationsApi.listPayoutInstructions({
      partner_account_id: 'workspace_004',
      limit: 10,
      offset: 0,
    });

    expect(verifyResponse.status).toBe(200);
    expect(verifiedId).toBe('payout_001');
    expect(verifyResponse.data.verification_status).toBe('verified');
    expect(instructionsResponse.status).toBe(200);
    expect(instructionsResponse.data[0]?.instruction_key).toBe('pi_001');
  });
});
