'use client';

import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import type { StorefrontSurfaceContext } from '@/features/storefront-shell/lib/runtime';
import { server } from '@/test/mocks/server';
import { StorefrontLegalDocumentsShell } from './storefront-legal-documents-shell';

const API_BASE = 'http://storefront.localhost:3002/api/v1';

const surfaceContext: StorefrontSurfaceContext = {
  family: 'storefront',
  host: 'storefront.localhost:3002',
  canonicalHost: 'storefront.ozoxy.ru',
  brandKey: 'ozoxy',
  brandName: 'Ozoxy Secure Access',
  brandLabel: 'Ozoxy Secure Access Storefront',
  brandTagline: 'Partner-branded commerce shell',
  storefrontKey: 'ozoxy-storefront',
  authRealmKey: 'ozoxy-storefront',
  saleChannel: 'partner_storefront',
  defaultCurrency: 'USD',
  defaultPartnerCode: 'OZOXY42',
  supportProfile: {
    label: 'Ozoxy Storefront Support',
    email: 'support@ozoxy.ru',
    responseWindow: '24h',
    helpCenterUrl: 'https://ozoxy.ru/help',
  },
  communicationProfile: {
    senderName: 'Ozoxy Secure Access',
    senderEmail: 'support@ozoxy.ru',
  },
  merchantProfile: {
    profileKey: 'ozoxy-merchant',
    legalEntityName: 'Ozoxy Commerce Ltd.',
    billingDescriptor: 'OZOXY*VPN',
    refundResponsibilityModel: 'merchant_of_record',
    chargebackLiabilityModel: 'merchant_of_record',
  },
  routes: {
    home: '/',
    checkout: '/checkout',
    support: '/support',
    legal: '/legal-docs',
    login: '/login',
  },
};

function renderShell() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <StorefrontLegalDocumentsShell
        surfaceContext={surfaceContext}
        locale="en-EN"
        labels={{
          eyebrow: 'Legal',
          title: 'Storefront legal',
          subtitle: 'Resolved legal set for {setName}',
          required: 'Required',
          optional: 'Optional',
          checkoutCta: 'Go to checkout',
          supportCta: 'Support',
          loading: 'Loading...',
          empty: 'No documents.',
        }}
      />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  window.location.href = 'http://storefront.localhost:3002/en-EN/legal-docs';
});

afterEach(() => {
  window.location.href = 'http://storefront.localhost:3002/en-EN/legal-docs';
});

describe('StorefrontLegalDocumentsShell', () => {
  it('shows a customer sign-in route when legal acceptance is attempted anonymously', async () => {
    server.use(
      http.get(`${API_BASE}/legal-documents/sets/resolve`, () =>
        HttpResponse.json({
          id: 'set_001',
          set_key: 'ozoxy-storefront-legal',
          storefront_id: 'storefront_001',
          auth_realm_id: 'realm_001',
          display_name: 'Ozoxy Legal Set',
          policy_version_id: 'policy_001',
          documents: [
            {
              id: 'item_001',
              legal_document_id: 'doc_001',
              required: true,
              display_order: 0,
            },
          ],
          created_at: '2026-04-18T00:00:00Z',
          updated_at: '2026-04-18T00:00:00Z',
        }),
      ),
      http.get(`${API_BASE}/legal-documents/`, () =>
        HttpResponse.json([
          {
            id: 'doc_001',
            document_key: 'tos',
            document_type: 'terms_of_service',
            locale: 'en-EN',
            title: 'Terms of Service',
            content_markdown: '# Terms',
            policy_version_id: 'policy_001',
            created_at: '2026-04-18T00:00:00Z',
            updated_at: '2026-04-18T00:00:00Z',
          },
        ]),
      ),
      http.get(`${API_BASE}/auth/session`, () =>
        HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 }),
      ),
    );

    renderShell();

    const signInLink = await screen.findByRole('link', { name: 'Customer sign in' });
    expect(signInLink).toHaveAttribute('href', expect.stringContaining('/login?redirect='));
  });

  it('shows accepted state when the current storefront legal set was already accepted', async () => {
    server.use(
      http.get(`${API_BASE}/legal-documents/sets/resolve`, () =>
        HttpResponse.json({
          id: 'set_001',
          set_key: 'ozoxy-storefront-legal',
          storefront_id: 'storefront_001',
          auth_realm_id: 'realm_001',
          display_name: 'Ozoxy Legal Set',
          policy_version_id: 'policy_001',
          documents: [
            {
              id: 'item_001',
              legal_document_id: 'doc_001',
              required: true,
              display_order: 0,
            },
          ],
          created_at: '2026-04-18T00:00:00Z',
          updated_at: '2026-04-18T00:00:00Z',
        }),
      ),
      http.get(`${API_BASE}/legal-documents/`, () =>
        HttpResponse.json([
          {
            id: 'doc_001',
            document_key: 'tos',
            document_type: 'terms_of_service',
            locale: 'en-EN',
            title: 'Terms of Service',
            content_markdown: '# Terms',
            policy_version_id: 'policy_001',
            created_at: '2026-04-18T00:00:00Z',
            updated_at: '2026-04-18T00:00:00Z',
          },
        ]),
      ),
      http.get(`${API_BASE}/auth/session`, () =>
        HttpResponse.json({
          id: 'usr_test_001',
          email: 'customer@example.com',
          login: 'customer',
          role: 'user',
          is_active: true,
          is_email_verified: true,
          created_at: '2026-04-18T00:00:00Z',
        }),
      ),
      http.get(`${API_BASE}/policy-acceptance/me`, () =>
        HttpResponse.json([
          {
            id: 'acceptance_001',
            legal_document_id: null,
            legal_document_set_id: 'set_001',
            storefront_id: 'storefront_001',
            auth_realm_id: 'realm_001',
            actor_principal_id: 'usr_test_001',
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

    renderShell();

    await waitFor(() => {
      expect(screen.getByText('Accepted')).toBeInTheDocument();
    });
    expect(screen.queryByRole('button', { name: 'Accept required documents' })).not.toBeInTheDocument();
  });
});
