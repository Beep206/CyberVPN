import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { customersApi } from '../customers';

const MATCH_ANY_API_ORIGIN = {
  mobileUsers: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/mobile-users(?:\?.*)?$/,
  mobileUserById: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/mobile-users\/[^/]+$/,
  mobileUserSubscription: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/mobile-users\/[^/]+\/subscription$/,
  mobileUserNotes: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/mobile-users\/[^/]+\/notes(?:\?.*)?$/,
  mobileUserVpn: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/mobile-users\/[^/]+\/vpn-user$/,
  mobileUserVpnEnable: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/mobile-users\/[^/]+\/vpn-user\/enable$/,
  mobileUserVpnDisable: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/mobile-users\/[^/]+\/vpn-user\/disable$/,
  mobileUserDeviceById: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/mobile-users\/[^/]+\/devices\/[^/]+$/,
  mobileUserDevicesRevokeAll: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/mobile-users\/[^/]+\/devices\/revoke-all$/,
  mobileUserPasswordReset: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/mobile-users\/[^/]+\/credentials\/reset-password$/,
  mobileUserSubscriptionResync: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/mobile-users\/[^/]+\/subscription\/resync$/,
  mobileUserTimeline: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/mobile-users\/[^/]+\/timeline(?:\?.*)?$/,
  mobileUserOperationsInsight: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/mobile-users\/[^/]+\/operations-insight$/,
  mobileUserOperationsInsightActions: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/mobile-users\/[^/]+\/operations-insight\/actions$/,
  mobileUserWorkspaceEvidence: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/mobile-users\/[^/]+\/operations-insight\/exports\/workspaces\/[^/]+$/,
  mobileUserStatementEvidence: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/mobile-users\/[^/]+\/operations-insight\/exports\/partner-statements\/[^/]+$/,
  mobileUserPayoutInstructionEvidence: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/mobile-users\/[^/]+\/operations-insight\/exports\/payout-instructions\/[^/]+$/,
  mobileUserPayoutExecutionEvidence: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/mobile-users\/[^/]+\/operations-insight\/exports\/payout-executions\/[^/]+$/,
};

beforeEach(() => {
  localStorage.clear();
  window.location.href = 'http://localhost:3000';
});

afterEach(() => {
  window.location.href = 'http://localhost:3000';
});

