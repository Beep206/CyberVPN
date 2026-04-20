import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { SubscriptionsClient } from '../SubscriptionsClient';
import { server } from '@/test/mocks/server';

vi.mock('../TrialSection', () => ({
  TrialSection: () => <div data-testid="trial-section">trial</div>,
}));

vi.mock('../CodesSection', () => ({
  CodesSection: () => <div data-testid="codes-section">codes</div>,
}));

vi.mock('../CancelSubscriptionModal', () => ({
  CancelSubscriptionModal: () => null,
}));

vi.mock('../PurchaseConfirmModal', () => ({
  PurchaseConfirmModal: () => null,
}));

const API_BASE = 'http://localhost:8000/api/v1';

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

function renderWithProviders(ui: ReactElement) {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
  );
}

const CURRENT_ENTITLEMENT = {
  status: 'active',
  plan_uuid: 'plan-pro-001',
  plan_code: 'pro',
  display_name: 'Pro Plan',
  period_days: 30,
  expires_at: '2026-05-18T12:00:00Z',
  effective_entitlements: {
    device_limit: 5,
    display_traffic_label: 'Unlimited',
    connection_modes: ['standard', 'stealth'],
    support_sla: 'priority',
  },
  invite_bundle: {},
  is_trial: false,
  addons: [],
};

const PLANS = [
  {
    uuid: 'plan-pro-001',
    name: 'PRO',
    plan_code: 'pro',
    display_name: 'Pro Plan',
    catalog_visibility: 'public',
    duration_days: 30,
    traffic_limit_bytes: null,
    devices_included: 5,
    price_usd: 29.99,
    price_rub: null,
    traffic_policy: {
      mode: 'fair_use',
      display_label: 'Unlimited',
      enforcement_profile: null,
    },
    connection_modes: ['standard', 'stealth'],
    server_pool: ['shared_plus'],
    support_sla: 'priority',
    dedicated_ip: {
      included: 0,
      eligible: true,
    },
    sale_channels: ['web'],
    invite_bundle: {
      count: 0,
      friend_days: 0,
      expiry_days: 0,
    },
    trial_eligible: false,
    features: {},
    is_active: true,
    sort_order: 10,
  },
  {
    uuid: 'plan-max-001',
    name: 'MAX',
    plan_code: 'max',
    display_name: 'Max Plan',
    catalog_visibility: 'public',
    duration_days: 90,
    traffic_limit_bytes: null,
    devices_included: 10,
    price_usd: 79.99,
    price_rub: null,
    traffic_policy: {
      mode: 'fair_use',
      display_label: 'Unlimited',
      enforcement_profile: null,
    },
    connection_modes: ['standard', 'stealth', 'manual_config'],
    server_pool: ['premium'],
    support_sla: 'vip',
    dedicated_ip: {
      included: 1,
      eligible: true,
    },
    sale_channels: ['web'],
    invite_bundle: {
      count: 0,
      friend_days: 0,
      expiry_days: 0,
    },
    trial_eligible: false,
    features: {},
    is_active: true,
    sort_order: 20,
  },
];

const ORDERS = [
  {
    id: 'order-paid-001',
    quote_session_id: 'quote-001',
    checkout_session_id: 'checkout-001',
    user_id: 'user-001',
    auth_realm_id: 'realm-001',
    storefront_id: 'storefront-001',
    merchant_profile_id: null,
    invoice_profile_id: null,
    billing_descriptor_id: null,
    pricebook_id: null,
    pricebook_entry_id: null,
    offer_id: null,
    legal_document_set_id: null,
    program_eligibility_policy_id: null,
    subscription_plan_id: 'plan-pro-001',
    promo_code_id: null,
    partner_code_id: null,
    sale_channel: 'web',
    currency_code: 'USD',
    order_status: 'committed',
    settlement_status: 'paid',
    base_price: 29.99,
    addon_amount: 0,
    displayed_price: 29.99,
    discount_amount: 0,
    wallet_amount: 0,
    gateway_amount: 29.99,
    partner_markup: 0,
    commission_base_amount: 29.99,
    merchant_snapshot: {},
    pricing_snapshot: {},
    policy_snapshot: {},
    entitlements_snapshot: {
      period_days: 30,
    },
    items: [
      {
        id: 'item-001',
        order_id: 'order-paid-001',
        item_type: 'plan',
        subject_id: 'plan-pro-001',
        subject_code: 'pro',
        display_name: 'Pro Plan',
        quantity: 1,
        unit_price: 29.99,
        total_price: 29.99,
        currency_code: 'USD',
        item_snapshot: {},
        created_at: '2026-04-18T10:00:00Z',
        updated_at: '2026-04-18T10:00:00Z',
      },
    ],
    created_at: '2026-04-18T10:00:00Z',
    updated_at: '2026-04-18T10:00:00Z',
  },
  {
    id: 'order-pending-001',
    quote_session_id: 'quote-002',
    checkout_session_id: 'checkout-002',
    user_id: 'user-001',
    auth_realm_id: 'realm-001',
    storefront_id: 'storefront-001',
    merchant_profile_id: null,
    invoice_profile_id: null,
    billing_descriptor_id: null,
    pricebook_id: null,
    pricebook_entry_id: null,
    offer_id: null,
    legal_document_set_id: null,
    program_eligibility_policy_id: null,
    subscription_plan_id: 'plan-max-001',
    promo_code_id: null,
    partner_code_id: null,
    sale_channel: 'web',
    currency_code: 'USD',
    order_status: 'committed',
    settlement_status: 'pending_payment',
    base_price: 79.99,
    addon_amount: 0,
    displayed_price: 79.99,
    discount_amount: 0,
    wallet_amount: 0,
    gateway_amount: 79.99,
    partner_markup: 0,
    commission_base_amount: 79.99,
    merchant_snapshot: {},
    pricing_snapshot: {},
    policy_snapshot: {},
    entitlements_snapshot: {
      period_days: 90,
    },
    items: [
      {
        id: 'item-002',
        order_id: 'order-pending-001',
        item_type: 'plan',
        subject_id: 'plan-max-001',
        subject_code: 'max',
        display_name: 'Max Plan',
        quantity: 1,
        unit_price: 79.99,
        total_price: 79.99,
        currency_code: 'USD',
        item_snapshot: {},
        created_at: '2026-04-17T09:00:00Z',
        updated_at: '2026-04-17T09:00:00Z',
      },
    ],
    created_at: '2026-04-17T09:00:00Z',
    updated_at: '2026-04-17T09:00:00Z',
  },
];

