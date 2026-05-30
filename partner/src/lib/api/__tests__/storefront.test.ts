import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { storefrontApi } from '../storefront';

const API_BASE = '*/api/v1';

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

  it('loads a side-effect-free storefront preview contract', async () => {
    let storefrontKey = '';
    let partnerCode = '';

    server.use(
      http.get(`${API_BASE}/storefronts/:storefrontKey/preview`, ({ params, request }) => {
        storefrontKey = String(params.storefrontKey);
        partnerCode = new URL(request.url).searchParams.get('partner_code') ?? '';

        return HttpResponse.json({
          storefront_id: '550e8400-e29b-41d4-a716-446655440010',
          storefront_key: storefrontKey,
          display_name: 'Partner Storefront',
          status: 'active',
          route_contract: {
            storefront_key: storefrontKey,
            host: 'partner.example',
            preview_api_path: `/api/v1/storefronts/${storefrontKey}/preview`,
            customer_entry_path: '/storefront/partner',
            route_status: 'preview',
            public_launch_requires_stages: ['legal_acceptance'],
            checkout_side_effects: false,
          },
          branding_boundary: {
            brand_id: '550e8400-e29b-41d4-a716-446655440020',
            brand_key: 'cybervpn',
            brand_display_name: 'CyberVPN',
            brand_status: 'active',
            allowed_customizations: ['logo_lockup'],
            prohibited_claims: ['free_forever'],
            legal_copy_source: 'cybervpn',
          },
          pricing_boundary: {
            display_policy: 'storefront_pricebook',
            finance_policy: 'ledger_review_required',
            offers: [],
          },
          attribution_contract: {
            owner_type: 'reseller',
            owner_source: 'explicit_code',
            partner_account_id: '550e8400-e29b-41d4-a716-446655440060',
            partner_account_key: 'northstar',
            partner_account_status: 'active',
            partner_code_id: '550e8400-e29b-41d4-a716-446655440070',
            partner_code: partnerCode,
            partner_code_required_for_reseller: true,
            touchpoint_policy: 'preview_only',
          },
          analytics_contract: {
            preview_records_touchpoint: false,
            checkout_records_storefront_origin: true,
            checkout_records_explicit_code: true,
            expected_dimensions: ['storefront_key', 'partner_code'],
          },
          generated_at: '2026-05-30T12:00:00Z',
        });
      }),
    );

    const response = await storefrontApi.previewContract('reseller-eu', {
      partner_code: 'RESELLER-EU',
    });

    expect(response.status).toBe(200);
    expect(storefrontKey).toBe('reseller-eu');
    expect(partnerCode).toBe('RESELLER-EU');
    expect(response.data.route_contract.checkout_side_effects).toBe(false);
  });
});