describe('customersApi mobile user admin operations', () => {
  it('lists mobile users with admin filters', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.mobileUsers, () =>
        HttpResponse.json({
          items: [
            {
              id: '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
              email: 'customer@example.com',
              username: 'customer',
              status: 'active',
              is_active: true,
              is_partner: false,
              telegram_id: 123456,
              telegram_username: 'customer_tg',
              remnawave_uuid: 'remna_001',
              referral_code: 'REF-001',
              referred_by_user_id: null,
              partner_user_id: null,
              partner_promoted_at: null,
              created_at: '2026-04-10T11:00:00Z',
              last_login_at: '2026-04-10T12:00:00Z',
              device_count: 2,
            },
          ],
          total: 1,
          offset: 0,
          limit: 100,
        }),
      ),
    );

    const response = await customersApi.listMobileUsers({
      search: 'customer',
      is_active: true,
      offset: 0,
      limit: 100,
    });

    expect(response.status).toBe(200);
    expect(response.data.total).toBe(1);
    expect(response.data.items[0]?.device_count).toBe(2);
  });

  it('loads a mobile user detail card', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.mobileUserById, ({ request }) => {
        const userId = new URL(request.url).pathname.split('/').at(-1) ?? '';

        return HttpResponse.json({
          id: userId,
          email: 'customer@example.com',
          username: 'customer',
          status: 'active',
          is_active: true,
          is_partner: true,
          telegram_id: 123456,
          telegram_username: 'customer_tg',
          remnawave_uuid: 'remna_001',
          referral_code: 'REF-001',
          referred_by_user_id: null,
          partner_user_id: '1e0fc958-4206-4375-990c-52ce3a7bcdaa',
          partner_promoted_at: '2026-04-10T13:00:00Z',
          created_at: '2026-04-10T11:00:00Z',
          last_login_at: '2026-04-10T12:00:00Z',
          device_count: 2,
          subscription_url: 'https://example.com/subscription',
          updated_at: '2026-04-10T14:00:00Z',
          devices: [
            {
              id: 'ae37a6f7-6eb5-411c-b02e-0b57c5b1f034',
              device_id: 'device_001',
              platform: 'ios',
              platform_id: 'apple',
              os_version: '18.1',
              app_version: '1.4.0',
              device_model: 'iPhone 16',
              push_token: null,
              registered_at: '2026-04-10T11:00:00Z',
              last_active_at: '2026-04-10T13:30:00Z',
            },
          ],
        });
      }),
    );

    const response = await customersApi.getMobileUser('9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0');

    expect(response.status).toBe(200);
    expect(response.data.devices[0]?.device_model).toBe('iPhone 16');
    expect(response.data.subscription_url).toBe('https://example.com/subscription');
  });

  it('updates mobile user lifecycle and editable profile fields', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.patch(MATCH_ANY_API_ORIGIN.mobileUserById, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        const userId = new URL(request.url).pathname.split('/').at(-1) ?? '';

        return HttpResponse.json({
          id: userId,
          email: capturedBody.email ?? 'customer@example.com',
          username: capturedBody.username ?? 'customer',
          status: capturedBody.status ?? 'suspended',
          is_active: capturedBody.is_active ?? false,
          is_partner: false,
          telegram_id: capturedBody.telegram_id ?? 998877,
          telegram_username: capturedBody.telegram_username ?? 'customer_tg',
          remnawave_uuid: 'remna_001',
          referral_code: capturedBody.referral_code ?? 'REF-001',
          referred_by_user_id: null,
          partner_user_id: null,
          partner_promoted_at: null,
          created_at: '2026-04-10T11:00:00Z',
          last_login_at: '2026-04-10T12:00:00Z',
          device_count: 0,
          subscription_url: null,
          updated_at: '2026-04-10T14:00:00Z',
          devices: [],
        });
      }),
    );

    const response = await customersApi.updateMobileUser(
      '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
      {
        email: 'updated@example.com',
        username: 'updated_customer',
        telegram_id: 998877,
        telegram_username: 'updated_tg',
        referral_code: 'REF-UPDATED',
        status: 'suspended',
        is_active: false,
      },
    );

    expect(response.status).toBe(200);
    expect(response.data.status).toBe('suspended');
    expect(response.data.email).toBe('updated@example.com');
    expect(response.data.telegram_username).toBe('updated_tg');
    expect(capturedBody).toMatchObject({
      email: 'updated@example.com',
      username: 'updated_customer',
      telegram_id: 998877,
      telegram_username: 'updated_tg',
      referral_code: 'REF-UPDATED',
      status: 'suspended',
      is_active: false,
    });
  });

  it('loads a customer subscription snapshot', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.mobileUserSubscription, () =>
        HttpResponse.json({
          exists: true,
          remnawave_uuid: 'e13906f7-645a-4f28-8f5d-62167b9f01c7',
          status: 'active',
          short_uuid: 'vpn-001',
          subscription_uuid: '2a0668df-7a6a-4f00-b208-d4f71c25c887',
          expires_at: '2026-05-10T00:00:00Z',
          days_left: 29,
          traffic_limit_bytes: 10737418240,
          used_traffic_bytes: 2147483648,
          download_bytes: 1610612736,
          upload_bytes: 536870912,
          lifetime_used_traffic_bytes: 8589934592,
          online_at: '2026-04-10T15:30:00Z',
          sub_last_user_agent: 'Shadowrocket/2.2',
          sub_revoked_at: null,
          last_traffic_reset_at: '2026-04-01T00:00:00Z',
          hwid_device_limit: 5,
          subscription_url: 'https://sub.ozoxy.ru/config/example',
          config_available: true,
          config: 'vless://config-string',
          config_client_type: 'vless',
          config_error: null,
          links: ['vless://config-string'],
          ss_conf_links: {
            'Amsterdam iOS': 'ss://example',
          },
        }),
      ),
    );

    const response = await customersApi.getSubscriptionSnapshot('9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0');

    expect(response.status).toBe(200);
    expect(response.data.exists).toBe(true);
    expect(response.data.days_left).toBe(29);
    expect(response.data.config_client_type).toBe('vless');
    expect(response.data.links?.[0]).toBe('vless://config-string');
  });

  it('loads customer operations insight for support and finance overlays', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.mobileUserOperationsInsight, () =>
        HttpResponse.json({
          user_id: '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
          section_access: {
            explainability_visible: true,
            finance_visible: true,
            finance_actions_visible: true,
            risk_visible: false,
          },
          order_insights: [
            {
              order_explainability: {
                order: {
                  id: '3f26804f-fc9c-4df1-b571-20f06fd3340d',
                  settlement_status: 'paid',
                  sale_channel: 'web',
                  currency_code: 'USD',
                  displayed_price: 99,
                  commission_base_amount: 84,
                  partner_code_id: '86cbb361-377e-4d3f-b6fd-319c52a74856',
                  program_eligibility_policy_id: '9b1f69af-a8dd-4879-833f-7b7668b68f0c',
                  created_at: '2026-04-18T12:00:00Z',
                  updated_at: '2026-04-18T12:00:00Z',
                },
                commissionability_evaluation: {
                  id: '9599d6f4-eaa6-4af7-b7df-363f75c53f4f',
                  order_id: '3f26804f-fc9c-4df1-b571-20f06fd3340d',
                  commissionability_status: 'eligible',
                  reason_codes: ['phase6_admin_overlay'],
                  partner_context_present: true,
                  program_allows_commissionability: true,
                  positive_commission_base: true,
                  paid_status: true,
                  fully_refunded: false,
                  open_payment_dispute_present: false,
                  risk_allowed: true,
                  evaluation_snapshot: {},
                  explainability_snapshot: {},
                  evaluated_at: '2026-04-18T12:00:00Z',
                  created_at: '2026-04-18T12:00:00Z',
                  updated_at: '2026-04-18T12:00:00Z',
                },
                explainability: {
                  commercial_resolution_summary: {
                    resolved_partner_account_id: '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
                  },
                },
              },
              auth_realm_id: 'd6cc27a6-3560-4ca7-85f1-6c4f7ef39335',
              storefront_id: 'c3f4a9f0-9a7b-4dd6-8b32-48fa66014d23',
              attribution_result: null,
              payment_disputes: [],
              dispute_cases: [],
              resolved_partner_account_id: '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
            },
          ],
          settlement_workspaces: [
            {
              partner_account_id: '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
              payout_accounts: [],
              payout_account_actions: {},
              partner_statements: [],
              payout_instructions: [],
              payout_instruction_actions: {},
              payout_executions: [],
            },
          ],
          service_access_insights: [],
          risk_subject_insights: [],
        }),
      ),
    );

    const response = await customersApi.getOperationsInsight('9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0');

    expect(response.status).toBe(200);
    expect(response.data.section_access.finance_visible).toBe(true);
    expect(response.data.order_insights[0]?.order_explainability.order.sale_channel).toBe('web');
    expect(response.data.settlement_workspaces[0]?.partner_account_id).toBe('5d4c6d90-32aa-4a81-b430-b390f5684d7d');
  });

  it('submits customer operations actions through the consolidated admin rail', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.mobileUserOperationsInsightActions, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          action_kind: 'approve_payout_instruction',
          target_kind: 'payout_instruction',
          target_id: '4df8b78c-e5ee-43ba-b6c4-ac2818c353b7',
          payout_account: null,
          payout_instruction: {
            id: '4df8b78c-e5ee-43ba-b6c4-ac2818c353b7',
            partner_account_id: '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
            partner_statement_id: '113bdbd9-8c12-46dd-a4d8-5fa54c9680cc',
            partner_payout_account_id: 'fa8f6898-ebf5-47ea-9ec0-304f825d8b2e',
            instruction_key: 'stmt_customer_ops:pending',
            instruction_status: 'approved',
            payout_amount: 20,
            currency_code: 'USD',
            instruction_snapshot: {},
            created_by_admin_user_id: null,
            approved_by_admin_user_id: '4a2bb6d0-e12f-4f51-9200-702edc8dbe22',
            approved_at: '2026-04-18T12:10:00Z',
            rejected_by_admin_user_id: null,
            rejected_at: null,
            rejection_reason_code: null,
            completed_at: null,
            created_at: '2026-04-18T12:00:00Z',
            updated_at: '2026-04-18T12:10:00Z',
          },
        });
      }),
    );

    const response = await customersApi.performOperationsAction(
      '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
      {
        action_kind: 'approve_payout_instruction',
        payout_instruction_id: '4df8b78c-e5ee-43ba-b6c4-ac2818c353b7',
      },
    );

    expect(response.status).toBe(200);
    expect(response.data.payout_instruction?.instruction_status).toBe('approved');
    expect(capturedBody).toEqual({
      action_kind: 'approve_payout_instruction',
      payout_instruction_id: '4df8b78c-e5ee-43ba-b6c4-ac2818c353b7',
    });
  });

  it('downloads canonical customer operations evidence packs', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.mobileUserWorkspaceEvidence, () =>
        HttpResponse.json(
          {
            export_kind: 'workspace_finance_evidence',
            filename: 'workspace-evidence.json',
            exported_at: '2026-04-19T10:00:00Z',
            user_id: '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
            partner_account_id: '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
            scope: {
              statement_ids: ['113bdbd9-8c12-46dd-a4d8-5fa54c9680cc'],
            },
            evidence: {
              workspace: {
                partner_account_id: '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
              },
            },
          },
          {
            headers: {
              'Content-Disposition': 'attachment; filename="workspace-evidence.json"',
            },
          },
        ),
      ),
      http.get(MATCH_ANY_API_ORIGIN.mobileUserPayoutExecutionEvidence, () =>
        HttpResponse.json(
          {
            export_kind: 'payout_execution_evidence',
            filename: 'execution-evidence.json',
            exported_at: '2026-04-19T10:00:00Z',
            user_id: '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
            partner_account_id: '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
            scope: {
              payout_execution_id: '98aa0f0d-fc06-4087-bd6e-36bb63f4cf1e',
            },
            evidence: {
              payout_execution: {
                id: '98aa0f0d-fc06-4087-bd6e-36bb63f4cf1e',
              },
            },
          },
          {
            headers: {
              'Content-Disposition': 'attachment; filename="execution-evidence.json"',
            },
          },
        ),
      ),
    );

    const workspaceDownload = await customersApi.downloadWorkspaceFinanceEvidence(
      '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
      '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
    );
    const executionDownload = await customersApi.downloadPayoutExecutionEvidence(
      '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
      '98aa0f0d-fc06-4087-bd6e-36bb63f4cf1e',
    );

    expect(workspaceDownload.filename).toBe('workspace-evidence.json');
    expect(workspaceDownload.blob).toBeInstanceOf(Blob);
    expect(executionDownload.filename).toBe('execution-evidence.json');
    expect(executionDownload.blob).toBeInstanceOf(Blob);
  });

  it('lists and creates customer staff notes', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.get(MATCH_ANY_API_ORIGIN.mobileUserNotes, () =>
        HttpResponse.json([
          {
            id: '7d70a6e9-fdab-4179-ae70-cf0b5427bfa7',
            user_id: '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
            admin_id: '4a2bb6d0-e12f-4f51-9200-702edc8dbe22',
            category: 'support',
            note: 'Customer requested device reset.',
            created_at: '2026-04-10T14:30:00Z',
            updated_at: '2026-04-10T14:30:00Z',
            author: {
              id: '4a2bb6d0-e12f-4f51-9200-702edc8dbe22',
              login: 'support.ops',
              email: 'support@example.com',
              display_name: 'Support Ops',
            },
          },
        ]),
      ),
      http.post(MATCH_ANY_API_ORIGIN.mobileUserNotes, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          id: 'f0d86f34-13c4-4f12-b33b-fb8b85ba3f9f',
          user_id: '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
          admin_id: '4a2bb6d0-e12f-4f51-9200-702edc8dbe22',
          category: capturedBody.category ?? 'general',
          note: capturedBody.note ?? 'General note',
          created_at: '2026-04-10T14:35:00Z',
          updated_at: '2026-04-10T14:35:00Z',
          author: {
            id: '4a2bb6d0-e12f-4f51-9200-702edc8dbe22',
            login: 'support.ops',
            email: 'support@example.com',
            display_name: 'Support Ops',
          },
        }, { status: 201 });
      }),
    );

    const listResponse = await customersApi.listSupportNotes(
      '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
      { offset: 0, limit: 20 },
    );
    const createResponse = await customersApi.createSupportNote(
      '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
      { category: 'billing', note: 'Issued manual wallet credit after payment mismatch.' },
    );

    expect(listResponse.status).toBe(200);
    expect(listResponse.data[0]?.author?.display_name).toBe('Support Ops');
    expect(createResponse.status).toBe(201);
    expect(createResponse.data.category).toBe('billing');
    expect(capturedBody).toMatchObject({
      category: 'billing',
      note: 'Issued manual wallet credit after payment mismatch.',
    });
  });

  it('loads and mutates linked vpn user access', async () => {
    let enableBody: Record<string, unknown> | null = null;
    let disableBody: Record<string, unknown> | null = null;

    server.use(
      http.get(MATCH_ANY_API_ORIGIN.mobileUserVpn, () =>
        HttpResponse.json({
          exists: true,
          remnawave_uuid: 'e13906f7-645a-4f28-8f5d-62167b9f01c7',
          username: 'vpn_customer',
          email: 'customer@example.com',
          status: 'active',
          short_uuid: 'vpn-001',
          subscription_uuid: '2a0668df-7a6a-4f00-b208-d4f71c25c887',
          expire_at: '2026-05-10T00:00:00Z',
          traffic_limit_bytes: 10737418240,
          used_traffic_bytes: 2147483648,
          created_at: '2026-04-01T00:00:00Z',
          updated_at: '2026-04-10T12:00:00Z',
          telegram_id: 123456,
        }),
      ),
      http.post(MATCH_ANY_API_ORIGIN.mobileUserVpnEnable, async ({ request }) => {
        enableBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          exists: true,
          remnawave_uuid: 'e13906f7-645a-4f28-8f5d-62167b9f01c7',
          username: 'vpn_customer',
          email: 'customer@example.com',
          status: 'active',
          short_uuid: 'vpn-001',
          subscription_uuid: '2a0668df-7a6a-4f00-b208-d4f71c25c887',
        });
      }),
      http.post(MATCH_ANY_API_ORIGIN.mobileUserVpnDisable, async ({ request }) => {
        disableBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          exists: true,
          remnawave_uuid: 'e13906f7-645a-4f28-8f5d-62167b9f01c7',
          username: 'vpn_customer',
          email: 'customer@example.com',
          status: 'disabled',
          short_uuid: 'vpn-001',
          subscription_uuid: '2a0668df-7a6a-4f00-b208-d4f71c25c887',
        });
      }),
    );

    const vpnResponse = await customersApi.getVpnUser('9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0');
    const enableResponse = await customersApi.enableVpnUser(
      '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
      { reason: 'Recovered account after support verification.' },
    );
    const disableResponse = await customersApi.disableVpnUser(
      '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
      { reason: 'Temporary security hold.' },
    );

    expect(vpnResponse.status).toBe(200);
    expect(vpnResponse.data.exists).toBe(true);
    expect(vpnResponse.data.used_traffic_bytes).toBe(2147483648);
    expect(enableResponse.data.status).toBe('active');
    expect(disableResponse.data.status).toBe('disabled');
    expect(enableBody).toMatchObject({
      reason: 'Recovered account after support verification.',
    });
    expect(disableBody).toMatchObject({
      reason: 'Temporary security hold.',
    });
  });

  it('revokes a customer device', async () => {
    server.use(
      http.delete(MATCH_ANY_API_ORIGIN.mobileUserDeviceById, ({ request }) => {
        const pathname = new URL(request.url).pathname;
        const deviceId = pathname.split('/').at(-1) ?? '';

        return HttpResponse.json({
          id: deviceId,
          device_id: 'device_002',
          platform: 'android',
          platform_id: 'google',
          os_version: '15',
          app_version: '1.5.2',
          device_model: 'Pixel 10',
          push_token: null,
          registered_at: '2026-04-08T11:00:00Z',
          last_active_at: '2026-04-10T15:00:00Z',
        });
      }),
    );

    const response = await customersApi.revokeDevice(
      '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
      'aef4eb30-f1d7-4dae-b6d4-b74ef8df65af',
    );

    expect(response.status).toBe(200);
    expect(response.data.id).toBe('aef4eb30-f1d7-4dae-b6d4-b74ef8df65af');
    expect(response.data.device_model).toBe('Pixel 10');
  });

  it('revokes all customer devices with support context', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.mobileUserDevicesRevokeAll, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          user_id: '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
          revoked_count: 2,
          revoked_devices: [
            {
              id: 'ae37a6f7-6eb5-411c-b02e-0b57c5b1f034',
              device_id: 'device_001',
              platform: 'ios',
              platform_id: 'apple',
              os_version: '18.1',
              app_version: '1.4.0',
              device_model: 'iPhone 16',
              push_token: null,
              registered_at: '2026-04-10T11:00:00Z',
              last_active_at: '2026-04-10T13:30:00Z',
            },
            {
              id: 'fe1c4d24-db8d-4386-9bf2-7c1a9d2130a9',
              device_id: 'device_002',
              platform: 'android',
              platform_id: 'pixel',
              os_version: '15',
              app_version: '1.4.0',
              device_model: 'Pixel 9',
              push_token: null,
              registered_at: '2026-04-09T11:00:00Z',
              last_active_at: '2026-04-10T10:30:00Z',
            },
          ],
        });
      }),
    );

    const response = await customersApi.revokeAllDevices(
      '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
      { reason: 'Containment after suspicious session activity' },
    );

    expect(response.status).toBe(200);
    expect(response.data.revoked_count).toBe(2);
    expect(response.data.revoked_devices?.[1]?.device_model).toBe('Pixel 9');
    expect(capturedBody).toMatchObject({
      reason: 'Containment after suspicious session activity',
    });
  });

  it('resets a customer password and clears device sessions when requested', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.mobileUserPasswordReset, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          user_id: '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
          password_mode: 'generated',
          device_sessions_cleared: true,
          devices_revoked: 3,
          generated_password: 'TempPass-42!Shield',
        });
      }),
    );

    const response = await customersApi.resetPassword(
      '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
      {
        generate_temporary_password: true,
        revoke_all_devices: true,
        reason: 'Customer lost access after suspected credential reuse',
      },
    );

    expect(response.status).toBe(200);
    expect(response.data.password_mode).toBe('generated');
    expect(response.data.device_sessions_cleared).toBe(true);
    expect(response.data.devices_revoked).toBe(3);
    expect(response.data.generated_password).toBe('TempPass-42!Shield');
    expect(capturedBody).toMatchObject({
      generate_temporary_password: true,
      revoke_all_devices: true,
      reason: 'Customer lost access after suspected credential reuse',
    });
  });

  it('resyncs the stored customer subscription url from upstream', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.mobileUserSubscriptionResync, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          user_id: '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
          previous_subscription_url: 'https://old-sub.ozoxy.ru/config/example',
          stored_subscription_url: 'https://sub.ozoxy.ru/config/example',
          upstream_subscription_url: 'https://sub.ozoxy.ru/config/example',
          changed: true,
          config_available: true,
          config_client_type: 'vless',
          links_count: 4,
        });
      }),
    );

    const response = await customersApi.resyncSubscription(
      '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
      { reason: 'Refresh stale delivery link after support complaint' },
    );

    expect(response.status).toBe(200);
    expect(response.data.changed).toBe(true);
    expect(response.data.stored_subscription_url).toBe('https://sub.ozoxy.ru/config/example');
    expect(response.data.links_count).toBe(4);
    expect(capturedBody).toMatchObject({
      reason: 'Refresh stale delivery link after support complaint',
    });
  });

  it('loads the customer support timeline', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.mobileUserTimeline, () =>
        HttpResponse.json({
          items: [
            {
              id: 'payment_001',
              kind: 'payment',
              occurred_at: '2026-04-10T10:00:00Z',
              title: 'Payment via cryptobot',
              description: 'Subscription days: 30',
              status: 'completed',
              amount: 19.99,
              currency: 'USD',
              actor_label: null,
              metadata: {
                plan_id: 'plan_001',
              },
            },
            {
              id: 'note_001',
              kind: 'note',
              occurred_at: '2026-04-10T11:00:00Z',
              title: 'Staff note / support',
              description: 'Customer requested device cleanup.',
              status: null,
              amount: null,
              currency: null,
              actor_label: 'Support Ops',
              metadata: null,
            },
          ],
        }),
      ),
    );

    const response = await customersApi.getTimeline(
      '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
      { limit: 25 },
    );

    expect(response.status).toBe(200);
    expect(response.data.items).toHaveLength(2);
    expect(response.data.items[0]?.kind).toBe('payment');
    expect(response.data.items[1]?.actor_label).toBe('Support Ops');
  });
});
