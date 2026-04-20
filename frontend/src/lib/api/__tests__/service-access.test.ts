import { afterEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import {
  DEFAULT_SERVICE_STATE_REQUEST,
  entitlementsApi,
  serviceAccessApi,
} from '../service-access';
import { server } from '@/test/mocks/server';

const API_BASE = 'http://localhost:8000/api/v1';

afterEach(() => {
  server.resetHandlers();
});

describe('service-access api clients', () => {
  it('reads canonical current entitlements from /entitlements/current', async () => {
    server.use(
      http.get(`${API_BASE}/entitlements/current`, () =>
        HttpResponse.json({
          status: 'active',
          plan_uuid: 'plan-pro-001',
          plan_code: 'pro',
          display_name: 'Pro Plan',
          period_days: 30,
          expires_at: '2026-05-18T12:00:00Z',
          effective_entitlements: {
            device_limit: 5,
          },
          invite_bundle: {},
          is_trial: false,
          addons: [],
        }, { status: 200 })),
    );

    const response = await entitlementsApi.getCurrent();

    expect(response.status).toBe(200);
    expect(response.data.plan_code).toBe('pro');
    expect(response.data.status).toBe('active');
  });

  it('posts canonical current service-state resolution request', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(`${API_BASE}/access-delivery-channels/current/service-state`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          customer_account_id: 'user-001',
          auth_realm_id: 'realm-001',
          provider_name: 'remnawave',
          entitlement_snapshot: {
            status: 'active',
            plan_uuid: 'plan-pro-001',
            plan_code: 'pro',
            display_name: 'Pro Plan',
            period_days: 30,
            expires_at: '2026-05-18T12:00:00Z',
            effective_entitlements: {},
            invite_bundle: {},
            is_trial: false,
            addons: [],
          },
          service_identity: null,
          provisioning_profile: null,
          device_credential: null,
          access_delivery_channel: null,
          purchase_context: {
            active_entitlement_grant_id: null,
            source_type: null,
            source_order_id: null,
            source_growth_reward_allocation_id: null,
            source_renewal_order_id: null,
            manual_source_key: null,
            origin_storefront_id: null,
          },
          consumption_context: {
            channel_type: DEFAULT_SERVICE_STATE_REQUEST.channel_type,
            channel_subject_ref: DEFAULT_SERVICE_STATE_REQUEST.channel_subject_ref ?? null,
            provisioning_profile_key: DEFAULT_SERVICE_STATE_REQUEST.provisioning_profile_key ?? null,
            credential_type: DEFAULT_SERVICE_STATE_REQUEST.credential_type,
            credential_subject_key: DEFAULT_SERVICE_STATE_REQUEST.credential_subject_key,
          },
        }, { status: 200 });
      }),
    );

    const response = await serviceAccessApi.getCurrentServiceState();

    expect(response.status).toBe(200);
    expect(capturedBody).toMatchObject({
      provider_name: DEFAULT_SERVICE_STATE_REQUEST.provider_name,
      channel_type: DEFAULT_SERVICE_STATE_REQUEST.channel_type,
      credential_type: DEFAULT_SERVICE_STATE_REQUEST.credential_type,
      credential_subject_key: DEFAULT_SERVICE_STATE_REQUEST.credential_subject_key,
    });
  });
});