const CURRENT_SERVICE_STATE = {
  customer_account_id: 'user-001',
  auth_realm_id: 'realm-001',
  provider_name: 'remnawave',
  entitlement_snapshot: CURRENT_ENTITLEMENT,
  service_identity: {
    id: 'service-001',
    service_key: 'svc-remnawave-user-001',
    customer_account_id: 'user-001',
    auth_realm_id: 'realm-001',
    source_order_id: 'order-paid-001',
    origin_storefront_id: 'storefront-001',
    provider_name: 'remnawave',
    provider_subject_ref: 'remnawave-user-001',
    identity_status: 'active',
    service_context: {},
    created_at: '2026-04-18T10:00:00Z',
    updated_at: '2026-04-18T10:00:00Z',
  },
  provisioning_profile: {
    id: 'profile-001',
    service_identity_id: 'service-001',
    profile_key: 'ovpn-desktop',
    target_channel: 'shared_client',
    delivery_method: 'subscription_url',
    profile_status: 'active',
    provider_name: 'remnawave',
    provider_profile_ref: 'profile-ref-001',
    provisioning_payload: {},
    created_at: '2026-04-18T10:00:00Z',
    updated_at: '2026-04-18T10:00:00Z',
  },
  device_credential: null,
  access_delivery_channel: {
    id: 'channel-001',
    delivery_key: 'shared-client-001',
    service_identity_id: 'service-001',
    auth_realm_id: 'realm-001',
    origin_storefront_id: 'storefront-001',
    provisioning_profile_id: 'profile-001',
    device_credential_id: null,
    channel_type: 'shared_client',
    channel_status: 'active',
    channel_subject_ref: 'official-web-dashboard',
    provider_name: 'remnawave',
    delivery_context: {},
    delivery_payload: {},
    last_delivered_at: '2026-04-18T10:00:00Z',
    last_accessed_at: '2026-04-18T10:15:00Z',
    archived_at: null,
    archived_by_admin_user_id: null,
    archive_reason_code: null,
    created_at: '2026-04-18T10:00:00Z',
    updated_at: '2026-04-18T10:15:00Z',
  },
  purchase_context: {
    active_entitlement_grant_id: 'grant-001',
    source_type: 'order',
    source_order_id: 'order-paid-001',
    source_growth_reward_allocation_id: null,
    source_renewal_order_id: null,
    manual_source_key: null,
    origin_storefront_id: 'storefront-001',
  },
  consumption_context: {
    channel_type: 'shared_client',
    channel_subject_ref: 'official-web-dashboard',
    provisioning_profile_key: 'ovpn-desktop',
    credential_type: 'desktop_client',
    credential_subject_key: 'official-web-dashboard',
  },
};

describe('SubscriptionsClient', () => {
  afterEach(() => {
    server.resetHandlers();
  });

  it('renders canonical current entitlement, service state, and order history', async () => {
    server.use(
      http.get(`${API_BASE}/entitlements/current`, () =>
        HttpResponse.json(CURRENT_ENTITLEMENT, { status: 200 })),
      http.get(`${API_BASE}/plans`, ({ request }) => {
        expect(new URL(request.url).searchParams.get('channel')).toBe('web');
        return HttpResponse.json(PLANS, { status: 200 });
      }),
      http.get(`${API_BASE}/orders/`, () =>
        HttpResponse.json(ORDERS, { status: 200 })),
      http.post(`${API_BASE}/access-delivery-channels/current/service-state`, () =>
        HttpResponse.json(CURRENT_SERVICE_STATE, { status: 200 })),
    );

    renderWithProviders(<SubscriptionsClient />);

    expect((await screen.findAllByText('Pro Plan')).length).toBeGreaterThan(0);

    await waitFor(() => {
      expect(screen.getByText('shared_client')).toBeInTheDocument();
      expect(screen.getByText('ovpn-desktop')).toBeInTheDocument();
      expect(screen.getByText('awaiting payment')).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: /Current Plan/i })).toBeInTheDocument();
    expect(screen.getByText('remnawave')).toBeInTheDocument();
    expect(screen.getAllByText('Max Plan').length).toBeGreaterThan(0);
  });
});
