import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { storefrontApi } from '../storefront';

const API_BASE = 'http://storefront.localhost:3002/api/v1';

beforeEach(() => {
  window.location.href = 'http://storefront.localhost:3002/en-EN';
});

afterEach(() => {
  window.location.href = 'http://storefront.localhost:3002/en-EN';
});

describe('storefrontApi', () => {
  it('resolves pricebooks by storefront key', async () => {
    server.use(
      http.get(`${API_BASE}/pricebooks/resolve`, ({ request }) => {
        const url = new URL(request.url);
        return HttpResponse.json([
          {
            pricebook_key: 'ozoxy-usd',
            storefront_id: 'storefront_001',
            display_name: url.searchParams.get('storefront_key'),
            currency_code: 'USD',
            entries: [],
          },
        ]);
      }),
    );

    const response = await storefrontApi.resolvePricebooks({
      storefront_key: 'ozoxy-storefront',
      currency_code: 'USD',
    });

    expect(response.status).toBe(200);
    expect(response.data[0].display_name).toBe('ozoxy-storefront');
  });

  it('resolves storefront legal document sets', async () => {
    server.use(
      http.get(`${API_BASE}/legal-documents/sets/resolve`, () =>
        HttpResponse.json({
          id: 'set_001',
          set_key: 'ozoxy-storefront-legal',
          storefront_id: 'storefront_001',
          auth_realm_id: 'realm_001',
          display_name: 'Ozoxy Legal Set',
          policy_version_id: 'policy_001',
          documents: [],
          created_at: '2026-04-18T00:00:00Z',
          updated_at: '2026-04-18T00:00:00Z',
        })),
    );

    const response = await storefrontApi.resolveLegalDocumentSet({
      storefront_key: 'ozoxy-storefront',
    });

    expect(response.status).toBe(200);
    expect(response.data.set_key).toBe('ozoxy-storefront-legal');
  });

  it('creates canonical storefront policy acceptance records', async () => {
    let capturedChannel: string | null = null;

    server.use(
      http.post(`${API_BASE}/policy-acceptance/`, async ({ request }) => {
        const body = await request.json() as {
          acceptance_channel?: string;
          storefront_id?: string;
          legal_document_set_id?: string;
        };
        capturedChannel = body.acceptance_channel ?? null;

        return HttpResponse.json({
          id: 'acceptance_001',
          legal_document_id: null,
          legal_document_set_id: body.legal_document_set_id ?? null,
          storefront_id: body.storefront_id,
          auth_realm_id: 'realm_001',
          actor_principal_id: 'customer_001',
          actor_principal_type: 'customer',
          acceptance_channel: body.acceptance_channel,
          quote_session_id: null,
          checkout_session_id: null,
          order_id: null,
          source_ip: '127.0.0.1',
          user_agent: 'vitest',
          device_context: { surface_family: 'storefront' },
          accepted_at: '2026-04-18T10:00:00Z',
        });
      }),
    );

    const response = await storefrontApi.createPolicyAcceptance({
      legal_document_set_id: 'set_001',
      storefront_id: 'storefront_001',
      acceptance_channel: 'storefront_legal_surface',
      device_context: { surface_family: 'storefront' },
    });

    expect(response.status).toBe(200);
    expect(response.data.legal_document_set_id).toBe('set_001');
    expect(capturedChannel).toBe('storefront_legal_surface');
  });

  it('lists my policy acceptance history from the canonical endpoint', async () => {
    server.use(
      http.get(`${API_BASE}/policy-acceptance/me`, () =>
        HttpResponse.json([
          {
            id: 'acceptance_001',
            legal_document_id: null,
            legal_document_set_id: 'set_001',
            storefront_id: 'storefront_001',
            auth_realm_id: 'realm_001',
            actor_principal_id: 'customer_001',
            actor_principal_type: 'customer',
            acceptance_channel: 'storefront_legal_surface',
            quote_session_id: null,
            checkout_session_id: null,
            order_id: null,
            source_ip: '127.0.0.1',
            user_agent: 'vitest',
            device_context: { surface_family: 'storefront' },
            accepted_at: '2026-04-18T10:00:00Z',
          },
        ]),
      ),
    );

    const response = await storefrontApi.listMyPolicyAcceptance();

    expect(response.status).toBe(200);
    expect(response.data[0]?.legal_document_set_id).toBe('set_001');
  });
});
