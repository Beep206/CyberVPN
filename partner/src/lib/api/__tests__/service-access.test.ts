import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import {
  createStorefrontServiceStateRequest,
  entitlementsApi,
  serviceAccessApi,
} from '../service-access';

const API_BASE = 'http://storefront.localhost:3002/api/v1';

beforeEach(() => {
  window.location.href = 'http://storefront.localhost:3002/en-EN/checkout';
});

afterEach(() => {
  window.location.href = 'http://storefront.localhost:3002/en-EN/checkout';
});

describe('service access storefront helpers', () => {
  it('creates a storefront-specific service state request payload', () => {
    expect(createStorefrontServiceStateRequest('ozoxy-storefront')).toEqual({
      provider_name: 'remnawave',
      channel_type: 'shared_client',
      credential_type: 'desktop_client',
      credential_subject_key: 'ozoxy-storefront-storefront',
    });
  });

  it('reads canonical current entitlement state', async () => {
    server.use(
      http.get(`${API_BASE}/entitlements/current`, () => HttpResponse.json({ status: 'active' })),
    );

    const response = await entitlementsApi.getCurrent();

    expect(response.status).toBe(200);
    expect(response.data.status).toBe('active');
  });

  it('posts current service-state requests to the canonical endpoint', async () => {
    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post(`${API_BASE}/access-delivery-channels/current/service-state`, async ({ request }) => {
        capturedBody = await request.json() as Record<string, unknown>;
        return HttpResponse.json({
          customer_account_id: 'user_001',
          auth_realm_id: 'realm_001',
          provider_name: 'remnawave',
          entitlement_snapshot: { status: 'active', effective_entitlements: {}, invite_bundle: {}, is_trial: false },
          purchase_context: {},
          consumption_context: {},
        });
      }),
    );

    const request = createStorefrontServiceStateRequest('ozoxy-storefront');
    const response = await serviceAccessApi.getCurrentServiceState(request);

    expect(response.status).toBe(200);
    expect(capturedBody).toMatchObject(request);
  });
});
